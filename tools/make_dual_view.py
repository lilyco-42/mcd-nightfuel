#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成社交传播对比图：左「普通点餐视角」 vs 右「NightFuel 视角」。

对标 #1 项目的 assets/demo-dual-view.svg —— 视觉对比比纯文字表格更有传播力。
零第三方依赖，纯标准库 + 手写 SVG。
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "demo-dual-view.svg"

F_ASCII = "Consolas, 'Courier New', monospace"
F_CJK = "'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', sans-serif"

BG = "#0d1117"
CARD = "#161b22"
BORDER = "#30363d"
LEFT_ACCENT = "#58a6ff"
RIGHT_ACCENT = "#f0b429"
TEXT = "#e6edf3"
TEXT_DIM = "#8b949e"
GREEN = "#3fb950"
RED = "#f85149"


def is_cjk(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff" or ch in "，。：；「」（）【】—…·"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def split_runs(s: str) -> list[tuple[str, str]]:
    runs: list[tuple[str, str]] = []
    cur, cur_cjk = "", None
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
    return runs


def text_svg(s: str, x: float, y: float, size: int, fill: str, weight: str = "normal") -> str:
    parts = [
        f'<tspan font-family="{font}" font-weight="{weight}">{esc(txt)}</tspan>'
        for txt, font in split_runs(s)
    ]
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}">'
        + "".join(parts)
        + "</text>"
    )


def card(x: int, y: int, w: int, h: int, accent: str, title: str) -> list[str]:
    return [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{CARD}" stroke="{BORDER}"/>',
        f'<rect x="{x}" y="{y}" width="{w}" height="4" rx="2" fill="{accent}"/>',
        text_svg(title, x + 24, y + 40, 19, accent, "bold"),
    ]


LEFT_LINES = [
    ("", 0, TEXT),
    ("$ 你现在凌晨1:30，还要再撑3小时", 14, TEXT_DIM),
    ("  帮我点最便宜的三件套", 14, TEXT),
    ("", 0, TEXT),
    ("模型：查菜单 → 比单价 → 推荐 34.50 元套餐", 14, TEXT_DIM),
    ("", 0, TEXT),
    ("✓ 回答了：哪套最便宜", 14, GREEN),
    ("", 0, TEXT),
    ("✗ 没回答：", 14, RED),
    ("· 现在这个点这家店开着吗？", 13, RED),
    ("· 今天喝的咖啡离能睡着还差几杯？", 13, RED),
    ("· 吃完这顿会不会更睡不着？", 13, RED),
    ("· 这张券要我凑单吗？", 13, RED),
    ("", 0, TEXT),
    ("于是你自己再查一遍营业时间", 13, TEXT_DIM),
    ("自己回忆今天喝了几杯咖啡", 13, TEXT_DIM),
    ("自己判断钠含量高不高", 13, TEXT_DIM),
]

RIGHT_LINES = [
    ("", 0, TEXT),
    ("$ 我夜班，凌晨1:30，7点能睡", 14, TEXT_DIM),
    ("  今天喝了两杯美式", 14, TEXT),
    ("", 0, TEXT),
    ("NightFuel：", 14, RIGHT_ACCENT),
    ("① 先查 businessStatus", 13, TEXT),
    ("徐家汇店 24 小时营业中", 13, GREEN),
    ("② 咖啡因红线倒推", 13, TEXT),
    ("7:00 睡 → 02:00 后别碰咖啡", 13, GREEN),
    ("今日 290mg，还可再喝 110mg", 13, GREEN),
    ("③ 睡眠负担分 22 / 100", 13, TEXT),
    ("钠偏高，建议少喝汤", 13, GREEN),
    ("④ 停止进食 05:00", 13, TEXT),
    ("", 0, TEXT),
    ("「今夜补给包：麦香鱼 + 麦茶」", 14, RIGHT_ACCENT),
    ("真实核价 11870 分 = 118.70 元", 12, TEXT_DIM),
]


def build() -> str:
    W, H = 1240, 700
    cx = W / 2
    s: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        '<text x="%.1f" y="48" font-size="24" fill="%s" text-anchor="middle" font-weight="bold">'
        '<tspan font-family="%s">同一</tspan>'
        '<tspan font-family="%s" fill="%s">个</tspan>'
        '<tspan font-family="%s">凌晨 01:30，两种问法</tspan>'
        '</text>' % (cx, TEXT, F_CJK, F_ASCII, TEXT_DIM, F_ASCII),
        text_svg("同一个 MCP Server，同一家门店，同一个点——差别在于问的问题", cx, 76, 15, TEXT_DIM),
    ]

    lx, ly, cw, chh = 40, 106, 560, 512
    s += card(lx, ly, cw, chh, LEFT_ACCENT, "问题：「这个点怎么点最省？」")
    yy = ly + 84
    for txt, sz, color in LEFT_LINES:
        if not txt:
            yy += 15
            continue
        s.append(text_svg(txt, lx + 26, yy, sz, color))
        yy += sz + 11

    rx = 640
    s += card(rx, ly, cw, chh, RIGHT_ACCENT, "问题：「这一夜怎么过，才不毁掉明天？」")
    yy = ly + 84
    for txt, sz, color in RIGHT_LINES:
        if not txt:
            yy += 15
            continue
        s.append(text_svg(txt, rx + 26, yy, sz, color))
        yy += sz + 11

    by = ly + chh + 32
    s.append(f'<rect x="40" y="{by}" width="1160" height="54" rx="12" fill="#1c2430" stroke="{BORDER}"/>')
    s.append(text_svg("差别不在数据，在于把「这一夜」当成一个完整决策周期", 64, by + 33, 17, TEXT, "bold"))
    s.append(
        '<text x="1176" y="%d" font-size="13" fill="%s" text-anchor="end">'
        '<tspan font-family="%s">数据全部来自真实 MCP 调用 · 28 </tspan>'
        '<tspan font-family="%s">个回归测试 · 零第三方依赖</tspan></text>'
        % (by + 33, TEXT_DIM, F_CJK, F_ASCII)
    )
    s.append("</svg>")
    return "\n".join(s)


def main() -> int:
    svg = build()
    OUT.write_text(svg, encoding="utf-8")
    print(f"已生成 {OUT.relative_to(ROOT)}  ({len(svg)} 字节)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
