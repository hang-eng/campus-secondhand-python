"""
私信与站内通知的操作逻辑。

对应原版 Java 的 `service/impl/MessageServiceImpl.java`（218 行）和
`service/impl/NoticeServiceImpl.java`（65 行）。

原版这两块分在两个 Service 里，但彼此咬得很紧 —— 每发一条私信都会顺手往
系统通知里塞一条（"XX 给你发了一条私信：…"），所以合成一个模块。
app 之间没有别的交叉依赖，合起来不会有循环导入。
"""

import logging

from django.db.models import Q

from accounts.models import User
from accounts.services import user_brief
from core.constants import MESSAGE_MAX_LENGTH
from core.utils import now_time

from .models import ContactRequest, Message, Notice

LOG = logging.getLogger(__name__)

# 通知正文里引用的私信摘要，超过这个长度就截断加省略号
SUMMARY_LIMIT = 40


# ================================================================ 私信

def send(from_user_id, to_user_id, goods_id, context):
    """发一条私信。返回 True / False（有没有发出去）。

    照抄原版 MessageServiceImpl.send 的五道关，每一道都有理由：

      1. from / to 都不能为空
      2. **不能发给自己** —— 自己跟自己聊没有意义，列表里还会多一行自己
      3. 正文 trim 后不能是空的。一个字的「在」算有效，但不能全是空白
      4. **太长就截断，不报错** —— 用户敲了一大段结果发不出去，比发出去
         少后半截更糟。数据库那边 context 是 text 装得下，500 字这个限
         主要是防止页面被撑爆（前端 textarea 上也写着 maxlength=500）
      5. **收件人必须存在且没被冻结** —— `t_shop_message` 没有外键约束，
         不挡的话会给一个不存在的 user_id 插数据，那条消息永远没人看得到

    最后补一条系统通知（失败不影响私信本身，见下面的 try/except）。
    """
    if from_user_id is None or to_user_id is None:
        return False
    if from_user_id == to_user_id:
        return False

    text = (context or "").strip()
    if not text:
        return False
    if len(text) > MESSAGE_MAX_LENGTH:
        text = text[:MESSAGE_MAX_LENGTH]

    recipient = User.objects.filter(id=to_user_id).first()
    if recipient is None or (recipient.status or 0) != 0:
        return False

    Message.objects.create(
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        goods_id=goods_id,
        context=text,
        create_at=now_time(),
        status=0,
    )

    # 顺带往系统通知里塞一条，"系统通知"那个标签页也能看到有人找过自己，
    # 不用把两种消息都翻一遍。
    #
    # try/except 是必要的：通知只是附带的，它失败了不能让用户以为私信没发出去。
    # 原版这里也是 catch 住记日志。
    try:
        add_notice(
            to_user_id, f"{_name_of(from_user_id)} 给你发了一条私信：{summarize(text)}"
        )
    except Exception:
        LOG.exception(
            "发送私信后补系统通知失败, from=%s, to=%s", from_user_id, to_user_id
        )

    return True


def list_conversation(me_id, other_id):
    """我和某人的全部私信，按时间从早到晚。

    **有副作用**：进来就把对方发给我的未读清掉 —— 打开对话就算读过了。
    能调这个函数的地方只有对话页那一个入口。

    标已读的 UPDATE 里 from 和 to **两列都要带上**。只按 `to_user_id=me`
    更新的话会把「我发给别人的消息」也标成已读（`status` 是**收件人视角**的
    未读标记）。原版 `MessageMapper.updateReadByFromAndTo` 特意写了两列，照抄。
    """
    if me_id is None or other_id is None or me_id == other_id:
        return []

    rows = list(Message.objects.filter(_between(me_id, other_id)).order_by("id"))
    if not rows:
        # 一条都没有就不用发那条 UPDATE 了（原版也只在非空时标已读）
        return []

    Message.objects.filter(
        from_user_id=other_id, to_user_id=me_id, status=0
    ).update(status=1)

    # 收发双方都挂上，模板里直接 m.fromUser.avatarUrl 就行。
    by_id = _users_by_id({me_id, other_id})
    return [_message_card(m, by_id) for m in rows]


