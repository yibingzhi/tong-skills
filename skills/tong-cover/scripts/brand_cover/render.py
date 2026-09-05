from __future__ import annotations

import os
import random
import re
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

from . import fonts, paint
from .presets import PRESETS, RATIOS, Preset, parse_calendar, pick_layout, pick_preset


def _box_dot(cx: float, cy: float, r: float):
    return [int(cx - r), int(cy - r), int(cx + r), int(cy + r)]


DEFAULT_BRAND = os.getenv("TONG_BRAND", "橦云异梦")


@dataclass
class CoverBrief:
    title: str = "每日速览"
    out: str = "out/cover.png"
    brand: str = DEFAULT_BRAND
    date: str = ""
    kicker: str = ""
    sub: str = ""
    preset: str = "auto"
    theme: str = "celestial"
    layout: str = "auto"
    ratio: str = "auto"
    seed: int = 42
    num: str = "01"
    quote: str = ""
    author: str = ""
    source: str = ""
    style: str = "auto"
    highlight: str = ""
    tag: str = ""
    bullets: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def resolve_size(ratio: str, layout: str = "editorial") -> tuple[int, int]:
    if ratio and ratio != "auto" and ratio in RATIOS:
        return RATIOS[ratio]
    if ratio and ratio != "auto" and ":" in ratio:
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
    if layout == "square":
        return RATIOS["1:1"]
    if layout == "quote":
        return RATIOS["3:4"]
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
    if not brief.brand:
        return y
    brand_text = brief.brand
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


_NON_STARTERS = frozenset("，。！？、；：）》”’」』】…—～·%-,.:;!?)]}>")
_NON_ENDERS = frozenset("（《“‘「『【[({<")


def _parse_quote_tokens(quote: str, highlight: str = "") -> list[tuple[str, bool]]:
    text = (quote or "流水不争先，争的是滔滔不绝。").strip()
    if not text:
        return [("", False)]

    # If markdown-style ==highlight== exists
    if "==" in text:
        raw_parts = re.split(r"(==.*?==)", text)
        tokens: list[tuple[str, bool]] = []
        for p in raw_parts:
            if not p:
                continue
            if p.startswith("==") and p.endswith("==") and len(p) >= 4:
                inner = p[2:-2]
                if inner:
                    tokens.append((inner, True))
            else:
                tokens.append((p, False))
        return tokens or [(text, False)]

    # If explicit highlight keyword provided
    if highlight and highlight in text:
        tokens = []
        remaining = text
        while highlight in remaining:
            idx = remaining.find(highlight)
            if idx > 0:
                tokens.append((remaining[:idx], False))
            tokens.append((highlight, True))
            remaining = remaining[idx + len(highlight):]
        if remaining:
            tokens.append((remaining, False))
        return tokens

    return [(text, False)]


def _wrap_quote_tokens(
    draw: ImageDraw.ImageDraw,
    tokens: list[tuple[str, bool]],
    font,
    max_width: float,
    max_lines: int = 6,
) -> list[list[tuple[str, bool]]]:
    chars: list[tuple[str, bool]] = []
    for text, is_hl in tokens:
        for ch in text:
            chars.append((ch, is_hl))
    if not chars:
        return [[("", False)]]

    lines: list[list[tuple[str, bool]]] = []
    cur_line: list[tuple[str, bool]] = []

    def line_w(line: list[tuple[str, bool]]) -> float:
        s = "".join(c for c, _ in line)
        return fonts.text_size(draw, s, font)[0]

    for ch, is_hl in chars:
        trial = cur_line + [(ch, is_hl)]
        tw = line_w(trial)

        if tw <= max_width or not cur_line:
            cur_line.append((ch, is_hl))
        else:
            if ch in _NON_STARTERS and len(cur_line) > 1:
                prev = cur_line.pop()
                lines.append(cur_line)
                cur_line = [prev, (ch, is_hl)]
            else:
                lines.append(cur_line)
                cur_line = [(ch, is_hl)]

        if len(lines) >= max_lines:
            break

    if cur_line and len(lines) < max_lines:
        lines.append(cur_line)

    merged_lines: list[list[tuple[str, bool]]] = []
    for line in lines:
        merged: list[tuple[str, bool]] = []
        for ch, is_hl in line:
            if merged and merged[-1][1] == is_hl:
                merged[-1] = (merged[-1][0] + ch, is_hl)
            else:
                merged.append((ch, is_hl))
        merged_lines.append(merged)

    return merged_lines


def _fit_quote_tokens(
    draw: ImageDraw.ImageDraw,
    tokens: list[tuple[str, bool]],
    font_kind: str,
    start_size: float,
    max_w: float,
    max_h: float,
    max_lines: int = 5,
):
    size = int(start_size)
    min_size = 20
    while size >= min_size:
        font = fonts.load_font(font_kind, size)
        lines = _wrap_quote_tokens(draw, tokens, font, max_w, max_lines=max_lines)
        single_h = fonts.text_size(draw, "国", font)[1]
        line_height = single_h * 1.58
        total_h = line_height * len(lines)
        if total_h <= max_h:
            return font, lines, line_height, single_h
        size -= 2
    font = fonts.load_font(font_kind, min_size)
    lines = _wrap_quote_tokens(draw, tokens, font, max_w, max_lines=max_lines)
    single_h = fonts.text_size(draw, "国", font)[1]
    return font, lines, single_h * 1.58, single_h


def _quote_date_str(brief: CoverBrief) -> tuple[str, str]:
    from datetime import datetime
    now = datetime.now()
    if brief.date:
        m, d, w_cn, en_date, _ = parse_calendar(brief.date)
        if m and d:
            w_short = en_date.split(" · ")[0] if " · " in en_date else (w_cn or "SAT")
            return "%02d.%02d" % (m, d), w_short
        return brief.date, ""
    w_en = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"][now.weekday()]
    return "%04d.%02d.%02d" % (now.year, now.month, now.day), w_en


def _resolve_quote_style(style: str, preset_name: str) -> str:
    if style and style != "auto":
        s = style.lower()
        if s in ("paper", "editorial", "highlight", "dark", "cinema", "polaroid", "tweet"):
            return s
    if preset_name in ("dusk", "ink", "ember"):
        return "dark"
    if preset_name in ("twilight", "dawn"):
        return "editorial"
    if preset_name == "frost":
        return "highlight"
    return "paper"


