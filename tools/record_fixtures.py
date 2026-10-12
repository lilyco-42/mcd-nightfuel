"""录制真实 MCP 响应为 fixtures（开发工具，不参与运行时）。

把 mcp.mcd.cn 的真实返回落盘成 fixtures/*.json，供 demo.py 与测试使用。
**只录公开数据**（门店/菜单/核价/营养/可领券），不录账户级数据（积分/我的券）。

    MCD_MCP_TOKEN=<token> python tools/record_fixtures.py

落盘的 JSON 已脱敏：不含 Token、不含手机号/地址等个人数据。
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://mcp.mcd.cn"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures"
TOKEN = os.environ.get("MCD_MCP_TOKEN", "")

# 演示用门店（公开信息：上海徐家汇餐厅，24 小时营业）
STORE_CODE = "1450034"   # 上海徐家汇餐厅，24h（00:00-23:59）

_rid = 0


def call(tool: str, args: dict) -> dict:
    global _rid
    _rid += 1
    req = urllib.request.Request(
        URL,
        data=json.dumps({
            "jsonrpc": "2.0", "id": _rid, "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        }).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    if body.lstrip().startswith(("event:", "data:")):
        for line in body.splitlines():
            if line.startswith("data:"):
                body = line[5:].strip()
                break
    return json.loads(body)


def unwrap(resp: dict):
    """拆掉 MCP content 包装，取出内层 JSON。"""
    for block in (resp.get("result", {}) or {}).get("content", []):
        if block.get("type") == "text":
            text = block["text"]
            i = text.find('{"success"')
            if i < 0:
                i = text.find("[")
            if i < 0:
                continue
            depth = 0
            end = 0
            for k, ch in enumerate(text[i:], start=i):
                if ch in "{[":
                    depth += 1
                elif ch in "}]":
                    depth -= 1
                    if depth == 0:
                        end = k + 1
                        break
            try:
                return json.loads(text[i:end])
            except json.JSONDecodeError:
                continue
    return resp


def main() -> int:
    if not TOKEN:
        sys.exit("需要 MCD_MCP_TOKEN（只录公开数据，不录账户数据）")

    OUT.mkdir(exist_ok=True)
    meta: dict[str, str] = {}

    def save(name: str, payload: dict) -> None:
        (OUT / f"{name}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        meta[name] = f"{tool}（真实返回）"
        print(f"  recorded {name}.json")

    print("录制 fixtures（仅公开数据）…")

    # 1. 门店（公开）
    tool = "query-nearby-stores"
    save("stores", unwrap(call(tool, {"city": "上海", "keyword": "徐家汇",
                                      "searchType": 2, "beType": 1})))

    # 2. 菜单（公开）
    # 注意：非 24h 门店在非营业时段会返回 600057「门店可能已关闭或不在营业时间」，
    # 因此演示固定用 24h 门店 1450034。
    tool = "query-meals"
    save("menu", unwrap(call(tool, {"storeCode": STORE_CODE, "orderType": 1, "beType": 1})))

    # 3. 核价（公开）
    tool = "calculate-price"
    save("prices", unwrap(call(tool, {
        "storeCode": STORE_CODE, "orderType": 1, "beType": 1,
        "items": [
            {"productCode": "9900015856", "quantity": 1},   # 精选单人餐（取自当日菜单）
            {"productCode": "521953", "quantity": 1},        # 麦乐鸡（取自当日菜单）
        ],
    })))

    # 4. 营养（公开）
    tool = "list-nutrition-foods"
    save("nutrition", unwrap(call(tool, {})))

    # 5. 可领券（公开，非账户级）
    tool = "available-coupons"
    save("coupons", unwrap(call(tool, {})))

    # 6. 活动日历（公开）
    tool = "campaign-calendar"
    save("campaign", unwrap(call(tool, {})))

    (OUT / "README.md").write_text(
        "# fixtures —— 录制的真实 MCP 响应\n\n"
        "这些文件由 `tools/record_fixtures.py` 从 `https://mcp.mcd.cn` **真实调用录制**，\n"
        "供 `demo.py` 与测试在无 Token 环境下复现链路。\n\n"
        "| 文件 | 来源 Tool |\n|---|---|\n"
        + "\n".join(f"| `{k}.json` | {v} |" for k, v in meta.items())
        + "\n\n> 只录制公开数据（门店 / 菜单 / 核价 / 营养 / 可领券 / 活动日历）。\n"
        "> **不录制账户级数据**（`query-my-account` 积分、`query-my-coupons` 我的券）。\n"
        "> 录制内容不含 Token、手机号、收货地址等敏感信息。\n",
        encoding="utf-8",
    )
    print(f"\n完成：{len(meta)} 个 fixtures + README.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())