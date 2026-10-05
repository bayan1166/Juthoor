"""Authorization and isolation matrix: who may read/write whose data, including what a refusal leaks.

Status codes alone are not enough, so every refusal also asserts that the victim's identifying data
(email, full name, handle) does not appear anywhere in the response body.
"""
import uuid

import pytest

from tests.helpers import make_internal_admin, register, register_parent


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
    """B2C world: learners, parents linked to their own children, and one internal moderation account."""
    w = {
        "a_student": register(client),
        "b_student": register(client),
        "loner": register(client),
        "stranger_parent": register_parent(client),  # a parent of some other child
        "admin": register(client),
    }
    make_internal_admin(db, w["admin"]["id"])
    w["child"] = register(client)
    w["parent"] = register_parent(client, w["child"])  # parent accounts exist only with a linked child
    w["sibling"] = register(client, guardian_email=w["parent"]["email"])
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


@pytest.mark.parametrize("path", READ_PATHS)
def test_parent_reads_their_children_but_not_other_learners(client, world, path):
    parent = world["parent"]
    for kid in (world["child"], world["sibling"]):
        assert _read(client, parent, path.format(id=kid["id"])).status_code == 200
    r = _read(client, parent, path.format(id=world["a_student"]["id"]))
    assert r.status_code == 403
    _no_leak(r, world["a_student"])


def test_roster_is_scoped_to_the_parent_s_own_children(client, world):
    roster = client.get("/me/students", headers=world["parent"]["headers"]).json()
    assert {r["student_id"] for r in roster} == {world["child"]["id"], world["sibling"]["id"]}
    stranger = client.get("/me/students", headers=world["stranger_parent"]["headers"]).json()
    assert [r["student_id"] for r in stranger] == [world["stranger_parent"]["child"]["id"]]
    assert client.get("/me/students", headers=world["a_student"]["headers"]).status_code == 403


def test_internal_admin_is_an_operations_account_not_a_learner(client, world):
    admin = world["admin"]
    assert _read(client, admin, f"/students/{world['a_student']['id']}/adaptive/state").status_code == 200
    me = client.get("/auth/me", headers=admin["headers"]).json()
    assert me["role"] == "platform_admin"


def test_parent_reads_only_their_own_child(client, world):
    assert _read(client, world["parent"], f"/students/{world['child']['id']}/adaptive/state").status_code == 200
    r = _read(client, world["stranger_parent"], f"/students/{world['child']['id']}/adaptive/state")
    assert r.status_code == 403
    _no_leak(r, world["child"])


@pytest.mark.parametrize("method, path, body", SELF_ONLY_WRITES)
@pytest.mark.parametrize("actor", ["admin", "parent", "b_student"])
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


@pytest.mark.parametrize("role", ["teacher", "org_admin", "school"])
def test_teacher_and_school_accounts_do_not_exist(client, role):
    r = _try(client, role=role)
    assert r.status_code == 422


def test_legacy_organization_fields_are_ignored_and_create_nothing(client):
    r = _try(client, org_slug="alpha", org_code="whatever")
    assert r.status_code == 200
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    assert me["role"] == "student" and "organization_id" not in me and "organization_name" not in me


def test_a_child_can_only_be_linked_to_an_existing_parent(client, world):
    assert _try(client, guardian_email=world["a_student"]["email"]).status_code == 400
    assert _try(client, guardian_id=world["b_student"]["id"]).status_code == 400
    assert _try(client, guardian_email=world["parent"]["email"]).status_code == 200


def test_admin_roles_cannot_be_self_registered(client):
    for role in ("platform_admin",):
        assert _try(client, role=role).status_code == 422
