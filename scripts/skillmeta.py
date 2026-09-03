#!/usr/bin/env python3
"""Shared metadata helpers for TongSkills repo tooling."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FORBIDDEN = (
    b"github_pat_",
    b"api_key",
    b"API_KEY=",
    b"password",
    b"PASSWORD=",
    b"Bearer ",
    b"BEGIN OPENSSH PRIVATE KEY",
    b"BEGIN RSA PRIVATE KEY",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def skills_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "skills"


def list_skill_dirs(root: Path | None = None) -> list[Path]:
    base = skills_dir(root)
    if not base.is_dir():
        return []
    return sorted(
        path
        for path in base.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    rest = text[3:].lstrip("\r\n")
    match = re.search(r"\n---\s*(?:\n|$)", rest)
    if not match:
        raise ValueError("unterminated YAML frontmatter")
    return rest[: match.start()], rest[match.end() :]


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse the SKILL.md subset: scalars, folded strings, one-level maps."""
    data: dict[str, Any] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.strip().startswith("#"):
            i += 1
            continue
        if raw.startswith(" ") or raw.startswith("\t"):
            raise ValueError(f"unexpected indent: {raw!r}")
        if ":" not in raw:
            raise ValueError(f"expected key: {raw!r}")
        key, _, rest = raw.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest in {">", ">-", "|", "|-"}:
            folded: list[str] = []
            i += 1
            while i < len(lines) and (
                not lines[i].strip() or lines[i].startswith((" ", "\t"))
            ):
                folded.append(lines[i].strip())
                i += 1
            joined = " ".join(part for part in folded if part)
            if rest.startswith("|"):
                joined = "\n".join(part for part in folded if part)
            data[key] = joined
            continue
        if rest == "":
            nested: dict[str, str] = {}
            i += 1
            while i < len(lines) and lines[i].startswith((" ", "\t")):
                child = lines[i].strip()
                if child and not child.startswith("#"):
                    if ":" not in child:
                        raise ValueError(f"expected nested key: {child!r}")
                    ck, _, cv = child.partition(":")
                    nested[ck.strip()] = _unquote(cv)
                i += 1
            data[key] = nested
            continue
        data[key] = _unquote(rest)
        i += 1
    return data


def load_skill(skill_dir: Path) -> dict[str, Any]:
    path = skill_dir / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    fm_text, body = split_frontmatter(text)
    meta = parse_frontmatter(fm_text)
    meta["_body"] = body
    meta["_text"] = text
    meta["_path"] = path
    meta["_dir"] = skill_dir
    return meta


def load_catalog(root: Path | None = None) -> dict[str, Any]:
    path = (root or repo_root()) / "catalog.yaml"
    text = path.read_text(encoding="utf-8")
    license_name = "MIT"
    match = re.search(r"^license:\s*(.+)$", text, re.M)
    if match:
        license_name = match.group(1).strip()
    skills: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        if line.startswith("  - name:"):
            if current:
                skills.append(current)
            current = {"name": line.split(":", 1)[1].strip()}
            continue
        if current is None:
            continue
        nested = re.match(r"^    ([A-Za-z0-9_]+):\s*(.*)$", line)
        if nested:
            current[nested.group(1)] = nested.group(2).strip()
    if current:
        skills.append(current)
    return {"license": license_name, "skills": skills, "_path": path}


def skill_version(meta: dict[str, Any]) -> str:
    extra = meta.get("metadata") or {}
    if isinstance(extra, dict) and extra.get("version"):
        return str(extra["version"]).strip().strip('"')
    raise ValueError(f"{meta.get('_path')}: metadata.version is required")


def skill_entry_script(skill_dir: Path) -> Path:
    scripts = skill_dir / "scripts"
    py_files = sorted(path for path in scripts.glob("*.py") if path.is_file())
    if not py_files:
        raise FileNotFoundError(f"no scripts/*.py in {skill_dir.name}")
    if len(py_files) > 1:
        names = ", ".join(path.name for path in py_files)
        raise ValueError(f"{skill_dir.name} has multiple entry scripts: {names}")
    return py_files[0]


def iter_pack_files(skill_dir: Path) -> list[str]:
    """Relative POSIX paths to include in the upload zip."""
    skip_dirs = {"tests", "tmp", "__pycache__"}
    skip_names = {"build_skill_zip.py", "secrets.local.env"}
    entries: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise FileNotFoundError(skill_md)
    entries.append("SKILL.md")
    for folder in ("agents", "scripts", "references", "assets"):
        base = skill_dir / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(skill_dir)
            parts = set(rel.parts)
            if parts & skip_dirs or path.name in skip_names:
                continue
            if path.suffix in {".pyc", ".pyo"}:
                continue
            entries.append(rel.as_posix())
    return entries
