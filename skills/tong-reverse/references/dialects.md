# 主流 AI 视频模型原生方言与语法手册 (Dialects & Syntax Guide)

在进行视频逆向工程时，切勿用同一段生硬的中文或英文套所有平台。各个模型的训练语料、时空自注意力机制与运镜控制标记大不相同。

---

## 1. 底层基底图 (I2V Base Image) · Midjourney / FLUX.1

高质量 AI 视频的前提是极致稳定的首帧。

- **Prompt 语法**：
  `[Shot type / Lens], [Subject with physical textures & clothing], [Environment & Weather], [Lighting & Color Grade], [Film Stock / Photography Aesthetic] --ar 16:9`
- **核心要诀**：
  - 先锁焦段（如 `35mm photography`, `85mm portrait`, `anamorphic lens`）；
  - 只写能入画的物理实体，不堆砌 `hyperrealistic, 8k, unreal engine` 等已被现代模型弃用的垃圾词；
  - 人物面部加入真实微瑕疵词（`subtle skin texture, natural soft shadows`）以防塑料感。

---

## 2. 可灵 (Kling 1.5) · 中文动词先行与微物理

可灵对中文语义有极强理解力，特别擅长国风、武侠、写实动作与镜头调度。

- **推荐句式**：
  `[机位运镜描述] + [主体动势与起承转合] + [环境交互与物理细节] + [电影质感与摄影格式]`
- **平台特性**：
  - 动词先行，且动作必须带幅度范围（如“右手缓缓抽出长刀三寸，随即停顿”比“拔刀”好十倍）；
  - 强物理交互：雨水溅落、布料翻卷、发丝随风飘散、烟雾流动；
  - 镜头关键词：`快速环绕运镜`、`低机位仰拍推进`、`大光圈焦点平移`、`升格慢动作`。

---

## 3. Runway Gen-3 Alpha · 工业级结构化标记

Runway Gen-3 极度依赖结构化提示词。官方强烈建议按照电影工业的分镜语法书写。

- **推荐标准语法**：
  `[Camera Movement]: [Subject Action] in [Environment], [Lighting / Cinematic Atmosphere], [Frame Rate / Motion Speed]`
- **标准运镜标识符 (Camera Movements)**：
  - `Low-angle tracking shot`: 低角度跟拍
  - `FPV fast orbit shot`: 第一人称视角快速环绕
  - `Continuous dolly-in / Push-in`: 持续向前推镜
  - `Crane shot / Jib down`: 摇臂自上而下俯摇
  - `Whip pan`: 快速甩镜转场
  - `Rack focus from [Foreground] to [Background]`: 焦点景深切换
- **严禁**：不要在 Runway 中堆砌毫无意义的形容词。

---

## 4. 海螺 (Minimax / Hailuo Video) · 纯自然语言与情感动态

海螺在人物肢体协调度、微表情和自然物理连贯性上属于第一梯队。海螺非常排斥指令式代码，偏好小说/电影剧本般的生动描绘。

- **推荐句式**：
  连贯的自然语言长句，重点描述**动作的因果链**和**人物的情感眼神流动**。
- **示例**：
  `电影质感特写。雪花受强气流吹拂斜向掠过镜头，刺客缓慢拔刀，雪落在黑色布料上融化，刀刃拔出瞬间有一道极细微的冷白反光掠过双眸，动作克制且充满杀气。`

---

## 5. Luma Dream Machine · 纯动量与推背感

Luma 擅长高速穿梭、推背感强的连续运镜。

- **关键词**：
  `Camera rushes forward past...`, `Smooth 360-degree rotation around...`, `High velocity camera zoom...`
