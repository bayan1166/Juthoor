"""API contract tests: request validation, response shape, auth and malformed input.

Responses are validated against the declared Pydantic models (not just the status code), and every
error body must be JSON with a ``detail``. No endpoint may answer a client mistake with a 500.
"""
import json
import uuid

import pytest

from app.schemas.adaptive import DecisionOut, QuestionOut, StudentStateOut
from app.schemas.auth import MeOut, TokenResponse
from tests.helpers import register

BASE = "/students/{id}/adaptive"


def _reg(client, **over):
    body = {"email": f"{uuid.uuid4().hex[:10]}@test.com", "password": "secret123", "full_name": "Test User", **over}
    return client.post("/auth/register", json=body)


def _assert_error_shape(r):
    assert r.status_code < 500, (r.status_code, r.text)
    assert r.headers["content-type"].startswith("application/json")
    assert "detail" in r.json()


# --- auth ---------------------------------------------------------------------------------------

def test_register_and_login_responses_match_their_schema(client):
    r = _reg(client)
    assert r.status_code == 200
    token = TokenResponse.model_validate(r.json())
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token.access_token}"})
    assert me.status_code == 200
    MeOut.model_validate(me.json())
    body = json.loads(r.request.content)
    login = client.post("/auth/login", json={"email": body["email"], "password": "secret123"})
    TokenResponse.model_validate(login.json())


@pytest.mark.parametrize("patch", [
    {"email": "not-an-email"}, {"password": "123"}, {"password": "x" * 129}, {"full_name": ""}, {"full_name": "   "},
    {"full_name": "n" * 151}, {"grade_level": 0}, {"grade_level": 13}, {"grade_level": "six"}, {"role": "wizard"},
    {"role": "platform_admin"}, {"role": "teacher"}, {"role": "org_admin"}, {"gender": "other"}, {"email": 12345},
])
def test_register_rejects_invalid_fields(client, patch):
    r = _reg(client, **patch)
    assert r.status_code == 422, (patch, r.text)
    _assert_error_shape(r)


@pytest.mark.parametrize("missing", ["email", "password", "full_name"])
def test_register_requires_its_mandatory_fields(client, missing):
    body = {"email": f"{uuid.uuid4().hex[:10]}@test.com", "password": "secret123", "full_name": "T"}
    body.pop(missing)
    r = client.post("/auth/register", json=body)
    assert r.status_code == 422
    _assert_error_shape(r)


@pytest.mark.parametrize("raw", ["{", "[]", "null", "\"text\"", "", "{'a': 1}"])
def test_malformed_json_bodies_are_client_errors_not_server_errors(client, raw):
    r = client.post("/auth/register", content=raw, headers={"Content-Type": "application/json"})
    assert r.status_code in (400, 422)
    _assert_error_shape(r)


def test_duplicate_email_is_a_conflict(client):
    first = _reg(client)
    email = json.loads(first.request.content)["email"]
    r = _reg(client, email=email)
    assert r.status_code == 409 and r.json()["detail"] == "email_already_registered"


