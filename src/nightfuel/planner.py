"""夜班决策周期引擎。

核心差异点：把「一夜」当成一个完整的决策周期，而不是单点「点一餐」。
四个阶段各有不同的进食/咖啡因策略，最后收敛成一份「今夜补给包」。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .caffeine import CaffeineBudget, caffeine_budget, sleep_load

STAGES = ("入夜", "续航", "深夜", "收尾")

STAGE_POLICY = {
    "入夜": "主食打底 + 第一杯咖啡，之后进入续航",
    "续航": "顶饱为主，低渣少油，咖啡配额在这里用掉",
    "深夜": "轻食优先，少油少钠，把钠和热量压下去",
    "收尾": "低咖啡因，温食为主，睡前 2 小时停止进食",
}


def stage_of(hour: int) -> str:
    """按小时判定夜班阶段。凌晨时段跨天归为「深夜/收尾」。"""
    h = hour % 24
    if 18 <= h < 21:
        return "入夜"
    if 21 <= h < 25 or h < 1:
        return "续航"
    if 1 <= h < 4:
        return "深夜"
    return "收尾"


@dataclass
class NightPlan:
    """一夜的补给决策。"""

    now: str
    sleep_time: str
    stage: str
    policy: str
    budget: CaffeineBudget
    caffeine_verdict: str
    stage_combo: list[str] = field(default_factory=list)
    load_score: int = 0
    load_tips: list[str] = field(default_factory=list)
    stop_eating_by: str = ""
    notes: list[str] = field(default_factory=list)

    def headline(self) -> str:
        return f"[{self.now} · {self.stage}] {self.caffeine_verdict}"


def _hhmm(hour: float) -> str:
    m = int(round(hour * 60)) % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def night_plan(
    *,
    now: str,
    sleep_time: str,
    consumed_mg: int = 0,
    sodium_mg: int = 0,
    kcal: int = 0,
    combo: list[str] | None = None,
) -> NightPlan:
    """生成今夜补给包。

    :param now: 当前时间 HH:MM（真实场景取自 MCP ``now-time-info``）
    :param sleep_time: 目标入睡时间 HH:MM
    :param consumed_mg: 今日已摄入咖啡因 mg
    :param sodium_mg: 本餐钠 mg（来自 MCP ``list-nutrition-foods``）
    :param kcal: 本餐能量 kcal（来自 MCP ``list-nutrition-foods``）
    """
    now_dt = datetime.strptime(now, "%H:%M")
    stage = stage_of(now_dt.hour)
    budget = caffeine_budget(sleep_time=sleep_time, now_time=now, consumed_mg=consumed_mg)
    score, tips = sleep_load(caffeine_mg=0, sodium_mg=sodium_mg, kcal=kcal)

    stop = _hhmm(max(0.0, (datetime.strptime(sleep_time, "%H:%M").hour + 24) - 2) % 24)

    notes = [STAGE_POLICY[stage]]
    if score >= 45:
        notes.append("本餐睡眠负担偏高，建议换轻食或减半")
    if budget.verdict == "stop":
        notes.append("咖啡因已到红线，转麦茶/无糖可乐")

    return NightPlan(
        now=now,
        sleep_time=sleep_time,
        stage=stage,
        policy=STAGE_POLICY[stage],
        budget=budget,
        caffeine_verdict=budget.advice(),
        stage_combo=list(combo or []),
        load_score=score,
        load_tips=tips,
        stop_eating_by=stop,
        notes=notes,
    )


def render(plan: NightPlan) -> str:
    """渲染成可直接发给用户的中文文案。"""
    lines = [
        f"## 今夜补给包 · {plan.now} · {plan.stage}",
        f"- 阶段策略：{plan.policy}",
        f"- 咖啡裁决：{plan.caffeine_verdict}",
        f"- 建议停止进食：{plan.stop_eating_by}（睡前 2 小时）",
    ]
    if plan.stage_combo:
        lines.append("- 阶段推荐：" + "、".join(plan.stage_combo))
    if plan.load_tips:
        lines.append("- 睡眠负担：" + "；".join(plan.load_tips))
    return "\n".join(lines)