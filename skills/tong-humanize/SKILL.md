---
name: tong-humanize
description: >-
  Rewrite Chinese or mixed text to remove AI writing tells: fake contrasts,
  filler transitions, stacked adverbs, empty jargon, WeChat punctuation.
  Use when the user asks 去AI味, 降AI味, 润色, 改写得更自然, 像人话, 口语化,
  humanize, 去塑料味, or tong-humanize.
license: MIT
compatibility: Requires Python 3.10+. Works on macOS, Windows, and Linux.
metadata:
  version: "0.2"
  author: TongSkills
---

# Tong Humanize

改「怎么说」，不改「说什么」。不换作者声音，不补原文没有的事实。

目标不是更华丽，是具体、可读、像这个人会说的话。无菌腔和套话一样假。

**Platforms: macOS, Windows, and Linux.** Same `SKILL.md` + `scripts/scan.py`. Do not regenerate a scanner.

## Workflow

Copy this checklist. `<skill-dir>` is the folder that contains this `SKILL.md`. If `python3` is missing, use `py -3`.

1. **定栏目。** 判断不了就问一句，别猜。

| 用户说法 | `--lane` |
|---|---|
| 去AI味 / 润色 / 没说栏目 | `general` |
| 公众号长文 / 主号 | `wechat` |
| 每日速览 / 简报 | `brief` |
| 小红书 / 小绿书 | `xhs` |

2. **先扫再改。** 把待改文本写成文件（用户已有文件就用原路径）：

```bash
python3 "<skill-dir>/scripts/scan.py" path/to/draft.md --lane general
```

`--list` 看栏目和检查项。输出分两档：

| 档 | 含义 | 你要做的 |
|---|---|---|
| `FAIL` | 硬伤（套话、喊话、堆叠副词、栏目标点、否定列举） | 必须改，改到退出码 0 |
| `WARN` | 要人判（单个「不是而是」、闭环 / 抓手 / 本质上、首先其次最后） | 逐条判：留就留，改就改。交稿时一句话说明 |

WARN 不是让你顺手删。「我爱上的不是容貌，而是你说话的方式」是好句子；「温控闭环」是术语。删了才是改坏。

3. **按档位改。** FAIL 当硬伤。没命中的句子尽量不动。

| 档位 | 怎么判 | 改多深 |
|---|---|---|
| 轻度 | 硬伤很少，结构还像人 | 只换词、拆套话 |
| 中度 | 套话 + 三毒 + 连接词成片 | 再去书面腔 |
| 重度 | 整段在演深刻 | 重写病灶段，其余仍少动 |

4. **再扫。** 同一文件改完必须再跑一遍，直到退出 0，或第 3 轮仍 ≥10 处 FAIL 则标 `[需复核]` 并停。
5. **交稿。** 正文 + 最后一次扫描原文 + 每条 WARN 的去留（一句话一条）。用户没要质检表就不要再做一层报告。

## 硬规则

1. **跑 bundled 脚本。** 不要手写另一份禁用词表来「代替扫描」。
2. **不新增事实。** 数字必须来自原文或用户；查不到的「某报告 / NASA 算了一笔账」直接删。原文只有空话没有数，就改成「具体数我这边没有」，不要照范例补一个「两天到四小时」。
3. **不换人。** `general` 只去塑料味，不灌口癖。用户明确要口语化 / 公众号口吻，才用更松的句子。
4. **不喊话收尾。** 「放话了 / 欢迎打脸 / 回来谢我 / 点个在看」整段删。说完就停。
5. **自嘲可以，吹牛不行。** 不写没跑过的「轻松搞定」「效率翻倍」。

## 「不是 A 而是 B」先判毒再修

脚本只报 WARN，判定归你。先归类：

| 毒 | 判定 | 修 |
|---|---|---|
| 假靶子 | 没人做过前半句那个判断 | 只留 B |
| 同义替换 | A 和 B 是同一件事 | 合成一句 |
| 硬凑 | 删掉脚手架意思不变 | 删 |
| 好用法 | 真有人会选 A，且 A ≠ B | 可留 |

NNY（「不是 X。不是 Y。只是 Z。」）是 FAIL，默认删前两句。修法细节见 [references/structures.md](references/structures.md)。

## 术语还是空话

`闭环 / 抓手 / 本质上 / 对齐 / 颗粒度` 报 WARN。判法一条：**把这个词删掉，句子还剩不剩具体内容？**

- 「温控闭环已经调稳，超调从 8% 收到 2%」删了「闭环」句子塌，是术语，留。
- 「赋能业务，形成增长闭环」删了什么都不剩，是空话。这种业务搭配脚本直接 FAIL。
- 「本质上这就是个缓存击穿」删掉「本质上」意思不变，删。

## 改的时候看这些

脚本扫硬伤。下面几条要人看：

- 心理告知改动作：「他很紧张」→「他的手在抖」。原文没有动作就删判断，不编动作。
- 莫名其妙的比喻（本体喻体对不上）→ 白描或删。
- 假精确数字（「跨了 49cm」）→ 删或改成正常说法。
- 自问自答老师腔（「这叫什么？这叫…」）→ 直接陈述。
- 「你以为 A 实际上 B」→ 只说 B。
- 连续排比留最强的 1–2 条。三段式列举改两项或四项，或改成「头一条 / 第二条」自然段。
- 结尾用具体动作或没说完的实话，不用「综上所述 / 未来可期」。
- 小说对照原设定，删私加的人设和刻板印象。

词表和替换见 [references/banned-words.md](references/banned-words.md)。栏目标点 / 表情 / 速览红线见 [references/channels.md](references/channels.md)。拿不准对照 [references/examples.md](references/examples.md)。

## 栏目差异

- `general`：套话、否定列举、堆叠副词。破折号每篇 ≤2。冒号和引号不禁。
- `wechat`：再加冒号 / 破折号 / 英文或弯引号清零。引用用「」。每段表情 ≤1–2，只放情绪高点。
- `brief`：冒号每篇 ≤2。读者是泛人群，专业黑话要解释或删。
- `xhs`：破折号和弯引号仍禁，冒号放开。

时间 `13:11` 和 `https://` 里的冒号不算。

## 家规放本地，不放 skill

每个号都有自己的红线：不能出现的产品名、不能暴露的作者身份、被毙过的收尾句。这些不写进 skill，写在一个本地文件里，扫描时传进去：

```bash
python3 "<skill-dir>/scripts/scan.py" draft.md --lane brief --rules ~/.tong/house-rules.txt
```

文件格式一行一条：普通文本按原文匹配；`re:` 开头当正则；`#` 是注释。命中算 FAIL。格式样例见 [references/channels.md](references/channels.md)。

用户提到「我们号的规矩」「上次被毙的」而没有给文件，问一句文件在哪，不要凭记忆把家规写死到改稿里。

## 终审（改完通读一遍）

- 读起来像这个作者在说话，不像在交作业。
- 每个硬观点旁边有原文里的人 / 场景 / 数字，没有就写轻一点，不编。
- 没有假引用、没有喊话 CTA、没有教程腔开头。

## Quality gate

- `scan.py` 对该栏目退出 0，或已标明 `[需复核]`
- 每条 WARN 都有去留说明，没有被顺手删掉的好对比句或术语
- 事实和数字能对上原文
- 没把职场稿改成网红口癖，也没把口语稿改回公文
