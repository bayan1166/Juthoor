"""
What happens around a wrong answer (pure Python, no Streamlit, so it can be tested on its own).

    wrong answer
        -> mistake card (why / rule / worked example)
        -> follow-up question on the SAME pattern (same skill, same level)
        -> still wrong: DEEP CASCADING DRILL-DOWN
               push the current (skill, pattern, difficulty) onto a stack, then step to
               the ONE thing it most depends on -- another pattern in the same skill, or,
               once that chain bottoms out, the previous skill's most foundational pattern
               (see offline_bank.PATTERN_PARENTS and knowledge_graph.nearest_prerequisite_with_bank).
               Answer wrong again -> drill one level deeper still (bounded by
               config.MAX_DRILL_DEPTH so a single wrong answer can't turn into an
               endless quiz).
               Answer correct -> pop one level and climb back up, level by level,
               until back at the very top.
        -> back to the normal adaptive flow (adaptive_engine.py takes over again;
           its own return_stack keeps the cascade going across whole skills if needed).

Every step generates a `breadcrumb`: a short, friendly sentence explaining WHY the
system is moving to a different question, e.g. "يبدو أن هناك لبساً في ...". app.py
already renders this through the existing `q['banner']` slot -- no UI change needed.

The follow-ups are practice: they are not sent to the adaptive engine, so they never
distort the diagnosis (the engine has already processed the original wrong answer).
"""
from __future__ import annotations

import random
from typing import Optional

import config
import knowledge_graph as kg
import offline_bank as ob
import llm_remediation as llm

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


# ------------------------------------------------------------ deep cascading drill-down
def _step_down(skill: str, pattern: str) -> Optional[tuple[str, str]]:
    """
    The single (skill, pattern) this one most depends on, or None at bedrock.
    offline_bank.PATTERN_PARENTS is a flat pattern -> pattern map that is allowed
    to cross skill boundaries directly (e.g. "md_sign" -> "si_rule", multiplying's
    sign rule depends on subtraction's core rule) -- so the parent's OWNING skill
    must always be looked up, never assumed to be the current one. Once the
    pattern chain bottoms out (no parent), cross into the nearest prerequisite
    skill that actually has a question bank, and start at its most foundational
    pattern.
    """
    parent_pattern = ob.pattern_parent(pattern)
    if parent_pattern:
        owner = ob.skill_of_pattern(parent_pattern) or skill
        return owner, parent_pattern

    pre_skill = kg.nearest_prerequisite_with_bank(skill, has_bank=lambda s: s in ob.REGISTRY)
    if pre_skill:
        pre_patterns = ob.patterns_of(pre_skill)
        if pre_patterns:
            return pre_skill, pre_patterns[0]
    return None


def _breadcrumb_down(from_skill: str, from_pattern: str, to_skill: str, to_pattern: str) -> str:
    target = ob.pattern_title(to_pattern)
    origin = ob.pattern_title(from_pattern)
    if to_skill != from_skill:
        return (f"يبدو أن السبب أعمق من درس «{kg.SKILLS[from_skill].name_ar}» نفسه. "
                f"لنراجع «{target}» من درس «{kg.SKILLS[to_skill].name_ar}» أولاً، ثم نعود لفكرة «{origin}».")
    return f"يبدو أن هناك لبساً في «{target}»، لنثبّتها أولاً ثم نعود إلى فكرة «{origin}»."


def _breadcrumb_up(to_skill: str, to_pattern: str) -> str:
    return f"هذا الأساس أصبح متيناً 🌱، لنعد إلى «{ob.pattern_title(to_pattern)}»."


def start(q: dict, selected=None) -> dict:
    """Remedial plan created right after a wrong answer to q.
    `selected` (the student's actual wrong choice) is optional but, when given,
    lets the very first stepping-stone question target that exact misconception."""
    return {
        "stage": SAME,
        "skill": q["skill"], "difficulty": q["difficulty"], "pattern": q["pattern"],
        "stack": [],                                            # levels dug through, deepest last
        "breadcrumb": "",
        "misconception": diagnose(q, selected) if selected is not None else None,
    }


