from __future__ import annotations

import os
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

from . import fonts, paint
from .presets import PRESETS, RATIOS, Preset, parse_calendar, pick_layout, pick_preset


def _box_dot(cx: float, cy: float, r: float):
    return [int(cx - r), int(cy - r), int(cx + r), int(cy + r)]


@dataclass
class CoverBrief:
    title: str = "每日速览"
    out: str = "out/cover.png"
    brand: str = "橦云异梦"
    date: str = ""
    kicker: str = ""
    sub: str = ""
    preset: str = "auto"
    layout: str = "auto"
    ratio: str = "4:3"
    seed: int = 42
    num: str = "01"
    quote: str = ""
    author: str = ""
    bullets: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def resolve_size(ratio: str, layout: str = "editorial") -> tuple[int, int]:
    if ratio and ratio in RATIOS:
        return RATIOS[ratio]
    if ratio and ":" in ratio:
        try:
            rw, rh = ratio.split(":")
            rw, rh = float(rw), float(rh)
            if rw >= rh:
                base_w = 1880 if rw / rh >= 2.0 else 1400
                return base_w, max(200, int(base_w * rh / rw))
            else:
                base_h = 1600 if rh / rw >= 1.6 else 1400
                return max(200, int(base_h * rw / rh)), base_h
        except Exception:
            pass

    # Layout default fallback ratios
    if layout == "feed":
        return RATIOS["2.35:1"]
    if layout == "divider":
        return RATIOS["4:1"]
    if layout in ("square", "quote"):
        return RATIOS["1:1"]
    if layout in ("briefing", "story", "poster"):
        return RATIOS["3:4"]
    if layout == "banner":
        return RATIOS["16:9"]
    return RATIOS["4:3"]


def wrap_title(draw, text: str, font, max_width: float, max_lines: int = 3) -> list[str]:
    if not text:
        return [""]
    if fonts.text_size(draw, text, font)[0] <= max_width:
        return [text]
    if " " in text or "·" in text or "/" in text:
        parts = text.replace("/", " / ").replace("·", " · ").split()
        lines, cur = [], ""
        for part in parts:
            trial = (cur + " " + part).strip()
            if fonts.text_size(draw, trial, font)[0] <= max_width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = part
        if cur:
            lines.append(cur)
        return lines[:max_lines] or [text]
    lines, buf = [], ""
    for ch in text:
        trial = buf + ch
        if fonts.text_size(draw, trial, font)[0] <= max_width and len(buf) < 18:
            buf = trial
        else:
            if buf:
                lines.append(buf)
            buf = ch
    if buf:
        lines.append(buf)
    return lines[:max_lines] or [text]


def fit_title(draw, text: str, kind: str, start_size: float, max_width: float, max_height: float, max_lines: int = 3):
    size = int(start_size)
    while size >= 18:
        font = fonts.load_font(kind, size)
        lines = wrap_title(draw, text, font, max_width, max_lines=max_lines)
        line_h = fonts.text_size(draw, "国", font)[1]
        total_h = line_h * len(lines) * 1.22
        widest = max(fonts.text_size(draw, line, font)[0] for line in lines)
        if widest <= max_width and total_h <= max_height:
            return font, lines, line_h
        size -= 2
    font = fonts.load_font(kind, 18)
    return font, wrap_title(draw, text, font, max_width, max_lines=max_lines), fonts.text_size(draw, "国", font)[1]


