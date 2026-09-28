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
sql/schema.sql         raw PostgreSQL DDL generated from the SQLAlchemy models, for review
frontend/src/          TypeScript API client + a React Socratic chat widget
```

## Running locally

```
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in DATABASE_URL, JWT_SECRET, GROQ_API_KEY
python scripts/init_db.py
python scripts/seed_shop.py
python scripts/ingest_curriculum.py
uvicorn app.main:app --reload
```

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
