"""
消息中心、私信对话、他人资料页。

对应原版 Java 的 `controller/MessageController.java`（217 行）。

为什么单独一个 app 而不是塞进 accounts：这三页的核心是 `t_shop_message`
这张表，而人（`t_shop_user`）的部分只是配角。原版也是单独一个 Controller。

原版 `/user/` 这个前缀下挂了两个 Controller（UserController 和
MessageController），Django 这边同样是两个 include（config/urls.py 里
chat 的排在 accounts 前面），路径一条都不冲突。
"""

from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Follow, User
from accounts.services import user_card
from core import auth
from core.decorators import login_required
from core.http import back
from goods.models import FRONT_VISIBLE, Goods
from goods.services import cards

from . import services


def _int_or_none(raw):
    """把 query string / 表单里的一格文本转成 int，转不动就 None。

    `?goodsId=abc` 这种脏参数不该让页面 500。原版是让 Spring 自己转
    （转不动直接 400），这里给个 None 当成「没传」处理。
    """
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


# ================================================================ 消息中心

@login_required
def message(request):
    """消息中心，一页两个标签。

    `tab=notice`（系统通知，**默认**）/ `tab=chat`（私信会话列表）。

    两个标签的未读数都要传：标签上各自显示自己的数字（`noticeUnread` /
    `msgUnread`），而左侧栏和右上角那个红点用的是 context processor 里
    那对全局的 `unreadCount` / `unreadMsgCount`，来源相同但用途不同。

    原版在这里无条件 `addObject("cur_user", ...)`，Django 这边不用 ——
    `core/context_processors.py` 已经给每个模板都塞了一份，而且它是在
    视图之后跑的、**会覆盖**视图传的同名变量，传了反而容易看糊。
    """
    me = auth.current(request)
    return render(
        request,
        "user/message.html",
        {
            "tab": "chat" if request.GET.get("tab") == "chat" else "notice",
            "notices": services.list_notices(me["id"]),
            "noticeUnread": services.count_notice_unread(me["id"]),
            "sessions": services.list_sessions(me["id"]),
            "msgUnread": services.count_unread(me["id"]),
        },
    )


@require_POST
@login_required
def notice_read(request, id):
    """把一条系统通知标为已读。

    **属主校验在 SQL 里**（services.mark_notice_read 的 WHERE 带 user_id）：
    改一下 URL 上的 id 就能标掉别人的通知，而「已读」是别人看得见的状态。
    """
    services.mark_notice_read(id, auth.current(request)["id"])
    return back(request, "/user/message?tab=notice")


@require_POST
@login_required
def notice_read_all(request):
    """一次把所有未读通知标掉。"""
    services.mark_notices_read_all(auth.current(request)["id"])
    return back(request, "/user/message?tab=notice")


# ================================================================ 对话页

def chat(request, user_id):
    """和某个人的对话页。GET 看消息，POST 发一条。

    同一个地址两种方法（原版是两个方法挂同一个 @RequestMapping），
    这里收进一个函数：发完消息还是回到这一页，PRG 模式（POST-Redirect-GET）
    保持住，否则用户按 F5 会把刚才那条重复发出去。

    **副作用在 GET 这一支里**：打开对话就调用 `services.list_conversation`，
    它顺手把对方发来的未读标成已读。能触发标已读的地方只有这一个入口。
    """
    me = auth.current(request)
    if not me:
        return redirect("goods_home")

    if request.method == "POST":
        services.send(
            me["id"],
            user_id,
            _int_or_none(request.POST.get("goodsId")),
            request.POST.get("context"),
        )
        # 发失败（空内容、对方被冻结…）也静默回对话页 ——
        # 原版只记一行日志。前端 textarea 上有 required + maxlength 挡着，
        # 真走到这儿的多半是脚本直接打接口。
        return redirect("user_chat", user_id=user_id)

    # 和自己聊天没有意义，直接回消息中心
    if me["id"] == user_id:
        return redirect("/user/message?tab=chat")

    other = User.objects.filter(id=user_id).first()
    if other is None:
        return redirect("/user/message?tab=chat")

    # 商品可能已经被删了：取不到就不显示那一行，不能让整页挂掉
    goods_id = _int_or_none(request.GET.get("goodsId"))
    goods = Goods.objects.filter(id=goods_id).first() if goods_id else None

    return render(
        request,
        "user/chat.html",
        {
            "other": user_card(other),
            "messages": services.list_conversation(me["id"], user_id),
            # 关注按钮显示「关注 TA」还是「已关注」
            "followed": Follow.objects.filter(
                user_id=me["id"], follow_user_id=user_id
            ).exists(),
            # 只拿来提示一句「TA 关注了你」，不参与任何判断
            "followsMe": Follow.objects.filter(
                user_id=user_id, follow_user_id=me["id"]
            ).exists(),
            "goods": goods,
            # 「联系方式」那一块该显示成什么样。**手机号 / QQ / 微信是在
            # 这个函数里才从库里取出来的** —— 没到「已交换」的时候，
            # 返回的 dict 里那三个键是空字符串，模板少写一个 if 也漏不出去。
            "contact": services.contact_state(
                me["id"], user_id, _contact_ok_ids(request)
            ),
        },
    )


