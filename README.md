# جذور | Juthoor

**A general learning platform that finds where the gap started.**

Adaptive learning + prerequisite-gap detection + evidence-first root diagnosis + targeted remediation + mastery.
Juthoor is not a mathematics, Grade 6, school or teacher product: it is a B2C product (student = user, parent = buyer)
whose current demo content happens to be Grade 6 mathematics. There is no teacher or school product, no classroom
feature and no teacher/school pricing anywhere in the code base. Plans: Free 0 JOD, Pro Monthly 4.50 JOD,
Pro Academic Year 32 JOD. See `docs/POSITIONING.md`.

When a learner struggles with a lesson, Juthoor gathers evidence across the prerequisite graph,
probes earlier skills, and names the *most likely* underlying gap — with the evidence, an honest
confidence level, and a targeted remediation. The learner remediates, retries the original lesson,
mastery is updated, and the parent sees where the gap started and what happens next.

> منصة تعلّم تكيفي تعرف المتطلبات السابقة لكل مهارة: عند تعثّر المتعلم تجمع الأدلة عبر شجرة المتطلبات
> وتقدّر الفجوة الجذرية الأرجح مع الأدلة ومستوى الثقة، ثم تعالجها وتعيده إلى الدرس الأصلي، ويرى ولي الأمر أين بدأت الفجوة وما الخطوة التالية.

The current content pack (demo/seed content only) is **one domain** — integer and fraction lessons from the Jordanian Grade 6
mathematics curriculum (9 live lessons). The UI shows it only as content metadata (`course` in `/curriculum/map` and the tree). The diagnosis core is not tied to mathematics, a grade or a
language (see *Architecture*); course wording lives in `app/engine/config.py` (`COURSE`). Other subjects are not built.

---

## Quick start (PostgreSQL)

Requirements: Python 3.11 or newer, PostgreSQL 14+ running locally, Node 18+ only for the UI tests.

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python scripts/check_env.py --dev   # says exactly which package is missing, if any
cp .env.example .env                # DATABASE_URL=postgresql://postgres:1234@localhost:5432/Juthoor
python run_demo.py --reset          # checks deps + DB, creates "Juthoor" if missing, wipes + seeds, starts the server
```

Database steps that `run_demo.py --reset` performs (each can be run on its own):
`scripts/check_db.py` (connect; create the database if missing) → `scripts/reset_db.py` (drop/recreate
the `public` schema) → `scripts/init_db.py` (create tables, then apply the versioned SQL migrations in `migrations/versions/`) →
`scripts/seed_shop.py` (avatar outfit catalogue: which outfits are free) → `scripts/seed_demo.py` (demo learners, played through the real engine).

Open <http://localhost:8000/app/>. Demo password for every account: `demo1234`.

| Account | Role | Story |
|---|---|---|
| `student2@demo.jo` (عمر) | student, Pro bought by his parent (seeded) | Really mastered absolute value + comparing; now on *multiplying integers*. 5–7 wrong answers lead to the root *adding integers*. Lands on his tree first. |
| `student1@demo.jo` (ليان) | student, Pro bought by her parent (seeded) | Already has a persisted diagnosis — visible in her parent's report. |
| `student3@demo.jo` (مريم) | student on the Free plan | Shows the locked root and the upgrade path. |
| `parent@demo.jo` | parent of ليان and عمر (the buyer) | Child report: root chain, diagnosis record (evidence, confidence, next step, live mastery, outcome), Pro checkout for a child. |
| `student4..6@demo.jo` | students | Community demo (friends, messages, one safety report). |

- `run_demo.py` uses `DATABASE_URL` from the environment or `.env`; if neither is set it uses
  `postgresql://postgres:1234@localhost:5432/Juthoor`. It **never** falls back to SQLite silently;
  `--sqlite` exists only as an explicit offline backup and prints a warning.
- `--reset` drops and recreates the `public` schema of that database, then reseeds. Run it before
  every demo so Omar starts clean. Without `--reset`, existing databases are upgraded additively
  (`app/database.py: ensure_schema`).
- Judge mode is on by default (learning workflow + Pro in the menu, no rate limits).
  `--full` also shows the community.
