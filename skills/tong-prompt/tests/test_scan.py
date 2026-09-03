from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

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
        self.assertIn("image", out)
        self.assertIn("WARN", out)
        self.assertIn("mj", out)

    def test_slop_fails_stack_and_schools(self) -> None:
        code, out = run_main(
            [str(FIX / "slop.txt"), "--lane", "image", "--target", "mj", "--json"]
        )
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertFalse(data["pass"])
        self.assertIn("画法堆叠", data["hits"])
        self.assertIn("塑料堆叠", data["hits"])
        self.assertIn("出处外配件", data["warnings"])

    def test_clean_bifang_passes(self) -> None:
        code, out = run_main(
            [
                str(FIX / "clean.txt"),
                "--json",
                "--anchor",
                "one-legged,burning ancient pine,flame from the open beak",
            ]
        )
        self.assertEqual(code, 0, out)
        data = json.loads(out)
        self.assertTrue(data["pass"])
        self.assertEqual(data["hits"], {})
        self.assertNotIn("未声明锚点", data["warnings"])
        self.assertNotIn("画法堆叠", data["hits"])

    def test_not_photoreal_is_not_a_school(self) -> None:
        text = (FIX / "clean.txt").read_text(encoding="utf-8")
        result = scan_text(text, "image", "mj", "gongbi")
        self.assertEqual(failed_count(result), 0, result["fail"])

    def test_anchor_missing_fails(self) -> None:
        code, out = run_main(
            [str(FIX / "clean.txt"), "--json", "--anchor", "three heads"]
        )
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertIn("锚点缺失", data["hits"])

    def test_camera_fails_on_image_lane(self) -> None:
        code, out = run_main(
            [str(FIX / "camera.txt"), "--lane", "image", "--json"]
        )
        self.assertEqual(code, 1)
        self.assertIn("动静混写", json.loads(out)["hits"])

    def test_camera_ok_on_video_lane(self) -> None:
        code, out = run_main(
            [str(FIX / "camera.txt"), "--lane", "video", "--json"]
        )
        self.assertEqual(code, 0, out)
        data = json.loads(out)
        self.assertNotIn("动静混写", data["hits"])
        self.assertNotIn("缺时长", data["warnings"])

    def test_mj_flags_fail_on_jimeng(self) -> None:
        code, out = run_main(
            [str(FIX / "mj-flags.txt"), "--target", "jimeng", "--json"]
        )
        self.assertEqual(code, 1)
        self.assertIn("工具尾缀", json.loads(out)["hits"])

    def test_mj_flags_ok_on_mj(self) -> None:
        code, out = run_main(
            [str(FIX / "mj-flags.txt"), "--target", "mj", "--look", "gongbi", "--json"]
        )
        self.assertEqual(code, 0, out)

    def test_cine_look_rejects_gongbi(self) -> None:
        text = (
            "Bifang one-legged on a burning pine, cinematic lighting, "
            "Chinese gongbi bird-and-flower."
        )
        result = scan_text(text, "image", "generic", "cine")
        self.assertTrue(result["fail"]["画派打架"])

    def test_cine_fixture_passes(self) -> None:
        code, out = run_main([str(FIX / "cine.txt"), "--json"])
        self.assertEqual(code, 0, out)
        self.assertNotIn("画派打架", json.loads(out)["hits"])

    def test_warn_without_anchor(self) -> None:
        result = scan_text("a red bird on a pine, mist only.", "image", "generic", "auto")
        self.assertEqual(failed_count(result), 0)
        self.assertTrue(result["warn"]["未声明锚点"])
        self.assertEqual(warn_count(result), 1)

    def test_house_rules(self) -> None:
        rules = load_rules([str(FIX / "house-rules.txt")])
        hit = scan_text(
            (FIX / "house-hit.txt").read_text(encoding="utf-8"),
            "image",
            "generic",
            "auto",
            rules=rules,
        )
        self.assertTrue(hit["fail"]["家规"])
        code, out = run_main(
            [
                str(FIX / "clean.txt"),
                "--rules",
                str(FIX / "house-rules.txt"),
                "--json",
            ]
        )
        self.assertEqual(code, 0, out)
        self.assertIn("家规", json.loads(out)["checks"]["fail"])

    def test_bad_rules_file(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            code, _ = run_main([str(FIX / "clean.txt"), "--rules", "nope-rules.txt"])
        self.assertEqual(code, 2)
        self.assertIn("rules file not found", err.getvalue())

    def test_stdin_scan(self) -> None:
        text = (FIX / "clean.txt").read_text(encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            with patch("sys.stdin", io.StringIO(text)):
                code = main(["-", "--json"])
        self.assertEqual(code, 0, buf.getvalue())
        self.assertTrue(json.loads(buf.getvalue())["pass"])

    def test_missing_file(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            code, _ = run_main(["missing-nope.txt"])
        self.assertEqual(code, 2)
        self.assertIn("not a file", err.getvalue())

    def test_counts(self) -> None:
        result = {"fail": {"a": [], "b": ["x"]}, "warn": {"c": ["y"], "d": []}}
        self.assertEqual(failed_count(result), 1)
        self.assertEqual(warn_count(result), 1)

    def test_file_required(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            code, _ = run_main([])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
