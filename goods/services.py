"""
商品列表的组装逻辑。

原版每个列表页面（首页 8 个板块、搜索、分类、我的闲置、他人资料页）都要
自己走一遍「查商品 → 逐件查图片 → 拼成一个 GoodsExtend」，那段代码在
`UserController.goods` / `GoodsController` 里抄了五遍，而且**每件商品
单独发一次图片查询**（N+1）。

这里收成一个 `cards()`，一次 `IN` 查出全部图片再按 goods_id 分组。
"""

from core.constants import DEFAULT_GOODS_IMAGE
from .models import Image

def cards(goods_queryset):
    """把商品查成一叠卡片：`{"goods": ..., "images": [...], "cover": "..."}`。

    模板里的用法：`item.goods.name`、`item.cover`、`item.images|length`。

    为什么多给一个 `cover` 而不是让模板自己取 `images[0]`：
    原版模板写的就是 `items.images[0].imgUrl`，商品一张图都没有时
    SpEL 越界、整页 500。多算一个字段比在十几个模板里重复写兜底划算。
    """
    goods_list = list(goods_queryset)
    ids = [g.id for g in goods_list if g.id is not None]

    by_goods = {}
    if ids:
        # 一次查完。原版是循环里逐件查，商品多了就是 N+1。
        for img in Image.objects.filter(goods_id__in=ids).order_by("id"):
            by_goods.setdefault(img.goods_id, []).append(img)

    result = []
    for goods in goods_list:
        images = by_goods.get(goods.id, [])
        result.append(
            {
                "goods": goods,
                "images": images,
                # img_url 存的是纯文件名，要自己拼 /upload/（原版的历史不一致，
                # 头像那一列存的是完整路径，别混）
                "cover": "/upload/" + images[0].img_url if images else DEFAULT_GOODS_IMAGE,
            }
        )
    return result


def card_json(item):
    """把一叠卡片转成 JSON 安全的 dict，供模板里 `|tojson` 塞给前端 JS。

    原版是把 Java 的 GoodsExtend 整个对象交给 Jackson 序列化进
    `th:inline="javascript"`。Python 这边不能这么干 —— Django 的 model
    实例没有通用的 JSON 编码器，`tojson` 会直接抛
    `TypeError: Object of type Goods is not JSON serializable`。

    键名换成 **camelCase**：前端 `static/js/goods/detailGoods.js` 里写的是
    `goodsExtend.goods.id`、`commentsList[i].userId`，那是 Jackson 按 Java
    属性名生成的，这套键名是既有 JS 的契约，改成 snake_case 就得动 JS。
    """
    goods = item["goods"]
    return {
        "goods": {
            "id": goods.id,
            "catelogId": goods.catelog_id,
            "userId": goods.user_id,
            "name": goods.name,
            "price": goods.price,
            "realPrice": goods.real_price,
            "describle": goods.describle,
            "state": goods.state,
            "sold": goods.sold,
            "startTime": goods.start_time,
            "polishTime": goods.polish_time,
            "endTime": goods.end_time,
        },
        "images": [{"id": i.id, "imgUrl": i.img_url} for i in item["images"]],
        "cover": item["cover"],
    }


def goods_rows(goods_queryset):
    """后台商品管理页要的那种「一行一件商品」，带发布人。

    和上面的 `cards()` 不是一回事，别合并：
      - `cards()` 是给前台列表用的，带图片和封面，模板要的是 `item.cover`。
      - 这一份是给**后台表格**用的，要的是 `item.user.username`
        （编辑弹层里那个「发布人」格子），图片一张都不要。

    键名照抄 Jackson 序列化 Java `Goods` 出来的样子（`catelogId` / `realPrice` /
    `polishTime` ...）：`static/js/manage/manage-goodsList.js` 发回去的时候
    写的就是 `goodsList[index].catelogId`、`goodsList[index].userId`，
    改成 snake_case 就得连 JS 一起改，而那几个 js 是和 Java 版共用的同一份。

    发布人是一次 `IN` 查完再按 id 挂上去的。原版 ManageController 是
    `getUsersByIds` 之后 `id2user.get(...)` 手工挂，也是这个思路；
    差别在于原版那条 `getUsersByIds` 收到空集合时会退化成查全表
    （见 UserMapper.xml），而这里空列表就是空列表。
    """
    from accounts.models import User

    rows = list(goods_queryset)
    owner_ids = {g.user_id for g in rows if g.user_id}
    owners = (
        {u.id: u for u in User.objects.filter(id__in=owner_ids)} if owner_ids else {}
    )

    result = []
    for goods in rows:
        owner = owners.get(goods.user_id)
        result.append(
            {
                "id": goods.id,
                "catelogId": goods.catelog_id,
                "userId": goods.user_id,
                "name": goods.name,
                "price": goods.price,
                "realPrice": goods.real_price,
                "startTime": goods.start_time,
                "endTime": goods.end_time,
                "polishTime": goods.polish_time,
                "commetNum": goods.commet_num,
                "describle": goods.describle,
                "state": goods.state,
                "sold": goods.sold,
                # 用户被删掉之后商品还在（表之间没有外键约束）。
                # 给一个空的占位对象而不是 None：`manage-goodsList.js` 里那句
                # `$('#updateUsername').val(goodsList[index].user.username)`
                # 拿到 null 会直接 TypeError，那一行的「编辑」按钮就点不开了。
                "user": (
                    {"id": owner.id, "username": owner.username}
                    if owner
                    else {"id": 0, "username": ""}
                ),
            }
        )
    return result