def _draw_token_line(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    line: list[tuple[str, bool]],
    font,
    text_color: tuple,
    style: str,
    accent: tuple,
    single_h: float,
    has_any_highlight: bool = False,
) -> float:
    cur_x = x
    # First pass: draw highlight backgrounds behind text
    for t, is_hl in line:
        tw, _ = fonts.text_size(draw, t, font)
        should_highlight = is_hl or (style == "highlight" and not has_any_highlight)
        if should_highlight:
            if style == "highlight":
                d_y0 = y + single_h * 0.40
                d_y1 = y + single_h * 1.05
                draw.rounded_rectangle(
                    [int(cur_x - 3), int(d_y0), int(cur_x + tw + 3), int(d_y1)],
                    radius=3,
                    fill=(255, 235, 59, 195 if is_hl else 140),
                )
            elif style in ("paper", "polaroid"):
                d_y0 = y + single_h * 0.52
                d_y1 = y + single_h * 1.04
                draw.rounded_rectangle(
                    [int(cur_x - 2), int(d_y0), int(cur_x + tw + 2), int(d_y1)],
                    radius=2,
                    fill=(245, 205, 125, 175),
                )
            elif style == "dark":
                d_y0 = y + single_h * 0.08
                d_y1 = y + single_h * 0.98
                draw.rounded_rectangle(
                    [int(cur_x - 4), int(d_y0), int(cur_x + tw + 4), int(d_y1)],
                    radius=4,
                    fill=accent + (55,),
                    outline=accent + (210,),
                    width=1,
                )
            elif style == "editorial":
                d_y0 = y + single_h * 0.08
                d_y1 = y + single_h * 0.98
                draw.rectangle([int(cur_x - 3), int(d_y0), int(cur_x + tw + 3), int(d_y1)], fill=accent + (255,))
            elif style == "cinema":
                d_y0 = y + single_h * 0.86
                d_y1 = y + single_h * 1.06
                draw.rounded_rectangle([int(cur_x - 2), int(d_y0), int(cur_x + tw + 2), int(d_y1)], radius=2, fill=(255, 238, 128, 230))
            elif style == "tweet":
                d_y0 = y + single_h * 0.45
                d_y1 = y + single_h * 1.02
                draw.rounded_rectangle([int(cur_x - 3), int(d_y0), int(cur_x + tw + 3), int(d_y1)], radius=3, fill=(195, 230, 255, 210))
        cur_x += tw

    # Second pass: draw text glyphs
    cur_x = x
    for t, is_hl in line:
        tw, _ = fonts.text_size(draw, t, font)
        c = text_color
        if is_hl and style in ("editorial", "dark", "cinema"):
            c = (255, 255, 255, 255)
        fonts.draw_text_measured(draw, (cur_x, y), t, font, c)
        cur_x += tw

    return cur_x


def _render_quote_paper(brief: CoverBrief, preset: Preset, size: tuple[int, int]) -> Image.Image:
    w, h = size
    unit = min(w, h)

    # 1. Warm parchment canvas
    base = paint.v_gradient((w, h), (244, 240, 232), (235, 229, 218)).convert("RGBA")
    base = paint.grain_rgb(base, 0.045, brief.seed).convert("RGBA")

    # 2. Card container
    card_box = [int(w * 0.075), int(h * 0.065), int(w * 0.925), int(h * 0.935)]
    cw = card_box[2] - card_box[0]
    ch = card_box[3] - card_box[1]
    radius = int(unit * 0.024)

    shadow = paint.card_drop_shadow((w, h), card_box, radius=radius, blur=int(unit * 0.024), offset_y=int(h * 0.014), color=(70, 60, 50), alpha=45)
    base = Image.alpha_composite(base, shadow)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(card_box, radius=radius, fill=(253, 251, 246, 255), outline=(224, 218, 206, 255), width=1)

    # 3. Header inside card
    pad_x = int(cw * 0.08)
    hx = card_box[0] + pad_x
    hy = card_box[1] + int(ch * 0.065)
    hr_x = card_box[2] - pad_x

    brand_str = brief.brand
    if brand_str:
        bf = fonts.load_font("fangsong", max(15, int(unit * 0.028)))
        fonts.draw_text_measured(draw, (hx, hy), fonts.letterspace(brand_str, "  "), bf, (92, 80, 72, 255))

    dt, wk = _quote_date_str(brief)
    date_label = f"{dt} · {wk}" if wk else dt
    df = fonts.load_font("sans_light", max(12, int(unit * 0.020)))
    dw, dh = fonts.text_size(draw, date_label, df)
    fonts.draw_text_measured(draw, (hr_x - dw, hy + int(dh * 0.2)), date_label, df, (148, 138, 130, 255))

    rule_y = hy + max(16, int(unit * 0.038))
    draw.line([(int(hx), int(rule_y)), (int(hr_x), int(rule_y))], fill=(228, 222, 212, 255), width=1)

    # 4. Measure body & sub for optical centering
    tokens = _parse_quote_tokens(brief.quote, brief.highlight)
    has_hl = any(is_hl for _, is_hl in tokens)
    q_max_w = hr_x - hx - int(unit * 0.02)
    q_max_h = ch * 0.52

    start_sz = unit * (0.064 if len(brief.quote or "") < 25 else (0.056 if len(brief.quote or "") < 50 else 0.048))
    q_font, q_lines, line_height, single_h = _fit_quote_tokens(draw, tokens, "serif", start_sz, q_max_w, q_max_h)
    quote_h = len(q_lines) * line_height

    sub_text = brief.sub or brief.kicker
    sub_font = fonts.load_font("sans", max(13, int(unit * 0.024)))
    wrapped_sub = wrap_title(draw, sub_text, sub_font, q_max_w - int(unit * 0.05), max_lines=3) if sub_text else []
    sub_single_h = fonts.text_size(draw, "国", sub_font)[1]
    sub_gap = max(18, int(unit * 0.034))
    sub_block_h = (len(wrapped_sub) * sub_single_h * 1.45 + sub_gap) if wrapped_sub else 0

    total_content_h = quote_h + sub_block_h
    body_top = rule_y + max(20, int(unit * 0.040))
    fy = card_box[3] - int(ch * 0.09)
    body_bottom = fy - max(20, int(unit * 0.040))
    available_h = body_bottom - body_top
    center_offset = max(0, int((available_h - total_content_h) * 0.35))

    q_top = body_top + center_offset

    # Quotation glyph
    q_glyph_font = fonts.load_font("en_serif", max(36, int(unit * 0.16)))
    fonts.draw_text_measured(draw, (hx - int(unit * 0.006), q_top - int(unit * 0.042)), "“", q_glyph_font, (205, 180, 160, 120))

    # Render Quote
    cur_y = q_top
    for line in q_lines:
        _draw_token_line(draw, hx + int(unit * 0.015), cur_y, line, q_font, (38, 34, 30, 255), "paper", preset.accent, single_h, has_hl)
        cur_y += line_height

    # Render Sub / Note
    if wrapped_sub:
        sub_y = cur_y + sub_gap
        line_box_y0 = sub_y
        line_box_y1 = sub_y + len(wrapped_sub) * sub_single_h * 1.45
        draw.line([(int(hx + unit * 0.015), int(line_box_y0)), (int(hx + unit * 0.015), int(line_box_y1))], fill=preset.accent + (180,), width=2)
        sy = sub_y
        for sline in wrapped_sub:
            fonts.draw_text_measured(draw, (hx + int(unit * 0.035), sy), sline, sub_font, (105, 96, 88, 255))
            sy += sub_single_h * 1.45

    # 6. Footer
    author_text = ("—— " + brief.author) if brief.author else (("—— %s" % brief.brand) if brief.brand else "")
    if brief.source:
        prefix = (author_text + " · ") if author_text else ""
        author_text = prefix + ("《%s》" % brief.source.strip("《》"))
    if author_text:
        af = fonts.load_font("sans", max(13, int(unit * 0.024)))
        fonts.draw_text_measured(draw, (hx + int(unit * 0.015), fy), author_text, af, (82, 74, 68, 255))

    # Stamp (only if brand is provided)
    if brief.brand:
        seal_font = fonts.load_font("kai", max(16, int(unit * 0.034)))
        seal_r = max(20, int(unit * 0.040))
        stamp = paint.seal_stamp((w, h), int(hr_x - unit * 0.04), int(fy + unit * 0.01), seal_r, brief.brand[0], preset.accent, seal_font)
        overlay = Image.alpha_composite(overlay, stamp)

    return Image.alpha_composite(base, overlay)


