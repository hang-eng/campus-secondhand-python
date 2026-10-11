"""
后台管理三页。

对应原版 Java 的 `controller/ManageController.java`（109 行）+ 三个模板
（`manage-login.html` / `manage-userList.html` / `manage-goodsList.html`）。

**为什么不用 Django admin。** 用户选的是「保留现有自定义后台页面」——
那三页是 Bootstrap 3 照原版做的，答辩时和 Java 版并排一模一样；
换成 django.contrib.admin 一来要重新注册 9 个 model、二来长得完全不一样，
三来原版那些操作（冻结 / 解冻 / 硬删商品）django admin 也没有现成的对应。

**权限。** 原版是在每个方法体里写 `if (currentUser == null || power != 90)
return "/error/404";`——渲染 404 页而不是 403，不告诉对方「这里有个后台，
只是你没权限」。这里用 `core.decorators.admin_required`，行为一样。
三个页面**全部**套了这个装饰器，包括登录页：

  登录页原版是「已登录就跳到用户管理，没登录就显示登录页」，本身不需要权限。
  但这个「已登录」判定用的是 session 里那份可能过期的 cur_user，
  而我们同时要求它下发 csrftoken cookie（见下面 ensure_csrf_cookie 的说明），
  套上 admin_required 之后语义变成「管理员看到的是跳转、其他人看到登录页」——
  和原版对普通登录用户的表现一致（原版会把他跳到 /manage/user/list，
  然后由那一页渲染 404，等于白跳一次）。

**分页数据的形状**（`data` 这个 dict）逐字照抄原版 `UserServiceImpl.getUsers`
和 `GoodsServiceImpl.getGoodsByCatelogIdAndNameAndDescrible`，因为模板里那句
`manageUserListPage.init(pageNum, pageSize, totalPageNum, totalPageSize, users)`
是按这个顺序取的，少一个键就是 `undefined`，分页条会直接算错。
"""

from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie

from accounts.models import User
from core.auth import current
from core.constants import GOODS_PAGE_SIZE, USER_PAGE_SIZE
from core.decorators import admin_required
from goods.models import Catelog, Goods
from goods.services import goods_rows

# ================================================================ 登录页


@ensure_csrf_cookie
def login_page(request):
    """GET /manage/login。

    **`@ensure_csrf_cookie` 是必须的。** 这一页的表单是
    `<form class="form-signin">`，里面只有 input，**没有任何 {{ csrf_input }}**，
    登录是 manage-login.js 用 `$.post()` 发的。而 Django 只在
    「模板里用到了 csrf_token」或「视图加了这个装饰器」时才下发 csrftoken
    cookie，两者的报错表现分别是：

      - 少了 csrftoken cookie → `static/js/csrf.js` 拿不到 token，直接 return，
        于是那一次 $.post 不带 X-CSRFToken 头 → 被 CsrfViewMiddleware 拦掉，
        返回一个 403 的 HTML 错误页 → 前端按 JSON 解析失败 →
        toastr 弹不出来、页面什么都不发生。用户看到的是「点了登录没反应」，
        很难查。
      - 所以这里必须显式要求下发。

    另外两页（用户管理 / 商品管理）也各要一个同样的装饰器 —— 它们的
    「冻结 / 删除 / 保存」全是 AJAX，靠 csrf.js 补头。
    """
    if current(request):
        return redirect("manage_user_list")
    return render(request, "manage/manage-login.html")


# ================================================================ 用户管理


@ensure_csrf_cookie
@admin_required
def user_list(request):
    """GET /manage/user/list —— 全部用户，按注册时间倒序，每页 10 个。"""
    return render(
        request,
        "manage/manage-userList.html",
        {"data": _users_page(request.GET.get("page"))},
    )


def _users_page(raw_page):
    """对应原版 `UserServiceImpl.getUsers(pageNum, pageSize)`。

    三种返回（空库 / 页码越界 / 正常）连 `pageNum: 0` 这种细节都照抄 ——
    模板里那句 `manageUserListPage.init(...)` 拿到的就是这几个数，
    分页条的「首页/上一页」是 disabled 还是可点由它们决定。

    `count == 0` 时 `totalPageNum` 是 **1** 不是 0（原版就这么写的），
    照抄：分页条会渲染成「首页|上一页|1|下一页|末页」全禁用，比一列 0 好看。
    """
    total = User.objects.count()
    if total == 0:
        return _empty_users_page(1)

    page_size = USER_PAGE_SIZE
    total_pages = (total + page_size - 1) // page_size

    page = _int_or(raw_page, 1)
    if page < 1 or page > total_pages:
        # 原版这里是 `pageNum > totalPageNum`，也就是 page=0 / 负数会漏下去，
        # 交给 PageHelper 处理（它把小于 1 当第 1 页）。这里一并收进同一条分支，
        # 免得 Django 的切片遇到 0 或负数切出一个空列表却报「这是第 0 页」。
        if page > total_pages:
            return _empty_users_page(total_pages)
        page = 1

    # 原版 SQL 是 `ORDER BY create_at DESC`。补一个 `-id` 兜底：
    # create_at 是 varchar，同一秒注册的两个人只按它排先后由 MySQL 决定
    # （实测库里两个账号时间不同，但页面刷新时顺序飘了很难查）。
    users = list(
        User.objects.order_by("-create_at", "-id")[
            (page - 1) * page_size : page * page_size
        ]
    )

    return {
        "pageNum": page,
        "pageSize": page_size,
        "totalPageNum": total_pages,
        # 原版这个键放的是**总条数**而不是「每页条数」，名字起岔了但绕不开 ——
        # 模板里那句 `totalPageSize` 是直接透传给 JS 的。
        "totalPageSize": total,
        "users": [_user_row(u) for u in users],
    }


