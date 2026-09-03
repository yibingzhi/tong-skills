---
name: tong-git
description: >-
  Project-repo git flow: status, commit only when asked, then push the same
  branch to Gitee, GitHub, and CNB. Use when the user asks to 提交, 推送, 发布,
  同步远程, 多平台, git管理, gitee, github, cnb, cnb.cool, or tong-git.
license: MIT
compatibility: Requires git on PATH. Works on macOS, Windows, and Linux.
metadata:
  version: "0.2"
  author: TongSkills
---

# Tong Git

Publish loop for **one project repo**: status → commit (only if asked) → push Gitee / GitHub / CNB.

Not a git encyclopedia. No rebase, stash, cherry-pick, or `git config`.

**Do not** force-push, `--amend`, skip hooks, or run when the git toplevel is the user home directory.

## Workflow

Copy this checklist. `<skill-dir>` is the folder that contains this `SKILL.md`. If `python3` is missing, use `py -3`.

```bash
python3 "<skill-dir>/scripts/sync_push.py" --repo . status
```

1. **Always status first.** Confirm `repo:` is the project, not `~`. If the script refuses home, stop.
2. **Commit only when the user asked** (提交 / commit / 发布并提交). Draft a 1–2 sentence message, then:

```bash
python3 "<skill-dir>/scripts/sync_push.py" --repo . commit -m "Message here."
```

If they did not ask to commit, do not pass `-m`, do not `git commit`.
3. **Missing remotes.** Ask for the clone URL. Do not invent GitHub/CNB addresses. `origin` on gitee.com already counts as gitee.

```bash
python3 "<skill-dir>/scripts/sync_push.py" --repo . add github https://github.com/USER/REPO.git
python3 "<skill-dir>/scripts/sync_push.py" --repo . add cnb https://cnb.cool/GROUP/REPO
python3 "<skill-dir>/scripts/sync_push.py" --repo . add gitee https://gitee.com/USER/REPO.git
```

4. **Push** when they asked 推 / 同步 / 发布:

```bash
python3 "<skill-dir>/scripts/sync_push.py" --repo . push
```

5. **One-shot publish** (status + optional commit + push) only if they asked to发布/同步三家. Pass `--message` only when they also asked to commit:

```bash
python3 "<skill-dir>/scripts/sync_push.py" --repo . publish
python3 "<skill-dir>/scripts/sync_push.py" --repo . publish -m "Message here."
```

Preview: `--dry-run` on `push` or `publish`.

6. Return OK/FAILED per remote. Do not retry with `--force`.

## Dirty tree + 推 only

If status is dirty and the user only said 推: show status and **stop**. Do not auto-commit.

## Host notes

| Host | URL | Notes |
|---|---|---|
| Gitee | `https://gitee.com/owner/repo.git` | This TongSkills repo already uses `origin` here |
| GitHub | `https://github.com/owner/repo.git` | Needed for `npx skills add owner/repo` and skills.sh |
| CNB | `https://cnb.cool/group/repo` | HTTPS only (no SSH). Git username is `cnb`; use an access token |

CNB also accepts a `.git` suffix. `cnb.build` is treated as CNB.

## Refuse

- `git push --force` / `-f` / `--force-with-lease` / `--mirror`
- `git commit --amend` / `--no-verify`
- `git config`
- Detached HEAD
- Git toplevel `==` home directory
- Inventing GitHub/CNB URLs
- Staging `.env`, `credentials.json`, `*.pem`, `id_rsa`

## Quality gate

- Status ran in the project repo
- Commit happened only if the user asked
- Every classified remote got a push attempt when pushing
- Failures quoted; no silent force retry
