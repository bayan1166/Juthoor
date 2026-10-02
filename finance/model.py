"""Juthoor financial model (JOD). Pure Python, deterministic, no external data fetched at run time.

Every input carries a tag:  V = verified from a public source on the stated date (see
docs/FINANCIAL_MODEL.md, "Sources"), A = assumption chosen by the team (not evidence).
Nothing here is a forecast of real demand: the 32-student survey is early validation of interest,
not evidence of willingness to pay.  Run:  python3 finance/model.py  (writes finance/outputs.json)
"""
from __future__ import annotations

import json
from pathlib import Path

FX = 0.709          # V  JOD per USD (CBJ peg)
SS = 1.1425         # V  employer social-security uplift on salary (14.25%)

INFRA_MONTHLY = {   # JOD / month at launch scale
    "app server 4GB/2vCPU": 24 * FX,                                  # V DigitalOcean list price
    "managed PostgreSQL HA 1GiB + 10GiB": (30.45 + 10 * 0.215) * FX,  # V DigitalOcean list price
    "backups, storage, CDN/DNS, TLS": 20.0,                           # A
    "monitoring, logging, error tracking": 25.0,                      # A
    "transactional email / SMS": 15.0,                                # A
    "domain and misc": 3.0,                                           # A
}
SALARY_BASE = {"developer": 900, "qa": 700, "designer": 700, "support_sales": 600,
               "customer_success": 550, "content_teacher": 450}      # A low confidence (Amman range)
LOADED = {k: round(v * SS) for k, v in SALARY_BASE.items()}

ONE_TIME = {        # JOD, A unless stated
    "production hardening (2 dev x 3 mo)": 2 * 3 * LOADED["developer"],
    "QA and test automation (1 x 3 mo)": 3 * LOADED["qa"],
    "UI/UX and accessibility (1 x 2 mo)": 2 * LOADED["designer"],
    "security review / penetration test": 3000,
    "legal: company, terms, privacy review": 2500,
    "curriculum authoring and teacher review (next subject)": 4000,
    "launch materials and training": 1000,
}

# LLM tutor cost: price V (Claude Haiku class list price), token counts A
LLM_IN_USD_MTOK, LLM_OUT_USD_MTOK, TOK_IN, TOK_OUT = 1.0, 5.0, 1200, 250
LLM_JOD_MSG = (TOK_IN * LLM_IN_USD_MTOK + TOK_OUT * LLM_OUT_USD_MTOK) / 1e6 * FX
MSGS_PER_MONTH, ACTIVE_MONTHS = 36, 9      # A

PAY_FEE_CARD = 0.03        # V range 2.5-3.5% typical gateway
PAY_FEE_SCHOOL = 0.01      # A schools pay by bank transfer / invoice
COLLECTION_RATE = 0.95     # A share of invoiced revenue actually collected
SCHOOL_DISCOUNT = 0.15     # A average volume / negotiated discount on list price
SCHOOL_CHURN = 0.15        # A yearly school churn
FAMILY_CHURN = 0.40        # A yearly family churn
TEACHER_CHURN = 0.30       # A yearly teacher churn
CS_PER_SCHOOL_YEAR = 240   # A customer success per school
ONBOARD_PER_SCHOOL = 120   # A one-time
CAC_PER_SCHOOL = 250       # A
CAC_PER_FAMILY = 4.0       # A
CAC_PER_TEACHER = 6.0      # A
TAX_NOTE = "Prices are shown exclusive of sales tax; income/corporate tax is NOT modelled (assumption: pre-tax view)."

PLANS = {   # list price JOD per year
    "school_seat_low": 3.5,      # A current proposal
    "school_seat_test": 7.0,     # A price point to test (hypothesis, not a finding)
    "teacher": 29.0,             # A per teacher per year, up to ~120 students
    "family": 14.9,              # A per family per year
}

