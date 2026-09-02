#!/usr/bin/env python3
"""Scaffold a new skill under skills/<name>/ and append catalog.yaml."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from skillmeta import NAME_RE, list_skill_dirs, repo_root


def display_name(name: str) -> str:
    return name.replace("-", " ").title().replace("Tong", "Tong")


def render(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace("{{" + key + "}}", value)
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if leftover:
        raise SystemExit(f"unreplaced template keys: {', '.join(leftover)}")
    return out


def append_catalog(root: Path, name: str, summary: str) -> None:
    path = root / "catalog.yaml"
    text = path.read_text(encoding="utf-8")
    if re.search(rf"^  - name:\s*{re.escape(name)}\s*$", text, re.M):
        return
    block = (
        f"  - name: {name}\n"
        f"    status: draft\n"
        f"    summary: {summary}\n"
        f"    tags: todo\n"
    )
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + block, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="tong-<job>, e.g. tong-chart")
    parser.add_argument(
        "--description",
        default="",
        help="SKILL.md description (what + when). Prompt later if omitted.",
    )
    parser.add_argument(
        "--summary",
        default="",
        help="one-line catalog / openai short_description",
    )
    args = parser.parse_args()
    name = args.name.strip()
    if not NAME_RE.match(name) or len(name) > 64:
        raise SystemExit(
            f"invalid name {name!r}: lowercase letters, digits, single hyphens only"
        )
    if not name.startswith("tong-") or name == "tong-":
        raise SystemExit(
            f"invalid name {name!r}: public skills must be tong-<job>, e.g. tong-chart"
        )

    root = repo_root()
    dest = root / "skills" / name
    if dest.exists():
        raise SystemExit(f"already exists: {dest}")

    description = args.description.strip() or (
        f"TODO: what this skill does and when to use it. "
        f"Include trigger terms for {name}."
    )
    summary = args.summary.strip() or description.split(".")[0]
    mapping = {
        "NAME": name,
        "DISPLAY": display_name(name),
        "DESCRIPTION": description,
        "SUMMARY": summary,
    }

    tmpl_dir = root / "templates"
    skill_body = render(
        (tmpl_dir / "SKILL.md.tmpl").read_text(encoding="utf-8"), mapping
    )
    openai_body = render(
        (tmpl_dir / "openai.yaml.tmpl").read_text(encoding="utf-8"), mapping
    )

    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text(skill_body, encoding="utf-8")
    (dest / "agents").mkdir()
    (dest / "agents" / "openai.yaml").write_text(openai_body, encoding="utf-8")
    (dest / "references").mkdir()
    (dest / "references" / "notes.md").write_text(
        f"# {mapping['DISPLAY']} notes\n\nOn-demand detail. Keep SKILL.md short.\n",
        encoding="utf-8",
    )
    append_catalog(root, name, summary)

    print(f"created: {dest}")
    print("next:")
    print(f"  1. Fill skills/{name}/SKILL.md (see docs/authoring.md)")
    print("  2. Add a README catalog row")
    print("  3. python scripts/validate_skills.py")
    existing = ", ".join(path.name for path in list_skill_dirs(root))
    print(f"skills now: {existing}")


if __name__ == "__main__":
    main()
