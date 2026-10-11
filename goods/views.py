"""
商品域视图。

对应原版 Java 的 `controller/GoodsController.java`（512 行）和
`controller/CommentsController.java`（47 行）—— 后者的三个接口
按 URL 前缀（`/comments/api/...`）单独挂了一条路由，见 `goods/urls_comments.py`，
但实现也放在本文件里：它们操作的是 `t_shop_comments`，属于商品域。
"""

from django.db import transaction
from django.db.models import F, Q
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from accounts.models import Follow, User
from chat.models import Message, Notice
from core import auth
from core.ajax import fail, json_body, ok
from core.constants import (
    GOODS_DURATION_DAYS,
    GOODS_PER_SECTION,
    SOLD_NO,
    SOLD_YES,
    STATE_OFF,
    STATE_ON,
)
from core.decorators import admin_api, ajax_login_required
from core.http import back
from core.uploads import store_image
from core.utils import days_later, now_day, now_time
from .models import FRONT_VISIBLE, Catelog, Comments, Goods, Image
from .services import card_json, cards

# 首页的 8 个板块：(分类 id, 板块标题)。
#
# 第一节的分类 id 是 **None**，意思是「不带分类条件，全站最新的 6 件」。
#
# 这里修掉了原版的一个缺陷：原版 GoodsController.homeGoods 从 i=1 循环到 7
# 拼出 catelogGoods1..7，模板里第一节「最新发布」和第二节「闲置数码」
# **都取 catelogGoods1**，所以那两栏永远显示同一批商品。
# 原版根本没有「全站最新」这样一个查询。
#
# 和用户确认过（2026-10-08），按标题的字面意思修：第一节给全站最新。
# 代价是首页第一栏和 8081 上的 Java 版对不上了 —— 那正是修它的目的。
SECTIONS = [
    (None, "最新发布"),
    (1, "闲置数码"),
    (2, "校园代步"),
    (3, "电器日用"),
    (4, "图书教材"),
    (5, "美妆衣物"),
    (6, "运动棋牌"),
    (7, "周边其他"),
]

PRICE_WARN = "价格只能填 0 或正数，无效的输入已忽略。"

# 发布页 / 编辑页「物品类别」下拉的选项。
# 就是上面那批分类切掉第一节 —— 第一节是「全站最新」，不是一个真分类，
# 不能出现在下拉里。
# 原版这两处的 7 个 <option> 是**逐字抄两遍**的，改一次要改两个文件。
CATELOG_OPTIONS = SECTIONS[1:]
CATELOG_IDS = {cid for cid, _ in CATELOG_OPTIONS}


# ================================================================ 首页

def home(request):
    """首页：第一节全站最新，其余每个分类各取最新上架的 6 件。

    原版「逐个分类循环、每件商品再单独查一次图片」会发出 6×7=42 次查询，
    这里每个板块只发 2 次（商品 + 图片 IN 查询），整页 16 次。

    排序加 `id` 兜底：库里 14 件商品的 polish_time **全都是同一天**，
    只按它倒序时先后完全由 MySQL 决定（原版就这样，刷新一次可能换个顺序）。
    补一个升序 id 恰好等价于 MySQL 在这种全表扫描下的实际输出，又不会飘。

    每节的键名叫 `goods` 不叫 `items`：Jinja2 取属性时**优先 getattr**，
    `section.items` 会拿到 dict 自带的那个 `.items()` 方法而不是我们的列表，
    渲染出来就是 `TypeError: 'builtin_function_or_method' object is not iterable`。
    """
    cache = {}
    sections = []
    for catelog_id, title in SECTIONS:
        # 第一节的 catelog_id 是 None（全站最新）。用它当 cache 的键不合适，
        # 换个不会和分类 id 撞的字符串。
        key = catelog_id if catelog_id is not None else "all"
        if key not in cache:
            query = Goods.objects.filter(FRONT_VISIBLE)
            if catelog_id is not None:
                query = query.filter(catelog_id=catelog_id)
            cache[key] = cards(query.order_by("-polish_time", "id")[:GOODS_PER_SECTION])
        sections.append({"title": title, "goods": cache[key]})

    return render(
        request,
        "goods/homeGoods.html",
        {
            "sections": sections,
            # 首页不属于任何分类，左侧导航高亮「最新发布」那一项
            "active_catelog": None,
        },
    )


# ================================================================ 分类 / 搜索

def catelog(request, id):
    """分类列表。支持分类内再按关键词和价格区间筛。"""
    catelog_obj = Catelog.objects.filter(id=id).first()
    if catelog_obj is None:
        raise Http404("分类不存在")

    keyword = (request.GET.get("str") or "").strip()
    price = _price_range(request.GET.get("minPrice"), request.GET.get("maxPrice"))

    query = Goods.objects.filter(FRONT_VISIBLE, catelog_id=id)
    query = _apply_filters(query, keyword, price)

    return render(
        request,
        "goods/catelogGoods.html",
        _listing_context(query, catelog=catelog_obj, active_catelog=id, search=keyword, price=price),
    )


