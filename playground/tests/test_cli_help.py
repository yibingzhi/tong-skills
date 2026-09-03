from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cli_help import parse_argparse_help


PROMPT_HELP = """
usage: scan.py [-h] [--lane {image,video}] [file]

positional arguments:
  file                  prompt file, or - for stdin

options:
  -h, --help            show this help message and exit
  --lane {image,video}
  --target {generic,mj,jimeng,kling}
  --anchor TEXT         comma-separated must-have phrases in the prompt body.
                        Repeatable.
  --json                machine-readable report
  --list                print lanes and checks
"""

GIT_HELP = """
positional arguments:
  {status,commit,push,publish,add}
    status              repo, branch, dirty files, remotes

options:
  -h, --help            show this help message and exit
  --repo REPO           git work tree (default: current directory)
"""

CHART_HELP = """
positional arguments:
  input                 Path to a .mmd file

options:
  -o, --output OUTPUT   Output PNG path
  --svg                 Also write SVG
  --classdef | --no-classdef
"""


class TestParseHelp(unittest.TestCase):
    def test_prompt_fields(self) -> None:
        fields = {item["id"]: item for item in parse_argparse_help(PROMPT_HELP)}
        self.assertIn("file", fields)
        self.assertTrue(fields["file"]["positional"])
        self.assertEqual(fields["lane"]["kind"], "choice")
        self.assertEqual(fields["lane"]["choices"], ["image", "video"])
        self.assertEqual(fields["json"]["kind"], "flag")
        self.assertNotIn("help", fields)
        self.assertIn("Repeatable", fields["anchor"]["help"])

    def test_git_subcommand(self) -> None:
        fields = {item["id"]: item for item in parse_argparse_help(GIT_HELP)}
        self.assertEqual(fields["command"]["kind"], "choice")
        self.assertIn("commit", fields["command"]["choices"])
        self.assertEqual(fields["repo"]["kind"], "text")

    def test_short_and_mutex_flags(self) -> None:
        fields = {item["id"]: item for item in parse_argparse_help(CHART_HELP)}
        self.assertEqual(fields["output"]["flags"][0], "-o")
        self.assertEqual(fields["svg"]["kind"], "flag")
        self.assertIn("classdef", fields)
        self.assertIn("no-classdef", fields)


if __name__ == "__main__":
    unittest.main()
