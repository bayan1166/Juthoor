"""BKT invariants, calibration and a baseline comparison (pure; no database).

Property-style: seeded random inputs, thousands of updates. (`hypothesis` is not a project
dependency; seeded loops keep the suite dependency-free and exactly reproducible.)

The calibration/baseline tests use *synthetic* learners generated from the BKT assumptions, so
they verify the implementation is a correct, calibrated BKT, not that BKT beats alternatives on
real students.
"""
import math
import random

import pytest

from app.engine import adaptive_engine as ae
from app.engine import config

P = config.BKT


def test_probability_stays_in_bounds_over_random_sequences():
    rng = random.Random(1)
    for _ in range(2000):
        p = rng.choice([0.0, 1.0, P["p_init"], rng.random()])
        for _ in range(60):
            p = ae.bkt_update(p, rng.random() < 0.6)
            assert math.isfinite(p) and ae.P_MIN <= p <= ae.P_MAX


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), -5.0, 7.0, None, "x", True])
def test_bad_inputs_never_produce_nan_or_out_of_range(bad):
    for ok in (True, False):
        out = ae.bkt_update(bad, ok)
        assert math.isfinite(out) and ae.P_MIN <= out <= ae.P_MAX


def test_a_correct_answer_never_lowers_mastery_relative_to_a_wrong_one():
    for i in range(0, 1001):
        p = i / 1000
        assert ae.bkt_update(p, True) >= ae.bkt_update(p, False)


def test_more_correct_answers_never_lower_mastery():
    p, last = P["p_init"], 0.0
    for _ in range(100):
        p = ae.bkt_update(p, True)
        assert p >= last
        last = p


def test_mastery_is_not_absorbing_at_the_top():
    p = P["p_init"]
    for _ in range(500):
        p = ae.bkt_update(p, True)
    assert p < 1.0  # regression: exactly 1.0 used to be absorbing
    for _ in range(40):
        p = ae.bkt_update(p, False)
    assert p < config.CONTEST_THRESHOLD  # later errors do move a long-mastered skill


def test_update_is_deterministic():
    seq = [True, False, True, True, False, False, True]
    runs = []
    for _ in range(3):
        p = P["p_init"]
        for y in seq:
            p = ae.bkt_update(p, y)
        runs.append(p)
    assert runs[0] == runs[1] == runs[2]


@pytest.mark.parametrize("patch", [
    {"p_slip": -0.1}, {"p_guess": 1.5}, {"p_learn": float("nan")}, {"p_init": 0.0}, {"p_init": 1.0},
    {"p_slip": 0.6, "p_guess": 0.5}, {"p_slip": True}, {"p_guess": "0.2"},
])
def test_invalid_parameters_are_rejected(patch):
    with pytest.raises(ValueError):
        ae.validate_bkt_params({**P, **patch})


def test_missing_parameter_is_rejected():
    bad = dict(P)
    bad.pop("p_slip")
    with pytest.raises(ValueError):
        ae.validate_bkt_params(bad)


def test_shipped_parameters_are_valid():
    ae.validate_bkt_params(P)


def test_persisted_garbage_is_repaired_on_load():
    raw = ('{"current_skill": "absolute_value", "difficulty": 99, "p_mastery": {"absolute_value": NaN, '
           '"adding_integers": 5.0}, "attempts": {"absolute_value": 2}, "correct": {"absolute_value": 9}}')
    state = ae.StudentState.from_json(raw)
    assert all(ae.P_MIN <= v <= ae.P_MAX for v in state.p_mastery.values())
    assert state.correct["absolute_value"] == 2
    assert state.difficulty == config.MAX_DIFFICULTY


def _generate(rng, n):
    known = rng.random() < P["p_init"]
    out = []
    for _ in range(n):
        out.append(rng.random() < ((1 - P["p_slip"]) if known else P["p_guess"]))
        if not known and rng.random() < P["p_learn"]:
            known = True
    return out


def _predictions(n_learners=2000, length=20, seed=11):
    rng = random.Random(seed)
    rows = []
    for _ in range(n_learners):
        p, hist = P["p_init"], []
        for y in _generate(rng, length):
            bkt = p * (1 - P["p_slip"]) + (1 - p) * P["p_guess"]
            last = hist[-3:]
            baseline = (sum(last) + 0.5) / (len(last) + 1)   # last-3 correctness, smoothed
            rows.append((bkt, baseline, y))
            p = ae.bkt_update(p, y)
            hist.append(y)
    return rows


def test_bkt_is_calibrated_on_synthetic_learners():
    rows = _predictions()
    bins = [[0, 0.0, 0.0] for _ in range(10)]
    for bkt, _b, y in rows:
        i = min(9, int(bkt * 10))
        bins[i][0] += 1
        bins[i][1] += bkt
        bins[i][2] += y
    ece = sum(abs(b[1] - b[2]) for b in bins) / len(rows)
    assert ece < 0.02, f"expected calibration error {ece:.4f}"


def test_bkt_beats_the_last_n_baseline_on_synthetic_learners():
    rows = _predictions()
    brier_bkt = sum((b - y) ** 2 for b, _l, y in rows) / len(rows)
    brier_last = sum((l - y) ** 2 for _b, l, y in rows) / len(rows)
    assert brier_bkt < brier_last, (brier_bkt, brier_last)
