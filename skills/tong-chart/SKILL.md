---
name: tong-chart
description: >-
  Create polished Mermaid diagrams and render them as validated PNG or SVG files
  for documents and Feishu. Use for 流程图、架构图、系统图、时序图、状态图、泳道图、类图、ER 图、
  思维导图、时间线、甘特图、GitGraph、用户旅程图、饼图、象限图、原生架构图、方块图、看板图、
  桑基图、XY 图或其他 Mermaid 文档配图。Triggers include tong-chart, tongchart, flowchart, mermaid 出图.
license: MIT
compatibility: Requires Python 3.10+, Node.js, @mermaid-js/mermaid-cli, and Chrome/Chromium/Edge. Works on macOS, Windows, and Linux.
metadata:
  version: "3.1"
  author: TongSkills
---

# Tong Chart

Create real Mermaid diagrams. Do not use image-generation tools for diagram text or connectors.

**Platforms: macOS, Windows, and Linux.** Same `SKILL.md` + `scripts/render_mermaid.py`. Do not write OS-specific agent steps, `.cmd` wrappers, or `~/.cursor/skills/flowchart` paths.

**Always render locally.** The Python script finds `node`/`node.exe` and mermaid-cli `cli.js` (global npm or npx cache), then Chromium/Chrome/Edge. Do not call `npx`, `mmdc.cmd`, mermaid.ink, or Kroki unless the user asks.

One invocation everywhere (forward slashes are fine on Windows):

```bash
python3 "<skill-dir>/scripts/render_mermaid.py" path/to/diagram.mmd --theme cursor
```

If `python3` is missing, use `py -3` with the same arguments. `<skill-dir>` is the folder that contains this `SKILL.md`.

Install once per machine:

- Python 3.10+
- Node.js
- `npm i -g @mermaid-js/mermaid-cli`
- Chrome, Edge, or Chromium (Linux: `google-chrome` or `chromium`)

Fonts are listed as PingFang (macOS), Segoe UI / 微软雅黑 (Windows), Noto Sans SC (Linux). The renderer picks whatever is installed.

Default style is **cursor** (white paper). The user can pick another named style or a hex accent; do not force Aurora.

## Styles and colors

If the user names a look, map it:

| 用户说法 | 参数 |
|---|---|
| 默认 / Cursor / 干净 / 文档 | `--theme cursor` |
| 深色 / 暗色 / 石墨 | `--theme dark` |
| 青绿 / 海洋 | `--theme ocean` |
| 绿色 / 森林 | `--theme forest` |
| 花一点 / 封面 / 极光 | `--theme aurora` |
| 更克制纸感 | `--theme docs` |
| 几乎单色 | `--theme minimal` |
| 只要这个色 `#RRGGBB` | `--theme cursor --accent #RRGGBB` |
| 还要改底色 | `--canvas #RRGGBB` |

Do not interrogate for a palette on every request. Use `cursor` unless they specify.

All diagram kinds below use the same `--theme` / `--accent` / `--canvas`. Flowcharts also get semantic `classDef`s; sequence, ER, pie, gantt, mindmap 等走同一套 `themeVariables`.

## Workflow

1. Identify the diagram kind.
   - Process or branching logic: `flowchart TD`
   - Layered architecture or data flow: `flowchart LR` with shallow subgraphs
   - Interactions over time: `sequenceDiagram`
   - Lifecycle and transitions: `stateDiagram`
   - Classes, interfaces, and inheritance: `classDiagram`
   - Entities, tables, and cardinality: `erDiagram`
   - Topic or knowledge hierarchy: `mindmap`
   - Dated events without task dependencies: `timeline`
   - Work with duration, dependencies, or milestones: `gantt`
   - Branches, commits, and merges: `gitGraph`
   - Touchpoints and experience scores: `journey`
   - A small part-to-whole dataset: `pie`
   - Two-axis positioning or prioritization: `quadrantChart`
   - Cloud, deployment, or CI/CD services and resources: `architecture-beta`
   - Explicit grid placement or nested system blocks: `block`
   - Work items grouped by current stage: `kanban`
   - Quantified flow between sources and destinations: `sankey`
   - Bar or line series over categories or a numeric range: `xychart`