def search(request):
    """全站搜索：关键词匹配名称或描述，可再叠加价格区间。

    **不带分类条件** —— 原版 searchGoods 的 SQL 里就没有 catelog_id，
    搜出来是全部类目里的结果。
    """
    keyword = (request.GET.get("str") or "").strip()
    price = _price_range(request.GET.get("minPrice"), request.GET.get("maxPrice"))

    query = _apply_filters(Goods.objects.filter(FRONT_VISIBLE), keyword, price)

    return render(
        request,
        "goods/searchGoods.html",
        _listing_context(query, catelog=None, active_catelog=None, search=keyword, price=price),
    )


def _apply_filters(query, keyword, price):
    """关键词 + 价格区间。

    关键词用 `icontains` 而不是 `contains`：Django 在 MySQL 上把
    `contains` 编译成 `LIKE BINARY`（区分大小写），而原版那条 SQL 是裸的
    `LIKE`，走表默认排序规则 utf8mb4_general_ci，**不区分大小写**。
    用 `icontains` 才对得上。

    另外原版把关键词直接拼进 LIKE 模式串，用户输入的 `%` `_` 会被当成通配符；
    Django 会转义它们。这是个刻意的差异 —— 搜「50%」时用户要的是字面量。

    `state=0` 的过滤在调用方（FRONT_VISIBLE）—— 原版**任何** SELECT 都不过滤
    state，所以「下架」从来没生效过。这是重写时实装的，见 README 的「行为变更」。
    """
    if keyword:
        query = query.filter(Q(name__icontains=keyword) | Q(describle__icontains=keyword))
    if price["minValue"] is not None:
        query = query.filter(price__gte=price["minValue"])
    if price["maxValue"] is not None:
        query = query.filter(price__lte=price["maxValue"])
    # 原版这几条 SQL 都没有 order by，返回顺序由 MySQL 决定（实测是主键升序）。
    # 显式写出来，免得以后加个索引顺序就变了。
    return query.order_by("id")


def _listing_context(query, price, **extra):
    """分类页 / 搜索页共用的上下文。

    price 是 _price_range() 那整个 dict；模板只要其中四个键，
    所以不整个摊进上下文（免得 minValue 这种内部字段也漏出去）。
    """
    return {
        "goodsExtendList": cards(query),
        "priceWarn": price["warn"],
        "priceFiltered": price["filtered"],
        "minPriceText": price["minText"],
        "maxPriceText": price["maxText"],
        **extra,
    }


# ================================================================ 价格区间

def _price_range(min_str, max_str):
    """解析价格区间。规则与原版 parsePriceRange 完全一致：

      - 空的：该端不限制
      - 非数字 / 负数 / NaN / Infinity：忽略这一端，回一句提示，**不打断查询**
      - 最低价填得比最高价大：自动对调，不算错
    """
    bad = False
    lo = hi = None

    for raw, assign in ((min_str, "lo"), (max_str, "hi")):
        text = (raw or "").strip()
        if not text:
            continue
        # NaN / Infinity 也能被 float() 接受，_float_or_none 已经挡住了
        value = _float_or_none(text)
        if value is None or value < 0:
            bad = True
            continue
        if assign == "lo":
            lo = value
        else:
            hi = value

    if lo is not None and hi is not None and lo > hi:
        lo, hi = hi, lo

    return {
        "minValue": lo,
        "maxValue": hi,
        "minText": _fmt_price(lo),
        "maxText": _fmt_price(hi),
        "warn": PRICE_WARN if bad else None,
        "filtered": lo is not None or hi is not None,
    }


def _fmt_price(value):
    """回显到输入框：去掉多余的小数尾巴（130.0 显示成 130），None 显示空。"""
    if value is None:
        return ""
    if value == int(value):
        return str(int(value))
    return str(value)


# ================================================================ 详情

