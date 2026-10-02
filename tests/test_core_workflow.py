"""End-to-end scenarios for the core workflow, through HTTP -> FastAPI -> database -> engine.

Learner attempts a skill -> difficulty -> evidence -> prerequisite investigation -> named root
with evidence and confidence -> remediation -> retry of the original lesson -> mastery update
-> teacher sees the diagnosis and its outcome.

Scenario letters match the README "Testing" table. Nothing here is mocked except where a test
deliberately breaks a dependency (AI provider, database) to check graceful failure.
"""
import uuid

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models.adaptive import AttemptLog, DiagnosisEvent, SkillMastery, StudentAdaptiveState
from app.models.org import User
from scripts import seed_demo
from tests.helpers import register


def misconception_answer(db, s) -> str:
    """A realistic wrong answer: one the question bank links to a named misconception
    (e.g. answering 28 to -4 x 7, "ignored the sign rule"), never a nonsense string."""
    db.expire_all()
    pending = db.get(StudentAdaptiveState, uuid.UUID(s["id"])).pending_question
    traps = pending.get("traps") or {}
    assert traps, f"question without a misconception-linked wrong answer: {pending['question']}"
    return next(iter(traps))


def teacher_with_class(client):
    teacher = register(client, "teacher")
    room = client.post("/classrooms", json={"name": "Class A"}, headers=teacher["headers"])
    assert room.status_code == 200, room.text
    return teacher, room.json()


def join(client, student, room):
    r = client.post("/classrooms/join", json={"join_code": room["join_code"]}, headers=student["headers"])
    assert r.status_code == 200, r.text


def question(client, s):
    r = client.get(f"/students/{s['id']}/adaptive/question", headers=s["headers"])
    assert r.status_code == 200, r.text
    return r.json()


def answer(client, s, selected):
    return client.post(f"/students/{s['id']}/adaptive/answer", json={"selected_answer": selected}, headers=s["headers"])


def correct_answer(db, s):
    db.expire_all()
    return db.get(StudentAdaptiveState, uuid.UUID(s["id"])).pending_question["correct_answer"]


def play(client, db, s, ok: bool) -> dict:
    question(client, s)
    r = answer(client, s, correct_answer(db, s) if ok else misconception_answer(db, s))
    assert r.status_code == 200, r.text
    body = r.json()
    if body["round_over"]:
        assert client.post(f"/students/{s['id']}/adaptive/round", headers=s["headers"]).status_code == 200
    return body


@pytest.fixture
def omar(client, db):
    """A class member who has really mastered the first two lessons, now placed on multiplication."""
    teacher, room = teacher_with_class(client)
    s = register(client)
    join(client, s, room)
    user = db.get(User, uuid.UUID(s["id"]))
    seed_demo.prepare_story_student(db, user, "mult_div_integers")
    return {"student": s, "teacher": teacher, "room": room}


def diagnose(client, db, s, limit=15):
    history = []
    for _ in range(limit):
        body = play(client, db, s, ok=False)
        history.append(body)
        if body["diagnosis"]:
            return body, history
    raise AssertionError([h["action"] for h in history])


# --- A: normal successful learner flow --------------------------------------------------

def test_a_correct_answers_progress_without_any_gap(client, db, student):
    actions = [play(client, db, student, ok=True) for _ in range(6)]
    assert all(a["is_correct"] and a["evidence_status"] is None and a["diagnosis"] is None for a in actions)
    assert "level_up" in {a["action"] for a in actions}
    state = client.get(f"/students/{student['id']}/adaptive/state", headers=student["headers"]).json()
    assert not [s for s in state["skills"] if s["status"] == "gap"]
    assert any(s["status"] == "mastered" for s in state["skills"])


# --- B: one wrong answer is recorded as evidence, not as a diagnosis ---------------------

