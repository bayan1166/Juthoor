# Changelog (final hardening phase)

## Added
- `app/engine/benchmark.py`, `scripts/diagnostic_benchmark.py`, `scripts/benchmark_sweep.py`, `benchmarks/{before,after,sweep}.json` - reproducible diagnostic benchmark and threshold sweep.
- `app/engine/integrity.py` - learner-state invariant checks.
- `app/migrations.py`, `app/migration_files.py`, `migrations/versions/0001-0004*.sql` - versioned, idempotent, advisory-locked SQL migrations.
- `app/integrity_sql.py`, `scripts/check_integrity.py` - database integrity checker.
- `app/services/org_access.py`, `scripts/org_join_code.py` - organisation join codes.
- `finance/model.py`, `finance/outputs.json`, `docs/FINANCIAL_MODEL.md`, `docs/COMPETITIVE_ADVANTAGE.md`.
- `scripts/verify_{migrations,locking,integrity}_sql.sh` - checks that run against a real PostgreSQL with psql/pgbench.
- Tests: `test_bkt_properties`, `test_knowledge_graph_integrity`, `test_evidence_needed`, `test_diagnostic_benchmark`, `test_stability_engine`, `test_stability_db`, `test_authz_matrix`, `test_api_contracts`, `test_tutor_eval`, `test_migrations`, `test_financial_model`.
- `TASKS/00-13`, `FINAL_AUDIT.md`.

## Changed
- Diagnosis: `solid` needs 2 correct answers and no wrong; likelihood-ratio gate (20); `insufficient_evidence` carries `evidence_needed` (`app/engine/diagnosis.py`, `config.py`, `adaptive_engine.py`, `session_core.py`).
- BKT: clamped, NaN-safe, validated parameters; sanitised persisted state.
- Answer submission: row lock, upsert, optional `request_id` idempotency with stored receipts (`engine_bridge.py`, `models/adaptive.py`, `schemas/adaptive.py`, `routers/adaptive.py`, `practice.js`). `diagnosis_history` N+1 replaced by one query.
- Registration: organisation join code required for teachers and for organisations that have a code; reset code logged only in demo mode.
- `chat_safety.py`: e-mail pattern bounded and guarded (was quadratic on long input).
- Course wording moved from `socratic.py` / `plan_rules.py` to `app/engine/config.py` (`COURSE`).
- `app/database.py`: warns on SQLite; runs migrations after `create_all`.
- Practice UI shows what evidence would settle the diagnosis; JS fixture regenerated from the real engine.
- Seed script prints the demo organisation join code.

## Fixed after the first real run on the team machine (756 passed, 2 failed)
- `test_first_request_race_creates_one_state_row` - **production bug**: `GET /adaptive/state` called an INSERT for a missing state row but never committed, so the row was always rolled back (and every read of every learner issued a useless INSERT, including each member in a teacher's class view). Now: `_load_state(lock=False)` is read-only (a learner without a row sees the default start state, nothing is written); a learner opening their own state/bootstrap calls `engine_bridge.provision_state` (INSERT ... ON CONFLICT DO NOTHING + commit, race-free); the locking write path creates the row itself (select FOR UPDATE -> insert on conflict -> select FOR UPDATE).
- `test_many_students_answer_at_the_same_time_without_corruption[20]` - **test-infrastructure bug**: each thread kept a long-lived `TestingSession` that held a pooled connection (an open transaction) for its whole journey, so 20 threads consumed the pool before their HTTP requests could get a connection. The helper now reads through a short-lived session. Production code was checked and does not hold more than one connection per request (`get_db` always closes).
- Pool: sizes are now configurable (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, defaults 10/20/30) through one `engine_options()` shared by the app and the test suite. The pool was not simply enlarged to hide the leak: new tests assert nothing stays checked out or idle in a transaction.
- New tests: real `get_db` closes on normal end and on exception; failing requests release their connection; 30 parallel requests leave no connection behind; unique key on the state row; atomic provisioning (exactly one of 8 racing callers creates it); write-path first-request race; read paths never write; own-state read stores exactly one row.
- New `scripts/verify_state_creation_sql.sh` (PostgreSQL + pgbench): without ON CONFLICT clients abort on unique violations; with the shipped pattern 0 errors, one row per key, one increment per transaction.

## Fixed after the second real run on the team machine (765 passed, 1 failed)
- `tests/test_api_contracts.py::test_question_state_and_answer_responses_match_their_schema` asserted `qo.options` is non-empty for every question. **The contract allows `type="input"` with `options=[]`**: source proof - `session_core._options` returns `[]` for any type other than `mcq`/`tf` (typed answers), the bank builds 164 of ~810 sampled questions as `input` (e.g. "ما معكوس العدد 9؟ (اكتب العدد فقط)"), `practice.js` renders a text field for `type === 'input'`, `preflight.py` and `test_api.py` already treat input as valid. The test was wrong, production code is right. No options were added to input questions.
- The assertion is now type-aware (`mcq`: >= 2 distinct options; `tf`: exactly صح/خطأ; `input`: options must be empty; all types: skill in graph, difficulty 1-3, non-empty question and hint, type in {mcq, tf, input}) - stricter than before (an input question that carried options, or an unknown type, now fails).
- New `tests/test_question_contract.py` (pure, runs without the web stack): the same invariants over every skill x difficulty of the bank (30 draws per cell), a regression for the reported inverse-of-9 input question, a check that typed answers are accepted, and a checker self-test that proves each violation is rejected. New API test serves 25 consecutive questions and checks every one against its type's contract.

## Tests changed (with reason)
- `tests/test_diagnosis_flow.py::test_a_passed_prerequisite_probe_stops_the_descent` - a prerequisite now needs 2 correct answers (rule change); regression test added for the single lucky answer.
- `tests/test_api.py::test_teacher_sees_their_org` - registration now needs the organisation code.
- `tests/js/smoke.mjs` - one new check; fixture `omar_flow.json` regenerated.

No test was deleted.

## Not done / BLOCKED
See `FINAL_AUDIT.md`.
