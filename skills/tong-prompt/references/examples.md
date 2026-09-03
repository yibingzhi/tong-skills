# 对照

## 作者已经选定效果时：收，不换画派

原文（感觉很满，四套画法 + 渲染器口癖 + 山海经没有的符石）：

```text
A mythical bird Bifang from Shan Hai Jing, standing on a burning ancient pine tree,
one leg, red feathers with intricate golden patterns, emitting flames from its beak,
ancient forest background, misty, lava cracks, floating rune stones,
Chinese traditional Gongbi painting combined with hyper-realism,
Wu Daozi line feeling, thick oil painting texture, 8k resolution,
volumetric light, Tyndall effect, subsurface scattering on feathers, dramatic shadows
--ar 16:9 --stylize 250 --q 2 --v 6.0 --no cartoon, 3d render, cute, disney style, plastic
```

整理后（锚点还是毕方独足 + 火松 + 喙火；画派听「工笔 + 吴道子」）：

```text
lane: image
target: mj
look: gongbi
anchor: Bifang, one-legged, burning ancient pine, flame from the open beak

prompt:
Bifang (毕方) from the Shan Hai Jing: a one-legged crimson fire-bird
perched on a burning ancient pine, trunk charred, needles still on fire.
Red feathers with fine gold filigree, a thin jet of flame from the open beak.
Primeval mountain forest, thin mist, dull lava glow in ground cracks.
Style: Chinese gongbi bird-and-flower on silk, Wu Daozi flying-line in the plumage,
mineral pigments, reserved gold. Not oil paint, not photoreal CGI.
Light: one shaft of late sun through smoke; forest around it stays dark.

negative:
cartoon, 3d render, cute, disney, plastic, extra legs, extra wings

params:
--ar 16:9 --stylize 250 --q 2 --v 6.0
```

删的是符石、油画、超写实、8k/丁达尔/SSS 堆叠。物种特征和动作不动。

## 作者要电影静帧时：不要纠回工笔

锚点可以相同。`--look cine`，正文写烟、逆光、静帧，不写绢本工笔。扫描若发现 `gongbi` 会报画派打架。

## 只给了一个模糊想法

先问「三秒内必须认出什么」，不要先扩写成壁纸。问完再写文件。
