# B2C release record

**Product (locked):** Juthoor is a general, subject- and grade-agnostic learning platform built around adaptive learning,
prerequisite-gap detection, evidence-first root diagnosis, targeted remediation and mastery. It is B2C: the student is the
user and the parent/guardian is the buyer. There is **no** teacher product, school product, classroom feature, teacher or
school subscription, seat, dashboard, billing or checkout. The Grade 6 mathematics curriculum is only the current demo
content (`app/engine/config.py` → `COURSE`).

**Plans (server-authoritative, minor units):** Free 0 / Pro Monthly 4500 (4.50 JOD) / Pro Academic Year 32000 (32.00 JOD).
Pro is owned by the learner, or bought by a parent for their own child.

## Final cleanup: the teacher/school subsystem was removed

### Dependency trace (what used what)
- `app/models/classroom.py` (Classroom, ClassroomMember, Assignment, Submission, Quiz, QuizQuestion, QuizAttempt) was used by
  `app/routers/classroom.py`, `app/deps.py` (teacher access to class members), `scripts/seed_demo.py` and `app/models/__init__.py`.
- `app/routers/classroom.py` used `class_analytics`, `quiz_scoring`, `remediation` (one-click class remediation), `plans.require_school`
  and also hosted the **teacher review of community safety reports** (the only part with a B2C need: child safety).
- `app/services/org_access.py` + `Organization` were used by registration (`org_slug`/`org_code`), the teacher trial, the cohort
  insights endpoint, `/me/students` for teachers and `require_student_access` (same-organization reads).
- `teacher.js` was the only consumer of the classroom API in the UI; its diagnosis-record card was the only piece with parent value.

### Deleted files (and why each deletion is safe)
| File | Why it is safe |
|---|---|
| `app/models/classroom.py` | Only used by the classroom router, the teacher branch of `deps.py` and the demo seed, all removed/refactored. No learner data lives in these tables. |
| `app/routers/classroom.py` | The whole classroom/quiz/assignment/teacher-analytics API. Its safety-report review moved to `app/routers/moderation.py` (internal moderation account). |
| `app/schemas/classroom.py` | Request models of the removed router; `ReportResolve` moved to `app/schemas/community.py`. |
| `app/services/class_analytics.py` | Class risk/ranking for teacher dashboards only. |
| `app/services/quiz_scoring.py` | Class quizzes/races only (the learner practice engine never used it). |
| `app/services/remediation.py` | Teacher one-click class remediation only; learner remediation lives in the engine (`adaptive_engine`, `session_core`) and is unchanged. |
| `app/services/org_access.py` | Organization join codes for teacher onboarding only. |
| `app/static/js/views/teacher.js` | Teacher dashboard. Its diagnosis-record card now lives in `parent.js` (`diagnosisRecord`). |
| `scripts/org_join_code.py` | Issued organization join codes. |
| `docs/teacher_agreement_template.csv` | Replaced by `docs/expert_agreement_template.csv` (blind review by an independent expert, outside the product). |
| `docs/audit/` (4 files) | Historical audit/Q&A/business notes written for the old school model; contradicted the B2C positioning. |
| `TASKS/` (14 files), `FINAL_AUDIT.md`, `CHANGELOG_FINAL.md` | Historical work logs of the old model (organization codes, school SaaS finance, teacher view, outdated "not run" statuses). Current facts are in README, HANDOFF, this file and `docs/COMPETITIVE_ADVANTAGE.md`. |

### Database (non-destructive)
- Models no longer define `organizations`, the classroom tables, `users.organization_id`, `users.trial_ends_at` or
  `diagnosis_events.teacher_verdict`. Fresh databases (`run_demo.py --reset`, the test suite) are created without them.
- Existing databases are **not** altered destructively: old tables/columns stay and are simply unused.
- `migrations/versions/0004_org_join_code.sql` is kept as a documented no-op (`SELECT 1;`) so the history stays consecutive
  (`tests/test_migrations.py` requires consecutive versions); `scripts/verify_migrations_sql.sh` now checks that a legacy
  `organizations` table is left untouched.
- Enums: `UserRole` = student, parent, platform_admin; `PlanTierUser` = basic, pro.

### Auth and roles
- Self-registration: student and parent only (`teacher`, `org_admin`, `platform_admin`, anything else → 422).
  Legacy `org_slug`/`org_code` fields are ignored; no organization onboarding exists.
- `platform_admin` is kept as an **internal** moderation account (child-safety reports): not self-registrable, never a buyer,
  no learning screens (the SPA shows a short "internal account" notice).
- JWTs no longer carry an organization claim. `/auth/me` no longer returns organization or trial fields.

### Plans, payments
- Catalogue: Free + Pro (monthly 4.50, academic year 32). No school plan, no class-sponsored Pro, no trial.
- Only students and parents can check out (others → 403 `pro_plan_for_students`); a parent only for their own child.
- Mock checkout only in demo mode or with `ALLOW_MOCK_PAYMENTS`; a failing real provider never falls back to the mock.

### Product surfaces kept (checked, coherent with B2C)
- **Community** (friends, messages, blocking, reporting): an existing student feature, hidden in judge mode (the avatar shop and the coin/gem economy were removed later, see `docs/UI_BEHAVIOUR_CHANGES.md`),
  no teacher/school dependency. Safety reports are now reviewed by the internal moderation account.
