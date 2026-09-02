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


if __name__ == "__main__":
    unittest.main()
