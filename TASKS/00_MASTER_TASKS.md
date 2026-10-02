# 00 - Master task list

Status words: DONE = implemented and verified here; IMPLEMENTED = code written but not executable here; BLOCKED = could not be run in the build sandbox (no PyPI access, so no FastAPI/SQLAlchemy/psycopg2); NOT DONE = deliberately or unavoidably not built.

| # | Task | Status | File |
|---|---|---|---|
| 01 | P0 stability | IMPLEMENTED; SQL VERIFIED; app tests BLOCKED | 01_P0_STABILITY.md |
| 02 | Diagnosis evidence/abstention | DONE | 02_DIAGNOSIS_EVIDENCE.md |
| 03 | BKT validation | DONE | 03_BKT_VALIDATION.md |
| 04 | Diagnostic benchmark | DONE (95 % not reached) | 04_DIAGNOSTIC_BENCHMARK.md |
| 05 | Stability suite | ENGINE DONE; API/DB BLOCKED | 05_STABILITY_SUITE.md |
| 06 | Security / authz | IMPLEMENTED; TESTS BLOCKED | 06_SECURITY_AUTHZ.md |
| 07 | DB migrations | SQL VERIFIED; runner BLOCKED | 07_DB_MIGRATIONS.md |
| 08 | Knowledge graph | DONE (no branching) | 08_KNOWLEDGE_GRAPH.md |
| 09 | API contracts + tutor eval | TUTOR DONE; API BLOCKED | 09_API_CONTRACTS_AND_TUTOR_EVAL.md |
| 10 | Financial model | DONE | 10_FINANCIAL_MODEL.md |
| 11 | Competitive advantage / teacher view | DONE learner; teacher extras NOT DONE | 11_COMPETITIVE_ADVANTAGE_TEACHER_VIEW.md |
| 12 | Performance / cleanup | IMPLEMENTED; measurement BLOCKED | 12_PERFORMANCE_CLEANUP.md |
| 13 | Final verification | PARTIAL | 13_FINAL_VERIFICATION.md |

Each task file lists Objective, Current problem, Required implementation, Files affected, Tests required, Acceptance criteria, Actual result, Status and Evidence. If a task file and the code disagree, the code and `FINAL_AUDIT.md` win.
