# 校园二手交易平台 —— Python / Django 版

武汉理工大学二手交易平台。原项目是 Java + SpringBoot + MyBatis + Thymeleaf，
这个版本是**原样重写成 Python + Django** 的结果：功能对齐、URL 逐字一致、数据库沿用同一个，
但代码换成 Python，能读、能改、能讲。

代码在 `campus-secondhand-python\` 子目录里，这份文档描述的就是它。

> 🔻 **拿到这个文件夹的人，直接跳到 [第 13 节](#13-接收方换一台电脑怎么跑起来)。**
> 那一节是从零开始的完整安装步骤，照做就能跑起来，前面 12 节不用看
> （那些是讲项目本身的设计和改动的，答辩时再翻）。

---

## 目录

- [1. 这是什么](#1-这是什么)
- [2. 跑起来](#2-跑起来)
- [3. 测试账号](#3-测试账号)
- [4. 目录结构与各模块职责](#4-目录结构与各模块职责)
- [5. 页面与接口清单](#5-页面与接口清单)
- [6. 数据库](#6-数据库)
- [7. 几个关键设计（答辩大概率会问）](#7-几个关键设计答辩大概率会问)
- [8. 相比 Java 版改了什么](#8-相比-java-版改了什么)
- [9. 新增功能详解](#9-新增功能详解)
- [10. 测试脚本](#10-测试脚本)
- [11. 常见问题](#11-常见问题)
- [12. 已知限制](#12-已知限制)
- [**13. 接收方：换一台电脑怎么跑起来**](#13-接收方换一台电脑怎么跑起来) ← 拿到文件夹的人看这节

---

## 1. 这是什么

一个服务端渲染的校园二手交易网站：注册登录、发布/编辑/删除闲置物品、按分类和关键词浏览搜索、
商品详情与评论、私信聊天、关注与粉丝、站内通知、后台管理三个页面，以及一个接 DeepSeek 的
智能导购机器人（对话式找货，回复里带商品卡片）。

**为什么要从 Java 重写成 Python。** 原项目是几周以来在 Java 上一点点堆出来的，功能是全的，
但作者只会 Python —— 一份自己读不懂、讲不出来的代码，功能再全对课程答辩也没有意义。
所以这次重写的目的不是「换个框架玩玩」，而是**得到一份自己能讲明白的代码**。

**Java 版原地保留，一行没动**，作为退路和对照物：

| 版本 | 位置 | 端口 |
|---|---|---|
| Java（原版，参照与退路） | `C:\Users\17360\campus-secondhand` | 8081 |
| Python（本版本） | `C:\Users\17360\Desktop\软件工程\campus-secondhand-python` | 8000 |

两个版本连的是**同一个数据库**，所以同一个 URL 在 8000 和 8081 上可以直接并排对照 ——
重写期间就是这么一页一页核对过来的。

### 规模对照

| 层 | Java 版 | Python 版 |
|---|---|---|
| 后端 | 66 个 `.java` / 6,802 行 + 9 个 MyBatis XML / 1,317 行 | 50 个 `.py` / 6,784 行（含 4 个测试脚本） |
| 模板 | 22 个 Thymeleaf / 4,708 行（948 个 `th:*` 表达式） | 25 个 Jinja2 / 3,205 行 |
| 前端 JS | 7 个自写 / 1,112 行 | 原样搬过来，只加了一个 10 行的 CSRF 补丁 |
| CSS | 2,287 行 | 原样搬过来，另加约 900 行新样式（换肤 + 新功能） |

模板行数少了一千多行，是因为原版**没有任何 extends/layout**，20 个页面各写一份完整的
`<head>` + 顶栏 + 登录弹层；Jinja2 里抽成了一个 `base.html` 加两个外壳，重复的部分只剩一份。

---

## 2. 跑起来

### 2.1 前置条件

| 需要什么 | 版本 | 说明 |
|---|---|---|
| Windows | 10 / 11 | 开发机是 Windows 11 |
| Python | 3.13 | 用 conda 环境隔离，不污染 base |
| MySQL | 8.0 | 本机是 8.0.45 |
| 网络 | 局域网 | 同一个 WiFi 下的手机/别的电脑可以访问 |

> **为什么 Django 钉在 5.2 而不是最新版。**
> Django 6.0 起不再支持 MySQL 8.0（要求 8.4+）。这台机器上的 MySQL 8.0.45 **不能动** ——
> Java 版还指着它跑。所以选了仍然支持 8.0 的 Django 5.2 LTS。

### 2.2 数据库

两件事：**建库**（如果还没有），**建表**。

已有 `squirrel_test` 库就不需要重新建，直接跳到「建表」。注意 Java 版共用这个库，
**不要让这个版本独占它**。

**建表**用 `campus-secondhand-python\sql\db_springboot_squirrel.sql`。这份脚本是按**当前真实库**
逐张 `SHOW CREATE TABLE` 导出来的，十张表一张不落，还带了 8 条分类种子数据。

**建完表之后要灌一份演示数据**，否则网站是空的（没账号可登、没商品可看）：

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" `
    -uroot -p123456 --default-character-set=utf8mb4 `
    -e "source C:/.../campus-secondhand-python/sql/seed_20261008_demo_data.sql"
```

`seed_20261008_demo_data.sql` 里有 2 个账号、14 件商品、14 条图片记录、17 条站内通知，
灌完和导出时那台电脑一模一样。**注意它会先清空那十张表**，只该在空库上用 ——
文件头部有详细说明。

> 只想空着手开始（自己注册、自己发商品）的话，跳过这一步即可。
> 那时要进后台得手动把自己提成管理员：
> `UPDATE t_shop_user SET power = 90 WHERE phone = '你的手机号';`

> 别用 Java 仓库里那份 `sql\db_springboot_squirrel.sql` —— 那是 2018 年原作者用 Navicat 导出的，
> 已经严重过期（缺 `t_shop_follow` 表、缺 `avatar` / `sold` / `wechat` / `font_size` 四列、
> 分类名也对不上）。那份文件保持原样不动，**要建库请用 Python 版这一份**。

如果库已经建好了，只想补上后来加的东西，跑 `sql\migrations\` 下的两个增量脚本：

| 脚本 | 加了什么 |
|---|---|
| `20261008_wechat_and_contact_request.sql` | `t_shop_user.wechat` 列 + `t_shop_contact_request` 表 |
| `20261008_font_size.sql` | `t_shop_user.font_size` 列 |

**跑法（PowerShell，用户终端是 PS 5.1）：**

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" `
    -uroot -p123456 --default-character-set=utf8mb4 squirrel_test `
    -e "source C:/Users/17360/Desktop/软件工程/campus-secondhand-python/sql/migrations/20261008_font_size.sql"
```

或者直接把文件内容粘进 Navicat / Workbench 执行。

### 2.3 Python 环境

```powershell
conda create -n campus2hand python=3.13 -y
conda activate campus2hand
Set-Location 'C:\Users\17360\Desktop\软件工程\campus-secondhand-python'
pip install -r requirements.txt
```

