"""
The curriculum tree.

One leaf per lesson of the book. Leaves sit on four boughs (one per unit, unit 1 lowest).
A leaf's colour follows curriculum.progress(): clear glass -> saturated emerald.
The scene is a single inline SVG so it scales to any phone / desktop width. Streamlit strips
JavaScript from st.markdown, so leaf taps are handled by tree_component.py (a tiny Streamlit
component that draws this same HTML and reports which leaf was tapped); detail_html() is the
panel that opens under the tree with the lesson's key concepts.
"""
from __future__ import annotations

import math
import random
import re
from html import escape

import curriculum as cur
import svgkit as sk
from theme import PALETTE as C, leaf_style

W, H = 720, 1140
TOP = 96                      # the top of the viewBox (empty sky is cropped)
GROUND = 905

# base -> top of the trunk (cubic)
TRUNK = ((360, 912), (336, 780), (390, 560), (360, 296))

# one bough per unit: cubic + thickness at the trunk / at the tip
BOUGHS = {
    1: dict(c=((352, 808), (272, 812), (198, 770), (104, 700)), w=(30, 7)),
    2: dict(c=((368, 744), (450, 742), (536, 700), (628, 636)), w=(28, 7)),
    3: dict(c=((358, 628), (290, 612), (216, 548), (128, 446)), w=(24, 6)),
    4: dict(c=((366, 548), (440, 526), (516, 458), (602, 352)), w=(22, 6)),
}
LEAF_LEN, LEAF_W = 104, 50


# ------------------------------------------------------------------ scenery
def _defs() -> str:
    return (
        "<defs>"
        f'<linearGradient id="jt-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C["ink"]}"/>'
        f'<stop offset=".55" stop-color="#0F2E52"/><stop offset="1" stop-color="{C["teal"]}"/></linearGradient>'
        f'<radialGradient id="jt-glow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#3FA98F" stop-opacity=".38"/>'
        f'<stop offset="1" stop-color="#3FA98F" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="jt-moon" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{C["gold_pale"]}" stop-opacity=".9"/>'
        f'<stop offset=".4" stop-color="{C["gold_pale"]}" stop-opacity=".22"/><stop offset="1" stop-color="{C["gold_pale"]}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="jt-soil" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3A2018"/>'
        f'<stop offset="1" stop-color="#160B09"/></linearGradient>'
        f'<linearGradient id="jt-bark" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C["gold_pale"]}"/>'
        f'<stop offset=".4" stop-color="{C["gold"]}"/><stop offset="1" stop-color="{C["gold_deep"]}"/></linearGradient>'
        f'<linearGradient id="jt-root" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F3C2A8"/>'
        f'<stop offset=".5" stop-color="{C["rose"]}"/><stop offset="1" stop-color="{C["rose_deep"]}"/></linearGradient>'
        f'<linearGradient id="jt-leafbase" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{C["emerald_deep"]}" stop-opacity=".0"/>'
        f'<stop offset="1" stop-color="#8FF5C8" stop-opacity=".0"/></linearGradient>'
        "</defs>"
    )


def _sky() -> str:
    rnd = random.Random(7)
    stars = []
    for _ in range(80):
        x, y = rnd.uniform(8, W - 8), rnd.uniform(TOP + 8, 780)
        r = rnd.choice((0.8, 1.0, 1.3, 1.7))
        stars.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#FFF6D8" fill-opacity="{rnd.uniform(.25, .8):.2f}"/>')
    sparkle = ""
    for x, y, s in ((84, 300, 9), (640, 200, 7), (596, 520, 6), (60, 560, 6)):
        sparkle += (f'<path d="M{x} {y - s}Q{x} {y} {x + s} {y}Q{x} {y} {x} {y + s}Q{x} {y} {x - s} {y}Q{x} {y} {x} {y - s}Z" '
                    f'fill="{C["gold_pale"]}" fill-opacity=".85"/>')
    return (
        f'<rect y="{TOP}" width="{W}" height="{GROUND + 30 - TOP}" fill="url(#jt-sky)"/>'
        f'<circle cx="120" cy="200" r="120" fill="url(#jt-moon)"/>'
        f'<circle cx="120" cy="200" r="30" fill="#FFF3CF"/>'
        f'<circle cx="132" cy="192" r="26" fill="#0E2A4A" fill-opacity=".16"/>'
        f'<circle cx="360" cy="470" r="380" fill="url(#jt-glow)"/>'
        + "".join(stars) + sparkle
        + f'<path d="M0 858C90 820 170 846 250 832C340 816 420 850 520 828C600 812 660 826 720 812L720 940L0 940Z" fill="#12406A" fill-opacity=".85"/>'
        + f'<path d="M0 884C110 858 200 880 300 866C410 850 520 884 620 862C670 852 700 858 720 856L720 940L0 940Z" fill="#0C2C4F"/>'
    )


