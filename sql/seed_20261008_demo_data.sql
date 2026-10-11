-- ============================================================================
--  校园二手交易平台 —— 演示数据（配合 db_springboot_squirrel.sql 使用）
--
--  日期：2026-10-08
--  作用：把「导出时那台电脑上现在的样子」原样搬到新机器上 ——
--        2 个账号、14 件商品、14 条商品图记录、2 条评论、17 条站内通知。
--
--  ---------------------------------------------------------------------------
--  ⚠ 只在**空库**上跑
--  ---------------------------------------------------------------------------
--  这个脚本会先把下面十张表清空，再重新插入。它的用途只有一个：
--  在新电脑上把演示数据恢复出来。
--
--  在你自己**正在用**的库上跑 = 把你后来加的商品、账号全冲掉。本机不要跑。
--
--  ---------------------------------------------------------------------------
--  怎么用
--  ---------------------------------------------------------------------------
--  第 1 步，建十张空表：   sql\db_springboot_squirrel.sql
--  第 2 步，灌演示数据：   sql\seed_20261008_demo_data.sql   ← 本文件
--
--  PowerShell（用户终端是 PS 5.1。行尾那个反引号 ` 是续行符）：
--
--      $SQL = 'C:\你解压到的位置\campus-secondhand-python\sql'
--      $MYSQL = 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe'
--
--      & $MYSQL -uroot -p你的密码 --default-character-set=utf8mb4 -e "source $SQL/db_springboot_squirrel.sql"
--      & $MYSQL -uroot -p你的密码 --default-character-set=utf8mb4 -e "source $SQL/seed_20261008_demo_data.sql"
--
--  （注意 source 后面要用**正斜杠** /，反斜杠会被 MySQL 当转义符。）
--  （也可以把两个 .sql 文件在 Navicat / Workbench 里依次打开执行。）
--
--  ---------------------------------------------------------------------------
--  几点说明
--  ---------------------------------------------------------------------------
--  · **商品图片不在这个脚本里。** 下面 t_shop_image 的 img_url 存的是
--    **纯文件名**（一串 uuid 加 .jpg），图片文件本身在项目目录
--
--        upload\images\
--
--    下面，一共 14 个，和这 14 条记录一一对应。搬文件夹的时候整个 upload
--    目录都要带上，少一个那个商品就是裂图。
--
--  · 两个账号的密码都是 **123456**（库里存的是 32 位大写 MD5）：
--        15377671813   管理员   power=90
--        12345678900   用户1    power=10，名下 14 件闲置
--
--  · t_shop_catelog.number 那几个数（19 / 8 / 7 / 9 / …）和实际商品数
--    **对不上**（实际每个分类各 2 件）。这是本项目历史遗留的计数漂移，
--    Java 版原样就是这样 —— 删商品、换分类时那个计数器不一定跟着走。
--    但**页面上从来没显示过这一列**，所以对不上也看不见：
--      · 左侧分类导航是 templates/base_shop.html 里硬编码的 nav_items
--      · 发布页/编辑页的「物品类别」下拉是 goods/views.py 的 CATELOG_OPTIONS
--    真正查这张表的地方只有两处，都不涉及 number：
--      · 分类页 /goods/catelog/{id} 取分类对象（取不到就 404）
--      · 后台商品管理页的品类下拉
--    这里**照原样导出，不做修正** —— 目的是搬一台机器，不是顺手改数据。
--
--  · 所有日期时间都是 **varchar 字符串**，不是 datetime，原样搬运。
--
--  · 表之间没有外键约束（原项目就是这个设计），所以 DELETE 的先后顺序
--    其实无所谓，按「引用别人的排前面」写只是习惯。
-- ============================================================================

SET NAMES utf8mb4;

USE `squirrel_test`;

START TRANSACTION;

DELETE FROM `t_shop_contact_request`;
DELETE FROM `t_shop_notice`;
DELETE FROM `t_shop_message`;
DELETE FROM `t_shop_reply`;
DELETE FROM `t_shop_comments`;
DELETE FROM `t_shop_image`;
DELETE FROM `t_shop_goods`;
DELETE FROM `t_shop_follow`;
DELETE FROM `t_shop_user`;
DELETE FROM `t_shop_catelog`;
-- ------------------------------------------------ 数据

INSERT INTO `t_shop_catelog` (`id`, `name`, `number`, `status`) VALUES (1,'闲置数码',19,1);
INSERT INTO `t_shop_catelog` (`id`, `name`, `number`, `status`) VALUES (2,'校园代步',8,1);
INSERT INTO `t_shop_catelog` (`id`, `name`, `number`, `status`) VALUES (3,'电器日用',7,1);
INSERT INTO `t_shop_catelog` (`id`, `name`, `number`, `status`) VALUES (4,'图书教材',9,1);
INSERT INTO `t_shop_catelog` (`id`, `name`, `number`, `status`) VALUES (5,'美妆衣物',8,1);
INSERT INTO `t_shop_catelog` (`id`, `name`, `number`, `status`) VALUES (6,'运动棋牌',4,1);
INSERT INTO `t_shop_catelog` (`id`, `name`, `number`, `status`) VALUES (7,'周边其他',4,1);
INSERT INTO `t_shop_catelog` (`id`, `name`, `number`, `status`) VALUES (8,'全部',0,1);
INSERT INTO `t_shop_user` (`id`, `phone`, `username`, `password`, `QQ`, `wechat`, `font_size`, `avatar`, `create_at`, `goods_num`, `power`, `last_login`, `status`) VALUES (10,'15377671813','管理员','E10ADC3949BA59ABBE56E057F20F883E',NULL,NULL,'m',NULL,'2026-09-20 18:50:00',0,90,NULL,0);
INSERT INTO `t_shop_user` (`id`, `phone`, `username`, `password`, `QQ`, `wechat`, `font_size`, `avatar`, `create_at`, `goods_num`, `power`, `last_login`, `status`) VALUES (11,'12345678900','用户1','E10ADC3949BA59ABBE56E057F20F883E',NULL,NULL,'m',NULL,'2026-09-20 18:50:05',14,10,NULL,0);
INSERT INTO `t_shop_goods` (`id`, `catelog_id`, `user_id`, `name`, `price`, `real_price`, `start_time`, `polish_time`, `end_time`, `describle`, `commet_num`, `state`, `sold`) VALUES (57,1,11,'iPhone 18 pro max',6666.00,9999.00,'2026-09-20','2026-09-20','2026-09-30','最新款苹果手机，先到先得，酒红配色',NULL,0,0);
INSERT INTO `t_shop_goods` (`id`, `catelog_id`, `user_id`, `name`, `price`, `real_price`, `start_time`, `polish_time`, `end_time`, `describle`, `commet_num`, `state`, `sold`) VALUES (58,1,11,'大疆摄像机',888.00,1899.00,'2026-09-20','2026-09-20','2026-09-30','大疆牌小型摄像机',NULL,0,0);
INSERT INTO `t_shop_goods` (`id`, `catelog_id`, `user_id`, `name`, `price`, `real_price`, `start_time`, `polish_time`, `end_time`, `describle`, `commet_num`, `state`, `sold`) VALUES (59,2,11,'自行车',500.00,999.00,'2026-09-20','2026-09-20','2026-09-30','小型自行车，方便代步，物美价廉',NULL,0,0);
INSERT INTO `t_shop_goods` (`id`, `catelog_id`, `user_id`, `name`, `price`, `real_price`, `start_time`, `polish_time`, `end_time`, `describle`, `commet_num`, `state`, `sold`) VALUES (60,2,11,'电动车',788.00,1688.00,'2026-09-20','2026-09-20','2026-09-30','小型电动车，代步，续航高，颜值也高',NULL,0,0);
INSERT INTO `t_shop_goods` (`id`, `catelog_id`, `user_id`, `name`, `price`, `real_price`, `start_time`, `polish_time`, `end_time`, `describle`, `commet_num`, `state`, `sold`) VALUES (61,3,11,'电风扇',100.00,200.00,'2026-09-20','2026-09-20','2026-09-30','宿舍自用电风扇，无噪音',NULL,0,0);
INSERT INTO `t_shop_goods` (`id`, `catelog_id`, `user_id`, `name`, `price`, `real_price`, `start_time`, `polish_time`, `end_time`, `describle`, `commet_num`, `state`, `sold`) VALUES (62,3,11,'充电宝',55.00,119.00,'2026-09-20','2026-09-20','2026-09-30','便携式充电宝，高续航，安全性高，不发热',NULL,0,0);
INSERT INTO `t_shop_goods` (`id`, `catelog_id`, `user_id`, `name`, `price`, `real_price`, `start_time`, `polish_time`, `end_time`, `describle`, `commet_num`, `state`, `sold`) VALUES (63,4,11,'福尔摩斯全集',88.00,218.00,'2026-09-20','2026-09-20','2026-09-30','福尔摩斯侦探系列全集小说，收藏纪念价值很高',NULL,0,0);
INSERT INTO `t_shop_goods` (`id`, `catelog_id`, `user_id`, `name`, `price`, `real_price`, `start_time`, `polish_time`, `end_time`, `describle`, `commet_num`, `state`, `sold`) VALUES (64,4,11,'python教学书',28.00,58.00,'2026-09-20','2026-09-20','2026-09-30','python二手教学书，实用性很强',NULL,0,0);
INSERT INTO `t_shop_goods` (`id`, `catelog_id`, `user_id`, `name`, `price`, `real_price`, `start_time`, `polish_time`, `end_time`, `describle`, `commet_num`, `state`, `sold`) VALUES (65,5,11,'洛丽塔',388.00,588.00,'2026-09-20','2026-09-20','2026-09-30','学姐二手洛丽塔服装，漫展校庆可用，成色完美',NULL,0,0);
INSERT INTO `t_shop_goods` (`id`, `catelog_id`, `user_id`, `name`, `price`, `real_price`, `start_time`, `polish_time`, `end_time`, `describle`, `commet_num`, `state`, `sold`) VALUES (66,5,11,'罗蒙西装',388.00,688.00,'2026-09-20','2026-09-20','2026-09-30','罗蒙大品牌西装，校庆典礼可用',NULL,0,0);
INSERT INTO `t_shop_goods` (`id`, `catelog_id`, `user_id`, `name`, `price`, `real_price`, `start_time`, `polish_time`, `end_time`, `describle`, `commet_num`, `state`, `sold`) VALUES (67,6,11,'羽毛球拍',888.00,1388.00,'2026-09-20','2026-09-20','2026-09-30','天斧88dpro，尤尼克斯大牌羽毛球拍',NULL,0,0);
INSERT INTO `t_shop_goods` (`id`, `catelog_id`, `user_id`, `name`, `price`, `real_price`, `start_time`, `polish_time`, `end_time`, `describle`, `commet_num`, `state`, `sold`) VALUES (68,6,11,'篮球',68.00,178.00,'2026-09-20','2026-09-20','2026-09-30','李宁篮球',NULL,0,0);
INSERT INTO `t_shop_goods` (`id`, `catelog_id`, `user_id`, `name`, `price`, `real_price`, `start_time`, `polish_time`, `end_time`, `describle`, `commet_num`, `state`, `sold`) VALUES (69,7,11,'纪念币',14.00,17.00,'2026-09-20','2026-09-20','2026-09-30','纪念币，非常有纪念价值，适合送人',NULL,0,0);
INSERT INTO `t_shop_goods` (`id`, `catelog_id`, `user_id`, `name`, `price`, `real_price`, `start_time`, `polish_time`, `end_time`, `describle`, `commet_num`, `state`, `sold`) VALUES (70,7,11,'初音未来周边',98.00,228.00,'2026-09-20','2026-09-20','2026-09-30','可爱的初音未来玩偶，可爱',NULL,0,0);
INSERT INTO `t_shop_image` (`id`, `goods_id`, `img_url`) VALUES (69,57,'58521ba2-4eb7-4ddc-9226-36b8472efed2.jpg');
INSERT INTO `t_shop_image` (`id`, `goods_id`, `img_url`) VALUES (70,58,'b496e189-c3e3-4ec3-aa80-327f73e53e23.jpg');
INSERT INTO `t_shop_image` (`id`, `goods_id`, `img_url`) VALUES (71,59,'c6b89dd1-9d2c-4da4-9e66-26786fc7d11a.jpg');
INSERT INTO `t_shop_image` (`id`, `goods_id`, `img_url`) VALUES (72,60,'67d7c00b-6398-4471-ae58-d602395db00f.jpg');
INSERT INTO `t_shop_image` (`id`, `goods_id`, `img_url`) VALUES (73,61,'e031a356-6b5c-4bf1-a5c2-d21897127b86.jpg');
INSERT INTO `t_shop_image` (`id`, `goods_id`, `img_url`) VALUES (74,62,'45149fa4-83b8-4ec7-a748-2b35f4aaf9ee.jpg');
INSERT INTO `t_shop_image` (`id`, `goods_id`, `img_url`) VALUES (75,63,'04b47e9a-87ce-4a56-923d-2756847e3110.jpg');
INSERT INTO `t_shop_image` (`id`, `goods_id`, `img_url`) VALUES (76,64,'12bb0c2c-4329-4dc7-9055-047bfd82bc3a.jpg');
INSERT INTO `t_shop_image` (`id`, `goods_id`, `img_url`) VALUES (77,65,'9667841d-240a-4f65-a126-a884fdde6104.jpg');
INSERT INTO `t_shop_image` (`id`, `goods_id`, `img_url`) VALUES (78,66,'b2013375-00be-4ce0-9b5e-22339b58e2ba.jpg');
INSERT INTO `t_shop_image` (`id`, `goods_id`, `img_url`) VALUES (79,67,'edfe8158-cd69-40ea-9c27-7752b0391084.jpg');
INSERT INTO `t_shop_image` (`id`, `goods_id`, `img_url`) VALUES (80,68,'7e7afb5d-0ece-4b67-9c66-108b7df74b48.jpg');
INSERT INTO `t_shop_image` (`id`, `goods_id`, `img_url`) VALUES (81,69,'343f07bf-19ef-437a-ba3f-181d262070a0.jpg');
INSERT INTO `t_shop_image` (`id`, `goods_id`, `img_url`) VALUES (82,70,'6c3abf9a-a5c8-4c37-abc6-149dbd038312.jpg');
INSERT INTO `t_shop_comments` (`id`, `user_id`, `atuser_id`, `goods_id`, `content`, `create_at`) VALUES (6,11,0,57,'想要的小伙伴可以打电话联系哦','2026-09-20 19:21:48');
INSERT INTO `t_shop_comments` (`id`, `user_id`, `atuser_id`, `goods_id`, `content`, `create_at`) VALUES (7,10,0,70,'同学可以便宜一点吗','2026-09-20 20:26:33');
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (6,11,'你发布的「iPhone 18 pro max」已经上架，可在「我的闲置」里查看。','2026-09-20 19:20:57',1);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (7,11,'你发布的「大疆摄像机」已经上架，可在「我的闲置」里查看。','2026-09-20 19:52:02',1);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (8,11,'你发布的「自行车」已经上架，可在「我的闲置」里查看。','2026-09-20 19:53:10',1);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (9,11,'你发布的「电动车」已经上架，可在「我的闲置」里查看。','2026-09-20 19:56:58',1);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (10,11,'你发布的「电风扇」已经上架，可在「我的闲置」里查看。','2026-09-20 19:58:28',1);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (11,11,'你发布的「充电宝」已经上架，可在「我的闲置」里查看。','2026-09-20 19:59:09',1);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (12,11,'你发布的「福尔摩斯全集」已经上架，可在「我的闲置」里查看。','2026-09-20 20:01:57',1);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (13,11,'你发布的「python教学书」已经上架，可在「我的闲置」里查看。','2026-09-20 20:02:47',1);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (14,11,'你发布的「洛丽塔」已经上架，可在「我的闲置」里查看。','2026-09-20 20:03:50',1);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (15,11,'你发布的「罗蒙西装」已经上架，可在「我的闲置」里查看。','2026-09-20 20:22:20',1);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (16,11,'你发布的「羽毛球拍」已经上架，可在「我的闲置」里查看。','2026-09-20 20:23:12',1);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (17,11,'你发布的「篮球」已经上架，可在「我的闲置」里查看。','2026-09-20 20:23:48',1);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (18,11,'你发布的「纪念币」已经上架，可在「我的闲置」里查看。','2026-09-20 20:24:38',1);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (19,11,'你发布的「初音未来周边」已经上架，可在「我的闲置」里查看。','2026-09-20 20:25:28',1);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (31,17,'欢迎来到武汉理工大学二手交易平台！在这里可以发布自己的闲置物品，也可以淘到同学的好东西。','2026-10-08 21:21:05',0);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (32,18,'欢迎来到武汉理工大学二手交易平台！在这里可以发布自己的闲置物品，也可以淘到同学的好东西。','2026-10-08 21:22:11',0);
INSERT INTO `t_shop_notice` (`id`, `user_id`, `context`, `create_at`, `status`) VALUES (33,19,'欢迎来到武汉理工大学二手交易平台！在这里可以发布自己的闲置物品，也可以淘到同学的好东西。','2026-10-08 21:24:23',0);

COMMIT;

-- ============================================================================
--  跑完之后，库里应该正好是：
--      t_shop_user              2 行
--      t_shop_follow            0 行
--      t_shop_catelog           8 行
--      t_shop_goods            14 行
--      t_shop_image            14 行
--      t_shop_comments          2 行
--      t_shop_reply             0 行
--      t_shop_message           0 行
--      t_shop_notice           17 行
--      t_shop_contact_request   0 行
--
--  自己核对一下：
--      SELECT COUNT(*) FROM t_shop_user;    -- 应该是 2
--      SELECT COUNT(*) FROM t_shop_goods;   -- 应该是 14
--  对不上的话，多半是第 1 步的建表脚本没跑成功。
-- ============================================================================