def _art(img: Image.Image, preset: Preset, layout: str, seed: int) -> Image.Image:
    w, h = img.size
    aspect = w / max(h, 1)

    # Adaptive artwork positioning based on aspect ratio
    if aspect >= 2.0:  # Ultra-wide (2.35:1, 3:1, 4:1)
        moon = (w * 0.88, h * 0.36, h * 0.20)
        cloud = (w * 0.85, h * 0.58, w * 0.28, h * 0.65)
        small = (w * 0.70, h * 0.20, w * 0.12, h * 0.22)
        wash = (w * 0.86, h * 0.48, h * 0.75)
        mtn_y, mtn_h = h * 0.98, h * 0.14
    elif aspect >= 1.25:  # Landscape (16:9, 4:3, 3:2)
        moon = (w * 0.80, h * 0.28, h * 0.095)
        cloud = (w * 0.76, h * 0.45, w * 0.46, h * 0.32)
        small = (w * 0.62, h * 0.78, w * 0.18, h * 0.10)
        wash = (w * 0.76, h * 0.36, min(w, h) * 0.55)
        mtn_y, mtn_h = h * 0.95, h * 0.12
    elif aspect >= 0.85:  # Square (1:1, 5:4)
        moon = (w * 0.78, h * 0.24, w * 0.085)
        cloud = (w * 0.74, h * 0.40, w * 0.46, h * 0.28)
        small = (w * 0.20, h * 0.82, w * 0.24, h * 0.14)
        wash = (w * 0.74, h * 0.34, min(w, h) * 0.55)
        mtn_y, mtn_h = h * 0.95, h * 0.10
    elif layout in ("briefing", "poster", "story"):
        moon = (w * 0.86, h * 0.09, w * 0.055)
        cloud = (w * 0.84, h * 0.14, w * 0.34, h * 0.10)
        small = (w * 0.16, h * 0.94, w * 0.20, h * 0.05)
        wash = (w * 0.88, h * 0.10, w * 0.32)
        mtn_y, mtn_h = h * 0.98, h * 0.07
    else:  # Vertical (3:4, 9:16, 4:5)
        moon = (w * 0.76, h * 0.16, w * 0.11)
        cloud = (w * 0.65, h * 0.24, w * 0.68, h * 0.18)
        small = (w * 0.22, h * 0.76, w * 0.32, h * 0.10)
        wash = (w * 0.70, h * 0.22, w * 0.60)
        mtn_y, mtn_h = h * 0.96, h * 0.08

    img = Image.alpha_composite(img, paint.wash_layer(img.size, preset, *wash))
    # Layered rolling distant hills
    img = Image.alpha_composite(img, paint.mountain_layer(img.size, mtn_y, mtn_h, preset.cloud_shadow, alpha=35, seed=seed))
    img = Image.alpha_composite(img, paint.mountain_layer(img.size, mtn_y + h * 0.015, mtn_h * 0.75, preset.cloud_shadow, alpha=55, seed=seed + 11))
    img = Image.alpha_composite(img, paint.moon_layer(img.size, *moon, preset))
    img = Image.alpha_composite(img, paint.cloud_layer(img.size, *cloud, preset, seed, alpha=220))
    img = Image.alpha_composite(
        img, paint.cloud_layer(img.size, small[0], small[1], small[2], small[3], preset, seed + 3, alpha=130)
    )
    img = Image.alpha_composite(img, paint.stars_layer(img.size, preset.stars, preset.moon, seed))
    img = Image.alpha_composite(img, paint.editorial_accents(img.size, preset.brand, alpha=35))
    return img


def _draw_brand(draw: ImageDraw.ImageDraw, x: float, y: float, unit: float, box_w: float, brief: CoverBrief, preset: Preset) -> float:
    brand_text = brief.brand or "橦云异梦"
    spaced_brand = fonts.letterspace(brand_text, "  ")
    brand_font = fonts.load_font("fangsong", max(16, int(unit * 0.038)))
    brand = fonts.draw_text_measured(draw, (x, y), spaced_brand, brand_font, preset.brand + (255,))

    en_font = fonts.load_font("sans_light", max(10, int(unit * 0.016)))
    draw.text(
        (int(brand.x1 + unit * 0.03), int(brand.y0 + brand.h * 0.28)),
        "EDITORIAL SELECTION",
        font=en_font,
        fill=preset.kicker + (160,),
        anchor="lt",
    )

    rule_y = brand.y1 + max(6, int(unit * 0.014))
    rule_len = min(box_w * 0.24, unit * 0.16)
    draw.line(
        [(int(x), int(rule_y)), (int(x + rule_len), int(rule_y))],
        fill=preset.accent + (180,),
        width=2,
    )
    draw.ellipse(_box_dot(x + rule_len + unit * 0.015, rule_y, 2), fill=preset.accent + (220,))
    return rule_y + max(8, int(unit * 0.018))


def _type_box(layout: str, w: int, h: int) -> tuple[float, float, float, float]:
    aspect = w / max(h, 1)
    if aspect >= 2.0:
        return w * 0.055, h * 0.11, w * 0.62, h * 0.78
    if aspect >= 1.25:
        return w * 0.070, h * 0.12, w * 0.56, h * 0.74
    if aspect >= 0.85:
        return w * 0.075, h * 0.11, w * 0.64, h * 0.76
    return w * 0.085, h * 0.12, w * 0.82, h * 0.68


def _hero_date(brief: CoverBrief) -> tuple[str, str, str]:
    month, day, weekday, en_date, _en_full = parse_calendar(brief.date)
    if month and day:
        return "%02d.%02d" % (month, day), weekday, en_date
    token = brief.date.split()[0] if brief.date else "09.01"
    return token, weekday, en_date


