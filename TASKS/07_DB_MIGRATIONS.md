# 07 - Database migrations

**Status: SQL VERIFIED; PYTHON RUNNER BLOCKED**

## Objective
Versioned, transactional migrations: fresh DB, upgrade of an old DB, data preserved, PostgreSQL only (no silent SQLite).

## Current problem (before this work)
Schema evolution was ad-hoc `ALTER` statements at start-up with no record of what ran.

## Required implementation
- `migrations/versions/NNNN_*.sql` run in order by `app/migrations.py` under an advisory lock, recorded in `schema_migrations`; idempotent files.
- File validation is pure (`app/migration_files.py`): naming, duplicates, gaps, no percent sign.
- Migration 0002 de-duplicates `skill_mastery` and repairs out-of-range values before adding constraints.
- SQLite remains an explicit, warned, non-production mode.

## Files affected
- app/migrations.py
- app/migration_files.py
- migrations/versions/*.sql
- app/database.py
- scripts/verify_migrations_sql.sh
- tests/test_migrations.py

## Tests required
- tests/test_migrations.py (pure validation: 7 pass; 2 PostgreSQL tests skip without a driver)
- scripts/verify_migrations_sql.sh

## Acceptance criteria
- Fresh DB reaches the final schema
- Old/degraded DB is repaired without losing rows
- Second run is a no-op

## Actual result
The SQL files were verified against a real PostgreSQL 16 server with psql: duplicate collapse, clamp repair, data preservation, constraint enforcement, idempotent re-run, fresh database - ALL PASS. **Alembic was not used**: it could not be installed or tested here, so a small SQL runner was written instead; adopting Alembic later is possible. The Python runner (`apply_pending`) and the two PostgreSQL pytest tests were **not executed** here.

## Status
SQL VERIFIED; PYTHON RUNNER BLOCKED

## Evidence
- `bash scripts/verify_migrations_sql.sh` -> ALL MIGRATION SQL CHECKS PASSED
- tests/test_migrations.py: 7 passed, 2 skipped
