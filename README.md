# جذور | Juthoor

**A prerequisite-aware adaptive learning and root-learning-gap diagnosis platform.**

When a learner struggles with a lesson, Juthoor gathers evidence across the prerequisite graph,
probes earlier skills, and names the *most likely* underlying gap — with the evidence, an honest
confidence level, and a targeted remediation. The learner remediates, retries the original lesson,
mastery is updated, and the teacher sees the diagnosis and what happened after it.

> منصة تعلّم تكيفي تعرف المتطلبات السابقة لكل مهارة: عند تعثّر المتعلم تجمع الأدلة عبر شجرة المتطلبات
> وتقدّر الفجوة الجذرية الأرجح مع الأدلة ومستوى الثقة، ثم تعالجها وتعيده إلى الدرس الأصلي، ويرى المعلم التشخيص ونتيجته.

The MVP demonstrates **one domain** — integer and fraction lessons from the Jordanian
mathematics curriculum (9 live lessons) — through a diagnosis core that is not tied to
mathematics (see *Architecture*). Other subjects are not built.

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
the `public` schema) → `scripts/init_db.py` (create tables, add any newer columns) →
`scripts/seed_shop.py` → `scripts/seed_demo.py` (demo learners, played through the real engine).

Open <http://localhost:8000/app/>. Demo password for every account: `demo1234`.

| Account | Role | Story |
|---|---|---|
| `student2@demo.jo` (عمر) | student in a class (full diagnosis) | Really mastered absolute value + comparing; now on *multiplying integers*. 5–7 wrong answers lead to the root *adding integers*. |
| `teacher@demo.jo` | teacher (school plan) | Class dashboard, diagnosis record per learner, one-click remediation. |
| `student1@demo.jo` (ليان) | student (pro) | Already has a persisted diagnosis — visible to the teacher. |
| `parent@demo.jo` | parent of ليان | Child report. |
| `student3..6@demo.jo` | class members | |

- `run_demo.py` uses `DATABASE_URL` from the environment or `.env`; if neither is set it uses
  `postgresql://postgres:1234@localhost:5432/Juthoor`. It **never** falls back to SQLite silently;
  `--sqlite` exists only as an explicit offline backup and prints a warning.
- `--reset` drops and recreates the `public` schema of that database, then reseeds. Run it before
  every demo so Omar starts clean. Without `--reset`, existing databases are upgraded additively
  (`app/database.py: ensure_schema`).
- Judge mode is on by default (only the learning workflow in the menu, no rate limits).
  `--full` shows everything else (shop, community, plans), which is outside the MVP scope.
- `GET /health` reports `database: ok|unavailable` and the dialect.

## The core workflow

```
Learner answers a question on skill S
  └─ wrong → BKT update, practice plan starts (same idea again → easier → prerequisite)
       └─ every wrong answer returns evidence_status = insufficient_evidence + why
            └─ the leading candidate has only one wrong probe → one confirmation probe on it
                 └─ verdict: root_identified — root, path, evidence per skill, confidence level,
                    explanation, intervention; DiagnosisEvent persisted
                      └─ remediation on the root (difficulty 1 → 3, mastery threshold 0.85)
                           └─ return_up: the learner retries the original lesson
                                └─ teacher drawer: diagnosis record + outcome
                                   (answers on the root after diagnosis, retry on the original lesson, resolved?)
```

The practice page shows this loop as a six-step stepper (**مسار التشخيص**: practising → gathering
evidence → likely root → targeted remediation → retry → mastery updated). The stage is computed on the
server (`app/services/workflow.py`) from the live learner state and the latest persisted diagnosis and is
returned as `workflow` by `POST …/adaptive/answer` and `GET …/adaptive/state`.

### Diagnosis rules (`app/engine/diagnosis.py`)

1. **failing(s)**: not currently believed mastered, and more wrong than right answers on `s`.
2. **solid(s)**: believed mastered, or every observed answer on `s` correct. Otherwise *unverified*.
   A mastered skill stops being "believed" only when fresh errors drop its BKT estimate below 0.5
   (two wrong answers in a row from 0.85); old history alone never re-opens it.
3. Candidates = failing skills on `origin + all prerequisites (ancestors)`.
4. A candidate is eligible only if **every direct prerequisite is solid** (a failing prerequisite is a
   deeper explanation; an unverified one cannot be ruled out).
5. Among eligible candidates, the strongest direct evidence wins (most wrong, then error rate), then
   the more fundamental skill. Other eligible candidates are reported as `competing`.
6. **No root is named** unless the chain shows ≥ 3 wrong answers *and* the root itself ≥ 2.
   Otherwise the verdict is `insufficient_evidence` with the reason (`too_few_errors`,
   `root_needs_confirmation`, `prerequisites_unverified`, or `mixed_evidence` when errors were seen but
   every skill still has at least as many right answers as wrong). `no_difficulty` means no unmastered
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

`p_gap` in the payload is `1 − BKT p(mastery)`. The BKT parameters (`app/engine/config.py`) are
literature-style defaults; **they have not been calibrated on real learner data**, so `p_gap` is a model
estimate, not a measured probability. In the Omar demo the root is named with *medium* confidence
because the root has two wrong answers.

### AI is optional

The diagnosis, question generation (140 deterministic templates), and grading never call an AI
service. An LLM (OpenAI/Groq) is used only if a key is set, for tutor replies and optional question
wording; every call has a timeout and falls back to the offline generator / offline tutor. Tested
with a provider that always throws (`test_g_…`).

