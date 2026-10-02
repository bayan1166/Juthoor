# 09 - API contract tests and AI-tutor evaluation

**Status: TUTOR EVAL DONE; API CONTRACTS BLOCKED**

## Objective
Contract tests for the API; an offline evaluation of the tutor's scope, safety and no-crash behaviour.

## Current problem (before this work)
API error shapes and malformed payload handling were only partly tested; the tutor had a small on/off-topic list and no fuzzing.

## Required implementation
- `tests/test_api_contracts.py` (schema validation, malformed/oversized payloads, error shape, tokens).
- `tests/test_tutor_eval.py`: off-topic and prompt-injection sets, on-topic set, hostile-input and seeded fuzz (no crash), contact/link filter, offline solver vs Python `eval` on 400 random expressions, linear-time check.
- Fix found by the evaluation: the e-mail pattern in `chat_safety` backtracked quadratically (4.6 s on a 20,000-character message); now bounded and guarded.

## Files affected
- tests/test_api_contracts.py
- tests/test_tutor_eval.py
- app/services/chat_safety.py

## Tests required
- tests/test_tutor_eval.py
- tests/test_api_contracts.py

## Acceptance criteria
- No crash on hostile input
- Solver correct vs Python on random integer expressions
- Every real bug has a regression test

## Actual result
Tutor evaluation: all 40+ tests pass (runs without the app). The ReDoS-style defect is fixed with a regression test (`test_safety_filter_is_linear_time_on_hostile_input`). The API caps chat messages at 1,000 characters, so real exposure was limited. `tests/test_api_contracts.py` is written but **BLOCKED**. Provider-failure fallback of `socratic` is covered by the existing `tests/test_guardrail.py`, which needs the full environment and was **not run** here. The guardrail remains keyword-based.

## Status
TUTOR EVAL DONE; API CONTRACTS BLOCKED

## Evidence
- tests/test_tutor_eval.py passes
- `tests/test_api_contracts.py` ast-checked only
- Team machine: 765 passed, 1 failed - the API contract test wrongly required options on `type=input` questions. Fixed by type-aware invariants and `tests/test_question_contract.py` (bank-wide, pure, 8 passing). Production code unchanged because `input` with `options=[]` is the designed behaviour.
