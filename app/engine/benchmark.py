"""Reproducible diagnostic benchmark for the root-gap engine.

Synthetic learners with a *known* ground truth are driven through the real
``session_core`` (question serving + grading) and the real adaptive engine. Nothing
here knows the engine's thresholds: the learner only has "how likely am I to answer
a question on skill X correctly", and ground truth is the skill the learner lacks.

What this proves and what it does not
-------------------------------------
* It measures how the *decision logic* behaves under controlled answer noise
  (slips, lucky guesses). Same seed => identical results (determinism is measured).
* It does NOT measure accuracy on real students. Real accuracy needs teacher-labelled
  field data. Do not quote these numbers as classroom accuracy.

Scenario definitions
--------------------
``known_root``   learner lacks skill G (answers G and everything built on it with
                 probability ``p_gap_ok``) and is solid below (``p_below_ok``).
``lucky_correct``same, but the gap learner guesses right often (``p_gap_ok`` high).
``no_gap``       learner is solid everywhere (``p_below_ok`` everywhere); any
                 named root is a *false diagnosis*.
``noisy_*``      the same scenarios at lower ``p_below_ok`` (more slips).

Metrics (see ``summarise``)
---------------------------
root_accuracy_when_committed  correct root / (cases that named a root)
root_accuracy_overall         correct root / all gap cases
wrong_root_rate               wrong root / all gap cases
false_diagnosis_rate          no-gap cases that named any root / no-gap cases
premature_rate                named roots whose direct prerequisites had < 2
                              observed answers at declaration time / named roots
abstention_rate               gap cases that never named a root within the budget
determinism                   identical digest on two full runs
calibration                   accuracy per reported confidence level
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Optional

from app.engine import adaptive_engine as ae
from app.engine import config
from app.engine import knowledge_graph as kg
from app.services import session_core as sc

MAX_ANSWERS = 40
PREMATURE_MIN_PREREQ_OBS = 2


@dataclass(frozen=True)
class Scenario:
    name: str
    kind: str  # "gap" | "none"
    p_below_ok: float
    p_gap_ok: float = 0.2


SCENARIOS: tuple[Scenario, ...] = (
    Scenario("known_root_clean", "gap", 0.95, 0.15),
    Scenario("known_root_noisy", "gap", 0.85, 0.20),
    Scenario("lucky_correct", "gap", 0.90, 0.45),
    Scenario("no_gap_clean", "none", 0.95),
    Scenario("no_gap_noisy", "none", 0.85),
    Scenario("no_gap_very_noisy", "none", 0.80),
)


@dataclass
class CaseResult:
    scenario: str
    true_gap: Optional[str]
    origin: str
    seed: int
    answers: int
    named_root: Optional[str] = None
    confidence: Optional[str] = None
    premature: bool = False
    saw_insufficient: bool = False
    trace: list = field(default_factory=list)


def _learner_answer(q: dict, rng: random.Random, true_gap: Optional[str], sc_: Scenario) -> tuple[str, bool]:
    skill = q["skill"]
    in_gap_zone = true_gap is not None and (skill == true_gap or true_gap in kg.ancestors(skill))
    p_ok = sc_.p_gap_ok if in_gap_zone else sc_.p_below_ok
    if rng.random() < p_ok:
        return q["correct_answer"], True
    wrong = [o for o in q["options"] if o != q["correct_answer"]]
    traps = [t for t in q.get("traps", {}) if t in wrong]
    pool = traps or wrong
    return (rng.choice(pool) if pool else "x"), False


def _premature(state: ae.StudentState, root: str) -> bool:
    for p in kg.prerequisites(root):
        if state.is_mastered(p):
            continue
        if state.attempts.get(p, 0) < PREMATURE_MIN_PREREQ_OBS:
            return True
    return False


def run_case(scenario: Scenario, true_gap: Optional[str], origin: str, seed: int) -> CaseResult:
    rng = random.Random(seed)
    state = ae.StudentState(current_skill=origin, difficulty=config.START_DIFFICULTY)
    sess = sc.Session(state=state)
    res = CaseResult(scenario.name, true_gap, origin, seed, 0)
    for n in range(1, MAX_ANSWERS + 1):
        q = sc.serve(sess, rng)
        selected, _ok = _learner_answer(q, rng, true_gap, scenario)
        out = sc.grade(sess, selected)
        res.answers = n
        res.trace.append((q["skill"], out["action"], bool(out["is_correct"])))
        status = out.get("evidence_status")
        if status and status.get("status") == "insufficient_evidence":
            res.saw_insufficient = True
        d = out.get("diagnosis")
        if d:
            res.named_root = d["root"]
            res.confidence = d["confidence_level"]
            res.premature = _premature(state, d["root"])
            break
        if sess.pending is None and out.get("round_over"):
            sc.new_round(sess)
    return res


def _cases(reps: int) -> list[tuple[Scenario, Optional[str], str, int]]:
    order = kg.ordered_skills()
    cases = []
    for si, scn in enumerate(SCENARIOS):
        if scn.kind == "gap":
            for gi, g in enumerate(order):
                for oi in range(gi, len(order)):
                    for r in range(reps):
                        cases.append((scn, g, order[oi], si * 10_000_019 + gi * 1_000_003 + oi * 10_007 + r))
        else:
            for oi, origin in enumerate(order):
                for r in range(reps):
                    cases.append((scn, None, origin, si * 10_000_019 + 777 * 1_000_003 + oi * 10_007 + r))
    return cases


def run_all(reps: int = 5) -> list[CaseResult]:
    return [run_case(*c) for c in _cases(reps)]


def digest(results: list[CaseResult]) -> str:
    h = hashlib.sha256()
    for r in results:
        h.update(json.dumps([r.scenario, r.true_gap, r.origin, r.seed, r.answers, r.named_root,
                             r.confidence, r.trace], ensure_ascii=False).encode())
    return h.hexdigest()


def _pct(a: int, b: int) -> Optional[float]:
    return round(100.0 * a / b, 1) if b else None


def summarise(results: list[CaseResult]) -> dict:
    by: dict[str, dict] = {}
    for scn in SCENARIOS:
        rs = [r for r in results if r.scenario == scn.name]
        n = len(rs)
        named = [r for r in rs if r.named_root]
        if scn.kind == "gap":
            correct = [r for r in named if r.named_root == r.true_gap]
            wrong = [r for r in named if r.named_root != r.true_gap]
            by[scn.name] = {
                "kind": "gap", "cases": n, "named_root": len(named),
                "correct_root": len(correct), "wrong_root": len(wrong),
                "root_accuracy_when_committed_pct": _pct(len(correct), len(named)),
                "root_accuracy_overall_pct": _pct(len(correct), n),
                "wrong_root_rate_pct": _pct(len(wrong), n),
                "abstention_rate_pct": _pct(n - len(named), n),
                "premature_rate_pct": _pct(sum(r.premature for r in named), len(named)),
            }
        else:
            by[scn.name] = {
                "kind": "none", "cases": n, "false_diagnoses": len(named),
                "false_diagnosis_rate_pct": _pct(len(named), n),
                "abstention_rate_pct": _pct(n - len(named), n),
                "premature_rate_pct": _pct(sum(r.premature for r in named), len(named)),
            }
    cal: dict[str, dict] = {}
    for level in ("high", "medium", "low"):
        rs = [r for r in results if r.named_root and r.confidence == level and r.true_gap is not None]
        cal[level] = {"n": len(rs), "accuracy_pct": _pct(sum(r.named_root == r.true_gap for r in rs), len(rs))}
    all_named_nogap = [r for r in results if r.true_gap is None and r.named_root]
    return {"scenarios": by, "calibration_by_confidence_level": cal,
            "total_cases": len(results), "digest": digest(results),
            "false_diagnoses_total_no_gap": len(all_named_nogap)}


def report(reps: int = 5, check_determinism: bool = True) -> dict:
    first = run_all(reps)
    out = summarise(first)
    out["reps_per_cell"] = reps
    out["max_answers_budget"] = MAX_ANSWERS
    if check_determinism:
        out["deterministic"] = digest(run_all(reps)) == out["digest"]
    return out