def list_sessions(me_id):
    """消息中心「私信」标签里的一行行会话。

    把「我参与过的所有消息」按**对方**分组，每组留最新一条 + 未读条数。

    SQL 已经是 id 倒序，所以每个对话第一次出现的那条就是最新一条，
    不用再比时间。dict 在 Python 3.7+ 保证插入顺序，正好等于
    「最近聊的排在最前面」—— 原版用 LinkedHashMap 就是图这个。

    未读**只算对方发给我的**（`to_user_id == me`）且 `status == 0` 的。
    """
    result = []
    if me_id is None:
        return result

    all_rows = Message.objects.filter(_between(me_id)).order_by("-id")
    by_other = {}  # other_id -> {"last": Message, "unread": int}
    for m in all_rows:
        other_id = m.to_user_id if m.from_user_id == me_id else m.from_user_id
        if other_id is None:
            continue
        session = by_other.get(other_id)
        if session is None:
            session = {"last": m, "unread": 0}
            by_other[other_id] = session
        if m.to_user_id == me_id and (m.status or 0) == 0:
            session["unread"] += 1

    by_id = _users_by_id(by_other.keys())
    for other_id, session in by_other.items():
        # 用户被删了（表间没有外键）就跳过，别在列表里留一行空白
        user = by_id.get(other_id)
        if user is None:
            continue
        result.append(
            {
                "user": user_brief(user),
                "last": _message_card(session["last"], by_id),
                "unread": session["unread"],
            }
        )
    return result


def count_unread(me_id):
    """我有多少条没读的私信。侧栏和右上角的红点用（原版 countUnread）。"""
    if me_id is None:
        return 0
    return Message.objects.filter(to_user_id=me_id, status=0).count()


def has_contacted(from_user_id, to_user_id):
    """我给某人发过私信没有。

    商品详情页的「联系卖家」按钮靠它决定显示「联系卖家」还是「继续沟通」——
    点过之后还写着「联系卖家」，用户分不清自己是没联系过还是早聊过了。
    """
    if from_user_id is None or to_user_id is None:
        return False
    return Message.objects.filter(
        from_user_id=from_user_id, to_user_id=to_user_id
    ).exists()


def summarize(text):
    """通知里显示的私信摘要，太长就截断加省略号。原版 summarize()。

    `……` 是**两个全角省略号**（原版 Java 里就是这么写的），照抄。
    """
    if len(text) <= SUMMARY_LIMIT:
        return text
    return text[:SUMMARY_LIMIT] + "……"


# ================================================================ 系统通知

def add_notice(user_id, context):
    """插一条系统通知。用户不存在、正文为空都直接忽略（原版行为）。

    `status` 这一列**没有数据库默认值**，必须显式给 0，否则在 STRICT 模式下
    INSERT 会直接报错。`create_at` 同理。
    """
    if user_id is None or not (context or "").strip():
        return None
    return Notice.objects.create(
        user_id=user_id, context=context, create_at=now_time(), status=0
    )


def list_notices(user_id):
    """某个人的全部通知，最新的在最前面（原版 selectByUserId 的 order by id desc）。"""
    if user_id is None:
        return []
    return list(Notice.objects.filter(user_id=user_id).order_by("-id"))


def count_notice_unread(user_id):
    """未读通知数。"""
    if user_id is None:
        return 0
    return Notice.objects.filter(user_id=user_id, status=0).count()


def mark_notice_read(notice_id, user_id):
    """把单条通知标为已读。

    `user_id` 一起放进 WHERE：**不这样的话改一下 URL 里的 id 就能标掉别人的通知**
    （改的还是「已读」状态，别人会莫名其妙少一条未读）。原版
    `updateStatusReadByIdAndUserId` 带了这个条件，照抄。
    """
    if notice_id is None or user_id is None:
        return 0
    return Notice.objects.filter(id=notice_id, user_id=user_id).update(status=1)