- **Parent accounts need a Child ID.** A parent/guardian account is created only together with the link to a
  learner: the learner sees their Child ID in the account menu (top right, «رمز الطالب لولي الأمر», e.g.
  `4821-K7Q2M9XD`), and the parent enters it on the sign-up form. The server refuses a missing, malformed,
  unknown or already-claimed Child ID and writes nothing (`app/services/child_link.py`). A second child can still
  link to an existing parent by entering the parent's e-mail when the child signs up.
- There are no coins, gems, wallet or avatar shop. The legacy tables are kept (nothing is dropped) but unused.
- `GET /health` reports `database: ok|unavailable` and the dialect.

## The core workflow

```
Learner answers a question on skill S
  └─ wrong → BKT update, practice plan starts (same idea again → easier → prerequisite)
       └─ every wrong answer returns evidence_status = insufficient_evidence + why + evidence_needed (what would settle it)
            └─ the leading candidate has only one wrong probe → one confirmation probe on it
                 └─ verdict: root_identified — root, path, evidence per skill, confidence level,
                    explanation, intervention; DiagnosisEvent persisted
                      └─ the learner sees «ظهر جذر المشكلة» → diagnosis card (problem, root, why, confidence,
                         current mastery, next step, competing candidate), always read from the backend
                      └─ remediation on the root (difficulty 1 → 3, mastery threshold 0.85); the round is not
                         closed while the root's p_mastery is above 0.95 but not yet confirmed (bounded, see below)
                           └─ return_up: the learner retries the original lesson
                                └─ parent report: diagnosis record + outcome
                                   (answers on the root after diagnosis, retry on the original lesson, resolved?)
```

The practice page shows this loop as a six-step stepper (**مسار التشخيص**: practising → gathering
evidence → likely root → targeted remediation → retry → mastery updated). The stage is computed on the
server (`app/services/workflow.py`) from the live learner state and the latest persisted diagnosis and is
returned as `workflow` by `POST …/adaptive/answer` and `GET …/adaptive/state`.

