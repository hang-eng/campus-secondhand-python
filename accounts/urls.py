"""
用户域路由。

**路径逐字照抄原版** UserController 的 @RequestMapping —— 这样 Django 开 8000、
Java 开 8081，同一个地址可以直接并排对照，模板里的链接也大多是机械替换。

`/user/message`、`/user/chat/{id}`、`/user/profile/{id}` 虽然也在 `/user/` 下，
但属于私信，放在 `chat/urls.py`，由 config/urls.py 先 include chat 再 include 本文件。
"""

from django.urls import path

from . import views

urlpatterns = [
    # ---------------------------------------------------------- 登录 / 注册 / 登出
    path("login", views.login_view, name="user_login"),
    path("addUser", views.add_user, name="user_add"),
    path("logout", views.logout_view, name="user_logout"),
    path("changeName", views.change_name, name="user_change_name"),

    # ---------------------------------------------------------- 个人中心 / 设置
    path("home", views.home, name="user_home"),
    path("basic", views.basic, name="user_basic"),
    path("updateInfo", views.update_info, name="user_update_info"),
    path("allGoods", views.all_goods, name="user_goods"),
    # 保存界面字体大小。**重写时新增的一条路由** —— 原版没有这个功能。
    # 路径起名跟上面 `updateInfo` 一样用 camelCase，和「改资料」是一类东西。
    path("fontSize", views.set_font_size, name="user_font_size"),

    # ---------------------------------------------------------- 头像
    path("avatar/preset", views.avatar_preset, name="user_avatar_preset"),
    path("avatar", views.avatar_upload, name="user_avatar"),

    # ---------------------------------------------------------- 关注
    path("follow", views.follow_list, name="user_follow"),
    path("follow/<int:user_id>", views.follow_add, name="user_follow_add"),
    path("unfollow/<int:user_id>", views.follow_remove, name="user_follow_remove"),

    # ---------------------------------------------------------- 旧地址转发
    # 原版这一页已并进 /user/message，路由留着免得老链接 404
    path("notice", views.notice_redirect, name="user_notice"),

    # ---------------------------------------------------------- JSON 接口
    path("api/login", views.api_login, name="user_api_login"),
    path("api/addUser", views.api_add_user, name="user_api_add"),
    path("api/updateUser", views.api_update_user, name="user_api_update"),
    path("api/deleteUser/<int:user_id>", views.api_delete_user, name="user_api_delete"),
    path("api/freezeUser/<int:user_id>", views.api_freeze_user, name="user_api_freeze"),
    path("api/unfreezeUser/<int:user_id>", views.api_unfreeze_user, name="user_api_unfreeze"),
]