def mark_notices_read_all(user_id):
    """把我所有未读通知一次标掉。"""
    if user_id is None:
        return 0
    return Notice.objects.filter(user_id=user_id, status=0).update(status=1)


# ================================================================ 联系方式交换
#
# 这是重写时新增的功能（原版没有），也是这一版**唯一**会把手机号 / QQ / 微信
# 露给别人的地方。需求是「聊得来才交换」，所以规则卡得比较死：
#
#   1. 双方都在这条会话里发过言，才给「请求交换信息」这个入口
#   2. 请求方点「请求」= 自己这边先同意
#   3. 对方点「同意」之后，**双方当前登录态**互相看得见
#   4. 只在对话页显示。商品详情页、他人资料页、后台，一律不露
#   5. 关掉浏览器重新登录 → session 是新的 → **必须重新请求**
#   6. 同意之后任一方可以撤销，撤销的那一刻两边同时失效
#
# 第 5 条和第 6 条是怎么做到的，就看下面这两个条件 —— 能不能看见，
# 取决于 **session 里点过没** 与 **库里当前是不是已同意**，两个都得成立：
#
#     visible = (对方的 id 在我这次登录的名单里) and (库里有一条 status=1)
#
# 为什么这么拆：
#   · 只存库里不行 —— 那样「交换成功」就永久生效了，跟需求第 5 条冲突
#   · 只存 session 不行 —— 撤销时改不到别人的 session，对方会一直看得见
#   · 两个都要求，重新登录会失败在①、撤销会失败在②，两条需求各自落在
#     不同的条件上，彼此不打架
#
# `t_shop_contact_request` 这张表存的是**请求的状态**（用来决定按钮文案、
# 决定要不要发通知），它本身不决定能不能看见。

CONTACT_SESSION_KEY = "contact_ok"

# contact_state() 返回的六种情况，模板按它选文案和按钮
CONTACT_NONE = "none"        # 还没聊够，这一块整个不显示
CONTACT_ASK = "ask"          # 可以请求
CONTACT_WAITING = "waiting"  # 我请求了，等对方
CONTACT_REPLY = "reply"      # 对方请求了，等我同意 / 拒绝
CONTACT_VISIBLE = "visible"  # 已交换，看得见
CONTACT_REFUSED = "refused"  # 我请求过，被拒了（还能再试一次）
# 之前交换成功过，但这次登录还没点过（关掉浏览器重开就是这样）。
# 和 ASK 分开是因为文案不一样：这一支点下去是**立刻**又能看见，
# 不需要等对方；写成「请求交换信息」会让用户以为还要等对方同意。
CONTACT_REGAIN = "regain"


