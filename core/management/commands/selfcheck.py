"""
环境自检。跑一条命令就知道这套环境是不是好的：

    python manage.py selfcheck

检查三件事：
  1. 能不能连上 squirrel_test
  2. 9 张表能不能读到数据（证明 model 的列名映射是对的）
  3. 密码校验逻辑对不对（原库密码是大写 MD5，这点最容易栽）

出问题的时候先跑这个，比盲猜快得多。
"""

from django.core.management.base import BaseCommand
from django.db.models import Count

from accounts.models import Follow, User
from chat.models import Message, Notice
from core.utils import check_password, days_later, md5_hex, now_time
from goods.models import Catelog, Comments, Goods, Image, Reply


class Command(BaseCommand):
    help = "检查数据库连接、model 映射和密码校验是否正常"

    def handle(self, *args, **options):
        ok = True

        self.stdout.write(self.style.MIGRATE_HEADING("1. 数据库连接与表"))
        try:
            counts = {
                "t_shop_user": User.objects.count(),
                "t_shop_catelog": Catelog.objects.count(),
                "t_shop_goods": Goods.objects.count(),
                "t_shop_image": Image.objects.count(),
                "t_shop_comments": Comments.objects.count(),
                "t_shop_reply": Reply.objects.count(),
                "t_shop_notice": Notice.objects.count(),
                "t_shop_message": Message.objects.count(),
                "t_shop_follow": Follow.objects.count(),
            }
            for table, n in counts.items():
                self.stdout.write(f"   {table:<20} {n:>6} 行")
        except Exception as exc:
            ok = False
            self.stderr.write(self.style.ERROR(f"   连不上或表结构不对：{exc}"))

        if not ok:
            self.stdout.write(self.style.ERROR("\n自检未通过。"))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("\n2. 用户（注意 QQ 列名是大写）"))
        for u in User.objects.all().order_by("id"):
            self.stdout.write(
                f"   id={u.id}  {u.phone}  {u.username}  power={u.power}  "
                f"goods_num={u.goods_num}  avatar_url={u.avatar_url}"
            )

        self.stdout.write(self.style.MIGRATE_HEADING("\n3. 密码校验（原库是大写 MD5）"))
        self.stdout.write(f'   md5_hex("123456") = {md5_hex("123456")}')
        sample = User.objects.exclude(password=None).first()
        if sample:
            right = check_password("123456", sample.password)
            wrong = check_password("这个肯定不对", sample.password)
            self.stdout.write(f"   对 {sample.phone} 校验 123456 -> {right}（应为 True）")
            self.stdout.write(f"   对 {sample.phone} 校验 错误密码 -> {wrong}（应为 False）")
            if not right or wrong:
                ok = False
                self.stderr.write(self.style.ERROR("   密码校验不对，检查 core/utils.py"))

        self.stdout.write(self.style.MIGRATE_HEADING("\n4. 日期工具"))
        self.stdout.write(f'   days_later("2026-09-20", 10) = {days_later("2026-09-20", 10)}'
                          "（库里商品的 end_time 正是 2026-09-30）")
        self.stdout.write(f"   now_time() = {now_time()}")

        self.stdout.write(self.style.MIGRATE_HEADING("\n5. 数据一致性抽查"))
        agg = Comments.objects.values("goods_id").annotate(cnt=Count("id")).order_by("goods_id")
        self.stdout.write(f"   每件商品的评论数：{[(r['goods_id'], r['cnt']) for r in agg]}")
        for u in User.objects.all().order_by("id"):
            actual = Goods.objects.filter(user_id=u.id).count()
            flag = "" if actual == (u.goods_num or 0) else "  ← 与 goods_num 不一致"
            self.stdout.write(f"   {u.username}：实际 {actual} 件，goods_num={u.goods_num}{flag}")

        if ok:
            self.stdout.write(self.style.SUCCESS("\n自检通过，环境可用。"))
        else:
            self.stdout.write(self.style.ERROR("\n自检未通过，看上面的报错。"))