def test_wrong_credentials_do_not_reveal_whether_the_account_exists(client):
    s = register(client)
    wrong_pw = client.post("/auth/login", json={"email": s["email"], "password": "bad-password"})
    no_user = client.post("/auth/login", json={"email": "nobody@test.com", "password": "bad-password"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()


@pytest.mark.parametrize("headers", [
    {}, {"Authorization": "Bearer"}, {"Authorization": "Bearer not.a.jwt"}, {"Authorization": "Basic abc"},
    {"Authorization": "Bearer " + "a" * 5000},
])
def test_protected_endpoints_refuse_missing_or_bad_tokens(client, headers):
    r = client.get("/auth/me", headers=headers)
    assert r.status_code in (401, 403)
    _assert_error_shape(r)


# --- adaptive question / answer -----------------------------------------------------------------

QUESTION_TYPES = {"mcq", "tf", "input"}


def _assert_question_contract(qo):
    """Invariants of a served question, by type (the bank-wide version is tests/test_question_contract.py).

    mcq   -> at least two distinct options;  tf -> exactly the two true/false statements;
    input -> NO options: the learner types the answer (QuestionOut.options is [] by design).
    """
    from app.engine import knowledge_graph as kg
    assert qo.type in QUESTION_TYPES, qo.type
    assert qo.skill in kg.SKILLS and 1 <= qo.difficulty <= 3
    assert qo.question.strip() and qo.hint.strip()
    if qo.type == "mcq":
        assert len(qo.options) >= 2 and len(set(qo.options)) == len(qo.options)
    elif qo.type == "tf":
        assert sorted(qo.options) == sorted(["صح", "خطأ"])
    else:
        assert qo.options == []



def test_question_state_and_answer_responses_match_their_schema(client, db):
    s = register(client)
    q = client.get(BASE.format(id=s["id"]) + "/question", headers=s["headers"])
    assert q.status_code == 200
    qo = QuestionOut.model_validate(q.json())
    _assert_question_contract(qo)
    st = client.get(BASE.format(id=s["id"]) + "/state", headers=s["headers"])
    StudentStateOut.model_validate(st.json())
    from app.models.adaptive import StudentAdaptiveState
    db.expire_all()
    right = db.get(StudentAdaptiveState, uuid.UUID(s["id"])).pending_question["correct_answer"]
    a = client.post(BASE.format(id=s["id"]) + "/answer", json={"selected_answer": right}, headers=s["headers"])
    assert a.status_code == 200
    d = DecisionOut.model_validate(a.json())
    assert d.is_correct is True and d.idempotent_replay is False


@pytest.mark.parametrize("payload", [
    {}, {"selected_answer": ""}, {"selected_answer": "x" * 201}, {"selected_answer": 5}, {"selected_answer": None},
    {"selected_answer": ["a"]}, {"selected_answer": "1", "is_remedial": "maybe"},
    {"selected_answer": "1", "request_id": "short"}, {"selected_answer": "1", "request_id": "bad id with spaces!!"},
    {"selected_answer": "1", "request_id": "x" * 65}, {"selected_answer": "1", "request_id": 12345678},
])
def test_answer_rejects_invalid_payloads(client, payload):
    s = register(client)
    client.get(BASE.format(id=s["id"]) + "/question", headers=s["headers"])
    r = client.post(BASE.format(id=s["id"]) + "/answer", json=payload, headers=s["headers"])
    assert r.status_code == 422, (payload, r.text)
    _assert_error_shape(r)


def test_answer_without_a_pending_question_is_a_clear_conflict(client):
    s = register(client)
    r = client.post(BASE.format(id=s["id"]) + "/answer", json={"selected_answer": "1"}, headers=s["headers"])
    assert r.status_code == 409 and r.json()["detail"] == "no_active_question"


def test_a_wrong_answer_string_is_graded_not_crashed(client, db):
    s = register(client)
    client.get(BASE.format(id=s["id"]) + "/question", headers=s["headers"])
    r = client.post(BASE.format(id=s["id"]) + "/answer", json={"selected_answer": "<script>alert(1)</script>"},
                    headers=s["headers"])
    assert r.status_code == 200 and r.json()["is_correct"] is False


@pytest.mark.parametrize("bad_id", ["not-a-uuid", "123", "0" * 36, "../../etc/passwd"])
def test_path_ids_must_be_uuids(client, bad_id):
    s = register(client)
    r = client.get(f"/students/{bad_id}/adaptive/state", headers=s["headers"])
    assert r.status_code in (404, 422)
    _assert_error_shape(r)


# --- tutor chat -----------------------------------------------------------------------------------

def test_chat_contract(client):
    s = register(client)
    base = f"/students/{s['id']}/chat"
    start = client.post(f"{base}/start", json={"skill_context": "adding_integers"}, headers=s["headers"])
    assert start.status_code == 200 and set(start.json()) >= {"session_id", "opening_message"}
    sid = start.json()["session_id"]
    ok = client.post(f"{base}/message", json={"session_id": sid, "message": "ما ناتج 3 + 4"}, headers=s["headers"])
    assert ok.status_code == 200 and set(ok.json()) >= {"reply", "source", "remaining_today"}
    for bad in ({"session_id": sid, "message": "x" * 1001}, {"session_id": sid, "message": ""},
                {"session_id": sid}, {"message": "hi"}, {"session_id": "nope", "message": "hi"},
                {"session_id": sid, "message": 5}):
        r = client.post(f"{base}/message", json=bad, headers=s["headers"])
        assert r.status_code == 422, (bad, r.text)
        _assert_error_shape(r)


def test_chat_start_rejects_unknown_skill_and_missing_field(client):
    s = register(client)
    base = f"/students/{s['id']}/chat"
    assert client.post(f"{base}/start", json={"skill_context": "nope"}, headers=s["headers"]).status_code == 422
    assert client.post(f"{base}/start", json={}, headers=s["headers"]).status_code == 422


# --- no teacher/school product ------------------------------------------------------------------

def test_the_retired_classroom_and_organization_apis_are_gone(client):
    s = register(client)
    for path in ("/classrooms", "/classrooms/join", "/classrooms/assignments"):
        for r in (client.get(path, headers=s["headers"]), client.post(path, json={"name": "x"}, headers=s["headers"])):
            assert r.status_code in (404, 405), (path, r.status_code)
            _assert_error_shape(r)
    r = client.get(f"/organizations/{uuid.uuid4()}/insights", headers=s["headers"])
    assert r.status_code == 404
    _assert_error_shape(r)


def test_unknown_routes_return_json_404(client):
    s = register(client)
    r = client.get("/definitely/not/here", headers=s["headers"])
    assert r.status_code == 404


def test_every_served_question_over_a_session_meets_its_types_contract(client, db):
    """Serve and answer a run of questions through the API; whatever types appear must satisfy the contract."""
    import uuid as _uuid
    from app.models.adaptive import StudentAdaptiveState
    from tests.helpers import set_plan
    s = register(client)
    set_plan(db, s["id"], "pro")
    seen = set()
    for _ in range(25):
        r = client.get(BASE.format(id=s["id"]) + "/question", headers=s["headers"])
        assert r.status_code == 200, r.text
        qo = QuestionOut.model_validate(r.json())
        _assert_question_contract(qo)
        seen.add(qo.type)
        db.expire_all()
        right = db.get(StudentAdaptiveState, _uuid.UUID(s["id"])).pending_question["correct_answer"]
        a = client.post(BASE.format(id=s["id"]) + "/answer", json={"selected_answer": right}, headers=s["headers"])
        assert a.status_code == 200, a.text
        if a.json()["round_over"]:
            assert client.post(BASE.format(id=s["id"]) + "/round", headers=s["headers"]).status_code == 200
    assert seen <= QUESTION_TYPES
    db.rollback()
