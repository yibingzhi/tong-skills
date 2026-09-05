from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


RGB = tuple[int, int, int]


@dataclass(frozen=True)
class Preset:
    name: str
    mood: str
    top: RGB
    bottom: RGB
    wash: RGB
    cloud: tuple[RGB, RGB, RGB]
    cloud_shadow: RGB
    moon: RGB
    glow: RGB
    brand: RGB
    title: RGB
    kicker: RGB
    date: RGB
    accent: RGB
    grain: float
    stars: int
    crescent: bool


PRESETS = {
    "twilight": Preset(
        name="twilight",
        mood="暮光云朵 · 奶油底 · 蓝粉橙",
        top=(255, 236, 214),
        bottom=(255, 248, 236),
        wash=(255, 186, 140),
        cloud=((140, 198, 230), (255, 176, 196), (255, 168, 112)),
        cloud_shadow=(196, 140, 118),
        moon=(255, 214, 118),
        glow=(255, 186, 120),
        brand=(118, 96, 86),
        title=(72, 56, 50),
        kicker=(148, 124, 112),
        date=(168, 144, 132),
        accent=(232, 132, 88),
        grain=0.055,
        stars=0,
        crescent=True,
    ),
    "dusk": Preset(
        name="dusk",
        mood="夜空金月 · 墨蓝",
        top=(28, 36, 62),
        bottom=(12, 16, 32),
        wash=(90, 70, 140),
        cloud=((72, 92, 140), (110, 88, 132), (156, 102, 118)),
        cloud_shadow=(24, 28, 48),
        moon=(255, 220, 140),
        glow=(255, 176, 96),
        brand=(214, 220, 236),
        title=(248, 246, 240),
        kicker=(156, 168, 196),
        date=(132, 144, 172),
        accent=(232, 176, 96),
        grain=0.07,
        stars=48,
        crescent=True,
    ),
    "paper": Preset(
        name="paper",
        mood="宣纸朱印 · 墨云",
        top=(246, 240, 226),
        bottom=(236, 226, 206),
        wash=(210, 186, 150),
        cloud=((132, 136, 140), (176, 168, 156), (118, 108, 96)),
        cloud_shadow=(120, 108, 92),
        moon=(232, 214, 176),
        glow=(200, 160, 120),
        brand=(92, 48, 40),
        title=(36, 32, 28),
        kicker=(122, 96, 82),
        date=(140, 118, 100),
        accent=(176, 48, 42),
        grain=0.08,
        stars=0,
        crescent=False,
    ),
    "frost": Preset(
        name="frost",
        mood="霜蓝冷雾",
        top=(226, 238, 246),
        bottom=(244, 248, 252),
        wash=(160, 200, 230),
        cloud=((170, 210, 230), (210, 226, 236), (186, 214, 228)),
        cloud_shadow=(140, 168, 186),
        moon=(244, 248, 255),
        glow=(180, 214, 236),
        brand=(70, 96, 118),
        title=(28, 48, 68),
        kicker=(96, 124, 148),
        date=(120, 144, 164),
        accent=(56, 132, 176),
        grain=0.05,
        stars=12,
        crescent=False,
    ),
    "ember": Preset(
        name="ember",
        mood="烬暖 · 深褐火光",
        top=(48, 28, 24),
        bottom=(22, 14, 14),
        wash=(180, 70, 40),
        cloud=((120, 52, 40), (176, 78, 48), (210, 120, 64)),
        cloud_shadow=(40, 18, 16),
        moon=(255, 186, 92),
        glow=(255, 120, 48),
        brand=(236, 210, 176),
        title=(255, 242, 220),
        kicker=(196, 150, 118),
        date=(168, 124, 96),
        accent=(255, 122, 54),
        grain=0.075,
        stars=18,
        crescent=True,
    ),
    "dawn": Preset(
        name="dawn",
        mood="日曜 · 浅金粉",
        top=(255, 226, 210),
        bottom=(255, 244, 230),
        wash=(255, 150, 120),
        cloud=((255, 176, 150), (255, 206, 140), (255, 168, 118)),
        cloud_shadow=(196, 130, 108),
        moon=(255, 220, 140),
        glow=(255, 170, 110),
        brand=(118, 78, 68),
        title=(72, 42, 36),
        kicker=(156, 112, 96),
        date=(168, 124, 108),
        accent=(232, 96, 72),
        grain=0.05,
        stars=8,
        crescent=True,
    ),
    "ink": Preset(
        name="ink",
        mood="墨青编辑风",
        top=(18, 28, 32),
        bottom=(8, 12, 16),
        wash=(40, 90, 92),
        cloud=((36, 64, 70), (50, 78, 82), (70, 96, 92)),
        cloud_shadow=(10, 16, 18),
        moon=(210, 228, 220),
        glow=(80, 160, 150),
        brand=(186, 210, 204),
        title=(244, 246, 242),
        kicker=(140, 168, 164),
        date=(112, 140, 138),
        accent=(88, 196, 176),
        grain=0.06,
        stars=28,
        crescent=False,
    ),
}

