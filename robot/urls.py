"""
机器人的三个路由。

**对话页那一条不在这里，在 `config/urls.py` 里单独写了一行。** 原因是
原版的地址就是 `/robot`（结尾没有斜杠），而 Django 的 `include()` 挂成
`path("robot/", ...)` 之后，`/robot` 会被 CommonMiddleware 用 301 跳到
`/robot/` —— 地址栏就和 Java 版对不上了，而重写的一个前提就是两边同一个
地址能直接并排对照。所以那一条单独挂成 `path("robot", ...)`。

顺带一提：这么写之后 `/robot/`（带斜杠）会 404，和原版 Spring 的行为一致。
"""

from django.urls import path

from . import views

urlpatterns = [
    path("send", views.send, name="robot_send"),
    path("clear", views.clear, name="robot_clear"),
]
