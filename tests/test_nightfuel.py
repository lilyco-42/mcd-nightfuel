"""本地测试：无需 MCP Token 即可验证全链路逻辑。

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nightfuel import (  # noqa: E402
    ContractError,
    PriceSnapshot,
    calculate_price_items,
    caffeine_budget,
    caffeine_of,
    detect_coupon_trap,
    fen_to_yuan,
    filter_real_orders,
    nearby_store_params,
    sleep_load,
    stage_of,
    store_context_params,
    yuan_str_to_yuan,
)
from nightfuel.planner import night_plan, render  # noqa: E402


class TestUnits(unittest.TestCase):
    """单位陷阱是本项目最核心的坑，必须锁死。"""

    def test_fen_to_yuan(self):
        self.assertEqual(fen_to_yuan(3350), 33.50)
        self.assertEqual(fen_to_yuan(0), 0)
        self.assertEqual(fen_to_yuan(None), 0)

    def test_yuan_str_is_opposite_direction(self):
        self.assertEqual(yuan_str_to_yuan("15.5"), 15.5)
        self.assertEqual(yuan_str_to_yuan(""), 0)


class TestContracts(unittest.TestCase):
    def test_nearby_requires_city_and_keyword(self):
        """实测：city 与 keyword 必须同时给，缺一分别报 600058 / 600050。"""
        params = nearby_store_params(be_type=1, search_type=2, city="上海", keyword="徐家汇")
        self.assertEqual(params["beType"], 1)
        self.assertEqual(params["searchType"], 2)
        with self.assertRaises(ContractError):
            nearby_store_params(be_type=1, search_type=2)  # 两者都缺
        with self.assertRaises(ContractError):
            nearby_store_params(be_type=9, search_type=2, city="上海", keyword="徐家汇")
        with self.assertRaises(ContractError):
            nearby_store_params(be_type=1, search_type=7, city="上海", keyword="徐家汇")

    def test_store_context_triple(self):
        params = store_context_params(store_code="1450323")
        self.assertEqual(params, {"storeCode": "1450323", "orderType": 1, "beType": 1})
        with self.assertRaises(ContractError):
            store_context_params(store_code="")

    def test_drive_through_be_type_allowed(self):
        """实测 schema：beType=5 是得来速车道取餐。"""
        self.assertEqual(store_context_params(store_code="S1", be_type=5)["beType"], 5)

    def test_calculate_price_items_field_name(self):
        items = calculate_price_items([("A1", 2)])
        self.assertEqual(items, [{"productCode": "A1", "quantity": 2}])
        with self.assertRaises(ContractError):
            calculate_price_items([])


class TestRealResponseShape(unittest.TestCase):
    """以下断言全部来自 2026-10-12 对 mcp.mcd.cn 的真实调用。"""

    def test_price_3450_fen_is_34_50_yuan(self):
        """真实返回：price=3450（分）→ 34.50 元 精选单人餐三件套。"""
        resp = {
            "price": 3450,
            "discount": 0,
            "productList": [{
                "productCode": "9900004064",
                "productName": "精选单人餐三件套",
                "quantity": 1,
                "originalSubtotal": 3450,
                "subtotal": 3450,
            }],
        }
        snap = PriceSnapshot.from_response(resp)
        self.assertEqual(fen_to_yuan(snap.total_fen), 34.50)
        self.assertEqual(snap.item_names(), ["精选单人餐三件套"])
        self.assertEqual(snap.unit_fen("9900004064"), 3450)

    def test_menu_has_no_name_or_price(self):
        """query-meals 只给 code/tags，品名与价格必须从 calculate-price 反查。"""
        menu_item = {"code": "9900004064", "tags": ["爆款"]}
        self.assertNotIn("name", menu_item)
        self.assertNotIn("price", menu_item)

    def test_unit_price_divided_by_quantity(self):
        resp = {"price": 6900, "productList": [
            {"productCode": "A", "quantity": 2, "subtotal": 6900},
        ]}
        self.assertEqual(PriceSnapshot.from_response(resp).unit_fen("A"), 3450)


class TestOrders(unittest.TestCase):
    def test_refund_orders_filtered(self):
        orders = [
            {"orderStatus": "已完成", "realTotalAmount": "33.5"},
            {"orderStatus": "整单退款", "realTotalAmount": "46.5"},
        ]
        real = filter_real_orders(orders)
        self.assertEqual(len(real), 1)
        self.assertEqual(real[0]["realTotalAmountYuan"], 33.5)


class TestCaffeine(unittest.TestCase):
    def test_cutoff_is_sleep_minus_half_life(self):
        b = caffeine_budget(sleep_time="07:00", now_time="21:00", consumed_mg=0)
        self.assertEqual(b.cutoff_time, "02:00")
        self.assertEqual(b.verdict, "ok")

    def test_verdict_stop_after_cutoff(self):
        b = caffeine_budget(sleep_time="07:00", now_time="03:00", consumed_mg=0)
        self.assertEqual(b.verdict, "stop")

    def test_verdict_stop_when_limit_reached(self):
        b = caffeine_budget(sleep_time="09:00", now_time="21:00", consumed_mg=400)
        self.assertEqual(b.verdict, "stop")
        self.assertEqual(b.remaining_mg, 0)

    def test_one_more_window(self):
        b = caffeine_budget(sleep_time="07:30", now_time="02:00", consumed_mg=100)
        self.assertEqual(b.cutoff_time, "02:30")
        self.assertEqual(b.verdict, "one_more")

    def test_bad_time_raises(self):
        with self.assertRaises(ValueError):
            caffeine_budget(sleep_time="7am", now_time="21:00")

    def test_caffeine_lookup(self):
        self.assertEqual(caffeine_of("鲜煮咖啡（中杯）"), 145)
        self.assertEqual(caffeine_of("麦茶"), 0)
        self.assertEqual(caffeine_of("未知品"), 0)

    def test_sleep_load_penalises_sodium_and_kcal(self):
        score, tips = sleep_load(caffeine_mg=0, sodium_mg=1500, kcal=950)
        self.assertGreater(score, 0)
        self.assertTrue(tips)


class TestStages(unittest.TestCase):
    def test_stage_boundaries(self):
        self.assertEqual(stage_of(19), "入夜")
        self.assertEqual(stage_of(22), "续航")
        self.assertEqual(stage_of(2), "深夜")
        self.assertEqual(stage_of(5), "收尾")


class TestTrap(unittest.TestCase):
    def test_not_worth_when_price_rises(self):
        base = PriceSnapshot.from_response({"price": 3350, "enjoyable": {"balance": 1500}})
        worse = PriceSnapshot.from_response({"price": 4250, "enjoyable": {"balance": 1500}})
        v = detect_coupon_trap(base, worse, extra_unit_fen=900)
        self.assertFalse(v.worth_adding)
        self.assertIn("凑单陷阱", v.reason)

    def test_worth_when_price_drops(self):
        base = PriceSnapshot.from_response({"price": 5000, "enjoyable": {"balance": 1500}})
        better = PriceSnapshot.from_response({"price": 4200, "enjoyable": {"balance": 0}})
        v = detect_coupon_trap(base, better, extra_unit_fen=900)
        self.assertTrue(v.worth_adding)

    def test_flat_is_not_worth(self):
        base = PriceSnapshot.from_response({"price": 5000, "enjoyable": {"balance": 1500}})
        same = PriceSnapshot.from_response({"price": 5000, "enjoyable": {"balance": 0}})
        v = detect_coupon_trap(base, same, extra_unit_fen=900)
        self.assertFalse(v.worth_adding)


class TestPlan(unittest.TestCase):
    def test_full_plan(self):
        # 01:30 距离 02:00 的咖啡因截止线只剩 30 分钟 -> 最后一杯窗口
        plan = night_plan(now="01:30", sleep_time="07:00", consumed_mg=290, combo=["麦香鱼", "麦茶"])
        self.assertEqual(plan.stage, "深夜")
        self.assertEqual(plan.budget.cutoff_time, "02:00")
        self.assertEqual(plan.budget.verdict, "one_more")
        self.assertEqual(plan.budget.remaining_mg, 110)
        self.assertTrue(render(plan).startswith("## 今夜补给包"))

    def test_midnight_wrap_not_a_day_early(self):
        """21:00 入睡到次日 07:00：截止线是今晚 02:00，不是已过去。"""
        b = caffeine_budget(sleep_time="07:00", now_time="21:00", consumed_mg=0)
        self.assertEqual(b.cutoff_time, "02:00")
        self.assertEqual(b.verdict, "ok")

    def test_stop_after_cutoff_across_midnight(self):
        b = caffeine_budget(sleep_time="07:00", now_time="02:30", consumed_mg=0)
        self.assertEqual(b.verdict, "stop")


if __name__ == "__main__":
    unittest.main()