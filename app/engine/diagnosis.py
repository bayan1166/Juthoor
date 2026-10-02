"""Domain-agnostic root-gap diagnosis over a prerequisite graph.

Nothing in this module knows about mathematics, Arabic, or the curriculum. It takes:

* a prerequisite mapping ``{skill_id: [prerequisite_skill_id, ...]}``
* per-skill evidence (attempts, correct answers, whether mastery was established)

and returns an explainable verdict. The adaptive engine wraps it with the curriculum graph
and the user-facing language; a second subject only needs a second mapping.

Decision rules (deliberately simple so every verdict can be explained and tested):

1. ``failing(s)``  – ``s`` is not currently believed mastered and the learner answered it
   wrong more often than right. (The caller decides what "currently believed mastered"
   means; the adaptive engine withdraws that belief when fresh errors collapse the BKT
   estimate, so old history alone never re-opens a mastered skill.)
2. ``solid(s)``    – believed mastered, or every observed answer on ``s`` was right.
   Anything else (untested, or mixed results) is *unverified*.
3. Candidates are the failing skills on the chain ``origin + all ancestors``.
4. A candidate is *eligible* as the root only when every direct prerequisite is solid.
   If a prerequisite is itself failing, the deeper skill is the better explanation;
   if a prerequisite is untested, we cannot rule it out yet.
5. Among eligible candidates the one with the strongest direct evidence (most wrong
   answers, then highest error rate) is the root; ties go to the more fundamental skill.
   Other eligible candidates with enough errors are reported as ``competing`` and cap
   confidence at medium (two independent gaps are possible on a branching graph).
6. No root is named unless the chain shows at least ``min_chain_errors`` wrong answers
   (one or two slips are not a gap) and the root itself shows at least
   ``min_root_errors`` wrong answers (one probe is not enough to blame a skill).
   Otherwise the verdict is ``insufficient_evidence``, with the leading candidate if any.
7. Errors on the chain with no failing skill (every skill still has at least as many right as wrong
   answers) are ``insufficient_evidence`` with reason ``mixed_evidence``; ``no_difficulty`` means no
   unmastered skill on the chain has any wrong answer.

Confidence is a level, not a probability (see ``confidence_level``).
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Mapping, Optional

ROOT_IDENTIFIED = "root_identified"
INSUFFICIENT = "insufficient_evidence"
NO_DIFFICULTY = "no_difficulty"
UNKNOWN_SKILL = "unknown_skill"

HIGH, MEDIUM, LOW = "high", "medium", "low"


class GraphError(ValueError):
    """Raised when a prerequisite mapping is not a valid DAG."""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def validate_prerequisites(prereqs: Mapping[str, Iterable[str]]) -> list[str]:
    """Return a list of human-readable problems (empty list means the graph is valid)."""
    problems: list[str] = []
    nodes = set(prereqs)
    for skill, pres in prereqs.items():
        seen = set()
        for pre in pres:
            if pre == skill:
                problems.append(f"{skill}: lists itself as a prerequisite")
            elif pre not in nodes:
                problems.append(f"{skill}: unknown prerequisite '{pre}'")
            if pre in seen:
                problems.append(f"{skill}: duplicate prerequisite '{pre}'")
            seen.add(pre)
    if problems:
        return problems

    white, grey, black = 0, 1, 2
    colour = {s: white for s in nodes}
    for start in sorted(nodes):
        if colour[start] != white:
            continue
        stack = [(start, iter(prereqs[start]))]
        path = [start]
        colour[start] = grey
        while stack:
            node, children = stack[-1]
            nxt = next(children, None)
            if nxt is None:
                colour[node] = black
                stack.pop()
                path.pop()
                continue
            if colour[nxt] == grey:
                cycle = path[path.index(nxt):] + [nxt]
                problems.append("cycle: " + " -> ".join(cycle))
                return problems
            if colour[nxt] == white:
                colour[nxt] = grey
                stack.append((nxt, iter(prereqs[nxt])))
                path.append(nxt)
    return problems


class PrereqGraph:
    """Immutable prerequisite DAG with the traversal helpers the diagnosis needs."""

    def __init__(self, prereqs: Mapping[str, Iterable[str]]):
        frozen = {s: tuple(p) for s, p in prereqs.items()}
        problems = validate_prerequisites(frozen)
        if problems:
            raise GraphError(problems)
        self._pre = frozen
        self._ancestors = lru_cache(maxsize=None)(self._compute_ancestors)
        self._depth = lru_cache(maxsize=None)(self._compute_depth)

    def __contains__(self, skill: object) -> bool:
        return skill in self._pre

    @property
    def skills(self) -> tuple[str, ...]:
        return tuple(self._pre)

    def prerequisites(self, skill: str) -> tuple[str, ...]:
        return self._pre[skill]

    def ancestors(self, skill: str) -> frozenset[str]:
        return self._ancestors(skill)

    def depth(self, skill: str) -> int:
        return self._depth(skill)

    def _compute_ancestors(self, skill: str) -> frozenset[str]:
        out: set[str] = set()
        for pre in self._pre[skill]:
            out.add(pre)
            out |= self._ancestors(pre)
        return frozenset(out)

    def _compute_depth(self, skill: str) -> int:
        pres = self._pre[skill]
        return 0 if not pres else 1 + max(self._depth(p) for p in pres)


@dataclass(frozen=True)
class SkillEvidence:
    attempts: int = 0
    correct: int = 0
    mastered: bool = False

    @property
    def wrong(self) -> int:
        return max(0, self.attempts - self.correct)


_EMPTY = SkillEvidence()


def failing(ev: SkillEvidence) -> bool:
    return not ev.mastered and ev.wrong > 0 and ev.wrong > ev.correct


def solid(ev: SkillEvidence) -> bool:
    return ev.mastered or (ev.attempts > 0 and ev.wrong == 0)


def confidence_level(root: SkillEvidence, prereq_evidence: list[SkillEvidence]) -> tuple[str, list[str]]:
    """Map evidence counts to an ordinal confidence level and the reasons behind it.

    high   : >= 3 wrong answers on the root, >= 75% of its answers wrong, and every direct
             prerequisite was *observed* correct at least once (not only assumed mastered).
    medium : >= 2 wrong answers on the root and more wrong than right.
    low    : anything weaker (only reachable when min_root_errors is set to 1).
    This is an evidence-count rule, not a calibrated probability.
    """
    reasons = [f"root_wrong={root.wrong}", f"root_right={root.correct}"]
    observed = all(p.correct > 0 for p in prereq_evidence)
    reasons.append("prerequisites_observed" if observed else "prerequisites_assumed")
    rate = root.wrong / root.attempts if root.attempts else 0.0
    if root.wrong >= 3 and rate >= 0.75 and observed:
        return HIGH, reasons
    if root.wrong >= 2 and root.wrong > root.correct:
        return MEDIUM, reasons
    return LOW, reasons


def diagnose(
    graph: PrereqGraph,
    origin: str,
    evidence: Mapping[str, SkillEvidence],
    *,
    min_chain_errors: int = 3,
    min_root_errors: int = 2,
) -> dict:
    """Explainable root-gap verdict for a learner who is struggling with ``origin``."""
    if origin not in graph:
        return {"status": UNKNOWN_SKILL, "origin": origin, "root": None, "candidates": []}

    def ev(s: str) -> SkillEvidence:
        return evidence.get(s, _EMPTY)

    chain = sorted({origin, *graph.ancestors(origin)}, key=lambda s: (-graph.depth(s), s))
    failing_skills = [s for s in chain if failing(ev(s))]
    chain_errors = sum(ev(s).wrong for s in failing_skills)
    base = {
        "origin": origin,
        "chain_errors": chain_errors,
        "min_chain_errors": min_chain_errors,
        "min_root_errors": min_root_errors,
    }
    if not failing_skills:
        # Errors were observed on the chain, but on every skill the learner still has at least as
        # many right answers as wrong ones. That is mixed evidence, not "no difficulty".
        observed = [{"skill": s, "wrong": ev(s).wrong, "right": ev(s).correct}
                    for s in chain if not ev(s).mastered and ev(s).wrong > 0]
        if observed:
            return {**base, "status": INSUFFICIENT, "reason": "mixed_evidence", "root": None,
                    "leading_candidate": None, "observed": observed, "candidates": []}
        return {**base, "status": NO_DIFFICULTY, "root": None, "candidates": []}

    candidates: list[dict] = []
    eligible: list[str] = []
    for skill in sorted(failing_skills, key=lambda s: (graph.depth(s), s)):
        e = ev(skill)
        row = {"skill": skill, "wrong": e.wrong, "right": e.correct, "depth": graph.depth(skill)}
        failing_pre = [p for p in graph.prerequisites(skill) if failing(ev(p))]
        untested_pre = [p for p in graph.prerequisites(skill) if not failing(ev(p)) and not solid(ev(p))]
        if failing_pre:
            row.update(verdict="explained_by_prerequisite", because=failing_pre)
        elif untested_pre:
            row.update(verdict="prerequisite_unverified", because=untested_pre)
        else:
            row.update(verdict="eligible", because=list(graph.prerequisites(skill)))
            eligible.append(skill)
        candidates.append(row)

    # Several independent branches can each explain the difficulty. Rank them by the
    # strength of their own evidence (more wrong answers, then higher error rate), and
    # only then prefer the more fundamental skill.
    def strength(s: str):
        e = ev(s)
        return (-e.wrong, -(e.wrong / e.attempts if e.attempts else 0.0), graph.depth(s), s)

    eligible.sort(key=strength)
    leading: Optional[str] = eligible[0] if eligible else None
    competing = [s for s in eligible[1:] if ev(s).wrong >= min_root_errors]
    for row in candidates:
        if row["verdict"] == "eligible":
            row["verdict"] = "leading" if row["skill"] == leading else "competing"

    if chain_errors < min_chain_errors:
        return {**base, "status": INSUFFICIENT, "reason": "too_few_errors", "root": None,
                "leading_candidate": leading, "candidates": candidates}
    if leading is None:
        return {**base, "status": INSUFFICIENT, "reason": "prerequisites_unverified", "root": None,
                "leading_candidate": None, "candidates": candidates}
    root_ev = ev(leading)
    if root_ev.wrong < min_root_errors:
        return {**base, "status": INSUFFICIENT, "reason": "root_needs_confirmation", "root": None,
                "leading_candidate": leading, "candidates": candidates}

    for row in candidates:
        if row["skill"] == leading:
            row["verdict"] = "root"
    pre_ev = [ev(p) for p in graph.prerequisites(leading)]
    level, reasons = confidence_level(root_ev, pre_ev)
    if competing:
        reasons.append("competing_candidates")
        if level == HIGH:
            level = MEDIUM
    path = [s for s in chain if graph.depth(s) >= graph.depth(leading)
            and (s == leading or leading in graph.ancestors(s))]
    return {
        **base,
        "status": ROOT_IDENTIFIED,
        "root": leading,
        "leading_candidate": leading,
        "path": path,
        "confidence_level": level,
        "confidence_basis": reasons,
        "prerequisites_checked": [
            {"skill": p, "wrong": ev(p).wrong, "right": ev(p).correct, "mastered": ev(p).mastered}
            for p in graph.prerequisites(leading)
        ],
        "competing": competing,
        "candidates": candidates,
    }