def _render_quote_editorial(brief: CoverBrief, preset: Preset, size: tuple[int, int]) -> Image.Image:
    w, h = size
    unit = min(w, h)

    # 1. Canvas
    base = Image.new("RGBA", (w, h), (248, 248, 250, 255))
    base = paint.grain_rgb(base, 0.03, brief.seed).convert("RGBA")

    # 2. Editorial frame card
    card_box = [int(w * 0.065), int(h * 0.055), int(w * 0.935), int(h * 0.945)]
    cw = card_box[2] - card_box[0]
    ch = card_box[3] - card_box[1]
    radius = int(unit * 0.014)

    shadow = paint.card_drop_shadow((w, h), card_box, radius=radius, blur=int(unit * 0.018), offset_y=int(h * 0.012), color=(20, 20, 28), alpha=35)
    base = Image.alpha_composite(base, shadow)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(card_box, radius=radius, fill=(255, 255, 255, 255), outline=(24, 24, 28, 255), width=2)

    # 3. Header
    pad_x = int(cw * 0.075)
    hx = card_box[0] + pad_x
    hy = card_box[1] + int(ch * 0.055)
    hr_x = card_box[2] - pad_x

    tag_str = (brief.tags[0] if brief.tags else "") or (brief.tag or "认知洞察 · INSIGHT")
    tag_font = fonts.load_font("sans", max(11, int(unit * 0.019)))
    tw, th = fonts.text_size(draw, tag_str, tag_font)
    chip_pad_x, chip_pad_y = max(8, int(unit * 0.012)), max(4, int(unit * 0.006))
    chip_rect = [int(hx), int(hy), int(hx + tw + chip_pad_x * 2), int(hy + th + chip_pad_y * 2)]
    draw.rounded_rectangle(chip_rect, radius=int((th + chip_pad_y * 2) * 0.3), fill=(24, 24, 28, 255))
    fonts.draw_text_measured(draw, (hx + chip_pad_x, hy + chip_pad_y), tag_str, tag_font, (255, 255, 255, 255))

    dt, _ = _quote_date_str(brief)
    issue_label = f"ISSUE // {dt}"
    issue_font = fonts.load_font("sans_light", max(11, int(unit * 0.018)))
    iw, ih = fonts.text_size(draw, issue_label, issue_font)
    fonts.draw_text_measured(draw, (hr_x - iw, hy + chip_pad_y), issue_label, issue_font, (120, 120, 126, 255))

    double_y = chip_rect[3] + max(12, int(unit * 0.024))
    draw.line([(int(hx), int(double_y)), (int(hr_x), int(double_y))], fill=(24, 24, 28, 255), width=2)
    draw.line([(int(hx), int(double_y + 4)), (int(hr_x), int(double_y + 4))], fill=(190, 190, 195, 255), width=1)

    # 4. Measure body & sub for optical centering
    tokens = _parse_quote_tokens(brief.quote, brief.highlight)
    has_hl = any(is_hl for _, is_hl in tokens)
    q_max_w = hr_x - hx
    q_max_h = ch * 0.52

    start_sz = unit * (0.066 if len(brief.quote or "") < 25 else (0.058 if len(brief.quote or "") < 50 else 0.048))
    q_font, q_lines, line_height, single_h = _fit_quote_tokens(draw, tokens, "headline", start_sz, q_max_w, q_max_h)
    quote_h = len(q_lines) * line_height

    sub_text = brief.sub or brief.kicker
    note_prefix = "NOTE // "
    nf = fonts.load_font("sans", max(12, int(unit * 0.020)))
    nw, _ = fonts.text_size(draw, note_prefix, nf)
    sub_font = fonts.load_font("sans_light", max(13, int(unit * 0.022)))
    wrapped_sub = wrap_title(draw, sub_text, sub_font, q_max_w - nw - int(unit * 0.02), max_lines=3) if sub_text else []
    sub_single_h = fonts.text_size(draw, "国", sub_font)[1]
    sub_gap = max(18, int(unit * 0.034))
    sub_block_h = (len(wrapped_sub) * sub_single_h * 1.40 + sub_gap) if wrapped_sub else 0

    total_content_h = quote_h + sub_block_h
    body_top = double_y + max(20, int(unit * 0.040))
    fy = card_box[3] - int(ch * 0.085)
    body_bottom = fy - max(20, int(unit * 0.040))
    available_h = body_bottom - body_top
    center_offset = max(0, int((available_h - total_content_h) * 0.35))

    q_top = body_top + center_offset

    cur_y = q_top
    for line in q_lines:
        _draw_token_line(draw, hx, cur_y, line, q_font, (18, 18, 22, 255), "editorial", preset.accent, single_h, has_hl)
        cur_y += line_height

    if wrapped_sub:
        sub_y = cur_y + sub_gap
        draw.line([(int(hx), int(sub_y - 8)), (int(hr_x), int(sub_y - 8))], fill=(225, 225, 230, 255), width=1)
        fonts.draw_text_measured(draw, (hx, sub_y), note_prefix, nf, preset.accent + (255,))
        sy = sub_y
        for sline in wrapped_sub:
            fonts.draw_text_measured(draw, (hx + nw, sy), sline, sub_font, (72, 72, 76, 255))
            sy += sub_single_h * 1.40

    # 6. Footer
    fy = card_box[3] - int(ch * 0.085)
    draw.line([(int(hx), int(fy - 12)), (int(hr_x), int(fy - 12))], fill=(220, 220, 225, 255), width=1)

    auth_label = "AUTHOR / SOURCE"
    alf = fonts.load_font("sans_light", max(10, int(unit * 0.016)))
    fonts.draw_text_measured(draw, (hx, fy), auth_label, alf, (135, 135, 142, 255))

    author_name = brief.author or brief.brand
    if brief.source:
        prefix = (author_name + " · ") if author_name else ""
        author_name = prefix + ("《%s》" % brief.source.strip("《》"))
    if not author_name:
        author_name = "QUOTATION"
    anf = fonts.load_font("headline", max(13, int(unit * 0.024)))
    fonts.draw_text_measured(draw, (hx, fy + max(12, int(unit * 0.020))), author_name, anf, (24, 24, 28, 255))

    # Barcode mockup
    bc_x = hr_x - int(unit * 0.14)
    rng = random.Random(brief.seed + 7)
    cur_bx = bc_x
    while cur_bx < hr_x:
        bw = rng.choice([1, 2, 3])
        draw.line([(int(cur_bx), int(fy + 2)), (int(cur_bx), int(fy + max(20, int(unit * 0.038))))], fill=(30, 30, 34, 255), width=bw)
        cur_bx += bw + rng.choice([2, 3, 4])

    ed_lab = "TONGSKILLS"
    ef = fonts.load_font("sans_light", max(9, int(unit * 0.014)))
    ew, _ = fonts.text_size(draw, ed_lab, ef)
    fonts.draw_text_measured(draw, (hr_x - ew, fy + max(24, int(unit * 0.042))), ed_lab, ef, (140, 140, 146, 255))

    return Image.alpha_composite(base, overlay)