def test_b_a_wrong_answer_updates_evidence_and_names_the_misconception(client, db, omar):
    s = omar["student"]
    sid = uuid.UUID(s["id"])
    db.expire_all()
    before = db.scalar(select(SkillMastery).where(SkillMastery.student_id == sid,
                                                  SkillMastery.skill_id == "mult_div_integers"))
    p_before = before.p_mastery if before else 0.3
    body = play(client, db, s, ok=False)
    assert body["is_correct"] is False and body["misconception"], "the misconception behind the answer is named"
    assert body["diagnosis"] is None and body["new_gaps"] == []
    assert body["evidence_status"]["status"] == "insufficient_evidence"
    assert body["evidence_status"]["reason"] in {"too_few_errors", "prerequisites_unverified"}
    db.expire_all()
    row = db.scalar(select(SkillMastery).where(SkillMastery.student_id == sid, SkillMastery.skill_id == "mult_div_integers"))
    assert row.attempts >= 1 and row.p_mastery < p_before
    log = db.scalar(select(AttemptLog).where(AttemptLog.student_id == sid).order_by(AttemptLog.created_at.desc()))
    assert log.is_correct is False and log.misconception and log.skill_id == "mult_div_integers"


# --- B, C, D: difficulty -> evidence -> prerequisite investigation -> named root --------

def test_bcd_wrong_answers_gather_evidence_before_naming_the_root(client, db, omar):
    s = omar["student"]
    found, history = diagnose(client, db, s)
    before = history[:-1]
    assert before and all(h["evidence_status"]["status"] == "insufficient_evidence" for h in before)
    assert all(h["evidence_status"]["message"] for h in before)
    assert any(h["evidence_status"].get("confirming") == "adding_integers" for h in before)
    assert any(h["action"] == "backtrack" for h in history)
    probed = db.scalars(select(AttemptLog.skill_id).where(AttemptLog.student_id == uuid.UUID(s["id"]))
                        .where(AttemptLog.remedial_stage != "")).all()
    assert {"subtracting_integers", "adding_integers"} <= set(probed), "prerequisites were probed with questions"
    assert all(h["misconception"] for h in history), "every wrong answer carries its misconception"

    diag = found["diagnosis"]
    assert diag["origin"] == "mult_div_integers" and diag["root"] == "adding_integers"
    assert diag["path"] == ["mult_div_integers", "subtracting_integers", "adding_integers"]
    assert diag["confidence_level"] in {"medium", "high"} and diag["explanation"] and diag["intervention"]
    rows = {e["skill"]: e for e in diag["evidence"]}
    assert rows["adding_integers"]["wrong"] >= 2 and rows["comparing_integers"]["right"] >= 1
    assert found["gap_skill"] == "adding_integers" and found["new_gaps"] == ["adding_integers"]
    assert 5 <= len(history) <= 8

    # H: targeted remediation is assigned on the root, with the intervention in the banner.
    nxt = question(client, s)
    assert nxt["skill"] == "adding_integers" and nxt["difficulty"] == 1
    assert "جمع الأعداد الصحيحة" in nxt["banner"]


# --- E: correct answers after remediation, retry of the original lesson -----------------

def test_e_remediation_then_retry_updates_mastery_and_teacher_outcome(client, db, omar):
    s, teacher = omar["student"], omar["teacher"]
    diagnose(client, db, s)
    asked = []
    for _ in range(40):
        q = question(client, s)
        asked.append(q["skill"])
        r = answer(client, s, correct_answer(db, s)).json()
        if r["round_over"]:
            client.post(f"/students/{s['id']}/adaptive/round", headers=s["headers"])
        state = client.get(f"/students/{s['id']}/adaptive/state", headers=s["headers"]).json()
        status = {k["skill_id"]: k["status"] for k in state["skills"]}
        if status["mult_div_integers"] == "mastered":
            break
    assert asked[0] == "adding_integers", "remediation starts on the named root"
    assert "mult_div_integers" in asked, "the original lesson is retried"
    assert status["adding_integers"] == "mastered" and status["mult_div_integers"] == "mastered"

    report = client.get(f"/students/{s['id']}/adaptive/report", headers=teacher["headers"]).json()
    record = report["diagnoses"][0]
    assert record["root_skill"] == "adding_integers" and record["outcome"]["stage"] == "resolved"
    assert record["outcome"]["root_after"]["right"] >= 1 and record["outcome"]["origin_retry"]["right"] >= 1


