from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont

from .fonts import load_font


def _find_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    kind = "headline" if bold else "sans"
    return load_font(kind, size)

WIDTH = 1080
HEIGHT = 1440

CARD_PALETTES = {
    "warm": {
        "bg": (250, 248, 245),
        "card_bg": (255, 255, 255),
        "text_main": (34, 34, 34),
        "text_sub": (110, 110, 110),
        "accent": (217, 83, 47),  # Terracotta
        "border": (232, 228, 222),
        "badge_bg": (245, 235, 230),
        "badge_text": (217, 83, 47),
    },
    "dark": {
        "bg": (18, 20, 24),
        "card_bg": (26, 29, 35),
        "text_main": (240, 242, 245),
        "text_sub": (150, 155, 165),
        "accent": (245, 166, 35),  # Amber
        "border": (45, 50, 60),
        "badge_bg": (35, 30, 20),
        "badge_text": (245, 166, 35),
    },
    "editorial": {
        "bg": (245, 245, 247),
        "card_bg": (255, 255, 255),
        "text_main": (17, 17, 17),
        "text_sub": (102, 102, 102),
        "accent": (0, 0, 0),
        "border": (220, 220, 225),
        "badge_bg": (230, 230, 235),
        "badge_text": (17, 17, 17),
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


def render_cover_card(
    title: str,
    subtitle: str,
    tag: str,
    brand: str,
    total_pages: int,
    palette_name: str = "warm",
) -> Image.Image:
    pal = CARD_PALETTES.get(palette_name, CARD_PALETTES["warm"])
    im = Image.new("RGB", (WIDTH, HEIGHT), pal["bg"])
    draw = ImageDraw.Draw(im)

    font_brand = _find_font(28, bold=False)
    font_tag = _find_font(26, bold=True)
    font_title = _find_font(68, bold=True)
    font_sub = _find_font(34, bold=False)
    font_footer = _find_font(26, bold=False)

    margin = 80
    y = margin

    if tag:
        tag_text = f" {tag} "
        tag_bbox = draw.textbbox((0, 0), tag_text, font=font_tag)
        tw = tag_bbox[2] - tag_bbox[0] + 24
        th = tag_bbox[3] - tag_bbox[1] + 16
        draw.rounded_rectangle([margin, y, margin + tw, y + th], radius=8, fill=pal["badge_bg"])
        draw.text((margin + 12, y + 8), tag_text, font=font_tag, fill=pal["badge_text"])

    page_str = f"1 / {total_pages}"
    pb = draw.textbbox((0, 0), page_str, font=font_brand)
    pw = pb[2] - pb[0]
    draw.text((WIDTH - margin - pw, y + 6), page_str, font=font_brand, fill=pal["text_sub"])

    card_x0 = margin
    card_y0 = y + 70
    card_x1 = WIDTH - margin
    card_y1 = HEIGHT - margin - 80

    draw.rounded_rectangle(
        [card_x0, card_y0, card_x1, card_y1],
        radius=24,
        fill=pal["card_bg"],
        outline=pal["border"],
        width=2,
    )

    draw.rectangle([card_x0 + 40, card_y0 + 60, card_x0 + 48, card_y0 + 160], fill=pal["accent"])

    title_lines = _wrap_text(title, font_title, card_x1 - card_x0 - 140, draw)
    ty = card_y0 + 60
    for line in title_lines:
        draw.text((card_x0 + 70, ty), line, font=font_title, fill=pal["text_main"])
        tb = draw.textbbox((0, 0), line, font=font_title)
        ty += (tb[3] - tb[1]) + 20

    ty += 30
    draw.line([card_x0 + 70, ty, card_x1 - 70, ty], fill=pal["border"], width=1)
    ty += 40

    if subtitle:
        sub_lines = _wrap_text(subtitle, font_sub, card_x1 - card_x0 - 140, draw)
        for line in sub_lines:
            draw.text((card_x0 + 70, ty), line, font=font_sub, fill=pal["text_sub"])
            sb = draw.textbbox((0, 0), line, font=font_sub)
            ty += (sb[3] - sb[1]) + 16

    foot_text = f"@{brand} · 左右滑动查看全篇 →" if brand else "左右滑动查看全篇 →"
    fb = draw.textbbox((0, 0), foot_text, font=font_footer)
    fw = fb[2] - fb[0]
    draw.text((WIDTH // 2 - fw // 2, HEIGHT - margin - 30), foot_text, font=font_footer, fill=pal["text_sub"])

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

    font_header = _find_font(28, bold=False)
    font_num = _find_font(84, bold=True)
    font_heading = _find_font(52, bold=True)
    font_body = _find_font(34, bold=False)
    font_takeaway = _find_font(30, bold=True)

    margin = 80
    page_str = f"{index} / {total_pages}"
    pb = draw.textbbox((0, 0), page_str, font=font_header)
    pw = pb[2] - pb[0]
    if brand:
        draw.text((margin, margin), brand, font=font_header, fill=pal["text_sub"])
    draw.text((WIDTH - margin - pw, margin), page_str, font=font_header, fill=pal["text_sub"])

    card_x0 = margin
    card_y0 = margin + 60
    card_x1 = WIDTH - margin
    card_y1 = HEIGHT - margin - 80

    draw.rounded_rectangle(
        [card_x0, card_y0, card_x1, card_y1],
        radius=24,
        fill=pal["card_bg"],
        outline=pal["border"],
        width=2,
    )

    ny = card_y0 + 50
    draw.text((card_x0 + 60, ny), step_num, font=font_num, fill=pal["accent"])
    nb = draw.textbbox((0, 0), step_num, font=font_num)
    nh = nb[3] - nb[1]

    hy = ny + nh + 20
    h_lines = _wrap_text(heading, font_heading, card_x1 - card_x0 - 120, draw)
    for line in h_lines:
        draw.text((card_x0 + 60, hy), line, font=font_heading, fill=pal["text_main"])
        hb = draw.textbbox((0, 0), line, font=font_heading)
        hy += (hb[3] - hb[1]) + 16

    hy += 20
    draw.line([card_x0 + 60, hy, card_x1 - 60, hy], fill=pal["border"], width=1)
    hy += 40

    if body:
        b_lines = _wrap_text(body, font_body, card_x1 - card_x0 - 120, draw)
        for line in b_lines:
            draw.text((card_x0 + 60, hy), line, font=font_body, fill=pal["text_main"])
            bb = draw.textbbox((0, 0), line, font=font_body)
            hy += (bb[3] - bb[1]) + 20

    if takeaway:
        box_y0 = card_y1 - 180
        box_y1 = card_y1 - 50
        draw.rounded_rectangle(
            [card_x0 + 40, box_y0, card_x1 - 40, box_y1],
            radius=16,
            fill=pal["badge_bg"],
        )
        draw.rectangle([card_x0 + 40, box_y0, card_x0 + 46, box_y1], fill=pal["accent"])
        t_lines = _wrap_text(f"【 核心洞察 】{takeaway}", font_takeaway, card_x1 - card_x0 - 140, draw)
        ty = box_y0 + 26
        for line in t_lines:
            draw.text((card_x0 + 66, ty), line, font=font_takeaway, fill=pal["badge_text"])
            tb = draw.textbbox((0, 0), line, font=font_takeaway)
            ty += (tb[3] - tb[1]) + 10

    dot_y = HEIGHT - margin - 30
    dot_gap = 20
    total_dots_w = total_pages * 12 + (total_pages - 1) * dot_gap
    start_x = WIDTH // 2 - total_dots_w // 2
    for i in range(1, total_pages + 1):
        x = start_x + (i - 1) * (12 + dot_gap)
        col = pal["accent"] if i == index else pal["border"]
        draw.ellipse([x, dot_y, x + 12, dot_y + 12], fill=col)

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

    font_header = _find_font(28, bold=False)
    font_quote = _find_font(56, bold=True)
    font_author = _find_font(32, bold=False)
    font_action = _find_font(28, bold=True)

    margin = 80
    page_str = f"{total_pages} / {total_pages}"
    pb = draw.textbbox((0, 0), page_str, font=font_header)
    pw = pb[2] - pb[0]
    if brand:
        draw.text((margin, margin), brand, font=font_header, fill=pal["text_sub"])
    draw.text((WIDTH - margin - pw, margin), page_str, font=font_header, fill=pal["text_sub"])

    card_x0 = margin
    card_y0 = margin + 60
    card_x1 = WIDTH - margin
    card_y1 = HEIGHT - margin - 80

    draw.rounded_rectangle(
        [card_x0, card_y0, card_x1, card_y1],
        radius=24,
        fill=pal["card_bg"],
        outline=pal["border"],
        width=2,
    )

    draw.text((card_x0 + 60, card_y0 + 80), "“", font=_find_font(120, bold=True), fill=pal["accent"])

    q_lines = _wrap_text(quote, font_quote, card_x1 - card_x0 - 120, draw)
    qy = card_y0 + 220
    for line in q_lines:
        draw.text((card_x0 + 60, qy), line, font=font_quote, fill=pal["text_main"])
        qb = draw.textbbox((0, 0), line, font=font_quote)
        qy += (qb[3] - qb[1]) + 24

    qy += 40
    if author:
        author_text = f"—— {author}"
        draw.text((card_x1 - 60 - draw.textbbox((0, 0), author_text, font=font_author)[2], qy), author_text, font=font_author, fill=pal["text_sub"])

    action_box_y = card_y1 - 160
    draw.rounded_rectangle(
        [card_x0 + 60, action_box_y, card_x1 - 60, card_y1 - 60],
        radius=16,
        fill=pal["badge_bg"],
    )
    act_text = "点赞 · 收藏 · 转发给需要的朋友"
    ab = draw.textbbox((0, 0), act_text, font=font_action)
    aw = ab[2] - ab[0]
    draw.text((WIDTH // 2 - aw // 2, action_box_y + 36), act_text, font=font_action, fill=pal["badge_text"])

    return im


def render_card_suite(
    title: str,
    subtitle: str,
    tag: str,
    points: List[Tuple[str, str, str, str]],
    outro: str,
    author: str,
    brand: str,
    out_dir: Path,
    style: str = "warm",
) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    total_pages = 1 + len(points) + (1 if outro else 0)
    saved_paths = []

    p1 = out_dir / "card_01_cover.png"
    im1 = render_cover_card(title, subtitle, tag, brand, total_pages, style)
    im1.save(str(p1), quality=95)
    saved_paths.append(p1)

    for idx, (step_num, heading, body, takeaway) in enumerate(points, start=2):
        im_pt = render_point_card(idx, total_pages, step_num, heading, body, takeaway, brand, style)
        pt_path = out_dir / f"card_{idx:02d}_point.png"
        im_pt.save(str(pt_path), quality=95)
        saved_paths.append(pt_path)

    if outro:
        last_idx = total_pages
        im_outro = render_outro_card(outro, author, brand, total_pages, style)
        outro_path = out_dir / f"card_{last_idx:02d}_outro.png"
        im_outro.save(str(outro_path), quality=95)
        saved_paths.append(outro_path)

    return saved_paths
