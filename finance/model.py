"""Juthoor B2C financial model (deterministic scenario arithmetic, not a forecast).

    python finance/model.py            # rewrites finance/outputs.json and prints a summary

Business model: B2C. The student is the user; the parent/guardian is the buyer. There is no teacher or
school pricing. Prices are locked: Free 0 JOD, Pro Monthly 4.50 JOD, Pro Academic Year 32 JOD (32 is a
floor price hypothesis, not proven willingness to pay). Every other input below is an ASSUMPTION; demand,
conversion, retention and acquisition cost are unvalidated. tests/test_financial_model.py checks the
arithmetic only. These are the same assumptions and scenarios as the TechSparks Task 2 document.
"""
from __future__ import annotations

import json
from pathlib import Path

# ---- locked prices (JOD) -------------------------------------------------------------------------
PRICE_FREE = 0.0
PRICE_MONTHLY = 4.50
PRICE_ACADEMIC_YEAR = 32.0
ACADEMIC_MONTHS = 8             # a monthly subscriber can pay at most 8 months of the academic year

# ---- assumptions ----------------------------------------------------------------------------------
GST = 1.16                      # Jordan general sales tax, applied once gross revenue passes the threshold
GST_THRESHOLD = 30000.0
GATEWAY_FEE = 0.03              # card/payment-gateway fee
REFUNDS = 0.03                  # refunds and failed payments
VAR_PER_PAYER_YEAR = 0.50       # hosting, SMS and e-mail per paying family per year
VAR_PER_FREE_YEAR = 0.05        # hosting per registered free learner per year
SIGNUP_COST = 1.8               # paid cost per registered free learner (CPC 0.45 / 25% landing->sign-up)
SOCIAL_SECURITY = 1.1425        # employer social-security multiplier on gross salaries
CONTINGENCY = 1.10


def monthly_cost(salaries: list[float], other: list[float]) -> float:
    return (sum(salaries) * SOCIAL_SECURITY + sum(other)) * CONTINGENCY


# Monthly running cost by stage (JOD): Stage 1 = founders/MVP, Stage 2 = small team, Stage 3 = scale-up.
STAGE_COST = {
    "stage1": monthly_cost([0], [60, 25, 15, 30, 60, 3, 80, 300]),
    "stage2": monthly_cost([700, 600, 300, 200, 350], [150, 250, 150, 150, 80, 50, 600]),
    "stage3": monthly_cost([2400, 900, 600, 1200, 800, 1400], [500, 1200, 500, 400, 250, 150, 2000]),
}

# signups = registered free learners per year; conv = share of sign-ups whose parent buys Pro in that year;
# churn = monthly churn of monthly subscribers; annual_share = buyers choosing the academic-year plan;
# renew = share of last year's payers who buy again; paid_share = share of sign-ups that cost SIGNUP_COST;
# w = weight of Stage-3 costs in each year (the rest is Stage 2).
SCENARIOS = {
    "Conservative": dict(signups=[5000, 12000, 24000], conv=[0.02, 0.025, 0.03], churn=0.18, annual_share=0.30,
                         renew=0.25, paid_share=0.40, w=[0.0, 0.0, 0.2]),
    "Base": dict(signups=[12000, 35000, 80000], conv=[0.035, 0.04, 0.045], churn=0.12, annual_share=0.40,
                 renew=0.35, paid_share=0.40, w=[0.0, 0.25, 0.6]),
    "Growth": dict(signups=[25000, 90000, 220000], conv=[0.05, 0.055, 0.06], churn=0.09, annual_share=0.50,
                   renew=0.45, paid_share=0.50, w=[0.0, 0.5, 1.0]),
}


def months_paid(churn: float) -> float:
    """Expected months a monthly subscriber pays within one academic year."""
    return sum((1 - churn) ** k for k in range(ACADEMIC_MONTHS))


def unit_economics(churn: float, annual_share: float, monthly: float = PRICE_MONTHLY,
                   annual: float = PRICE_ACADEMIC_YEAR, gst: bool = True) -> dict:
    """Revenue and contribution per paying family per academic year."""
    monthly_revenue = monthly * months_paid(churn)
    gross = annual_share * annual + (1 - annual_share) * monthly_revenue
    after_tax = gross / (GST if gst else 1.0)
    net = after_tax * (1 - GATEWAY_FEE - REFUNDS)
    return {
        "months_paid": months_paid(churn), "monthly_plan_revenue": monthly_revenue, "gross": gross,
        "after_tax": after_tax, "fees": after_tax - net, "net": net,
        "variable_cost": VAR_PER_PAYER_YEAR, "contribution": net - VAR_PER_PAYER_YEAR,
    }


