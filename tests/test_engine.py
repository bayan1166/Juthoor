"""Pure engine tests: no web server or database involved."""
import random

from app.engine import adaptive_engine as ae
from app.engine import knowledge_graph as kg
from app.engine import offline_bank as ob
from app.engine import practice


def test_graph_is_a_dag_with_one_root():
    roots = [s for s in kg.SKILLS if not kg.prerequisites(s)]
    assert roots == ["absolute_value"]


def test_backtracks_to_the_root_gap():
    """The core claim: repeated misses on the top skill walk back to the real gap."""
    state = ae.StudentState(current_skill="mult_div_integers", difficulty=1)
    path = []
    for _ in range(5):
        d = ae.decide_next(state, is_correct=False)
        path.append((d.action, d.next_skill))
    assert path == [
        ("backtrack", "subtracting_integers"),
        ("backtrack", "adding_integers"),
        ("backtrack", "comparing_integers"),
        ("backtrack", "absolute_value"),
        ("remediate", "absolute_value"),
    ]
    assert "absolute_value" in state.gaps


def test_stuck_student_is_parked_not_looped_forever():
    state = ae.StudentState(current_skill="absolute_value", difficulty=1)
    actions = [ae.decide_next(state, False).action for _ in range(3)]
    assert actions[-1] in ("park", "complete")
    assert "absolute_value" in state.parked


def test_correct_answers_level_up_then_master():
    state = ae.StudentState(current_skill="absolute_value", difficulty=1)
    actions = [ae.decide_next(state, True).action for _ in range(8)]
    assert actions[:2] == ["level_up", "level_up"]
    assert "absolute_value" in state.mastered


def test_every_skill_and_level_generates_valid_questions():
    for skill in kg.SKILLS:
        for level in (1, 2, 3):
            for seed in range(20):
                q = ob.generate_offline(skill, level, random.Random(seed))
                assert q["question"] and q["correct_answer"]
                texts = [d["text"] for d in q["distractors"]]
                assert q["correct_answer"] not in texts


def test_answer_matching_ignores_bidi_marks_and_spacing():
    assert practice.is_correct({"correct_answer": "\u20662\u2069"}, " 2 ")
    assert not practice.is_correct({"correct_answer": "\u20662\u2069"}, "3")
