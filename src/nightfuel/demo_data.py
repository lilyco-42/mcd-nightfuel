"""DEMO 菜单样本（不含真实门店价格，仅用于本地跑通链路）。

真实运行时，所有价格必须来自 MCP ``calculate-price``，禁止使用本文件的数字。
"""

from __future__ import annotations

# 深夜时段真实在售的常见品（品名为公开常识，价格一律以 calculate-price 为准）
NIGHT_MENU = [
    {"name": "麦辣鸡腿汉堡", "kcal": 550, "sodium_mg": 980, "caffeine_mg": 0, "type": "main"},
    {"name": "板烧鸡腿堡", "kcal": 520, "sodium_mg": 900, "caffeine_mg": 0, "type": "main"},
    {"name": "麦香鱼", "kcal": 560, "sodium_mg": 1020, "caffeine_mg": 0, "type": "main"},
    {"name": "吉士汉堡堡", "kcal": 480, "sodium_mg": 860, "caffeine_mg": 0, "type": "main"},
    {"name": "中薯条", "kcal": 335, "sodium_mg": 620, "caffeine_mg": 0, "type": "side"},
    {"name": "麦辣鸡腿堡三件套", "kcal": 950, "sodium_mg": 1500, "caffeine_mg": 0, "type": "combo"},
    {"name": "鲜煮咖啡（中杯）", "kcal": 10, "sodium_mg": 20, "caffeine_mg": 145, "type": "drink"},
    {"name": "冰美式（中杯）", "kcal": 15, "sodium_mg": 10, "caffeine_mg": 150, "type": "drink"},
    {"name": "无糖可乐（中杯）", "kcal": 5, "sodium_mg": 15, "caffeine_mg": 35, "type": "drink"},
    {"name": "麦茶", "kcal": 0, "sodium_mg": 5, "caffeine_mg": 0, "type": "drink"},
    {"name": "红豆派", "kcal": 260, "sodium_mg": 180, "caffeine_mg": 0, "type": "dessert"},
]

# 阶段推荐（品名，来自 NIGHT_MENU）
STAGE_COMBO = {
    "入夜": ["麦辣鸡腿堡三件套", "鲜煮咖啡（中杯）"],
    "续航": ["吉士汉堡堡", "中薯条", "鲜煮咖啡（中杯）"],
    "深夜": ["麦香鱼", "麦茶"],
    "收尾": ["红豆派", "麦茶"],
}

# DEMO 价格响应（单位：分，模拟 calculate-price 返回）
DEMO_PRICE = {"price": 3350, "discount": 0, "enjoyable": {"balance": 1500, "enjoyed": 0}}


def stage_combo(stage: str) -> list[str]:
    return list(STAGE_COMBO.get(stage, []))