# --- F: wrong answers after remediation ---------------------------------------------------

def test_f_wrong_answers_during_remediation_keep_the_gap_without_duplicate_diagnoses(client, db, omar):
    s = omar["student"]
    diagnose(client, db, s)
    for _ in range(4):
        body = play(client, db, s, ok=False)
        assert body["diagnosis"] is None
    count = db.scalar(select(func.count(DiagnosisEvent.id)).where(DiagnosisEvent.student_id == uuid.UUID(s["id"])))
    assert count == 1
    state = client.get(f"/students/{s['id']}/adaptive/state", headers=s["headers"]).json()
    status = {k["skill_id"]: k["status"] for k in state["skills"]}
    assert status["adding_integers"] in {"gap", "parked"}


# --- G: AI unavailable --------------------------------------------------------------------

class _BrokenCompletions:
    def create(self, **_):
        raise TimeoutError("provider down")


class _BrokenClient:
    chat = type("Chat", (), {"completions": _BrokenCompletions()})()


def test_g_questions_and_diagnosis_work_when_the_ai_provider_fails(client, db, omar, monkeypatch):
    from app.engine import llm_remediation
    monkeypatch.setattr(llm_remediation, "_get_client", lambda: ("openai", _BrokenClient()))
    found, _ = diagnose(client, db, omar["student"])
    assert found["diagnosis"]["root"] == "adding_integers"
    sources = set(db.scalars(select(AttemptLog.source).where(AttemptLog.student_id == uuid.UUID(omar["student"]["id"]))))
    assert "llm" not in sources


# --- K/24: persistence across a restart, then the retry continues ------------------------

def test_persistence_survives_restart_and_the_retry_continues(client, db, omar, session_factory):
    s = omar["student"]
    sid = uuid.UUID(s["id"])
    diagnose(client, db, s)

    # Simulate a server restart: drop every pooled connection and use a brand-new client.
    db.close()
    session_factory.kw["bind"].dispose()
    from fastapi.testclient import TestClient
    fresh_client = TestClient(app)
    fresh = session_factory()
    try:
        ev = fresh.scalar(select(DiagnosisEvent).where(DiagnosisEvent.student_id == sid))
        assert ev.root_skill == "adding_integers" and ev.explanation and ev.confidence_level in {"medium", "high"}
        assert isinstance(ev.evidence, list) and ev.path[-1] == "adding_integers"
        row = fresh.get(StudentAdaptiveState, sid)
        assert row.current_skill == "adding_integers" and "mult_div_integers" in row.return_stack
        gap = fresh.scalar(select(SkillMastery).where(SkillMastery.student_id == sid, SkillMastery.skill_id == "adding_integers"))
        assert gap.status.value == "gap" and gap.attempts >= 2

        # Continue the retry from the reloaded state.
        state = fresh_client.get(f"/students/{s['id']}/adaptive/state", headers=s["headers"]).json()
        assert {k["skill_id"]: k["status"] for k in state["skills"]}["adding_integers"] == "gap"
        for _ in range(40):
            fresh_client.get(f"/students/{s['id']}/adaptive/question", headers=s["headers"])
            r = fresh_client.post(f"/students/{s['id']}/adaptive/answer",
                                  json={"selected_answer": correct_answer(fresh, s)}, headers=s["headers"]).json()
            if r["round_over"]:
                fresh_client.post(f"/students/{s['id']}/adaptive/round", headers=s["headers"])
            fresh.expire_all()
            if fresh.scalar(select(SkillMastery.status).where(SkillMastery.student_id == sid,
                                                              SkillMastery.skill_id == "mult_div_integers")).value == "mastered":
                break
        statuses = dict(fresh.execute(select(SkillMastery.skill_id, SkillMastery.status)
                                      .where(SkillMastery.student_id == sid)).all())
        assert statuses["adding_integers"].value == "mastered" and statuses["mult_div_integers"].value == "mastered"
    finally:
        fresh.close()


