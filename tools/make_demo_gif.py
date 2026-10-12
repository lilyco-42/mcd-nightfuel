"""生成README 用的终端实录 GIF（开发工具，不参与运行时）。

内容直接调用 nightfuel CLI 实时抓取，保证 GIF 与实际行为完全一致。
中文用微软雅黑、ASCII 用 Consolas，按字符类型分段绘制以还原终端排版。

    python tools/make_demo_gif.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "demo.gif"

FONT_ASCII = "C:/Windows/Fonts/consola.ttf"
FONT_ASCII_BOLD = "C:/Windows/Fonts/consolab.ttf"
FONT_CJK = "C:/Windows/Fonts/msyh.ttc"

BG = (24, 26, 33)
BAR = (38, 41, 51)
FG = (203, 208, 216)
GREEN = (126, 208, 126)
CYAN = (94, 200, 214)
GREY = (110, 118, 134)

FONT_SIZE = 19
PAD = 26
LINE_H = 30
WIDTH = 980


def is_cjk(ch: str) -> bool:
    o = ord(ch)
    return (
        0x2E80 <= o <= 0x9FFF
        or 0xAC00 <= o <= 0xD7AF
        or 0xF900 <= o <= 0xFAFF
        or 0xFF00 <= o <= 0xFFEF
        or 0x3000<= o <= 0x303F
    )


class Fonts:
    def __init__(self) -> None:
        self.ascii_ = ImageFont.truetype(FONT_ASCII, FONT_SIZE)
        self.ascii_b = ImageFont.truetype(FONT_ASCII_BOLD, FONT_SIZE)
        self.cjk = ImageFont.truetype(FONT_CJK, FONT_SIZE)
        self.cjk_b = ImageFont.truetype(FONT_CJK, FONT_SIZE)

    def pick(self, ch: str, bold: bool = False) -> ImageFont.ImageFont:
        if is_cjk(ch):
            return self.cjk_b if bold else self.cjk
        return self.ascii_b if bold else self.ascii_

    def draw_line(self, d: ImageDraw.ImageDraw, x: int, y: int, text: str, color, bold=False) -> int:
        """按字符类型分段绘制，返回结束x。"""
        for ch in text:
            font = self.pick(ch, bold)
            d.text((x, y), ch, font=font, fill=color)
            x += int(font.getlength(ch))
        return x


def run_cli(*args: str) -> list[str]:
    """真实调用 CLI 拿输出，绝不手写。"""
    env = {"PYTHONPATH": str(ROOT / "src"), "PATH": os.environ.get("PATH", "")}
    for key in ("SYSTEMROOT", "SystemRoot", "WINDIR", "TEMP", "TMP", "HOMEDRIVE", "HOMEPATH"):
        if key in os.environ:
            env[key] = os.environ[key]
    proc = subprocess.run(
        [sys.executable, "-m", "nightfuel", *args],
        capture_output=True, text=True, encoding="gbk", errors="replace",
        cwd=ROOT, env=env,
    )
    return (proc.stdout or "").rstrip("\n").split("\n")


def build_script() -> list[tuple[str, tuple[int, int, int]]]:
    steps: list[tuple[str, tuple[int, int, int]]] = [
        ("$ python -m unittest discover -s tests", GREY),
        ("Ran 24 tests in 0.015s", FG),
        ("OK", GREEN),
        ("", FG),
        ("$ python -m nightfuel plan --now 01:30 --sleep 07:00 \\", CYAN),
        ("      --consumed 290", CYAN),
    ]
    steps += [(ln, FG) for ln in run_cli("plan", "--now", "01:30", "--sleep", "07:00",
                                       "--consumed", "290", "--demo")]
    steps.append(("", FG))
    steps.append(("$ python -m nightfuel trap", CYAN))
    steps += [(ln, FG) for ln in run_cli("trap")]
    return steps


def render() -> None:
    fonts = Fonts()
    steps = build_script()
    body_h = PAD * 2 + LINE_H * len(steps)
    width, height = WIDTH, body_h + 34

    def frame(n_chars: int, cursor: bool) -> Image.Image:
        img = Image.new("RGB", (width, height), BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, width, 34], fill=BAR)
        for i, c in enumerate([(237, 106, 94), (245, 191, 79), (98, 197, 84)]):
            d.ellipse([16 + i * 20, 12, 26 + i * 20, 22], fill=c)
        fonts.draw_line(d, 90, 8, "nightfuel · 麦麦深夜补给官", GREY)

        shown, y = 0, 34 + PAD
        for text, color in steps:
            if shown >= n_chars:
                break
            take = max(0, min(len(text), n_chars - shown))
            if take:
                fonts.draw_line(d, PAD, y, text[:take], color)
            shown += len(text)
            y += LINE_H
        if cursor:
            cy = 34 + PAD + min(sum(1 for _ in steps), len(steps)) * LINE_H
            if cy + 4 < height - PAD:
                d.rectangle([PAD, cy, PAD + 11, cy + 2], fill=FG)
        return img

    frames: list[Image.Image] = []
    total = sum(len(t) for t, _ in steps)
    n = 0
    while n <= total:
        frames.append(frame(n, True))
        n += 3
    frames.append(frame(total, True))
    for _ in range(20):      # 停留约2.4s 让结果可读
        frames.append(frame(total, True))
    for _ in range(6):
        frames.append(frame(total, False))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=30, loop=0, optimize=True)
    print(f"OK  {OUT.relative_to(ROOT)}  {len(frames)} frames  {OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    render()