装的是这五个（版本是实际跑通的）：

| 包 | 版本 | 干什么用 |
|---|---|---|
| Django | 5.2.18 | Web 框架 |
| Jinja2 | 3.1.6 | 模板引擎（为什么不用 Django Template 见第 7 节） |
| PyMySQL | 1.2.3 | MySQL 驱动（纯 Python，Windows 上不用装编译器） |
| requests | 2.34.2 | 机器人调 DeepSeek 用 |
| python-dotenv | 1.2.4 | 读 `.env` 里的密钥 |

### 2.4 配置（可选）

复制 `campus-secondhand-python\.env.example` 成 `.env`，把 DeepSeek 的 key 填进去：

```
ROBOT_API_KEY=sk-你的key
```

**不填也能跑** —— 机器人功能会自动关闭（右下角的悬浮入口不显示），其余功能完全不受影响。
`.env` 已经在 `.gitignore` 里，不会被提交。

数据库连接写死在 `config/settings.py` 里（`root` / `123456` / `squirrel_test` / `127.0.0.1:3306`），
换机器的话改那几行。

### 2.5 启动

```powershell
conda activate campus2hand
Set-Location 'C:\Users\17360\Desktop\软件工程\campus-secondhand-python'
python manage.py runserver 0.0.0.0:8000
```

`0.0.0.0` 是为了让局域网里的手机也能访问；只在本机看的话用 `127.0.0.1:8000` 更安全。

访问地址形如 `http://<本机局域网IP>:8000`。**换网络之后 IP 会变**，用 `ipconfig` 查当前地址。

> `.env` 没生效、或者改了代码不生效？`runserver` 默认会自动重载，
> 但用 `--noreload` 起来的进程必须**手动重启**才会读到新代码。
> exe 被锁住（提示文件被占用）时先 `taskkill /F /IM dotnet.exe`，
> 不行就 `Get-Process python | Stop-Process`。

---

## 3. 测试账号

库里现成两个账号，密码都是 `123456`：

| 手机号 | 昵称 | 权限 | 身份 | 名下闲置 |
|---|---|---|---|---|
| `15377671813` | 管理员 | 90 | 管理员，能进后台 | 0 件 |
| `12345678900` | 用户1 | 10 | 普通用户 | 14 件 |

**密码存的是 32 位大写 MD5**（`E10ADC3949BA59ABBE56E057F20F883E` 就是 `123456`），
不是 Django 默认的 `pbkdf2` 格式 —— 这一点很关键，见第 7 节。

想试后台管理，用管理员号登录后访问 `http://localhost:8000/manage/login`。

---

## 4. 目录结构与各模块职责

```
campus-secondhand-python\
├─ manage.py                   Django 命令行入口
├─ requirements.txt            依赖清单
├─ .env.example                配置模板（真 key 放 .env，不进版本库）
├─ sql\
│  ├─ db_springboot_squirrel.sql   完整建库脚本（十张表 + 分类种子数据）
│  ├─ seed_20261008_demo_data.sql  演示数据（2 账号 / 14 商品 / 14 图片 / 17 通知）
│  └─ migrations\                  增量变更脚本（加列 / 加表）
├─ config\                     项目配置
│  ├─ settings.py              双模板引擎、MySQL、24 小时 session、机器人参数
│  ├─ urls.py                  总路由（路径和 Java 版逐字一致）
│  ├─ jinja2.py                给模板注入 url() / static() / csrf_input()
│  └─ __init__.py              把 PyMySQL 注册成 MySQLdb
├─ core\                       公共地基（不属于任何业务域）
│  ├─ constants.py             常量：状态值、权限值、字体档位、上传上限
│  ├─ auth.py                  登录态（session 里那份用户 dict）
│  ├─ decorators.py            权限装饰器：login_required / admin_required / admin_api
│  ├─ context_processors.py    替代原版两个 @ControllerAdvice
│  ├─ http.py                  back()：同源校验过的「跳回来源页」
│  ├─ ajax.py                  AjaxResult 的统一出口（code / success / msg）
│  ├─ uploads.py               图片落盘（商品图 + 头像）
│  ├─ utils.py                 md5_hex() / check_password() / 时间字符串
│  └─ views.py                 404 / 500 页面
├─ accounts\                   账号域：User、Follow
├─ goods\                      商品域：Goods、Catelog、Image、Comments、Reply
├─ chat\                       私信与通知：Message、Notice、ContactRequest
├─ backstage\                  自定义后台三页
├─ robot\                      智能导购（DeepSeek）
├─ templates\                  Jinja2 模板
│  ├─ base.html                最外层（文档结构、标题、机器人悬浮入口）
│  ├─ base_shop.html           商城外壳（首页/搜索/分类/详情/他人资料）
│  ├─ base_user.html           用户中心外壳（个人中心/消息/关注/设置/闲置/对话）
│  ├─ fragments\               复用片段（机器人、已售角标 macro）
│  ├─ goods\ user\ manage\ robot\ error\
├─ static\                     静态资源（原版整体搬过来，CSS 加了新章节）
├─ upload\images\              用户上传的图片（商品图 + 头像）
└─ test_*_e2e.py               四个端到端测试脚本
```

**app 划分的理由：按功能切，答辩时好讲。** 依赖是单向的
`accounts → goods → chat`，没有循环导入。

**为什么叫 `backstage` 不叫 `manage`：** 避开和 `django.contrib.admin` 的命名冲突，
也避免和 URL 前缀 `/manage/` 混在一起分不清哪个是代码、哪个是地址。

---

## 5. 页面与接口清单

路径和 Java 版**逐字一致**，所以两个版本可以并排对照。

### 5.1 商城（前台）

| URL | 方法 | 干什么 |
|---|---|---|
| `/` | GET | 302 跳到 `/goods/homeGoods` |
| `/goods/homeGoods` | GET | 首页。第一节「最新发布」是全站最新 6 件，之后每个分类各 6 件 |
| `/goods/search` | GET | 全站搜索。`?str=关键词&minPrice=&maxPrice=` |
| `/goods/catelog/{id}` | GET | 分类列表，同样支持关键词和价格区间 |
| `/goods/goodsId/{id}` | GET | 商品详情（含评论、卖家信息、关注/联系按钮） |
| `/goods/publishGoods` | GET | 发布页（需登录） |
| `/goods/publishGoodsSubmit` | POST | 发布提交（图片 + 落库 + 用户闲置数 +1，一个事务） |
| `/goods/editGoods/{id}` | GET | 编辑页（**只有货主能打开**，别人一律 404） |
| `/goods/editGoodsSubmit` | POST | 编辑提交 |
| `/goods/deleteGoods/{id}` | POST | 删除自己的商品（带二次确认） |
| `/goods/sold/{id}` | POST | 标记已售出 / 恢复在售 |
| `/goods/state/{id}` | POST | 下架 / 重新上架（**新功能**，见第 9 节） |
| `/goods/uploadFile` | POST | 图片上传（发布页/编辑页用） |
| `/comments/api/addComments` | POST | 发评论（JSON） |
| `/comments/api/updateComments` | POST | 改评论（JSON） |
| `/comments/api/deleteComments/{id}` | POST | 删评论（JSON） |

