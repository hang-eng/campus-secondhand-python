"""
这个 app 没有自己的 model —— 9 张表的 model 分在各自的 app 里：

    accounts/models.py   User（t_shop_user）、Follow（t_shop_follow）
    goods/models.py      Catelog、Goods、Image、Comments、Reply
    chat/models.py       Notice、Message、ContactRequest（新表）

**为什么所有 model 都是 `managed = False`：**

表早就存在、数据也都在（2 个账号、14 件商品、8 个分类……），Django 一行都不该动。
建表和改表一律走手写 SQL 脚本（见 `sql/`），**不生成 migration**。

所以：
  - 不要跑 `python manage.py makemigrations` / `migrate`，这些表 Django 不管；
  - 列名、类型、拼写都照抄原库，包括那几个拼错的
    （`describle`、`catelog`、`commet_id`、大写 `QQ`）—— 改对了反而连不上。

另外 9 张表之间**一个外键约束都没有**，跨表引用全靠应用层。所以关联字段
用普通 `IntegerField`，需要取关联对象时自己查（见各 service）。
"""
