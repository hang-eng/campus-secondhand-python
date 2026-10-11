"""
用户域：注册 / 登录 / 登出 / 个人中心 / 个人设置 / 头像 / 关注。

对应原版 Java 的 `controller/UserController.java`（634 行）。
"""

from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core import auth
from core.ajax import fail, json_body, ok
from core.constants import (
    ADMIN_POWER, FONT_SIZE_CODES, FONT_SIZES, MAX_UPLOAD_IMAGE_SIZE,
    PRESET_AVATARS, USER_POWER,
)
from core.decorators import admin_api, login_required
from core.http import back, safe_referer
from core.uploads import store_image
from core.utils import check_password, md5_hex, now_time
from chat.models import Notice
from goods.models import Comments, Goods
from goods.services import cards

from .models import Follow, User


# ================================================================ 小工具

def _get_user_by_phone(phone):
    """按手机号取用户。手机号是唯一登录凭据（没有用户名登录）。"""
    if not phone:
        return None
    return User.objects.filter(phone=phone).first()


def _register(phone, username, password, power=USER_POWER):
    """建号。返回新用户，号码已注册则返回 None。

    字段默认值照抄原版 UserController.addUser：
    status=0（正常）、power=10（普通用户）、goods_num=0。

    `power` 只有后台那个「添加用户」弹层会传别的值（可以选管理员），
    前台注册表单走的是 `/user/addUser`，走不到这个参数。
    """
    # 空手机号 / 空用户名 / 空密码一律不建号：手机号是唯一登录凭据，
    # 放空进去等于造出一个没法登录的账号，还会把后续的空号注册静默吞掉。
    if not phone or not username or not password:
        return None
    if _get_user_by_phone(phone):
        return None

    user = User.objects.create(
        phone=phone,
        username=username,
        # 大写 MD5，和库里已有的两个账号同格式
        password=md5_hex(password),
        qq=None,
        avatar=None,  # 留空 -> User.avatar_url 回落到默认头像
        create_at=now_time(),
        goods_num=0,
        power=power,
        status=0,
    )
    # 注册成功送一条欢迎通知，让「我的消息」一进来不是空的。
    # 原版这里有个坑：UserMapper 的 insert 没配 useGeneratedKeys，
    # 插完拿不到 id，得按手机号再查一次。Django 的 create() 直接返回带
    # 主键的实例，不用再查。
    Notice.objects.create(
        user_id=user.id,
        context=(
            "欢迎来到武汉理工大学二手交易平台！"
            "在这里可以发布自己的闲置物品，也可以淘到同学的好东西。"
        ),
        create_at=now_time(),
        # 这一列**没有默认值**，必须显式给 0
        status=0,
    )
    return user


# ================================================================ 登录 / 注册 / 登出

@require_POST
def login_view(request):
    """登录。表单字段 phone / password。

    三种失败都回来源页并带上提示（原版是静默 redirect，用户点了没反应，
    分不清是没注册还是密码打错）。
    """
    phone = (request.POST.get("phone") or "").strip()
    password = request.POST.get("password") or ""
    target = safe_referer(request) or "goods_home"

    user = _get_user_by_phone(phone)
    if user is None:
        return _login_fail(request, "该手机号还没有注册", phone)
    if user.status:
        return _login_fail(request, "该账号已被冻结，无法登录", phone)
    # 密码框是 required 的，正常走不到空；挡一下是因为 md5_hex(None) 会炸
    if not password or not check_password(password, user.password):
        return _login_fail(request, "密码不正确", phone)

    auth.login(request, user)
    return redirect(target)


def _login_fail(request, message, phone):
    """登录失败的统一出口：写 session 后跳回来源页。

    提示由 core.context_processors 在下一个请求里读出来塞进上下文，
    登录弹层显示成红字，并且自动展开。**读一次即删**，免得刷新还在。
    """
    auth.set_login_error(request, message, phone)
    return back(request, "goods_home")


