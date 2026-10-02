# Final audit

Team TechSparks - Juthoor. Written from the commands actually run; anything not run is marked **BLOCKED** with the reason.

## Before

| Area | State at the start of this phase |
|---|---|
| Tests | 495 passed and preflight 41/41, reported from the team machine (not reproducible in the build sandbox) |
| Diagnosis | One correct answer made a prerequisite "solid". Benchmark (810 synthetic cases): known root, clean answers - wrong root 19.1 %, premature declaration 50.0 %, correct overall 76.0 % (79.9 % when it named a root); noisy 63.1 %; lucky-correct 45.3 %; no-gap false diagnosis 2.2 / 8.9 / 20.0 % |
| BKT | No clamping; persisted state trusted |
| Concurrency | No row lock, no unique constraint on (student, skill), no idempotency; two simultaneous answers could lose an update |
| Auth | Any user could register as a teacher of any organisation; reset code always logged |
| DB | Ad-hoc start-up ALTERs, no migration history |
| Tutor safety filter | E-mail regex backtracked quadratically (found in this phase) |
| Finance | Single-price model, no tested arithmetic |

## After

| Area | State now | Evidence |
|---|---|---|
| Diagnosis | Evidence threshold (2 correct, none wrong), likelihood ratio >= 20, abstention with `evidence_needed`. Known root clean: wrong root 2.7 %, premature 0 %, correct 97.1 % when committed / 89.8 % overall. Noisy: 91.1 % / 77.8 %. Lucky-correct: wrong root 30.2 %. Abstention (clean) 7.6 %. Calibration: high 86.3 % (n=401), medium 80.0 % (n=180). Deterministic. | `benchmarks/after.json`, `python scripts/diagnostic_benchmark.py --reps 5` |
| BKT | Clamped to [0.001, 0.999], NaN/inf-safe, non-absorbing, parameters validated, state sanitised | `tests/test_bkt_properties.py` |
| Concurrency | Row lock + upsert + unique/CHECK constraints + idempotency receipts. Without lock 3,800 of 4,000 updates lost; with lock 0 lost | `scripts/verify_locking_sql.sh` on PostgreSQL 16 (pgbench, 20 clients x 200 tx) |
| Auth | Org join code (hashed), throttled; reset code logged only in demo mode; authorisation matrix written | `tests/test_authz_matrix.py` - **BLOCKED** (not executed) |
| DB | Versioned SQL migrations, advisory lock, idempotent; data preserved on repair | `scripts/verify_migrations_sql.sh` ALL PASS; DB integrity checker 13/13 seeded defects detected |
| Tutor eval | On/off-topic, injection, hostile input, fuzz, solver vs Python, linear-time check; ReDoS fixed | `tests/test_tutor_eval.py` |
| Finance | Reproducible model, 3.5 vs 7.0 JOD, teacher/family separate, break-even, burn, 3 scenarios | `docs/FINANCIAL_MODEL.md`, `tests/test_financial_model.py` |
| UI | Learner sees what evidence would settle the diagnosis | `tests/js/smoke.mjs` 179/179 |

## Verification actually run (build sandbox, final state)

| Check | Result |
|---|---|
| Pure Python tests (`python3 -m pytest -q --noconftest -p no:cacheprovider` over 17 files: engine, flow, BKT, graph, evidence, benchmark, stability-engine, tutor eval, financial model, migrations validation, offline tutor, session, pilot, bank, logic, safety) | **540 passed, 2 skipped, 1 failed** - the failure is `ModuleNotFoundError: pydantic_settings` (missing package in the sandbox, not a code defect); the 2 skips are the PostgreSQL tests in `test_migrations.py` |
| JS UI tests (`judge_smoke`, `smoke`, `main_smoke`) | 8/8, 179/179, 20/20 |
| `python -m compileall -q app scripts tests finance` | pass |
| `scripts/verify_migrations_sql.sh`, `verify_locking_sql.sh`, `verify_integrity_sql.sh` (PostgreSQL 16 via psql) | all pass |
| Benchmark `--reps 5` | deterministic, results above |

## Reported from the team machine, and what was done about it

