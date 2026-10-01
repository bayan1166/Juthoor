# Juthoor Backend (B2B2C Architecture)

FastAPI + PostgreSQL backend that wraps the existing Juthoor adaptive-learning engine
(`app/engine/`, carried over from the original Streamlit MVP with its merge conflicts
resolved) in a multi-tenant, API-driven service. Adds a RAG-powered Socratic tutor,
a dual-currency economy, a Math Esports module, and a B2B/parent analytics dashboard.

## Merge conflicts in the original codebase

`config.py`, `knowledge_graph.py`, `practice.py`, `prompts.py`, `theme.py`,
`adaptive_engine.py` and `offline_bank.py` all shipped with unresolved
`<<<<<<< HEAD / ======= / >>>>>>>` markers. `app/engine/` contains those files with
the `HEAD` branch kept (it is the more complete version: `MAX_DRILL_DEPTH`, the LLM
remediation hooks, Arabic breadcrumbs, `nearest_prerequisite_with_bank`, and the
light/dark palette). Resolve this in your own git history before continuing to
develop the engine directly; this backend only re-packaged the already-resolved text.

## Project layout

```
app/
  engine/              original adaptive engine, knowledge graph, offline bank,
                       avatar/theme/svgkit modules -- copied in with import paths
                       rewritten to app.engine.* so they run as a normal package
  models/              SQLAlchemy ORM models (org/user, adaptive, economy, esports, chat)
  schemas/             Pydantic request/response models
  routers/             FastAPI route handlers
  services/            business logic, including services/rag/ (Chroma + Groq)
  config.py            pydantic-settings environment configuration
  database.py          SQLAlchemy engine/session
  security.py          JWT + password hashing
  deps.py              auth dependencies and per-student access control
  main.py              FastAPI app entry point
scripts/
  init_db.py           create all tables (use Alembic migrations for real deployments)
  seed_shop.py         convert app.engine.avatar_items.CATALOG into ShopItem rows
  ingest_curriculum.py build the Chroma vector store from the knowledge graph
  seed_demo.py         demo org, teacher, parent and students with history
sql/schema.sql         raw PostgreSQL DDL generated from the SQLAlchemy models, for review
frontend/src/          TypeScript API client + a React Socratic chat widget
tests/                 pytest suite (in-memory SQLite)
```

## Running locally

```
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in DATABASE_URL, JWT_SECRET, GROQ_API_KEY
python scripts/init_db.py
python scripts/seed_shop.py
python scripts/seed_demo.py         # optional: demo teacher/parent/students, password demo1234
python scripts/ingest_curriculum.py # optional: without it the tutor still answers (no context)
uvicorn app.main:app --reload       # API docs at http://localhost:8000/docs
```

No Postgres/Docker available (e.g. on the demo laptop)? Set
`DATABASE_URL=sqlite:///./juthoor.db` in `.env` and run the same commands.

If you already had a database from before this change, drop and recreate it
(`init_db.py` only creates missing tables; `student_adaptive_states` gained a
`pending_question` column).

## Tests

```
pip install -r requirements-dev.txt
pytest -q
```

Runs against in-memory SQLite; no Postgres, Chroma, or Groq needed. Covers the
backtracking engine (missing `mult_div_integers` repeatedly must walk back to the
`absolute_value` root gap), auth validation, server-side grading, replay protection,
role-based access, the roster endpoint, the offline chat path, and a 25-answer
stability run.



## Frontend (Streamlit)

```
pip install -r web/requirements.txt
streamlit run web/streamlit_app.py   # http://localhost:8501, expects API on :8000
```

Or start both at once (SQLite fallback, no Docker needed):

```
python run_demo.py                    # demo accounts: password demo1234
```

RAG tutor (optional):

```
pip install -r requirements-optional.txt
echo "GROQ_API_KEY=..." >> .env
python scripts/ingest_curriculum.py
```

## Recent fixes

- `GET /adaptive/question` returned 500 on every call (`source` missing). Fixed.
- `requirements.txt`: added `email-validator` (app crashed on import) and pinned
  `bcrypt==4.0.1` (passlib 1.7.4 fails on newer bcrypt, breaking register/login).
- Answers are now graded **server-side** against the question actually served
  (`pending_question`). The client only sends `selected_answer`; a forged
  `correct_answer` is ignored and re-submitting the same answer returns 409.
  The decision now includes `is_correct`, `correct_answer`, `misconception`
  (diagnosed from the question's known traps) and `explanation`.
- Questions include a shuffled `options` list ready to render.
- Registration: admin roles can no longer be self-assigned; password >= 6 chars,
  non-blank name, grade 1-12, `guardian_id` must be an existing parent, emails are
  case-insensitive.
- Chat no longer 500s when the vector store is empty or chromadb is missing
  (chromadb is imported lazily); Groq replies are requested as JSON and parsed
  tolerantly. Default model changed to `llama-3.3-70b-versatile`
  (`llama-3.1-70b-versatile` was retired). `skill_context` and message are validated.
- Esports submissions are validated (`0 <= correct <= total <= question_count`).
- New: `GET /curriculum/skills` (knowledge graph + teaching content, public) and
  `GET /me/students` (a parent's children / a teacher's organization).
- SQLite supported as a no-Docker fallback; `.env.example` added.

## Key design decisions

- The BKT math, the knowledge graph, the cascading drill-down, and the offline
  question bank are untouched -- `engine_bridge.py` is the only new code that talks
  to them, translating the in-memory `StudentState` dataclass to and from Postgres
  rows on every request. This keeps the pedagogical logic testable in isolation,
  exactly as it already was.
- The RAG tutor never generates the final answer. Its system prompt forbids it, and
  its output is parsed defensively (same pattern as the existing `llm_remediation.py`):
  on any malformed response it falls back to a generic Socratic prompt rather than
  breaking the chat. When the model reports `gap_detected` with a valid `skill_id`,
  `engine_bridge.trigger_manual_drill_down` builds a remediation plan with
  `app/engine/practice.py` and reroutes the student's next question there, logging a
  `DrillDownEvent` the dashboard can later report on.
- Coins are earned continuously (per correct answer, per mastery, per esports
  challenge); gems are earned only from mastery bonuses and top esports finishes, or
  purchased with real money (`TxnReason.real_money_purchase`, wired for a payment
  provider webhook but not implemented here). Premium/job/heritage avatar items are
  gem-only so gems keep genuine scarcity value.
- All student-scoped endpoints go through `require_student_access`, which allows the
  student themselves, their linked parent (`guardian_id`), or a teacher/admin in the
  same organization -- enforcing the B2B2C boundary at the dependency layer rather
  than in each router.