def detail(request, id):
    """商品详情。

    一次把详情页要的东西全查出来：商品 + 图 + 分类 + 卖家 + 评论（连评论人
    和被打招呼的人一起）。原版是逐条评论查用户，这里一次 IN 查完。
    """
    goods = Goods.objects.filter(id=id).first()
    if goods is None:
        raise Http404("商品不存在")

    me = auth.current(request)
    is_self = bool(me and me["id"] == goods.user_id)

    # 已下架的商品前台看不到 —— 原版 state 列根本不过滤，这条是实现「下架」时
    # 补的行为（见 README「行为变更」）。**但货主自己要看得到**：「我的闲置」
    # 里还列着他的全部商品（含已下架），点进详情却 404 会很莫名其妙。
    if goods.state != STATE_ON and not is_self:
        raise Http404("商品不存在")

    seller = User.objects.filter(id=goods.user_id).first()
    catelog_obj = Catelog.objects.filter(id=goods.catelog_id).first()
    comments = list(Comments.objects.filter(goods_id=id).order_by("id"))
    _attach_comment_users(comments)

    # 列表和商品对象都转成 JSON 安全的 dict，模板里一份用于服务端渲染、
    # 一份 |tojson 交给前端 JS（原版是 Jackson 序列化 Java 对象）。
    goods_extend = cards([goods])[0]

    return render(
        request,
        "goods/detailGoods.html",
        {
            "goodsExtend": goods_extend,
            "goodsExtendJson": card_json(goods_extend),
            "seller": seller,
            "catelog": catelog_obj,
            "commentsList": comments,
            "search": (request.GET.get("str") or "").strip(),
            "active_catelog": None,
            # 卖家信息区那个按钮要显示「关注」还是「已关注」。
            # 自己看自己的商品时干脆不渲染按钮 —— follow 那边也挡了自关注，
            # 但渲染一个点了没反应的按钮更糟。
            "isSelf": is_self,
            "followed": bool(me and seller and not is_self
                             and Follow.objects.filter(
                                 user_id=me["id"], follow_user_id=seller.id
                             ).exists()),
            # 「联系卖家」点过之后要变成「继续沟通」，否则用户分不清自己是
            # 还没联系过、还是早聊过了。只看「我有没有给这位卖家发过」，
            # 对方给我发过不算 —— 那样按钮写着「继续沟通」但我一句话没说，很怪。
            "contacted": bool(me and seller and not is_self
                              and Message.objects.filter(
                                  from_user_id=me["id"], to_user_id=seller.id
                              ).exists()),
        },
    )


def _attach_comment_users(comments):
    """把每条评论**就地换成**带 user / atuser 的 dict。

    模板要显示评论人和被回复人的昵称（`item.user.username`）；
    前端 `static/js/goods/detailGoods.js` 要的是 `commentsList[i].userId`，
    而且它把这个数组当 JS 全局变量用（`var commentsList = ...` 在页面里声明）。

    所以这里统一产出 **camelCase 的 dict**，服务端渲染和 `|tojson` 共用同一份，
    不搞两套并行结构 —— 两套迟早会对不上。
    """
    if not comments:
        return comments

    ids = set()
    for c in comments:
        if c.user_id:
            ids.add(c.user_id)
        if c.atuser_id:
            ids.add(c.atuser_id)
    by_id = {u.id: u for u in User.objects.filter(id__in=ids)} if ids else {}

    def brief(user):
        if user is None:
            return None
        return {"id": user.id, "username": user.username, "avatarUrl": user.avatar_url}

    rows = []
    for c in comments:
        # atuser_id == 0 表示「不是回复某个人」，原版就是这么约定的，照抄。
        at = by_id.get(c.atuser_id) if c.atuser_id else None
        rows.append(
            {
                "id": c.id,
                "userId": c.user_id,
                "atuserId": c.atuser_id or 0,
                "goodsId": c.goods_id,
                "content": c.content,
                "createAt": c.create_at,
                "user": brief(by_id.get(c.user_id)),
                "atuser": brief(at),
            }
        )
    # 原地替换：调用方拿到的还是同一个 list 对象
    comments[:] = rows
    return comments


# ================================================================ 标记已售出

@require_POST
def set_sold(request, id):
    """标记「已售出」或恢复「在售」。表单字段 sold = 0 / 1。

    几个刻意的选择（原版注释里的理由，一条都保留）：
      - **POST 不是 GET** —— 这是改状态的动作。用 GET 的话浏览器预取、
        爬虫、甚至用户手滑点两下都会把它改掉。
      - **重定向回 Referer 而不是固定回「我的闲置」** —— 这个按钮在首页、
        分类页、搜索页、详情页上都有，固定跳回一处用户会被弹走。
      - **越权校验在这里**，不在模板里。模板藏起按钮只是不显示，
        手搓一个 POST 照样能提交上来。
      - 失败时**不区分**「商品不存在」和「不是你的」—— 区分了就等于
        告诉对方这个 id 是有效的。
    """
    me = auth.current(request)
    if not me:
        return redirect("goods_home")

    sold = request.POST.get("sold")
    try:
        sold = int(sold) if sold is not None else SOLD_YES
    except (TypeError, ValueError):
        sold = SOLD_YES
    # 只接受 0 / 1，别的一律当非法请求，不往库里写奇怪的值
    if sold not in (SOLD_NO, SOLD_YES):
        return back(request, "user_goods")

    # 一条只改 sold 的 UPDATE。**绝不能**走「先查出来再整条 save()」——
    # 「标记已售出」手里并没有完整的商品对象，整条写回会把商品名、价格、
    # 描述一起冲成空。where 里带上 user_id 就是属主校验：不是自己的货，
    # 影响 0 行，静默失败（这是有意的，见上面第 4 条）。
    Goods.objects.filter(id=id, user_id=me["id"]).update(sold=sold)
    return back(request, "user_goods")