def _draw_date_meta(draw, date_box, weekday: str, en_date: str, date_font_size: float, unit: float, preset: Preset):
    if not (weekday or en_date):
        return
    gap = max(14, int(unit * 0.028))
    cal_x = date_box.x1 + gap
    top = date_box.y0 + date_box.h * 0.10
    bot = date_box.y1 - date_box.h * 0.06
    if bot - top < 8:
        return
    draw.line([(int(cal_x), int(top)), (int(cal_x), int(bot))], fill=preset.accent + (140,), width=1)
    info_x = cal_x + max(12, int(unit * 0.022))
    if en_date:
        en_f = fonts.load_font("en_serif", max(12, int(date_font_size * 0.15)))
        fonts.draw_text_measured(draw, (info_x, date_box.y0 + date_box.h * 0.12), en_date, en_f, preset.accent + (240,))
    if weekday:
        wd_f = fonts.load_font("sans", max(16, int(date_font_size * 0.20)))
        fonts.draw_text_measured(draw, (info_x, date_box.y0 + date_box.h * 0.52), weekday, wd_f, preset.kicker + (255,))


def _fit_date_font(draw, text: str, start: float, max_w: float, max_h: float):
    size = int(start)
    while size >= 28:
        font = fonts.load_font("display_num", size)
        bw, bh = fonts.text_size(draw, text, font)
        if bw <= max_w and bh <= max_h:
            return font, size
        size -= 4
    font = fonts.load_font("display_num", 28)
    return font, 28


def draw_type_feed(img: Image.Image, brief: CoverBrief, preset: Preset) -> Image.Image:
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x, y, box_w, box_h = _type_box("feed", w, h)
    unit = min(w, h)
    box_bottom = y + box_h

    cursor = _draw_brand(draw, x, y, unit, box_w, brief, preset)
    date_hero, weekday, en_date = _hero_date(brief)
    title = brief.title or "每日速览"
    sub_text = brief.sub or brief.kicker
    if sub_text:
        sub_text = " · ".join(s.strip() for s in sub_text.replace("/", "·").split("·") if s.strip())

    title_size = max(22, int(min(h * 0.088, unit * 0.10, box_w * 0.12)))
    title_font = fonts.load_font("headline", title_size)
    title_h = fonts.text_size(draw, title, title_font)[1]
    sub_h = 0
    if sub_text:
        sub_h = fonts.text_size(draw, sub_text, fonts.load_font("sans", max(13, int(title_size * 0.46))))[1]

    gap_date_title = max(28, int(h * 0.058))
    gap_title_sub = max(10, int(h * 0.028))
    reserved = title_h + gap_date_title + (sub_h + gap_title_sub if sub_text else 0) + max(10, int(h * 0.03))
    date_budget = max(unit * 0.16, box_bottom - cursor - reserved)

    date_font, date_font_size = _fit_date_font(
        draw, date_hero, min(h * 0.30, unit * 0.32, date_budget * 0.92), box_w * 0.72, date_budget
    )
    date_box = fonts.draw_text_measured(draw, (x, cursor + max(2, int(h * 0.012))), date_hero, date_font, preset.title + (255,))
    _draw_date_meta(draw, date_box, weekday, en_date, date_font_size, unit, preset)

    sep_y = date_box.y1 + max(10, int(gap_date_title * 0.38))
    sep_w = min(date_box.w * 0.18, unit * 0.10)
    draw.line([(int(x), int(sep_y)), (int(x + sep_w), int(sep_y))], fill=preset.kicker + (90,), width=1)

    title_box = fonts.draw_text_measured(
        draw, (x, date_box.y1 + gap_date_title), title, title_font, preset.title + (255,)
    )
    if sub_text:
        sub_font = fonts.load_font("sans", max(13, int(title_size * 0.46)))
        fonts.draw_text_measured(draw, (x, title_box.y1 + gap_title_sub), sub_text, sub_font, preset.kicker + (230,))
    return Image.alpha_composite(img, overlay)


def draw_type_divider(img: Image.Image, brief: CoverBrief, preset: Preset) -> Image.Image:
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x, y, box_w, _box_h = _type_box("divider", w, h)

    num_str = brief.num or "01"
    num_font = fonts.load_font("display_num", max(36, int(h * 0.48)))
    num_box = fonts.draw_text_measured(draw, (x, y + int(h * 0.08)), num_str, num_font, preset.accent + (255,))

    bar_x = num_box.x1 + max(16, int(h * 0.07))
    draw.line(
        [(int(bar_x), int(num_box.y0 + num_box.h * 0.08)), (int(bar_x), int(num_box.y1 - num_box.h * 0.04))],
        fill=preset.accent + (160,),
        width=2,
    )

    tx = bar_x + max(16, int(h * 0.07))
    title_font = fonts.load_font("headline", max(20, int(h * 0.22)))
    title_box = fonts.draw_text_measured(
        draw, (tx, num_box.y0 + int(num_box.h * 0.04)), brief.title or "核心前沿动态", title_font, preset.title + (255,)
    )
    sub_text = brief.sub or brief.kicker or ("SECTION %s · TOP HEADLINES" % num_str)
    sub_font = fonts.load_font("sans", max(12, int(h * 0.10)))
    fonts.draw_text_measured(draw, (tx, title_box.y1 + max(6, int(h * 0.04))), sub_text, sub_font, preset.kicker + (240,))
    return Image.alpha_composite(img, overlay)