def contact_state(me_id, other_id, ok_ids):
    """算对话页「联系方式」那一块该显示成什么样。

    返回一个 dict，模板只读它：

        {"state": "visible", "visible": True,
         "phone": "138...", "qq": "...", "wechat": "..."}

    没到 `visible` 的时候，phone / qq / wechat 三个键是**空字符串**，
    不是 None —— 模板里 `{% if contact.visible %}` 之外都不用再判空。

    手机号 / QQ / 微信**是在这里才从库里取出来的**，取值和「能不能看」
    写在同一个函数里。别的地方（商品详情、他人资料页）拿到的用户 dict
    里根本没有这三个键，从源头上就没有「模板少写一个 if 就漏出去」的机会。
    """
    result = {
        "state": CONTACT_NONE,
        "visible": False,
        "phone": "",
        "qq": "",
        "wechat": "",
    }
    if not me_id or not other_id or me_id == other_id:
        return result

    rows = list(ContactRequest.objects.filter(_between(me_id, other_id)))
    mine = next((r for r in rows if r.from_user_id == me_id), None)
    theirs = next((r for r in rows if r.from_user_id == other_id), None)
    # 「已同意」看**任一方向**：A 请求、B 同意之后，两个人的库里都只有 (A,B,1)。
    agreed = any((r.status or 0) == ContactRequest.AGREED for r in rows)

    if agreed:
        # 条件①不成立就还没到「交换成功」这一步 —— 关掉浏览器重登就是这样。
        # 点一下「重新查看」立刻又能看见，不用再等对方（库里那条 status=1
        # 一直都在，contact_request 也不会把它打回 0）。
        if other_id not in ok_ids:
            result["state"] = CONTACT_REGAIN
            return result
        other = User.objects.filter(id=other_id).first()
        if other is None:
            # 对方账号被删了（表间没有外键）。什么都不显示，别去取 None 的属性
            return result
        result.update(
            {
                "state": CONTACT_VISIBLE,
                "visible": True,
                "phone": other.phone or "",
                "qq": other.qq or "",
                "wechat": other.wechat or "",
            }
        )
        return result

    # 我发起的还在等对方
    if mine is not None and (mine.status or 0) == ContactRequest.PENDING:
        result["state"] = CONTACT_WAITING
        return result

    # 对方发起的，等我处理
    if theirs is not None and (theirs.status or 0) == ContactRequest.PENDING:
        result["state"] = CONTACT_REPLY
        return result

    # 我发起过、被拒了。允许再试 —— 一次点错就永久拉黑没有道理
    if mine is not None and (mine.status or 0) == ContactRequest.REFUSED:
        result["state"] = CONTACT_REFUSED
        return result

    # 到这儿说明没有有效记录。没聊够的话这一块整个不显示
    if not both_talked(me_id, other_id):
        return result

    result["state"] = CONTACT_ASK
    return result


def both_talked(a_id, b_id):
    """两个人**互相**都发过言没有。

    只要求各发过至少一条，不要求数量 —— 门槛再往上加就得引入计时或者
    关键词识别，规则会变得没法在答辩时讲明白。两个人一人一句就算聊过了。

    注意原版的「联系卖家」按钮只看**我有没有发过**（见上面 has_contacted），
    这里是另一个更严的口径：两边都得开过口。
    """
    if not a_id or not b_id or a_id == b_id:
        return False
    return (
        Message.objects.filter(from_user_id=a_id, to_user_id=b_id).exists()
        and Message.objects.filter(from_user_id=b_id, to_user_id=a_id).exists()
    )


def contact_request(me_id, other_id):
    """我点「请求交换信息」。返回 True / False（有没有真的请求出去）。

    调用方拿到 True 之后还要把对方记进 session 的名单 —— 那一步在视图里，
    service 这一层不碰 request。

    这里**同时**处理两种情况，故意的：
      · 正常地发起一条新请求（库里没有记录）
      · 已经同意过、但这次登录还没点过（重新登录回来了）—— 这时候
        库里那条 status=1 保持不动，只是让对方重新点一下，
        免得顺手把它打回 0、把对方那边也一起弄看不见
    """
    if not both_talked(me_id, other_id):
        return False

    now = now_time()
    row = ContactRequest.objects.filter(
        from_user_id=me_id, to_user_id=other_id
    ).first()

    if row is None:
        ContactRequest.objects.create(
            from_user_id=me_id,
            to_user_id=other_id,
            status=ContactRequest.PENDING,
            create_at=now,
            update_at=now,
        )
    elif (row.status or 0) == ContactRequest.REFUSED:
        # 被拒过还能再试：状态退回「待处理」，让对方再看到一次
        ContactRequest.objects.filter(id=row.id).update(
            status=ContactRequest.PENDING, update_at=now
        )
    else:
        # 已经有一条待处理 / 已同意的记录。状态不动，也不重复发通知 ——
        # 重新登录之后点一下就走这条路，不该把对方的通知栏刷一遍。
        return True

    add_notice(
        other_id, f"{_name_of(me_id)} 想和你交换联系方式，去对话页看看。"
    )
    return True


