#!/usr/bin/env python3
"""Render Mermaid source to validated PNG and optional SVG files.

Local-first: Python launches Node + mermaid-cli on macOS, Windows, and Linux.
Remote Kroki / mermaid.ink are opt-in only.
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zlib
from copy import deepcopy
from pathlib import Path
from typing import Any


KROKI_PNG = "https://kroki.io/mermaid/png"
KROKI_SVG = "https://kroki.io/mermaid/svg"
MERMAID_INK_PNG = "https://mermaid.ink/img/{encoded}"
MERMAID_INK_SVG = "https://mermaid.ink/svg/{encoded}"
UA = "tong-chart-skill/3.1"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SANKEY_PALETTE = (
    "#3D6EB5",
    "#6F91C5",
    "#4A8B68",
    "#B08D4F",
    "#7A6F92",
    "#A8B6C8",
)
AURORA_SANKEY_PALETTE = (
    "#3F72F2",
    "#7C5CE7",
    "#19A987",
    "#F0A13B",
    "#E45F7A",
    "#46A7E8",
)
AURORA_BACKGROUND_STOPS = (
    (226, 238, 255),
    (239, 228, 255),
    (220, 249, 239),
)


DIAGRAM_KEYWORDS = {
    "flowchart": "flowchart",
    "graph": "flowchart",
    "sequencediagram": "sequence",
    "statediagram": "state",
    "statediagram-v2": "state",
    "classdiagram": "class",
    "erdiagram": "er",
    "mindmap": "mindmap",
    "timeline": "timeline",
    "gantt": "gantt",
    "gitgraph": "gitgraph",
    "journey": "journey",
    "pie": "pie",
    "quadrantchart": "quadrant",
    "architecture-beta": "architecture-native",
    "block": "block",
    "block-beta": "block",
    "kanban": "kanban",
    "sankey": "sankey",
    "sankey-beta": "sankey",
    "xychart": "xychart",
    "xychart-beta": "xychart",
}


THEME_DEFAULT_LOOK = {
    "cursor": "classic",
    "aurora": "neo",
    "docs": "neo",
    "dark": "classic",
    "ocean": "classic",
    "forest": "classic",
    "neutral": "classic",
    "minimal": "classic",
}


# Premium editorial palette: cool paper, ink text, quiet role colors.
# Goal: expensive-looking restraint, not saturated stickers.
THEMES: dict[str, dict[str, Any]] = {
    "docs": {
        "theme": "base",
        "htmlLabels": True,
        "themeCSS": (
            ".edgeLabel { font-size: 12px; color: #64748B; }"
            ".cluster-label .nodeLabel { font-weight: 600; letter-spacing: 0.02em; }"
        ),
        "themeVariables": {
            "darkMode": False,
            "background": "#F8FAFC",
            "fontFamily": (
                "Inter, Segoe UI, PingFang SC, Microsoft YaHei, "
                "Noto Sans SC, sans-serif"
            ),
            "fontSize": "16px",
            "primaryColor": "#F1F5F9",
            "primaryTextColor": "#0F172A",
            "primaryBorderColor": "#64748B",
            "secondaryColor": "#F5F0E6",
            "secondaryTextColor": "#6B5428",
            "secondaryBorderColor": "#B08D4F",
            "tertiaryColor": "#EEF2F7",
            "tertiaryTextColor": "#334155",
            "tertiaryBorderColor": "#CBD5E1",
            "lineColor": "#94A3B8",
            "textColor": "#0F172A",
            "mainBkg": "#FFFFFF",
            "nodeBorder": "#CBD5E1",
            "nodeTextColor": "#0F172A",
            "clusterBkg": "#F1F5F9",
            "clusterBorder": "#E2E8F0",
            "titleColor": "#0F172A",
            "edgeLabelBackground": "#F8FAFC",
            "actorBkg": "#FFFFFF",
            "actorBorder": "#64748B",
            "actorTextColor": "#0F172A",
            "actorLineColor": "#CBD5E1",
            "signalColor": "#64748B",
            "signalTextColor": "#0F172A",
            "labelBoxBkgColor": "#FFFFFF",
            "labelBoxBorderColor": "#E2E8F0",
            "labelTextColor": "#334155",
            "loopTextColor": "#475569",
            "noteBkgColor": "#F8F4EC",
            "noteTextColor": "#6B5428",
            "noteBorderColor": "#C4A574",
            "stateBkg": "#FFFFFF",
            "stateBorder": "#64748B",
            "stateLabelColor": "#0F172A",
            "classText": "#0F172A",
            "relationColor": "#64748B",
            "relationLabelColor": "#475569",
            "attributeBackgroundColorOdd": "#FFFFFF",
            "attributeBackgroundColorEven": "#F8FAFC",
            "git0": "#3D6EB5",
            "git1": "#4A8B68",
            "git2": "#B08D4F",
            "git3": "#7A6F92",
            "gitInv0": "#FFFFFF",
            "gitInv1": "#FFFFFF",
            "gitInv2": "#FFFFFF",
            "gitInv3": "#FFFFFF",
            "pie1": "#3D6EB5",
            "pie2": "#6F91C5",
            "pie3": "#4A8B68",
            "pie4": "#B08D4F",
            "pie5": "#7A6F92",
            "pie6": "#A8B6C8",
            "pie7": "#D3B879",
            "pie8": "#8EB5A0",
            "pieTitleTextSize": "22px",
            "pieTitleTextColor": "#0F172A",
            "pieSectionTextSize": "14px",
            "pieSectionTextColor": "#0F172A",
            "pieLegendTextSize": "14px",
            "pieLegendTextColor": "#334155",
            "pieStrokeColor": "#F8FAFC",
            "pieStrokeWidth": "2px",
            "pieOuterStrokeColor": "#CBD5E1",
            "pieOuterStrokeWidth": "1px",
            "pieOpacity": "0.94",
            "sectionBkgColor": "#F1F5F9",
            "altSectionBkgColor": "#FFFFFF",
            "sectionBkgColor2": "#EEF2F7",
            "gridColor": "#CBD5E1",
            "taskBkgColor": "#DCE7F7",
            "taskBorderColor": "#3B6FB0",
            "taskTextColor": "#0F172A",
            "taskTextOutsideColor": "#334155",
            "activeTaskBkgColor": "#E6F2EB",
            "activeTaskBorderColor": "#4A8B68",
            "doneTaskBkgColor": "#E2E8F0",
            "doneTaskBorderColor": "#94A3B8",
            "critBkgColor": "#F5F0E6",
            "critBorderColor": "#B08D4F",
            "todayLineColor": "#B08D4F",
            "cScale0": "#DCE7F7",
            "cScale1": "#E8EEF8",
            "cScale2": "#E6F2EB",
            "cScale3": "#F5F0E6",
            "cScale4": "#EEEAF3",
            "cScale5": "#EEF2F7",
            "cScaleLabel0": "#0F172A",
            "cScaleLabel1": "#0F172A",
            "cScaleLabel2": "#1F4D38",
            "cScaleLabel3": "#5C4A28",
            "cScaleLabel4": "#3F3A52",
            "cScaleLabel5": "#334155",
            "quadrant1Fill": "#E8EEF8",
            "quadrant2Fill": "#EEF2F7",
            "quadrant3Fill": "#FFFFFF",
            "quadrant4Fill": "#F8FAFC",
            "quadrant1TextFill": "#334155",
            "quadrant2TextFill": "#334155",
            "quadrant3TextFill": "#475569",
            "quadrant4TextFill": "#475569",
            "quadrantPointFill": "#3D6EB5",
            "quadrantPointTextFill": "#0F172A",
            "quadrantXAxisTextFill": "#334155",
            "quadrantYAxisTextFill": "#334155",
            "quadrantInternalBorderStrokeFill": "#CBD5E1",
            "quadrantExternalBorderStrokeFill": "#94A3B8",
            "quadrantTitleFill": "#0F172A",
            "xyChart": {
                "backgroundColor": "#F8FAFC",
                "titleColor": "#0F172A",
                "xAxisLabelColor": "#475569",
                "xAxisTitleColor": "#334155",
                "xAxisTickColor": "#CBD5E1",
                "xAxisLineColor": "#94A3B8",
                "yAxisLabelColor": "#475569",
                "yAxisTitleColor": "#334155",
                "yAxisTickColor": "#CBD5E1",
                "yAxisLineColor": "#94A3B8",
                "plotColorPalette": "#3D6EB5,#4A8B68,#B08D4F,#7A6F92",
            },
        },
    },
    "neutral": {
        "theme": "neutral",
        "htmlLabels": True,
    },
    "minimal": {
        "theme": "base",
        "htmlLabels": True,
        "themeVariables": {
            "darkMode": False,
            "background": "#FFFFFF",
            "fontFamily": (
                "Inter, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
            ),
            "fontSize": "15px",
            "primaryColor": "#FFFFFF",
            "primaryTextColor": "#0F172A",
            "primaryBorderColor": "#64748B",
            "secondaryColor": "#F8FAFC",
            "secondaryTextColor": "#0F172A",
            "secondaryBorderColor": "#94A3B8",
            "tertiaryColor": "#F8FAFC",
            "tertiaryTextColor": "#334155",
            "tertiaryBorderColor": "#E2E8F0",
            "lineColor": "#94A3B8",
            "nodeTextColor": "#0F172A",
            "stateLabelColor": "#0F172A",
            "clusterBkg": "#FCFCFD",
            "clusterBorder": "#E2E8F0",
            "edgeLabelBackground": "#FFFFFF",
        },
    },
}


# Aurora deliberately uses renderer-safe SVG fills and Neo depth instead of
# browser-only backdrop filters. The local output pass supplies the luminous
# gradient canvas consistently for PNG and SVG.
_aurora_theme = deepcopy(THEMES["docs"])
_aurora_theme["themeCSS"] = (
    ".edgeLabel { font-size: 12px; color: #566581; }"
    ".edgeLabel rect { fill: #F7F8FF !important; fill-opacity: .9; }"
    ".cluster rect { fill: #F7F9FF !important; fill-opacity: .72; "
    "stroke: #B8C8E8 !important; }"
    ".cluster-label .nodeLabel { font-weight: 700; letter-spacing: .025em; }"
    ".node rect,.node circle,.node ellipse,.node polygon,.node path { "
    "filter: drop-shadow(0 7px 10px rgba(67,83,142,.14)); }"
    ".actor { filter: drop-shadow(0 6px 9px rgba(67,83,142,.12)); }"
    ".messageLine0,.messageLine1 { stroke-width: 1.45px; }"
    ".task { filter: drop-shadow(0 4px 7px rgba(67,83,142,.1)); }"
)
_aurora_variables = _aurora_theme["themeVariables"]
_aurora_variables.update(
    {
        "background": "transparent",
        "primaryColor": "#F7F9FF",
        "primaryTextColor": "#17213D",
        "primaryBorderColor": "#A8BCE4",
        "secondaryColor": "#E9E4FF",
        "secondaryTextColor": "#443A83",
        "secondaryBorderColor": "#8B72E8",
        "tertiaryColor": "#E2F8F0",
        "tertiaryTextColor": "#155E50",
        "tertiaryBorderColor": "#55B99D",
        "lineColor": "#7D8EB2",
        "textColor": "#17213D",
        "mainBkg": "#F9FAFF",
        "nodeBorder": "#B6C6E6",
        "nodeTextColor": "#17213D",
        "clusterBkg": "#F7F9FF",
        "clusterBorder": "#B8C8E8",
        "titleColor": "#17213D",
        "edgeLabelBackground": "#F7F8FF",
        "actorBkg": "#F8FAFF",
        "actorBorder": "#8EA8D9",
        "actorTextColor": "#17213D",
        "actorLineColor": "#B7C6E2",
        "signalColor": "#6479A4",
        "signalTextColor": "#17213D",
        "labelBoxBkgColor": "#F5F7FF",
        "labelBoxBorderColor": "#C7D3EA",
        "labelTextColor": "#394867",
        "loopTextColor": "#52617E",
        "noteBkgColor": "#FFF0D8",
        "noteTextColor": "#74501E",
        "noteBorderColor": "#EAB464",
        "stateBkg": "#F8FAFF",
        "stateBorder": "#8EA8D9",
        "stateLabelColor": "#17213D",
        "classText": "#17213D",
        "relationColor": "#7083AB",
        "relationLabelColor": "#52617E",
        "attributeBackgroundColorOdd": "#F9FAFF",
        "attributeBackgroundColorEven": "#EEF2FF",
        "git0": "#3F72F2",
        "git1": "#19A987",
        "git2": "#F0A13B",
        "git3": "#7C5CE7",
        "pie1": "#3F72F2",
        "pie2": "#7C5CE7",
        "pie3": "#19A987",
        "pie4": "#F0A13B",
        "pie5": "#E45F7A",
        "pie6": "#46A7E8",
        "pie7": "#9A78EE",
        "pie8": "#55C7A8",
        "pieStrokeColor": "#F5F7FF",
        "pieOuterStrokeColor": "#A9BCE0",
        "sectionBkgColor": "#E7EEFF",
        "altSectionBkgColor": "#F8F9FF",
        "sectionBkgColor2": "#EEE8FF",
        "gridColor": "#C4D1E8",
        "taskBkgColor": "#DDE8FF",
        "taskBorderColor": "#4C78E8",
        "taskTextColor": "#17213D",
        "taskTextOutsideColor": "#394867",
        "activeTaskBkgColor": "#DDF7EE",
        "activeTaskBorderColor": "#2FA789",
        "doneTaskBkgColor": "#E8ECF6",
        "doneTaskBorderColor": "#9AAAC8",
        "critBkgColor": "#FFE9C8",
        "critBorderColor": "#E99A32",
        "todayLineColor": "#E45F7A",
        "cScale0": "#DDE8FF",
        "cScale1": "#EAE4FF",
        "cScale2": "#DDF7EE",
        "cScale3": "#FFE9C8",
        "cScale4": "#FFE2E8",
        "cScale5": "#DDF2FF",
        "quadrant1Fill": "#E4ECFF",
        "quadrant2Fill": "#EEE8FF",
        "quadrant3Fill": "#E3F8F1",
        "quadrant4Fill": "#FFF0D9",
        "quadrantPointFill": "#3F72F2",
        "quadrantPointTextFill": "#17213D",
        "quadrantInternalBorderStrokeFill": "#B9C8E4",
        "quadrantExternalBorderStrokeFill": "#879BC2",
    }
)
_aurora_variables["xyChart"] = {
    "backgroundColor": "transparent",
    "titleColor": "#17213D",
    "xAxisLabelColor": "#52617E",
    "xAxisTitleColor": "#394867",
    "xAxisTickColor": "#C4D1E8",
    "xAxisLineColor": "#8EA1C5",
    "yAxisLabelColor": "#52617E",
    "yAxisTitleColor": "#394867",
    "yAxisTickColor": "#C4D1E8",
    "yAxisLineColor": "#8EA1C5",
    "plotColorPalette": "#3F72F2,#7C5CE7,#19A987,#F0A13B,#E45F7A",
}
_cursor_theme = deepcopy(THEMES["docs"])
_cursor_theme["themeCSS"] = (
    ".edgeLabel { font-size: 13px; color: #52525B; }"
    ".edgeLabel rect { fill: #FFFFFF !important; fill-opacity: .96; }"
    ".cluster rect { fill: #F4F4F5 !important; fill-opacity: .92; "
    "stroke: #E4E4E7 !important; }"
    ".cluster-label .nodeLabel { font-weight: 600; letter-spacing: .01em; }"
    ".messageLine0,.messageLine1,.flowchart-link,.edge-pattern-solid { "
    "stroke-width: 1.8px; }"
)
_cursor_variables = _cursor_theme["themeVariables"]
_cursor_variables.update(
    {
        "background": "#FFFFFF",
        "fontSize": "16px",
        "primaryColor": "#FFFFFF",
        "primaryTextColor": "#18181B",
        "primaryBorderColor": "#A1A1AA",
        "secondaryColor": "#F4F4F5",
        "secondaryTextColor": "#3F3F46",
        "secondaryBorderColor": "#D4D4D8",
        "tertiaryColor": "#FAFAFA",
        "tertiaryTextColor": "#3F3F46",
        "tertiaryBorderColor": "#E4E4E7",
        "lineColor": "#71717A",
        "textColor": "#18181B",
        "mainBkg": "#FFFFFF",
        "nodeBorder": "#D4D4D8",
        "nodeTextColor": "#18181B",
        "clusterBkg": "#F4F4F5",
        "clusterBorder": "#E4E4E7",
        "titleColor": "#18181B",
        "edgeLabelBackground": "#FFFFFF",
        "actorBkg": "#FFFFFF",
        "actorBorder": "#A1A1AA",
        "actorTextColor": "#18181B",
        "actorLineColor": "#D4D4D8",
        "signalColor": "#52525B",
        "signalTextColor": "#18181B",
        "labelBoxBkgColor": "#FFFFFF",
        "labelBoxBorderColor": "#E4E4E7",
        "labelTextColor": "#3F3F46",
        "loopTextColor": "#52525B",
        "noteBkgColor": "#FFFBEB",
        "noteTextColor": "#78350F",
        "noteBorderColor": "#FBBF24",
        "stateBkg": "#FFFFFF",
        "stateBorder": "#A1A1AA",
        "stateLabelColor": "#18181B",
        "classText": "#18181B",
        "relationColor": "#71717A",
        "relationLabelColor": "#52525B",
        "attributeBackgroundColorOdd": "#FFFFFF",
        "attributeBackgroundColorEven": "#FAFAFA",
        "git0": "#2563EB",
        "git1": "#059669",
        "git2": "#D97706",
        "git3": "#7C3AED",
        "pie1": "#2563EB",
        "pie2": "#64748B",
        "pie3": "#059669",
        "pie4": "#D97706",
        "pie5": "#7C3AED",
        "pie6": "#0EA5E9",
        "pieStrokeColor": "#FFFFFF",
        "pieOuterStrokeColor": "#D4D4D8",
        "sectionBkgColor": "#F4F4F5",
        "altSectionBkgColor": "#FFFFFF",
        "sectionBkgColor2": "#FAFAFA",
        "gridColor": "#E4E4E7",
        "taskBkgColor": "#EFF6FF",
        "taskBorderColor": "#2563EB",
        "taskTextColor": "#18181B",
        "taskTextOutsideColor": "#3F3F46",
        "activeTaskBkgColor": "#ECFDF5",
        "activeTaskBorderColor": "#059669",
        "doneTaskBkgColor": "#E4E4E7",
        "doneTaskBorderColor": "#A1A1AA",
        "critBkgColor": "#FFFBEB",
        "critBorderColor": "#D97706",
        "todayLineColor": "#2563EB",
        "cScale0": "#EFF6FF",
        "cScale1": "#F4F4F5",
        "cScale2": "#ECFDF5",
        "cScale3": "#FFFBEB",
        "cScale4": "#F5F3FF",
        "cScale5": "#F0F9FF",
        "quadrant1Fill": "#EFF6FF",
        "quadrant2Fill": "#F4F4F5",
        "quadrant3Fill": "#FFFFFF",
        "quadrant4Fill": "#FAFAFA",
        "quadrantPointFill": "#2563EB",
        "quadrantPointTextFill": "#18181B",
        "quadrantInternalBorderStrokeFill": "#E4E4E7",
        "quadrantExternalBorderStrokeFill": "#A1A1AA",
    }
)
_cursor_variables["xyChart"] = {
    "backgroundColor": "#FFFFFF",
    "titleColor": "#18181B",
    "xAxisLabelColor": "#52525B",
    "xAxisTitleColor": "#3F3F46",
    "xAxisTickColor": "#E4E4E7",
    "xAxisLineColor": "#A1A1AA",
    "yAxisLabelColor": "#52525B",
    "yAxisTitleColor": "#3F3F46",
    "yAxisTickColor": "#E4E4E7",
    "yAxisLineColor": "#A1A1AA",
    "plotColorPalette": "#2563EB,#059669,#D97706,#7C3AED",
}
THEMES = {"cursor": _cursor_theme, "aurora": _aurora_theme, **THEMES}


def normalize_hex(color: str) -> str:
    text = color.strip()
    if not text.startswith("#"):
        text = f"#{text}"
    match = re.fullmatch(r"#([0-9A-Fa-f]{6})", text)
    if not match:
        raise SystemExit(f"color must be #RRGGBB: {color}")
    return f"#{match.group(1).upper()}"


def mix_hex(color: str, other: str, amount: float) -> str:
    amount = max(0.0, min(1.0, amount))
    first = tuple(int(normalize_hex(color)[index : index + 2], 16) for index in (1, 3, 5))
    second = tuple(int(normalize_hex(other)[index : index + 2], 16) for index in (1, 3, 5))
    mixed = tuple(
        round(first[index] * (1.0 - amount) + second[index] * amount)
        for index in range(3)
    )
    return f"#{mixed[0]:02X}{mixed[1]:02X}{mixed[2]:02X}"


def _cursor_variant(
    *,
    accent: str,
    canvas: str,
    cluster: str,
    ink: str,
    muted: str,
    line: str,
) -> dict[str, Any]:
    theme = deepcopy(_cursor_theme)
    fill = mix_hex(accent, canvas, 0.88)
    variables = theme["themeVariables"]
    variables.update(
        {
            "background": canvas,
            "primaryTextColor": ink,
            "textColor": ink,
            "nodeTextColor": ink,
            "titleColor": ink,
            "clusterBkg": cluster,
            "clusterBorder": mix_hex(cluster, line, 0.35),
            "lineColor": line,
            "git0": accent,
            "pie1": accent,
            "taskBkgColor": fill,
            "taskBorderColor": accent,
            "todayLineColor": accent,
            "quadrant1Fill": fill,
            "quadrantPointFill": accent,
        }
    )
    chart = dict(variables["xyChart"])
    chart["backgroundColor"] = canvas
    chart["titleColor"] = ink
    chart["plotColorPalette"] = f"{accent},{variables['git1']},{variables['git2']},{variables['git3']}"
    variables["xyChart"] = chart
    theme["themeCSS"] = theme["themeCSS"].replace("#FFFFFF", canvas).replace("#52525B", muted)
    return theme


_ocean_theme = _cursor_variant(
    accent="#0E7490",
    canvas="#F4FBFC",
    cluster="#E7F4F6",
    ink="#134E4A",
    muted="#3F6F73",
    line="#5B8A8F",
)
_forest_theme = _cursor_variant(
    accent="#15803D",
    canvas="#F5FBF6",
    cluster="#E7F4EA",
    ink="#14532D",
    muted="#3F6B4C",
    line="#5B8064",
)
_dark_theme = deepcopy(_cursor_theme)
_dark_theme["themeCSS"] = (
    ".edgeLabel { font-size: 13px; color: #A1A1AA; }"
    ".edgeLabel rect { fill: #18181B !important; fill-opacity: .96; }"
    ".cluster rect { fill: #27272A !important; fill-opacity: .92; "
    "stroke: #3F3F46 !important; }"
    ".cluster-label .nodeLabel { font-weight: 600; color: #FAFAFA; }"
    ".messageLine0,.messageLine1,.flowchart-link { stroke-width: 1.8px; }"
)
_dark_variables = _dark_theme["themeVariables"]
_dark_variables.update(
    {
        "darkMode": True,
        "background": "#18181B",
        "primaryColor": "#27272A",
        "primaryTextColor": "#FAFAFA",
        "primaryBorderColor": "#52525B",
        "secondaryColor": "#27272A",
        "secondaryTextColor": "#E4E4E7",
        "secondaryBorderColor": "#3F3F46",
        "tertiaryColor": "#1F1F23",
        "tertiaryTextColor": "#D4D4D8",
        "tertiaryBorderColor": "#3F3F46",
        "lineColor": "#A1A1AA",
        "textColor": "#FAFAFA",
        "mainBkg": "#27272A",
        "nodeBorder": "#3F3F46",
        "nodeTextColor": "#FAFAFA",
        "clusterBkg": "#27272A",
        "clusterBorder": "#3F3F46",
        "titleColor": "#FAFAFA",
        "edgeLabelBackground": "#18181B",
        "actorBkg": "#27272A",
        "actorBorder": "#52525B",
        "actorTextColor": "#FAFAFA",
        "actorLineColor": "#3F3F46",
        "signalColor": "#A1A1AA",
        "signalTextColor": "#FAFAFA",
        "stateBkg": "#27272A",
        "stateBorder": "#52525B",
        "stateLabelColor": "#FAFAFA",
        "classText": "#FAFAFA",
        "noteBkgColor": "#422006",
        "noteTextColor": "#FDE68A",
        "pieStrokeColor": "#18181B",
        "pieOuterStrokeColor": "#3F3F46",
        "sectionBkgColor": "#27272A",
        "altSectionBkgColor": "#18181B",
        "attributeBackgroundColorOdd": "#27272A",
        "attributeBackgroundColorEven": "#18181B",
        "quadrant1Fill": "#1E3A5F",
        "quadrant2Fill": "#27272A",
        "quadrant3Fill": "#18181B",
        "quadrant4Fill": "#1F1F23",
        "quadrantPointFill": "#60A5FA",
        "quadrantPointTextFill": "#FAFAFA",
        "taskBkgColor": "#1E3A8A",
        "taskTextColor": "#FAFAFA",
    }
)
_dark_variables["xyChart"] = {
    "backgroundColor": "#18181B",
    "titleColor": "#FAFAFA",
    "xAxisLabelColor": "#A1A1AA",
    "xAxisTitleColor": "#D4D4D8",
    "xAxisTickColor": "#3F3F46",
    "xAxisLineColor": "#52525B",
    "yAxisLabelColor": "#A1A1AA",
    "yAxisTitleColor": "#D4D4D8",
    "yAxisTickColor": "#3F3F46",
    "yAxisLineColor": "#52525B",
    "plotColorPalette": "#60A5FA,#34D399,#FBBF24,#C084FC",
}
THEMES = {
    "cursor": THEMES["cursor"],
    "aurora": THEMES["aurora"],
    "dark": _dark_theme,
    "ocean": _ocean_theme,
    "forest": _forest_theme,
    **{key: value for key, value in THEMES.items() if key not in {"cursor", "aurora"}},
}


PRESETS: dict[str, dict[str, Any]] = {
    "process": {
        "flowchart": {
            "curve": "basis",
            "padding": 28,
            "nodeSpacing": 64,
            "rankSpacing": 80,
            "useMaxWidth": True,
        }
    },
    "architecture": {
        "flowchart": {
            "curve": "linear",
            "padding": 30,
            "nodeSpacing": 72,
            "rankSpacing": 96,
            "useMaxWidth": True,
        }
    },
    "sequence": {
        "sequence": {
            "actorMargin": 60,
            "boxMargin": 14,
            "boxTextMargin": 10,
            "diagramMarginX": 28,
            "diagramMarginY": 24,
            "messageMargin": 42,
            "mirrorActors": False,
            "noteMargin": 14,
            "useMaxWidth": True,
        }
    },
    "state": {},
    "class": {
        "class": {
            "useMaxWidth": True,
        }
    },
    "er": {
        "er": {
            "diagramPadding": 24,
            "entityPadding": 18,
            "layoutDirection": "LR",
            "minEntityHeight": 90,
            "minEntityWidth": 120,
            "useMaxWidth": True,
        }
    },
    "mindmap": {
        "mindmap": {
            "maxNodeWidth": 220,
            "padding": 24,
            "useMaxWidth": True,
        }
    },
    "timeline": {
        "timeline": {
            "diagramMarginX": 28,
            "diagramMarginY": 24,
            "useMaxWidth": True,
        }
    },
    "gantt": {
        "gantt": {
            "barGap": 6,
            "barHeight": 24,
            "fontSize": 14,
            "gridLineStartPadding": 30,
            "leftPadding": 96,
            "sectionFontSize": 14,
            "topPadding": 48,
            "useMaxWidth": True,
        }
    },
    "gitgraph": {
        "gitGraph": {
            "mainBranchName": "main",
            "parallelCommits": True,
            "showBranches": True,
            "showCommitLabel": True,
        }
    },
    "journey": {
        "journey": {
            "boxMargin": 12,
            "boxTextMargin": 8,
            "diagramMarginX": 28,
            "diagramMarginY": 24,
            "leftMargin": 120,
            "useMaxWidth": True,
        }
    },
    "pie": {
        "pie": {
            "textPosition": 0.72,
            "useMaxWidth": True,
        }
    },
    "quadrant": {
        "quadrantChart": {
            "chartHeight": 500,
            "chartWidth": 500,
            "pointLabelFontSize": 13,
            "pointRadius": 6,
            "quadrantPadding": 14,
            "titleFontSize": 18,
            "titlePadding": 14,
        }
    },
    "architecture-native": {},
    "block": {},
    "kanban": {},
    "sankey": {
        "sankey": {
            "height": 480,
            "linkColor": "gradient",
            "nodeAlignment": "left",
            "showValues": True,
            "width": 900,
        }
    },
    "xychart": {
        "xyChart": {
            "chartHeight": 450,
            "chartWidth": 720,
        }
    },
    "generic": {},
}


CLASSDEF_BLOCK = """
classDef startEnd fill:#E8EEF8,stroke:#3D6EB5,stroke-width:1.6px,color:#0F172A
classDef process fill:#FFFFFF,stroke:#CBD5E1,stroke-width:1.2px,color:#0F172A
classDef accent fill:#DCE7F7,stroke:#3B6FB0,stroke-width:1.7px,color:#0F172A
classDef decision fill:#F5F0E6,stroke:#B08D4F,stroke-width:1.5px,color:#5C4A28
classDef store fill:#E6F2EB,stroke:#4A8B68,stroke-width:1.4px,color:#1F4D38
classDef external fill:#EEEAF3,stroke:#7A6F92,stroke-width:1.3px,color:#3F3A52
""".strip()

LINKSTYLE_BLOCK = "linkStyle default stroke:#94A3B8,stroke-width:1.35px"

AURORA_CLASSDEF_BLOCK = """
classDef startEnd fill:#E6ECFF,stroke:#567EE7,stroke-width:1.7px,color:#17213D
classDef process fill:#F9FAFF,stroke:#B6C6E6,stroke-width:1.25px,color:#17213D
classDef accent fill:#526FE6,stroke:#795DE0,stroke-width:1.9px,color:#FFFFFF
classDef decision fill:#FFE9C8,stroke:#E99A32,stroke-width:1.6px,color:#704817
classDef store fill:#DDF7EE,stroke:#2FA789,stroke-width:1.5px,color:#155E50
classDef external fill:#EAE4FF,stroke:#8B72E8,stroke-width:1.45px,color:#443A83
""".strip()

AURORA_LINKSTYLE_BLOCK = (
    "linkStyle default stroke:#7184AE,stroke-width:1.5px"
)

CURSOR_CLASSDEF_BLOCK = """
classDef startEnd fill:#F4F4F5,stroke:#71717A,stroke-width:1.6px,color:#18181B
classDef process fill:#FFFFFF,stroke:#D4D4D8,stroke-width:1.4px,color:#18181B
classDef accent fill:#EFF6FF,stroke:#2563EB,stroke-width:1.8px,color:#1E3A8A
classDef decision fill:#FFFBEB,stroke:#D97706,stroke-width:1.5px,color:#78350F
classDef store fill:#ECFDF5,stroke:#059669,stroke-width:1.5px,color:#064E3B
classDef external fill:#FAFAFA,stroke:#A1A1AA,stroke-width:1.4px,color:#3F3F46
""".strip()

CURSOR_LINKSTYLE_BLOCK = (
    "linkStyle default stroke:#52525B,stroke-width:1.85px"
)

CURSOR_SANKEY_PALETTE = (
    "#2563EB",
    "#64748B",
    "#059669",
    "#D97706",
    "#7C3AED",
    "#0EA5E9",
)

OCEAN_CLASSDEF_BLOCK = """
classDef startEnd fill:#E7F4F6,stroke:#5B8A8F,stroke-width:1.6px,color:#134E4A
classDef process fill:#FFFFFF,stroke:#B7D4D8,stroke-width:1.4px,color:#134E4A
classDef accent fill:#E0F2FE,stroke:#0E7490,stroke-width:1.8px,color:#155E75
classDef decision fill:#FFFBEB,stroke:#D97706,stroke-width:1.5px,color:#78350F
classDef store fill:#ECFDF5,stroke:#0F766E,stroke-width:1.5px,color:#134E4A
classDef external fill:#F8FAFC,stroke:#94A3B8,stroke-width:1.4px,color:#334155
""".strip()

FOREST_CLASSDEF_BLOCK = """
classDef startEnd fill:#E7F4EA,stroke:#5B8064,stroke-width:1.6px,color:#14532D
classDef process fill:#FFFFFF,stroke:#C5D9C9,stroke-width:1.4px,color:#14532D
classDef accent fill:#DCFCE7,stroke:#15803D,stroke-width:1.8px,color:#166534
classDef decision fill:#FFFBEB,stroke:#D97706,stroke-width:1.5px,color:#78350F
classDef store fill:#ECFDF5,stroke:#047857,stroke-width:1.5px,color:#14532D
classDef external fill:#F8FAFC,stroke:#A3A3A3,stroke-width:1.4px,color:#3F3F46
""".strip()

DARK_CLASSDEF_BLOCK = """
classDef startEnd fill:#27272A,stroke:#71717A,stroke-width:1.6px,color:#FAFAFA
classDef process fill:#18181B,stroke:#3F3F46,stroke-width:1.4px,color:#FAFAFA
classDef accent fill:#1E3A8A,stroke:#60A5FA,stroke-width:1.8px,color:#DBEAFE
classDef decision fill:#422006,stroke:#F59E0B,stroke-width:1.5px,color:#FDE68A
classDef store fill:#064E3B,stroke:#34D399,stroke-width:1.5px,color:#D1FAE5
classDef external fill:#27272A,stroke:#52525B,stroke-width:1.4px,color:#E4E4E7
""".strip()

DARK_LINKSTYLE_BLOCK = "linkStyle default stroke:#A1A1AA,stroke-width:1.85px"
OCEAN_LINKSTYLE_BLOCK = "linkStyle default stroke:#3F6F73,stroke-width:1.85px"
FOREST_LINKSTYLE_BLOCK = "linkStyle default stroke:#3F6B4C,stroke-width:1.85px"

OCEAN_SANKEY_PALETTE = (
    "#0E7490",
    "#64748B",
    "#0F766E",
    "#D97706",
    "#7C3AED",
    "#0284C7",
)
FOREST_SANKEY_PALETTE = (
    "#15803D",
    "#4D7C0F",
    "#0F766E",
    "#CA8A04",
    "#57534E",
    "#2563EB",
)
DARK_SANKEY_PALETTE = (
    "#60A5FA",
    "#A1A1AA",
    "#34D399",
    "#FBBF24",
    "#C084FC",
    "#38BDF8",
)


def classdef_block(theme_name: str, accent: str | None = None) -> str:
    blocks = {
        "aurora": AURORA_CLASSDEF_BLOCK,
        "cursor": CURSOR_CLASSDEF_BLOCK,
        "dark": DARK_CLASSDEF_BLOCK,
        "ocean": OCEAN_CLASSDEF_BLOCK,
        "forest": FOREST_CLASSDEF_BLOCK,
    }
    block = blocks.get(theme_name, CLASSDEF_BLOCK)
    if not accent:
        return block
    paper = "#18181B" if theme_name == "dark" else "#FFFFFF"
    fill = mix_hex(accent, paper, 0.86)
    text = "#DBEAFE" if theme_name == "dark" else mix_hex(accent, "#000000", 0.35)
    return re.sub(
        r"classDef accent fill:#[0-9A-Fa-f]{6},stroke:#[0-9A-Fa-f]{6},"
        r"stroke-width:[0-9.]+px,color:#[0-9A-Fa-f]{6}",
        f"classDef accent fill:{fill},stroke:{accent},stroke-width:1.8px,color:{text}",
        block,
        count=1,
    )


def linkstyle_block(theme_name: str) -> str:
    return {
        "aurora": AURORA_LINKSTYLE_BLOCK,
        "cursor": CURSOR_LINKSTYLE_BLOCK,
        "dark": DARK_LINKSTYLE_BLOCK,
        "ocean": OCEAN_LINKSTYLE_BLOCK,
        "forest": FOREST_LINKSTYLE_BLOCK,
    }.get(theme_name, LINKSTYLE_BLOCK)


def read_mermaid(path: Path) -> str:
    """Read UTF-8 Mermaid source and remove an optional Markdown fence."""
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise SystemExit(f"empty mermaid file: {path}")
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if not text:
        raise SystemExit(f"empty mermaid file: {path}")
    return text


def _source_without_frontmatter(source: str) -> str:
    stripped = source.lstrip()
    if not stripped.startswith("---"):
        return stripped
    lines = stripped.splitlines()
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1 :]).lstrip()
    return stripped


def detect_diagram_type(source: str) -> str:
    """Return the Mermaid grammar family without changing source semantics."""
    body = _source_without_frontmatter(source)
    for line in body.splitlines():
        statement = line.strip()
        if not statement or statement.startswith("%%"):
            continue
        keyword = statement.split(maxsplit=1)[0].lower()
        return DIAGRAM_KEYWORDS.get(keyword, "generic")
    return "generic"


def detect_flowchart_direction(source: str) -> str | None:
    body = _source_without_frontmatter(source)
    match = re.search(
        r"(?im)^\s*(?:flowchart|graph)\s+(TB|TD|BT|RL|LR)\b", body
    )
    return match.group(1).upper() if match else None


def _diagram_content_lines(source: str) -> list[tuple[int, str]]:
    """Return numbered lines after the first effective diagram declaration."""
    body = _source_without_frontmatter(source)
    found_declaration = False
    content: list[tuple[int, str]] = []
    for line_number, line in enumerate(body.splitlines(), 1):
        statement = line.strip()
        if not found_declaration:
            if not statement or statement.startswith("%%"):
                continue
            found_declaration = True
            continue
        content.append((line_number, line))
    return content


def validate_sankey_source(source: str) -> None:
    """Validate the stable three-column Sankey subset before network rendering."""
    rows = 0
    for line_number, line in _diagram_content_lines(source):
        statement = line.strip()
        if not statement or statement.startswith("%%"):
            continue
        try:
            parsed = next(csv.reader([line], skipinitialspace=True, strict=True))
        except csv.Error as error:
            raise ValueError(f"Sankey line {line_number}: invalid CSV: {error}") from error
        if len(parsed) != 3:
            raise ValueError(
                f"Sankey line {line_number}: expected source,target,value"
            )
        source_name, target_name, raw_value = (value.strip() for value in parsed)
        if not source_name or not target_name:
            raise ValueError(
                f"Sankey line {line_number}: source and target must not be empty"
            )
        if not source_name.isascii() or not target_name.isascii():
            raise ValueError(
                f"Sankey line {line_number}: labels must use ASCII for stable "
                "remote rendering"
            )
        try:
            value = float(raw_value)
        except ValueError as error:
            raise ValueError(
                f"Sankey line {line_number}: value must be numeric"
            ) from error
        if not math.isfinite(value) or value <= 0:
            raise ValueError(
                f"Sankey line {line_number}: value must be a finite positive number"
            )
        rows += 1
    if rows == 0:
        raise ValueError("Sankey diagram requires at least one data row")


def _parse_csv_items(text: str, line_number: int, context: str) -> list[str]:
    try:
        items = next(
            csv.reader(io.StringIO(text), skipinitialspace=True, strict=True)
        )
    except csv.Error as error:
        raise ValueError(f"XY line {line_number}: invalid {context}: {error}") from error
    values = [item.strip() for item in items]
    if not values or any(not item for item in values):
        raise ValueError(f"XY line {line_number}: {context} contains an empty value")
    return values


def _parse_finite_numbers(
    text: str,
    line_number: int,
    context: str,
) -> list[float]:
    items = _parse_csv_items(text, line_number, context)
    values: list[float] = []
    for item in items:
        try:
            value = float(item)
        except ValueError as error:
            raise ValueError(
                f"XY line {line_number}: {context} values must be plain numbers"
            ) from error
        if not math.isfinite(value):
            raise ValueError(
                f"XY line {line_number}: {context} values must be finite"
            )
        values.append(value)
    return values


def validate_xychart_source(source: str) -> None:
    """Validate stable categorical/numeric XY bar and line data."""
    category_count: int | None = None
    series: list[tuple[int, str, int]] = []
    number = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
    range_pattern = re.compile(rf"({number})\s*-->\s*({number})\s*$")

    for line_number, line in _diagram_content_lines(source):
        statement = line.strip()
        if not statement or statement.startswith("%%"):
            continue
        lowered = statement.lower()
        if lowered.startswith("x-axis"):
            categories = re.search(r"\[(.*)\]\s*$", statement)
            if categories:
                category_count = len(
                    _parse_csv_items(categories.group(1), line_number, "x-axis categories")
                )
            elif "-->" in statement:
                axis_range = range_pattern.search(statement)
                if not axis_range:
                    raise ValueError(f"XY line {line_number}: invalid x-axis range")
                minimum, maximum = (float(value) for value in axis_range.groups())
                if not all(math.isfinite(value) for value in (minimum, maximum)):
                    raise ValueError(f"XY line {line_number}: x-axis range must be finite")
                if minimum >= maximum:
                    raise ValueError(
                        f"XY line {line_number}: x-axis minimum must be below maximum"
                    )
            continue
        if lowered.startswith("y-axis") and "-->" in statement:
            axis_range = range_pattern.search(statement)
            if not axis_range:
                raise ValueError(f"XY line {line_number}: invalid y-axis range")
            minimum, maximum = (float(value) for value in axis_range.groups())
            if not all(math.isfinite(value) for value in (minimum, maximum)):
                raise ValueError(f"XY line {line_number}: y-axis range must be finite")
            if minimum >= maximum:
                raise ValueError(
                    f"XY line {line_number}: y-axis minimum must be below maximum"
                )
            continue

        series_match = re.fullmatch(r"(?i)(bar|line)\s*\[(.*)\]", statement)
        if series_match:
            kind = series_match.group(1).lower()
            values = _parse_finite_numbers(
                series_match.group(2), line_number, f"{kind} series"
            )
            series.append((line_number, kind, len(values)))
        elif lowered.startswith(("bar", "line")):
            raise ValueError(
                f"XY line {line_number}: bar and line series must use [number,...]"
            )

    if not series:
        raise ValueError("XY chart requires at least one bar or line series")
    if category_count is not None:
        for line_number, kind, value_count in series:
            if value_count != category_count:
                raise ValueError(
                    f"XY line {line_number}: {kind} series has {value_count} values "
                    f"but x-axis has {category_count} categories"
                )


def validate_diagram_source(source: str, diagram_type: str) -> None:
    if diagram_type == "sankey":
        validate_sankey_source(source)
    elif diagram_type == "xychart":
        validate_xychart_source(source)


def resolve_preset(source: str, requested: str = "auto") -> str:
    """Select a layout preset, respecting an explicit CLI override."""
    if requested != "auto":
        return requested
    diagram_type = detect_diagram_type(source)
    if diagram_type == "flowchart":
        direction = detect_flowchart_direction(source)
        has_layers = bool(re.search(r"(?im)^\s*subgraph\b", source))
        if direction in {"LR", "RL"} and has_layers:
            return "architecture"
        return "process"
    if diagram_type in PRESETS:
        return diagram_type
    return "generic"


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def resolve_look(theme_name: str, requested: str = "auto") -> str:
    if requested != "auto":
        return requested
    return THEME_DEFAULT_LOOK.get(theme_name, "classic")


def apply_accent_variables(config: dict[str, Any], accent: str | None) -> dict[str, Any]:
    if not accent:
        return config
    result = deepcopy(config)
    variables = result.setdefault("themeVariables", {})
    fill = mix_hex(accent, str(variables.get("background", "#FFFFFF")), 0.88)
    variables["git0"] = accent
    variables["pie1"] = accent
    variables["taskBorderColor"] = accent
    variables["taskBkgColor"] = fill
    variables["todayLineColor"] = accent
    variables["quadrantPointFill"] = accent
    chart = variables.get("xyChart")
    if isinstance(chart, dict):
        rest = str(chart.get("plotColorPalette", "")).split(",")[1:]
        chart["plotColorPalette"] = ",".join([accent, *rest]) if rest else accent
    return result


def build_config(
    theme_name: str,
    preset: str,
    look: str,
    accent: str | None = None,
) -> dict[str, Any]:
    theme = THEMES.get(theme_name, THEMES["docs"])
    preset_config = PRESETS.get(preset, PRESETS["generic"])
    merged = deep_merge(deep_merge(theme, preset_config), {"look": look})
    return apply_accent_variables(merged, accent)


def source_config_overlay(
    source: str,
    preset: str,
    theme_name: str = "docs",
) -> dict[str, Any]:
    if preset != "sankey":
        return {}
    nodes: list[str] = []
    for _, line in _diagram_content_lines(source):
        statement = line.strip()
        if not statement or statement.startswith("%%"):
            continue
        try:
            row = next(csv.reader([line], skipinitialspace=True, strict=True))
        except csv.Error:
            continue
        if len(row) != 3:
            continue
        for label in (row[0].strip(), row[1].strip()):
            if label and label not in nodes:
                nodes.append(label)
    if theme_name == "aurora":
        palette = AURORA_SANKEY_PALETTE
    elif theme_name == "cursor":
        palette = CURSOR_SANKEY_PALETTE
    elif theme_name == "ocean":
        palette = OCEAN_SANKEY_PALETTE
    elif theme_name == "forest":
        palette = FOREST_SANKEY_PALETTE
    elif theme_name == "dark":
        palette = DARK_SANKEY_PALETTE
    else:
        palette = SANKEY_PALETTE
    node_colors = {
        label: palette[index % len(palette)]
        for index, label in enumerate(nodes)
    }
    return {"sankey": {"nodeColors": node_colors}} if node_colors else {}


def has_theme_config(source: str) -> bool:
    """Detect author-supplied frontmatter or an init directive."""
    stripped = source.lstrip()
    if stripped.startswith("---"):
        return True
    return bool(re.search(r"(?is)^\s*(?:%%[^\n]*\n\s*)*%%\{\s*init\s*:", source))


def build_init_directive(
    theme_name: str,
    preset: str,
    look: str,
    source: str = "",
    accent: str | None = None,
) -> str:
    config = build_config(theme_name, preset, look, accent)
    if source:
        config = deep_merge(
            config,
            source_config_overlay(source, preset, theme_name),
        )
    payload = json.dumps(
        config,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"%%{{init: {payload}}}%%"


def apply_theme(
    source: str,
    theme_name: str,
    preset: str,
    look: str,
    inject_classdef: bool,
    accent: str | None = None,
) -> str:
    """Apply config and flowchart-only semantic class definitions."""
    parts: list[str] = []
    if not has_theme_config(source):
        parts.append(
            build_init_directive(theme_name, preset, look, source, accent)
        )
    parts.append(source.rstrip())

    is_flowchart = detect_diagram_type(source) == "flowchart"
    has_classdef = bool(re.search(r"(?im)^\s*classDef\s+", source))
    if inject_classdef and is_flowchart and not has_classdef:
        parts.extend(("", classdef_block(theme_name, accent)))
    has_linkstyle = bool(re.search(r"(?im)^\s*linkStyle\s+", source))
    if is_flowchart and not has_linkstyle:
        parts.extend(("", linkstyle_block(theme_name)))
    return "\n".join(parts) + "\n"


def fetch(url: str, data: bytes | None = None, timeout: int = 90) -> bytes:
    headers = {"User-Agent": UA, "Accept": "image/png,image/svg+xml,*/*"}
    if data is not None:
        headers["Content-Type"] = "text/plain; charset=utf-8"
    request = urllib.request.Request(
        url,
        data=data,
        method="POST" if data is not None else "GET",
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        content_type = (response.headers.get("Content-Type") or "").lower()
        if not body:
            raise RuntimeError("renderer returned an empty response")
        if "text/html" in content_type:
            raise RuntimeError("renderer returned HTML instead of an image")
        return body


def validate_payload(payload: bytes, fmt: str) -> None:
    """Reject error pages or truncated responses before writing output files."""
    if fmt == "png":
        if (
            len(payload) < 24
            or not payload.startswith(PNG_SIGNATURE)
            or payload[12:16] != b"IHDR"
            or int.from_bytes(payload[16:20], "big") <= 0
            or int.from_bytes(payload[20:24], "big") <= 0
        ):
            raise RuntimeError("renderer response is not a valid PNG")
        return
    if fmt == "svg":
        sample = payload.lstrip(b"\xef\xbb\xbf\x00\t\r\n ")[:2048].lower()
        if b"<svg" not in sample or b"</svg>" not in payload[-4096:].lower():
            raise RuntimeError("renderer response is not a valid SVG")
        return
    raise ValueError(f"unsupported format: {fmt}")


def png_dimensions(payload: bytes) -> tuple[int, int]:
    validate_payload(payload, "png")
    return (
        int.from_bytes(payload[16:20], "big"),
        int.from_bytes(payload[20:24], "big"),
    )


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind)
    checksum = zlib.crc32(data, checksum) & 0xFFFFFFFF
    return (
        len(data).to_bytes(4, "big")
        + kind
        + data
        + checksum.to_bytes(4, "big")
    )


def _paeth_predictor(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left


def _blend_rgb(
    base: tuple[int, int, int],
    overlay: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, amount))
    return tuple(
        round(base[index] * (1.0 - amount) + overlay[index] * amount)
        for index in range(3)
    )


def aurora_background_pixel(
    x: int,
    y: int,
    width: int,
    height: int,
) -> tuple[int, int, int]:
    """Return a light blue-violet-mint Aurora canvas pixel."""
    x_ratio = x / max(1, width - 1)
    y_ratio = y / max(1, height - 1)
    position = 0.62 * x_ratio + 0.38 * y_ratio
    first, middle, last = AURORA_BACKGROUND_STOPS
    if position <= 0.5:
        base = _blend_rgb(first, middle, position * 2.0)
    else:
        base = _blend_rgb(middle, last, (position - 0.5) * 2.0)

    def radial_amount(cx: float, cy: float, radius: float, strength: float) -> float:
        distance = math.hypot(x_ratio - cx, y_ratio - cy)
        return max(0.0, 1.0 - distance / radius) ** 2 * strength

    base = _blend_rgb(
        base,
        (116, 157, 255),
        radial_amount(0.03, 0.04, 0.58, 0.18),
    )
    base = _blend_rgb(
        base,
        (168, 116, 244),
        radial_amount(0.88, 0.12, 0.46, 0.12),
    )
    return _blend_rgb(
        base,
        (92, 221, 177),
        radial_amount(0.98, 0.94, 0.60, 0.15),
    )


def png_has_alpha(payload: bytes) -> bool:
    validate_payload(payload, "png")
    return payload[24] == 8 and payload[25] in {4, 6} and payload[28] == 0


def flatten_png_background(
    payload: bytes,
    background: tuple[int, int, int],
    *,
    aurora: bool = False,
) -> bytes:
    """Composite 8-bit alpha PNGs onto a solid or Aurora background."""
    validate_payload(payload, "png")
    width, height = png_dimensions(payload)
    bit_depth = payload[24]
    color_type = payload[25]
    interlace = payload[28]
    if bit_depth != 8 or color_type not in {4, 6} or interlace != 0:
        return payload

    idat_parts: list[bytes] = []
    offset = len(PNG_SIGNATURE)
    while offset + 12 <= len(payload):
        length = int.from_bytes(payload[offset : offset + 4], "big")
        kind = payload[offset + 4 : offset + 8]
        data_start = offset + 8
        data_end = data_start + length
        if data_end + 4 > len(payload):
            raise RuntimeError("PNG contains a truncated chunk")
        if kind == b"IDAT":
            idat_parts.append(payload[data_start:data_end])
        offset = data_end + 4
        if kind == b"IEND":
            break
    if not idat_parts:
        raise RuntimeError("PNG contains no image data")

    channels = 4 if color_type == 6 else 2
    row_length = width * channels
    decoded = zlib.decompress(b"".join(idat_parts))
    expected = height * (row_length + 1)
    if len(decoded) != expected:
        raise RuntimeError("PNG image data has an unexpected size")

    previous = bytearray(row_length)
    output_rows: list[bytes] = []
    cursor = 0
    for row_index in range(height):
        filter_type = decoded[cursor]
        cursor += 1
        filtered = decoded[cursor : cursor + row_length]
        cursor += row_length
        row = bytearray(row_length)
        for index, value in enumerate(filtered):
            left = row[index - channels] if index >= channels else 0
            up = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                predictor = _paeth_predictor(left, up, upper_left)
            else:
                raise RuntimeError(f"PNG uses unsupported filter {filter_type}")
            row[index] = (value + predictor) & 0xFF

        rgb = bytearray(width * 3)
        for pixel in range(width):
            source = pixel * channels
            target = pixel * 3
            if color_type == 6:
                red, green, blue, alpha = row[source : source + 4]
            else:
                gray, alpha = row[source : source + 2]
                red = green = blue = gray
            backdrop = (
                aurora_background_pixel(pixel, row_index, width, height)
                if aurora
                else background
            )
            for channel, foreground in enumerate((red, green, blue)):
                rgb[target + channel] = (
                    foreground * alpha
                    + backdrop[channel] * (255 - alpha)
                    + 127
                ) // 255
        output_rows.append(b"\x00" + bytes(rgb))
        previous = row

    ihdr = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + bytes((8, 2, 0, 0, 0))
    )
    image_data = zlib.compress(b"".join(output_rows), 9)
    return (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", image_data)
        + _png_chunk(b"IEND", b"")
    )


def add_svg_background(payload: bytes, color: str) -> bytes:
    """Insert a solid background as the first SVG child."""
    validate_payload(payload, "svg")
    start = payload.find(b"<svg")
    opening_end = payload.find(b">", start)
    if start < 0 or opening_end < 0:
        raise RuntimeError("SVG root element is malformed")
    rectangle = (
        f'<rect width="100%" height="100%" fill="{color}"/>'.encode("ascii")
    )
    return payload[: opening_end + 1] + rectangle + payload[opening_end + 1 :]


def add_svg_aurora_background(payload: bytes) -> bytes:
    """Insert a deterministic Aurora gradient behind the SVG content."""
    validate_payload(payload, "svg")
    marker = b'id="flowchart-aurora-background"'
    if marker in payload:
        return payload
    start = payload.find(b"<svg")
    opening_end = payload.find(b">", start)
    if start < 0 or opening_end < 0:
        raise RuntimeError("SVG root element is malformed")
    background = (
        '<defs id="flowchart-aurora-background">'
        '<linearGradient id="flowchart-aurora-linear" x1="0%" y1="0%" '
        'x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#E2EEFF"/>'
        '<stop offset="52%" stop-color="#EFE4FF"/>'
        '<stop offset="100%" stop-color="#DCF9EF"/>'
        '</linearGradient>'
        '<radialGradient id="flowchart-aurora-blue" cx="0%" cy="0%" r="62%">'
        '<stop offset="0%" stop-color="#74A0FF" stop-opacity=".22"/>'
        '<stop offset="100%" stop-color="#74A0FF" stop-opacity="0"/>'
        '</radialGradient>'
        '<radialGradient id="flowchart-aurora-mint" cx="100%" cy="100%" r="64%">'
        '<stop offset="0%" stop-color="#5CDDB1" stop-opacity=".18"/>'
        '<stop offset="100%" stop-color="#5CDDB1" stop-opacity="0"/>'
        '</radialGradient>'
        '<radialGradient id="flowchart-aurora-violet" cx="88%" cy="12%" r="48%">'
        '<stop offset="0%" stop-color="#A874F4" stop-opacity=".14"/>'
        '<stop offset="100%" stop-color="#A874F4" stop-opacity="0"/>'
        '</radialGradient>'
        '</defs>'
        '<rect width="100%" height="100%" fill="url(#flowchart-aurora-linear)"/>'
        '<rect width="100%" height="100%" fill="url(#flowchart-aurora-blue)"/>'
        '<rect width="100%" height="100%" fill="url(#flowchart-aurora-violet)"/>'
        '<rect width="100%" height="100%" fill="url(#flowchart-aurora-mint)"/>'
    ).encode("ascii")
    return payload[: opening_end + 1] + background + payload[opening_end + 1 :]


def theme_background(theme_name: str) -> str:
    if theme_name == "cursor":
        return "#FFFFFF"
    if theme_name == "aurora":
        return "#E8EEFF"
    if theme_name == "dark":
        return "#18181B"
    if theme_name == "ocean":
        return "#F4FBFC"
    if theme_name == "forest":
        return "#F5FBF6"
    theme = THEMES.get(theme_name, THEMES["docs"])
    variables = theme.get("themeVariables", {})
    return str(variables.get("background", "#FFFFFF"))


def apply_png_theme_background(payload: bytes, theme_name: str) -> tuple[bytes, bool]:
    """Apply the local canvas and report whether an opaque PNG forced fallback."""
    has_alpha = png_has_alpha(payload)
    background = hex_to_rgb(theme_background(theme_name))
    result = flatten_png_background(
        payload,
        background,
        aurora=theme_name == "aurora",
    )
    return result, theme_name == "aurora" and not has_alpha


def add_svg_theme_background(payload: bytes, theme_name: str) -> bytes:
    if theme_name == "aurora":
        return add_svg_aurora_background(payload)
    return add_svg_background(payload, theme_background(theme_name))


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"#([0-9a-fA-F]{6})", color)
    if not match:
        raise ValueError(f"background must be a six-digit hex color: {color}")
    value = match.group(1)
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def layout_warnings(payload: bytes, diagram_type: str = "generic") -> list[str]:
    """Flag extreme aspect ratios that usually indicate a layout problem."""
    width, height = png_dimensions(payload)
    warnings: list[str] = []
    tall_exempt = {"state", "sequence", "mindmap"}
    wide_exempt = {
        "sequence",
        "mindmap",
        "timeline",
        "gantt",
        "gitgraph",
        "journey",
    }
    tall_limit = {
        "er": 3.6,
        "architecture-native": 3.6,
        "block": 3.6,
        "kanban": 3.6,
        "sankey": 3.6,
        "xychart": 3.2,
    }.get(diagram_type, 2.8)
    wide_limit = {
        "class": 5.0,
        "er": 6.0,
        "architecture-native": 6.5,
        "block": 6.5,
        "kanban": 8.0,
        "sankey": 7.0,
        "xychart": 5.5,
    }.get(diagram_type, 4.0)
    if diagram_type not in tall_exempt and height / width >= tall_limit:
        warnings.append(
            "output is very tall; simplify the structure or split the diagram"
        )
    if diagram_type not in wide_exempt and width / height >= wide_limit:
        warnings.append(
            "output is very wide; reduce fan-out or split the diagram"
        )
    return warnings


def encode_mermaid_ink(source: str) -> str:
    state = json.dumps(
        {
            "code": source,
            "mermaid": {},
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    compressed = zlib.compress(state.encode("utf-8"), 9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    return "pako:" + encoded


def render_kroki(source: str, fmt: str) -> bytes:
    url = KROKI_PNG if fmt == "png" else KROKI_SVG
    return fetch(url, data=source.encode("utf-8"))


def render_mermaid_ink(
    source: str,
    fmt: str,
) -> bytes:
    encoded = encode_mermaid_ink(source)
    template = MERMAID_INK_PNG if fmt == "png" else MERMAID_INK_SVG
    quoted = urllib.parse.quote(encoded, safe=":")
    query = "?type=png&bgColor=transparent&scale=2" if fmt == "png" else ""
    return fetch(template.format(encoded=quoted) + query)


def _hidden_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    run_kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "check": False,
        **kwargs,
    }
    if os.name == "nt":
        run_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(command, **run_kwargs)


def _which_binary(*names: str) -> str | None:
    """Return a real executable, skipping Windows .cmd/.bat shims."""
    for name in names:
        path = shutil.which(name)
        if not path:
            continue
        if os.name == "nt" and Path(path).suffix.lower() in {".cmd", ".bat"}:
            continue
        return path
    return None


def _node_binary() -> str | None:
    return _which_binary("node", "node.exe")


def _npm_global_root() -> Path | None:
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        return None
    completed = _hidden_run([npm, "root", "-g"], timeout=30)
    if completed.returncode != 0:
        return None
    root = completed.stdout.strip()
    return Path(root) if root else None


def _npx_cache_roots() -> list[Path]:
    home = Path.home()
    roots = [
        home / ".npm" / "_npx",
        home / "Library" / "Caches" / "npm" / "_npx",
    ]
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        roots.append(Path(local_app) / "npm-cache" / "_npx")
    npm_cache = os.environ.get("npm_config_cache")
    if npm_cache:
        roots.append(Path(npm_cache) / "_npx")
    return roots


def _mermaid_cli_js() -> Path | None:
    names = (
        Path("@mermaid-js") / "mermaid-cli" / "src" / "cli.js",
        Path("@mermaid-js") / "mermaid-cli" / "cli.js",
    )
    npm_root = _npm_global_root()
    if npm_root:
        for relative in names:
            candidate = npm_root / relative
            if candidate.is_file():
                return candidate
    found: list[Path] = []
    for cache in _npx_cache_roots():
        if not cache.is_dir():
            continue
        found.extend(cache.glob("*/node_modules/@mermaid-js/mermaid-cli/src/cli.js"))
        found.extend(cache.glob("*/node_modules/@mermaid-js/mermaid-cli/cli.js"))
    if not found:
        return None
    found.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return found[0]


def chromium_executable() -> str | None:
    """Chrome / Edge / Chromium on macOS, Windows, and Linux."""
    explicit = os.environ.get("PUPPETEER_EXECUTABLE_PATH") or os.environ.get(
        "CHROME_PATH"
    )
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    if sys.platform == "darwin":
        candidates.extend(
            [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
            ]
        )
    elif os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "")
        program = os.environ.get("PROGRAMFILES", "")
        program_x86 = os.environ.get("PROGRAMFILES(X86)", "")
        candidates.extend(
            [
                str(Path(local) / "Google" / "Chrome" / "Application" / "chrome.exe"),
                str(Path(program) / "Google" / "Chrome" / "Application" / "chrome.exe"),
                str(Path(program) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
                str(Path(program_x86) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
                str(Path(local) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
            ]
        )
    else:
        for name in (
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "microsoft-edge",
            "microsoft-edge-stable",
        ):
            found = shutil.which(name)
            if found:
                candidates.append(found)
    for path in candidates:
        if path and Path(path).is_file():
            return path
    return None


def _mmdc_command() -> list[str]:
    """Launch mermaid-cli the same way on macOS, Windows, and Linux."""
    node = _node_binary()
    cli = _mermaid_cli_js()
    if node and cli:
        return [node, str(cli)]
    mmdc = _which_binary("mmdc")
    if mmdc:
        return [mmdc]
    raise RuntimeError(
        "local mermaid-cli is missing. On macOS, Windows, and Linux install Node, "
        "then: npm i -g @mermaid-js/mermaid-cli"
    )


def render_local(
    source: str,
    fmt: str,
    background: str = "#FFFFFF",
) -> bytes:
    """Render with local mermaid-cli so CJK fonts and current Mermaid are used."""
    with tempfile.TemporaryDirectory(prefix="tong-chart-") as temporary:
        root = Path(temporary)
        source_path = root / "diagram.mmd"
        output_path = root / f"diagram.{fmt}"
        source_path.write_text(source, encoding="utf-8")
        command = [
            *_mmdc_command(),
            "-i",
            str(source_path),
            "-o",
            str(output_path),
            "-e",
            fmt,
            "-s",
            "2",
            "-b",
            background,
        ]
        env = os.environ.copy()
        chrome = chromium_executable()
        if chrome:
            env.setdefault("PUPPETEER_EXECUTABLE_PATH", chrome)
            env.setdefault("CHROME_PATH", chrome)
        completed = _hidden_run(command, timeout=180, env=env)
        if completed.returncode != 0 or not output_path.is_file():
            detail = (completed.stderr or completed.stdout or "no output").strip()
            raise RuntimeError(f"local mermaid-cli failed: {detail[:500]}")
        payload = output_path.read_bytes()
        validate_payload(payload, fmt)
        return payload


def engine_chain(engine: str) -> tuple[str, ...]:
    if engine in {"auto", "local"}:
        return ("local",)
    if engine == "kroki":
        return ("kroki",)
    if engine == "mermaid.ink":
        return ("mermaid.ink",)
    raise SystemExit(f"unknown engine: {engine}")


LAST_RENDER_ENGINE = ""


def render(
    source: str,
    fmt: str,
    engine: str,
    background: str = "#FFFFFF",
) -> bytes:
    global LAST_RENDER_ENGINE
    errors: list[str] = []
    for name in engine_chain(engine):
        try:
            if name == "local":
                payload = render_local(source, fmt, background)
            elif name == "kroki":
                payload = render_kroki(source, fmt)
            else:
                payload = render_mermaid_ink(source, fmt)
            validate_payload(payload, fmt)
            LAST_RENDER_ENGINE = name
            return payload
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            RuntimeError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
            OSError,
        ) as error:
            errors.append(f"{name}: {error}")
    raise SystemExit("render failed:\n- " + "\n- ".join(errors))


def atomic_write(path: Path, payload: bytes) -> None:
    """Replace a target only after a complete payload is present on disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def default_out(path: Path, fmt: str) -> Path:
    return path.with_suffix(f".{fmt}")