RATIOS = {
    "16:9": (1672, 941),
    "1:1": (1400, 1400),
    "4:3": (1400, 1050),
    "3:4": (1050, 1400),
    "9:16": (1080, 1920),
    "2.35:1": (1880, 800),
    "3:1": (1800, 600),
    "4:1": (1600, 400),
}

LAYOUTS = ("editorial", "poster", "banner", "story", "feed", "divider", "quote", "bullet", "square", "briefing")
QUOTE_STYLES = ("paper", "editorial", "highlight", "dark", "cinema", "polaroid", "tweet")
COVER_THEMES = ("celestial", "swiss", "press")
LAYOUT_ALIASES = {
    "masthead": "editorial",
    "刊头": "editorial",
    "头图": "editorial",
    "封面": "feed",
    "分割条": "divider",
    "金句": "quote",
    "金句卡": "quote",
    "摘要": "bullet",
    "速览": "bullet",
    "方图": "square",
    "简报": "briefing",
    "竖封": "briefing",
    "竖版": "briefing",
    "海报": "briefing",
}

WEEKDAY_PRESET = {
    "一": "dusk",
    "二": "twilight",
    "三": "paper",
    "四": "frost",
    "五": "ember",
    "六": "ink",
    "日": "dawn",
    "天": "dawn",
}

_WEEKDAY_RE = re.compile(r"(?:星期|周)([一二三四五六日天])")
_CAL_RE = re.compile(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日")
_WEEKDAY_CN = "一二三四五六日"

_HINTS = (
    ("夜", "dusk"),
    ("晚", "dusk"),
    ("黑", "dusk"),
    ("纸", "paper"),
    ("书", "paper"),
    ("古", "paper"),
    ("霜", "frost"),
    ("冰", "frost"),
    ("冷", "frost"),
    ("火", "ember"),
    ("暖", "ember"),
    ("烬", "ember"),
    ("墨", "ink"),
    ("青", "ink"),
)


_MONTH_EN = ("", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
_WEEKDAY_EN = {
    "一": ("MON", "MONDAY"),
    "二": ("TUE", "TUESDAY"),
    "三": ("WED", "WEDNESDAY"),
    "四": ("THU", "THURSDAY"),
    "五": ("FRI", "FRIDAY"),
    "六": ("SAT", "SATURDAY"),
    "日": ("SUN", "SUNDAY"),
}


def today_cn_date() -> str:
    now = datetime.now()
    return "%s月%s日 星期%s" % (now.month, now.day, _WEEKDAY_CN[now.weekday()])


def weekday_char(text: str) -> str:
    match = _WEEKDAY_RE.search(text or "")
    if not match:
        return ""
    ch = match.group(1)
    return "日" if ch == "天" else ch


def parse_calendar(date: str):
    text = date or ""
    cal = _CAL_RE.search(text)
    month = int(cal.group(2)) if cal else None
    day = int(cal.group(3)) if cal else None
    ch = weekday_char(text)
    weekday = "星期%s" % ch if ch else ""
    
    en_month = _MONTH_EN[month] if (month and 1 <= month <= 12) else ""
    en_short, en_full = _WEEKDAY_EN.get(ch, ("", ""))
    en_date = ("%s · %s %02d" % (en_short, en_month, day)) if (en_short and en_month and day) else ""
    return month, day, weekday, en_date, en_full


def pick_preset(title: str = "", brand: str = "", explicit: str = "auto", date: str = "") -> str:
    if explicit and explicit != "auto":
        key = explicit.lower()
        if key not in PRESETS:
            raise ValueError("未知预设 %s，可选: %s" % (explicit, ", ".join(PRESETS)))
        return key
    ch = weekday_char(date)
    if ch:
        return WEEKDAY_PRESET[ch]
    blob = "%s%s" % (title, brand)
    for needle, name in _HINTS:
        if needle in blob:
            return name
    return "twilight"


def pick_layout(ratio: str, explicit: str = "auto") -> str:
    if explicit and explicit != "auto":
        key = LAYOUT_ALIASES.get(explicit, explicit)
        if key in ("poster", "story"):
            key = "briefing"
        if key not in LAYOUTS:
            raise ValueError("未知版式 %s，可选: %s" % (explicit, ", ".join(LAYOUTS)))
        return key
    if ratio == "2.35:1":
        return "feed"
    if ratio == "16:9":
        return "banner"
    if ratio in ("3:4", "9:16", "4:5"):
        return "briefing"
    return "editorial"
