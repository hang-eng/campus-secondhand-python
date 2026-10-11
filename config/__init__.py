"""Django 启动时把 PyMySQL 注册成 MySQLdb。

Django 的 MySQL 后端写的是 `import MySQLdb`，PyMySQL 提供了一个同名适配器。
这样就不用装 mysqlclient —— 那个在 Windows 上要编译 C 扩展，很麻烦。
"""

import pymysql

pymysql.install_as_MySQLdb()
