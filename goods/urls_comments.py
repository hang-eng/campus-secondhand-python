"""
评论的 JSON 接口路由。

路径不在 `/goods/` 底下，而是**挂在根上**的 `/comments/api/...` ——
原版 `CommentsController` 的类级注解是 `@RequestMapping("/comments")`，
和 `GoodsController` 的 `/goods` 是两条独立前缀。前端 `static/js/goods/detailGoods.js`
里的地址也是写死的 `/comments/api/...`（在 `static/js/app.js` 的 `app.URL` 里），
所以这里单开一个 urlconf，在 `config/urls.py` 里也挂到根上。

实现放在 `goods/views.py` 里（这三个接口操作的是 `t_shop_comments`，
属于商品域），路由拆出来只是为了让 `/goods/xxx` 那一份保持清爽。
"""

from django.urls import path

from . import views

urlpatterns = [
    path("comments/api/addComments", views.comments_add, name="comments_add"),
    path("comments/api/updateComments", views.comments_update, name="comments_update"),
    path(
        "comments/api/deleteComments/<int:id>",
        views.comments_delete,
        name="comments_delete",
    ),
]