def _ground() -> str:
    soil = (
        f'<path d="M0 {GROUND - 8}C120 {GROUND - 26} 230 {GROUND + 2} 360 {GROUND - 8}C480 {GROUND - 18} 600 {GROUND + 4} 720 {GROUND - 12}'
        f'L720 {H}L0 {H}Z" fill="url(#jt-soil)"/>'
        f'<path d="M0 {GROUND - 8}C120 {GROUND - 26} 230 {GROUND + 2} 360 {GROUND - 8}C480 {GROUND - 18} 600 {GROUND + 4} 720 {GROUND - 12}" '
        f'fill="none" stroke="{C["emerald"]}" stroke-opacity=".55" stroke-width="3"/>'
    )
    strata = ""
    for i, y in enumerate((968, 1030, 1092)):
        strata += (f'<path d="M0 {y}C140 {y - 14} 260 {y + 12} 380 {y}C500 {y - 12} 620 {y + 10} 720 {y - 4}" fill="none" '
                   f'stroke="{C["rose"]}" stroke-opacity="{.10 - i * .02:.2f}" stroke-width="2"/>')
    roots_def = [
        ((352, 918), (300, 936), (226, 950), (120, 1004), 26, 2.4),
        ((354, 924), (322, 968), (292, 1010), (240, 1074), 22, 2.2),
        ((358, 930), (348, 982), (344, 1030), (326, 1100), 18, 2.0),
        ((366, 930), (376, 984), (382, 1032), (398, 1096), 18, 2.0),
        ((368, 924), (398, 968), (432, 1008), (486, 1070), 22, 2.2),
        ((370, 918), (420, 936), (494, 952), (604, 1006), 26, 2.4),
    ]
    roots = ""
    for a, b, c, d, w0, w1 in roots_def:
        roots += f'<path d="{sk.tapered(a, b, c, d, w0, w1, ease=0.8)}" fill="url(#jt-root)"/>'
        roots += f'<circle cx="{d[0]}" cy="{d[1]}" r="4" fill="{C["gold_pale"]}" fill-opacity=".9"/>'
    for x0, y0, x1, y1 in ((214, 954, 176, 986), (270, 1004, 232, 1040), (466, 1010, 506, 1044), (500, 962, 548, 990), (336, 1030, 300, 1068)):
        roots += (f'<path d="M{x0} {y0}Q{(x0 + x1) / 2 + 8} {(y0 + y1) / 2} {x1} {y1}" fill="none" stroke="{C["rose"]}" '
                  f'stroke-opacity=".7" stroke-width="2" stroke-linecap="round"/>'
                  f'<circle cx="{x1}" cy="{y1}" r="2.4" fill="{C["gold_pale"]}" fill-opacity=".8"/>')
    caption = (f'<text x="360" y="{H - 22}" text-anchor="middle" class="jt-ruq" font-size="24" fill="{C["gold"]}" '
               f'fill-opacity=".62">كل درس يقوم على جذره</text>')
    return soil + strata + roots + caption


def _fireflies() -> str:
    rnd = random.Random(21)
    out = []
    for _ in range(16):
        x, y = rnd.uniform(40, W - 40), rnd.uniform(240, 860)
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.choice((1.6, 2.2, 2.8))}" fill="{C["gold_pale"]}" fill-opacity="{rnd.uniform(.35, .75):.2f}"/>')
    return "".join(out)


