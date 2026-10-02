from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Optional

from app.engine import config
from app.engine import diagnosis as dx
from app.engine import knowledge_graph as kg

_SET_FIELDS = ("mastered", "inferred", "gaps", "parked")


@dataclass
class StudentState:
    current_skill: str = config.DEFAULT_START_SKILL
    difficulty: int = config.START_DIFFICULTY
    p_mastery: dict[str, float] = field(default_factory=dict)
    attempts: dict[str, int] = field(default_factory=dict)
    correct: dict[str, int] = field(default_factory=dict)
    mastered: set[str] = field(default_factory=set)
    inferred: set[str] = field(default_factory=set)
    gaps: set[str] = field(default_factory=set)
    parked: set[str] = field(default_factory=set)
    return_stack: list[str] = field(default_factory=list)
    consec_wrong: int = 0
    total_answered: int = 0
    round_answered: int = 0


    def mastery(self, skill: str) -> float:
        return self.p_mastery.get(skill, config.BKT["p_init"])

    def is_mastered(self, skill: str) -> bool:
        return skill in self.mastered or skill in self.inferred


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
    action: str

    next_skill: str
    next_difficulty: int
    reason: str
    gap_skill: Optional[str] = None
    round_over: bool = False
    breadcrumb: str = ""
    diagnosis: Optional[dict] = None


STUDENT_MESSAGES = {
    "level_up": "Your branch is getting stronger. This next one is a little tougher.",
    "stay": "Almost there. One more like this to lock it in.",
    "level_down": "Let's try one that's a bit gentler.",
    "advance": "A new branch is growing. Here's something fresh.",
    "backtrack": "Let's dig down and check the roots underneath this.",
    "return_up": "That root is firm now. Back up to where we were.",
    "retry": "One more like this, so we can be sure where the difficulty is.",
    "remediate": "Let's slow down and rebuild this root together.",
    "park": "We'll save this root for your teacher. Let's grow another branch.",
    "complete": "Your tree is in full bloom for now.",
}

def _name(sid: str) -> str:
    return kg.SKILLS[sid].name_ar if sid in kg.SKILLS else sid


def _breadcrumb_backtrack(struggling: str, prerequisite: str) -> str:
    return f"يبدو أن السبب في «{_name(struggling)}» يعود لدرس أسبق: لنراجع «{_name(prerequisite)}» أولاً."


def _breadcrumb_return_up(firmed_up: str, going_back_to: str) -> str:
    return f"أساس «{_name(firmed_up)}» أصبح متيناً الآن، لنعد إلى «{_name(going_back_to)}»."


def _breadcrumb_remediate(root_gap: str) -> str:
    return f"الأرجح أن «{_name(root_gap)}» هو الجذر وراء التعثّر. {kg.SKILLS[root_gap].intervention}"


def _breadcrumb_root(origin: str, root: str, confidence: str) -> str:
    if origin == root:
        return f"بناءً على إجاباتك، الأرجح أن الصعوبة في «{_name(root)}» نفسه (الثقة: {confidence}). {kg.SKILLS[root].intervention}"
    return (f"بناءً على إجاباتك، الأرجح أن تعثّرك في «{_name(origin)}» يعود إلى «{_name(root)}» (الثقة: {confidence}). "
            f"سنعالج «{_name(root)}» أولاً ثم نعود. {kg.SKILLS[root].intervention}")


def _breadcrumb_park(parked_gap: str, moving_to: str) -> str:
    return f"سنحفظ «{_name(parked_gap)}» لمعلمك، ونتابع الآن بدرس جديد: «{_name(moving_to)}»."


def _breadcrumb_advance(new_skill: str) -> str:
    return f"أحسنت! أصبحت جاهزاً لدرس جديد: «{_name(new_skill)}»."


def bkt_update(p_known: float, is_correct: bool) -> float:
    p = config.BKT
    if is_correct:
        num = p_known * (1 - p["p_slip"])
        den = num + (1 - p_known) * p["p_guess"]
    else:
        num = p_known * p["p_slip"]
        den = num + (1 - p_known) * (1 - p["p_guess"])
    posterior = num / den
    return posterior + (1 - posterior) * p["p_learn"]


def errors(state: StudentState, skill: str) -> int:
    return max(0, state.attempts.get(skill, 0) - state.correct.get(skill, 0))


