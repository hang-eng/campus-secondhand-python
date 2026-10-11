-- ============================================================================
--  校园二手交易平台 —— 完整建库脚本（Django 版）
--
--  日期：2026-10-08
--  作用：从零建出一个能直接跑起来的 `squirrel_test`。
--
--  ---------------------------------------------------------------------------
--  这份文件和 Java 仓库里那份同名文件的关系
--  ---------------------------------------------------------------------------
--  Java 仓库 `C:\Users\17360\campus-secondhand\sql\db_springboot_squirrel.sql`
--  是 2018 年原作者用 Navicat 导出的，**已经严重过期**，别拿它建库：
--
--    · 缺 `t_shop_follow`（关注功能是后来加的）
--    · 缺 `t_shop_user.avatar` 列（换头像功能是后来加的）
--    · 缺 `t_shop_goods.sold` 列（「已售出」标记是后来加的）
--    · 缺 `t_shop_contact_request` 表和 `t_shop_user.wechat` 列（本次新加）
--    · 缺 `t_shop_user.font_size` 列（「界面字体大小」是本次新加的）
--    · 分类名和现在对不上（那份里分类 7 叫「票券小物」，现在是「周边其他」）
--    · 带一堆 2018 年的测试数据（用户 id 1/4、商品 id 1…），跟现在的库毫无关系
--
--  那份文件**保持原样不动** —— Java 版是退路，一行不改。
--  要建新库请用**本文件**：它是按当前真实库
--  （`SHOW CREATE TABLE` 逐张导出）写的，十张表一张不落。
--
--  ---------------------------------------------------------------------------
--  怎么跑（PowerShell，用户终端是 PS 5.1）
--  ---------------------------------------------------------------------------
--
--      & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" `
--          -uroot -p123456 --default-character-set=utf8mb4 `
--          -e "source C:/Users/17360/Desktop/软件工程/campus-secondhand-python/sql/db_springboot_squirrel.sql"
--
--  ---------------------------------------------------------------------------
--  几点说明
--  ---------------------------------------------------------------------------
--  · 十张表**之间没有任何外键约束**，跨表引用全靠应用层。这不是疏漏，
--    是原项目的既有设计（原作者把 `user_id` / `goods_id` 都只当普通整数存），
--    重写时照抄了 —— 加外键会让「删用户」「删商品」那几条路径当场炸掉，
--    因为它们都没做级联清理。本脚本里也就一个 FOREIGN KEY 都不写。
--
--  · 表级字符集不统一（`t_shop_user` 是 latin1、`t_shop_message` 是 utf8mb3、
--    其余是 utf8mb3/utf8mb4），需要中文的列上单独写了 utf8mb4。
--    照抄现状 —— 统一字符集要重建表，风险远大于收益。
--
--  · 所有日期时间都是 **varchar 字符串**，不是 datetime。照抄现状：
--    换成 datetime 之后，既有的「2026-10-08 21:25:35」这类值对不上，
--    按字符串排序的行为也会变（`polish_time` 就是靠字符串序排首页的）。
--
--  · 这份脚本只建**结构 + 分类种子数据**，不塞任何用户和商品。
--    商品靠页面发布，用户靠页面注册。
--
--  建完之后怎么弄出一个管理员：
--      1) 打开首页 → 注册一个账号
--      2) 执行：UPDATE t_shop_user SET power = 90 WHERE phone = '你的手机号';
--      （密码存的是 **32 位大写 MD5**，'123456' 是
--        E10ADC3949BA59ABBE56E057F20F883E）
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `squirrel_test`
    DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `squirrel_test`;


-- ============================================================================
--  1. 用户
-- ============================================================================
CREATE TABLE IF NOT EXISTS `t_shop_user` (
  `id`         int NOT NULL AUTO_INCREMENT,
  `phone`      char(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '登录使用的手机号',
  `username`   varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户名',
  `password`   char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '密码，32位大写MD5',
  -- 列名是大写 QQ，Django 那边靠 db_column 指名（accounts/models.py）
  `QQ`         varchar(12) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '即时通讯',
  -- 微信是本次新加的列，位置紧跟 QQ 后面（顺序跟现有库保持一致）
  `wechat`     varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '微信',
  -- 界面字体大小也是新加的列，紧跟 wechat 后面（顺序跟现有库保持一致）。
  -- 存短码 s/m/l/xl，不是百分比 —— 理由见 core/constants.py: FONT_SIZES
  `font_size`  varchar(10) NOT NULL DEFAULT 'm' COMMENT '界面字体大小 s小 m标准 l大 xl特大',
  `avatar`     varchar(120) DEFAULT NULL COMMENT '头像web路径，NULL表示用默认',
  `create_at`  varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '创建时间',
  `goods_num`  int DEFAULT '0' COMMENT '发布过的物品数量',
  `power`      tinyint DEFAULT '10' COMMENT '权限值，普通用户默认为10，管理员90',
  `last_login` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '最近一次登陆时间',
  `status`     tinyint DEFAULT '0' COMMENT '账号是否冻结，默认0未冻结，1已冻结',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;


-- ============================================================================
--  2. 关注关系
-- ============================================================================
CREATE TABLE IF NOT EXISTS `t_shop_follow` (
  `id`             int NOT NULL AUTO_INCREMENT COMMENT '关注关系主键',
  `user_id`        int NOT NULL COMMENT '关注者（粉丝）的用户id',
  `follow_user_id` int NOT NULL COMMENT '被关注者的用户id',
  `create_at`      varchar(25) DEFAULT NULL COMMENT '关注时间',
  PRIMARY KEY (`id`),
  -- 唯一键兜底：重复关注靠它挡，业务层用 get_or_create
  UNIQUE KEY `uk_user_follow` (`user_id`,`follow_user_id`),
  KEY `idx_follow_user` (`follow_user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户关注关系表';


