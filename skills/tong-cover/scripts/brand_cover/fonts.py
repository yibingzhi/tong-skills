from __future__ import annotations

import os
import sys
import shutil
import tempfile
import urllib.request
from fnmatch import fnmatch
from functools import lru_cache
from typing import NamedTuple

from PIL import ImageFont


class TextBounds(NamedTuple):
    x0: int
    y0: int
    x1: int
    y1: int
    w: int
    h: int


_CJK_KINDS = frozenset({"headline", "fangsong", "serif", "kai", "bold", "sans", "sans_light"})

_KIND_GLOBS = {
    "display_num": (
        "constanb.ttf",
        "georgiab.ttf",
        "timesbd.ttf",
        "LiberationSerif-Bold.*",
        "NotoSerif*Bold*.ttf",
        "NotoSerif*Bold*.otf",
        "DejaVuSerif-Bold.ttf",
        "NotoSansSC-Bold.*",
        "NotoSansCJK*Bold*",
        "SourceHanSerif*Bold*",
    ),
    "en_serif": (
        "constan.ttf",
        "georgia.ttf",
        "times.ttf",
        "LiberationSerif-Regular.*",
        "NotoSerif-Regular.*",
        "DejaVuSerif.ttf",
        "NotoSerifCJK*",
        "SourceHanSerif*",
    ),
    "headline": (
        "STZHONGS.TTF",
        "msyhbd.ttc",
        "Dengb.ttf",
        "simhei.ttf",
        "NotoSansSC-Bold.*",
        "NotoSansCJK*Bold*",
        "SourceHanSans*Bold*",
        "NotoSansSC-Regular.*",
        "NotoSansCJK*",
        "wqy-microhei.*",
        "PingFang*",
    ),
    "fangsong": (
        "STFANGSO.TTF",
        "simfang.ttf",
        "STSONG.TTF",
        "simsun.ttc",
        "Songti*",
        "NotoSerifSC*",
        "NotoSerifCJK*",
        "SourceHanSerif*",
        "NotoSansSC-Regular.*",
        "NotoSansCJK*",
    ),
    "serif": (
        "STSONG.TTF",
        "simsun.ttc",
        "STZHONGS.TTF",
        "Songti*",
        "NotoSerifSC*",
        "NotoSerifCJK*",
        "SourceHanSerif*",
        "NotoSansSC*",
        "NotoSansCJK*",
    ),
    "kai": (
        "STKAITI.TTF",
        "simkai.ttf",
        "STZHONGS.TTF",
        "NotoSerifSC*",
        "NotoSerifCJK*",
        "NotoSansSC*",
        "NotoSansCJK*",
        "wqy-zenhei.*",
    ),
    "bold": (
        "Dengb.ttf",
        "msyhbd.ttc",
        "simhei.ttf",
        "NotoSansSC-Bold.*",
        "NotoSansCJK*Bold*",
        "SourceHanSans*Bold*",
        "NotoSansSC-Regular.*",
        "wqy-microhei.*",
        "PingFang*",
    ),
    "sans": (
        "Deng.ttf",
        "msyh.ttc",
        "PingFang*",
        "NotoSansSC-Regular.*",
        "NotoSansCJK*Regular*",
        "NotoSansCJK*",
        "SourceHanSans*Regular*",
        "SourceHanSansCN*",
        "wqy-microhei.*",
        "DroidSansFallback*",
    ),
    "sans_light": (
        "Dengl.ttf",
        "msyhl.ttc",
        "NotoSansSC-Light.*",
        "NotoSansSC-DemiLight.*",
        "NotoSansCJK*Light*",
        "NotoSansSC-Regular.*",
        "NotoSansCJK*",
        "wqy-microhei.*",
        "Deng.ttf",
        "msyh.ttc",
    ),
}

_WIN_DIR = "C:/Windows/Fonts"
_MAC_DIRS = (
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    "/Library/Fonts",
)
_LINUX_DIRS = (
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    "/usr/share/fonts/opentype",
    "/usr/share/fonts/truetype",
    "/usr/share/fonts/opentype/noto",
    "/usr/share/fonts/opentype/noto-cjk",
    "/usr/share/fonts/truetype/noto",
    "/usr/share/fonts/truetype/noto-cjk",
    "/usr/share/fonts/google-noto-cjk",
    "/usr/share/fonts/truetype/wqy",
    "/usr/share/fonts/truetype/droid",
    "/usr/share/fonts/truetype/arphic",
    "/usr/share/fonts/opentype/source-han-sans",
    "/usr/share/fonts/opentype/source-han-serif",
    "/usr/share/fonts/adobe-source-han-sans-cn",
)

