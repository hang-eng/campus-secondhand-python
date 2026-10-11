"""
上传文件落盘。

头像和商品图**存法不一样**，这是原版的历史不一致，重写时照抄：

  - 头像（`t_shop_user.avatar`）存**完整 web 路径**，`/upload/<uuid>.jpg`
  - 商品图（`t_shop_image.img_url`）只存**文件名**，`<uuid>.jpg`
    （模板自己拼 `/upload/` 前缀）

所以这里只负责「校验 + 落盘 + 生成新文件名」，返回**裸文件名**；
要不要加 `/upload/` 前缀由调用方决定。
"""

import uuid

from django.conf import settings

from .constants import ALLOWED_IMAGE_EXT, MAX_UPLOAD_IMAGE_SIZE


def image_ext(filename):
    """取小写扩展名（含点）。没有扩展名返回空串。"""
    name = filename or ""
    dot = name.rfind(".")
    return name[dot:].lower() if dot >= 0 else ""


# 各图片格式的文件头魔数。扩展名和 Content-Type 都能伪造，文件头不行。
_MAGIC = (
    b"\xff\xd8\xff",                    # JPEG
    b"\x89PNG\r\n\x1a\n",               # PNG
    b"GIF87a", b"GIF89a",               # GIF
    b"BM",                              # BMP
)


def _looks_like_image(file):
    """读文件头验证内容真的是图片（JPEG/PNG/GIF/BMP/WebP）。

    扩展名白名单和客户端自报的 Content-Type 都能伪造，这是第三道校验。
    不引 Pillow：项目依赖里没有它，为这一处加一个 C 扩展依赖不值。
    """
    try:
        head = file.read(12)
    finally:
        # 读完必须倒回去，后面 chunks() 要从头再读一遍
        file.seek(0)
    if not head:
        return False
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return True
    return any(head.startswith(magic) for magic in _MAGIC)


def store_image(file, max_size=MAX_UPLOAD_IMAGE_SIZE):
    """把上传的图片落盘到 `upload/images/`，返回新文件名；不合法返回 None。

    三道校验，一道都不省：
      1. 扩展名在白名单里（统一转小写再比）
      2. Content-Type 以 image/ 开头
      3. 体积不超过 max_size

    第 3 条是重写时加的：原版模板上写着「单张不超过 10M」，
    但代码里根本没查，10M 的承诺是空的。

    第 1 条也是加的。原版 `uploadFile` 直接拿 `oldFileName` 里最后一个点
    后面的部分当扩展名、原名作废，**不检查是什么类型** ——
    上传一个 .jsp/.html 就能落进静态目录里。本项目是 Django 不走 JSP 容器，
    但这个口子没理由留着。
    """
    if file is None:
        return None

    ext = image_ext(file.name)
    if ext not in ALLOWED_IMAGE_EXT:
        return None

    # 不信任客户端传来的 Content-Type（那个是浏览器说的，随便改），
    # 但作为第二道过滤仍然有用：能挡住「改了扩展名的脚本文件」
    content_type = getattr(file, "content_type", "") or ""
    if not content_type.startswith("image/"):
        return None

    if file.size > max_size:
        return None

    # 第三道：文件头魔数。改了扩展名、伪造了 Content-Type 的脚本文件
    # 走到这里就过不去了
    if not _looks_like_image(file):
        return None

    new_name = f"{uuid.uuid4()}{ext}"
    target = settings.UPLOAD_ROOT / new_name
    # 目录可能被整个删掉过（清理测试文件时就这么干过），先确保它在
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "wb") as fh:
        # chunks() 而不是 .read()：10M 的图整个读进内存没必要
        for chunk in file.chunks():
            fh.write(chunk)
    return new_name
