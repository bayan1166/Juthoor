# Handoff

README.md is the full reference; `FINAL_AUDIT.md` holds the before/after numbers; `TASKS/` has one file per work item with
its evidence. This file records the current state and exactly what has been verified, where, and what was **not**.

## What the MVP is
A prerequisite-aware adaptive learning and root-learning-gap diagnosis platform. The demo domain is 9 integer lessons
(Jordan Grade 6 mathematics) used as an example; the diagnosis core is subject- and grade-agnostic. Core loop: difficulty
-> evidence -> prerequisite probes -> confirmation probe -> named root with evidence + confidence level (or an explicit
"insufficient evidence" with what would settle it) -> targeted remediation -> retry of the original lesson -> mastery
update -> teacher sees the diagnosis and its outcome.

## Final hardening phase (this revision)
Added: evidence threshold + likelihood-ratio gate + `evidence_needed`; BKT bounds/validation; reproducible benchmark and
threshold sweep; row locking, upsert, unique/CHECK constraints and request-id idempotency; SQL migration runner;
database integrity checker; organisation join codes; tutor evaluation suite (and a quadratic-regex fix in the chat
safety filter); financial model rebuild. Details: `CHANGELOG_FINAL.md`, `TASKS/00_MASTER_TASKS.md`.

Honest headline numbers (synthetic learners, `python scripts/diagnostic_benchmark.py --reps 5`): clean known-root wrong-root
rate 19.1 % -> 2.7 %, premature declarations 50 % -> 0 %, root correct when committed 79.9 % -> 97.1 % (89.8 % overall).
The 95 % goal was not reached; lucky-guess learners are still misdiagnosed 30.2 % of the time; no real-student data exists.

## Earlier fixes (previous phase)
### Five failures reported from the team machine (475 passed / 5 failed / 480)
1. `test_api_backtracks_to_root_gap` — the diagnosis started from the lesson where the *current practice
   plan* began (adding) instead of where the learner's difficulty began (multiplying). The engine now
   diagnoses from `investigation_origin` (bottom of the return stack whose prerequisite chain contains the
   probed skill) in both the engine and the practice-plan branches, so the path follows real graph edges
   from multiplying down to the root. Side effect, intended and documented: errors on the whole chain now
   count as evidence, so the root can be named on its second own miss (test_engine expectation updated
   with the reason, and strengthened to assert the full path).
2. `test_avatar_requires_ownership` — `PurchaseResult` was built from the ORM `Wallet`. `WalletOut` now
   has `from_attributes=True` and the router converts with `WalletOut.model_validate(wallet)` (also for
   `/wallet` and `/convert`); validation stays on.
3. `test_student_buys_pro_with_mock_card` — `/auth/me` returned a naive datetime without zone. All API
   datetimes are stored as naive UTC and now serialise as UTC with `Z` (`app/schemas/common.py`); aware
   values are converted to UTC first, never relabelled.
4. `test_avatar_options_previews_and_ownership` — the shop table is empty on any database where
   `seed_shop.py` has not run (including the test DB), so the catalogue was empty *and* the ownership check
   skipped unknown items. `ensure_shop_catalog` (app/services/shop_catalog.py) inserts missing catalogue
   rows before shop reads, purchases and ownership checks.
5. `test_one_click_remediation_targets_gap_students` — one-click remediation re-assigned the same gap to
   students who had already been assigned it. Students already assigned remediation for that skill since
   their latest diagnosis are excluded; when nobody qualifies the API returns `422 no_students_with_gap`.
   The demo seed no longer pre-creates remediation assignments, so the teacher can create one live.

