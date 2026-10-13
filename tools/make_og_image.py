#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成 Open Graph 分享图 assets/og-image.png（1200×630）。

为什么需要：og:image 只在 PNG/JPG 上被微信/Twitter/X 等平台正确渲染，SVG 多数平台不支持。
这张图是「分享到社交平台 / IM 时的第一眼」，决定点击率。

零第三方依赖，纯标准库 + 手写 SVG → 由 tools/make_og_image.py 生成 SVG，
再用 Chrome headless 截成 PNG（见 main() 的说明）。
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SVG_OUT = ROOT / "assets" / "og-image.svg"

F_ASCII = "Consolas, 'Courier New', monospace"
F_CJK = "'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', sans-serif"

BG0 = "#0a0e27"
BG1 = "#141c3a"
YELLOW = "#f0b429"
CYAN = "#5ec8d6"
GREEN = "#7ed07e"
TEXT = "#f2f5ff"
DIM = "#aeb9dd"


def is_cjk(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff" or ch in "，。：；「」（）【】—…·、"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(s: str, x: float, y: float, size: int, fill: str,
         weight: str = "normal", anchor: str = "start") -> str:
    runs, cur, cur_cjk = [], "", None
    for ch in s:
        c = is_cjk(ch)
        if cur_cjk is None or c == cur_cjk:
            cur += ch
            cur_cjk = c
        else:
            runs.append((cur, F_CJK if cur_cjk else F_ASCII))
            cur, cur_cjk = ch, c
    if cur:
        runs.append((cur, F_CJK if cur_cjk else F_ASCII))
    spans = "".join(
        f'<tspan font-family="{f}" font-weight="{weight}">{esc(t)}</tspan>' for t, f in runs
    )
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}">{spans}</text>'
    )


def build() -> str:
    W, H = 1200, 630
    s: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">',
        f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/>',
        '</linearGradient></defs>',
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>',
    ]

    # 星星
    stars = [(88, 62), (238, 40), (392, 84), (536, 46), (672, 92), (818, 52),
             (952, 76), (1104, 44), (140, 140), (700, 140), (1044, 158)]
    for x, y in stars:
        s.append(f'<circle cx="{x}" cy="{y}" r="1.8" fill="#c9d4f2" opacity="0.7"/>')

    # 弯月
    s.append('<circle cx="1076" cy="88" r="40" fill="#ffd54d"/>')
    s.append('<circle cx="1056" cy="76" r="35" fill="#141c3a"/>')

    # 咖啡杯（标题右侧）
    s.append('<g>')
    s.append('<path d="M 930 74 q 6 -9 0 -18" stroke="#7f8fc0" stroke-width="2.5" fill="none" stroke-linecap="round"/>')
    s.append('<path d="M 952 70 q 6 -9 0 -18" stroke="#7f8fc0" stroke-width="2.5" fill="none" stroke-linecap="round"/>')
    s.append('<rect x="918" y="92" width="80" height="66" rx="9" fill="#f0b429"/>')
    s.append('<path d="M 998 105 h 12 a 16 16 0 0 1 0 32 h -12" fill="none" stroke="#f0b429" stroke-width="8" stroke-linecap="round"/>')
    s.append('<rect x="918" y="92" width="80" height="9" rx="4" fill="#d99a17"/>')
    s.append(text("M", 958, 134, 30, "#7a4f00", "bold", "middle"))
    s.append('</g>')

    # 主标题
    s.append(text("麦麦深夜补给官", 64, 190, 62, TEXT, "bold"))
    s.append(text("NightFuel", 64, 250, 40, YELLOW, "bold"))

    # 冲突式副标题
    s.append(text("市面上的工具都在回答「这一餐怎么点最省」", 64, 316, 25, DIM))
    s.append(text("我们多回答一句：这一夜，会不会废掉明天的睡眠？", 64, 356, 27, TEXT, "bold"))

    # 四阶段时间轴
    segs = [
        ("入夜", "18:00-21:00", "#ffb84d", 64, 300),
        ("续航", "21:00-01:00", "#7f9cf5", 364, 320),
        ("深夜", "01:00-04:00", "#4c5fd7", 684, 300),
        ("收尾", "04:00-06:00", "#38b2ac", 984, 172),
    ]
    for name, rng, color, x, w in segs:
        s.append(f'<rect x="{x}" y="418" width="{w}" height="30" rx="5" fill="{color}"/>')
        fg = "#10193a" if name in ("续航", "收尾") else ("#3a2a00" if name == "入夜" else "#eef1ff")
        s.append(text(name, x + w / 2, 439, 17, fg, "bold", "middle"))
        s.append(text(rng, x + w / 2, 470, 14, DIM, "normal", "middle"))

    # 底部指标条
    s.append(f'<rect x="64" y="512" width="1072" height="1" fill="#2e3550"/>')
    metrics = [
        ("35", "实测 MCP 工具"),
        ("19", "固化契约"),
        ("28", "测试全绿"),
        ("6", "真实 fixtures"),
        ("0", "第三方依赖"),
    ]
    step = 1072 / len(metrics)
    for i, (num, label) in enumerate(metrics):
        cx = 64 + step * i + step / 2
        s.append(text(num, cx, 556, 34, GREEN, "bold", "middle"))
        s.append(text(label, cx, 584, 15, DIM, "normal", "middle"))

    # 页脚
    s.append(text("github.com/lilyco-42/mcd-nightfuel", 64, 612, 15, "#5d6a94"))
    s.append(text("麦当劳 MCP 程序员创意开发大赛参赛作品", 1136, 612, 15, "#5d6a94", "normal", "end"))

    s.append("</svg>")
    return "\n".join(s)


def main() -> int:
    svg = build()
    SVG_OUT.write_text(svg, encoding="utf-8")
    print(f"已生成 {SVG_OUT.relative_to(ROOT)}  ({len(svg)} 字节)")
    print("转 PNG：")
    print('  chrome --headless --screenshot=assets/og-image.png --window-size=1200,630 '
          'file:///' + str(SVG_OUT).replace('\\', '/'))
    return 0


if __name__ == "__main__":
    sys.exit(main())