_FETCH_URLS = (
    (
        "NotoSansSC-Regular.otf",
        "https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf",
        "https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf",
    ),
    (
        "NotoSansSC-Bold.otf",
        "https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Sans/SubsetOTF/SC/NotoSansSC-Bold.otf",
        "https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/SC/NotoSansSC-Bold.otf",
    ),
)


def _bundled_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def _cache_dir() -> str:
    root = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(root, "brand-cover", "fonts")


def _extra_dirs() -> list[str]:
    dirs = []
    env_dir = os.environ.get("BRAND_COVER_FONT_DIR", "").strip()
    if env_dir:
        dirs.append(env_dir)
    env_file = os.environ.get("BRAND_COVER_FONT", "").strip()
    if env_file:
        dirs.append(os.path.dirname(env_file) or ".")
    home = os.path.expanduser("~")
    dirs.extend(
        [
            os.path.join(home, ".local", "share", "fonts"),
            os.path.join(home, ".fonts"),
            _bundled_dir(),
            _cache_dir(),
        ]
    )
    return dirs


def _font_roots() -> list[str]:
    roots = []
    if os.path.isdir(_WIN_DIR):
        roots.append(_WIN_DIR)
    for path in _MAC_DIRS:
        if os.path.isdir(path):
            roots.append(path)
    for path in _LINUX_DIRS:
        if os.path.isdir(path):
            roots.append(path)
    roots.extend(d for d in _extra_dirs() if os.path.isdir(d))
    return roots


def _iter_font_files(root: str):
    if os.path.isfile(root):
        yield root
        return
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            lower = name.lower()
            if lower.endswith((".ttf", ".otf", ".ttc", ".otc")):
                yield os.path.join(dirpath, name)


