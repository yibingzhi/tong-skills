---
name: tong-reverse
description: >-
  Reverse-engineers and decodes prompts from AI videos and images: extracts
  keyframes, builds a timeline contact sheet, infers camera vectors,
  physical dynamics, and translates to Kling, Runway, Hailuo, and MJ/FLUX.
  Use when the user asks 逆向提示词, 反推提示词, 解构视频, 视频提示词推测,
  分析视频镜头, reverse prompt, video prompt reverse, deconstruct video, or tong-reverse.
license: MIT
compatibility: Requires Python 3.10+, ffmpeg, and Pillow. Works on macOS, Windows, and Linux.
metadata:
  version: "1.0.0"
  author: TongSkills
---

# Tong Reverse

AI 视频与视觉提示词逆向解构工坊。将任何成片视频（或截图），通过本地轻量切片与分镜拼图，让多模态 Agent 瞬间逆向出其背后的**首帧基底质感 + 镜头运镜轨迹 + 物理动力学**，并转译为各大生成模型的原生提示词。

**Platforms: macOS, Windows, and Linux.** Same `SKILL.md` + `scripts/deconstruct.py`.

## Two Modes (多模态模式 vs 纯文本模型降级)

| 模式 | 运行环境 | Agent 动作 |
|---|---|---|
| **多模态视觉模式 (推荐)** | Gemini, Claude 3.5 Sonnet, GPT-4o, Cursor 等支持视觉的 Agent | 脚本抽帧生成 `contact_sheet.png` 后，Agent 直接调用视觉工具看图，毫秒级推导精确运镜与物理。 |
| **纯文本模型降级** | 纯文本 LLM（不支持读图） | 脚本会输出提示建议切换至多模态模型；若继续在纯文本模型下运行，Agent 引导用户提供画面描述或调用 `--describe` 参数。 |

## Workflow

`<skill-dir>` is the folder containing this `SKILL.md`. If `python3` is missing, use `py -3`.

### 1. 运行本地抽帧切片

从视频中快速抽取绝对首帧（0.0s）、动作终点尾帧，并自动合成为一张 2×3 的 **胶片接触印样拼图（Contact Sheet）**：

```bash
python3 "<skill-dir>/scripts/deconstruct.py" --video path/to/sample.mp4 --out-dir tmp/reverse
```

输出文件：
- `tmp/reverse/first_frame.png`：用于推测 I2V 首帧底图。
- `tmp/reverse/last_frame.png`：用于比对终局动作位移。
- `tmp/reverse/contact_sheet.png`：时序采样大图，标有时间戳，供 Agent 直观观察运镜与动力学。

### 2. 多模态 Agent 读图五维解构

Agent 读取 `contact_sheet.png` 与 `first_frame.png`，按照以下五维协议逆向推断：

1. **制作路径诊断 (Path Diagnosis)**：
   - 判定是 **I2V (首帧图生视频)** 还是 **T2V (纯文生视频)**。
   - 绝大多数人物面部与光影极度稳定的视频均为 I2V。
2. **首帧基底逆向 (Base Image Prompt)**：
   - 锁定画幅比例、镜头焦段（35mm / 85mm / Anamorphic）、主体服装与微材质、环境天气与光影（Rim light / Volumetric）、胶片质感。
3. **摄像机运镜差分 (Camera Mechanics)**：
   - 对比 6 格拼图的背景透视与边界位移：
   - 背景左移 ➔ `Pan right`；
   - 画面向四周膨胀 ➔ `Dolly in / Push-in`；
   - 背景弧形倾斜 ➔ `Orbit / Arc shot`；
   - 焦点深浅转移 ➔ `Rack focus`。
4. **物理动力学解构 (Physical Dynamics)**：
   - 布料褶皱、雨滴水花飞溅、发丝随风翻滚、人物视线与微表情。
5. **多端原生方言输出 (Native Dialects)**：
   - 详细方言语法见 [references/dialects.md](references/dialects.md)。

---

## 交付格式 (交稿模板)

解构完成后，直接输出整洁、可复制的五维清单：

```markdown
### 🎬 视频逆向解构报告

- **制作路径**：推荐 I2V（首帧垫图 + 动态生成）
- **核心运镜**：低机位推镜 + 慢速弧形环绕 (Low-angle dolly-in with subtle orbit)
- **物理要点**：风吹重质感布料飘动、雨滴飞溅光斑、视线从偏转回正

---

#### 1. 首帧底图提示词 (Midjourney / FLUX)
> `Cinematic film still, low-angle medium shot, an ancient lone assassin in rugged black silk robe on snowy cliff, gripping katana hilt, blizzard, cold overcast lighting, rim light, 35mm photography, film grain --ar 16:9`

#### 2. 可灵 (Kling 1.5) 动态提示词
> `低机位慢速环绕向前推镜。暴风雪中刺客右手拇指缓慢推刀出鞘三寸，金属刀刃泛起冷光，反光掠过眼神，黑色斗篷剧烈翻卷摆动。电影质感，升格慢动作。`

#### 3. Runway Gen-3 Alpha 提示词
> `Low-angle tracking push-in shot with subtle orbit: An assassin slowly pushes out katana three inches, sharp specular glint across eyes. Heavy blizzard particle physics, heavy cloth fluttering, 60fps slow-motion.`

#### 4. 海螺 (Minimax) 提示词
> `电影质感特写。雪花受强气流吹拂斜向掠过镜头，刺客缓慢推刀出鞘，雪落在黑色布料上融化，刀刃拔出瞬间有一道极细微的冷白反光掠过双眸，动作克制且充满杀气。`
```

---

## Hard Rules

1. **绝对不编造画面不存在的元素**：只写接触印样中真实存在的物理对象与光影。
2. **剥离运镜与主体动作**：镜头怎么动写镜头的，主体怎么动写主体的，严禁混合成“镜头拔刀”。
3. **拒绝无效垃圾词**：严禁输出 `8k, hyperrealistic, octane render, trending on artstation` 等破坏生成权重的废词。
4. **纯文本环境主动声明**：若 Agent 无法查看图像，必须主动告知用户切换至多模态大模型以获得最高精度。
