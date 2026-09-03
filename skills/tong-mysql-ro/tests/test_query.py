from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from query import (  # noqa: E402
    apply_row_guard,
    assert_readonly,
    load_secrets,
    resolve_database,
    split_statements,
)


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "query.py"


class TestReadonlyGuard(unittest.TestCase):
    def test_select_ok(self) -> None:
        self.assertEqual(assert_readonly("SELECT 1"), "SELECT 1")

    def test_rejects_update(self) -> None:
        with self.assertRaises(ValueError):
            assert_readonly("UPDATE users SET x=1 WHERE id=1")

    def test_rejects_into_outfile(self) -> None:
        with self.assertRaises(ValueError):
            assert_readonly("SELECT 1 INTO OUTFILE '/tmp/x'")

    def test_with_requires_select(self) -> None:
        with self.assertRaises(ValueError):
            assert_readonly("WITH x AS (SELECT 1)")
        assert_readonly("WITH x AS (SELECT 1) SELECT * FROM x")

    def test_keyword_inside_literal_is_allowed(self) -> None:
        sql = "SELECT * FROM log WHERE msg LIKE '%update%' AND kind='do'"
        self.assertEqual(assert_readonly(sql), sql)

    def test_rejects_comments(self) -> None:
        for sql in (
            "SELECT * FROM big -- note",
            "SELECT * FROM big # note",
            "SELECT /* hint */ * FROM big",
        ):
            with self.assertRaises(ValueError):
                assert_readonly(sql)
        # '--' inside a literal is data, not a comment
        assert_readonly("SELECT * FROM t WHERE note='a -- b'")

    def test_rejects_load_file_and_for_update(self) -> None:
        with self.assertRaises(ValueError):
            assert_readonly("SELECT LOAD_FILE('/etc/hosts')")
        with self.assertRaises(ValueError):
            assert_readonly("SELECT * FROM t WHERE id=1 FOR UPDATE")

    def test_limit_regex_ignores_literals(self) -> None:
        sql, note = apply_row_guard("SELECT * FROM t WHERE tag='limit 5'", 200)
        self.assertTrue(sql.lower().endswith("limit 200"))
        self.assertIsNotNone(note)

    def test_backslash_escape_does_not_split(self) -> None:
        parts = split_statements("SELECT 'a\\'; DROP TABLE x' FROM t")
        self.assertEqual(len(parts), 1)
        with self.assertRaises(ValueError):
            split_statements("SELECT 'unclosed FROM t")

    def test_auto_limit(self) -> None:
        sql, note = apply_row_guard("SELECT id FROM users WHERE id>1", 200)
        self.assertTrue(sql.lower().endswith("limit 200"))
        self.assertIn("auto LIMIT", note or "")

    def test_cap_limit(self) -> None:
        sql, note = apply_row_guard("SELECT * FROM users LIMIT 9999", 200)
        self.assertTrue(sql.lower().endswith("limit 200"))
        self.assertIn("capped", note or "")

    def test_scalar_agg_no_limit(self) -> None:
        sql, note = apply_row_guard("SELECT COUNT(*) FROM users WHERE id=1", 200)
        self.assertEqual(sql, "SELECT COUNT(*) FROM users WHERE id=1")
        self.assertIsNone(note)

    def test_max_rows_0_requires_limit(self) -> None:
        with self.assertRaises(ValueError):
            apply_row_guard("SELECT id FROM users", 0)

    def test_split_statements(self) -> None:
        parts = split_statements("SELECT 1; SELECT 2;")
        self.assertEqual(parts, ["SELECT 1", "SELECT 2"])

    def test_env_database(self) -> None:
        db = resolve_database({"MYSQL_ENV_RELEASE": "prod"}, "release", None)
        self.assertEqual(db, "prod")

    def test_load_secrets_from_env(self) -> None:
        old = os.environ.get("MYSQL_HOST")
        os.environ["MYSQL_HOST"] = "127.0.0.1"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                secrets = load_secrets(Path(tmp) / "missing.env")
            self.assertEqual(secrets.get("MYSQL_HOST"), "127.0.0.1")
        finally:
            if old is None:
                os.environ.pop("MYSQL_HOST", None)
            else:
                os.environ["MYSQL_HOST"] = old

    def test_help(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--sql", result.stdout)


if __name__ == "__main__":
    unittest.main()