**Root found (learner).** When the backend names a root (`diagnosis` in the answer, i.e. status
`root_identified`) the practice page shows a large «ظهر جذر المشكلة» button; while the workflow stage is
`root_identified`, `remediation` or `retry` it stays in the stepper card. Opening it reads
`GET …/adaptive/diagnoses` and shows: the current problem (origin lesson), the root, why (the engine's explanation
and the evidence counts), the confidence level (مرتفعة/متوسطة/أولية = High/Medium/Low), the **current** BKT mastery
of the root (`outcome.root_mastery`, the engine's own `p_mastery`), what happens now, and any competing candidate.
Nothing is shown for insufficient evidence, and the UI never computes a diagnosis itself.

**Live record.** `engine_bridge.diagnosis_history` keeps what the engine decided (origin, root, confidence,
evidence, competing candidates) and recomputes everything about *now* on every request: `root_mastery`,
`origin_mastery`, `root_status`, `origin_status`, answers on the root and on the original lesson since the
diagnosis. The parent report shows the same live line and re-reads it when the tab becomes visible again.

**Round pacing during remediation.** A round normally ends after `SESSION_LENGTH` (5) answers. If the learner is
remediating a named root whose `p_mastery` is already above `REMEDIATION_CONTINUE_P` (0.95) but mastery is not yet
confirmed (that still needs a correct answer at the top difficulty with p ≥ 0.85), the round stays open and the
next (harder) question is served instead of «أنهيت الجولة». The exit is the engine's own: mastery confirmed, a wrong
answer that drops p to 0.95 or below, a park, or a cap of `ROUND_EXTENSION` = 3 extra answers
(`app/engine/adaptive_engine.py: round_over`). BKT parameters, thresholds and the diagnosis are unchanged; the
synthetic benchmark is identical (it stops at the first diagnosis).

### Diagnosis rules (`app/engine/diagnosis.py`)

1. **failing(s)**: not currently believed mastered, and more wrong than right answers on `s`.
2. **solid(s)**: believed mastered, or no wrong answer and at least `MIN_SOLID_EVIDENCE` (2) correct answers
   on `s`. One lucky correct answer is *not* enough. Otherwise *unverified*.
   A mastered skill stops being "believed" only when fresh errors drop its BKT estimate below 0.5
   (two wrong answers in a row from 0.85); old history alone never re-opens it.
3. Candidates = failing skills on `origin + all prerequisites (ancestors)`.
4. A candidate is eligible only if **every direct prerequisite is solid** (a failing prerequisite is a
   deeper explanation; an unverified one cannot be ruled out).
5. Among eligible candidates, the strongest direct evidence wins (most wrong, then error rate), then
   the more fundamental skill. Other eligible candidates are reported as `competing`.
6. **No root is named** unless the chain shows ≥ 3 wrong answers, the root itself ≥ 2, *and* the leading
   candidate's likelihood ratio against "no gap" is at least `MIN_ROOT_LR` (20; computed in log space from the
   candidate's right/wrong counts with `p_gap=0.2`, `p_known=0.9`). These two thresholds are uncalibrated
   defaults; `benchmarks/sweep.json` shows how stricter values trade false diagnoses for abstention.
   Otherwise the verdict is `insufficient_evidence` with the reason (`too_few_errors`,
   `root_needs_confirmation`, `prerequisites_unverified`, or `mixed_evidence` when errors were seen but
   every skill still has at least as many right answers as wrong). Each insufficient verdict also returns
   `evidence_needed`: machine-readable items (`more_errors`, `confirm_root`, `verify_prerequisite`,
   `resolve_mixed`, each with a skill and the minimum number of answers) that the practice page shows as
   "ما يلزم لحسم التشخيص". `no_difficulty` means no unmastered
   skill on the chain has a wrong answer.
7. The engine checks the evidence first on every wrong answer: as soon as the verdict names a new root
   it is declared on that answer (the evidence status and the decision never disagree).

**Origin and path.** The diagnosis is computed from the lesson where the visible difficulty started
(the bottom of the engine's return stack, `adaptive_engine.investigation_origin`), so the reported path
follows real prerequisite edges from that lesson down to the root, e.g. multiplying → subtracting →
adding → comparing → absolute value. Errors on every lesson of that chain count as cross-skill evidence.

**Confidence is an ordinal level, not a probability:**

| Level | Rule |
|---|---|
| high (مرتفعة) | ≥ 3 wrong on the root, ≥ 75 % of its answers wrong, every direct prerequisite *observed* correct |
| medium (متوسطة) | ≥ 2 wrong on the root and more wrong than right (also the cap when a competing candidate exists) |
| low (أولية) | weaker evidence (not reachable with the default thresholds) |

BKT probabilities are clamped to [0.001, 0.999] (never absorbing, NaN-safe) and the parameters are validated at import.
`p_gap` in the payload is `1 − BKT p(mastery)`. The BKT parameters (`app/engine/config.py`) are
literature-style defaults; **they have not been calibrated on real learner data**, so `p_gap` is a model
estimate, not a measured probability. In the Omar demo the root is named with *medium* confidence
because the root has two wrong answers.

### AI is optional

The diagnosis, question generation (140 deterministic templates), and grading never call an AI
service. An LLM (OpenAI/Groq) is used only if a key is set, for tutor replies and optional question
wording; every call has a timeout and falls back to the offline generator / offline tutor. Tested
with a provider that always throws (`test_g_…`).

### Measured behaviour (synthetic benchmark only)

`python scripts/diagnostic_benchmark.py --reps 5` drives synthetic learners with a known gap through the real
engine (810 cases, deterministic). Result for the shipped thresholds: with clean answers the engine names the
right root in 97.1 % of the cases where it names one (89.8 % of all gap cases; 2.7 % wrong; 7.6 % abstentions;
no premature declarations). With noisy answers: 91.1 % / 77.8 %. A learner who guesses right often still gets a
wrong root 30.2 % of the time, and learners with no gap get a false diagnosis in 2.2 / 8.9 / 20.0 % of clean /
noisy / very noisy cases. The 95 % goal was **not** reached, and these figures say nothing about real students.
Details and before/after: `docs/COMPETITIVE_ADVANTAGE.md`.

## Concurrency, idempotency and migrations

- Every answer locks the learner's state row (`SELECT … FOR UPDATE`); the state row is created with
  `INSERT … ON CONFLICT DO NOTHING`; `skill_mastery` has a unique (student, skill) constraint and CHECK constraints.
- `POST /adaptive/answer` accepts an optional `request_id` (8–64 chars). A retry with the same id returns the stored
  response (`idempotent_replay: true`); the same id with a different answer is `409 request_id_reused`. The UI sends one.
- Migrations: `migrations/versions/NNNN_*.sql`, applied in order under an advisory lock and recorded in
  `schema_migrations` (`app/migrations.py`). They are idempotent, so a fresh database and an older one converge.
  Alembic is not used.
- A learner's state row is created exactly once: the answer/question path creates and locks it; opening one's own
  state provisions it (`provision_state`); every other read (parent, integrity checker) is read-only.
- Connections: one per request, always returned by `get_db`. Pool sizes: `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` /
  `DB_POOL_TIMEOUT` (defaults 10 / 20 / 30). The test suite uses the same options.
- `scripts/check_integrity.py` checks a live database for orphans, duplicates and out-of-range values.
- `scripts/verify_{migrations,locking,integrity,state_creation}_sql.sh` verify the SQL against a PostgreSQL server using psql/pgbench.

## Architecture

- `app/static/` – single-page app, vanilla ES modules, no build step, served at `/app/`.
- `app/main.py`, `app/routers/` – FastAPI; JWT bearer auth; role checks in `app/deps.py`. Roles: `student`,
  `parent` (self-registration) and `platform_admin` (internal moderation account; not self-registrable, no product screen).
- `app/routers/moderation.py` – internal review of community safety reports (child safety); no teacher or school reviewer.
- `app/services/engine_bridge.py` – loads/saves learner state, persists attempts, drill-downs and
  diagnoses, builds the diagnosis history with outcomes shown in the parent report.
- `app/services/session_core.py` – one question/answer step: practice plan, confirmation probes, evidence status.
- `app/engine/diagnosis.py` – **domain-agnostic**: graph validation (unknown prerequisite, self-loop,
  duplicate, cycle), traversal, candidate ranking, confidence. No curriculum or language inside.
- `app/engine/knowledge_graph.py` – the example content graph (9 integer skills); validated at import.
- `app/engine/benchmark.py` – synthetic-learner benchmark; `app/engine/integrity.py` – learner-state invariants.
- `finance/model.py` – B2C financial model (see `docs/FINANCIAL_MODEL.md`).
- `app/engine/adaptive_engine.py` – BKT, difficulty ladder, backtracking, remediation routing, Arabic explanations.
- `app/models/` – SQLAlchemy models. PostgreSQL schema is created by `scripts/init_db.py` / app start-up.
- `docs/ARCHITECTURE.png` – diagram.

Adding a subject means supplying another prerequisite mapping + question bank; the diagnosis module is
already exercised with a reading-literacy graph in `tests/test_diagnosis_engine.py`.

## Testing

```bash
python -m pytest -q             # PostgreSQL: postgresql://postgres:1234@localhost:5432/juthoor_test
cd tests/js && npm test         # UI tests on a fake DOM, replaying real engine payloads
python scripts/preflight.py     # live checks against the running server (start run_demo.py first)
python scripts/make_test_report.py   # writes docs/TEST_REPORT.md from an actual run
python -m compileall -q app scripts tests finance
python scripts/diagnostic_benchmark.py --reps 5   # synthetic diagnosis benchmark (deterministic)
python scripts/benchmark_sweep.py                 # threshold trade-off table
python finance/model.py                           # financial scenarios -> finance/outputs.json

# Real-browser walk-through (Chromium via Playwright; run while run_demo.py is serving):
pip install playwright && python -m playwright install chromium
python tests/e2e/browser_e2e.py      # then run_demo.py --reset again: it changes Omar's state
```

Which of these have actually been run, and where, is recorded in `HANDOFF.md` ("Verification status") and
`docs/FINAL_B2C_AUDIT.md`. Several test files need no web framework or database and run with
`python -m pytest -q --noconftest <file>` (engine, flow, BKT properties, graph integrity, benchmark, stability-engine,
tutor evaluation, financial model, migration-file validation).

How the suite is configured (`tests/conftest.py`), so that a clean checkout behaves the same everywhere:

- It never reads your `.env` for application settings (`JUTHOOR_ENV_FILE=` is set empty) and pins every
  behaviour switch to a valid value (`DEMO_MODE=0`, `JUDGE_MODE=0`, `RATE_LIMIT_ENABLED=0`, …).
  Settings also treat a blank value such as `DEMO_MODE=` as "use the default" instead of failing.
- Database: `TEST_DATABASE_URL` (environment or `.env`) if set; otherwise the server and credentials of
  `DATABASE_URL` with the database name `juthoor_test`. The test database is created if missing, its
  schema is rebuilt once per run and every table is truncated after each test. It refuses to run against
  the application database. If PostgreSQL is unreachable, pytest stops with a clear message — there is no
  silent SQLite fallback (SQLite is used only if you explicitly set `TEST_DATABASE_URL=sqlite://`).
- If a package is missing, pytest stops before collecting and prints the exact `pip install` command.

Scenario matrix (wrong answers in these tests are misconception-linked answers from the question bank,
e.g. *28* for *−4 × 7* = "ignored the sign rule", never nonsense strings):

| | Scenario | Test |
|---|---|---|
| A | normal success | `test_core_workflow.py::test_a_…` |
| B | one wrong answer updates evidence + names the misconception, no diagnosis | `test_core_workflow.py::test_b_…` |
| C/D | repeated difficulty → evidence gathering → prerequisite probes | `test_core_workflow.py::test_bcd_…`, `test_diagnosis_flow.py` |
| E | strong evidence → supported root with confidence + explanation | `test_bcd_…`, `test_diagnosis_engine.py` |
| F | competing candidates on a branching graph | `test_diagnosis_engine.py::test_two_failing_branches_…` |
| G | insufficient evidence (too few errors / needs confirmation / prerequisite unverified) | `test_diagnosis_engine.py`, `test_b_…` |
| H | targeted remediation assigned on the root | `test_bcd_…` (next question), `test_features.py::test_a_named_gap_reaches_…` |
| I | remediation success → retry of the original lesson → mastery → outcome in the parent report | `test_core_workflow.py::test_e_…` |
| J | remediation failure: gap kept, no duplicate diagnosis | `test_core_workflow.py::test_f_…` |
| K | persistence across a simulated restart, then the retry continues | `test_core_workflow.py::test_persistence_…` |
| L | the parent sees diagnosis, evidence, intervention, outcome; others cannot | `test_core_workflow.py::test_i_…` |
| M | invalid input (empty, too long, missing, null, garbage, replay, refresh) | `test_core_workflow.py::test_k_…`, `test_j_…`, `test_api.py` |
| N | missing learner; stale state with an unknown skill is repaired | `test_core_workflow.py::test_n_…` |
| O/P | unknown prerequisite, self-loop, duplicate, cycle, unknown origin; linear and diamond graphs | `test_diagnosis_engine.py` |
| Q | AI provider failing (questions, diagnosis, tutor) | `test_core_workflow.py::test_g_…`, `test_q_…` |
| R | database outage → 503; failure mid-answer rolls back cleanly | `test_core_workflow.py::test_k_database_…`, `test_r_…` |
| S | repeated execution (same history → same root; random learners keep invariants) | `test_j_…`, `test_diagnosis_engine.py` |
| – | configuration (blank values, booleans, no `.env` leak) | `test_config.py` |
| – | question-bank integrity (`BANK_SAMPLES=20000` for the long run) | `test_bank_integrity.py` |
| V | ownership/authorization: other students' data, parent ↔ own child only, avatar, payments; forged and expired tokens | `test_authz_matrix.py`, `test_economy_payments.py`, `test_core_workflow.py::test_i_…`, `test_api.py` |
| – | parent signup: Child ID required, unknown/malformed/claimed/inactive refused with no row written, valid one links parent and child; student signup and parent login unchanged | `test_parent_signup.py` |
| – | live diagnosis record (current mastery, statuses, competing candidates) for the learner card and the parent report | `test_diagnosis_live.py` |
| – | round pacing during remediation (>95 % keeps asking, bounded, completion still ends the round) | `test_remediation_round.py` |
| – | report contrast in light and dark mode (tokens, no forced colours, AA pairs, print stays light) | `test_dark_mode_contrast.py`, `tests/e2e/browser_e2e.py` |
| – | B2C model: only student/parent accounts, no teacher/school signup or classroom API, Free 0 / Pro 4.50 / Pro 32, only students and parents can buy, server-side amounts, no mock fallback | `test_b2c_model.py`, `test_features.py` |
| – | positioning: no subject/grade hard-coded in the shell, course metadata from the content pack | `test_positioning.py` |
| W | payments: session ownership, bad cards, double confirm, renewal extends the period, UTC `…Z` timestamps | `test_economy_payments.py`, `test_features.py` |
| X | no coins/gems/wallet/shop (API gone, nothing written, nothing shown); wearing a formerly paid outfit needs prior ownership | `test_no_economy.py`, `test_economy_payments.py`, `test_api.py`, `test_features.py` |
| – | UI: evidence → root → remediation → retry → resolved, from real engine payloads | `tests/js/smoke.mjs` |
| – | real browser: login → tree → wrong answers → diagnosis card → «ظهر جذر المشكلة» card → outage message → remediation (live mastery rises) → retry → refresh → parent report record → contrast in light/dark → PostgreSQL check | `tests/e2e/browser_e2e.py` |

## Field validation (lightweight)

- `docs/PILOT.md` – a small B2C validation round with families (consenting parents and their children):
  pre/post check and parent interviews. `scripts/pilot_summary.py` summarises the pre/post numbers.
- **Blind expert review:** before seeing Juthoor's result, an independent subject expert writes the gap they believe
  each learner has into `docs/expert_agreement_template.csv`; then Juthoor's root is copied in and
  `python scripts/agreement_summary.py docs/expert_agreement_template.csv` reports raw agreement.
  That is an early agreement signal on a small sample — not diagnostic accuracy. Experts are reviewers, not customers.

No pilot or agreement data has been collected yet. The repository makes no accuracy, learning-gain
or efficacy claims.

## Configuration

One source of truth: `app/config.py`. Precedence: environment variables > `.env` at the repository root
(found regardless of the working directory) > defaults. Copy `.env.example` to `.env`.
Key variables: `DATABASE_URL`, `TEST_DATABASE_URL`, `JWT_SECRET` (the server refuses a weak secret unless
`DEMO_MODE=1`; `run_demo.py` uses a random per-run secret while `.env` still holds the placeholder),
`DEMO_MODE`, `JUDGE_MODE`, `RATE_LIMIT_ENABLED`, and optional `OPENAI_API_KEY`/`GROQ_API_KEY`,
`STRIPE_SECRET_KEY`, `SMTP_*`. Booleans accept `0/1/true/false`; a blank value means the default.

Timestamps are stored as naive UTC and always leave the API as ISO-8601 UTC with a trailing `Z`
(`app/schemas/common.py`), so browsers do not misread them as local time.

Dependencies: `requirements.txt` is the core runtime (FastAPI, SQLAlchemy, psycopg2, pydantic-settings,
PyJWT, bcrypt, networkx, …) with version ranges that have wheels for current Python versions.
`requirements-optional.txt` holds the LLM, Stripe and vector-store SDKs — the core workflow never needs them.

## Known limitations

- One demonstrated domain: 9 of 18 lessons of the curriculum map are live (units 1–2). The 95 % diagnosis goal is not met
  on the synthetic benchmark (see above); there are no field results.
- The prerequisite edges, including the integers → fractions edge, are a pedagogical assumption not yet
  reviewed by independent subject experts.
- BKT parameters and the evidence thresholds are uncalibrated defaults; the confidence level is a
  documented rule, not a validated probability.
- The current graph is a chain; branching and competing roots are supported and tested on a synthetic
  graph, not yet on curriculum content.
- Rate limiting is in-process memory (single worker). Concurrency was verified at the SQL level (pgbench) and by
  engine-level tests; an HTTP load test has not been run.
- Password-reset codes are not e-mailed unless SMTP is wired up; outside demo mode they are not logged.
- The off-topic guardrail for the tutor is keyword-based.
- No field pilot has been run yet.
- Community (friends, messages, safety reports) is a student feature hidden in judge mode; the avatar keeps the
  look chosen at sign-up (the outfit editor was part of the removed shop). Esports challenges exist in the API only
  and award nothing. Payments run through Stripe when a key is configured; otherwise only
  the clearly labelled demo checkout is available (demo mode), which never charges anyone.
- The Child ID is derived from `JWT_SECRET`; rotating the secret changes every Child ID (existing links are kept).
- Databases created by earlier versions keep their old, now unused tables (organizations, classrooms, wallets, …):
  nothing is dropped automatically. `python run_demo.py --reset` rebuilds a clean schema.
