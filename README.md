# TongSkills

Skill 素材库。格式遵循 [Agent Skills](https://agentskills.io/specification)，可用 Cursor、Codex、Claude，以及 `npx skills` 安装。

新 skill 按 [`AGENTS.md`](AGENTS.md) 加，不要往这个仓库塞无关内容。

## 现在有什么

| Skill | 做什么 |
|---|---|
| [tong-chart](skills/tong-chart/) | 本地 Mermaid 出图（流程 / 架构 / 时序 / 甘特等），多主题，macOS · Windows · Linux |
| [tong-cover](skills/tong-cover/) | 本地 Pillow 封面 / 刊头 / 简报 / 金句卡，按星期换色 |
| [tong-git](skills/tong-git/) | 项目仓状态 → 按需提交 → 推到 Gitee / GitHub / CNB |

## 安装

```bash
npx skills add https://gitee.com/yibingzhi/tong-skills.git
npx skills add https://gitee.com/yibingzhi/tong-skills.git --skill tong-chart
npx skills add https://gitee.com/yibingzhi/tong-skills.git --skill tong-cover
npx skills add https://gitee.com/yibingzhi/tong-skills.git --skill tong-git
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
```

细节看 [`AGENTS.md`](AGENTS.md) 和 [`docs/authoring.md`](docs/authoring.md)。

## 开发

不用装到 `~/.cursor/skills`。对着仓库里的 `skills/` 测：

```bash
python scripts/test_skills.py
python scripts/test_skills.py tong-git
python scripts/run_skill.py tong-cover --list
python scripts/run_skill.py tong-git --repo . status
python scripts/new_skill.py tong-name
python scripts/pack_skill.py tong-cover
```

`test_skills.py` 会校验 `SKILL.md` 并跑每个 skill 的 `tests/`。`tong-cover` 的测试需要 Pillow：`pip install pillow`。

直接跑某个 skill 自带的脚本（第一个 `scripts/*.py`）用 `run_skill.py`，参数原样传下去。

## License

[MIT](LICENSE)