def _empty_users_page(total_pages):
    return {
        "pageNum": 0,
        "pageSize": 0,
        "totalPageNum": total_pages,
        "totalPageSize": 0,
        "users": [],
    }


def _user_row(user):
    """用户在页面上的样子。

    **不带密码哈希。** 原版模板那句 `var users = /*[[${data['users']}]]*/;`
    是 Thymeleaf 把整个 Java `User` 对象序列化成 JSON，**连 password 一起**
    写进了 HTML 源码 —— 右击查看源代码就能拿到全站所有账号的 MD5。
    前端脚本一个字段都没读过它（`updatePassword` 那个框是空的、
    下面那行填密码的代码也被注释掉了），所以这里不给。

    键名用 camelCase：`manage-userList.js` 里写的是 `users[index].username`
    这种，那是 Jackson 按 Java 属性名生成的，是既有 JS 的契约。
    """
    return {
        "id": user.id,
        "username": user.username or "",
        "phone": user.phone or "",
        "qq": user.qq or "",
        "createAt": user.create_at or "",
        "goodsNum": user.goods_num or 0,
        "power": user.power if user.power is not None else 10,
        "status": user.status or 0,
    }


# ================================================================ 商品管理


@ensure_csrf_cookie
@admin_required
def goods_list(request):
    """GET /manage/goods/list —— 全部商品，可按分类和关键词筛，每页 16 个。

    **不过滤 state。** 前台那些列表一律加 `state=0`（下架的商品不该出现），
    后台这个页面是管理员用来处理下架商品的，过滤掉就看不见了。
    原版那条 `selectByCatelog` 也没有 state 条件，行为和它一致。
    """
    catelog_id = _int_or(request.GET.get("catelogId"), 0)
    text = (request.GET.get("text") or "").strip()

    data = _goods_page(request.GET.get("page"), catelog_id, text)
    data["catelogs"] = Catelog.objects.filter(status=1).order_by("id")
    data["catelogId"] = catelog_id
    data["text"] = text
    return render(request, "manage/manage-goodsList.html", {"data": data})


def _goods_page(raw_page, catelog_id, text):
    """对应原版 `GoodsServiceImpl.getGoodsByCatelogIdAndNameAndDescrible`。

    关键词同时匹配名称和描述（原版把同一个 `text` 传了两次，一次当 name
    一次当 describle），`catelogId == 0` 表示不限分类。

    原版那条 SQL 有两个毛病，这里没有跟着抄：
      - `AND (name like ..` 和 `OR describle like ..)` 的左右括号被拆在两个
        `<if>` 里，**只填关键词不填描述的话括号配不上**，SQL 直接报错、整页 500。
        渲染这条语句的 MyBatis 拼出来是 `... AND (name like '%x%'`，缺一个右括号。
        Django 的 Q() 组合天然没有这个问题。
      - 没有 `order by`。没有排序的 `LIMIT` 查询，翻页时同一条可能重复出现、
        也可能被跳过。原版实测是主键序，这里显式写出来。
    """
    query = Goods.objects.all()
    if catelog_id:
        query = query.filter(catelog_id=catelog_id)
    if text:
        query = query.filter(Q(name__icontains=text) | Q(describle__icontains=text))

    total = query.count()
    if total == 0:
        return _empty_goods_page(1)

    page_size = GOODS_PAGE_SIZE
    total_pages = (total + page_size - 1) // page_size

    page = _int_or(raw_page, 1)
    if page < 1 or page > total_pages:
        if page > total_pages:
            return _empty_goods_page(total_pages)
        page = 1

    rows = query.order_by("id")[(page - 1) * page_size : page * page_size]

    return {
        "pageNum": page,
        "pageSize": page_size,
        "totalPageNum": total_pages,
        "totalPageSize": total,
        # 原版这里还有一步「拿 userIds 去查 users 再 setUser 挂到每件商品上」，
        # 那正是 goods.services.goods_rows() 干的事（一次 IN 查完，不是 N+1）。
        # 模板和 JS 要的是 `item.user.username`（编辑弹层里那格发布人）。
        "goodsList": goods_rows(rows),
    }


def _empty_goods_page(total_pages):
    return {
        "pageNum": 0,
        "pageSize": 0,
        "totalPageNum": total_pages,
        "totalPageSize": 0,
        "goodsList": [],
    }


# ================================================================ 小工具


def _int_or(raw, default):
    """把 query string 上的一格文本转成 int。转不动就用默认值。

    原版是 `@RequestParam(defaultValue = "1") int page`，Spring 自己转；
    Django 不转，`"abc"` 直接进切片就是 TypeError、整页 500。
    """
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default
