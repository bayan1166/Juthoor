# Juthoor | جذور

### Find where the learning gap started.

Juthoor is a **general B2C adaptive learning platform** that helps learners understand not only *what* they got wrong, but **where the underlying learning gap most likely started**.

Juthoor combines:

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

### Important

**These are synthetic evaluation results, not real-student accuracy results.**

The project currently does **not** claim that the diagnostic engine has achieved a specific real-world diagnostic accuracy percentage.

Current benchmark results and limitations are documented in:

```text
docs/COMPETITIVE_ADVANTAGE.md
docs/FINAL_B2C_AUDIT.md
```

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
