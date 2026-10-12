"""nightfuel —— 麦麦深夜补给官（麦门夜班垂直场景 Skill）。

零依赖（仅标准库）。DEMO 模式无需 MCP Token 即可跑通全链路逻辑。
"""

from .planner import NightPlan, night_plan, render, stage_of
from .caffeine import CaffeineBudget, caffeine_budget, caffeine_of, sleep_load
from .mcp_adapter import (
    ContractError,
    PriceSnapshot,
    TrapVerdict,
    calculate_price_items,
    detect_coupon_trap,
    fen_to_yuan,
    filter_real_orders,
    nearby_store_params,
    store_context_params,
    yuan_str_to_yuan,
)

__version__ = "0.1.0"

__all__ = [
    "NightPlan",
    "night_plan",
    "render",
    "stage_of",
    "CaffeineBudget",
    "caffeine_budget",
    "caffeine_of",
    "sleep_load",
    "ContractError",
    "PriceSnapshot",
    "TrapVerdict",
    "calculate_price_items",
    "detect_coupon_trap",
    "fen_to_yuan",
    "filter_real_orders",
    "nearby_store_params",
    "store_context_params",
    "yuan_str_to_yuan",
]