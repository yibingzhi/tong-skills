---
name: tong-cover
description: >-
  Renders brand covers and full article visual suites locally with Pillow:
  公众号封面 2.35:1, 刊头 4:3, 简报竖封 3:4, 分割条 4:1, 金句卡, 要闻清单卡.
  Use when the user asks for 封面, 刊头, 分割条, 金句卡, 每日速览, 简报, 竖封, 小红书, 小绿书,
  视频号图文, brand cover, tong-cover, or 整套图文配图.
license: MIT
compatibility: Requires Python 3.10+ and Pillow. Works on macOS, Windows, and Linux.
metadata:
  version: "1.2.0"
  author: TongSkills
---

# Tong Cover

Local Pillow covers. Default brand **橦云异梦**（支持 `--brand "你的号"`、环境变量 `TONG_BRAND` 全局覆盖，或传 `--no-brand` 纯净无水印生成），default column **每日速览**. Pick color by weekday. Do not ask the user to choose a palette.

**Platforms: macOS, Windows, and Linux.** Same `SKILL.md` + `scripts/make_cover.py`. Do not write OS-specific agent steps, `.cmd` wrappers, or a `brand-cover` repo-root requirement.

Install once: `pip install pillow`

One invocation everywhere (forward slashes are fine on Windows):

```bash
python3 "<skill-dir>/scripts/make_cover.py" --layout feed --ratio 2.35:1 --out tmp/tong-cover/feed.png
```

If `python3` is missing, use `py -3` with the same arguments. `<skill-dir>` is the folder that contains this `SKILL.md`.

Color board and layout notes: [references/presets.md](references/presets.md)

## Hard rules

1. Run the bundled script. Do not regenerate a Pillow renderer.
2. User did not give a date → omit `--date` (script uses today). User did not name a color → leave `--preset` at `auto`.
3. Feed cover: `feed` + `2.35:1`. Body masthead: `editorial` + `4:3`. Vertical briefing/poster: `briefing` + `3:4` with `--bullets`. Do not mix these three.
4. Return local paths and say what each file is for. If Chinese is tofu, run `--list` and check fonts.

## Which layout

| 用户要的 | layout | ratio |
|---|---|---|
| 整套图文 / 发文章 | `--pack DIR` | （全出） |
| 公众号信息流封面 | `feed` | `2.35:1` |
| 刊头 / 正文头图 | `editorial` | `4:3` |
| 竖封 / 简报 / 海报 / 笔记封面 / 小红书 / 小绿书 / 视频号图文 | `briefing` | `3:4`（更长用 `9:16`） |
| 章节分割条 | `divider` | `4:1` |
| 金句卡 / 箴言卡 | `quote` | `3:4`（也支持 `1:1`, `9:16`, `16:9`） |
| 正文里的横版清单 | `bullet` | `4:3` |
| 朋友圈方图 / 小红书方图 | `square` | `1:1` |

`poster` / `story` / 简报 / 竖封 / 竖版 / 海报 / 小红书 / 小绿书 / 视频号图文 → `briefing`。封面必须带 `--bullets`。

### 金句卡风格 (`--style`)

| 风格 | 视觉特征 | 适用场景 |
|---|---|---|
| `paper` (默认) | 宣纸便签风：温润米白底、悬浮投影卡片、典雅宋体、朱红印章 | 深度阅读、文学随笔、经典箴言 |
| `editorial` | 杂志高定风：黑白高对比、现代粗字体、双重装饰线、分类徽章与条形码 | 商业洞察、职场真相、力量感金句 |
| `highlight` | 划线读书风：荧光黄标记笔划线高亮、热划线人数、想法便签框与书名出处 | 读者共鸣、书籍摘抄、痛点洞察 |
| `dark` | 暗黑极客风：深邃黑夜微渐变、磨砂玻璃浮板、赛博高亮强调字、终端极客感 | 科技反思、硬核认知、黑色幽默 |
| `cinema` | 电影台词风：经典暗角电影画幅、REC红点、时间戳、中英双语电影字幕与声轨 | 叙事共鸣、故事对白、情感金句 |
| `polaroid` | 拍立得胶片风：白边相纸卡框、左上角仿真纸胶带斜贴、手账随笔与落款印章 | 手账文艺、生活美学、清欢随感 |
| `tweet` | 社交推文风：即刻/Twitter爆款单条、头像认证蓝V、大字金句与互动数据栏 | 社交货币、现代热点、锐评洞见 |

