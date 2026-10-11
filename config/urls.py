"""
总路由。

**路径与原版 Java 逐字一致**（`/goods/homeGoods`、`/user/chat/{id}`、`/manage/login`），
这样 Django 版跑在 8000、Java 版跑在 8081，同一个地址可以直接并排对照。

注意 `/user/` 前缀挂了两个 include：原版 MessageController 和 UserController
都挂类级 `/user`，这里按功能拆开。Django 按顺序匹配，chat 的先试，
试不中会自动落到 accounts。
"""

from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve

from robot import views as robot_views

urlpatterns = [
    # 根路径 302 到首页（原版 MainController.index 的 redirect:/goods/homeGoods）
    path("", include("goods.urls_root")),
    # 评论接口在根上的 /comments/api/...（原版 CommentsController 的 /comments 前缀）
    path("", include("goods.urls_comments")),
    path("goods/", include("goods.urls")),
    path("user/", include("chat.urls")),
    path("user/", include("accounts.urls")),
    path("manage/", include("backstage.urls")),
    # 对话页单独写一行，不走下面的 include，原因见 robot/urls.py 的模块说明
    path("robot", robot_views.page, name="robot_page"),
    path("robot/", include("robot.urls")),
    # 用户上传的图片。原版是 Spring 的 addResourceHandlers 把 /upload/** 指到
    # <user.dir>/upload/images/，这里等价。
    re_path(r"^upload/(?P<path>.*)$", serve, {"document_root": settings.UPLOAD_ROOT}),
    # `/img/**` 这一条是补的：原版 Spring Boot 会自动把 classpath:/static/**
    # 映射到根路径，所以 /img/photo.jpg、/css/xxx.css 都能直接访问。Django 只
    # 认 STATIC_URL（本项目的 /static/），`/img/photo.jpg` 会 404。
    #
    # 而 User.avatar 为空时 avatar_url 回落到 `/img/photo.jpg`（见
    # core/constants.DEFAULT_AVATAR），商品没图时也用这个 —— 也就是说
    # 这台机器上两个用户都没设头像，全站的头像原本全是裂图。
    # 这里把 /img/ 单独接到 static/img/ 上，和原版的路径保持一字不差
    # （模板里写的是 {{ static('img/...') }} 的地方仍然走 /static/，两边都通）。
    re_path(
        r"^img/(?P<path>.*)$",
        serve,
        {"document_root": settings.BASE_DIR / "static" / "img"},
    ),
]

handler404 = "core.views.page_not_found"
handler500 = "core.views.server_error"