def _render_quote_highlight(brief: CoverBrief, preset: Preset, size: tuple[int, int]) -> Image.Image:
    w, h = size
    unit = min(w, h)

    # 1. Warm reading background
    base = Image.new("RGBA", (w, h), (247, 244, 237, 255))
    base = paint.grain_rgb(base, 0.035, brief.seed).convert("RGBA")

    # 2. Reading Card
    card_box = [int(w * 0.070), int(h * 0.060), int(w * 0.930), int(h * 0.940)]
    cw = card_box[2] - card_box[0]
    ch = card_box[3] - card_box[1]
    radius = int(unit * 0.022)

    shadow = paint.card_drop_shadow((w, h), card_box, radius=radius, blur=int(unit * 0.022), offset_y=int(h * 0.012), color=(55, 45, 35), alpha=38)
    base = Image.alpha_composite(base, shadow)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(card_box, radius=radius, fill=(255, 255, 255, 255), outline=(232, 228, 218, 255), width=1)

    # 3. Header
    pad_x = int(cw * 0.08)
    hx = card_box[0] + pad_x
    hy = card_box[1] + int(ch * 0.060)
    hr_x = card_box[2] - pad_x

    reader_header = "精选划线 · 深度阅读"
    rhf = fonts.load_font("sans", max(13, int(unit * 0.024)))
    fonts.draw_text_measured(draw, (hx, hy), reader_header, rhf, (88, 82, 76, 255))

    chip_text = "999+ 人划线"
    cf = fonts.load_font("sans", max(11, int(unit * 0.018)))
    cw_txt, ch_txt = fonts.text_size(draw, chip_text, cf)
    cp_x, cp_y = max(8, int(unit * 0.012)), max(3, int(unit * 0.005))
    chip_box = [int(hr_x - cw_txt - cp_x * 2), int(hy), int(hr_x), int(hy + ch_txt + cp_y * 2)]
    draw.rounded_rectangle(chip_box, radius=int((ch_txt + cp_y * 2) * 0.4), fill=(255, 243, 205, 255))
    fonts.draw_text_measured(draw, (chip_box[0] + cp_x, hy + cp_y), chip_text, cf, (175, 105, 18, 255))

    rule_y = chip_box[3] + max(12, int(unit * 0.022))
    draw.line([(int(hx), int(rule_y)), (int(hr_x), int(rule_y))], fill=(240, 236, 226, 255), width=1)

    # 4. Measure body & sub for optical centering
    tokens = _parse_quote_tokens(brief.quote, brief.highlight)
    has_hl = any(is_hl for _, is_hl in tokens)
    q_max_w = hr_x - hx
    q_max_h = ch * 0.50

    start_sz = unit * (0.062 if len(brief.quote or "") < 25 else (0.054 if len(brief.quote or "") < 50 else 0.046))
    q_font, q_lines, line_height, single_h = _fit_quote_tokens(draw, tokens, "serif", start_sz, q_max_w, q_max_h)
    quote_h = len(q_lines) * line_height

    sub_text = brief.sub or brief.kicker
    sub_font = fonts.load_font("sans", max(13, int(unit * 0.022)))
    wrapped_sub = wrap_title(draw, sub_text, sub_font, q_max_w - int(unit * 0.06), max_lines=3) if sub_text else []
    sub_single_h = fonts.text_size(draw, "国", sub_font)[1]
    sub_gap = max(18, int(unit * 0.034))
    note_h = int(sub_single_h * len(wrapped_sub) * 1.35 + unit * 0.06) if wrapped_sub else 0
    sub_block_h = (note_h + sub_gap) if wrapped_sub else 0

    total_content_h = quote_h + sub_block_h
    body_top = rule_y + max(20, int(unit * 0.040))
    fy = card_box[3] - int(ch * 0.085)
    body_bottom = fy - max(20, int(unit * 0.040))
    available_h = body_bottom - body_top
    center_offset = max(0, int((available_h - total_content_h) * 0.35))

    q_top = body_top + center_offset

    cur_y = q_top
    for line in q_lines:
        _draw_token_line(draw, hx, cur_y, line, q_font, (32, 32, 36, 255), "highlight", preset.accent, single_h, has_hl)
        cur_y += line_height

    if wrapped_sub:
        note_y = cur_y + sub_gap
        note_box = [int(hx), int(note_y), int(hr_x), int(note_y + note_h)]
        draw.rounded_rectangle(note_box, radius=int(unit * 0.012), fill=(254, 252, 240, 255), outline=(244, 236, 216, 255), width=1)
        draw.line([(note_box[0], note_box[1] + 2), (note_box[0], note_box[3] - 2)], fill=(240, 195, 60, 255), width=3)

        nh_font = fonts.load_font("sans", max(11, int(unit * 0.018)))
        fonts.draw_text_measured(draw, (hx + int(unit * 0.025), note_y + int(unit * 0.014)), "想法札记 · 深度共鸣", nh_font, (170, 115, 25, 255))
        sy = note_y + int(unit * 0.040)
        for sline in wrapped_sub:
            fonts.draw_text_measured(draw, (hx + int(unit * 0.025), sy), sline, sub_font, (80, 75, 70, 255))
            sy += sub_single_h * 1.35

    # 6. Footer
    fy = card_box[3] - int(ch * 0.085)
    draw.line([(int(hx), int(fy - 12)), (int(hr_x), int(fy - 12))], fill=(240, 236, 226, 255), width=1)

    book_title = ("《%s》" % brief.source.strip("《》")) if brief.source else "《思想录》"
    bf = fonts.load_font("serif", max(14, int(unit * 0.024)))
    fonts.draw_text_measured(draw, (hx, fy), book_title, bf, (35, 35, 38, 255))
    bw, _ = fonts.text_size(draw, book_title, bf)

    auth = brief.author or brief.brand
    if auth:
        af = fonts.load_font("sans_light", max(12, int(unit * 0.020)))
        fonts.draw_text_measured(draw, (hx + bw + max(8, int(unit * 0.015)), fy + max(1, int(unit * 0.002))), auth, af, (120, 115, 108, 255))

    brand_tag = brief.brand if brief.brand else ""
    page_label = f"划线存念 · {brand_tag}" if brand_tag else "精选划线 · 存念"
    pf = fonts.load_font("sans_light", max(11, int(unit * 0.017)))
    pw, _ = fonts.text_size(draw, page_label, pf)
    fonts.draw_text_measured(draw, (hr_x - pw, fy + max(1, int(unit * 0.002))), page_label, pf, (155, 148, 138, 255))

    return Image.alpha_composite(base, overlay)


