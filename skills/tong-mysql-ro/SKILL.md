---
name: tong-mysql-ro
description: >-
  Query MySQL read-only via a guarded CLI: SELECT/SHOW/DESCRIBE/EXPLAIN only,
  describe-before-select, auto LIMIT. Use when the user asks to 查库, 只读查询,
  DESCRIBE, mysql select, or tong-mysql-ro. Never write. Never reuse
  application.yml credentials.
license: MIT
compatibility: Requires Python 3.10+ and pymysql. Works on macOS, Windows, and Linux.
metadata:
  version: "0.1"
  author: TongSkills
---

# Tong MySQL (read-only)

Run **one** bundled script. Do not invent a query helper. Do not use app config accounts.

Writes go to `tong-mysql-write`. This skill never `INSERT`/`UPDATE`/`DELETE`.

## Workflow

Copy this checklist. `<skill-dir>` is the folder that contains this `SKILL.md`. If `python3` is missing, use `py -3`.

```bash
python3 "<skill-dir>/scripts/query.py" --sql "SELECT DATABASE()"
```

1. **凭证。** Need `MYSQL_HOST` / `MYSQL_USER` / `MYSQL_PASS` / `MYSQL_DATABASE` in `secrets.local.env` next to this `SKILL.md`, or the same names in the environment. Template: [env.example](references/env.example). Missing keys → ask the user for a **read-only** account. Do not copy values from `application.yml`.
2. **先核实列，再写列名。** Before a `SELECT` that names columns, the column list must come from `--describe TABLE`, `--schema-like 'prefix%'`, or a schema note already loaded this session. Same table: do not describe twice.
3. **窄查。** Indexed `WHERE` (`id` / unique key / time range). No unbounded `SELECT *` on big tables. Default `--max-rows 200` adds or caps `LIMIT`. Keyset page: `WHERE id > ? ORDER BY id LIMIT n`.
4. **Unknown column** → `--describe` again. Do not guess renames.
5. Return the TSV (or `--json`). Do not dump credentials.

## Commands

```bash
python3 "<skill-dir>/scripts/query.py" --describe users
python3 "<skill-dir>/scripts/query.py" --schema-like "order%"
python3 "<skill-dir>/scripts/query.py" --sql "SELECT id FROM users WHERE id=1"
python3 "<skill-dir>/scripts/query.py" --file path/to/q.sql --max-rows 500
python3 "<skill-dir>/scripts/query.py" --env release --sql "SELECT 1"
python3 "<skill-dir>/scripts/query.py" --database other_db --sql "SHOW TABLES"
```

| Flag | Meaning |
|---|---|
| `--sql` / `--file` / `--describe` / `--schema-like` | Exactly one |
| `--database` | Override `MYSQL_DATABASE` |
| `--env NAME` | Use `MYSQL_ENV_NAME` as the database |
| `--secrets PATH` | Alternate env file |
| `--max-rows N` | Default `200`. `0` = no cap, but SQL must still include `LIMIT` |
| `--json` | JSON instead of TSV |

## Hard rules

1. Only `SELECT` / `SHOW` / `DESCRIBE` / `EXPLAIN` / `WITH … SELECT`. `FOR UPDATE`, `LOCK IN SHARE MODE`, `LOAD_FILE` are rejected.
2. **No SQL comments** (`--`, `#`, `/* */`). A trailing comment would swallow the auto `LIMIT`. Keywords inside string values (`LIKE '%update%'`) are fine.
3. Do not regenerate this script. Do not open a second SQL client "just this once".
4. Never print `MYSQL_PASS` or the env file.
5. `--max-rows 0` is an escape hatch, not the default.

Install: `python3 -m pip install pymysql`

## Quality gate

- Columns were verified before a named-column `SELECT`
- Result is bounded (script LIMIT or scalar aggregate)
- Failures quote the script error; no silent retry with guessed column names
