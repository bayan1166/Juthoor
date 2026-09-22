"""
Juthoor avatar: a hand-built SVG bust (boy or girl) inside a gold-ringed night-sky medallion.

Layers (back to front): hair behind -> clothing -> hair over the shoulders -> neck -> scarf -> ears/head/face
-> hair on top -> glasses -> headwear (cap, hijab, shemagh ...).

What can be worn lives in avatar_items.py (drawings + the shop catalog).  Item ids the shop already used
(skin / clothing / accessories / top) are unchanged, so an old gami_state keeps working.
"""
from __future__ import annotations

import math

import avatar_items as ai
from theme import PALETTE as C, mix

# skin id -> (base, shade, blush)
SKINS = {
    "ffe0c2": ("#FBE3CD", "#EBC3A2", "#F2A79A"),   # فاتح جداً
    "f8d25c": ("#F7D8BE", "#E3B48F", "#EE9C90"),   # فاتح
    "edb98a": ("#DFAA79", "#C48A5A", "#D9826F"),   # حنطي
    "c68642": ("#C68A5A", "#A56C40", "#C5745A"),   # برونزي
    "8d5524": ("#94603A", "#6F4327", "#B8674F"),   # أسمر
}
SKIN_OPTIONS = [("ffe0c2", "فاتح جداً"), ("f8d25c", "فاتح"), ("edb98a", "حنطي"), ("c68642", "برونزي"), ("8d5524", "أسمر")]

# hair colour id -> (Arabic name, base, highlight)
HAIR_COLORS = {
    "black": ("أسود", "#2A1B15", "#5A3F31"),
    "brown": ("بني غامق", "#5A3620", "#8A5A38"),
    "chestnut": ("كستنائي", "#8B4A2B", "#B9744A"),
    "blonde": ("أشقر", "#D6A64A", "#F0CF86"),
    "ginger": ("أحمر", "#B4491F", "#E07A45"),
    "gray": ("رمادي", "#8B8F98", "#C2C6CE"),
}
# hair style id -> (Arabic name, gender it is for (None = both))
HAIR_STYLES = {
    "straight": ("ستريت", None),
    "wavy": ("ويفي", None),
    "curly": ("كيرلي", None),
    "buzz": ("قصير جداً", "ولد"),
    "pony": ("ذيل حصان", "بنت"),
}


# -------------------------------------------------------------------- defs
def _defs(u: str, skin: tuple[str, str, str]) -> str:
    base, shade, _ = skin
    return (
        "<defs>"
        f'<radialGradient id="{u}-bg" cx=".5" cy=".3" r=".85"><stop offset="0" stop-color="#25689A"/>'
        f'<stop offset=".55" stop-color="#123A63"/><stop offset="1" stop-color="{C["ink"]}"/></radialGradient>'
        f'<linearGradient id="{u}-ring" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C["gold_pale"]}"/>'
        f'<stop offset=".5" stop-color="{C["gold"]}"/><stop offset="1" stop-color="{C["gold_deep"]}"/></linearGradient>'
        f'<linearGradient id="{u}-skin" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{base}"/>'
        f'<stop offset="1" stop-color="{shade}"/></linearGradient>'
        f'<linearGradient id="{u}-em" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#34D99A"/>'
        f'<stop offset="1" stop-color="{C["emerald_deep"]}"/></linearGradient>'
        f'<linearGradient id="{u}-coat" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF"/>'
        f'<stop offset="1" stop-color="#CFDBE7"/></linearGradient>'
        f'<linearGradient id="{u}-suit" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F1F5FA"/>'
        f'<stop offset="1" stop-color="#A9B8CB"/></linearGradient>'
        f'<linearGradient id="{u}-goldf" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C["gold_pale"]}"/>'
        f'<stop offset="1" stop-color="{C["gold_deep"]}"/></linearGradient>'
        f'<linearGradient id="{u}-lens" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3A4A66"/>'
        f'<stop offset="1" stop-color="#0B1220"/></linearGradient>'
        # Jordanian cross-stitch embroidery
        f'<pattern id="{u}-emb" width="9" height="9" patternUnits="userSpaceOnUse"><rect width="9" height="9" fill="#6E1424"/>'
        f'<path d="M4.5 0L9 4.5L4.5 9L0 4.5Z" fill="#D63A3A"/><path d="M4.5 2.3L6.7 4.5L4.5 6.7L2.3 4.5Z" fill="#E6BE6A"/>'
        f'<circle cx="4.5" cy="4.5" r="1" fill="#1E7A4C"/></pattern>'
        # shemagh (red / black checks)
        f'<pattern id="{u}-shr" width="9" height="9" patternUnits="userSpaceOnUse"><rect width="9" height="9" fill="#FFFFFF"/>'
        f'<path d="M0 0H4.5V4.5H0ZM4.5 4.5H9V9H4.5Z" fill="#C8202F"/><path d="M0 4.5H9M4.5 0V9" stroke="#FFFFFF" stroke-opacity=".35" stroke-width=".6"/></pattern>'
        f'<pattern id="{u}-shb" width="9" height="9" patternUnits="userSpaceOnUse"><rect width="9" height="9" fill="#FFFFFF"/>'
        f'<path d="M0 0H4.5V4.5H0ZM4.5 4.5H9V9H4.5Z" fill="#23262E"/><path d="M0 4.5H9M4.5 0V9" stroke="#FFFFFF" stroke-opacity=".35" stroke-width=".6"/></pattern>'
        f'<clipPath id="{u}-clip"><circle cx="120" cy="120" r="112"/></clipPath>'
        "</defs>"
    )


