from __future__ import annotations

import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .presets import RGB, Preset


def lerp(a: RGB, b: RGB, t: float) -> RGB:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def v_gradient(size: tuple[int, int], top: RGB, bottom: RGB) -> Image.Image:
    w, h = size
    strip = Image.new("RGB", (1, h))
    px = strip.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        # Smooth quadratic curve for silkier gradient transition
        t_smooth = t * t * (3.0 - 2.0 * t)
        px[0, y] = lerp(top, bottom, t_smooth)
    return strip.resize((w, h), Image.Resampling.BILINEAR)


def h_gradient(size: tuple[int, int], colors: tuple[RGB, ...]) -> Image.Image:
    w, h = size
    strip = Image.new("RGB", (w, 1))
    px = strip.load()
    n = max(len(colors) - 1, 1)
    for x in range(w):
        t = (x / max(w - 1, 1)) * n
        i = min(int(t), n - 1)
        sub_t = t - i
        sub_smooth = sub_t * sub_t * (3.0 - 2.0 * sub_t)
        px[x, 0] = lerp(colors[i], colors[i + 1], sub_smooth)
    return strip.resize((w, h), Image.Resampling.BILINEAR)


def _box(cx: float, cy: float, rx: float, ry: float = None):
    ry = rx if ry is None else ry
    return [int(cx - rx), int(cy - ry), int(cx + rx), int(cy + ry)]


def radial_glow(size: tuple[int, int], cx: float, cy: float, radius: float, color: RGB, alpha_max: int) -> Image.Image:
    w, h = size
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse(_box(cx, cy, radius), fill=alpha_max)
    blur = max(10, int(radius * 0.60))
    mask = mask.filter(ImageFilter.GaussianBlur(blur))
    layer = Image.new("RGBA", (w, h), color + (0,))
    layer.putalpha(mask)
    return layer


def blob_mask(size: tuple[int, int], blobs, blur: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    for x, y, rx, ry, fill in blobs:
        d.ellipse(_box(x, y, rx, ry), fill=fill)
    if blur:
        mask = mask.filter(ImageFilter.GaussianBlur(blur))
    return mask


def cloud_layer(size: tuple[int, int], cx: float, cy: float, cw: float, ch: float, preset: Preset, seed: int, alpha: int = 210) -> Image.Image:
    rng = random.Random(seed)
    w, h = size
    blobs = []
    cores = (
        (cx - cw * 0.28, cy + ch * 0.08, cw * 0.32, ch * 0.42),
        (cx - cw * 0.02, cy - ch * 0.12, cw * 0.38, ch * 0.50),
        (cx + cw * 0.26, cy + ch * 0.02, cw * 0.30, ch * 0.40),
        (cx + cw * 0.02, cy + ch * 0.20, cw * 0.52, ch * 0.35),
        (cx - cw * 0.16, cy - ch * 0.28, cw * 0.20, ch * 0.24),
        (cx + cw * 0.18, cy - ch * 0.22, cw * 0.22, ch * 0.26),
    )
    for x, y, rx, ry in cores:
        blobs.append((x, y, rx, ry, rng.randint(220, 255)))
    for _ in range(12):
        ox = cx + rng.uniform(-cw * 0.45, cw * 0.45)
        oy = cy + rng.uniform(-ch * 0.40, ch * 0.45)
        rx = cw * rng.uniform(0.08, 0.20)
        ry = ch * rng.uniform(0.10, 0.24)
        blobs.append((ox, oy, rx, ry, rng.randint(140, 230)))
    mask = blob_mask(size, blobs, blur=max(10, int(min(cw, ch) * 0.10)))
    mask = mask.point(lambda p: int(p * alpha / 255))
    
    grad = h_gradient(size, preset.cloud).convert("RGBA")
    grad.putalpha(mask)
    
    # Soft ambient drop shadow under cloud for volume
    shadow_mask = ImageChops.offset(mask, 0, int(ch * 0.07))
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(max(6, int(ch * 0.05))))
    shadow_mask = shadow_mask.point(lambda p: int(p * 0.30))
    shadow = Image.new("RGBA", (w, h), preset.cloud_shadow + (0,))
    shadow.putalpha(shadow_mask)
    
    return Image.alpha_composite(shadow, grad)


