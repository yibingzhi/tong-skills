from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from scan import failed_count, load_rules, main, scan_text, warn_count


FIX = Path(__file__).resolve().parent / "fixtures"


def run_main(argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


class TestScan(unittest.TestCase):
    def test_list(self) -> None:
        code, out = run_main(["--list"])
        self.assertEqual(code, 0)
        self.assertIn("general", out)
        self.assertIn("WARN", out)

    def test_slop_fails(self) -> None:
        code, out = run_main([str(FIX / "slop.md"), "--lane", "general", "--json"])
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertFalse(data["pass"])
        self.assertIn("套话", data["hits"])
        self.assertIn("喊话CTA", data["hits"])
        self.assertIn("不是而是", data["warnings"])
        self.assertIn("三段式", data["warnings"])

    def test_clean_passes_general(self) -> None:
        code, out = run_main([str(FIX / "clean.md"), "--json"])
        self.assertEqual(code, 0, out)
        data = json.loads(out)
        self.assertTrue(data["pass"])
        self.assertEqual(data["warnings"], {})

    def test_good_contrast_is_warn_not_fail(self) -> None:
        text = "我爱上的不是你的容貌，而是你说话的方式。"
        result = scan_text(text, "general")
        self.assertEqual(failed_count(result), 0)
        self.assertTrue(result["warn"]["不是而是"])
        code, out = run_main([str(FIX / "contrast.md"), "--json"])
        self.assertEqual(code, 0, out)
        self.assertIn("不是而是", json.loads(out)["warnings"])

    def test_nny_is_hard_fail(self) -> None:
        result = scan_text("不是英雄。不是圣人。只是一个普通人。", "general")
        self.assertTrue(result["fail"]["否定列举"])
        result = scan_text("不是错误，不是特性，而是设计缺陷。", "general")
        self.assertTrue(result["fail"]["否定列举"])

    def test_engineering_jargon_warns_business_jargon_fails(self) -> None:
        eng = scan_text("温控闭环已经调稳，超调从 8% 收到 2%。", "general")
        self.assertEqual(failed_count(eng), 0)
        self.assertIn("闭环 x1", eng["warn"]["疑似空话"])
        biz = scan_text("赋能业务，形成增长闭环。", "general")
        self.assertTrue(biz["fail"]["套话"])
        self.assertNotIn("闭环 x1", biz["warn"]["疑似空话"])

    def test_time_and_url_colon_ignored(self) -> None:
        text = (FIX / "clean.md").read_text(encoding="utf-8")
        hits = scan_text(text, "wechat")
        self.assertEqual(hits["fail"]["标点"], [])

    def test_wechat_quotes_fail(self) -> None:
        self.assertTrue(scan_text('他说“可以”。', "wechat")["fail"]["标点"])
        self.assertFalse(scan_text('他说“可以”。', "general")["fail"]["标点"])

    def test_general_allows_two_dashes(self) -> None:
        two = "一句——两句——。"
        three = "一句——两句——三句——。"
        self.assertEqual(scan_text(two, "general")["fail"]["标点"], [])
        self.assertTrue(scan_text(three, "general")["fail"]["标点"])
        self.assertTrue(scan_text(two, "wechat")["fail"]["标点"])

    def test_stack_same_paragraph(self) -> None:
        code, _ = run_main([str(FIX / "stack.md")])
        self.assertEqual(code, 1)
        lonely = scan_text("他猛地站起来，把门关上。", "general")
        self.assertEqual(lonely["fail"]["堆叠副词"], [])

    def test_first_alone_is_not_triad(self) -> None:
        hits = scan_text("最后再看一眼日志。", "general")
        self.assertEqual(hits["warn"]["三段式"], [])

    def test_house_rules_are_opt_in(self) -> None:
        text = "内部代号先别写，我们团队的排期也别写。"
        self.assertNotIn("家规", scan_text(text, "brief")["fail"])
        rules = load_rules([str(FIX / "house-rules.txt")])
        hit = scan_text(text, "brief", rules)["fail"]["家规"]
        self.assertEqual(len(hit), 2)
        code, out = run_main(
            [str(FIX / "clean.md"), "--rules", str(FIX / "house-rules.txt"), "--json"]
        )
        self.assertEqual(code, 0, out)
        self.assertIn("家规", json.loads(out)["checks"]["fail"])

    def test_bad_rules_file(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            code, _ = run_main([str(FIX / "clean.md"), "--rules", "nope-rules.txt"])
        self.assertEqual(code, 2)
        self.assertIn("rules file not found", err.getvalue())

    def test_literary_wechat_only_for_ru(self) -> None:
        text = "阳光仿佛停了一下。"
        self.assertTrue(scan_text(text, "wechat")["fail"]["网文腔"])
        self.assertFalse(scan_text(text, "general")["fail"]["网文腔"])

    def test_report_shows_snippet_not_regex(self) -> None:
        code, out = run_main([str(FIX / "contrast.md")])
        self.assertEqual(code, 0)
        self.assertIn("WARN", out)
        self.assertIn("「", out)
        self.assertNotIn("[^", out)

    def test_missing_file(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            code, _ = run_main(["missing-nope.md"])
        self.assertEqual(code, 2)
        self.assertIn("not a file", err.getvalue())

    def test_counts(self) -> None:
        result = {"fail": {"a": [], "b": ["x"]}, "warn": {"c": ["y"], "d": []}}
        self.assertEqual(failed_count(result), 1)
        self.assertEqual(warn_count(result), 1)


if __name__ == "__main__":
    unittest.main()
