"""Scenarios V (authorization/ownership), W (payment/subscription edge cases) and
X (avatar, and the removal of the coin/gem economy), through the HTTP API and the test database."""
import uuid
from datetime import datetime, timedelta

from app.engine import avatar_items as ai
from app.models.economy import Currency, InventoryItem
from app.services.plans import PERIOD_DAYS
from tests.helpers import register


def econ(s):
    return f"/students/{s['id']}/economy"


# --- X: avatar (the coin/gem shop was removed) ----------------------------------------------

def test_x_the_coin_and_gem_economy_api_is_gone(client):
    s = register(client)
    base = econ(s)
    for method, path, body in (("get", "/wallet", None), ("get", "/shop", None), ("get", "/catalog", None),
                               ("post", "/purchase", {"item_id": "jersey", "currency": "coins"}),
                               ("post", "/convert", {"coins": 200})):
        kw = {"headers": s["headers"]}
        if body is not None:
            kw["json"] = body
        assert getattr(client, method)(base + path, **kw).status_code in (404, 405), path


def test_x_wearing_a_formerly_paid_item_requires_prior_ownership_and_bundles_count(client, db):
    s = register(client)
    base = econ(s)
    avatar = client.get(f"{base}/avatar", headers=s["headers"]).json()
    paid = next(i for i in ai.CATALOG if i.cat == "clothing" and i.price > 0 and i.bundle)
    r = client.put(f"{base}/avatar", json={**avatar, "clothing": paid.id}, headers=s["headers"])
    assert r.status_code == 403 and r.json()["detail"].startswith("item_not_owned:")
    # an item bought before the shop was removed stays wearable, together with its bundled piece
    db.add(InventoryItem(student_id=uuid.UUID(s["id"]), item_id=paid.id, currency_spent=Currency.coins, price_paid=0))
    db.commit()
    bundled = dict(paid.bundle)
    r = client.put(f"{base}/avatar", json={**avatar, "clothing": paid.id, **bundled}, headers=s["headers"])
    assert r.status_code == 200 and r.json()["svg"].startswith("<svg")
    assert client.get(f"{base}/avatar", headers=s["headers"]).json()["clothing"] == paid.id
    too_long = client.put(f"{base}/avatar", json={**avatar, "clothing": "x" * 41}, headers=s["headers"])
    assert too_long.status_code == 422


# --- V: ownership / authorization ------------------------------------------------------------

def test_v_students_cannot_touch_each_others_avatar(client):
    a, b = register(client), register(client)
    avatar = client.get(f"{econ(a)}/avatar", headers=a["headers"]).json()
    assert client.put(f"{econ(a)}/avatar", json=avatar, headers=b["headers"]).status_code == 403
    assert client.get(f"{econ(a)}/previews", headers=b["headers"]).status_code == 403
    assert client.get(f"{econ(a)}/avatar").status_code in (401, 403)
    assert client.get(f"{econ(a)}/avatar", headers={"Authorization": "Bearer forged.token.value"}).status_code == 401


def test_v_expired_token_is_rejected(client):
    import jwt as pyjwt
    from app.config import settings
    s = register(client)
    expired = pyjwt.encode({"sub": s["id"], "role": "student",
                            "exp": datetime.utcnow() - timedelta(minutes=1)}, settings.jwt_secret, algorithm="HS256")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401 and r.json()["detail"] == "invalid_token"


# --- W: payments / subscriptions --------------------------------------------------------------

def _checkout(client, s, period="monthly"):
    r = client.post("/payments/checkout", json={"plan": "pro", "period": period}, headers=s["headers"])
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def _confirm(client, s, sid, last4="4242", holder="Lian"):
    return client.post("/payments/confirm", json={"session_id": sid, "card_last4": last4, "card_holder": holder},
                       headers=s["headers"])


def _expiry(client, s):
    raw = client.get("/auth/me", headers=s["headers"]).json()["plan_expires_at"]
    assert raw.endswith("Z")
    return datetime.fromisoformat(raw[:-1])


def test_w_checkout_sessions_belong_to_their_buyer(client):
    a, b = register(client), register(client)
    sid = _checkout(client, a)
    assert _confirm(client, b, sid).status_code == 404
    assert client.get(f"/payments/session/{sid}", headers=b["headers"]).status_code == 404
    assert _confirm(client, a, str(uuid.uuid4())).status_code == 404
    status = client.get(f"/payments/session/{sid}", headers=a["headers"]).json()
    assert status["status"] == "pending" and status["created_at"].endswith("Z")
    assert client.get("/auth/me", headers=b["headers"]).json()["plan"] == "basic"


def test_w_bad_cards_are_rejected_without_granting_anything(client):
    s = register(client)
    sid = _checkout(client, s)
    for last4, holder in (("42", "Lian"), ("abcd", "Lian"), ("4242", "   ")):
        r = _confirm(client, s, sid, last4, holder)
        assert r.status_code == 422 and r.json()["detail"] == "bad_card"
    assert client.get("/auth/me", headers=s["headers"]).json()["plan"] == "basic"
    assert _confirm(client, s, sid).status_code == 200


def test_w_renewal_extends_the_current_period_instead_of_resetting_it(client):
    s = register(client)
    assert _confirm(client, s, _checkout(client, s)).status_code == 200
    first = _expiry(client, s)
    assert abs((first - datetime.utcnow()) - timedelta(days=PERIOD_DAYS["monthly"])) < timedelta(minutes=5)
    assert _confirm(client, s, _checkout(client, s)).status_code == 200
    second = _expiry(client, s)
    assert abs((second - first) - timedelta(days=PERIOD_DAYS["monthly"])) < timedelta(seconds=5)
