"""Authorization and isolation matrix: who may read/write whose data, including what a refusal leaks.

Status codes alone are not enough, so every refusal also asserts that the victim's identifying data
(email, full name, handle) does not appear anywhere in the response body.
"""
import uuid

import pytest

from app.models.org import Organization
from app.services import org_access
from tests.helpers import register


def _org(db, slug, with_code=True):
    org = Organization(name=f"School {slug}", slug=slug)
    code = org_access.issue_join_code(org) if with_code else None
    db.add(org)
    db.commit()
    return code


def _read(client, actor, path):
    return client.get(path, headers=actor["headers"] if actor else {})


def _no_leak(resp, victim):
    text = resp.text
    for secret in (victim["email"], victim.get("full_name") or "\0", victim.get("handle") or "\0"):
        assert secret not in text, f"refusal leaked {secret!r}"


READ_PATHS = ["/students/{id}/adaptive/state", "/students/{id}/adaptive/report", "/students/{id}/adaptive/diagnoses",
              "/students/{id}/adaptive/tree", "/students/{id}/insights"]
SELF_ONLY_WRITES = [("get", "/students/{id}/adaptive/question", None),
                    ("post", "/students/{id}/adaptive/answer", {"selected_answer": "1"}),
                    ("post", "/students/{id}/adaptive/round", None)]


@pytest.fixture
def world(client, db):
    code_a, code_b = _org(db, "alpha"), _org(db, "beta")
    w = {
        "a_student": register(client, org_slug="alpha", org_code=code_a),
        "a_teacher": register(client, role="teacher", org_slug="alpha", org_code=code_a),
        "b_student": register(client, org_slug="beta", org_code=code_b),
        "b_teacher": register(client, role="teacher", org_slug="beta", org_code=code_b),
        "loner": register(client),
        "stranger_parent": register(client, role="parent"),
        "floating_teacher": register(client, role="teacher"),
    }
    w["parent"] = register(client, role="parent")
    w["child"] = register(client, guardian_id=w["parent"]["id"])
    w["codes"] = {"alpha": code_a, "beta": code_b}
    return w


@pytest.mark.parametrize("path", READ_PATHS)
def test_student_reads_own_data_but_not_another_students(client, world, path):
    own = world["a_student"]
    assert _read(client, own, path.format(id=own["id"])).status_code == 200
    r = _read(client, own, path.format(id=world["loner"]["id"]))
    assert r.status_code == 403
    _no_leak(r, world["loner"])


@pytest.mark.parametrize("path", READ_PATHS)
def test_unauthenticated_access_is_refused(client, world, path):
    r = _read(client, None, path.format(id=world["a_student"]["id"]))
    assert r.status_code in (401, 403)
    _no_leak(r, world["a_student"])


@pytest.mark.parametrize("path", READ_PATHS[:3])
def test_teacher_reads_students_of_their_own_organization_only(client, world, path):
    assert _read(client, world["a_teacher"], path.format(id=world["a_student"]["id"])).status_code == 200
    r = _read(client, world["a_teacher"], path.format(id=world["b_student"]["id"]))
    assert r.status_code == 403
    _no_leak(r, world["b_student"])
    r = _read(client, world["b_teacher"], path.format(id=world["a_student"]["id"]))
    assert r.status_code == 403
    _no_leak(r, world["a_student"])


def test_teacher_without_an_organization_or_class_reads_nobody(client, world):
    r = _read(client, world["floating_teacher"], f"/students/{world['a_student']['id']}/adaptive/state")
    assert r.status_code == 403
    assert client.get("/me/students", headers=world["floating_teacher"]["headers"]).json() == []


def test_teacher_sees_a_class_member_through_the_classroom_link_only(client, world):
    teacher, member, other = world["floating_teacher"], world["loner"], world["stranger_parent"]
    room = client.post("/classrooms", json={"name": "Class A"}, headers=teacher["headers"]).json()
    assert client.post("/classrooms/join", json={"join_code": room["join_code"]}, headers=member["headers"]).status_code == 200
    assert _read(client, teacher, f"/students/{member['id']}/adaptive/state").status_code == 200
    pupil = register(client)
    r = _read(client, teacher, f"/students/{pupil['id']}/adaptive/state")
    assert r.status_code == 403
    _no_leak(r, pupil)


