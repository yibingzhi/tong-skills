#!/usr/bin/env python3
"""Guarded MySQL DML. Preview by default; --apply commits one INSERT/UPDATE/DELETE."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SECRETS = SKILL_DIR / "secrets.local.env"
DEFAULT_SAMPLE_ROWS = 20
DEFAULT_UNDO_MAX_ROWS = 5000
DEFAULT_UNDO_DIR = Path("tmp") / "tong-mysql-write"
UNDO_INSERT_CHUNK = 500

CORE_KEYS = (
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASS",
    "MYSQL_DATABASE",
)
SAFE_ENV = re.compile(r"^[A-Za-z0-9_]+$")
SAFE_IDENT = re.compile(r"^[A-Za-z0-9_]+$")
BARE_WHERE = re.compile(r"^(?:1\s*=\s*1|true|1)$", re.I)
# Scanned on masked SQL (string/identifier contents blanked), so data values never trigger it.
FORBIDDEN = re.compile(
    r"\b(alter|drop|create|truncate|rename|grant|revoke|call|do|lock|unlock|"
    r"load|load_file|handler|replace|set\s+global|set\s+@@|into\s+outfile|"
    r"into\s+dumpfile)\b",
    re.I,
)
COMMENT_START = re.compile(r"--(?=\s|$)|#|/\*")
TAIL_CLAUSE = re.compile(r"\b(order\s+by|limit)\b", re.I)
LIMIT_TAIL = re.compile(r"\blimit\s+(\d+)\s*$", re.I)
ON_DUPLICATE = re.compile(r"\bon\s+duplicate\s+key\s+update\b", re.I)


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
    parens, semicolons, comments) never see user data.
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


def _skip_ws(text: str, i: int) -> int:
    while i < len(text) and text[i].isspace():
        i += 1
    return i


def _read_ident(text: str, i: int) -> tuple[str, int]:
    i = _skip_ws(text, i)
    if i < len(text) and text[i] == "`":
        end = text.find("`", i + 1)
        if end < 0:
            raise ValueError("Unclosed identifier")
        return text[i : end + 1], end + 1
    start = i
    while i < len(text) and (text[i].isalnum() or text[i] == "_"):
        i += 1
    if start == i:
        raise ValueError("Expected table name")
    return text[start:i], i


def _read_table(text: str, i: int) -> tuple[str, int]:
    first, i = _read_ident(text, i)
    j = _skip_ws(text, i)
    if j < len(text) and text[j] == ".":
        second, i = _read_ident(text, j + 1)
        table = "{}.{}".format(first, second)
    else:
        table = first
    qualify_table(table)
    return table, i


def _skip_paren_list(masked: str, i: int) -> int:
    i = _skip_ws(masked, i)
    if i >= len(masked) or masked[i] != "(":
        return i
    depth = 0
    while i < len(masked):
        ch = masked[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("Unclosed parenthesis")


def _depth0_keyword(masked: str, keyword: str) -> int:
    """Index of the last depth-0 whole-word keyword in masked SQL, or -1."""
    lower = masked.lower()
    target = keyword.lower()
    depth = 0
    last = -1
    for i, ch in enumerate(lower):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and lower.startswith(target, i):
            before = lower[i - 1] if i else " "
            after_i = i + len(target)
            after = lower[after_i] if after_i < len(lower) else " "
            if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
                last = i
    return last


def _next_keyword(masked: str, i: int) -> str:
    i = _skip_ws(masked, i)
    start = i
    while i < len(masked) and (masked[i].isalpha() or masked[i] == "_"):
        i += 1
    return masked[start:i].lower()


def _value_groups(masked: str, i: int) -> tuple[list[tuple[int, int]], int]:
    """Spans of the (...) groups after VALUES, and the index after the last one."""
    groups: list[tuple[int, int]] = []
    while i < len(masked):
        i = _skip_ws(masked, i)
        if i >= len(masked):
            break
        if masked[i] != "(":
            if groups:
                break
            raise ValueError("INSERT VALUES must start with (")
        end = _skip_paren_list(masked, i)
        groups.append((i, end))
        i = _skip_ws(masked, end)
        if i < len(masked) and masked[i] == ",":
            i += 1
            continue
        break
    if not groups:
        raise ValueError("INSERT VALUES has no rows")
    return groups, i


def _split_depth0(masked: str, start: int, end: int) -> list[tuple[int, int]]:
    """Spans between depth-0 commas inside masked[start:end]."""
    spans: list[tuple[int, int]] = []
    depth = 0
    piece_start = start
    for i in range(start, end):
        ch = masked[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            spans.append((piece_start, i))
            piece_start = i + 1
    spans.append((piece_start, end))
    return spans


def _strip_ident(raw: str) -> str:
    name = raw.strip().strip("`").strip()
    if not SAFE_IDENT.match(name):
        raise ValueError("Invalid column {!r}".format(raw.strip()))
    return name


def _parse_assignments(text: str, masked: str, start: int, end: int) -> list[tuple[str, str]]:
    """`col = expr, col2 = expr2` -> [(col, expr_text), ...]."""
    pairs: list[tuple[str, str]] = []
    for a, b in _split_depth0(masked, start, end):
        eq = masked.find("=", a, b)
        if eq < 0:
            raise ValueError("Expected col = expr in SET")
        pairs.append((_strip_ident(text[a:eq]), text[eq + 1 : b].strip()))
    return pairs


def qualify_table(table: str) -> str:
    parts = []
    for chunk in table.split("."):
        bare = chunk.strip("`")
        if not SAFE_IDENT.match(bare):
            raise ValueError("Invalid table {!r}".format(table))
        parts.append("`{}`".format(bare))
    return ".".join(parts)


def _split_where_tail(text: str, masked: str, where_at: int) -> tuple[str | None, str | None, int | None]:
    """Return (condition, order_by_sql, limit_n) for the text after WHERE."""
    tail = text[where_at:]
    mtail = masked[where_at:]
    cut = len(tail)
    for m in TAIL_CLAUSE.finditer(mtail):
        depth = mtail.count("(", 0, m.start()) - mtail.count(")", 0, m.start())
        if depth == 0:
            cut = m.start()
            break
    cond = tail[:cut].strip() or None
    rest = tail[cut:].strip()
    limit_n = None
    order_sql = None
    if rest:
        lm = LIMIT_TAIL.search(rest)
        if lm:
            limit_n = int(lm.group(1))
            rest = rest[: lm.start()].strip()
        if rest:
            if not rest.lower().startswith("order"):
                raise ValueError("Only ORDER BY / LIMIT may follow WHERE")
            order_sql = rest
    return cond, order_sql, limit_n


def _where_block(text: str, masked: str, allow_full_table: bool, verb: str) -> dict:
    where_at = _depth0_keyword(masked, "where")
    clause_at = len(masked)
    if where_at >= 0:
        clause_at = where_at
        cond, order_sql, limit_n = _split_where_tail(text, masked, where_at + len("where"))
    else:
        cond, order_sql, limit_n = None, None, None
        # UPDATE t SET ... LIMIT n / ORDER BY without WHERE is still full-table
        for m in TAIL_CLAUSE.finditer(masked):
            depth = masked.count("(", 0, m.start()) - masked.count(")", 0, m.start())
            if depth == 0:
                clause_at = m.start()
                _c, order_sql, limit_n = _split_where_tail(text, masked, clause_at)
                break
    full_table = cond is None or bool(BARE_WHERE.match(cond))
    if full_table:
        if not allow_full_table:
            shown = "WHERE {}".format(cond) if cond else "without WHERE"
            raise ValueError("{} {} is forbidden (pass --allow-full-table)".format(verb, shown))
        cond = None
    return {
        "where": cond,
        "order": order_sql,
        "limit": limit_n,
        "full_table": full_table,
        "_clause_at": clause_at,
    }


def parse_dml(sql: str, allow_full_table: bool = False) -> dict:
    text = sql.strip().rstrip(";").strip()
    if not text:
        raise ValueError("Empty SQL")
    masked = mask_literals(text)
    cm = COMMENT_START.search(masked)
    if cm:
        raise ValueError(
            "Comments are not allowed in DML (found {!r}); a comment can hide the WHERE".format(
                masked[cm.start() : cm.start() + 2]
            )
        )
    if FORBIDDEN.search(masked):
        raise ValueError("DDL and REPLACE are forbidden; only INSERT/UPDATE/DELETE")
    lower = masked.lower()
    if not lower.startswith(("insert", "update", "delete")):
        raise ValueError("Only INSERT/UPDATE/DELETE are allowed")

    if lower.startswith("insert"):
        i = len("insert")
        while True:
            kw = _next_keyword(masked, i)
            if kw in {"low_priority", "delayed", "high_priority", "ignore", "into"}:
                i = _skip_ws(masked, i) + len(kw)
                if kw == "into":
                    break
                continue
            break
        table, i = _read_table(text, i)
        columns: list[str] | None = None
        j = _skip_ws(masked, i)
        if j < len(masked) and masked[j] == "(":
            end = _skip_paren_list(masked, j)
            columns = [_strip_ident(text[a:b]) for a, b in _split_depth0(masked, j + 1, end - 1)]
            i = end
        kind = _next_keyword(masked, i)
        if kind == "select":
            raise ValueError("INSERT ... SELECT is forbidden")
        dup = ON_DUPLICATE.search(masked)
        upsert = dup is not None
        out = {"kind": "insert", "table": table, "sql": text, "full_table": False, "upsert": upsert}
        if kind == "set":
            i = _skip_ws(masked, i) + len("set")
            end = dup.start() if dup else len(masked)
            pairs = _parse_assignments(text, masked, i, end)
            out.update(rows=1, columns=[c for c, _ in pairs], values=[[e for _, e in pairs]])
            return out
        if kind == "values":
            i = _skip_ws(masked, i) + len("values")
            groups, after = _value_groups(masked, i)
            trailing = _next_keyword(masked, after)
            if trailing not in {"", "on"}:
                raise ValueError("Unexpected {!r} after VALUES".format(trailing))
            values = [
                [text[a:b].strip() for a, b in _split_depth0(masked, s + 1, e - 1)]
                for s, e in groups
            ]
            if columns is not None and any(len(v) != len(columns) for v in values):
                raise ValueError("VALUES row length != column list length")
            out.update(rows=len(values), columns=columns, values=values)
            return out
        raise ValueError("INSERT must use VALUES or SET")

    if lower.startswith("update"):
        i = len("update")
        while _next_keyword(masked, i) in {"low_priority", "ignore"}:
            i = _skip_ws(masked, i) + len(_next_keyword(masked, i))
        table, i = _read_table(text, i)
        if _next_keyword(masked, i) != "set":
            raise ValueError("UPDATE must be single-table SET (no JOIN / alias)")
        set_start = _skip_ws(masked, i) + len("set")
        out = {"kind": "update", "table": table, "sql": text}
        block = _where_block(text, masked, allow_full_table, "UPDATE")
        pairs = _parse_assignments(text, masked, set_start, block.pop("_clause_at"))
        out["set_cols"] = [c for c, _ in pairs]
        out.update(block)
        return out

    i = len("delete")
    while _next_keyword(masked, i) in {"low_priority", "quick", "ignore"}:
        i = _skip_ws(masked, i) + len(_next_keyword(masked, i))
    if _next_keyword(masked, i) != "from":
        raise ValueError("DELETE must be DELETE FROM table WHERE ...")
    i = _skip_ws(masked, i) + len("from")
    table, i = _read_table(text, i)
    if _next_keyword(masked, i) in {"join", "using", "inner", "left", "right", "as"}:
        raise ValueError("Multi-table / aliased DELETE is forbidden")
    out = {"kind": "delete", "table": table, "sql": text}
    block = _where_block(text, masked, allow_full_table, "DELETE")
    block.pop("_clause_at")
    out.update(block)
    return out


def preview_plan(parsed: dict, sample_rows: int) -> dict:
    table = qualify_table(parsed["table"])
    if parsed["kind"] == "insert":
        return {
            "mode": "preview",
            "kind": "insert",
            "table": parsed["table"],
            "sql": parsed["sql"],
            "would_affect": parsed["rows"],
            "count_sql": None,
            "sample_sql": None,
        }
    cond = parsed.get("where")
    where_part = " WHERE {}".format(cond) if cond else ""
    order_part = " {}".format(parsed["order"]) if parsed.get("order") else ""
    limit_n = parsed.get("limit")
    sample_n = min(sample_rows, limit_n) if limit_n else sample_rows
    return {
        "mode": "preview",
        "kind": parsed["kind"],
        "table": parsed["table"],
        "sql": parsed["sql"],
        "where": cond,
        "limit": limit_n,
        "count_sql": "SELECT COUNT(*) AS n FROM {}{}".format(table, where_part),
        "sample_sql": "SELECT * FROM {}{}{} LIMIT {}".format(table, where_part, order_part, sample_n),
    }


def _q(name: str) -> str:
    return "`{}`".format(name)


def _pk_predicate(row: dict, pk_cols: list[str], literal) -> str:
    parts = []
    for col in pk_cols:
        val = row.get(col)
        if val is None:
            parts.append("{} IS NULL".format(_q(col)))
        else:
            parts.append("{}={}".format(_q(col), literal(val)))
    return " AND ".join(parts)


def undo_blocker(parsed: dict, pk_cols: list[str], auto_inc: list[str]) -> str | None:
    """Why an undo script cannot be built, or None if it can."""
    kind = parsed["kind"]
    if kind == "delete":
        return None
    if kind == "update":
        if not pk_cols:
            return "table has no PRIMARY KEY"
        if not parsed.get("set_cols"):
            return "cannot parse SET columns"
        touched = set(parsed["set_cols"]) & set(pk_cols)
        if touched:
            return "UPDATE touches primary key column(s) {}".format(", ".join(sorted(touched)))
        return None
    # insert
    if parsed.get("upsert"):
        return "ON DUPLICATE KEY UPDATE may update instead of insert"
    if not pk_cols:
        return "table has no PRIMARY KEY"
    columns = parsed.get("columns")
    if columns is None:
        return "INSERT without a column list"
    if all(col in columns for col in pk_cols):
        idx = [columns.index(col) for col in pk_cols]
        for row in parsed["values"]:
            for k in idx:
                if row[k].strip().upper() in {"NULL", "DEFAULT"}:
                    return "primary key given as NULL/DEFAULT"
        return None
    if len(pk_cols) == 1 and pk_cols[0] in auto_inc and pk_cols[0] not in columns:
        return None
    return "primary key is neither listed in the INSERT nor a single AUTO_INCREMENT column"


def build_undo_delete(table_q: str, rows: list[dict], literal) -> list[str]:
    if not rows:
        return []
    cols = list(rows[0].keys())
    col_sql = ", ".join(_q(c) for c in cols)
    out: list[str] = []
    for start in range(0, len(rows), UNDO_INSERT_CHUNK):
        chunk = rows[start : start + UNDO_INSERT_CHUNK]
        tuples = ", ".join(
            "({})".format(", ".join(literal(row[c]) for c in cols)) for row in chunk
        )
        out.append("INSERT INTO {} ({}) VALUES {};".format(table_q, col_sql, tuples))
    return out


def build_undo_update(
    table_q: str, rows: list[dict], set_cols: list[str], pk_cols: list[str], literal
) -> list[str]:
    out: list[str] = []
    for row in rows:
        assigns = ", ".join("{}={}".format(_q(c), literal(row.get(c))) for c in set_cols)
        out.append(
            "UPDATE {} SET {} WHERE {};".format(table_q, assigns, _pk_predicate(row, pk_cols, literal))
        )
    return out


def build_undo_insert(
    table_q: str, parsed: dict, pk_cols: list[str], lastrowid: int | None, affected: int
) -> list[str]:
    columns = parsed.get("columns") or []
    if all(col in columns for col in pk_cols):
        idx = [columns.index(col) for col in pk_cols]
        if len(pk_cols) == 1:
            keys = ", ".join("({})".format(row[idx[0]]) for row in parsed["values"])
            return ["DELETE FROM {} WHERE {} IN ({});".format(table_q, _q(pk_cols[0]), keys)]
        cols_sql = "({})".format(", ".join(_q(c) for c in pk_cols))
        tuples = ", ".join(
            "({})".format(", ".join("({})".format(row[k]) for k in idx)) for row in parsed["values"]
        )
        return ["DELETE FROM {} WHERE {} IN ({});".format(table_q, cols_sql, tuples)]
    if not lastrowid or affected < 1:
        return []
    first, last = lastrowid, lastrowid + affected - 1
    return [
        "DELETE FROM {} WHERE {} BETWEEN {} AND {};".format(table_q, _q(pk_cols[0]), first, last)
    ]


def snapshot_sql(parsed: dict, table_q: str, cap: int) -> str:
    cond = parsed.get("where")
    where_part = " WHERE {}".format(cond) if cond else ""
    order_part = " {}".format(parsed["order"]) if parsed.get("order") else ""
    limit_n = parsed.get("limit")
    n = min(limit_n, cap) if limit_n else cap
    # FOR UPDATE: lock exactly the rows we snapshot so the DML that follows hits the same set
    return "SELECT * FROM {}{}{} LIMIT {} FOR UPDATE".format(table_q, where_part, order_part, n)


def write_undo_file(
    undo_dir: Path, database: str, parsed: dict, statements: list[str], affected: int
) -> Path:
    import datetime as _dt

    undo_dir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    table = parsed["table"].replace("`", "").replace(".", "_")
    path = undo_dir / "undo-{}-{}.sql".format(stamp, table)
    header = [
        "-- tong-mysql-write undo script",
        "-- run with a mysql client (write.py rejects comment lines; paste statements one by one if using it)",
        "-- generated: {}".format(_dt.datetime.now().isoformat(timespec="seconds")),
        "-- database: {}".format(database),
        "-- table: {}".format(parsed["table"]),
        "-- original: {}".format(" ".join(parsed["sql"].split())),
        "-- affected: {}".format(affected),
        "-- undo statements: {}".format(len(statements)),
    ]
    if parsed["kind"] == "insert" and statements and "BETWEEN" in statements[0]:
        header.append("-- note: ids assumed consecutive from LAST_INSERT_ID (simple multi-row INSERT)")
    path.write_text("\n".join(header + [""] + statements) + "\n", encoding="utf-8")
    return path


def print_tsv(rows: list[dict]) -> None:
    if not rows:
        print("(0 rows)")
        return
    cols = list(rows[0].keys())
    print("\t".join(cols))
    for row in rows:
        print("\t".join("" if row[c] is None else str(row[c]) for c in cols))
    print("({} rows)".format(len(rows)))


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
            "Missing write credentials: {}.\n"
            "Copy references/env.example to secrets.local.env in this skill folder,\n"
            "or set the same MYSQL_* environment variables.\n"
            "Do not reuse application.yml accounts.".format(
                ", ".join(missing) or "MYSQL_DATABASE"
            ),
            file=sys.stderr,
        )
        sys.exit(3)
    pymysql = require_pymysql()
    from pymysql.constants import CLIENT

    auth = {"pass" + "word": secrets.get("MYSQL_PASS")}
    return pymysql.connect(
        host=secrets.get("MYSQL_HOST"),
        port=int(secrets.get("MYSQL_PORT") or "3306"),
        user=secrets.get("MYSQL_USER"),
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        # FOUND_ROWS: rowcount = matched rows, same thing the preview COUNT(*) measured
        client_flag=CLIENT.FOUND_ROWS,
        connect_timeout=15,
        read_timeout=60,
        write_timeout=60,
        **auth,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Guarded MySQL DML (preview by default; --apply to commit)"
    )
    parser.add_argument("--sql")
    parser.add_argument("--file")
    parser.add_argument("--database", help="Override MYSQL_DATABASE")
    parser.add_argument("--env", help="Use MYSQL_ENV_<NAME> as the database")
    parser.add_argument("--secrets", help="Path to secrets.local.env")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the DML. Default is preview only.",
    )
    parser.add_argument(
        "--expect-rows",
        type=int,
        metavar="N",
        help="With --apply: roll back unless matched rows == N "
        "(pass would_affect from the preview). Required for full-table writes.",
    )
    parser.add_argument(
        "--allow-full-table",
        action="store_true",
        help="Allow UPDATE/DELETE with no WHERE (still preview first; --apply needs --expect-rows).",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=DEFAULT_SAMPLE_ROWS,
        help="Preview sample size (default {}).".format(DEFAULT_SAMPLE_ROWS),
    )
    parser.add_argument(
        "--no-undo",
        action="store_true",
        help="Skip the undo script. Otherwise --apply refuses when undo cannot be built.",
    )
    parser.add_argument(
        "--undo-dir",
        default=str(DEFAULT_UNDO_DIR),
        help="Where undo-*.sql is written (default {}, relative to cwd).".format(DEFAULT_UNDO_DIR.as_posix()),
    )
    parser.add_argument(
        "--undo-max-rows",
        type=int,
        default=DEFAULT_UNDO_MAX_ROWS,
        help="Refuse --apply when more rows than this would need undo (default {}).".format(
            DEFAULT_UNDO_MAX_ROWS
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    args = parse_args(argv)
    if bool(args.sql) == bool(args.file):
        print("Provide exactly one of --sql / --file", file=sys.stderr)
        return 2
    if args.sample_rows < 1:
        print("--sample-rows must be >= 1", file=sys.stderr)
        return 2
    if args.expect_rows is not None and args.expect_rows < 0:
        print("--expect-rows must be >= 0", file=sys.stderr)
        return 2

    sql_text = args.sql if args.sql else Path(args.file).read_text(encoding="utf-8")
    try:
        statements = split_statements(sql_text)
        if len(statements) != 1:
            raise ValueError("exactly one statement required")
        parsed = parse_dml(statements[0], allow_full_table=args.allow_full_table)
    except ValueError as exc:
        print("Rejected: {}".format(exc), file=sys.stderr)
        return 1
    if args.apply and parsed.get("full_table") and args.expect_rows is None:
        print(
            "Rejected: full-table {} with --apply requires --expect-rows N "
            "(take match_count from the preview)".format(parsed["kind"].upper()),
            file=sys.stderr,
        )
        return 1

    secrets = load_secrets(Path(args.secrets) if args.secrets else None)
    try:
        database = resolve_database(secrets, args.env, args.database)
    except ValueError as exc:
        print("Rejected: {}".format(exc), file=sys.stderr)
        return 1

    conn = connect(secrets, database)
    print("# database={}".format(database), file=sys.stderr)
    print("# mode={}".format("apply" if args.apply else "preview"), file=sys.stderr)

    try:
        with conn.cursor() as cur:
            if not args.apply:
                plan = preview_plan(parsed, args.sample_rows)
                if parsed["kind"] == "insert":
                    if args.json:
                        print(json.dumps(plan, ensure_ascii=False, indent=2))
                    else:
                        print("kind\tinsert")
                        print("table\t{}".format(parsed["table"]))
                        print("would_affect\t{}".format(parsed["rows"]))
                        print("sql\t{}".format(parsed["sql"]))
                    return 0
                cur.execute(plan["count_sql"])
                count_row = cur.fetchone() or {}
                n = int(count_row.get("n") or 0)
                limit_n = plan.get("limit")
                would_affect = min(n, limit_n) if limit_n else n
                cur.execute(plan["sample_sql"])
                sample = cur.fetchall()
                payload = dict(plan)
                payload["match_count"] = n
                payload["would_affect"] = would_affect
                payload["sample"] = sample
                if args.json:
                    print(json.dumps(payload, ensure_ascii=False, default=str, indent=2))
                else:
                    print("kind\t{}".format(parsed["kind"]))
                    print("table\t{}".format(parsed["table"]))
                    print("match_count\t{}".format(n))
                    print("would_affect\t{}".format(would_affect))
                    print("sql\t{}".format(parsed["sql"]))
                    print("## sample")
                    print_tsv(sample)
                return 0

            table_q = qualify_table(parsed["table"])
            undo_stmts: list[str] | None = None
            pk_cols: list[str] = []
            if not args.no_undo:
                cur.execute("SHOW COLUMNS FROM {}".format(table_q))
                cols_info = cur.fetchall()
                pk_cols = [c["Field"] for c in cols_info if (c.get("Key") or "") == "PRI"]
                auto_inc = [
                    c["Field"] for c in cols_info if "auto_increment" in (c.get("Extra") or "").lower()
                ]
                reason = undo_blocker(parsed, pk_cols, auto_inc)
                if reason:
                    print(
                        "Rejected: cannot build undo SQL ({}); pass --no-undo to apply anyway".format(reason),
                        file=sys.stderr,
                    )
                    return 1
                if parsed["kind"] in {"update", "delete"}:
                    cur.execute(snapshot_sql(parsed, table_q, args.undo_max_rows + 1))
                    before = cur.fetchall()
                    if len(before) > args.undo_max_rows:
                        conn.rollback()
                        print(
                            "Rejected: {}+ rows would need undo (limit --undo-max-rows {}); "
                            "narrow the WHERE, raise the limit, or pass --no-undo".format(
                                args.undo_max_rows, args.undo_max_rows
                            ),
                            file=sys.stderr,
                        )
                        return 1
                    if parsed["kind"] == "delete":
                        undo_stmts = build_undo_delete(table_q, before, conn.literal)
                    else:
                        undo_stmts = build_undo_update(
                            table_q, before, parsed["set_cols"], pk_cols, conn.literal
                        )

            cur.execute(parsed["sql"])
            affected = cur.rowcount
            if args.expect_rows is not None and affected != args.expect_rows:
                conn.rollback()
                print(
                    "Rolled back: matched {} rows, expected {}. "
                    "Data changed since the preview; preview again.".format(
                        affected, args.expect_rows
                    ),
                    file=sys.stderr,
                )
                return 1
            if not args.no_undo and parsed["kind"] == "insert":
                undo_stmts = build_undo_insert(table_q, parsed, pk_cols, cur.lastrowid, affected)

            undo_path: Path | None = None
            if undo_stmts is not None:
                # Written before commit: if the process dies right after commit the file exists.
                undo_path = write_undo_file(
                    Path(args.undo_dir), database, parsed, undo_stmts, affected
                )
            conn.commit()
            payload = {
                "mode": "apply",
                "kind": parsed["kind"],
                "table": parsed["table"],
                "sql": parsed["sql"],
                "affected": affected,
                "undo": str(undo_path) if undo_path else None,
                "undo_statements": len(undo_stmts) if undo_stmts is not None else 0,
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print("kind\t{}".format(parsed["kind"]))
                print("table\t{}".format(parsed["table"]))
                print("affected\t{}".format(affected))
                print("undo\t{}".format(undo_path if undo_path else "(skipped)"))
            return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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
