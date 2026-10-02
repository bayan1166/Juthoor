# 03 - BKT validation, bounds and NaN safety

**Status: DONE**

## Objective
BKT must never produce NaN/inf or an absorbing 0/1 state, and parameters must be validated.

## Current problem (before this work)
`bkt_update` did not clamp; stored state from JSON was trusted (negative attempts, correct > attempts, out-of-range mastery).

## Required implementation
- `P_MIN=0.001`, `P_MAX=0.999`; `clamp_p`; `bkt_update` clamps input and output (NaN-safe, non-absorbing).
- `validate_bkt_params` runs at import.
- `StudentState.from_json` sanitises persisted values.
- `app/engine/integrity.py::check_state` for state invariants.

## Files affected
- app/engine/adaptive_engine.py
- app/engine/integrity.py

## Tests required
- tests/test_bkt_properties.py (property-style, seeded: bounds, monotonicity, NaN/inf inputs, non-absorbing, calibration, last-3 baseline comparison)

## Acceptance criteria
- p always in [0.001, 0.999]
- NaN/inf input never escapes
- BKT beats the last-N baseline on synthetic learners generated from BKT assumptions

## Actual result
Done. Note on honesty: the calibration/baseline tests use synthetic learners drawn from the BKT's own assumptions; they test the implementation, not real-student calibration. Finding: the engine can legitimately leave a mastered skill whose prerequisite was later declared a gap, so `integrity.lineage_warnings` reports it as a warning, not a failure.

## Status
DONE

## Evidence
- `python -m pytest tests/test_bkt_properties.py` -> all pass (run in this sandbox with `--noconftest`)