@require_POST
def add_user(request):
    """注册。表单字段 username / phone / password。

    注意：号码已存在时原版也是静默跳回，什么都不提示。
    这里保持原行为（前端注册弹层本来就没有错误提示位）。
    """
    _register(
        phone=(request.POST.get("phone") or "").strip(),
        username=(request.POST.get("username") or "").strip(),
        password=request.POST.get("password") or "",
    )
    return back(request, "goods_home")


def logout_view(request):
    """登出。

    原版只把 session 里的 cur_user 置 null，**没有 invalidate 整个 session**
    （也就是登录失败提示之类的其他 key 会留着）。core.auth.logout 用 pop，
    行为对齐。跳回首页。
    """
    auth.logout(request)
    return redirect("goods_home")


@require_POST
def change_name(request):
    """改用户名。来源是顶栏下拉里的那个小弹层。"""
    username = (request.POST.get("username") or "").strip()
    user = auth.current(request)
    if user and username:
        User.objects.filter(id=user["id"]).update(username=username)
        # session 里那份是登录时查出来的**副本**，不刷新的话本次会话里
        # 所有页面读到的还是旧名字，得等重新登录才变。
        auth.refresh(request, username=username)
    return back(request, "user_home")


# ================================================================ 个人中心 / 个人设置

@login_required
def home(request):
    """个人中心。

    页面右侧那块是原版遗留的空壳（一个发不出东西的发布框 + 「没有任何内容」），
    照搬，不做二次加工。
    """
    return render(request, "user/home.html")


@login_required
def basic(request):
    """个人设置：改昵称 / QQ，换头像（预设 + 上传两套表单），调界面字体大小。"""
    return render(
        request,
        "user/basic.html",
        {
            # 预设头像列表给页面渲染单选框用，和提交时的白名单是**同一份数据**，
            # 避免两边各抄一份写岔（用户选了却存不进去）
            "presets": PRESET_AVATARS,
            # 字体大小的四个档位 (短码, 名字, 百分比)。同样是**一份数据两处用**：
            # 页面按它渲染四个选项、提交时按它做白名单校验。
            # 当前选中哪个不看这里，看上下文处理器给的 fontSize（它读的是 session）。
            "fontSizes": FONT_SIZES,
        },
    )


@require_POST
@login_required
def set_font_size(request):
    """保存界面字体大小。

    表单字段 fontSize，取值是 s / m / l / xl 四个短码之一，
    写进 `t_shop_user.font_size`。`base.html` 把它写到
    `<html data-fs="...">`，缩放规则在 campus.css 第 30 节。

    **存进库而不是 cookie**：这是用户明确选的 —— 换浏览器、换台电脑、
    重新登录都要记得，只有跟着账号走才做得到。

    校验是白名单，不是「非空就行」：参数来自表单，不校验的话别人能塞
    任意字符串进库。更关键的是这个值**最终会变成 HTML 属性**，
    虽然 Jinja2 会自动转义（引号进不了属性），但从源头堵住更干净 ——
    而且库里存了脏值之后，页面表现为「设置没生效」，很难查。
    """
    me = auth.current(request)
    code = (request.POST.get("fontSize") or "").strip()
    if code not in FONT_SIZE_CODES:
        return redirect("user_basic")

    User.objects.filter(id=me["id"]).update(font_size=code)
    # session 里那份是登录时查出来的**副本**，不刷新的话本次会话里
    # 所有页面读到的还是旧档位，要重新登录才变 —— 和改昵称、换头像一个道理。
    auth.refresh(request, fontSize=code)
    return redirect("user_basic")


@require_POST
def update_info(request):
    """保存昵称和 QQ。

    原版会把表单参数拼成一个 User 再整条 selective 更新，这里只动
    明确传上来的两列 —— 少一个「表单漏传就把别的列刷成空」的机会。
    """
    user = auth.current(request)
    if not user:
        return redirect("goods_home")

    changes = {}
    username = (request.POST.get("username") or "").strip()
    qq = (request.POST.get("qq") or "").strip()
    if username:
        changes["username"] = username
    # QQ 允许被清空，所以这里不能判 `if qq:`，要看表单有没有这一项
    if "qq" in request.POST:
        changes["qq"] = qq

    if changes:
        User.objects.filter(id=user["id"]).update(**changes)
        auth.refresh(request, **{"qq" if k == "qq" else k: v for k, v in changes.items()})
    return redirect("user_basic")