def moon_layer(size: tuple[int, int], cx: float, cy: float, radius: float, preset: Preset) -> Image.Image:
    w, h = size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # Multi-tier celestial glow
    glow_outer = radial_glow(size, cx, cy, radius * 3.4, preset.glow, 45)
    glow_inner = radial_glow(size, cx, cy, radius * 1.8, preset.glow, 85)
    out = Image.alpha_composite(out, glow_outer)
    out = Image.alpha_composite(out, glow_inner)
    
    body = Image.new("L", (w, h), 0)
    bd = ImageDraw.Draw(body)
    bd.ellipse(_box(cx, cy, radius), fill=255)
    
    if preset.crescent:
        hole = Image.new("L", (w, h), 0)
        hd = ImageDraw.Draw(hole)
        ox = radius * 0.36
        oy = -radius * 0.14
        hd.ellipse(_box(cx + ox, cy + oy, radius * 0.98), fill=255)
        body = ImageChops.subtract(body, hole)
        
    disc = Image.new("RGBA", (w, h), preset.moon + (255,))
    disc.putalpha(body)
    
    highlight = radial_glow(
        size, cx - radius * 0.20, cy - radius * 0.25, radius * 0.75, (255, 255, 248), 110
    )
    out = Image.alpha_composite(out, disc)
    out = Image.alpha_composite(out, highlight)
    return out


