"""Question contract by type, checked over the whole question bank (pure: no web framework, no database).

Supported question types (see app/services/session_core.py::_options and the UI in practice.js):
  mcq   multiple choice          -> options non-empty, distinct, contain the correct answer
  tf    true / false             -> options are exactly the two statements, contain the correct answer
  input free response (typed)    -> options are EMPTY by design (the learner types the answer)
Every type: skill exists in the graph, difficulty in range, non-empty question / hint, valid type.
"""
import random

import pytest

from app.engine import adaptive_engine as ae
from app.engine import config
from app.engine import knowledge_graph as kg
from app.schemas.adaptive import QuestionOut
from app.services import session_core as sc

TYPES = {"mcq", "tf", "input"}
TF_OPTIONS = ["صح", "خطأ"]


def check_question(q: dict) -> None:
    """The invariants the API contract promises, by question type."""
    assert q["type"] in TYPES, q["type"]
    assert q["skill"] in kg.SKILLS
    assert config.MIN_DIFFICULTY <= q["difficulty"] <= config.MAX_DIFFICULTY
    assert isinstance(q["question"], str) and q["question"].strip()
    assert isinstance(q["hint"], str) and q["hint"].strip()
    assert q["correct_answer"] not in (None, "")
    opts = q["options"]
    if q["type"] == "mcq":
        assert len(opts) >= 2 and len(set(opts)) == len(opts)
        assert q["correct_answer"] in opts
    elif q["type"] == "tf":
        assert sorted(opts) == sorted(TF_OPTIONS)
        assert q["correct_answer"] in TF_OPTIONS
    else:  # input
        assert opts == []
    QuestionOut.model_validate({k: v for k, v in q.items() if k in QuestionOut.model_fields})


def _serve_everything(per_cell: int, seed: int):
    rng = random.Random(seed)
    for skill in kg.ordered_skills():
        for difficulty in range(config.MIN_DIFFICULTY, config.MAX_DIFFICULTY + 1):
            state = ae.StudentState(current_skill=skill, difficulty=difficulty)
            for _ in range(per_cell):
                yield sc.serve(sc.Session(state=state), rng)


def test_every_served_question_meets_the_contract_for_its_type():
    seen = set()
    for q in _serve_everything(per_cell=30, seed=7):
        check_question(q)
        seen.add(q["type"])
    assert seen == TYPES, f"the bank no longer serves every supported type: {seen}"


def test_input_questions_have_no_options_and_accept_a_typed_answer():
    from app.engine import practice as pr
    inputs = [q for q in _serve_everything(per_cell=30, seed=11) if q["type"] == "input"]
    assert inputs
    for q in inputs:
        assert q["options"] == []
        pending = {"correct_answer": q["correct_answer"], "type": "input", "traps": q.get("traps", {})}
        assert pr.is_correct(pending, q["correct_answer"]) is True


def test_the_inverse_of_9_question_from_the_report_is_a_valid_input_question():
    """Regression for the reported case: 'ما معكوس العدد 9؟ (اكتب العدد فقط)' is type=input, options=[]."""
    found = [q for q in _serve_everything(per_cell=60, seed=3)
             if q["skill"] == "absolute_value" and q["type"] == "input" and "معكوس" in q["question"]]
    assert found, "no inverse-number input question was served"
    for q in found:
        check_question(q)


@pytest.mark.parametrize("bad", [
    dict(type="mcq", options=[]), dict(type="mcq", options=["1", "1"]), dict(type="tf", options=["صح"]),
    dict(type="input", options=["a"]), dict(type="essay", options=[]),
])
def test_the_checker_rejects_violations(bad):
    q = dict(question="س", hint="ت", skill="absolute_value", difficulty=1, correct_answer="1", pattern="p", source="offline")
    q.update(bad)
    with pytest.raises(AssertionError):
        check_question(q)
