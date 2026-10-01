# Juthoor Backend & Web Platform (B2B2C Architecture)

FastAPI + SQLite/PostgreSQL backend that wraps the Juthoor adaptive-learning engine in a multi-tenant, API-driven service with a modern Streamlit web frontend.

Built for **Jordan 2076 (Stage 3)**, Juthoor diagnoses the **root educational gap** (Root Gap Diagnosis via Backtracking) for 6th-grade mathematics (Jordanian Curriculum) rather than merely treating the surface-level symptom.

---

## What's in this Release

1. **Dual AI Model Engine (OpenAI Primary + Groq Fallback + Offline)**:
* **OpenAI** (`gpt-4o-mini` / `gpt-4o`) as primary for the Socratic Tutor and dynamic problem generator, using strict `json_object` enforcement.
* Automatic fallback to **Groq** (`llama-3.3-70b-versatile`), and transparent fallback to offline pedagogical heuristics if API keys or internet are unavailable.
* Step-by-step problem deconstruction and clear conceptual explanations upon student request.


2. **Real Community & Friends Module (`/community`)**:
* Backed by database tables: `friendships` and `direct_messages`.
* Search students via unique 4+ digit Student ID (`#handle`), send/accept/reject friend requests, and exchange direct messages.


3. **Virtual Classrooms & Assignments (`/classrooms`, `/assignments`)**:
* Teams-like virtual groups for math classes.
* Students join via short alphanumeric join codes (e.g., `HK3P9W`).
* Teachers create homework assignments and class competitions tied directly to curriculum skills.


4. **Self-Service Password Reset**:
* 3-step password recovery flow (`/auth/forgot-password` and `/auth/reset-password`) with 6-digit verification code.


5. **Jordanian Market Subscription Tiers & Demo Checkout**:
* **Basic (0 JOD)**: Free forever curriculum tree and daily challenges.
* **Pro (4.99 JOD / month)**: Unlimited Socratic AI tutor, instant mistake breakdown, and avatar wardrobes.
* **School (1.49 JOD / student / month)**: Classrooms, homework assignments, class esports, and school analytics.
* Commercial demo checkout page with card validation (15/16 digits, MM/YY, CVV) and confetti feedback.


6. **Optimistic Avatar Customization**:
* Instant avatar equip with zero UI latency (local mutation + background API sync).
* 81 shop items including Jordanian heritage wear and profession suits.


7. **Heritage Green & Emerald UI (Streamlit)**:
* 100% blue-free nature aesthetic with dark emerald, forest green, and gold accents.
* Interactive SVG curriculum tree with visual root-gap backtracking chain.
* Streamlined, bug-free expanders (zero `keyboard_ar` leaks) and modern theme toggle pill.



---

## Project Layout

```text
app/
  engine/              Adaptive engine (BKT), knowledge graph DAG, offline question bank,
                       avatar/theme/svgkit modules
  models/              SQLAlchemy ORM models:
                         - org (Organization, User, Classroom, Assignment)
                         - adaptive (StudentAdaptiveState, AttemptLog, DrillDownEvent)
                         - community (Friendship, DirectMessage)
                         - economy (Wallet, Transaction, AvatarConfig, ShopItem)
                         - chat (ChatSession, ChatMessage)
  schemas/             Pydantic v2 request/response validation models
  routers/             FastAPI endpoints: auth, adaptive, chat, community,
                       curriculum, dashboard, economy, esports
  services/            Business logic, session core, economy, engine bridge,
                       and RAG (Chroma + OpenAI/Groq)
  config.py            Pydantic Settings with CORS origin handling
  database.py          SQLAlchemy database engine/session (SQLite & Postgres)
  security.py          JWT token generation and bcrypt password hashing
  deps.py              Role-based access control and B2B2C student scoping
  main.py              FastAPI application entry point and middleware

web/
  streamlit_app.py     Full-featured RTL Streamlit frontend
  tree_view.py         Interactive SVG curriculum tree renderer
  tree_component.py    Bidirectional leaf click listener
  curriculum.py        Grade 6 math units and lesson metadata
  theme.py             Forest green, emerald, and gold palette tokens
  brand.py             Juthoor medallion brand mark and lockup SVG
  api.py               HTTP client for the backend with friendly error handling

scripts/
  init_db.py           Create database schema and tables
  seed_shop.py         Seed the 81 avatar items into the shop catalog
  seed_demo.py         Seed demo organization, classes, and 5 pre-configured accounts
  ingest_curriculum.py Ingest Grade 6 mathematics concepts into Chroma vector store

run_demo.py            One-command launcher (runs SQLite setup, API :8000, and UI :8501)
tests/                 Comprehensive test suite (45+ tests, runs fully in-memory)

```