def render_formats(
    source: str,
    formats: tuple[str, ...],
    engine: str,
    background: str = "#FFFFFF",
) -> dict[str, bytes]:
    return {fmt: render(source, fmt, engine, background) for fmt in formats}


def render_with_look_fallback(
    raw: str,
    source: str,
    formats: tuple[str, ...],
    engine: str,
    theme_name: str,
    preset: str,
    look: str,
    inject_classdef: bool,
    allow_classic_fallback: bool,
    accent: str | None = None,
    background: str = "#FFFFFF",
) -> tuple[dict[str, bytes], str, str, bool]:
    """Render all formats with one look, optionally retrying auto Neo as Classic."""
    try:
        return (
            render_formats(source, formats, engine, background=background),
            source,
            look,
            False,
        )
    except SystemExit as neo_error:
        if not allow_classic_fallback or look != "neo":
            raise

        classic_source = apply_theme(
            raw,
            theme_name,
            preset,
            "classic",
            inject_classdef=inject_classdef,
            accent=accent,
        )
        try:
            payloads = render_formats(
                classic_source, formats, engine, background=background
            )
        except SystemExit as classic_error:
            raise SystemExit(
                f"{neo_error}\nclassic compatibility fallback failed:\n{classic_error}"
            ) from classic_error
        return payloads, classic_source, "classic", True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render Mermaid to validated PNG and optional SVG files"
    )
    parser.add_argument(
        "input", type=Path, help="Path to a .mmd, .mermaid, or fenced snippet"
    )
    parser.add_argument("-o", "--output", type=Path, help="Output PNG path")
    parser.add_argument("--svg", action="store_true", help="Also write SVG")
    parser.add_argument(
        "--engine",
        choices=("local", "auto", "kroki", "mermaid.ink"),
        default="local",
        help="Renderer; local mermaid-cli is the default. Remote engines are opt-in.",
    )
    parser.add_argument(
        "--theme",
        choices=tuple(THEMES),
        default="cursor",
        help="Named visual style: cursor, dark, ocean, forest, aurora, docs, minimal, neutral",
    )
    parser.add_argument(
        "--accent",
        help="Override accent color as #RRGGBB (flow accent, pie/git/task highlight)",
    )
    parser.add_argument(
        "--canvas",
        help="Override background as #RRGGBB",
    )
    parser.add_argument(
        "--preset",
        choices=("auto", *PRESETS),
        default="auto",
        help="Layout preset; auto detects from source",
    )
    parser.add_argument(
        "--look",
        choices=("auto", "neo", "classic"),
        default="auto",
        help="Diagram look; auto uses classic for cursor and Neo for aurora/docs",
    )
    parser.add_argument(
        "--no-theme",
        action="store_true",
        help="Do not inject a theme or semantic classes",
    )
    class_group = parser.add_mutually_exclusive_group()
    class_group.add_argument(
        "--classdef",
        dest="classdef",
        action="store_true",
        help="Inject semantic class definitions for flowcharts (default)",
    )
    class_group.add_argument(
        "--no-classdef",
        dest="classdef",
        action="store_false",
        help="Do not inject semantic flowchart class definitions",
    )
    parser.set_defaults(classdef=True)
    parser.add_argument(
        "--dump-source",
        type=Path,
        help="Write the final Mermaid source sent to the service",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.input.is_file():
        raise SystemExit(f"input not found: {args.input}")

    raw = read_mermaid(args.input)
    diagram_type = detect_diagram_type(raw)
    try:
        validate_diagram_source(raw, diagram_type)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    preset = resolve_preset(raw, args.preset)
    user_config = has_theme_config(raw)
    look = resolve_look(args.theme, args.look)
    accent = normalize_hex(args.accent) if args.accent else None
    canvas = normalize_hex(args.canvas) if args.canvas else None
    source = (
        raw
        if args.no_theme
        else apply_theme(
            raw,
            args.theme,
            preset,
            look,
            inject_classdef=args.classdef,
            accent=accent,
        )
    )

    out_png = args.output or default_out(args.input, "png")
    formats = ("png", "svg") if args.svg else ("png",)
    allow_classic_fallback = (
        not args.no_theme
        and not user_config
        and args.look == "auto"
        and look == "neo"
    )
    if canvas:
        mmdc_background = canvas
    elif args.theme == "aurora" and not args.no_theme and not user_config:
        mmdc_background = "transparent"
    else:
        mmdc_background = theme_background(args.theme)
    payloads, source, rendered_look, used_look_fallback = render_with_look_fallback(
        raw,
        source,
        formats,
        args.engine,
        args.theme,
        preset,
        look,
        inject_classdef=args.classdef,
        allow_classic_fallback=allow_classic_fallback,
        accent=accent,
        background=mmdc_background,
    )

    if args.dump_source:
        atomic_write(args.dump_source, source.encode("utf-8"))

    png = payloads["png"]
    svg = payloads.get("svg")
    background_degraded = False
    if canvas:
        png = flatten_png_background(png, hex_to_rgb(canvas), aurora=False)
        if svg is not None:
            svg = add_svg_background(svg, canvas)
    elif not args.no_theme and not user_config:
        png, background_degraded = apply_png_theme_background(
            png,
            args.theme,
        )
        if svg is not None:
            svg = add_svg_theme_background(svg, args.theme)
    out_svg = out_png.with_suffix(".svg")

    atomic_write(out_png, png)
    if svg is not None:
        atomic_write(out_svg, svg)

    print(f"PNG\t{out_png.resolve()}")
    if svg is not None:
        print(f"SVG\t{out_svg.resolve()}")
    print(f"TYPE\t{diagram_type}")
    print(f"PRESET\t{preset}")
    print(f"THEME\t{('none' if args.no_theme else args.theme)}")
    if accent:
        print(f"ACCENT\t{accent}")
    if canvas:
        print(f"CANVAS\t{canvas}")
    print(f"ENGINE\t{LAST_RENDER_ENGINE or args.engine}")
    if args.no_theme or user_config:
        print("LOOK\tsource")
    else:
        print(f"LOOK\t{rendered_look}")
    if used_look_fallback:
        print("FALLBACK\tneo-to-classic")
    if background_degraded:
        print("WARNING\tAurora PNG background could not be composited because "
              "the renderer returned an opaque image")
    for warning in layout_warnings(png, diagram_type):
        print(f"WARNING\t{warning}")


if __name__ == "__main__":
    main()
