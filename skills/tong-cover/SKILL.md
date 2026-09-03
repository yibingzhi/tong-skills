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
  version: "1.1.0"
  author: TongSkills
---

# Tong Cover

Local Pillow covers. Default brand **橦云异梦**, default column **每日速览**. Pick color by weekday. Do not ask the user to choose a palette.

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
| 金句卡 | `quote` | `1:1` |
| 正文里的横版清单 | `bullet` | `4:3` |
| 朋友圈方图 / 小红书方图 | `square` | `1:1` |

`poster` / `story` / 简报 / 竖封 / 竖版 / 海报 / 小红书 / 小绿书 / 视频号图文 → `briefing`。封面必须带 `--bullets`。

## Commands

Full suite:

```bash
python3 "<skill-dir>/scripts/make_cover.py" \
  --pack tmp/tong-cover/my_article \
  --title "每日速览" \
  --sub "今日要闻 · AI动态 · 深度思考" \
  --bullets "要点一;要点二;要点三" \
  --quote "金句正文。" \
  --author "出处" \
  --dividers "01:今日头条:核心动态; 02:行业观察:落地思考; 03:深度洞察:趋势启示"
```

Single image:

```bash
python3 "<skill-dir>/scripts/make_cover.py" --layout feed --ratio 2.35:1 --out tmp/tong-cover/feed.png
python3 "<skill-dir>/scripts/make_cover.py" --layout briefing --ratio 3:4 --bullets "要点一;要点二;要点三" --out tmp/tong-cover/briefing.png
python3 "<skill-dir>/scripts/make_cover.py" --layout divider --ratio 4:1 --num 01 --title "今日头条" --out tmp/tong-cover/div01.png
python3 "<skill-dir>/scripts/make_cover.py" --layout quote --ratio 1:1 --quote "金句。" --author "出处" --out tmp/tong-cover/quote.png
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
