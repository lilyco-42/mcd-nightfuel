"""命令行入口（零依赖）。

DEMO 模式（无需 MCP Token）::

    python -m nightfuel plan --now 01:30 --sleep 07:00 --consumed 290
    python -m nightfuel trap
"""

from __future__ import annotations

import argparse
import sys

from . import demo_data
from .mcp_adapter import PriceSnapshot, detect_coupon_trap, fen_to_yuan
from .planner import night_plan, render


def cmd_plan(args: argparse.Namespace) -> int:
    stage_combo = demo_data.stage_combo(night_plan(
        now=args.now, sleep_time=args.sleep, consumed_mg=args.consumed
    ).stage) if args.demo else []

    # DEMO 模式下用样本营养值算睡眠负担；真实模式由 MCP list-nutrition-foods 提供
    kcal = sodium = 0
    if args.demo:
        for name in stage_combo:
            item = next((i for i in demo_data.NIGHT_MENU if i["name"] == name), None)
            if item:
                kcal += item["kcal"]
                sodium += item["sodium_mg"]

    plan = night_plan(
        now=args.now,
        sleep_time=args.sleep,
        consumed_mg=args.consumed,
        sodium_mg=sodium,
        kcal=kcal,
        combo=stage_combo,
    )
    print(render(plan))
    if args.demo:
        print(f"- DEMO 核价：{fen_to_yuan(demo_data.DEMO_PRICE['price'])} 元（真实以 MCP calculate-price 为准）")
    return 0


def cmd_trap(_: argparse.Namespace) -> int:
    baseline = PriceSnapshot.from_response(demo_data.DEMO_PRICE)
    extra = PriceSnapshot.from_response({"price": demo_data.DEMO_PRICE["price"] + 900, "enjoyable": {"balance": 1500}})
    verdict = detect_coupon_trap(baseline, extra, extra_unit_fen=900)
    print(f"基准实付 {fen_to_yuan(verdict.baseline_fen)} 元 → {verdict.reason}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nightfuel", description="麦麦深夜补给官 · 夜班决策周期引擎")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="生成今夜补给包")
    p_plan.add_argument("--now", required=True, help="当前时间 HH:MM")
    p_plan.add_argument("--sleep", required=True, dest="sleep", help="目标入睡时间 HH:MM")
    p_plan.add_argument("--consumed", type=int, default=0, help="今日已摄入咖啡因 mg")
    p_plan.add_argument("--demo", action="store_true", help="DEMO 模式（无需 Token）")
    p_plan.set_defaults(func=cmd_plan)

    p_trap = sub.add_parser("trap", help="凑单陷阱检测演示")
    p_trap.set_defaults(func=cmd_trap)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())