### Failing preflight check (40/41 -> expected 41/41)
`core workflow: repeated errors -> evidence gathering -> root detected (fresh learner)` failed because
wrong answers were reported as `no_difficulty`. Root cause, traced with the same scenario (fresh learner,
random displayed options): the verdict returned `no_difficulty` whenever no skill had *more* wrong than
right answers, e.g. right-then-wrong (1–1) or 5 right / 4 wrong. A wrong answer was therefore labelled
"no difficulty" (19% of wrong answers in a 2,000-run simulation). A second, rarer inconsistency (8.5% of
runs): at difficulty > 1 the engine stepped down a level before looking at the evidence, so the evidence
status could already say `root_identified` while no root was declared.
Fixes: errors without a failing skill are now `insufficient_evidence / mixed_evidence` (thresholds
unchanged), and `_handle_incorrect` checks the evidence first and declares a newly evidenced root on the
same answer. The preflight check now uses the full 20-answer Basic-plan budget. In a 3,000-run simulation
of the preflight scenario every pre-diagnosis wrong answer reports `insufficient_evidence`; 2/3,000 runs
(a learner who is right about half the time) need more than 20 answers, which is correct behaviour for
mixed evidence. New regression tests fail on the previous revision (14 failures) and pass now.

## Verification status
| Check | Where | Result |
|---|---|---|
| Full `python -m pytest -q` on PostgreSQL, previous revision | team machine | 495 passed (reported) |
| `python scripts/preflight.py`, previous revision | team machine | 41/41 expected after the fix above (reported 40/41 before it) |
| Pure-Python test files (17 files, `--noconftest`) | build sandbox | 540 passed, 2 skipped, 1 failed (`pydantic_settings` not installable there - environment, not a defect) |
| `node tests/js/judge_smoke.mjs`, `smoke.mjs`, `main_smoke.mjs` | build sandbox | 8/8, 179/179, 20/20 |
| `python -m compileall -q app scripts tests finance` | build sandbox | pass |
| `scripts/verify_migrations_sql.sh`, `verify_locking_sql.sh`, `verify_integrity_sql.sh`, `verify_state_creation_sql.sh` against PostgreSQL 16 (psql/pgbench) | build sandbox | all pass (locking: 3,800/4,000 lost updates without the lock, 0 with it) |
| Diagnostic benchmark `--reps 5` | build sandbox | deterministic; numbers above |
| Full `python -m pytest -q` on PostgreSQL, hardening revision (before the fixes below) | team machine | 756 passed, 2 failed (`test_stability_db.py`): state-row provisioning never committed (production bug) and the test held pooled connections (test bug). Both fixed in this revision - see CHANGELOG_FINAL.md / FINAL_AUDIT.md |
| Full `python -m pytest -q`, after the state-row/pool fixes | team machine | 765 passed, 1 failed (`test_api_contracts.py::test_question_state_and_answer_responses_match_their_schema`: the test required options on an `input` question, which is a supported type with no options). Test replaced by type-aware invariants; production code unchanged |
| `bash scripts/verify_state_creation_sql.sh` against PostgreSQL 16 | build sandbox | pass |
| **Full `python -m pytest -q` and `scripts/preflight.py` on this revision (after the contract-test fix)** | - | **NOT RUN here; please re-run and send the output** (sandbox cannot install FastAPI/SQLAlchemy/psycopg2) |
| New DB/API tests: `test_stability_db.py`, `test_authz_matrix.py`, `test_api_contracts.py`, PostgreSQL part of `test_migrations.py`, changed `test_api.py` | - | **NOT RUN** (syntax-checked only) |
| `python scripts/preflight.py` against `run_demo.py` | - | **NOT RUN** |
| Real-browser E2E against PostgreSQL | - | **NOT RUN** |

## Before judging (on the team machine)
```bash
python -m pip install -r requirements-dev.txt
python scripts/check_env.py --dev
python -m pytest -q                         # first real run of the new DB/API tests: fix or report any failure
python -m compileall -q app scripts tests finance
cd tests/js && node judge_smoke.mjs && node smoke.mjs && node main_smoke.mjs && cd ../..
python run_demo.py --reset                  # terminal 1 (prints the demo organisation join code)
python scripts/preflight.py                 # terminal 2
python tests/e2e/browser_e2e.py             # terminal 2 (needs playwright + chromium)
python scripts/check_integrity.py           # database integrity report
python run_demo.py --reset                  # restore the clean demo state
```
If a new DB/API test fails on first run, treat it as unverified code, not as a reason to loosen the test.

## Known limits
See README "Known limitations" and `FINAL_AUDIT.md`. No field data exists; make no accuracy, learning-gain or calibration claims.
