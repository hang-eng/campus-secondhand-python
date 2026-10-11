"""
校园二手交易平台 —— Django 配置。

设计原则（照抄 Java 版的行为，不顺手"改进"）：
  1. 直接连现有的 squirrel_test 库，一行数据都不搬 → 所有 model 都是 managed = False
  2. 密码是大写 MD5，不用 django.contrib.auth（它认 pbkdf2 格式，会一个都登不上）
  3. 会话有效期 24 小时，与原版 setMaxInactiveInterval(24*60*60) 对齐
  4. 模板用 Jinja2 而不是 Django Template，理由见计划文档
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# .env 里放 ROBOT_API_KEY 这类密钥；.env 不进版本库
load_dotenv(BASE_DIR / ".env")

# 本地开发用的固定 key。这项目不上公网，SECRET_KEY 泄露的后果只是本地 session 能伪造。
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-campus-secondhand-local-dev-only"
)

# 局域网演示要能被别的机器访问，所以放开。只在校园网内跑。
DEBUG = True
ALLOWED_HOSTS = ["*"]


# ---------------------------------------------------------------- 应用

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.sessions",
    # 六个自建 app。注意没有 django.contrib.admin / auth：
    # 后台是照搬原版的自定义页面（backstage），认证也是自己写的（见 core/auth.py）。
    "core",
    "accounts",
    "goods",
    "chat",
    "backstage",
    "robot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"


# ---------------------------------------------------------------- 模板

TEMPLATES = [
    {
        # 主引擎。Jinja2 的表达式就是 Python 子集，原版 948 个 th:* 里的
        # 三元、带参方法调用（${commentCounts.get(x)}）、th:with 局部变量
        # 都能直接对应过去，不用把逻辑搬进 view。
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "environment": "config.jinja2.environment",
            "context_processors": ["core.context_processors.globals"],
            # autoescape 和 undefined 都不在这里设：
            #   autoescape  Django 已 setdefault(True)
            #   undefined   Django 在 DEBUG 下默认 DebugUndefined（变量为 null 渲染成空，
            #               与 Thymeleaf 行为一致）。注意它是**类**不是字符串，
            #               写字符串会直接把 Jinja2 初始化搞崩。
        },
    },
    {
        # 兜底引擎。Django 内部有少数地方硬走模板（调试页、错误页），
        # 留着它免得那些地方报 "no DjangoTemplates backend configured"。
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {"context_processors": []},
    },
]


# ---------------------------------------------------------------- 数据库

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "squirrel_test",
        "USER": "root",
        "PASSWORD": "123456",
        "HOST": "127.0.0.1",
        "PORT": "3306",
        "OPTIONS": {
            # 必须 utf8mb4。实测过：用 latin1 连 t_shop_user，中文全变成问号。
            "charset": "utf8mb4",
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------- 会话

# 原版 UserController 登录成功时调用 setMaxInactiveInterval(24*60*60)
SESSION_COOKIE_AGE = 24 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# **不用默认的 db 后端**（那也是 Django 的默认值：django.contrib.sessions
# .backends.db）。它会往库里写一张 django_session 表，而这个库是原版
# Java 项目正在用的 —— 为了存一个登录态就往里面塞一张 Django 专用表，
# 没必要，而且这台机器上不开 migrate 的话表根本不存在，一登录就 500。
#
# 签名 cookie 后端：整个 session 加签名后放在 cookie 里，不落库。
# 这反而更贴近原版 —— Tomcat 的 session 就在内存里，也不落库。
#
# 两个前提都满足：
#   1. session 里那点东西（id/phone/username/qq/avatar/avatarUrl/
#      createAt/goodsNum/power/status）序列化后不到 400 字节，
#      离 cookie 的 4KB 上限很远。往 session 里塞大对象之前先想一下这里。
#   2. SECRET_KEY 是固定的（不是每次启动随机生成），否则重启一次
#      所有人的登录态全掉。
#
# 注意：签名只保证**改不了**，不保证**看不见** —— 里面那个 power=90
# 用户自己能看到。但能看到不等于能改（改一个字节签名就失效），
# 而 session 里本来也只有他自己的信息。
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"


# ---------------------------------------------------------------- 本地化

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = False  # 原版时间全是 varchar 字符串，没有时区概念


# ---------------------------------------------------------------- 静态与上传

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# 对应 Java 版 GgeeConst.UPLOAD_ROOT + "/images/"
# 原版是 <user.dir>/upload/images/，这里换成项目根，位置等价。
UPLOAD_ROOT = BASE_DIR / "upload" / "images"

# 单文件 10MB / 整个请求 100MB，与原版 application.properties 一致
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024


# ---------------------------------------------------------------- CSRF

# 允许 JS 读 csrftoken cookie —— static/js/csrf.js 靠它给 AJAX 补上 header
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"


# ---------------------------------------------------------------- 机器人

# 对应原版 RobotProperties。key 只从环境变量来，绝不写进代码或配置文件。
#
# 原版把这个 key 的默认值**硬编码在 RobotProperties 里**（注释里也承认了
# 那是一把开发过程中泄露过的测试 key）。重写时不给默认值：没配就是没配，
# 右下角图标整个不出现，而不是拿一把泄漏的 key 去调付费接口。
ROBOT_ENABLED = os.environ.get("ROBOT_ENABLED", "1") != "0"
ROBOT_API_KEY = os.environ.get("ROBOT_API_KEY", "")
ROBOT_API_URL = os.environ.get(
    "ROBOT_API_URL", "https://api.deepseek.com/v1/chat/completions"
)
ROBOT_MODEL = os.environ.get("ROBOT_MODEL", "deepseek-chat")

# 建连超时。给 5 秒：连不上就是连不上，让用户干等一分钟没意义。
ROBOT_CONNECT_TIMEOUT = 5

# 读取超时给 60 秒。这不是「整个请求最多 60 秒」，而是「两次收到字节之间」
# 的等待上限（对应 Java 的 SO_TIMEOUT）。max_tokens=700 的中文回复，模型那边
# 全生成完最坏要三四十秒，所以必须给宽，给窄了会在模型正吐字的时候被判超时。
ROBOT_READ_TIMEOUT = 60

ROBOT_MAX_TOKENS = 700

# 0.7 是刻意压住的。要它稳定地照着清单里的 id 抄，
# 温度再往上它就开始自己编商品名了。
ROBOT_TEMPERATURE = 0.7

# 最多带几轮历史（一轮 = 用户一句 + 助手一句）
ROBOT_MAX_TURNS = 6

# 单条提问的长度上限，前端 maxlength 只是顺手，服务端还要再截一次
ROBOT_MAX_INPUT_LENGTH = 500

# 一条回复里最多渲染几张商品卡片，防止模型一口气列二十件把页面撑爆
ROBOT_MAX_CARDS_PER_REPLY = 6

# 塞进提示词的商品描述截断长度。别改成 0 或负数 —— 截断逻辑会切出一堆空串。
# 原版 RobotProperties 专门写了个 setter 把小于 4 的值兜成 4；这里是个写死的
# 常量，没有从配置文件读进来的入口，所以不再多一层防御。
ROBOT_DESCRIBLE_SUMMARY_LENGTH = 30

# 商品清单快照在缓存里存活多久。60 秒是刻意的：新发布的商品最多等一分钟
# 就能被推荐到，又能省掉「每聊一句就全表扫一遍商品」。
ROBOT_CATALOG_CACHE_SECONDS = 60

# 一次登录的对话历史在缓存里留多久。原版是放在 HttpSession 里、跟着会话
# 一起没的（Tomcat 默认 30 分钟不活动就回收）。这里给 4 小时，比会话宽松 ——
# 记录本身不敏感，多留一会儿只是体验问题。
ROBOT_HISTORY_CACHE_SECONDS = 4 * 60 * 60


# ---------------------------------------------------------------- 日志

(BASE_DIR / "logs").mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "encoding": "utf-8",
            "formatter": "simple",
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
}
