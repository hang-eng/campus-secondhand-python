"""
根路径。

`/` → 302 → `/goods/homeGoods`。

用 302 不是 301：换首页地址的时候（比如以后改版放到 /index）301 会被浏览器
永久缓存住，用户清缓存前回不来。原版是 `IndexController` 里的一个
`return "redirect:/goods/homeGoods"`。
"""

from django.urls import path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="goods_home", permanent=False)),
]
