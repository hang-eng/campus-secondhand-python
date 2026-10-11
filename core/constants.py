"""
常量。对应原版 Java 的 `common/GgeeConst.java`，外加几个重写新增的。

命名尽量保持原样（CUR_USER / LOGIN_ERROR / ...），方便和 Java 版对照。
会话里存的 key 用的就是原版那几个字符串，两边行为对齐。
"""

# ---------------------------------------------------------------- 会话 key

# 原版 GgeeConst.CUR_USER
CUR_USER = "cur_user"
# 原版 GgeeConst.LOGIN_ERROR / LOGIN_PHONE，登录失败时写进 session，页面读一次即删
LOGIN_ERROR = "loginError"
LOGIN_PHONE = "loginPhone"
# 原版 GgeeConst.DATA，后台分页数据塞在一个 map 里
DATA = "data"
# 机器人对话历史（原版 RobotController 的 session key）
ROBOT_SESSION = "robotSession"
ROBOT_ERROR = "robotError"

# 新增：本次登录里已经点过「请求」或「同意」交换联系方式的人。见 chat/services.py
CONTACT_OK = "contact_ok"


# ---------------------------------------------------------------- 分页

# 原版 GgeeConst.userPageSize / goodsPageSize
USER_PAGE_SIZE = 10
GOODS_PAGE_SIZE = 16

# 首页每个分类板块显示几件。原版 GoodsController.homeGoods 里写死的 goodsSize = 6，
# 和列表页的 GOODS_PAGE_SIZE 不是一回事，别合并。
GOODS_PER_SECTION = 6


# ---------------------------------------------------------------- 头像

# 原版 UserController.PRESET_AVATARS，6 张内置图
PRESET_AVATARS = [
    "/img/photo.jpg",
    "/img/photo1.jpg",
    "/img/photo2.jpg",
    "/img/photo3.jpg",
    "/img/photo4.jpg",
    "/img/photo5.jpg",
]

# 允许上传的图片扩展名。头像和商品图共用一份 —— 原版两边各写各的，
# 商品图那边其实**什么都不校验**（见 core/uploads.py 的说明）。
# 注意故意不含 .svg（svg 能带脚本）。
ALLOWED_IMAGE_EXT = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]

# 用户没设过头像时显示这张（原版 User.getAvatarUrl() 的兜底）
DEFAULT_AVATAR = "/img/photo.jpg"

# 商品一张图都没有时列表里显示的占位图。
# 原版没有这个兜底：模板写的是 `items.images[0].imgUrl`，
# 商品没图就是 SpEL 越界、整页 500。重写时兜一张，宁可显示占位图。
DEFAULT_GOODS_IMAGE = "/img/photo.jpg"

# 单张图片体积上限。原版模板上写着「单张不超过 10M」但**代码里没查**，
# 这里补上，让界面上的承诺和实际行为一致。头像和商品图共用。
MAX_UPLOAD_IMAGE_SIZE = 10 * 1024 * 1024


# ---------------------------------------------------------------- 权限

# 原版判断管理员就是 User.power == 90
ADMIN_POWER = 90

# 普通用户。原版没有这个常量（到处直接写 10），补一个让上面那条成对。
# 后台「添加用户 / 编辑用户」那两个下拉框里也只有这两个值。
USER_POWER = 10

# 发布商品默认上架天数（原版 GoodsController 固定传 10）
GOODS_DURATION_DAYS = 10


# ---------------------------------------------------------------- 商品状态

# t_shop_goods.state
STATE_ON = 0  # 进行中（在售）
STATE_OFF = 1  # 已下架
STATE_AUDIT = 2  # 审核中

# t_shop_goods.sold
SOLD_NO = 0  # 在售
SOLD_YES = 1  # 已售出


# ---------------------------------------------------------------- 私信

# 原版 MessageServiceImpl.MAX_LENGTH
MESSAGE_MAX_LENGTH = 500

# t_shop_contact_request.status
CONTACT_PENDING = 0  # 已请求，等对方处理
CONTACT_AGREED = 1  # 双方同意
CONTACT_REFUSED = 2  # 被拒绝


# ---------------------------------------------------------------- 界面字体大小
#
# **重写时新增的功能**（个人设置里那个「界面字体大小」）。
#
# 存进库的是**短码**（s / m / l / xl），不是百分比：
#   · 百分比属于「长什么样」，写在 static/css/campus.css 最后一节，
#     以后想把「大」从 110% 调成 115%，改 CSS 一行，不用 UPDATE 全库数据；
#   · 库里存 'l' 这种短码，一眼能看出是哪个档，出问题好查。
#
# 每个元素是 (短码, 界面上显示的名字, 缩放百分比)。
# 百分比这一列只用于**在设置页面上显示**「大（110%）」给人看，
# 真正的缩放值写在 CSS 里 —— 两处必须对上，改一个记得改另一个。
FONT_SIZE_DEFAULT = "m"
FONT_SIZES = (
    ("s", "小", "90%"),
    ("m", "标准", "100%"),
    ("l", "大", "110%"),
    ("xl", "特大", "120%"),
)
# 白名单。表单传上来的值只认这几个，别的一律不写库。
FONT_SIZE_CODES = frozenset(code for code, _, _ in FONT_SIZES)
