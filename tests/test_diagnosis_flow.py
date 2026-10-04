import random

import pytest

from app.engine import adaptive_engine as ae
from app.engine import config
from app.engine import knowledge_graph as kg
from app.services import session_core as sc

BASICS = {"absolute_value", "comparing_integers"}


def misconception(q):
    """A realistic wrong answer the bank links to a named misconception (never a nonsense string)."""
    assert q["traps"], q["question"]
    return next(iter(q["traps"]))
SEEDS = range(60)


def play(start, mastered, policy, seed, limit=40):
    rng = random.Random(seed)
    state = ae.StudentState(current_skill=start, difficulty=1)
    state.mastered.update(mastered)
    sess = sc.Session(state=state)
    asked = []
    for index in range(limit):
        q = sc.serve(sess, rng)
        asked.append(q["skill"])
        ok = policy(q, index)
        before = set(state.gaps)
        result = sc.grade(sess, q["correct_answer"] if ok else misconception(q))
        found = set(state.gaps) - before
        if found:
            return index + 1, sorted(found)[0], result, asked, sess
        if result["round_over"]:
            sc.new_round(sess)
    return None, None, None, asked, sess


@pytest.mark.parametrize("seed", SEEDS)
def test_omar_story_names_addition_as_the_root_within_seven_answers(seed):
    count, root, result, asked, _ = play("mult_div_integers", BASICS, lambda q, i: False, seed)
    assert root == "adding_integers" and 5 <= count <= 7
    diag = result["diagnosis"]
    assert diag["origin"] == "mult_div_integers" and diag["root"] == "adding_integers"
    assert diag["path"][0] == "mult_div_integers" and diag["path"][-1] == "adding_integers"
    assert diag["confidence"] in {"أولية", "متوسطة", "مرتفعة"} and 0 <= diag["p_gap"] <= 1
    # The root is only named after a confirmation probe: at least two wrong answers on it.
    root_row = next(e for e in diag["evidence"] if e["skill"] == "adding_integers")
    assert root_row["wrong"] >= 2 and diag["confidence_level"] in {"medium", "high"}
    assert "adding_integers" in diag["explanation"] or "جمع" in diag["explanation"]
    assert all(e["wrong"] >= 0 and e["right"] >= 0 for e in diag["evidence"]) and diag["evidence"]
    assert result["action"] == "remediate" and result["gap_skill"] == "adding_integers"
    assert "الأرجح" in result["breadcrumb"]


@pytest.mark.parametrize("seed", SEEDS)
def test_one_or_two_slips_never_create_a_gap(seed):
    for slips in ({0}, {0, 2}, {1, 4}):
        count, root, _, _, sess = play("adding_integers", BASICS, lambda q, i, s=slips: i not in s, seed, limit=12)
        assert root is None and not sess.state.gaps


@pytest.mark.parametrize("seed", SEEDS)
def test_a_fresh_student_needs_three_errors_before_a_gap_is_named(seed):
    count, root, result, _, _ = play("absolute_value", set(), lambda q, i: False, seed)
    assert (count, root) == (3, "absolute_value")
    assert result["diagnosis"]["path"] == ["absolute_value"]


@pytest.mark.parametrize("seed", SEEDS)
def test_failing_only_the_current_lesson_blames_that_lesson_not_a_prerequisite(seed):
    solid = BASICS | {"adding_integers", "subtracting_integers"}
    count, root, result, _, _ = play("mult_div_integers", solid, lambda q, i: q["skill"] != "mult_div_integers", seed)
    assert root == "mult_div_integers" and result["diagnosis"]["origin"] == "mult_div_integers"


@pytest.mark.parametrize("seed", range(20))
def test_unmastered_prerequisites_are_probed_before_blaming_the_lesson(seed):
    count, root, result, asked, _ = play("mult_div_integers", BASICS, lambda q, i: q["skill"] != "mult_div_integers", seed)
    assert root == "mult_div_integers"
    assert "subtracting_integers" in asked or "adding_integers" in asked


