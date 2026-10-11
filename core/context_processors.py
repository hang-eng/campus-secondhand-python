"""
全局模板变量。

原版靠两个 `@ControllerAdvice` 往每个 Model 里塞数据：
  UnreadNoticeAdvice → unreadCount / unreadMsgCount / loginError / loginPhone
  RobotAdvice        → robotEnabled
Django 里对应的机制就是 context processor。

**注意执行顺序**：Django 的 Jinja2 后端是在渲染前把 processor 的结果
`update` 进 context 的，也就是会**覆盖** view 传进来的同名变量。
所以 `cur_user` 一律以 session 为准，view 里不要再自己传一份。
"""

from .constants import CUR_USER, FONT_SIZE_CODES, FONT_SIZE_DEFAULT, LOGIN_ERROR, LOGIN_PHONE


def robot_enabled():
    """机器人可不可用。对应原版 RobotAdvice.robotEnabled()。

    判断条件收在 robot/services.available() 一处 —— 视图里的入口判断用的
    也是那一个函数，免得两处各写一遍判断条件、改了一处忘另一处。

    出任何意外都返回 False：机器人是个锦上添花的功能，
    绝不能因为读配置出错就让全站页面挂掉。
    """
    try:
        from robot.services import available

        return available()
    except Exception:
        return False


def globals(request):  # noqa: A001 —— 名字是给 settings 里那行字符串用的
    context = {
        "cur_user": request.session.get(CUR_USER),
        # 读一次即删。原版 UnreadNoticeAdvice.consume() 就是这个语义：
        # 登录失败的提示只显示一次，刷新页面就没了。
        "loginError": request.session.pop(LOGIN_ERROR, None),
        "loginPhone": request.session.pop(LOGIN_PHONE, None),
        # 原版 RobotProperties.isUsable()：开关打开 + key 非空 + url 非空
        "robotEnabled": robot_enabled(),
        "unreadCount": None,
        "unreadMsgCount": None,
        # 界面字体大小（s/m/l/xl），base.html 把它写到 <html data-fs="..."> 上，
        # campus.css 最后一节按这个属性做整体缩放。
        # 未登录、或库里那一列是空/坏值时回落到标准档 —— 这里**必须**给出
        # 四个白名单短码之一，属性值写错的话 CSS 匹配不上，页面就是没缩放
        # （宁可回落到标准，也不要给一个匹配不上的值）。
        "fontSize": FONT_SIZE_DEFAULT,
    }

    user = context["cur_user"]
    if user:
        stored = user.get("fontSize")
        context["fontSize"] = stored if stored in FONT_SIZE_CODES else FONT_SIZE_DEFAULT
    if user:
        try:
            from chat.models import Message, Notice

            context["unreadCount"] = Notice.objects.filter(
                user_id=user["id"], status=0
            ).count()
            context["unreadMsgCount"] = Message.objects.filter(
                to_user_id=user["id"], status=0
            ).count()
        except Exception:
            # 原版这里就是 try/catch 后返回 null。
            # 红点数查不出来，不该让整页 500。
            context["unreadCount"] = None
            context["unreadMsgCount"] = None

    return context
