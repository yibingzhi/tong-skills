#!/usr/bin/env python3
"""Run a skill's bundled script from this checkout. Does not install the skill."""

from __future__ import annotations

import argparse
import subprocess
import sys

from skillmeta import list_skill_dirs, repo_root, skill_entry_script


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Example: python scripts/run_skill.py tong-cover --list",
    )
    parser.add_argument("skill", help="folder name under skills/")
    parser.add_argument("script_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    root = repo_root()
    skill_dir = root / "skills" / args.skill
    known = ", ".join(path.name for path in list_skill_dirs(root)) or "(none)"
    if not skill_dir.is_dir():
        raise SystemExit(f"unknown skill {args.skill!r}. have: {known}")
    script = skill_entry_script(skill_dir)
    extra = list(args.script_args)
    if extra and extra[0] == "--":
        extra = extra[1:]
    cmd = [sys.executable, str(script), *extra]
    print("run:", " ".join(cmd))
    return subprocess.run(cmd, cwd=str(root)).returncode


if __name__ == "__main__":
    raise SystemExit(main())
