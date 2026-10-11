"""用户与关注关系。

对应原库 `t_shop_user` 和 `t_shop_follow`。

两个坑写在明面上：
  1. `QQ` 列名是**大写**的，必须 db_column 指名，否则 Django 会去找 `qq` 列。
  2. `t_shop_user` 的字符集是 latin1（其他表是 utf8mb3），但连接层用 utf8mb4
     读出来是对的 —— 实测过，别被表定义吓到。
"""

from django.db import models

from core.constants import DEFAULT_AVATAR


class User(models.Model):
    """用户。密码是 32 位大写 MD5，见 core.utils.check_password。"""

    id = models.AutoField(primary_key=True)
    phone = models.CharField(max_length=11, null=True)
    username = models.CharField(max_length=30, null=True)
    password = models.CharField(max_length=32, null=True)
    # 列名大写 QQ
    qq = models.CharField(max_length=12, null=True, db_column="QQ")
    # 微信。**重写时新加的列**，原库没有 —— 见
    # sql/migrations/20261008_wechat_and_contact_request.sql。
    # 它只在「双方都同意交换联系方式」的对话页上出现，别的地方一律不露。
    wechat = models.CharField(max_length=30, null=True)
    # 界面字体大小，存短码 s / m / l / xl（见 core/constants.py: FONT_SIZES）。
    # **重写时新加的列**，原库没有 —— 见
    # sql/migrations/20261008_font_size.sql。
    #
    # 列上带 NOT NULL DEFAULT 'm'，理论上不会是 NULL；这里仍然允许 null
    # 并把 default 写成 'm'，是因为 Django 建 INSERT 语句时会带上这个默认值，
    # 而读的时候（core/auth.py）另有一层 `or FONT_SIZE_DEFAULT` 兜底。
    # 万一有人手工把这列改成 NULL，页面不该因此炸掉。
    font_size = models.CharField(max_length=10, null=True, default="m")
    # 存的是完整 web 路径（/img/photo3.jpg 或 /upload/<uuid>.jpg），不是文件名
    avatar = models.CharField(max_length=120, null=True)
    # 日期一律是 varchar 字符串，不是 DateTimeField
    create_at = models.CharField(max_length=20, null=True)
    goods_num = models.IntegerField(null=True, default=0)
    power = models.SmallIntegerField(null=True, default=10)
    last_login = models.CharField(max_length=20, null=True)
    status = models.SmallIntegerField(null=True, default=0)

    class Meta:
        managed = False
        db_table = "t_shop_user"

    @property
    def avatar_url(self):
        """原版 User.getAvatarUrl()：没设过头像就回落到默认图。

        兜底只写在这一处，模板里不要重复判断。
        """
        return self.avatar or DEFAULT_AVATAR

    @property
    def is_admin(self):
        """原版判断管理员唯一的口径：power == 90。"""
        return self.power == 90

    def __str__(self):
        return self.username or self.phone or str(self.id)


class Follow(models.Model):
    """关注关系。`user_id` 是关注者（粉丝），`follow_user_id` 是被关注者。

    表上有唯一键 `uk_user_follow(user_id, follow_user_id)`，
    所以重复关注靠数据库兜底，业务层用 get_or_create 就够了。
    """

    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()
    follow_user_id = models.IntegerField()
    create_at = models.CharField(max_length=25, null=True)

    class Meta:
        managed = False
        db_table = "t_shop_follow"