@require_POST
def set_state(request, id):
    """下架 / 重新上架自己的商品。表单字段 state = 0 / 1。

    这是**重写时新做的一个功能**。原版页面上有「下架」这两个字，但背后是空的：

      · 用户侧那个按钮指向 `/goods/offGoods`，而那个方法体只有一句
        `return null;` —— 点了什么都不发生。
      · 后台那个也叫「下架」的按钮倒是真干活，干的是**硬删**
        （`deleteGoodsByPrimaryKey`），而且文案看不出来。

    更关键的是，`state` 这一列在原版**任何一条 SELECT 里都没有被过滤过**，
    所以就算把值改对了，下架的商品照样挂在首页上。重写时先在前台查询里
    统一加了 `state = STATE_ON`（见 goods/models.py: FRONT_VISIBLE），
    这个按钮才真正有了意义。

    和 set_sold 的分工（两列语义不同，互不影响）：
      · `sold` = 卖掉了没有。只影响角标，商品照样在列表里挂着
      · `state` = 有没有收起来。收起来之后前台**查不到**，但
        后台和「我的闲置」还看得见（否则用户下架完就找不回来了）

    几个刻意的选择跟 set_sold 一模一样：POST 不是 GET、重定向回来源页、
    越权校验写在 WHERE 里、失败时不区分「商品不存在」和「不是你的」。
    """
    me = auth.current(request)
    if not me:
        return redirect("goods_home")

    raw = request.POST.get("state")
    try:
        state = int(raw) if raw is not None else STATE_OFF
    except (TypeError, ValueError):
        state = STATE_OFF
    # 只接受 0 / 1。2（审核中）是给后台审核流程留的，用户自己不能设成那个状态
    if state not in (STATE_ON, STATE_OFF):
        return back(request, "user_goods")

    # 一条只改 state 的 UPDATE。和 set_sold 同样的道理：**绝不能**走
    # 「先查出来再整条 save()」，那会把商品名、价格、描述一起冲空。
    # WHERE 里的 user_id 就是属主校验，不是自己的货影响 0 行。
    Goods.objects.filter(id=id, user_id=me["id"]).update(state=state)
    return back(request, "user_goods")


# ================================================================ 发布 / 编辑 / 删除

def publish(request):
    """发布页。未登录直接弹回首页（原版就是 `redirect:/goods/homeGoods`）。

    `form` 传一个空 dict：模板里每个输入框都写的是
    `value="{{ form.name|default('', true) }}"`，用来在**提交失败**时把用户
    已经填好的内容回填（那条路径传的是 request.POST）。第一次打开这一页时
    没有 form，不传的话 Jinja2 直接 UndefinedError、整页 500。
    （模板里靠 `|default('', true)` 把「取不到」变成空字符串。）
    """
    if not auth.current(request):
        return redirect("goods_home")
    return render(
        request, "goods/pubGoods.html", {"catelogs": CATELOG_OPTIONS, "form": {}}
    )


@require_POST
def publish_submit(request):
    """提交发布。

    原版这里跨 5 步写库却**没有事务**：插商品 → 插图片 → 分类计数 +1 →
    用户闲置数 +1 → 记一条站内通知。中间任何一步炸了，前面写进去的
    脏数据就留在库里（比如商品已上架但 goods_num 没加）。
    这里用 `transaction.atomic()` 包起来，要么全成要么全不成。
    """
    me = auth.current(request)
    if not me:
        return redirect("goods_home")

    fields, error = _goods_form(request.POST)
    if error:
        # 回填用户已填的内容，别让人重打一遍
        return render(
            request,
            "goods/pubGoods.html",
            {"catelogs": CATELOG_OPTIONS, "formError": error, "form": request.POST},
        )

    today = now_day()
    with transaction.atomic():
        goods = Goods.objects.create(
            catelog_id=fields["catelog_id"],
            user_id=me["id"],
            name=fields["name"],
            price=fields["price"],
            real_price=fields["real_price"],
            start_time=today,
            polish_time=today,
            # 原版固定给 10 天（GoodsController 硬编码的字面量 10）
            end_time=days_later(today, GOODS_DURATION_DAYS),
            describle=fields["describle"],
            # commet_num 不写：原版 insert 里塞的是 null，全库 14 行也确实都是
            # NULL（评论数是查询时 GROUP BY 现算的，这一列没人读）
            state=STATE_ON,
            sold=SOLD_NO,
        )

        img_url = (request.POST.get("imgUrl") or "").strip()
        # 原版不管有没有图都往 t_shop_image 插一条。图没传上来时
        # img_url 是空串，详情页的封面就变成 "/upload/" 后面空着 —— 一张裂图。
        # 这里没图就不插，列表页会走 DEFAULT_GOODS_IMAGE 的占位图。
        if img_url:
            Image.objects.create(goods_id=goods.id, img_url=img_url)

        # 原版是「先 select 出 number，再 +1 写回」，两个请求同时发布就会互相盖掉。
        # 用 F() 让数据库自己算，一条 UPDATE 搞定。
        Catelog.objects.filter(id=fields["catelog_id"]).update(number=F("number") + 1)
        User.objects.filter(id=me["id"]).update(goods_num=F("goods_num") + 1)

        Notice.objects.create(
            user_id=me["id"],
            context=f"你发布的「{fields['name']}」已经上架，可在「我的闲置」里查看。",
            create_at=now_time(),
            # 这一列没有数据库默认值，必须显式给
            status=0,
        )

    # session 里那个 goodsNum 也要跟着走，否则左侧栏的「闲置数量」要等重新登录才更新。
    # 必须整个 dict 重新赋值（core.auth.refresh 里有说明）。
    auth.refresh(request, goodsNum=(me.get("goodsNum") or 0) + 1)
    return redirect("user_goods")


