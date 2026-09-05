from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "make_cover.py"


def run_script(*args: str) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        env=env,
    )


def load_cli():
    sys.path.insert(0, str(SKILL / "scripts"))
    from brand_cover.cli import parse_bullets_arg, parse_dividers_arg

    return parse_bullets_arg, parse_dividers_arg


class TestTongCover(unittest.TestCase):
    def test_script_exists(self) -> None:
        self.assertTrue(SCRIPT.is_file())

    def test_parse_bullets_and_dividers(self) -> None:
        parse_bullets_arg, parse_dividers_arg = load_cli()
        self.assertEqual(parse_bullets_arg("一;二;三"), ["一", "二", "三"])
        self.assertEqual(
            parse_dividers_arg("01:今日头条:核心动态"),
            [("01", "今日头条", "核心动态")],
        )

    def test_list_cli(self) -> None:
        result = run_script("--list")
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        out = result.stdout.decode("utf-8", "replace")
        self.assertIn("presets:", out)
        self.assertIn("layouts:", out)
        self.assertIn("feed", out)

    def test_feed_png(self) -> None:
        try:
            spec = importlib.util.find_spec("PIL")
        except ValueError:
            spec = None
        if spec is None:
            self.skipTest("Pillow not installed")
        with tempfile.TemporaryDirectory(prefix="tong-cover-") as tmp:
            out = Path(tmp) / "feed.png"
            result = run_script(
                "--layout",
                "feed",
                "--ratio",
                "2.35:1",
                "--out",
                str(out),
            )
            self.assertEqual(
                result.returncode,
                0,
                result.stderr.decode("utf-8", "replace")
                + result.stdout.decode("utf-8", "replace"),
            )
            self.assertTrue(out.is_file())
            self.assertTrue(out.read_bytes().startswith(b"\x89PNG"))

    def test_quote_tokens_parsing(self) -> None:
        sys.path.insert(0, str(SKILL / "scripts"))
        from brand_cover.render import _parse_quote_tokens

        tokens = _parse_quote_tokens("打工是出租算力，副业是在给自己==买服务器==。")
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[0], ("打工是出租算力，副业是在给自己", False))
        self.assertEqual(tokens[1], ("买服务器", True))
        self.assertEqual(tokens[2], ("。", False))

        tokens_hl = _parse_quote_tokens("离开公司还能带走的东西才是资产。", highlight="资产")
        self.assertEqual(tokens_hl, [("离开公司还能带走的东西才是", False), ("资产", True), ("。", False)])

    def test_quote_card_styles_and_ratios(self) -> None:
        try:
            spec = importlib.util.find_spec("PIL")
        except ValueError:
            spec = None
        if spec is None:
            self.skipTest("Pillow not installed")

        cases = [
            ("paper", "3:4"),
            ("editorial", "1:1"),
            ("highlight", "3:4"),
            ("dark", "9:16"),
            ("cinema", "3:4"),
            ("polaroid", "1:1"),
            ("tweet", "3:4"),
        ]
        with tempfile.TemporaryDirectory(prefix="tong-quote-") as tmp:
            for style, ratio in cases:
                out = Path(tmp) / f"quote_{style}_{ratio.replace(':', '_')}.png"
                result = run_script(
                    "--layout",
                    "quote",
                    "--style",
                    style,
                    "--ratio",
                    ratio,
                    "--quote",
                    "流水不争先，争的是==滔滔不绝==。",
                    "--author",
                    "老子",
                    "--source",
                    "道德经",
                    "--sub",
                    "保持复利与长期主义。",
                    "--out",
                    str(out),
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"Failed {style} {ratio}: " + result.stderr.decode("utf-8", "replace"),
                )
                self.assertTrue(out.is_file())
                self.assertTrue(out.read_bytes().startswith(b"\x89PNG"))

    def test_themes_swiss_and_press(self) -> None:
        try:
            spec = importlib.util.find_spec("PIL")
        except ValueError:
            spec = None
        if spec is None:
            self.skipTest("Pillow not installed")

        with tempfile.TemporaryDirectory(prefix="tong-themes-") as tmp:
            for theme in ("swiss", "press"):
                out = Path(tmp) / f"feed_{theme}.png"
                result = run_script(
                    "--layout",
                    "feed",
                    "--theme",
                    theme,
                    "--title",
                    "测试现代主题",
                    "--sub",
                    "国际主义平面网格排版",
                    "--out",
                    str(out),
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"Failed theme {theme}: " + result.stderr.decode("utf-8", "replace"),
                )
                self.assertTrue(out.is_file())
                self.assertTrue(out.read_bytes().startswith(b"\x89PNG"))

    def test_brand_custom_and_clean_modes(self) -> None:
        try:
            spec = importlib.util.find_spec("PIL")
        except ValueError:
            spec = None
        if spec is None:
            self.skipTest("Pillow not installed")

        with tempfile.TemporaryDirectory(prefix="tong-brand-") as tmp:
            # 1. Custom brand
            out_custom = Path(tmp) / "quote_custom.png"
            res1 = run_script(
                "--layout", "quote",
                "--style", "polaroid",
                "--brand", "晚点LatePost",
                "--quote", "专注深度报道。",
                "--out", str(out_custom),
            )
            self.assertEqual(res1.returncode, 0, res1.stderr.decode("utf-8", "replace"))
            self.assertTrue(out_custom.is_file())

            # 2. Clean empty brand (no watermark mode)
            out_clean = Path(tmp) / "quote_clean.png"
            res2 = run_script(
                "--layout", "quote",
                "--style", "paper",
                "--brand", "",
                "--quote", "大道至简，纯净无痕。",
                "--out", str(out_clean),
            )
            self.assertEqual(res2.returncode, 0, res2.stderr.decode("utf-8", "replace"))
            self.assertTrue(out_clean.is_file())

            # 3. Clean briefing cover (no brand watermark)
            out_briefing = Path(tmp) / "briefing_clean.png"
            res3 = run_script(
                "--layout", "briefing",
                "--brand", "",
                "--title", "纯净简报",
                "--bullets", "纯净模式无水印;自适应排版",
                "--out", str(out_briefing),
            )
            self.assertEqual(res3.returncode, 0, res3.stderr.decode("utf-8", "replace"))
            self.assertTrue(out_briefing.is_file())


if __name__ == "__main__":
    unittest.main()

