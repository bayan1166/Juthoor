"""B2C business-model regressions: student = user, parent = buyer, teachers/schools never pay.

Locked prices (minor units, JOD): Free 0, Pro monthly 4500 (4.50), Pro academic year 32000 (32.00).
"""
import pathlib
import re

import pytest

from app.config import settings
from app.services import plan_rules
from tests.helpers import make_internal_admin, register, register_parent

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_locked_prices_and_only_free_and_pro_are_public(client):
    body = client.get("/payments/plans").json()
    by_id = {p["id"]: p for p in body["plans"]}
    assert list(by_id) == ["basic", "pro"]
    assert (by_id["basic"]["price_month"], by_id["basic"]["price_year"]) == (0, 0)
    assert (by_id["pro"]["price_month"], by_id["pro"]["price_year"]) == (4500, 32000)
    assert body["currency"] == "JOD"


def test_catalogue_never_mentions_teachers_schools_or_seats():
    blob = repr(plan_rules.PLAN_CATALOG) + repr(plan_rules.USP)
    for word in ("للمعلم", "المدرسة", "مقعد", "الصفوف والواجبات", "واتساب"):
        assert word not in blob


@pytest.mark.parametrize("plan", ["school", "basic", "enterprise", ""])
def test_server_rejects_any_plan_but_pro(client, plan):
    student = register(client)
    assert client.post("/payments/checkout", json={"plan": plan}, headers=student["headers"]).status_code == 422


def test_server_computes_amount_ignoring_client_supplied_price(client):
    student = register(client)
    res = client.post("/payments/checkout", json={"plan": "pro", "period": "monthly", "amount_minor": 1, "price": 1},
                      headers=student["headers"])
    assert res.status_code == 200 and res.json()["amount_minor"] == 4500
    yearly = client.post("/payments/checkout", json={"plan": "pro", "period": "yearly"}, headers=student["headers"])
    assert yearly.json()["amount_minor"] == 32000


@pytest.mark.parametrize("role", ["teacher", "org_admin", "school", "platform_admin"])
def test_there_is_no_teacher_school_or_admin_signup(client, role):
    r = client.post("/auth/register", json={"email": f"{role}@test.com", "password": "secret123", "full_name": "X", "role": role})
    assert r.status_code == 422


def test_only_students_and_parents_can_buy(client, db):
    internal = register(client)
    make_internal_admin(db, internal["id"])
    for period in ("monthly", "yearly"):
        res = client.post("/payments/checkout", json={"plan": "pro", "period": period}, headers=internal["headers"])
        assert res.status_code == 403


def test_parent_is_the_buyer_and_only_for_their_own_child(client):
    parent = register_parent(client)
    child = parent["child"]
    stranger = register(client)
    assert client.post("/payments/checkout", json={"plan": "pro", "for_student_id": stranger["id"]},
                       headers=parent["headers"]).status_code == 403
    start = client.post("/payments/checkout", json={"plan": "pro", "period": "yearly", "for_student_id": child["id"]},
                        headers=parent["headers"])
    assert start.status_code == 200 and start.json()["amount_minor"] == 32000
    sid = start.json()["session_id"]
    # another account cannot confirm or read the parent's session (IDOR)
    assert client.get(f"/payments/session/{sid}", headers=stranger["headers"]).status_code == 404
    assert client.post("/payments/confirm", json={"session_id": sid, "card_last4": "4242", "card_holder": "X"},
                       headers=stranger["headers"]).status_code == 404
    assert client.get("/auth/me", headers=child["headers"]).json()["plan"] == "basic"


def test_subscription_is_owned_by_the_learner_or_bought_by_their_parent(client):
    parent = register_parent(client)
    child = parent["child"]
    own = register(client)
    for buyer, body, beneficiary in ((parent, {"plan": "pro", "for_student_id": child["id"]}, child), (own, {"plan": "pro"}, own)):
        sid = client.post("/payments/checkout", json=body, headers=buyer["headers"]).json()["session_id"]
        assert client.post("/payments/confirm", json={"session_id": sid, "card_last4": "4242", "card_holder": "X"},
                           headers=buyer["headers"]).status_code == 200
        me = client.get("/auth/me", headers=beneficiary["headers"]).json()
        assert me["plan"] == "pro" and me["plan_source"] == "own"
    assert client.get("/auth/me", headers=parent["headers"]).json()["plan"] == "basic"


