"""错误页。

原版有两个内容完全一样的 404 模板（`404.html` 和 `error/404.html`），
后者被 ManageController 在权限不足时直接返回。重写后只留 `error/404.html` 一份，
两处都指向它。
"""

from django.http import HttpResponse
from django.shortcuts import render


def page_not_found(request, exception=None):
    return render(request, "error/404.html", status=404)


def server_error(request):
    """500 页。

    这里要格外稳：触发 500 的原因可能是 context processor 自己炸了，
    所以套一层兜底，实在渲染不出来就退成纯文本，绝不能二次抛异常。
    """
    try:
        return render(request, "error/500.html", status=500)
    except Exception:
        return HttpResponse("服务器内部错误", status=500, content_type="text/plain; charset=utf-8")