### 5.2 账号与用户中心

| URL | 方法 | 干什么 |
|---|---|---|
| `/user/login` | POST | 登录 |
| `/user/addUser` | POST | 注册 |
| `/user/logout` | GET | 退出登录 |
| `/user/changeName` | POST | 改昵称 |
| `/user/home` | GET | 个人中心 |
| `/user/basic` | GET | 个人设置：改资料 / 换头像 / **调字体大小** |
| `/user/updateInfo` | POST | 保存昵称和 QQ |
| `/user/allGoods` | GET | 我的闲置（**已下架的商品也列出来**，带灰色角标） |
| `/user/fontSize` | POST | 保存界面字体大小（**新功能**） |
| `/user/avatar/preset` | POST | 用预设头像 |
| `/user/avatar` | POST | 上传自定义头像 |
| `/user/follow` | GET | 关注列表（`?tab=following` 我关注的 / `?tab=fans` 关注我的） |
| `/user/follow/{id}` | POST | 关注 |
| `/user/unfollow/{id}` | POST | 取消关注 |
| `/user/profile/{id}` | GET | 他人资料页（**允许未登录访问**） |
| `/user/notice` | GET | 老地址，转发到 `/user/message` |

### 5.3 私信与通知

| URL | 方法 | 干什么 |
|---|---|---|
| `/user/message` | GET | 消息中心（`?tab=notice` 系统通知，默认 / `?tab=chat` 私信会话） |
| `/user/notice/read/{id}` | POST | 单条通知标已读 |
| `/user/notice/readAll` | POST | 全部通知标已读 |
| `/user/chat/{id}` | GET | 和某个人的对话页 |
| `/user/chat/{id}` | POST | 发一条私信 |
| `/user/contact/request/{id}` | POST | 请求交换联系方式（**新功能**） |
| `/user/contact/agree/{id}` | POST | 同意交换 |
| `/user/contact/refuse/{id}` | POST | 拒绝交换 |
| `/user/contact/revoke/{id}` | POST | 撤销已达成的交换 |

### 5.4 后台管理

三个页面都是**自定义模板**（照搬原版），没有用 `django.contrib.admin`。
只有 `power = 90` 的账号进得去，**非管理员访问返回 404 页面而不是 403** ——
不告诉对方「这里有个后台，只是你没权限」。

| URL | 方法 | 干什么 |
|---|---|---|
| `/manage/login` | GET | 控制台登录页 |
| `/manage/user/list` | GET | 用户管理 |
| `/manage/goods/list` | GET | 商品管理 |
| `/user/api/login` | POST | 控制台登录（JSON） |
| `/user/api/addUser` | POST | 后台添加用户（JSON） |
| `/user/api/updateUser` | POST | 后台改用户（JSON） |
| `/user/api/deleteUser/{id}` | POST | 删除用户（JSON） |
| `/user/api/freezeUser/{id}` | POST | 冻结用户（JSON） |
| `/user/api/unfreezeUser/{id}` | POST | 解冻用户（JSON） |
| `/goods/api/updateGoods` | POST | 后台改商品（JSON） |
| `/goods/api/offGoods/{id}` | DELETE | 后台删商品（JSON，硬删） |

### 5.5 机器人

| URL | 方法 | 干什么 |
|---|---|---|
| `/robot` | GET | 机器人对话页（要 `ROBOT_API_KEY`，没配就入口都不显示） |
| `/robot/send` | POST | 发一句，拿回复 + 商品卡片（JSON） |
| `/robot/clear` | POST | 清空本轮对话历史（JSON） |

> `/robot` 后面**故意不加斜杠**，和原版一致；写成 `/robot/` 会被 Django 的
> `CommonMiddleware` 用 301 跳走，两边地址就对不上了。

---

## 6. 数据库

库名 `squirrel_test`，共 **10 张表**：

| 表 | 对应 model | 说明 |
|---|---|---|
| `t_shop_user` | `accounts.User` | 用户。密码是 32 位大写 MD5 |
| `t_shop_follow` | `accounts.Follow` | 关注关系，唯一键 `uk_user_follow` |
| `t_shop_catelog` | `goods.Catelog` | 分类，`number` 是各类目下的商品数 |
| `t_shop_goods` | `goods.Goods` | 商品。`state` 和 `sold` 是**两个不同语义的列**（见下） |
| `t_shop_image` | `goods.Image` | 商品图片，一件可以多张 |
| `t_shop_comments` | `goods.Comments` | 评论，`atuser_id != 0` 表示回复某人 |
| `t_shop_reply` | `goods.Reply` | 原项目的死表，只建了 model 没做业务 |
| `t_shop_message` | `chat.Message` | 私信，`status` 是收件人视角的已读标记 |
| `t_shop_notice` | `chat.Notice` | 站内通知，`status` 列**没有默认值**，插入必须显式给 0 |
| `t_shop_contact_request` | `chat.ContactRequest` | **新表**，联系方式交换请求 |

### 三个必须知道的约定

**① 所有 model 都是 `managed = False`，永远不用 migration。**

Django 的迁移会想接管表结构，而这些表的真实所有权在 SQL 脚本和既有的 Java 版手里。
所以每个 model 都写了 `db_table`，schema 变更一律走 `sql/migrations/` 下**手写并手工执行**的脚本。

**② 9 张原表之间没有任何外键约束。**

跨表引用全靠应用层（`goods.user_id`、`message.from_user_id` 这些列只是普通整数）。
加外键的话，删用户/删商品要先做级联清理，而原版那些删除路径都没做 —— 会当场炸掉。
所以新加的表也**不设外键**，保持同一套规矩。

**③ 所有日期时间都是 `varchar`，不是 `DateTimeField`。**

`create_at`、`polish_time`、`start_time` 存的是 `'2026-09-20'` 这样的字符串。
用 `DateTimeField` 会和现有数据对不上，排序也会变。

### `state` 和 `sold` 是两回事

| 列 | 取值 | 含义 | 效果 |
|---|---|---|---|
| `sold` | 0 在售 / 1 已售出 | 卖掉了没有 | 只加个角标，商品**照样挂在列表里**，禁用联系与评论 |
| `state` | 0 进行中 / 1 已下架 / 2 审核中 | 有没有收起来 | **前台查不到**（首页/分类/搜索/详情都没有），后台和「我的闲置」还看得见 |

前台所有查询统一走 `goods/models.py: FRONT_VISIBLE`（就是 `Q(state=0)`），
后台和「我的闲置」**刻意不带**这个条件。

---

## 7. 几个关键设计（答辩大概率会问）

### 7.1 为什么模板引擎用 Jinja2，不用 Django Template

原版有 **948 个 `th:*` 表达式**，里面大量是 SpEL 风格的写法：三元 `? :`、带参方法调用
（`${commentCounts.get(x)}`）、`th:with` 局部变量、字符串拼接。

