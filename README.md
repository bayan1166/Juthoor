
# Juthoor | جذور

### Find where the learning gap started.

Juthoor is a **general B2C adaptive learning platform** that helps learners understand not only *what* they got wrong, but **where the underlying learning gap most likely started**.

Juthoor combines:

- Adaptive questioning
- Prerequisite-aware learning
- Evidence-first root-gap diagnosis
- Targeted remediation
- Mastery tracking
- Explainable feedback
- Optional AI tutoring

**Student = user. Parent/guardian = buyer.**

Juthoor is **not a school product, teacher product, classroom platform, or school management system**. The current demo content happens to be Grade 6 mathematics, but the product architecture and diagnosis engine are designed to be domain-agnostic.

---

##  Team

**Juthoor — جذور**

Built by:

- **[Bayan Marashdeh]**
- **[Marah Al-Kilani]**
- **[Sadeen Nabab**
- **[Rana Shalout]**

---

#  What problem does Juthoor solve?

A learner can get a question wrong for many different reasons.

The visible mistake may happen in one lesson while the actual learning gap started several prerequisite skills earlier.

Traditional learning systems often stop at:

> “You got this question wrong.”

Juthoor asks a different question:

> **“Where did the difficulty most likely start?”**

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

#  Core workflow

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
````

The product is deliberately **evidence-first**.

A weak signal does not automatically become a diagnosis.

---

# 🔎 Diagnostic engine

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

* failing-skill detection
* prerequisite validation
* root-candidate ranking
* insufficient-evidence states
* confirmation probes
* competing candidates
* likelihood-ratio evidence
* confidence levels
* machine-readable evidence requirements
* explainable diagnosis output

### Diagnostic states

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

# 📊 BKT / Mastery

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

# 🌳 Knowledge graph

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

* unknown prerequisites
* self-loops
* duplicate prerequisites
* cycles

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

---

# AI is optional

The core learning workflow does **not** require an LLM.

AI is optional and can be used for:

* tutor responses
* optional question wording

The core system still works through deterministic/offline components for:

* diagnosis
* adaptive decisions
* question generation
* grading
* mastery updates

External AI failures are handled through controlled fallback behavior.

Supported providers currently include:

```text
OpenAI
Groq
```

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

---

# ⚙️ Architecture

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

### Main layers

**Frontend**

Single-page application served from:

```text
app/static/
```

**Backend**

FastAPI application with:

```text
app/main.py
app/routers/
```

**Adaptive engine**

```text
app/engine/adaptive_engine.py
```

**Diagnosis**

```text
app/engine/diagnosis.py
```

**Knowledge graph**

```text
app/engine/knowledge_graph.py
```

**Persistence**

PostgreSQL + SQLAlchemy.

---

# 🗄️ Persistence & reliability

The application includes:

* PostgreSQL support
* connection pooling
* row locking for learner state
* unique mastery constraints
* database integrity checks
* transactional updates
* answer idempotency receipts
* versioned SQL migrations
* migration ordering validation

Answer submissions support an optional:

```text
request_id
```

Repeated submissions with the same request ID can safely replay the stored response instead of creating duplicate state changes.

---

# Testing

The project currently includes a large automated test suite covering:

* authentication
* authorization
* adaptive workflow
* diagnosis
* mastery/BKT logic
* API contracts
* payment behavior
* data isolation
* knowledge graph integrity
* persistence
* stability
* safety logic
* UI behavior
* financial model
* B2C positioning

Run the backend tests with:

```bash
python -m pytest -q
```

Run the preflight checks with:

```bash
python scripts/preflight.py
```

Run the JavaScript UI tests with:

```bash
cd tests/js
npm test
```

The repository also contains deterministic diagnostic benchmark tooling:

```bash
python scripts/diagnostic_benchmark.py --reps 5
```

---

# Diagnostic benchmark

The repository includes a synthetic benchmark that evaluates the diagnosis engine against learners with known simulated gaps.

Important:

**These are synthetic evaluation results, not real-student accuracy results.**

The project currently does **not** claim that the diagnostic engine has achieved 95% real-world diagnostic accuracy.

Current benchmark results and limitations are documented in:

```text
docs/COMPETITIVE_ADVANTAGE.md
docs/FINAL_B2C_AUDIT.md
```

---

# 🚀 Quick start

## Requirements

```text
Python 3.11+
PostgreSQL 14+
Node 18+ for UI tests
```

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

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

### 4. Start the demo

```bash
python run_demo.py --reset
```

### 5. Open Juthoor

```text
http://localhost:8000/app/
```

---

# 👤 Demo accounts

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

#  Current limitations

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

## جذور | Juthoor

**Adaptive learning that looks beneath the mistake.**
