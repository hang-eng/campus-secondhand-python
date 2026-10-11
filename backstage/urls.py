"""
后台管理路由。

**路径逐字照抄原版** `ManageController` 的 @RequestMapping：

    /manage/login        控制台登录页
    /manage/user/list    用户管理
    /manage/goods/list   商品管理

`config/urls.py` 里已经挂了 `path("manage/", include("backstage.urls"))`，
所以这里的路径不带 `manage/` 前缀。

原版还有一个 `TODO::商品审核管理` 的空注释（没有对应的路由和方法），
没有可搬的东西，不建假方法。
"""

from django.urls import path

from . import views

urlpatterns = [
    path("login", views.login_page, name="manage_login"),
    path("user/list", views.user_list, name="manage_user_list"),
    path("goods/list", views.goods_list, name="manage_goods_list"),
]
