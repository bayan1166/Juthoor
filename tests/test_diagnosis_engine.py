"""Scenario tests for the domain-agnostic diagnosis engine (app/engine/diagnosis.py).

Scenarios covered here (see README "Testing"): C evidence confirms a gap, D insufficient
evidence, K invalid graph / unknown skill, L a non-mathematics graph, J repeated execution,
plus branching graphs with competing candidate roots and honest confidence levels.
"""
import random

import pytest

from app.engine import adaptive_engine as ae
from app.engine import diagnosis as dx
from app.engine import knowledge_graph as kg
from app.services import session_core as sc

E = dx.SkillEvidence

# A small reading-literacy graph with a branch: comprehension needs both fluent word
# reading and vocabulary. Nothing in the engine knows this is not mathematics.
READING = {
    "letter_sounds": (),
    "decoding": ("letter_sounds",),
    "word_reading": ("decoding",),
    "fluency": ("word_reading",),
    "vocabulary": (),
    "comprehension": ("fluency", "vocabulary"),
}


@pytest.fixture
def reading():
    return dx.PrereqGraph(READING)


# --- K: graph validation ---------------------------------------------------------------

def test_valid_graph_has_no_problems():
    assert dx.validate_prerequisites(READING) == []
    assert dx.validate_prerequisites({s.id: s.prerequisites for s in kg.SKILLS.values()}) == []


@pytest.mark.parametrize("bad, fragment", [
    ({"a": ("ghost",)}, "unknown prerequisite 'ghost'"),
    ({"a": ("a",)}, "lists itself"),
    ({"a": (), "b": ("a", "a")}, "duplicate prerequisite"),
    ({"a": ("c",), "b": ("a",), "c": ("b",)}, "cycle"),
])
def test_invalid_graphs_are_rejected_with_a_reason(bad, fragment):
    problems = dx.validate_prerequisites(bad)
    assert problems and any(fragment in p for p in problems)
    with pytest.raises(dx.GraphError):
        dx.PrereqGraph(bad)


def test_unknown_origin_is_a_safe_verdict_not_a_crash(reading):
    verdict = dx.diagnose(reading, "astrophysics", {})
    assert verdict["status"] == dx.UNKNOWN_SKILL and verdict["root"] is None
    state = ae.StudentState()
    assert ae.diagnose_root(state, "not_a_skill") is None
    assert "غير موجود" in ae.assess_root(state, "not_a_skill")["explanation"]


def test_branching_traversal(reading):
    assert reading.ancestors("comprehension") == {"fluency", "word_reading", "decoding", "letter_sounds", "vocabulary"}
    assert reading.depth("comprehension") == 4 and reading.depth("vocabulary") == 0


# --- L: non-mathematics graph through the same engine --------------------------------

def test_reading_graph_root_is_found_below_the_visible_difficulty(reading):
    evidence = {
        "comprehension": E(4, 0),
        "fluency": E(2, 0),
        "word_reading": E(2, 0),
        "decoding": E(3, 0),
        "letter_sounds": E(3, 3),
        "vocabulary": E(2, 2),
    }
    verdict = dx.diagnose(reading, "comprehension", evidence)
    assert verdict["status"] == dx.ROOT_IDENTIFIED and verdict["root"] == "decoding"
    assert verdict["path"] == ["comprehension", "fluency", "word_reading", "decoding"]
    assert verdict["confidence_level"] == dx.HIGH
    rows = {c["skill"]: c for c in verdict["candidates"]}
    assert rows["fluency"]["verdict"] == "explained_by_prerequisite"


def test_reading_graph_blames_the_lesson_when_every_prerequisite_is_solid(reading):
    evidence = {"comprehension": E(3, 0), "fluency": E(2, 2), "vocabulary": E(2, 2)}
    verdict = dx.diagnose(reading, "comprehension", evidence)
    assert verdict["root"] == "comprehension" and verdict["path"] == ["comprehension"]


# --- competing candidates on separate branches ----------------------------------------

def test_two_failing_branches_pick_the_stronger_evidence_and_lower_confidence(reading):
    evidence = {
        "comprehension": E(3, 0),
        "fluency": E(4, 0), "word_reading": E(2, 2),
        "vocabulary": E(2, 0),
    }
    verdict = dx.diagnose(reading, "comprehension", evidence)
    assert verdict["root"] == "fluency"
    assert verdict["competing"] == ["vocabulary"]
    assert verdict["confidence_level"] == dx.MEDIUM and "competing_candidates" in verdict["confidence_basis"]