def draw_type_quote(img: Image.Image, brief: CoverBrief, preset: Preset) -> Image.Image:
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x, y, box_w, box_h = _type_box("quote", w, h)
    unit = min(w, h)

    cursor = _draw_brand(draw, x, y, unit, box_w, brief, preset)
    quote_glyph_font = fonts.load_font("en_serif", int(unit * 0.22))
    fonts.draw_text_measured(draw, (x - unit * 0.01, cursor), "“", quote_glyph_font, preset.wash + (170,))

    quote_body = brief.quote or brief.title or "流水不争先，争的是滔滔不绝。"
    q_font, lines, _line_h = fit_title(draw, quote_body, "fangsong", unit * 0.076, box_w * 0.86, box_h * 0.44, max_lines=4)

    cur_y = cursor + int(unit * 0.08)
    last = None
    for line in lines:
        last = fonts.draw_text_measured(draw, (x + unit * 0.02, cur_y), line, q_font, preset.title + (255,))
        cur_y = last.y1 + max(10, int(unit * 0.022))

    author_text = ("—— " + brief.author) if brief.author else ("—— %s · 每日箴言" % (brief.brand or "橦云异梦"))
    author_font = fonts.load_font("sans", max(14, int(unit * 0.034)))
    ay = (last.y1 if last else cur_y) + max(16, int(unit * 0.040))
    fonts.draw_text_measured(draw, (x + box_w * 0.22, ay), author_text, author_font, preset.kicker + (255,))

    if brief.date:
        d_font = fonts.load_font("sans_light", max(12, int(unit * 0.026)))
        fonts.draw_text_measured(draw, (x, y + box_h - unit * 0.02), brief.date, d_font, preset.date + (200,))

    seal_font = fonts.load_font("kai", max(18, int(unit * 0.045)))
    overlay = Image.alpha_composite(
        overlay,
        paint.seal_stamp(img.size, int(w * 0.86), int(h * 0.82), max(24, int(unit * 0.068)), (brief.brand or "云")[0], preset.accent, seal_font),
    )
    return Image.alpha_composite(img, overlay)


def draw_type_bullet(img: Image.Image, brief: CoverBrief, preset: Preset) -> Image.Image:
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x, y, box_w, _box_h = _type_box("bullet", w, h)
    unit = min(w, h)

    cursor = _draw_brand(draw, x, y, unit, box_w, brief, preset)
    hdr_font = fonts.load_font("headline", max(22, int(unit * 0.068)))
    hdr = fonts.draw_text_measured(draw, (x, cursor + int(unit * 0.024)), brief.title or "今日核心要闻速览", hdr_font, preset.title + (255,))
    cursor = hdr.y1

    if brief.date:
        d_font = fonts.load_font("sans", max(14, int(unit * 0.028)))
        date_box = fonts.draw_text_measured(draw, (x, cursor + int(unit * 0.016)), brief.date, d_font, preset.accent + (240,))
        cursor = date_box.y1

    items = brief.bullets or [
        "全球前沿大模型与具身智能新突破加速涌现",
        "芯片巨头发布亮眼财报，算力基础设施需求强劲",
        "国内 AI 落地应用迎来政策红利，产业赋能提速",
    ]
    item_font = fonts.load_font("sans", max(16, int(unit * 0.036)))
    num_font = fonts.load_font("display_num", max(14, int(unit * 0.030)))
    iy = cursor + int(unit * 0.032)

    for i, item in enumerate(items[:4]):
        tag_str = "%02d" % (i + 1)
        badge_w = int(unit * 0.062)
        badge_h = int(unit * 0.042)
        badge_box = [int(x), int(iy), int(x + badge_w), int(iy + badge_h)]
        draw.rounded_rectangle(badge_box, radius=int(badge_h * 0.35), fill=preset.accent + (45,), outline=preset.accent + (160,), width=1)
        tw, th = fonts.text_size(draw, tag_str, num_font)
        draw.text(
            (int(x + (badge_w - tw) / 2), int(iy + (badge_h - th) / 2)),
            tag_str,
            font=num_font,
            fill=preset.accent + (255,),
            anchor="lt",
        )

        text_x = x + badge_w + max(10, int(unit * 0.022))
        wrapped = wrap_title(draw, item, item_font, box_w - badge_w - unit * 0.04, max_lines=2)
        line_bottom = iy
        for w_line in wrapped:
            line = fonts.draw_text_measured(draw, (text_x, line_bottom), w_line, item_font, preset.title + (255,))
            line_bottom = line.y1 + max(4, int(unit * 0.008))
        iy = max(iy + badge_h, line_bottom) + max(10, int(unit * 0.018))
    return Image.alpha_composite(img, overlay)


