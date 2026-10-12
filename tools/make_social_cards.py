"""生成小红书/掘金配图（开发工具，不参与运行时）。

生成 2 张对比图：
  1) 参数对比：官方文档说的 vs 实际必须传的（code snippet风格）
  2) 菜单接口返回：为什么拿到菜单却不知道多少钱

用双色终端风格，中文用微软雅黑、ASCII 用 Consolas。

    python tools/make_social_cards.py
"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"

FONT_ASCII = "C:/Windows/Fonts/consola.ttf"
FONT_CJK = "C:/Windows/Fonts/msyh.ttc"

BG = (24, 26, 33)
CARD = (32, 35, 44)
BAR = (38, 41, 51)
FG = (203, 208, 216)
DIM = (120, 128, 145)
GREEN = (126, 208, 126)
RED = (238, 120, 116)
CYAN = (94, 200, 214)
YELLOW = (222, 180, 104)

FS = 26
FS_TITLE = 34
PAD = 40
LINE = 42


def is_cjk(ch: str) -> bool:
    if not isinstance(ch, str) or len(ch) != 1:
        raise TypeError(f"is_cjk 只接受单字符，收到: {type(ch).__name__} {str(ch)[:40]!r}")
    o = ord(ch)
    return 0x2E80 <= o <= 0x9FFF or 0xFF00 <= o <= 0xFFEF or 0x3000 <= o <= 0x303F


class Fonts:
    def __init__(self) -> None:
        self.a = ImageFont.truetype(FONT_ASCII, FS)
        self.c = ImageFont.truetype(FONT_CJK, FS)
        self.t = ImageFont.truetype(FONT_CJK, FS_TITLE)
        self.ta = ImageFont.truetype(FONT_ASCII, FS_TITLE)

    def pick(self, ch: str, size: str = "body"):
        # 防御：pick 只应收到单个字符
        if len(ch) != 1:
            raise TypeError(f"pick 只接受单字符，收到 {len(ch)} 字符: {ch[:40]!r}")
        if size == "title":
            return self.t if is_cjk(ch) else self.ta
        return self.c if is_cjk(ch) else self.a

    def line(self, d, x, y, text, color, size="body"):
        # 纯 ASCII 串直接整段绘制（快且不会有逐字间距误差）
        if text and not any(is_cjk(c) for c in text):
            d.text((x, y), text, font=(self.ta if size == "title" else self.a), fill=color)
            return x + int((self.ta if size == "title" else self.a).getlength(text))
        for ch in text:
            f = self.pick(ch, size)
            d.text((x, y), ch, font=f, fill=color)
            x += int(f.getlength(ch))
        return x


def new_canvas(title: str, w: int, h: int, f: Fonts) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 66], fill=BAR)
    for i, c in enumerate([(237, 106, 94), (245, 191, 79), (98, 197, 84)]):
        d.ellipse([20 + i * 26, 24, 34 + i * 26, 38], fill=c)
    f.line(d, 130, 16, title, FG, "title")
    return img, d


def card1(f: Fonts) -> Image.Image:
    w, h = 1200, 860
    img, d = new_canvas("官方文档 vs 实际必须传的参数", w, h, f)

    left = [
        ("×  按文档想当然写的", RED),
        ("", FG),
        ('{', DIM),
        ('  "latitude": 31.2304,', DIM),
        ('  "longitude": 121.4737,', DIM),
        ('  "searchType": 2,', DIM),
        ('  "beType": 1', DIM),
        ('}', DIM),
        ("", FG),
        ("×  少传 city", RED),
        ('{ "city": "上海", ... }', DIM),
        ('→ 600050 收藏餐厅列表为空', RED),
        ("", FG),
        ("×  少传 keyword", RED),
        ('{ "keyword": "徐家汇", ... }', DIM),
        ('→ 600058 城市名或者关键词不能为空', RED),
    ]
    right = [
        ("√  实测唯一可行", GREEN),
        ("", FG),
        ("query-nearby-stores", CYAN),
        ('{', DIM),
        ('  "city": "上海",      ← 必填', DIM),
        ('  "keyword": "徐家汇",   ← 必填', DIM),
        ('  "searchType": 2,     ← 必填', DIM),
        ('  "beType": 1', DIM),
        ('}', DIM),
        ("", FG),
        ("schema 里没有经纬度入参", YELLOW),
        ("定位由服务端按 city+keyword 处理", YELLOW),
    ]

    for col, lines in enumerate((left, right)):
        x0 = PAD + col * 570
        y = 110
        for text, color in lines:
            f.line(d, x0, y, text, color)
            y += LINE

    f.line(d, PAD, h - 56, "麦当劳 MCP · 实测于 2026-10-12", DIM)
    return img


def card2(f: Fonts) -> Image.Image:
    """动态布局：正文画完后再按实际底部位置放结论与页脚，避免重叠。"""
    blocks = [
        ("1. query-meals 的返回", CYAN, [
            ('{ "categories": [{ "name": "人气热卖",', DIM),
            ('    "meals": [', DIM),
            ('      { "code": "9900004064",', DIM),
            ('        "tags": ["爆款"] },', DIM),
            ('      { "code": "521950",', DIM),
            ('        "tags": ["蓝莓"] }', DIM),
            ("    ] }] }", DIM),
        ]),
        ("只有 code 和 tags，没有名称、没有价格", YELLOW, []),
        ("2. 必须再调 calculate-price", CYAN, [
            ('{ "storeCode": "1450323", "orderType": 1,', DIM),
            ('  "beType": 1,', DIM),
            ('  "items": [{"productCode": "9900004064",', DIM),
            ('             "quantity": 1}] }', DIM),
            ("", DIM),
            ('"productName": "精选单人餐三件套"', GREEN),
            ('"price": 3450        <- 单位是「分」= 34.50 元', GREEN),
        ]),
    ]

    # 先量出正文占多高
    body_h = 108
    for _, _, lines in blocks:
        body_h += LINE + 8 + LINE * len(lines) + 22
    conclusion_y = body_h + 16
    footer_y = conclusion_y + LINE + 16
    h = footer_y + 40

    img, d = new_canvas("拿到菜单，却不知道多少钱", 1200, h, f)
    y = 108
    for header, color, lines in blocks:
        f.line(d, PAD, y, header, color)
        y += LINE + 8
        for ln, ln_color in lines:
            f.line(d, PAD + 26, y, ln, ln_color)
            y += LINE
        y += 22

    f.line(d, PAD, conclusion_y, "所以：枚举与计价必须分离，金额只认核价接口的返回", GREEN)
    f.line(d, PAD, footer_y, "麦当劳 MCP · 实测于 2026-10-12", DIM)
    return img


def main() -> None:
    f = Fonts()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, maker in (("card-params.png", card1), ("card-menu.png", card2)):
        img = maker(f)
        img.save(OUT / name, optimize=True)
        print(f"OK  assets/{name}  {img.size[0]}x{img.size[1]}  "
              f"{(OUT / name).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()