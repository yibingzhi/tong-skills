from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sync_push import classify_url, is_forbidden_root, looks_secret, main


GIT_ENV = {
    "GIT_AUTHOR_NAME": "tong-git-test",
    "GIT_AUTHOR_EMAIL": "tong-git@test.local",
    "GIT_COMMITTER_NAME": "tong-git-test",
    "GIT_COMMITTER_EMAIL": "tong-git@test.local",
    "GIT_TERMINAL_PROMPT": "0",
}


def run_git(repo: Path, *args: str) -> None:
    env = os.environ.copy()
    env.update(GIT_ENV)
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


class TestClassify(unittest.TestCase):
    def test_hosts(self) -> None:
        self.assertEqual(classify_url("https://gitee.com/yibingzhi/tong-skills.git"), "gitee")
        self.assertEqual(classify_url("https://github.com/acme/repo.git"), "github")
        self.assertEqual(classify_url("https://cnb.cool/group/repo"), "cnb")
        self.assertEqual(classify_url("https://cnb.build/group/repo.git"), "cnb")
        self.assertEqual(classify_url("git@github.com:acme/repo.git"), "github")
        self.assertIsNone(classify_url("https://gitlab.com/acme/repo.git"))

    def test_home_is_forbidden(self) -> None:
        self.assertTrue(is_forbidden_root(Path.home()))
        self.assertFalse(is_forbidden_root(Path.home() / "Desktop" / "TongSkills"))

    def test_secrets(self) -> None:
        self.assertTrue(looks_secret(".env"))
        self.assertTrue(looks_secret("secrets.local.env"))
        self.assertTrue(looks_secret("certs/id_rsa"))
        self.assertFalse(looks_secret("README.md"))

    def test_refuse_force_and_amend(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            main(["--force", "push"])
        self.assertIn("refuse", str(ctx.exception))
        with self.assertRaises(SystemExit) as ctx:
            main(["commit", "--amend", "-m", "x"])
        self.assertIn("refuse", str(ctx.exception))
        with self.assertRaises(SystemExit) as ctx:
            main(["config", "--list"])
        self.assertIn("config", str(ctx.exception))

    def test_commit_in_temp_repo(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tong-git-") as tmp:
            repo = Path(tmp)
            run_git(repo, "init", "-b", "master")
            (repo / "hello.txt").write_text("hi\n", encoding="utf-8")
            (repo / ".env").write_text("TOKEN=nope\n", encoding="utf-8")
            old = os.environ.copy()
            os.environ.update(GIT_ENV)
            try:
                code = main(["--repo", str(repo), "commit", "-m", "Add hello."])
            finally:
                os.environ.clear()
                os.environ.update(old)
            self.assertEqual(code, 0)
            self.assertTrue((repo / ".env").is_file())
            names = subprocess.check_output(
                ["git", "-C", str(repo), "show", "--pretty=", "--name-only", "HEAD"],
                text=True,
            )
            self.assertIn("hello.txt", names)
            self.assertNotIn(".env", names)

    def test_publish_refuses_dirty_without_message(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tong-git-") as tmp:
            repo = Path(tmp)
            run_git(repo, "init", "-b", "master")
            (repo / "hello.txt").write_text("hi\n", encoding="utf-8")
            run_git(repo, "add", "hello.txt")
            old = os.environ.copy()
            os.environ.update(GIT_ENV)
            try:
                run_git(repo, "commit", "-m", "seed")
                (repo / "hello.txt").write_text("there\n", encoding="utf-8")
                with self.assertRaises(SystemExit) as ctx:
                    main(["--repo", str(repo), "publish"])
            finally:
                os.environ.clear()
                os.environ.update(old)
            self.assertIn("dirty", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
