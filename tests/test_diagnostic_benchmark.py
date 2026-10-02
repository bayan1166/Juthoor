"""Regression guard for the diagnostic benchmark (synthetic learners; see app/engine/benchmark.py).

The floors below are deliberately loose guard-rails derived from measured runs (see
benchmarks/after.json), not claims about real-student accuracy. A change that makes diagnosis
markedly worse or non-deterministic fails here.
"""
import pytest

from app.engine import benchmark as bm
from app.engine import config


@pytest.fixture(scope="module")
def report():
    return bm.report(reps=2, check_determinism=True)


def test_benchmark_is_deterministic(report):
    assert report["deterministic"] is True


def test_no_premature_diagnoses(report):
    for name, row in report["scenarios"].items():
        assert row["premature_rate_pct"] in (0.0, None), (name, row)


def test_clean_known_root_accuracy_floor(report):
    row = report["scenarios"]["known_root_clean"]
    assert row["root_accuracy_when_committed_pct"] >= 90.0, row
    assert row["wrong_root_rate_pct"] <= 8.0, row


def test_clean_no_gap_rarely_triggers_a_false_diagnosis(report):
    assert report["scenarios"]["no_gap_clean"]["false_diagnosis_rate_pct"] <= 8.0


def test_every_gap_case_either_names_a_root_or_abstains_never_crashes(report):
    for name, row in report["scenarios"].items():
        if row["kind"] == "gap":
            assert row["named_root"] + round(row["abstention_rate_pct"] * row["cases"] / 100) == row["cases"]


def test_metrics_are_computed_not_hardcoded():
    # Changing the evidence policy must change the measured result.
    saved = (config.MIN_SOLID_EVIDENCE, config.MIN_ROOT_LR)
    try:
        config.MIN_SOLID_EVIDENCE, config.MIN_ROOT_LR = 1, 1.0
        legacy = bm.summarise(bm.run_all(2))
    finally:
        config.MIN_SOLID_EVIDENCE, config.MIN_ROOT_LR = saved
    current = bm.summarise(bm.run_all(2))
    assert legacy["digest"] != current["digest"]
    # Regression for the lucky-correct weakness: the old one-correct-answer rule names wrong roots
    # more often and does so prematurely.
    assert (legacy["scenarios"]["known_root_clean"]["wrong_root_rate_pct"]
            > current["scenarios"]["known_root_clean"]["wrong_root_rate_pct"])
    assert (legacy["scenarios"]["known_root_clean"]["premature_rate_pct"]
            > current["scenarios"]["known_root_clean"]["premature_rate_pct"])
