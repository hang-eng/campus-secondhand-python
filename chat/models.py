"""站内通知、私信，以及新增的联系方式交换请求。

对应原库 `t_shop_notice`、`t_shop_message`，加一张重写时新建的
`t_shop_contact_request`（见下）。
"""

from django.db import models


class Notice(models.Model):
    """系统通知。

    注意 `status` 列**没有默认值**，插入时必须显式给 0，否则在
    STRICT 模式下会报错。
    """

    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(null=True)
    context = models.TextField(null=True)
    create_at = models.CharField(max_length=25, null=True)
    # 0 未读 / 1 已读
    status = models.SmallIntegerField(null=True)

    class Meta:
        managed = False
        db_table = "t_shop_notice"


class Message(models.Model):
    """私信。`status` 是**收件人视角**的已读标记。

    标已读时一定要把 from_user_id 和 to_user_id **两个条件都带上**，
    只按 id 更新会让人能标掉别人的未读（原版 MessageMapper.updateReadByFromAndTo
    特意带了两列，这里也照做）。
    """

    id = models.AutoField(primary_key=True)
    from_user_id = models.IntegerField()
    to_user_id = models.IntegerField()
    # 从哪件商品发起的，可以为空
    goods_id = models.IntegerField(null=True)
    context = models.TextField(null=True)
    create_at = models.CharField(max_length=25, null=True)
    # 0 未读 / 1 已读
    status = models.SmallIntegerField(null=True, default=0)

    class Meta:
        managed = False
        db_table = "t_shop_message"


class ContactRequest(models.Model):
    """联系方式交换请求（**重写时新增的表**）。

    私信里聊得来才交换手机号/QQ/微信，这是需求。规则：

      - 只有双方都在**当前会话**里发过言，才能点「请求交换信息」
      - 请求方点请求 = 自己这边同意；对方点同意后，双方**当前登录态**互见
      - 只见于对话页。商品详情页原本就把卖家的手机号和 QQ 摆在「卖家信息」
        那一栏里，他人资料页摆着 QQ —— 那是原版就有的，重写时照搬，**不算**
        这条规则的范围。这条管的是**新加的微信**和「已交换」这个状态：
        微信这一列只在对话页那个 `.chat-contact` 块里渲染，
        `accounts/services.py: user_card()` 根本不带它，
        所以别的页面没有「模板少写一个 if 就漏出去」的机会。
      - 下次登录必须重新请求（可见性不落库、不落 cookie）
      - 有同意也有拒绝，同意后任一方可撤销

    这张表**只存请求与同意的状态**（用来显示按钮文案、发通知），
    **不决定能不能看见** —— 能不能看见还要求当前 session 里点过。
    完整判定见 `chat/services.py: contact_state()`。

    表结构由 `sql/migrations/` 下的脚本创建，不用 migration。
    """

    PENDING = 0
    AGREED = 1
    REFUSED = 2

    id = models.AutoField(primary_key=True)
    from_user_id = models.IntegerField()
    to_user_id = models.IntegerField()
    status = models.SmallIntegerField(default=0)
    create_at = models.CharField(max_length=25, null=True)
    update_at = models.CharField(max_length=25, null=True)

    class Meta:
        managed = False
        db_table = "t_shop_contact_request"
        # 表上建了 uk_from_to 唯一键，这里只作文档（managed=False 不会落地）
        constraints = [
            models.UniqueConstraint(
                fields=["from_user_id", "to_user_id"], name="uk_from_to"
            )
        ]
