#!/usr/bin/env python3
"""L1 gate for tong-humanize. Scan a draft; do not rewrite.

Usage:
  python3 scan.py PATH [--lane general|wechat|brief|xhs]
  python3 scan.py --list
  python3 scan.py - --lane general   # read stdin

Two tiers:
  FAIL  hard tells. Must be fixed. Any FAIL -> exit 1.
  WARN  needs a human call (good contrast vs fake contrast, engineering
        term vs empty jargon). Does not affect exit code, but the agent
        must judge each one and say keep/change in the delivery.

Exit: 0 no FAIL, 1 FAIL present, 2 bad args.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LANES = ("general", "wechat", "brief", "xhs")

# ---- FAIL tier -------------------------------------------------------------

# "不是X。不是Y。只是Z。" is a rhetorical stall; almost never a real contrast.
NNY_RE = (r"不是[^。！？\n]{1,15}[。，,]不是[^。！？\n]{1,15}[。，,]?(?:只|而|就)是",)

CLICHES = (
    "值得注意的是",
    "需要指出的是",
    "不难发现",
    "基于以上分析",
    "综上所述",
    "总而言之",
    "总的来说",
    "从某种意义上说",
    "在当今",
    "随着技术",
    "让我们来看看",
    "接下来让我们",
    "先说答案",
    "掰开了揉碎了",
    "你品一下",
    "看明白了吗",
    "看到没有",
    "说白了",
    "意味着什么",
    "换句话说",
    "不可否认",
    "毋庸置疑",
    "众所周知",
    "赋能",
    "一站式",
    "相关研究表明",
    "大量实践证明",
    "命运的齿轮",
    "如沐春风",
    "梨花带雨",
    "某个AI工具",
    "某个模型",
    "某大学实验",
    "据某报告",
    "这叫什么？这叫",
    "说明什么？说明",
    "怎么办到的？",
)

STRUCT_RE = (
    r"让我们来看",
    r"在当今[^。\n]{0,12}的时代",
    r"随着[^\n]{0,12}的不断进步",
    r"你以为[^\n]{1,20}[，,]?(?:实际|其实)上",
    # 闭环 as business filler. Engineering 闭环 (控制/温控/反馈) is left to WARN.
    r"(?:形成|实现|完成|打通|构建|做到|跑通)[^。\n]{0,4}闭环",
    r"(?:业务|商业|增长|运营|管理|数据|价值)闭环",
)

LITERARY = (
    "眼中闪过",
    "嘴角勾起",
    "深吸一口气",
    "心中一动",
    "心头一震",
    "心下了然",
    "心中暗道",
    "心底泛起",
    "不容置疑",
    "不易察觉",
    "瞳孔微缩",
    "眉头微皱",
    "顶不住",
    "哭哭啼啼",
    "死死按在",
    "暗涌",
    "波涛汹涌",
    "翻江倒海",
    "守塔人",
    "眼眶发酸",
    "红了眼眶",
    "泪目",
)

WECHAT_LITERARY = LITERARY + ("仿佛", "犹如", "宛若")

STACK_ADV = (
    "极其",
    "极度",
    "极易",
    "极为",
    "猛地",
    "死死",
    "狠狠",
    "稳稳",
    "偏偏",
    "生生",
    "硬生生",
    "活生生",
    "瞬间",
    "下一秒",
    "紧接着",
    "骤然",
)

CTA = (
    "放话了",
    "欢迎打脸",
    "来打脸",
    "看我笑话",
    "回来谢我",
    "不信邪",
    "不服来战",
    "评论区聊聊",
    "点个在看",
    "星标",
    "关注我不迷路",
    "长按扫码",
    "转发给你",
)

PUNCT = {
    "general": {"colon": None, "dash": 2, "dquote": None},
    "wechat": {"colon": 0, "dash": 0, "dquote": 0},
    "brief": {"colon": 2, "dash": 0, "dquote": 0},
    "xhs": {"colon": None, "dash": 0, "dquote": 0},
}

# ---- WARN tier -------------------------------------------------------------

# Single "不是A，而是B": judge 假靶子 / 同义替换 / 硬凑 / 好用法 before touching.
CONTRAST_RE = (r"不是[^。！？\n]{1,25}[，,]?而是[^。！？\n]{0,25}",)

# Words that are slop in business prose but real terms in engineering.
JARGON_WARN = (
    "闭环",
    "抓手",
    "本质上",
    "这意味着",
    "不仅仅是",
    "底层逻辑",
    "颗粒度",
    "对齐",
)

WARN_HINTS = {
    "不是而是": "先判毒。假靶子/同义/硬凑改，真对比可留",
    "疑似空话": "工程术语放过，空话改具体",
    "三段式": "长文分节可留；短稿改成自然段",
}


def snippet(text: str, start: int, end: int, pad: int = 6) -> str:
    left = max(0, start - pad)
    right = min(len(text), end + pad)
    piece = text[left:right]
    cut = re.search(r"[。！？\n]", piece[end - left :])
    if cut:
        piece = piece[: end - left + cut.start()]
    return f"「{piece.replace(chr(10), ' ')}」"


def regex_hits(text: str, patterns: tuple[str, ...], show: bool = False) -> list[str]:
    out: list[str] = []
    for pat in patterns:
        matches = list(re.finditer(pat, text, flags=re.IGNORECASE))
        if not matches:
            continue
        if show:
            first = matches[0]
            out.append(f"{snippet(text, first.start(), first.end())} x{len(matches)}")
        else:
            label = matches[0].group(0).replace("\n", " ")
            out.append(f"{label} x{len(matches)}")
    return out


def phrase_hits(text: str, phrases: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for phrase in phrases:
        n = text.count(phrase)
        if n:
            out.append(f"{phrase} x{n}")
    return out


def stack_hits(text: str) -> list[str]:
    out: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        if not para.strip():
            continue
        for word in STACK_ADV:
            n = para.count(word)
            if n >= 2:
                head = para.strip().splitlines()[0][:24]
                out.append(f"{word} x{n} @ {head}")
    return out


def triad_hits(text: str) -> list[str]:
    if all(token in text for token in ("首先", "其次", "最后")):
        return ["首先/其次/最后 三件套"]
    return []


def count_colons(text: str) -> int:
    n = 0
    for match in re.finditer(r"[:：]", text):
        i = match.start()
        prev_ch = text[i - 1] if i else ""
        next_ch = text[i + 1] if i + 1 < len(text) else ""
        if prev_ch.isdigit() and next_ch.isdigit():
            continue
        window = text[max(0, i - 5) : i + 3]
        if "://" in window or window.endswith(("http:", "https:")):
            continue
        n += 1
    return n


def count_dashes(text: str) -> int:
    return len(re.findall(r"——|—(?!-)", text))


def count_dquotes(text: str) -> int:
    return len(re.findall(r"[“”\"]", text))


def punct_hits(text: str, lane: str) -> list[str]:
    rules = PUNCT[lane]
    out: list[str] = []
    n_colon = count_colons(text)
    n_dash = count_dashes(text)
    n_dq = count_dquotes(text)
    if rules["colon"] is not None and n_colon > rules["colon"]:
        out.append(f"冒号{n_colon}处(限{rules['colon']})")
    if rules["dash"] is not None and n_dash > rules["dash"]:
        out.append(f"破折号{n_dash}处(限{rules['dash']})")
    if rules["dquote"] is not None and n_dq > rules["dquote"]:
        out.append(f"双引号{n_dq}处(限{rules['dquote']})")
    return out


def load_rules(paths: list[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """House rules live outside the skill. One entry per line.

    plain text  -> literal phrase
    re:PATTERN  -> regex
    # ...       -> comment
    """
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


def jargon_hits(text: str) -> list[str]:
    """闭环 already caught by STRUCT_RE in business context is not repeated here."""
    out: list[str] = []
    business_closed = sum(
        len(re.findall(pat, text)) for pat in STRUCT_RE if "闭环" in pat
    )
    for word in JARGON_WARN:
        n = text.count(word)
        if word == "闭环":
            n -= business_closed
        if n > 0:
            out.append(f"{word} x{n}")
    return out


def scan_text(
    text: str,
    lane: str,
    rules: tuple[tuple[str, ...], tuple[str, ...]] | None = None,
) -> dict[str, dict[str, list[str]]]:
    if lane not in LANES:
        raise ValueError(f"unknown lane {lane!r}")
    literary = WECHAT_LITERARY if lane in {"wechat", "brief", "xhs"} else LITERARY
    fail = {
        "否定列举": regex_hits(text, NNY_RE, show=True),
        "套话": phrase_hits(text, CLICHES) + regex_hits(text, STRUCT_RE),
        "网文腔": phrase_hits(text, literary),
        "堆叠副词": stack_hits(text),
        "标点": punct_hits(text, lane),
        "喊话CTA": phrase_hits(text, CTA),
    }
    if rules is not None:
        phrases, patterns = rules
        fail["家规"] = phrase_hits(text, phrases) + regex_hits(text, patterns, show=True)
    warn = {
        "不是而是": regex_hits(text, CONTRAST_RE, show=True),
        "疑似空话": jargon_hits(text),
        "三段式": triad_hits(text),
    }
    return {"fail": fail, "warn": warn}


def failed_count(result: dict[str, dict[str, list[str]]]) -> int:
    return sum(1 for items in result["fail"].values() if items)


def warn_count(result: dict[str, dict[str, list[str]]]) -> int:
    return sum(1 for items in result["warn"].values() if items)


def format_report(source: str, lane: str, result: dict[str, dict[str, list[str]]]) -> str:
    lines = [f"== tong-humanize {source} [lane:{lane}] =="]
    for name, items in result["fail"].items():
        mark = "PASS" if not items else "FAIL"
        detail = ", ".join(items) if items else "0"
        lines.append(f"{mark}  {name}: {detail}")
    for name, items in result["warn"].items():
        if not items:
            continue
        hint = WARN_HINTS.get(name, "")
        lines.append(f"WARN  {name}: {', '.join(items)}  -> {hint}")
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
    parser.add_argument("file", nargs="?", help="markdown/text file, or - for stdin")
    parser.add_argument("--lane", default="general", choices=LANES)
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
        print("FAIL: 否定列举 套话 网文腔 堆叠副词 标点 喊话CTA 家规(--rules)")
        print("WARN: 不是而是 疑似空话 三段式")
        return 0
    if not args.file:
        parser.print_usage()
        print("error: file required (or --list)", file=sys.stderr)
        return 2
    try:
        source, text = read_source(args.file)
        rules = load_rules(args.rules) if args.rules else None
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    result = scan_text(text, args.lane, rules)
    payload = {
        "file": source,
        "lane": args.lane,
        "pass": failed_count(result) == 0,
        "hits": {k: v for k, v in result["fail"].items() if v},
        "warnings": {k: v for k, v in result["warn"].items() if v},
        "checks": result,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_report(source, args.lane, result))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
