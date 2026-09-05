# 主流 AI 图像与视频模型原生方言指南 (Dialects & Syntax Guide)

在进行提示词逆向工程时，切勿用同一段生硬的套话抹平所有模型。各个模型的训练语料架构（CLIP / T5 / 结构化标记）差异极大。

---

## 第一部分：图像文生图模型方言 (Text-to-Image Dialects)

### 1. Midjourney (v6 / v6.1) · 摄影结构短语与精准参数
- **解析逻辑**：偏好逗号分隔的短语群，强调摄影镜头与光影词汇。
- **推荐语法**：
  `[Shot Type / Lens Angle], [Subject description with material & textures], [Environment & Background details], [Lighting & Color grading], [Film stock / Aesthetic medium] --ar X:Y --style raw --v 6.1`
- **关键参数**：
  - `--ar 16:9` / `--ar 9:16` / `--ar 1:1`：锁定画幅比例
  - `--style raw`：减少 MJ 默认的过度平滑与美学偏置，还原真实物理质感
  - `--stylize 100~250`：权衡写实度与艺术感

### 2. FLUX.1 (Dev / Schnell) · 纯自然语言长句叙事
- **解析逻辑**：基于 T5 编码器，对复杂语法从句和物体间空间相对位置（Spatial relations）具有顶级理解力。**极度排斥逗号标签堆砌**。
- **推荐语法**：连贯的英文自然长句，像摄影师在描述眼前的真实取景。
- **示例**：
  `A high-resolution cinematic photograph of an orange tabby cat sitting with majestic posture on an intricate ancient Chinese golden dragon throne. The cat is clad in an elaborate imperial yellow silk robe embroidered with dragons. Golden hour sunlight washes over the scene, casting warm rim lights on its fur. In the distant background, ancient palace rooftops blend seamlessly into the modern Beijing skyline.`

### 3. Stable Diffusion (SDXL / WebUI / ComfyUI) · 权重标签与负向约束
- **解析逻辑**：基于 CLIP 标签检索，支持括号权重 `(keyword:weight)`。
- **正向推荐**：
  `masterpiece, best quality, cinematic composition, (regal orange tabby cat:1.2), wearing (imperial golden dragon robe:1.1), sitting on golden throne, ancient palace and beijing skyline in background, sunset, golden rim lighting, 35mm photography, film grain`
- **负向提示词 (Negative Prompt)**：
  `worst quality, low quality, deformed paws, bad anatomy, mutated whiskers, blur, plastic skin, watermark, signature`

### 4. 即梦 (Jimeng / 豆包) · 中文高保真自然语言
- **解析逻辑**：原生中文大模型底座，完全无需翻译成英文，直接用中文细腻描摹主体、服装材质、背景地标与光影。
- **推荐语法**：
  `电影质感特写，低机位仰拍。一只神态威严的橘色虎斑猫身穿金黄色重工刺绣龙袍，端坐在紫禁城纯金九龙宝座之上。背景融合了夕阳下的故宫角楼与现代北京CBD天际线，大裤衩与中国尊沐浴在金色晚霞中。逆光轮廓光清晰勾勒出猫咪绒毛，大片光影，35毫米镜头摄影。`

---

## 第二部分：视频与动效模型方言 (Video & Motion Dialects)

### 1. 可灵 (Kling 1.5) · 中文动词先行与微物理
- **推荐句式**：`[机位运镜描述] + [主体动势与起承转合] + [环境交互与物理细节] + [电影质感与摄影格式]`
- **要诀**：动词先行，且动作必须带幅度限制（“缓慢抬眼”、“胸膛随呼吸平缓起伏”）。

### 2. Runway Gen-3 Alpha · 工业级结构化标记
- **推荐标准语法**：
  `[Camera Movement]: [Subject Action] in [Environment], [Lighting / Cinematic Atmosphere], [Frame Rate / Motion Speed]`
- **标准运镜标识符**：
  `Continuous dolly-in / Push-in`, `Low-angle tracking shot`, `FPV fast orbit shot`, `Rack focus from [A] to [B]`

### 3. 海螺 (Minimax / Hailuo Video) · 自然语言情感流
- **推荐句式**：沉浸感长句，强调因果动力学与光线呼吸感。

---

## 第三部分：中文高权重神态与流体动词宝典 (High-Impact Chinese Video Lexicon)

实战验证，中文大模型与视频生成底座（可灵、海螺、Grok-Imagine、即梦）对以下文学感词汇具有极高敏感度：

1. **神态气场高权重词**：
   - `眼神睥睨 / 睥睨天下`：激发不可一世的帝王威严感与半垂眼帘的高冷微表情。
   - `不怒自威 / 沉鸷内敛`：锁定面部肌肉稳定，杜绝五官崩坏或无序抽动。
   - `微微侧头 / 微昂下颌`：提供细微且可控的头部角度位移。
2. **环境流体与时空动态词**：
   - `云层翻涌 / 残霞流动`：比单纯“云彩飘动”更能激活背景的延时摄影张力与深度运动。
   - `金色粒子在空气中浮动 / 余烬升腾`：激活空间微物理，使画面具有透气感与体积光漫反射。
   - `衣摆轻微飘动 / 斗篷翻卷`：赋予布料重力与风向动力学。
3. **中文模型画质锁定位（Grok / 即梦 / 可灵专用）**：
   - 适度在末尾加入 `电影级布光`、`超写实`、`画面细腻流畅` 作为质量稳定锚点。