def stars_layer(size: tuple[int, int], count: int, color: RGB, seed: int) -> Image.Image:
    if count <= 0:
        return Image.new("RGBA", size, (0, 0, 0, 0))
    rng = random.Random(seed + 7)
    w, h = size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(count):
        x = rng.randint(int(w * 0.32), w - 12)
        y = rng.randint(12, int(h * 0.60))
        r = rng.choice([1, 1, 1, 2, 2, 3])
        a = rng.randint(60, 200)
        d.ellipse(_box(x, y, r), fill=color + (a,))
        # Occasional 4-point subtle star twinkle
        if r >= 2 and rng.random() > 0.65:
            arm = rng.randint(3, 6)
            d.line([(x - arm, y), (x + arm, y)], fill=color + (a // 2,), width=1)
            d.line([(x, y - arm), (x, y + arm)], fill=color + (a // 2,), width=1)
    return layer


def mountain_layer(size: tuple[int, int], base_y: float, height: float, color: RGB, alpha: int = 55, seed: int = 1) -> Image.Image:
    w, h = size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    rng = random.Random(seed)
    
    step = 8
    points = [(0, h)]
    p1 = rng.uniform(0.0015, 0.0028)
    p2 = rng.uniform(0.0040, 0.0075)
    p3 = rng.uniform(0.0090, 0.0160)
    phase1 = rng.uniform(0, 6.28)
    phase2 = rng.uniform(0, 6.28)
    phase3 = rng.uniform(0, 6.28)
    
    for x in range(0, w + step, step):
        y = base_y - math.sin(x * p1 + phase1) * height * 0.55 - math.cos(x * p2 + phase2) * height * 0.32 - math.sin(x * p3 + phase3) * height * 0.13
        points.append((x, int(y)))
    points.append((w, h))
    d.polygon(points, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2))
    mask = mask.point(lambda p: int(p * alpha / 255))
    
    layer = Image.new("RGBA", (w, h), color + (0,))
    layer.putalpha(mask)
    return layer


def editorial_accents(size: tuple[int, int], color: RGB, alpha: int = 40) -> Image.Image:
    w, h = size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c = color + (alpha,)
    
    pad_x = int(w * 0.035)
    pad_y = int(h * 0.045)
    arm = max(5, int(min(w, h) * 0.010))
    
    # Elegant thin corner registration crosses
    for cx, cy in [(pad_x, pad_y), (w - pad_x, pad_y), (pad_x, h - pad_y), (w - pad_x, h - pad_y)]:
        d.line([(cx - arm, cy), (cx + arm, cy)], fill=c, width=1)
        d.line([(cx, cy - arm), (cx, cy + arm)], fill=c, width=1)
        
    # Extremely subtle hairline inner boundary
    d.rectangle([pad_x, pad_y, w - pad_x, h - pad_y], outline=color + (int(alpha * 0.45),), width=1)
    return layer


def seal_stamp(size: tuple[int, int], cx: float, cy: float, radius: float, text: str, color: RGB, font) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = int(radius)
    
    # Outer rounded square or circle with authentic seal framing
    box = [cx - r, cy - r, cx + r, cy + r]
    d.rounded_rectangle(box, radius=int(r * 0.28), outline=color + (210,), width=max(2, r // 14))
    
    inner_r = r * 0.82
    inner_box = [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r]
    d.rounded_rectangle(inner_box, radius=int(inner_r * 0.24), outline=color + (160,), width=max(1, r // 24))
    
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((cx - tw / 2, cy - th / 2 - r * 0.04), text, font=font, fill=color + (230,))
    return layer.rotate(-8, resample=Image.Resampling.BICUBIC, center=(cx, cy))


def wash_layer(size: tuple[int, int], preset: Preset, cx: float, cy: float, radius: float) -> Image.Image:
    return radial_glow(size, cx, cy, radius, preset.wash, 50)


def grain_rgb(img: Image.Image, amount: float, seed: int) -> Image.Image:
    if amount <= 0:
        return img.convert("RGB")
    rgb = img.convert("RGB")
    rng = random.Random(seed)
    sigma = 16 + rng.randint(0, 8)
    noise = Image.effect_noise(rgb.size, sigma).convert("RGB")
    return Image.blend(rgb, noise, amount)


def vignette(img: Image.Image, strength: float = 0.18) -> Image.Image:
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    pad = int(min(w, h) * 0.04)
    d.rounded_rectangle([pad, pad, w - pad, h - pad], radius=int(min(w, h) * 0.08), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(int(min(w, h) * 0.14)))
    shade = Image.new("RGB", (w, h), (18, 14, 12))
    return Image.composite(img, Image.blend(img, shade, strength), mask)


def card_drop_shadow(
    size: tuple[int, int],
    box: list[float] | tuple[float, float, float, float],
    radius: float,
    blur: int = 24,
    offset_y: float = 14,
    color: RGB = (0, 0, 0),
    alpha: int = 50,
) -> Image.Image:
    w, h = size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    x0, y0, x1, y1 = box
    sbox = [int(x0), int(y0 + offset_y), int(x1), int(y1 + offset_y)]
    d.rounded_rectangle(sbox, radius=int(radius), fill=min(255, max(0, alpha)))
    if blur > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(blur))
    layer = Image.new("RGBA", (w, h), color + (0,))
    layer.putalpha(mask)
    return layer


def card_tape(
    size: tuple[int, int],
    cx: float,
    cy: float,
    tape_w: float = 160,
    tape_h: float = 42,
    angle: float = -20,
    color: tuple[int, int, int, int] = (230, 220, 200, 215),
) -> Image.Image:
    """Renders a semi-transparent washi tape (和纸/牛皮纸胶带) with torn edges and soft shadow."""
    tw = int(tape_w)
    th = int(tape_h)
    tape = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    td = ImageDraw.Draw(tape)

    # Torn zigzag edge on left and right
    points = [(8, 0)]
    for x in range(8, tw - 8, 4):
        points.append((x, 0))
    # Right torn edge
    for y in range(0, th, 4):
        offset_x = tw - (4 if (y // 4) % 2 == 0 else 8)
        points.append((offset_x, y))
    points.append((tw - 8, th))
    for x in range(tw - 8, 8, -4):
        points.append((x, th))
    # Left torn edge
    for y in range(th, 0, -4):
        offset_x = 4 if (y // 4) % 2 == 0 else 8
        points.append((offset_x, y))
    points.append((8, 0))

    td.polygon(points, fill=color, outline=(color[0] - 20, color[1] - 20, color[2] - 20, 160))

    # Add subtle fiber noise to tape
    rng = random.Random(int(cx * 10 + cy))
    for _ in range(40):
        rx = rng.randint(10, tw - 12)
        ry = rng.randint(4, th - 4)
        td.line([(rx, ry), (rx + rng.randint(2, 6), ry)], fill=(255, 255, 255, 60), width=1)

    # Rotate tape
    rot_tape = tape.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)

    # Create shadow for tape
    alpha_mask = rot_tape.split()[3]
    shadow_mask = alpha_mask.filter(ImageFilter.GaussianBlur(6))
    shadow_mask = shadow_mask.point(lambda p: int(p * 0.35))

    rot_shadow = Image.new("RGBA", rot_tape.size, (40, 30, 20, 0))
    rot_shadow.putalpha(shadow_mask)

    # Place onto full canvas
    w, h = size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rw, rh = rot_tape.size
    paste_x = int(cx - rw / 2)
    paste_y = int(cy - rh / 2)

    layer.paste(rot_shadow, (paste_x, paste_y + 3), rot_shadow)
    layer.paste(rot_tape, (paste_x, paste_y), rot_tape)
    return layer


def swiss_art(size: tuple[int, int], preset: Preset, seed: int) -> Image.Image:
    """Renders a clean, modern Swiss-style international typographic grid layout without moons."""
    w, h = size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    unit = min(w, h)

    # Subtle grid lines
    step = int(unit * 0.12)
    grid_color = preset.brand + (18,)
    cross_color = preset.accent + (120,)

    for x in range(step, w, step):
        d.line([(x, 0), (x, h)], fill=grid_color, width=1)
    for y in range(step, h, step):
        d.line([(0, y), (w, y)], fill=grid_color, width=1)

    # Crosshairs at select intersections
    rng = random.Random(seed)
    arm = max(4, int(unit * 0.008))
    for x in range(step * 2, w - step, step * 2):
        for y in range(step * 2, h - step, step * 2):
            if rng.random() > 0.4:
                d.line([(x - arm, y), (x + arm, y)], fill=cross_color, width=1)
                d.line([(x, y - arm), (x, y + arm)], fill=cross_color, width=1)

    # Right-side geometric accent bar
    bar_w = max(4, int(unit * 0.008))
    bar_x = int(w * 0.93)
    d.line([(bar_x, int(h * 0.15)), (bar_x, int(h * 0.85))], fill=preset.accent + (180,), width=bar_w)
    d.ellipse(_box(bar_x, h * 0.15, bar_w * 1.5), fill=preset.accent + (220,))
    d.ellipse(_box(bar_x, h * 0.85, bar_w * 1.5), fill=preset.accent + (220,))

    # Technical datum annotations
    tag_color = preset.kicker + (140,)
    d.text((int(w * 0.06), int(h * 0.94)), "SYS // 04.09 · INTERNATIONAL TYPOGRAPHIC", fill=tag_color)
    d.text((int(w * 0.65), int(h * 0.05)), "INDEX // 120.19°E  30.26°N", fill=tag_color)
    return layer


def press_art(size: tuple[int, int], preset: Preset, seed: int) -> Image.Image:
    """Renders a vintage editorial newspaper / press layout with double border lines."""
    w, h = size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    unit = min(w, h)

    pad_outer = int(unit * 0.038)
    pad_inner = int(unit * 0.046)

    # Outer 2px rule
    d.rectangle([pad_outer, pad_outer, w - pad_outer, h - pad_outer], outline=preset.brand + (180,), width=2)
    # Inner 1px rule
    d.rectangle([pad_inner, pad_inner, w - pad_inner, h - pad_inner], outline=preset.brand + (120,), width=1)

    # Corner corner-bracket marks
    c_len = int(unit * 0.024)
    for cx, cy, dx, dy in (
        (pad_inner + 4, pad_inner + 4, 1, 1),
        (w - pad_inner - 4, pad_inner + 4, -1, 1),
        (pad_inner + 4, h - pad_inner - 4, 1, -1),
        (w - pad_inner - 4, h - pad_inner - 4, -1, -1),
    ):
        d.line([(cx, cy), (cx + dx * c_len, cy)], fill=preset.accent + (220,), width=2)
        d.line([(cx, cy), (cx, cy + dy * c_len)], fill=preset.accent + (220,), width=2)

    # Bottom press stamp rule
    bot_y = int(h * 0.92)
    d.line([(pad_inner, bot_y), (w - pad_inner, bot_y)], fill=preset.brand + (100,), width=1)
    d.text((pad_inner + 12, bot_y + 4), "THE CHRONICLE · EDITORIAL SPECIAL DISPATCH", fill=preset.kicker + (160,))
    return layer
