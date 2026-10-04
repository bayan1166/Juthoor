<<<<<<< HEAD
# جذور | Juthoor

**A general learning platform that finds where the gap started.**
=======
# Juthoor | جذور
>>>>>>> f32b62e70c21a476ee538f9065465fa6cdd48ad3

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

<<<<<<< HEAD
The current content pack (demo/seed content only) is **one domain** — integer and fraction lessons from the Jordanian Grade 6
mathematics curriculum (9 live lessons). The UI shows it only as content metadata (`course` in `/curriculum/map` and the tree). The diagnosis core is not tied to mathematics, a grade or a
language (see *Architecture*); course wording lives in `app/engine/config.py` (`COURSE`). Other subjects are not built.

---

## Quick start (PostgreSQL)

Requirements: Python 3.11 or newer, PostgreSQL 14+ running locally, Node 18+ only for the UI tests.
=======
* Adaptive questioning
* Prerequisite-aware learning
* Evidence-first root-gap diagnosis
* Targeted remediation
* Mastery tracking
* Explainable feedback
* Optional AI tutoring

**Student = user. Parent/guardian = buyer.**

Juthoor is **not a school product, teacher product, classroom platform, or school management system**. The current demo content happens to be Grade 6 mathematics, but the product architecture and diagnosis engine are designed to be domain-agnostic.

---

# Team

## Juthoor — جذور

Built by:

* **Bayan Marashdeh**
* **Marah Al-Kilani**
* **Sadeen Nababteh**
* **Rana Shalout**

---

# What problem does Juthoor solve?

A learner can get a question wrong for many different reasons.

The visible mistake may happen in one lesson while the actual learning gap started several prerequisite skills earlier.

Traditional learning systems often stop at:

> "You got this question wrong."

Juthoor asks a different question:

> **"Where did the difficulty most likely start?"**

When a learner struggles, Juthoor:

1. Detects the current difficulty.
2. Uses the prerequisite graph to investigate earlier skills.
3. Collects evidence instead of immediately assigning a diagnosis.
4. Avoids naming a root when the evidence is insufficient.
5. Identifies the most supported root gap when the evidence becomes strong enough.
6. Shows the evidence and confidence behind the diagnosis.
7. Routes the learner to targeted remediation.
8. Returns the learner to the original lesson.
9. Updates mastery based on the new evidence.
10. Makes the learning history visible to the parent.

---

# Core workflow

```text
Learner answers a question
        │
        ├── Correct
        │     └── mastery update → adaptive progression
        │
        └── Wrong
              │
              ├── BKT mastery update
              ├── collect evidence
              ├── inspect prerequisites
              └── test deeper skills when needed
                       │
                       ├── Evidence insufficient
                       │      └── gather more evidence
                       │
                       └── Root identified
                              │
                              ├── explain root + evidence
                              ├── confidence level
                              ├── targeted remediation
                              └── return to original lesson
```

The product is deliberately **evidence-first**.

A weak signal does not automatically become a diagnosis.

---

# Diagnostic engine

The diagnostic core is implemented in:

```text
app/engine/diagnosis.py
```

It is domain-agnostic and operates on:

```text
Prerequisite graph
+
Per-skill evidence
+
Mastery state
```

The engine supports:

* Failing-skill detection
* Prerequisite validation
* Root-candidate ranking
* Insufficient-evidence states
* Confirmation probes
* Competing candidates
* Likelihood-ratio evidence
* Confidence levels
* Machine-readable evidence requirements
* Explainable diagnosis output

## Diagnostic states

```text
root_identified
insufficient_evidence
no_difficulty
unknown_skill
```

When evidence is insufficient, the system explains **why** and can return:

```text
more_errors
confirm_root
verify_prerequisite
resolve_mixed
```

instead of forcing a diagnosis.

---

# BKT / Mastery

Juthoor uses Bayesian Knowledge Tracing-style mastery updates.

Current parameters:

```text
p_init  = 0.30
p_slip  = 0.10
p_guess = 0.20
p_learn = 0.20
```

Mastery is kept inside a safe numerical range:

```text
0.001 ≤ mastery ≤ 0.999
```

The implementation protects against:

