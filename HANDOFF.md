# Handoff

README.md is the full reference; `docs/FINAL_B2C_AUDIT.md` records the B2C cleanup and what changed in each round.
This file records the current state and exactly what has been verified, where, and what was **not**.

## What the product is
A general B2C learning platform that finds where the gap started. Student = user, parent/guardian = buyer. There is
no teacher product, no school product, no classroom feature and no teacher/school pricing. Plans: Free 0 JOD,
Pro Monthly 4.50 JOD, Pro Academic Year 32 JOD (a floor price hypothesis). The current demo content is 9 lessons of
Jordan Grade 6 mathematics; it is content, not the product's scope, and the diagnosis core is subject- and
grade-agnostic (`docs/POSITIONING.md`).

Core loop: difficulty -> evidence -> prerequisite probes -> confirmation probe -> named root with evidence + an ordinal
confidence level (or an explicit "insufficient evidence" with what would settle it) -> targeted remediation -> retry
of the original lesson -> mastery update -> the parent report shows where the gap started, the evidence and what happened.

Roles: `student` and `parent` (self-registration); `platform_admin` is an internal moderation account for community
safety reports (`/moderation/*`), cannot be self-registered and has no product screen.

## Honest headline numbers (synthetic learners only)
`python scripts/diagnostic_benchmark.py --reps 5`: root correct when committed 97.1 % (89.8 % of all gap cases), wrong root
2.7 %, no premature declarations. The 95 % goal was not reached; lucky-guess learners are still misdiagnosed 30.2 % of
the time; no real-student data exists.

## Verification status
| Check | Where | Result |
|---|---|---|
| Full `python -m pytest -q` (PostgreSQL), revision before the teacher/school removal | team machine | 798 passed, 1 failed: `test_stability_db.py::test_reusing_a_request_id_…` was flaky (it assumed every first question has options; typed-input questions have none). Test fixed; product unchanged |
| Full `python -m pytest -q` on **this** revision (teacher/school subsystem removed, tests rewritten for B2C) | - | **NOT RUN here** (the build sandbox cannot install FastAPI/SQLAlchemy/psycopg2). Please run and send the output |
| `python scripts/preflight.py` on this revision | - | **NOT RUN here** (needs PostgreSQL + the app) |
| Pure-Python checks run here: finance tests, pilot/agreement tests, positioning tests, static import/undefined-name check over app/scripts/tests/finance | build sandbox | pass (see `docs/FINAL_B2C_AUDIT.md`) |
| `node tests/js/judge_smoke.mjs`, `smoke.mjs`, `main_smoke.mjs` | build sandbox | 10/10, 167/167, 21/21 |
| Real-browser E2E (`tests/e2e/browser_e2e.py --oracle sim`) against the simulated backend (real engine) | build sandbox | 15/15 |
| `python -m compileall -q app scripts tests finance` | build sandbox | pass |

## Before judging (on the team machine)
Extract the release into an **empty** folder (extracting over an older copy leaves deleted files behind).
```bash
python -m pip install -r requirements-dev.txt
python scripts/check_env.py --dev
python -m pytest -q
python -m compileall -q app scripts tests finance
cd tests/js && node judge_smoke.mjs && node smoke.mjs && node main_smoke.mjs && cd ../..
python run_demo.py --reset                  # terminal 1 (wipes and reseeds; old databases need this once)
python scripts/preflight.py                 # terminal 2
python tests/e2e/browser_e2e.py             # terminal 2 (needs playwright + chromium)
python scripts/check_integrity.py           # database integrity report
python run_demo.py --reset                  # restore the clean demo state
```
If a test fails, treat it as unverified code, not as a reason to loosen the test.

## Known limits
See README "Known limitations". No field data exists; make no accuracy, learning-gain or calibration claims.
