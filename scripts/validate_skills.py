#!/usr/bin/env python3
"""Validate every skill in this repo. Exit 0 only when the catalog is consistent."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from skillmeta import (
    FORBIDDEN,
    NAME_RE,
    list_skill_dirs,
    load_catalog,
    load_skill,
    repo_root,
    skill_version,
)


MAX_NAME = 64
MAX_DESC = 1024
MAX_COMPAT = 500
MAX_SKILL_LINES = 500


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def check_no_stray_skill_md(root: Path, errors: list[str]) -> None:
    allowed_root = (root / "skills").resolve()
    for path in root.rglob("SKILL.md"):
        resolved = path.resolve()
        if allowed_root not in resolved.parents:
            fail(errors, f"SKILL.md must live under skills/: {path.relative_to(root)}")
            continue
        rel = resolved.relative_to(allowed_root)
        if len(rel.parts) != 2:
            fail(
                errors,
                f"skills must be flat (skills/<name>/SKILL.md): {path.relative_to(root)}",
            )


def check_skill(meta: dict, errors: list[str]) -> None:
    path: Path = meta["_path"]
    skill_dir: Path = meta["_dir"]
    name = str(meta.get("name") or "")
    if not name:
        fail(errors, f"{path}: missing name")
        return
    if name != skill_dir.name:
        fail(errors, f"{path}: name {name!r} != directory {skill_dir.name!r}")
    if len(name) > MAX_NAME or not NAME_RE.match(name):
        fail(errors, f"{path}: invalid name {name!r}")

    desc = str(meta.get("description") or "").strip()
    if not desc:
        fail(errors, f"{path}: missing description")
    elif len(desc) > MAX_DESC:
        fail(errors, f"{path}: description is {len(desc)} chars (max {MAX_DESC})")

    license_name = str(meta.get("license") or "").strip()
    if license_name != "MIT":
        fail(errors, f"{path}: license must be MIT (got {license_name!r})")

    compat = meta.get("compatibility")
    if compat is not None and (
        not str(compat).strip() or len(str(compat)) > MAX_COMPAT
    ):
        fail(errors, f"{path}: compatibility must be 1–{MAX_COMPAT} chars")

    try:
        skill_version(meta)
    except ValueError as exc:
        fail(errors, str(exc))

    extra = meta.get("metadata") or {}
    if isinstance(extra, dict) and not extra.get("author"):
        fail(errors, f"{path}: metadata.author is required")

    body = str(meta.get("_body") or "")
    line_count = len(meta["_text"].splitlines())
    if line_count > MAX_SKILL_LINES:
        fail(errors, f"{path}: {line_count} lines (max {MAX_SKILL_LINES})")

    for match in re.finditer(r"\(([^)]+\.md)\)", body):
        target = match.group(1)
        if target.startswith(("http://", "https://", "#")):
            continue
        linked = (skill_dir / target).resolve()
        if not linked.is_file():
            fail(errors, f"{path}: broken link {target}")

    if "\\" in body and re.search(r"[A-Za-z]:\\|\\\\", body):
        fail(errors, f"{path}: use forward slashes, not Windows paths")

    lowered = meta["_text"].encode("utf-8").lower()
    for marker in FORBIDDEN:
        if marker.lower() in lowered:
            fail(errors, f"{path}: forbidden marker {marker.decode()!r}")


def check_catalog(root: Path, skill_names: set[str], errors: list[str]) -> None:
    catalog = load_catalog(root)
    listed = [row["name"] for row in catalog["skills"]]
    listed_set = set(listed)
    if len(listed) != len(listed_set):
        fail(errors, "catalog.yaml has duplicate names")
    missing = skill_names - listed_set
    extra = listed_set - skill_names
    if missing:
        fail(errors, f"catalog.yaml missing: {', '.join(sorted(missing))}")
    if extra:
        fail(errors, f"catalog.yaml extra: {', '.join(sorted(extra))}")
    readme = (root / "README.md").read_text(encoding="utf-8")
    for name in sorted(skill_names):
        if name not in readme:
            fail(errors, f"README.md does not mention skill {name}")


def run_tests(skill_dir: Path, errors: list[str]) -> None:
    tests = skill_dir / "tests"
    if not tests.is_dir():
        return
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(tests),
            "-p",
            "test_*.py",
        ],
        cwd=str(skill_dir),
    )
    if result.returncode != 0:
        fail(errors, f"{skill_dir.name}: tests failed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate skills in this checkout. Does not install them."
    )
    parser.add_argument(
        "skill",
        nargs="?",
        help="only this skills/<name>/ folder (default: all)",
    )
    args = parser.parse_args(argv)

    root = repo_root()
    errors: list[str] = []
    if args.skill:
        check_no_stray_skill_md(root, errors)
        dirs = [root / "skills" / args.skill]
        if not dirs[0].is_dir():
            fail(errors, f"unknown skill {args.skill!r}")
            print("validate failed:", file=sys.stderr)
            for item in errors:
                print(f"  - {item}", file=sys.stderr)
            return 1
        names = {args.skill}
    else:
        check_no_stray_skill_md(root, errors)
        dirs = list_skill_dirs(root)
        if not dirs:
            fail(errors, "no skills found under skills/")
        names = {path.name for path in dirs}

    for skill_dir in dirs:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            fail(errors, f"missing {skill_md.relative_to(root)}")
            continue
        try:
            meta = load_skill(skill_dir)
        except ValueError as exc:
            fail(errors, f"{skill_md}: {exc}")
            continue
        check_skill(meta, errors)
        run_tests(skill_dir, errors)
    if not args.skill:
        check_catalog(root, names, errors)

    if errors:
        print("validate failed:", file=sys.stderr)
        for item in errors:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print(f"ok: {len(dirs)} skill(s) - {', '.join(sorted(names))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