def _render_quote_dark(brief: CoverBrief, preset: Preset, size: tuple[int, int]) -> Image.Image:
    w, h = size
    unit = min(w, h)

    # 1. Obsidian night gradient canvas
    base = paint.v_gradient((w, h), (14, 16, 22), (20, 24, 34)).convert("RGBA")
    base = paint.grain_rgb(base, 0.05, brief.seed).convert("RGBA")

    # Faint corner glow
    glow = paint.radial_glow((w, h), int(w * 0.85), int(h * 0.15), int(unit * 0.35), preset.accent, 45)
    base = Image.alpha_composite(base, glow)

    # 2. Dark glass floating card
    card_box = [int(w * 0.070), int(h * 0.060), int(w * 0.930), int(h * 0.940)]
    cw = card_box[2] - card_box[0]
    ch = card_box[3] - card_box[1]
    radius = int(unit * 0.024)

    shadow = paint.card_drop_shadow((w, h), card_box, radius=radius, blur=int(unit * 0.028), offset_y=int(h * 0.016), color=(0, 0, 0), alpha=130)
    base = Image.alpha_composite(base, shadow)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(card_box, radius=radius, fill=(26, 30, 42, 238), outline=(255, 255, 255, 30), width=1)

    # 3. Header
    pad_x = int(cw * 0.08)
    hx = card_box[0] + pad_x
    hy = card_box[1] + int(ch * 0.060)
    hr_x = card_box[2] - pad_x

    # Terminal dots
    dot_r = max(4, int(unit * 0.007))
    for i, dot_color in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        dx = hx + i * int(dot_r * 2.8)
        draw.ellipse([dx, hy + 2, dx + dot_r * 2, hy + 2 + dot_r * 2], fill=dot_color + (240,))

    term_label = "// TONG_KERNEL :: DAILY QUOTE"
    tmf = fonts.load_font("sans", max(11, int(unit * 0.018)))
    fonts.draw_text_measured(draw, (hx + int(dot_r * 10), hy), term_label, tmf, (140, 158, 182, 255))

    dt, _ = _quote_date_str(brief)
    date_label = f"● {dt}"
    df = fonts.load_font("sans", max(11, int(unit * 0.018)))
    dw, _ = fonts.text_size(draw, date_label, df)
    fonts.draw_text_measured(draw, (hr_x - dw, hy), date_label, df, preset.accent + (240,))

    rule_y = hy + max(16, int(unit * 0.032))
    draw.line([(int(hx), int(rule_y)), (int(hr_x), int(rule_y))], fill=(255, 255, 255, 24), width=1)

    # 4. Measure body & sub for optical centering
    tokens = _parse_quote_tokens(brief.quote, brief.highlight)
    has_hl = any(is_hl for _, is_hl in tokens)
    q_max_w = hr_x - hx
    q_max_h = ch * 0.50

    start_sz = unit * (0.064 if len(brief.quote or "") < 25 else (0.056 if len(brief.quote or "") < 50 else 0.048))
    q_font, q_lines, line_height, single_h = _fit_quote_tokens(draw, tokens, "headline", start_sz, q_max_w, q_max_h)
    quote_h = len(q_lines) * line_height

    sub_text = brief.sub or brief.kicker
    pfx = "> ANALYSIS: "
    pf = fonts.load_font("sans", max(12, int(unit * 0.020)))
    pw, _ = fonts.text_size(draw, pfx, pf)
    sub_font = fonts.load_font("sans_light", max(13, int(unit * 0.022)))
    wrapped_sub = wrap_title(draw, sub_text, sub_font, q_max_w - pw, max_lines=3) if sub_text else []
    sub_single_h = fonts.text_size(draw, "国", sub_font)[1]
    sub_gap = max(18, int(unit * 0.034))
    sub_block_h = (len(wrapped_sub) * sub_single_h * 1.40 + sub_gap) if wrapped_sub else 0

    total_content_h = quote_h + sub_block_h
    body_top = rule_y + max(20, int(unit * 0.040))
    fy = card_box[3] - int(ch * 0.085)
    body_bottom = fy - max(20, int(unit * 0.040))
    available_h = body_bottom - body_top
    center_offset = max(0, int((available_h - total_content_h) * 0.35))

    q_top = body_top + center_offset

    q_glyph_font = fonts.load_font("en_serif", max(36, int(unit * 0.16)))
    fonts.draw_text_measured(draw, (hx - int(unit * 0.006), q_top - int(unit * 0.042)), "“", q_glyph_font, preset.accent + (90,))

    cur_y = q_top
    for line in q_lines:
        _draw_token_line(draw, hx, cur_y, line, q_font, (246, 248, 252, 255), "dark", preset.accent, single_h, has_hl)
        cur_y += line_height

    if wrapped_sub:
        sub_y = cur_y + sub_gap
        draw.line([(int(hx), int(sub_y - 8)), (int(hr_x), int(sub_y - 8))], fill=(255, 255, 255, 20), width=1)
        fonts.draw_text_measured(draw, (hx, sub_y), pfx, pf, preset.accent + (240,))
        sy = sub_y
        for sline in wrapped_sub:
            fonts.draw_text_measured(draw, (hx + pw, sy), sline, sub_font, (156, 168, 186, 255))
            sy += sub_single_h * 1.40

    # 6. Footer
    fy = card_box[3] - int(ch * 0.085)
    draw.line([(int(hx), int(fy - 12)), (int(hr_x), int(fy - 12))], fill=(255, 255, 255, 22), width=1)

    author_str = ("AUTHOR // " + brief.author) if brief.author else (("KERNEL // " + brief.brand) if brief.brand else "KERNEL // INSIGHT")
    if brief.source:
        author_str += (" · 《%s》" % brief.source.strip("《》"))
    af = fonts.load_font("sans", max(12, int(unit * 0.020)))
    fonts.draw_text_measured(draw, (hx, fy), author_str, af, (160, 175, 195, 255))

    v_tag = "[ VERIFIED INSIGHT ]"
    vf = fonts.load_font("sans", max(10, int(unit * 0.016)))
    vw, vh = fonts.text_size(draw, v_tag, vf)
    v_pad_x, v_pad_y = max(6, int(unit * 0.010)), max(3, int(unit * 0.005))
    v_rect = [int(hr_x - vw - v_pad_x * 2), int(fy), int(hr_x), int(fy + vh + v_pad_y * 2)]
    draw.rounded_rectangle(v_rect, radius=3, outline=preset.accent + (180,), width=1)
    fonts.draw_text_measured(draw, (v_rect[0] + v_pad_x, fy + v_pad_y), v_tag, vf, preset.accent + (230,))

    return Image.alpha_composite(base, overlay)


