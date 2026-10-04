"""Invariants of finance/model.py (the B2C arithmetic, not the assumptions)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("fm", Path(__file__).resolve().parents[1] / "finance" / "model.py")
fm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fm)


def test_prices_are_the_locked_b2c_prices():
    assert (fm.PRICE_FREE, fm.PRICE_MONTHLY, fm.PRICE_ACADEMIC_YEAR) == (0.0, 4.50, 32.0)
    assert fm.build()["prices_jod"] == {"free": 0.0, "pro_monthly": 4.50, "pro_academic_year": 32.0}
    source = (Path(__file__).resolve().parents[1] / "finance" / "model.py").read_text(encoding="utf-8").lower()
    for legacy in ("per_school", "seat", "teacher_price", "school_7_0"):
        assert legacy not in source


def test_higher_price_never_lowers_contribution():
    low = fm.unit_economics(0.12, 0.4, monthly=4.50, annual=32.0)
    high = fm.unit_economics(0.12, 0.4, monthly=5.50, annual=40.0)
    assert high["contribution"] > low["contribution"]


def test_unit_economics_add_up():
    u = fm.unit_economics(0.12, 0.4)
    assert abs(u["after_tax"] - u["fees"] - u["net"]) < 1e-9
    assert abs(u["net"] - u["variable_cost"] - u["contribution"]) < 1e-9
    assert u["months_paid"] <= fm.ACADEMIC_MONTHS
    assert abs(u["gross"] - (0.4 * 32.0 + 0.6 * 4.50 * u["months_paid"])) < 1e-9


def test_academic_year_plan_is_cheaper_than_paying_monthly_all_year():
    assert fm.PRICE_ACADEMIC_YEAR < fm.PRICE_MONTHLY * fm.ACADEMIC_MONTHS


def test_break_even_covers_fixed_cost_and_is_minimal():
    for name in fm.SCENARIOS:
        contribution = fm.build()["scenarios"][name]["unit"]["contribution"]
        for stage in ("stage2", "stage3"):
            fixed = 12 * fm.STAGE_COST[stage]
            n = fm.break_even_payers(fixed, contribution)
            assert n * contribution >= fixed and (n - 1) * contribution < fixed


def test_scenarios_are_ordered_and_deterministic():
    r1, r2 = fm.build(), fm.build()
    assert r1 == r2
    payers = {n: v["years"][2]["payers"] for n, v in r1["scenarios"].items()}
    assert payers["Conservative"] < payers["Base"] < payers["Growth"]


def test_cumulative_result_matches_yearly_operating_results():
    for sc in fm.build()["scenarios"].values():
        assert abs(sc["years"][-1]["cumulative"] - sum(r["operating"] for r in sc["years"])) < 1e-6
        assert sc["peak_cumulative_deficit"] == -min(r["cumulative"] for r in sc["years"])


def test_payers_are_new_buyers_plus_renewals():
    for name, s in fm.SCENARIOS.items():
        rows = fm.build()["scenarios"][name]["years"]
        previous = 0.0
        for y, row in enumerate(rows):
            assert abs(row["payers"] - (s["signups"][y] * s["conv"][y] + s["renew"] * previous)) < 1e-9
            previous = row["payers"]


def test_no_negative_inputs():
    assert all(v >= 0 for v in fm.STAGE_COST.values())
    assert 0 < fm.GATEWAY_FEE < 1 and 0 <= fm.REFUNDS < 1 and fm.GST >= 1
    for s in fm.SCENARIOS.values():
        assert all(0 < c < 1 for c in s["conv"]) and 0 <= s["renew"] < 1 and 0 <= s["churn"] < 1
