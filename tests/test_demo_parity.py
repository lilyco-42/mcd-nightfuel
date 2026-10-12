"""Demo（demo/index.html）与 Python 引擎的交叉一致性测试。

Demo 里的 JS 算法是从 src/nightfuel/ 移植的。两套实现必须逐案一致，
否则用户看到的和 Skill 实际跑出来的会是两个结果 —— 这是可信度问题。

本测试把 demo/index.html 里的 JS 算法抽出来，用 Node 执行，
与 Python 引擎在同一批输入上的输出做逐字段比对。

    python -m unittest tests.test_demo_parity -v
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Demo 在 docs/index.html（GitHub Pages 只支持 / 或 /docs，故不放 demo/）
DEMO_HTML = ROOT / "docs" / "index.html"

NODE = r"C:/Users/liuqi/.workbuddy/binaries/node/versions/22.22.2-6/node.exe"

# (now, sleep, consumed_mg)
CAFFEINE_CASES = [
    ("01:30", "07:00", 290),
    ("21:00", "07:00", 0),      # 跨零点：21:00 睡到次日 07:00
    ("03:00", "07:00", 0),
    ("02:00", "07:30", 100),    # one_more 窗口
    ("21:00", "09:00", 400),    # 触顶
    ("23:59", "06:00", 50),
    ("00:01", "07:00", 0),
    ("05:00", "09:00", 150),
    ("19:00", "23:30", 80),
    ("02:30", "07:00", 0),      # 已过截止线
    ("01:59", "07:00", 399),
    ("04:00", "08:00", 200),
]

# (caffeine, sodium, kcal)
LOAD_CASES = [
    (0, 0, 0), (290, 1025, 560), (400, 0, 0),
    (0, 1500, 0), (0, 0, 950), (150, 1200, 700),
]


def extract_js() -> str:
    """从 demo/index.html 抽出算法部分（DOM 相关代码之前）。"""
    html = DEMO_HTML.read_text(encoding="utf-8")
    match = re.search(r"<script>([\s\S]*?)</script>", html)
    assert match, "demo/index.html 里没找到 <script>"
    body = match.group(1)
    cut = body.index("function advice(")
    return body[:cut]


def build_cases() -> list[dict]:
    sys.path.insert(0, str(ROOT / "src"))
    from nightfuel.caffeine import caffeine_budget, sleep_load
    from nightfuel.planner import stage_of

    cases = []
    for now, sleep, caf in CAFFEINE_CASES:
        b = caffeine_budget(sleep_time=sleep, now_time=now, consumed_mg=caf)
        cases.append({
            "kind": "caffeine",
            "now": now, "sleep": sleep, "consumed": caf,
            "py": {
                "cutoff": b.cutoff_time,
                "remaining": b.remaining_mg,
                "verdict": b.verdict,
                "stage": stage_of(int(now[:2])),
            },
        })
    for caf, na, kcal in LOAD_CASES:
        score, tips = sleep_load(caffeine_mg=caf, sodium_mg=na, kcal=kcal)
        cases.append({
            "kind": "load",
            "caf": caf, "na": na, "kcal": kcal,
            "py": {"score": score, "tips": tips},
        })
    return cases


def run_js(cases: list[dict]) -> list[dict]:
    """在 Node 里执行 demo 的 JS 算法，返回与 cases 对齐的结果。"""
    driver = (
        extract_js()
        + "\nmodule.exports={toMin,toHHMM,stageOf,caffeineBudget,sleepLoad};\n"
    )
    module = ROOT / "tests" / "_demo_algo.tmp.js"
    module.write_text(driver, encoding="utf-8")
    payload = json.dumps(cases, ensure_ascii=False)
    script = (
        "const {toMin,toHHMM,stageOf,caffeineBudget,sleepLoad}=require("
        + json.dumps(str(module))
        + ");const cases=" + payload + ";const out=[];"
        "for(const c of cases){if(c.kind==='load'){const r=sleepLoad(c.caf,c.na,c.kcal);"
        "out.push({kind:'load',score:r.score,tips:r.tips});}else{"
        "const r=caffeineBudget(c.sleep,c.now,c.consumed);"
        "out.push({kind:'caffeine',cutoff:r.cutoff,remaining:r.remaining,verdict:r.verdict,"
        "stage:stageOf(+c.now.slice(0,2))});}}console.log(JSON.stringify(out));"
    )
    proc = subprocess.run(
        [NODE, "-e", script], capture_output=True, text=True, encoding="utf-8"
    )
    module.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise AssertionError(f"Node 执行失败:\n{proc.stderr}")
    return json.loads(proc.stdout)


@unittest.skipUnless(DEMO_HTML.exists(), "docs/index.html 不存在")
class TestDemoParity(unittest.TestCase):
    """Demo 的 JS 实现必须与 Python 引擎逐案一致。"""

    @classmethod
    def setUpClass(cls):
        cls.cases = build_cases()
        cls.js = run_js(cls.cases)

    def test_case_count_matches(self):
        self.assertEqual(len(self.js), len(self.cases))

    def test_caffeine_budget_parity(self):
        for case, js in zip(self.cases, self.js):
            if case["kind"] != "caffeine":
                continue
            with self.subTest(now=case["now"], sleep=case["sleep"]):
                self.assertEqual(js["cutoff"], case["py"]["cutoff"])
                self.assertEqual(js["remaining"], case["py"]["remaining"])
                self.assertEqual(js["verdict"], case["py"]["verdict"])
                self.assertEqual(js["stage"], case["py"]["stage"])

    def test_sleep_load_parity(self):
        for case, js in zip(self.cases, self.js):
            if case["kind"] != "load":
                continue
            with self.subTest(load=(case["caf"], case["na"], case["kcal"])):
                self.assertEqual(js["score"], case["py"]["score"])
                self.assertEqual(js["tips"], case["py"]["tips"])

    def test_midnight_wrap_rendering(self):
        """回归：21:00 睡 07:00 必须显示 02:00，不能是 26:00。"""
        idx = next(
            i for i, c in enumerate(self.cases)
            if c.get("kind") == "caffeine" and c["now"] == "21:00" and c["sleep"] == "07:00"
        )
        self.assertEqual(self.js[idx]["cutoff"], "02:00")


if __name__ == "__main__":
    unittest.main()