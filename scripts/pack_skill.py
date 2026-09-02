#!/usr/bin/env python3
"""Pack one skill into dist/<name>-v<version>.zip for SkillHub / Codex upload."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

from skillmeta import (
    FORBIDDEN,
    iter_pack_files,
    list_skill_dirs,
    load_skill,
    repo_root,
    skill_version,
)


def pack(name: str) -> Path:
    root = repo_root()
    skill_dir = root / "skills" / name
    if not skill_dir.is_dir():
        known = ", ".join(path.name for path in list_skill_dirs(root)) or "(none)"
        raise SystemExit(f"unknown skill {name!r}. have: {known}")

    meta = load_skill(skill_dir)
    version = skill_version(meta)
    entries = iter_pack_files(skill_dir)
    license_src = root / "LICENSE"
    if license_src.is_file() and "LICENSE" not in entries:
        entries.append("LICENSE")

    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    output = dist / f"{name}-v{version}.zip"
    if output.exists():
        output.unlink()

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel in entries:
            if rel == "LICENSE" and not (skill_dir / "LICENSE").is_file():
                data = license_src.read_bytes()
            else:
                data = (skill_dir / rel).read_bytes()
            lowered = data.lower()
            if any(marker.lower() in lowered for marker in FORBIDDEN):
                raise RuntimeError(f"forbidden marker in {rel}")
            archive.writestr(rel, data)

    written = zipfile.ZipFile(output).namelist()
    if written[0] != "SKILL.md":
        raise RuntimeError("zip must start with SKILL.md at the archive root")
    print(f"created: {output} ({output.stat().st_size} bytes)")
    print(f"verified: skill={name} version={version}")
    print("manifest:")
    for rel in written:
        print(f"  {rel}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="skill directory name under skills/")
    args = parser.parse_args()
    pack(args.name)


if __name__ == "__main__":
    main()
