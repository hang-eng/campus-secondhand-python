"""
消息域路由：消息中心、私信对话、他人资料页、通知已读。

**路径逐字照抄原版** MessageController 的 @RequestMapping，
放在 `config/urls.py` 里 `user/` 前缀下的**第一个** include：
本文件里的路径（message / chat / profile / notice/read…）在
`accounts/urls.py` 里没有重名，但先 include chat 更省心 ——
万一以后有人加了一条同名的，先注册的那条赢，不会静默换掉一个页面。

`/user/notice`（单数、不带 read）那一条在 accounts 里：
原版它只是把老地址 302 到 `/user/message?tab=notice`，属于用户域的历史包袱。
本文件里的是 `/user/notice/read/...`，两条不冲突。
"""

from django.urls import path

from . import views

urlpatterns = [
    # ---------------------------------------------------------- 消息中心
    path("message", views.message, name="chat_message"),
    path("notice/read/<int:id>", views.notice_read, name="user_notice_read"),
    path("notice/readAll", views.notice_read_all, name="user_notice_read_all"),

    # ---------------------------------------------------------- 对话
    # GET 看消息、POST 发一条，两个方法同一个地址（原版也是这样）
    path("chat/<int:user_id>", views.chat, name="user_chat"),

    # ---------------------------------------------------------- 联系方式交换
    # 这四个是**重写时新增的**，原版没有 —— 原版根本不交换联系方式，
    # 手机号 / QQ 直接摆在商品详情页上谁都能看。四个动作各一条，
    # 全是 POST（都会改库、都会给对方推通知）。
    path("contact/request/<int:user_id>", views.contact_request,
         name="user_contact_request"),
    path("contact/agree/<int:user_id>", views.contact_agree,
         name="user_contact_agree"),
    path("contact/refuse/<int:user_id>", views.contact_refuse,
         name="user_contact_refuse"),
    path("contact/revoke/<int:user_id>", views.contact_revoke,
         name="user_contact_revoke"),

    # ---------------------------------------------------------- 他人资料
    path("profile/<int:id>", views.profile, name="user_profile"),
]