Django Template **刻意做得受限**（不能调带参方法），上面这些全部得在 view 里预先算好 ——
等于把逻辑从模板搬进 view，模板反而更难读。Jinja2 的表达式就是 Python 的子集，
转换基本是语法替换：

| 原版（Thymeleaf） | 现在（Jinja2） |
|---|---|
| `${following.size()}` | `{{ following \| length }}` |
| `${commentCounts.get(x)}` | `{{ commentCounts.get(x) }}` |
| `${followingIds.contains(u.id)}` | `{{ u.id in followingIds }}` |
| `th:if="${a} ? ' is-sold' : ''"` | `{{ ' is-sold' if a else '' }}` |
| `@{'/goods/goodsId/'+${id}}` | `{{ url('goods_detail', id=...) }}` |
| `th:inline="javascript"` | `\|tojson` |
| `th:each="item,st : ..."` + `${st.index}` | `{% for item in ... %}` + `loop.index0` |

Django 原生支持多模板引擎并存，后台页面是自定义模板、不用 admin，所以**没有冲突**。

### 7.2 为什么不用 `django.contrib.auth`

**因为库里的密码是大写 MD5，`django.contrib.auth` 认的是 `pbkdf2_sha256$...`，会一个都登不上。**

而且现有的两个账号是原版建的，密码哈希不能换 —— 换了 Java 版就登不进去了。
所以自己写了 `core/auth.py`，`md5_hex()` 算一遍大写 MD5 跟库里比。

登录状态存在 `request.session['cur_user']` 里，存的是一个 **dict**（不是 model 实例），
键名照抄原版 Java 的属性名（含 `avatarUrl` 这个计算属性），模板里 `cur_user.xxx` 能一一对应。

> **一个必须记住的坑：session 是签名 cookie，整份都存在浏览器那 4KB 里。
> 就地改嵌套结构（比如 `ids.append(x)`）Django 检测不到，写不回去。**
> 所以 `core/auth.refresh(request, **changes)` 是**整个 dict 重新赋值**的，
> 改字体大小的那个「本次登录能看谁的联系方式」名单也是整个 list 重新赋值。
> 不这么做，表现就是「点了同意，刷新一下又看不见了」。

### 7.3 为什么不用 Django 的 migration

见 6.①。补充一条实际原因：Java 版同时连着这个库，schema 变更必须是**两边都能接受的纯增量**
（加列、加表，不改既有列、不动数据），手写 SQL 脚本能一眼看清改了哪几个字，
自动生成的 migration 反而看不清。

### 7.4 CSRF 打开了（原版完全没有）

原版没有任何 CSRF 防护。这个版本开了，模板里的表单都带 `{{ csrf_input }}`；
纯 AJAX 的页面（详情页的评论、后台三页）额外引一个 10 行的 `static/js/csrf.js`，
它从 `csrftoken` 这个 cookie 里读 token 塞进请求头。

**有个反直觉的地方：Django 是「渲染到 `csrf_token` 时才把 cookie 发给浏览器」的。**
详情页有个分支（登录着看别人一件已售出的商品）页面上一个表单都不渲染，
cookie 就不下发，评论区的 AJAX 会被 CSRF 拦掉。所以详情页模板里放了一行
`var csrfToken = "{{ csrf_token }}";` —— 看着没用到，但不能删。

### 7.5 权限收在一处

原版把「有没有登录」「是不是管理员」散在每个 Controller 方法里判断，漏掉了好几处
（见第 8 节）。这个版本收成装饰器 `core/decorators.py`：

| 装饰器 | 未登录 | 登录了但不是管理员 |
|---|---|---|
| `login_required` | 302 跳首页 | 放行 |
| `admin_required` | 渲染 404 页（状态码 404） | 渲染 404 页 |
| `admin_api` | 返回 `code=3009`（JSON） | 返回 `code=3009` |
| `ajax_login_required` | 返回 `code=3010`（JSON） | 放行 |

**`admin_api` 对「未登录」和「登录了但没权限」返回同一个错误码，是有意的** ——
不让对方从错误码的差别里推断出「这里有个后台接口，只是我权限不够」。

---

## 8. 相比 Java 版改了什么

重写过程中发现的问题分两类：**修掉的缺陷**（原版就是错的）和**新增的功能**。
下面逐条列清楚，答辩时可以直接对着讲。

### 8.1 修掉的安全缺陷

| # | 原版的问题 | 现在怎么做 |
|---|---|---|
| 1 | **删商品没有属主校验** —— 任何登录用户改一下 URL 里的 id 就能删别人的货 | 删除时 WHERE 里带 `user_id` |
| 2 | **编辑商品会把别人的货「过户」给自己** —— 提交时有一句 `goods.setUserId(cur_user.getId())` | 编辑页打开就校验货主，不是自己的一律 404；提交时 UPDATE **不碰 `user_id`** |
| 3 | **评论的增 / 改 / 删三个接口任何人可操作** | 三个接口都加了登录 + 属主校验 |
| 4 | **后台 `/user/api/delete|freeze|unfreezeUser` 完全没检查 power** —— 任何登录用户都能删号、冻结别人 | 后台 7 个 JSON 接口全部挂 `admin_api` |
| 5 | **删商品、发布商品跨 5 步写库，没有事务** —— 中途失败会留下脏数据 | 包 `transaction.atomic()` |
| 6 | **删商品是 GET 链接** —— 浏览器预取、爬虫、甚至鼠标悬停预加载都能触发 | 改成 POST 表单 + 二次确认 |
| 7 | **用户管理页把密码的 MD5 直接输出在 HTML 里** | 不再输出 |

第 1 条最值得讲：这是**水平越权**，攻击成本只是改个数字。

### 8.2 修掉的功能缺陷

| # | 原版的问题 | 现在怎么做 |
|---|---|---|
| 8 | **「下架」是假的** —— 用户侧那个按钮指向 `/goods/offGoods`，方法体只有一句 `return null`；而且 `state` 列在任何 SELECT 里都不过滤 | 真改 `state`，前台查询统一加 `state=0`。见第 9 节 |
| 9 | **搜索页「只填关键词」会 500** —— `GoodsMapper.xml` 的 `<if>` 括号跨标签不配对 | 用 Django 的 `Q()` 组合，天然没这个问题 |
| 10 | **`getUsersByIds` 传空集会退化成查全表** | Django 的 `id__in=[]` 天然返回空集 |
| 11 | **「我的闲置」的评论数是假的** —— 取 `t_shop_goods.commet_num`，而这一列全库都是 NULL，连数字都不显示 | 改成一次 `GROUP BY` 查真实评论数 |
| 12 | **首页第一节和第二节重复** —— 模板第一节标题写「最新发布」，数据却是分类 1，和第二节「闲置数码」一模一样 | 第一节改成真正的全站最新 |
| 13 | **「擦亮」按钮是个空链接** `href=""`，点了只会滚回顶部 | 删掉 |
| 14 | **登录失败是静默的** —— 点了没反应，用户分不清是没注册还是密码错 | 回来源页并提示「该手机号还没有注册 / 密码不正确 / 该账号已被冻结」 |
| 15 | **后台「品类」下拉框少一个「全部」** —— 页面一打开列着全部商品、下拉框却显示成第一个分类 | 补一个 `<option value="0">全部</option>` |
| 16 | **后台控制台登录页把 toastr 当样式表引** —— `<link rel="stylesheet" href="toastr.min.js">`，脚本根本没执行 | 改回 `<script src>` |
| 17 | **`index.bundle.js`（5 万行 webpack 遗留）+ 4 个页面里未启动的 `ng-*` 属性** | 直接删掉 |