def draw_type_square(img: Image.Image, brief: CoverBrief, preset: Preset) -> Image.Image:
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x, y, box_w, box_h = _type_box("square", w, h)
    unit = min(w, h)
    box_bottom = y + box_h

    cursor = _draw_brand(draw, x, y, unit, box_w, brief, preset)
    date_hero, weekday, en_date = _hero_date(brief)
    title = brief.title or "每日速览"
    sub_text = brief.sub or brief.kicker or brief.quote

    title_font = fonts.load_font("headline", max(24, int(unit * 0.072)))
    title_h = fonts.text_size(draw, title, title_font)[1]
    sub_h = 0
    if sub_text:
        sub_font_probe = fonts.load_font("sans", max(14, int(unit * 0.032)))
        wrapped_probe = wrap_title(draw, sub_text, sub_font_probe, box_w * 0.88, max_lines=3)
        sub_h = fonts.text_size(draw, "国", sub_font_probe)[1] * len(wrapped_probe)

    gap_date_title = max(32, int(unit * 0.048))
    gap_title_sub = max(12, int(unit * 0.026))
    reserved = title_h + gap_date_title + (sub_h + gap_title_sub if sub_text else 0) + int(unit * 0.08)
    date_budget = max(unit * 0.10, box_bottom - cursor - reserved)
    date_font, date_font_size = _fit_date_font(draw, date_hero, min(unit * 0.15, date_budget * 0.92), box_w * 0.62, date_budget)

    date_box = fonts.draw_text_measured(draw, (x, cursor + int(unit * 0.02)), date_hero, date_font, preset.title + (255,))
    _draw_date_meta(draw, date_box, weekday, en_date, date_font_size, unit, preset)

    sep_y = date_box.y1 + max(12, int(gap_date_title * 0.38))
    sep_w = min(date_box.w * 0.16, unit * 0.10)
    draw.line([(int(x), int(sep_y)), (int(x + sep_w), int(sep_y))], fill=preset.kicker + (90,), width=1)

    title_box = fonts.draw_text_measured(
        draw, (x, date_box.y1 + gap_date_title), title, title_font, preset.title + (255,)
    )
    if sub_text:
        sub_font = fonts.load_font("sans", max(14, int(unit * 0.032)))
        wrapped = wrap_title(draw, sub_text, sub_font, box_w * 0.88, max_lines=3)
        cur_y = title_box.y1 + gap_title_sub
        for line in wrapped:
            line_box = fonts.draw_text_measured(draw, (x, cur_y), line, sub_font, preset.kicker + (230,))
            cur_y = line_box.y1 + max(4, int(unit * 0.010))

    seal_font = fonts.load_font("kai", max(18, int(unit * 0.045)))
    overlay = Image.alpha_composite(
        overlay,
        paint.seal_stamp(img.size, int(w * 0.86), int(h * 0.82), max(24, int(unit * 0.068)), (brief.brand or "云")[0], preset.accent, seal_font),
    )
    return Image.alpha_composite(img, overlay)


def _briefing_tags(text: str) -> list[str]:
    raw = text.replace("/", "·").replace("|", "·")
    tags = [s.strip() for s in raw.split("·") if s.strip()]
    return tags[:4]


def _default_briefs() -> list[str]:
    return [
        "全球前沿大模型与具身智能新突破加速涌现",
        "芯片巨头发布亮眼财报，算力基础设施需求强劲",
        "国内 AI 落地应用迎来政策红利，产业赋能提速",
    ]


