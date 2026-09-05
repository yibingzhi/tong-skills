---
name: tong-title
description: >-
  Generate headline matrices across 4 psychological models for WeChat, Xiaohongshu, and Zhihu. Use when the user asks for 起标题, 爆款标题, 标题矩阵, or tong-title.
license: MIT
metadata:
  version: "0.1"
  author: TongSkills
---

# Tong Title (爆款标题矩阵工厂)

标题必须独立产出，正文写手禁止“顺便想标题”。

本 Skill 在流水线中运行两次：
- **阶段 1（Pre-writing）**：写作前，用标题矩阵探测最具痛感的内容切口。
- **阶段 2（Post-writing）**：正文终稿后，根据真实正文定制各平台最终上架标题。

## 四大心理模型

1. **反常识认知型**：打破固有预期，直击本质反差。
   - 模式：“别再 XXX 了：真正 XXX 的，其实是 XXX”、“你以为你在 XXX，其实你只是 XXX”。
2. **现实荒诞纪实型**：白描时间、地点、数字、具象物品、真实原声。
   - 模式：“走两个人，留三个工位：今天下午领导给我发的那条钉钉”。
3. **情绪嘴替型**：说出读者憋在心头不敢发声的大实话。
   - 模式：“工资一分没涨，我却成了全组最后的‘干电池’”。
4. **反差狠人宣言型**：用平静、冷幽默对抗现实重压。
   - 模式：“我很同情被裁的兄弟，但我更想保护自己的发际线”。

## Workflow

1. **识别执行阶段**：读取入参中的 `stage`（`pre` 还是 `post`）。
2. **生成四大维度候选池**：
   - 每类模型生成至少 3-5 条候选，共计 15-20 条标题。
   - 评估每条标题的 CTR 点击欲、情绪张力与好奇心缺口。
3. **阶段 1 任务（Pre-writing）**：
   - 挑出最有戏剧张力的 3 条切角，推荐给大纲与正文写手作为写作聚焦点。
4. **阶段 2 任务（Post-writing）**：
   - 严格对照 `humanized_draft` 正文进行事实一致性核查（`fact_check_status`）。
   - **红线核查**：标题里出现的数字、角色、事件，正文中必须真实存在；情绪不得超出正文上限（正文只是调侃，标题不得写成血海深仇）。
   - 按平台输出专属主标题与备选方案：
     - **微信公众号**：强调朋友圈社交转发货币、认知反差与故事悬念。
     - **小红书**：强调第一人称身份标贴、现实痛感与评论区求助感。
     - **知乎**：强调机制剖析、专业自嘲与反直觉判断。
5. **交付输出**：按结构化 JSON 格式输出，参见 [references/schema.md](references/schema.md)。

## Quality Gate

- 严禁出现“震惊”、“泪目”、“看哭了”等廉价低俗标题党词汇。
- 在 `stage=post` 时，标题绝不透支正文不存在的事实。
- 输出完全符合 [references/schema.md](references/schema.md)。
