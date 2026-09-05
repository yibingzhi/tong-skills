from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont

from .fonts import load_font


def _find_font(size: int, kind: str = "sans") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return load_font(kind, size)


WIDTH = 1080
HEIGHT = 1440

CARD_PALETTES = {
    "warm": {
        "bg": (248, 246, 241),
        "card_a_bg": (255, 255, 255),
        "card_b_bg": (255, 252, 248),
        "text_main": (24, 24, 24),
        "text_body": (60, 60, 60),
        "text_muted": (140, 134, 126),
        "accent": (224, 86, 36),  # Terracotta
        "accent_bg": (253, 244, 239),
        "border_a": (234, 228, 218),
        "border_b": (238, 226, 214),
        "watermark": (247, 244, 238),
        "bar_inactive": (228, 222, 212),
        "divider": (244, 238, 230),
    },
    "dark": {
        "bg": (15, 17, 21),
        "card_a_bg": (24, 27, 34),
        "card_b_bg": (30, 34, 44),
        "text_main": (245, 247, 250),
        "text_body": (195, 200, 210),
        "text_muted": (125, 133, 148),
        "accent": (245, 166, 35),  # Amber Gold
        "accent_bg": (40, 36, 26),
        "border_a": (42, 48, 60),
        "border_b": (65, 55, 35),
        "watermark": (32, 36, 46),
        "bar_inactive": (40, 45, 56),
        "divider": (45, 52, 66),
    },
    "editorial": {
        "bg": (244, 245, 247),
        "card_a_bg": (255, 255, 255),
        "card_b_bg": (248, 248, 250),
        "text_main": (16, 16, 16),
        "text_body": (60, 60, 60),
        "text_muted": (130, 130, 136),
        "accent": (20, 20, 20),
        "accent_bg": (235, 235, 240),
        "border_a": (225, 226, 230),
        "border_b": (215, 216, 222),
        "watermark": (240, 240, 244),
        "bar_inactive": (220, 222, 226),
        "divider": (235, 236, 240),
    },
}


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    if not text:
        return []
    lines = []
    paragraphs = text.split("\n")
    for para in paragraphs:
        if not para.strip():
            lines.append("")
            continue
        cur = ""
        for char in para:
            test = cur + char
            bbox = draw.textbbox((0, 0), test, font=font)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = char
        if cur:
            lines.append(cur)
    return lines


def _draw_top_progress(draw: ImageDraw.ImageDraw, current_page: int, total_pages: int, pal: dict) -> None:
    pad_x = 64
    inner_w = WIDTH - pad_x * 2
    y_prog = 44
    gap = 8
    seg_w = (inner_w - (total_pages - 1) * gap) // total_pages

    for i in range(1, total_pages + 1):
        x0 = pad_x + (i - 1) * (seg_w + gap)
        x1 = x0 + seg_w
        color = pal["accent"] if i == current_page else (pal["text_muted"] if i < current_page else pal["bar_inactive"])
        draw.rounded_rectangle([x0, y_prog, x1, y_prog + 4], radius=2, fill=color)


