> **Historical / internal document.** Written before the locked positioning. Where it describes teachers, schools, classrooms, a school pilot or Juthoor as a Grade 6 mathematics product, it is superseded: Juthoor is a general B2C learning platform (student = user, parent = buyer) and Grade 6 mathematics is only the current demo content. Educators appear only as internal reviewers. Current reference: `docs/POSITIONING.md`.

# 10 - Financial model rebuild

**Status: DONE**

## Objective
A reproducible, honest model: school SaaS at 3.5 vs 7.0 JOD/student/year, teacher and family plans separately, unit economics, break-even, burn, three scenarios.

## Current problem (before this work)
The earlier model mixed plans, used a single price and gave no tested arithmetic.

## Required implementation
- `finance/model.py` (pure, deterministic) -> `finance/outputs.json`; `docs/FINANCIAL_MODEL.md` generated from it.
- Every input tagged V or A; survey not used as price evidence; no market-size claims.

## Files affected
- finance/model.py
- finance/outputs.json
- docs/FINANCIAL_MODEL.md
- tests/test_financial_model.py

## Tests required
- tests/test_financial_model.py

## Acceptance criteria
- Arithmetic checks pass; outputs reproducible
- Assumptions and unverified items clearly labelled

## Actual result
Done. Key results (250 students/school): contribution per school 319 JOD at 3.5 vs 1,018 JOD at 7.0. None of the three scenarios recovers the one-time investment (20,668 JOD) in three years; only the aggressive scenario at 7.0 turns annual net positive in year 3. Whether schools pay 7 JOD is **untested**. Verified inputs (price lists, CBJ peg, social-security rate) were retrieved during the audit phase and must be re-checked before external use; market sizing is not in the repository.

## Status
DONE

## Evidence
- `python3 finance/model.py`
- tests/test_financial_model.py: 6 passed