def record_probe(state: StudentState, skill: str, is_correct: bool) -> None:
    state.attempts[skill] = state.attempts.get(skill, 0) + 1
    if is_correct:
        state.correct[skill] = state.correct.get(skill, 0) + 1
    state.p_mastery[skill] = bkt_update(state.mastery(skill), is_correct)


CONFIDENCE_AR = {dx.HIGH: "مرتفعة", dx.MEDIUM: "متوسطة", dx.LOW: "أولية"}


def believed_mastered(state: StudentState, skill: str) -> bool:
    """Mastered (or inferred) and not contradicted by fresh errors.

    Two fresh wrong answers drop the BKT estimate of a mastered skill below
    CONTEST_THRESHOLD (0.85 -> 0.53 -> 0.30), which re-opens it as a candidate root.
    One slip does not.
    """
    if not state.is_mastered(skill):
        return False
    return state.attempts.get(skill, 0) == 0 or state.mastery(skill) >= config.CONTEST_THRESHOLD


def evidence_of(state: StudentState) -> dict[str, dx.SkillEvidence]:
    return {
        s: dx.SkillEvidence(attempts=state.attempts.get(s, 0), correct=state.correct.get(s, 0),
                            mastered=believed_mastered(state, s))
        for s in kg.SKILLS
    }


def _counts(wrong: int, right: int) -> str:
    return f"{wrong} خاطئة و{right} صحيحة"


def explain_ar(verdict: dict) -> str:
    """One-paragraph Arabic explanation of a diagnosis verdict, built only from its evidence."""
    status = verdict.get("status")
    if status == dx.UNKNOWN_SKILL:
        return "هذا الدرس غير موجود في شجرة المنهج، فلا يمكن تشخيصه."
    if status == dx.NO_DIFFICULTY:
        return "لا توجد أدلة على تعثّر في هذا المسار."
    rows = {c["skill"]: c for c in verdict.get("candidates", [])}
    lead = verdict.get("leading_candidate")
    if status == dx.INSUFFICIENT:
        reason = verdict.get("reason")
        if reason == "mixed_evidence":
            o = max(verdict["observed"], key=lambda r: (r["wrong"] - r["right"], r["wrong"]))
            return (f"رصدنا خطأ في «{_name(o['skill'])}» ({_counts(o['wrong'], o['right'])})، لكن إجاباتك الصحيحة عليه "
                    "ما زالت تعادل الخاطئة أو تزيد، فلا نعدّه تعثّراً مستمراً بعد. نجمع أدلة أكثر.")
        if reason == "too_few_errors":
            return (f"الأدلة غير كافية بعد: {verdict['chain_errors']} خطأ في المسار، ونحتاج {verdict['min_chain_errors']} "
                    "على الأقل حتى لا نعدّ الزلّة فجوة. نجمع أدلة أكثر.")
        if reason == "root_needs_confirmation" and lead:
            c = rows[lead]
            return (f"المرشح الأقوى حتى الآن «{_name(lead)}» ({_counts(c['wrong'], c['right'])})، "
                    "لكن سؤالاً واحداً لا يكفي للحكم. نطرح سؤال تأكيد قبل تسمية الجذر.")
        blocked = [p for c in rows.values() if c["verdict"] == "prerequisite_unverified" for p in c["because"]]
        if blocked:
            return f"نتائج «{_name(blocked[0])}» غير حاسمة بعد، فلا يمكن استبعاده سبباً. نفحصه أولاً."
        return "الأدلة غير كافية بعد لتسمية جذر."
    root = verdict["root"]
    c = rows[root]
    parts = [f"اخترنا «{_name(root)}» لأن الإجابات عليه {_counts(c['wrong'], c['right'])}"]
    pres = verdict.get("prerequisites_checked", [])
    if pres:
        solid = "، ".join(f"«{_name(p['skill'])}» ({_counts(p['wrong'], p['right'])})" for p in pres)
        parts.append(f"وأساسه السابق ثابت: {solid}")
    else:
        parts.append("وهو درس أساسي لا متطلبات قبله")
    above = [s for s in verdict.get("path", []) if s != root and rows.get(s)]
    if above:
        parts.append("والتعثّر في " + "، ".join(f"«{_name(s)}»" for s in above) + " يُفسَّر به لأنه متطلب سابق")
    if verdict.get("competing"):
        parts.append("وتوجد فجوة محتملة أخرى في «" + "»، «".join(_name(s) for s in verdict["competing"]) + "» لذا خُفّضت الثقة")
    return "، ".join(parts) + "."


