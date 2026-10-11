"""
跳回来源页。

原版到处都是 `return new ModelAndView("redirect:" + request.getHeader("Referer"))`，
而且**没做任何校验** —— 也就是说 `Referer` 是攻击者可控的，改一下就能把用户
从本站跳到钓鱼站（开放重定向）。

原版还有第二个坑：用户直接在地址栏敲地址、或者浏览器隐私设置不带 Referer 时，
`getHeader("Referer")` 返回 null，拼出来就是 `redirect:null`，
浏览器会跳到 `/user/null` 这种不存在的地址。UserController.loginValidate
里对登录单独补了兜底，但 `changeName` / `addUser` / `back()` 都没有。

这里一次把两件事都办了：**同源才跳，不同源退到 fallback**。
判定用 Django 自带的 `url_has_allowed_host_and_scheme`（它处理了协议、
端口、`//evil.com` 这类协议相对地址），不自己写正则。
"""

from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def safe_referer(request):
    """取来源页地址；不是同源的就返回 None。"""
    referer = request.META.get("HTTP_REFERER")
    if not referer:
        return None
    if url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return referer
    return None


def back(request, fallback):
    """跳回来源页；没有来源页（或来源页不可信）就跳 fallback。

    fallback 传**路由名或路径**都行，直接交给 redirect()。
    """
    return redirect(safe_referer(request) or fallback)
