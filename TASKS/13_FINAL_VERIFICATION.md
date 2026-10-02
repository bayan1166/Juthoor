# 13 - Final verification

**Status: PARTIAL (see BLOCKED list)**

## Objective
Verify the delivered ZIP honestly.

## Current problem (before this work)
The full 495-test suite, preflight 41/41 and the browser E2E ran only on the team machine.

## Required implementation
- Run everything that can run; label the rest BLOCKED with reasons.
- Build `JUTHOOR_FINAL.zip` without secrets/caches; extract it and re-run the checks from the extracted copy.

## Files affected
- JUTHOOR_FINAL.zip
- FINAL_AUDIT.md
- CHANGELOG_FINAL.md

## Tests required
- All pure tests
- JS smoke tests
- SQL verification scripts
- Static compile of all Python

## Acceptance criteria
- Extracted ZIP passes the same checks; no secret or cache files inside

## Actual result
See FINAL_AUDIT.md for the numbers. **BLOCKED here**: the full `pytest` suite (needs FastAPI/SQLAlchemy/psycopg2), `scripts/preflight.py`, the DB-backed tests, the real-browser E2E against PostgreSQL. They must be run on a machine with the dependencies: `python -m pytest -q`, `python run_demo.py --reset`, `python scripts/preflight.py`.

## Status
PARTIAL (see BLOCKED list)

## Evidence
- See FINAL_AUDIT.md, section 'Verification actually run'
