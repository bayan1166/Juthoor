# Juthoor \| جذور 

> **Prerequisite-aware adaptive learning and root-learning-gap
> diagnosis.**

Juthoor is an adaptive learning MVP built around a simple idea: a
learner’s visible mistake is not always the underlying problem.

When a learner struggles, Juthoor follows the prerequisite path, gathers
evidence from earlier skills, and decides whether there is enough
evidence to identify a likely root gap. If the evidence is not
sufficient, it says so instead of forcing a diagnosis.

When a root gap is supported by evidence, Juthoor assigns targeted
remediation, returns the learner to the original lesson, updates
mastery, and records the outcome for the teacher.

> **جذور** منصة تعلّم تكيفي تتابع المتطلبات السابقة للمهارات. عند تعثّر
> المتعلم، تجمع المنصة الأدلة عبر مسار المتطلبات السابقة، وتحدد الفجوة
> الجذرية الأرجح عندما تتوفر أدلة كافية، أو تصرّح بأن الأدلة غير كافية
> للحسم. بعد ذلك تعالج الفجوة وتعيد المتعلم إلى المهارة الأصلية، مع حفظ
> التشخيص ونتيجته للمعلم.

## MVP scope

The current MVP uses **Grade 6 mathematics** as its implemented
validation scope:

- 9 live lessons from the current curriculum map
- prerequisite-aware adaptive practice
- evidence gathering across prerequisite skills
- root-gap diagnosis with explicit confidence levels
- `insufficient_evidence` when evidence is not enough
- targeted remediation and retry
- BKT-based mastery updates
- teacher-facing diagnosis and outcomes
- optional AI assistance for tutor responses and question wording

**Grade 6 mathematics is the current MVP scope, not the long-term
definition of the product.** The diagnosis engine is designed around
prerequisite graphs rather than mathematics-specific rules. Other
subjects are not yet implemented.

## Core workflow

``` text
Learner answers a question
        │
        ├── Correct → update mastery and continue
        │
        └── Wrong
              │
              ├── update BKT + record evidence
              ├── insufficient evidence → keep probing
              │
              └── evidence supports a root
                     │
                     ├── root + path + evidence + confidence
                     ├── persist DiagnosisEvent
                     ├── targeted remediation
                     ├── retry original lesson
                     └── update mastery + record outcome
```

The UI presents the workflow as:

**Practising → Gathering evidence → Likely root → Targeted remediation →
Retry → Mastery updated**

## Diagnosis

The main diagnosis logic is in `app/engine/diagnosis.py`.

The engine:

1.  records answers and updates mastery;
2.  follows prerequisite edges when difficulty persists;
3.  checks whether prerequisites have enough evidence to be considered
    solid;
4.  compares eligible candidate gaps;
5.  names a root only when the configured evidence thresholds are met;
6.  otherwise returns `insufficient_evidence`;
7.  returns machine-readable evidence requirements;
8.  assigns remediation only after a supported root is identified.

A root currently requires:

- at least 3 wrong answers across the relevant chain;
- at least 2 wrong answers on the candidate root;
- `MIN_ROOT_LR = 20`.

Insufficient evidence can be reported as:

`too_few_errors`, `root_needs_confirmation`, `prerequisites_unverified`,
or `mixed_evidence`.

The confidence level is ordinal, not a probability:

| Level    | Meaning                                                                    |
|----------|----------------------------------------------------------------------------|
| `high`   | Strong root evidence and observed correct evidence on direct prerequisites |
| `medium` | At least 2 wrong answers on the root and more wrong than right             |
| `low`    | Weaker evidence                                                            |

These thresholds are documented defaults and have **not** been
calibrated on real learner data.

## BKT

Juthoor uses Bayesian Knowledge Tracing for mastery updates.

The implementation:

- clamps mastery to `[0.001, 0.999]`;
- avoids absorbing states at exactly 0 or 1;
- validates BKT parameters;
- keeps mastery estimation separate from diagnosis.

The current BKT parameters are literature-style defaults. They are **not
calibrated on a real learner dataset**.

## Synthetic benchmark

Run:

``` bash
python scripts/diagnostic_benchmark.py --reps 5
```

The shipped threshold configuration currently reports, on synthetic
learners:

- clean cases: 97.1% correct among cases where a root is named;
- clean cases: 89.8% correct across all gap cases;
- noisy cases: 91.1% correct among cases where a root is named;
- noisy cases: 77.8% correct across all gap cases.

The benchmark also measures abstention and false diagnoses under
different noise levels.

These are **synthetic-engine measurements only**. They are not claims
about real students, learning gain, or educational efficacy.

See `FINAL_AUDIT.md`, `docs/COMPETITIVE_ADVANTAGE.md`, and
`benchmarks/sweep.json`.

## Architecture

``` text
app/
├── engine/
│   ├── adaptive_engine.py      # BKT, difficulty, backtracking, remediation
│   ├── diagnosis.py            # prerequisite-aware diagnosis
│   ├── knowledge_graph.py      # current curriculum graph
│   ├── benchmark.py            # synthetic benchmark
│   └── integrity.py            # learner-state invariants
├── services/
│   ├── engine_bridge.py        # engine ↔ persistence
│   └── session_core.py         # question/answer workflow
├── routers/                    # FastAPI endpoints
├── models/                     # SQLAlchemy models
├── schemas/                    # API schemas
├── config.py                   # configuration
└── main.py                     # application entry point

migrations/versions/            # versioned SQL migrations
scripts/                        # setup, demo, integrity and benchmark tools
tests/                          # Python tests
tests/js/                       # UI tests
tests/e2e/                      # browser E2E
docs/                           # project documentation
finance/                        # financial model
```