# ================================================================ 头像

@require_POST
@login_required
def avatar_preset(request):
    """从预设的 6 张里挑一张。

    **必须做白名单校验**：参数来自表单，不校验的话别人可以提交
    `/img/../../application.properties` 这种值存进库，页面上就成了
    一个指向站点任意路径的 <img>。
    """
    avatar = request.POST.get("avatar")
    user = auth.current(request)
    if user and avatar in PRESET_AVATARS:
        User.objects.filter(id=user["id"]).update(avatar=avatar)
        auth.refresh(request, avatar=avatar, avatarUrl=avatar)
    return back(request, "user_basic")


@require_POST
@login_required
def avatar_upload(request):
    """上传自定义头像。

    用最普通的一个 `<input type="file">` 表单，不引 jQuery / 上传插件 ——
    user/ 目录下的页面本来就没有 jQuery 依赖。
    """
    user = auth.current(request)
    saved = _save_avatar(request.FILES.get("file"))
    if user and saved:
        User.objects.filter(id=user["id"]).update(avatar=saved)
        # 存的是**完整 web 路径**（/upload/xxx.jpg），和预设头像一致
        auth.refresh(request, avatar=saved, avatarUrl=saved)
    return back(request, "user_basic")


def _save_avatar(file):
    """把上传的头像落盘，返回可直接访问的 web 路径；不合法返回 None。

    校验和落盘都在 core.uploads.store_image 里（和商品图共用同一套），
    这里只负责把「裸文件名」拼成完整 web 路径 —— 头像这一列存的是
    `/upload/<uuid>.jpg`，商品图那一列存的是裸文件名，原版就不一致，照抄。
    """
    name = store_image(file, max_size=MAX_UPLOAD_IMAGE_SIZE)
    return ("/upload/" + name) if name else None


# ================================================================ 我的闲置

@login_required
def all_goods(request):
    """我的闲置。

    **不过滤 state** —— 已下架的商品在这个页面要看得见（打成灰色角标），
    否则用户下架完就找不回来了。这是和前台其他列表的关键区别。
    """
    user = auth.current(request)
    goods_list = Goods.objects.filter(user_id=user["id"]).order_by("id")
    cards_ = cards(goods_list)
    return render(
        request,
        "user/goods.html",
        {
            "goodsAndImage": cards_,
            # 每件商品的真实评论数。不能取 t_shop_goods.commet_num ——
            # 那一列没有任何地方回写，全库都是 NULL，图标连数字都显示不出来。
            "commentCounts": Comments.count_by_goods_ids(
                [c["goods"].id for c in cards_]
            ),
        },
    )


# ================================================================ 关注

@login_required
def follow_list(request):
    """关注列表。两个标签：tab=following（我关注的，默认）/ tab=fans（关注我的）。"""
    me = auth.current(request)["id"]

    following_ids = list(
        Follow.objects.filter(user_id=me).order_by("-id").values_list("follow_user_id", flat=True)
    )
    fans_ids = list(
        Follow.objects.filter(follow_user_id=me).order_by("-id").values_list("user_id", flat=True)
    )

    following = _users_in_order(following_ids)
    fans = _users_in_order(fans_ids)
    followed = {u.id for u in following}

    return render(
        request,
        "user/follow.html",
        {
            "following": following,
            "fans": fans,
            # 粉丝那一栏里有的人我已经回关了、有的没有，按钮要显示成
            # 「已关注」还是「关注」，所以把「我关注了谁」的集合一起给页面
            "followingIds": followed,
            "followingCount": len(following),
            "fansCount": len(fans),
            "tab": "fans" if request.GET.get("tab") == "fans" else "following",
        },
    )