def test_diagnosis_requires_corroborating_evidence_threshold():
    state = ae.StudentState(current_skill="adding_integers", difficulty=1)
    state.mastered.update(BASICS)
    ae.record_probe(state, "adding_integers", False)
    ae.record_probe(state, "adding_integers", False)
    assert ae.diagnose_root(state, "adding_integers") is None
    ae.record_probe(state, "adding_integers", False)
    found = ae.diagnose_root(state, "adding_integers")
    # Prerequisites are only *assumed* mastered (never observed), so confidence stays medium.
    assert found["root"] == "adding_integers" and found["confidence"] == "متوسطة"
    assert "prerequisites_assumed" in found["confidence_basis"]
    ae.record_probe(state, "comparing_integers", True)
    found = ae.diagnose_root(state, "adding_integers")
    assert found["confidence"] == "مرتفعة" and found["confidence_level"] == "high"
    assert config.MIN_CHAIN_EVIDENCE == 3


def test_a_passed_prerequisite_probe_stops_the_descent():
    # Behaviour change (evidence policy, see docs/COMPETITIVE_ADVANTAGE.md): a single correct answer used to
    # make a prerequisite "solid". One lucky answer is not evidence (a learner who lacks the skill
    # still guesses right ~20% of the time), so two observed correct answers are now required.
    state = ae.StudentState(current_skill="mult_div_integers", difficulty=1)
    state.mastered.update(BASICS)
    for _ in range(3):
        ae.record_probe(state, "mult_div_integers", False)
    assert ae.diagnose_root(state, "mult_div_integers") is None
    for _ in range(config.MIN_SOLID_EVIDENCE):
        ae.record_probe(state, "subtracting_integers", True)
        ae.record_probe(state, "adding_integers", True)
    found = ae.diagnose_root(state, "mult_div_integers")
    assert found["root"] == "mult_div_integers"


def test_one_lucky_correct_prerequisite_answer_does_not_clear_the_prerequisite():
    # Regression: the old rule (attempts > 0 and wrong == 0) let one lucky correct answer make a
    # prerequisite solid, so the engine blamed a lesson built on a gap it had not ruled out.
    state = ae.StudentState(current_skill="mult_div_integers", difficulty=1)
    state.mastered.update(BASICS)
    for _ in range(3):
        ae.record_probe(state, "mult_div_integers", False)
    ae.record_probe(state, "subtracting_integers", True)
    ae.record_probe(state, "adding_integers", True)
    assert ae.diagnose_root(state, "mult_div_integers") is None
    verdict = ae.assess_root(state, "mult_div_integers")
    assert verdict["status"] == "insufficient_evidence"


def test_after_a_root_is_named_the_student_is_routed_to_it_and_back_up():
    count, root, result, _, sess = play("mult_div_integers", BASICS, lambda q, i: False, 5)
    state = sess.state
    assert state.current_skill == "adding_integers" and sess.plan is None
    assert state.return_stack and state.return_stack[0] == "mult_div_integers"
    rng = random.Random(1)
    returned = False
    for _ in range(60):
        q = sc.serve(sess, rng)
        result = sc.grade(sess, q["correct_answer"])
        if result["action"] == "return_up":
            returned = True
            break
        if result["round_over"]:
            sc.new_round(sess)
    assert returned and "adding_integers" not in state.gaps and state.is_mastered("adding_integers")


def test_probe_answers_update_mastery_and_attempt_counts():
    state = ae.StudentState(current_skill="mult_div_integers", difficulty=1)
    before = state.mastery("adding_integers")
    ae.record_probe(state, "adding_integers", False)
    assert state.attempts["adding_integers"] == 1 and state.correct.get("adding_integers", 0) == 0
    assert state.mastery("adding_integers") < before + 0.0001 or state.mastery("adding_integers") < 0.3
    ae.record_probe(state, "adding_integers", True)
    assert state.correct["adding_integers"] == 1


def test_every_skill_in_the_graph_has_a_reachable_root_by_descent():
    for skill in kg.SKILLS:
        chain = {skill, *kg.ancestors(skill)}
        assert any(not kg.prerequisites(s) for s in chain)
