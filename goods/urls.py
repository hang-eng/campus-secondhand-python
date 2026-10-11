"""商品域路由。

**路径逐字照抄原版** GoodsController 的 @RequestMapping：

    /goods/homeGoods          首页
    /goods/search             搜索
    /goods/catelog/{id}       分类列表
    /goods/goodsId/{id}       商品详情
    /goods/sold/{id}          标记已售出 / 恢复在售（POST）
    /goods/publishGoods       发布页
    /goods/publishGoodsSubmit 发布提交（POST）
    /goods/editGoods/{id}     编辑页
    /goods/editGoodsSubmit    编辑提交（POST）
    /goods/deleteGoods/{id}   删除（POST）
    /goods/uploadFile         图片上传（POST）
    /goods/api/updateGoods    编辑提交（POST）  ← 后台商品管理页
    /goods/api/offGoods/{id}  后台删除（DELETE）← 后台商品管理页
    /comments/api/*           评论增删改（POST）← P4

原版另有一条 `/goods/offGoods`，方法体就是 `return null;`（空壳死路由），
**丢弃不搬**。

`deleteGoods` 原版是 GET（模板用 `<a href>` 点一下就删），重写改成 POST
并配了确认框 —— 删数据的动作不该能被浏览器预取或爬虫踩到。
"""

from django.urls import path

from . import views

urlpatterns = [
    path("homeGoods", views.home, name="goods_home"),
    path("search", views.search, name="goods_search"),
    path("catelog/<int:id>", views.catelog, name="goods_catelog"),
    path("goodsId/<int:id>", views.detail, name="goods_detail"),
    path("sold/<int:id>", views.set_sold, name="goods_sold"),
    # 下架 / 重新上架。**重写时新增的一条路由** —— 原版那个「下架」按钮
    # 指向的 `/goods/offGoods` 方法体是 `return null`（空壳死路由，已丢弃）。
    # 路径起名和 `sold` 对称，一眼能看出是同一类东西。
    path("state/<int:id>", views.set_state, name="goods_state"),

    path("publishGoods", views.publish, name="goods_publish"),
    path("publishGoodsSubmit", views.publish_submit, name="goods_publish_submit"),
    path("editGoods/<int:id>", views.edit, name="goods_edit"),
    path("editGoodsSubmit", views.edit_submit, name="goods_edit_submit"),
    path("deleteGoods/<int:id>", views.delete_goods, name="goods_delete"),
    path("uploadFile", views.upload_file, name="goods_upload"),

    # 后台商品管理页那两个（只有 manage-goodsList.js 会调）
    path("api/updateGoods", views.api_update_goods, name="goods_api_update"),
    path("api/offGoods/<int:id>", views.api_off_goods, name="goods_api_off"),
]
