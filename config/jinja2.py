"""
Jinja2 环境的定制点。

只需要补两个全局函数：Django 的 Jinja2 后端不会自动给 `{% url %}` 和
`{% static %}`（原版 Thymeleaf 的 `@{...}` 一个顶这两个）。

`csrf_input` 和 `csrf_token` **不用在这里加** —— Django 在 render 时会自己
注入（见 django/template/backends/jinja2.py 的 Template.render），
模板里直接写 `{{ csrf_input }}` 即可。
"""

from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import NoReverseMatch, reverse
from jinja2 import Environment


def url(name, *args, **kwargs):
    """模板里的 `{{ url('goods_detail', id=5) }}` → `/goods/goodsId/5`。

    **不能把 django.urls.reverse 直接挂上去。** reverse 的签名是
    `reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None)`，
    也就是说它**没有** `**kwargs` —— 模板里写 `url('goods_detail', id=5)`
    会被当成给 reverse 传了一个叫 `id` 的参数，直接
    `TypeError: reverse() got an unexpected keyword argument 'id'`。
    （`id` 是 Python 内置名，额外扎眼，但 `name=`、`args=` 这些名字一样会撞。）

    所以包一层，把多余的关键字原样收进 kwargs 再交给 reverse。
    """
    return reverse(name, args=args, kwargs=kwargs)


def environment(**options):
    env = Environment(**options)
    env.globals.update(
        {
            "url": url,
            # {{ static('css/campus.css') }}  →  /static/css/campus.css
            "static": staticfiles_storage.url,
            # 模板里想 try/except 地拼地址时用得上（目前没人用，留着方便调试）
            "NoReverseMatch": NoReverseMatch,
        }
    )
    return env