# scenario: schools / students per school / teachers / families at END of years 1..3, staffing per year
SCENARIOS = {
    "Conservative": dict(schools=[2, 6, 12], students=150, teachers=[10, 40, 90], families=[0, 30, 80],
                         staff=[{}, {"support_sales": 0.5}, {"support_sales": 0.5, "developer": 0.5}]),
    "Expected": dict(schools=[4, 15, 40], students=250, teachers=[30, 120, 300], families=[30, 150, 400],
                     staff=[{}, {"developer": 0.5, "support_sales": 0.5},
                            {"developer": 1, "support_sales": 1, "content_teacher": 0.5}]),
    "Aggressive": dict(schools=[8, 40, 120], students=300, teachers=[80, 400, 1200], families=[100, 600, 2000],
                       staff=[{"developer": 1, "support_sales": 1},
                              {"developer": 2, "qa": 0.5, "support_sales": 2, "content_teacher": 1},
                              {"developer": 3, "qa": 1, "designer": 0.5, "support_sales": 3, "content_teacher": 1.5}]),
}


def llm_per_user_year(msgs_month: int = MSGS_PER_MONTH) -> float:
    return LLM_JOD_MSG * msgs_month * ACTIVE_MONTHS


def infra_year(users: int) -> float:
    scale = 1 + max(0, users - 1000) / 5000      # A infra grows with load
    return sum(INFRA_MONTHLY.values()) * 12 * scale


def unit_economics(school_price: float, students_per_school: int) -> dict:
    """Per-student and per-school contribution for one plan, excluding fixed team/infra."""
    net_price = school_price * (1 - SCHOOL_DISCOUNT) * COLLECTION_RATE
    var_student = llm_per_user_year() + net_price * PAY_FEE_SCHOOL
    cs_student = CS_PER_SCHOOL_YEAR / students_per_school
    contrib_student = net_price - var_student - cs_student
    return {"list_price": school_price, "net_revenue_per_student": round(net_price, 3),
            "variable_cost_per_student": round(var_student, 3), "cs_cost_per_student": round(cs_student, 3),
            "contribution_per_student": round(contrib_student, 3),
            "contribution_margin_pct": round(100 * contrib_student / net_price, 1) if net_price else None,
            "contribution_per_school": round(contrib_student * students_per_school, 1)}


def family_unit() -> dict:
    net = PLANS["family"] * COLLECTION_RATE
    var = llm_per_user_year() + net * PAY_FEE_CARD
    return {"list_price": PLANS["family"], "net_revenue": round(net, 3), "variable_cost": round(var, 3),
            "contribution": round(net - var, 3), "contribution_margin_pct": round(100 * (net - var) / net, 1)}


def teacher_unit() -> dict:
    net = PLANS["teacher"] * COLLECTION_RATE
    var = llm_per_user_year(20) + net * PAY_FEE_CARD
    return {"list_price": PLANS["teacher"], "net_revenue": round(net, 3), "variable_cost": round(var, 3),
            "contribution": round(net - var, 3), "contribution_margin_pct": round(100 * (net - var) / net, 1)}


def avg(prev: int, now: int) -> float:
    return (prev + now) / 2


def run(scn: dict, school_price: float) -> list[dict]:
    rows, prev = [], dict(schools=0, teachers=0, families=0)
    for y in range(3):
        s, t, f = scn["schools"][y], scn["teachers"][y], scn["families"][y]
        avg_s, avg_t, avg_f = avg(prev["schools"], s), avg(prev["teachers"], t), avg(prev["families"], f)
        students = avg_s * scn["students"]
        rev_school = students * school_price * (1 - SCHOOL_DISCOUNT) * COLLECTION_RATE
        rev_teacher = avg_t * PLANS["teacher"] * COLLECTION_RATE
        rev_family = avg_f * PLANS["family"] * COLLECTION_RATE
        rev = rev_school + rev_teacher + rev_family
        llm = students * llm_per_user_year() + avg_t * llm_per_user_year(20) + avg_f * llm_per_user_year()
        fees = rev_school * PAY_FEE_SCHOOL + (rev_teacher + rev_family) * PAY_FEE_CARD
        infra = infra_year(int(students + avg_t + avg_f))
        cs = avg_s * CS_PER_SCHOOL_YEAR
        gross_new_s = max(0, s - prev["schools"] * (1 - SCHOOL_CHURN))
        gross_new_t = max(0, t - prev["teachers"] * (1 - TEACHER_CHURN))
        gross_new_f = max(0, f - prev["families"] * (1 - FAMILY_CHURN))
        acq = gross_new_s * (ONBOARD_PER_SCHOOL + CAC_PER_SCHOOL) + gross_new_t * CAC_PER_TEACHER + gross_new_f * CAC_PER_FAMILY
        staff = sum(LOADED[r] * n for r, n in scn["staff"][y].items()) * 12
        cogs = infra + llm + fees + cs
        total = cogs + acq + staff
        rows.append({"year": y + 1, "schools_end": s, "avg_students": round(students), "teachers_end": t,
                     "families_end": f, "revenue": round(rev), "rev_school": round(rev_school),
                     "rev_teacher": round(rev_teacher), "rev_family": round(rev_family),
                     "cogs": round(cogs), "gross_margin_pct": round(100 * (rev - cogs) / rev, 1) if rev else None,
                     "acquisition": round(acq), "staff": round(staff), "total_cost": round(total),
                     "net": round(rev - total), "avg_monthly_burn": round(max(0, total - rev) / 12)})
        prev = dict(schools=s, teachers=t, families=f)
    return rows