# -------------------------------------------------------------------- hair
def _circles(pts, r, color) -> str:
    return "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}"/>' for x, y in pts)


def _arc_pts(cx, cy, rad, a0, a1, n):
    return [(cx + rad * math.cos(math.radians(a0 + (a1 - a0) * i / (n - 1))),
             cy - rad * math.sin(math.radians(a0 + (a1 - a0) * i / (n - 1)))) for i in range(n)]


def _scallops(x0, x1, y, amp, n) -> str:
    d, step = "", (x1 - x0) / n
    for i in range(n):
        xs, xe = x0 + step * i, x0 + step * (i + 1)
        d += f"Q{(xs + xe) / 2:.1f} {y + amp:.1f} {xe:.1f} {y:.1f}"
    return d


def _hair_back(girl: bool, style: str, hc: str, hi: str) -> str:
    """Hair that sits behind the shoulders (long styles for the girl)."""
    if not girl:
        return ""
    if style == "pony":
        return f'<path d="M158 88C194 88 208 134 194 178C190 196 174 200 170 186C180 152 174 116 150 100Z" fill="{hc}"/>'
    base = f'<path d="M64 112C56 60 88 30 122 30C156 30 186 60 178 112C182 152 194 190 186 236L54 236C46 190 58 152 64 112Z" fill="{hc}"/>'
    if style == "wavy":
        bumps = _circles([(60, 132), (55, 154), (60, 178), (53, 200), (58, 224)] + [(180, 132), (185, 154), (180, 178), (187, 200), (182, 224)], 10, hc)
        return base + bumps
    if style == "curly":
        left = [(60, 100), (50, 124), (46, 148), (50, 172), (46, 196), (52, 220), (64, 236)]
        pts = left + [(240 - x, y) for x, y in left]
        return base + _circles(pts, 19, hc) + _circles([(x + 3, y - 4) for x, y in pts[::2]], 5, hi).replace(f'fill="{hi}"', f'fill="{hi}" fill-opacity=".35"')
    return base


def _hair_locks(girl: bool, style: str, hc: str, hi: str) -> str:
    """Girl's hair falling over the front of the shoulders."""
    if not girl or style == "pony":
        return ""
    if style == "curly":
        pts = [(78, 142), (70, 166), (72, 190), (68, 214), (162, 142), (170, 166), (168, 190), (172, 214)]
        return _circles(pts, 15, hc)
    out = (f'<path d="M70 124C60 156 62 196 56 222C74 230 94 222 98 204C92 178 92 152 94 134Z" fill="{hc}"/>'
           f'<path d="M170 124C180 156 178 196 184 222C166 230 146 222 142 204C148 178 148 152 146 134Z" fill="{hc}"/>'
           f'<path d="M68 150C64 172 66 194 64 210" fill="none" stroke="{hi}" stroke-opacity=".6" stroke-width="3" stroke-linecap="round"/>')
    if style == "wavy":
        out += _circles([(66, 152), (62, 178), (60, 204), (174, 152), (178, 178), (180, 204)], 8, hc)
    return out


