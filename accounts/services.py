"""
用户对象的展示层转换。

原版模板里写的是 Java 属性名 —— `${cur_user.goodsNum}`、`${other.avatarUrl}`
（`avatarUrl` 还是 `getAvatarUrl()` 这个计算属性）。Python 的 model 上
是 `goods_num` / `avatar_url`，名字对不上。

两种做法：
  1. 给 model 加一堆 camelCase 的 property —— 会把 Python 里很别扭的命名
     塞进 model，而且和 session 里那份 dict 成为两套并行结构；
  2. 需要的时候转成 dict，键名照抄 Java。

选 2。理由是 `core/auth.py` 里 session 存的 `cur_user` **本来就是**这种
camelCase dict，模板里 `cur_user.username` 和 `other.username` 才是同一种东西，
不用去想「这个名字是取属性还是取键」。

key 的集合和 `auth.user_to_session()` 保持一致，差一个 `password`（那个不给模板）。
"""


def user_card(user):
    """User → 模板用的 dict。user 为 None 时返回 None。

    多带一个 `isAdmin`：后台模板判断管理员用的（原版是 directly 比 power == 90）。
    """
    if user is None:
        return None
    return {
        "id": user.id,
        "phone": user.phone or "",
        "username": user.username or "",
        "qq": user.qq or "",
        "avatar": user.avatar or "",
        # 空头像回落到默认图，兜底只在 User.avatar_url 里写一次
        "avatarUrl": user.avatar_url,
        "createAt": user.create_at or "",
        "goodsNum": user.goods_num or 0,
        "power": user.power if user.power is not None else 10,
        "status": user.status or 0,
        "isAdmin": user.is_admin,
    }


def user_brief(user):
    """只要头像和昵称的场合（评论列表、会话列表）。

    比 user_card 少给一堆用不上的字段 —— 这些 dict 会被 `|tojson` 塞进页面，
    字段越少页面越干净。
    """
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username or "",
        "avatarUrl": user.avatar_url,
    }
