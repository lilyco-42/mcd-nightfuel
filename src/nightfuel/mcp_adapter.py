"""麦当劳 MCP 适配层。

只做三件事：字段映射、单位换算、契约校验。
所有真实金额必须来自 MCP ``calculate-price``；本模块不猜测任何价格。

⚠️ 单位陷阱（实测，见 MCP_INTEGRATION.md）：
   - ``calculate-price`` 的 price/discount/productPrice 是**整数分**
   - ``order-list`` 的 realTotalAmount 是**元的字符串**（"15.5"）
   两者方向相反，混用会造成数量级错误。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# 单位换算
# ---------------------------------------------------------------------------


def fen_to_yuan(fen: int | float | None) -> Decimal:
    """分 -> 元。calculate-price 的所有金额字段走这里。"""
    if fen is None:
        return Decimal("0")
    return (Decimal(int(fen)) / Decimal(100)).quantize(Decimal("0.01"))


def yuan_str_to_yuan(text: str | None) -> Decimal:
    """元字符串 -> 元。order-list 的 realTotalAmount 走这里。"""
    if text in (None, ""):
        return Decimal("0")
    return Decimal(str(text)).quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# 入参契约校验（官方文档未写明，来自实测）
# ---------------------------------------------------------------------------

CONTRACT_NOTES = {
    "query-nearby-stores": "必传 beType + searchType；还须带 city 或 keyword，否则报 600058",
    "query-meals": "必传 storeCode + orderType + beType；beCode 与 storeCode 配对",
    "query-store-coupons": "必传 storeCode + orderType + beType",
    "calculate-price": "必传 storeCode+orderType+beType；商品字段是 items，不是 meals",
    "order-list": "不接受任何参数，传参反而校验失败",
}

# 以下取值取自官方 inputSchema（2026-10-12 实测 tools/list 核对）
BE_TYPE = {
    1: "到店自提",
    2: "麦乐送到家",
    5: "得来速车道取餐(Drive Through)",
    6: "企业团餐",
}
ORDER_TYPE = {
    1: "到店（含到店自取 + 得来速车道取餐）",
    2: "外送（含麦乐送 + 企业团餐）",
}


class ContractError(ValueError):
    """违反实测调用契约时抛出，避免把参数错误当成业务空结果。"""


def nearby_store_params(
    *,
    be_type: int,
    search_type: int,
    city: str | None = None,
    keyword: str | None = None,
) -> dict[str, Any]:
    """query-nearby-stores 入参。

    实测结论：只给经纬度会报 ``600058城市名或者关键词不能为空``。
    官方 schema 也未暴露 latitude/longitude 入参 —— 定位由服务端按
    city/keyword + searchType 处理，故必须提供 city 或 keyword 之一。
    """
    if be_type not in BE_TYPE:
        raise ContractError(f"beType 非法: {be_type}（可选 {sorted(BE_TYPE)}）")
    if search_type not in (1, 2):
        raise ContractError(f"searchType 非法: {search_type}（1=收藏门店, 2=按位置）")
    if not city and not keyword:
        raise ContractError("city 与 keyword 至少提供一个，否则服务端报 600058")
    params: dict[str, Any] = {"beType": be_type, "searchType": search_type}
    if city:
        params["city"] = city
    if keyword:
        params["keyword"] = keyword
    return params


def store_context_params(
    *,
    store_code: str,
    order_type: int = 1,
    be_type: int = 1,
    be_code: str | None = None,
) -> dict[str, Any]:
    """菜单/券/核价查询的三件套：storeCode + orderType + beType，缺一不可。

    beCode 与 storeCode 配对使用，从 query-nearby-stores 返回结果中一并取回。
    """
    if not store_code:
        raise ContractError("storeCode 不能为空：菜单与券查询都依赖门店上下文")
    if order_type not in ORDER_TYPE:
        raise ContractError(f"orderType 非法: {order_type}（可选 {sorted(ORDER_TYPE)}）")
    if be_type not in BE_TYPE:
        raise ContractError(f"beType 非法: {be_type}（可选 {sorted(BE_TYPE)}）")
    params: dict[str, Any] = {"storeCode": store_code, "orderType": order_type, "beType": be_type}
    if be_code:
        params["beCode"] = be_code
    return params


def calculate_price_items(items: Iterable[tuple[str, int]]) -> list[dict[str, Any]]:
    """items 字段名必须是 productCode/quantity，用错字段名会直接参数校验失败。"""
    payload = [{"productCode": code, "quantity": int(qty)} for code, qty in items if int(qty) > 0]
    if not payload:
        raise ContractError("items 不能为空：核价必须带至少一个商品")
    return payload


# ---------------------------------------------------------------------------
# 订单清洗
# ---------------------------------------------------------------------------

REFUND_STATUSES = {"整单退款", "已退款", "退款"}


def filter_real_orders(orders: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """历史订单含「整单退款」，不过滤会让月度支出虚高。金额统一转成元。"""
    real: list[dict[str, Any]] = []
    for order in orders:
        if str(order.get("orderStatus", "")).strip() in REFUND_STATUSES:
            continue
        item = dict(order)
        item["realTotalAmountYuan"] = yuan_str_to_yuan(order.get("realTotalAmount"))
        real.append(item)
    return real


# ---------------------------------------------------------------------------
# 凑单陷阱检测
# ---------------------------------------------------------------------------


@dataclass
class TrapVerdict:
    """为凑券门槛加购，是否让实付不降反升。"""

    worth_adding: bool
    baseline_fen: int
    with_extra_fen: int
    delta_fen: int
    gap_fen: int
    reason: str


@dataclass
class PriceSnapshot:
    """calculate-price 响应的最小快照。"""

    total_fen: int
    discount_fen: int = 0
    balance_fen: int = 0  # enjoyable.balance：距可享受优惠还差多少分
    labels: list[str] = field(default_factory=list)
    items: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_response(cls, resp: dict[str, Any]) -> "PriceSnapshot":
        enjoyable = (resp or {}).get("enjoyable") or {}
        return cls(
            total_fen=int(resp.get("price") or resp.get("totalPrice") or 0),
            discount_fen=int(resp.get("discount") or 0),
            balance_fen=int(enjoyable.get("balance") or 0),
            labels=list(resp.get("couponNames") or []),
            items=list(resp.get("productList") or []),
        )

    def item_names(self) -> list[str]:
        """品名只在这里才有。

        实测：``query-meals`` 返回的 ``meals`` 数组**只有 code 和 tags，没有名称和价格**；
        品名与单价须从 ``calculate-price`` 的 ``productList[].productName`` 反查。
        """
        return [str(i.get("productName", "")) for i in self.items if i.get("productName")]

    def unit_fen(self, product_code: str) -> int:
        """按 productCode 反查单价（分），用于睡眠负担等计算。"""
        for item in self.items:
            if item.get("productCode") == product_code:
                qty = int(item.get("quantity") or 1)
                sub = int(item.get("subtotal") or 0)
                return sub // qty if qty else sub
        return 0


def detect_coupon_trap(
    baseline: PriceSnapshot,
    with_extra: PriceSnapshot,
    *,
    extra_unit_fen: int,
) -> TrapVerdict:
    """多数工具只答「怎么用券最省」，本函数额外回答「这张券值不值得为它凑单」。

    判定：加上凑单商品后 ``total_fen`` 不降反升 -> 不值得凑。
    金额全部来自 calculate-price，本函数不做任何价格推算。
    """
    delta = with_extra.total_fen - baseline.total_fen
    worth = delta < 0
    gap = baseline.balance_fen
    if worth:
        reason = f"凑单后实付降 {abs(delta) / 100:.2f} 元，门槛还差 {gap / 100:.2f} 元，补齐可享券"
    elif delta == 0:
        reason = f"凑单后实付持平（门槛差 {gap / 100:.2f} 元），不为凑单多买"
    else:
        reason = (
            f"凑单陷阱：加购 {_fmt(extra_unit_fen)} 后实付反涨 {delta / 100:.2f} 元，"
            f"距券门槛仍差 {gap / 100:.2f} 元 —— 不凑单"
        )
    return TrapVerdict(worth, baseline.total_fen, with_extra.total_fen, delta, gap, reason)


def _fmt(fen: int) -> str:
    return f"{fen / 100:.2f} 元"