# --- I: teacher views the diagnosis; access control ---------------------------------------

def test_i_teacher_sees_evidence_and_others_cannot(client, db, omar):
    s, teacher = omar["student"], omar["teacher"]
    diagnose(client, db, s)
    r = client.get(f"/students/{s['id']}/adaptive/diagnoses", headers=teacher["headers"])
    assert r.status_code == 200 and not r.json()["locked"]
    record = r.json()["diagnoses"][0]
    assert record["root_name_ar"] and record["explanation"] and record["intervention"]
    assert record["evidence"] and all("name_ar" in e for e in record["evidence"])
    assert record["outcome"]["stage"] in {"pending", "remediating"}

    analytics = client.get(f"/classrooms/{omar['room']['classroom_id']}/analytics", headers=teacher["headers"]).json()
    row = next(x for x in analytics["students"] if x["user_id"] == s["id"])
    assert row["root_gap_ids"] == ["adding_integers"]

    insights = client.get(f"/students/{s['id']}/insights", headers=teacher["headers"]).json()
    causes = {a["skill_id"]: a["predicted_root_cause_skill"] for a in insights["struggle_alerts"]}
    assert causes.get("adding_integers") == "adding_integers"

    stranger_teacher = register(client, "teacher")
    other_student = register(client)
    assert client.get(f"/students/{s['id']}/adaptive/diagnoses", headers=stranger_teacher["headers"]).status_code == 403
    assert client.get(f"/students/{s['id']}/adaptive/diagnoses", headers=other_student["headers"]).status_code == 403
    assert client.get(f"/students/{s['id']}/adaptive/diagnoses").status_code in {401, 403}


# --- J: repeated execution and refresh ----------------------------------------------------

def test_j_refreshing_the_question_never_breaks_grading(client, db, student):
    question(client, student)
    question(client, student)
    r = answer(client, student, correct_answer(db, student))
    assert r.status_code == 200 and r.json()["is_correct"] is True
    assert answer(client, student, "1").status_code == 409


def test_j_two_learners_with_the_same_history_get_the_same_root(client, db):
    roots = []
    for _ in range(2):
        teacher, room = teacher_with_class(client)
        s = register(client)
        join(client, s, room)
        seed_demo.prepare_story_student(db, db.get(User, uuid.UUID(s["id"])), "mult_div_integers")
        roots.append(diagnose(client, db, s)[0]["diagnosis"]["root"])
    assert roots == ["adding_integers", "adding_integers"]


# --- K: invalid inputs and errors fail safely ---------------------------------------------

@pytest.mark.parametrize("payload, code", [
    ({"selected_answer": ""}, 422),
    ({"selected_answer": "x" * 201}, 422),
    ({}, 422),
    ({"selected_answer": None}, 422),
])
def test_k_invalid_answers_are_rejected_without_side_effects(client, db, student, payload, code):
    question(client, student)
    r = client.post(f"/students/{student['id']}/adaptive/answer", json=payload, headers=student["headers"])
    assert r.status_code == code
    db.expire_all()
    assert db.get(StudentAdaptiveState, uuid.UUID(student["id"])).pending_question is not None


def test_k_garbage_text_is_just_a_wrong_answer(client, db, student):
    question(client, student)
    r = answer(client, student, "<script>alert(1)</script> ١٢ ∅")
    assert r.status_code == 200 and r.json()["is_correct"] is False


def test_k_bad_identity_and_ids_are_rejected_cleanly(client, student):
    other = register(client)
    assert client.get(f"/students/{other['id']}/adaptive/question", headers=student["headers"]).status_code == 403
    assert client.get("/students/not-a-uuid/adaptive/state", headers=student["headers"]).status_code == 422
    assert client.get(f"/students/{student['id']}/adaptive/state",
                      headers={"Authorization": "Bearer not.a.token"}).status_code == 401
    missing = uuid.uuid4()
    assert client.get(f"/students/{missing}/adaptive/state", headers=student["headers"]).status_code == 403