def _hair_top(girl: bool, style: str, hc: str, hi: str) -> str:
    """Hair on top of the head, in front of the face."""
    if style == "curly":
        r = 17 if girl else 15
        crown = _arc_pts(120, 96, 45, 192, -12, 10)
        fringe = [(x, 80 + abs(x - 120) * 0.07) for x in range(90, 152, 12)]
        side = [(75, 100), (165, 100)] if not girl else [(74, 104), (166, 104)]
        return (f'<ellipse cx="120" cy="74" rx="46" ry="30" fill="{hc}"/>' + _circles(crown, r, hc) + _circles(fringe, 10, hc) + _circles(side, 11, hc) +
                _circles([(x + 2, y - 5) for x, y in crown[1:-1:2]], 4.5, hi).replace(f'fill="{hi}"', f'fill="{hi}" fill-opacity=".4"'))
    if style == "buzz":
        return (f'<path d="M76 102C73 66 94 50 120 50C146 50 167 66 164 102C160 88 154 80 146 76C132 70 108 70 94 76C86 80 80 90 76 102Z" fill="{hc}" fill-opacity=".92"/>')
    if style == "pony":
        return (f'<path d="M75 104C72 66 94 50 120 50C146 50 168 66 165 104C160 84 148 72 132 68C118 80 92 86 75 104Z" fill="{hc}"/>'
                f'<circle cx="164" cy="90" r="6.5" fill="{C["rose"]}" stroke="{C["rose_deep"]}" stroke-width="1.5"/>'
                f'<path d="M96 56C108 50 128 50 144 56" fill="none" stroke="{hi}" stroke-opacity=".7" stroke-width="3" stroke-linecap="round"/>')
    if girl:
        if style == "wavy":
            edge = _scallops(134, 92, 66, 8, 4)
            return (f'<path d="M71 106C62 56 94 36 122 36C152 36 180 58 169 106C166 88 152 74 134 66{edge}C86 82 76 92 71 106Z" fill="{hc}"/>'
                    f'<path d="M92 46C108 38 130 38 148 46" fill="none" stroke="{hi}" stroke-opacity=".7" stroke-width="3" stroke-linecap="round"/>')
        return (f'<path d="M71 104C64 58 94 38 122 38C150 38 178 58 169 104C166 86 152 70 134 64C122 80 90 90 71 104Z" fill="{hc}"/>'
                f'<path d="M96 48C110 40 130 40 146 48" fill="none" stroke="{hi}" stroke-opacity=".7" stroke-width="3" stroke-linecap="round"/>')
    if style == "wavy":
        edge = _scallops(151, 88, 80, 8, 5)
        return (f'<path d="M73 106C64 60 92 30 122 30C152 30 180 60 167 106C164 94 158 86 151 80{edge}C82 88 76 96 73 106Z" fill="{hc}"/>'
                f'<path d="M92 46C106 38 128 36 146 44" fill="none" stroke="{hi}" stroke-opacity=".7" stroke-width="3" stroke-linecap="round"/>')
    return (f'<path d="M73 106C66 62 92 34 122 34C152 34 176 62 167 106C163 92 157 84 149 80C136 88 106 90 91 78C83 86 76 96 73 106Z" fill="{hc}"/>'
            f'<path d="M94 48C108 40 128 38 146 46" fill="none" stroke="{hi}" stroke-opacity=".7" stroke-width="3" stroke-linecap="round"/>')


