"""NightFuel 真实 MCP 链路验证客户端（一次性验证脚本，不进仓库）。

用法：TOKEN=<token> python tools/verify_mcp.py
Token 仅从环境变量读取，绝不落盘。
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

URL = "https://mcp.mcd.cn"
TOKEN = os.environ.get("MCD_MCP_TOKEN", "")
PROTOCOL = "2024-11-05"

if not TOKEN:
    sys.exit("缺少环境变量 MCD_MCP_TOKEN")

_rid = 0


def call(method: str, params: dict | None = None, notify: bool = False) -> dict:
    """发起一次 JSON-RPC 调用。"""
    global _rid
    payload: dict = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if not notify:
        _rid += 1
        payload["id"] = _rid

    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode("utf-8", "replace")[:400]}

    if notify or not body.strip():
        return {}

    # Streamable HTTP 可能返回 SSE 格式
    if body.lstrip().startswith("event:") or body.lstrip().startswith("data:"):
        for line in body.splitlines():
            if line.startswith("data:"):
                body = line[5:].strip()
                break
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"_raw": body[:400]}


def tool(name: str, args: dict) -> dict:
    return call("tools/call", {"name": name, "arguments": args})


def unwrap(resp: dict) -> object:
    """把 MCP content 包装拆成原始 JSON。"""
    if "_http_error" in resp or "_raw" in resp:
        return resp
    result = resp.get("result")
    if not result:
        return resp.get("error", resp)
    content = (result.get("content") or [])
    for block in content:
        if block.get("type") == "text":
            text = block["text"]
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
    return result


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> int:
    section("0. initialize")
    init = call("initialize", {
        "protocolVersion": PROTOCOL,
        "capabilities": {},
        "clientInfo": {"name": "nightfuel-verify", "version": "0.1.0"},
    })
    print(json.dumps(init.get("result", init), ensure_ascii=False)[:200])
    call("notifications/initialized", notify=True)

    section("1. now-time-info（夜班时间基准）")
    now = unwrap(tool("now-time-info", {}))
    print(json.dumps(now, ensure_ascii=False)[:400])

    section("2. list-nutrition-foods（核实是否含咖啡因字段）")
    nut = unwrap(tool("list-nutrition-foods", {}))
    items = nut if isinstance(nut, list) else (nut.get("data") or nut.get("list") or [] if isinstance(nut, dict) else [])
    if not items and isinstance(nut, dict):
        for v in nut.values():
            if isinstance(v, list) and v:
                items = v
                break
    print(f"返回条目数：{len(items) if isinstance(items, list) else 'N/A'}")
    if isinstance(items, list) and items:
        print("首条字段：", json.dumps(items[0], ensure_ascii=False)[:400])
        keys = set()
        for it in items[:200]:
            if isinstance(it, dict):
                keys.update(it.keys())
        print("全部字段并集：", sorted(keys))
        print(">>> 是否含 caffeine 字段：", any("caffeine" in k.lower() for k in keys))

    section("3. query-nearby-stores（验证 beType/searchType 必传）")
    print("-- 3a 缺参数（预期报错）--")
    bad = unwrap(tool("query-nearby-stores", {"latitude": 31.2304, "longitude": 121.4737}))
    print(json.dumps(bad, ensure_ascii=False)[:300])

    print("-- 3b 补齐 beType+searchType --")
    good = unwrap(tool("query-nearby-stores", {
        "latitude": 31.2304, "longitude": 121.4737, "searchType": 2, "beType": 1,
    }))
    print(json.dumps(good, ensure_ascii=False)[:700])

    section("4. query-meals（三件套契约）")
    store_code = None
    if isinstance(good, dict):
        for v in good.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                store_code = v[0].get("storeCode") or v[0].get("storecode") or v[0].get("code")
                break
    print("解析到 storeCode：", store_code)
    if store_code:
        print("-- 4a 缺三件套（预期报错）--")
        print(json.dumps(unwrap(tool("query-meals", {"storeCode": store_code})), ensure_ascii=False)[:300])
        print("-- 4b 补齐 orderType+beType --")
        meals = unwrap(tool("query-meals", {"storeCode": store_code, "orderType": 1, "beType": 1}))
        print(json.dumps(meals, ensure_ascii=False)[:900])
    else:
        print("未解析到 storeCode，跳过")

    section("5. calculate-price（核实单位是分）")
    print("-- 5a 用一个假 productCode 看返回结构（不产生真实订单）--")
    price = unwrap(tool("calculate-price", {
        "storeCode": store_code or "S001",
        "orderType": 1,
        "beType": 1,
        "items": [{"productCode": "0000000000000", "quantity": 1}],
    }))
    print(json.dumps(price, ensure_ascii=False)[:700])

    section("6. query-my-coupons / available-coupons（只读，券约束）")
    print("my:", json.dumps(unwrap(tool("query-my-coupons", {})), ensure_ascii=False)[:300])
    print("avail:", json.dumps(unwrap(tool("available-coupons", {})), ensure_ascii=False)[:300])

    section("7. query-my-account（积分账户，只读）")
    print(json.dumps(unwrap(tool("query-my-account", {})), ensure_ascii=False)[:300])

    section("验证结束（未调用任何写操作）")
    return 0


if __name__ == "__main__":
    sys.exit(main())