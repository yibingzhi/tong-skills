# Visual and layout reference

## Default visual system

Use the **cursor** theme by default. Other named styles: `dark`, `ocean`, `forest`, `aurora`, `docs`, `minimal`, `neutral`. `--accent #RRGGBB` retints the highlight; `--canvas #RRGGBB` replaces the page color.

Prefer local mermaid-cli so the machine's CJK font is used: PingFang on macOS, 微软雅黑 on Windows, Noto Sans SC on Linux.

| Role | Shape | Class | Meaning |
|---|---|---|---|
| Start or end | `(["开始"])` | `startEnd` | Entry or terminal state |
| Process | `["处理步骤"]` | `process` | Action or transformation |
| Accent | `["核心步骤"]` | `accent` | One or two central steps only |
| Decision | `{"条件？"}` | `decision` | Branch or validation gate |
| Store | `[("结果表")]` | `store` | Database or persisted output |
| External | `[["外部系统"]]` | `external` | Third-party or remote system |

Apply classes only to flowcharts. The renderer injects their definitions automatically unless custom definitions already exist.

Use `accent` sparingly. If more than two nodes need it, the diagram lacks a clear hierarchy; return most of them to `process`.

## Layout presets

### Process

- Prefer `flowchart TD`.
- Use LR only when the process has a short, naturally staged left-to-right story and will not trigger a width warning.
- Keep the happy path vertical and centered.
- Put retries, failures, and manual handling on short side branches.
- Label decision edges with short outcomes such as `是/否` or `通过/拒绝`.
- When three or more rejection branches converge, end them at `修改后重新提交`. Do not draw a return edge around the full diagram; show the retry cycle in a separate detail only when it matters.

### Architecture

- Prefer `flowchart LR` with subgraphs representing layers or ownership boundaries.
- Arrange subgraphs in data-flow order, such as client → service → data.
- Keep subgraph titles short and avoid nested subgraphs deeper than two levels.
- Use one edge per meaningful dependency; omit incidental implementation calls.
- Avoid a dense service-to-store mesh. At overview level, group shared persistence behind a data-access boundary or show only ownership-critical dependencies.

### Sequence

- Declare participants in reading order before messages.
- Use solid arrows for calls and dashed arrows for responses.
- Use `alt`, `opt`, and `loop` only when they clarify behavior.
- Avoid more than six participants in one view; split by scenario when necessary.

### State

- Name states as conditions, not actions.
- Label transitions with events or guards.
- Use composite states only when they remove repeated transitions.
- Keep start and terminal states visually obvious.

### Class

- Prefer an overview of responsibilities and relationships over a dump of every field and method.
- Keep each class to the few members that explain the design; omit accessors and framework boilerplate.
- Use inheritance only for a real is-a relationship and label associations when their meaning is not obvious.
- Split diagrams above roughly eight classes or when inheritance and runtime dependencies become tangled.

### Entity relationship

- Prefer `direction LR` for a compact overview; use TB when the domain is naturally hierarchical.
- Use singular entity names and show only keys plus relationship-critical attributes in overview diagrams.
- Verify every cardinality; a visually polished wrong cardinality is still a wrong diagram.
- Arrange entities around the main transaction or aggregate instead of producing a table-to-table mesh.
- Split by bounded context when the view exceeds roughly eight entities.

### Mindmap

- Put one clear subject at the root and keep sibling labels grammatically parallel.
- Prefer two to four main branches and no more than three visible levels.
- Use short noun phrases; move explanations into surrounding prose.
- Do not encode process order with a mindmap when arrows or dates carry meaning.

### Timeline

- Use one consistent date or period granularity.
- Keep entries chronological and limit each period to one or two short events.
- Use a Gantt chart instead when duration, overlap, or dependency is the point.

### Gantt

- Group tasks into a few meaningful sections and expose only decision-relevant dependencies.
- Use `milestone`, `crit`, `active`, and `done` semantically, not decoratively.
- Prefer a planning horizon that remains readable on one page; split long programs by phase.
- Never invent dates or durations. Ask for missing scheduling facts or clearly mark assumptions outside the diagram.

### GitGraph

- Keep branch names short and show only commits needed to explain the release or integration story.
- Use concise commit labels and avoid reconstructing a full repository history.
- Prefer `main` as the primary branch unless the source explicitly uses another name.

### User journey

- Organize steps into stages and keep the actor list stable across the journey.
- Use scores consistently on the same scale; do not infer sentiment from text without saying so.
- Keep the journey focused on one persona and one goal.

### Pie

- Use only for a part-to-whole relationship with non-negative values.
- Prefer two to six slices; combine immaterial categories into “其他” only when the user approves the aggregation.
- Sort or order slices intentionally and use short labels; include values when they aid comparison.
- Switch to a bar chart outside this skill when precise comparison matters more than composition.

