---
name: tong-prompt
description: >-
  Turn an author's idea into a model-ready image or video prompt without
  swapping their intended look. Lock a 3-second recognizability anchor, ask
  at most one missing fork, paste a ready-to-copy prompt, then scan plastic
  style-stacks.
  Use when the user asks 提示词, 出图prompt, 即梦提示词, Midjourney, 可灵,
  视频提示词, 把想法写成提示词, or tong-prompt. Does not call image or video APIs.
license: MIT
compatibility: Requires Python 3.10+. Works on macOS, Windows, and Linux.
metadata:
  version: "0.2"
  author: TongSkills
---

# Tong Prompt

把作者的想法收成一份可粘贴的提示词。不换他想要的效果，不替他审美，不调用生图/生视频 API。

目标不是「更精品」，是三秒内能认出他要的那张图（或那段视频）。

**Platforms: macOS, Windows, and Linux.** Same `SKILL.md` + `scripts/scan.py`. Do not regenerate a scanner.

## Workflow

Copy this checklist. `<skill-dir>` is the folder that contains this `SKILL.md`. If `python3` is missing, use `py -3`.

1. **锁锚点。** 作者已经说清「三秒内必须认出什么」就照写，不要再问。写不出这一句，才问一句，例如：「这张图成功时，别人必须认出什么？」不要同时问画幅、画派、模型。

2. **缺效果才分叉。** 画派 / 动静会改画面、而且作者没说时，只问一个分叉，并带倾向。作者用自己的词回答；你负责填格子，不要把所有神兽都收成工笔壁纸。

| 用户说法 | `--lane` | `--look` |
|---|---|---|
| 图 / 插画 / 没说 | `image` | `auto` |
| 工笔 / 吴道子 / 绢本 | `image` | `gongbi` |
| 油画 / 厚涂 | `image` | `oil` |
| 电影静帧 / MV 封面 | `image` | `cine` |
| 信息图 / 示意图 | `image` | `info` |
| 视频 / 可灵 / 镜头怎么动 | `video` | `auto` 或上面同款 |

`--target` 默认 `generic`。用户要贴 Midjourney / 即梦 / 可灵再改 `mj` / `jimeng` / `kling`。

3. **压缩零件。** 只留能入画的：主体、必须看清的物种特征、动作、环境里最多两件、必须原样上屏的文字。出处里没有的符石、仙侠配件不要补。空间不够就拆第二张，不要一张塞满。布局见 [references/layouts.md](references/layouts.md)。

4. **先结构后材质。** 一种画派（作者要的那种），一道光。不要并列工笔 + 油画 + 超写实 + 3D。`auto` 且作者没点画派时，可以不写画派，只写能看见的东西。

5. **扫完直接交正文。** 提示词写进对话里给作者复制。扫描走 stdin，不要为了交稿去建 `tmp/` 文件。用户明确说「存文件 / 写入仓库」才落盘。

```bash
python3 "<skill-dir>/scripts/scan.py" - --lane image --target mj --look gongbi --anchor "毕方独足,burning pine,beak"
```

把下面这种正文喂给 stdin（没有分段的原文也能扫）。`--no` 行只在 `--target mj` 时合法。

```text
lane: image
target: mj
look: gongbi
anchor: 毕方独足, burning pine, flame from the open beak

prompt:
Bifang (毕方) from the Shan Hai Jing: a single-legged crimson fire-bird
perched on a burning ancient pine...

negative:
cartoon, 3d render, cute, disney, plastic, extra legs

params:
--ar 16:9 --stylize 250 --q 2 --v 6.0
```

`--list` 看栏目和检查项。输出分两档：

| 档 | 含义 | 你要做的 |
|---|---|---|
| `FAIL` | 硬伤（塑料堆叠、三种以上画法、锚点没写进 prompt、图里写了镜头运动） | 必须改，改到退出码 0 |
| `WARN` | 要人判（单个 8k、出处外的符石、未声明锚点、视频缺时长） | 逐条判：留就留，改就改。交稿时一句话说明 |

6. **再扫。** 改完必须再扫一遍，直到退出 0，或第 3 轮仍有 FAIL 则标 `[需复核]` 并停。
7. **交稿。** 只给可复制的 `prompt` / `negative` / `params` + 一句「这版按你选的〈效果〉」。不要报文件路径。用户没要质检表就不要再做一层报告。WARN 去留各写一句。

## 硬规则

1. **跑 bundled 脚本。** 不要手写另一份禁用词表来「代替扫描」。
2. **不换效果。** 作者要油画就走 `--look oil`，不要纠回工笔。默认口味只在完全没说时启用：克制、一种光、不堆渲染器名词。
3. **不发明。** 品牌、人脸、图上文字必须来自用户；中文要上图就整句写入。查不到的纹样、年号、出处细节不要编。
4. **不调 API。** 不调用 KIE / Midjourney / 即梦 / 可灵。本 skill 的交付物是对话里的提示词正文，不是仓库里的 txt。
5. **图和视频分开。** 一次输出只做 `--lane image` 或 `--lane video`。视频写时长、机位、首尾帧；静帧不要写「镜头缓缓」。

家规（不能入画的产品名、人脸）放本地，不放 skill：

```bash
python3 "<skill-dir>/scripts/scan.py" prompt.txt --lane image --rules ~/.tong/prompt-rules.txt
```

一行一条；`re:` 开头当正则；`#` 是注释。命中算 FAIL。

## 引导时怎么问

已经够用就出稿。缺的是效果，不是形容词。

- 认得出什么？比「要不要更精品」优先。
- 更像博物志插图、壁画、还是电影静帧？（只问尚未确定的那一个）
- 光是殿堂里的静，还是烟火里的一道光？

映射到格子：物种特征、动作、环境两件、一种画派、一道光、工具尾缀。对错看锚点在不在 prompt 里，不看像不像壁纸。

词表见 [references/banned-words.md](references/banned-words.md)。毕方类对照 [references/examples.md](references/examples.md)。

## Quality gate

- `scan.py` 对该 lane/target/look 退出 0，或已标明 `[需复核]`
- `--anchor` 里的词都出现在 prompt 正文（负向和 `--no` 不算）
- 每条 WARN 都有去留说明
- 交稿句能对上作者要的效果，没有被换成 skill 默认审美
- 没有调用生图/生视频接口
- 交稿是对话里的提示词，没有把 `tmp/` 路径当交付物
