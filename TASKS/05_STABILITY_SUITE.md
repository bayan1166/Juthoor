# 05 - Stability suite (repetition, concurrency, soak, integrity checker)

**Status: ENGINE-LEVEL DONE; API/DB-LEVEL BLOCKED**

## Objective
Prove repeatability and absence of corruption under repetition, concurrency and long runs.

## Current problem (before this work)
Only single-user tests existed; nothing exercised concurrent users, soak or DB integrity.

## Required implementation
- Engine-level suite: 10/50/100 repeated workflows, 2,500-answer soak, 20 interleaved students, threaded 5/10/20 students equal to solo runs, JSON round-trip, corruption detection.
- DB-level suite (`tests/test_stability_db.py`).
- SQL integrity checker (`app/integrity_sql.py`, `scripts/check_integrity.py`) with 13 ERROR checks, each verified against a seeded defect.

## Files affected
- tests/test_stability_engine.py
- tests/test_stability_db.py
- app/integrity_sql.py
- scripts/check_integrity.py
- scripts/verify_integrity_sql.sh

## Tests required
- tests/test_stability_engine.py
- tests/test_stability_db.py
- scripts/verify_integrity_sql.sh

## Acceptance criteria
- 0 corruption, lost updates, duplicates or leakage in every run

## Actual result
Engine-level: all pass (7 test functions covering the repetitions above). SQL integrity checker: clean database reports 0 violations and **13/13** error checks detect their seeded defect (run against real PostgreSQL 16 with psql). DB/API-level stability tests and `scripts/check_integrity.py` were written but **could not be run** here.

## Status
ENGINE-LEVEL DONE; API/DB-LEVEL BLOCKED

## Evidence
- `bash scripts/verify_integrity_sql.sh` -> INTEGRITY CHECKER VERIFIED
- tests/test_stability_engine.py passes; tests/test_stability_db.py BLOCKED (BLOCKED here = the build sandbox cannot install FastAPI/SQLAlchemy/psycopg2 (PyPI returns 403), so nothing that imports the app or opens a database from Python could be executed.)
- Team machine run: 756 passed, 2 failed in `test_stability_db.py` -> both root-caused and fixed (one production bug, one test-infrastructure bug); connection-leak assertions added. Re-run needed.
