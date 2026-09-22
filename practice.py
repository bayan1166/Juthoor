"""
What happens around a wrong answer (pure Python, no Streamlit, so it can be tested on its own).

    wrong answer  ->  mistake card (why / rule / worked example)
                  ->  follow-up question on the SAME pattern (same skill, same level)
                  ->  if that is wrong too: a question from a LOWER level
                  ->  back to the normal adaptive flow

The follow-ups are practice: they are not sent to the adaptive engine, so they never distort the
diagnosis (the engine has already processed the original wrong answer).
"""
from __future__ import annotations

import random
from typing import Optional

import knowledge_graph as kg
import offline_bank as ob

SAME, EASIER = "same_pattern", "easier"


# ------------------------------------------------------------------ answers
def is_correct(q: dict, selected) -> bool:
    return ob.norm(selected) == ob.norm(q["correct_answer"])


def diagnose(q: dict, selected) -> Optional[str]:
    """The misconception that produces this exact wrong answer, if the bank knows it."""
    return q.get("traps", {}).get(ob.norm(selected))


# --------------------------------------------------------------------- card
def mistake_card(q: dict, selected) -> dict:
    card = ob.PATTERNS.get(q.get("pattern"), {})
    return {
        "title": card.get("title", "راجع الفكرة"),
        "rule": card.get("rule", ""),
        "example": card.get("example", ""),
        "why": diagnose(q, selected),
        "chosen": str(selected).strip(),
        "correct": q["correct_answer"],
        "solution": q.get("explanation", ""),
        "type": q.get("type", "mcq"),
    }


# ------------------------------------------------------------ follow-up flow
def start(q: dict) -> dict:
    """Remedial plan created right after a wrong answer to q."""
    return {"stage": SAME, "skill": q["skill"], "difficulty": q["difficulty"], "pattern": q["pattern"]}


def advance(plan: dict, answered_correctly: bool) -> Optional[dict]:
    """Plan after a remedial question was answered (None = remediation is finished)."""
    if plan["stage"] == SAME and not answered_correctly:
        return {**plan, "stage": EASIER}
    return None


def same_pattern_question(plan: dict, rng: random.Random, avoid=()) -> dict:
    """Another question on the same idea; never the same text again if any other variant exists."""
    skill, level, pattern = plan["skill"], plan["difficulty"], plan["pattern"]
    avoid = set(avoid)
    q = ob.generate_offline(skill, level, rng, avoid, pattern=pattern)
    if q["question"] in avoid:                          # this idea has a single fixed wording on this level
        for lvl in sorted(ob.REGISTRY[skill], key=lambda l: (abs(l - level), l)):
            alt = _build(skill, lvl, rng, avoid, pattern=pattern)
            if alt and alt["question"] not in avoid:
                q = alt
                break
        else:
            alt = _build(skill, level, rng, avoid)
            q = alt if alt and alt["question"] not in avoid else q
    return {**q, "remedial": SAME, "banner": "سؤال جديد على الفكرة نفسها. جرّب مرة ثانية!"}


def _build(skill: str, level: int, rng, avoid, pattern: Optional[str] = None, not_pattern: Optional[str] = None):
    pool = [t for t in ob.REGISTRY[skill].get(level, [])
            if (pattern is None or t.pattern == pattern) and (not_pattern is None or t.pattern != not_pattern)]
    rng.shuffle(pool)
    fallback = None
    for t in pool * 3:
        q = ob._finish(t, rng)
        if q is None:
            continue
        if q["question"] not in avoid:
            return q
        fallback = fallback or q
    return fallback


def easier_question(plan: dict, state, rng: random.Random, avoid=()) -> dict:
    """A gentler question: one level down; on level 1, a prerequisite skill; else a guided level-1 question."""
    skill, level, pattern = plan["skill"], plan["difficulty"], plan["pattern"]
    q, banner, guided = None, "", False
    if level > 1:
        for lvl in range(level - 1, 0, -1):                       # same idea, lower level, if it exists
            q = _build(skill, lvl, rng, avoid, pattern=pattern)
            if q:
                break
        q = q or _build(skill, level - 1, rng, avoid)
        banner = "سؤال أسهل قليلاً لنثبّت الفكرة."
    else:
        pres = [p for p in kg.prerequisites(skill) if p in ob.REGISTRY]
        if pres:
            pre = min(pres, key=lambda p: (state.is_mastered(p), state.mastery(p)))
            q = _build(pre, 1, rng, avoid)
            banner = "لنتأكد من الأساس الذي يقوم عليه هذا الدرس."
        if q is None:
            q = _build(skill, 1, rng, avoid, not_pattern=pattern) or _build(skill, 1, rng, avoid)
            banner, guided = "خطوة أبسط، ومعها تلميح يساعدك.", True
    return {**q, "remedial": EASIER, "banner": banner, "guided": guided}