def advance(plan: dict, answered_correctly: bool) -> Optional[dict]:
    """
    Plan after a remedial question was answered (None = remediation is finished,
    control returns to the normal adaptive flow).
    """
    if plan["stage"] == SAME:
        if answered_correctly:
            return None
        return _descend(plan)

    # stage == EASIER: somewhere inside the drill, possibly several levels deep.
    if answered_correctly:
        if not plan["stack"]:
            return None                          # already at the top -- resume the normal flow
        top = plan["stack"][-1]
        remaining = plan["stack"][:-1]
        if not remaining:
            return None                          # that WAS the last level; back to the top, done
        return {**plan, "skill": top["skill"], "pattern": top["pattern"], "difficulty": top["difficulty"],
                "stack": remaining, "breadcrumb": _breadcrumb_up(top["skill"], top["pattern"])}

    if len(plan["stack"]) >= config.MAX_DRILL_DEPTH:
        return None                              # deep enough -- let adaptive_engine flag the root gap
    return _descend(plan)


def _descend(plan: dict) -> Optional[dict]:
    deeper = _step_down(plan["skill"], plan["pattern"])
    if deeper is None:
        return None                              # true bedrock: nothing left to drill into
    to_skill, to_pattern = deeper
    stack = plan["stack"] + [{"skill": plan["skill"], "pattern": plan["pattern"], "difficulty": plan["difficulty"]}]
    return {
        **plan, "stage": EASIER, "skill": to_skill, "pattern": to_pattern,
        "difficulty": config.PROBE_DIFFICULTY, "stack": stack,
        "breadcrumb": _breadcrumb_down(plan["skill"], plan["pattern"], to_skill, to_pattern),
    }


# ------------------------------------------------------------ question builders
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


def same_pattern_question(plan: dict, rng: random.Random, avoid=()) -> dict:
    """Another question on the same idea -- tries a live, targeted LLM generation
    first (grounded in the exact misconception just diagnosed), then the static
    bank; never repeats the same wording twice if any other variant exists."""
    skill, level, pattern = plan["skill"], plan["difficulty"], plan["pattern"]
    avoid = set(avoid)
    q = llm.generate(skill, level, rng, avoid, pattern=pattern, misconception=plan.get("misconception"))
    if q["question"] in avoid:                          # this idea has a single fixed wording on this level
        for lvl in sorted(ob.REGISTRY[skill], key=lambda l: (abs(l - level), l)):
            alt = _build(skill, lvl, rng, avoid, pattern=pattern)
            if alt and alt["question"] not in avoid:
                q = alt
                break
        else:
            alt = _build(skill, level, rng, avoid)
            q = alt if alt and alt["question"] not in avoid else q
    banner = plan.get("breadcrumb") or "سؤال جديد على الفكرة نفسها. جرّب مرة ثانية!"
    return {**q, "remedial": SAME, "banner": banner}


def easier_question(plan: dict, state, rng: random.Random, avoid=()) -> dict:
    """
    A stepping-stone question at wherever `advance()` decided the drill should go
    next (a deeper pattern, possibly in an earlier skill). `advance()` -- not this
    function -- owns the routing decision; this function's only job is building a
    real question for the (skill, pattern, difficulty) it was given.
    """
    skill, level, pattern = plan["skill"], plan["difficulty"], plan["pattern"]
    avoid = set(avoid)
    q = llm.generate(skill, level, rng, avoid, pattern=pattern, misconception=plan.get("misconception"))
    if q["question"] in avoid:
        alt = _build(skill, level, rng, avoid, pattern=pattern) or _build(skill, level, rng, avoid)
        q = alt if alt and alt["question"] not in avoid else q
    banner = plan.get("breadcrumb") or "لنتأكد من الأساس الذي يقوم عليه هذا الدرس."
    return {**q, "remedial": EASIER, "banner": banner, "guided": True}