### 8.3 顺手补上的

| # | 问题 | 现在怎么做 |
|---|---|---|
| 18 | **`/img/**` 会 404** —— 原版 Spring Boot 自动把 `classpath:/static/**` 映射到根路径，Django 只认 `/static/`。而头像为空时回落到 `/img/photo.jpg`，导致全站头像都是裂图 | `config/urls.py` 里把 `/img/` 单独接到 `static/img/` |
| 19 | **`GET /user/notice` 老地址** | 转发到 `/user/message`，老链接不至于 404 |
| 20 | **改商品分类时，两边的分类计数不跟着动** | 换分类时在一个事务里把两个计数对着调 |

### 8.4 新增的功能

| # | 功能 | 见第几节 |
|---|---|---|
| 21 | **下架 / 重新上架**（真功能，不是空壳） | 9.1 |
| 22 | **联系方式交换**（手机号 / QQ / 微信，双方都同意才互见） | 9.2 |
| 23 | **各处操作加二次确认框** | 9.3 |
| 24 | **用户中心「返回首页」按钮** | 9.4 |
| 25 | **界面字体大小可调**（四档，跟着账号走） | 9.5 |

### 8.5 一处**偏离原计划**的地方（要说明）

做联系方式交换时，原计划写的是「在对话流里插一条系统提示」，
**实际做成了只往 `t_shop_notice` 推一条站内通知**（消息中心的红点会亮），
没有往 `t_shop_message` 里插伪造的会话气泡。

理由：对话页顶上那条常驻的状态栏已经显示了当前状态（「等待对方同意」「已交换」等），
再插一条假消息是重复的；而且 `t_shop_message` 是**纯私信**表，
往里塞系统消息会把那张表的语义搞脏 —— 会话列表、未读数、已读标记全都得跟着特殊处理。

代价是：用户在对话页看不到「某年某月我请求过」这样的历史痕迹，
只有当前状态。**这一点如实记在这里，不藏着。**

### 8.6 第二轮修复（2026-10-11，代码复审后）

| # | 问题 | 修法 |
|---|---|---|
| 26 | **卖家账号被删后商品详情页整页 500** —— 表间没有外键约束，删用户不连带删商品，`seller` 查出 None 后模板直接 `seller.id` | 详情页卖家信息区加 `{% if seller %}` 分支，显示「卖家已注销」 |
| 27 | **后台登录接口 `/user/api/login` 不校验冻结状态** —— 被冻结的账号能从后台入口拿到登录会话 | 和前台 `login_view` 同一口径，补 `status` 检查 |
| 28 | **冻结 / 降级对已登录用户不生效** —— session 是登录时的快照，最长 24 小时内照旧能用 | `core.auth.current()` 每次回库核对 `power` / `status`（只查两列）：被冻结或账号被删立即使 session 失效，power 变了就地同步 |
| 29 | **后台编辑商品选了 id=8 的分类永远保存不了** —— 校验用硬编码的 `{1-7}`，下拉却来自数据库 `status=1` 的分类 | 校验改成和下拉同一口径，查 `Catelog` 表 |
| 30 | **用户侧编辑商品换分类不同步分类计数** —— 发布 +1、删除 -1、后台编辑同步调，唯独这条路径不管，导航数字会漂移 | `edit_submit` 换分类时在一个事务里把两边计数对着调 |
| 31 | **后台修改用户手机号不查重** —— 手机号是唯一登录凭据，改出重复后登录结果不可预期 | 和注册同一口径先查重（排除自己），重复返回「该电话号码已经注册过了」 |
| 32 | **关注列表直接列出对方手机号** —— 联系方式交换机制（9.2）等于白做 | 关注 / 粉丝两栏都不再显示手机号 |
| 33 | **可以关注不存在的用户**，留下孤儿关注和通知 | `follow_add` 先查目标用户存在 |
| 34 | **已下架商品仍能通过接口加评论** —— 详情页对别人 404，但手搓 POST 能绕过 | `comments_add` 补 `state` 检查（货主自己不受限） |
| 35 | **注册不校验空值** —— 空手机号 / 空用户名 / 空密码都能建号 | `_register` 入口统一拦截 |
| 36 | **图片上传不校验内容** —— 扩展名和 Content-Type 都能伪造 | 加文件头魔数校验（JPEG/PNG/GIF/BMP/WebP），不引新依赖 |

---

## 9. 新增功能详解

### 9.1 下架 / 重新上架

原版页面上确实有「下架」这两个字，但背后是空的（见 8.2 第 8 条）。现在：

- 用户侧（「我的闲置」和商品详情页）：「下架」→ `state=1`，「重新上架」→ `state=0`
- **前台所有列表/搜索/详情统一加 `state=0` 过滤** —— 这是让下架有意义的前提，
  下架后商品从首页、分类页、搜索里消失，别人打开详情页直接 404
- **但货主自己看得见**：「我的闲置」里照常列出来（灰色「已下架」角标），
  自己的资料页也照常显示，详情页也打得开 —— 否则用户下架完就找不回来了
- **后台管理不过滤 `state`**（管理员要看得到全部）；后台那个也叫「下架」的按钮
  保持原版行为（硬删），只把文案改成「删除」并加了确认

`sold` 和 `state` 互不影响：可以「已售出」但没下架，也可以下架了但没卖出去。

### 9.2 联系方式交换（本版本工作量最大的新功能）

**需求：** 私信里聊得来才交换手机号 / QQ / 微信；只在对话页显示；下次登录必须重新请求；
有同意也有拒绝；同意后任一方可以撤销。

**数据变更：**

- `t_shop_user` 加一列 `wechat`（原库只有手机号和 QQ）
- 新建 `t_shop_contact_request` 表，存「谁向谁请求过、是什么状态」，
  唯一键 `uk_from_to` 是**有向的**（(A,B) 和 (B,A) 是两行）

**核心逻辑只有两句：**

```python
# 必须同时满足，缺一不可：
#   ① 本次登录里我亲手点过「请求」或「同意」   → 存在 session 的 contact_ok 列表里
#   ② 库里当前是「已同意」                      → ContactRequest.status == 1
```

- **条件① 存在 session**，不落库 —— 关掉浏览器重新登录，这个名单就是空的，
  必须重新请求。这就实现了「下次登录必须重新请求」。
  库里那条 `status=1` 一直在，所以点一下「重新查看」立刻又能看见，不用再等对方。
- **条件② 落库** —— 撤销时只要把 `status` 改掉，**两边的条件②同时失效**，
  当场互相看不见。不用（也做不到）去动别人浏览器里的 session。

