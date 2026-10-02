from __future__ import annotations

import random
from typing import Optional

from app.engine import config
from app.engine import knowledge_graph as kg
from app.engine import offline_bank as ob
from app.engine import llm_remediation as llm

SAME, EASIER = "same_pattern", "easier"


def is_correct(q: dict, selected) -> bool:
    return ob.norm(selected) == ob.norm(q["correct_answer"])


def diagnose(q: dict, selected) -> Optional[str]:
    return q.get("traps", {}).get(ob.norm(selected))


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


def _step_down(skill: str, pattern: str) -> Optional[tuple[str, str]]:
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
    return f"هذا الأساس أصبح متيناً، لنعد إلى «{ob.pattern_title(to_pattern)}»."


def start(q: dict, selected=None) -> dict:
    return {
        "stage": SAME,
        "skill": q["skill"], "difficulty": q["difficulty"], "pattern": q["pattern"],
        "stack": [],
        "breadcrumb": "",
        "misconception": diagnose(q, selected) if selected is not None else None,
    }


def confirm(plan: Optional[dict], skill: str, last: dict) -> dict:
    """Plan one confirmation probe on the leading root candidate before naming it."""
    pattern = last.get("pattern") if last.get("skill") == skill else None
    if not pattern or ob.skill_of_pattern(pattern) not in (None, skill):
        patterns = ob.patterns_of(skill)
        pattern = patterns[0] if patterns else last.get("pattern", "")
    return {
        "stage": EASIER, "skill": skill, "difficulty": config.PROBE_DIFFICULTY, "pattern": pattern,
        "stack": list(plan["stack"]) if plan else [],
        "misconception": (plan or {}).get("misconception"),
        "confirm": True,
        "breadcrumb": f"سؤال تأكيد على «{kg.SKILLS[skill].name_ar}»: خطأ واحد لا يكفي لنحكم أنه الجذر.",
    }


def advance(plan: dict, answered_correctly: bool) -> Optional[dict]:
    if plan["stage"] == SAME:
        if answered_correctly:
            return None
        return _descend(plan)


    if answered_correctly:
        if not plan["stack"]:
            return None
        top = plan["stack"][-1]
        remaining = plan["stack"][:-1]
        if not remaining:
            return None
        return {**plan, "skill": top["skill"], "pattern": top["pattern"], "difficulty": top["difficulty"],
                "stack": remaining, "breadcrumb": _breadcrumb_up(top["skill"], top["pattern"])}

    if len(plan["stack"]) >= config.MAX_DRILL_DEPTH:
        return None
    return _descend(plan)


def _descend(plan: dict) -> Optional[dict]:
    deeper = _step_down(plan["skill"], plan["pattern"])
    if deeper is None:
        return None
    to_skill, to_pattern = deeper
    stack = plan["stack"] + [{"skill": plan["skill"], "pattern": plan["pattern"], "difficulty": plan["difficulty"]}]
    return {
        **plan, "stage": EASIER, "skill": to_skill, "pattern": to_pattern,
        "difficulty": config.PROBE_DIFFICULTY, "stack": stack,
        "breadcrumb": _breadcrumb_down(plan["skill"], plan["pattern"], to_skill, to_pattern),
    }


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
    skill, level, pattern = plan["skill"], plan["difficulty"], plan["pattern"]
    avoid = set(avoid)
    q = llm.generate(skill, level, rng, avoid, pattern=pattern, misconception=plan.get("misconception"))
    if q["question"] in avoid:
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
    skill, level, pattern = plan["skill"], plan["difficulty"], plan["pattern"]
    avoid = set(avoid)
    q = llm.generate(skill, level, rng, avoid, pattern=pattern, misconception=plan.get("misconception"))
    if q["question"] in avoid:
        alt = _build(skill, level, rng, avoid, pattern=pattern) or _build(skill, level, rng, avoid)
        q = alt if alt and alt["question"] not in avoid else q
    banner = plan.get("breadcrumb") or "لنتأكد من الأساس الذي يقوم عليه هذا الدرس."
    return {**q, "remedial": EASIER, "banner": banner, "guided": True}
