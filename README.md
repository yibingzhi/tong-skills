# TongSkills

Skill 素材库。格式遵循 [Agent Skills](https://agentskills.io/specification)，可用 Cursor、Codex、Claude，以及 `npx skills` 安装。

新 skill 按 [`AGENTS.md`](AGENTS.md) 加，不要往这个仓库塞无关内容。

## 现在有什么

### ✍️ 深度写作流水线 (Writing Pipeline)

覆盖从“灵感催化”到“长文成稿、去AI味终审与标题矩阵”的工业级创作矩阵：

```text
[灵感困境/碎片] ──> tong-muse (灵感催化与素材拆解)
                         │
                         ▼
                   tong-writer (长文创作中枢)
                   (立意骨架 + 镜头开篇 + 正文展开 + 金句点睛)
                         │
                         ├────────────────────────┐
                         ▼                        ▼
                   tong-humanize              tong-title
                (去AI味扫描与主编终审)      (多平台爆款标题矩阵)
```

| Skill | 做什么 |
|---|---|
| [tong-muse](skills/tong-muse/) | 灵感催化与表达教练：苏格拉底追问 / 四层事实与冲突拆解 / 即时微课 |
| [tong-writer](skills/tong-writer/) | 长文写作中枢：3 切角立意与 8 段骨架 / 电影感冷开场 / 正文起草与金句点睛 |
| [tong-humanize](skills/tong-humanize/) | 去 AI 味与主编终审：扫描套话标点 / 九维负向剪枝 / 事实一票否决门禁 |
| [tong-title](skills/tong-title/) | 爆款标题矩阵工厂：四维心理模型切角探索与多平台终稿标题 |

### 🎨 视觉与媒介工坊 (Visual & Media)

| Skill | 做什么 |
|---|---|
| [tong-cover](skills/tong-cover/) | 本地 Pillow 封面 / 刊头 / 简报 / 金句卡 / 小红书多图轮播卡片组，按星期换色 |
| [tong-chart](skills/tong-chart/) | 本地 Mermaid 出图（流程 / 架构 / 时序 / 甘特等），多主题，macOS · Windows · Linux |
| [tong-prompt](skills/tong-prompt/) | 引导作者把想法写成可粘贴的图 / 视频提示词，先锁锚点再扫塑料词 |
| [tong-reverse](skills/tong-reverse/) | AI 视频与图像提示词逆向解构：图像文生图 (MJ/FLUX/SDXL) + 视频抽帧运镜 (可灵/Runway/海螺) |

### 🛠️ 研发与基础设施 (DevOps & Data)

| Skill | 做什么 |
|---|---|
| [tong-git](skills/tong-git/) | 项目仓状态 → 按需提交 → 推到 Gitee / GitHub / CNB |
| [tong-mysql-ro](skills/tong-mysql-ro/) | 只读 MySQL：SELECT / SHOW / DESCRIBE，强制 LIMIT，凭证本地填 |
| [tong-mysql-write](skills/tong-mysql-write/) | 写库 DML：默认预览，确认后 `--apply` 并落回滚 SQL；不做 DDL |

## 安装

```bash
npx skills add https://gitee.com/yibingzhi/tong-skills.git
npx skills add https://gitee.com/yibingzhi/tong-skills.git --skill tong-muse
npx skills add https://gitee.com/yibingzhi/tong-skills.git --skill tong-chart
npx skills add https://gitee.com/yibingzhi/tong-skills.git --skill tong-cover
npx skills add https://gitee.com/yibingzhi/tong-skills.git --skill tong-reverse
npx skills add https://gitee.com/yibingzhi/tong-skills.git --skill tong-git
npx skills add https://gitee.com/yibingzhi/tong-skills.git --skill tong-humanize
npx skills add https://gitee.com/yibingzhi/tong-skills.git --skill tong-writer
```

短名 `owner/repo` 只走 GitHub，Gitee 必须用完整 git URL。仓库需公开。

ChatGPT / Codex / SkillHub 需要 zip 时，从仓库根目录：

```bash
python scripts/pack_skill.py tong-chart
```

生成 `dist/tong-chart-v<version>.zip`，再在对应产品里上传。

## 这个仓库怎么长

```text
skills/<name>/     每个 skill 一个目录
templates/         新建 skill 的脚手架（不是 skill）
scripts/           校验 / 打包 / 脚手架
docs/              怎么写、怎么打包
playground/        本机网页测 skill，不装到系统
```

细节看 [`AGENTS.md`](AGENTS.md) 和 [`docs/authoring.md`](docs/authoring.md)。

## 开发

不用装到 `~/.cursor/skills`。对着仓库里的 `skills/` 测：

```bash
python scripts/test_skills.py
python scripts/test_skills.py tong-git
python scripts/run_skill.py tong-cover --list
python scripts/run_skill.py tong-git --repo . status
python playground/server.py
python scripts/new_skill.py tong-name
python scripts/pack_skill.py tong-cover
```

`test_skills.py` 会校验 `SKILL.md` 并跑每个 skill 的 `tests/`。`tong-cover` 的测试需要 Pillow：`pip install pillow`。

直接跑某个 skill 自带的脚本（第一个 `scripts/*.py`）用 `run_skill.py`，参数原样传下去。

本机网页（只绑 `127.0.0.1`，Key 留在浏览器里）：

```bash
python playground/server.py
```

打开 http://127.0.0.1:8765 。**默认是「跑脚本」**：选 skill，把 `--help` 里的参数填进表，点运行。预设只填表，不自动跑。默认禁止 commit/push；要测写操作再勾「允许写操作」。

「对话测 SKILL.md」才是可选的第二层：把 SKILL.md 当系统提示词丢给任意 OpenAI 兼容接口。DeepSeek 的深度思考在 `reasoning_content`，测页默认不打印（可勾「显示深度思考」）。日常验收仍以 `test_skills.py` + 跑脚本为准。

## License

[MIT](LICENSE)