**七种状态**（`chat/services.py: contact_state()` 算出来，模板只负责按状态选文案）：

| 状态 | 什么时候 | 页面显示 |
|---|---|---|
| `none` | 还没互相聊过 | 整块不渲染 |
| `ask` | 双方都发过言了 | 「请求交换信息」按钮 |
| `waiting` | 我请求了，等对方 | 「等待对方同意」 |
| `reply` | 对方请求了，等我 | 「同意」「拒绝」两个按钮 |
| `visible` | 已交换 | 手机号 / QQ / 微信 |
| `refused` | 我请求过被拒了 | 「再请求一次」 |
| `regain` | 以前交换过，但这次登录还没确认 | 「重新查看联系方式」 |

**隐私是怎么守住的：** 手机号 / QQ / 微信**是在 `contact_state()` 这个函数里才从库里取出来的**，
没到「已交换」时返回的 dict 里那三个键是空字符串。别的地方（商品详情、他人资料页、
消息中心）拿到的用户 dict 里根本没有这三个键 ——
从源头上就没有「模板少写一个 `if` 就漏出去」的机会。

> 补一句免得误会：商品详情页的「卖家信息」栏本来就显示卖家的手机号和 QQ、
> 他人资料页本来就显示 QQ，**那是原版就有的，重写时照搬了，没有动**。
> 这里收口的是**新加的微信**和「已交换」这个状态。

### 9.3 二次确认框

用浏览器原生 `confirm()`，不引任何弹窗库：

- **要确认**（会改变别人看得见的状态）：下架、删除商品、删除评论、撤销交换、拒绝交换、
  后台的删除用户 / 冻结 / 删除商品
- **不确认**（方向是安全的）：重新上架、恢复在售、取消关注、同意交换

判断标准就一条：**这一步会让别人看到的东西变少、或者数据没法恢复，就问一句。**

### 9.4 用户中心「返回首页」按钮

点顶栏右上角的用户名进到个人中心之后，原版唯一能回商城的入口是顶栏左边一个 logo、
加右边一个圆形图标（背景图还是挂在作者自己的阿里云 OSS 上、写的是 http）。
两个都不像「返回」。

现在在用户中心那套外壳（`base_user.html`）的顶栏加了一个写明字的「返回首页」按钮，
**一次覆盖 9 个页面**：个人中心、我的消息、关注列表、个人设置、我的闲置、对话页、
发布物品、编辑物品、机器人对话页。

（严格说是 9 个**模板**继承了这套外壳。机器人那页要配了 `ROBOT_API_KEY` 才打得开，
不配 key 时日常见得到的是 8 个。）

指向 `/goods/homeGoods`，用的是 `<a>` 不是 `history.back()` —— 从收藏夹直接打开这一页时
「上一页」是空的；而且用户说「返回」的意思是回商城，不是回浏览器上一页。

> **他人资料页 `/user/profile/{id}` 没有这个按钮** —— 它用的是商城外壳
> （原版就是这样，从商品页点头像去看别人的资料，不该掉进自己的用户中心），
> 那套外壳本来就有完整的顶部导航。

### 9.5 界面字体大小

在「个人设置」页选，四个档位：**小 90% / 标准 100% / 大 110% / 特大 120%**。

- **实现方式**：`base.html` 上写一个 `<html data-fs="...">` 属性，
  缩放规则全在 `campus.css` 第 30 节（CSS `zoom`），模板里一行判断都没有。
  以后想调档位（比如「大」改成 115%），**只改 CSS 一行，不用动数据库**
  —— 库里存的是短码 `s` / `m` / `l` / `xl`，不是百分比数字。
- **为什么用 `zoom` 而不是改 `font-size`**：这个站点的样式是原版照搬的两千多行，
  字号全是写死的 px。改 `html` 的 `font-size` 对它们一点用都没有，得逐个类去覆盖，
  覆盖面靠人肉列清单，总有漏掉的角落。`zoom` 是整体缩放，文字、图片、按钮、间距一起变，
  不用挑，也就不会漏。
- **存哪儿**：`t_shop_user.font_size` 列。**跟着账号走** —— 换浏览器、换电脑、
  重新登录都记得（测试里专门用全新会话重新登录验证过）。
- **生效范围**：前台 + 用户中心。后台三页不继承 `base.html`，天然吃不到这个属性。
- **顺手加的**：设置页上选一档会**当场预览**（改属性，不写库），
  行末提示变成橙色的「预览中，还没保存」。不然得在「保存 → 看效果 → 不合适 → 再改」
  里来回好几趟。

---

## 10. 测试脚本

四个端到端脚本，**都是真发 HTTP 请求打真实服务**，不是单元测试。
跑之前**先把服务起来**，另外建议先备份数据库（脚本会写库，但都会还原）。

```powershell
conda activate campus2hand
Set-Location 'C:\Users\17360\Desktop\软件工程\campus-secondhand-python'

python test_manage_e2e.py        # 后台三页 + 7 个 JSON 接口的权限与行为
python test_p7_e2e.py            # 下架/重新上架 + 联系方式交换全流程
python test_usercenter_e2e.py    # 返回首页按钮 + 界面字体大小
python test_robot_e2e.py         # 机器人（需要 ROBOT_API_KEY）
```

| 脚本 | 项目数 | 覆盖什么 |
|---|---|---|
| `test_manage_e2e.py` | 91 | 三种身份进后台的结果、页面关键 DOM、页面源码里**不含密码哈希**、7 个接口的权限闸、CSRF 真的在查、后台改商品只改该改的列、后台删商品连图片和两处计数一起处理干净 |
| `test_p7_e2e.py` | 68 | 下架后从首页/分类/搜索消失、非货主 404、货主仍可见；交换七种状态、重新登录失效、撤销当场生效、越权改不动任何东西 |
| `test_usercenter_e2e.py` | 81 | 按钮在 8 个页面上的存在性与指向、匿名被踢回首页；四档渲染、保存后库里/session/前台三处同时生效、重新登录仍记得、非法值和未登录都不写库 |
| `test_robot_e2e.py` | 7 组用例 | 登录 → 提问 → 解析页面上的气泡和商品卡片 |

**这几个脚本有个共同的设计：跑完一定把库还原成跑之前的样子。**
下架测试借真实商品来回切 `state`，结束时改回原值；交换测试按 id 水位线删掉新增的私信和通知，
交换请求按开跑前的快照重建。**跑完测试库应该是干净的**，如果发现数据对不上，说明脚本有 bug。

---

## 11. 常见问题

**Q：启动报 `No module named 'MySQLdb'`。**
A：`pip install -r requirements.txt` 没跑，或者跑在了别的环境里。
PyMySQL 是通过 `config/__init__.py` 里的 `install_as_MySQLdb()` 注册成 MySQLdb 的。

**Q：登录一直提示「密码不正确」，但密码明明是对的。**
A：检查库里存的密码是不是**大写** MD5。`md5_hex()` 算出来会转大写再比。
另外确认连的是 `squirrel_test` 库、不是别的库。