def render_cover_card(
    title: str,
    subtitle: str,
    tag: str,
    brand: str,
    total_pages: int,
    palette_name: str = "warm",
    points_summary: List[Tuple[str, str, str]] | None = None,
) -> Image.Image:
    pal = CARD_PALETTES.get(palette_name, CARD_PALETTES["warm"])
    im = Image.new("RGB", (WIDTH, HEIGHT), pal["bg"])
    draw = ImageDraw.Draw(im)

    _draw_top_progress(draw, 1, total_pages, pal)

    font_title = _find_font(58, "headline")
    font_sub = _find_font(30, "sans")
    font_tag = _find_font(22, "bold")
    font_meta = _find_font(24, "sans")
    font_preview_title = _find_font(22, "bold")
    font_preview_item = _find_font(28, "sans")
    font_preview_num = _find_font(26, "display_num")

    pad_x = 64
    inner_w = WIDTH - pad_x * 2

    # Header Bar
    y = 76
    brand_label = f"@{brand} · 独家专栏" if brand else "独家专栏 · 深度写作"
    draw.text((pad_x, y), brand_label, font=font_meta, fill=pal["text_muted"])
    page_text = f"01 / {total_pages:02d}"
    pb = draw.textbbox((0, 0), page_text, font=font_meta)
    draw.text((WIDTH - pad_x - (pb[2] - pb[0]), y), page_text, font=font_meta, fill=pal["text_muted"])

    y += 64

    # Measure title & subtitle lines to determine Card A height
    title_lines = _wrap_text(title, font_title, inner_w - 120, draw)
    sub_lines = _wrap_text(subtitle, font_sub, inner_w - 96, draw) if subtitle else []

    title_block_h = len(title_lines) * 78 + (len(sub_lines) * 44 if sub_lines else 0) + 120
    card_a_h = max(380, min(500, title_block_h))
    card_a_y0 = y
    card_a_y1 = card_a_y0 + card_a_h

    # Card A: Main Title
    draw.rounded_rectangle(
        [pad_x, card_a_y0, WIDTH - pad_x, card_a_y1],
        radius=28,
        fill=pal["card_a_bg"],
        outline=pal["border_a"],
        width=1,
    )

    ay = card_a_y0 + 44
    tag_str = tag or "深度思考"
    tb = draw.textbbox((0, 0), tag_str, font=font_tag)
    tw = (tb[2] - tb[0]) + 24
    draw.rounded_rectangle([pad_x + 48, ay, pad_x + 48 + tw, ay + 36], radius=6, fill=pal["accent_bg"])
    draw.text((pad_x + 60, ay + 6), tag_str, font=font_tag, fill=pal["accent"])
    draw.text((pad_x + 48 + tw + 18, ay + 7), "ARCHIVE · 全文结构化速读", font=font_meta, fill=pal["text_muted"])

    ay += 64
    bar_top = ay + 6
    for line in title_lines:
        draw.text((pad_x + 72, ay), line, font=font_title, fill=pal["text_main"])
        ay += 74

    bar_bottom = ay - 14
    draw.rounded_rectangle([pad_x + 48, bar_top, pad_x + 55, max(bar_top + 40, bar_bottom)], radius=4, fill=pal["accent"])

    if sub_lines:
        ay += 14
        for line in sub_lines:
            draw.text((pad_x + 48, ay), line, font=font_sub, fill=pal["text_body"])
            ay += 44

    # Card B: Outline Preview
    card_b_y0 = card_a_y1 + 28
    card_b_h = HEIGHT - 96 - card_b_y0
    card_b_y1 = card_b_y0 + card_b_h

    draw.rounded_rectangle(
        [pad_x, card_b_y0, WIDTH - pad_x, card_b_y1],
        radius=28,
        fill=pal["card_b_bg"],
        outline=pal["border_b"],
        width=1,
    )

    by = card_b_y0 + 40
    draw.text((pad_x + 44, by), "✦ 本篇核心框架速览", font=font_preview_title, fill=pal["accent"])
    by += 54

    items = points_summary or [
        ("01", "选题破局", "拒绝同质化口号，直击第一痛点与业务冲突"),
        ("02", "叙事架构", "冷开场切入叠加八段式论证骨架，不写流水账"),
        ("03", "负向剪枝", "主编终审严卡九维AI塑料感，删去假升华"),
        ("04", "视觉呈现", "本地多卡无损排版，小红书3:4黄金比例轮播"),
    ]

    for num, h, sub in items[:4]:
        draw.rounded_rectangle([pad_x + 44, by, pad_x + 44 + 44, by + 30], radius=6, fill=pal["accent_bg"])
        draw.text((pad_x + 52, by + 3), num, font=font_preview_num, fill=pal["accent"])
        item_heading = f"{h}："
        draw.text((pad_x + 104, by + 1), item_heading, font=font_preview_item, fill=pal["text_main"])
        hb = draw.textbbox((0, 0), item_heading, font=font_preview_item)
        sub_text = sub if len(sub) < 22 else sub[:21] + "…"
        draw.text((pad_x + 104 + (hb[2] - hb[0]), by + 1), sub_text, font=font_preview_item, fill=pal["text_muted"])
        by += 66

    # Bottom footer button
    foot_y = HEIGHT - 76
    btn_w = 340
    btn_h = 44
    btn_x0 = (WIDTH - btn_w) // 2
    draw.rounded_rectangle(
        [btn_x0, foot_y, btn_x0 + btn_w, foot_y + btn_h],
        radius=22,
        fill=pal["accent_bg"],
        outline=pal["border_b"],
        width=1,
    )
    btn_text = "左右滑动阅读完整切片 ➔"
    draw.text((btn_x0 + 44, foot_y + 9), btn_text, font=font_tag, fill=pal["accent"])

    return im


