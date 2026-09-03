# TongSkills

This repo is skill material. Each folder under `skills/` is one installable Agent Skill. Agents add and edit skills; humans decide what to ship.

Read this before adding or editing a skill. Details: [docs/authoring.md](docs/authoring.md). Release: [docs/publishing.md](docs/publishing.md).

## Layout

```text
skills/<name>/           # the only installable skills
  SKILL.md               # required; `name` == directory
  scripts/               # optional; the agent RUNS these
  references/            # optional; the agent READS on demand
  assets/                # optional; templates, images
  agents/openai.yaml     # optional; ChatGPT / Codex zip upload
  tests/                 # optional; never packed
templates/               # scaffolds; must NOT contain SKILL.md
scripts/                 # repo tooling
docs/                    # how to write and pack skills
dist/                    # generated zips (gitignored)
catalog.yaml             # source of truth for the skill list
```

Do **not** put `SKILL.md` at the repo root (Skills CLI would treat the repo as one skill and skip `skills/`). Do **not** put `SKILL.md` under `templates/` or `docs/`.

Keep `skills/` **flat**: `skills/tong-chart/SKILL.md`. Never `skills/diagrams/tong-chart/` — the Agent Skills spec requires `name` == parent folder.

Public skill ids are `tong-<job>` (hyphen required): `tong-chart`, not `tongchart`, not `chart`.

## Two audiences (never mix)

| Path | Reader | Budget |
|---|---|---|
| `skills/*/SKILL.md` | coding agents at task time | < 500 lines, procedural |
| `skills/*/references/` | agents when a step needs detail | on demand |
| `README.md` | humans installing the repo | catalog + install only |

A skill is a **procedure**. Do not pad `SKILL.md` with marketing copy.

## Add a skill

1. `python scripts/new_skill.py <name>`
2. Fill `skills/<name>/SKILL.md` using [docs/authoring.md](docs/authoring.md)
3. Keep `catalog.yaml` and the README catalog table in sync (the scaffold already appends a stub)
4. If there is a script, add `tests/`
5. `python scripts/test_skills.py` (same as `validate_skills.py`; no install)
6. `python scripts/pack_skill.py <name>` only when uploading a zip

One directory = one job. New public skills must be named `tong-<job>`.

## Edit a skill

- Change agent behavior in that skill's `SKILL.md` / `scripts/` / `references/`, not in README.
- Bump `metadata.version` when the agent-facing contract changes (workflow, flags, outputs).
- Keep `compatibility` aligned with real runtime needs.
- Re-run validate. Pack only if publishing.

## Do not

- Invent a second layout (`.cursor/skills/` in this repo, `src/`, nested categories)
- Put secrets, tokens, internal hostnames, or private credentials in any skill
- Use Windows backslash paths in `SKILL.md`
- Duplicate a long spec in `SKILL.md`; link one level deep to `references/`
- Tell the agent to `npx skills` at runtime (that is install-time)
- Commit `dist/`, `__pycache__/`, or render `tmp/`

## Commands

```bash
python scripts/new_skill.py tong-name
python scripts/test_skills.py
python scripts/test_skills.py tong-git
python scripts/run_skill.py tong-cover --list
python scripts/pack_skill.py tong-chart
```