def _users_in_order(ids):
    """按 id 批量取用户，并**保持传入顺序**（列表里最新的关注在前）。

    原版 FollowServiceImpl.loadUsers 的两个坑，这里都不会踩：
      1. `getUsersByIds` 空集合时会退化成「查全部用户」——
         Django 的 `id__in=[]` 天然返回空集，不用自己挡。
      2. 那条 SQL 不带 order by，返回顺序由数据库决定，不能指望和 ids 一致，
         所以要在 Python 里按 id 重排。这里也是。
    """
    if not ids:
        return []
    by_id = {u.id: u for u in User.objects.filter(id__in=set(ids))}
    # 顺带去重：同一个人不可能被关注两次，但 t_shop_follow 没有外键约束，
    # 手工改过库的话可能出现重复行
    seen, result = set(), []
    for uid in ids:
        if uid in seen:
            continue
        seen.add(uid)
        user = by_id.get(uid)
        # 跳过已被删除的用户：删用户不会连带删关注关系
        if user is not None:
            result.append(user)
    return result


@require_POST
@login_required
def follow_add(request, user_id):
    """关注某人。不能关注自己。"""
    me = auth.current(request)
    # 目标用户必须真实存在：不然能对一个不存在的 id 建关注、发通知，
    # 留下永远清不掉的孤儿数据
    if user_id != me["id"] and User.objects.filter(id=user_id).exists():
        # get_or_create 代替原版的「先 count 再 insert」——
        # 表上有 uk_user_follow 唯一键，并发插入时 count 那套会撞唯一键报错
        follow, created = Follow.objects.get_or_create(
            user_id=me["id"],
            follow_user_id=user_id,
            defaults={"create_at": now_time()},
        )
        # 只有确实新增了才发通知，重复点不会反复打扰对方
        if created:
            Notice.objects.create(
                user_id=user_id,
                context=f"{me['username']} 关注了你，去关注列表看看吧。",
                create_at=now_time(),
                status=0,
            )
    return back(request, "user_follow")


@require_POST
@login_required
def follow_remove(request, user_id):
    """取消关注。"""
    Follow.objects.filter(user_id=auth.current(request)["id"], follow_user_id=user_id).delete()
    return back(request, "user_follow")


# ================================================================ 通知入口

def notice_redirect(request):
    """`/user/notice` 转发到消息中心的「系统通知」标签。

    这一页原来独立存在，加了私信之后并进了 /user/message。
    路由留着是因为用户中心的侧栏、注册后的欢迎提示、以及浏览器里
    存着的历史链接都指向它，删掉就是 404。用 302 不用 301：
    万一以后又要拆开，301 会被浏览器缓存住改不回来。
    """
    return redirect("/user/message?tab=notice")


# ================================================================ JSON 接口
#
# 这一组（/user/api/*）**只有一个调用方**：后台管理页
# （`templates/manage/manage-userList.html` + `static/js/manage/manage-userList.js`，
# login 那个是 manage-login.js）。前台注册登录走的是 `/user/addUser` 和
# `/user/login` 两个表单地址，不经过这里。
#
# 返回格式严格照 AjaxResult（见 core/ajax.py），前端脚本才读得懂。
# 除 `api/login` 外（它就是后台的登录接口，未登录时唯一的入口），
# 其余全部要求管理员身份 —— 原版这几个接口**一个都没检查权限**。

@require_POST
def api_login(request):
    """POST /user/api/login，参数 phone / password。"""
    phone = (request.POST.get("phone") or "").strip()
    password = request.POST.get("password") or ""
    user = _get_user_by_phone(phone)
    if user is None:
        return fail(3002)  # WRONG_USERNAME 该账号不存在
    # 和前台 login_view 同一口径：被冻结的账号不能从这里拿登录会话
    if user.status:
        return fail(message="该账号已被冻结，无法登录。")
    if not check_password(password, user.password):
        return fail(3003)  # WRONG_PASSWORD 密码错误

    auth.login(request, user)
    # 原版这里 setData(cur_user) 会把整个 User 序列化出去，**包含密码哈希**。
    # 重写改成返回 session 里那份（不含 password），字段名一致，
    # 前端拿 data.id / data.username 不受影响。
    return ok(auth.current(request))