**Q：改了代码但页面上没变化。**
A：`runserver` 用 `--noreload` 起来的话必须手动重启。
CSS/JS 改了还要**顶一下版本号**（模板里 `campus.css?v=2026xxxx`），否则浏览器吃缓存。

**Q：页面上头像都是裂图。**
A：`/img/**` 那条路径映射没了。检查 `config/urls.py` 里那个 `re_path(r"^img/...")`。

**Q：手机连不上电脑的服务。**
A：① `runserver` 要绑 `0.0.0.0:8000` 不是 `127.0.0.1`；
② 手机和电脑要连同一个 WiFi；③ Windows 防火墙可能拦了 8000 端口，放行一下。

**Q：`ALLOWED_HOSTS` 要不要改？**
A：现在是 `["*"]`，局域网访问不用改。真要对外发布的话得收紧，并把 `DEBUG` 关掉。

**Q：右下角没有机器人入口。**
A：`.env` 没配 `ROBOT_API_KEY`。这是**故意的** —— 没配就整个功能关掉，
不显示一个点了没反应的入口（判断条件收在 `robot/services.py: available()` 一处）。

**Q：为什么有些注释写着「原版是……」「重写时……」。**
A：那是在标注**和 Java 版的差异**。答辩时那些注释就是讲稿 ——
每一处偏离都写了为什么偏离，每一处照搬都写了为什么照搬。
一共 6,784 行 Python 里有相当一部分是这个。

---

## 12. 已知限制

诚实列一下**没做的事**和**做不到的事**：

1. **`t_shop_reply` 是死表。** 只建了 model，没实现任何业务 ——
   原版也是这样，模板里没有任何地方用它。可以理解为历史遗留。
2. **`t_shop_catelog` 里 id=8 那个「全部」是空壳**（`number=0`、`status=1`），
   是早期留下的，不是真的分类。前台用的是 `goods/views.py: SECTIONS` 里那份硬编码的
   7 个分类，后台下拉框走 `t_catelog`。所以后台的下拉框里会出现**两个「全部」**
   （新补的那个和这个空壳），名字撞了但含义不同 —— 这是个已知的小瑕疵。
3. **`DEBUG = True`、`ALLOWED_HOSTS = ["*"]`、数据库密码明文写在 `settings.py` 里。**
   课程项目、局域网内跑没问题，**真要放到公网上必须先改这三样**。
4. **`zoom` 不是所有浏览器都一样。** Chromium 系（Chrome / Edge）和 Firefox 126+
   都没问题；特别老的浏览器上「大 / 特大」档可能没效果（功能不受影响，只是字不变大）。
5. **「特大」档在小屏上会出现横向滚动条。** 这个站点的布局是固定 1150px 宽，
   ×1.2 就是 1380px，1366×768 的笔记本放不下。这是选「整体等比缩放」时就说好的代价
   —— 要的就是字更大，页面宽出去是必然的。
6. **机器人对话每轮都要调一次外部 API，有延迟也有费用。**
   历史记录存在 Django cache 里（4 小时过期），重启服务就没了。
7. **没有做单元测试。** 四个脚本都是端到端黑盒测试（真发 HTTP 请求）。
   对课程项目来说够用，但严格的工程实践应该还有一层针对 service 层的单元测试。

---

## 13. 接收方：换一台电脑怎么跑起来

> **这一节是给拿到这个文件夹的人写的。** 从一台什么都没装的电脑开始。
> **照 13.2 → 13.8 的顺序做**就行（13.1 是先看一下手里有什么，13.9 是出错了再翻）。
> 前面 1–12 节讲的是这个项目本身（设计、接口、改了什么），光跑起来不需要看。
>
> 全程大约 **20–30 分钟**，其中大半是等 MySQL 安装。

### 13.1 先确认手里有什么

| 你需要的 | 说明 |
|---|---|
| `campus-secondhand-python\` **整个文件夹** | 必须整份拷贝。**尤其别漏 `upload\images\`** |
| MySQL **8.0** | 没装的话先装。安装时会让你设 root 密码，**记住它** |
| Python **3.13** | conda 或 python.org 的安装包都行 |
| 一个浏览器 | Chrome / Edge / Firefox 都可以 |

**立刻检查一下图片在不在：** 打开 `campus-secondhand-python\upload\images\`，
应该看到 **48 个 `.jpg` 文件**（文件名是一长串字母数字加横杠，比如
`58521ba2-4eb7-4ddc-9226-36b8472efed2.jpg`）。

这 48 个里**只有 14 个是当前那 14 件商品在用的**，其余 34 个是历次测试上传留下的孤儿文件。
**这个目录整个原样拷过来就对了，别挑别删。**

**少了一大半就说明拷漏了** —— 网站照样能跑，但对应的商品会是裂图。

> 这个文件夹里**没有** Java 版的东西，也**不需要**装 Java 或 SpringBoot。
> Java 版是原项目的留档，在另一台电脑上，跟这里无关。

### 13.2 建 Python 环境

**有 conda：**

```powershell
conda create -n campus2hand python=3.13 -y
conda activate campus2hand
```

**没有 conda（用 python.org 的官方安装包）：**

装 3.13，安装界面勾上 **Add python.exe to PATH**。装完开个新的 PowerShell 窗口验证：

```powershell
python --version
```

显示 `Python 3.13.x` 就行，不用再建虚拟环境。

### 13.3 建库 + 灌数据（两步，别跳）

数据库分两个脚本：**先建十张空表，再灌演示数据**。

```powershell
# 把这两个变量改成你自己电脑上的真实路径
$SQL   = 'C:\你解压到的位置\campus-secondhand-python\sql'
$MYSQL = 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe'

# 第 1 步：建库 + 建十张空表
& $MYSQL -uroot -p你的密码 --default-character-set=utf8mb4 -e "source $SQL/db_springboot_squirrel.sql"

# 第 2 步：灌演示数据（2 个账号、14 件商品、17 条通知）
& $MYSQL -uroot -p你的密码 --default-character-set=utf8mb4 -e "source $SQL/seed_20261008_demo_data.sql"
```

三处要注意：

- `-p你的密码` **中间不能有空格**。密码是 `123456` 就写 `-p123456`。
- `source` 后面用**正斜杠** `/`，不要用反斜杠。
- 执行时提示 `Using a password on the command line interface can be insecure`
  **不是错误**，是 MySQL 的例行提醒，忽略它。

**跑完自己核对一下：**

```powershell
& $MYSQL -uroot -p你的密码 --default-character-set=utf8mb4 squirrel_test -e "SELECT COUNT(*) FROM t_shop_user; SELECT COUNT(*) FROM t_shop_goods;"
```

应该是 **2** 和 **14**。不是的话看 [13.9](#139-卡住了看这里)。

> 不习惯命令行的话，把这两个 `.sql` 文件在 Navicat / Workbench 里**按顺序**打开执行也一样，
> 顺序不能反 —— 数据脚本是往表里插，表还没建就会报错。

### 13.4 如果你的 MySQL 密码不是 123456

改 `campus-secondhand-python\config\settings.py` 里这几行（大约第 93–97 行）：

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "squirrel_test",     # 不用改
        "USER": "root",              # 按你的改
        "PASSWORD": "123456",        # ← 主要改这一行
        "HOST": "127.0.0.1",         # 不用改
        "PORT": "3306",              # 不用改
        ...
```

