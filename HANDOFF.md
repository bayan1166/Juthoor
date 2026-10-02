# Handoff / تسليم

README.md is the full reference. This file records the current state and exactly what has been
verified, where, and by whom.

## What the MVP is
A prerequisite-aware adaptive learning and root-learning-gap diagnosis platform, demonstrated on one
domain (9 live mathematics lessons). Core loop: difficulty → evidence → prerequisite probes →
confirmation probe → named root with evidence + confidence level → targeted remediation → retry of the
original lesson → mastery update → teacher sees the diagnosis and its outcome. The practice page shows
the loop as a six-step stepper (مسار التشخيص).

## Fixes for the five failures reported from the team machine (475 passed / 5 failed / 480)
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

## Fix for the failing preflight check (40/41 → expected 41/41)
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
| Full `python -m pytest -q` on PostgreSQL, previous revision | team machine | 475 passed, 5 failed (480) — the five above |
| Full `python -m pytest -q` on PostgreSQL, previous revision | team machine | 495 passed (reported) |
| Full `python -m pytest -q` on PostgreSQL, this revision (538 tests by static count) | — | **not run yet** (the build sandbox cannot install packages from PyPI) |
| `python scripts/preflight.py`, previous revision | team machine | 40/41 (the check fixed above) |
| Engine/session/workflow/graph/bank/tutor/pilot tests (`--noconftest`, 413 tests), run twice | build sandbox | 413 passed, twice |
| `node tests/js/judge_smoke.mjs`, `smoke.mjs`, `main_smoke.mjs` | build sandbox | 8/8, 178/178, 20/20 |
| `python -m compileall -q app scripts tests` (Python 3.13 and 3.11) | build sandbox | pass |
| Real Chromium walk-through `tests/e2e/browser_e2e.py --oracle sim` against `tests/e2e/sim_server.py` (real UI + real engine, **simulated** HTTP/persistence) | build sandbox | 14/14, three consecutive runs |
| Real Chromium walk-through against `run_demo.py` + PostgreSQL (`--oracle db`) | — | **not run yet** |
| `python scripts/preflight.py` against `run_demo.py` | — | **not run yet** |
| Manual browser walk-through of the full loop + teacher view, previous revision | team machine | worked (reported) |

## Before judging (on the team machine)
```bash
python -m pip install -r requirements-dev.txt
python scripts/check_env.py --dev
python -m pytest -q                         # expect 538 passed
python -m compileall -q app scripts tests
cd tests/js && node judge_smoke.mjs && node smoke.mjs && node main_smoke.mjs && cd ../..
python run_demo.py --reset                  # terminal 1
python scripts/preflight.py                 # terminal 2
python tests/e2e/browser_e2e.py             # terminal 2 (needs playwright + chromium)
python run_demo.py --reset                  # restore the clean demo state
```

## Known limits
See README "Known limitations". No field data exists; make no accuracy, learning-gain or calibration claims.