* NaN
* infinity
* invalid probabilities
* impossible persisted counts
* corrupted mastery state

The current parameters are **uncalibrated defaults**, not claims of validated real-world learner accuracy.

---

# Knowledge graph

The current demo content uses a prerequisite graph connecting 9 live skills.

Example:

```text
Absolute Value
      ↓
Comparing Integers
      ↓
Adding Integers
      ↓
Subtracting Integers
      ↓
Multiplying & Dividing Integers
      ↓
Adding & Subtracting Fractions
      ↓
Mixed Numbers
      ↓
Multiplication
      ↓
Division
```

The graph is validated against:

* Unknown prerequisites
* Self-loops
* Duplicate prerequisites
* Cycles

The diagnosis module itself does **not** depend on mathematics.

A different subject can provide another prerequisite mapping and question bank.

---

# Current demo content

The shipped demo currently contains:

**9 live lessons from a Grade 6 mathematics content pack based on the Jordanian curriculum.**

This is **demo content**, not the product's scope.

The content is intentionally separated from the diagnostic core.

Course metadata lives in:

```text
app/engine/config.py
```

while the diagnosis engine operates independently of subject and grade.

The current MVP and available evidence are focused on Grade 6 mathematics. Other subjects and grades are planned validation areas rather than existing validated evidence.

---

# AI is optional

The core learning workflow does **not** require an LLM.

AI is optional and can be used for:

* Tutor responses
* Optional question wording

The core system still works through deterministic/offline components for:

* Diagnosis
* Adaptive decisions
* Question generation
* Grading
* Mastery updates

External AI failures are handled through controlled fallback behavior.

Supported providers currently include:

```text
OpenAI
Groq
```

AI is optional and does not determine the core diagnosis.

---

# B2C pricing

Juthoor uses a simple consumer pricing model:

| Plan              |            Price |
| ----------------- | ---------------: |
| Free              |            0 JOD |
| Pro Monthly       | 4.50 JOD / month |
| Pro Academic Year |    32 JOD / year |

The learner can use the product directly.

A parent/guardian can purchase Pro for their own child.

There is **no teacher/school subscription model** in the product.

The current prices are **pricing hypotheses to be tested**, not validated willingness-to-pay ceilings. The 32 JOD academic-year price is currently treated as the minimum price hypothesis for testing.

---

# Product value proposition

For students whose current lesson depends on earlier concepts, and for parents who see a weak result without knowing why, Juthoor is a prerequisite-aware adaptive learning platform that finds the most likely earlier gap behind a student's errors, shows the evidence and confidence label, and guides the student back to that foundation before returning to the current lesson.

Unlike a generic chatbot or content library that mainly answers the question in front of the learner, Juthoor focuses on the prerequisite chain.

A free diagnostic lets a family try it first.

Pro adds:

* Full root-chain diagnosis
* Guided prerequisite path
* Printable parent gap report

Current test prices:

* 4.50 JOD/month
* 32 JOD/academic year

---

# Security & data ownership

The application uses:

* JWT bearer authentication
* bcrypt password hashing
* role-based authorization
* student ownership checks
* parent → own-child authorization
* protected payment sessions
* request idempotency
* input validation
* controlled database error handling
* security response headers

The system is designed to prevent:

```text
Unauthorized reads
Unauthorized writes
Cross-student data access
Session ownership violations
Invalid token access
```

The product also treats child data and trust as important launch requirements:

* Parent consent/account
* Minimum necessary data
* Clear privacy notice
* Payment and tax verification before real payments

---

# Architecture

```text
app/
├── engine/
│   ├── adaptive_engine.py
│   ├── diagnosis.py
│   ├── knowledge_graph.py
│   ├── benchmark.py
│   └── integrity.py
│
├── routers/
│   ├── auth.py
│   ├── adaptive.py
│   ├── dashboard.py
│   ├── payment.py
│   ├── chat.py
│   └── moderation.py
│
├── services/
│   ├── engine_bridge.py
│   ├── session_core.py
│   ├── plans.py
│   ├── plan_rules.py
│   ├── curriculum_map.py
│   └── rag/
│
├── models/
├── schemas/
└── static/
```

## Main layers

### Frontend

Single-page application served from:

```text
app/static/
```

### Backend

FastAPI application with:

```text
app/main.py
app/routers/
```

### Adaptive engine

```text
app/engine/adaptive_engine.py
```

### Diagnosis

```text
app/engine/diagnosis.py
```

### Knowledge graph

```text
app/engine/knowledge_graph.py
```

### Persistence

PostgreSQL + SQLAlchemy.

---

# Persistence & reliability

The application includes:

* PostgreSQL support
* Connection pooling
* Row locking for learner state
* Unique mastery constraints
* Database integrity checks
* Transactional updates
* Answer idempotency receipts
* Versioned SQL migrations
* Migration ordering validation

Answer submissions support an optional:

```text
request_id
```

Repeated submissions with the same request ID can safely replay the stored response instead of creating duplicate state changes.

---

# Testing

The project currently includes a large automated test suite covering:

* Authentication
* Authorization
* Adaptive workflow
* Diagnosis
* Mastery/BKT logic
* API contracts
* Payment behavior
* Data isolation
* Knowledge graph integrity
* Persistence
* Stability
* Safety logic
* UI behavior
* Financial model
* B2C positioning

Run the backend tests with:
>>>>>>> f32b62e70c21a476ee538f9065465fa6cdd48ad3

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

<<<<<<< HEAD
No pilot or agreement data has been collected yet. The repository makes no accuracy, learning-gain
or efficacy claims.
=======
### Important
>>>>>>> f32b62e70c21a476ee538f9065465fa6cdd48ad3

## Configuration

<<<<<<< HEAD
One source of truth: `app/config.py`. Precedence: environment variables > `.env` at the repository root
(found regardless of the working directory) > defaults. Copy `.env.example` to `.env`.
Key variables: `DATABASE_URL`, `TEST_DATABASE_URL`, `JWT_SECRET` (the server refuses a weak secret unless
`DEMO_MODE=1`; `run_demo.py` uses a random per-run secret while `.env` still holds the placeholder),
`DEMO_MODE`, `JUDGE_MODE`, `RATE_LIMIT_ENABLED`, and optional `OPENAI_API_KEY`/`GROQ_API_KEY`,
`STRIPE_SECRET_KEY`, `SMTP_*`. Booleans accept `0/1/true/false`; a blank value means the default.
=======
The project currently does **not** claim that the diagnostic engine has achieved a specific real-world diagnostic accuracy percentage.
>>>>>>> f32b62e70c21a476ee538f9065465fa6cdd48ad3

Timestamps are stored as naive UTC and always leave the API as ISO-8601 UTC with a trailing `Z`
(`app/schemas/common.py`), so browsers do not misread them as local time.

Dependencies: `requirements.txt` is the core runtime (FastAPI, SQLAlchemy, psycopg2, pydantic-settings,
PyJWT, bcrypt, networkx, …) with version ranges that have wheels for current Python versions.
`requirements-optional.txt` holds the LLM, Stripe and vector-store SDKs — the core workflow never needs them.

<<<<<<< HEAD
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
=======
The Task 1 evidence also explicitly distinguishes the synthetic benchmark from real-student diagnostic accuracy.

---

# Quick start

## Requirements

```text
Python 3.11+
PostgreSQL 14+
Node 18+ for UI tests
```

## 1. Create a virtual environment

```bash
python -m venv .venv
```

### Windows

```powershell
.venv\Scripts\activate
```

### macOS/Linux

```bash
source .venv/bin/activate
```

## 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

## 3. Configure environment variables

Copy:

```text
.env.example
```

to:

```text
.env
```

Set your local PostgreSQL connection in:

```text
DATABASE_URL
```

## 4. Start the demo

```bash
python run_demo.py --reset
```

## 5. Open Juthoor

```text
http://localhost:8000/app/
```

---

# Demo accounts

The demo database includes student and parent accounts.

Demo password:

```text
demo1234
```

Example accounts:

| Account               | Role    | Demo purpose                             |
| --------------------- | ------- | ---------------------------------------- |
| `student2@demo.jo`    | student | Adaptive diagnosis + remediation journey |
| `student1@demo.jo`    | student | Persisted diagnosis + parent report      |
| `student3@demo.jo`    | student | Free plan + upgrade path                 |
| `parent@demo.jo`      | parent  | Child report + Pro purchase              |
| `student4..6@demo.jo` | student | Community demonstration                  |