def test_k_database_outage_returns_a_clean_503(client, tmp_path):
    broken = create_engine(f"sqlite:///{tmp_path}/missing-dir/nope.db")
    Broken = sessionmaker(bind=broken)

    def broken_db():
        s = Broken()
        try:
            yield s
        finally:
            s.close()

    previous = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = broken_db
    try:
        r = client.post("/auth/login", json={"email": "a@b.com", "password": "secret123"})
    finally:
        app.dependency_overrides[get_db] = previous
    assert r.status_code == 503 and r.json() == {"detail": "database_unavailable"}
    assert "Traceback" not in r.text


# --- N: missing learner / unknown skill / stale state -------------------------------------

def test_n_missing_learner_is_a_controlled_error(client, omar):
    teacher = omar["teacher"]
    ghost = uuid.uuid4()
    for path in ("diagnoses", "state", "report", "tree"):
        r = client.get(f"/students/{ghost}/adaptive/{path}", headers=teacher["headers"])
        assert r.status_code in {403, 404} and "detail" in r.json()


def test_n_stale_state_with_unknown_skills_is_repaired_not_crashed(client, db, student):
    sid = uuid.UUID(student["id"])
    question(client, student)
    row = db.get(StudentAdaptiveState, sid)
    row.current_skill = "removed_skill"
    row.difficulty = 99
    row.return_stack = ["removed_skill", "adding_integers"]
    row.pending_question = {**row.pending_question, "skill": "removed_skill"}
    row.remediation_plan = {"stage": "easier", "skill": "removed_skill", "difficulty": 1, "pattern": "x", "stack": []}
    db.add(SkillMastery(student_id=sid, skill_id="removed_skill", attempts=3, correct=0))
    db.commit()

    state = client.get(f"/students/{student['id']}/adaptive/state", headers=student["headers"])
    assert state.status_code == 200 and state.json()["current_skill"] == "absolute_value"
    assert answer(client, student, "1").status_code == 409, "stale pending question is discarded"
    q = question(client, student)
    assert q["skill"] in {"absolute_value"} and 1 <= q["difficulty"] <= 3
    assert answer(client, student, "1").status_code == 200


# --- Q: AI unavailable in the tutor -------------------------------------------------------

def test_q_tutor_falls_back_offline_when_the_provider_fails(client, student, monkeypatch):
    from app.services.rag import socratic
    monkeypatch.setattr(socratic, "_client", lambda: ("openai", _BrokenClient()))
    socratic.BREAKER.success()
    base = f"/students/{student['id']}/chat"
    sid = client.post(f"{base}/start", json={"skill_context": "adding_integers"}, headers=student["headers"]).json()["session_id"]
    r = client.post(f"{base}/message", json={"session_id": sid, "message": "5 + (-2)"}, headers=student["headers"])
    assert r.status_code == 200 and r.json()["reply"] and r.json()["source"] in {"solver", "tutor"}


# --- R: a database failure in the middle of an answer leaves no partial state ------------

def test_r_failure_mid_answer_rolls_back_and_the_answer_can_be_resent(client, db, student, monkeypatch):
    from sqlalchemy.exc import OperationalError
    from app.services import engine_bridge
    sid = uuid.UUID(student["id"])
    question(client, student)
    right = correct_answer(db, student)
    db.expire_all()
    before = db.get(StudentAdaptiveState, sid).total_answered

    def down(*_, **__):
        raise OperationalError("UPDATE wallets", {}, Exception("connection lost"))

    monkeypatch.setattr(engine_bridge, "grant_reward", down)
    r = answer(client, student, right)
    assert r.status_code == 503 and r.json() == {"detail": "database_unavailable"}
    db.expire_all()
    row = db.get(StudentAdaptiveState, sid)
    assert row.total_answered == before and row.pending_question is not None, "nothing half-written"
    assert db.scalar(select(func.count(AttemptLog.id)).where(AttemptLog.student_id == sid)) == 0

    monkeypatch.undo()
    r = answer(client, student, right)
    assert r.status_code == 200 and r.json()["is_correct"] is True
    db.expire_all()
    assert db.get(StudentAdaptiveState, sid).total_answered == before + 1
