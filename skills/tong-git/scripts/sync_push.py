#!/usr/bin/env python3
"""Project-repo git flow: status, commit (only when asked), push to Gitee/GitHub/CNB."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


HOSTS = {
    "gitee": ("gitee.com",),
    "github": ("github.com",),
    "cnb": ("cnb.cool", "cnb.build"),
}

FORBIDDEN_FLAGS = (
    "--force",
    "-f",
    "--force-with-lease",
    "--mirror",
    "--delete",
    "--amend",
    "--no-verify",
    "--no-gpg-sign",
)

SECRET_NAMES = {
    ".env",
    ".netrc",
    "credentials.json",
    "secrets.local.env",
    "secrets.env",
}


def classify_url(url: str) -> str | None:
    raw = url.strip()
    if not raw:
        return None
    if raw.startswith("git@"):
        host = raw.split(":", 1)[0].split("@", 1)[-1].lower()
    else:
        parsed = urlparse(raw if "://" in raw else "ssh://" + raw)
        host = (parsed.hostname or "").lower()
    for name, hosts in HOSTS.items():
        if host in hosts:
            return name
    return None


def is_forbidden_root(toplevel: Path) -> bool:
    try:
        return toplevel.resolve() == Path.home().resolve()
    except OSError:
        return False


def looks_secret(path: str) -> bool:
    name = Path(path.replace("\\", "/")).name.lower()
    if name in SECRET_NAMES or name.startswith(".env."):
        return True
    if name.endswith((".pem", ".p12", ".key")):
        return True
    if "id_rsa" in name or name.endswith("_rsa"):
        return True
    return False


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def require_repo(repo: Path) -> Path:
    result = git(repo, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f"not a git repo: {repo}")
    toplevel = Path(result.stdout.strip())
    if is_forbidden_root(toplevel):
        raise SystemExit(
            f"refuse: git toplevel is home directory ({toplevel}). "
            "Init a project repo first."
        )
    return toplevel


def list_remotes(repo: Path) -> list[tuple[str, str, str | None]]:
    result = git(repo, "remote", "-v")
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "git remote failed")
    seen: dict[str, str] = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name, url = parts[0], parts[1]
        if name not in seen:
            seen[name] = url
    return [(name, url, classify_url(url)) for name, url in seen.items()]


def current_branch(repo: Path) -> str:
    result = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "cannot read HEAD")
    branch = result.stdout.strip()
    if not branch or branch == "HEAD":
        raise SystemExit("detached HEAD; checkout a branch first")
    return branch


def porcelain(repo: Path) -> list[str]:
    result = git(repo, "status", "--porcelain")
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "git status failed")
    return [line for line in result.stdout.splitlines() if line.strip()]


def untracked_files(repo: Path) -> list[str]:
    result = git(repo, "ls-files", "--others", "--exclude-standard")
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "git ls-files failed")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def print_status(repo: Path) -> int:
    branch = current_branch(repo)
    dirty = porcelain(repo)
    remotes = list_remotes(repo)
    print(f"repo: {repo}")
    print(f"branch: {branch}")
    print(f"dirty: {'yes' if dirty else 'no'}")
    for line in dirty[:40]:
        print(f"  {line}")
    if len(dirty) > 40:
        print(f"  ... {len(dirty) - 40} more")
    found: set[str] = set()
    if not remotes:
        print("remotes: (none)")
    for name, url, host in remotes:
        label = host or "other"
        print(f"  {name:12} {label:8} {url}")
        if host:
            found.add(host)
    missing = [name for name in HOSTS if name not in found]
    if missing:
        print("missing hosts: " + ", ".join(missing))
        return 2
    print("hosts: gitee, github, cnb")
    return 0


def add_remote(repo: Path, name: str, url: str) -> None:
    host = classify_url(url)
    if host is None:
        raise SystemExit(f"url is not gitee/github/cnb: {url}")
    existing = {item[0]: item for item in list_remotes(repo)}
    if name in existing:
        raise SystemExit(f"remote already exists: {name} -> {existing[name][1]}")
    for other_name, other_url, other_host in existing.values():
        if other_host == host:
            raise SystemExit(
                f"{host} already mapped as {other_name} ({other_url}). "
                "Do not add a duplicate."
            )
    result = git(repo, "remote", "add", name, url)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "git remote add failed")
    print(f"added {name} ({host}) {url}")


def stage_worktree(repo: Path) -> list[str]:
    skipped: list[str] = []
    tracked = git(repo, "add", "-u", "--")
    if tracked.returncode != 0:
        raise SystemExit(tracked.stderr.strip() or "git add -u failed")
    for rel in untracked_files(repo):
        if looks_secret(rel):
            skipped.append(rel)
            continue
        added = git(repo, "add", "--", rel)
        if added.returncode != 0:
            raise SystemExit(added.stderr.strip() or f"git add failed: {rel}")
    if skipped:
        print("skipped secrets:")
        for rel in skipped:
            print(f"  {rel}")
    return skipped


def commit_worktree(repo: Path, message: str) -> int:
    message = message.strip()
    if not message:
        raise SystemExit("commit message is empty")
    if porcelain(repo):
        stage_worktree(repo)
    staged = git(repo, "diff", "--cached", "--name-only")
    names = [line.strip() for line in staged.stdout.splitlines() if line.strip()]
    if not names:
        raise SystemExit("nothing to commit")
    for name in names:
        if looks_secret(name):
            raise SystemExit(f"refuse to commit secret path: {name}")
    result = git(repo, "commit", "-m", message)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "git commit failed")
    print(f"committed {len(names)} file(s)")
    return 0


def push_all(repo: Path, dry_run: bool) -> int:
    branch = current_branch(repo)
    remotes = list_remotes(repo)
    targets = [(name, url, host) for name, url, host in remotes if host]
    if not targets:
        raise SystemExit("no gitee/github/cnb remotes. Add them first.")
    status = 0
    for name, url, host in targets:
        print(f"{'dry-run' if dry_run else 'push'} {name} ({host}) {branch} -> {url}")
        if dry_run:
            continue
        result = git(repo, "push", name, branch)
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        if result.returncode != 0:
            status = 1
            print(f"FAILED {name}", file=sys.stderr)
        else:
            print(f"OK {name}")
    return status


def publish(repo: Path, message: str | None, dry_run: bool) -> int:
    dirty = bool(porcelain(repo))
    print_status(repo)
    if dirty and not message:
        raise SystemExit(
            "dirty working tree. Pass --message only if the user asked to commit, "
            "otherwise commit nothing and do not push."
        )
    if dirty and message:
        if dry_run:
            print(f"dry-run commit: {message}")
        else:
            commit_worktree(repo, message)
    elif message and not dirty:
        print("working tree clean; skip commit")
    return push_all(repo, dry_run=dry_run)


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    extra = [a for a in argv if a in FORBIDDEN_FLAGS]
    if extra:
        raise SystemExit(f"refuse: {extra} is not allowed")
    if "config" in argv:
        raise SystemExit("refuse: git config is not allowed")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=".",
        help="git work tree (default: current directory)",
    )
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("status", help="repo, branch, dirty files, remotes")
    commit_p = sub.add_parser("commit", help="stage and commit; never amend")
    commit_p.add_argument("-m", "--message", required=True)
    push_p = sub.add_parser("push", help="push current branch to known hosts")
    push_p.add_argument("--dry-run", action="store_true")
    pub_p = sub.add_parser("publish", help="status, optional commit, then push")
    pub_p.add_argument("-m", "--message", default="")
    pub_p.add_argument("--dry-run", action="store_true")
    add_p = sub.add_parser("add", help="git remote add for one host URL")
    add_p.add_argument("name", choices=sorted(HOSTS))
    add_p.add_argument("url")
    args = parser.parse_args(argv)

    repo = require_repo(Path(args.repo).resolve())
    cmd = args.cmd or "status"
    if cmd == "status":
        return print_status(repo)
    if cmd == "commit":
        return commit_worktree(repo, args.message)
    if cmd == "push":
        return push_all(repo, dry_run=args.dry_run)
    if cmd == "publish":
        return publish(repo, args.message or None, dry_run=args.dry_run)
    if cmd == "add":
        add_remote(repo, args.name, args.url)
        return 0
    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
