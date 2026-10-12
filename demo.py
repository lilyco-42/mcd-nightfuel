#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦麦深夜补给官 —— 零配置演示。

不需要 MCP Token、不联网、不装任何第三方库：

    python demo.py

它读取 fixtures/ 里**录制的真实 MCP 响应**（2026-10-13 录制于 mcp.mcd.cn），
跑通夜班决策链路，并打印与真实使用时相同的输出。

真实运行时，这些响应由 Skill 编排层通过麦当劳 MCP 实时获取。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from nightfuel.caffeine import caffeine_budget, sleep_load  # noqa: E402
from nightfuel.mcp_adapter import (  # noqa: E402
    explain_error,
    fen_to_yuan,
    is_store_open,
)
from nightfuel.planner import night_plan, render, stage_of  # noqa: E402

FIXTURES = ROOT / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def hr(title: str = "") -> None:
    print("\n" + "=" * 62)
    if title:
        print(title)
        print("=" * 62)


def main() -> int:
    stores = load("stores")
    menu = load("menu")
    price = load("prices")

    hr("第 1 步 · 定位深夜还在营业的门店")
    rows = stores.get("data") or []
    print(f"query-nearby-stores → {len(rows)} 家门店（真实返回）\n")
    for r in rows:
        flag = "营业中" if r.get("businessStatus") else "已打烊"
        print(f"  [{flag}] {r.get('storeName')}")
        print(f"           {r.get('businessStartTime')} - {r.get('businessEndTime')}"
              f"  ·  storeCode={r.get('storeCode')}")

    open_stores = [r for r in rows if is_store_open(r)]
    if not open_stores:
        hr("结论")
        print("此刻没有营业中的门店。夜班场景下这是常见情况：")
        print(f"  query-meals 会返回 {explain_error(600057)}")
        print("  NightFuel 的做法：先查 businessStatus，别让用户看到一句看不懂的报错。")
        return 0

    store = open_stores[0]
    print(f"\n  → 选择营业中的：{store.get('storeName')}")

    hr("第 2 步 · 咖啡因红线（本地算法，不吃 Token）")
    budget = caffeine_budget(sleep_time="07:00", now_time="01:30", consumed_mg=290)
    print(f"目标入睡 07:00，现在 01:30，已摄入 290mg")
    print(f"  最后一杯截止：{budget.cutoff_time}（入睡 − 半衰期 5h）")
    print(f"  剩余额度：{budget.remaining_mg}mg / {budget.daily_limit_mg}mg")
    print(f"  裁决：{budget.verdict}")

    hr("第 3 步 · 今夜补给包（四阶段决策周期）")
    plan = night_plan(
        now="01:30", sleep_time="07:00", consumed_mg=290,
        sodium_mg=1025, kcal=560, combo=["麦香鱼", "麦茶"],
    )
    print(render(plan))

    hr("第 4 步 · 真实核价（金额唯一来源：calculate-price）")
    if price.get("success"):
        data = price.get("data") or {}
        print(f"storeCode={store.get('storeCode')}  单位：分\n")
        for item in data.get("productList") or []:
            print(f"  {item.get('productName')}"
                  f"  x{item.get('quantity')}"
                  f"  {item.get('subtotal')}分"
                  f" = {fen_to_yuan(item.get('subtotal'))} 元")
        print(f"\n  应付合计：{data.get('price')} 分 = {fen_to_yuan(data.get('price'))} 元")
        print(f"  取餐方式：{[w.get('title') for w in data.get('takeWayList') or []]}")
        print("\n  ⚠️ 注意：query-meals 只返回 code 和 tags，")
        print("     商品名称和价格必须从这里反查 —— 这是「枚举与计价分离」的物理依据。")
    else:
        print(f"  核价失败：{explain_error(price.get('code'))}")

    hr("以上数据均为 2026-10-13 对 mcp.mcd.cn 的真实录制")
    print("仓库：https://github.com/lilyco-42/mcd-nightfuel")
    print("在线体验：https://lilyco-42.github.io/mcd-nightfuel/")
    return 0


if __name__ == "__main__":
    sys.exit(main())