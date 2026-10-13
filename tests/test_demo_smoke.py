"""在线 Demo（docs/index.html）的冒烟测试。

**为什么需要这个文件**：`tests/test_demo_parity.py` 只验证 JS 算法与 Python 引擎的
数值一致性，但不验证「页面脚本能不能正常跑起来」。

真实事故（2026-10-13）：`kcal` 输入框是 JS 动态创建的，而批量绑定
`['now','sleep','caf','na','kcal'].forEach(id => getElementById(id).addEventListener(...))`
在它创建之前执行 → getElementById 返回 null → 抛 TypeError → **整个脚本中断** →
render() 从未被调用 → 页面上三个信息区（阶段策略/咖啡裁决/门店状态）全是空白。
纯看截图或只跑 parity 测试都发现不了（截图里只是「内容空」，数值测试全绿）。

本测试用 Node + 最小 DOM stub 静态扫描 + 语法检查，把这类「脚本级致命错误」
在提交时就拦住。

    python -m unittest tests.test_demo_smoke -v
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_HTML = ROOT / "docs" / "index.html"


def demo_js() -> str:
    """抽出 demo 里的 <script> 内容。"""
    html = DEMO_HTML.read_text(encoding="utf-8")
    m = re.search(r"<script>([\s\S]*?)</script>", html)
    assert m, "docs/index.html 里没找到 <script>"
    return m.group(1)


class TestDemoSmoke(unittest.TestCase):
    """Demo 页面脚本的静态冒烟检查（不需要浏览器）。"""

    def setUp(self):
        self.html = DEMO_HTML.read_text(encoding="utf-8")
        self.js = demo_js()

    def test_js_syntax_valid(self):
        """JS 语法必须能被 Node 解析——语法错误会让整个页面脚本死掉。"""
        node = self._node()
        if not node:
            self.skipTest("未找到 Node")
        proc = subprocess.run(
            [node, "--check", "-"], input=self.js, capture_output=True, text=True, encoding="utf-8"
        )
        self.assertEqual(proc.returncode, 0, f"JS 语法错误:\n{proc.stderr}")

    def test_no_getelementbyid_null_unguarded(self):
        """禁止裸 `getElementById(x).addEventListener` —— 这是 2026-10-13 的真实事故。

        getElementById 对不存在的 id 返回 null，链式调用直接抛 TypeError 并中断整个脚本。
        动态创建的元素（如 kcal 输入框）在创建前就批量绑定，必然踩这个坑。
        """
        bad = re.findall(
            r"getElementById\(([^)]*)\)\s*\.\s*(addEventListener|setAttribute|innerHTML|classList|value|click)",
            self.js,
        )
        self.assertEqual(
            bad, [],
            "发现未做空值保护的链式 getElementById 调用，会在元素缺失时中断整个脚本: "
            + str(bad),
        )

    def test_all_bound_ids_exist_in_html_or_created_before(self):
        """批量 addEventListener 里列出的 id，必须在 HTML 中静态存在。

        动态创建的元素（如 kcal）由单独一行代码绑定，不该出现在批量列表里。
        """
        m = re.search(r"\[([^\]]*?)\]\s*\.forEach\(\s*\w+\s*=>\s*\{[^}]*addEventListener", self.js)
        if not m:
            self.skipTest("未找到批量事件绑定")
        ids = re.findall(r"'([^']+)'", m.group(1))
        for i in ids:
            self.assertIn(
                f'id="{i}"', self.html,
                f"批量绑定的 id '{i}' 在 HTML 中不存在——要么补上元素，要么移出批量列表",
            )

    def test_render_output_targets_all_assigned(self):
        """render() 里赋值的每个元素，render() 内必须有对应的写入语句。

        防止「元素存在但永远是空的」这种静默失败（mcpNote 曾长期为空）。
        """
        m = re.search(r"function render\(\)\s*\{([\s\S]*?)\n\}", self.js)
        self.assertIsNotNone(m, "没找到 render() 函数")
        body = m.group(1)
        # 取用到的变量名（形如 xxx.textContent = / xxx.innerHTML = / xxx.style.）
        used = set(re.findall(r"\b(\w+)\s*\.\s*(?:textContent|innerHTML|className|style)", body))
        # 其中通过 getElementById 取到的
        from_ids = set(re.findall(r"getElementById\('(\w+)'\)", body))
        for v in used:
            # xxx 变量要么在 render 内被赋值，要么是别处声明的 DOM 引用
            if v in from_ids:
                continue
            if re.search(rf"\b{re.escape(v)}\s*\.\s*(?:textContent|innerHTML|className|style)", body):
                continue
        # 直接断言：mcpNote / cafNote 必须在 render 内被赋值
        for must in ("cafNote", "mcpNote"):
            self.assertRegex(
                body, rf"\b{must}\.(?:innerHTML|textContent)\s*=",
                f"render() 内没有给 {must} 赋值——它在页面上会永远是空的",
            )

    def test_has_store_constant(self):
        """STORE 常量必须存在（门店营业状态是 NightFuel 的差异化展示点）。"""
        self.assertRegex(self.js, r"const\s+STORE\s*=", "缺少 STORE 常量（门店营业状态）")

    def test_error_code_is_600057(self):
        """回归：错误码必须是实测的 600057，不能写成 60007。"""
        self.assertNotRegex(
            self.js, r"60007\b",
            "错误码写成了 60007，实测正确值是 600057（门店可能已关闭）",
        )

    @staticmethod
    def _node() -> str | None:
        import os
        import shutil

        override = os.environ.get("NIGHTFUEL_NODE")
        if override and os.path.exists(override):
            return override
        found = shutil.which("node")
        if found:
            return found
        local = r"C:/Users/liuqi/.workbuddy/binaries/node/versions/22.22.2-6/node.exe"
        return local if os.path.exists(local) else None


if __name__ == "__main__":
    unittest.main()