def edit(request, id):
    """编辑页。

    **属主校验在这一步就做**：原版 editGoods 只按 id 查商品、不比对当前用户，
    改一下 URL 里的 id 就能打开别人的商品编辑页（提交那一步虽然有个
    `goods.setUserId(cur_user.getId())`，但那是把别人的货**过户给自己**，
    不是拦截）。不是自己的货一律 404，不提示「这不是你的」。
    """
    me = auth.current(request)
    if not me:
        return redirect("goods_home")

    goods = Goods.objects.filter(id=id, user_id=me["id"]).first()
    if goods is None:
        raise Http404("商品不存在")

    return render(
        request,
        "goods/editGoods.html",
        {
            "goodsExtend": cards([goods])[0],
            "catelogs": CATELOG_OPTIONS,
        },
    )


@require_POST
def edit_submit(request):
    """提交编辑。

    用一条 UPDATE 写，**不碰 user_id** —— 属主是 WHERE 里的条件，不是写进去的值。
    原版的 `goods.setUserId(cur_user.getId())` 会把商品过户给操作者，
    这里从根上没有了。

    也没写 `commet_num`：原版的 updateByPrimaryKeyWithBLOBs 是整行覆盖，
    而表单根本没提交这个字段，于是每次编辑都把评论数冲成 NULL。
    （全库本来就是 NULL、也没人读，但没必要写这一笔。）
    """
    me = auth.current(request)
    if not me:
        return redirect("goods_home")

    try:
        goods_id = int(request.POST.get("id") or 0)
    except (TypeError, ValueError):
        goods_id = 0

    fields, error = _goods_form(request.POST)
    if error or not goods_id:
        return back(request, "user_goods")

    # 前端把开始/结束时间放在隐藏域里带过来，原版就是这么保住这两列的。
    # 拿不到就保持库里的原值（传 None 给 update 会写成 NULL，那是数据丢失）。
    start_time = (request.POST.get("startTime") or "").strip()
    end_time = (request.POST.get("endTime") or "").strip()

    changes = {
        "catelog_id": fields["catelog_id"],
        "name": fields["name"],
        "price": fields["price"],
        "real_price": fields["real_price"],
        "describle": fields["describle"],
        # 改过就重新擦亮，让它回到首页/分类页的最前面（原版行为）
        "polish_time": now_day(),
    }
    if start_time:
        changes["start_time"] = start_time
    if end_time:
        changes["end_time"] = end_time

    # 先查出来（WHERE 里带 user_id 就是属主校验），换分类时要同步调计数
    goods = Goods.objects.filter(id=goods_id, user_id=me["id"]).first()
    if goods is None:
        raise Http404("商品不存在")

    with transaction.atomic():
        # 换分类要把两边的计数对着调，和后台 api_update_goods 同一套做法：
        # 发布是给当时所属分类 +1、删除是 -1，编辑换了分类却不动计数的话，
        # 旧分类永久虚高、新分类永久虚低，分类导航上的数字就再也对不上了
        if fields["catelog_id"] != goods.catelog_id:
            if goods.catelog_id:
                Catelog.objects.filter(id=goods.catelog_id, number__gt=0).update(
                    number=F("number") - 1
                )
            Catelog.objects.filter(id=fields["catelog_id"]).update(
                number=F("number") + 1
            )
        Goods.objects.filter(id=goods_id).update(**changes)

    return redirect("user_goods")


@require_POST
def delete_goods(request, id):
    """删除自己的商品。

    原版 `deleteGoods` **没有任何属主校验**，任何登录用户改一下 URL 里的 id
    就能删掉别人的商品。这里四个动作全限制在自己的货上。

    顺带把分类计数和用户闲置数减回来（原版也做了这两步），
    只是改用 F() 一条 UPDATE，不再「先查再写」。

    用 POST 不用 GET：这是删数据的动作，GET 会被浏览器预取和爬虫踩到。
    原版的模板是用 `<a href>` 点一下就删的，重写时改成了带 confirm 的表单按钮。
    """
    me = auth.current(request)
    if not me:
        return redirect("goods_home")

    goods = Goods.objects.filter(id=id, user_id=me["id"]).first()
    if goods is None:
        # 同样不区分「商品不存在」和「不是你的」
        return redirect("user_goods")

    with transaction.atomic():
        _remove_goods(goods)

    auth.refresh(request, goodsNum=max((me.get("goodsNum") or 0) - 1, 0))
    return redirect("user_goods")


