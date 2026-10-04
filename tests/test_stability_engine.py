"""Engine-level stability suite (pure; no database).

Covers: repeated workflows (10/50/100 and a long soak), many students interleaved and on threads
(no shared mutable state, no cross-student contamination), state round-trips through the same JSON
the database stores, and the state invariant checker after every answer.

NOT covered here (needs PostgreSQL + the API, see tests/test_stability_db.py):
concurrent submissions against the database, transaction rollback and restart persistence.
"""
import random
import threading

import pytest

from app.engine import adaptive_engine as ae
from app.engine import integrity
from app.engine import knowledge_graph as kg
from app.services import session_core as sc

ORDER = kg.ordered_skills()


def drive(seed, answers=60, accuracy=None, check=True, roundtrip=True):
    """One student's journey; returns (trace, final_state_json)."""
    rng = random.Random(seed)
    acc = accuracy if accuracy is not None else rng.choice([0.15, 0.4, 0.7, 0.95])
    state = ae.StudentState(current_skill=rng.choice(ORDER))
    sess = sc.Session(state=state)
    trace = []
    for n in range(answers):
        q = sc.serve(sess, rng)
        choice = q["correct_answer"] if rng.random() < acc else next(
            (o for o in q["options"] if o != q["correct_answer"]), "x")
        out = sc.grade(sess, choice)
        trace.append((q["skill"], q["difficulty"], out["action"], out["is_correct"],
                      (out["diagnosis"] or {}).get("root"), (out["evidence_status"] or {}).get("status")))
        if check:
            assert integrity.check_state(state) == [], (seed, n)
        if roundtrip:
            again = ae.StudentState.from_json(state.to_json())
            assert again.to_json() == state.to_json(), (seed, n)
            sess.state = state = again
        if sess.pending is None and out.get("round_over"):
            sc.new_round(sess)
    return trace, state.to_json()


@pytest.mark.parametrize("runs", [10, 50, 100])
def test_core_workflow_repeated_without_failure(runs):
    for seed in range(runs):
        drive(seed, answers=40)


def test_same_seed_gives_identical_journey():
    assert drive(7) == drive(7)


def test_one_long_soak_run_keeps_state_valid():
    trace, raw = drive(99, answers=2500, accuracy=0.6, check=True, roundtrip=False)
    assert len(trace) == 2500
    assert integrity.check_state(ae.StudentState.from_json(raw)) == []


def test_interleaved_students_do_not_contaminate_each_other():
    seeds = list(range(20))
    solo = {s: drive(s, answers=30)[0] for s in seeds}
    rngs = {s: random.Random(s) for s in seeds}
    # replay interleaved, using the same per-student rng stream as drive()
    accs, states, sessions, got = {}, {}, {}, {s: [] for s in seeds}
    for s in seeds:
        r = random.Random(s)
        accs[s] = r.choice([0.15, 0.4, 0.7, 0.95])
        states[s] = ae.StudentState(current_skill=r.choice(ORDER))
        sessions[s] = sc.Session(state=states[s])
        rngs[s] = r
    for _ in range(30):
        for s in seeds:
            r, sess = rngs[s], sessions[s]
            q = sc.serve(sess, r)
            choice = q["correct_answer"] if r.random() < accs[s] else next(
                (o for o in q["options"] if o != q["correct_answer"]), "x")
            out = sc.grade(sess, choice)
            got[s].append((q["skill"], q["difficulty"], out["action"], out["is_correct"],
                           (out["diagnosis"] or {}).get("root"), (out["evidence_status"] or {}).get("status")))
            st = ae.StudentState.from_json(sess.state.to_json())
            sess.state = states[s] = st
            if sess.pending is None and out.get("round_over"):
                sc.new_round(sess)
    for s in seeds:
        assert got[s] == solo[s], f"student {s} diverged when interleaved"


@pytest.mark.parametrize("threads", [5, 10, 20])
def test_threaded_students_match_their_solo_journeys(threads):
    solo = {s: drive(s, answers=30)[0] for s in range(threads)}
    results, errors = {}, []

    def work(s):
        try:
            results[s] = drive(s, answers=30)[0]
        except Exception as exc:  # pragma: no cover - failure path
            errors.append((s, repr(exc)))

    ts = [threading.Thread(target=work, args=(s,)) for s in range(threads)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errors, errors
    assert results == solo


def test_truncated_or_corrupt_persisted_state_raises_a_clear_error_not_a_silent_default():
    good = ae.StudentState().to_json()
    for bad in (good[: len(good) // 2], "", "null", "[]"):
        with pytest.raises((ValueError, TypeError, AttributeError)):
            ae.StudentState.from_json(bad)


def test_invariant_checker_detects_real_corruption():
    st = ae.StudentState()
    st.attempts["absolute_value"] = 1
    st.correct["absolute_value"] = 3
    st.p_mastery["absolute_value"] = 1.0
    st.mastered.add("nope")
    st.difficulty = 9
    problems = " | ".join(integrity.check_state(st))
    for needle in ("exceeds attempts", "strictly inside", "unknown skill 'nope'", "difficulty 9"):
        assert needle in problems
