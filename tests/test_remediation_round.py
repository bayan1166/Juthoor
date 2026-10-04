"""Round pacing during remediation (adaptive_engine.round_over / finishing_remediation).

The metric is the engine's own BKT estimate, state.mastery(skill) (p_mastery). A round normally closes after
SESSION_LENGTH answers. While a named root is being remediated and its p_mastery is above
REMEDIATION_CONTINUE_P (0.95) but mastery is not yet confirmed (that still needs a correct answer at the top
difficulty with p >= MASTERY_THRESHOLD), the round stays open so a learner who is doing well keeps getting
questions. The extension is bounded and the engine's own exits still apply. BKT, thresholds and the
diagnosis are untouched.
"""
import random

from app.engine import adaptive_engine as ae
from app.engine import config
from app.services import session_core as sc


def _remediating(p: float, difficulty: int, answered: int, root="adding_integers") -> ae.StudentState:
    st = ae.StudentState(current_skill=root, difficulty=difficulty)
    st.mastered.update({"absolute_value", "comparing_integers"})
    st.gaps.add(root)
    st.p_mastery[root] = p
    st.attempts[root], st.correct[root] = 6, 3
    st.round_answered = answered
    st.total_answered = 20
    return st


def test_the_thresholds_and_bkt_are_unchanged():
    assert config.MASTERY_THRESHOLD == 0.85 and config.SESSION_LENGTH == 5
    assert config.BKT == {"p_init": 0.3, "p_slip": 0.1, "p_guess": 0.2, "p_learn": 0.2}
    assert config.REMEDIATION_CONTINUE_P == 0.95
    assert ae.ROUND_EXTENSION == config.MAX_DIFFICULTY - config.MIN_DIFFICULTY + 1


def test_above_95_percent_during_remediation_the_round_stays_open():
    st = _remediating(p=0.93, difficulty=2, answered=config.SESSION_LENGTH - 1)
    d = ae.decide_next(st, True)                      # 5th answer of the round, correct at level 2
    assert d.action == "level_up" and st.mastery("adding_integers") > 0.95
    assert st.round_answered == config.SESSION_LENGTH
    assert d.round_over is False and ae.round_over(st) is False, "keep asking: mastery is high but not confirmed"


def test_at_or_below_95_percent_the_round_closes_as_before():
    st = _remediating(p=0.40, difficulty=1, answered=config.SESSION_LENGTH - 1)
    d = ae.decide_next(st, True)
    assert st.mastery("adding_integers") <= 0.95
    assert d.round_over is True and ae.round_over(st) is True


def test_outside_remediation_the_round_closes_as_before():
    st = ae.StudentState(current_skill="adding_integers", difficulty=2)
    st.mastered.update({"absolute_value", "comparing_integers"})
    st.p_mastery["adding_integers"] = 0.97          # high, but not a named root gap
    st.round_answered = config.SESSION_LENGTH - 1
    d = ae.decide_next(st, True)
    assert d.round_over is True


def test_completion_still_ends_the_round_once_mastery_is_confirmed():
    st = _remediating(p=0.93, difficulty=2, answered=config.SESSION_LENGTH - 1)
    ae.decide_next(st, True)                          # level 2 -> 3, round kept open
    d = ae.decide_next(st, True)                      # correct at the top level -> mastered
    assert "adding_integers" in st.mastered and "adding_integers" not in st.gaps
    assert d.action in ("advance", "return_up", "complete")
    assert d.round_over is True, "the root is closed: the normal round end applies again"


def test_a_wrong_answer_that_drops_the_estimate_ends_the_extension():
    st = _remediating(p=0.93, difficulty=2, answered=config.SESSION_LENGTH - 1)
    ae.decide_next(st, True)
    assert not ae.round_over(st)
    ae.decide_next(st, False)
    ae.decide_next(st, False)                         # two misses drop p_mastery to 0.95 or below
    assert st.mastery("adding_integers") <= 0.95
    assert ae.round_over(st) is True


def test_the_extension_is_bounded_even_if_the_estimate_stays_high():
    st = _remediating(p=0.999, difficulty=2, answered=config.SESSION_LENGTH)
    limit = config.SESSION_LENGTH + ae.ROUND_EXTENSION
    for answered in range(config.SESSION_LENGTH, limit + 3):
        st.round_answered = answered
        assert ae.finishing_remediation(st)
        assert ae.round_over(st) is (answered >= limit), answered


def test_no_infinite_round_in_a_real_session_with_alternating_answers():
    """Correct, wrong, correct, wrong... never keeps one round open past the cap."""
    rng = random.Random(3)
    st = _remediating(p=0.99, difficulty=2, answered=0)
    sess = sc.Session(state=st)
    longest = 0
    for i in range(200):
        q = sc.serve(sess, rng)
        r = sc.grade(sess, q["correct_answer"] if i % 2 == 0 else "999999")
        longest = max(longest, st.round_answered)
        if r["round_over"]:
            sc.new_round(sess)
    assert longest <= config.SESSION_LENGTH + ae.ROUND_EXTENSION


def test_simulated_learners_get_questions_while_above_95_percent_and_still_finish():
    """Across many simulated remediations: whenever the round is kept open the root is above 95% and not yet
    mastered; every kept-open round ends; and every learner who keeps answering correctly reaches 'mastered'."""
    kept_open = 0
    for seed in range(40):
        rng = random.Random(seed)
        st = ae.StudentState()
        sess = sc.Session(state=st)
        pattern = "CCCCCC" + "W" * (4 + seed % 6) + "C" * 14
        for ch in pattern:
            q = sc.serve(sess, rng)
            r = sc.grade(sess, q["correct_answer"] if ch == "C" else "999999")
            if st.round_answered >= config.SESSION_LENGTH and not r["round_over"] and sess.plan is None:
                kept_open += 1
                root = st.current_skill
                assert root in st.gaps and not st.is_mastered(root) and st.mastery(root) > 0.95
            assert st.round_answered <= config.SESSION_LENGTH + ae.ROUND_EXTENSION
            if r["round_over"]:
                sc.new_round(sess)
        assert not st.gaps, f"seed {seed}: the named root was closed by the correct answers ({sorted(st.gaps)})"
    assert kept_open > 0, "the >95% rule is exercised by realistic remediation runs"
