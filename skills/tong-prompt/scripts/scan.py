#!/usr/bin/env python3
"""L1 gate for tong-prompt. Scan a prompt file; do not rewrite.

Usage:
  python3 scan.py PATH [--lane image|video] [--target generic|mj|jimeng|kling]
  python3 scan.py PATH --look gongbi --anchor "one leg,burning pine"
  python3 scan.py --list
  python3 scan.py - --lane image   # read stdin

Two tiers:
  FAIL  hard tells. Must be fixed. Any FAIL -> exit 1.
  WARN  needs a human call. Does not affect exit code; the agent must
        judge each one and say keep/change in the delivery.

Exit: 0 no FAIL, 1 FAIL present, 2 bad args.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LANES = ("image", "video")
TARGETS = ("generic", "mj", "jimeng", "kling")
LOOKS = ("auto", "gongbi", "oil", "cine", "info")

HEADER_RE = re.compile(r"^(lane|target|look|anchor)\s*:\s*(.*)$", re.I)
SECTION_RE = re.compile(r"^(prompt|negative|neg|params|no)\s*:\s*$", re.I)
MJ_PARAM_RE = re.compile(
    r"--(?:stylize|sref|oref|iw|cw|v|q|s)(?:\s+\S+)?", re.I
)
MJ_NO_RE = re.compile(r"--no\b[^\n]*", re.I)
OTHER_FLAG_RE = re.compile(r"--(?:ar|aspect|niji)\s+\S+", re.I)

SCHOOLS: dict[str, tuple[str, ...]] = {
    "gongbi": ("gongbi", "工笔", "bird-and-flower", "工笔花鸟"),
    "oil": ("oil painting", "thick oil", "impasto", "油画", "厚涂"),
    "hyperreal": (
        "hyper-real",
        "hyperreal",
        "hyper-realism",
        "photoreal",
        "超写实",
        "photographic",
    ),
    "cgi3d": (
        "3d render",
        "octane render",
        "unreal engine",
        "blender cycles",
    ),
    "watercolor": ("watercolor", "水彩"),
    "ink": ("水墨", "sumi-e", "ink wash"),
    "anime": ("anime style", "二次元", "disney style", "pixar", "cute chibi"),
}

LIGHTING_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("volumetric", ("volumetric",)),
    ("tyndall", ("tyndall", "丁达尔")),
    ("sss", ("subsurface", "sss")),
    ("godrays", ("god rays", "god-rays")),
    ("cine-light", ("cinematic lighting",)),
    ("8k", ("8k resolution", "8k,", " 8k", "8k ")),
    ("masterpiece", ("masterpiece",)),
    ("best-quality", ("best quality", "ultra detailed", "ultra-detailed")),
    ("octane", ("octane render",)),
    ("raytrace", ("ray tracing", "ray-tracing")),
)

ALWAYS_FAIL = (
    "trending on artstation",
    "stunning artwork",
    "breathtaking",
    "精美高级",
    "氛围感拉满",
    "咨询一页纸",
    "咨询公司一页纸",
)

FANTASY_EXTRA = (
    "floating rune",
    "rune stone",
    "rune stones",
    "magic circle",
    "符石",
    "法阵",
    "仙侠",
)

VIDEO_IN_IMAGE = (
    r"first frame",
    r"last frame",
    r"camera (?:slowly|pans|dollies|zooms)",
    r"dolly zoom",
    r"缓缓推进",
    r"缓缓拉远",
    r"前\d+秒",
    r"时长\s*\d+",
)

DURATION_RE = (
    r"\b\d+\s*(?:s|sec|secs|second|seconds)\b",
    r"\d+\s*秒",
    r"时长",
    r"duration",
)

LOOK_CLASH = {
    "gongbi": {"oil", "hyperreal", "cgi3d", "anime"},
    "oil": {"gongbi", "cgi3d", "anime"},
    "cine": {"gongbi", "anime", "watercolor"},
    "info": {"oil", "cine", "anime", "hyperreal", "gongbi"},
}

WARN_HINTS = {
    "渲染器口癖": "单个可留；两个以上优先改成一道具体的光",
    "出处外配件": "山海经/作者没给的符石仙侠删；锚点里有的可留",
    "未声明锚点": "交稿必须带 --anchor 或文件头 anchor:",
    "缺时长": "视频写几秒；没有就问一句",
    "缺画幅": "MJ 补 --ar；其它 target 在 prompt 里写比例",
    "画派打架": "look 与正文画法不一致时，听作者的 look",
}


def snippet(text: str, start: int, end: int, pad: int = 6) -> str:
    left = max(0, start - pad)
    right = min(len(text), end + pad)
    piece = text[left:right].replace("\n", " ")
    return f"「{piece}」"


def split_csv(raw: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,，;；]", raw) if part.strip()]


def parse_prompt_file(text: str) -> dict[str, object]:
    meta: dict[str, object] = {
        "lane": None,
        "target": None,
        "look": None,
        "anchor": [],
    }
    lines = text.splitlines()
    consumed = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            if consumed == i:
                consumed = i + 1
            continue
        match = HEADER_RE.match(stripped)
        if not match:
            break
        key = match.group(1).lower()
        val = match.group(2).strip()
        if key == "anchor":
            meta["anchor"] = split_csv(val)
        else:
            meta[key] = val.lower()
        consumed = i + 1
    rest = "\n".join(lines[consumed:])
    sections = {"prompt": "", "negative": "", "params": ""}
    current = "prompt"
    buckets = {"prompt": [], "negative": [], "params": []}
    labeled = False
    for line in rest.splitlines():
        head = SECTION_RE.match(line.strip())
        if head:
            labeled = True
            name = head.group(1).lower()
            current = {
                "prompt": "prompt",
                "negative": "negative",
                "neg": "negative",
                "no": "negative",
                "params": "params",
            }[name]
            continue
        buckets[current].append(line)
    if labeled:
        sections["prompt"] = "\n".join(buckets["prompt"]).strip()
        sections["negative"] = "\n".join(buckets["negative"]).strip()
        sections["params"] = "\n".join(buckets["params"]).strip()
    else:
        nos = MJ_NO_RE.findall(rest)
        params = MJ_PARAM_RE.findall(rest) + OTHER_FLAG_RE.findall(rest)
        body = MJ_NO_RE.sub(" ", rest)
        body = MJ_PARAM_RE.sub(" ", body)
        body = OTHER_FLAG_RE.sub(" ", body)
        sections["prompt"] = body.strip()
        if nos:
            cleaned = [re.sub(r"^--no\s*", "", item, flags=re.I).strip(" :") for item in nos]
            sections["negative"] = "; ".join(cleaned)
        sections["params"] = " ".join(params).strip()
    return {"meta": meta, "sections": sections, "raw": text}


def prompt_body(parsed: dict[str, object]) -> str:
    sections = parsed["sections"]  # type: ignore[assignment]
    return str(sections["prompt"])  # type: ignore[index]


def lower_has(text: str, needle: str) -> bool:
    return needle.casefold() in text.casefold()


def is_negated_at(folded: str, index: int) -> bool:
    window = folded[max(0, index - 16) : index]
    return bool(
        re.search(r"\b(?:not|no)\s+$", window)
        or re.search(r"(?:不要|不是|别|禁止|而非)\s*$", window)
    )


def contains_positive(text: str, needle: str) -> bool:
    folded = text.casefold()
    n = needle.casefold()
    start = 0
    while True:
        index = folded.find(n, start)
        if index < 0:
            return False
        if not is_negated_at(folded, index):
            return True
        start = index + 1


def school_hits(body: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for name, needles in SCHOOLS.items():
        for needle in needles:
            if contains_positive(body, needle):
                found[name] = needle
                break
    return found


def lighting_hits(body: str) -> list[str]:
    found: list[str] = []
    padded = f" {body} "
    for family, needles in LIGHTING_FAMILIES:
        for needle in needles:
            if contains_positive(padded, needle):
                found.append(family)
                break
    return found


def phrase_hits(text: str, phrases: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for phrase in phrases:
        if contains_positive(text, phrase):
            out.append(phrase)
    return out


def regex_hits(text: str, patterns: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for pat in patterns:
        matches = list(re.finditer(pat, text, flags=re.IGNORECASE))
        if matches:
            first = matches[0]
            out.append(f"{snippet(text, first.start(), first.end())} x{len(matches)}")
    return out


def missing_anchors(body: str, anchors: list[str]) -> list[str]:
    missing: list[str] = []
    for item in anchors:
        if not lower_has(body, item):
            missing.append(item)
    return missing


def load_rules(paths: list[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    phrases: list[str] = []
    patterns: list[str] = []
    for raw in paths:
        path = Path(raw)
        if not path.is_file():
            raise FileNotFoundError(f"rules file not found: {path}")
        for line in path.read_text(encoding="utf-8").splitlines():
            entry = line.strip()
            if not entry or entry.startswith("#"):
                continue
            if entry.startswith("re:"):
                pat = entry[3:].strip()
                try:
                    re.compile(pat)
                except re.error as exc:
                    raise ValueError(f"{path}: bad regex {pat!r}: {exc}") from exc
                patterns.append(pat)
            else:
                phrases.append(entry)
    return tuple(phrases), tuple(patterns)


def scan_text(
    text: str,
    lane: str,
    target: str,
    look: str,
    extra_anchors: list[str] | None = None,
    rules: tuple[tuple[str, ...], tuple[str, ...]] | None = None,
) -> dict[str, dict[str, list[str]]]:
    if lane not in LANES:
        raise ValueError(f"unknown lane {lane!r}")
    if target not in TARGETS:
        raise ValueError(f"unknown target {target!r}")
    if look not in LOOKS:
        raise ValueError(f"unknown look {look!r}")

    parsed = parse_prompt_file(text)
    meta = parsed["meta"]  # type: ignore[assignment]
    body = prompt_body(parsed)
    sections = parsed["sections"]  # type: ignore[assignment]
    params = str(sections["params"])  # type: ignore[index]
    whole_flags = params + "\n" + str(parsed["raw"])

    file_lane = meta.get("lane") or lane  # type: ignore[union-attr]
    file_target = meta.get("target") or target  # type: ignore[union-attr]
    file_look = meta.get("look") or look  # type: ignore[union-attr]
    if file_lane in LANES:
        lane = str(file_lane)
    if file_target in TARGETS:
        target = str(file_target)
    if file_look in LOOKS:
        look = str(file_look)

    anchors = list(meta.get("anchor") or [])  # type: ignore[arg-type]
    if extra_anchors:
        anchors.extend(extra_anchors)
    # de-dupe preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for item in anchors:
        key = item.casefold()
        if key not in seen:
            seen.add(key)
            uniq.append(item)
    anchors = uniq

    schools = school_hits(body)
    lighting = lighting_hits(body)
    lost = missing_anchors(body, anchors)

    fail: dict[str, list[str]] = {
        "塑料套话": phrase_hits(body, ALWAYS_FAIL),
        "画法堆叠": [],
        "塑料堆叠": [],
        "锚点缺失": [f"{item} 未出现在 prompt" for item in lost],
        "动静混写": [],
        "工具尾缀": [],
        "画派打架": [],
    }
    if len(schools) >= 3:
        labels = ", ".join(f"{name}({hit})" for name, hit in schools.items())
        fail["画法堆叠"] = [f"{len(schools)}种: {labels}"]
    if len(lighting) >= 3:
        fail["塑料堆叠"] = [", ".join(lighting)]
    if lane == "image":
        fail["动静混写"] = regex_hits(body, VIDEO_IN_IMAGE)
    clash = LOOK_CLASH.get(look, set()) & set(schools)
    if look != "auto" and clash:
        fail["画派打架"] = [f"look={look} vs {', '.join(sorted(clash))}"]

    mj_hits = MJ_PARAM_RE.findall(whole_flags) + MJ_NO_RE.findall(whole_flags)
    if target != "mj" and mj_hits:
        fail["工具尾缀"] = [item.strip() for item in mj_hits[:6]]

    if rules is not None:
        phrases, patterns = rules
        fail["家规"] = phrase_hits(body, phrases) + regex_hits(body, patterns)

    warn: dict[str, list[str]] = {
        "渲染器口癖": [],
        "出处外配件": phrase_hits(body, FANTASY_EXTRA),
        "未声明锚点": [],
        "缺时长": [],
        "缺画幅": [],
    }
    if 0 < len(lighting) < 3:
        warn["渲染器口癖"] = lighting
    if not anchors:
        warn["未声明锚点"] = ["没有 anchor: / --anchor"]
    if lane == "video" and not regex_hits(body, DURATION_RE):
        warn["缺时长"] = ["正文里没有秒数或 duration"]
    if target == "mj" and not re.search(r"--ar\b", whole_flags, re.I):
        if not re.search(r"\b\d+:\d+\b", body):
            warn["缺画幅"] = ["MJ 缺少 --ar"]

    return {"fail": fail, "warn": warn, "_meta": {"lane": lane, "target": target, "look": look}}


def failed_count(result: dict[str, dict[str, list[str]]]) -> int:
    return sum(1 for key, items in result["fail"].items() if key != "_meta" and items)


def warn_count(result: dict[str, dict[str, list[str]]]) -> int:
    return sum(1 for items in result["warn"].values() if items)


def format_report(
    source: str,
    lane: str,
    target: str,
    look: str,
    result: dict[str, dict[str, list[str]]],
) -> str:
    meta = result.get("_meta") or {}
    lane = str(meta.get("lane") or lane)
    target = str(meta.get("target") or target)
    look = str(meta.get("look") or look)
    lines = [f"== tong-prompt {source} [lane:{lane} target:{target} look:{look}] =="]
    for name, items in result["fail"].items():
        if name.startswith("_"):
            continue
        mark = "PASS" if not items else "FAIL"
        detail = ", ".join(items) if items else "0"
        lines.append(f"{mark}  {name}: {detail}")
    for name, items in result["warn"].items():
        if not items:
            continue
        hint = WARN_HINTS.get(name, "")
        suffix = f"  -> {hint}" if hint else ""
        lines.append(f"WARN  {name}: {', '.join(items)}{suffix}")
    bad = failed_count(result)
    pending = warn_count(result)
    if bad:
        lines.append(f"结论: {bad} 项未过，先修再交")
    elif pending:
        lines.append(f"结论: 通过，{pending} 项待判（交稿时逐条说明留还是改）")
    else:
        lines.append("结论: 通过")
    return "\n".join(lines)


def read_source(path_arg: str) -> tuple[str, str]:
    if path_arg == "-":
        return "-", sys.stdin.read()
    path = Path(path_arg)
    if not path.is_file():
        raise FileNotFoundError(f"not a file: {path}")
    return str(path), path.read_text(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", help="prompt file, or - for stdin")
    parser.add_argument("--lane", default="image", choices=LANES)
    parser.add_argument("--target", default="generic", choices=TARGETS)
    parser.add_argument("--look", default="auto", choices=LOOKS)
    parser.add_argument(
        "--anchor",
        action="append",
        default=[],
        metavar="TEXT",
        help="comma-separated must-have phrases in the prompt body. Repeatable.",
    )
    parser.add_argument(
        "--rules",
        action="append",
        default=[],
        metavar="FILE",
        help="house-rules file kept outside the skill; one phrase per line, "
        "re:PATTERN for regex, # comments. Repeatable. Hits are FAIL.",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    parser.add_argument("--list", action="store_true", help="print lanes and checks")
    return parser


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list:
        print("lanes:", " ".join(LANES))
        print("targets:", " ".join(TARGETS))
        print("looks:", " ".join(LOOKS))
        print("FAIL: 塑料套话 画法堆叠 塑料堆叠 锚点缺失 动静混写 工具尾缀 画派打架 家规(--rules)")
        print("WARN: 渲染器口癖 出处外配件 未声明锚点 缺时长 缺画幅")
        return 0
    if not args.file:
        parser.print_usage()
        print("error: file required (or --list)", file=sys.stderr)
        return 2
    extra: list[str] = []
    for item in args.anchor:
        extra.extend(split_csv(item))
    try:
        source, text = read_source(args.file)
        rules = load_rules(args.rules) if args.rules else None
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    result = scan_text(text, args.lane, args.target, args.look, extra, rules)
    meta = result.get("_meta") or {}
    payload = {
        "file": source,
        "lane": meta.get("lane", args.lane),
        "target": meta.get("target", args.target),
        "look": meta.get("look", args.look),
        "pass": failed_count(result) == 0,
        "hits": {k: v for k, v in result["fail"].items() if v},
        "warnings": {k: v for k, v in result["warn"].items() if v},
        "checks": {k: v for k, v in result.items() if k != "_meta"},
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            format_report(
                source,
                str(payload["lane"]),
                str(payload["target"]),
                str(payload["look"]),
                result,
            )
        )
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
