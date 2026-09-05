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

AI 视觉与视频提示词逆向解构工坊。自动区分**静态图像文生图逆向**与**动态视频时空解构**，转译为各大生成模型的原生高精度提示词。

**Platforms: macOS, Windows, and Linux.** Same `SKILL.md` + `scripts/deconstruct.py`.

## Input Routing (输入类型自动分流)

根据用户输入的素材与诉求，严格执行对应模式：

| 触发场景 | 输入类型 | 执行模式 | 交付重点 |
|---|---|---|---|
| **单图逆向** | 用户上传单张静态图（且未要求视频动效） | **Mode A: 图像文生图逆向 (默认)** | 构图焦段、主体微细节、光影氛围、MJ/FLUX/SDXL/即梦 提示词 |
| **视频逆向** | 用户上传视频文件（.mp4/.mov/等）或要求逆向视频 | **Mode B: 视频时空动力学解构** | 自动抽帧切片、I2V/T2V 诊断、运镜差分、可灵/Runway/海螺 提示词 |
| **图生视频动效** | 用户上传静态图，但**明确要求**“做成视频/让图动起来” | **Mode C: 图生视频运镜延伸** | 结构稳定性评估、低风险微动力学、视频模型方言 |

---

## Workflow

`<skill-dir>` is the folder containing this `SKILL.md`. If `python3` is missing, use `py -3`.

### 模式 A：静态图像文生图逆向 (Image Reverse)

1. **运行本地图像元数据分析**（可选，提取画幅与色调）：
   ```bash
   python3 "<skill-dir>/scripts/deconstruct.py" --image path/to/image.png
   ```
2. **多模态 Agent 四维解构**：
   - **构图与景深**：画幅比例（`--ar 16:9` 等）、视点（低机位仰拍/正视/俯拍）、摄影焦段（35mm人文/85mm特写/广角）。
   - **主体与微材质**：解剖细节、服装面料（如重工金丝刺绣、黑丝绸）、毛发质感、微瑕疵。
   - **环境与光影**：主光源方位、色温（夕阳黄金时刻/冷调）、轮廓光（Rim light）、大气透视。
   - **媒介风格**：电影胶片（35mm film still）、数字绘画、写实摄影等。
3. **输出 4 大原生图像方言**（Midjourney v6.1、FLUX.1、SDXL、即梦）。

---

### 模式 B：动态视频时空解构 (Video Reverse)

1. **运行本地抽帧切片与接触印样拼图**：
   ```bash
   python3 "<skill-dir>/scripts/deconstruct.py" --video path/to/sample.mp4 --out-dir tmp/reverse
   ```
   - 提取 `first_frame.png`（基底底图）、`last_frame.png`（终局态）及 2×3 `contact_sheet.png`。
2. **多模态 Agent 读拼图五维解构**：
   - **制作路径**：I2V（首帧垫图，人物稳定）还是 T2V（纯文生视频）。
   - **运镜差分**：对比 6 格拼图位移（推镜 Dolly-in、横摇 Pan、环绕 Orbit、景深切换 Rack focus）。
   - **物理动力学**：风力、布料翻卷、水花粒子、呼吸眨眼。
   - **输出原生视频方言**（详见 [references/dialects.md](references/dialects.md)）。

---

## 交付格式 (交稿模板)

### 模板 1：图像文生图逆向交付卡 (Mode A)

```markdown
### 🎨 图像提示词逆向解构

- **画幅与焦段**：16:9 / 35mm 电影镜头 / 低机位仰角
- **核心主体**：端坐金龙宝座的橘猫皇帝，重工刺绣金色龙袍，神态威严
- **光影与环境**：夕阳暖金逆光 + 轮廓光，背景故宫角楼融合现代北京CBD天际线

---

#### 1. Midjourney (v6.1)
> `Cinematic film still, low-angle medium shot, a majestic orange tabby cat as ancient Chinese emperor, wearing ornate imperial golden dragon robes and golden crown, sitting regally on golden dragon throne, paws on armrests. Background combines ancient Chinese palaces and modern Beijing skyline with CCTV tower under epic golden sunset, volumetric lighting, rim light on fur, 35mm photography --ar 16:9 --style raw`

#### 2. FLUX.1 (Dev / Schnell)
> `A high-resolution cinematic photograph of an orange tabby cat sitting with majestic posture on an intricate ancient Chinese golden dragon throne. The cat is dressed in an ornate imperial yellow silk robe embroidered with dragons. Golden hour sunlight bathes the scene, casting warm rim lights on its fur. In the distant background, ancient palace rooftops blend seamlessly into the modern Beijing skyline.`

#### 3. Stable Diffusion (SDXL / WebUI)
> **Prompt**: `masterpiece, best quality, cinematic composition, (regal orange tabby cat:1.2), wearing (imperial golden dragon robe:1.1), sitting on golden throne, ancient palace and beijing skyline in background, sunset, golden rim lighting, 35mm photography, film grain`  
> **Negative Prompt**: `worst quality, low quality, deformed paws, bad anatomy, mutated whiskers, blur, plastic skin, watermark`

#### 4. 即梦 (Jimeng / 豆包)
> `电影质感特写，低机位仰拍。一只神态威严的橘色虎斑猫身穿金黄色重工刺绣龙袍，端坐在紫禁城纯金九龙宝座之上。背景融合了夕阳下的故宫角楼与现代北京CBD天际线，大裤衩与中国尊沐浴在金色晚霞中。逆光轮廓光清晰勾勒出猫咪绒毛，大片光影，35毫米镜头摄影。`
```

---

### 模板 2：视频时空解构交付卡 (Mode B)

输出包含：制作路径诊断、首帧底图提示词、以及可灵 1.5、Runway Gen-3、海螺 Minimax 动态提示词。

---

## Hard Rules

1. **输入严格定性，严禁答非所问**：用户给图片未提视频时，**只输出图像文生图提示词**；只有给视频或明确要求“让图动起来”时，才输出视频运镜。
2. **严禁编造不存在的元素**：只描写画面中确凿存在的物理实体、结构与光线。
3. **彻底摒弃塑料词**：绝不添加 `8k, hyperrealistic, octane render, trending on artstation` 等破坏模型权重的废词。
4. **纯文本环境主动声明**：若 Agent 无法查看图像，必须主动告知用户切换至多模态大模型以获得最高精度。

