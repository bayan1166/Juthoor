# 01 - P0 stability: concurrency, locking, idempotency

**Status: IMPLEMENTED; SQL-level behaviour VERIFIED; application-level tests BLOCKED**

## Objective
No lost updates, duplicate attempts or corrupted learner state when answers arrive concurrently or are retried.

## Current problem (before this work)
`submit_answer` read-modify-write the learner state without a row lock; two simultaneous requests could both read the same state and one update would be lost. There was no unique constraint on (student, skill) and no idempotency key, so a double-click or retry could be applied twice.

## Required implementation
- Row lock (`SELECT ... FOR UPDATE`) on the student state for every answer, drill-down and session load (`lock_student_state`).
- `INSERT ... ON CONFLICT DO NOTHING` to create the state row race-free.
- Unique constraint `uq_skill_mastery_student_skill`; CHECK constraints on mastery bounds and counts.
- Optional `request_id` on `POST /adaptive/answer`; receipts in `answer_receipts` (PK student_id + request_id) replay the stored response (`idempotent_replay`); reusing an id with a different answer returns 409 `request_id_reused`.
- Front end sends a fresh `request_id` per question/answer so a double click is harmless.
- Without a request_id, a second submit for an already-answered question is rejected (409), not applied twice.

## Files affected
- app/services/engine_bridge.py
- app/models/adaptive.py
- app/schemas/adaptive.py
- app/routers/adaptive.py
- app/static/js/views/practice.js
- migrations/versions/0002_skill_mastery_integrity.sql
- migrations/versions/0003_answer_receipts.sql

## Tests required
- tests/test_stability_db.py (parallel duplicate submits, request_id reuse, replay equality, 5/10/20 concurrent students, two-tab question, first-request race, constraints)
- scripts/verify_locking_sql.sh (real PostgreSQL, pgbench)

## Acceptance criteria
- 0 lost updates under 20 concurrent clients
- 0 duplicate attempts for the same request_id
- DB constraints reject duplicates and out-of-range values

## Actual result
Locking is verified on a real PostgreSQL 16 server with pgbench: 20 clients x 200 transactions, **without** the lock 3,800 of 4,000 increments were lost; **with** `FOR UPDATE` 0 were lost (5 x 100 also 0). The Python/ORM implementation and `tests/test_stability_db.py` are written and syntax-checked but **could not be executed** here. BLOCKED here = the build sandbox cannot install FastAPI/SQLAlchemy/psycopg2 (PyPI returns 403), so nothing that imports the app or opens a database from Python could be executed.

## Status
IMPLEMENTED; SQL-level behaviour VERIFIED; application-level tests BLOCKED

## Evidence
- `bash scripts/verify_locking_sql.sh` output: `(A) no lock ... lost updates: 3800`, `(B) FOR UPDATE ... lost updates: 0`, `PASS`
- `bash scripts/verify_migrations_sql.sh`: ALL MIGRATION SQL CHECKS PASSED (constraints enforced)
- `tests/test_stability_db.py` - BLOCKED (needs the app + PostgreSQL driver); run `python -m pytest -q tests/test_stability_db.py` on a machine with the dependencies
- Team machine run: 756 passed, 2 failed -> fixed (state-row provisioning bug in production code; connection-holding in the test). See FINAL_AUDIT.md "Reported from the team machine". Re-run needed.
- `bash scripts/verify_state_creation_sql.sh`: with the shipped pattern 0 errors, one row per key; without ON CONFLICT clients abort on unique violations.
