# 禁用词与替换

脚本 `scripts/scan.py` 扫硬伤子集。这里给人改稿用。

## 出现即修（FAIL 塑料套话）

| 表达 | 问题 | 修法 |
|---|---|---|
| trending on artstation / stunning artwork / breathtaking | 社区口癖 | 删 |
| 精美高级 / 氛围感拉满 / 咨询一页纸 | 空夸 | 改成纸色、线宽、一种强调色，或删 |

## 三种以上并列即修（FAIL 画法堆叠）

工笔 / 油画 / 超写实 / 3D·Octane / 水彩 / 水墨 / 二次元·迪士尼

同一次只留作者要的那一种。吴道子用线可以叠在工笔上，脚本不把「Wu Daozi」单独算一派。

## 三个以上即修（FAIL 塑料堆叠）

`volumetric` / 丁达尔 / SSS / god rays / cinematic lighting / 8k / masterpiece / best quality / octane render / ray tracing

一个可当 WARN 留下（例如只要一道体积光）。两个以上优先收成一句具体的光：「烟里一道晚照」。

## 图 lane 禁止写进正文

first frame、last frame、camera pans/dollies、缓缓推进、前 N 秒、时长 N。这些去 `--lane video`。

## Midjourney 尾缀

`--stylize` / `--v` / `--q` / `--sref` / `--no` 只在 `--target mj`。即梦、可灵、generic 把否定词放 `negative:`，比例写进 prompt 或 `--ar` 仅 MJ。

## WARN：出处外配件

floating rune、符石、法阵、仙侠。作者锚点里有的可留；山海经没写就删。
