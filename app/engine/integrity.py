"""Invariant checker for a persisted ``StudentState`` (pure; no database).

Returns human-readable violations; an empty list means the state is internally consistent.
The database-level checker (duplicate rows, orphans, cross-user data) lives in
``scripts/check_integrity.py`` and calls this for every stored session state.
"""
from __future__ import annotations

import math

from app.engine import config
from app.engine import knowledge_graph as kg


def check_state(state, strict_lineage: bool = False) -> list[str]:
    """Hard invariants. ``strict_lineage`` also flags a mastered skill whose prerequisite is no longer
    mastered; the engine allows that on purpose (a gap found later in a prerequisite does not un-master
    lessons already passed), so it is reported as a warning by ``lineage_warnings`` instead of a failure."""
    problems: list[str] = []
    known = set(kg.SKILLS)

    def need_known(label: str, skills) -> None:
        for s in skills:
            if s not in known:
                problems.append(f"{label}: unknown skill '{s}'")

    if state.current_skill not in known:
        problems.append(f"current_skill: unknown skill '{state.current_skill}'")
    if not config.MIN_DIFFICULTY <= state.difficulty <= config.MAX_DIFFICULTY:
        problems.append(f"difficulty {state.difficulty} outside [{config.MIN_DIFFICULTY}, {config.MAX_DIFFICULTY}]")
    for s, p in state.p_mastery.items():
        if not isinstance(p, (int, float)) or not math.isfinite(p) or not 0.0 < p < 1.0:
            problems.append(f"p_mastery[{s}]={p!r} must be finite and strictly inside (0, 1)")
    for s, a in state.attempts.items():
        c = state.correct.get(s, 0)
        if a < 0 or c < 0:
            problems.append(f"negative counts on {s}: attempts={a}, correct={c}")
        if c > a:
            problems.append(f"correct ({c}) exceeds attempts ({a}) on {s}")
    for s in state.correct:
        if s not in state.attempts:
            problems.append(f"correct recorded for {s} with no attempts")
    for label in ("mastered", "inferred", "gaps", "parked"):
        need_known(label, getattr(state, label))
    need_known("p_mastery", state.p_mastery)
    need_known("attempts", state.attempts)
    need_known("return_stack", state.return_stack)
    both = state.gaps & (state.mastered | state.inferred)
    if both:
        problems.append(f"skills both gap and mastered: {sorted(both)}")
    if strict_lineage:
        problems.extend(lineage_warnings(state))
    if state.total_answered < 0:
        problems.append("total_answered negative")
    if state.round_answered < 0 or state.consec_wrong < 0:
        problems.append("negative round/consecutive counters")
    if state.total_answered and state.total_answered < state.round_answered:
        problems.append("round_answered exceeds total_answered")
    return problems


def lineage_warnings(state) -> list[str]:
    """Mastered skills whose prerequisites are not (or no longer) believed mastered."""
    out = []
    for s in sorted(state.mastered):
        if s not in kg.SKILLS:
            continue
        missing = sorted(a for a in kg.ancestors(s) if not state.is_mastered(a))
        if missing:
            out.append(f"{s} mastered but prerequisite(s) not mastered: {missing}")
    return out