# --- D: insufficient evidence is a first-class outcome --------------------------------

def test_one_or_two_errors_are_not_a_gap(reading):
    verdict = dx.diagnose(reading, "decoding", {"decoding": E(2, 0), "letter_sounds": E(2, 2)})
    assert verdict["status"] == dx.INSUFFICIENT and verdict["reason"] == "too_few_errors"
    assert verdict["leading_candidate"] == "decoding"


def test_a_single_wrong_probe_needs_confirmation(reading):
    evidence = {"fluency": E(3, 0), "word_reading": E(1, 0), "decoding": E(2, 2)}
    verdict = dx.diagnose(reading, "fluency", evidence)
    assert verdict["status"] == dx.INSUFFICIENT and verdict["reason"] == "root_needs_confirmation"
    assert verdict["leading_candidate"] == "word_reading"


def test_untested_prerequisite_blocks_a_verdict(reading):
    verdict = dx.diagnose(reading, "word_reading", {"word_reading": E(4, 0)})
    assert verdict["status"] == dx.INSUFFICIENT and verdict["reason"] == "prerequisites_unverified"
    rows = {c["skill"]: c for c in verdict["candidates"]}
    assert rows["word_reading"]["because"] == ["decoding"]


def test_no_errors_means_no_difficulty(reading):
    assert dx.diagnose(reading, "fluency", {"fluency": E(3, 3)})["status"] == dx.NO_DIFFICULTY


# --- C: evidence and honest confidence ------------------------------------------------

def test_confidence_levels_follow_documented_rule():
    assert dx.confidence_level(E(3, 0), [E(2, 2)])[0] == dx.HIGH
    assert dx.confidence_level(E(3, 0), [E(0, 0, mastered=True)])[0] == dx.MEDIUM
    assert dx.confidence_level(E(5, 2), [E(2, 2)])[0] == dx.MEDIUM
    assert dx.confidence_level(E(4, 2), [E(2, 2)])[0] == dx.LOW
    assert dx.confidence_level(E(1, 0), [E(2, 2)])[0] == dx.LOW


def test_a_believed_mastered_skill_is_never_blamed(reading):
    evidence = {"fluency": E(3, 0), "word_reading": E(3, 0, mastered=True), "decoding": E(2, 2)}
    verdict = dx.diagnose(reading, "fluency", evidence)
    assert verdict["root"] == "fluency"


def test_old_errors_on_a_remediated_skill_do_not_reopen_it():
    state = ae.StudentState(current_skill="adding_integers")
    for _ in range(5):
        ae.record_probe(state, "absolute_value", False)
    for _ in range(3):
        ae.record_probe(state, "absolute_value", True)
    state.mastered.add("absolute_value")
    state.p_mastery["absolute_value"] = 0.95
    state.mastered.add("comparing_integers")
    for _ in range(3):
        ae.record_probe(state, "adding_integers", False)
    assert ae.diagnose_root(state, "adding_integers")["root"] == "adding_integers"


def test_two_fresh_errors_reopen_a_mastered_prerequisite_but_one_slip_does_not():
    state = ae.StudentState(current_skill="adding_integers")
    state.mastered.update({"absolute_value", "comparing_integers"})
    state.p_mastery["comparing_integers"] = 0.85
    for _ in range(3):
        ae.record_probe(state, "adding_integers", False)
    ae.record_probe(state, "comparing_integers", False)
    assert ae.diagnose_root(state, "adding_integers")["root"] == "adding_integers"
    ae.record_probe(state, "comparing_integers", False)
    found = ae.diagnose_root(state, "adding_integers")
    assert found["root"] == "comparing_integers" and found["path"][-1] == "comparing_integers"