2. Compose for the Cursor look, not for decoration.
   - One idea per node; 2–8 Chinese characters.
   - Happy path vertical and obvious; exception branches short and shallow.
   - **No full-height loop-back edges.** End rework at a terminal such as `修改后重新提交`.
   - At most **two** `accent` nodes. Everything else stays `process`.
   - Split above ~8–10 nodes or when edges cross.
   - Put SQL, class names, and IDs in surrounding prose, not inside nodes.
3. Use English IDs and quote Chinese labels, for example `SAVE["保存结果"]`.
4. For flowcharts, apply semantic classes when useful:
   - `startEnd`: start or end
   - `process`: normal step
   - `accent`: one or two central steps
   - `decision`: branch or gate
   - `store`: database or persisted result
   - `external`: third-party or external system
5. Write UTF-8 `.mmd` source without a hand-written theme directive unless the user supplied custom Mermaid configuration.
6. Render with the bundled script.

```bash
python3 "<skill-dir>/scripts/render_mermaid.py" path/to/diagram.mmd --theme cursor
python3 "<skill-dir>/scripts/render_mermaid.py" path/to/diagram.mmd --theme dark
python3 "<skill-dir>/scripts/render_mermaid.py" path/to/diagram.mmd --theme ocean --accent "#0E7490"
```

7. After the **first** PNG in a session, `Read` it once. Fix crowding, clipped labels, missing CJK glyphs, or wrap-around arrows, then re-render. Do not batch-`Read` every PNG.
   - Renderer `WARNING` lines are a required fix-or-explain gate.
8. Return absolute paths for the PNG and `.mmd`; include SVG when generated. Do not paste a large Mermaid block unless requested.

## Renderer options

- `--engine local|auto|mermaid.ink|kroki`: default `local`. `auto` is local-only. Remote engines only when requested.
- `--theme cursor|dark|ocean|forest|aurora|docs|neutral|minimal`
- `--accent #RRGGBB`: recolor the highlight (flowchart accent, pie/git/task)
- `--canvas #RRGGBB`: solid background override
- `--preset auto|<name>`: `process`, `architecture`, `architecture-native`, `block`, `kanban`, `sankey`, `xychart`, `sequence`, `state`, `class`, `er`, `mindmap`, `timeline`, `gantt`, `gitgraph`, `journey`, `pie`, `quadrant`, `generic`
- `--look auto|neo|classic`: `auto` uses classic for cursor/dark/ocean/forest
- `--svg`: also write SVG
- `--no-theme` / `--no-classdef` / `--dump-source`

## Output location

Use the user's path when given. Otherwise use:

`tmp/tong-chart/<slug>-<yyyymmdd-HHMMSS>.{mmd,png}`

## Quality gate

- The diagram kind and direction match the information.
- Labels are concise and contain no secrets.
- Decisions have labeled exits; there are no orphan nodes.
- Architecture reads left to right and avoids crossing edges.
- Default export is `THEME cursor`, `ENGINE local`, white paper, readable CJK.
- Named styles and `--accent` match what the user asked for.
- Layout `WARNING`s have been fixed or explained.
- First PNG in the session was inspected; a clean re-render is the deliverable.

Read [references/styles.md](references/styles.md) when choosing shapes, classes, or layout details. Read [references/examples.md](references/examples.md) when drafting a new diagram or troubleshooting a crowded one.

## Upload package

Publish to SkillHub / Codex / OpenAI skills as a zip with **exactly** these paths (no `tests/`, no `tmp/`):

```text
SKILL.md
agents/openai.yaml
scripts/render_mermaid.py
references/styles.md
references/examples.md
```

From the TongSkills repo root: `python scripts/pack_skill.py tong-chart` (writes `dist/tong-chart-v3.1.zip`).
