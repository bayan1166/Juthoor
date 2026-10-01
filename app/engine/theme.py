"""
Juthoor design tokens.

Forest canopy, warm gold (bark / rims), emerald (growth) and Petra rose (roots).
Everything visual in the app (logo, avatar, tree, CSS) reads from here.
"""
from __future__ import annotations

PALETTE = {
    "ink":         "#040D07",
    "night":       "#07160E",
    "deep":        "#0F2318",
    "lift":        "#173525",
    "teal":        "#1D5140",
    "gold":        "#F0C674",
    "gold_deep":   "#B98A2C",
    "gold_pale":   "#FFE3A6",
    "emerald":     "#3DDC91",
    "emerald_deep":"#1E9E63",
    "mint":        "#B7F5D5",
    "rose":        "#E88B70",
    "rose_deep":   "#A8452B",
    "umber":       "#0D1A11",
    "text":        "#EAF6EE",
    "muted":       "#8FB09B",
    "mode":        "dark",
}

# Same roles, a daylight reading of the brand: warm parchment background,
# the gold/emerald/rose accents darkened just enough to stay legible on a
# light surface. Every CSS rule in app.py is written against these named
# roles (never a raw hex), so switching PALETTE for LIGHT_PALETTE re-themes
# the whole app with no other code changes.
LIGHT_PALETTE = {
    "ink":         "#F6FBF5",
    "night":       "#EDF6EE",
    "deep":        "#FFFFFF",
    "lift":        "#DDEEE0",
    "teal":        "#CFE7E0",
    "gold":        "#8C6620",
    "gold_deep":   "#5F4515",
    "gold_pale":   "#3E2E10",
    "emerald":     "#1F8F5F",
    "emerald_deep":"#116E44",
    "mint":        "#116E44",
    "rose":        "#B34F35",
    "rose_deep":   "#83382A",
    "umber":       "#E5F1E5",
    "text":        "#0F2118",
    "muted":       "#4C6F58",
    "mode":        "light",
}


def get_palette(dark: bool) -> dict:
    return PALETTE if dark else LIGHT_PALETTE


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def mix(c1: str, c2: str, t: float) -> str:
    """Linear blend of two hex colours, t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    a, b = _hex_to_rgb(c1), _hex_to_rgb(c2)
    return "#%02X%02X%02X" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def leaf_style(progress: float) -> dict:
    """
    Progress 0..1  ->  glass-clear leaf  ..  fully saturated emerald leaf.

    Returns fill / stroke colours + opacities and the number colour that stays readable.
    """
    p = max(0.0, min(1.0, progress))
    e = p ** 0.85
    fill = mix("#D9F7EC", PALETTE["emerald"], min(1.0, e * 1.25))
    if e > 0.8:
        fill = mix(fill, PALETTE["emerald_deep"], (e - 0.8) / 0.2 * 0.55)
    return {
        "fill": fill,
        "fill_opacity": round(0.06 + 0.94 * e, 3),
        "stroke": mix("#DDF6EE", "#7CF0BE", e),
        "stroke_opacity": round(0.38 + 0.55 * e, 3),
        "vein_opacity": round(0.22 + 0.25 * e, 3),
        "number": "#06301F" if p >= 0.5 else "#E6F2F8",
    }
