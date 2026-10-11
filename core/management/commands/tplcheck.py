"""
模板体检。P1–P8 全程都用它，所以做成了命令而不是一次性脚本。

    python manage.py tplcheck            # 报告模式：列出问题，缺路由名只提示
    python manage.py tplcheck --strict   # 门禁模式：缺路由名/缺静态文件也算失败

查四件事：
  1. 每个模板能不能编译（Jinja2 语法错在这里就炸，不用等访问页面才发现）
  2. 模板里 url('某某') 引用的路由名，URLconf 里到底有没有
  3. 模板里 static('某某') 引用的文件，static/ 下到底有没有
  4. 有没有 {% extends %} 指向不存在的模板

为什么需要第 2 条：模板是 P1 就写好的，路由是 P2–P6 才逐个补上的。
中间这段时间模板引用的名字大半还不存在，跑一遍就能拿到「还欠哪些路由」的清单。
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template import engines
from django.urls import get_resolver

# 模板里 url('x') / static('x') 的引用。只匹配字面量，拼出来的名字查不到，
# 那种写法在项目里只有一处（侧边栏分类图 static('img/' ~ cclass ~ '.png')），
# 是故意拼的，编译器管不着。
URL_REF = re.compile(r"""url\(\s*['"]([^'"]+)['"]""")
STATIC_REF = re.compile(r"""static\(\s*['"]([^'"]+)['"]""")


def route_names():
    """URLconf 里当前所有具名路由。带 namespace 的拼成 ns:name。"""
    names = set()

    def walk(resolver, prefix=""):
        for key in resolver.reverse_dict:
            if isinstance(key, str):
                names.add(prefix + key)
        for ns, (_, sub) in resolver.namespace_dict.items():
            walk(sub, prefix + ns + ":")

    walk(get_resolver())
    return names


class Command(BaseCommand):
    help = "编译全部模板，并核对 url()/static() 引用是否存在"

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="缺路由名或缺静态文件时也返回失败（P8 收尾时用）",
        )

    def handle(self, *args, **options):
        strict = options["strict"]
        root = Path(settings.BASE_DIR)
        templates_dir = root / "templates"
        static_dir = root / "static"

        env = engines["jinja2"].env
        known_routes = route_names()
        files = sorted(templates_dir.rglob("*.html"))

        used_routes, used_statics = {}, {}
        syntax_errors, missing_extends = [], []
        compiles = 0

        for path in files:
            rel = path.relative_to(templates_dir).as_posix()
            source = path.read_text(encoding="utf-8")

            try:
                env.parse(source)
                compiles += 1
            except Exception as exc:
                syntax_errors.append((rel, f"{type(exc).__name__}: {exc}"))
                continue  # 编译不了就不用往下查引用了

            for name in URL_REF.findall(source):
                used_routes.setdefault(name, []).append(rel)
            for name in STATIC_REF.findall(source):
                used_statics.setdefault(name, []).append(rel)

            head = source[:2000]
            for parent in re.findall(r"""extends\s+['"]([^'"]+)['"]""", head):
                if not (templates_dir / parent).exists():
                    missing_extends.append((rel, parent))

        self.stdout.write(self.style.MIGRATE_HEADING(f"1. 编译（{len(files)} 个模板）"))
        if syntax_errors:
            for rel, err in syntax_errors:
                self.stderr.write(self.style.ERROR(f"   ✗ {rel}\n     {err}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"   ✓ {compiles} 个全部编译通过"))

        missing_routes = {n: v for n, v in used_routes.items() if n not in known_routes}
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\n2. url() 引用（用到 {len(used_routes)} 个名字，已定义 {len(known_routes)} 个路由）"
            )
        )
        if missing_routes:
            self.stdout.write(f"   还欠 {len(missing_routes)} 个路由名（P2–P6 补）：")
            for name in sorted(missing_routes):
                where = sorted(set(missing_routes[name]))
                self.stdout.write(f"     · {name:<22} 被 {len(where)} 个模板引用")

        unused = sorted(known_routes - set(used_routes))
        if unused:
            self.stdout.write(f"   已定义但没人用：{', '.join(unused)}")

        missing_statics = {
            n: v for n, v in used_statics.items() if not (static_dir / n).exists()
        }
        self.stdout.write(
            self.style.MIGRATE_HEADING(f"\n3. static() 引用（{len(used_statics)} 个文件）")
        )
        if missing_statics:
            for name in sorted(missing_statics):
                where = sorted(set(missing_statics[name]))
                self.stderr.write(
                    self.style.ERROR(
                        f"   ✗ static/{name} 不存在，被 {', '.join(where)} 引用"
                    )
                )
        else:
            self.stdout.write(self.style.SUCCESS("   ✓ 全部存在"))

        if missing_extends:
            self.stdout.write(self.style.MIGRATE_HEADING("\n4. extends 指向的模板"))
            for rel, parent in missing_extends:
                self.stderr.write(self.style.ERROR(f"   ✗ {rel} extends {parent}，该模板不存在"))

        hard_fail = bool(syntax_errors) or bool(missing_extends)
        if strict:
            hard_fail = hard_fail or bool(missing_routes) or bool(missing_statics)

        self.stdout.write("")
        if hard_fail:
            self.stdout.write(
                self.style.ERROR(
                    "模板体检未通过。"
                    + ("" if strict else "（当前缺路由名是正常进度，加 --strict 才算失败）")
                )
            )
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("模板体检通过。"))