## Architecture

- `app/static/` – single-page app, vanilla ES modules, no build step, served at `/app/`.
- `app/main.py`, `app/routers/` – FastAPI; JWT bearer auth; role checks in `app/deps.py`.
- `app/services/engine_bridge.py` – loads/saves learner state, persists attempts, drill-downs and
  diagnoses, builds the teacher-facing diagnosis history with outcomes.
- `app/services/session_core.py` – one question/answer step: practice plan, confirmation probes, evidence status.
- `app/engine/diagnosis.py` – **domain-agnostic**: graph validation (unknown prerequisite, self-loop,
  duplicate, cycle), traversal, candidate ranking, confidence. No curriculum or language inside.
- `app/engine/knowledge_graph.py` – the mathematics content graph (9 skills); validated at import.
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
python -m compileall -q app scripts tests

# Real-browser walk-through (Chromium via Playwright; run while run_demo.py is serving):
pip install playwright && python -m playwright install chromium
python tests/e2e/browser_e2e.py      # then run_demo.py --reset again: it changes Omar's state
```

Which of these have actually been run, and where, is recorded in `HANDOFF.md` ("Verification status").

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
| H | targeted remediation assigned on the root | `test_bcd_…` (next question), `test_features.py::test_one_click_remediation_…` |
| I | remediation success → retry of the original lesson → mastery → teacher outcome | `test_core_workflow.py::test_e_…` |
| J | remediation failure: gap kept, no duplicate diagnosis | `test_core_workflow.py::test_f_…` |
| K | persistence across a simulated restart, then the retry continues | `test_core_workflow.py::test_persistence_…` |
| L | teacher sees diagnosis, evidence, intervention, outcome; others cannot | `test_core_workflow.py::test_i_…` |
| M | invalid input (empty, too long, missing, null, garbage, replay, refresh) | `test_core_workflow.py::test_k_…`, `test_j_…`, `test_api.py` |
| N | missing learner; stale state with an unknown skill is repaired | `test_core_workflow.py::test_n_…` |
| O/P | unknown prerequisite, self-loop, duplicate, cycle, unknown origin; linear and diamond graphs | `test_diagnosis_engine.py` |
| Q | AI provider failing (questions, diagnosis, tutor) | `test_core_workflow.py::test_g_…`, `test_q_…` |
| R | database outage → 503; failure mid-answer rolls back cleanly | `test_core_workflow.py::test_k_database_…`, `test_r_…` |
| S | repeated execution (same history → same root; random learners keep invariants) | `test_j_…`, `test_diagnosis_engine.py` |
| – | configuration (blank values, booleans, no `.env` leak) | `test_config.py` |
| – | question-bank integrity (`BANK_SAMPLES=20000` for the long run) | `test_bank_integrity.py` |
| V | ownership/authorization: other students' data, economy, payments; forged and expired tokens | `test_economy_payments.py`, `test_core_workflow.py::test_i_…`, `test_api.py` |
| W | payments: session ownership, bad cards, double confirm, renewal extends the period, UTC `…Z` timestamps | `test_economy_payments.py`, `test_features.py` |
| X | shop/avatar: catalogue present on a fresh DB, purchase rules, no double charge, wearing needs ownership | `test_economy_payments.py`, `test_api.py`, `test_features.py` |
| – | UI: evidence → root → remediation → retry → resolved, from real engine payloads | `tests/js/smoke.mjs` |
| – | real browser: login → wrong answers → diagnosis card → outage message → remediation → retry → refresh → teacher record → PostgreSQL check | `tests/e2e/browser_e2e.py` |

## Field validation (lightweight)

- `docs/PILOT.md` – 3-day classroom protocol (pre/post quiz). `scripts/pilot_summary.py` summarises it.
- **Teacher-blind comparison:** before opening Juthoor's report, the teacher writes the gap she believes
  each learner has into `docs/teacher_agreement_template.csv`; then Juthoor's root is copied in and
  `python scripts/agreement_summary.py docs/teacher_agreement_template.csv` reports raw agreement.
  That is an early agreement signal on a small sample — not diagnostic accuracy.

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

Teacher one-click remediation (`POST /classrooms/{id}/remediation`) targets only students whose state shows
the gap and who have not already been assigned remediation for it since their latest diagnosis; when nobody
qualifies it answers `422 no_students_with_gap` instead of creating duplicates.

Dependencies: `requirements.txt` is the core runtime (FastAPI, SQLAlchemy, psycopg2, pydantic-settings,
PyJWT, bcrypt, networkx, …) with version ranges that have wheels for current Python versions.
`requirements-optional.txt` holds the LLM, Stripe and vector-store SDKs — the core workflow never needs them.

## Known limitations

- One demonstrated domain: 9 of 18 lessons of the curriculum map are live (units 1–2).
- The prerequisite edges, including the integers → fractions edge, are a pedagogical assumption not yet
  reviewed by teachers.
- BKT parameters and the evidence thresholds are uncalibrated defaults; the confidence level is a
  documented rule, not a validated probability.
- The current graph is a chain; branching and competing roots are supported and tested on a synthetic
  graph, not yet on curriculum content.
- Rate limiting is in-process memory (single worker). No load testing has been done.
- The off-topic guardrail for the tutor is keyword-based.
- No field pilot has been run yet.
- Shop, community, esports and payments exist in the code base but are outside the MVP scope and hidden
  in judge mode.