def draw_type_briefing(img: Image.Image, brief: CoverBrief, preset: Preset) -> Image.Image:
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    unit = min(w, h)
    x = w * 0.078
    y = h * 0.048
    box_w = w * 0.844
    box_right = x + box_w
    box_bottom = h * 0.935
    tall = h / max(w, 1) >= 1.55

    draw.rectangle([0, 0, w, max(5, int(h * 0.0075))], fill=preset.accent + (235,))

    brand_font = fonts.load_font("fangsong", max(18, int(unit * 0.034)))
    brand = fonts.draw_text_measured(
        draw, (x, y), fonts.letterspace(brief.brand or "橦云异梦", "  "), brand_font, preset.brand + (255,)
    )
    label = "DAILY BRIEFING"
    lab_font = fonts.load_font("sans_light", max(11, int(unit * 0.020)))
    lw, lh = fonts.text_size(draw, label, lab_font)
    fonts.draw_text_measured(
        draw,
        (box_right - lw, brand.y0 + max(0, (brand.h - lh) * 0.35)),
        label,
        lab_font,
        preset.kicker + (200,),
    )

    rule_y = brand.y1 + max(10, int(unit * 0.016))
    draw.line([(int(x), int(rule_y)), (int(box_right), int(rule_y))], fill=preset.title + (80,), width=1)

    date_hero, weekday, en_date = _hero_date(brief)
    date_top = rule_y + max(14, int(h * 0.018))
    date_font, date_size = _fit_date_font(draw, date_hero, min(unit * 0.13, h * 0.10), box_w * 0.58, h * 0.12)
    date_box = fonts.draw_text_measured(draw, (x, date_top), date_hero, date_font, preset.title + (255,))
    _draw_date_meta(draw, date_box, weekday, en_date, date_size, unit, preset)

    title = brief.title or "每日速览"
    title_font, lines, _ = fit_title(draw, title, "headline", unit * 0.086, box_w * 0.92, h * 0.15, max_lines=2)
    cur_y = date_box.y1 + max(16, int(h * 0.020))
    last = None
    for line in lines:
        last = fonts.draw_text_measured(draw, (x, cur_y), line, title_font, preset.title + (255,))
        cur_y = last.y1 + max(6, int(unit * 0.010))

    tags = _briefing_tags(brief.sub or brief.kicker or "今日要闻 · AI动态 · 深度思考")
    tag_font = fonts.load_font("sans", max(13, int(unit * 0.024)))
    tag_y = (last.y1 if last else cur_y) + max(12, int(h * 0.012))
    tag_x = x
    tag_bottom = tag_y
    for tag in tags:
        tw, th = fonts.text_size(draw, tag, tag_font)
        pad_x, pad_y = max(10, int(unit * 0.012)), max(5, int(unit * 0.006))
        chip_w, chip_h = tw + pad_x * 2, th + pad_y * 2
        if tag_x + chip_w > box_right and tag_x > x:
            tag_x = x
            tag_y = tag_bottom + max(8, int(unit * 0.010))
        chip = [int(tag_x), int(tag_y), int(tag_x + chip_w), int(tag_y + chip_h)]
        draw.rounded_rectangle(chip, radius=3, outline=preset.accent + (150,), width=1)
        fonts.draw_text_measured(draw, (tag_x + pad_x, tag_y + pad_y), tag, tag_font, preset.kicker + (240,))
        tag_x = chip[2] + max(8, int(unit * 0.010))
        tag_bottom = max(tag_bottom, chip[3])

    rule1 = tag_bottom + max(16, int(h * 0.018))
    draw.line([(int(x), int(rule1)), (int(box_right), int(rule1))], fill=preset.title + (170,), width=2)
    draw.line([(int(x), int(rule1 + 5)), (int(box_right), int(rule1 + 5))], fill=preset.title + (70,), width=1)

    idx_font = fonts.load_font("sans_light", max(11, int(unit * 0.018)))
    idx = fonts.draw_text_measured(
        draw, (x, rule1 + max(12, int(h * 0.012))), "TODAY'S BRIEF", idx_font, preset.accent + (220,)
    )

    items = brief.bullets[:4] if brief.bullets else _default_briefs()
    item_font = fonts.load_font("sans", max(16, int(unit * (0.032 if tall else 0.038))))
    num_font = fonts.load_font("display_num", max(18, int(unit * (0.036 if tall else 0.042))))
    iy = idx.y1 + max(14, int(h * 0.014))
    n = min(3, len(items))
    footer_reserve = max(48, int(unit * 0.08))

    for i, item in enumerate(items[:n]):
        num = "%02d" % (i + 1)
        nb = fonts.draw_text_measured(draw, (x, iy), num, num_font, preset.accent + (255,))
        text_x = nb.x1 + max(14, int(unit * 0.020))
        wrapped = wrap_title(draw, item, item_font, box_right - text_x, max_lines=2)
        line_y = iy + max(0, int((nb.h - fonts.text_size(draw, "国", item_font)[1]) * 0.15))
        last_line = nb
        for wline in wrapped:
            last_line = fonts.draw_text_measured(draw, (text_x, line_y), wline, item_font, preset.title + (255,))
            line_y = last_line.y1 + max(4, int(unit * 0.006))
        row_bottom = max(nb.y1, last_line.y1)
        if i < n - 1:
            hy = row_bottom + max(12, int(h * (0.014 if tall else 0.018)))
            draw.line([(int(text_x), int(hy)), (int(box_right), int(hy))], fill=preset.kicker + (65,), width=1)
            iy = hy + max(14, int(h * (0.016 if tall else 0.022)))
        else:
            iy = row_bottom
        if iy > box_bottom - footer_reserve:
            break

    close_y = iy + max(20, int(h * 0.022))
    draw.line([(int(x), int(close_y)), (int(box_right), int(close_y))], fill=preset.title + (70,), width=1)
    fy = close_y + max(14, int(h * 0.016))
    if tall:
        fy = min(max(fy, box_bottom - int(unit * 0.04)), h - int(unit * 0.055))
    if brief.date:
        df = fonts.load_font("sans", max(13, int(unit * 0.022)))
        fonts.draw_text_measured(draw, (x, fy), brief.date, df, preset.date + (220,))

    seal_font = fonts.load_font("kai", max(18, int(unit * 0.042)))
    seal_cy = min(int(fy + unit * 0.02), int(h * 0.90))
    overlay = Image.alpha_composite(
        overlay,
        paint.seal_stamp(
            img.size, int(w * 0.88), max(int(fy + 8), seal_cy), max(22, int(unit * 0.058)), (brief.brand or "云")[0], preset.accent, seal_font
        ),
    )
    return Image.alpha_composite(img, overlay)