---

## Quick Start (Run in 1 Command)

### 1. Environment Setup

```bash
git clone https://github.com/bayan1166/Juthoor.git
cd Juthoor

python -m venv venv

# Linux / macOS:
source venv/bin/activate

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

```

### 2. Install Dependencies

```bash
pip install -r requirements.txt -r web/requirements.txt

```

### 3. Configure Environment (`.env`)

Create a `.env` file in the root directory:

```env
DATABASE_URL=sqlite:///./juthoor_demo.db
JWT_SECRET=your-secure-jwt-random-string-here
ACCESS_TOKEN_MINUTES=120

# OpenAI (Primary AI Model - Optional):
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-4o-mini

# Groq (Fast Fallback Model - Optional):
GROQ_API_KEY=your-groq-api-key-here
GROQ_CHAT_MODEL=llama-3.3-70b-versatile

CORS_ORIGINS=http://localhost:3000,http://localhost:5173

```

*(Note: The system works seamlessly with SQLite for development. If no AI keys are provided, it automatically uses the offline pedagogical tutor).*

### 4. Launch Everything

```bash
python run_demo.py

```

* **Web UI (Streamlit)**: `http://localhost:8501`
* **API Documentation (Swagger)**: `http://localhost:8000/docs`
* **Health Check**: `http://localhost:8000/health` (reports active AI provider)

To reset and rebuild the local database from scratch at any time:

```bash
python run_demo.py --reset

```

---

## Demo Accounts

All demo accounts share the password: **`demo1234`**

| Email | Role | Name | Purpose in Demo |
| --- | --- | --- | --- |
| `student1@demo.jo` | Student | Layan | **Primary Demo Account**: Pre-diagnosed root gap (`absolute_value` from `mult_div`) showing full tree & backtrack path. |
| `student2@demo.jo` | Student | Omar | Demonstrates mastery progression with lush green leaves. |
| `student3@demo.jo` | Student | New Student | Fresh student for live interactive quiz & error card testing. |
| `teacher@demo.jo` | Teacher | Sarah | Classroom management, assignments, and struggle alerts. |
| `parent@demo.jo` | Parent | Ahmad | Linked to student1 for parent diagnostic insights. |

---

## Tests

Install development dependencies and run the suite:

```bash
pip install -r requirements-dev.txt
pytest -q

```

The test suite covers:

* Knowledge graph prerequisite validation
* BKT Bayesian engine and cascading backtracking logic
* Repeated errors walking back to the `absolute_value` root gap
* Server-side grading integrity and replay prevention (409 on re-submission)
* Multi-tenant role-based access control (RBAC)
* Community friendship workflows and direct messaging
* Offline Socratic tutor resilience and JSON schema adherence

---

## Production Deployment

For production environments:

* Set `DATABASE_URL` to a managed PostgreSQL 14+ instance.
* Apply schema migrations using Alembic (`alembic upgrade head`).
* Run the FastAPI application behind an ASGI server like Uvicorn/Gunicorn with multiple workers.
* Ensure `JWT_SECRET` is generated using a cryptographically secure random generator.
* Deploy behind HTTPS with appropriate reverse proxy configurations (Nginx / Cloudflare).

---

## License

Juthoor is released under the **Juthoor Custom License**.

```text
You may view, study, modify, and use the code for personal,
educational, research, and non-commercial competition purposes.

Commercial use, resale, or incorporation into a commercial product
or service requires prior written permission from the copyright holder.

Any use or redistribution must retain attribution to the original
author and the Juthoor project.

```