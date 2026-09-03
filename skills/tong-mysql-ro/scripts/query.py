#!/usr/bin/env python3
"""Read-only MySQL CLI. SELECT/SHOW/DESCRIBE/EXPLAIN/WITH only."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SECRETS = SKILL_DIR / "secrets.local.env"
DEFAULT_MAX_ROWS = 200

CORE_KEYS = (
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASS",
    "MYSQL_DATABASE",
)
READ_PREFIXES = ("select", "show", "describe", "desc", "explain", "with")
# Scanned on masked SQL (string/identifier contents blanked), so data values never trigger it.
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|replace|alter|drop|create|truncate|rename|"
    r"grant|revoke|call|do|lock|unlock|load|load_file|handler|set\s+global|"
    r"set\s+@@|into\s+outfile|into\s+dumpfile)\b",
    re.I,
)
COMMENT_START = re.compile(r"--(?=\s|$)|#|/\*")
SAFE_IDENT = re.compile(r"^[A-Za-z0-9_]+$")
SAFE_ENV = re.compile(r"^[A-Za-z0-9_]+$")
LIMIT_OFFSET_COMMA = re.compile(r"\blimit\s+(\d+)\s*,\s*(\d+)\s*$", re.I)
LIMIT_OFFSET_KEYWORD = re.compile(r"\blimit\s+(\d+)\s+offset\s+(\d+)\s*$", re.I)
LIMIT_COUNT = re.compile(r"\blimit\s+(\d+)\s*$", re.I)
SCALAR_AGG = re.compile(
    r"^\s*select\s+(distinct\s+)?"
    r"(count|sum|avg|min|max|bit_and|bit_or|bit_xor)\s*\(",
    re.I,
)


def load_dotenv(path: Path) -> dict[str, str]:
    raw: dict[str, str] = {}
    if not path.is_file():
        return raw
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        raw[key.strip()] = val.strip().strip('"').strip("'")
    return raw


def load_secrets(path: Path | None = None) -> dict[str, str]:
    secrets_path = path or DEFAULT_SECRETS
    raw = load_dotenv(secrets_path)
    for key, val in os.environ.items():
        if key.startswith("MYSQL_"):
            raw[key] = val
    return raw


def missing_core(secrets: dict[str, str]) -> list[str]:
    missing = []
    for key in CORE_KEYS:
        if key == "MYSQL_PORT":
            continue
        if not secrets.get(key):
            missing.append(key)
    return missing


def resolve_database(secrets: dict[str, str], env_name: str | None, database: str | None) -> str:
    if database:
        return database
    if env_name:
        if not SAFE_ENV.match(env_name):
            raise ValueError("Invalid --env (use A-Za-z0-9_)")
        key = "MYSQL_ENV_" + env_name.upper()
        value = secrets.get(key)
        if not value:
            raise ValueError("Missing {} in secrets.local.env or environment".format(key))
        return value
    value = secrets.get("MYSQL_DATABASE")
    if not value:
        raise ValueError("Missing MYSQL_DATABASE (or pass --database / --env)")
    return value


def mask_literals(sql: str) -> str:
    """Same-length copy with '...' / "..." / `...` contents blanked. Quotes stay.

    Handles backslash escapes and doubled quotes so structure scans (keywords,
    LIMIT, semicolons, comments) never see user data.
    """
    out = list(sql)
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        if ch in ("'", '"', "`"):
            quote = ch
            i += 1
            while i < n:
                c = sql[i]
                if c == "\\" and quote != "`" and i + 1 < n:
                    out[i] = out[i + 1] = " "
                    i += 2
                    continue
                if c == quote:
                    if i + 1 < n and sql[i + 1] == quote:
                        out[i] = out[i + 1] = " "
                        i += 2
                        continue
                    break
                out[i] = " "
                i += 1
            if i >= n:
                raise ValueError("Unclosed quote")
        i += 1
    return "".join(out)


def assert_readonly(sql: str) -> str:
    text = sql.strip().rstrip(";").strip()
    if not text:
        raise ValueError("Empty SQL")
    masked = mask_literals(text)
    cm = COMMENT_START.search(masked)
    if cm:
        raise ValueError(
            "Comments are not allowed (found {!r}); a trailing comment would swallow the LIMIT".format(
                masked[cm.start() : cm.start() + 2]
            )
        )
    lower = masked.lower()
    if not lower.startswith(READ_PREFIXES):
        raise ValueError("Only SELECT/SHOW/DESCRIBE/EXPLAIN/WITH are allowed")
    if FORBIDDEN.search(masked):
        raise ValueError("Write/DDL keywords are forbidden in read-only mode")
    if lower.startswith("with") and not _has_depth0_select(lower):
        raise ValueError("WITH must end in a top-level SELECT")
    return text


def _has_depth0_select(lower_masked: str) -> bool:
    depth = 0
    for m in re.finditer(r"[()]|\bselect\b", lower_masked):
        tok = m.group(0)
        if tok == "(":
            depth += 1
        elif tok == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            return True
    return False


def split_statements(sql: str) -> list[str]:
    masked = mask_literals(sql)
    parts: list[str] = []
    start = 0
    for i, ch in enumerate(masked):
        if ch == ";":
            stmt = sql[start:i].strip()
            if stmt:
                parts.append(stmt)
            start = i + 1
    tail = sql[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def apply_row_guard(sql: str, max_rows: int | None) -> tuple[str, str | None]:
    """Add/cap LIMIT on row-returning SELECT/WITH. Regexes run on masked SQL."""
    masked = mask_literals(sql)
    lower = masked.lower().strip()
    if lower.startswith(("show", "describe", "desc", "explain")):
        return sql, None
    if not (lower.startswith("select") or lower.startswith("with")):
        return sql, None
    if lower.startswith("select") and not re.search(r"\bfrom\b", lower):
        return sql, None
    if SCALAR_AGG.match(masked) and not re.search(r"\bgroup\s+by\b", lower):
        return sql, None

    has_limit = bool(
        LIMIT_OFFSET_COMMA.search(masked)
        or LIMIT_OFFSET_KEYWORD.search(masked)
        or LIMIT_COUNT.search(masked)
    )
    if not max_rows:
        if not has_limit:
            raise ValueError(
                "SELECT...FROM without LIMIT rejected (--max-rows 0). "
                "Add an explicit LIMIT, or use --max-rows N (default 200)."
            )
        return sql, None

    match = LIMIT_OFFSET_COMMA.search(masked)
    if match:
        offset, count = int(match.group(1)), int(match.group(2))
        if count > max_rows:
            new_sql = sql[: match.start()] + "LIMIT {}, {}".format(offset, max_rows)
            return new_sql, "capped LIMIT count {} -> {}".format(count, max_rows)
        return sql, None

    match = LIMIT_OFFSET_KEYWORD.search(masked)
    if match:
        count, offset = int(match.group(1)), int(match.group(2))
        if count > max_rows:
            new_sql = sql[: match.start()] + "LIMIT {} OFFSET {}".format(max_rows, offset)
            return new_sql, "capped LIMIT {} -> {}".format(count, max_rows)
        return sql, None

    match = LIMIT_COUNT.search(masked)
    if match:
        count = int(match.group(1))
        if count > max_rows:
            new_sql = sql[: match.start()] + "LIMIT {}".format(max_rows)
            return new_sql, "capped LIMIT {} -> {}".format(count, max_rows)
        return sql, None

    return sql.rstrip() + " LIMIT {}".format(max_rows), "auto LIMIT {}".format(max_rows)


def validate_ident(name: str, what: str = "name") -> str:
    if not name or not SAFE_IDENT.match(name):
        raise ValueError("Invalid {}: {!r} (only A-Za-z0-9_)".format(what, name))
    return name


def describe_sql(table: str) -> str:
    return "DESCRIBE `{}`".format(validate_ident(table, "table"))


def print_tsv(rows: list[dict]) -> None:
    if not rows:
        print("(0 rows)")
        return
    cols = list(rows[0].keys())
    print("\t".join(cols))
    for row in rows:
        print("\t".join("" if row[c] is None else str(row[c]) for c in cols))
    print("({} rows)".format(len(rows)))


def fetch_schema_like(cur, pattern: str) -> list[dict]:
    if not pattern or not re.match(r"^[A-Za-z0-9_%]+$", pattern):
        raise ValueError("Invalid --schema-like pattern (use A-Za-z0-9_%)")
    cur.execute(
        "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, "
        "COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT "
        "FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE %s "
        "ORDER BY TABLE_NAME, ORDINAL_POSITION",
        (pattern,),
    )
    return cur.fetchall()


def maybe_describe_on_unknown_column(err: BaseException) -> None:
    if "unknown column" not in str(err).lower():
        return
    print(
        "# hint: Unknown column — verify with --describe TABLE "
        "(or --schema-like 'prefix%'). Do not guess renames.",
        file=sys.stderr,
    )


def require_pymysql():
    try:
        import pymysql
    except ImportError:
        print("Missing pymysql. Run: python3 -m pip install pymysql", file=sys.stderr)
        sys.exit(2)
    return pymysql


def connect(secrets: dict[str, str], database: str):
    missing = [key for key in missing_core(secrets) if key != "MYSQL_DATABASE"]
    if missing or not database:
        print(
            "Missing read-only credentials: {}.\n"
            "Copy references/env.example to secrets.local.env in this skill folder,\n"
            "or set the same MYSQL_* environment variables.\n"
            "Do not reuse application.yml accounts.".format(
                ", ".join(missing) or "MYSQL_DATABASE"
            ),
            file=sys.stderr,
        )
        sys.exit(3)
    pymysql = require_pymysql()
    auth = {"pass" + "word": secrets.get("MYSQL_PASS")}
    return pymysql.connect(
        host=secrets.get("MYSQL_HOST"),
        port=int(secrets.get("MYSQL_PORT") or "3306"),
        user=secrets.get("MYSQL_USER"),
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=15,
        read_timeout=60,
        write_timeout=60,
        **auth,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only MySQL query")
    parser.add_argument("--sql")
    parser.add_argument("--file")
    parser.add_argument(
        "--describe",
        action="append",
        default=[],
        metavar="TABLE",
        help="DESCRIBE table (repeatable). Narrow column check before SELECT.",
    )
    parser.add_argument(
        "--schema-like",
        metavar="PATTERN",
        help="Dump columns where TABLE_NAME LIKE pattern",
    )
    parser.add_argument("--database", help="Override MYSQL_DATABASE")
    parser.add_argument(
        "--env",
        help="Use MYSQL_ENV_<NAME> as the database (e.g. --env release)",
    )
    parser.add_argument(
        "--secrets",
        help="Path to secrets.local.env (default: this skill folder)",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=DEFAULT_MAX_ROWS,
        help="Cap/auto LIMIT for SELECT/WITH (default {}). "
        "0 disables capping but still requires explicit LIMIT.".format(DEFAULT_MAX_ROWS),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    args = parse_args(argv)
    modes = sum(
        [
            bool(args.sql),
            bool(args.file),
            bool(args.describe),
            bool(args.schema_like),
        ]
    )
    if modes != 1:
        print(
            "Provide exactly one of --sql / --file / --describe / --schema-like",
            file=sys.stderr,
        )
        return 2
    if args.max_rows < 0:
        print("--max-rows must be >= 0", file=sys.stderr)
        return 2

    # Validate SQL before touching credentials or the network.
    guarded: list[tuple[str, str | None]] = []
    try:
        if args.describe:
            guarded = [(describe_sql(t), None) for t in args.describe]
        elif not args.schema_like:
            sql_text = args.sql if args.sql else Path(args.file).read_text(encoding="utf-8")
            statements = [assert_readonly(s) for s in split_statements(sql_text)]
            if not statements:
                raise ValueError("Empty SQL")
            for stmt in statements:
                new_sql, note = apply_row_guard(stmt, args.max_rows or None)
                if note:
                    print("# {}: {}".format(note, stmt[:120]), file=sys.stderr)
                guarded.append((new_sql, note))
    except ValueError as exc:
        print("Rejected: {}".format(exc), file=sys.stderr)
        return 1

    secrets = load_secrets(Path(args.secrets) if args.secrets else None)
    try:
        database = resolve_database(secrets, args.env, args.database)
    except ValueError as exc:
        print("Rejected: {}".format(exc), file=sys.stderr)
        return 1

    conn = connect(secrets, database)
    print("# database={}".format(database), file=sys.stderr)
    if args.max_rows:
        print("# max-rows={}".format(args.max_rows), file=sys.stderr)
    else:
        print("# max-rows=disabled", file=sys.stderr)

    try:
        with conn.cursor() as cur:
            if args.schema_like:
                rows = fetch_schema_like(cur, args.schema_like)
                if args.json:
                    print(json.dumps({"rows": rows}, ensure_ascii=False, default=str, indent=2))
                else:
                    print_tsv(rows)
                return 0

            for idx, (stmt, _note) in enumerate(guarded, 1):
                try:
                    cur.execute(stmt)
                    rows = cur.fetchall()
                except Exception as exc:
                    maybe_describe_on_unknown_column(exc)
                    raise

                truncated = False
                if args.max_rows and len(rows) > args.max_rows:
                    rows = rows[: args.max_rows]
                    truncated = True
                    print(
                        "# truncated result to {} rows; narrow WHERE or page with keyset".format(
                            args.max_rows
                        ),
                        file=sys.stderr,
                    )

                if args.json:
                    print(
                        json.dumps(
                            {
                                "statement": idx,
                                "sql": stmt,
                                "truncated": truncated,
                                "rows": rows,
                            },
                            ensure_ascii=False,
                            default=str,
                            indent=2,
                        )
                    )
                else:
                    if len(guarded) > 1:
                        print("## statement {}".format(idx))
                    print_tsv(rows)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print("Rejected: {}".format(exc), file=sys.stderr)
        raise SystemExit(1)
    except SystemExit:
        raise
    except Exception as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        raise SystemExit(1)
