"""Invariants of finance/model.py (the arithmetic, not the assumptions)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("fm", Path(__file__).resolve().parents[1] / "finance" / "model.py")
fm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fm)


def test_higher_price_never_lowers_contribution():
    a, b = fm.unit_economics(3.5, 250), fm.unit_economics(7.0, 250)
    assert b["contribution_per_student"] > a["contribution_per_student"]


def test_unit_economics_add_up():
    u = fm.unit_economics(7.0, 250)
    assert abs(u["net_revenue_per_student"] - u["variable_cost_per_student"] - u["cs_cost_per_student"]
               - u["contribution_per_student"]) < 0.01


def test_break_even_covers_fixed_cost_and_is_minimal():
    for price in (3.5, 7.0):
        be = fm.break_even(price, 250, fm.TEAMS["0.5 FTE support/sales"])
        c = fm.unit_economics(price, 250)["contribution_per_school"]
        assert be["schools"] * c >= be["fixed_cost_year"] - 1
        assert (be["schools"] - 1) * c < be["fixed_cost_year"]


def test_scenarios_are_ordered_by_size_and_deterministic():
    r1, r2 = fm.build(), fm.build()
    assert r1 == r2
    y3 = {n: v["school_7_0"]["years"][2]["revenue"] for n, v in r1["scenarios"].items()}
    assert y3["Conservative"] < y3["Expected"] < y3["Aggressive"]


def test_cash_need_matches_cumulative_net():
    d = fm.build()["scenarios"]["Expected"]["school_7_0"]
    cum = -sum(fm.ONE_TIME.values()) + sum(r["net"] for r in d["years"])
    assert abs(d["cash"]["cumulative_cash_end_y3"] - cum) <= 3


def test_no_negative_inputs():
    assert all(v >= 0 for v in fm.INFRA_MONTHLY.values()) and fm.LLM_JOD_MSG > 0
    assert 0 <= fm.SCHOOL_DISCOUNT < 1 and 0 < fm.COLLECTION_RATE <= 1
