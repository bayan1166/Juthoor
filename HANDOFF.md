# Juthoor — handoff for a new chat

Attach this file, `README.md`, and `Juthoor-main-mvp.zip` to a new chat and say
**"Continue from HANDOFF.md."**

## What Juthoor is (30 seconds)

Grade-6 Arabic math MVP. When a student misses a question, the engine walks *back*
through prerequisite skills and diagnoses the **root gap** — not the surface failure.
For the demo it works on the Integers unit: multiplication/division → subtraction →
addition → comparing → absolute value. Extending to fractions and grades 7–9 is
"add more skills to the graph", not a rewrite.

The submission for **Jordan 2076 Stage 3 (technical judging, 6 October 2026)** is a
working MVP + 3-minute demo video + 6 slides + architecture diagram.

## What's in the zip (MVP is complete)

- **Backend** — FastAPI at `app/`. Endpoints: `/auth` (register / login / me),
  `/students/{id}/adaptive/*` (question, answer, state, round, drilldowns),
  `/students/{id}/chat/*` (Socratic tutor with RAG + offline fallback),
  `/students/{id}/economy/*` (wallet, shop, purchase, avatar), `/students/{id}/insights`,
  `/organizations/{id}/insights`, `/me/students`, `/curriculum/skills`, `/health`.
- **Adaptive engine** — `app/engine/` (Bayesian Knowledge Tracing + backtracking) and
  `app/services/session_core.py` (pure Python, so it's easy to test).
- **Frontend** — `web/streamlit_app.py`. Streamlit UI (Arabic RTL). Student sees the
  tree, challenges, mistake cards, tutor, shop. Teacher/parent sees the diagnosis
  path and student report.
- **Tests** — `tests/` (in-memory SQLite; no Postgres/Chroma/Groq needed).
- **One-command launch** — `python run_demo.py` sets up SQLite, seeds demo data,
  starts API + UI. No Docker, works on any laptop.
- **Demo accounts** — password `demo1234`. `student1@demo.jo` is pre-seeded with
  the full backtrack chain already diagnosed (perfect for the 4-minute demo).

## Run it

```
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt -r web/requirements.txt
python run_demo.py                                 # opens API :8000 and UI :8501
```

To add the RAG-grounded tutor:

```
pip install -r requirements-optional.txt
echo "GROQ_API_KEY=..." >> .env                    # optional, tutor still works without
python scripts/ingest_curriculum.py
```

Restart. Everything else keeps working offline.

## Tests

```
pip install -r requirements-dev.txt
pytest -q
```

There are ~45 tests covering: the backtracking chain (missing `mult_div_integers`
walks to `absolute_value`), auth validation, server-side grading, replay protection,
role permissions, roster, tutor→practice hand-off, avatar ownership, curriculum
endpoint, chat resilience with no vector store, and a 60-answer stability run.

## What we changed since the older repo

- Frontend is now the API's client (was a self-contained Streamlit prototype).
- Server grades answers against what it served (`pending_question`); the client
  never sees the correct answer up-front, and can't forge it or replay it.
- Remediation logic (same-pattern → easier chain) moved into `app/services/session_core.py`.
- `.env.example`, SQLite fallback, `run_demo.py`, `seed_demo.py`, tests, README rewrite.
- Fixed: `email-validator` missing, `bcrypt` unpinned, retired Groq model, chat 500
  on empty vector store, admin self-signup, weak input validation, shop item worn
  without buying, questions leaking the answer, esports scoring math.

## What is deliberately NOT built

Fractions, Grades 7–9, the OER textbook ingestion pipeline, esports tournaments,
season rewards, password reset, email verification, teacher-created assignments,
platform-admin console. Say so on the Limitations slide — the judging rubric
rewards a focused MVP over a wide half-built one.

## What's still to do for judging (6 October)

1. **You:** run `pytest -q` and `python run_demo.py` on the actual demo laptop, and
   send any failures back to the chat.
2. **You:** test a real Groq key (~2 minutes: put it in `.env`, run
   `ingest_curriculum.py`, send one tutor message).
3. **Next chat (fastest to ask for):** architecture diagram (SVG), 6-slide
   `.pptx`, demo video shot list.
4. **You:** record the 3-minute video (no team/university names in it).
5. **You:** submit the 3 Bootcamp tasks — paste them into the new chat.

## Storyline for judges (don't improvise this)

1. Log in as `student1@demo.jo`. Show the tree with the red root-gap chip on
   Absolute Value; show the "root-cause path" chain.
2. Answer one question wrong. Point at the mistake card + the breadcrumb ("we're
   moving you because…").
3. Log out. Log in as `teacher@demo.jo`. Pick student1. Same chain, plus the
   struggle-alert table.
4. Close by saying: this is Grade-6 integers today; adding fractions or Grade 7 is
   *adding nodes to the graph*, not a rewrite.

Keep the shop and the AI tutor for Q&A, not the main flow.

## Files a new chat should read first

- `README.md` — how to run and what changed.
- `HANDOFF.md` — this file.
- `app/services/session_core.py` — the diagnosis + remediation logic.
- `app/services/engine_bridge.py` — the DB glue around it.
- `app/engine/adaptive_engine.py` — the routing decisions.
- `app/engine/knowledge_graph.py` — the 5 skills and their prerequisites.
- `web/streamlit_app.py` — the whole UI.
- `tests/test_session_core.py`, `tests/test_api.py` — how things are meant to work.

Everything else is either data (`offline_bank.py` — the question templates),
generated (avatar SVG, tree SVG), or plumbing.
