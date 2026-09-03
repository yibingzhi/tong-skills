"""Parse argparse --help into form fields for the local lab."""

from __future__ import annotations

import re

SKIP_IDS = {"h", "help"}
ITEM_RE = re.compile(r"^  (?! )\S")
CONT_RE = re.compile(r"^ {10,}\S")


def _split_left_help(rest: str) -> tuple[str, str]:
    if "  " in rest:
        left, help_text = rest.split("  ", 1)
        return left.strip(), help_text.strip()
    return rest.strip(), ""


def _choices(meta: str) -> list[str]:
    if meta.startswith("{") and meta.endswith("}"):
        return [part.strip() for part in meta[1:-1].split(",") if part.strip()]
    return []


def _parse_optional(line: str) -> list[dict]:
    left, help_text = _split_left_help(line[2:])
    if "|" in left and not left.startswith("{"):
        out: list[dict] = []
        for chunk in left.split("|"):
            out.extend(_parse_optional("  " + chunk.strip() + "  " + help_text))
        return out
    tokens = left.split()
    flags: list[str] = []
    meta_parts: list[str] = []
    for tok in tokens:
        cleaned = tok.rstrip(",")
        if cleaned.startswith("-"):
            flags.append(cleaned)
        else:
            meta_parts.append(tok)
    meta = " ".join(meta_parts)
    long = next((flag for flag in flags if flag.startswith("--")), flags[0] if flags else "")
    fid = long.lstrip("-")
    if not fid or fid in SKIP_IDS:
        return []
    choices = _choices(meta)
    if choices:
        kind = "choice"
    elif meta:
        kind = "text"
    else:
        kind = "flag"
    return [
        {
            "id": fid,
            "flags": flags or ["--" + fid],
            "positional": False,
            "kind": kind,
            "choices": choices,
            "metavar": "" if choices else meta,
            "help": help_text,
        }
    ]


def _parse_positional(line: str) -> dict | None:
    left, help_text = _split_left_help(line[2:])
    name = left.split()[0] if left else ""
    if not name:
        return None
    choices = _choices(name)
    if choices:
        return {
            "id": "command",
            "flags": [],
            "positional": True,
            "kind": "choice",
            "choices": choices,
            "metavar": "",
            "help": help_text or "subcommand",
        }
    return {
        "id": name,
        "flags": [],
        "positional": True,
        "kind": "text",
        "choices": [],
        "metavar": name,
        "help": help_text,
    }


def parse_argparse_help(text: str) -> list[dict]:
    fields: list[dict] = []
    section = None
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if current and current.get("id") not in SKIP_IDS:
            fields.append(current)
        current = None

    for raw in text.splitlines():
        line = raw.rstrip()
        heading = line.strip().rstrip(":").lower()
        if heading in {"positional arguments", "options", "optional arguments"}:
            flush()
            section = "pos" if heading.startswith("positional") else "opt"
            continue
        if section is None:
            continue
        if ITEM_RE.match(line):
            flush()
            parsed = _parse_optional(line) if section == "opt" else [_parse_positional(line)]
            parsed = [item for item in parsed if item]
            if not parsed:
                continue
            current = parsed[0]
            for extra in parsed[1:]:
                fields.append(extra)
            continue
        if current and CONT_RE.match(line):
            extra = line.strip()
            if extra:
                prev = current.get("help") or ""
                current["help"] = f"{prev} {extra}".strip()
    flush()
    seen: set[str] = set()
    unique: list[dict] = []
    for item in fields:
        fid = item["id"]
        if fid in seen:
            continue
        seen.add(fid)
        unique.append(item)
    return unique