def _remove_goods(goods):
    """把一个商品连同它的图片一起删掉，并把两处计数减回来。

    两个调用方共用这一段：用户自己删（`delete_goods`）和后台删（`api_off_goods`）。

    原版后台那条接口只调了一次 `deleteGoodsByPrimaryKey` —— 图片行留在库里、
    分类计数和用户的闲置数也不减，删完就是一条对不上的孤儿数据。
    这里让两条路径做同一件事。

    两个坑：
      - 删图片必须在删商品**之前**。表之间没有外键约束，反过来商品没了、
        图片记录还挂在库里，而且再也没人知道它们属于哪件商品了。
      - `id` / `catelog_id` / `user_id` 要在 `delete()` **之前**读出来 ——
        删完 Django 会把实例的主键置成 None。
    """
    goods_id = goods.id
    catelog_id = goods.catelog_id
    owner_id = goods.user_id

    Image.objects.filter(goods_id=goods_id).delete()
    goods.delete()

    # `number__gt=0`：已经数到 0 就别再减成负数了。
    # 用 F() 在数据库里算，别「先 select 出来再写回」—— 两端同时删会互相盖掉。
    if catelog_id:
        Catelog.objects.filter(id=catelog_id, number__gt=0).update(
            number=F("number") - 1
        )
    if owner_id:
        User.objects.filter(id=owner_id, goods_num__gt=0).update(
            goods_num=F("goods_num") - 1
        )


# ================================================================ 图片上传

@require_POST
def upload_file(request):
    """商品图上传接口。

    **返回的不是标准 AjaxResult**，别顺手改成 core.ajax.ok/fail ——
    原版这里返回的是一个裸 Map，就两个键：

        成功  {"success": "成功啦", "imgUrl": "<uuid>.jpg"}
        失败  {"error": "图片不合法"}

    前端 `static/js/goods/` 里的 fileinput 插件读的是 `data.response.imgUrl`，
    改了键名上传就白传了。契约照抄，连「成功啦」这个字符串都不动。
    """
    new_name = store_image(request.FILES.get("myfile"))
    if not new_name:
        return JsonResponse({"error": "图片不合法"})
    return JsonResponse({"success": "成功啦", "imgUrl": new_name})


# ================================================================ 后台接口
#
# 原版 `GoodsController` 末尾那两个挂在 `/api/...` 上的动作。调用方只有一个：
# `static/js/manage/manage-goodsList.js`（后台商品管理页）。
#
# **原版这两个接口都没有任何权限校验。** `/goods/api/offGoods/{id}` 更是
# 直接按 id 硬删商品 —— 任何登录用户手搓一个请求就能删掉别人的货，
# 和 `deleteGoods` 那个「改 URL 里的 id 就删别人的货」是同一个洞，只是入口在后门。
# 重写时一起补上 `admin_api`，见 README 的「行为变更」。

@admin_api
@require_POST
def api_update_goods(request):
    """POST /goods/api/updateGoods —— 后台商品管理页的「保存」。

    请求体（JSON，由 manage-goodsList.js 拼出来）：
        {id, catelogId, userId, name, price, realPrice,
         startTime, endTime, polishTime, commetNum, describle}

    原版是 `@RequestBody Goods` 直接绑一个 Java 对象，再走一条把九列全
    `set` 一遍的整行 UPDATE。这里改成**逐列判断**：

      - `userId` **不写**。那一格在页面上是 readonly（发布人不能改），
        传上来的就是当前值，写回去等于没写；不写则顺手堵死了
        「构造一个请求把货过户给别人」这条路。
      - `commetNum` **不写**。这一列原版就没维护过（全库是 NULL），
        页面上那一格也永远是空的；写它是把「查询时现算的评论数」
        覆盖成一个假数字。
      - `polishTime` / `startTime` / `endTime` 只在**真传了非空值**时才写。
        空值写进去会让商品在首页排到最后（polish_time 是排序键），
        或者留下一个空的开始时间 —— 都不是管理员想干的事。

    **和原版有意不同的一处：换分类时会同步调 `t_shop_catelog.number`。**
    见下面那段注释，用户 2026-10-08 确认过。
    """
    body = json_body(request)
    if body is None:
        return fail(message="请求格式不正确。")

    goods_id = _int_or_zero(body.get("id"))
    if not goods_id:
        return fail(message="商品不存在。")

    name = (body.get("name") or "").strip()
    if not name:
        # 原版不校验：物品名清空就存一条空名字的商品，列表页那一格空白。
        return fail(message="商品名不能为空。")

    catelog_id = _int_or_zero(body.get("catelogId"))
    # 和后台编辑弹层的下拉同一口径（status=1 的分类，来自数据库），
    # 不用前台那份硬编码的 CATELOG_IDS：库里存在 id=8 这类不在 1-7 里的
    # 分类，用硬编码校验会让这类商品在后台永远保存不了
    if not Catelog.objects.filter(id=catelog_id, status=1).exists():
        return fail(message="请选择一个物品类别。")

    changes = {
        "catelog_id": catelog_id,
        "name": name,
        # 价格框被清空时原版会把这两列写成 NULL（Jackson 把 "" 转成 null），
        # 照抄：这两个值在这一页是可清的。
        "price": _float_or_none(body.get("price")),
        "real_price": _float_or_none(body.get("realPrice")),
        "describle": body.get("describle") or "",
    }
    for field, key in (
        ("polish_time", "polishTime"),
        ("start_time", "startTime"),
        ("end_time", "endTime"),
    ):
        value = (body.get(key) or "").strip()
        if value:
            changes[field] = value

    goods = Goods.objects.filter(id=goods_id).first()
    if goods is None:
        # 原版这时候影响 0 行、也照样回一个成功响应，前端拿到 success 就刷页面。
        # 这里回 ok(False) 意思一样（manage-goodsList.js 只看 success 那个键）。
        return ok(False)

    with transaction.atomic():
        # 换分类要把两边的计数对着调。
        #
        # 原版那条 UPDATE 只写 goods.catelog_id，不碰 t_shop_catelog.number，
        # 而发布是给商品**当时**所属的分类 +1、删除是给它**当时**所属的分类 -1。
        # 中间在后台悄悄换一次分类，那两笔账就再也对不上了：旧分类永久虚高 1、
        # 新分类永久虚低 1，首页分类导航上那两个数字跟着一直错下去。
        #
        # 用户 2026-10-08 选的是「改分类时同步调计数」。库里现存的虚高数字
        # （「闲置数码」写着 19、实际只有 2 件）**不动** —— 那是原版攒下的历史账。
        if catelog_id != goods.catelog_id:
            if goods.catelog_id:
                Catelog.objects.filter(id=goods.catelog_id, number__gt=0).update(
                    number=F("number") - 1
                )
            Catelog.objects.filter(id=catelog_id).update(number=F("number") + 1)

        Goods.objects.filter(id=goods_id).update(**changes)

    return ok(True)


