"""
通用工具。对应原版 Java 的 `util/MD5.java` 和 `util/DateUtil.java`。

原版的 DateUtil 有 20 多个方法，但实际被业务调用的只有三个：
  getNowDay()    → "2026-10-08"
  getNowTime()   → "2026-10-08 20:30:00"
  getLastTime(t, n) → t 之后 n 天
其余（getThreeBeginDate / getMonthBeginDate / formatTime ...）在整个项目里
没有任何调用点，是死代码，不搬。
"""

import hashlib
from datetime import datetime, timedelta

# 原版 DateUtil.FORMAT1 / FORMAT2 / FORMAT3
FMT_DAY = "%Y-%m-%d"
FMT_MINUTE = "%Y-%m-%d %H:%M"
FMT_SECOND = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------- 密码

def md5_hex(raw):
    """原版 MD5.md5()：32 位**大写**十六进制。

    大写这点很重要 —— 库里存的是 E10ADC3949BA59ABBE56E057F20F883E，
    小写比对会一个都登不上。
    """
    return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()


def check_password(raw, stored):
    """把用户输入的明文和库里的 MD5 比对。"""
    if not raw or not stored:
        return False
    return md5_hex(raw) == stored.upper()


# ---------------------------------------------------------------- 时间

def now_day():
    """原版 DateUtil.getNowDay()，用于商品的 start_time / polish_time。"""
    return datetime.now().strftime(FMT_DAY)


def now_time():
    """原版 DateUtil.getNowTime()，用于注册时间 / 通知 / 私信。"""
    return datetime.now().strftime(FMT_SECOND)


def days_later(day, days):
    """原版 DateUtil.getLastTime()：把 'yyyy-MM-dd' 往后推 days 天。

    原版解析失败时会把原字符串原样返回（吞掉异常），这里保持同样的兜底 ——
    宁可 end_time 存成 start_time，也不要发布商品直接 500。
    """
    try:
        return (datetime.strptime(day, FMT_DAY) + timedelta(days=days)).strftime(FMT_DAY)
    except (ValueError, TypeError):
        return day
