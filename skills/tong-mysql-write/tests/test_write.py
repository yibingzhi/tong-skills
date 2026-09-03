from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import write  # noqa: E402
from write import (  # noqa: E402
    build_undo_delete,
    build_undo_insert,
    build_undo_update,
    parse_dml,
    preview_plan,
    snapshot_sql,
    undo_blocker,
)


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "write.py"


def lit(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'{}'".format(str(value).replace("'", "''"))


class FakeCursor:
    """Answers SHOW COLUMNS / snapshot SELECT / DML with canned rows."""

    def __init__(self, columns, snapshot, rowcount, lastrowid=None):
        self.columns = columns
        self.snapshot = snapshot
        self.rowcount_value = rowcount
        self.lastrowid = lastrowid
        self.executed: list[str] = []
        self._rows: list[dict] = []
        self.rowcount = -1

    def execute(self, sql, params=None):
        self.executed.append(sql)
        upper = sql.upper()
        if upper.startswith("SHOW COLUMNS"):
            self._rows = self.columns
        elif upper.startswith("SELECT"):
            self._rows = self.snapshot
        else:
            self._rows = []
            self.rowcount = self.rowcount_value

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self._cursor

    def literal(self, value):
        return lit(value)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


USERS_COLUMNS = [
    {"Field": "id", "Key": "PRI", "Extra": "auto_increment"},
    {"Field": "name", "Key": "", "Extra": ""},
    {"Field": "status", "Key": "", "Extra": ""},
]


class TestParseDml(unittest.TestCase):
    def test_update_ok(self) -> None:
        parsed = parse_dml("UPDATE users SET status=1 WHERE id=42")
        self.assertEqual(parsed["kind"], "update")
        self.assertEqual(parsed["table"], "users")
        self.assertEqual(parsed["where"], "id=42")

    def test_update_requires_where(self) -> None:
        with self.assertRaises(ValueError):
            parse_dml("UPDATE users SET status=1")

    def test_update_rejects_1eq1(self) -> None:
        with self.assertRaises(ValueError):
            parse_dml("UPDATE users SET status=1 WHERE 1=1")

    def test_allow_full_table(self) -> None:
        parsed = parse_dml("UPDATE users SET status=1", allow_full_table=True)
        self.assertIsNone(parsed["where"])

    def test_delete_ok(self) -> None:
        parsed = parse_dml("DELETE FROM users WHERE id=9")
        self.assertEqual(parsed["kind"], "delete")
        self.assertEqual(parsed["where"], "id=9")

    def test_insert_values_count(self) -> None:
        parsed = parse_dml("INSERT INTO users (id, name) VALUES (1, 'a'), (2, 'b')")
        self.assertEqual(parsed["kind"], "insert")
        self.assertEqual(parsed["rows"], 2)

    def test_insert_ignore(self) -> None:
        parsed = parse_dml("INSERT IGNORE INTO users (id) VALUES (1)")
        self.assertEqual(parsed["table"], "users")
        self.assertEqual(parsed["rows"], 1)

    def test_rejects_insert_select(self) -> None:
        with self.assertRaises(ValueError):
            parse_dml("INSERT INTO users SELECT * FROM other")

    def test_rejects_drop(self) -> None:
        with self.assertRaises(ValueError):
            parse_dml("DROP TABLE users")

    def test_rejects_replace(self) -> None:
        with self.assertRaises(ValueError):
            parse_dml("REPLACE INTO users (id) VALUES (1)")

    def test_subquery_where_uses_outer(self) -> None:
        parsed = parse_dml(
            "UPDATE users SET x=(SELECT y FROM z WHERE id=1) WHERE id=2"
        )
        self.assertEqual(parsed["where"], "id=2")

    def test_preview_plan_update(self) -> None:
        parsed = parse_dml("UPDATE `users` SET x=1 WHERE id=2")
        plan = preview_plan(parsed, 20)
        self.assertIn("COUNT(*)", plan["count_sql"])
        self.assertIn("LIMIT 20", plan["sample_sql"])
        self.assertIn("`users`", plan["count_sql"])

    def test_comment_cannot_hide_where(self) -> None:
        for sql in (
            "UPDATE t SET a=1 -- WHERE id=1",
            "UPDATE t SET a=1 /* WHERE id=1 */",
            "DELETE FROM t # WHERE id=1",
        ):
            with self.assertRaises(ValueError):
                parse_dml(sql)

    def test_keyword_inside_literal_is_allowed(self) -> None:
        parsed = parse_dml("UPDATE t SET bio='I do stuff', note='drop it' WHERE id=1")
        self.assertEqual(parsed["where"], "id=1")

    def test_backslash_and_doubled_quotes(self) -> None:
        parsed = parse_dml("UPDATE t SET a='it\\'s', b='x''y' WHERE id=1 AND n='a\\'b'")
        self.assertEqual(parsed["where"], "id=1 AND n='a\\'b'")
        with self.assertRaises(ValueError):
            parse_dml("UPDATE t SET a='unclosed WHERE id=1")

    def test_where_tail_order_limit(self) -> None:
        parsed = parse_dml("UPDATE t SET a=1 WHERE id>0 ORDER BY id LIMIT 10")
        self.assertEqual(parsed["where"], "id>0")
        self.assertEqual(parsed["order"], "ORDER BY id")
        self.assertEqual(parsed["limit"], 10)
        plan = preview_plan(parsed, 20)
        self.assertEqual(plan["count_sql"], "SELECT COUNT(*) AS n FROM `t` WHERE id>0")
        self.assertEqual(plan["sample_sql"], "SELECT * FROM `t` WHERE id>0 ORDER BY id LIMIT 10")

    def test_limit_without_where_is_full_table(self) -> None:
        with self.assertRaises(ValueError):
            parse_dml("UPDATE t SET a=1 LIMIT 10")
        parsed = parse_dml("DELETE FROM t LIMIT 10", allow_full_table=True)
        self.assertTrue(parsed["full_table"])
        self.assertEqual(parsed["limit"], 10)

    def test_update_set_cols(self) -> None:
        parsed = parse_dml("UPDATE t SET a = 1, `b`='x=y', c=IF(d=1, 2, 3) WHERE id=1")
        self.assertEqual(parsed["set_cols"], ["a", "b", "c"])

    def test_insert_columns_values_upsert(self) -> None:
        parsed = parse_dml("INSERT INTO t (id, name) VALUES (1, 'a'), (2, 'b')")
        self.assertEqual(parsed["columns"], ["id", "name"])
        self.assertEqual(parsed["values"], [["1", "'a'"], ["2", "'b'"]])
        self.assertFalse(parsed["upsert"])
        parsed = parse_dml("INSERT INTO t SET id=5, name='z' ON DUPLICATE KEY UPDATE name='z'")
        self.assertEqual(parsed["columns"], ["id", "name"])
        self.assertTrue(parsed["upsert"])
        with self.assertRaises(ValueError):
            parse_dml("INSERT INTO t (id, name) VALUES (1)")

    def test_undo_blocker(self) -> None:
        upd = parse_dml("UPDATE t SET status=1 WHERE id=1")
        self.assertIsNone(undo_blocker(upd, ["id"], ["id"]))
        self.assertIn("PRIMARY KEY", undo_blocker(upd, [], []))
        self.assertIn("primary key", undo_blocker(parse_dml("UPDATE t SET id=2 WHERE id=1"), ["id"], []))
        self.assertIsNone(undo_blocker(parse_dml("DELETE FROM t WHERE id=1"), [], []))
        ins_auto = parse_dml("INSERT INTO t (name) VALUES ('a')")
        self.assertIsNone(undo_blocker(ins_auto, ["id"], ["id"]))
        self.assertIsNotNone(undo_blocker(ins_auto, ["id"], []))
        ins_pk = parse_dml("INSERT INTO t (id, name) VALUES (7, 'a')")
        self.assertIsNone(undo_blocker(ins_pk, ["id"], []))
        self.assertIn("NULL", undo_blocker(parse_dml("INSERT INTO t (id) VALUES (NULL)"), ["id"], ["id"]))
        self.assertIn("DUPLICATE", undo_blocker(
            parse_dml("INSERT INTO t (id) VALUES (1) ON DUPLICATE KEY UPDATE id=1"), ["id"], []))
        self.assertIn("column list", undo_blocker(parse_dml("INSERT INTO t VALUES (1)"), ["id"], []))

    def test_build_undo_statements(self) -> None:
        rows = [{"id": 1, "name": "a'b", "status": 0}, {"id": 2, "name": None, "status": 1}]
        upd = build_undo_update("`t`", rows, ["status"], ["id"], lit)
        self.assertEqual(upd, [
            "UPDATE `t` SET `status`=0 WHERE `id`=1;",
            "UPDATE `t` SET `status`=1 WHERE `id`=2;",
        ])
        dele = build_undo_delete("`t`", rows, lit)
        self.assertEqual(dele, [
            "INSERT INTO `t` (`id`, `name`, `status`) VALUES (1, 'a''b', 0), (2, NULL, 1);"
        ])
        ins = build_undo_insert("`t`", parse_dml("INSERT INTO t (id, name) VALUES (7,'a'),(8,'b')"), ["id"], None, 2)
        self.assertEqual(ins, ["DELETE FROM `t` WHERE `id` IN ((7), (8));"])
        ins = build_undo_insert("`t`", parse_dml("INSERT INTO t (name) VALUES ('a'),('b')"), ["id"], 41, 2)
        self.assertEqual(ins, ["DELETE FROM `t` WHERE `id` BETWEEN 41 AND 42;"])
        comp = build_undo_insert("`t`", parse_dml("INSERT INTO t (a, b, v) VALUES (1, 2, 'x')"), ["a", "b"], None, 1)
        self.assertEqual(comp, ["DELETE FROM `t` WHERE (`a`, `b`) IN (((1), (2)));"])

    def test_snapshot_sql_locks_and_caps(self) -> None:
        parsed = parse_dml("UPDATE t SET a=1 WHERE id>0 ORDER BY id LIMIT 10")
        self.assertEqual(snapshot_sql(parsed, "`t`", 5001),
                         "SELECT * FROM `t` WHERE id>0 ORDER BY id LIMIT 10 FOR UPDATE")
        parsed = parse_dml("DELETE FROM t WHERE id=3")
        self.assertEqual(snapshot_sql(parsed, "`t`", 5001),
                         "SELECT * FROM `t` WHERE id=3 LIMIT 5001 FOR UPDATE")

    def _run_apply(self, argv, cursor):
        conn = FakeConn(cursor)
        env = {"MYSQL_HOST": "h", "MYSQL_USER": "u", "MYSQL_PASS": "p", "MYSQL_DATABASE": "d"}
        with mock.patch.object(write, "connect", return_value=conn), \
             mock.patch.dict(os.environ, env, clear=False):
            code = write.main(argv)
        return code, conn

    def test_apply_writes_undo_then_commits(self) -> None:
        snapshot = [{"id": 1, "name": "a", "status": 0}]
        cur = FakeCursor(USERS_COLUMNS, snapshot, rowcount=1)
        with tempfile.TemporaryDirectory() as tmp:
            code, conn = self._run_apply(
                ["--sql", "UPDATE users SET status=1 WHERE id=1", "--apply",
                 "--expect-rows", "1", "--undo-dir", tmp], cur)
            self.assertEqual(code, 0)
            self.assertTrue(conn.committed)
            files = list(Path(tmp).glob("undo-*-users.sql"))
            self.assertEqual(len(files), 1)
            text = files[0].read_text(encoding="utf-8")
            self.assertIn("UPDATE `users` SET `status`=0 WHERE `id`=1;", text)
            self.assertIn("-- original: UPDATE users SET status=1 WHERE id=1", text)
        self.assertTrue(cur.executed[1].endswith("FOR UPDATE"))
        self.assertEqual(cur.executed[2], "UPDATE users SET status=1 WHERE id=1")

    def test_apply_expect_rows_mismatch_rolls_back(self) -> None:
        cur = FakeCursor(USERS_COLUMNS, [{"id": 1, "name": "a", "status": 0}], rowcount=3)
        with tempfile.TemporaryDirectory() as tmp:
            code, conn = self._run_apply(
                ["--sql", "DELETE FROM users WHERE status=0", "--apply",
                 "--expect-rows", "1", "--undo-dir", tmp], cur)
            self.assertEqual(code, 1)
            self.assertTrue(conn.rolled_back)
            self.assertFalse(conn.committed)
            self.assertEqual(list(Path(tmp).glob("*.sql")), [])

    def test_apply_refuses_when_undo_impossible(self) -> None:
        no_pk = [{"Field": "a", "Key": "", "Extra": ""}]
        cur = FakeCursor(no_pk, [], rowcount=1)
        code, conn = self._run_apply(["--sql", "UPDATE t SET a=1 WHERE a=2", "--apply"], cur)
        self.assertEqual(code, 1)
        self.assertFalse(conn.committed)
        self.assertEqual(len(cur.executed), 1)  # only SHOW COLUMNS, no DML
        cur = FakeCursor(no_pk, [], rowcount=1)
        code, conn = self._run_apply(["--sql", "UPDATE t SET a=1 WHERE a=2", "--apply", "--no-undo"], cur)
        self.assertEqual(code, 0)
        self.assertTrue(conn.committed)

    def test_apply_refuses_over_undo_max(self) -> None:
        big = [{"id": i, "name": "n", "status": 0} for i in range(4)]
        cur = FakeCursor(USERS_COLUMNS, big, rowcount=4)
        code, conn = self._run_apply(
            ["--sql", "DELETE FROM users WHERE status=0", "--apply", "--undo-max-rows", "3"], cur)
        self.assertEqual(code, 1)
        self.assertFalse(conn.committed)

    def test_apply_insert_undo_uses_lastrowid(self) -> None:
        cur = FakeCursor(USERS_COLUMNS, [], rowcount=2, lastrowid=100)
        with tempfile.TemporaryDirectory() as tmp:
            code, conn = self._run_apply(
                ["--sql", "INSERT INTO users (name) VALUES ('a'), ('b')", "--apply", "--undo-dir", tmp], cur)
            self.assertEqual(code, 0)
            text = next(Path(tmp).glob("*.sql")).read_text(encoding="utf-8")
            self.assertIn("DELETE FROM `users` WHERE `id` BETWEEN 100 AND 101;", text)

    def test_cli_full_table_apply_needs_expect_rows(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--sql", "UPDATE t SET a=1",
             "--allow-full-table", "--apply"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--expect-rows", result.stderr)

    def test_cli_rejects_two_statements(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--sql", "UPDATE t SET a=1 WHERE id=1; DELETE FROM t WHERE id=2"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("one statement", result.stderr)

    def test_help(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--apply", result.stdout)

    def test_cli_rejects_select(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--sql", "SELECT 1"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Rejected", result.stderr)


if __name__ == "__main__":
    unittest.main()
