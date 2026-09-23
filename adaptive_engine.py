"""
Juthoor adaptive engine.

Public entry point:  decide_next(state, is_correct) -> Decision

How it works
------------
1. Update a Bayesian Knowledge Tracing (BKT-lite) estimate for the skill just tested.
2. If CORRECT   -> climb the difficulty ladder (1 -> 2 -> 3).
                   Correct at the top level with enough confidence = skill MASTERED:
                   * all its ancestors are marked "inferred mastered" (you can't do
                     fraction division without subtraction),
                   * then return to the skill we were digging beneath (if any),
                     otherwise advance to the next unlocked skill.
3. If INCORRECT -> first miss above level 1: step down one level (could be a slip).
                   Otherwise DIAGNOSE:
                   * an unmastered prerequisite exists -> walk DOWN the graph to the
                     weakest one (remember where we came from),
                   * all prerequisites are mastered -> this skill IS the root gap:
                     flag it, remediate at level 1, and park it if the student stays stuck.

The whole StudentState is JSON-serialisable so it can live in SQLite.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Optional

import config
import knowledge_graph as kg

_SET_FIELDS = ("mastered", "inferred", "gaps", "parked")


# ============================================================ student state
@dataclass
class StudentState:
    current_skill: str = config.DEFAULT_START_SKILL
    difficulty: int = config.START_DIFFICULTY
    p_mastery: dict[str, float] = field(default_factory=dict)   # BKT estimate per skill
    attempts: dict[str, int] = field(default_factory=dict)
    correct: dict[str, int] = field(default_factory=dict)
    mastered: set[str] = field(default_factory=set)              # earned by answering
    inferred: set[str] = field(default_factory=set)              # implied by a higher skill
    gaps: set[str] = field(default_factory=set)                  # diagnosed root gaps
    parked: set[str] = field(default_factory=set)                # skipped this round (stuck)
    return_stack: list[str] = field(default_factory=list)        # where to climb back to
    consec_wrong: int = 0
    total_answered: int = 0
    round_answered: int = 0

    # -- helpers -----------------------------------------------------------
    def mastery(self, skill: str) -> float:
        return self.p_mastery.get(skill, config.BKT["p_init"])

    def is_mastered(self, skill: str) -> bool:
        return skill in self.mastered or skill in self.inferred

    # -- persistence -------------------------------------------------------
    def to_json(self) -> str:
        data = asdict(self)
        for key in _SET_FIELDS:
            data[key] = sorted(data[key])
        return json.dumps(data)

    @classmethod
    def from_json(cls, raw: str) -> "StudentState":
        data = json.loads(raw)
        for key in _SET_FIELDS:
            data[key] = set(data.get(key, []))
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class Decision:
    """What the engine decided, and why. Logged for the teacher dashboard."""
    action: str            # level_up | stay | level_down | advance | backtrack | return_up |
                           # remediate | park | complete
    next_skill: str
    next_difficulty: int
    reason: str
    gap_skill: Optional[str] = None   # set when a root gap was just diagnosed
    round_over: bool = False
<<<<<<< HEAD
    breadcrumb: str = ""   # student-facing Arabic sentence explaining the move (UI transparency)
=======
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23


# Friendly, non-test-like wording for the student (tree metaphor).
STUDENT_MESSAGES = {
    "level_up": "Your branch is getting stronger. This next one is a little tougher.",
    "stay": "Almost there. One more like this to lock it in.",
    "level_down": "Let's try one that's a bit gentler.",
    "advance": "A new branch is growing. Here's something fresh.",
    "backtrack": "Let's dig down and check the roots underneath this.",
    "return_up": "That root is firm now. Back up to where we were.",
    "remediate": "Let's slow down and rebuild this root together.",
    "park": "We'll save this root for your teacher. Let's grow another branch.",
    "complete": "Your tree is in full bloom for now.",
}

<<<<<<< HEAD
def _name(sid: str) -> str:
    return kg.SKILLS[sid].name_ar if sid in kg.SKILLS else sid


# Arabic breadcrumbs shown directly to the student (same "why did it move me" UI
# slot the practice.py drill-down uses). Kept separate from STUDENT_MESSAGES
# above, which is English scaffolding used elsewhere; these name the actual
# skills involved so the jump between lessons is never a mystery.
def _breadcrumb_backtrack(struggling: str, prerequisite: str) -> str:
    return f"يبدو أن السبب في «{_name(struggling)}» يعود لدرس أسبق: لنراجع «{_name(prerequisite)}» أولاً."


def _breadcrumb_return_up(firmed_up: str, going_back_to: str) -> str:
    return f"أساس «{_name(firmed_up)}» أصبح متيناً الآن، لنعد إلى «{_name(going_back_to)}»."


def _breadcrumb_remediate(root_gap: str) -> str:
    return f"«{_name(root_gap)}» هو الجذر الحقيقي للمشكلة. {kg.SKILLS[root_gap].intervention}"


def _breadcrumb_park(parked_gap: str, moving_to: str) -> str:
    return f"سنحفظ «{_name(parked_gap)}» لمعلمك، ونتابع الآن بدرس جديد: «{_name(moving_to)}»."


def _breadcrumb_advance(new_skill: str) -> str:
    return f"أحسنت! أصبحت جاهزاً لدرس جديد: «{_name(new_skill)}»."

=======
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23

# ================================================================= BKT-lite
def bkt_update(p_known: float, is_correct: bool) -> float:
    """One Bayesian Knowledge Tracing step (posterior given the answer + learning)."""
    p = config.BKT
    if is_correct:
        num = p_known * (1 - p["p_slip"])
        den = num + (1 - p_known) * p["p_guess"]
    else:
        num = p_known * p["p_slip"]
        den = num + (1 - p_known) * (1 - p["p_guess"])
    posterior = num / den
    return posterior + (1 - posterior) * p["p_learn"]


# ============================================================ small helpers
def _move(state: StudentState, skill: str, difficulty: int, action: str,
<<<<<<< HEAD
          reason: str, gap: Optional[str] = None, breadcrumb: str = "") -> Decision:
    state.current_skill = skill
    state.difficulty = difficulty
    state.consec_wrong = 0
    return Decision(action, skill, difficulty, reason, gap_skill=gap, breadcrumb=breadcrumb)
=======
          reason: str, gap: Optional[str] = None) -> Decision:
    state.current_skill = skill
    state.difficulty = difficulty
    state.consec_wrong = 0
    return Decision(action, skill, difficulty, reason, gap_skill=gap)
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23


def _infer_ancestors(state: StudentState, skill: str) -> None:
    """Mastering a skill implies its prerequisites (and lifts their confidence)."""
    for anc in kg.ancestors(skill):
        if anc not in state.mastered:
            state.inferred.add(anc)
        state.p_mastery[anc] = max(state.mastery(anc), config.MASTERY_THRESHOLD)
        state.gaps.discard(anc)


def _pick_frontier(state: StudentState, just_mastered: Optional[str] = None) -> Optional[str]:
    """Next unlocked skill: all prerequisites mastered, itself not yet mastered."""
    successors = set(kg.dependents(just_mastered)) if just_mastered else set()
    candidates = [
        s for s in kg.SKILLS
        if not state.is_mastered(s)
        and s not in state.parked
        and all(state.is_mastered(p) for p in kg.prerequisites(s))
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda s: (
        s in state.gaps,                    # known trouble spots last
        state.attempts.get(s, 0) > 0,       # untouched skills first
        s not in successors,                # then things that build on what was just learned
        kg.depth(s),                        # then foundations before advanced skills
    ))
    return candidates[0]


def _route_after_mastery(state: StudentState, skill: str) -> Decision:
    while state.return_stack:                       # climb back to where we dug from
        target = state.return_stack.pop()
        if not state.is_mastered(target):
            return _move(state, target, config.MIN_DIFFICULTY, "return_up",
<<<<<<< HEAD
                         f"Root '{skill}' is solid; returning to '{target}'.",
                         breadcrumb=_breadcrumb_return_up(skill, target))
=======
                         f"Root '{skill}' is solid; returning to '{target}'.")
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23
    nxt = _pick_frontier(state, just_mastered=skill)
    if nxt is None:
        return Decision("complete", skill, config.MAX_DIFFICULTY,
                        "Every reachable skill is mastered or parked.", round_over=True)
    return _move(state, nxt, config.MIN_DIFFICULTY, "advance",
<<<<<<< HEAD
                 f"'{skill}' mastered; unlocking '{nxt}'.",
                 breadcrumb=_breadcrumb_advance(nxt))
=======
                 f"'{skill}' mastered; unlocking '{nxt}'.")
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23


# ============================================================= two branches
def _handle_correct(state: StudentState) -> Decision:
    state.consec_wrong = 0
    skill, diff = state.current_skill, state.difficulty

    if diff < config.MAX_DIFFICULTY:
        state.difficulty += 1
        return Decision("level_up", skill, state.difficulty, f"Correct at level {diff}.")

    if state.mastery(skill) < config.MASTERY_THRESHOLD:
        return Decision("stay", skill, diff, "Top level passed but confidence is still low.")

    state.mastered.add(skill)
    state.gaps.discard(skill)
    state.parked.discard(skill)
    _infer_ancestors(state, skill)
    return _route_after_mastery(state, skill)


def _handle_incorrect(state: StudentState) -> Decision:
    state.consec_wrong += 1
    skill, diff = state.current_skill, state.difficulty

    # 1) First miss above level 1 might be a slip or a stretch: step down.
    if diff > config.MIN_DIFFICULTY and state.consec_wrong == 1:
        state.difficulty -= 1
        return Decision("level_down", skill, state.difficulty, f"Missed at level {diff}.")

    # 2) Diagnose: is a prerequisite the real problem?
    weak = [p for p in kg.prerequisites(skill) if not state.is_mastered(p)]
    if weak:
        target = min(weak, key=state.mastery)       # weakest link first
        if not state.return_stack or state.return_stack[-1] != skill:
            state.return_stack.append(skill)
        return _move(state, target, config.PROBE_DIFFICULTY, "backtrack",
<<<<<<< HEAD
                     f"Struggling with '{skill}'; probing prerequisite '{target}'.",
                     breadcrumb=_breadcrumb_backtrack(skill, target))
=======
                     f"Struggling with '{skill}'; probing prerequisite '{target}'.")
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23

    # 3) All prerequisites are solid -> this skill is the root gap.
    state.gaps.add(skill)
    if state.consec_wrong >= 3:                     # stuck: don't frustrate the student
        state.parked.add(skill)
        blocked = kg.descendants(skill)
        state.return_stack = [s for s in state.return_stack if s not in blocked and s != skill]
        nxt = _pick_frontier(state)
        if nxt is None:
            return Decision("complete", skill, config.MIN_DIFFICULTY,
                            f"Root gap '{skill}' parked; nothing else unlocked.",
                            gap_skill=skill, round_over=True)
<<<<<<< HEAD
        return _move(state, nxt, config.MIN_DIFFICULTY, "park",
                     f"Root gap '{skill}' needs the teacher; moving to '{nxt}'.", gap=skill,
                     breadcrumb=_breadcrumb_park(skill, nxt))
    state.difficulty = config.MIN_DIFFICULTY
    return Decision("remediate", skill, config.MIN_DIFFICULTY,
                    f"Prerequisites are solid, so '{skill}' is a root gap.", gap_skill=skill,
                    breadcrumb=_breadcrumb_remediate(skill))
=======
        d = _move(state, nxt, config.MIN_DIFFICULTY, "park",
                  f"Root gap '{skill}' needs the teacher; moving to '{nxt}'.", gap=skill)
        return d
    state.difficulty = config.MIN_DIFFICULTY
    return Decision("remediate", skill, config.MIN_DIFFICULTY,
                    f"Prerequisites are solid, so '{skill}' is a root gap.", gap_skill=skill)
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23


# ================================================================ public API
def decide_next(state: StudentState, is_correct: bool) -> Decision:
    """
    Record the answer for state.current_skill and choose the next skill + difficulty.
    Mutates `state` in place and returns a Decision describing the move.
    """
    skill = state.current_skill
    state.total_answered += 1
    state.round_answered += 1
    state.attempts[skill] = state.attempts.get(skill, 0) + 1
    if is_correct:
        state.correct[skill] = state.correct.get(skill, 0) + 1
    state.p_mastery[skill] = bkt_update(state.mastery(skill), is_correct)

    decision = _handle_correct(state) if is_correct else _handle_incorrect(state)
    if state.round_answered >= config.SESSION_LENGTH:
        decision.round_over = True
    return decision


def round_over(state: StudentState) -> bool:
    return state.round_answered >= config.SESSION_LENGTH


def start_round(state: StudentState) -> None:
    """Begin a fresh round: keep what we know, forget last round's detours."""
    state.round_answered = 0
    state.consec_wrong = 0
    state.return_stack = []
    state.parked = set()
    if state.total_answered == 0:
        return                                       # brand-new student keeps the default start
    nxt = _pick_frontier(state)
    if nxt is not None:
        state.current_skill, state.difficulty = nxt, config.MIN_DIFFICULTY


# ================================================================ reporting
def skill_status(state: StudentState, skill: str) -> str:
    """mastered | gap | learning | untouched  (used by the tree and the database)."""
    if state.is_mastered(skill):
        return "mastered"
    if skill in state.gaps:
        return "gap"
    if state.attempts.get(skill, 0) > 0:
        return "learning"
    return "untouched"


def all_statuses(state: StudentState) -> dict[str, str]:
    return {s: skill_status(state, s) for s in kg.SKILLS}


def tree_health(state: StudentState) -> float:
    """Share of the tree that is mastered (0..1)."""
    return sum(state.is_mastered(s) for s in kg.SKILLS) / len(kg.SKILLS)