def _render_quote_cinema(brief: CoverBrief, preset: Preset, size: tuple[int, int]) -> Image.Image:
    w, h = size
    unit = min(w, h)

    # 1. Cinematic dark background with slight vignette
    base = paint.v_gradient((w, h), (14, 16, 22), (8, 10, 14)).convert("RGBA")
    base = paint.grain_rgb(base, 0.045, brief.seed).convert("RGBA")

    # 2. Outer letterbox / cinema frame
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    pad_x = int(w * 0.075)
    pad_y = int(h * 0.055)

    # REC dot
    rec_r = max(4, int(unit * 0.009))
    rec_x = pad_x
    rec_y = pad_y + int(unit * 0.015)
    draw.ellipse([rec_x - rec_r, rec_y - rec_r, rec_x + rec_r, rec_y + rec_r], fill=(238, 48, 48, 255))

    rec_f = fonts.load_font("sans", max(11, int(unit * 0.018)))
    fonts.draw_text_measured(draw, (rec_x + rec_r * 2 + 6, rec_y - rec_r * 1.5), "REC", rec_f, (238, 48, 48, 255))

    mid_f = fonts.load_font("sans_light", max(11, int(unit * 0.018)))
    mid_tag = "CINEMA ARCHIVE // 4K SCOPE"
    mw, _ = fonts.text_size(draw, mid_tag, mid_f)
    fonts.draw_text_measured(draw, (int(w / 2 - mw / 2), rec_y - rec_r * 1.5), mid_tag, mid_f, (140, 150, 165, 200))

    time_str = "24 FPS  01:42:18"
    tw, _ = fonts.text_size(draw, time_str, mid_f)
    fonts.draw_text_measured(draw, (w - pad_x - tw, rec_y - rec_r * 1.5), time_str, mid_f, (160, 170, 185, 220))

    draw.line([(pad_x, rec_y + int(unit * 0.035)), (w - pad_x, rec_y + int(unit * 0.035))], fill=(255, 255, 255, 28), width=1)

    # Cinema Card Container (Floating view pane with subtle edge glow)
    card_box = [int(pad_x), int(h * 0.12), int(w - pad_x), int(h * 0.88)]
    cw = card_box[2] - card_box[0]
    ch = card_box[3] - card_box[1]

    draw.rectangle(card_box, outline=(255, 255, 255, 30), width=1)

    c_len = int(unit * 0.024)
    for bx, by, dx, dy in (
        (card_box[0], card_box[1], 1, 1),
        (card_box[2], card_box[1], -1, 1),
        (card_box[0], card_box[3], 1, -1),
        (card_box[2], card_box[3], -1, -1),
    ):
        draw.line([(bx, by), (bx + dx * c_len, by)], fill=(255, 220, 90, 220), width=2)
        draw.line([(bx, by), (bx, by + dy * c_len)], fill=(255, 220, 90, 220), width=2)

    tokens = _parse_quote_tokens(brief.quote, brief.highlight)
    has_hl = any(is_hl for _, is_hl in tokens)
    q_max_w = cw - int(unit * 0.12)
    q_max_h = ch * 0.48

    start_sz = unit * (0.062 if len(brief.quote or "") < 25 else (0.054 if len(brief.quote or "") < 50 else 0.046))
    q_font, q_lines, line_height, single_h = _fit_quote_tokens(draw, tokens, "sans", start_sz, q_max_w, q_max_h)
    quote_h = len(q_lines) * line_height

    sub_text = brief.sub or brief.kicker
    sub_font = fonts.load_font("sans", max(13, int(unit * 0.022)))
    wrapped_sub = wrap_title(draw, sub_text, sub_font, q_max_w, max_lines=2) if sub_text else []
    sub_single_h = fonts.text_size(draw, "国", sub_font)[1]
    sub_gap = max(20, int(unit * 0.036))
    sub_block_h = (len(wrapped_sub) * sub_single_h * 1.45 + sub_gap) if wrapped_sub else 0

    total_content_h = quote_h + sub_block_h
    body_top = card_box[1] + int(unit * 0.04)
    body_bottom = card_box[3] - int(unit * 0.08)
    available_h = body_bottom - body_top
    center_offset = max(0, int((available_h - total_content_h) * 0.42))

    q_top = body_top + center_offset

    cur_y = q_top
    subtitle_yellow = (255, 238, 128, 255)
    for line in q_lines:
        line_w = sum(fonts.text_size(draw, t, q_font)[0] for t, _ in line)
        lx = int(w / 2 - line_w / 2)
        _draw_token_line(draw, lx + 2, cur_y + 2, line, q_font, (0, 0, 0, 200), "cinema", (0, 0, 0), single_h, has_hl)
        _draw_token_line(draw, lx, cur_y, line, q_font, subtitle_yellow, "cinema", (255, 238, 128), single_h, has_hl)
        cur_y += line_height

    if wrapped_sub:
        sy = cur_y + sub_gap
        for sline in wrapped_sub:
            sw, _ = fonts.text_size(draw, sline, sub_font)
            sx = int(w / 2 - sw / 2)
            fonts.draw_text_measured(draw, (sx, sy), sline, sub_font, (170, 182, 198, 220))
            sy += sub_single_h * 1.45

    fy = card_box[3] - int(ch * 0.07)
    draw.line([(card_box[0] + 16, fy - 10), (card_box[2] - 16, fy - 10)], fill=(255, 255, 255, 22), width=1)

    src_str = "“ %s ”" % (brief.source or "MEMORABLE QUOTE")
    if brief.author:
        src_str = ("%s · " % brief.author) + src_str
    sf = fonts.load_font("sans", max(11, int(unit * 0.020)))
    fonts.draw_text_measured(draw, (card_box[0] + 20, fy), src_str, sf, (150, 160, 175, 255))

    sprocket_str = "||||| | |||| | |||"
    sp_f = fonts.load_font("sans", max(10, int(unit * 0.018)))
    sp_w, _ = fonts.text_size(draw, sprocket_str, sp_f)
    fonts.draw_text_measured(draw, (card_box[2] - 20 - sp_w, fy), sprocket_str, sp_f, (255, 220, 90, 180))

    return Image.alpha_composite(base, overlay)


def _render_quote_polaroid(brief: CoverBrief, preset: Preset, size: tuple[int, int]) -> Image.Image:
    w, h = size
    unit = min(w, h)

    # 1. Warm studio desktop canvas
    base = paint.v_gradient((w, h), (238, 234, 226), (226, 220, 210)).convert("RGBA")
    base = paint.grain_rgb(base, 0.040, brief.seed).convert("RGBA")

    # 2. Classic Polaroid Frame: top/left/right 6%, bottom 20%
    card_box = [int(w * 0.075), int(h * 0.060), int(w * 0.925), int(h * 0.930)]
    cw = card_box[2] - card_box[0]
    ch = card_box[3] - card_box[1]
    radius = int(unit * 0.012)

    shadow = paint.card_drop_shadow((w, h), card_box, radius=radius, blur=int(unit * 0.026), offset_y=int(h * 0.016), color=(60, 50, 42), alpha=50)
    base = Image.alpha_composite(base, shadow)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(card_box, radius=radius, fill=(255, 254, 250, 255), outline=(220, 215, 205, 255), width=1)

    margin_top = int(ch * 0.055)
    margin_side = int(cw * 0.065)
    margin_bottom = int(ch * 0.200)

    photo_box = [
        int(card_box[0] + margin_side),
        int(card_box[1] + margin_top),
        int(card_box[2] - margin_side),
        int(card_box[3] - margin_bottom),
    ]
    pw = photo_box[2] - photo_box[0]
    ph = photo_box[3] - photo_box[1]

    draw.rounded_rectangle(photo_box, radius=max(2, int(radius * 0.5)), fill=(247, 244, 237, 255), outline=(228, 222, 210, 255), width=1)

    mk_len = int(unit * 0.016)
    for px, py, dx, dy in (
        (photo_box[0] + 8, photo_box[1] + 8, 1, 1),
        (photo_box[2] - 8, photo_box[1] + 8, -1, 1),
        (photo_box[0] + 8, photo_box[3] - 8, 1, -1),
        (photo_box[2] - 8, photo_box[3] - 8, -1, -1),
    ):
        draw.line([(px, py), (px + dx * mk_len, py)], fill=(200, 192, 178, 160), width=1)
        draw.line([(px, py), (px, py + dy * mk_len)], fill=(200, 192, 178, 160), width=1)

    tokens = _parse_quote_tokens(brief.quote, brief.highlight)
    has_hl = any(is_hl for _, is_hl in tokens)
    q_max_w = pw - int(unit * 0.08)
    q_max_h = ph * 0.58

    start_sz = unit * (0.062 if len(brief.quote or "") < 25 else (0.052 if len(brief.quote or "") < 50 else 0.044))
    q_font, q_lines, line_height, single_h = _fit_quote_tokens(draw, tokens, "serif", start_sz, q_max_w, q_max_h)
    quote_h = len(q_lines) * line_height

    sub_text = brief.sub or brief.kicker
    sub_font = fonts.load_font("fangsong", max(13, int(unit * 0.024)))
    wrapped_sub = wrap_title(draw, sub_text, sub_font, q_max_w, max_lines=2) if sub_text else []
    sub_single_h = fonts.text_size(draw, "国", sub_font)[1]
    sub_gap = max(16, int(unit * 0.030))
    sub_block_h = (len(wrapped_sub) * sub_single_h * 1.45 + sub_gap) if wrapped_sub else 0

    total_content_h = quote_h + sub_block_h
    available_h = ph - int(unit * 0.06)
    center_offset = max(0, int((available_h - total_content_h) * 0.40))

    q_top = photo_box[1] + int(unit * 0.03) + center_offset

    q_sym = fonts.load_font("serif", max(28, int(unit * 0.08)))
    fonts.draw_text_measured(draw, (photo_box[0] + int(unit * 0.04), q_top - int(unit * 0.03)), "“", q_sym, (168, 150, 136, 120))

    cur_y = q_top
    for line in q_lines:
        _draw_token_line(draw, photo_box[0] + int(unit * 0.04), cur_y, line, q_font, (48, 42, 36, 255), "polaroid", (245, 205, 125), single_h, has_hl)
        cur_y += line_height

    if wrapped_sub:
        sy = cur_y + sub_gap
        draw.line([(photo_box[0] + int(unit * 0.04), sy - 6), (photo_box[2] - int(unit * 0.04), sy - 6)], fill=(225, 218, 205, 200), width=1)
        for sline in wrapped_sub:
            fonts.draw_text_measured(draw, (photo_box[0] + int(unit * 0.04), sy), sline, sub_font, (120, 108, 98, 255))
            sy += sub_single_h * 1.45

    bottom_y = photo_box[3] + int((card_box[3] - photo_box[3]) * 0.30)

    author_str = ("— %s" % brief.author) if brief.author else (("— %s" % brief.brand) if brief.brand else "")
    if brief.source:
        prefix = (author_str + " · ") if author_str else ""
        author_str = prefix + ("《%s》" % brief.source.strip("《》"))
    if author_str:
        af = fonts.load_font("fangsong", max(14, int(unit * 0.026)))
        fonts.draw_text_measured(draw, (photo_box[0] + 4, bottom_y), author_str, af, (70, 60, 50, 255))

    dt, wk = _quote_date_str(brief)
    date_str = f"{dt} {wk}" if wk else dt
    df = fonts.load_font("sans", max(11, int(unit * 0.020)))
    dw, _ = fonts.text_size(draw, date_str, df)
    fonts.draw_text_measured(draw, (photo_box[2] - dw - 4, bottom_y + 2), date_str, df, (148, 136, 124, 255))

    if brief.brand:
        seal_r = max(10, int(unit * 0.016))
        seal_cx = photo_box[2] - dw - 24
        seal_cy = bottom_y + 8
        draw.rounded_rectangle([seal_cx - seal_r, seal_cy - seal_r, seal_cx + seal_r, seal_cy + seal_r], radius=3, outline=(186, 64, 52, 220), width=1)
        sf_font = fonts.load_font("fangsong", max(9, int(unit * 0.016)))
        draw.text((seal_cx - seal_r + 3, seal_cy - seal_r + 2), brief.brand[0], font=sf_font, fill=(186, 64, 52, 220))

    composite = Image.alpha_composite(base, overlay)

    tape_x = card_box[0] + int(cw * 0.14)
    tape_y = card_box[1] + 4
    tape_img = paint.card_tape((w, h), tape_x, tape_y, tape_w=max(90, int(unit * 0.16)), tape_h=max(26, int(unit * 0.040)), angle=-16)
    return Image.alpha_composite(composite, tape_img)