# ================================================================ 联系方式交换
#
# 四个动作各一个 URL、一个视图，都走 POST 然后跳回对话页（POST-Redirect-GET）。
# 用 POST 不用 GET 的理由和其他改状态的动作一样：GET 会被浏览器预取和爬虫踩到，
# 而「请求 / 同意」会往对方那边推一条通知。
#
# 越权校验全在 services 那一层：同意 / 拒绝的 WHERE 里带着 `to_user_id=me_id`
# （只能处理别人**发给我**的请求），撤销的 WHERE 里带着 `status=1`。
# 改 URL 上的 user_id 顶多是操作一个和自己无关的人，动不了别人的记录。


def _contact_ok_ids(request):
    """这次登录以来，我亲手点过「请求」或「同意」的人。

    存在 session 里，**不落库** —— 关掉浏览器重新登录，这份名单就是空的，
    必须重新请求。这是需求里明确要的（完整说明见 chat/services.py 那一大段）。

    类型过滤不是走过场：session 是签名 cookie，签名保证了它没被改过，
    但读出来时仍然不该假设里面一定是个干净的整数列表 —— 手工造一个
    空 session 再来访问是能发生的。
    """
    raw = request.session.get(services.CONTACT_SESSION_KEY)
    if not isinstance(raw, list):
        return []
    return [i for i in raw if isinstance(i, int)]


def _remember_contact_ok(request, other_id):
    """把某人记进「这次登录我能看联系方式」的名单。

    **必须重新赋值整个列表。** session 只比较序列化后的结果，
    `ids.append(x)` 这样的原地修改不会被标成「已修改」，写不回 cookie 去，
    表现就是「点了同意，刷新一下又看不见了」。
    """
    ids = _contact_ok_ids(request)
    if other_id not in ids:
        ids.append(other_id)
        request.session[services.CONTACT_SESSION_KEY] = ids


@require_POST
@login_required
def contact_request(request, user_id):
    """请求交换联系方式。请求方点这一下 = 自己这边先同意。"""
    me = auth.current(request)
    if services.contact_request(me["id"], user_id):
        # **只有 service 说成功了才把自己这边记上。** 两个人没聊够的时候
        # service 返回 False，这时候如果照样记进 session，就把
        # 「必须先互相聊过」这条规则绕过去了。
        _remember_contact_ok(request, user_id)
    return back(request, "/user/chat/%d" % user_id)


@require_POST
@login_required
def contact_agree(request, user_id):
    """同意对方的交换请求。同意之后**双方当前登录态**互相看得见。"""
    me = auth.current(request)
    if services.contact_agree(me["id"], user_id):
        _remember_contact_ok(request, user_id)
    return back(request, "/user/chat/%d" % user_id)


@require_POST
@login_required
def contact_refuse(request, user_id):
    """拒绝。拒绝方本来也看不见，所以不用动自己这边的名单。"""
    services.contact_refuse(auth.current(request)["id"], user_id)
    return back(request, "/user/chat/%d" % user_id)


@require_POST
@login_required
def contact_revoke(request, user_id):
    """撤销已经达成的交换。

    撤完**两边同时失效**：库里的 status 一旦不是 1，双方 `contact_state`
    的第二个条件就都不成立了。不用去动对方的 session —— 也动不到，
    session 是各自浏览器上的 cookie。
    """
    services.contact_revoke(auth.current(request)["id"], user_id)
    return back(request, "/user/chat/%d" % user_id)


# ================================================================ 他人资料页

def profile(request, id):
    """看某个人的资料页。

    **允许未登录访问** —— 商品详情页点头像进来的人可能还没登录。
    未登录时只是不渲染「关注」「联系 TA」这两个需要身份才能做的按钮
    （在模板里判断），页面本身照常出来。原版这一页就是这样，
    所以这里**不能**挂 @login_required。
    """
    me = auth.current(request)
    profile_user = User.objects.filter(id=id).first()
    if profile_user is None:
        return redirect("goods_home")

    is_self = bool(me and me["id"] == id)

    query = Goods.objects.filter(user_id=id)
    # 已下架的商品不给别人看（重写时实装的 state 过滤，见 README「行为变更」），
    # 但**自己看自己**要看得见 —— 「我的闲置」里还列着它们，
    # 点进资料页却少几件会很莫名其妙。和 goods.views.detail 一个口径。
    if not is_self:
        query = query.filter(FRONT_VISIBLE)

    return render(
        request,
        "user/profile.html",
        {
            "profile": user_card(profile_user),
            "goodsAndImage": cards(query.order_by("id")),
            "isSelf": is_self,
            "followed": bool(
                me and not is_self
                and Follow.objects.filter(user_id=me["id"], follow_user_id=id).exists()
            ),
            # 原版 FollowService.countFollowing / countFans
            "followingCount": Follow.objects.filter(user_id=id).count(),
            "fansCount": Follow.objects.filter(follow_user_id=id).count(),
        },
    )