# --------------------------------------------------------------------- tree
def _tree_wood() -> str:
    parts = []
    trunk = sk.tapered(*TRUNK, 80, 22, ease=0.85)
    parts.append(f'<path d="{trunk}" fill="url(#jt-bark)"/>')
    parts.append(f'<path d="{sk.tapered(*TRUNK, 16, 5, shift=-15, ease=0.85)}" fill="{C["gold_pale"]}" fill-opacity=".38"/>')
    parts.append(f'<path d="{sk.tapered(*TRUNK, 14, 4, shift=17, ease=0.85)}" fill="{C["gold_deep"]}" fill-opacity=".55"/>')
    for u, b in BOUGHS.items():
        c, (w0, w1) = b["c"], b["w"]
        parts.append(f'<path d="{sk.tapered(*c, w0, w1, ease=0.9)}" fill="url(#jt-bark)"/>')
        parts.append(f'<path d="{sk.tapered(*c, w0 * .28, 2, shift=-w0 * .26, ease=0.9)}" fill="{C["gold_pale"]}" fill-opacity=".4"/>')
    # small crown twigs at the top of the trunk
    for c in (((360, 306), (350, 280), (334, 262), (312, 250)), ((360, 306), (372, 280), (390, 262), (414, 252))):
        parts.append(f'<path d="{sk.tapered(*c, 9, 2.4)}" fill="url(#jt-bark)"/>')
        parts.append(f'<circle cx="{c[3][0]}" cy="{c[3][1]}" r="3.6" fill="{C["gold_pale"]}"/>')
    return "".join(parts)


def _leaf_positions(unit: cur.Unit) -> list[dict]:
    """Place the leaves of a unit along its bough, alternating above / below."""
    b = BOUGHS[unit.no]["c"]
    n = len(unit.lessons)
    out = []
    for k, lesson in enumerate(unit.lessons):
        t = 0.24 + 0.71 * (k / (n - 1) if n > 1 else 0.5)
        x, y = sk.bez(*b, t)
        tx, ty = sk.bez_tan(*b, t)
        upper = k % 2 == 0
        cands = [sk.rotate(tx, ty, 50), sk.rotate(tx, ty, -50)]
        vx, vy = min(cands, key=lambda v: v[1]) if upper else max(cands, key=lambda v: v[1])
        twig = 20
        bx, by = x + vx * twig, y + vy * twig                       # leaf base
        scale = 1.0 if upper else 0.9
        out.append(dict(lesson=lesson, x=bx, y=by, deg=sk.angle_of(vx, vy), scale=scale,
                        stem=(x, y), order=k))
    return out


