"""The engine explains what evidence is missing when it abstains (pure)."""
from app.engine import diagnosis as dx

LINEAR = dx.PrereqGraph({"a": [], "b": ["a"], "c": ["b"]})
E_ = dx.SkillEvidence


def verdict(evidence, origin="c"):
    return dx.diagnose(LINEAR, origin, evidence)


def test_abstains_with_a_concrete_request_when_errors_are_too_few():
    v = verdict({"c": E_(2, 0)})
    assert v["status"] == dx.INSUFFICIENT and v["reason"] == "too_few_errors"
    assert v["evidence_needed"][0]["kind"] == "more_errors" and v["evidence_needed"][0]["needed"] == 1


def test_a_single_lucky_correct_answer_does_not_clear_a_prerequisite():
    v = verdict({"c": E_(3, 0), "b": E_(1, 1)})
    assert v["status"] == dx.INSUFFICIENT and v["reason"] == "prerequisites_unverified"
    need = v["evidence_needed"]
    assert need == [{"kind": "verify_prerequisite", "skill": "b", "needed": 1,
                     "detail": "correct answers (with none wrong) to rule this prerequisite out"}]


def test_two_correct_answers_clear_the_prerequisite_and_name_the_root():
    v = verdict({"c": E_(3, 0), "b": E_(2, 2)})
    assert v["status"] == dx.ROOT_IDENTIFIED and v["root"] == "c"
    assert v["evidence_needed"] == []
    assert v["likelihood_ratio"] >= v["min_root_lr"]


def test_root_needs_confirmation_reports_how_many_more_wrong_answers():
    v = dx.diagnose(LINEAR, "c", {"c": E_(2, 0), "b": E_(2, 2), "a": E_(2, 2)}, min_chain_errors=2, min_root_errors=2,
                    min_root_lr=1000)
    assert v["status"] == dx.INSUFFICIENT and v["reason"] == "root_needs_confirmation"
    assert v["evidence_needed"][0]["kind"] == "confirm_root" and v["evidence_needed"][0]["needed"] >= 1


def test_mixed_evidence_asks_for_resolution():
    v = verdict({"c": E_(4, 2)})
    assert v["reason"] == "mixed_evidence"
    assert v["evidence_needed"][0]["kind"] == "resolve_mixed"


def test_likelihood_ratio_is_monotone_and_validated():
    assert dx.likelihood_ratio(E_(3, 0)) > dx.likelihood_ratio(E_(2, 0)) > dx.likelihood_ratio(E_(2, 1))
    assert dx.likelihood_ratio(E_(0, 0)) == 1.0
    import pytest
    with pytest.raises(ValueError):
        dx.likelihood_ratio(E_(1, 0), p_gap=0.9, p_known=0.5)


def test_verdict_is_deterministic_for_the_same_evidence():
    ev = {"c": E_(4, 1), "b": E_(3, 3), "a": E_(2, 2)}
    assert dx.diagnose(LINEAR, "c", ev) == dx.diagnose(LINEAR, "c", ev)