def test_named_diagnosis_carries_evidence_explanation_and_intervention():
    state = ae.StudentState(current_skill="mult_div_integers")
    state.mastered.update({"absolute_value", "comparing_integers"})
    ae.record_probe(state, "comparing_integers", True)
    for skill, wrong in (("mult_div_integers", 3), ("subtracting_integers", 1), ("adding_integers", 2)):
        for _ in range(wrong):
            ae.record_probe(state, skill, False)
    found = ae.diagnose_root(state, "mult_div_integers")
    assert found["root"] == "adding_integers"
    assert found["path"] == ["mult_div_integers", "subtracting_integers", "adding_integers"]
    roles = {e["skill"]: e["role"] for e in found["evidence"]}
    assert roles == {"mult_div_integers": "origin", "subtracting_integers": "path",
                     "adding_integers": "root", "comparing_integers": "prerequisite"}
    assert "جمع الأعداد الصحيحة" in found["explanation"] and found["intervention"]


# --- J: repeated execution is deterministic -------------------------------------------

def test_same_evidence_gives_the_same_verdict(reading):
    evidence = {"comprehension": E(4, 0), "fluency": E(2, 0), "word_reading": E(2, 0),
                "decoding": E(3, 0), "letter_sounds": E(3, 3), "vocabulary": E(2, 2)}
    first = dx.diagnose(reading, "comprehension", evidence)
    for _ in range(20):
        assert dx.diagnose(reading, "comprehension", dict(reversed(list(evidence.items())))) == first


# --- session level: B/D/E/F through the real practice session -------------------------

def _omar(seed):
    state = ae.StudentState(current_skill="mult_div_integers", difficulty=1)
    state.mastered.update({"absolute_value", "comparing_integers"})
    return sc.Session(state=state), random.Random(seed)


def test_wrong_answers_report_evidence_status_until_a_root_is_named():
    sess, rng = _omar(3)
    statuses = []
    for _ in range(10):
        q = sc.serve(sess, rng)
        r = sc.grade(sess, next(iter(q["traps"])))
        if r["diagnosis"]:
            assert r["evidence_status"] is None
            break
        statuses.append(r["evidence_status"])
    assert statuses and all(s["status"] == dx.INSUFFICIENT and s["message"] for s in statuses)
    assert any(s.get("confirming") == "adding_integers" for s in statuses)


def test_correct_answer_has_no_evidence_status():
    sess, rng = _omar(4)
    q = sc.serve(sess, rng)
    assert sc.grade(sess, q["correct_answer"])["evidence_status"] is None


def _diagnose(sess, rng):
    for _ in range(12):
        q = sc.serve(sess, rng)
        r = sc.grade(sess, next(iter(q["traps"])))
        if r["diagnosis"]:
            return r
    raise AssertionError("no diagnosis")


def test_remediation_then_retry_of_the_original_lesson_succeeds():
    sess, rng = _omar(7)
    _diagnose(sess, rng)
    assert sess.state.current_skill == "adding_integers" and "adding_integers" in sess.state.gaps
    seen_origin = False
    for _ in range(40):
        q = sc.serve(sess, rng)
        seen_origin = seen_origin or q["skill"] == "mult_div_integers"
        r = sc.grade(sess, q["correct_answer"])
        if r["round_over"]:
            sc.new_round(sess)
        if "mult_div_integers" in sess.state.mastered:
            break
    assert "adding_integers" not in sess.state.gaps and sess.state.is_mastered("adding_integers")
    assert seen_origin and "mult_div_integers" in sess.state.mastered
    assert sess.state.mastery("adding_integers") > 0.85


def test_wrong_answers_during_remediation_keep_the_gap_and_do_not_duplicate_it():
    sess, rng = _omar(8)
    _diagnose(sess, rng)
    before = sess.state.mastery("adding_integers")
    diagnoses = 0
    for _ in range(6):
        q = sc.serve(sess, rng)
        r = sc.grade(sess, next(iter(q["traps"])))
        diagnoses += bool(r["diagnosis"])
        if r["round_over"]:
            sc.new_round(sess)
    assert "adding_integers" in sess.state.gaps or "adding_integers" in sess.state.parked
    assert sess.state.mastery("adding_integers") <= before
    assert diagnoses == 0


# --- break-it: random learners never crash the session or violate the evidence rules ---

