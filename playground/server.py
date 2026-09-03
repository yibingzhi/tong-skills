#!/usr/bin/env python3
"""Local skill lab. Bind 127.0.0.1 only. API keys stay in the browser request."""

from __future__ import annotations

import json
import mimetypes
import os
import shlex
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from cli_help import parse_argparse_help

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from skillmeta import (  # noqa: E402
    list_skill_dirs,
    load_catalog,
    load_skill,
    skill_entry_script,
)

STATIC = Path(__file__).resolve().parent / "static"
HOST = "127.0.0.1"
PORT = 8765
WRITE_ARGV = {"push", "commit", "publish", "add", "--apply", "--allow-full-table"}
MAX_ROUNDS = 8
MAX_ARG = 4000
MAX_ARGS = 40
PRESETS = {
    "tong-cover": [
        {"label": "--list", "argv": "--list"},
        {
            "label": "信息流封面",
            "argv": "--layout feed --ratio 2.35:1 --out tmp/tong-cover/feed.png",
        },
        {
            "label": "小红书竖封",
            "argv": '--layout briefing --ratio 3:4 --bullets "要点一;要点二;要点三" --out tmp/tong-cover/briefing.png',
        },
    ],
    "tong-chart": [{"label": "--help", "argv": "--help"}],
    "tong-git": [
        {"label": "status", "argv": "--repo . status"},
        {"label": "push dry-run", "argv": "--repo . push --dry-run"},
    ],
    "tong-mysql-ro": [{"label": "--help", "argv": "--help"}],
    "tong-mysql-write": [{"label": "--help", "argv": "--help"}],
    "tong-humanize": [
        {"label": "--list", "argv": "--list"},
        {
            "label": "扫套话样稿",
            "argv": "skills/tong-humanize/tests/fixtures/slop.md --lane general",
        },
        {
            "label": "扫干净样稿",
            "argv": "skills/tong-humanize/tests/fixtures/clean.md --lane general",
        },
        {
            "label": "好用法只报 WARN",
            "argv": "skills/tong-humanize/tests/fixtures/contrast.md --lane general",
        },
        {
            "label": "带家规文件扫",
            "argv": "skills/tong-humanize/tests/fixtures/clean.md --lane brief --rules skills/tong-humanize/tests/fixtures/house-rules.txt",
        },
    ],
    "tong-prompt": [
        {"label": "--list", "argv": "--list"},
        {
            "label": "扫塑料样稿",
            "argv": "skills/tong-prompt/tests/fixtures/slop.txt --lane image --target mj",
        },
        {
            "label": "扫整理后毕方",
            "argv": 'skills/tong-prompt/tests/fixtures/clean.txt --anchor "one-legged,burning ancient pine"',
        },
    ],
}
MAX_OUTPUT = 80_000
_CLI_CACHE: dict[str, dict] = {}


def describe_cli(skill_dir: Path) -> dict:
    cached = _CLI_CACHE.get(skill_dir.name)
    if cached is not None:
        return cached
    empty = {"usage": "", "fields": []}
    try:
        script = skill_entry_script(skill_dir)
    except (FileNotFoundError, ValueError):
        _CLI_CACHE[skill_dir.name] = empty
        return empty
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=12,
    )
    text = (result.stdout or "") + (result.stderr or "")
    usage = ""
    for line in text.splitlines():
        if line.strip():
            usage = line.strip()
            break
    payload = {"usage": usage, "fields": parse_argparse_help(text)}
    _CLI_CACHE[skill_dir.name] = payload
    return payload


def json_bytes(data: object, status: int = 200) -> tuple[int, bytes, str]:
    return status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json"


def skill_payload(skill_dir: Path) -> dict:
    meta = load_skill(skill_dir)
    entry = None
    try:
        entry = skill_entry_script(skill_dir).relative_to(skill_dir).as_posix()
    except (FileNotFoundError, ValueError):
        entry = None
    refs = []
    ref_dir = skill_dir / "references"
    if ref_dir.is_dir():
        refs = sorted(path.name for path in ref_dir.glob("*.md"))
    return {
        "name": skill_dir.name,
        "description": str(meta.get("description") or ""),
        "version": str((meta.get("metadata") or {}).get("version") or ""),
        "entry": entry,
        "references": refs,
        "skill_dir": skill_dir.as_posix(),
        "skill_md": meta["_text"],
        "presets": PRESETS.get(skill_dir.name) or (
            [{"label": "--help", "argv": "--help"}] if entry else []
        ),
        "cli": describe_cli(skill_dir),
    }


def list_skills() -> dict:
    catalog = {row["name"]: row for row in load_catalog(ROOT)["skills"]}
    rows = []
    skipped = []
    for skill_dir in list_skill_dirs(ROOT):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            skipped.append(f"{skill_dir.name}: missing SKILL.md")
            continue
        try:
            info = skill_payload(skill_dir)
        except Exception as exc:  # noqa: BLE001
            skipped.append(f"{skill_dir.name}: {exc}")
            continue
        stub = catalog.get(skill_dir.name) or {}
        info["summary"] = stub.get("summary") or info["description"][:80]
        info["status"] = stub.get("status") or "draft"
        rows.append(info)
    return {"skills": rows, "skipped": skipped}