def _leaf(unit: cur.Unit, pos: dict, state, selected: str | None, idx: int) -> str:
    lesson = pos["lesson"]
    key = cur.lesson_key(unit, lesson)
    st = cur.status(state, lesson)
    prog = cur.progress(state, lesson)
    sty = leaf_style(prog)
    L, Wd = LEAF_LEN * pos["scale"], LEAF_W * pos["scale"]
    x, y, deg = pos["x"], pos["y"], pos["deg"]
    rad = math.radians(deg)
    cx, cy = x + math.sin(rad) * L * 0.5, y - math.cos(rad) * L * 0.5      # leaf centre

    cls = f"jt-leaf jt-{st}"
    dash = ""
    if st in (cur.LOCKED, cur.SOON):
        dash = ' stroke-dasharray="5 5"'
    fill_opacity = sty["fill_opacity"]
    stroke_opacity = sty["stroke_opacity"]
    if st == cur.SOON:
        stroke_opacity = 0.26
    elif st == cur.LOCKED:
        stroke_opacity = 0.30

    glow = f'<path d="{sk.leaf_d(L * 1.15, Wd * 1.25)}" class="jt-halo" fill="{C["emerald"]}" fill-opacity=".0"/>' if st == cur.MASTERED else ""
    ring = ""
    if cur.is_current(state, lesson):
        ring = (f'<g transform="translate({x:.1f} {y:.1f}) rotate({deg:.1f})">'
                f'<path class="jt-pulse" d="{sk.leaf_d(L * 1.22, Wd * 1.4)}" transform="translate(0 {L * 0.09:.1f})" '
                f'fill="none" stroke="{C["gold"]}" stroke-width="2.4"/></g>')
    sel = ""
    if selected == key:
        sel = (f'<g transform="translate({x:.1f} {y:.1f}) rotate({deg:.1f})">'
               f'<path d="{sk.leaf_d(L * 1.16, Wd * 1.32)}" transform="translate(0 {L * 0.07:.1f})" fill="none" '
               f'stroke="{C["gold_pale"]}" stroke-width="2" stroke-dasharray="4 5"/></g>')

    shine = ""
    if prog >= 0.3:
        w2 = Wd / 2 * 1.33
        shine = (f'<path d="M0 0C{-w2:.1f} {-L * 0.2:.1f} {-w2:.1f} {-L * 0.68:.1f} 0 {-L:.1f}Z" fill="#FFFFFF" '
                 f'fill-opacity="{0.06 + 0.10 * prog:.2f}"/>')

    stem = (f'<path d="M{pos["stem"][0]:.1f} {pos["stem"][1]:.1f}L{x:.1f} {y:.1f}" stroke="{C["gold"]}" '
            f'stroke-width="3.2" stroke-linecap="round"/>')

    icon = ""
    if st == cur.LOCKED:
        icon = (f'<g transform="translate({cx:.1f} {cy:.1f})" fill="none" stroke="#DCEBF5" stroke-opacity=".75" stroke-width="2">'
                f'<rect x="-7" y="-2" width="14" height="11" rx="2.5" fill="#DCEBF5" fill-opacity=".18"/>'
                f'<path d="M-4.2 -2V-5.5a4.2 4.2 0 0 1 8.4 0V-2"/></g>')
    else:
        num_op = 0.55 if st == cur.SOON else 1
        icon = (f'<text x="{cx:.1f}" y="{cy:.1f}" dy=".36em" text-anchor="middle" class="jt-num" font-size="{26 * pos["scale"]:.0f}" '
                f'fill="{sty["number"]}" fill-opacity="{num_op}">{lesson.no}</text>')

    label = f"{unit.title} - الدرس {lesson.no}: {lesson.title}"
    pct = int(round(prog * 100))
    status_word = {cur.MASTERED: "متقن", cur.LEARNING: f"{pct}%", cur.OPEN: "مفتوح",
                   cur.LOCKED: "مغلق", cur.SOON: "قريباً"}[st]
    delay = 250 + idx * 70
    body = (
        f'<g class="{cls}" data-key="{key}">'
        f"<title>{escape(label)} ({status_word})</title>"
        f"{stem}{ring}"
        f'<g transform="translate({x:.1f} {y:.1f}) rotate({deg:.1f})">{glow}'
        f'<path class="jt-lf" d="{sk.leaf_d(L, Wd)}" fill="{sty["fill"]}" fill-opacity="{fill_opacity}" '
        f'stroke="{sty["stroke"]}" stroke-opacity="{stroke_opacity}" stroke-width="1.6"{dash} style="animation-delay:{delay}ms"/>'
        f'<path d="{sk.leaf_veins(L, Wd)}" fill="none" stroke="#FFFFFF" stroke-opacity="{sty["vein_opacity"] if st != cur.MASTERED else 0.22}" '
        f'stroke-width="1.1" stroke-linecap="round"/></g>'
        f"{sel}{icon}"
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{34 * pos["scale"]:.0f}" fill="transparent"/>'
        "</g>"
    )
    return body


def _medallion(unit: cur.Unit) -> str:
    c = BOUGHS[unit.no]["c"]
    x, y = sk.bez(*c, 0.07)
    return (
        f'<g transform="translate({x:.1f} {y:.1f})">'
        f'<circle r="19" fill="url(#jt-bark)" stroke="#6F4B12" stroke-width="2"/>'
        f'<circle r="14" fill="{C["ink"]}" fill-opacity=".92"/>'
        f'<text y="1" dy=".36em" text-anchor="middle" class="jt-num" font-size="19" fill="{C["gold_pale"]}">{unit.no}</text>'
        "</g>"
    )


