# TongSkills

Skill 素材库。格式遵循 [Agent Skills](https://agentskills.io/specification)，可用 Cursor、Codex、Claude，以及 `npx skills` 安装。

新 skill 按 [`AGENTS.md`](AGENTS.md) 加，不要往这个仓库塞无关内容。

## 现在有什么

| Skill | 做什么 |
|---|---|
| [tong-chart](skills/tong-chart/) | 本地 Mermaid 出图（流程 / 架构 / 时序 / 甘特等），多主题，macOS · Windows · Linux |

## 安装

仓库公开之后：

```bash
npx skills add <github-user>/TongSkills
npx skills add <github-user>/TongSkills --skill tong-chart
```

把 `<github-user>` 换成实际账号。装好后，直接说「画一张架构图」或「用 tong-chart 出图」即可。

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

```bash
python scripts/new_skill.py my-skill
python scripts/validate_skills.py
python scripts/pack_skill.py my-skill
```

`tong-chart` 自带单元测试：

```bash
python -m unittest discover -s skills/tong-chart/tests
```

## License

[MIT](LICENSE)
