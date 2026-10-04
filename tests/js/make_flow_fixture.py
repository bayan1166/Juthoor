"""Record real engine payloads for the UI replay tests (tests/js/smoke.mjs).

omar_flow.json      wrong answers (misconception-linked distractors) until the root is named
omar_recovery.json  correct answers through remediation, the retry of the original lesson and
                    the mastery update, until the workflow reaches "resolved"

Every payload is produced by the real session code (app/services/session_core.py) and the real
workflow stage (app/services/workflow.py); only the HTTP/database layer is absent.
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.engine import adaptive_engine as ae
from app.services import session_core as sc
from app.services import workflow as wf

SEED = 5
BASICS = {"absolute_value", "comparing_integers"}
QUESTION_KEYS = ("question", "hint", "skill", "difficulty", "pattern", "type", "options", "remedial", "banner",
                 "skill_name", "source", "guided")


def wrong_for(q):
    """A realistic mistake: an answer the bank links to a named misconception."""
    trap = next(iter(q["traps"]))
    if q["type"] == "input":
        return trap
    from app.engine import offline_bank as ob
    return next(o for o in q["options"] if ob.norm(o) == trap)


def _step(sess, rng, answer_for, latest):
    q = sc.serve(sess, rng)
    answer = answer_for(q)
    before = set(sess.state.gaps)
    result = sc.grade(sess, answer)
    result.pop("events", None)
    result.pop("engine_action", None)
    found = sorted(set(sess.state.gaps) - before)
    if result["diagnosis"]:
        d = result["diagnosis"]
        latest = {"origin": d["origin"], "root": d["root"], "confidence": d["confidence"]}
    result.update(new_gaps=found, gap_locked=False, remaining_questions=None,
                  workflow=wf.workflow(sess.state, latest, result, q["skill"]))
    question = {k: q.get(k) for k in QUESTION_KEYS}
    if result["round_over"]:
        sc.new_round(sess)
    return {"question": question, "answer": answer, "wrong": answer, "result": result}, latest


def record(limit=60):
    rng = random.Random(SEED)
    state = ae.StudentState(current_skill="mult_div_integers", difficulty=1)
    state.mastered.update(BASICS)
    sess = sc.Session(state=state)
    latest = None
    flow, recovery = [], []
    for _ in range(limit):
        step, latest = _step(sess, rng, wrong_for, latest)
        flow.append(step)
        if step["result"]["diagnosis"]:
            break
    for _ in range(limit):
        step, latest = _step(sess, rng, lambda q: q["correct_answer"], latest)
        recovery.append(step)
        if step["result"]["workflow"]["stage"] == "resolved":
            break
    return flow, recovery


if __name__ == "__main__":
    flow, recovery = record()
    out = Path(__file__).resolve().parent / "fixtures"
    (out / "omar_flow.json").write_text(json.dumps(flow, ensure_ascii=False, default=str), encoding="utf-8")
    (out / "omar_recovery.json").write_text(json.dumps(recovery, ensure_ascii=False, default=str), encoding="utf-8")
    last = flow[-1]["result"]["diagnosis"]
    stages = []
    for s in recovery:
        stage = s["result"]["workflow"]["stage"]
        if not stages or stages[-1] != stage:
            stages.append(stage)
    print(f"recorded {len(flow)} wrong answers; root={last['root']} path={last['path']}")
    print(f"recorded {len(recovery)} recovery answers; stages={stages}")
