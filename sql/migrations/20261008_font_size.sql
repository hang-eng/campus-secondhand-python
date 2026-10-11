-- ============================================================================
--  校园二手交易平台 —— 结构变更 ②：界面字体大小列
--
--  日期：2026-10-08
--  库：  squirrel_test
--
--  在 `20261008_wechat_and_contact_request.sql` 之后跑。**只跑一次。**
--
--  跑法（PowerShell，用户终端是 PS 5.1）：
--
--      & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" `
--          -uroot -p123456 --default-character-set=utf8mb4 squirrel_test `
--          -e "source C:/Users/17360/Desktop/软件工程/campus-secondhand-python/sql/migrations/20261008_font_size.sql"
--
--  或者直接把这个文件的内容粘进 Navicat / Workbench 执行。
--
--  为什么要改结构：
--    需求里「个人设置里加一个字体大小的选项，能调节所有界面的字体大小」。
--    这个偏好要跟着账号走（换浏览器、换电脑、重新登录都记得），
--    所以必须落库，不能只放 cookie。现有十张表里没有一列装得下 → 加一列。
--
--  向后兼容：纯新增，不加外键、不改既有列、不动任何一行数据。
--  同时连这个库的 Java 版（8081）不受影响，照常跑。
-- ============================================================================

USE `squirrel_test`;


-- ---------------------------------------------------------------------- ①
-- t_shop_user 加一列 font_size。
--
-- **存的是短码（s / m / l / xl），不是百分比数字。**
-- 百分比写在 CSS 里（static/css/campus.css 最后一节）和
-- core/constants.py: FONT_SIZES 里。以后想把「大」从 110% 调成 115%，
-- 只改 CSS 一行就行，不用去 UPDATE 全库用户的数据。
--
-- 长度 10 是宽裕取整（最长的是 'xl'，两位）。
-- 默认 'm'（标准）：存量用户一行都不用改，自动拿到标准档；
-- NOT NULL + DEFAULT 也让调用方不必到处判空，不过
-- core/auth.py 那边仍然写了 `or FONT_SIZE_DEFAULT` 兜底 ——
-- 万一有人手工把这列改成 NULL，页面不该因此炸掉。
--
-- 放在 wechat 后面，和 `sql/db_springboot_squirrel.sql` 里
-- 那份完整建表语句的列顺序保持一致：两边不一致的话，拿那份脚本新建出来的库
-- 跑这个 ALTER，列顺序会跟现有的库不一样，`SELECT *` 的结果对不上。
-- ----------------------------------------------------------------------
ALTER TABLE `t_shop_user`
    ADD COLUMN `font_size` varchar(10) NOT NULL DEFAULT 'm'
        COMMENT '界面字体大小 s小 m标准 l大 xl特大' AFTER `wechat`;
