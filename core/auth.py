"""
登录态。

原版是往 `session["cur_user"]` 里塞一个 Java `User` 对象，然后到处
`cur_user.setGoodsNum(...)` 再 `setAttribute` 回 session。这里塞 **dict**：

  - session 要序列化，塞 model 实例会连带一堆状态进去；
  - dict 语义更直白，改哪个键一眼看得见；
  - 键名照抄原版 User 的属性名（含 `avatarUrl` 这个计算属性），
    模板里 `${cur_user.xxx}` 能一一对应过去。

**没有用 django.contrib.auth**，也没法用：库里密码是大写 MD5，
django.contrib.auth 认的是 `pbkdf2_sha256$...` 格式，会一个都登不上。
"""

from .constants import CUR_USER, FONT_SIZE_DEFAULT, LOGIN_ERROR, LOGIN_PHONE


def user_to_session(user):
    """把 User 实例转成 session 里存的那个 dict。"""
    return {
        "id": user.id,
        "phone": user.phone or "",
        "username": user.username or "",
        "qq": user.qq or "",
        "avatar": user.avatar or "",
        "avatarUrl": user.avatar_url,
        "createAt": user.create_at or "",
        "goodsNum": user.goods_num or 0,
        "power": user.power if user.power is not None else 10,
        "status": user.status or 0,
        # 界面字体大小（s/m/l/xl）。跟着账号走，换浏览器也记得 ——
        # 所以它从库里取，而不是从 cookie 里取。
        "fontSize": user.font_size or FONT_SIZE_DEFAULT,
    }


def login(request, user):
    """登录成功。有效期由 settings.SESSION_COOKIE_AGE 统一控制（24 小时）。"""
    request.session[CUR_USER] = user_to_session(user)


def logout(request):
    """登出。

    原版只是 `setAttribute("cur_user", null)`，**没有 session.invalidate()**，
    所以这里用 pop 而不是 flush —— 行为对齐，也免得顺手把登录失败提示清掉。
    """
    request.session.pop(CUR_USER, None)


def current(request):
    """取当前登录用户（dict），未登录返回 None。

    顺带做一次**回库核对**（只查 power / status 两列）：
      - 账号被管理员冻结后，已签发的 session 不能再继续用，立即失效；
      - 账号被删除后同样立即失效；
      - power 被管理员改过后，session 里的快照同步更新（降级立即失去
        管理员权限，升级也不用重新登录）。
    不核对的话，冻结/降级要等 session 过期（最长 24 小时）才真正生效。

    惰性导入 User：accounts.models 依赖 core，模块级 import 会成环。
    """
    user = request.session.get(CUR_USER)
    if not user:
        return None

    from accounts.models import User

    fresh = User.objects.filter(id=user.get("id")).values("power", "status").first()
    if fresh is None or fresh["status"]:
        request.session.pop(CUR_USER, None)
        return None
    if fresh["power"] is not None and fresh["power"] != user.get("power"):
        user["power"] = fresh["power"]
        request.session[CUR_USER] = user
    return user


def refresh(request, **changes):
    """就地改 session 里的用户信息：换头像、改昵称、goodsNum 加减。

    必须整个重新赋值，不能只在 dict 上改键 —— Django 不跟踪嵌套修改，
    不重新赋值的话 session 不会标记为脏，改动静默丢失。
    """
    user = request.session.get(CUR_USER)
    if user:
        user.update(changes)
        request.session[CUR_USER] = user
    return user


def is_admin(request):
    """原版判断管理员的唯一口径：power == 90。"""
    user = current(request)
    return bool(user and user.get("power") == 90)


# ---------------------------------------------------------------- 登录失败回显

def set_login_error(request, message, phone=""):
    """原版 UserController.loginFail()。

    不写 flash（本项目没装 messages 框架），直接写 session，
    由 core.context_processors 读出来放进模板上下文，**读一次即删**。
    """
    request.session[LOGIN_ERROR] = message
    request.session[LOGIN_PHONE] = phone or ""