@pytest.mark.parametrize("start", sorted(kg.SKILLS))
def test_random_learners_keep_engine_invariants(start):
    from app.engine import config
    for seed in range(25):
        rng = random.Random(seed)
        p_right = rng.choice([0.0, 0.2, 0.5, 0.8, 1.0])
        state = ae.StudentState(current_skill=start, difficulty=1)
        sess = sc.Session(state=state)
        named = []
        for _ in range(60):
            q = sc.serve(sess, rng)
            assert q["skill"] in kg.SKILLS and q["question"]
            pick = q["correct_answer"] if rng.random() < p_right else rng.choice(["zzz", "", "0", q["correct_answer"] + "1"])
            r = sc.grade(sess, pick or "x")
            assert all(0.0 <= v <= 1.0 for v in state.p_mastery.values())
            assert state.gaps <= set(kg.SKILLS)
            if r["diagnosis"]:
                d = r["diagnosis"]
                root_row = next(e for e in d["evidence"] if e["skill"] == d["root"])
                assert root_row["wrong"] >= config.MIN_ROOT_EVIDENCE
                assert d["confidence_level"] in {"high", "medium", "low"} and d["explanation"]
                assert d["root"] in {d["origin"], *kg.ancestors(d["origin"])}
                named.append(d["root"])
            if r["round_over"]:
                sc.new_round(sess)
        # A root is re-named only after it was remediated (mastered) and then failed again.
        assert all(named.count(x) <= 2 for x in named), named


# --- the learner-facing workflow stage follows the real loop ------------------------------

def test_workflow_stage_walks_the_whole_core_loop():
    from app.services import workflow as wf
    sess, rng = _omar(11)
    stages, latest = [], None
    for _ in range(60):
        q = sc.serve(sess, rng)
        diagnosed = latest is not None
        trap = next(iter(q["traps"]))
        r = sc.grade(sess, q["correct_answer"] if diagnosed else trap)
        if r["diagnosis"]:
            latest = {"origin": r["diagnosis"]["origin"], "root": r["diagnosis"]["root"],
                      "confidence": r["diagnosis"]["confidence"]}
        w = wf.workflow(sess.state, latest, r, q["skill"])
        if not stages or stages[-1] != w["stage"]:
            stages.append(w["stage"])
        if r["round_over"]:
            sc.new_round(sess)
        if w["stage"] == "resolved":
            break
    assert stages[0] == "gathering_evidence"
    assert stages.index("root_identified") < stages.index("remediation") < stages.index("retry") < stages.index("resolved")
    final = wf.workflow(sess.state, latest)
    assert final["stage"] == "resolved" and final["root"] == "adding_integers" and final["origin"] == "mult_div_integers"


def test_workflow_stage_without_any_diagnosis_is_practising():
    from app.services import workflow as wf
    w = wf.workflow(ae.StudentState())
    assert w["stage"] == "practising" and w["step"] == 0 and w["root"] is None


# --- graph shapes: linear, diamond (shared prerequisite) -------------------------------------

LINEAR = {"a": (), "b": ("a",), "c": ("b",), "d": ("c",)}
DIAMOND = {"base": (), "left": ("base",), "right": ("base",), "top": ("left", "right")}


def test_linear_graph_path_runs_from_the_struggling_skill_to_the_root():
    g = dx.PrereqGraph(LINEAR)
    verdict = dx.diagnose(g, "d", {"d": E(2, 0), "c": E(1, 0), "b": E(2, 0), "a": E(3, 3)})
    assert verdict["root"] == "b" and verdict["path"] == ["d", "c", "b"]
    assert [c["verdict"] for c in verdict["candidates"]] == ["root", "explained_by_prerequisite", "explained_by_prerequisite"]


def test_diamond_graph_blames_only_the_failing_branch():
    g = dx.PrereqGraph(DIAMOND)
    evidence = {"top": E(3, 0), "left": E(3, 0), "right": E(2, 2), "base": E(2, 2)}
    verdict = dx.diagnose(g, "top", evidence)
    assert verdict["root"] == "left" and verdict["path"] == ["top", "left"]
    assert verdict["competing"] == []


def test_diamond_graph_shared_prerequisite_explains_both_branches():
    g = dx.PrereqGraph(DIAMOND)
    evidence = {"top": E(3, 0), "left": E(1, 0), "right": E(1, 0), "base": E(2, 0)}
    verdict = dx.diagnose(g, "top", evidence)
    assert verdict["root"] == "base"
    assert set(verdict["path"]) == {"top", "left", "right", "base"} and verdict["path"][0] == "top"
    assert verdict["path"][-1] == "base"