金句文本支持 `==重点词==` 语法，或通过 `--highlight 词语` 指定高亮。可搭配 `--sub`（金句解读）与 `--source`（出处/书名）。

### 封面背景主题 (`--theme`)

| 主题 | 视觉特征 | 适用场景 |
|---|---|---|
| `celestial` (默认) | 云月星辰：东方月夜、流云与微光 | 人文、随笔、综合夜读、品牌默认风 |
| `swiss` | 瑞士现代网格：无月亮插画，精密排版网格、十字准星、技术坐标与几何强调块 | 硬科技、AI研究、商业研报、严肃深度特稿 |
| `press` | 复古报刊社论：双线规整外框、报刊社论双栏线、复古细纹 | 深度调查、历史纪实、社论观点 |

## Commands

Full suite:

```bash
python3 "<skill-dir>/scripts/make_cover.py" \
  --pack tmp/tong-cover/my_article \
  --title "每日速览" \
  --sub "今日要闻 · AI动态 · 深度思考" \
  --bullets "要点一;要点二;要点三" \
  --quote "打工是出租算力，副业才是在给自己==买服务器==。" \
  --author "橦云异梦" \
  --source "商业思考" \
  --dividers "01:今日头条:核心动态; 02:行业观察:落地思考; 03:深度洞察:趋势启示"
```

Single image:

```bash
python3 "<skill-dir>/scripts/make_cover.py" --layout feed --ratio 2.35:1 --out tmp/tong-cover/feed.png
python3 "<skill-dir>/scripts/make_cover.py" --layout briefing --ratio 3:4 --bullets "要点一;要点二;要点三" --out tmp/tong-cover/briefing.png
python3 "<skill-dir>/scripts/make_cover.py" --layout divider --ratio 4:1 --num 01 --title "今日头条" --out tmp/tong-cover/div01.png
python3 "<skill-dir>/scripts/make_cover.py" --layout quote --style polaroid --brand "晚点LatePost" --quote "天下大事，必作于细。" --out tmp/tong-cover/quote_brand.png
python3 "<skill-dir>/scripts/make_cover.py" --layout quote --style paper --no-brand --quote "大道至简，行稳致远。" --out tmp/tong-cover/quote_clean.png
python3 "<skill-dir>/scripts/make_cover.py" --list
```

`--pack` files:

| 文件 | 用途 |
|---|---|
| `01_cover_feed.png` | 公众号信息流封面 |
| `02_masthead.png` | 正文刊头 |
| `03_summary_card.png` | 横版要闻清单 |
| `04_divider_01.png` … | 章节分割条 |
| `05_quote_card.png` | 金句卡 |
| `06_share_square.png` | 方图 |
| `07_briefing.png` | 竖版简报 |

## Colors

Unspecified `--preset` follows weekday:

| 一 | 二 | 三 | 四 | 五 | 六 | 日 |
|---|---|---|---|---|---|---|
| `dusk` 墨蓝 | `twilight` 暮光 | `paper` 宣纸 | `frost` 霜蓝 | `ember` 烬暖 | `ink` 墨青 | `dawn` 浅金 |

## Fonts

Windows / macOS use system CJK fonts. Linux tries Noto CJK, Source Han, WenQuanYi, then `fc-list :lang=zh`, then caches Noto Sans SC.

```bash
export BRAND_COVER_FONT=/path/to/NotoSansSC-Regular.otf
```

## Output location

Use the user's path when given. Otherwise use `tmp/tong-cover/` (`--pack` a directory, `--out` a png).

## Quality gate

- Layout and ratio match the request.
- Weekday preset unless the user named a color.
- Paths returned; each file has a one-line use.
- Chinese is not tofu (`--list` if it is).

## Upload package

From the TongSkills repo root: `python scripts/pack_skill.py tong-cover`