# -------------------------------------------------------------------- main
def avatar_svg(gender: str = "ولد", skin: str = "f8d25c", clothing: str = "shirtCrewNeck", accessories: str = "blank",
               top: str = "none", hair: str = "straight", hair_color: str = "black", neck: str = "none",
               size: int | None = None, uid: str = "av") -> str:
    girl = gender == "بنت"
    base, shade, blush = SKINS.get(skin, SKINS["f8d25c"])
    palette = (base, shade, blush)
    hc, hi = HAIR_COLORS.get(hair_color, HAIR_COLORS["black"])[1:]
    if hair not in HAIR_STYLES or (HAIR_STYLES[hair][1] not in (None, gender)):
        hair = "straight"
    top = top if top in ai.HEADWEAR else "none"
    covered = top in ai.HAIR_COVER_FULL              # hijab / shemagh / coin scarf hide all hair
    hat = top not in ("none", "astrohelmet")           # the space helmet is glass: the hair stays visible
    dim = f' width="{size}" height="{size}"' if size else ""

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240"{dim} role="img" aria-label="أفاتار الطالب">',
           _defs(uid, palette),
           f'<circle cx="120" cy="120" r="112" fill="url(#{uid}-bg)"/>',
           '<g fill="#FFE8AE" fill-opacity=".7"><circle cx="46" cy="52" r="1.6"/><circle cx="196" cy="46" r="1.3"/>'
           '<circle cx="34" cy="108" r="1.1"/><circle cx="206" cy="96" r="1.6"/><circle cx="170" cy="30" r="1.1"/></g>',
           f'<g clip-path="url(#{uid}-clip)">']

    if not covered:
        out.append(_hair_back(girl, hair, hc, hi))
    out.append(ai.CLOTHING.get(clothing, ai.CLOTHING["shirtCrewNeck"])(uid))
    out.append('<path d="M22 244C26 198 72 178 120 178C168 178 214 198 218 244" fill="none" stroke="#FFFFFF" stroke-opacity=".22" stroke-width="2"/>')   # rim light: keeps dark outfits readable
    if not covered:
        out.append(_hair_locks(girl, hair, hc, hi))

    # neck (soft shadow under the chin), scarf, ears, head
    out.append(f'<path d="M103 138L103 178C103 190 137 190 137 178L137 138Z" fill="{shade}"/>')
    out.append('<ellipse cx="120" cy="160" rx="18" ry="9" fill="#000" fill-opacity=".10"/>')
    out.append(ai.NECK.get(neck, ai.NECK["none"])(uid))
    out.append(f'<circle cx="76" cy="116" r="9" fill="{base}"/><circle cx="164" cy="116" r="9" fill="{base}"/>'
               f'<circle cx="76" cy="117" r="4.5" fill="{shade}" fill-opacity=".7"/><circle cx="164" cy="117" r="4.5" fill="{shade}" fill-opacity=".7"/>')
    out.append(f'<path d="M75 108C75 74 95 54 120 54C145 54 165 74 165 108C165 138 146 162 120 164C94 162 75 138 75 108Z" fill="url(#{uid}-skin)"/>')

    # face
    eye_h = 6.2 if girl else 5.4
    out.append(f'<ellipse cx="102" cy="114" rx="4.8" ry="{eye_h}" fill="#26160F"/><ellipse cx="138" cy="114" rx="4.8" ry="{eye_h}" fill="#26160F"/>')
    out.append('<circle cx="103.8" cy="111.8" r="1.7" fill="#fff"/><circle cx="139.8" cy="111.8" r="1.7" fill="#fff"/>')
    brow = 3.0 if girl else 3.8
    out.append(f'<path d="M91 101Q102 95 113 100M127 100Q138 95 149 101" fill="none" stroke="{hc}" stroke-width="{brow}" stroke-linecap="round"/>')
    if girl:
        out.append('<path d="M96 110L92 107M99 108L96 104M144 110L148 107M141 108L144 104" stroke="#26160F" stroke-width="1.8" stroke-linecap="round"/>')
    out.append(f'<path d="M120 119Q115 130 121 131" fill="none" stroke="{shade}" stroke-width="2.4" stroke-linecap="round"/>')
    out.append(f'<circle cx="92" cy="130" r="8.5" fill="{blush}" fill-opacity=".30"/><circle cx="148" cy="130" r="8.5" fill="{blush}" fill-opacity=".30"/>')
    if girl:
        out.append('<path d="M108 141Q120 152 132 141Q120 145 108 141Z" fill="#B5453F" stroke="#B5453F" stroke-width="2.6" stroke-linejoin="round"/>')
    else:
        out.append('<path d="M107 141Q120 152 133 141" fill="none" stroke="#8A3B32" stroke-width="3.2" stroke-linecap="round"/>')

    # hair on top / sideburns under a cap
    if not hat:
        out.append(_hair_top(girl, hair, hc, hi))
    elif not covered and not girl:
        out.append(f'<path d="M73 106C72 96 74 90 78 86L82 100Z M167 106C168 96 166 90 162 86L158 100Z" fill="{hc}"/>')

    out.append(ai.GLASSES.get(accessories, lambda u: "")(uid))
    out.append(ai.HEADWEAR[top](uid))
    out.append("</g>")
    out.append(f'<circle cx="120" cy="120" r="112" fill="none" stroke="url(#{uid}-ring)" stroke-width="6"/>')
    out.append(f'<circle cx="120" cy="120" r="105" fill="none" stroke="{C["gold"]}" stroke-opacity=".3" stroke-width="1"/>')
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------- helpers used by the shop UI
def item_name(cat: str, item_id: str) -> str:
    it = ai.BY_ID.get((cat, item_id))
    return it.name if it else item_id


def items(group: str, gender: str) -> list[ai.Item]:
    """Catalog items of one shop group that suit this avatar (girl-only / boy-only items are filtered)."""
    return [i for i in ai.CATALOG if i.group == group and i.gender in (None, gender)]


DEFAULTS = {"clothing": "shirtCrewNeck", "top": "none", "neck": "none", "accessories": "blank", "hair": "straight", "hair_color": "black", "skin": "f8d25c"}


def fit_to_gender(g: dict) -> dict:
    """After switching boy/girl, take off anything that belongs to the other one. Returns the fixed dict."""
    gender = g.get("gender", "ولد")
    for cat in ("clothing", "top"):
        it = ai.BY_ID.get((cat, g.get(cat)))
        if it and it.gender not in (None, gender):
            g[cat] = DEFAULTS[cat]
    style = HAIR_STYLES.get(g.get("hair"), (None, None))
    if style[1] not in (None, gender):
        g["hair"] = DEFAULTS["hair"]
    return g