def render_point_card(
    index: int,
    total_pages: int,
    step_num: str,
    heading: str,
    body: str,
    takeaway: str,
    brand: str,
    palette_name: str = "warm",
) -> Image.Image:
    pal = CARD_PALETTES.get(palette_name, CARD_PALETTES["warm"])
    im = Image.new("RGB", (WIDTH, HEIGHT), pal["bg"])
    draw = ImageDraw.Draw(im)

    _draw_top_progress(draw, index, total_pages, pal)

    font_wm = _find_font(240, "display_num")
    font_num = _find_font(76, "display_num")
    font_step = _find_font(22, "bold")
    font_heading = _find_font(52, "headline")
    font_body = _find_font(36, "sans")
    font_meta = _find_font(26, "sans")
    font_insight_tag = _find_font(22, "bold")
    font_insight_text = _find_font(36, "headline")

    pad_x = 64
    inner_w = WIDTH - pad_x * 2

    # Top Header Bar
    y = 76
    brand_label = f"@{brand} · 深度切片" if brand else "深度长文切片"
    draw.text((pad_x, y), brand_label, font=font_meta, fill=pal["text_muted"])
    page_text = f"{index:02d} / {total_pages:02d}"
    pb = draw.textbbox((0, 0), page_text, font=font_meta)
    draw.text((WIDTH - pad_x - (pb[2] - pb[0]), y), page_text, font=font_meta, fill=pal["text_muted"])

    y += 64

    # Calculate content height to size Card A and Card B adaptively
    h_lines = _wrap_text(heading, font_heading, inner_w - 96, draw)
    b_lines = _wrap_text(body, font_body, inner_w - 96, draw) if body else []

    # Dynamic Card A height
    card_a_h = max(360, min(540, 140 + len(h_lines) * 68 + (len(b_lines) * 52 if b_lines else 0)))
    
    # Dynamic Card B height
    take_text = takeaway or "穿透表层同质化叙事，直达真实业务痛点。"
    t_lines = _wrap_text(take_text, font_insight_text, inner_w - 96, draw)
    sub_t = "不解决具体痛苦的宏大叙事毫无传播价值。让每一次表达都锚定读者最紧迫的真实境遇。"
    sub_lines = _wrap_text(sub_t, font_body, inner_w - 96, draw)
    card_b_h = max(300, min(440, 180 + len(t_lines) * 52 + len(sub_lines) * 46))

    gap = 28
    total_cards_h = card_a_h + gap + card_b_h
    available_space = (HEIGHT - 130) - y
    offset_y = max(0, (available_space - total_cards_h) // 2)

    card_a_y0 = y + offset_y
    card_a_y1 = card_a_y0 + card_a_h

    draw.rounded_rectangle(
        [pad_x, card_a_y0, WIDTH - pad_x, card_a_y1],
        radius=28,
        fill=pal["card_a_bg"],
        outline=pal["border_a"],
        width=1,
    )

    num_str = f"{int(step_num):02d}" if step_num.isdigit() else step_num
    # Watermark placed safely inside card
    draw.text((WIDTH - pad_x - 260, card_a_y0 + 20), num_str, font=font_wm, fill=pal["watermark"])

    ay = card_a_y0 + 44
    draw.text((pad_x + 48, ay), num_str, font=font_num, fill=pal["accent"])
    nb = draw.textbbox((0, 0), num_str, font=font_num)

    tag_x = pad_x + 48 + (nb[2] - nb[0]) + 18
    tag_y = ay + 18
    draw.rounded_rectangle([tag_x, tag_y, tag_x + 140, tag_y + 36], radius=6, fill=pal["accent_bg"])
    draw.text((tag_x + 12, tag_y + 6), "CORE POINT", font=font_step, fill=pal["accent"])

    ay += (nb[3] - nb[1]) + 20
    for line in h_lines:
        draw.text((pad_x + 48, ay), line, font=font_heading, fill=pal["text_main"])
        ay += 68

    ay += 16
    if b_lines:
        for line in b_lines:
            if not line:
                ay += 16
                continue
            draw.text((pad_x + 48, ay), line, font=font_body, fill=pal["text_body"])
            ay += 52

    # Card B: Insight
    card_b_y0 = card_a_y1 + gap
    card_b_y1 = card_b_y0 + card_b_h

    draw.rounded_rectangle(
        [pad_x, card_b_y0, WIDTH - pad_x, card_b_y1],
        radius=28,
        fill=pal["card_b_bg"],
        outline=pal["border_b"],
        width=2,
    )
    draw.rounded_rectangle([pad_x, card_b_y0 + 16, pad_x + 8, card_b_y1 - 16], radius=4, fill=pal["accent"])

    by = card_b_y0 + 38
    draw.rounded_rectangle([pad_x + 40, by, pad_x + 40 + 190, by + 40], radius=6, fill=pal["accent_bg"])
    draw.text((pad_x + 52, by + 7), "✦ INSIGHT 核心洞察", font=font_insight_tag, fill=pal["accent"])

    by += 64
    for line in t_lines:
        draw.text((pad_x + 40, by), line, font=font_insight_text, fill=pal["text_main"])
        by += 52

    by += 16
    draw.line([pad_x + 40, by, WIDTH - pad_x - 48, by], fill=pal["divider"], width=1)
    by += 28

    for line in sub_lines:
        draw.text((pad_x + 40, by), line, font=font_body, fill=pal["text_muted"])
        by += 48

    # Bottom footer cue
    foot_y = HEIGHT - 68
    cue_msg = "左右滑动继续阅读下一要点 ➔" if index < total_pages - 1 else "左右滑动查看总结结语 ➔"
    cb = draw.textbbox((0, 0), cue_msg, font=font_meta)
    draw.text(((WIDTH - (cb[2] - cb[0])) // 2, foot_y), cue_msg, font=font_meta, fill=pal["text_muted"])

    return im


def render_outro_card(
    quote: str,
    author: str,
    brand: str,
    total_pages: int,
    palette_name: str = "warm",
) -> Image.Image:
    pal = CARD_PALETTES.get(palette_name, CARD_PALETTES["warm"])
    im = Image.new("RGB", (WIDTH, HEIGHT), pal["bg"])
    draw = ImageDraw.Draw(im)

    _draw_top_progress(draw, total_pages, total_pages, pal)

    font_quote_mark = _find_font(130, "display_num")
    font_quote = _find_font(46, "headline")
    font_meta = _find_font(24, "sans")
    font_author = _find_font(30, "sans")
    font_cta_title = _find_font(28, "bold")
    font_cta_sub = _find_font(26, "sans")

    pad_x = 64
    inner_w = WIDTH - pad_x * 2

    # Header Bar
    y = 76
    brand_label = f"@{brand} · 结语沉淀" if brand else "结语沉淀 · 创作手记"
    draw.text((pad_x, y), brand_label, font=font_meta, fill=pal["text_muted"])
    page_text = f"{total_pages:02d} / {total_pages:02d}"
    pb = draw.textbbox((0, 0), page_text, font=font_meta)
    draw.text((WIDTH - pad_x - (pb[2] - pb[0]), y), page_text, font=font_meta, fill=pal["text_muted"])

    y += 64

    # Main Quote Card (Card A)
    card_a_y0 = y
    card_a_h = 660
    card_a_y1 = card_a_y0 + card_a_h
    draw.rounded_rectangle(
        [pad_x, card_a_y0, WIDTH - pad_x, card_a_y1],
        radius=28,
        fill=pal["card_a_bg"],
        outline=pal["border_a"],
        width=1,
    )

    draw.text((pad_x + 52, card_a_y0 + 36), "“", font=font_quote_mark, fill=pal["accent"])

    qy = card_a_y0 + 170
    quote_text = quote or "好内容从来不是堆砌出来的，\n而是在克制与真实中打磨出来的。"
    q_lines = _wrap_text(quote_text, font_quote, inner_w - 100, draw)
    for line in q_lines:
        if not line:
            qy += 20
            continue
        draw.text((pad_x + 52, qy), line, font=font_quote, fill=pal["text_main"])
        qy += 68

    sig = f"—— {author or brand or '橦云异梦'} · 创作手记"
    sb = draw.textbbox((0, 0), sig, font=font_author)
    draw.text((WIDTH - pad_x - 52 - (sb[2] - sb[0]), card_a_y1 - 64), sig, font=font_author, fill=pal["text_muted"])

    # Secondary CTA Action Card (Card B)
    card_b_y0 = card_a_y1 + 28
    card_b_h = HEIGHT - 84 - card_b_y0
    card_b_y1 = card_b_y0 + card_b_h
    draw.rounded_rectangle(
        [pad_x, card_b_y0, WIDTH - pad_x, card_b_y1],
        radius=28,
        fill=pal["card_b_bg"],
        outline=pal["border_b"],
        width=1,
    )

    cy = card_b_y0 + 54
    cta1 = "✦ 喜欢本篇长文拆解？"
    cb1 = draw.textbbox((0, 0), cta1, font=font_cta_title)
    draw.text(((WIDTH - (cb1[2] - cb1[0])) // 2, cy), cta1, font=font_cta_title, fill=pal["accent"])

    cy += 54
    cta2 = "欢迎「 点赞 · 收藏 · 转发给同路人 」"
    cb2 = draw.textbbox((0, 0), cta2, font=font_cta_sub)
    draw.text(((WIDTH - (cb2[2] - cb2[0])) // 2, cy), cta2, font=font_cta_sub, fill=pal["text_main"])

    cy += 48
    cta3 = "持续输出深度干货与AI工程实践思考"
    cb3 = draw.textbbox((0, 0), cta3, font=font_meta)
    draw.text(((WIDTH - (cb3[2] - cb3[0])) // 2, cy), cta3, font=font_meta, fill=pal["text_muted"])

    return im


def render_card_suite(
    title: str,
    subtitle: str = "",
    tag: str = "思考",
    points: List[Tuple[str, str, str, str]] | None = None,
    outro: str = "",
    author: str = "",
    brand: str = "橦云异梦",
    out_dir: Path | str = "out/cards",
    style: str = "warm",
) -> List[Path]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    points = points or []
    total_pages = 1 + len(points) + (1 if outro else 0)
    saved: List[Path] = []

    summaries: List[Tuple[str, str, str]] = []
    for step, h, b, take in points:
        sub_desc = take if take else (b[:24] if b else "核心要点深度展开")
        summaries.append((step, h, sub_desc))

    # 1. Cover Card
    p_cover = out_path / "card_01_cover.png"
    im_cover = render_cover_card(
        title=title,
        subtitle=subtitle,
        tag=tag,
        brand=brand,
        total_pages=total_pages,
        palette_name=style,
        points_summary=summaries if summaries else None,
    )
    im_cover.save(p_cover)
    saved.append(p_cover)

    # 2. Point Cards
    for idx, (step, heading, body, takeaway) in enumerate(points, 2):
        p_card = out_path / f"card_{idx:02d}_point.png"
        im_point = render_point_card(
            index=idx,
            total_pages=total_pages,
            step_num=step,
            heading=heading,
            body=body,
            takeaway=takeaway,
            brand=brand,
            palette_name=style,
        )
        im_point.save(p_card)
        saved.append(p_card)

    # 3. Outro Card
    if outro:
        idx = total_pages
        p_outro = out_path / f"card_{idx:02d}_outro.png"
        im_outro = render_outro_card(
            quote=outro,
            author=author,
            brand=brand,
            total_pages=total_pages,
            palette_name=style,
        )
        im_outro.save(p_outro)
        saved.append(p_outro)

    return saved
