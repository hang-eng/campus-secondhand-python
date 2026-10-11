"""
右下角那个智能导购机器人的入口与对话页。

**为什么发消息要用 POST-Redirect-GET：** 拿一次模型回答要几秒到几十秒，
如果 POST 直接返回视图名，用户按一下 F5 浏览器就会把那条提问重发一遍 ——
既重复计费，页面上也会多出一轮一模一样的对话。重定向之后刷新只是重新
GET 一次页面，什么都不会发生。

**为什么要登录：** 用户明确选了这个。未登录时模板上那个图标不会链到这里，
但直接敲 URL 还是能进来，所以这一层也要挡一道（模板藏起来只是不显示，
不等于访问不到）。
"""

import logging
import uuid

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.auth import current
from core.constants import ROBOT_ERROR, ROBOT_SESSION
from core.decorators import login_required

from . import services

log = logging.getLogger(__name__)

# 空对话时给的示例问题。降低开口门槛，也顺便告诉用户「原来可以这么问」。
# 第一句是价格区间，第二句是完全没有关键词的场景（也是最需要机器人的那种），
# 第三句是普通的书名。三种问法各示范一次。
EXAMPLES = [
    "有没有 500 块以内的自行车？",
    "推荐一个送朋友的生日礼物",
    "想买本四级单词书，有吗？",
]

# 对话历史和「正在思考」闸门在缓存里的 key 模板，%s 是下面那个随机串
HISTORY_KEY = "robot:history:%s"
BUSY_KEY = "robot:busy:%s"

# 闸门最长挂多久。正常路径上它是 try/finally 里主动删的，
# 这个超时只为「进程刚好在提问中途挂了」兜底。
BUSY_TTL = 300


# ---------------------------------------------------------------- 对话历史放哪

# 对话历史**不放在 session 里**，只把一把「钥匙」放进去。
#
# 原因：settings.SESSION_ENGINE 用的是签名 cookie 后端 —— 整个 session
# 序列化后要塞进一个 4KB 的 Cookie。而一轮对话按中文 JSON 转义（一个汉字
# 6 个字节）序列化下来就是几 KB，六轮下来几十 KB，一放进去 Cookie 立刻超限。
# 超限的后果不是「聊天记录丢了」这么轻：浏览器会**整个丢掉这个 Cookie**，
# 用户的登录态跟着一起没，表现是「聊了一句就被登出」，而且完全看不出原因。
#
# 所以 session 里只留一个 32 位的随机串（几十字节），真正的记录放缓存。
# 行为和原版一致：跳页面不丢、关掉浏览器就没了；服务重启也会没，
# 但原版 Tomcat 重启同样会没。


def _key(request, template, create=False):
    """取缓存 key。`create=True` 时才为这次登录新建一个随机串。"""
    sid = request.session.get(ROBOT_SESSION)
    if not sid:
        if not create:
            return None
        sid = uuid.uuid4().hex
        request.session[ROBOT_SESSION] = sid
    return template % sid


def _history(request):
    """取对话历史。没有就返回空列表 —— 调用方拿去往 ask() 里传。

    `ask()` 会往这个列表里 append，所以**绝不能返回 None**。
    """
    key = _key(request, HISTORY_KEY)
    if not key:
        return []
    return cache.get(key) or []


def _save_history(request, history):
    cache.set(
        _key(request, HISTORY_KEY, create=True),
        history,
        settings.ROBOT_HISTORY_CACHE_SECONDS,
    )


def _first_text(reply):
    """兜底文案一定在第一个文字段里，见 services._fallback 的实现。"""
    for segment in (reply or {}).get("segments") or []:
        if segment.get("type") == "text" and segment.get("text"):
            return segment["text"]
    return services.MSG_SERVER


# ---------------------------------------------------------------- 视图


@login_required
def page(request):
    """对话页。"""
    if not services.available():
        return redirect("goods_home")

    bubbles = services.render(_history(request))

    # 上一次提问失败留下的提示，附在对话末尾当一条机器人消息。
    # 合并进 bubbles 而不是另开一个模板变量，模板那边就只用遍历一个列表。
    error = request.session.pop(ROBOT_ERROR, None)
    if error:
        bubbles.append(
            {"mine": False, "time": None, "segments": [services.text_segment(error)]}
        )

    return render(request, "robot/chat.html", {"bubbles": bubbles, "examples": EXAMPLES})


@require_POST
@login_required
def send(request):
    """提问。拿到回答（或失败提示）写进缓存，然后重定向回对话页。"""
    if not services.available():
        return redirect("goods_home")

    busy_key = _key(request, BUSY_KEY, create=True)

    # 同一个会话同时只允许一个请求在飞。
    # 表单是同步 POST、浏览器端没有超时，等不及的用户会再点一次；
    # 每点一次都是真实的模型调用（要花钱、要占住一个线程几十秒）。
    # 抢不到这把闸就直接回去，页面上看不出任何异常。
    #
    # cache.add 是「不存在才写」的原子操作，正好是一次 test-and-set；
    # 自己写 `if key in cache: return` 再 set 是两步，两个并发请求能同时过。
    if not cache.add(busy_key, 1, BUSY_TTL):
        log.info("上一个提问还没答完，忽略这次重复提交, userId=%s", _user_id(request))
        return redirect("robot_page")

    try:
        history = _history(request)
        reply = services.ask(request.POST.get("q"), history)
        _save_history(request, history)
        if reply["fallback"]:
            request.session[ROBOT_ERROR] = _first_text(reply)
    except Exception:
        # ask() 内部已经把能预料到的失败（网络、超时、状态码、JSON 不合法）
        # 全收敛成兜底文案了，能漏到这里的都是没预料到的
        log.exception("处理机器人提问时发生未预期的异常, userId=%s", _user_id(request))
        request.session[ROBOT_ERROR] = services.MSG_SERVER
    finally:
        # 放在 finally 里：不管上面怎么退出，闸都必须松开，
        # 否则这个会话的机器人就永远卡在「正在思考」了
        cache.delete(busy_key)

    return redirect("robot_page")


@require_POST
@login_required
def clear(request):
    """清空对话。只清缓存里的历史，不涉及任何数据库操作。"""
    key = _key(request, HISTORY_KEY)
    if key:
        cache.delete(key)
    request.session.pop(ROBOT_ERROR, None)
    return redirect("robot_page")


def _user_id(request):
    user = current(request)
    return user["id"] if user else None
