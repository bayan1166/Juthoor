> **Historical / internal document.** Written before the locked positioning. Where it describes teachers, schools, classrooms, a school pilot or Juthoor as a Grade 6 mathematics product, it is superseded: Juthoor is a general B2C learning platform (student = user, parent = buyer) and Grade 6 mathematics is only the current demo content. Educators appear only as internal reviewers. Current reference: `docs/POSITIONING.md`.

# 11 - Competitive advantage and teacher view

**Status: DONE for learner; teacher-view extras NOT DONE**

## Objective
Make the evidence-first diagnosis a visible, measurable differentiator.

## Current problem (before this work)
The product's differentiator was described in prose but not demonstrable (no abstention, no 'what would settle it', no measurement).

## Required implementation
- Evidence-first diagnosis implemented (tasks 02 and 04).
- `evidence_needed` returned in every answer and shown to the learner.
- `docs/COMPETITIVE_ADVANTAGE.md` states the claim, the measurement and the limits.

## Files affected
- docs/COMPETITIVE_ADVANTAGE.md
- app/static/js/views/practice.js
- tests/js/smoke.mjs
- tests/js/fixtures/omar_flow.json

## Tests required
- tests/js/smoke.mjs (new check: learner sees what would settle the diagnosis)

## Acceptance criteria
- Measured on the benchmark; demoable in the UI

## Actual result
Done for the learner view. The teacher drawer already shows evidence, path, confidence and outcome; it does **not** show the likelihood ratio or `evidence_needed` because those are not persisted with the diagnosis event - not done.

## Status
DONE for learner; teacher-view extras NOT DONE

## Evidence
- tests/js/smoke.mjs 179/179
- docs/COMPETITIVE_ADVANTAGE.md