def test_roster_is_scoped_to_the_organization(client, world):
    roster = client.get("/me/students", headers=world["a_teacher"]["headers"]).json()
    ids = {r["student_id"] for r in roster}
    assert world["a_student"]["id"] in ids
    assert world["b_student"]["id"] not in ids and world["loner"]["id"] not in ids
    assert client.get("/me/students", headers=world["a_student"]["headers"]).status_code == 403


def test_cohort_insights_cannot_cross_organizations(client, db, world):
    from app.models.org import User
    org_a = db.get(User, uuid.UUID(world["a_teacher"]["id"])).organization_id
    r = client.get(f"/organizations/{org_a}/insights", headers=world["b_teacher"]["headers"])
    assert r.status_code == 403 and r.json()["detail"] == "cross_organization_access_denied"
    assert client.get(f"/organizations/{org_a}/insights", headers=world["a_student"]["headers"]).status_code == 403


def test_parent_reads_only_their_own_child(client, world):
    assert _read(client, world["parent"], f"/students/{world['child']['id']}/adaptive/state").status_code == 200
    r = _read(client, world["stranger_parent"], f"/students/{world['child']['id']}/adaptive/state")
    assert r.status_code == 403
    _no_leak(r, world["child"])


@pytest.mark.parametrize("method, path, body", SELF_ONLY_WRITES)
@pytest.mark.parametrize("actor", ["a_teacher", "parent", "b_student"])
def test_only_the_student_can_play_as_the_student(client, world, actor, method, path, body):
    victim = world["a_student"]
    kw = {"headers": world[actor]["headers"]}
    if body is not None:
        kw["json"] = body
    r = getattr(client, method)(path.format(id=victim["id"]), **kw)
    assert r.status_code == 403
    _no_leak(r, victim)


def test_chat_sessions_belong_to_their_student(client, world):
    a, b = world["a_student"], world["b_student"]
    sid = client.post(f"/students/{a['id']}/chat/start", json={"skill_context": "adding_integers"}, headers=a["headers"]).json()["session_id"]
    r = client.get(f"/students/{b['id']}/chat/sessions/{sid}/messages", headers=b["headers"])
    assert r.status_code == 404
    assert client.get(f"/students/{a['id']}/chat/sessions/{sid}/messages", headers=b["headers"]).status_code == 403


# --- registration is controlled ------------------------------------------------------------------

def _try(client, **extra):
    body = {"email": f"{uuid.uuid4().hex[:10]}@test.com", "password": "secret123", "full_name": "N N", **extra}
    return client.post("/auth/register", json=body)


def test_a_public_slug_alone_cannot_make_you_a_teacher_of_an_organization(client, world):
    r = _try(client, role="teacher", org_slug="alpha")
    assert r.status_code == 403 and r.json()["detail"] == "invalid_org_code"
    r = _try(client, role="teacher", org_slug="alpha", org_code="not-the-code")
    assert r.status_code == 403
    assert _try(client, role="teacher", org_slug="alpha", org_code=world["codes"]["beta"]).status_code == 403
    ok = _try(client, role="teacher", org_slug="alpha", org_code=world["codes"]["alpha"])
    assert ok.status_code == 200


def test_joining_an_organization_that_issued_a_code_requires_it_for_students_too(client, world):
    assert _try(client, org_slug="alpha").status_code == 403
    assert _try(client, org_slug="alpha", org_code=world["codes"]["alpha"]).status_code == 200


def test_a_teacher_cannot_join_an_organization_that_has_no_code(client, db):
    _org(db, "legacy", with_code=False)
    assert _try(client, role="teacher", org_slug="legacy").status_code == 403
    assert _try(client, org_slug="legacy").status_code == 200  # students may still join a code-less legacy org


def test_unknown_organization_is_reported_as_not_found(client):
    assert _try(client, org_slug="nope-" + uuid.uuid4().hex[:6]).status_code == 404


def test_admin_roles_cannot_be_self_registered(client):
    for role in ("org_admin", "platform_admin"):
        assert _try(client, role=role).status_code == 422
