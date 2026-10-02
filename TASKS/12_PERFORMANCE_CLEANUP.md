# 12 - Performance and code cleanup

**Status: IMPLEMENTED; MEASUREMENT BLOCKED**

## Objective
Remove the N+1 in `diagnosis_history`; remove hard-coded course wording from engine prompts and plan rules.

## Current problem (before this work)
`diagnosis_history` issued a query per diagnosis; Grade 6 / integers wording was hard-coded in the tutor prompt and plan rules.

## Required implementation
- One query for attempts (capped at 5,000) used for all diagnoses.
- Course wording moved to `ecfg.COURSE` in `app/engine/config.py`.
- Receipts older than 7 days purged by the migration runner.

## Files affected
- app/services/engine_bridge.py
- app/engine/config.py
- app/services/rag/socratic.py
- app/services/plan_rules.py

## Tests required
- existing API tests (BLOCKED here)

## Acceptance criteria
- Constant number of queries regardless of diagnosis count

## Actual result
Code change made. **No query-count or timing measurement was taken** because the app could not run against a database here. Hard-coded wording moved to config; the curriculum itself is still the integer/fraction map.

## Status
IMPLEMENTED; MEASUREMENT BLOCKED

## Evidence
- Code review only; no timing data
