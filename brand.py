"""
Juthoor brand mark.

Idea: "جذور" means both *roots* and the mathematical *square root*.
The mark is a radical sign drawn the Arabic way (mirrored, bar running to the left).
Its long stroke is the trunk, the bar is a branch that carries five leaves fading from
solid emerald to clear glass (the same mechanic as the curriculum tree), and the vertex
of the radical is planted, with roots spreading below it.
"""
from __future__ import annotations

import svgkit as sk
from theme import PALETTE as C

# ---- geometry (design space 200 x 200, mirrored radical) -------------------
_TICK = ((160, 108), (154, 122), (146, 138), (136, 154))          # short stroke, becomes a sapling
_TRUNK = ((136, 154), (126, 128), (108, 92), (98, 60))            # long stroke, the trunk
_ARCH = ((98, 60), (78, 40), (48, 42), (18, 66))                  # the bar, now a branch
_LEAF_T = (0.17, 0.36, 0.55, 0.74, 0.93)
_LEAF_ALPHA = (1.0, 0.80, 0.58, 0.38, 0.20)
_ROOTS = (
    ((136, 154), (128, 170), (114, 180), (100, 190), 7, 1.2),
    ((136, 154), (136, 172), (138, 184), (140, 196), 7, 1.2),
    ((136, 154), (146, 168), (160, 176), (176, 182), 7, 1.2),
    ((136, 154), (120, 162), (100, 166), (84, 176), 5, 1.0),
)


def _leaf(uid: str, x: float, y: float, deg: float, length: float, width: float, alpha: float) -> str:
    return (
        f'<g transform="translate({x:.1f} {y:.1f}) rotate({deg:.1f})">'
        f'<path d="{sk.leaf_d(length, width)}" fill="url(#{uid}-em)" fill-opacity="{0.10 + 0.90 * alpha:.2f}" '
        f'stroke="{C["mint"]}" stroke-opacity="{0.45 + 0.5 * alpha:.2f}" stroke-width="1.1"/>'
        f'<path d="{sk.leaf_veins(length, width)}" fill="none" stroke="#04281B" '
        f'stroke-opacity="{0.10 + 0.25 * alpha:.2f}" stroke-width="0.8" stroke-linecap="round"/>'
        f'</g>'
    )


def _mark_body(uid: str) -> str:
    parts: list[str] = []

    # roots first (they sit behind the vertex)
    for p0, p1, p2, p3, w0, w1 in _ROOTS:
        parts.append(f'<path d="{sk.tapered(p0, p1, p2, p3, w0, w1)}" fill="url(#{uid}-rose)"/>')
        parts.append(f'<circle cx="{p3[0]}" cy="{p3[1]}" r="2.6" fill="{C["gold_pale"]}" fill-opacity=".9"/>')

    # trunk, tick, branch: tapered gold ribbons with a light strip for metal
    trunk = sk.tapered(*_TRUNK, 17, 8.5, ease=0.9)
    tick = sk.tapered(*_TICK, 6.5, 14, ease=1.0)
    arch = sk.tapered(*_ARCH, 9.5, 4.2, ease=0.9)
    for d in (tick, trunk, arch):
        parts.append(f'<path d="{d}" fill="url(#{uid}-gold)"/>')
    parts.append(f'<path d="{sk.tapered(*_TRUNK, 4.6, 2.2, shift=-2.6)}" fill="{C["gold_pale"]}" fill-opacity=".55"/>')
    parts.append(f'<path d="{sk.tapered(*_ARCH, 3.4, 1.4, shift=-1.5)}" fill="{C["gold_pale"]}" fill-opacity=".5"/>')

    # sapling leaf on the tick (fully grown)
    parts.append(_leaf(uid, 160, 107, 28, 38, 20, 1.0))

    # leaves along the branch, alternating above / below
    for k, (t, a) in enumerate(zip(_LEAF_T, _LEAF_ALPHA)):
        x, y = sk.bez(*_ARCH, t)
        tx, ty = sk.bez_tan(*_ARCH, t)
        upper = k % 2 == 0
        cands = [sk.rotate(tx, ty, 62), sk.rotate(tx, ty, -62)]
        vx, vy = min(cands, key=lambda v: v[1]) if upper else max(cands, key=lambda v: v[1])
        length, width = (42, 22) if upper else (36, 19)
        parts.append(_leaf(uid, x + vx * 3, y + vy * 3, sk.angle_of(vx, vy), length, width, a))

    # vertex bead where the roots start
    parts.append(f'<circle cx="136" cy="154" r="4.4" fill="{C["gold_pale"]}"/>')
    return "".join(parts)


def _defs(uid: str) -> str:
    return (
        "<defs>"
        f'<linearGradient id="{uid}-gold" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{C["gold_pale"]}"/><stop offset=".45" stop-color="{C["gold"]}"/>'
        f'<stop offset="1" stop-color="{C["gold_deep"]}"/></linearGradient>'
        f'<linearGradient id="{uid}-rose" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#F3C2A8"/><stop offset=".5" stop-color="{C["rose"]}"/>'
        f'<stop offset="1" stop-color="{C["rose_deep"]}"/></linearGradient>'
        f'<linearGradient id="{uid}-em" x1="0" y1="1" x2="0" y2="0">'
        f'<stop offset="0" stop-color="{C["emerald_deep"]}"/><stop offset="1" stop-color="#5FE6AE"/></linearGradient>'
        f'<radialGradient id="{uid}-bg" cx=".5" cy=".38" r=".75">'
        f'<stop offset="0" stop-color="#1D4A78"/><stop offset=".6" stop-color="#0F2A4E"/>'
        f'<stop offset="1" stop-color="{C["ink"]}"/></radialGradient>'
        f'<linearGradient id="{uid}-ring" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{C["gold_pale"]}"/><stop offset=".5" stop-color="{C["gold"]}"/>'
        f'<stop offset="1" stop-color="{C["gold_deep"]}"/></linearGradient>'
        "</defs>"
    )


def logo_mark(uid: str = "jl", variant: str = "badge", size: int | None = None) -> str:
    """
    variant="badge": the mark inside a navy medallion with a gold ring (favicon, headers).
    variant="bare" : the mark alone (for use on dark surfaces that already frame it).
    """
    dim = f' width="{size}" height="{size}"' if size else ""
    body = _mark_body(uid)
    if variant == "bare":
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-24 -4 210 210"{dim} role="img" '
                f'aria-label="جذور">{_defs(uid)}{body}</svg>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"{dim} role="img" aria-label="جذور">'
        f"{_defs(uid)}"
        f'<circle cx="100" cy="100" r="97" fill="url(#{uid}-bg)"/>'
        f'<circle cx="100" cy="100" r="95" fill="none" stroke="url(#{uid}-ring)" stroke-width="4"/>'
        f'<circle cx="100" cy="100" r="86" fill="none" stroke="{C["gold"]}" stroke-opacity=".28" stroke-width="1"/>'
        f'<g transform="translate(100 101) scale(.68) translate(-85 -110)">{body}</g>'
        "</svg>"
    )


def lockup_html(size: int = 52) -> str:
    """Mark + Arabic wordmark (Aref Ruqaa) + Latin name. Styled by .jt-lockup in the app CSS."""
    return (
        '<div class="jt-lockup">'
        f'<span class="jt-lockup-mark" style="width:{size}px;height:{size}px">{logo_mark("jlk", "badge")}</span>'
        '<span class="jt-lockup-word"><b>جذور</b><i>Juthoor</i></span>'
        "</div>"
    )