---

# Product positioning

Juthoor is positioned as:

> **A general adaptive learning platform that finds where the learning gap started.**

The current mathematics content is only the first demonstrated content pack.

The diagnosis architecture is designed to support additional domains without rewriting the core diagnostic logic.

---

# Market & business model

## Target customer

### User

Students in Grades 5–7.

The initial MVP focus is Grade 6 mathematics.

### Economic buyer

Parent/guardian.

### Distribution and validation

Teachers and schools can recommend Juthoor or review diagnoses, but they are not paying customers in the current B2C model.

---

# Competitive context

Relevant alternatives include:

* Private tutoring
* Curriculum/content platforms
* Video/content libraries
* General-purpose chatbots

Juthoor's intended distinction is not "more content".

It is:

* Evidence-first prerequisite diagnosis
* A targeted return path
* A parent-facing gap report

Juthoor starts from the learner's gap rather than only the current topic.

The diagnosis system can also abstain when evidence is insufficient rather than forcing an answer.

---

# Market funnel

The current market model uses a planning funnel:

```text
Total school students
        ↓
Grades 4–9
        ↓
Digitally reachable
        ↓
Serviceable families
```

Current planning estimates:

| Stage                         |   Estimate |
| ----------------------------- | ---------: |
| Total school students 2023/24 |  2,307,110 |
| Excluding kindergarten        |  2,143,249 |
| Grades 4–9                    | ≈1,070,000 |
| Digitally reachable           |   ≈750,000 |
| Serviceable families          |   ≈225,000 |

These are **planning assumptions, not measured TAM/SAM/SOM**.

The model must be replaced with observed acquisition and payment data after the 90-day test.

---

# Unit economics

The following variables are treated as assumptions until measured:

* Free-to-paid conversion
* Retention/churn
* CAC
* Referral share
* Annual-plan choice

Validation requires real user data.

The project should not scale hiring or paid acquisition based on projections alone.

---

# Lean company cost model

Stage 1 is intentionally lean.

Current planning assumptions include:

| Cost category                         | Stage 1 monthly JOD |
| ------------------------------------- | ------------------: |
| Engineers                             |                   0 |
| Product/operations                    |                   0 |
| Education/content                     |                   0 |
| Support                               |                   0 |
| Growth/marketing staff                |                   0 |
| Employer social security              |                   0 |
| Office/coworking                      |                   0 |
| Hosting/DB/monitoring/email/analytics |                 130 |
| Software                              |                  60 |
| Accounting                            |                  40 |
| Legal                                 |                  40 |
| Licences/insurance                    |                   0 |
| Fixed marketing/tests                 |                 300 |
| Contingency                           |                  57 |
| **Total**                             |            **≈630** |

These are planning assumptions, not quotations.

Payment fees, refunds, per-user infrastructure, paid ads and tax must be confirmed before launch.

---

# Three-year reality check

Current planning scenarios:

| Scenario             | Year-3 paying students |
| -------------------- | ---------------------: |
| Conservative         |                   ≈800 |
| Base                 |                 ≈4,100 |
| Growth / stress test |                ≈15,700 |

These are scenario outputs rather than forecasts.

The key variables remain:

* Conversion
* Retention
* CAC
* Organic/referral acquisition
* Revenue per family

At the current 32 JOD price, scale alone does not solve the economics.

---

# Break-even logic

Current planning references:

```text
≈2,400 paying students/year
```

to cover the Stage 2 annual cost base.

```text
≈8,200 paying students/year
```

to cover the Stage 3 annual cost base.

These are planning outputs, not forecasts, and are before acquisition effects.

---

# Validation evidence

The current opportunity validation found:

* 21/34 students often or always cited forgotten basics.
* 30/34 could not pinpoint the old gap alone.
* 33/34 rated a step-by-step return as important.

However, these results are from a convenience sample and represent student perceptions, not parent purchase evidence.

The six anonymised cases produced:

* 1 exact match
* 5 partial matches
* 0 recorded disagreements against one educator's recorded root