def year_rows(name: str) -> list[dict]:
    s = SCENARIOS[name]
    u = unit_economics(s["churn"], s["annual_share"])
    rows, previous_payers, cumulative = [], 0.0, 0.0
    for y in range(3):
        signups = s["signups"][y]
        new_payers = signups * s["conv"][y]
        renewals = s["renew"] * previous_payers
        payers = new_payers + renewals
        previous_payers = payers
        gross = payers * u["gross"]
        gst_applies = gross > GST_THRESHOLD
        after_tax = gross / (GST if gst_applies else 1.0)
        fees = after_tax * (GATEWAY_FEE + REFUNDS)
        revenue = after_tax - fees
        variable = payers * VAR_PER_PAYER_YEAR + signups * VAR_PER_FREE_YEAR
        marketing = signups * s["paid_share"] * SIGNUP_COST
        fixed = 12 * (STAGE_COST["stage2"] * (1 - s["w"][y]) + STAGE_COST["stage3"] * s["w"][y])
        operating = revenue - variable - marketing - fixed
        cumulative += operating
        rows.append({
            "year": y + 1, "signups": signups, "conversion": s["conv"][y], "new_payers": new_payers,
            "renewals": renewals, "payers": payers, "gross": gross, "gst_applies": gst_applies,
            "after_tax": after_tax, "fees": fees, "revenue": revenue, "variable": variable, "marketing": marketing,
            "fixed": fixed, "operating": operating, "cumulative": cumulative,
            "break_even_payers": fixed / u["contribution"],
        })
    return rows


def break_even_payers(fixed_cost_year: float, contribution: float) -> int:
    """Smallest whole number of paying families whose contribution covers the fixed cost."""
    n = int(fixed_cost_year // contribution)
    while n * contribution < fixed_cost_year:
        n += 1
    return n


def acquisition(name: str) -> dict:
    s = SCENARIOS[name]
    u = unit_economics(s["churn"], s["annual_share"])
    cac_blended = s["paid_share"] * SIGNUP_COST / s["conv"][1]
    cac_paid = SIGNUP_COST / s["conv"][1]
    lifetime_years = 1 / (1 - s["renew"])
    ltv = u["contribution"] * lifetime_years
    return {"cac_blended": cac_blended, "cac_paid_only": cac_paid, "lifetime_years": lifetime_years, "ltv": ltv,
            "ltv_to_cac_blended": ltv / cac_blended, "ltv_to_cac_paid_only": ltv / cac_paid}


def build() -> dict:
    out = {
        "business_model": "B2C: student = user, parent/guardian = buyer; no teacher or school pricing",
        "prices_jod": {"free": PRICE_FREE, "pro_monthly": PRICE_MONTHLY, "pro_academic_year": PRICE_ACADEMIC_YEAR},
        "stage_monthly_cost": STAGE_COST,
        "scenarios": {},
    }
    for name, s in SCENARIOS.items():
        rows = year_rows(name)
        u = unit_economics(s["churn"], s["annual_share"])
        out["scenarios"][name] = {
            "unit": u,
            "years": rows,
            "acquisition": acquisition(name),
            "peak_cumulative_deficit": -min(r["cumulative"] for r in rows),
            "steady_state_payers_to_cover": {
                "stage2": break_even_payers(12 * STAGE_COST["stage2"], u["contribution"]),
                "stage3": break_even_payers(12 * STAGE_COST["stage3"], u["contribution"]),
            },
        }
    return out


def main() -> None:
    result = build()
    path = Path(__file__).resolve().parent / "outputs.json"
    path.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    for name, sc in result["scenarios"].items():
        y3 = sc["years"][2]
        print(f"{name:12s} contribution/payer {sc['unit']['contribution']:.2f} JOD | Y3 payers {y3['payers']:.0f} "
              f"| Y3 operating {y3['operating']:.0f} JOD | peak deficit {sc['peak_cumulative_deficit']:.0f} JOD")


if __name__ == "__main__":
    main()