def draw_type_editorial(img: Image.Image, brief: CoverBrief, preset: Preset, layout: str) -> Image.Image:
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x, y, box_w, box_h = _type_box(layout, w, h)
    unit = min(w, h)

    cursor = _draw_brand(draw, x, y, unit, box_w, brief, preset)
    title_font, lines, _ = fit_title(
        draw, brief.title, "headline", unit * (0.11 if layout != "banner" else 0.13), box_w, box_h * 0.42
    )

    cur_y = cursor + max(8, int(unit * 0.028))
    last = None
    for line in lines:
        last = fonts.draw_text_measured(draw, (x, cur_y), line, title_font, preset.title + (255,))
        cur_y = last.y1 + max(6, int(unit * 0.016))

    sub_text = brief.sub or brief.kicker
    if sub_text and last:
        kicker_font = fonts.load_font("sans", max(14, int(unit * 0.028)))
        sub_box = fonts.draw_text_measured(draw, (x, last.y1 + max(10, int(unit * 0.026))), sub_text, kicker_font, preset.kicker + (240,))
        last = sub_box

    if brief.date:
        date_font = fonts.load_font("sans", max(14, int(unit * 0.026)))
        floor_y = (last.y1 + int(unit * 0.048)) if last else cursor
        dy = min(max(floor_y, y + box_h - unit * 0.04), h - unit * 0.06)
        dx = (w - fonts.text_size(draw, brief.date, date_font)[0]) / 2 if layout == "poster" else x
        date_box = fonts.draw_text_measured(draw, (dx + unit * 0.022, dy), brief.date, date_font, preset.date + (240,))
        draw.ellipse(_box_dot(dx, (date_box.y0 + date_box.y1) / 2, 3), fill=preset.accent + (255,))

    if preset.name in ("paper", "ink", "twilight"):
        seal_font = fonts.load_font("kai", max(18, int(unit * 0.045)))
        overlay = Image.alpha_composite(
            overlay,
            paint.seal_stamp(img.size, int(w * 0.86), int(h * 0.82), max(24, int(unit * 0.068)), (brief.brand or "云")[0], preset.accent, seal_font),
        )
    return Image.alpha_composite(img, overlay)


def draw_type(img: Image.Image, brief: CoverBrief, preset: Preset, layout: str) -> Image.Image:
    if layout == "feed":
        return draw_type_feed(img, brief, preset)
    if layout == "divider":
        return draw_type_divider(img, brief, preset)
    if layout == "quote":
        return draw_type_quote(img, brief, preset)
    if layout == "bullet":
        return draw_type_bullet(img, brief, preset)
    if layout == "square":
        return draw_type_square(img, brief, preset)
    if layout in ("briefing", "poster", "story"):
        return draw_type_briefing(img, brief, preset)
    return draw_type_editorial(img, brief, preset, layout)


