> **Historical / internal document.** Written before the locked positioning. Where it describes teachers, schools, classrooms, a school pilot or Juthoor as a Grade 6 mathematics product, it is superseded: Juthoor is a general B2C learning platform (student = user, parent = buyer) and Grade 6 mathematics is only the current demo content. Educators appear only as internal reviewers. Current reference: `docs/POSITIONING.md`.

# 06 - Security and authorisation

**Status: IMPLEMENTED; TESTS BLOCKED**

## Objective
Org membership must be controlled; every role/resource pair must be tested, including response-body leakage.

## Current problem (before this work)
Anyone could register as a teacher in any organisation; the password-reset code was logged in all modes; there was no matrix test of who can see what.

## Required implementation
- Organisation join code (stored as SHA-256 hash; `invalid_org_code` 403, throttled); teachers and joiners of an org with a code must present it.
- Reset code is logged only in demo mode; otherwise an error log says it was not delivered.
- Authorisation matrix (role x resource) that also asserts other users' data does not appear in the body.

## Files affected
- app/services/org_access.py
- app/routers/auth.py
- app/schemas/auth.py
- app/models/org.py
- scripts/org_join_code.py
- scripts/seed_demo.py
- migrations/versions/0004_org_join_code.sql
- tests/test_authz_matrix.py
- tests/test_api.py

## Tests required
- tests/test_authz_matrix.py
- tests/test_api.py::test_teacher_sees_their_org (updated for the org code)

## Acceptance criteria
- Cross-org and cross-role reads denied with no body leakage
- Registration cannot join an org without its code

## Actual result
Implemented and written; **not executed** here (BLOCKED here = the build sandbox cannot install FastAPI/SQLAlchemy/psycopg2 (PyPI returns 403), so nothing that imports the app or opens a database from Python could be executed.). `tests/test_api.py::test_teacher_sees_their_org` was changed because registration now requires the org code (documented behaviour change). Not done: email delivery of reset codes (no SMTP in this environment), rotation of join codes beyond re-running `scripts/org_join_code.py`.

## Status
IMPLEMENTED; TESTS BLOCKED

## Evidence
- tests/test_authz_matrix.py syntax-checked (ast.parse) only
- migration 0004 applied on PostgreSQL 16 by `scripts/verify_migrations_sql.sh`
