"""The practice session logic (pure Python, no database): diagnosis + remediation."""
import random

from app.engine import adaptive_engine as ae
from app.engine import knowledge_graph as kg
from app.services import session_core as sc

WRONG = "zzz"


def _session(skill="absolute_value", level=1):
    return sc.Session(ae.StudentState(current_skill=skill, difficulty=level))


def test_always_wrong_student_ends_at_the_root_gap():
    s, rng = _session("mult_div_integers"), random.Random(3)
    engine_moves = []
    for _ in range(80):
        q = sc.serve(s, rng)
        r = sc.grade(s, WRONG)
        if q["remedial"] is None:
            engine_moves.append((r["action"], r["next_skill"]))
        if r["gap_skill"]:
            break
    assert engine_moves[:5] == [("backtrack", "subtracting_integers"), ("backtrack", "adding_integers"),
                                ("backtrack", "comparing_integers"), ("backtrack", "absolute_value"),
                                ("remediate", "absolute_value")]
    assert s.state.gaps == {"absolute_value"}


def test_wrong_answer_then_same_pattern_then_easier():
    s, rng = _session(), random.Random(1)
    q1 = sc.serve(s, rng)
    r1 = sc.grade(s, WRONG)
    assert r1["next_stage"] == "same_pattern" and r1["mistake_card"]
    q2 = sc.serve(s, rng)
    assert q2["remedial"] == "same_pattern" and q2["pattern"] == q1["pattern"]
    total_before = s.state.total_answered
    sc.grade(s, WRONG)
    assert s.state.total_answered == total_before      # remedial answers never reach the engine


def test_correct_remedial_answer_returns_to_normal_flow():
    s, rng = _session(), random.Random(2)
    sc.serve(s, rng)
    sc.grade(s, WRONG)
    q = sc.serve(s, rng)
    assert q["remedial"] == "same_pattern"
    r = sc.grade(s, s.pending["correct_answer"])
    assert r["is_correct"] and r["next_stage"] is None and s.plan is None
    assert sc.serve(s, rng)["remedial"] is None


def test_banner_explains_the_move_on_the_next_normal_question():
    s, rng = _session("adding_integers"), random.Random(4)
    sc.serve(s, rng)
    r = sc.grade(s, WRONG)                  # level 1 miss with weak prerequisite -> backtrack
    assert r["action"] == "backtrack" and r["breadcrumb"]
    for _ in range(10):                     # finish the remediation practice
        if not s.plan:
            break
        sc.serve(s, rng)
        sc.grade(s, s.pending["correct_answer"])
    q = sc.serve(s, rng)
    assert q["remedial"] is None and q["banner"] == r["breadcrumb"]


def test_no_repeated_wording_in_a_row():
    s, rng = _session(), random.Random(5)
    seen = []
    for _ in range(12):
        q = sc.serve(s, rng)
        seen.append(q["question"])
        sc.grade(s, s.pending["correct_answer"])
    assert all(a != b for a, b in zip(seen, seen[1:]))


def test_fuzz_random_students_never_crash():
    for seed in range(60):
        rng = random.Random(seed)
        s = _session(rng.choice(list(kg.SKILLS)), rng.randint(1, 3))
        p = rng.random()
        for _ in range(40):
            q = sc.serve(s, rng)
            if q["type"] == "mcq":
                assert s.pending["correct_answer"] in q["options"]
            ok = rng.random() < p
            r = sc.grade(s, s.pending["correct_answer"] if ok else WRONG)
            assert r["is_correct"] == ok
            if r["round_over"]:
                sc.new_round(s)