def contact_agree(me_id, other_id):
    """我点「同意」。把对方发来的那条请求置为已同意。

    WHERE 里带上 `to_user_id=me_id` 就是属主校验：同意**别人发给我的**
    请求才有效，改 URL 里的 id 同意不了不相干的记录。
    """
    now = now_time()
    changed = ContactRequest.objects.filter(
        from_user_id=other_id,
        to_user_id=me_id,
        status=ContactRequest.PENDING,
    ).update(status=ContactRequest.AGREED, update_at=now)

    if changed:
        add_notice(
            other_id, f"{_name_of(me_id)} 同意了交换联系方式，去对话页看看吧。"
        )
    return bool(changed)


def contact_refuse(me_id, other_id):
    """我点「拒绝」。同样只能拒别人发给我的那条。"""
    now = now_time()
    changed = ContactRequest.objects.filter(
        from_user_id=other_id,
        to_user_id=me_id,
        status=ContactRequest.PENDING,
    ).update(status=ContactRequest.REFUSED, update_at=now)

    if changed:
        add_notice(other_id, f"{_name_of(me_id)} 拒绝了交换联系方式。")
    return bool(changed)


def contact_revoke(me_id, other_id):
    """撤销已经达成的交换。**任一方都能撤**，撤完两边同时失效。

    只改库里那一条 status=1 的记录，**不去动任何人的 session** ——
    `contact_state` 的第二个条件当场就失败了，对方刷新一下页面就看不见了。
    这是把「能不能看见」拆成两个条件的好处：撤销只要动一个。

    撤销之后用的是 REFUSED 而不是 PENDING：对方那边会看到「对方拒绝了」
    那一支，比显示成「等待对方同意」诚实。
    """
    now = now_time()
    changed = ContactRequest.objects.filter(
        _between(me_id, other_id), status=ContactRequest.AGREED
    ).update(status=ContactRequest.REFUSED, update_at=now)

    if changed:
        add_notice(other_id, f"{_name_of(me_id)} 撤销了联系方式交换。")
    return bool(changed)


# ================================================================ 内部工具

def _between(a_id, b_id=None):
    """两个人之间所有的消息 / 请求。

    `b_id` 传 None 表示「我和所有人之间的」（会话列表用）。

    用 Q() 组合而不是拼 SQL 字符串：`(from=a AND to=b) OR (from=b AND to=a)`
    这种括号在原版 `selectByCatelog` 那里出过事（跨 `<if>` 括号不配对，
    只填关键词就 500），Q 组合天然不会括号错位。
    """
    if b_id is None:
        return Q(from_user_id=a_id) | Q(to_user_id=a_id)
    return Q(from_user_id=a_id, to_user_id=b_id) | Q(
        from_user_id=b_id, to_user_id=a_id
    )


def _name_of(user_id):
    """通知正文里怎么称呼某个人。

    查不到、或者昵称是空的，一律叫「有人」—— 通知只是动作的附带产物，
    不能因为一次查不到就把整个动作带崩（用户被删了是常态，表间没有外键）。
    """
    user = User.objects.filter(id=user_id).first()
    if user is None:
        return "有人"
    return user.username or "有人"


def _users_by_id(ids):
    """按 id 批量取用户，返回 {id: User}。

    原版 `getUsersByIds` 有个坑：空集合时 SQL 会退化成「查全部用户」。
    Django 的 `id__in=set()` 天然返回空集，不会踩这个坑；这里先判一下
    只是为了省掉一次没意义的查询。
    """
    ids = {i for i in ids if i is not None}
    if not ids:
        return {}
    return {u.id: u for u in User.objects.filter(id__in=ids)}


def _message_card(message, by_id):
    """Message → 模板 / JSON 用的 camelCase dict。

    键名照抄 Java `Message` 的属性名：前端脚本和 session 里那份 cur_user
    都是这套命名，模板里 `m.fromUserId == cur_user.id` 才读得通。
    """
    return {
        "id": message.id,
        "fromUserId": message.from_user_id,
        "toUserId": message.to_user_id,
        "goodsId": message.goods_id,
        "context": message.context or "",
        "createAt": message.create_at or "",
        "status": message.status or 0,
        "fromUser": user_brief(by_id.get(message.from_user_id)),
        "toUser": user_brief(by_id.get(message.to_user_id)),
    }
