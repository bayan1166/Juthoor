"""The diagnosis record follows the learner: what was decided stays, what is true *now* is recomputed.

Through HTTP -> FastAPI -> database -> engine. The record returned by /adaptive/diagnoses (shown on the learner's
"root found" card) and by /adaptive/report (the parent report) carries the live BKT mastery of the root and the
original lesson, their current status, and the competing candidates persisted with the diagnosis.
"""
import uuid

from sqlalchemy import select

from app.models.adaptive import DiagnosisEvent
from app.models.org import User
from scripts import seed_demo
from tests.helpers import register, register_parent, set_plan
from tests.test_core_workflow import answer, correct_answer, diagnose, question


def _story(client, db):
    s = register(client)
    parent = register_parent(client, s)
    set_plan(db, s["id"], "pro")
    seed_demo.prepare_story_student(db, db.get(User, uuid.UUID(s["id"])), "mult_div_integers")
    return s, parent


def _record(client, s, who):
    body = client.get(f"/students/{s['id']}/adaptive/diagnoses", headers=who["headers"]).json()
    assert body["locked"] is False and body["diagnoses"]
    return body["diagnoses"][0]


def test_the_record_carries_live_mastery_and_the_persisted_competing_candidates(client, db):
    s, parent = _story(client, db)
    found, _ = diagnose(client, db, s)
    rec = _record(client, s, s)
    assert rec["root_skill"] == found["diagnosis"]["root"] and rec["origin_skill"] == found["diagnosis"]["origin"]
    o = rec["outcome"]
    assert o["root_status"] == "gap" and o["origin_status"] in {"learning", "untouched"}
    assert 0 < o["root_mastery"] < 0.85, "a fresh root is far from mastered"
    state = client.get(f"/students/{s['id']}/adaptive/state", headers=s["headers"]).json()
    live = {k["skill_id"]: k["p_mastery"] for k in state["skills"]}
    assert o["root_mastery"] == live[rec["root_skill"]], "the same p_mastery the engine uses, not a separate percentage"
    db.expire_all()
    event = db.scalar(select(DiagnosisEvent).where(DiagnosisEvent.student_id == uuid.UUID(s["id"])))
    assert event.competing == list(found["diagnosis"]["competing"])
    assert rec["competing"] == [{"skill": c, "name_ar": rec["competing"][i]["name_ar"]} for i, c in enumerate(event.competing)]
    assert _record(client, s, parent)["outcome"] == o, "the parent sees the same live record"


def test_the_record_changes_as_the_learner_recovers(client, db):
    s, parent = _story(client, db)
    diagnose(client, db, s)
    first = _record(client, s, parent)["outcome"]
    seen = [first]
    for _ in range(40):
        question(client, s)
        r = answer(client, s, correct_answer(db, s)).json()
        if r["round_over"]:
            client.post(f"/students/{s['id']}/adaptive/round", headers=s["headers"])
        seen.append(_record(client, s, parent)["outcome"])
        if seen[-1]["origin_status"] == "mastered":
            break
    last = seen[-1]
    assert last["root_mastery"] > first["root_mastery"], "mastery of the root rose after correct answers"
    assert first["stage"] in {"pending", "remediating"} and last["stage"] == "resolved"
    assert last["root_status"] == "mastered" and last["origin_status"] == "mastered"
    assert last["root_after"]["right"] > first["root_after"]["right"] and last["origin_retry"]["right"] >= 1
    # the in-between state "root firm, original lesson not yet" was reported on the way
    assert any(o["root_status"] == "mastered" and o["origin_status"] != "mastered" for o in seen)
    report = client.get(f"/students/{s['id']}/adaptive/report", headers=parent["headers"]).json()
    assert report["diagnoses"][0]["outcome"] == last
