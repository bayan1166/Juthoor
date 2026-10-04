import uuid

from app.models.org import PlanTierUser, User, UserRole

_counter = {"n": 0}


def register(client, role="student", **extra):
    _counter["n"] += 1
    body = {"email": f"user{_counter['n']}@test.com", "password": "secret123",
            "full_name": f"User {_counter['n']}", "role": role, **extra}
    r = client.post("/auth/register", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    return {"id": data["user_id"], "token": data["access_token"], "email": body["email"],
            "headers": {"Authorization": f"Bearer {data['access_token']}"}}


def child_id_of(client, student):
    """The Child ID shown in the learner's account (what a parent must enter to sign up)."""
    code = client.get("/auth/me", headers=student["headers"]).json()["child_id"]
    assert code, "learners always have a Child ID"
    return code


def register_parent(client, child=None, **extra):
    """A parent account can only be created with a valid Child ID: registers the child first when none is given."""
    child = child or register(client)
    parent = register(client, role="parent", child_id=child_id_of(client, child), **extra)
    parent["child"] = child
    return parent


def set_plan(db, user_id, plan):
    user = db.get(User, uuid.UUID(str(user_id)))
    user.plan = PlanTierUser(plan)
    user.plan_expires_at = None
    db.commit()
    return user


def make_internal_admin(db, user_id):
    """Turn a registered account into the internal operations (moderation) account. It cannot be self-registered."""
    user = db.get(User, uuid.UUID(str(user_id)))
    user.role = UserRole.platform_admin
    db.commit()
    return user


def handle_of(client, user):
    return client.get("/auth/me", headers=user["headers"]).json()["handle"]