-- ============================================================================
--  3. 商品分类
-- ============================================================================
CREATE TABLE IF NOT EXISTS `t_shop_catelog` (
  `id`     int NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name`   varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '分类名',
  `number` int DEFAULT '0' COMMENT '该分类下的商品数量',
  `status` tinyint DEFAULT '0' COMMENT '分类状态，1启用',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- 分类的种子数据。这几行属于**必需的基础数据**，不是测试数据 ——
-- 缺了它，分类页 /goods/catelog/{id} 会 404（那一页要按 id 取分类对象），
-- 后台商品管理页的品类下拉也会是空的。
--
-- 注意：**前台左侧那条分类导航不是查这张表的**，是
-- templates/base_shop.html 里硬编码的 nav_items。发布页和编辑页的
-- 「物品类别」下拉走的也是 goods/views.py 里硬编码的 CATELOG_OPTIONS。
-- 所以这一列 `number` 页面上从来不显示（见下面 id=8 那条的说明）。
--
-- id=8 那个「全部」是**历史遗留的空壳**：`number=0`、底下没有任何商品，
-- 但 `status=1` 所以首页照样把它列出来。照抄现状（之前和用户确认过，
-- 后台商品管理页那个品类下拉框里也因此会看到两个「全部」——
-- 一个是 value=0 的真·不限分类，一个是这个 value=8 的空分类）。
INSERT INTO `t_shop_catelog` (`id`, `name`, `number`, `status`) VALUES
  (1, '闲置数码', 0, 1),
  (2, '校园代步', 0, 1),
  (3, '电器日用', 0, 1),
  (4, '图书教材', 0, 1),
  (5, '美妆衣物', 0, 1),
  (6, '运动棋牌', 0, 1),
  (7, '周边其他', 0, 1),
  (8, '全部',     0, 1);


-- ============================================================================
--  4. 商品
-- ============================================================================
CREATE TABLE IF NOT EXISTS `t_shop_goods` (
  `id`          int NOT NULL AUTO_INCREMENT COMMENT '商品主键',
  `catelog_id`  int DEFAULT NULL COMMENT '商品分类，外键',
  `user_id`     int DEFAULT NULL COMMENT '用户外键',
  `name`        varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '商品名称',
  `price`       float(11,2) DEFAULT NULL COMMENT '出售价格',
  `real_price`  float(11,2) DEFAULT NULL COMMENT '真实价格',
  `start_time`  varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '发布时间',
  -- 首页/分类页的排序键。改商品时会刷新它，让商品回到最前面（「擦亮」）
  `polish_time` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '擦亮时间，按该时间进行查询，精确到时分秒',
  `end_time`    varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '下架时间',
  `describle`   text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '详细信息',
  -- 全库都是 NULL：加评论时没有任何地方回写它，评论数是查询时现算的。
  -- 留着这一列是照抄原表，不删。
  `commet_num`  int DEFAULT NULL COMMENT '评论回复数量（实际未使用）',
  `state`       int DEFAULT '0' COMMENT '0进行中，1已下架，2审核中',
  -- 和 state 语义**不同**：state 是「有没有收起来」，sold 是「卖掉了没有」。
  -- 两者互不影响：已售出的商品不会自动下架。
  `sold`        tinyint NOT NULL DEFAULT '0' COMMENT '是否已售出，0在售，1已售出',
  PRIMARY KEY (`id`),
  KEY `catelog_id` (`catelog_id`),
  KEY `user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;


-- ============================================================================
--  5. 商品图片
-- ============================================================================
CREATE TABLE IF NOT EXISTS `t_shop_image` (
  `id`      int NOT NULL AUTO_INCREMENT COMMENT '图片主键',
  -- 存的是**纯文件名**（<uuid>.jpg），模板自己拼 /upload/images/。
  -- 注意：`t_shop_user.avatar` 存的却是**完整 web 路径**，两者不一致，
  -- 这是原项目就有的，照抄别统一。
  `goods_id` int NOT NULL COMMENT '商品外键',
  `img_url`  text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '图片链接',
  PRIMARY KEY (`id`),
  KEY `goods_id` (`goods_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;


-- ============================================================================
--  6. 评论
-- ============================================================================
CREATE TABLE IF NOT EXISTS `t_shop_comments` (
  `id`        int NOT NULL AUTO_INCREMENT COMMENT '评论主键',
  `user_id`   int DEFAULT NULL COMMENT '用户，外键',
  `atuser_id` int DEFAULT NULL COMMENT '回复用户',
  `goods_id`  int DEFAULT NULL COMMENT '商品，外键',
  `content`   text COMMENT '评论内容',
  `create_at` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '评论时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 ROW_FORMAT=DYNAMIC;


-- ============================================================================
--  7. 评论回复（**死表**）
-- ============================================================================
-- 原项目里没有任何代码读写它 —— 页面上的「回复」按钮从来就没接上过。
-- 重写时同样只保留模型、不实现业务（见 goods/models.py: Reply）。
-- 留在建库脚本里是为了和 Java 版建出来的库保持一致，方便并排对照。
CREATE TABLE IF NOT EXISTS `t_shop_reply` (
  `id`        int NOT NULL AUTO_INCREMENT COMMENT '评论回复主键',
  `user_id`   int DEFAULT NULL COMMENT '用户，外键',
  `atuser_id` int DEFAULT NULL,
  `commet_id` int DEFAULT NULL COMMENT '评论，外键',
  `content`   text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '回复内容',
  `create_at` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '回复时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;


-- ============================================================================
--  8. 私信
-- ============================================================================
CREATE TABLE IF NOT EXISTS `t_shop_message` (
  `id`           int NOT NULL AUTO_INCREMENT COMMENT '私信id',
  `from_user_id` int NOT NULL COMMENT '发件人id',
  `to_user_id`   int NOT NULL COMMENT '收件人id',
  `goods_id`     int DEFAULT NULL COMMENT '从哪件商品发起，可为空',
  `context`      text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '正文',
  `create_at`    varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '发送时间',
  -- 是**收件人视角**的未读标记。标已读时 WHERE 里 from 和 to 两列都要带上，
  -- 只按 to_user_id 更新会把「我发给别人的消息」也标成已读。
  `status`       tinyint DEFAULT '0' COMMENT '状态：0未读 1已读（收件人视角）',
  PRIMARY KEY (`id`),
  KEY `idx_from_to` (`from_user_id`,`to_user_id`),
  KEY `idx_to_status` (`to_user_id`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COMMENT='用户间私信';


-- ============================================================================
--  9. 系统通知
-- ============================================================================
CREATE TABLE IF NOT EXISTS `t_shop_notice` (
  `id`        int NOT NULL AUTO_INCREMENT COMMENT '系统信息主键',
  `user_id`   int DEFAULT NULL COMMENT '用户，外键',
  `context`   text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '信息内容',
  `create_at` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '推送信息时间',
  -- 这一列**没有默认值**，插入时必须显式传 0，否则 STRICT 模式下直接报错。
  -- 见 chat/services.py: add_notice 的注释。
  `status`    tinyint DEFAULT NULL COMMENT '状态，0未读，1已读',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;


-- ============================================================================
--  10. 联系方式交换请求（**本次新增的表**）
-- ============================================================================
-- 这张表只存「谁向谁请求过、同意了没有」，**不决定现在能不能看见对方的手机号**。
--
-- 完整规则见 chat/models.py: ContactRequest 和 chat/services.py：
--   · 双方都在会话里发过言，才能点「请求交换信息」
--   · 请求方点请求 = 自己这边同意；对方同意后，双方**当前登录态**互见
--   · 只在对话页显示，商品详情页和他人资料页一律不露
--   · 下次登录必须重新请求（可见性不落库、不落 cookie）
--   · 同意后任一方可以撤销，撤销后两边**当场**互相看不见
--
-- 唯一键 uk_from_to 是**有向的**：(A,B) 和 (B,A) 是两行，互不冲突。
CREATE TABLE IF NOT EXISTS `t_shop_contact_request` (
  `id`           int NOT NULL AUTO_INCREMENT COMMENT '请求id',
  `from_user_id` int NOT NULL COMMENT '发起方用户id',
  `to_user_id`   int NOT NULL COMMENT '接收方用户id',
  `status`       tinyint NOT NULL DEFAULT '0' COMMENT '0待处理 1已同意 2已拒绝',
  `create_at`    varchar(25) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '发起时间',
  `update_at`    varchar(25) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '状态变更时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_from_to` (`from_user_id`,`to_user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='联系方式交换请求';