### Quadrant

- State both axis directions explicitly and keep all coordinates between `0` and `1`.
- Keep point labels short and avoid placing many points at nearly identical coordinates.
- Use a restrained number of points—roughly three to ten—for a readable decision view.
- Treat coordinates as supplied judgments or data; never present invented precision as measured fact.

### Native architecture

- Use `architecture-beta` for cloud, deployment, CI/CD, or resource topology where groups and connection sides matter.
- Use short service IDs and labels; declare groups and services before edges.
- Quote Chinese or multi-word architecture labels inside brackets.
- Use Mermaid's built-in `internet`, `cloud`, `server`, `database`, or `disk` icons; do not assume an external pack is registered.
- Keep group nesting shallow and use junctions only when they materially simplify routing.
- Continue using flowchart architecture for ordinary application-layer overviews that do not need native resource semantics.

### Block

- Declare `columns` intentionally; Block is for controlled placement, not automatic process layout.
- Keep composite blocks to at most two levels and use `space` sparingly.
- Use block arrows when direction is part of the layout and ordinary edges when relationships are the point.
- Avoid manually recreating a dense free-form canvas with dozens of invisible spacer blocks.

### Kanban

- Use three to six columns with short stage names and roughly eight cards or fewer per column.
- Keep card text action-oriented and assign one owner only when ownership matters.
- Use priority metadata semantically; do not mark every item High.
- Kanban is a snapshot of state. Use Gantt for schedule dependencies and flowchart for transition logic.

### Sankey

- Each row is `source,target,value`; quote names containing commas.
- Use concise ASCII node labels for compatibility with the current remote Mermaid Sankey renderers; explain their Chinese meaning in surrounding prose when needed.
- Values must be finite and positive. Preserve the user's units and do not invent balancing flows.
- Keep intermediate nodes meaningful and avoid dense all-to-all links.
- Split unrelated flow systems instead of forcing them into one Sankey canvas.

### XY chart

- Use bars for discrete comparison and lines for ordered trends.
- Keep category labels short and series count low enough for colors to remain distinguishable.
- Start a bar-chart y axis at zero unless the user explicitly needs another truthful range.
- Do not imply a named legend when Mermaid source has no series-label syntax; explain series order in surrounding prose when needed.
- Use a spreadsheet/charting workflow when statistical analysis, stacked data, dual axes, or precise publication charts are required.

## Label rules

- Aim for 2–8 Chinese characters per flowchart node when possible.
- Use `<br/>` only for a deliberate two-line label.
- Keep identifiers out of labels unless the identifier is the subject of the diagram.
- Never place secrets, access tokens, personal data, or private URLs in diagram text sent to remote renderers.

## Split rules

Create an overview plus one or more detail diagrams when any condition holds:

- More than roughly 10 nodes
- More than three exception paths
- More than six sequence participants
- More than eight classes or ER entities
- More than three visible mindmap levels
- More than six pie slices or ten quadrant points
- More than six Kanban columns or roughly eight cards per column
- Sankey labels or links overlap after one simplification pass
- More than roughly twelve XY categories with long labels
- Crossings remain after one layout revision
- One diagram mixes business flow and deployment topology

## Common repairs

| Symptom | Repair |
|---|---|
| Very tall architecture | Switch to LR and group layers with subgraphs |
| Wide process with weak hierarchy | Switch to TD and center the happy path |
| Crossing connectors | Reorder declarations, remove incidental edges, or split the diagram |
| Full-height retry loop | End at `修改后重新提交` or move retry behavior to a detail diagram |
| Dense lines into data stores | Show ownership only or add a shared data-access boundary |
| Oversized nodes | Shorten labels and move detail into surrounding prose |
| Too many colors | Return to semantic role classes |
| Everything looks equally important | Keep most nodes as `process`; apply `accent` to at most two central steps |
| Blurry document image | Generate SVG in addition to PNG |
| Class or ER diagram becomes a wall of text | Keep relationship-critical members only and split by domain |
| Timeline hides task overlap | Replace it with a Gantt chart |
| Gantt labels consume the canvas | Shorten task names and split the planning horizon |
| Pie slices are hard to compare | Reduce categories or use a bar chart |
| Quadrant labels collide | Reduce points, shorten labels, or revise coordinates without changing their meaning |
| Native architecture shows missing icons | Replace external icon references with Mermaid's built-in architecture icons |
| Block layout has many empty cells | Reduce columns or replace spacer blocks with a simpler structure |
| Kanban is extremely wide | Merge adjacent stages or split by team/product |
| Sankey becomes a ribbon wall | Remove incidental flows or split by flow domain |
| XY labels overlap | Shorten categories, switch orientation, or reduce the visible time window |