`python -m pytest -q` on PostgreSQL: **756 passed, 2 failed** (both in `tests/test_stability_db.py`). Neither was treated as acceptable.

| Failing test | Root cause | Kind | Fix |
|---|---|---|---|
| `test_first_request_race_creates_one_state_row` (`assert 0 == 1`) | `GET /state` executed an INSERT but never committed; the session closed and rolled it back, so no row was ever stored (and every read issued a pointless INSERT) | production code | read paths are read-only; own-state read provisions with INSERT ... ON CONFLICT DO NOTHING + commit; write path creates-then-locks |
| `test_many_students_...[20]` (`QueuePool limit of size 5 overflow 10`) | the test held one pooled connection per thread open for the whole journey (long-lived session with an open transaction), exhausting the pool before the requests could connect | test infrastructure (production `get_db` closes every session) | short-lived session per read; pool options shared between app and tests and configurable; leak assertions added |

**Second team-machine run: 765 passed, 1 failed.** `test_question_state_and_answer_responses_match_their_schema` expected options on an `input` question. Source shows `input` is a supported type with `options=[]` by design (`session_core._options`, `practice.js`, `preflight.py`, `test_api.py`), so the test was wrong and was replaced by type-aware invariants (stricter, not weaker) plus a bank-wide contract test (`tests/test_question_contract.py`, 8 tests, passing in the sandbox). Production code unchanged. Not re-run on the team machine yet.

Checked and found correct: unique key on the state row (primary key `student_id`), `SELECT ... FOR UPDATE` on every write path (all writers go through `lock_student_state`), atomic create/update, race-free first insert, `get_db` closing in a `finally`.
The two fixed tests and the new ones were **not re-run in the build sandbox** (no database driver); the SQL pattern was verified with `scripts/verify_state_creation_sql.sh`. **Please re-run `python -m pytest -q` and send the result.**

## BLOCKED (could not be run here)

The sandbox has no PyPI access (403 by organisation policy), so FastAPI, SQLAlchemy, psycopg2, pydantic-settings, bcrypt and hypothesis could not be installed. Therefore **not executed**:

- the full `python -m pytest -q` suite (the previous 495 plus the new DB/API tests: `test_stability_db.py`, `test_authz_matrix.py`, `test_api_contracts.py`, the DB part of `test_migrations.py`, and the changed `test_api.py`) - the new files are syntax-checked only;
- `python scripts/preflight.py` against a running server;
- `python tests/e2e/browser_e2e.py` against PostgreSQL;
- the Python/ORM code paths for locking, receipts, org join code and `app/migrations.py` (the SQL they rely on was verified directly in PostgreSQL);
- query-count / timing measurement for the `diagnosis_history` N+1 fix;
- Alembic (not installed; a small SQL runner is used instead).

Does this block acceptance? For the engine, benchmark, SQL schema and docs: no. For the claim "the application is stable under concurrent HTTP load": **yes** - that is shown at the SQL level only until `python -m pytest -q` passes on a machine with the dependencies.

## Remaining limitations

- The 95 % diagnosis target was **not** reached; numbers are from synthetic learners only. No field data.
- Lucky-correct learners are still misdiagnosed 30.2 % of the time; the no-gap false-diagnosis rate is unchanged (2.2 / 8.9 / 20.0 %). Stricter thresholds in `benchmarks/sweep.json` trade this against abstention.
- One test (`test_a_passed_prerequisite_probe_stops_the_descent`) was changed because the product rule changed; `test_teacher_sees_their_org` was changed because registration now needs the org code. No test was deleted or weakened to pass.
- The shipped graph is a chain; branching is not on curriculum content. The integers -> fractions edge is unreviewed.
- Teacher view does not show the likelihood ratio or `evidence_needed` (not persisted).
- Password-reset codes are not delivered by e-mail unless SMTP is configured and wired; outside demo mode they are not logged.
- Rate limiting is in-process (single worker); no HTTP load test was run.
- The tutor guardrail is keyword-based.
- Financial model: assumptions tagged A are not evidence; willingness to pay 7 JOD is untested; the 32-respondent survey is early interest validation only.
