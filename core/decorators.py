"""
权限装饰器。

原版把「有没有登录」和「是不是管理员」的判断散在每个 Controller 方法里，
重写时收成装饰器，免得漏掉 —— 原版正是因为漏判，才留下几个越权漏洞。
"""

from functools import wraps

from django.shortcuts import redirect, render

from .ajax import CODE_FORBIDDEN, CODE_NOT_LOGIN, fail
from .auth import current
from .constants import ADMIN_POWER


def login_required(view):
    """未登录跳首页。

    原版是 `if (cur_user == null) return "redirect:/goods/homeGoods";`，
    这里保持同一行为（不是跳到登录页 —— 原版的登录是首页上的弹层）。
    """

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not current(request):
            return redirect("goods_home")
        return view(request, *args, **kwargs)

    return wrapper


def admin_required(view):
    """后台页面：不是管理员就渲染 404。

    原版 ManageController 就是这么做的 —— 返回 `/error/404` 而不是 403，
    不告诉对方「这里有个后台，只是你没权限」。
    """

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = current(request)
        if not user or user.get("power") != ADMIN_POWER:
            return render(request, "error/404.html", status=404)
        return view(request, *args, **kwargs)

    return wrapper


def admin_api(view):
    """后台的 JSON 接口：不是管理员返回「没权限」。

    原版这几个接口（删用户 / 冻结 / 解冻）**完全没检查 power**，
    任何登录用户都能调。这是重写时补上的。

    走 HTTP 200 + success:false 而不是 403，原因见 core/ajax.py: fail()。
    """

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = current(request)
        if not user or user.get("power") != ADMIN_POWER:
            return fail(CODE_FORBIDDEN)
        return view(request, *args, **kwargs)

    return wrapper


def ajax_login_required(view):
    """JSON 接口的登录校验。"""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not current(request):
            return fail(CODE_NOT_LOGIN)
        return view(request, *args, **kwargs)

    return wrapper
