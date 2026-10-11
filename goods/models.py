"""商品域：分类、商品、商品图片、评论、回复。

对应原库 `t_shop_catelog`、`t_shop_goods`、`t_shop_image`、
`t_shop_comments`、`t_shop_reply`。

**两个状态列语义不同，别混：**
  - `state`（int）  0 进行中 / 1 已下架 / 2 审核中  ← 用户主动下架用这个
  - `sold`（tinyint）0 在售   / 1 已售出           ← 「标记已出售」用这个

原版还有个更隐蔽的问题：`state` 列在**任何 SELECT 里都不过滤**，
所以「下架」根本没效果。重写后前台查询统一加 `state=STATE_ON`，
后台不过滤（管理员要看得见全部）。
"""

from django.db import models
from django.db.models import Count

from core.constants import SOLD_NO, STATE_ON


class Catelog(models.Model):
    """分类。表名拼写就是 `catelog`（不是 catalog）。"""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30, null=True)
    number = models.IntegerField(null=True, default=0)
    status = models.SmallIntegerField(null=True, default=0)

    class Meta:
        managed = False
        db_table = "t_shop_catelog"

    def __str__(self):
        return self.name or str(self.id)


class Goods(models.Model):
    """商品。

    `describle` 是原库的拼写（应为 describe），照抄不改。
    `commet_num` 同样拼错，而且原版**从来不回写**这一列，全库都是 NULL ——
    评论数是在查询时用 GROUP BY 现算的（见 Comments.count_by_goods_ids）。
    """

    id = models.AutoField(primary_key=True)
    catelog_id = models.IntegerField(null=True)
    user_id = models.IntegerField(null=True)
    name = models.CharField(max_length=50, null=True)
    price = models.FloatField(null=True)
    real_price = models.FloatField(null=True)
    # 三个时间都是 varchar，格式 yyyy-MM-dd（不是 DateTimeField，排序按字符串）
    start_time = models.CharField(max_length=25, null=True)
    # 擦亮时间，前台列表全按它倒序
    polish_time = models.CharField(max_length=30, null=True)
    end_time = models.CharField(max_length=25, null=True)
    describle = models.TextField(null=True)
    commet_num = models.IntegerField(null=True)
    state = models.IntegerField(null=True, default=0)
    sold = models.SmallIntegerField(default=0)

    class Meta:
        managed = False
        db_table = "t_shop_goods"

    @property
    def is_sold(self):
        return self.sold == SOLD_NO + 1

    @property
    def is_off(self):
        return self.state == 1

    def __str__(self):
        return self.name or str(self.id)


class Image(models.Model):
    """商品图片。`img_url` 存的是**纯文件名**（<uuid>.jpg），不是完整路径。

    这点和 User.avatar 不一样（那个存的是完整 web 路径），是原版的历史不一致。
    模板里要自己拼 `/upload/` 前缀，重写时照抄，别顺手统一。
    """

    id = models.AutoField(primary_key=True)
    goods_id = models.IntegerField()
    img_url = models.TextField()

    class Meta:
        managed = False
        db_table = "t_shop_image"


class Comments(models.Model):
    """商品评论。`atuser_id` 用 0 表示「不是回复某个人」。"""

    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(null=True)
    atuser_id = models.IntegerField(null=True)
    goods_id = models.IntegerField(null=True)
    content = models.TextField(null=True)
    create_at = models.CharField(max_length=25, null=True)

    class Meta:
        managed = False
        db_table = "t_shop_comments"

    @classmethod
    def count_by_goods_ids(cls, goods_ids):
        """一次 GROUP BY 查出这批商品各自的评论数，返回 {goods_id: 条数}。

        原版是 `CommentsService.countByGoodsIds`，同样一条 IN + GROUP BY。
        评论数**不能**取 `t_shop_goods.commet_num` —— 加评论时没有任何地方
        去回写那一列，全库都是 NULL。模板里按 0 兜底。
        """
        ids = [i for i in (goods_ids or []) if i is not None]
        if not ids:
            return {}
        rows = (
            cls.objects.filter(goods_id__in=ids)
            .values("goods_id")
            .annotate(n=Count("id"))
        )
        return {row["goods_id"]: row["n"] for row in rows}


class Reply(models.Model):
    """评论的回复。

    **原项目里这是一张死表** —— ReplyMapper 存在，但没有任何 service 或
    controller 注入它，整套 XML 从未被调用过。这里只建 model 保住表映射，
    不实现业务。答辩时如果被问到，这就是"原版有张表没做完"。
    """

    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(null=True)
    atuser_id = models.IntegerField(null=True)
    # 列名拼写就是 commet_id；而且这张表**没有 goods_id 列**
    commet_id = models.IntegerField(null=True)
    content = models.TextField(null=True)
    create_at = models.CharField(max_length=25, null=True)

    class Meta:
        managed = False
        db_table = "t_shop_reply"


# 前台（首页 / 搜索 / 分类 / 详情）统一用的过滤条件。
# 后台管理**不加**这个条件 —— 管理员要看得见已下架的货。
FRONT_VISIBLE = models.Q(state=STATE_ON)
