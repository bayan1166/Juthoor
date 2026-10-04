"""A parent/guardian account is created only together with its link to an existing learner (no orphan parents).

The Child ID is shown in the learner's own account; the server checks it (format, learner exists, active, HMAC tag)
before writing anything, and links parent and child in the same transaction.
"""
import uuid

from sqlalchemy import func, select

from app.models.org import User, UserRole
from app.services import child_link
from tests.helpers import child_id_of, register, register_parent


def _parent_signup(client, **extra):
    body = {"email": f"p{uuid.uuid4().hex[:10]}@test.com", "password": "secret123", "full_name": "ولي أمر",
            "role": "parent", **extra}
    return client.post("/auth/register", json=body), body["email"]


def _parents(db) -> int:
    db.expire_all()
    return db.scalar(select(func.count(User.id)).where(User.role == UserRole.parent))


def _exists(db, email) -> bool:
    db.expire_all()
    return db.scalar(select(User.id).where(User.email == email)) is not None


def test_parent_signup_without_child_id_fails_and_writes_nothing(client, db):
    before = _parents(db)
    for extra in ({}, {"child_id": ""}, {"child_id": "   "}, {"child_id": None}):
        r, email = _parent_signup(client, **extra)
        assert r.status_code == 400 and r.json()["detail"] == "child_id_required", (extra, r.text)
        assert not _exists(db, email)
    assert _parents(db) == before


def test_parent_signup_with_an_unknown_or_malformed_child_id_fails_and_writes_nothing(client, db):
    kid = register(client)
    real = child_id_of(client, kid)
    handle = real.split("-")[0]
    before = _parents(db)
    for bad in ("0000-AAAAAAAA", f"{handle}-AAAAAAAA", handle, kid["id"], "not a code", real + "X",
                "9" * 13 + "-" + real.split("-")[1]):
        r, email = _parent_signup(client, child_id=bad)
        assert r.status_code == 400 and r.json()["detail"] == "child_id_invalid", (bad, r.text)
        assert not _exists(db, email)
    assert _parents(db) == before
    db.expire_all()
    assert db.get(User, uuid.UUID(kid["id"])).guardian_id is None, "a failed attempt never links the child"


def test_parent_signup_with_a_valid_child_id_links_parent_and_child(client, db):
    kid = register(client)
    code = child_id_of(client, kid)
    r, email = _parent_signup(client, child_id=f"  #{code.lower()} ")  # pasted with spaces / '#' / lower case
    assert r.status_code == 200, r.text
    parent_id = uuid.UUID(r.json()["user_id"])
    db.expire_all()
    parent = db.get(User, parent_id)
    child = db.get(User, uuid.UUID(kid["id"]))
    assert parent.role == UserRole.parent and parent.email == email and parent.guardian_id is None
    assert child.guardian_id == parent_id
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    roster = client.get("/me/students", headers=headers).json()
    assert [row["student_id"] for row in roster] == [kid["id"]]
    assert client.get(f"/students/{kid['id']}/adaptive/report", headers=headers).status_code == 200


def test_a_learner_who_already_has_a_parent_cannot_be_claimed_again(client, db):
    parent = register_parent(client)
    kid = parent["child"]
    before = _parents(db)
    r, email = _parent_signup(client, child_id=child_id_of(client, kid))
    assert r.status_code == 409 and r.json()["detail"] == "child_already_linked"
    assert not _exists(db, email) and _parents(db) == before
    db.expire_all()
    assert str(db.get(User, uuid.UUID(kid["id"])).guardian_id) == parent["id"], "the existing link is never overwritten"


def test_only_a_learner_has_a_child_id(client, db):
    parent = register_parent(client)
    me = client.get("/auth/me", headers=parent["headers"]).json()
    assert me["role"] == "parent" and me["child_id"] is None
    db.expire_all()
    assert child_link.child_id_for(db.get(User, uuid.UUID(parent["id"]))) is None
    # a parent's handle with a forged tag is not a Child ID either
    r, _ = _parent_signup(client, child_id=f"{me['handle']}-AAAAAAAA")
    assert r.status_code == 400 and r.json()["detail"] == "child_id_invalid"


def test_public_identifiers_are_not_enough_to_link_a_child(client, db):
    """Handles and user ids are visible in the community; the Child ID also needs the secret tag."""
    kid = register(client)
    handle = client.get("/auth/me", headers=kid["headers"]).json()["handle"]
    for guess in (handle, f"#{handle}", kid["id"], f"{handle}-{kid['id'][:8]}"):
        r, _ = _parent_signup(client, child_id=guess)
        assert r.status_code == 400
    db.expire_all()
    assert db.get(User, uuid.UUID(kid["id"])).guardian_id is None


def test_an_inactive_learner_cannot_be_linked(client, db):
    kid = register(client)
    code = child_id_of(client, kid)
    user = db.get(User, uuid.UUID(kid["id"]))
    user.is_active = False
    db.commit()
    r, email = _parent_signup(client, child_id=code)
    assert r.status_code == 400 and r.json()["detail"] == "child_id_invalid" and not _exists(db, email)


def test_student_signup_is_unchanged(client, db):
    plain = register(client)
    me = client.get("/auth/me", headers=plain["headers"]).json()
    assert me["role"] == "student" and me["child_id"] and me["child_id"].startswith(me["handle"] + "-")
    # a learner can still name a parent who already has an account; a stray child_id is ignored for learners
    parent = register_parent(client)
    second = register(client, guardian_email=parent["email"], child_id="ignored-for-students")
    db.expire_all()
    assert str(db.get(User, uuid.UUID(second["id"])).guardian_id) == parent["id"]
    assert client.post("/auth/register", json={"email": "x1@test.com", "password": "secret123", "full_name": "X",
                                               "guardian_email": "nobody@test.com"}).status_code == 400


def test_existing_parent_login_is_unchanged(client):
    parent = register_parent(client)
    r = client.post("/auth/login", json={"email": parent["email"], "password": "secret123"})
    assert r.status_code == 200 and r.json()["role"] == "parent"
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert [row["student_id"] for row in client.get("/me/students", headers=headers).json()] == [parent["child"]["id"]]
    assert client.post("/auth/login", json={"email": parent["email"], "password": "wrong-pass"}).status_code == 401


def test_the_child_id_does_not_change_between_requests_and_is_unique(client):
    a, b = register(client), register(client)
    assert child_id_of(client, a) == child_id_of(client, a)
    assert child_id_of(client, a) != child_id_of(client, b)