def completions_url(base: str) -> str:
    text = base.strip().rstrip("/")
    if text.endswith("/chat/completions"):
        return text
    if text.endswith("/v1"):
        return text + "/chat/completions"
    return text + "/v1/chat/completions"


def uses_deepseek(base: str, model: str) -> bool:
    return "deepseek" in f"{base} {model}".lower()


def reasoning_text(message: dict) -> str:
    """DeepSeek thinking mode: CoT is reasoning_content, not content."""
    raw = message.get("reasoning_content")
    if raw is None:
        raw = message.get("reasoning")
    if isinstance(raw, dict):
        raw = raw.get("content") or raw.get("text") or ""
    return str(raw or "")


def assistant_from_api(message: dict) -> dict:
    calls = message.get("tool_calls") or []
    if not isinstance(calls, list):
        calls = []
    return {
        "role": "assistant",
        "content": str(message.get("content") or ""),
        "reasoning_content": reasoning_text(message),
        "tool_calls": calls,
    }


def assistant_for_api(item: dict, *, include_reasoning: bool) -> dict:
    """Replay an assistant turn. DeepSeek + tools requires reasoning_content."""
    out: dict = {
        "role": "assistant",
        "content": str(item.get("content") or ""),
    }
    reasoning = reasoning_text(item)
    if include_reasoning and reasoning:
        out["reasoning_content"] = reasoning
    calls = item.get("tool_calls") or []
    if calls:
        out["tool_calls"] = calls
    return out


def llm_payload(model: str, messages: list, *, tools: list | None, base: str) -> dict:
    payload: dict = {"model": model, "messages": messages}
    if tools:
        payload["tools"] = tools
    if uses_deepseek(base, model):
        # Official thinking-mode toggle. CoT returns on reasoning_content.
        # temperature/top_p have no effect in thinking mode — omit them.
        payload["thinking"] = {"type": "enabled"}
        payload["reasoning_effort"] = "high"
    else:
        payload["temperature"] = 0.2
    return payload


def openai_chat(base: str, key: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        completions_url(base),
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"LLM HTTP {exc.code}: {detail[:800]}") from exc


def tools_schema() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "run_skill_script",
                "description": (
                    "Run this skill's bundled CLI. Pass argv only "
                    "(no python, no script path). Example: [\"--list\"]"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "argv": {
                            "type": "array",
                            "items": {"type": "string"},
                        }
                    },
                    "required": ["argv"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_skill_file",
                "description": "Read SKILL.md or a file under references/ or assets/.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
    ]


def run_skill_script(skill_dir: Path, argv: list[str], allow_write: bool) -> str:
    if len(argv) > MAX_ARGS or any(len(item) > MAX_ARG for item in argv):
        return "refuse: argv too large"
    if not allow_write and any(item in WRITE_ARGV for item in argv):
        return "refuse: write command blocked (enable 允许写操作)"
    try:
        script = skill_entry_script(skill_dir)
    except (FileNotFoundError, ValueError) as exc:
        return f"no entry script: {exc}"
    cmd = [sys.executable, str(script), *argv]
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    text = (result.stdout or "") + (result.stderr or "")
    if len(text) > MAX_OUTPUT:
        text = text[:MAX_OUTPUT] + "\n...truncated..."
    return f"exit {result.returncode}\n{text}".rstrip()


def read_skill_file(skill_dir: Path, rel: str) -> str:
    rel_path = rel.replace("\\", "/").lstrip("/")
    if rel_path in {"SKILL.md", "./SKILL.md"}:
        target = skill_dir / "SKILL.md"
    else:
        first = rel_path.split("/", 1)[0]
        if first not in {"references", "assets"}:
            return "refuse: only SKILL.md, references/, assets/"
        target = (skill_dir / rel_path).resolve()
        if skill_dir.resolve() not in target.parents and target != skill_dir.resolve():
            return "refuse: path escapes skill dir"
    if not target.is_file():
        return f"missing: {rel_path}"
    text = target.read_text(encoding="utf-8")
    if len(text) > MAX_OUTPUT:
        return text[:MAX_OUTPUT] + "\n...truncated..."
    return text


def system_prompt(info: dict, include_refs: bool) -> str:
    skill_dir = Path(info["skill_dir"])
    parts = [
        f"You are testing Agent Skill `{info['name']}` in the TongSkills checkout.",
        f"skill-dir is `{skill_dir.as_posix()}`.",
        "Follow SKILL.md. Prefer the bundled script over regenerating it.",
        "If tools are available, call run_skill_script with argv only.",
        "User-visible content is only the reply to the human: the question, "
        "the paste-ready prompt, or the result. Do not narrate SKILL.md, do not "
        "explain the workflow, do not preface tool calls in content.",
        "Do not print API keys. Do not invent git remotes.",
        "",
        info["skill_md"],
    ]
    if include_refs:
        for name in info["references"]:
            path = skill_dir / "references" / name
            parts.append(f"\n\n# {name}\n{path.read_text(encoding='utf-8')}")
    return "\n".join(parts)


