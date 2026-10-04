# Juthoor financial model (B2C)

Generated from `finance/model.py` (deterministic; `python finance/model.py` rewrites `finance/outputs.json`; `tests/test_financial_model.py` checks the arithmetic). All amounts are in JOD. The numbers and assumptions are the same as in the TechSparks Task 2 document.

## Read this first

- **Business model: B2C.** The student is the user and the parent/guardian is the buyer. There is no teacher or school pricing, no seats and no school subscription.
- **Prices (locked):** Free 0 JOD; Pro Monthly 4.50 JOD/month; Pro Academic Year 32 JOD/academic year. 32 JOD is a floor price hypothesis, not proven willingness to pay.
- This is **scenario arithmetic, not a forecast.** Parent demand, conversion, retention and acquisition cost have not been validated with paying customers.
- Every input except the prices is an assumption written at the top of `finance/model.py`.

## Key assumptions

| Input | Value |
|---|---|
| Months a monthly subscriber can pay in an academic year | 8 |
| Sales tax (GST) once gross revenue passes 30,000 JOD | 16% |
| Payment-gateway fee / refunds and failed payments | 3% / 3% |
| Variable cost per paying family per year / per free learner per year | 0.50 / 0.05 |
| Paid acquisition cost per registered free learner | 1.80 |
| Monthly running cost: Stage 1 / Stage 2 / Stage 3 | 630 / 4,275 / 14,674 |

## Scenarios

| Scenario | Sign-ups Y1 / Y2 / Y3 | Conversion Y1 / Y2 / Y3 | Monthly churn | Academic-year share | Renewal |
|---|---|---|---|---|---|
| Conservative | 5,000 / 12,000 / 24,000 | 2.0% / 2.5% / 3.0% | 18% | 30% | 25% |
| Base | 12,000 / 35,000 / 80,000 | 3.5% / 4.0% / 4.5% | 12% | 40% | 35% |
| Growth | 25,000 / 90,000 / 220,000 | 5.0% / 5.5% / 6.0% | 9% | 50% | 45% |

## Unit economics per paying family per academic year

| Scenario | Gross | After tax | Net of fees | Contribution |
|---|---|---|---|---|
| Conservative | 23.52 | 20.28 | 19.06 | 18.56 |
| Base | 27.21 | 23.46 | 22.05 | 21.55 |
| Growth | 29.24 | 25.21 | 23.70 | 23.20 |

## Three-year results

| Scenario | Year | Paying families | Revenue | Operating result | Cumulative |
|---|---|---|---|---|---|
| Conservative | 1 | 100 | 2,211 | -52,989 | -52,989 |
| Conservative | 2 | 325 | 7,186 | -53,516 | -106,505 |
| Conservative | 3 | 801 | 17,717 | -77,422 | -183,928 |
| Base | 1 | 420 | 10,742 | -50,008 | -50,008 |
| Base | 2 | 1,547 | 34,108 | -76,113 | -126,121 |
| Base | 3 | 4,141 | 91,311 | -98,535 | -224,656 |
| Growth | 1 | 1,250 | 29,622 | -46,053 | -46,053 |
| Growth | 2 | 5,512 | 130,632 | -71,320 | -117,373 |
| Growth | 3 | 15,681 | 371,591 | -21,340 | -138,713 |

## Break-even reference and acquisition

| Scenario | Payers to cover Stage-2 costs | Payers to cover Stage-3 costs | Peak cumulative deficit | LTV | LTV / CAC (blended) |
|---|---|---|---|---|---|
| Conservative | 2,764 | 9,487 | 183,928 | 24.7 | 0.86 |
| Base | 2,381 | 8,173 | 224,656 | 33.2 | 1.84 |
| Growth | 2,212 | 7,591 | 138,713 | 42.2 | 2.58 |

## What this means

None of the scenarios reaches an operating profit within three years at the modelled cost levels. The model is most sensitive to conversion from free learners to paying parents, to renewal of the academic-year plan and to acquisition cost. These are exactly the numbers the next validation round with parents must measure before any of these scenarios is treated as a plan.