**用的是默认的 `root` / `123456` 就什么都不用动。**

### 13.5 装依赖

```powershell
conda activate campus2hand
Set-Location 'C:\你解压到的位置\campus-secondhand-python'
pip install -r requirements.txt
```

装 5 个包，大约 1–2 分钟。装完最后一行会显示 `Successfully installed Django-5.2.18 ...`。

> 没用 conda 的话，把第一行 `conda activate campus2hand` **去掉**，直接跑后两行。

> 这五个包的版本是**钉死的**，不要 `pip install -U` 升级 ——
> `requirements.txt` 头部写了为什么 Django 必须是 5.2 而不是 6.x
> （6.x 不支持 MySQL 8.0）。

### 13.6 启动服务

```powershell
conda activate campus2hand
Set-Location 'C:\你解压到的位置\campus-secondhand-python'
python manage.py runserver 0.0.0.0:8000
```

看到这几行就是起来了，**这个窗口不要关**：

```
Starting development server at http://0.0.0.0:8000/
Quit the server with CTRL-BREAK.
```

本机访问：直接开 `http://127.0.0.1:8000`

**想让同一个 WiFi 下的手机也能访问：** 另开一个 PowerShell 窗口：

```powershell
ipconfig
```

找 **IPv4 地址**（形如 `192.168.x.x` 或 `10.x.x.x`），那么局域网地址就是：

```
http://那个IP:8000
```

> 第一次手机连不上，八成是 **Windows 防火墙拦了 8000 端口**。
> 弹窗问「是否允许 Python 访问网络」时选**允许**（专用网络勾上）。
> 已经点过「取消」的话，去「Windows 安全中心 → 防火墙和网络保护 → 允许应用通过防火墙」
> 里把 Python 勾上。

### 13.7 第一次进来，应该看到什么

打开 `http://127.0.0.1:8000`，对着这张表核一遍 —— 都对上就说明装好了：

| 看哪儿 | 应该是什么 |
|---|---|
| 首页 | **左侧**一条分类导航：首页 / 最新发布 / 闲置数码 / 校园代步 / 电器日用 / 图书教材 / 美妆衣物 / 运动棋牌 / 周边其他 |
| 首页正文 | 顶部一节「最新发布」，往下每个分类一节；**全站一共 14 件商品** |
| 商品图片 | 每件商品都有图，**没有裂图** |
| 登录 | 手机号 `15377671813`，密码 `123456` → 登录成功 |
| 后台 | 用上面那个号登录后访问 `/manage/login` → 能进用户管理页，看到 2 个账号 |
| 普通用户 | 退出，用 `12345678900` / `123456` 登录 → 「我的闲置」里有 14 件 |
| 搜索 | 首页搜索框输入「自行车」→ 有结果 |
| 站内通知 | 登录后「我的消息」上有未读红点 |

> 那个未读红点来自数据脚本里的 17 条站内通知，**属正常现象**，不是出错。

### 13.8 智能导购机器人（可选，不装不影响其他功能）

首页右下角那个机器人入口，**默认是关着的** —— 它要一个 DeepSeek 的 API key，
这种密钥不能随文件夹一起给（会泄露、也要花钱）。想要就自己申请一个：

```powershell
Set-Location 'C:\你解压到的位置\campus-secondhand-python'
Copy-Item .env.example .env
notepad .env
```

把 `ROBOT_API_KEY=` 后面填上你自己的 key，保存，**重启服务**（Ctrl+C 停掉再跑一次 13.6）。

不填的话，机器人入口**整个不显示**，其余功能一点不受影响。

### 13.9 卡住了看这里

| 现象 | 原因 | 怎么办 |
|---|---|---|
| `No module named 'MySQLdb'` | 依赖没装，或装到别的环境去了 | 确认 `conda activate campus2hand` 之后再 `pip install -r requirements.txt` |
| `Access denied for user 'root'@'localhost'` | 数据库密码不对 | 照 [13.4](#134-如果你的-mysql-密码不是-123456) 改 `settings.py` |
| `Unknown database 'squirrel_test'` | 建库脚本没跑 | 回到 [13.3](#133-建库--灌数据两步别跳) 跑第 1 步 |
| 网站能开，但**一件商品都没有** | 只跑了建表、没跑数据脚本 | 跑 13.3 的第 2 步 |
| 商品**全是裂图** | `upload\images\` 没拷全 | 对照 [13.1](#131-先确认手里有什么) 数一下，应该是 48 个 jpg |
| 登录提示「密码不正确」 | 库里没有账号（数据脚本没跑） | 同上，或者自己去注册一个 |
| 首页中文变成 `???` | 连库没带 utf8mb4 | 跑脚本时加 `--default-character-set=utf8mb4` |
| `That port is already in use` | 8000 被占了 | 换成 `python manage.py runserver 0.0.0.0:8001`，地址也跟着变 |
| 手机连不上 | 三个可能：绑了 127.0.0.1 / 防火墙 / 不在同一 WiFi | 见 [13.6](#136-启动服务) 下面的说明 |
| 改了代码页面没变 | 浏览器缓存 / 用的是 `--noreload` | 按 Ctrl+F5 强制刷新；`--noreload` 起来的要重启进程 |
| 右下角没有机器人入口 | `.env` 没配 | 见 [13.8](#138-智能导购机器人可选不装不影响其他功能)，**这是正常的** |

**还是不行的话**，把报错信息完整复制下来 —— 错误信息里通常直接写着是哪一步没做。

---

## 附：这次重写是怎么做的

按阶段推进，每段做完立刻验证，`runserver` 和 Java 版同时开着逐页对照：

| 阶段 | 内容 |
|---|---|
| P0 | conda 环境 + Django/PyMySQL + 验证能连库读出用户 |
| P1 | 骨架：settings、`core`、10 个 model、`base.html`、静态资源搬迁 |
| P2 | 账号域：登录 / 注册 / 登出 / 个人中心 / 个人设置 / 头像 / 关注 |
| P3 | 商品域：首页 / 搜索 / 分类 / 详情 / 发布 / 编辑 / 删除 / 已售出 / 图片上传 |
| P4 | 私信 + 通知 + 聊天页 + 他人资料页 + 评论 AJAX |
| P5 | 后台三页 + 3 个 `manage-*.js` 适配 + CSRF 补丁 |
| P6 | 机器人（743 行核心逻辑，HTTP 换成 `requests`，Caffeine 换成 Django cache） |
| P7 | 下架实装 + 联系方式交换 + 二次确认 |
| P8 | 逐页对照验证 + 修补 + 本文档 |

**验证口径**：所有关键流程都**手工走过一遍**才算过 ——
「看起来对」不算数，要看到库里那一行真的变了、另一个账号登录进去真的看到了该看到的东西。

---

*最后更新：2026-10-08*
