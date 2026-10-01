# Juthoor Backend (B2B2C Architecture)

FastAPI + PostgreSQL backend that wraps the existing Juthoor adaptive-learning engine (`app/engine/`, carried over from the original Streamlit MVP with its merge conflicts resolved) in a multi-tenant, API-driven service.

Adds a RAG-powered Socratic tutor, a dual-currency economy, a Math Esports module, and a B2B/parent analytics dashboard.

## Merge conflicts in the original codebase

`config.py`, `knowledge_graph.py`, `practice.py`, `prompts.py`, `theme.py`, `adaptive_engine.py` and `offline_bank.py` originally shipped with unresolved:

```text
<<<<<<< HEAD
=======
>>>>>>> 
````

markers.

`app/engine/` contains the resolved versions with the `HEAD` branch kept. This is the more complete version and includes:

* `MAX_DRILL_DEPTH`
* LLM remediation hooks
* Arabic breadcrumbs
* `nearest_prerequisite_with_bank`
* light/dark palette support

Resolve these conflicts in your own git history before continuing to develop the engine directly. This backend re-packages the already-resolved engine.

## Project layout

```text
app/
  engine/              original adaptive engine, knowledge graph, offline bank,
                       avatar/theme/svgkit modules -- copied in with import paths
                       rewritten to app.engine.* so they run as a normal package

  models/              SQLAlchemy ORM models (org/user, adaptive, economy,
                       esports, chat)

  schemas/             Pydantic request/response models

  routers/             FastAPI route handlers

  services/            business logic, including services/rag/ (Chroma + Groq)

  config.py            pydantic-settings environment configuration

  database.py          SQLAlchemy PostgreSQL engine/session

  security.py          JWT + password hashing

  deps.py              auth dependencies and per-student access control

  main.py              FastAPI app entry point

scripts/
  init_db.py           create all tables
                       (use Alembic migrations for real deployments)

  seed_shop.py         convert app.engine.avatar_items.CATALOG into ShopItem rows

  ingest_curriculum.py build the Chroma vector store from the knowledge graph

  seed_demo.py         demo org, teacher, parent and students with history

sql/
  schema.sql           raw PostgreSQL DDL generated from the SQLAlchemy models,
                       for review

frontend/
  src/                 TypeScript API client + React Socratic chat widget

tests/
  pytest suite for the backend and adaptive engine
```

## Requirements

* Python 3.11+
* PostgreSQL 14+
* PostgreSQL database
* Groq API key for the optional RAG tutor
* Chroma for optional RAG curriculum ingestion

## PostgreSQL setup

Create a PostgreSQL database for Juthoor.

For example:

```sql
CREATE DATABASE juthoor;
```

Configure the database connection in `.env`:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/juthoor
JWT_SECRET=your-secret-key
GROQ_API_KEY=your-groq-api-key
```

The application database is PostgreSQL.

## Running locally

Create and activate a virtual environment:

```bash
python -m venv venv
```

### Linux / macOS

```bash
source venv/bin/activate
```

### Windows

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy the environment configuration:

```bash
cp .env.example .env
```

On Windows, copy `.env.example` to `.env` manually if `cp` is unavailable.

Configure the required environment variables:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/juthoor
JWT_SECRET=your-secret-key
GROQ_API_KEY=your-groq-api-key
```

Initialize the database:

```bash
python scripts/init_db.py
```

Seed the shop:

```bash
python scripts/seed_shop.py
```

Optionally seed demo data:

```bash
python scripts/seed_demo.py
```

The demo accounts use:

```text
password: demo1234
```

Optionally ingest the curriculum into Chroma:

```bash
python scripts/ingest_curriculum.py
```

Start the API:

```bash
uvicorn app.main:app --reload
```

API documentation:

```text
http://localhost:8000/docs
```

## Database migrations

`init_db.py` creates missing tables for local development.

For real deployments, use Alembic migrations.

Create a migration after a model change:

```bash
alembic revision --autogenerate -m "describe change"
```

Apply migrations:

```bash
alembic upgrade head
```

The production database is PostgreSQL.

## Tests

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the test suite:

```bash
pytest -q
```

The test suite covers:

* adaptive-engine backtracking
* missing `mult_div_integers` repeatedly walking back to the `absolute_value` root gap
* authentication validation
* server-side grading
* replay protection
* role-based access
* roster endpoint
* offline chat path
* 25-answer stability run

Tests do not require Groq or Chroma.

## Frontend (Streamlit)

Install frontend dependencies:

```bash
pip install -r web/requirements.txt
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Then start Streamlit:

```bash
streamlit run web/streamlit_app.py
```

Streamlit will run at:

```text
http://localhost:8501
```

The Streamlit frontend expects the FastAPI backend to be available at:

```text
http://localhost:8000
```

## RAG Tutor

The RAG tutor is optional.

Install the optional dependencies:

```bash
pip install -r requirements-optional.txt
```

Configure your Groq API key:

```env
GROQ_API_KEY=your-groq-api-key
```

Build the curriculum vector store:

```bash
python scripts/ingest_curriculum.py
```

The tutor uses Chroma + Groq.

If the vector store is unavailable or empty, the chat endpoint falls back to the
offline Socratic behavior instead of failing.

## Recent fixes

* `GET /adaptive/question` returned 500 on every call (`source` missing). Fixed.
* Added `email-validator` to `requirements.txt`.
* Pinned `bcrypt==4.0.1` because Passlib 1.7.4 fails on newer bcrypt versions,
  breaking register/login.
* Answers are now graded **server-side** against the question actually served
  through `pending_question`.
* The client only sends `selected_answer`.
* A forged `correct_answer` is ignored.
* Re-submitting the same answer returns `409`.
* The decision now includes:

  * `is_correct`
  * `correct_answer`
  * `misconception`
  * `explanation`
* Questions include a shuffled `options` list ready to render.
* Registration:

  * admin roles can no longer be self-assigned
  * password must be at least 6 characters
  * name cannot be blank
  * grade must be 1-12
  * `guardian_id` must reference an existing parent
  * emails are case-insensitive
* Chat no longer returns 500 when the vector store is empty or Chroma is missing.
* Chroma is imported lazily.
* Groq replies are requested as JSON and parsed tolerantly.
* Default Groq model is `llama-3.3-70b-versatile`.
* `skill_context` and message are validated.
* Esports submissions are validated:
  `0 <= correct <= total <= question_count`.
* Added `GET /curriculum/skills`:
  knowledge graph + teaching content, public.
* Added `GET /me/students`:
  parent's children / teacher's organization.
* PostgreSQL is now the application database.

## Key design decisions

### Adaptive learning engine

The BKT math, knowledge graph, cascading drill-down, and offline question bank
are untouched.

`engine_bridge.py` is the only new code that talks to them, translating the
in-memory `StudentState` dataclass to and from PostgreSQL rows on every request.

This keeps the pedagogical logic testable in isolation, exactly as it already was.

### RAG Socratic tutor

The RAG tutor never generates the final answer.

Its system prompt forbids directly giving the answer, and its output is parsed
defensively using the same pattern as the existing `llm_remediation.py`.

If the model returns malformed output, the system falls back to a generic
Socratic prompt rather than breaking the chat.

When the model reports `gap_detected` with a valid `skill_id`,
`engine_bridge.trigger_manual_drill_down` builds a remediation plan with
`app/engine/practice.py` and reroutes the student's next question there.

A `DrillDownEvent` is logged so the dashboard can report remediation activity.

### Economy

Coins are earned continuously:

* per correct answer
* per mastery
* per esports challenge

Gems are earned only from:

* mastery bonuses
* top esports finishes
* real-money purchases

Real-money purchases use `TxnReason.real_money_purchase` and are wired for a
payment-provider webhook, but the payment provider itself is not implemented here.

Premium, job, and heritage avatar items are gem-only so gems retain scarcity value.

### B2B2C access control

All student-scoped endpoints go through `require_student_access`.

Access is allowed for:

* the student themselves
* their linked parent (`guardian_id`)
* a teacher/admin in the same organization

This enforces the B2B2C boundary at the dependency layer rather than duplicating
authorization logic across individual routers.

## Architecture

```text
                    ┌─────────────────────┐
                    │     Streamlit       │
                    │      Frontend       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       FastAPI       │
                    │        API          │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
       │   Engine    │  │     RAG     │  │   Economy   │
       │   Bridge    │  │    Tutor    │  │   Esports   │
       └──────┬──────┘  └──────┬──────┘  └─────────────┘
              │                 │
              ▼                 ▼
       ┌─────────────┐   ┌─────────────┐
       │ PostgreSQL  │   │   Chroma    │
       │             │   │ Vector DB   │
       └─────────────┘   └─────────────┘
```

## Production

For production deployments:

* Use PostgreSQL.
* Use Alembic migrations.
* Store secrets in environment variables or a secret manager.
* Use a strong `JWT_SECRET`.
* Do not use demo passwords.
* Configure PostgreSQL backups.
* Run FastAPI behind a production ASGI server/reverse proxy.
* Configure database connection pooling appropriately for the expected number of users.
* Use HTTPS.
* Keep Groq/API credentials server-side.
* Do not expose database credentials to the frontend.

## License

Juthoor is released under the **Juthoor Custom License**.
```
You may view, study, modify, and use the code for personal,
educational, research, and other non-commercial purposes.

Commercial use, resale, or incorporation into a commercial product
or service requires prior written permission from the copyright holder.

Any use or redistribution must retain attribution to the original
author and the **Juthoor** project.

See the [LICENSE](LICENSE) file for the full terms.
```