- **Parent report** now includes the explainable diagnosis record (origin, root, ordinal confidence, evidence, next step, outcome).

### Finance
`finance/model.py` was rebuilt as the B2C model (same assumptions and numbers as the Task 2 document; verified identical);
`finance/outputs.json` and `docs/FINANCIAL_MODEL.md` regenerated; `tests/test_financial_model.py` rewritten for the B2C
arithmetic (locked prices, unit economics, break-even minimality, renewals, determinism).

### Tests changed on purpose (none weakened)
- Removed (feature no longer exists): school trial, classroom creation/joining, assignments upload/grade, quiz race and manual
  quiz validation, class analytics/CSV export, one-click class remediation, organization join-code registration,
  cohort insights, teacher roster, `quiz_scoring`/`class_analytics`/`remediation` unit tests, trial-days unit test.
- Replaced with B2C equivalents: parent ↔ own children authorization matrix (incl. siblings, stranger parents, internal admin),
  teacher/org/school signup refused, legacy org fields create nothing, guardian link only to an existing parent, moderation review
  by the internal account only, a named gap reaching the learner and their parent only, parent report as the buyer view,
  subscription ownership (own / bought by parent), only students and parents can buy, classroom/organization APIs return 404,
  core-workflow scenarios E/I/N now use the parent instead of a teacher, preflight checks 6 B2C facts instead of 6 teacher facts.
- Flaky test fixed at its cause: `test_reusing_a_request_id_for_a_different_answer_is_rejected_not_replayed` assumed every first
  question has options; typed-input questions have none.

## Earlier rounds (summary)
1. B2C pricing 0 / 4.50 / 32; School plan removed from the catalogue; upgrade CTA visible (judge mode used to hide `/plans`);
   honest demo checkout; "صفوفي" and the classes view removed.
2. Positioning: subject/grade shown only as content metadata (`course` in `/curriculum/map` and the tree); landing page about the
   problem and the mechanism; "المعلم الذكي" → "المساعد الذكي"; `docs/POSITIONING.md`; `tests/test_positioning.py`.
3. Tree redesign: two-tone leaves, progress fill, buds, "أنت هنا", diagnosed-root trace along the branches, upright trunk with root
   flare, light/dark; sign-in lands on the tree; light/dark switch on the sign-in page.

## Final repository search (case-sensitive `grep -rI`, release tree, counts exclude this file)
| Term | Hits / files | Where |
|---|---|---|
| `teacher` | 61 / 23 | tests (negative assertions), README/HANDOFF/POSITIONING/FINANCIAL_MODEL statements, preflight check, comments, `finance` "no teacher pricing", avatar outfit |
| `Teacher` | 1 / 1 | preflight ("Not A Teacher" refused signup) |
| `school` | 45 / 21 | same classes as above, plus `test_logic` (school plan → error), `test_tutor_eval` (`school.org` e-mail), migration verification fixture |
| `School` | 1 / 1 | legacy-table fixture in `verify_migrations_sql.sh` |
| `classroom` | 20 / 8 | README/HANDOFF/POSITIONING negations, preflight + tests asserting `/classrooms` → 404 |
| `Classroom` | 0 / 0 | - |
| `صفوفي` | 5 / 4 | 4 test files asserting it is absent from the UI |
| `org_admin` | 6 / 6 | tests asserting `org_admin` signup → 422 / no such role in the SPA |
| `teacher@demo.jo` | 1 / 1 | `test_positioning.py` asserts it is **not** a demo account |
| `6.99`, `69.90`, `2.99`, `29.90` | 1 each / 1 | `tests/js/smoke.mjs` asserts none of the old prices are rendered |

No occurrence in `app/static` (the whole public frontend), in the routers other than the moderation docstring, or in any
user-facing string. Arabic "الصف/الصفر" hits are the course metadata (`COURSE`) or the word "zero".

## Remaining references to "teacher"/"school"/"classroom" (all intentional)
| Where | Why it stays |
|---|---|
| Tests (`test_b2c_model.py`, `test_authz_matrix.py`, `test_api_contracts.py`, `test_features.py`, `test_logic.py`, `test_positioning.py`, `test_api.py`, `tests/js/*`) | Negative assertions: teacher/school signup → 422, school plan → 422, classroom API → 404, no teacher UI. |
| `scripts/preflight.py` | Live check that teacher signup is refused and the classroom API does not exist. |
| `app/schemas/auth.py`, `app/routers/moderation.py`, `app/models/org.py`, `finance/model.py`, `scripts/seed_demo.py` | Comments/docstrings stating that there is no teacher/school product. |
| `migrations/versions/0004_org_join_code.sql`, `scripts/verify_migrations_sql.sh` | Retired migration (no-op) and its verification that legacy tables are left untouched. |
| `app/engine/avatar_items.py` (`teacher` outfit, "معلم/ة") | A cosmetic avatar outfit among other professions (engineer, doctor…), not a role or product. |
| `app/services/rag/guardrail.py` ("معلم", "مدرسه", "صف") | Keywords a student may type; they mark a message as study-related for the tutor guardrail. |
| `scripts/pilot_summary.py` ("صفوف") | Arabic for spreadsheet *rows* in the CSV, not classes. |
| `tests/test_tutor_eval.py` ("school.org") | An e-mail address used to test the contact-detail filter. |
| README / HANDOFF / POSITIONING / FINANCIAL_MODEL | Explicit statements that no teacher/school product exists. |
