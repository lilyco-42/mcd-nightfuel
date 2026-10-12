"""咖啡因预算与睡眠负担引擎。

⚠️ 数据来源声明（重要，不可省略）：
   麦当劳 MCP ``list-nutrition-foods`` 返回的是能量、蛋白质、脂肪、碳水化合物、钠、钙，
   **不含咖啡因字段**。因此本模块的咖啡因含量来自 `CAFFEINE_MG` 这张**本地基准表**
   （公开资料整理，单位 mg/中杯），不是 MCP 实时数据，也不声称是。
   能量、蛋白质、脂肪、钠等仍以 MCP ``list-nutrition-foods`` 为准。
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 公开基准（成人）
# ---------------------------------------------------------------------------
DAILY_LIMIT_MG = 400          # FDA / EFSA 成人每日咖啡因上限 400mg
HALF_LIFE_H = 5.0             # 咖啡因半衰期约 5 小时（保守取 4~6h 中位）
PRE_SLEEP_CUTOFF_H = 5.0      # 睡前至少 5 小时（=1 个半衰期）不再摄入

# 咖啡因基准表：mg / 中杯。键为本地品名关键词，匹配 MCP 餐品名。
CAFFEINE_MG: dict[str, int] = {
    "鲜煮咖啡": 145,
    "冰美式": 150,
    "美式": 150,
    "拿铁": 150,
    "咖啡": 150,
    "可乐": 35,
    "雪碧": 30,
    "红茶": 5,
    "麦茶": 0,
    "奶茶": 60,
    "巧克力": 5,
    "奶昔": 0,
    "橙汁": 0,
    "牛奶": 0,
    "冰淇淋": 0,
    "薯条": 0,
    "汉堡": 0,
}


def caffeine_of(name: str) -> int:
    """按品名估算咖啡因含量（mg）。未知品名返回 0。"""
    for key, mg in CAFFEINE_MG.items():
        if key in name:
            return mg
    return 0


def sleep_load(*, caffeine_mg: int, sodium_mg: int, kcal: int) -> tuple[int, list[str]]:
    """睡眠负担分 0~100，越高越难睡。返回 (分数, 建议列表)。

    三个维度：咖啡因残留 / 高钠口渴 / 夜宵热量负担。
    """
    score = 0
    tips: list[str] = []

    # 咖啡因：按剩余量线性折算，半衰期后仍残留约 50%
    if caffeine_mg > 0:
        score += min(60, int(caffeine_mg / 400 * 100 * 0.6))
        tips.append(f"咖啡因 {caffeine_mg}mg，距入睡不足一个半衰期，仍会残留约 {int(caffeine_mg / 2)}mg")

    # 高钠：>800mg/餐 记分（麦当劳薯条/酱料钠含量高）
    if sodium_mg > 800:
        over = sodium_mg - 800
        score += min(20, int(over / 200))
        tips.append(f"钠 {sodium_mg}mg 偏高，口渴影响睡眠，建议配无糖饮品")

    # 夜宵热量：>700kcal 记分
    if kcal > 700:
        score += min(20, int((kcal - 700) / 150))
        tips.append(f"能量 {kcal}kcal 偏高，深夜消化负担重")

    return min(100, score), tips


@dataclass
class CaffeineBudget:
    """咖啡因预算裁决。"""

    consumed_mg: int
    remaining_mg: int
    daily_limit_mg: int
    cutoff_time: str       # 建议的「最后一杯」时刻 HH:MM
    sleep_time: str
    verdict: str           # stop / one_more / ok

    def advice(self) -> str:
        if self.verdict == "stop":
            return (
                f"今日咖啡因已达 {self.consumed_mg}mg（上限 {self.daily_limit_mg}mg），"
                f"且已过 {self.cutoff_time} —— 今晚别再喝，改喝麦茶/无糖可乐。"
            )
        if self.verdict == "one_more":
            return (
                f"还剩 {self.remaining_mg}mg 额度，且未过 {self.cutoff_time} —— "
                f"最多再来一杯中杯，之后转无咖啡因饮品。"
            )
        return (
            f"额度充足（剩 {self.remaining_mg}mg），但已过 {self.cutoff_time} —— "
            f"为保证 {self.sleep_time} 能睡着，咖啡到此为止。"
        )


def caffeine_budget(
    *,
    sleep_time: str,
    now_time: str,
    consumed_mg: int = 0,
    limit_mg: int = DAILY_LIMIT_MG,
    half_life_h: float = HALF_LIFE_H,
) -> CaffeineBudget:
    """按目标入睡时间倒推咖啡因截止时刻，并裁决今晚还能不能喝。

    截止时刻 = 目标入睡时间 - 1 个半衰期（不摄入区间至少等于半衰期）。

    ⚠️ 深夜场景天然跨零点：21:00 入睡 07:00 必须理解为**次日** 07:00。
    这里把两个时间放到同一条时间轴上比较（入睡时间若不晚于当前时间则 +24h），
    避免「21:00 早于 02:00」这种把当晚当昨天算的错误。
    """
    _assert_hhmm(now_time, "now_time")
    _assert_hhmm(sleep_time, "sleep_time")

    now_min = _to_min(now_time)
    sleep_min = _to_min(sleep_time)
    # 统一到同一条时间轴：入睡时间不晚于现在 -> 视为次日
    if sleep_min <= now_min:
        sleep_min += 24 * 60
    cutoff_min = sleep_min - half_life_h * 60

    remaining = max(0, limit_mg - consumed_mg)

    if consumed_mg >= limit_mg:
        verdict = "stop"
    elif now_min >= cutoff_min:
        verdict = "stop"
    else:
        verdict = "ok"

    # 还有额度但已进入「最后一杯」窗口（距截止不足 1 小时）
    if verdict == "ok" and 0 <= cutoff_min - now_min < 60:
        verdict = "one_more"

    return CaffeineBudget(
        consumed_mg=consumed_mg,
        remaining_mg=remaining,
        daily_limit_mg=limit_mg,
        cutoff_time=_to_hhmm(cutoff_min),
        sleep_time=sleep_time,
        verdict=verdict,
    )


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _to_hhmm(minutes: float) -> str:
    minutes = int(round(minutes)) % (24 * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _assert_hhmm(value: str, field_name: str) -> None:
    parts = str(value).split(":")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise ValueError(f"{field_name} 必须是 HH:MM，收到 {value!r}")