def _render_quote_tweet(brief: CoverBrief, preset: Preset, size: tuple[int, int]) -> Image.Image:
    w, h = size
    unit = min(w, h)

    # 1. Crisp modern social canvas
    base = paint.v_gradient((w, h), (242, 245, 248), (236, 240, 244)).convert("RGBA")
    base = paint.grain_rgb(base, 0.035, brief.seed).convert("RGBA")

    # 2. Tweet card box
    card_box = [int(w * 0.070), int(h * 0.065), int(w * 0.930), int(h * 0.935)]
    cw = card_box[2] - card_box[0]
    ch = card_box[3] - card_box[1]
    radius = int(unit * 0.024)

    shadow = paint.card_drop_shadow((w, h), card_box, radius=radius, blur=int(unit * 0.022), offset_y=int(h * 0.012), color=(50, 65, 80), alpha=40)
    base = Image.alpha_composite(base, shadow)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(card_box, radius=radius, fill=(255, 255, 255, 255), outline=(228, 232, 238, 255), width=1)

    pad_x = int(cw * 0.08)
    hx = card_box[0] + pad_x
    hr_x = card_box[2] - pad_x
    hy = card_box[1] + int(ch * 0.065)

    # 3. Tweet Header: Avatar + Display Name + Verified Blue Badge + Handle
    avatar_r = max(18, int(unit * 0.034))
    av_cx = hx + avatar_r
    av_cy = hy + avatar_r

    av_box = [av_cx - avatar_r, av_cy - avatar_r, av_cx + avatar_r, av_cy + avatar_r]
    draw.ellipse(av_box, fill=preset.accent + (240,), outline=(255, 255, 255, 255), width=2)
    av_font = fonts.load_font("headline", max(14, int(avatar_r * 0.9)))
    brand_char = (brief.brand[0] if brief.brand else (brief.author[0] if brief.author else "推"))
    fonts.draw_text_measured(draw, (av_cx - avatar_r * 0.45, av_cy - avatar_r * 0.55), brand_char, av_font, (255, 255, 255, 255))

    info_x = av_cx + avatar_r + max(10, int(unit * 0.018))
    name_str = brief.author or (brief.brand or "精选灵感")
    nf = fonts.load_font("headline", max(15, int(unit * 0.026)))
    nw, nh = fonts.text_size(draw, name_str, nf)
    fonts.draw_text_measured(draw, (info_x, hy + int(avatar_r * 0.1)), name_str, nf, (15, 20, 25, 255))

    badge_r = max(6, int(unit * 0.011))
    badge_cx = info_x + nw + badge_r + 6
    badge_cy = hy + int(avatar_r * 0.1) + nh / 2
    draw.ellipse([badge_cx - badge_r, badge_cy - badge_r, badge_cx + badge_r, badge_cy + badge_r], fill=(29, 155, 240, 255))
    vf = fonts.load_font("sans", max(8, int(badge_r * 1.3)))
    draw.text((badge_cx - badge_r * 0.55, badge_cy - badge_r * 0.8), "✓", font=vf, fill=(255, 255, 255, 255))

    hf = fonts.load_font("sans", max(12, int(unit * 0.020)))
    handle_str = "@tong_skills · 精选热推"
    fonts.draw_text_measured(draw, (info_x, hy + int(avatar_r * 0.95)), handle_str, hf, (110, 118, 125, 255))

    dots_x = hr_x - max(12, int(unit * 0.02))
    for dx in range(3):
        draw.ellipse([dots_x + dx * 6, hy + int(avatar_r * 0.3), dots_x + dx * 6 + 3, hy + int(avatar_r * 0.3) + 3], fill=(180, 186, 194, 255))

    rule_y = hy + avatar_r * 2 + max(14, int(unit * 0.025))
    draw.line([(int(hx), int(rule_y)), (int(hr_x), int(rule_y))], fill=(240, 242, 246, 255), width=1)

    tokens = _parse_quote_tokens(brief.quote, brief.highlight)
    has_hl = any(is_hl for _, is_hl in tokens)
    q_max_w = hr_x - hx
    q_max_h = ch * 0.48

    start_sz = unit * (0.060 if len(brief.quote or "") < 25 else (0.052 if len(brief.quote or "") < 50 else 0.044))
    q_font, q_lines, line_height, single_h = _fit_quote_tokens(draw, tokens, "sans", start_sz, q_max_w, q_max_h)
    quote_h = len(q_lines) * line_height

    sub_text = brief.sub or brief.kicker
    sub_font = fonts.load_font("sans", max(13, int(unit * 0.024)))
    wrapped_sub = wrap_title(draw, sub_text, sub_font, q_max_w - int(unit * 0.05), max_lines=3) if sub_text else []
    sub_single_h = fonts.text_size(draw, "国", sub_font)[1]
    sub_box_pad = max(12, int(unit * 0.020))
    sub_block_h = (len(wrapped_sub) * sub_single_h * 1.45 + sub_box_pad * 2 + 16) if wrapped_sub else 0

    total_content_h = quote_h + sub_block_h
    body_top = rule_y + max(16, int(unit * 0.030))
    fy = card_box[3] - int(ch * 0.10)
    body_bottom = fy - max(16, int(unit * 0.030))
    available_h = body_bottom - body_top
    center_offset = max(0, int((available_h - total_content_h) * 0.35))

    q_top = body_top + center_offset

    cur_y = q_top
    for line in q_lines:
        _draw_token_line(draw, hx, cur_y, line, q_font, (15, 20, 25, 255), "tweet", (210, 235, 255), single_h, has_hl)
        cur_y += line_height

    if wrapped_sub:
        box_y0 = cur_y + max(14, int(unit * 0.025))
        box_y1 = box_y0 + sub_block_h - 10
        draw.rounded_rectangle([int(hx), int(box_y0), int(hr_x), int(box_y1)], radius=8, fill=(247, 249, 251, 255), outline=(225, 230, 236, 255), width=1)

        qt_header = "📌 深度解读 / 思考脉络"
        qth_f = fonts.load_font("sans", max(11, int(unit * 0.020)))
        fonts.draw_text_measured(draw, (hx + sub_box_pad, box_y0 + sub_box_pad * 0.6), qt_header, qth_f, (83, 100, 113, 255))

        sy = box_y0 + sub_box_pad * 0.6 + int(unit * 0.034)
        for sline in wrapped_sub:
            fonts.draw_text_measured(draw, (hx + sub_box_pad, sy), sline, sub_font, (50, 60, 70, 255))
            sy += sub_single_h * 1.45

    draw.line([(int(hx), int(fy - 12)), (int(hr_x), int(fy - 12))], fill=(240, 242, 246, 255), width=1)

    actions = [
        ("REPLIES", "348"),
        ("REPOSTS", "1.4K"),
        ("LIKES", "9.6K"),
        ("SAVES", "2,150"),
    ]
    lbl_font = fonts.load_font("sans_light", max(10, int(unit * 0.016)))
    num_font = fonts.load_font("sans", max(11, int(unit * 0.019)))
    act_spacing = (hr_x - hx) / len(actions)

    for idx, (lbl, count) in enumerate(actions):
        ax = hx + idx * act_spacing
        lw, lh = fonts.text_size(draw, lbl, lbl_font)
        fonts.draw_text_measured(draw, (ax, fy), lbl, lbl_font, (140, 150, 165, 255))
        fonts.draw_text_measured(draw, (ax + lw + 6, fy - 1), count, num_font, (70, 80, 95, 255))

    return Image.alpha_composite(base, overlay)


