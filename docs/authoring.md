# Authoring a skill

Follow [Agent Skills](https://agentskills.io/specification). Cursor, Codex, Claude, and `npx skills` all consume this format.

The agent already knows general programming. A skill only adds **what it would not know**: your workflow, your renderer, your taste, your forbidden paths.

## Directory

```text
skills/my-skill/
├── SKILL.md                 # required
├── scripts/                 # optional executables
├── references/              # optional, loaded on demand
├── assets/                  # optional static files
├── agents/
│   └── openai.yaml          # optional ChatGPT / Codex adapter
└── tests/                   # optional; excluded from the zip
```

`SKILL.md` `name` must match the folder. Lowercase, digits, single hyphens. Max 64 characters. No leading/trailing hyphen, no `--`.

Public skills in this repo: `tong-<job>`. Examples: `tong-chart`. Not `tongchart`, not a bare `chart`.

## Frontmatter

```yaml
---
name: my-skill
description: >-
  Does X. Use when the user mentions A, B, or C.
license: MIT
compatibility: Requires Python 3.10+ and ffmpeg.   # omit if nothing special
metadata:
  version: "0.1"
  author: TongSkills
---
```

| Field | Required | Notes |
|---|---|---|
| `name` | yes | == directory name |
| `description` | yes | 1–1024 chars. Third person. **What** + **when**. Include Chinese trigger terms if the audience is Chinese. |
| `license` | yes in this repo | `MIT` |
| `compatibility` | if the runtime is unusual | packages, OS, network |
| `metadata.version` | yes in this repo | bump when the agent contract changes |
| `metadata.author` | yes in this repo | `TongSkills` |

Do not put `disable-model-invocation: true` on published skills. Users install them so agents will auto-trigger.

### Description

Bad: `Helps with diagrams.`

Good: `Create polished Mermaid diagrams and render PNG/SVG. Use for 流程图、架构图, tong-chart, or mermaid 出图.`

## Body (SKILL.md)

Progressive disclosure:

1. Startup: only `name` + `description` (~100 tokens, every skill)
2. Activation: the whole SKILL.md body (keep < 500 lines, aim < 5000 tokens)
3. On demand: `references/`, `scripts/`, `assets/`

Write like a runbook:

- Default path first, then an escape hatch
- Concrete commands the agent can run, with `<skill-dir>` not a machine-specific home path
- Forward slashes in paths
- Link references one level deep: `[styles](references/styles.md)`
- Scripts: say **run** vs **read**

Do not explain what Mermaid is. Do not list five libraries. Pick one default.

### Scripts vs prose

If a step is fragile (render, zip, hash, pixel check), put it in `scripts/` and tell the agent to run it. Do not regenerate that code in the conversation.

Scripts must:

- Work on macOS, Windows, and Linux unless `compatibility` says otherwise
- Print errors that tell the agent what to fix
- Take paths as arguments; do not hardcode `/Users/...`

### Tests

Put unittest (or equivalent) under `tests/`. `validate_skills.py` discovers them. They are **not** in the upload zip.

### `agents/openai.yaml`

Only for ChatGPT / Codex / SkillHub zip upload. Not needed for `npx skills`. Keep `allow_implicit_invocation: true` unless the skill is dangerous.

## Definition of done

- [ ] `name` == folder == catalog entry
- [ ] description has what + when + trigger words
- [ ] SKILL.md < 500 lines
- [ ] no secrets
- [ ] `python scripts/validate_skills.py` exits 0
- [ ] README catalog row exists
- [ ] if scripts: at least one test, or an explicit reason in the PR/commit
- [ ] version bumped if this was an edit to a published skill