def _scene(state, selected: str | None) -> str:
    out = [f'<svg class="jt-svg" viewBox="0 {TOP} {W} {H - TOP}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="شجرة المنهج: ورقة لكل درس">', _defs(), _sky(), _fireflies(), _ground(), _tree_wood()]
    idx = 0
    leaves = []
    for u in cur.UNITS:
        for pos in _leaf_positions(u):
            leaves.append(_leaf(u, pos, state, selected, idx))
            idx += 1
    out.extend(leaves)
    out.extend(_medallion(u) for u in cur.UNITS)
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------ mini UI
def _mini_leaf(progress: float, soon: bool = False) -> str:
    s = leaf_style(progress)
    so = 0.28 if soon else s["stroke_opacity"]
    dash = ' stroke-dasharray="3 3"' if soon else ""
    return (f'<svg viewBox="-16 -50 32 54" width="15" height="25" aria-hidden="true">'
            f'<path d="{sk.leaf_d(46, 24)}" fill="{s["fill"]}" fill-opacity="{s["fill_opacity"]}" stroke="{s["stroke"]}" '
            f'stroke-opacity="{so}" stroke-width="2"{dash}/></svg>')


def _units_legend(state) -> str:
    rows = []
    for u in cur.UNITS:
        pips, done = [], 0
        for l in u.lessons:
            st = cur.status(state, l)
            done += st == cur.MASTERED
            pips.append(_mini_leaf(cur.progress(state, l), soon=st in (cur.SOON, cur.LOCKED)))
        rows.append(
            f'<li class="jt-unit"><span class="jt-coin">{u.no}</span>'
            f'<span class="jt-unit-body"><b>{escape(u.title)}</b><span class="jt-pips">{"".join(pips)}</span></span>'
            f'<span class="jt-unit-count">{done}/{len(u.lessons)}</span></li>'
        )
    return f'<ul class="jt-units">{"".join(rows)}</ul>'


def _key_bar() -> str:
    return (
        '<div class="jt-key" aria-hidden="true"><span>لم تبدأ</span><i></i><span>متقنة</span></div>'
    )


def tree_html(state, selected: str | None = None) -> str:
    s = cur.summary(state)
    head = (
        '<div class="jt-tree-head"><div>'
        '<h2 class="jt-title">شجرة المنهج</h2>'
        '<p class="jt-sub">ورقة لكل درس في الكتاب. تخضرّ الورقة مع كل إجابة صحيحة.</p></div>'
        f'<div class="jt-count"><b>{s["mastered"]}</b><span>من {s["total"]} ورقة متقنة</span></div></div>'
    )
    return (f'<div class="jt-tree">{head}{_key_bar()}<div class="jt-scene">{_scene(state, selected)}</div>'
            f'{_units_legend(state)}</div>')


_MATH = re.compile(r"\[\[(.+?)\]\]")


def _rich(text: str) -> str:
    """Escape, then draw [[maths]] as an isolated left-to-right span inside the Arabic sentence."""
    return _MATH.sub(lambda m: f'<bdi class="jt-m" dir="ltr">{m.group(1)}</bdi>', escape(text))


def _concepts_block(key: str) -> str:
    items = cur.concepts_for(key)
    if not items:
        return ""
    lis = "".join(f"<li><b>{escape(c.title)}</b><span>{_rich(c.text)}</span></li>" for c in items)
    return f'<div class="jt-concepts"><h4>أهم مفاهيم الدرس</h4><ol>{lis}</ol></div>'