def draw_type_quote(arg1, brief_or_preset=None, preset_or_size=None) -> Image.Image:
    if isinstance(arg1, Image.Image):
        brief = brief_or_preset
        preset = preset_or_size
        size = arg1.size
    else:
        brief = arg1
        preset = brief_or_preset
        size = preset_or_size if preset_or_size is not None else (1050, 1400)

    preset_name = getattr(preset, "name", "paper")
    style_name = _resolve_quote_style(getattr(brief, "style", "auto"), preset_name)

    if style_name == "editorial":
        return _render_quote_editorial(brief, preset, size)
    elif style_name == "highlight":
        return _render_quote_highlight(brief, preset, size)
    elif style_name == "dark":
        return _render_quote_dark(brief, preset, size)
    elif style_name == "cinema":
        return _render_quote_cinema(brief, preset, size)
    elif style_name == "polaroid":
        return _render_quote_polaroid(brief, preset, size)
    elif style_name == "tweet":
        return _render_quote_tweet(brief, preset, size)
    else:
        return _render_quote_paper(brief, preset, size)


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

    if brief.brand:
        seal_font = fonts.load_font("kai", max(18, int(unit * 0.045)))
        overlay = Image.alpha_composite(
            overlay,
            paint.seal_stamp(img.size, int(w * 0.86), int(h * 0.82), max(24, int(unit * 0.068)), brief.brand[0], preset.accent, seal_font),
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

    if brief.brand:
        brand_font = fonts.load_font("fangsong", max(18, int(unit * 0.034)))
        brand = fonts.draw_text_measured(
            draw, (x, y), fonts.letterspace(brief.brand, "  "), brand_font, preset.brand + (255,)
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
    else:
        label = "DAILY BRIEFING"
        lab_font = fonts.load_font("sans_light", max(12, int(unit * 0.022)))
        lw, lh = fonts.text_size(draw, label, lab_font)
        fonts.draw_text_measured(draw, (x, y), label, lab_font, preset.kicker + (220,))
        rule_y = y + lh + max(10, int(unit * 0.016))
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

    if brief.brand:
        seal_font = fonts.load_font("kai", max(18, int(unit * 0.042)))
        seal_cy = min(int(fy + unit * 0.02), int(h * 0.90))
        overlay = Image.alpha_composite(
            overlay,
            paint.seal_stamp(
                img.size, int(w * 0.88), max(int(fy + 8), seal_cy), max(22, int(unit * 0.058)), brief.brand[0], preset.accent, seal_font
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

    if brief.brand and preset.name in ("paper", "ink", "twilight"):
        seal_font = fonts.load_font("kai", max(18, int(unit * 0.045)))
        overlay = Image.alpha_composite(
            overlay,
            paint.seal_stamp(img.size, int(w * 0.86), int(h * 0.82), max(24, int(unit * 0.068)), brief.brand[0], preset.accent, seal_font),
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

    if layout == "quote":
        img = draw_type_quote(brief, preset, (w, h))
        out_path = os.path.abspath(brief.out)
        parent = os.path.dirname(out_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        img.save(out_path)
        style_used = _resolve_quote_style(getattr(brief, "style", "auto"), preset_name)
        return "%s (%sx%s) preset=%s layout=%s style=%s" % (out_path, w, h, preset_name, layout, style_used)

    base = paint.v_gradient((w, h), preset.top, preset.bottom).convert("RGBA")
    theme = getattr(brief, "theme", "celestial")
    if theme == "swiss":
        base = Image.alpha_composite(base, paint.swiss_art((w, h), preset, brief.seed))
    elif theme == "press":
        base = Image.alpha_composite(base, paint.press_art((w, h), preset, brief.seed))
    else:
        base = _art(base, preset, layout, brief.seed)
    base = draw_type(base, brief, preset, layout)
    rgb = paint.vignette(paint.grain_rgb(base, preset.grain, brief.seed))

    out_path = os.path.abspath(brief.out)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    rgb.save(out_path)
    return "%s (%sx%s) preset=%s layout=%s theme=%s" % (out_path, w, h, preset_name, layout, theme)


def render_pack(
    out_dir: str,
    date: str = "",
    brand: str = None,
    title: str = "每日速览",
    sub: str = "",
    bullets: list[str] = None,
    quote: str = "",
    author: str = "",
    source: str = "",
    style: str = "auto",
    highlight: str = "",
    dividers: list[tuple[str, str, str]] = None,
    preset: str = "auto",
    theme: str = "auto",
    seed: int = 42,
) -> dict[str, str]:
    if brand is None:
        brand = DEFAULT_BRAND
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
        theme=theme,
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
        theme=theme,
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
            theme=theme,
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
                theme=theme,
                seed=seed + idx * 5,
            )
            render_cover(div_brief)
            results["divider_%02d" % (idx + 1)] = div_path

    # 5. Quote Card (金句卡 / 箴言卡 3:4)
    if quote:
        quote_path = os.path.join(out_dir, "05_quote_card.png")
        quote_brief = CoverBrief(
            quote=quote,
            author=author,
            source=source,
            style=style,
            highlight=highlight,
            sub=sub,
            brand=brand,
            date=date,
            out=quote_path,
            layout="quote",
            ratio="3:4",
            preset=preset,
            theme=theme,
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
        theme=theme,
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
        theme=theme,
        seed=seed,
    )
    render_cover(briefing_brief)
    results["briefing"] = briefing_path

    return results
