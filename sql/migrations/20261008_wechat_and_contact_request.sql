-- ============================================================================
--  校园二手交易平台 —— 结构变更 ①：微信列 + 联系方式交换请求表
--
--  日期：2026-10-08
--  库：  squirrel_test
--
--  这个脚本把 `sql/db_springboot_squirrel.sql` 建出来的库补齐到能跑
--  P7（联系方式隐私收口）的状态。**只跑一次。**
--
--  跑法（PowerShell，用户终端是 PS 5.1）：
--
--      & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" `
--          -uroot -p123456 --default-character-set=utf8mb4 squirrel_test `
--          -e "source C:/Users/17360/Desktop/软件工程/campus-secondhand-python/sql/migrations/20261008_wechat_and_contact_request.sql"
--
--  或者直接把这个文件的内容粘进 Navicat / Workbench 执行。
--
--  为什么要改结构：
--    · 需求里「交换联系方式」要交换手机号 / QQ / 微信三样，而
--      `t_shop_user` 只有手机号和 QQ 两列，微信没地方存 → 加一列。
--    · 「谁向谁请求过、同意了没有」这个状态必须落库（要显示按钮文案、
--      要在对方那边标未读），现有九张表里没有一张装得下 → 加一张表。
--
--  向后兼容：这次改动**纯新增**，不加外键、不改既有列、不动任何一行数据，
--  所以同时连这个库的 Java 版（8081）不受影响，照常跑。
-- ============================================================================

USE `squirrel_test`;


-- ---------------------------------------------------------------------- ①
-- t_shop_user 加一列 wechat。
--
-- 放在 QQ 后面（AFTER `QQ`），和 `sql/db_springboot_squirrel.sql` 里
-- 那份完整建表语句的列顺序保持一致 —— 两边不一致的话，拿那份脚本新建出来的
-- 库跑这个 ALTER，列顺序会跟现有的库不一样，`SELECT *` 的结果对不上。
--
-- 长度取 30：微信号官方上限是 20 位，留点余量。允许 NULL ——
-- 用户不填微信是常态，不能因此卡住注册。
-- 字符集单独写 utf8mb4：`t_shop_user` 的表级字符集是 latin1（历史遗留），
-- 不写的话这一列会跟着变成 latin1，中文昵称类的内容会存不进去。
-- ----------------------------------------------------------------------
ALTER TABLE `t_shop_user`
    ADD COLUMN `wechat` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        DEFAULT NULL COMMENT '微信' AFTER `QQ`;


-- ---------------------------------------------------------------------- ②
-- 联系方式交换请求表。
--
-- 这张表**只存请求与同意的状态**，不决定「现在能不能看见对方的手机号」。
-- 完整规则见 `chat/models.py: ContactRequest` 和 `chat/services.py`：
--
--   · 双方都在会话里发过言，才能点「请求交换信息」
--   · 请求方点请求 = 自己这边同意；对方同意后，双方**当前登录态**互见
--   · 下次登录必须重新请求（可见性不落库、不落 cookie）
--   · 同意后任一方可以撤销，撤销后两边**当场**互相看不见
--
-- 唯一键 uk_from_to 是**有向的**：(A,B) 和 (B,A) 是两行，互不冲突。
-- 所以 A 向 B 请求过之后，B 再向 A 请求一次，是合法的一条新记录。
--
-- 没有外键约束 —— 和库里其余九张表一样，跨表引用全靠应用层。
-- 这不是疏漏：加外键之后删用户就要先删请求，而原版的删用户/删商品
-- 都没做级联清理，加进来会当场把那些路径炸掉。
--
-- 字符集 utf8mb4，和 `t_shop_message`（同类数据）一致。
-- ----------------------------------------------------------------------
CREATE TABLE `t_shop_contact_request` (
    `id`           int NOT NULL AUTO_INCREMENT COMMENT '请求id',
    `from_user_id` int NOT NULL COMMENT '发起方用户id',
    `to_user_id`   int NOT NULL COMMENT '接收方用户id',
    `status`       tinyint NOT NULL DEFAULT '0' COMMENT '0待处理 1已同意 2已拒绝',
    `create_at`    varchar(25) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '发起时间',
    `update_at`    varchar(25) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '状态变更时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_from_to` (`from_user_id`,`to_user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='联系方式交换请求';