def detail_html(state, key: str, concepts: bool = True) -> str:
    found = cur.find_by_key(key)
    if not found:
        return ""
    unit, lesson = found
    st = cur.status(state, lesson)
    prog = cur.progress(state, lesson)
    pct = int(round(prog * 100))
    sk_id = lesson.skill
    a = state.attempts.get(sk_id, 0) if sk_id else 0
    c = state.correct.get(sk_id, 0) if sk_id else 0

    if st == cur.MASTERED:
        note = "أتقنت هذا الدرس، وورقتك خضراء بالكامل."
    elif st == cur.LEARNING:
        note = f"أجبت {c} إجابة صحيحة من {a} محاولة. تابع في ساحة الألغاز لتكتمل الورقة."
    elif st == cur.OPEN:
        note = "الدرس مفتوح لك. سيصل إليه المسار في ساحة الألغاز."
    elif st == cur.LOCKED:
        miss = "، ".join(cur.missing_prerequisites(state, lesson))
        note = f"يفتح بعد إتقان: {miss}."
    else:
        note = "الدرس قيد التجهيز، وسيظهر بنك أسئلته قريباً."

    chip = ""
    if cur.is_current(state, lesson):
        chip = '<span class="jt-chip-now">درسك الآن</span>'
    return (
        '<div class="jt-detail">'
        f'<div class="jt-detail-leaf">{_mini_leaf(prog, soon=st in (cur.SOON, cur.LOCKED))}</div>'
        '<div class="jt-detail-body">'
        f'<div class="jt-detail-unit">الوحدة {unit.no}: {escape(unit.title)}{chip}</div>'
        f'<h3>الدرس {lesson.no}: {escape(lesson.title)}</h3>'
        f'<div class="jt-bar"><span style="width:{pct}%"></span></div>'
        f'<p>{escape(note)}</p>{_concepts_block(key) if concepts else ""}</div></div>'
    )