def assess_root(state: StudentState, origin: str) -> dict:
    """Full verdict, including 'insufficient_evidence', with an Arabic explanation."""
    verdict = dx.diagnose(kg.PREREQ_GRAPH, origin, evidence_of(state),
                          min_chain_errors=config.MIN_CHAIN_EVIDENCE, min_root_errors=config.MIN_ROOT_EVIDENCE)
    verdict["explanation"] = explain_ar(verdict)
    return verdict


def diagnose_root(state: StudentState, origin: str) -> Optional[dict]:
    """Return a named root-gap diagnosis, or None while the evidence is insufficient."""
    verdict = assess_root(state, origin)
    if verdict["status"] != dx.ROOT_IDENTIFIED:
        return None
    root = verdict["root"]
    path = verdict["path"]
    shown = list(path) + [p for p in kg.prerequisites(root) if p not in path]
    roles = {s: ("prerequisite" if s not in path else "root" if s == root else "origin" if s == origin else "path")
             for s in shown}
    return {
        "root": root,
        "origin": origin,
        "path": path,
        "confidence": CONFIDENCE_AR[verdict["confidence_level"]],
        "confidence_level": verdict["confidence_level"],
        "confidence_basis": verdict["confidence_basis"],
        "p_gap": round(1 - state.mastery(root), 2),
        "evidence": [
            {"skill": s, "wrong": errors(state, s), "right": state.correct.get(s, 0), "role": roles[s]}
            for s in shown if state.attempts.get(s, 0) > 0
        ],
        "candidates": verdict["candidates"],
        "competing": verdict["competing"],
        "explanation": verdict["explanation"],
        "intervention": kg.SKILLS[root].intervention,
    }


def investigation_origin(state: StudentState, local: str) -> str:
    """The lesson where the visible difficulty started for the current investigation.

    The return stack records, bottom first, every lesson the learner was moved away from while the
    engine descended toward prerequisites. The origin is the earliest of those for which `local`
    (the skill being probed now) is the same skill or one of its prerequisites; otherwise `local`.
    Diagnosing from this origin makes the reported path run from the struggling lesson down to
    the root (e.g. multiplying -> subtracting -> adding -> comparing -> absolute value).
    """
    if local not in kg.SKILLS:
        return local
    for skill in state.return_stack:
        if skill in kg.SKILLS and (skill == local or local in kg.ancestors(skill)):
            return skill
    return local


def declare_root(state: StudentState, diagnosis: dict) -> Decision:
    root, origin = diagnosis["root"], diagnosis["origin"]
    state.gaps.add(root)
    # Fresh direct evidence outranks an earlier (possibly inferred) mastery flag.
    state.mastered.discard(root)
    state.inferred.discard(root)
    if origin != root and origin not in state.return_stack:
        state.return_stack.append(origin)
    decision = _move(state, root, config.MIN_DIFFICULTY, "remediate",
                     f"Evidence points to '{root}' as the root gap behind '{origin}'.",
                     gap=root, breadcrumb=_breadcrumb_root(origin, root, diagnosis["confidence"]))
    decision.diagnosis = diagnosis
    return decision


def _move(state: StudentState, skill: str, difficulty: int, action: str,
          reason: str, gap: Optional[str] = None, breadcrumb: str = "") -> Decision:
    state.current_skill = skill
    state.difficulty = difficulty
    state.consec_wrong = 0
    return Decision(action, skill, difficulty, reason, gap_skill=gap, breadcrumb=breadcrumb)


def _infer_ancestors(state: StudentState, skill: str) -> None:
    for anc in kg.ancestors(skill):
        if anc not in state.mastered:
            state.inferred.add(anc)
        state.p_mastery[anc] = max(state.mastery(anc), config.MASTERY_THRESHOLD)
        state.gaps.discard(anc)


def _pick_frontier(state: StudentState, just_mastered: Optional[str] = None) -> Optional[str]:
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
        s in state.gaps,
        state.attempts.get(s, 0) > 0,
        s not in successors,
        kg.depth(s),
    ))
    return candidates[0]


