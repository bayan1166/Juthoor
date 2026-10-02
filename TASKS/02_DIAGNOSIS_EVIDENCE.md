# 02 - Diagnosis: evidence threshold and abstention

**Status: DONE**

## Objective
One lucky correct answer must not mark a prerequisite 'solid'; the engine must abstain, and say why, when evidence is thin.

## Current problem (before this work)
`solid(s)` accepted a single correct answer. On the benchmark the original engine named a wrong root in 19.1 % of clean known-root cases and declared the root 'prematurely' (prerequisites barely observed) in 50 % of them.

## Required implementation
- `solid` requires mastered, or no wrong answers and at least `MIN_SOLID_EVIDENCE` (2) correct.
- Log-space likelihood ratio of the leading candidate vs no gap (`likelihood_ratio`, validated inputs); a root needs LR >= `MIN_ROOT_LR` (20) else `root_needs_confirmation`.
- `insufficient_evidence` verdict with a reason and machine-readable `evidence_needed`; surfaced in `evidence_status` and in the practice UI.
- Thresholds live in `app/engine/config.py`.

## Files affected
- app/engine/diagnosis.py
- app/engine/config.py
- app/engine/adaptive_engine.py
- app/services/session_core.py
- app/static/js/views/practice.js

## Tests required
- tests/test_diagnosis_engine.py
- tests/test_diagnosis_flow.py (one existing test updated, one regression added)
- tests/test_evidence_needed.py
- tests/js/smoke.mjs

## Acceptance criteria
- A single correct prerequisite answer never clears it
- Every insufficient verdict carries a reason and evidence_needed
- No previously passing behavioural test weakened without a documented reason

## Actual result
Done. One existing test (`test_a_passed_prerequisite_probe_stops_the_descent`) was changed because the product rule changed (a prerequisite now needs 2 correct answers); the reason is recorded in the test and in CHANGELOG_FINAL.md. A stricter profile (3 correct, LR 100) broke 35 tests that encode product behaviour, so it was **not** shipped; the sweep is in `benchmarks/sweep.json`.

## Status
DONE

## Evidence
- Pure test files: 540 passed, 2 skipped, 1 failed (the failure is `ModuleNotFoundError: pydantic_settings` in this sandbox, not a defect)
- `benchmarks/before.json` vs `benchmarks/after.json`
- Regression: `test_one_lucky_correct_prerequisite_answer_does_not_clear_the_prerequisite`