@lru_cache(maxsize=1)
def _catalog() -> tuple[str, ...]:
    seen = []
    env_file = os.environ.get("BRAND_COVER_FONT", "").strip()
    if env_file and os.path.isfile(env_file):
        seen.append(os.path.abspath(env_file))
    for root in _font_roots():
        for path in _iter_font_files(root):
            seen.append(os.path.abspath(path))
    # fontconfig (Linux/mac)
    try:
        import subprocess

        out = subprocess.check_output(
            ["fc-list", ":lang=zh", "file"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        )
        for line in out.splitlines():
            path = line.split(":")[0].strip()
            if path and os.path.isfile(path):
                seen.append(os.path.abspath(path))
    except Exception:
        pass
    uniq = []
    used = set()
    for path in seen:
        if path not in used:
            used.add(path)
            uniq.append(path)
    return tuple(uniq)


def _name_matches(path: str, patterns: tuple[str, ...]) -> bool:
    name = os.path.basename(path)
    for raw in patterns:
        if fnmatch(name, raw) or fnmatch(name.lower(), raw.lower()):
            return True
    return False


def _open_face(path: str, size: int, index: int = 0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except OSError:
        return None


def _has_cjk(font) -> bool:
    try:
        cjk = font.getbbox("国")
        missing = font.getbbox("\uFFFF")
        if not cjk:
            return False
        if missing and tuple(cjk) == tuple(missing):
            return False
        return (cjk[2] - cjk[0]) > 4
    except Exception:
        return False


def _best_index(path: str, need_cjk: bool) -> int | None:
    lower = path.lower()
    collection = lower.endswith(".ttc") or lower.endswith(".otc")
    indexes = range(8) if collection else range(1)
    fallback = None
    for index in indexes:
        font = _open_face(path, 32, index)
        if font is None:
            if index == 0:
                return None
            break
        if not need_cjk:
            return index
        if _has_cjk(font):
            try:
                family = " ".join(font.getname()).lower()
            except Exception:
                family = ""
            if any(token in family for token in (" sc", " cn", " hans", "simplified", "gb")):
                return index
            if fallback is None:
                fallback = index
    return fallback


def _fetch_noto() -> list[str]:
    dest_dir = _cache_dir()
    os.makedirs(dest_dir, exist_ok=True)
    saved = []
    for filename, *urls in _FETCH_URLS:
        dest = os.path.join(dest_dir, filename)
        if os.path.isfile(dest) and os.path.getsize(dest) > 100000:
            saved.append(dest)
            continue
        ok = False
        for url in urls:
            tmp_path = None
            try:
                print("brand-cover: fetching %s" % filename, file=sys.stderr)
                with urllib.request.urlopen(url, timeout=30) as resp:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".otf") as tmp:
                        shutil.copyfileobj(resp, tmp)
                        tmp_path = tmp.name
                if tmp_path and os.path.getsize(tmp_path) > 100000:
                    shutil.move(tmp_path, dest)
                    saved.append(dest)
                    ok = True
                    break
            except Exception:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
        if not ok:
            continue
    return saved


@lru_cache(maxsize=16)
def resolve_font(kind: str) -> tuple[str, int] | None:
    need_cjk = kind in _CJK_KINDS
    patterns = _KIND_GLOBS.get(kind, _KIND_GLOBS["sans"])
    catalog = list(_catalog())
    env_file = os.environ.get("BRAND_COVER_FONT", "").strip()
    ranked = []
    if env_file and os.path.isfile(env_file):
        ranked.append(os.path.abspath(env_file))
    ranked.extend(path for path in catalog if _name_matches(path, patterns))
    if need_cjk:
        ranked.extend(
            path
            for path in catalog
            if any(token in os.path.basename(path).lower() for token in ("noto", "sourcehan", "wqy", "droid", "uming", "cjk", "hans"))
        )
    ranked.extend(catalog)

    seen = set()
    for path in ranked:
        if path in seen:
            continue
        seen.add(path)
        index = _best_index(path, need_cjk)
        if index is None:
            continue
        return path, index

    fetched = _fetch_noto()
    if fetched:
        _catalog.cache_clear()
        for path in fetched:
            index = _best_index(path, need_cjk)
            if index is not None:
                return path, index
    return None


@lru_cache(maxsize=64)
def load_font(kind: str, size: int):
    size = max(8, int(size))
    resolved = resolve_font(kind)
    if resolved:
        path, index = resolved
        font = _open_face(path, size, index)
        if font is not None:
            return font
    if kind != "sans":
        resolved = resolve_font("sans")
        if resolved:
            font = _open_face(resolved[0], size, resolved[1])
            if font is not None:
                return font
    print("brand-cover: no CJK font found, Chinese will tofu. Set BRAND_COVER_FONT or install fonts-noto-cjk.", file=sys.stderr)
    return ImageFont.load_default()


def diagnose() -> list[str]:
    lines = []
    for kind in _KIND_GLOBS:
        resolved = resolve_font(kind)
        if not resolved:
            lines.append("%s: MISSING" % kind)
            continue
        path, index = resolved
        font = _open_face(path, 24, index)
        cjk = "cjk" if (font and _has_cjk(font)) else "no-cjk"
        lines.append("%s: %s  index=%s  %s" % (kind, path, index, cjk))
    return lines


def text_bounds(draw, pos: tuple[float, float], text: str, font) -> TextBounds:
    if not text:
        x, y = int(pos[0]), int(pos[1])
        return TextBounds(x, y, x, y, 0, 0)
    bbox = draw.textbbox((pos[0], pos[1]), text, font=font, anchor="lt")
    x0, y0, x1, y1 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
    return TextBounds(x0, y0, x1, y1, max(0, x1 - x0), max(0, y1 - y0))


def draw_text_measured(draw, pos: tuple[float, float], text: str, font, fill) -> TextBounds:
    if not text:
        x, y = int(pos[0]), int(pos[1])
        return TextBounds(x, y, x, y, 0, 0)
    x, y = int(pos[0]), int(pos[1])
    draw.text((x, y), text, font=font, fill=fill, anchor="lt")
    return text_bounds(draw, (x, y), text, font)


def text_size(draw, text: str, font) -> tuple[int, int]:
    if not text:
        return 0, 0
    bbox = draw.textbbox((0, 0), text, font=font, anchor="lt")
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def letterspace(text: str, gap: str = " ") -> str:
    chars = [ch for ch in text if not ch.isspace()]
    return gap.join(chars)