def _route_after_mastery(state: StudentState, skill: str) -> Decision:
    while state.return_stack:
        target = state.return_stack.pop()
        if not state.is_mastered(target):
            return _move(state, target, config.MIN_DIFFICULTY, "return_up",
                         f"Root '{skill}' is solid; returning to '{target}'.",
                         breadcrumb=_breadcrumb_return_up(skill, target))
    nxt = _pick_frontier(state, just_mastered=skill)
    if nxt is None:
        return Decision("complete", skill, config.MAX_DIFFICULTY,
                        "Every reachable skill is mastered or parked.", round_over=True)
    return _move(state, nxt, config.MIN_DIFFICULTY, "advance",
                 f"'{skill}' mastered; unlocking '{nxt}'.",
                 breadcrumb=_breadcrumb_advance(nxt))


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


def _name_new_root(state: StudentState, skill: str, diagnosis: dict) -> Decision:
    if diagnosis["root"] != skill:
        return declare_root(state, diagnosis)
    state.gaps.add(skill)
    state.mastered.discard(skill)
    state.inferred.discard(skill)
    state.consec_wrong = 0
    state.difficulty = config.MIN_DIFFICULTY
    return Decision("remediate", skill, config.MIN_DIFFICULTY,
                    f"Evidence points to '{skill}' as a root gap.", gap_skill=skill,
                    breadcrumb=_breadcrumb_root(diagnosis["origin"], skill, diagnosis["confidence"]),
                    diagnosis=diagnosis)


def _handle_incorrect(state: StudentState) -> Decision:
    state.consec_wrong += 1
    skill, diff = state.current_skill, state.difficulty

    # Evidence first: once the accumulated evidence names a root that is not yet recorded, name it
    # now instead of only stepping the difficulty down (the verdict and the decision must agree).
    diagnosis = diagnose_root(state, investigation_origin(state, skill))
    if diagnosis is not None and diagnosis["root"] not in state.gaps:
        return _name_new_root(state, skill, diagnosis)

    if diff > config.MIN_DIFFICULTY and state.consec_wrong == 1:
        state.difficulty -= 1
        return Decision("level_down", skill, state.difficulty, f"Missed at level {diff}.")


    weak = [p for p in kg.prerequisites(skill) if not state.is_mastered(p)]
    if weak:
        target = min(weak, key=state.mastery)
        if not state.return_stack or state.return_stack[-1] != skill:
            state.return_stack.append(skill)
        return _move(state, target, config.PROBE_DIFFICULTY, "backtrack",
                     f"Struggling with '{skill}'; probing prerequisite '{target}'.",
                     breadcrumb=_breadcrumb_backtrack(skill, target))


    if diagnosis is None:
        state.difficulty = config.MIN_DIFFICULTY
        return Decision("retry", skill, config.MIN_DIFFICULTY,
                        "Not enough evidence yet to name a root gap; gathering more.")
    if diagnosis["root"] != skill:
        # The already-recorded root lies elsewhere: go back to remediating it, without recording
        # the same diagnosis a second time.
        decision = declare_root(state, diagnosis)
        decision.diagnosis = None
        return decision
    if state.consec_wrong >= 3:
        state.parked.add(skill)
        blocked = kg.descendants(skill)
        state.return_stack = [s for s in state.return_stack if s not in blocked and s != skill]
        nxt = _pick_frontier(state)
        if nxt is None:
            return Decision("complete", skill, config.MIN_DIFFICULTY,
                            f"Root gap '{skill}' parked; nothing else unlocked.",
                            gap_skill=skill, round_over=True)
        return _move(state, nxt, config.MIN_DIFFICULTY, "park",
                     f"Root gap '{skill}' needs the teacher; moving to '{nxt}'.", gap=skill,
                     breadcrumb=_breadcrumb_park(skill, nxt))
    state.difficulty = config.MIN_DIFFICULTY
    return Decision("remediate", skill, config.MIN_DIFFICULTY,
                    f"'{skill}' is already the named root gap; continuing remediation.", gap_skill=skill,
                    breadcrumb=_breadcrumb_remediate(skill))


def decide_next(state: StudentState, is_correct: bool) -> Decision:
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
    state.round_answered = 0
    state.consec_wrong = 0
    state.return_stack = []
    state.parked = set()
    if state.total_answered == 0:
        return
    nxt = _pick_frontier(state)
    if nxt is not None:
        state.current_skill, state.difficulty = nxt, config.MIN_DIFFICULTY


def skill_status(state: StudentState, skill: str) -> str:
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
    return sum(state.is_mastered(s) for s in kg.SKILLS) / len(kg.SKILLS)
