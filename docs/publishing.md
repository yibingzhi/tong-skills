# Publishing

One skill tree. GitHub install and zip upload share the same `skills/<name>/`. Do not fork per platform.

## 1. Git + `npx skills` (default)

This is how most agents install skills. This repo is on Gitee, so the install source is the full git URL (GitHub shorthand would look up the wrong host).

1. Push this repo (public).
2. Anyone runs:

```bash
npx skills add https://gitee.com/yibingzhi/tong-skills.git
npx skills add https://gitee.com/yibingzhi/tong-skills.git --skill tong-chart
npx skills add https://gitee.com/yibingzhi/tong-skills.git --skill tong-cover
```

The CLI looks in `skills/` by default. That is why skills live there, not at the repo root.

After the public URL exists, put it in README and do not invent a second install path.

## 2. Zip for SkillHub / Codex / ChatGPT

From the repo root:

```bash
python scripts/validate_skills.py
python scripts/pack_skill.py tong-chart
```

Output: `dist/tong-chart-v<version>.zip`

The zip root is the skill root (`SKILL.md` at the top), never `skills/tong-chart/...`. Tests, `tmp/`, and this repo's tooling are excluded.

Upload that zip in the product UI. Do not zip the whole TongSkills repo.

## Version bump

Bump `metadata.version` in `SKILL.md` when you change:

- workflow steps the agent must follow
- script CLI flags or outputs
- default theme / engine / paths

Do not bump for README-only edits.

`pack_skill.py` reads the version from frontmatter. Do not hardcode it elsewhere (except a script's own `UA` string, which must match).
