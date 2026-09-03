---
name: tong-mysql-write
description: >-
  Run approved MySQL DML (INSERT/UPDATE/DELETE) through a guarded CLI: preview
  matching rows first, apply only after the user confirms. Use when the user
  explicitly asks to 改库, 写入, 执行 UPDATE/INSERT/DELETE, or tong-mysql-write.
  Do not use for SELECT or schema dumps — that is tong-mysql-ro.
license: MIT
compatibility: Requires Python 3.10+ and pymysql. Works on macOS, Windows, and Linux.
metadata:
  version: "0.2"
  author: TongSkills
---

# Tong MySQL (write)

One `INSERT` / `UPDATE` / `DELETE` at a time. **Default is preview.** `--apply` only after the user sees the preview and says 执行 / 确认 / apply. Every `--apply` writes an undo script first; if undo cannot be built it refuses.

If they only asked to 查 / SELECT, stop and use `tong-mysql-ro`.

No DDL (`CREATE`/`ALTER`/`DROP`/`TRUNCATE`). No `REPLACE`. No `INSERT … SELECT`. No multi-table JOIN writes.

## Workflow

Copy this checklist. `<skill-dir>` is the folder that contains this `SKILL.md`. If `python3` is missing, use `py -3`.

1. **授权。** The user must have asked to change rows (改库 / 写入 / 执行这条 UPDATE). "帮我看看能不能改" is not `--apply`.
2. **列。** `tong-mysql-ro --describe TABLE` first if columns are not already verified this session.
3. **预览（无 --apply）。**

```bash
python3 "<skill-dir>/scripts/write.py" --sql "UPDATE users SET status=1 WHERE id=42"
```

`UPDATE`/`DELETE`: script runs `COUNT(*)` + `SELECT * … LIMIT 20` on the same `WHERE` (honours the statement's own `ORDER BY` / `LIMIT`). `INSERT`: prints the would-affect row count, does not write.
4. **停。** Show `would_affect` and the sample. Do not pass `--apply` in the same turn.
5. **提交。** Only when they reply 执行 / 确认 / apply **for this statement**. Pass the preview's `would_affect` as `--expect-rows`; the script rolls back if the live match count differs:

```bash
python3 "<skill-dir>/scripts/write.py" --sql "UPDATE users SET status=1 WHERE id=42" --apply --expect-rows 1
```

Same SQL as the preview. If they edited the SQL, preview again. Full-table writes (`--allow-full-table`) refuse `--apply` without `--expect-rows`.
6. **回滚脚本。** `--apply` snapshots the rows it is about to touch (`SELECT … FOR UPDATE` in the same transaction), writes `tmp/tong-mysql-write/undo-<stamp>-<table>.sql`, then commits. Output has `undo\t<path>`. Tell the user the path. Undo content: `DELETE` → `INSERT` rows back; `UPDATE` → `UPDATE … SET old values WHERE pk`; `INSERT` → `DELETE … WHERE pk IN (...)` or `BETWEEN` on the auto-increment id.

`--apply` refuses (exit 1, nothing written) when undo is impossible: table without primary key (UPDATE/INSERT), UPDATE that changes a primary key column, `INSERT … ON DUPLICATE KEY UPDATE`, INSERT without a column list, or more than `--undo-max-rows` (5000) rows. Only pass `--no-undo` when the user explicitly accepts no rollback.

## Commands

```bash
python3 "<skill-dir>/scripts/write.py" --sql "INSERT INTO users (id, name) VALUES (1, 'a')"
python3 "<skill-dir>/scripts/write.py" --file path/to/dml.sql --apply
python3 "<skill-dir>/scripts/write.py" --env release --sql "DELETE FROM users WHERE id=42"
```

| Flag | Meaning |
|---|---|
| `--sql` / `--file` | Exactly one statement |
| `--apply` | Commit. Omit = preview |
| `--expect-rows N` | With `--apply`: roll back unless matched rows == N. Use the preview's `would_affect` |
| `--allow-full-table` | `UPDATE`/`DELETE` with no `WHERE` (preview first; `--apply` also needs `--expect-rows`) |
| `--no-undo` | Skip the undo script. Needs the user's explicit OK |
| `--undo-dir PATH` | Default `tmp/tong-mysql-write` under cwd |
| `--undo-max-rows N` | Refuse `--apply` above N rows (default 5000) |
| `--database` / `--env` / `--secrets` | Same as `tong-mysql-ro` |
| `--sample-rows N` | Preview sample size (default 20) |
| `--json` | JSON instead of TSV |

凭证: copy [env.example](references/env.example) to `secrets.local.env`, or set `MYSQL_*`. Use a dedicated write account granted only `SELECT, INSERT, UPDATE, DELETE` — no `DROP` / `ALTER` / `CREATE` / `TRUNCATE`. The script blocks DDL, but the grant is the real floor.

Undo files land in `tmp/` (gitignored in TongSkills). They contain row data; do not commit or paste them into chat.

## Hard rules

1. Run the bundled script. Do not hand-roll `pymysql` "just this once".
2. `UPDATE`/`DELETE` need a real `WHERE`. `WHERE 1=1` / `WHERE true` / a bare `LIMIT` count as full-table and need `--allow-full-table` **and** an explicit user ask.
3. **No SQL comments** (`--`, `#`, `/* */`). The script rejects them: a comment can hide the `WHERE` from the preview. Keywords inside string values are fine.
4. Never print `MYSQL_PASS`.
5. Never `--apply` because a previous turn previewed a *different* statement.
6. On error, "Rolled back: matched X rows, expected N", or "cannot build undo SQL": quote the script, preview again. Do not retry with a broader `WHERE`, do not add `--no-undo` on your own.
7. To roll back, hand the user the undo file path. Run it with a mysql client; `write.py` takes one statement at a time and rejects the comment header.

Install: `python3 -m pip install pymysql`

## Quality gate

- Preview ran and the user confirmed **this** SQL
- `--apply` output includes `affected` and an `undo` path (or the user said no-undo)
- No DDL, no second statement, no guessed table
