"""Scenarios V (authorization/ownership), W (payment/subscription edge cases) and
X (avatar/economy edge cases), through the HTTP API and the test database."""
import uuid
from datetime import datetime, timedelta

from app.engine import avatar_items as ai
from app.models.economy import Currency, TxnReason
from app.services.economy_service import apply_txn, get_or_create_wallet
from app.services.plans import PERIOD_DAYS
from tests.helpers import register


def econ(s):
    return f"/students/{s['id']}/economy"


def grant(db, s, coins=0, gems=0):
    wallet = get_or_create_wallet(db, uuid.UUID(s["id"]))
    if coins:
        apply_txn(db, wallet, Currency.coins, coins, TxnReason.admin_grant)
    if gems:
        apply_txn(db, wallet, Currency.gems, gems, TxnReason.admin_grant)
    db.commit()


def wallet_of(client, s):
    r = client.get(f"{econ(s)}/wallet", headers=s["headers"])
    assert r.status_code == 200, r.text
    return r.json()


# --- X: shop / avatar economy --------------------------------------------------------------

def test_x_shop_is_complete_on_a_fresh_database_and_never_duplicated(client):
    s = register(client)
    first = client.get(f"{econ(s)}/shop", headers=s["headers"]).json()
    again = client.get(f"{econ(s)}/catalog", headers=s["headers"]).json()
    assert len(first) == len(ai.CATALOG) == len(again)
    assert len({i["id"] for i in first}) == len(first)
    free = [i for i in first if i["price_coins"] == 0 and i["price_gems"] == 0]
    assert free and all(i["owned"] for i in free)
    assert any(not i["owned"] for i in first)
    assert all(i["price_coins"] == 0 for i in first if i["is_premium"])


def test_x_purchase_rules_and_balances(client, db):
    s = register(client)
    base = econ(s)
    shop = client.get(f"{base}/shop", headers=s["headers"]).json()
    paid = sorted((i for i in shop if not i["is_premium"] and i["price_coins"] > 0), key=lambda i: i["price_coins"])
    cheap, dear = paid[0], paid[-1]
    premium = next(i for i in shop if i["is_premium"])

    def buy(item_id, currency="coins"):
        return client.post(f"{base}/purchase", json={"item_id": item_id, "currency": currency}, headers=s["headers"])

    assert buy("no_such_item").status_code == 404 and buy("no_such_item").json()["detail"] == "item_not_found"
    assert buy(cheap["id"], "diamonds").status_code == 422
    r = buy(premium["id"], "coins")
    assert r.status_code == 400 and r.json()["detail"] == "premium_item_requires_gems"

    start = wallet_of(client, s)["coins"]
    if dear["price_coins"] > start:
        r = buy(dear["id"])
        assert r.status_code == 402 and r.json()["detail"] == "insufficient_balance"
        assert wallet_of(client, s)["coins"] == start, "a refused purchase changes nothing"

    grant(db, s, coins=cheap["price_coins"])
    before = wallet_of(client, s)["coins"]
    r = buy(cheap["id"])
    body = r.json()
    assert r.status_code == 200 and body["success"] is True and body["message"] == "purchased"
    assert body["wallet"]["coins"] == before - cheap["price_coins"] == wallet_of(client, s)["coins"]
    assert set(body["wallet"]) == {"student_id", "coins", "gems", "lifetime_coins_earned", "lifetime_gems_earned"}

    repeat = buy(cheap["id"])
    assert repeat.status_code == 200 and repeat.json()["success"] is False and repeat.json()["message"] == "already_owned"
    assert repeat.json()["wallet"]["coins"] == body["wallet"]["coins"], "no double charge"
    owned = {i["id"]: i["owned"] for i in client.get(f"{base}/shop", headers=s["headers"]).json()}
    assert owned[cheap["id"]] is True


def test_x_gem_conversion_rules(client, db):
    s = register(client)
    base = econ(s)
    r = client.post(f"{base}/convert", json={"coins": 150}, headers=s["headers"])
    assert r.status_code == 400 and r.json()["detail"].startswith("coins_must_be_multiple_of_")
    assert client.post(f"{base}/convert", json={"coins": 0}, headers=s["headers"]).status_code == 400
    coins = wallet_of(client, s)["coins"]
    if coins < 200:
        r = client.post(f"{base}/convert", json={"coins": 200}, headers=s["headers"])
        assert r.status_code == 402 and r.json()["detail"] == "insufficient_coins"
    grant(db, s, coins=400)
    before = wallet_of(client, s)
    r = client.post(f"{base}/convert", json={"coins": 400}, headers=s["headers"])
    assert r.status_code == 200
    assert r.json()["coins"] == before["coins"] - 400 and r.json()["gems"] == before["gems"] + 2


def test_x_wearing_requires_ownership_and_bundles_count(client, db):
    s = register(client)
    base = econ(s)
    avatar = client.get(f"{base}/avatar", headers=s["headers"]).json()
    shop = {i["id"]: i for i in client.get(f"{base}/shop", headers=s["headers"]).json()}
    locked = next(i for i in shop.values() if i["category"] == "clothing" and not i["owned"])
    r = client.put(f"{base}/avatar", json={**avatar, "clothing": locked["id"]}, headers=s["headers"])
    assert r.status_code == 403 and r.json()["detail"].startswith("item_not_owned:")
    grant(db, s, coins=locked["price_coins"] + 10)
    assert client.post(f"{base}/purchase", json={"item_id": locked["id"], "currency": "coins"},
                       headers=s["headers"]).json()["success"] is True
    r = client.put(f"{base}/avatar", json={**avatar, "clothing": locked["id"]}, headers=s["headers"])
    assert r.status_code == 200 and r.json()["svg"].startswith("<svg")
    assert client.get(f"{base}/avatar", headers=s["headers"]).json()["clothing"] == locked["id"]
    too_long = client.put(f"{base}/avatar", json={**avatar, "clothing": "x" * 41}, headers=s["headers"])
    assert too_long.status_code == 422


# --- V: ownership / authorization ------------------------------------------------------------

def test_v_students_cannot_touch_each_others_economy(client):
    a, b = register(client), register(client)
    avatar = client.get(f"{econ(a)}/avatar", headers=a["headers"]).json()
    assert client.get(f"{econ(a)}/wallet", headers=b["headers"]).status_code == 403
    assert client.get(f"{econ(a)}/shop", headers=b["headers"]).status_code == 403
    assert client.post(f"{econ(a)}/purchase", json={"item_id": "jersey", "currency": "coins"},
                       headers=b["headers"]).status_code == 403
    assert client.post(f"{econ(a)}/convert", json={"coins": 200}, headers=b["headers"]).status_code == 403
    assert client.put(f"{econ(a)}/avatar", json=avatar, headers=b["headers"]).status_code == 403
    assert client.get(f"{econ(a)}/wallet").status_code in (401, 403)
    assert client.get(f"{econ(a)}/wallet", headers={"Authorization": "Bearer forged.token.value"}).status_code == 401


def test_v_expired_token_is_rejected(client):
    import jwt as pyjwt
    from app.config import settings
    s = register(client)
    expired = pyjwt.encode({"sub": s["id"], "role": "student", "org_id": None,
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