TREE_CSS = f"""
.jt-tree {{ margin: 4px 0 8px; }}
.jt-tree-head {{ display:flex; align-items:flex-end; justify-content:space-between; gap:12px; margin-bottom:10px; }}
.jt-title {{ font-family:'Aref Ruqaa','Tajawal',serif !important; font-weight:700; font-size:34px; line-height:1.15;
  margin:0; padding:0; color:{C['gold']}; }}
.jt-sub {{ margin:4px 0 0; font-size:14px; color:{C['muted']}; }}
.jt-count {{ text-align:center; padding:6px 14px; border:1px solid rgba(230,190,106,.35); border-radius:14px;
  background:rgba(230,190,106,.07); white-space:nowrap; }}
.jt-count b {{ display:block; font-size:26px; line-height:1.1; color:{C['gold_pale']}; font-weight:800; }}
.jt-count span {{ font-size:12px; color:{C['muted']}; }}
.jt-key {{ display:flex; align-items:center; gap:8px; font-size:12px; color:{C['muted']}; margin:0 2px 8px; }}
.jt-key i {{ flex:0 0 110px; height:8px; border-radius:8px;
  background:linear-gradient(to left, rgba(217,247,236,.10), {C['emerald']}); border:1px solid rgba(255,255,255,.18); }}
.jt-scene {{ border-radius:22px; overflow:hidden; border:1px solid rgba(230,190,106,.28);
  box-shadow:0 18px 50px rgba(0,0,0,.45), inset 0 0 0 1px rgba(255,255,255,.03); line-height:0; }}
.jt-svg {{ display:block; width:100%; height:auto; direction:ltr; }}
.jt-svg text {{ direction:rtl; }}
.jt-ruq {{ font-family:'Aref Ruqaa','Tajawal',serif !important; }}
.jt-num {{ font-family:'Tajawal',sans-serif !important; font-weight:800; pointer-events:none; }}
.jt-leaf {{ cursor:pointer; }}
.jt-leaf .jt-lf {{ animation: jt-grow 1.5s ease-out both; transition: filter .2s; }}
.jt-leaf.jt-mastered .jt-lf {{ filter: drop-shadow(0 0 7px rgba(46,214,150,.55)); }}
.jt-leaf:hover .jt-lf {{ filter: drop-shadow(0 0 9px rgba(255,232,174,.55)); }}
.jt-pulse {{ transform-box: fill-box; transform-origin: 50% 100%; animation: jt-pulse 2.6s ease-in-out infinite; }}
@keyframes jt-grow {{ from {{ fill-opacity:.04; stroke-opacity:.18; }} }}
@keyframes jt-pulse {{ 0%,100% {{ opacity:.25; transform:scale(1); }} 50% {{ opacity:.95; transform:scale(1.05); }} }}
@media (prefers-reduced-motion: reduce) {{ .jt-leaf .jt-lf, .jt-pulse {{ animation:none; }} .jt-pulse {{ opacity:.8; }} }}
.jt-units {{ list-style:none; margin:14px 0 0; padding:0; display:grid; gap:8px; }}
.jt-unit {{ display:flex; align-items:center; gap:12px; padding:10px 12px; border-radius:14px;
  background:rgba(16,40,74,.72); border:1px solid rgba(157,178,200,.16); }}
.jt-coin {{ flex:0 0 34px; height:34px; border-radius:50%; display:grid; place-items:center; font-weight:800; font-size:17px;
  color:{C['ink']}; background:linear-gradient(135deg,{C['gold_pale']},{C['gold']} 45%,{C['gold_deep']}); }}
.jt-unit-body {{ flex:1; display:flex; flex-direction:column; gap:2px; min-width:0; }}
.jt-unit-body b {{ font-size:14px; font-weight:700; color:{C['text']}; }}
.jt-pips {{ display:flex; gap:5px; align-items:flex-end; }}
.jt-pips svg {{ display:block; }}
.jt-unit-count {{ font-weight:800; font-size:15px; color:{C['gold_pale']}; }}
.jt-detail {{ display:flex; gap:14px; align-items:flex-start; margin:10px 0 4px; padding:14px 16px; border-radius:18px;
  background:linear-gradient(135deg, rgba(23,55,99,.85), rgba(16,40,74,.85)); border:1px solid rgba(230,190,106,.3); }}
.jt-detail-leaf {{ flex:0 0 auto; padding-top:4px; }}
.jt-detail-leaf svg {{ width:26px; height:44px; }}
.jt-detail-body {{ flex:1; min-width:0; }}
.jt-detail-unit {{ font-size:12.5px; color:{C['muted']}; }}
.jt-detail h3 {{ margin:2px 0 10px; padding:0; font-size:19px; font-weight:800; color:{C['text']}; }}
.jt-detail p {{ margin:10px 0 0; font-size:14px; color:{C['muted']}; }}
.jt-bar {{ height:8px; border-radius:8px; background:rgba(255,255,255,.10); overflow:hidden; }}
.jt-bar span {{ display:block; height:100%; border-radius:8px; background:linear-gradient(to left,{C['emerald_deep']},{C['emerald']},#7CF0BE); }}
.jt-concepts {{ margin-top:14px; padding-top:12px; border-top:1px solid rgba(230,190,106,.22); }}
.jt-concepts h4 {{ margin:0 0 8px; padding:0; font-size:15px; font-weight:800; color:{C['gold']}; }}
.jt-concepts ol {{ margin:0; padding:0; list-style:none; counter-reset:jtc; display:grid; gap:8px; }}
.jt-concepts li {{ counter-increment:jtc; position:relative; padding:8px 42px 8px 10px; border-radius:12px;
  background:rgba(8,20,40,.38); border:1px solid rgba(157,178,200,.14); }}
.jt-concepts li::before {{ content:counter(jtc); position:absolute; right:10px; top:9px; width:22px; height:22px; border-radius:50%;
  display:grid; place-items:center; font-size:12px; font-weight:800; color:{C['ink']};
  background:linear-gradient(135deg,{C['gold_pale']},{C['gold']}); }}
.jt-concepts li b {{ display:block; font-size:14px; color:{C['text']}; margin-bottom:2px; }}
.jt-concepts li span {{ font-size:13.5px; line-height:1.75; color:{C['muted']}; }}
.jt-m {{ direction:ltr; unicode-bidi:isolate; color:{C['gold_pale']}; font-weight:700; white-space:nowrap; }}
.jt-chip-now {{ margin-inline-start:8px; padding:1px 8px; border-radius:20px; background:{C['gold']}; color:{C['ink']};
  font-weight:800; font-size:11.5px; }}
"""
