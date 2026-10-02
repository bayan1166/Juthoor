# 04 - Reproducible diagnostic benchmark

**Status: DONE (target not reached)**

## Objective
Measure the diagnosis honestly with known ground truth; no hard-coded results.

## Current problem (before this work)
No benchmark existed; accuracy could not be stated or compared.

## Required implementation
- Synthetic learners driven through the real `session_core` + engine (scenarios: known root clean/noisy, lucky-correct, no gap clean/noisy/very noisy).
- Metrics: root accuracy (committed/overall), wrong-root rate, false-diagnosis rate, premature rate, abstention, determinism digest, calibration by confidence level.
- `scripts/diagnostic_benchmark.py` and `scripts/benchmark_sweep.py`.

## Files affected
- app/engine/benchmark.py
- scripts/diagnostic_benchmark.py
- scripts/benchmark_sweep.py
- benchmarks/before.json
- benchmarks/after.json
- benchmarks/sweep.json
- tests/test_diagnostic_benchmark.py

## Tests required
- tests/test_diagnostic_benchmark.py (determinism, metrics arithmetic, no-gap handling)

## Acceptance criteria
- Same seed gives an identical digest
- Before and after measured on the same cases
- 95 % only claimed if measured

## Actual result
810 cases per run, deterministic (digest identical on two runs). Clean known-root: correct when committed 79.9 % -> 97.1 %, overall 76.0 % -> 89.8 %, wrong root 19.1 % -> 2.7 %, premature 50 % -> 0 %. Noisy: overall 63.1 % -> 77.8 %. **The 95 % target was not reached overall**; lucky-correct learners are still misdiagnosed 30.2 % of the time and the no-gap false-diagnosis rate (2.2 / 8.9 / 20.0 %) is unchanged. These are synthetic-learner numbers, not classroom accuracy.

## Status
DONE (target not reached)

## Evidence
- `python scripts/diagnostic_benchmark.py --reps 5` (rc 0, deterministic true)
- `benchmarks/after.json`, `benchmarks/before.json`, `benchmarks/sweep.json`