This is an early signal, not a validated diagnostic-accuracy study.

---

# What we learned and changed

### Students report difficulty locating earlier gaps

Decision:

> Keep root-gap diagnosis at the center.

### Six selected cases show topic-level alignment but only one exact match

Decision:

> Keep evidence-first diagnosis and expand independent validation.

### No school/teacher commitment and no parent purchase data

Decision:

> Use B2C: parent pays, student uses.

### Wrong diagnosis can destroy trust

Decision:

> Require sufficient evidence; otherwise return "insufficient evidence"; show ordinal confidence rather than fake probability.

These decisions are part of the current product positioning and validation strategy.

---

# Go-to-market

## Who we reach first

### Students

Grades 5–7 in Amman studying mathematics.

Start with Grade 6 because the MVP content exists there.

### Buyer

Parent/guardian.

### Hook

```text
Free diagnostic
→ root-gap report
→ targeted remediation
→ retry
```

### Not first

* Public-school rollout
* Unbuilt grades
* Unbuilt subjects
* Paid teacher product
* Paid school product

---

# Acquisition channels

| Channel                | Action                                                              | Evidence status                  |
| ---------------------- | ------------------------------------------------------------------- | -------------------------------- |
| Free diagnostic        | Primary entry point + shareable parent gap card                     | Not yet tested                   |
| Student social content | Arabic short videos, hidden-gap concept, streaks, friend challenges | 24/34 selected friend challenges |
| Parent communities     | Arabic posts + diagnostic CTA                                       | Not tested with parents          |
| Referral               | Completed diagnosis + friend invite + one-week Pro reward           | Not tested                       |
| Ambassadors            | Small peer cohort                                                   | Not tested                       |
| Paid digital           | Small capped parent-targeted tests                                  | Conversion unknown               |
| Teacher distribution   | Share diagnostic + blind-review diagnoses                           | Distribution + validation        |

Paid advertising is a **test**, not the business model.

---

# First 30 days — experiments

| Experiment | Metric                        | Target / interpretation              |
| ---------- | ----------------------------- | ------------------------------------ |
| E1         | Visitor → registration        | ≥25% hypothesis                      |
| E2         | Diagnostic start → completion | ≥40% hypothesis                      |
| E3         | Parent interviews             | 15 parents; ≥5/15 say they would pay |
| E4         | Refundable pre-order          | ≥3%; annual ≥40%                     |
| E5         | Referral                      | ≥20%                                 |
| E6         | Cost / registered user        | ≤1.80 JOD                            |

A 300 JOD test budget at an indicative 0.30–0.70 JOD CPC buys roughly 430–1,000 visits.

Early results should therefore be reported as counts and funnel rates, not as proof of product-market fit.

---

# Days 31–90

The second phase measures:

* Free-to-paid conversion
* Monthly retention
* Annual share
* CAC/payer
* Teacher distribution
* Independent root agreement
* Diagnosis usefulness
* Parent willingness-to-pay

Target hypotheses:

```text
Free-to-paid ≥3.5%
Retention ≥88%
Annual share ≥40%
CAC/payer ≤18 JOD
```

A 100-parent WTP survey should include the current test prices:

```text
4.50 JOD/month
32 JOD/year
```

These are validation targets and hypotheses, not guaranteed outcomes.

---

# First 30 days — execution

| Days  | Action                                                                      | Output                          |
| ----- | --------------------------------------------------------------------------- | ------------------------------- |
| 1–5   | Instrument visit → registration → start → completion → report → plan choice | Measured funnel                 |
| 6–10  | Soft launch, ambassadors, referral loop, ads capped at 100 JOD              | First readings                  |
| 11–20 | 15 parent interviews + parent content twice weekly                          | WTP + acquisition signal        |
| 21–30 | Refundable pre-order + channel comparison                                   | Pre-order + plan-choice results |

---

# 30-day decision rules

### Continue

If:

```text
Registration ≥25%
Completion ≥40%
Cost/registration ≤1.80 JOD
```

Continue to 90 days with the same message.

### Fix the funnel

If registration or completion is materially below target:

> Fix the landing page or diagnostic before increasing spend.

### Limit paid advertising

If cost/registration is above 3 JOD with weak organic/referral performance:

> Stop or limit paid ads and prioritize communities, ambassadors and teacher sharing.

### Weak parent demand

If fewer than 3/15 parents say they would pay:

> Do not claim demand. Investigate objections and packaging.

Keep 32 JOD as the current price-floor hypothesis rather than automatically lowering it.

---

# 90-day decision gates

The gates require at least:

```text
300 free users
+
20 payers
```

before conversion and retention percentages are treated as strong signals.

### Weak result

```text
Free-to-paid <2%
OR
CAC/payer >45 JOD
```

Action:

* No hiring
* No scale-up
* Revisit packaging/content
* Stay Stage 1

### Moderate result

```text
Free-to-paid 2–3.5%
AND
Churn >12%
```

Action:

* Stay lean
* Grow through low-cost/free channels

### Strong result

```text
Free-to-paid ≥3.5%
Retention ≥88%
CAC/payer ≤18 JOD
Referrals ≥20%
```

Action:

* Open paid roles one at a time
* Rerun Task 2 using measured economics

### Stronger result

```text
Free-to-paid ≥5%
```

with the same retention/CAC performance:

> Prepare scale-up only after longer verification.

These are **decision gates, not forecasts**.

---

# Resources, risks & next steps

## Team

Four members split across:

* Product/diagnosis
* Growth/content
* Parent research/partnerships
* Analytics/operations

No paid staff before the validation gate.

## 90-day budget

Approximately:

```text
1,900 JOD
```

at Stage 1 planning cost, including approximately 300 JOD/month test marketing.

No funding source is assumed.

## Payments and tax

Before taking real money, confirm:

* Registration requirements
* Tax requirements
* Gateway fees
* Refund process

## Child data

Require:

* Parent consent/account
* Minimum necessary data
* Clear privacy notice

## Main risks

* Low registration
* Noisy sample
* Price/value mismatch
* Weak referral
* Teacher reluctance
* Diagnosis quality weaker than the six selected cases

## Immediate next steps

* Instrument the funnel end-to-end.
* Finish the Arabic parent report and interview guide.
* Verify payment/tax/privacy setup before real payments.
* Recruit the first ambassador and teacher-validation cohorts.

---

# Current limitations

The project is an MVP and intentionally makes several limitations explicit:

* Only one demonstrated content domain is currently shipped.
* The current benchmark is synthetic.
* BKT parameters are not calibrated on real learner data.
* Confidence levels are evidence-based ordinal labels, not validated probabilities.
* The current content graph is mainly linear.
* No real field pilot has been completed yet.
* AI is optional and does not determine the core diagnosis.
* Older databases may retain unused legacy tables from previous versions.

These limitations are documented rather than hidden.

---

# MVP goal

Juthoor's MVP is focused on one core promise:

> **Don't just tell the learner what they got wrong. Help identify where the gap started, show the evidence, and guide the learner back to mastery.**

---

# Important documentation

```text
docs/POSITIONING.md
docs/FINAL_B2C_AUDIT.md
docs/COMPETITIVE_ADVANTAGE.md
docs/FINANCIAL_MODEL.md
docs/DEMO_SCRIPT.md
docs/ARCHITECTURE.png
```

---

# Sources

1. Department of Statistics, Jordan Statistical Yearbook 2024 – Education.
2. OECD Education GPS – Jordan, PISA 2025.
3. "Private Tutoring in Jordan: Underpinning Factors and Impacts", IJHSS 3(13), 2013.
4. Al-Adaa Center, Assessment of the Current State of Education in Jordan (2023/2024).
5. TechSparks Juthoor MVP repository.
6. TechSparks six anonymised cases S01–S06.
7. TechSparks student questionnaire, 34 responses, 1–3 October 2026.
8. DataReportal/ITU internet-use reference from the original model; re-verify exact year/source before external publication.
9. RevenueCat State of Subscription Apps 2026 – Education; used as an external subscription benchmark in the original model.
10. Jordan tax/payment and labour references used in the original planning model; confirm before launch.

---

# Juthoor | جذور

**Adaptive learning that looks beneath the mistake.**
>>>>>>> f32b62e70c21a476ee538f9065465fa6cdd48ad3