@admin_api
@require_POST
def api_add_user(request):
    """POST /user/api/addUser，请求体是 JSON（原版用的 @RequestBody）。

    调用方只有后台用户管理页的「添加用户」弹层。

    **权限校验是重写时补的**：原版这个接口没有任何检查，任何登录用户都能
    POST 一个 `{"phone":..., "power":90}` 把自己提成管理员。
    前端表单里那个 `power` 下拉框不是权限控制 —— 手搓一个请求就绕过去了。
    """
    payload = json_body(request)
    if payload is None:
        return fail(3000)

    user = _register(
        phone=(payload.get("phone") or "").strip(),
        username=(payload.get("username") or "").strip(),
        password=payload.get("password") or "",
        power=_power_or_default(payload.get("power")),
    )
    if user is None:
        return fail(3007)  # AREADY_EXIST_PHONE 该电话号码已经注册过了
    # 原版返回的就是字面量 1
    return ok(1)


@admin_api
@require_POST
def api_update_user(request):
    """POST /user/api/updateUser，请求体是 JSON。密码传的是明文，存前 md5。

    同样只给后台用户管理页用，同样补了权限校验（原版没有，
    改一下请求体里的 `id` 和 `power` 就能把任意账号提成管理员）。
    """
    payload = json_body(request)
    if payload is None or not payload.get("id"):
        return fail(3000)

    changes = {}
    if payload.get("phone"):
        # 手机号是唯一登录凭据，和注册同一口径先查重（排除自己），
        # 不然改出重复号码后 _get_user_by_phone 的 .first() 结果不可预期
        existing = _get_user_by_phone((payload["phone"] or "").strip())
        if existing is not None and existing.id != payload["id"]:
            return fail(3007)  # AREADY_EXIST_PHONE 该电话号码已经注册过了
        changes["phone"] = (payload["phone"] or "").strip()
    if payload.get("username"):
        changes["username"] = payload["username"]
    if payload.get("qq") is not None:
        changes["qq"] = payload["qq"]
    # 页面上那个「权限」下拉框只有 10 / 90 两个选项，也只认这两个值
    if payload.get("power") is not None:
        changes["power"] = _power_or_default(payload.get("power"))
    # 原版是无条件 MD5.md5(user.getPassword())，密码为 null 时直接 NPE。
    # 这里只在真传了密码时才改 —— 顺带也拦掉了「密码框空着提交，
    # 把人家密码改成空串的 MD5」这种情况。
    if payload.get("password"):
        changes["password"] = md5_hex(payload["password"])

    updated = User.objects.filter(id=payload["id"]).update(**changes) if changes else 0
    return ok(bool(updated))


def _power_or_default(raw):
    """把表单传来的权限值收成 10 或 90。

    原版是 `byte power` 直接绑上去：请求体里塞一个 999 或者 "abc"
    要么被 Spring 拒掉整条请求，要么往库里写一个别的代码都不认识的值
    （`power == 90` 判管理员、其它一律按普通用户渲染，等于谁也管不了这一行）。
    白名单两个值，别的都当普通用户。
    """
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return USER_POWER
    return ADMIN_POWER if value == ADMIN_POWER else USER_POWER


@admin_api
def api_delete_user(request, user_id):
    """DELETE /user/api/deleteUser/{id}

    原版**没有**做 power 校验 —— 任何登录用户都能删掉任意账号。
    这里补上 admin_api（不是管理员返回 success:false + code 3009）。
    """
    return ok(bool(User.objects.filter(id=user_id).delete()[0]))


@admin_api
@require_POST
def api_freeze_user(request, user_id):
    """POST /user/api/freezeUser/{id} —— status 置 1。同样补了权限校验。"""
    return ok(bool(User.objects.filter(id=user_id).update(status=1)))


@admin_api
@require_POST
def api_unfreeze_user(request, user_id):
    """POST /user/api/unfreezeUser/{id} —— status 置 0。"""
    return ok(bool(User.objects.filter(id=user_id).update(status=0)))
