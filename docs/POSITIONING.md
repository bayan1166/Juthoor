# Product positioning (locked)

**Juthoor | جذور — a learning platform that finds where the gap started.**

Juthoor is a GENERAL adaptive-learning platform built around one mechanism:
adaptive learning + prerequisite-gap detection + evidence-first root diagnosis + targeted remediation + mastery.

It is **not** a mathematics platform, **not** a Grade 6 platform, **not** a school platform and **not** a teacher platform.

## The problem it solves
A student can know that the current question is hard without knowing which earlier concept is causing the difficulty.
A mark says where the mistake appeared, not where the gap started. Juthoor finds the likely root and guides the student back to it.

## Core journey (valid for any subject, grade or curriculum)
Learn → struggle / make mistakes → gather evidence → inspect prerequisites → identify the likely root (or say
"insufficient evidence yet") → targeted remediation → retry the original skill → mastery update.

## What we compete on
Prerequisite-aware diagnosis, explainable evidence, honest ordinal confidence, an explicit insufficient-evidence state,
targeted remediation, return to the original skill and a mastery update. We do **not** compete on more lessons, more subjects,
cheaper content or "better tutoring".

## Business model
B2C only. Student = user. Parent/guardian = economic buyer. Free 0 JOD, Pro monthly 4.50 JOD, Pro academic year 32 JOD
(a floor price hypothesis, not proven willingness to pay). There is no teacher or school product: no teacher or school
accounts, dashboards, classrooms, seats, billing or checkout. Independent subject experts may review diagnoses blindly in a
validation study (outside the product), and parent communities are the acquisition channel.

## Current content
The Grade 6 mathematics curriculum (integers and fractions, 9 live lessons of 18) is the **current demo/seed content**.
It is kept because the MVP runs on it. It is described as data (`app/engine/config.py` → `COURSE`, exposed as `course`
in `/curriculum/map` and the tree payload) and the UI shows it only as content metadata ("المحتوى الحالي: …").
The product shell (landing, navigation, plans, parent screens, empty states) never hard-codes a subject or grade;
`tests/test_positioning.py` enforces this.

## Known limits of the generalisation (honest)
- The question bank, misconception catalogue and the tutor's topic guardrail are specific to the current content pack;
  a new subject needs its own bank, graph and keyword list (the diagnosis engine itself does not change).
- Only one content pack exists; there is no content switcher yet because there is nothing to switch to.
- Users still carry a `grade_level` field whose default comes from the current content (`COURSE["grade"]`).