def test_the_classroom_api_does_not_exist(client):
    student = register(client)
    assert client.get("/classrooms", headers=student["headers"]).status_code == 404
    assert client.post("/classrooms/join", json={"join_code": "JUTH26"}, headers=student["headers"]).status_code == 404


def test_mock_checkout_is_refused_when_no_provider_and_not_demo(client, monkeypatch):
    student = register(client)
    monkeypatch.setattr(settings, "allow_mock_payments", False)
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "stripe_secret_key", "")
    assert client.get("/payments/plans").json()["provider"] == "none"
    res = client.post("/payments/checkout", json={"plan": "pro"}, headers=student["headers"])
    assert res.status_code == 503 and res.json()["detail"] == "payment_provider_not_configured"
    assert client.get("/auth/me", headers=student["headers"]).json()["plan"] == "basic"


def test_real_provider_failure_never_falls_back_to_mock(client, monkeypatch):
    student = register(client)
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_invalid_for_regression")
    import sys
    import types

    boom = types.SimpleNamespace(checkout=types.SimpleNamespace(Session=types.SimpleNamespace(
        create=lambda **kw: (_ for _ in ()).throw(RuntimeError("network")))), api_key=None)
    monkeypatch.setitem(sys.modules, "stripe", boom)
    res = client.post("/payments/checkout", json={"plan": "pro"}, headers=student["headers"])
    assert res.status_code == 502 and res.json()["detail"] == "payment_provider_unavailable"


def test_confirm_requires_a_pending_session_and_cannot_be_replayed(client):
    student = register(client)
    sid = client.post("/payments/checkout", json={"plan": "pro"}, headers=student["headers"]).json()["session_id"]
    card = {"session_id": sid, "card_last4": "4242", "card_holder": "Parent"}
    assert client.post("/payments/confirm", json=card, headers=student["headers"]).status_code == 200
    assert client.post("/payments/confirm", json=card, headers=student["headers"]).status_code == 409


def test_failed_stripe_confirmation_grants_nothing(client, monkeypatch):
    student = register(client)
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_invalid_for_regression")
    import sys
    import types

    created = types.SimpleNamespace(id="cs_1", url="https://pay.example/cs_1")
    unpaid = types.SimpleNamespace(payment_status="unpaid")
    fake = types.SimpleNamespace(checkout=types.SimpleNamespace(Session=types.SimpleNamespace(
        create=lambda **kw: created, retrieve=lambda ref: unpaid)), api_key=None)
    monkeypatch.setitem(sys.modules, "stripe", fake)
    start = client.post("/payments/checkout", json={"plan": "pro"}, headers=student["headers"]).json()
    assert start["provider"] == "stripe" and start["stripe_url"]
    res = client.post("/payments/confirm-stripe", json={"session_id": start["session_id"]}, headers=student["headers"])
    assert res.status_code == 402 and res.json()["detail"] == "payment_not_completed"
    assert client.get("/auth/me", headers=student["headers"]).json()["plan"] == "basic"
    # the mock confirm endpoint cannot be used to bypass a real provider session
    bypass = client.post("/payments/confirm", json={"session_id": start["session_id"], "card_last4": "4242", "card_holder": "x"},
                         headers=student["headers"])
    assert bypass.status_code == 400


def test_no_legacy_prices_or_teacher_billing_in_shipped_code():
    legacy = re.compile(r"\b(2990|29900|6990|69900)\b|2\.99|29\.90|6\.99|69\.90")
    offenders = []
    for base in ("app", "scripts"):
        for path in (ROOT / base).rglob("*"):
            if path.suffix in {".py", ".js", ".html", ".css"} and legacy.search(path.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_public_frontend_has_no_classes_surface_or_school_checkout():
    js = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "app/static/js").rglob("*.js"))
    for forbidden in ("صفوفي", "/classes", "باقة المدرسة", "اشترك في باقة", "برو عبر الصف", "تجربة المدرسة"):
        assert forbidden not in js, forbidden
    assert not (ROOT / "app/static/js/views/classes.js").exists()