def test_diamond_with_an_untested_branch_waits_for_evidence():
    g = dx.PrereqGraph(DIAMOND)
    verdict = dx.diagnose(g, "top", {"top": E(4, 0), "left": E(2, 2), "base": E(2, 2)})
    assert verdict["status"] == dx.INSUFFICIENT and verdict["reason"] == "prerequisites_unverified"
    assert {c["skill"]: c["because"] for c in verdict["candidates"]}["top"] == ["right"]


def test_math_graph_paths_follow_real_prerequisite_edges():
    for skill in kg.SKILLS:
        for pre in kg.prerequisites(skill):
            assert pre in kg.ancestors(skill) and kg.depth(pre) < kg.depth(skill)
    assert kg.PREREQ_GRAPH.ancestors("mult_div_integers") == {
        "subtracting_integers", "adding_integers", "comparing_integers", "absolute_value"}


def test_investigation_origin_is_the_lesson_where_the_struggle_started():
    state = ae.StudentState(current_skill="adding_integers")
    state.return_stack = ["mult_div_integers", "subtracting_integers"]
    assert ae.investigation_origin(state, "adding_integers") == "mult_div_integers"
    assert ae.investigation_origin(state, "fractions_addsub") == "fractions_addsub"
    assert ae.investigation_origin(state, "unknown") == "unknown"
    assert ae.investigation_origin(ae.StudentState(), "adding_integers") == "adding_integers"


# --- evidence states progress honestly (regression: preflight fresh-learner scenario) ------

def test_errors_without_a_failing_skill_are_mixed_evidence_not_no_difficulty(reading):
    verdict = dx.diagnose(reading, "decoding", {"decoding": E(2, 1), "letter_sounds": E(1, 1)})
    assert verdict["status"] == dx.INSUFFICIENT and verdict["reason"] == "mixed_evidence"
    assert {o["skill"] for o in verdict["observed"]} == {"decoding"}
    state = ae.StudentState(current_skill="absolute_value")
    ae.record_probe(state, "absolute_value", True)
    ae.record_probe(state, "absolute_value", False)
    assessed = ae.assess_root(state, "absolute_value")
    assert assessed["reason"] == "mixed_evidence" and "القيمة المطلقة" in assessed["explanation"]


def test_a_wrong_answer_after_a_right_one_reports_insufficient_evidence():
    state = ae.StudentState()
    sess = sc.Session(state=state)
    rng = random.Random(1)
    q = sc.serve(sess, rng)
    assert sc.grade(sess, q["correct_answer"])["is_correct"]
    q = sc.serve(sess, rng)
    r = sc.grade(sess, next(iter(q["traps"])))
    assert r["diagnosis"] is None
    assert r["evidence_status"]["status"] == dx.INSUFFICIENT and r["evidence_status"]["reason"] == "mixed_evidence"


def test_sufficient_evidence_names_the_root_instead_of_only_stepping_down():
    state = ae.StudentState(current_skill="absolute_value", difficulty=1)
    actions = [ae.decide_next(state, ok).action for ok in (False, False, True)]
    assert actions == ["retry", "retry", "level_up"] and state.difficulty == 2
    d = ae.decide_next(state, False)  # 3 wrong vs 1 right on a lesson with no prerequisites
    assert d.action == "remediate" and d.diagnosis["root"] == "absolute_value" and "absolute_value" in state.gaps


@pytest.mark.parametrize("seed", range(40))
def test_wrong_answers_never_report_no_difficulty_or_an_undeclared_root(seed):
    """A learner picking displayed options at random (as scripts/preflight.py does): every wrong
    answer before the root is named reports insufficient evidence, and once the evidence names a
    root the engine declares it on that same answer."""
    rng, pick = random.Random(seed), random.Random(seed * 7 + 1)
    state = ae.StudentState()
    sess = sc.Session(state=state)
    for _ in range(30):
        q = sc.serve(sess, rng)
        r = sc.grade(sess, pick.choice(q["options"]) if q["options"] else "0")
        if r["diagnosis"]:
            break
        if not r["is_correct"]:
            assert r["evidence_status"]["status"] == dx.INSUFFICIENT, r["evidence_status"]
        if r["round_over"]:
            sc.new_round(sess)
