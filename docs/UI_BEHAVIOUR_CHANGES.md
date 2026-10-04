# UI/UX and behaviour changes (economy removal, parent Child ID, dark mode, root CTA, round pacing, live report)

Scope: the seven requested points only. No change to BKT parameters, `MASTERY_THRESHOLD`, evidence thresholds,
the likelihood-ratio rule, the prerequisite graph or root selection. The synthetic benchmark is identical.

## 1. Coins, gems, wallet and shop removed
- **UI:** the «المتجر» nav item and `/shop` route, `views/shop.js`, the coin/gem pills in the header, the `+coins/+gems`
  chips after a correct answer, `store.addWallet`, the coin/gem/bag icons, the shop CSS and the shop error messages.
  The Pro plan no longer lists «كامل متجر الشخصية». The quota message no longer says «رصيدك».
- **Backend:** answers no longer award coins/gems (`grant_reward` removed; `coins_awarded`/`gems_awarded` removed from
  the answer schema), registration creates no wallet, the bootstrap payload has no `wallet`, esports challenges
  award nothing, and the `/economy/wallet|shop|catalog|purchase|convert` endpoints are gone (404). The avatar
  endpoints (`/economy/avatar`, `options`, `previews`) stay so the avatar still renders; an outfit that used to
  cost coins can be worn only if it was already owned.
- **Database:** nothing dropped. `wallets`, `wallet_transactions`, `shop_items`, `inventory_items` stay as legacy tables.
- **Seed:** the demo seed no longer creates wallets.

## 2. Parent signup requires a Child ID (no orphan parent accounts)
- `app/services/child_link.py`: Child ID = `<handle>-<8-char HMAC tag>` (HMAC-SHA256 of the learner id under
  `JWT_SECRET`). Handles and user ids are public in the community, so they alone cannot link an account.
- `POST /auth/register` with `role=parent`: missing → 400 `child_id_required`; malformed/unknown/not a learner/
  inactive/wrong tag → 400 `child_id_invalid`; learner already has a parent → 409 `child_already_linked`. All checks
  run before any row is written; the learner row is locked (`FOR UPDATE`) and the parent row + `guardian_id` link are
  committed in one transaction.
- `/auth/me` returns `child_id` for learners (null otherwise). The learner sees it in the account menu with a copy
  button; the parent form asks for it and explains where to find it. Student signup (incl. `guardian_email` of an
  existing parent) and login are unchanged.

## 3. Dark mode contrast in the report
- Cause: `.report{background:#fff;color:#10231A}` forced dark text, while the cards/tables/chips inside it use the
  dark-theme surfaces → near-black text on near-black (measured 1.13:1 in Chromium on the old stylesheet).
- Fix: `.report` uses `var(--surface)`/`var(--ink)`; new text tokens `--danger-ink`, `--amber-ink`, `--accent-ink`
  defined for both themes and used for all status/accent text (chips, banners, risk, verdicts, KPI values, flow
  steps, avatar initials); light `--muted` darkened slightly (#5E7667 → #566D5F) to pass AA on `--surface-2`;
  `color-scheme` set per theme; inline hex colours in the printable report replaced by classes; print always uses
  the light tokens. Measured in Chromium after the fix: worst report text contrast 5.01 (light) / 5.97 (dark).

## 4. «ظهر جذر المشكلة»
- Shown only when the backend named a root: in the feedback of the answer whose response contains `diagnosis`
  (status `root_identified`), and in the stepper card while the workflow stage is `root_identified`, `remediation`
  or `retry`. Never for `insufficient_evidence`, never for a masked (Free) workflow, never after `resolved`.
- Clicking it reads `GET …/adaptive/diagnoses` and shows: current problem (origin), root, why (engine explanation +
  evidence counts), confidence (مرتفعة/متوسطة/أولية = High/Medium/Low from `confidence_level`), **current mastery**
  of the root (`outcome.root_mastery` = the engine's `p_mastery`, as a percentage), what happens now (from the live
  outcome), and the competing candidate(s) when there are any.

## 5. Questions above 95 %
- Metric: `StudentState.mastery(skill)` = BKT `p_mastery` (the value stored in `skill_mastery.p_mastery`).
- Where the session stopped: `adaptive_engine.round_over` / `decide_next` close a round after `SESSION_LENGTH` (5)
  answers and the UI then shows «أنهيت الجولة»; mastery itself is confirmed in `_handle_correct` (top difficulty and
  p ≥ 0.85).
- Change (engine, not UI): the round stays open while the current skill is a named root being remediated, not yet
  confirmed mastered, and its `p_mastery` > `REMEDIATION_CONTINUE_P` = 0.95 — for at most `ROUND_EXTENSION` = 3
  extra answers. The next question uses the existing difficulty ladder. Exits: mastery confirmed, a wrong answer
  that drops p to ≤ 0.95, a park, or the cap. Before the first diagnosis nothing changes, so the benchmark is identical.

## 6. The report follows the learner
- `diagnosis_history` adds live fields recomputed on every request: `outcome.root_mastery`, `origin_mastery`,
  `root_status`, `origin_status` (plus the existing answers on the root / retry of the original lesson), and the
  persisted `competing` list (new nullable column `diagnosis_events.competing`, migration `0005`, additive).
- The parent record shows «الحالة الآن» (current mastery of the root, status of the original lesson); the parent view
  re-reads the data when the tab becomes visible again; the learner card is fetched fresh each time it is opened.

## 7. Diagnosis core untouched
`app/engine/diagnosis.py`, `knowledge_graph.py`, BKT and every threshold are unchanged; `test_diagnostic_benchmark.py`
(determinism and the recorded numbers) passes unchanged.

## Verification (build sandbox)
| Check | Result |
|---|---|
| pytest files that run without FastAPI/SQLAlchemy | 574 passed, 2 skipped; 2 failed + 13 files and 1 DB test not run only because fastapi/sqlalchemy/pydantic_settings (and the DB fixtures) are missing |
| Node: judge_smoke / smoke / main_smoke | 11/11, 189/189, 23/23 |
| Browser E2E against the simulated backend (real engine, Chromium) | 26/26 (incl. CTA, live mastery 23 % → 98 %, contrast light 5.01 / dark 5.97) |
| `scripts/verify_*_sql.sh` on PostgreSQL 16 (migrations incl. 0005, integrity, state creation, locking) | all pass |
| Static check (undefined names, unused imports, import resolution), `compileall` | no problems |
| ruff (E4, E7, E9, F) | no new findings (same 79 pre-existing as before this change) |
| Full `python -m pytest -q` on PostgreSQL, `scripts/preflight.py`, DB browser E2E | **not run here** (no FastAPI/SQLAlchemy in the sandbox) |
