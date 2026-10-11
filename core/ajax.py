"""
JSON 接口的统一返回格式。对应原版 Java 的 `dto/AjaxResult.java`。

形状**逐字照抄**，因为 `manage-userList.js` / `manage-goodsList.js` /
`detailGoods.js` 这些前端脚本是照这个形状写的，改了它们就读不懂返回值：

    成功：{"message": "", "success": true,  "data": ...}
    失败：{"message": "密码错误", "success": false, "code": 3003}

两个细节别改：
  - **成功时没有 `code` 键**。原版 AjaxResult 只有 setState()（失败路径）
    才 put(CODE)，setData() 只有 message/success/data。
  - 失败时**不是** HTTP 4xx/5xx，是 HTTP 200 + success:false。
    所以这里的 fail() 默认返回 200，见下面 fail() 的注释。
"""

import json

from django.http import JsonResponse

# 原版 GgeeWebError 枚举，码值和文案一起搬过来。
# 前端按 code 判断的地方（如果有）才不会对不上。
ERRORS = {
    3000: "服务器端出错",
    3001: "账号或密码错误",
    3002: "该账号不存在",
    3003: "密码错误",
    3004: "确认密码不一致",
    3005: "服务端解析文件出错",
    3006: "图片不合法",
    3007: "该电话号码已经注册过了",
    3008: "该账号已被冻结",
}

# 重写新增的两条，接着原版的码值往下排。
# 原版没有这两个场景（它那几个接口压根不校验权限），所以没有历史包袱。
CODE_FORBIDDEN = 3009
CODE_NOT_LOGIN = 3010
ERRORS[CODE_FORBIDDEN] = "没有权限"
ERRORS[CODE_NOT_LOGIN] = "请先登录"

# 原版 AjaxResult.COMMON_ERROR
COMMON = 3000


def ok(data=None):
    """成功。对应原版 `new AjaxResult().setData(x)`。"""
    return JsonResponse({"message": "", "success": True, "data": data})


def fail(code=COMMON, message=None, status=200):
    """失败。对应原版 `AjaxResult.fixedError(...)`。

    默认 HTTP 200 —— 原版就是 200，前端脚本的 success 回调里判 `data.success`。
    改成 403 会让 jQuery 走 error 回调，而那几个脚本的 error 回调大多没写，
    用户点了会「什么都不发生」。所以**鉴权失败也返回 200 + success:false**，
    让页面能弹出提示。status 参数留着给确实需要真 HTTP 码的地方用。
    """
    return JsonResponse(
        {
            "message": message or ERRORS.get(code, ERRORS[COMMON]),
            "success": False,
            "code": code,
        },
        status=status,
    )


def json_body(request):
    """解析 JSON 请求体，返回 dict；不是合法 JSON 就返回 None。

    原版这几个接口是 `@RequestBody` 收的（Spring 自己用 Jackson 反序列化），
    这里手动解析。坏 JSON 不能让整页 500 —— 原版那几个接口碰到畸形请求体
    也是走 catch 返回 3000，调用方按 None 处理即可。

    顺带挡掉「顶层不是对象」的情况（比如请求体是 `[1,2]` 或 `"abc"`）：
    那种情况下 `.get()` 会 AttributeError，而前端脚本按对象用返回值。
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return body if isinstance(body, dict) else None
