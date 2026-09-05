#!/usr/bin/env python3
"""Validate every skill in this repo. Exit 0 only when the catalog is consistent."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

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
LOCAL_LINK = re.compile(r'\[[^\]\n]+\]\((?:<([^>]+)>|([^\s)]+))(?:\s+"[^"]*")?\)')
BUNDLED_PATH = re.compile(r"<skill-dir>/((?:scripts|references|assets)/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)")


def check_resources(skill_dir: Path, errors: list[str]) -> None:
    """Check links relative to their document, including on-demand references."""
    documents = [skill_dir / "SKILL.md"]
    documents.extend(sorted((skill_dir / "references").rglob("*.md")))
    root = skill_dir.resolve()
    for document in documents:
        text = document.read_text(encoding="utf-8")
        targets = [(match.group(1) or match.group(2), document.parent)
                   for match in LOCAL_LINK.finditer(text)]
        targets.extend((match.group(1), skill_dir) for match in BUNDLED_PATH.finditer(text))
        for target, base in targets:
            if target.startswith("#") or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            relative = unquote(target.split("#", 1)[0].split("?", 1)[0])
            linked = (base / relative).resolve()
            if linked != root and root not in linked.parents:
                fail(errors, f"{document}: resource escapes installable skill: {target}")
            elif not linked.exists():
                fail(errors, f"{document}: missing bundled resource {target}")


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
    if len(name) > MAX_NAME or not NAME_RE.fullmatch(name):
        fail(errors, f"{path}: invalid name {name!r}")
    if not name.startswith("tong-") or name == "tong-":
        fail(errors, f"{path}: public skill name must be tong-<job>")

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
    if not isinstance(extra, dict) or extra.get("author") != "TongSkills":
        fail(errors, f"{path}: metadata.author must be TongSkills")

    body = str(meta.get("_body") or "")
    line_count = len(meta["_text"].splitlines())
    if line_count >= MAX_SKILL_LINES:
        fail(errors, f"{path}: {line_count} lines (must be < {MAX_SKILL_LINES})")

    if (re.match(r"TODO\b", desc, re.I)
            or re.search(r"\{\{[A-Z_]+\}\}", meta["_text"])
            or re.search(r"(?m)^\s*(?:[-*]\s+)?TODO(?:\s*:|\s*$)", body)
            or "One paragraph: what the agent actually does. No marketing." in body):
        fail(errors, f"{path}: unfinished scaffold placeholder")
    check_resources(skill_dir, errors)

    if any((skill_dir / "scripts").rglob("*.py")):
        if not any((skill_dir / "tests").rglob("test_*.py")):
            fail(errors, f"{skill_dir.name}: bundled scripts require tests/test_*.py")

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
        row = rf"(?m)^\|\s*\[{re.escape(name)}\]\(skills/{re.escape(name)}/\)\s*\|"
        if not re.search(row, readme):
            fail(errors, f"README.md missing catalog row for {name}")


def run_tests(skill_dir: Path, errors: list[str]) -> None:
    run_test_directory(skill_dir / "tests", skill_dir, skill_dir.name, errors)


def run_test_directory(tests: Path, cwd: Path, label: str, errors: list[str]) -> None:
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
        cwd=str(cwd),
    )
    if result.returncode != 0:
        fail(errors, f"{label}: tests failed")


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
        run_test_directory(root / "scripts" / "tests", root, "repo tooling", errors)
        run_test_directory(root / "playground" / "tests", root, "playground", errors)

    if errors:
        print("validate failed:", file=sys.stderr)
        for item in errors:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print(f"ok: {len(dirs)} skill(s) - {', '.join(sorted(names))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