@admin_api
@require_http_methods(["DELETE"])
def api_off_goods(request, id):
    """DELETE /goods/api/offGoods/{id} —— 后台商品管理页的「删除」。

    **真的是硬删，不是下架。** 原版方法体里就是一句
    `deleteGoodsByPrimaryKey(id)`，而按钮上的文案写的是「下架」——
    管理员以为只是把商品收起来，实际那一行已经没了。

    和用户确认过的处理（见计划 P7 一节）：**后台这个按钮保持硬删**，
    只把文案改成「删除」并加二次确认；用户侧那个「下架 / 重新上架」
    才是真的改 state。

    用 DELETE 不用 POST 是照抄原版（`@DeleteMapping`），manage-goodsList.js
    里写的也是 `type: "DELETE"`，改方法名会同时废掉前端。
    """
    goods = Goods.objects.filter(id=id).first()
    if goods is None:
        return ok(False)

    with transaction.atomic():
        _remove_goods(goods)
    return ok(True)


# ================================================================ 评论接口
#
# 原版 `CommentsController`，三个接口，路径 `/comments/api/...`。
# 前端是 `static/js/goods/detailGoods.js`，它读的返回形状见 core/ajax.py。
#
# **三个接口原版都没有任何属主校验**，这是重写时补的（见 README「行为变更」）：
#   - addComments 完全信任请求体里的 userId 字段 → 谁都能冒充别人发评论
#   - updateComments 的 SQL 是整行覆盖，连 user_id 一起改 → 能把别人的评论过户给自己
#   - deleteComments 只按 id 删 → 谁都能删任何一条评论
#
# 补法统一是「身份只认 session，权限写进 WHERE」。

@require_POST
@ajax_login_required
def comments_add(request):
    """POST /comments/api/addComments —— 发一条评论或回复。

    请求体（JSON）：`{userId, atuserId, goodsId, content}`。

    **`userId` 不读**。原版直接用它建记录，也就是说把请求体里的 userId 换成
    别人就能以别人的名义发评论。这里一律用 session 里那个 id。
    （前端脚本照旧传着这个字段，不用改 JS —— 契约没变，只是后端不信它了。）

    `atuserId` 为 0 表示「不是回复某个人」，这是原版就有的约定，
    和 `_attach_comment_users` 那边一致。
    """
    me = auth.current(request)
    body = json_body(request)
    if body is None:
        return fail(message="请求格式不正确。")

    goods_id = _int_or_zero(body.get("goodsId"))
    goods = Goods.objects.filter(id=goods_id).first() if goods_id else None
    if goods is None:
        return fail(message="商品不存在。")

    # 已售出的商品不给再发新评论。前端的输入框在 sold=1 时整块不渲染，
    # 但那只是「不显示」—— 手搓一个请求照样能提交上来，所以后端也挡一道。
    if goods.sold == SOLD_YES:
        return fail(message="该商品已售出，无法再发表评论。")

    # 已下架的商品别人连详情页都打不开（404），接口这边也挡一道，
    # 不然手搓一个 POST 照样能给它加评论。货主自己不受限：
    # 他能打开自己的下架商品详情页，页面上评论框也照常渲染。
    if goods.state != STATE_ON and goods.user_id != me["id"]:
        return fail(message="该商品已下架，无法发表评论。")

    content = (body.get("content") or "").strip()
    if not content:
        return fail(message="评论内容不能为空。")

    atuser_id = _int_or_zero(body.get("atuserId"))
    # 回复对象必须真实存在，否则详情页那行「回复 @谁」会渲染成一个空名字。
    # 正常路径下这个 id 来自页面上已有的评论，不会出错；挡住的是手工伪造的请求。
    if atuser_id and not User.objects.filter(id=atuser_id).exists():
        return fail(message="回复的用户不存在。")

    comment = Comments.objects.create(
        user_id=me["id"],
        atuser_id=atuser_id,
        goods_id=goods_id,
        content=content,
        create_at=now_time(),
    )

    # 原版返回的是 `commentsService.addComments(...)` 的返回值，而那个是
    # MyBatis insert 的**影响行数**（恒为 1），不是一个 id。
    # 这里返回新评论的真实 id —— 前端脚本没读 data，改掉不影响它，
    # 但把「id」这个名字对应的东西还给它。
    return ok(comment.id)