The diagnosis engine is domain-agnostic. The current content graph lives
separately in `app/engine/knowledge_graph.py`.

## Reliability

The answer workflow includes:

- `SELECT ... FOR UPDATE` for learner state;
- `INSERT ... ON CONFLICT DO NOTHING` for state creation;
- a unique `(student_id, skill_id)` constraint;
- database CHECK constraints;
- transactional rollback on failures;
- optional idempotency through `request_id`;
- integrity checking through `scripts/check_integrity.py`.

A repeated `request_id` returns the stored response. Reusing the same ID
with a different answer returns `409 request_id_reused`.

## Database and migrations

Normal development and testing use PostgreSQL 14+.

Migrations are versioned SQL files under:

``` text
migrations/versions/
```

They are applied in order and recorded in `schema_migrations`. The
project uses its own migration runner rather than Alembic.

SQLite is not used as a silent fallback.

## Quick start

Requirements:

- Python 3.11+
- PostgreSQL 14+
- Node 18+ for UI tests
- Chromium for optional browser E2E

``` bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows:
# .venv\Scripts\activate

python -m pip install -r requirements-dev.txt
python scripts/check_env.py --dev
```

Create `.env` from `.env.example` and set `DATABASE_URL`.

Then:

``` bash
python run_demo.py --reset
```

Open:

``` text
http://localhost:8000/app/
```

Demo password:

``` text
demo1234
```

## Demo accounts

| Account                                 | Role     | Purpose                                    |
|-----------------------------------------|----------|--------------------------------------------|
| `student2@demo.jo`                      | Student  | Active adaptive workflow and diagnosis     |
| `teacher@demo.jo`                       | Teacher  | Class dashboard, diagnosis and remediation |
| `student1@demo.jo`                      | Student  | Persisted diagnosis visible to teacher     |
| `parent@demo.jo`                        | Parent   | Child report                               |
| `student3@demo.jo` – `student6@demo.jo` | Students | Additional class members                   |

Run `python run_demo.py --reset` before a fresh demo.

## Testing

``` bash
python -m pytest -q
cd tests/js && npm test
python scripts/preflight.py
python -m compileall -q app scripts tests finance
python scripts/diagnostic_benchmark.py --reps 5
python scripts/benchmark_sweep.py
python finance/model.py
```

Optional browser test:

``` bash
pip install playwright
python -m playwright install chromium
python tests/e2e/browser_e2e.py
```

The test suite covers core workflow, diagnosis, insufficient evidence,
competing candidates, remediation, persistence, authorization, invalid
inputs, graph integrity, AI-provider failures, rollback, concurrency,
configuration, question-bank integrity, payments/economy, UI behaviour
and browser E2E.

Verification status is recorded in `HANDOFF.md` and `FINAL_AUDIT.md`.

## AI

AI is optional.

The core learning workflow does not require an LLM:

- diagnosis is deterministic;
- grading is deterministic;
- question generation has deterministic templates;
- BKT and remediation do not require an external AI provider.

OpenAI/Groq can be configured for tutor replies and optional question
wording. External calls have timeouts and fallbacks, and provider
failures are tested.

## Field validation

The repository includes a lightweight pilot protocol in `docs/PILOT.md`
and a teacher-agreement template in
`docs/teacher_agreement_template.csv`.

The intended comparison is blind: the teacher records a suspected gap
before seeing Juthoor’s diagnosis, then the two records can be compared.

**No formal pilot or teacher-agreement dataset has been collected yet.**

Therefore this repository does not claim validated diagnostic accuracy,
learning gain, or educational efficacy.

## Known limitations

- 9 of 18 mapped curriculum lessons are currently live.
- Current demonstrated content is Grade 6 mathematics.
- Prerequisite relationships are pedagogical assumptions and need
  broader expert review.
- BKT parameters and diagnosis thresholds are not calibrated on real
  learner data.
- The current curriculum graph is mostly linear; branching is supported
  by the engine and synthetic tests.
- Production-scale HTTP load testing has not been completed.
- Rate limiting is in-process memory.
- Tutor off-topic protection is keyword-based.
- No formal classroom pilot has been completed.
- Shop, community, esports and payments exist in the codebase but are
  outside the MVP learning workflow and hidden in judge mode.

## Documentation

| File                            | Purpose                               |
|---------------------------------|---------------------------------------|
| `HANDOFF.md`                    | Verification and handoff status       |
| `FINAL_AUDIT.md`                | Technical, market and financial audit |
| `docs/ARCHITECTURE.png`         | Architecture overview                 |
| `docs/PILOT.md`                 | Field-validation protocol             |
| `docs/COMPETITIVE_ADVANTAGE.md` | Evidence-first differentiation        |
| `docs/FINANCIAL_MODEL.md`       | Financial model                       |
| `docs/TEST_REPORT.md`           | Generated test report                 |
| `TASKS/`                        | Submission tasks                      |

## Team

**Juthoor \| جذور**

- Bayan Marashdeh
- Marah Al-Kilani
- Rana Shalout
- Sadeen Nababteh

Jordan 2076 Bootcamp

## License

This project is released under the **MIT License**.

See [`LICENSE`](LICENSE).

The MIT License applies to Juthoor code and original project materials
owned by the team. Third-party libraries, datasets, fonts, icons,
curriculum materials, and other external assets remain subject to their
respective licenses and terms.