def chat_loop(body: dict) -> dict:
    name = str(body.get("skill") or "")
    skill_dir = ROOT / "skills" / name
    if not skill_dir.is_dir():
        raise ValueError(f"unknown skill {name}")
    key = str(body.get("api_key") or "").strip()
    base = str(body.get("base_url") or "").strip()
    model = str(body.get("model") or "").strip()
    if not key or not base or not model:
        raise ValueError("api_key, base_url, and model are required")
    info = skill_payload(skill_dir)
    include_refs = bool(body.get("include_refs"))
    use_tools = bool(body.get("tools"))
    allow_write = bool(body.get("allow_write"))
    history = body.get("messages") or []
    if not isinstance(history, list):
        raise ValueError("messages must be a list")
    messages: list[dict] = [
        {"role": "system", "content": system_prompt(info, include_refs)}
    ]
    for item in history:
        role = item.get("role")
        if role == "user":
            messages.append({"role": "user", "content": str(item.get("content") or "")})
        elif role == "assistant":
            messages.append(assistant_for_api(item, include_reasoning=use_tools and uses_deepseek(base, model)))
    trace: list[dict] = []
    for _ in range(MAX_ROUNDS):
        payload = llm_payload(
            model,
            messages,
            tools=tools_schema() if use_tools else None,
            base=base,
        )
        data = openai_chat(base, key, payload)
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        packed = assistant_from_api(message)
        trace.append(packed)
        if not packed["tool_calls"]:
            return {"trace": trace}
        replay = assistant_for_api(packed, include_reasoning=uses_deepseek(base, model))
        messages.append(replay)
        for call in packed["tool_calls"]:
            fn = (call.get("function") or {})
            fn_name = fn.get("name") or ""
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            if fn_name == "run_skill_script":
                argv = args.get("argv") or []
                if not isinstance(argv, list):
                    argv = []
                result = run_skill_script(
                    skill_dir, [str(item) for item in argv], allow_write
                )
            elif fn_name == "read_skill_file":
                result = read_skill_file(skill_dir, str(args.get("path") or ""))
            else:
                result = f"unknown tool {fn_name}"
            trace.append({"role": "tool", "name": fn_name, "content": result})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id") or "",
                    "content": result,
                }
            )
    return {"trace": trace, "note": "stopped after max tool rounds"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, status: int, payload: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON object required")
        return data

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/skills":
            try:
                status, payload, ctype = json_bytes(list_skills())
            except Exception as exc:  # noqa: BLE001
                status, payload, ctype = json_bytes({"error": str(exc)}, 500)
            self._send(status, payload, ctype)
            return
        if path.startswith("/api/skills/"):
            name = path.rsplit("/", 1)[-1]
            skill_dir = ROOT / "skills" / name
            if not skill_dir.is_dir():
                status, payload, ctype = json_bytes({"error": "not found"}, 404)
                self._send(status, payload, ctype)
                return
            status, payload, ctype = json_bytes(skill_payload(skill_dir))
            self._send(status, payload, ctype)
            return
        rel = "index.html" if path in {"/", "/index.html"} else path.lstrip("/")
        target = (STATIC / rel).resolve()
        if STATIC.resolve() not in target.parents and target != STATIC.resolve():
            self._send(403, b"forbidden", "text/plain")
            return
        if not target.is_file():
            self._send(404, b"not found", "text/plain")
            return
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self._send(200, target.read_bytes(), ctype)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/run":
            try:
                body = self._read_json()
                name = str(body.get("skill") or "")
                skill_dir = ROOT / "skills" / name
                if not skill_dir.is_dir():
                    raise ValueError(f"unknown skill {name}")
                raw = body.get("argv")
                if isinstance(raw, list):
                    argv = [str(item) for item in raw]
                else:
                    argv = shlex.split(str(raw or "").strip(), posix=True)
                output = run_skill_script(
                    skill_dir, argv, bool(body.get("allow_write"))
                )
                status, payload, ctype = json_bytes(
                    {"argv": argv, "output": output}
                )
            except Exception as exc:  # noqa: BLE001
                status, payload, ctype = json_bytes({"error": str(exc)}, 400)
            self._send(status, payload, ctype)
            return
        if path != "/api/chat":
            self._send(404, b"not found", "text/plain")
            return
        try:
            body = self._read_json()
            result = chat_loop(body)
            status, payload, ctype = json_bytes(result)
        except Exception as exc:  # noqa: BLE001
            status, payload, ctype = json_bytes({"error": str(exc)}, 400)
        self._send(status, payload, ctype)


def main() -> None:
    if not STATIC.is_dir():
        raise SystemExit(f"missing {STATIC}")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"Tong lab: {url}", flush=True)
    print("API keys are not written to disk. Ctrl+C to stop.", flush=True)
    if os.environ.get("TONG_LAB_NO_BROWSER") != "1":
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
        server.server_close()


if __name__ == "__main__":
    main()