@require_POST
@ajax_login_required
def comments_update(request):
    """POST /comments/api/updateComments —— 改自己写的评论。

    **只改 content**。原版走的是 `updateByPrimaryKeyWithBLOBs`（整行覆盖），
    请求体里带上 `goodsId` 或 `userId` 就能把一条评论挪到别的商品下、
    或者过户给别人。表单上没提交的字段不该被这一次请求碰。

    WHERE 里带 `user_id` 就是属主校验：不是自己的评论，影响 0 行，
    返回 `false` 而不是报错（不告诉对方这条评论存不存在）。
    """
    me = auth.current(request)
    body = json_body(request)
    if body is None:
        return fail(message="请求格式不正确。")

    comment_id = _int_or_zero(body.get("id"))
    content = (body.get("content") or "").strip()
    if not comment_id or not content:
        return fail(message="评论不存在或内容为空。")

    updated = Comments.objects.filter(id=comment_id, user_id=me["id"]).update(
        content=content
    )
    return ok(bool(updated))


@require_http_methods(["DELETE"])
@ajax_login_required
def comments_delete(request, id):
    """DELETE /comments/api/deleteComments/{id} —— 删自己写的评论。

    用 DELETE 不用 POST 是**照抄原版**（`@DeleteMapping`），前端
    detailGoods.js 里写的也是 `type: "DELETE"`。改方法名会同时废掉前端。

    属主校验同样在 WHERE 里。原版只按 id 删，改一下 URL 上的 id
    就能删掉任何人的评论。
    """
    me = auth.current(request)
    deleted = Comments.objects.filter(id=id, user_id=me["id"]).delete()[0]
    return ok(bool(deleted))


def _int_or_zero(raw):
    """把 JSON 里的一个数字字段转成 int，转不动就 0。

    0 在这些接口里是一个**合法值**（`atuserId: 0` 就是「不是回复」），
    所以不能用 None 表示失败。不合法的一律折成 0，由调用方各自判断。
    """
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


# ================================================================ 表单解析

def _goods_form(post):
    """把发布/编辑表单解析成能直接写库的字段。

    返回 `(fields, None)` 或 `(None, "错误提示")`。

    原版不做任何校验，字段直接绑到 Java 对象上：物品名留空就存一条空名字的商品，
    价格填「一百块」会让 Spring 绑定失败、直接甩一个 400 错误页。
    这里给一句中文提示并把已填内容回填，比 400 页面有用。
    """
    name = (post.get("name") or "").strip()
    if not name:
        return None, "请填写物品名。"

    price = _float_or_none(post.get("price"))
    if price is None or price < 0:
        return None, "出售价格要填一个不小于 0 的数字。"

    # 原价选填。填了负数或者乱码就当没填，不必为它拦下整次提交。
    real_price = _float_or_none(post.get("realPrice"))
    if real_price is not None and real_price < 0:
        real_price = None

    try:
        catelog_id = int(post.get("catelogId") or 0)
    except (TypeError, ValueError):
        catelog_id = 0
    if catelog_id not in CATELOG_IDS:
        return None, "请选择一个物品类别。"

    return (
        {
            "name": name,
            "price": price,
            "real_price": real_price,
            "catelog_id": catelog_id,
            "describle": post.get("describle") or "",
        },
        None,
    )


def _float_or_none(raw):
    """把表单里的一格文本转成 float。空 / 非数字 / NaN / Infinity 一律返回 None。

    NaN 和 Infinity 得单独挡：`float("nan")` 是合法的、`float("inf")` 也是，
    放过去会让价格比较得出一个诡异结果（NaN 参与的比较永远为假，
    筛选条件会静默失效）。
    """
    text = (raw or "").strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return value
