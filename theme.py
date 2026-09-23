"""
Juthoor design tokens.

Night-sky navy, brushed gold (bark / rims), emerald (growth) and Petra rose (roots).
Everything visual in the app (logo, avatar, tree, CSS) reads from here.
"""
from __future__ import annotations

PALETTE = {
    "ink": "#081428",        # sky top
    "night": "#0A1A33",      # page background
    "deep": "#10284A",       # cards
    "lift": "#173763",       # raised surfaces / hover
    "teal": "#1C5B63",       # horizon glow
    "gold": "#E6BE6A",
    "gold_deep": "#B8862F",
    "gold_pale": "#FFE8AE",
    "emerald": "#1FC98A",
    "emerald_deep": "#0E9A68",
    "mint": "#B9F3D9",
    "rose": "#D98466",       # Petra sandstone
    "rose_deep": "#9C4A38",
    "umber": "#24140F",
    "text": "#EAF1F7",
    "muted": "#9DB2C8",
    "mode": "dark",
}

# Same roles, a daylight reading of the brand: warm parchment background,
# the gold/emerald/rose accents darkened just enough to stay legible on a
# light surface. Every CSS rule in app.py is written against these named
# roles (never a raw hex), so switching PALETTE for LIGHT_PALETTE re-themes
# the whole app with no other code changes.
LIGHT_PALETTE = {
    "ink": "#FBF7EE",         # sky top
    "night": "#F6F1E4",       # page background (warm parchment, not stark white)
    "deep": "#FFFFFF",        # cards
    "lift": "#F0E9D8",        # raised surfaces / hover
    "teal": "#CFE7E3",        # horizon glow
    "gold": "#A9761F",
    "gold_deep": "#7C5716",
    "gold_pale": "#5C4014",
    "emerald": "#158A5D",
    "emerald_deep": "#0E6B47",
    "mint": "#0E6B47",
    "rose": "#B0492F",
    "rose_deep": "#8A3623",
    "umber": "#F3E7DD",
    "text": "#241A0F",
    "muted": "#6B5D45",
    "mode": "light",
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