def cash_need(rows: list[dict]) -> dict:
    cum, low = -sum(ONE_TIME.values()), -sum(ONE_TIME.values())
    for r in rows:
        cum += r["net"]
        low = min(low, cum)
    return {"one_time_investment": sum(ONE_TIME.values()), "lowest_cumulative_cash": round(low),
            "funding_needed_to_cover_3_years": round(-low) if low < 0 else 0, "cumulative_cash_end_y3": round(cum)}


def break_even(school_price: float, students_per_school: int, team_cost_year: float) -> dict:
    ue = unit_economics(school_price, students_per_school)
    fixed = sum(INFRA_MONTHLY.values()) * 12 + team_cost_year
    c = ue["contribution_per_school"]
    if c <= 0:
        return {"schools": None, "students": None, "note": "negative contribution: never breaks even"}
    schools = int(-(-fixed // c))
    return {"fixed_cost_year": round(fixed), "schools": schools, "students": schools * students_per_school}


TEAMS = {"team unpaid (infra only)": 0.0,
         "0.5 FTE support/sales": LOADED["support_sales"] * 0.5 * 12,
         "1 dev + 1 support/sales + 0.5 content": (LOADED["developer"] + LOADED["support_sales"] + 0.5 * LOADED["content_teacher"]) * 12}


def build() -> dict:
    out = {"inputs": {"fx": FX, "loaded_salaries": LOADED, "llm_jod_per_message": round(LLM_JOD_MSG, 5),
                      "llm_jod_per_student_year": round(llm_per_user_year(), 3), "infra_month_total": round(sum(INFRA_MONTHLY.values()), 1),
                      "plans": PLANS, "churn": {"school": SCHOOL_CHURN, "family": FAMILY_CHURN, "teacher": TEACHER_CHURN},
                      "discount": SCHOOL_DISCOUNT, "collection_rate": COLLECTION_RATE, "tax_note": TAX_NOTE},
           "unit_economics": {"school_3_5": unit_economics(3.5, 250), "school_7_0": unit_economics(7.0, 250),
                              "teacher": teacher_unit(), "family": family_unit()},
           "scenarios": {}, "break_even": {}}
    for name, scn in SCENARIOS.items():
        out["scenarios"][name] = {}
        for label, price in (("school_3_5", 3.5), ("school_7_0", 7.0)):
            rows = run(scn, price)
            out["scenarios"][name][label] = {"years": rows, "cash": cash_need(rows)}
    for team, cost in TEAMS.items():
        for price in (3.5, 7.0):
            for st in (150, 250):
                out["break_even"][f"{team} | {price} JOD | {st} students/school"] = break_even(price, st, cost)
    return out


if __name__ == "__main__":
    res = build()
    Path(__file__).with_name("outputs.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res["unit_economics"], indent=1))
    for n, v in res["scenarios"].items():
        for lab, d in v.items():
            print(n, lab, [(r["year"], r["revenue"], r["net"], r["gross_margin_pct"]) for r in d["years"]], d["cash"])
    for k, v in res["break_even"].items():
        print(k, v)