def render_cover(brief: CoverBrief) -> str:
    preset_name = pick_preset(brief.title, brief.brand, brief.preset, brief.date)
    layout = pick_layout(brief.ratio, brief.layout)
    preset = PRESETS[preset_name]
    w, h = resolve_size(brief.ratio, layout)

    base = paint.v_gradient((w, h), preset.top, preset.bottom).convert("RGBA")
    base = _art(base, preset, layout, brief.seed)
    base = draw_type(base, brief, preset, layout)
    rgb = paint.vignette(paint.grain_rgb(base, preset.grain, brief.seed))

    out_path = os.path.abspath(brief.out)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    rgb.save(out_path)
    return "%s (%sx%s) preset=%s layout=%s" % (out_path, w, h, preset_name, layout)


def render_pack(
    out_dir: str,
    date: str = "",
    brand: str = "橦云异梦",
    title: str = "每日速览",
    sub: str = "",
    bullets: list[str] = None,
    quote: str = "",
    author: str = "",
    dividers: list[tuple[str, str, str]] = None,
    preset: str = "auto",
    seed: int = 42,
) -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    results = {}

    # 1. Feed Cover (公众号封面 2.35:1)
    feed_path = os.path.join(out_dir, "01_cover_feed.png")
    feed_brief = CoverBrief(
        title=title,
        brand=brand,
        date=date,
        sub=sub,
        out=feed_path,
        layout="feed",
        ratio="2.35:1",
        preset=preset,
        seed=seed,
    )
    render_cover(feed_brief)
    results["cover_feed"] = feed_path

    # 2. Masthead (正文刊头 4:3)
    masthead_path = os.path.join(out_dir, "02_masthead.png")
    masthead_brief = CoverBrief(
        title=title,
        brand=brand,
        date=date,
        sub=sub,
        kicker=sub,
        out=masthead_path,
        layout="editorial",
        ratio="4:3",
        preset=preset,
        seed=seed,
    )
    render_cover(masthead_brief)
    results["masthead"] = masthead_path

    # 3. Summary Bullet Card (速览摘要清单卡 4:3)
    if bullets:
        bullet_path = os.path.join(out_dir, "03_summary_card.png")
        bullet_brief = CoverBrief(
            title="今日核心要闻速览",
            brand=brand,
            date=date,
            bullets=bullets,
            out=bullet_path,
            layout="bullet",
            ratio="4:3",
            preset=preset,
            seed=seed,
        )
        render_cover(bullet_brief)
        results["summary_card"] = bullet_path

    # 4. Dividers (正文章节分割条 4:1)
    if dividers:
        for idx, item in enumerate(dividers):
            num = item[0] if len(item) > 0 else ("%02d" % (idx + 1))
            sec_title = item[1] if len(item) > 1 else ("章节 %s" % num)
            sec_sub = item[2] if len(item) > 2 else ""
            div_path = os.path.join(out_dir, "04_divider_%02d.png" % (idx + 1))
            div_brief = CoverBrief(
                title=sec_title,
                sub=sec_sub,
                num=num,
                brand=brand,
                out=div_path,
                layout="divider",
                ratio="4:1",
                preset=preset,
                seed=seed + idx * 5,
            )
            render_cover(div_brief)
            results["divider_%02d" % (idx + 1)] = div_path

    # 5. Quote Card (金句卡 / 箴言卡 1:1)
    if quote:
        quote_path = os.path.join(out_dir, "05_quote_card.png")
        quote_brief = CoverBrief(
            quote=quote,
            author=author,
            brand=brand,
            date=date,
            out=quote_path,
            layout="quote",
            ratio="1:1",
            preset=preset,
            seed=seed + 9,
        )
        render_cover(quote_brief)
        results["quote_card"] = quote_path

    # 6. Share Square (1:1 朋友圈分享卡)
    square_path = os.path.join(out_dir, "06_share_square.png")
    square_brief = CoverBrief(
        title=title,
        brand=brand,
        date=date,
        sub=sub or quote,
        out=square_path,
        layout="square",
        ratio="1:1",
        preset=preset,
        seed=seed,
    )
    render_cover(square_brief)
    results["share_square"] = square_path

    # 7. Daily Briefing (竖版简报 3:4)
    briefing_path = os.path.join(out_dir, "07_briefing.png")
    briefing_brief = CoverBrief(
        title=title,
        brand=brand,
        date=date,
        sub=sub,
        bullets=bullets or _default_briefs(),
        out=briefing_path,
        layout="briefing",
        ratio="3:4",
        preset=preset,
        seed=seed,
    )
    render_cover(briefing_brief)
    results["briefing"] = briefing_path

    return results
