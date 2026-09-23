"""
Everything the avatar can wear, plus the shop catalog.

Drawing functions return SVG fragments in the 240x240 avatar space (head centre ~ (120,110),
shoulders at y ~ 178, hat line at y ~ 84).  They rely on gradients / patterns declared by
avatar._defs():  {u}-goldf {u}-em {u}-coat {u}-suit {u}-lens {u}-emb {u}-shr {u}-shb.

Item ids that already existed in the shop keep their names (shirtCrewNeck, blazerAndShirt, overall,
hat, winterHat1, prescription02, sunglasses) so saved gami_state keeps working.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

import svgkit as sk
from theme import PALETTE as C, mix

BODY = "M22 244C26 198 72 178 120 178C168 178 214 198 218 244Z"


def _dk(c, t=0.28): return mix(c, "#000000", t)
def _lt(c, t=0.45): return mix(c, "#FFFFFF", t)


# ============================================================ CLOTHING
def _tee(u, color):
    d, l = _dk(color), _lt(color)
    return (f'<path d="{BODY}" fill="{color}"/>'
            f'<path d="M40 214Q58 196 74 190M200 214Q182 196 166 190" fill="none" stroke="{d}" stroke-opacity=".3" stroke-width="2.5" stroke-linecap="round"/>'
            f'<path d="M96 178C104 198 136 198 144 178" fill="none" stroke="{d}" stroke-width="7" stroke-linecap="round"/>'
            f'<path d="M98 179C106 195 134 195 142 179" fill="none" stroke="{l}" stroke-opacity=".55" stroke-width="2" stroke-linecap="round"/>')


def _tee_default(u):
    leaf = f'<g transform="translate(154 212) rotate(24)"><path d="{sk.leaf_d(18, 9)}" fill="url(#{u}-goldf)"/></g>'
    return (f'<path d="{BODY}" fill="url(#{u}-em)"/>'
            f'<path d="M96 178C104 198 136 198 144 178" fill="none" stroke="#0A7A52" stroke-width="7" stroke-linecap="round"/>'
            f'<path d="M98 179C106 195 134 195 142 179" fill="none" stroke="#7CF0BE" stroke-opacity=".55" stroke-width="2" stroke-linecap="round"/>{leaf}')


def _hoodie(u, color):
    d, l = _dk(color, .3), _lt(color, .4)
    return (f'<path d="M72 182C64 150 92 136 120 136C148 136 176 150 168 182Z" fill="{d}"/>'
            f'<path d="{BODY}" fill="{color}"/>'
            f'<path d="M22 244C26 198 72 178 120 178" fill="none" stroke="{l}" stroke-opacity=".25" stroke-width="3"/>'
            f'<path d="M86 178C90 158 150 158 154 178C150 200 90 200 86 178Z" fill="{d}"/>'
            f'<path d="M107 190L105 216M133 190L135 216" stroke="#F2F4F8" stroke-width="3" stroke-linecap="round"/>'
            f'<circle cx="105" cy="218" r="3" fill="#F2F4F8"/><circle cx="135" cy="218" r="3" fill="#F2F4F8"/>'
            f'<path d="M70 244L82 222H158L170 244Z" fill="{_dk(color, .12)}" stroke="{d}" stroke-width="1.6"/>')


def _jacket_denim(u, color="#3E6DA8"):
    d, l = _dk(color, .3), _lt(color, .35)
    return (f'<path d="{BODY}" fill="{color}"/>'
            f'<path d="M100 178L120 238L140 178C130 187 110 187 100 178Z" fill="#F3F6FA"/>'
            f'<path d="M100 178L82 200L106 216L120 238L120 196Z" fill="{_lt(color, .12)}" stroke="{d}" stroke-width="1.6" stroke-linejoin="round"/>'
            f'<path d="M140 178L158 200L134 216L120 238L120 196Z" fill="{_lt(color, .12)}" stroke="{d}" stroke-width="1.6" stroke-linejoin="round"/>'
            f'<rect x="54" y="212" width="26" height="22" rx="3" fill="none" stroke="{l}" stroke-width="1.6" stroke-dasharray="3 3"/>'
            f'<rect x="160" y="212" width="26" height="22" rx="3" fill="none" stroke="{l}" stroke-width="1.6" stroke-dasharray="3 3"/>'
            f'<path d="M120 238V244" stroke="{d}" stroke-width="2"/>'
            f'<circle cx="66" cy="214" r="2.4" fill="url(#{u}-goldf)"/><circle cx="174" cy="214" r="2.4" fill="url(#{u}-goldf)"/>')


def _jacket_bomber(u, color="#5B6B3A"):
    d, l = _dk(color, .3), _lt(color, .35)
    stripes = "".join(f'<path d="M{x} {170 + abs(x - 120) * 0.16:.0f}V{198 - abs(x - 120) * 0.12:.0f}" stroke="{_dk(color, .45)}" stroke-width="2" opacity=".55"/>' for x in range(94, 150, 8))
    return (f'<path d="{BODY}" fill="{color}"/>'
            f'<path d="M22 244C24 228 30 216 38 208L66 244Z" fill="{d}" opacity=".55"/><path d="M218 244C216 228 210 216 202 208L174 244Z" fill="{d}" opacity=".55"/>'
            f'<path d="M120 196V244" stroke="url(#{u}-goldf)" stroke-width="3"/>'
            f'<path d="M90 178C96 202 144 202 150 178C146 168 94 168 90 178Z" fill="{d}"/>{stripes}'
            f'<path d="M92 179C98 198 142 198 148 179" fill="none" stroke="#E98B2A" stroke-width="3" stroke-linecap="round"/>'
            f'<path d="M30 226Q44 210 62 206" fill="none" stroke="{l}" stroke-opacity=".3" stroke-width="3" stroke-linecap="round"/>')


def _jacket_puffer(u, color):
    d, l = _dk(color, .3), _lt(color, .4)
    quilt = "".join(f'<path d="M{24 - k} {204 + k * 20}Q120 {188 + k * 20} {216 + k} {204 + k * 20}" fill="none" stroke="{d}" stroke-opacity=".6" stroke-width="2"/>' for k in range(0, 3))
    return (f'<path d="{BODY}" fill="{color}"/>{quilt}'
            f'<path d="M22 244C26 198 72 178 120 178" fill="none" stroke="{l}" stroke-opacity=".3" stroke-width="3"/>'
            f'<path d="M80 168C90 204 150 204 160 168L152 164C142 178 98 178 88 164Z" fill="{d}"/>'
            f'<path d="M84 170C94 198 146 198 156 170" fill="none" stroke="{l}" stroke-opacity=".5" stroke-width="2"/>'
            f'<path d="M120 190V244" stroke="#DDE6F0" stroke-width="3"/><rect x="117" y="196" width="6" height="9" rx="2" fill="url(#{u}-goldf)"/>')


def _jacket_leather(u, color="#25262C"):
    l = "#3A3C46"
    return (f'<path d="{BODY}" fill="{color}"/>'
            f'<path d="M100 178L120 232L140 178C130 187 110 187 100 178Z" fill="#E7ECF2"/>'
            f'<path d="M98 178L74 212L104 228L120 196Z" fill="{l}" stroke="#0F1014" stroke-width="1.6" stroke-linejoin="round"/>'
            f'<path d="M142 178L166 212L136 228L120 196Z" fill="{l}" stroke="#0F1014" stroke-width="1.6" stroke-linejoin="round"/>'
            f'<path d="M104 232L120 244M136 232L120 244" stroke="#0F1014" stroke-width="2"/>'
            f'<path d="M36 220Q48 204 64 198M176 200Q190 206 200 218" fill="none" stroke="#FFFFFF" stroke-opacity=".18" stroke-width="3" stroke-linecap="round"/>'
            f'<circle cx="86" cy="206" r="2.6" fill="url(#{u}-goldf)"/><circle cx="154" cy="206" r="2.6" fill="url(#{u}-goldf)"/>')


def _dishdasha(u):
    return (f'<path d="{BODY}" fill="#F5F2E9"/>'
            f'<path d="M22 244C26 198 72 178 120 178" fill="none" stroke="#FFFFFF" stroke-opacity=".7" stroke-width="3"/>'
            f'<path d="M98 178C106 196 134 196 142 178L142 188C134 204 106 204 98 188Z" fill="#E7E2D3" stroke="#CFC8B4" stroke-width="1.4"/>'
            f'<path d="M120 200V244" stroke="#CFC8B4" stroke-width="2"/>'
            f'<circle cx="120" cy="208" r="2.4" fill="#B49F70"/><circle cx="120" cy="222" r="2.4" fill="#B49F70"/><circle cx="120" cy="236" r="2.4" fill="#B49F70"/>'
            f'<path d="M152 214H172V236H152Z" fill="none" stroke="#D8D2C0" stroke-width="1.6"/>'
            f'<path d="M40 218Q56 200 72 194M200 218Q184 200 168 194" fill="none" stroke="#D8D2C0" stroke-width="2" stroke-linecap="round"/>')


def _thobe(u, color):
    d = _dk(color, .35)
    return (f'<path d="{BODY}" fill="{color}"/>'
            f'<path d="M92 178L148 178L160 244L80 244Z" fill="url(#{u}-emb)" stroke="url(#{u}-goldf)" stroke-width="2.4" stroke-linejoin="round"/>'
            f'<path d="M24 232Q30 212 58 204L66 244L24 244Z" fill="url(#{u}-emb)" stroke="url(#{u}-goldf)" stroke-width="2"/>'
            f'<path d="M216 232Q210 212 182 204L174 244L216 244Z" fill="url(#{u}-emb)" stroke="url(#{u}-goldf)" stroke-width="2"/>'
            f'<path d="M96 178C104 198 136 198 144 178" fill="none" stroke="{d}" stroke-width="7" stroke-linecap="round"/>'
            f'<path d="M98 179C106 195 134 195 142 179" fill="none" stroke="url(#{u}-goldf)" stroke-width="2.4" stroke-linecap="round"/>')


def _jersey(u):
    return (f'<path d="{BODY}" fill="#C8202F"/>'
            f'<path d="M22 244C24 226 30 214 38 206L52 244Z" fill="#FFFFFF" opacity=".92"/><path d="M218 244C216 226 210 214 202 206L188 244Z" fill="#FFFFFF" opacity=".92"/>'
            f'<path d="M94 178L120 208L146 178" fill="none" stroke="#FFFFFF" stroke-width="7" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<text x="120" y="238" text-anchor="middle" font-family="Tajawal,sans-serif" font-weight="800" font-size="24" fill="#FFFFFF">10</text>'
            f'<circle cx="152" cy="208" r="5.5" fill="url(#{u}-goldf)"/>')


# ---- jobs
def _doctor(u):
    return (
        f'<path d="{BODY}" fill="url(#{u}-coat)"/>'
        f'<path d="M96 178C102 210 112 226 120 232C128 226 138 210 144 178C134 186 106 186 96 178Z" fill="#2FA7A0"/>'
        f'<path d="M96 178L86 214L112 232L120 214Z" fill="#FFFFFF" stroke="#C6D3E0" stroke-width="1.5"/>'
        f'<path d="M144 178L154 214L128 232L120 214Z" fill="#FFFFFF" stroke="#C6D3E0" stroke-width="1.5"/>'
        f'<path d="M104 182C98 206 106 224 118 226" fill="none" stroke="#1F2C3B" stroke-width="3" stroke-linecap="round"/>'
        f'<path d="M136 182C142 206 134 224 122 226" fill="none" stroke="#1F2C3B" stroke-width="3" stroke-linecap="round"/>'
        f'<circle cx="120" cy="229" r="5" fill="url(#{u}-goldf)" stroke="#8A6420" stroke-width="1"/>'
        f'<rect x="164" y="208" width="26" height="22" rx="4" fill="#EAF1F7" stroke="#C6D3E0" stroke-width="1.5"/>'
        f'<rect x="171" y="200" width="3" height="14" rx="1.5" fill="{C["rose"]}"/>')


def _nurse(u):
    return (f'<path d="{BODY}" fill="#2FA7A0"/>'
            f'<path d="M94 178L120 216L146 178" fill="#1E8A84" stroke="#EAFBF8" stroke-width="5" stroke-linejoin="round"/>'
            f'<rect x="150" y="210" width="24" height="20" rx="3" fill="none" stroke="#1E8A84" stroke-width="2"/>'
            f'<path d="M66 232L82 232" stroke="#EAFBF8" stroke-width="3" stroke-linecap="round"/>'
            f'<rect x="60" y="208" width="22" height="12" rx="3" fill="#FFFFFF"/><path d="M64 214H78" stroke="#2FA7A0" stroke-width="2"/>')


def _engineer(u):
    stripe = '<path d="{d}" fill="#EAF0F6" opacity=".92"/>'
    return (f'<path d="{BODY}" fill="#F1F5FA"/>'
            f'<path d="M100 178L120 200L140 178" fill="none" stroke="#C6D3E0" stroke-width="5" stroke-linejoin="round"/>'
            f'<path d="M62 186C80 180 98 180 108 184L110 244L42 244C44 220 50 200 62 186Z" fill="#FF8A1F"/>'
            f'<path d="M178 186C160 180 142 180 132 184L130 244L198 244C196 220 190 200 178 186Z" fill="#FF8A1F"/>'
            + stripe.format(d="M47 214L109 218L109 226L45 222Z") + stripe.format(d="M193 214L131 218L131 226L195 222Z")
            + stripe.format(d="M44 232L109 234L110 242L42 242Z") + stripe.format(d="M196 232L131 234L130 242L198 242Z"))


def _pilot(u):
    gold = f"url(#{u}-goldf)"
    ep = (f'<path d="M48 196L78 186L84 198L54 210Z" fill="#141F38"/><path d="M52 198L78 190M54 204L80 195" stroke="{gold}" stroke-width="2.4"/>'
          f'<path d="M192 196L162 186L156 198L186 210Z" fill="#141F38"/><path d="M188 198L162 190M186 204L160 195" stroke="{gold}" stroke-width="2.4"/>')
    return (f'<path d="{BODY}" fill="#1B2A4A"/>'
            f'<path d="M100 178L120 232L140 178C130 187 110 187 100 178Z" fill="#F3F6FA"/>'
            f'<path d="M98 178L82 208L110 226L120 196Z" fill="#12203B"/><path d="M142 178L158 208L130 226L120 196Z" fill="#12203B"/>'
            f'<path d="M116 186H124L127 222L120 230L113 222Z" fill="#101318"/>{ep}'
            f'<path d="M146 216Q156 206 172 210Q162 215 152 219Z" fill="{gold}"/><circle cx="159" cy="214" r="3" fill="{gold}"/>')


def _officer(u):
    gold = f"url(#{u}-goldf)"
    star = lambda cx, cy: f'<path d="M{cx} {cy - 4}L{cx + 1.2} {cy - 1.2}L{cx + 4} {cy - 1}L{cx + 1.8} {cy + .9}L{cx + 2.4} {cy + 3.8}L{cx} {cy + 2.2}L{cx - 2.4} {cy + 3.8}L{cx - 1.8} {cy + .9}L{cx - 4} {cy - 1}L{cx - 1.2} {cy - 1.2}Z" fill="{gold}"/>'
    return (f'<path d="{BODY}" fill="#3E5A3A"/>'
            f'<path d="M100 178L120 232L140 178C130 187 110 187 100 178Z" fill="#E9E0C8"/>'
            f'<path d="M98 178L80 210L110 228L120 196Z" fill="#2E4530" stroke="#1F3121" stroke-width="1.4"/><path d="M142 178L160 210L130 228L120 196Z" fill="#2E4530" stroke="#1F3121" stroke-width="1.4"/>'
            f'<path d="M116 188H124L126 222L120 228L114 222Z" fill="#5A1F1F"/>'
            f'<path d="M46 198L78 187L84 199L52 211Z" fill="#26392A" stroke="{gold}" stroke-width="1.6"/>{star(66, 200)}'
            f'<path d="M194 198L162 187L156 199L188 211Z" fill="#26392A" stroke="{gold}" stroke-width="1.6"/>{star(174, 200)}'
            f'<rect x="146" y="208" width="6" height="4" fill="#C8202F"/><rect x="152" y="208" width="6" height="4" fill="#1FA37A"/><rect x="158" y="208" width="6" height="4" fill="#E6BE6A"/>')


def _chef(u):
    btn = "".join(f'<circle cx="{x}" cy="{y}" r="2.8" fill="#2B2F3A"/>' for x in (106, 134) for y in (202, 216, 230))
    return (f'<path d="{BODY}" fill="#FBFBFD"/>'
            f'<path d="M120 190V244" stroke="#D5DCE6" stroke-width="2"/>'
            f'<path d="M22 244C26 198 72 178 120 178" fill="none" stroke="#E4EAF2" stroke-width="3"/>'
            f'<path d="M98 178C106 196 134 196 142 178L120 210Z" fill="#D9463A"/>{btn}')


def _firefighter(u):
    return (f'<path d="{BODY}" fill="#333844"/>'
            f'<path d="M24 228Q120 208 216 228L216 238Q120 218 24 238Z" fill="#E8D44D"/>'
            f'<path d="M32 208Q120 190 208 208L206 214Q120 198 34 214Z" fill="#E8D44D" opacity=".9"/>'
            f'<path d="M84 172C90 200 150 200 156 172C146 166 94 166 84 172Z" fill="#E8D44D"/>'
            f'<path d="M120 192V244" stroke="#8A93A6" stroke-width="3"/><rect x="112" y="200" width="16" height="6" rx="2" fill="#8A93A6"/><rect x="112" y="214" width="16" height="6" rx="2" fill="#8A93A6"/>')


def _teacher(u):
    return (f'<path d="{BODY}" fill="#7A2E3E"/>'
            f'<path d="M100 178L120 232L140 178C130 187 110 187 100 178Z" fill="#F6F8FB"/>'
            f'<path d="M98 178L80 210L108 228L120 196Z" fill="#652535" stroke="#4B1826" stroke-width="1.4"/><path d="M142 178L160 210L132 228L120 196Z" fill="#652535" stroke="#4B1826" stroke-width="1.4"/>'
            f'<path d="M160 208l3 5 6 .8-4.4 4 1.2 6-5.8-3-5.8 3 1.2-6-4.4-4 6-.8Z" fill="url(#{u}-goldf)"/>'
            f'<rect x="58" y="212" width="24" height="18" rx="2" fill="#C9963A"/><path d="M58 218H82" stroke="#7A5A1E" stroke-width="1.6"/>')


def _astronaut(u):
    return (
        f'<path d="{BODY}" fill="url(#{u}-suit)"/>'
        f'<path d="M22 244C24 220 34 204 50 194L62 244Z" fill="{C["gold"]}" fill-opacity=".9"/>'
        f'<path d="M218 244C216 220 206 204 190 194L178 244Z" fill="{C["gold"]}" fill-opacity=".9"/>'
        f'<rect x="96" y="204" width="48" height="30" rx="8" fill="#12305A" stroke="{C["gold"]}" stroke-width="2"/>'
        f'<circle cx="108" cy="219" r="4.2" fill="{C["emerald"]}"/><circle cx="120" cy="219" r="4.2" fill="{C["rose"]}"/>'
        f'<circle cx="132" cy="219" r="4.2" fill="{C["gold_pale"]}"/>'
        f'<circle cx="60" cy="208" r="11" fill="{C["rose_deep"]}" stroke="{C["gold_pale"]}" stroke-width="2"/>'
        f'<path d="M60 201L62.2 206.3L68 206.8L63.6 210.6L65 216L60 213L55 216L56.4 210.6L52 206.8L57.8 206.3Z" fill="{C["gold_pale"]}"/>'
        f'<path d="M92 179C100 196 140 196 148 179" fill="none" stroke="url(#{u}-goldf)" stroke-width="11" stroke-linecap="round"/>'
        f'<path d="M92 179C100 196 140 196 148 179" fill="none" stroke="#FFFFFF" stroke-opacity=".35" stroke-width="3" stroke-linecap="round"/>')


def _farmer(u):
    plaid = "".join(f'<path d="M{x} 180V244" stroke="#8E2A25" stroke-width="3" opacity=".45"/>' for x in range(30, 220, 16))
    plaid += "".join(f'<path d="M22 {y}H218" stroke="#8E2A25" stroke-width="3" opacity=".35"/>' for y in (204, 224))
    return (f'<path d="{BODY}" fill="#C6463D"/>{plaid}'
            f'<path d="M96 178C104 194 136 194 144 178" fill="none" stroke="#8E2A25" stroke-width="6" stroke-linecap="round"/>'
            f'<path d="M86 214H154L152 244H88Z" fill="#3E6DA8" stroke="#2C5185" stroke-width="1.6"/>'
            f'<path d="M92 190L88 214M148 190L152 214" stroke="#3E6DA8" stroke-width="10" stroke-linecap="round"/>'
            f'<circle cx="90" cy="214" r="3.4" fill="url(#{u}-goldf)"/><circle cx="150" cy="214" r="3.4" fill="url(#{u}-goldf)"/>'
            f'<rect x="108" y="222" width="24" height="14" rx="2" fill="none" stroke="#2C5185" stroke-width="1.6"/>')


# ============================================================ HEADWEAR
def _cap(u, color="#173763"):
    d = _dk(color, .3)
    return (f'<path d="M71 82C68 38 98 26 120 26C142 26 172 38 169 82C150 76 90 76 71 82Z" fill="{color}"/>'
            f'<path d="M120 26C112 44 110 62 112 77M120 26C128 44 130 62 128 77" fill="none" stroke="{d}" stroke-width="2"/>'
            f'<path d="M92 34C104 28 118 26 130 27" fill="none" stroke="{_lt(color, .4)}" stroke-opacity=".6" stroke-width="3" stroke-linecap="round"/>'
            f'<circle cx="120" cy="26" r="4.5" fill="url(#{u}-goldf)"/>'
            f'<path d="M68 80C96 92 144 92 172 80C180 92 158 102 120 102C82 102 60 92 68 80Z" fill="{d}"/>'
            f'<path d="M76 84C100 94 140 94 164 84" fill="none" stroke="{C["gold"]}" stroke-width="2.2" stroke-linecap="round"/>')


def _beanie(u, color):
    d = _dk(color, .3)
    knit = "".join(f'<path d="M{x} 78V96" stroke="{_dk(color, .45)}" stroke-opacity=".55" stroke-width="2"/>' for x in range(80, 165, 10))
    return (f'<path d="M72 84C68 40 94 26 120 26C146 26 172 40 168 84Z" fill="{color}"/>'
            f'<path d="M92 44C102 36 116 32 130 33" fill="none" stroke="{_lt(color, .55)}" stroke-opacity=".7" stroke-width="3" stroke-linecap="round"/>'
            f'<rect x="66" y="76" width="108" height="22" rx="10" fill="{d}"/>{knit}'
            f'<rect x="66" y="76" width="108" height="6" rx="3" fill="#FFFFFF" fill-opacity=".14"/>'
            f'<circle cx="120" cy="22" r="12" fill="{_lt(color, .6)}"/><circle cx="116" cy="18" r="4" fill="#FFFFFF" fill-opacity=".55"/>')


def _hardhat(u):
    return (f'<path d="M70 86C66 42 96 28 120 28C144 28 174 42 170 86Z" fill="#F5C518"/>'
            f'<path d="M108 29C112 27 128 27 132 29L132 86H108Z" fill="#E0AC0C"/>'
            f'<path d="M84 40C96 33 110 30 120 30" fill="none" stroke="#FFF3B0" stroke-opacity=".7" stroke-width="3" stroke-linecap="round"/>'
            f'<path d="M62 86C90 96 150 96 178 86C182 95 160 104 120 104C80 104 58 95 62 86Z" fill="#D9A80F"/>'
            f'<rect x="112" y="60" width="16" height="12" rx="3" fill="#FFFFFF" opacity=".9"/>')


def _pilot_cap(u):
    return (f'<g transform="translate(0 -9)">' +
            f'<path d="M72 90C66 52 96 42 120 42C144 42 174 52 168 90Z" fill="#1B2A4A"/>'
            f'<path d="M64 62C88 32 152 32 176 62C152 52 88 52 64 62Z" fill="#26386A"/>'
            f'<path d="M70 82C96 94 144 94 170 82L170 94C144 106 96 106 70 94Z" fill="#0F1A33"/>'
            f'<path d="M72 84C98 95 142 95 168 84" fill="none" stroke="#F3F6FA" stroke-width="2"/>'
            f'<path d="M86 100C102 112 138 112 154 100L150 108C136 120 104 120 90 108Z" fill="#0B0F1A"/>'
            f'<circle cx="120" cy="80" r="7.5" fill="url(#{u}-goldf)" stroke="#8A6420" stroke-width="1"/>'
            f'<path d="M100 78Q110 72 116 79M140 78Q130 72 124 79" fill="none" stroke="url(#{u}-goldf)" stroke-width="2.4" stroke-linecap="round"/></g>')


def _officer_cap(u):
    gold = f"url(#{u}-goldf)"
    return (f'<g transform="translate(0 -9)">' +
            f'<path d="M74 88C70 46 98 36 120 36C142 36 170 46 166 88Z" fill="#3E5A3A"/>'
            f'<path d="M62 62C88 32 152 32 178 62C152 52 88 52 62 62Z" fill="#4A6A45"/>'
            f'<path d="M70 82C96 94 144 94 170 82L170 94C144 106 96 106 70 94Z" fill="#2A3F28"/>'
            f'<path d="M72 84C98 96 142 96 168 84" fill="none" stroke="{gold}" stroke-width="2.4"/>'
            f'<path d="M84 100C102 114 138 114 156 100L152 110C136 122 104 122 88 110Z" fill="#141414"/>'
            f'<path d="M86 101C104 114 136 114 154 101" fill="none" stroke="{gold}" stroke-width="2"/>'
            f'<path d="M120 60l3.4 7 7.6 1.1-5.5 5.4 1.3 7.6-6.8-3.6-6.8 3.6 1.3-7.6-5.5-5.4 7.6-1.1Z" fill="{gold}" stroke="#8A6420" stroke-width=".8"/></g>')


def _chef_hat(u):
    puff = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#FFFFFF" stroke="#DDE4EE" stroke-width="1.4"/>'
                   for x, y, r in ((92, 46, 20), (148, 46, 20), (120, 34, 24), (106, 54, 18), (134, 54, 18)))
    return (puff +
            f'<path d="M74 72C74 56 166 56 166 72L166 92C166 78 74 78 74 92Z" fill="#FFFFFF" stroke="#DDE4EE" stroke-width="1.4"/>'
            f'<path d="M80 80C100 86 140 86 160 80" fill="none" stroke="#E6ECF4" stroke-width="2"/>')


def _fire_helmet(u):
    return (f'<g transform="translate(0 -7)">' +
            f'<path d="M68 90C66 46 96 30 120 30C144 30 174 46 172 90Z" fill="#C8202F"/>'
            f'<path d="M120 30V90" stroke="#8E1520" stroke-width="5"/><path d="M104 32V90M136 32V90" stroke="#8E1520" stroke-width="2" opacity=".6"/>'
            f'<path d="M84 44C96 36 108 33 118 33" fill="none" stroke="#FF8A8A" stroke-opacity=".6" stroke-width="3" stroke-linecap="round"/>'
            f'<path d="M58 90C90 102 150 102 182 90C188 100 162 112 120 112C78 112 52 100 58 90Z" fill="#8E1520"/>'
            f'<path d="M108 52H132V68C132 76 120 82 120 82C120 82 108 76 108 68Z" fill="url(#{u}-goldf)" stroke="#8A6420" stroke-width="1.2"/></g>')


def _nurse_cap(u):
    return (f'<path d="M80 88C78 58 162 58 160 88L156 96C132 88 108 88 84 96Z" fill="#FFFFFF" stroke="#D5DEE9" stroke-width="1.6"/>'
            f'<path d="M116 66h8v18h-8zM111 71h18v8h-18z" fill="#D64545"/>')


def _scrub_cap(u):
    return (f'<path d="M73 92C68 44 96 32 120 32C144 32 172 44 167 92C150 80 90 80 73 92Z" fill="#2FA7A0"/>'
            f'<path d="M88 46C100 38 116 35 130 36" fill="none" stroke="#8FE0DA" stroke-opacity=".7" stroke-width="3" stroke-linecap="round"/>'
            f'<path d="M73 92C90 82 150 82 167 92" fill="none" stroke="#1E8A84" stroke-width="5" stroke-linecap="round"/>')


def _straw_hat(u):
    weave = "".join(f'<path d="M{x} 44Q{x + 2} 62 {x} 80" fill="none" stroke="#B98A2C" stroke-opacity=".5" stroke-width="1.6"/>' for x in range(90, 152, 9))
    return (f'<path d="M30 86C58 66 182 66 210 86C204 104 36 104 30 86Z" fill="#E2B85A" stroke="#B98A2C" stroke-width="1.6"/>'
            f'<path d="M76 84C74 50 98 38 120 38C142 38 166 50 164 84Z" fill="#EBC46A"/>{weave}'
            f'<path d="M75 74C100 84 140 84 165 74L164 86C140 96 100 96 76 86Z" fill="#8A5A2B"/>')


def _astro_helmet(u):
    return (f'<circle cx="120" cy="112" r="70" fill="#BFE6FF" fill-opacity=".14" stroke="#EAF2FA" stroke-width="7"/>'
            f'<circle cx="120" cy="112" r="70" fill="none" stroke="{C["gold"]}" stroke-opacity=".55" stroke-width="1.5"/>'
            f'<path d="M78 70C92 52 118 46 140 52" fill="none" stroke="#FFFFFF" stroke-opacity=".7" stroke-width="5" stroke-linecap="round"/>'
            f'<ellipse cx="120" cy="184" rx="58" ry="12" fill="none" stroke="#EAF2FA" stroke-width="7"/>')


def _hijab(u, color):
    d, l = _dk(color, .25), _lt(color, .4)
    outer = "M120 28C160 28 188 60 186 112C185 142 194 168 200 194C186 208 160 212 120 212C80 212 54 208 40 194C46 168 55 142 54 112C52 60 80 28 120 28Z"
    hole = "M79 108C79 82 96 66 120 66C144 66 161 82 161 108C161 140 146 166 120 168C94 166 79 140 79 108Z"
    return (f'<path d="{outer} {hole}" fill="{color}" fill-rule="evenodd"/>'
            f'<path d="{hole}" fill="none" stroke="{d}" stroke-width="3" stroke-linejoin="round"/>'
            f'<path d="M70 56C84 42 100 36 118 35" fill="none" stroke="{l}" stroke-opacity=".7" stroke-width="3.5" stroke-linecap="round"/>'
            f'<path d="M60 128C64 156 58 180 50 196M180 128C176 156 182 180 190 196" fill="none" stroke="{d}" stroke-opacity=".4" stroke-width="2.4" stroke-linecap="round"/>'
            f'<path d="M72 190C100 204 140 204 168 190" fill="none" stroke="{d}" stroke-opacity=".38" stroke-width="2.4" stroke-linecap="round"/>')


def _coin_scarf(u):
    color, d = "#F6EFE0", "#CDBB90"
    outer = "M120 28C160 28 188 60 186 112C185 142 194 168 200 194C186 208 160 212 120 212C80 212 54 208 40 194C46 168 55 142 54 112C52 60 80 28 120 28Z"
    hole = "M79 108C79 82 96 66 120 66C144 66 161 82 161 108C161 140 146 166 120 168C94 166 79 140 79 108Z"
    coin = lambda x, y, r: (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="url(#{u}-goldf)" stroke="#8A6420" stroke-width=".9"/>'
                            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * .58:.1f}" fill="none" stroke="#8A6420" stroke-opacity=".55" stroke-width=".9"/>')
    row = ""
    for k in range(9):                                            # a row of gold coins above the forehead
        x = 84 + k * 9
        y = 108 - 44 * math.sqrt(max(0.0, 1 - ((x - 120) / 43) ** 2)) - 6
        row += coin(x, y, 5.6)
    side = "".join(coin(x, y, 4.8) for x in (63, 177) for y in (120, 134, 148, 162, 176))
    return (f'<path d="{outer} {hole}" fill="{color}" fill-rule="evenodd"/>'
            f'<path d="M60 128C64 156 58 180 50 196M180 128C176 156 182 180 190 196" fill="none" stroke="{d}" stroke-opacity=".55" stroke-width="2.4" stroke-linecap="round"/>'
            f'<path d="{hole}" fill="none" stroke="#A5242C" stroke-width="3.6" stroke-linejoin="round"/>'
            f'<path d="M44 194C70 208 170 208 196 194" fill="none" stroke="#A5242C" stroke-width="5" stroke-linecap="round"/>'
            f'<path d="M50 198C74 210 166 210 190 198" fill="none" stroke="url(#{u}-goldf)" stroke-width="1.8" stroke-dasharray="2 5" stroke-linecap="round"/>'
            f'{row}{side}')


def _shemagh(u, pat):
    outline = ("M40 206C48 174 58 142 58 110C56 60 82 30 120 30C158 30 184 60 182 110C182 142 192 174 200 206"
               "L160 206C158 178 156 158 152 146C160 132 162 122 162 108C162 82 144 66 120 66C96 66 78 82 78 108"
               "C78 122 80 132 88 146C84 158 82 178 80 206Z")
    fringe = "".join(f'<path d="M{x} 206V213" stroke="#1B1B1B" stroke-width="2"/>' for x in list(range(42, 80, 6)) + list(range(162, 200, 6)))
    return (f'<path d="{outline}" fill="url(#{u}-{pat})" stroke="#1B1B1B" stroke-opacity=".55" stroke-width="1.6" stroke-linejoin="round"/>{fringe}'
            f'<path d="M62 78C74 50 166 50 178 78" fill="none" stroke="#111" stroke-width="8" stroke-linecap="round"/>'
            f'<path d="M64 88C76 62 164 62 176 88" fill="none" stroke="#111" stroke-width="8" stroke-linecap="round"/>'
            f'<path d="M70 70C90 54 140 52 166 66" fill="none" stroke="#FFFFFF" stroke-opacity=".22" stroke-width="2" stroke-linecap="round"/>')


# ============================================================ NECK (scarves)
def _scarf(u, color, stripe=None):
    d = _dk(color, .25)
    st = ""
    if stripe:
        st = "".join(f'<path d="M{x} 166L{x - 3} 200" stroke="{stripe}" stroke-width="4" opacity=".9"/>' for x in range(92, 150, 12))
    return (f'<path d="M84 162C92 182 148 182 156 162L164 184C146 204 94 204 76 184Z" fill="{color}"/>{st}'
            f'<path d="M84 162C92 182 148 182 156 162" fill="none" stroke="{_lt(color, .4)}" stroke-opacity=".5" stroke-width="2.4"/>'
            f'<path d="M136 190L148 240L168 236L158 188Z" fill="{d}"/>'
            f'<path d="M140 220L165 216M142 230L166 226" stroke="{_lt(color, .35)}" stroke-width="2" opacity=".8"/>')


# ============================================================ GLASSES
def _glasses_round(u):
    return (f'<g fill="#BFE6FF" fill-opacity=".16" stroke="url(#{u}-goldf)" stroke-width="3.2">'
            f'<circle cx="100" cy="113" r="15"/><circle cx="140" cy="113" r="15"/></g>'
            f'<path d="M115 112C118 108 122 108 125 112M85 111L76 108M155 111L164 108" fill="none" stroke="url(#{u}-goldf)" stroke-width="3" stroke-linecap="round"/>'
            f'<path d="M90 106C94 102 99 101 103 102" fill="none" stroke="#FFFFFF" stroke-opacity=".7" stroke-width="2" stroke-linecap="round"/>')


def _sunglasses(u):
    return (f'<path d="M83 104H118C118 122 112 128 100 128C88 128 83 120 83 104Z" fill="url(#{u}-lens)" stroke="url(#{u}-goldf)" stroke-width="3" stroke-linejoin="round"/>'
            f'<path d="M122 104H157C157 120 152 128 140 128C128 128 122 122 122 104Z" fill="url(#{u}-lens)" stroke="url(#{u}-goldf)" stroke-width="3" stroke-linejoin="round"/>'
            f'<path d="M118 108C120 105 120 105 122 108M83 106L74 104M157 106L166 104" fill="none" stroke="url(#{u}-goldf)" stroke-width="3" stroke-linecap="round"/>'
            f'<path d="M89 109L98 109M128 109L137 109" stroke="#FFFFFF" stroke-opacity=".45" stroke-width="2.4" stroke-linecap="round"/>')


def _aviator(u):
    return (f'<path d="M82 102H118C118 124 108 132 98 130C86 128 82 116 82 102Z" fill="#3B4B3A" fill-opacity=".85" stroke="url(#{u}-goldf)" stroke-width="2.6" stroke-linejoin="round"/>'
            f'<path d="M122 102H158C158 116 154 128 142 130C132 132 122 124 122 102Z" fill="#3B4B3A" fill-opacity=".85" stroke="url(#{u}-goldf)" stroke-width="2.6" stroke-linejoin="round"/>'
            f'<path d="M118 104Q120 100 122 104M82 103L73 102M158 103L167 102" fill="none" stroke="url(#{u}-goldf)" stroke-width="2.6" stroke-linecap="round"/>'
            f'<path d="M90 108L100 108M130 108L140 108" stroke="#FFFFFF" stroke-opacity=".4" stroke-width="2.2" stroke-linecap="round"/>')


def _glasses_red(u):
    return (f'<rect x="83" y="103" width="31" height="23" rx="6" fill="#BFE6FF" fill-opacity=".14" stroke="#D64545" stroke-width="3.4"/>'
            f'<rect x="126" y="103" width="31" height="23" rx="6" fill="#BFE6FF" fill-opacity=".14" stroke="#D64545" stroke-width="3.4"/>'
            f'<path d="M114 111H126M83 110L74 107M157 110L166 107" stroke="#D64545" stroke-width="3" fill="none" stroke-linecap="round"/>')


# ================================================================ registries
CLOTHING: dict[str, Callable[[str], str]] = {"shirtCrewNeck": _tee_default}
HEADWEAR: dict[str, Callable[[str], str]] = {}
NECK: dict[str, Callable[[str], str]] = {}
GLASSES: dict[str, Callable[[str], str]] = {"prescription02": _glasses_round, "sunglasses": _sunglasses,
                                            "aviator": _aviator, "redframes": _glasses_red}
HAIR_COVER_FULL = set()          # headwear that hides all hair (hijab, shemagh, coin scarf)


@dataclass(frozen=True)
class Item:
    id: str
    cat: str                    # clothing | top | neck | accessories | hair | hair_color | skin
    group: str                  # shop section
    name: str
    price: int = 0
    gender: Optional[str] = None
    bundle: tuple = field(default_factory=tuple)      # extra (cat, id) equipped together (job outfit + its cap)


CATALOG: list[Item] = []


def _add(item: Item): CATALOG.append(item)


# ---- t-shirts
TEE_COLORS = {"red": ("أحمر", "#D64545"), "blue": ("أزرق", "#3B7DD8"), "yellow": ("أصفر", "#F2C230"), "white": ("أبيض", "#F1F5FA"),
              "purple": ("بنفسجي", "#8B5CC7"), "orange": ("برتقالي", "#EE8A2E"), "black": ("أسود", "#2B2F3A")}
_add(Item("shirtCrewNeck", "clothing", "tees", "تيشيرت جذور (أخضر)", 0))
for k, (nm, col) in TEE_COLORS.items():
    CLOTHING[f"tee_{k}"] = (lambda u, c=col: _tee(u, c))
    _add(Item(f"tee_{k}", "clothing", "tees", f"تيشيرت {nm}", 10))
CLOTHING["jersey"] = _jersey
_add(Item("jersey", "clothing", "tees", "قميص المنتخب ⚽", 30))

# ---- hoodies
HOODIE_COLORS = {"red": ("أحمر", "#D64545"), "blue": ("أزرق", "#3B7DD8"), "green": ("أخضر", "#2FA36B"), "yellow": ("أصفر", "#E9B824"),
                 "purple": ("بنفسجي", "#8B5CC7"), "orange": ("برتقالي", "#EE8A2E"), "gray": ("رمادي", "#8A94A6"), "pink": ("وردي", "#E97FA8")}
for k, (nm, col) in HOODIE_COLORS.items():
    CLOTHING[f"hoodie_{k}"] = (lambda u, c=col: _hoodie(u, c))
    _add(Item(f"hoodie_{k}", "clothing", "hoodies", f"هودي {nm}", 25))

# ---- jackets
CLOTHING["jacket_denim"] = _jacket_denim
CLOTHING["jacket_bomber"] = _jacket_bomber
CLOTHING["jacket_leather"] = _jacket_leather
_add(Item("jacket_denim", "clothing", "jackets", "جاكيت جينز", 35))
_add(Item("jacket_bomber", "clothing", "jackets", "جاكيت بومبر", 40))
_add(Item("jacket_leather", "clothing", "jackets", "جاكيت جلد", 50))
PUFFER = {"navy": ("كحلي", "#1E3A6E"), "red": ("أحمر", "#C8202F"), "green": ("أخضر", "#2A7B57"), "yellow": ("أصفر", "#E9B824")}
for k, (nm, col) in PUFFER.items():
    CLOTHING[f"puffer_{k}"] = (lambda u, c=col: _jacket_puffer(u, c))
    _add(Item(f"puffer_{k}", "clothing", "jackets", f"جاكيت شتوي {nm}", 45))

# ---- heritage
CLOTHING["dishdasha"] = _dishdasha
_add(Item("dishdasha", "clothing", "heritage", "دشداشة", 60, gender="ولد"))
for k, (nm, col) in {"black": ("أسود", "#1F1A24"), "maroon": ("عنابي", "#6E1F31")}.items():
    CLOTHING[f"thobe_{k}"] = (lambda u, c=col: _thobe(u, c))
    _add(Item(f"thobe_{k}", "clothing", "heritage", f"ثوب أردني مطرّز ({nm})", 90, gender="بنت"))

# ---- jobs (outfit + its own cap, bought together)
JOBS = [  # id, Arabic name, outfit fn, (cap id, cap fn) or None, price
    ("blazerAndShirt", "طبيب 🥼", _doctor, ("scrubcap", _scrub_cap), 40),
    ("nurse", "ممرض/ة 💉", _nurse, ("nursecap", _nurse_cap), 40),
    ("engineer", "مهندس 👷", _engineer, ("hardhat", _hardhat), 60),
    ("pilot", "طيار ✈️", _pilot, ("pilotcap", _pilot_cap), 80),
    ("officer", "ضابط 🎖️", _officer, ("officercap", _officer_cap), 80),
    ("chef", "طباخ 👨‍🍳", _chef, ("chefhat", _chef_hat), 50),
    ("firefighter", "إطفائي 🚒", _firefighter, ("firehelmet", _fire_helmet), 70),
    ("teacher", "معلم/ة 📚", _teacher, None, 50),
    ("farmer", "مزارع 🌾", _farmer, ("strawhat", _straw_hat), 45),
    ("overall", "رائد فضاء 🚀", _astronaut, ("astrohelmet", _astro_helmet), 80),
]
JOB_HEADGEAR_NAMES = {"scrubcap": "قبعة الطبيب", "nursecap": "قبعة التمريض", "hardhat": "خوذة المهندس", "pilotcap": "قبعة الطيار",
                      "officercap": "قبعة الضابط", "chefhat": "قبعة الطباخ", "firehelmet": "خوذة الإطفائي", "strawhat": "قبعة المزارع",
                      "astrohelmet": "خوذة الفضاء"}
for jid, nm, fn, cap, price in JOBS:
    CLOTHING[jid] = fn
    bundle = ()
    if cap:
        HEADWEAR[cap[0]] = cap[1]
        bundle = (("top", cap[0]),)
        _add(Item(cap[0], "top", "jobcaps", JOB_HEADGEAR_NAMES[cap[0]], price // 2))
    _add(Item(jid, "clothing", "jobs", nm, price, bundle=bundle))

# ---- caps & winter hats
HEADWEAR["none"] = lambda u: ""
_add(Item("none", "top", "caps", "بدون غطاء رأس", 0))
CAPS = {"hat": ("قبعة رياضية (كحلي)", "#173763", 30), "cap_red": ("قبعة رياضية حمراء", "#C8202F", 30), "cap_green": ("قبعة رياضية خضراء", "#2A7B57", 30)}
for cid, (nm, col, price) in CAPS.items():
    HEADWEAR[cid] = (lambda u, c=col: _cap(u, c))
    _add(Item(cid, "top", "caps", nm, price))
WINTER = {"winterHat1": ("وردية", "#D98466"), "winter_navy": ("كحلية", "#1E3A6E"), "winter_red": ("حمراء", "#C8202F"), "winter_green": ("خضراء", "#2A7B57"),
          "winter_mustard": ("خردلية", "#E0A526"), "winter_gray": ("رمادية", "#8A94A6"), "winter_purple": ("بنفسجية", "#8B5CC7"), "winter_white": ("بيضاء", "#EEF2F7")}
for wid, (nm, col) in WINTER.items():
    HEADWEAR[wid] = (lambda u, c=col: _beanie(u, c))
    _add(Item(wid, "top", "winter", f"طاقية شتاء {nm}", 30 if wid != "winterHat1" else 50))

# ---- heritage headwear + hijab
HEADWEAR["shemagh_red"] = lambda u: _shemagh(u, "shr")
HEADWEAR["shemagh_black"] = lambda u: _shemagh(u, "shb")
HEADWEAR["coin_scarf"] = _coin_scarf
HAIR_COVER_FULL.update({"shemagh_red", "shemagh_black", "coin_scarf"})
_add(Item("shemagh_red", "top", "heritage_head", "شماغ أحمر", 50))
_add(Item("shemagh_black", "top", "heritage_head", "شماغ أسود", 50))
_add(Item("coin_scarf", "top", "heritage_head", "حطة الليرات الذهبية", 70, gender="بنت"))
HIJAB = {"white": ("أبيض", "#F4F1EA"), "black": ("أسود", "#23222B"), "navy": ("كحلي", "#22406E"), "rose": ("وردي", "#D98466"),
         "emerald": ("أخضر", "#1FA37A"), "lilac": ("بنفسجي فاتح", "#9C82C9"), "gray": ("رمادي", "#8F98A8"), "gold": ("ذهبي", "#D9B45A")}
for k, (nm, col) in HIJAB.items():
    HEADWEAR[f"hijab_{k}"] = (lambda u, c=col: _hijab(u, c))
    HAIR_COVER_FULL.add(f"hijab_{k}")
    _add(Item(f"hijab_{k}", "top", "hijab", f"حجاب {nm}", 0, gender="بنت"))

# ---- scarves
NECK["none"] = lambda u: ""
_add(Item("none", "neck", "scarves", "بدون لفحة", 0))
SCARVES = {"red": ("حمراء", "#C8202F", None), "blue": ("زرقاء", "#3B7DD8", None), "green": ("خضراء", "#2A7B57", None),
           "gray": ("رمادية", "#8A94A6", None), "pink": ("وردية", "#E97FA8", None), "striped": ("مقلّمة", "#1FA37A", "#E6BE6A")}
for k, (nm, col, stripe) in SCARVES.items():
    NECK[f"scarf_{k}"] = (lambda u, c=col, s=stripe: _scarf(u, c, s))
    _add(Item(f"scarf_{k}", "neck", "scarves", f"لفحة {nm}", 20))

# ---- glasses
_add(Item("blank", "accessories", "glasses", "بدون نظارة", 0))
_add(Item("prescription02", "accessories", "glasses", "نظارة طبية 👓", 30))
_add(Item("redframes", "accessories", "glasses", "نظارة بإطار أحمر", 30))
_add(Item("sunglasses", "accessories", "glasses", "نظارة شمسية 🕶️", 50))
_add(Item("aviator", "accessories", "glasses", "نظارة طيّارين", 50))

BY_ID = {(i.cat, i.id): i for i in CATALOG}
