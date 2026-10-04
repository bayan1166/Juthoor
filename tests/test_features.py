import uuid

import pytest

from app.config import settings
from tests.helpers import handle_of, make_internal_admin, register, register_parent, set_plan

STUDENT_QUESTIONS_LIMIT = 20
TUTOR_LIMIT = 5


def answer_wrong(client, student):
    q = client.get(f"/students/{student['id']}/adaptive/question", headers=student["headers"])
    if q.status_code != 200:
        return q
    return client.post(
        f"/students/{student['id']}/adaptive/answer", json={"selected_answer": "zzz"}, headers=student["headers"]
    )


def test_health_reports_demo_flag_and_tutor_mode(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["demo"] is False and body["ai_tutor"] == "offline_fallback"


def test_basic_plan_daily_question_limit(client, db):
    student = register(client)
    for _ in range(STUDENT_QUESTIONS_LIMIT):
        assert answer_wrong(client, student).status_code == 200
    blocked = client.get(f"/students/{student['id']}/adaptive/question", headers=student["headers"])
    assert blocked.status_code == 402
    assert blocked.json()["detail"].startswith("daily_limit_reached")
    boot = client.get(f"/students/{student['id']}/adaptive/bootstrap", headers=student["headers"]).json()
    assert boot["plan"]["remaining"]["questions"] == 0
    set_plan(db, student["id"], "pro")
    assert client.get(f"/students/{student['id']}/adaptive/question", headers=student["headers"]).status_code == 200


def test_basic_plan_tutor_limit_and_offline_tutor_solves(client, db):
    student = register(client)
    start = client.post(
        f"/students/{student['id']}/chat/start", json={"skill_context": "adding_integers"}, headers=student["headers"]
    ).json()
    sid = start["session_id"]
    first = client.post(
        f"/students/{student['id']}/chat/message",
        json={"session_id": sid, "message": "7 + (-3)"},
        headers=student["headers"],
    )
    assert first.status_code == 200
    assert "4" in first.json()["reply"]
    assert first.json()["remaining_today"] == TUTOR_LIMIT - 1
    for _ in range(TUTOR_LIMIT - 1):
        res = client.post(
            f"/students/{student['id']}/chat/message",
            json={"session_id": sid, "message": "اشرح لي الجمع"},
            headers=student["headers"],
        )
        assert res.status_code == 200
    blocked = client.post(
        f"/students/{student['id']}/chat/message",
        json={"session_id": sid, "message": "اشرح لي الجمع"},
        headers=student["headers"],
    )
    assert blocked.status_code == 402 and blocked.json()["detail"] == "daily_limit_reached:tutor"
    history = client.get(f"/students/{student['id']}/chat/sessions/{sid}/messages", headers=student["headers"])
    assert history.status_code == 200 and len(history.json()) >= 2 * TUTOR_LIMIT


def test_chat_session_belongs_to_its_student(client):
    owner = register(client)
    other = register(client)
    sid = client.post(
        f"/students/{owner['id']}/chat/start", json={"skill_context": "adding_integers"}, headers=owner["headers"]
    ).json()["session_id"]
    res = client.get(f"/students/{other['id']}/chat/sessions/{sid}/messages", headers=other["headers"])
    assert res.status_code == 404


def test_friend_request_chat_read_receipts(client):
    a, b, c = register(client), register(client), register(client)
    found = client.get("/community/search", params={"q": handle_of(client, b)}, headers=a["headers"]).json()
    assert len(found) == 1 and "email" not in found[0] and found[0]["friendship_status"] is None
    assert client.post(f"/community/request/{b['id']}", headers=a["headers"]).status_code == 200
    incoming = client.get("/community/requests", headers=b["headers"]).json()
    assert len(incoming) == 1 and incoming[0]["is_incoming"] is True
    assert client.post(f"/community/accept/{incoming[0]['friendship_id']}", headers=a["headers"]).status_code == 403
    assert client.post(f"/community/accept/{incoming[0]['friendship_id']}", headers=b["headers"]).status_code == 200
    assert client.post(f"/community/messages/{c['id']}", json={"body": "hi"}, headers=a["headers"]).status_code == 403
    assert client.post(f"/community/messages/{b['id']}", json={"body": "   "}, headers=a["headers"]).status_code == 422
    sent = client.post(f"/community/messages/{b['id']}", json={"body": "hello"}, headers=a["headers"])
    assert sent.status_code == 200 and sent.json()["created_at"].endswith("Z")
    convs = client.get("/community/conversations", headers=b["headers"]).json()
    assert convs[0]["unread"] == 1 and convs[0]["last_message"]["body"] == "hello"
    assert client.get("/community/summary", headers=b["headers"]).json()["unread_messages"] == 1
    assert client.post(f"/community/messages/{a['id']}/read", headers=b["headers"]).json()["marked"] == 1
    assert client.get("/community/summary", headers=b["headers"]).json()["unread_messages"] == 0
    seen = client.get(f"/community/messages/{b['id']}", headers=a["headers"]).json()
    assert seen[0]["read_at"] is not None
    client.post(f"/community/messages/{b['id']}", json={"body": "second"}, headers=a["headers"])
    newer = client.get(f"/community/messages/{b['id']}", params={"after": seen[0]["created_at"]}, headers=a["headers"]).json()
    assert [m["body"] for m in newer][-1] == "second"


def test_basic_plan_allows_three_friends(client):
    me = register(client)
    others = [register(client) for _ in range(4)]
    for other in others[:3]:
        req = client.post(f"/community/request/{other['id']}", headers=me["headers"])
        assert req.status_code == 200
        pending = client.get("/community/requests", headers=other["headers"]).json()[0]
        assert client.post(f"/community/accept/{pending['friendship_id']}", headers=other["headers"]).status_code == 200
    fourth = client.post(f"/community/request/{others[3]['id']}", headers=me["headers"])
    assert fourth.status_code == 402 and fourth.json()["detail"] == "friend_limit_reached"


def test_payment_catalogue_is_public_and_priced_in_jod(client):
    body = client.get("/payments/plans").json()
    assert body["currency"] == "JOD"
    by_id = {p["id"]: p for p in body["plans"]}
    assert list(by_id) == ["basic", "pro"]
    assert by_id["basic"]["price_month"] == 0 and by_id["basic"]["price_year"] == 0
    assert by_id["pro"]["price_month"] == 4500 and by_id["pro"]["price_year"] == 32000
    assert by_id["basic"]["limits"]["questions_per_day"] == STUDENT_QUESTIONS_LIMIT
    assert body["usp"]["name"]


def test_student_buys_pro_with_mock_card(client):
    student = register(client)
    start = client.post("/payments/checkout", json={"plan": "pro", "period": "yearly"}, headers=student["headers"])
    assert start.status_code == 200 and start.json()["amount_minor"] == 32000 and start.json()["provider"] == "mock"
    sid = start.json()["session_id"]
    bad = client.post("/payments/confirm", json={"session_id": sid, "card_last4": "42", "card_holder": "Lian"}, headers=student["headers"])
    assert bad.status_code == 422
    done = client.post("/payments/confirm", json={"session_id": sid, "card_last4": "4242", "card_holder": "Lian"}, headers=student["headers"])
    assert done.status_code == 200 and done.json()["status"] == "succeeded"
    me = client.get("/auth/me", headers=student["headers"]).json()
    assert me["plan"] == "pro" and me["plan_source"] == "own" and me["plan_expires_at"].endswith("Z")
    again = client.post("/payments/confirm", json={"session_id": sid, "card_last4": "4242", "card_holder": "Lian"}, headers=student["headers"])
    assert again.status_code == 409


def test_plan_purchase_rules_by_role(client, db):
    student = register(client)
    internal = register(client)
    make_internal_admin(db, internal["id"])
    assert client.post("/payments/checkout", json={"plan": "school"}, headers=student["headers"]).status_code == 422
    assert client.post("/payments/checkout", json={"plan": "basic"}, headers=student["headers"]).status_code == 422
    for period in ("monthly", "yearly"):
        r = client.post("/payments/checkout", json={"plan": "pro", "period": period}, headers=internal["headers"])
        assert r.status_code == 403 and r.json()["detail"] == "pro_plan_for_students"
    teacher_signup = client.post("/auth/register", json={"email": "t@test.com", "password": "secret123", "full_name": "T", "role": "teacher"})
    assert teacher_signup.status_code == 422


def test_parent_buys_pro_for_child(client):
    parent = register_parent(client)
    child = parent["child"]
    stranger = register(client)
    assert client.post("/payments/checkout", json={"plan": "pro"}, headers=parent["headers"]).status_code == 400
    assert client.post("/payments/checkout", json={"plan": "pro", "for_student_id": stranger["id"]}, headers=parent["headers"]).status_code == 403
    start = client.post("/payments/checkout", json={"plan": "pro", "for_student_id": child["id"]}, headers=parent["headers"])
    assert start.status_code == 200
    client.post("/payments/confirm", json={"session_id": start.json()["session_id"], "card_last4": "4242", "card_holder": "Parent"}, headers=parent["headers"])
    assert client.get("/auth/me", headers=child["headers"]).json()["plan"] == "pro"
    assert client.get("/auth/me", headers=parent["headers"]).json()["plan"] == "basic"
    assert client.get(f"/students/{child['id']}/adaptive/report", headers=parent["headers"]).status_code == 200


def test_password_reset_three_step_flow(client, monkeypatch):
    sent = {}
    monkeypatch.setattr("app.routers.auth._deliver_code", lambda email, code: sent.update(email=email, code=code))
    user = register(client)
    res = client.post("/auth/forgot-password", json={"email": user["email"]})
    assert res.status_code == 200 and "demo_code" not in res.json()
    code = sent["code"]
    assert len(code) == 6 and code.isdigit()
    wrong = "000000" if code != "000000" else "111111"
    assert client.post("/auth/verify-reset-code", json={"email": user["email"], "code": wrong}).status_code == 400
    verified = client.post("/auth/verify-reset-code", json={"email": user["email"], "code": code})
    assert verified.status_code == 200
    token = verified.json()["reset_token"]
    assert client.post("/auth/reset-password", json={"reset_token": token, "new_password": "123"}).status_code == 422
    done = client.post("/auth/reset-password", json={"reset_token": token, "new_password": "brandnew1"})
    assert done.status_code == 200 and done.json()["access_token"]
    assert client.post("/auth/login", json={"email": user["email"], "password": "brandnew1"}).status_code == 200
    assert client.post("/auth/login", json={"email": user["email"], "password": "secret123"}).status_code == 401
    assert client.post("/auth/reset-password", json={"reset_token": token, "new_password": "another11"}).status_code == 400
    sent.clear()
    unknown = client.post("/auth/forgot-password", json={"email": "nobody@test.com"})
    assert unknown.status_code == 200 and not sent


def test_tree_endpoint_and_public_curriculum_map(client):
    student = register(client)
    res = client.get(f"/students/{student['id']}/adaptive/tree", headers=student["headers"])
    assert res.status_code == 200, res.text
    tree = res.json()
    lessons = [lesson for unit in tree["units"] for lesson in unit["lessons"]]
    assert [u["no"] for u in tree["units"]] == [1, 2, 3, 4] and len(lessons) == 18
    assert lessons[0]["key"] == "u1l1" and lessons[0]["current"] is True and lessons[0]["status"] in ("open", "learning")
    assert tree["root_gap"]["found"] is False
    public = client.get("/curriculum/map")
    assert public.status_code == 200 and len(public.json()["units"]) == 4


def test_avatar_options_previews_and_ownership(client):
    student = register(client)
    base = f"/students/{student['id']}/economy"
    options = client.get(f"{base}/options", headers=student["headers"]).json()
    assert options["skins"] and options["hair_styles"] and options["hair_colors"]
    previews = client.get(f"{base}/previews", headers=student["headers"]).json()
    assert any(k.startswith("skin:") for k in previews) and all("svg" in v for v in previews.values())
    from app.engine import avatar_items as ai
    assert client.get(f"{base}/catalog", headers=student["headers"]).status_code == 404  # the coin shop is gone
    locked = next(item for item in ai.CATALOG if item.cat == "clothing" and item.price > 0)
    avatar = client.get(f"{base}/avatar", headers=student["headers"]).json()
    res = client.put(f"{base}/avatar", json={**avatar, "clothing": locked.id}, headers=student["headers"])
    assert res.status_code == 403
    saved = client.put(f"{base}/avatar", json={**avatar, "skin": options["skins"][-1]["id"]}, headers=student["headers"])
    assert saved.status_code == 200 and saved.json()["svg"].startswith("<svg")


def make_friends(client, a, b):
    assert client.post(f"/community/request/{b['id']}", headers=a["headers"]).status_code == 200
    pending = client.get("/community/requests", headers=b["headers"]).json()[0]
    assert client.post(f"/community/accept/{pending['friendship_id']}", headers=b["headers"]).status_code == 200


def test_login_lockout_after_repeated_failures(client, monkeypatch):
    from app.ratelimit import limiter
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    limiter.reset()
    try:
        user = register(client)
        for _ in range(5):
            res = client.post("/auth/login", json={"email": user["email"], "password": "wrong-pass"})
            assert res.status_code == 401
        blocked = client.post("/auth/login", json={"email": user["email"], "password": "secret123"})
        assert blocked.status_code == 429 and blocked.json()["detail"] == "too_many_attempts"
        assert int(blocked.headers["retry-after"]) >= 1
        other = register(client)
        assert client.post("/auth/login", json={"email": other["email"], "password": "secret123"}).status_code == 200
    finally:
        limiter.reset()


def test_successful_login_resets_the_failure_counter(client, monkeypatch):
    from app.ratelimit import limiter
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    limiter.reset()
    try:
        user = register(client)
        for _ in range(4):
            assert client.post("/auth/login", json={"email": user["email"], "password": "bad-pass"}).status_code == 401
        assert client.post("/auth/login", json={"email": user["email"], "password": "secret123"}).status_code == 200
        for _ in range(4):
            assert client.post("/auth/login", json={"email": user["email"], "password": "bad-pass"}).status_code == 401
    finally:
        limiter.reset()


def test_login_is_case_insensitive_on_email(client):
    user = register(client)
    res = client.post("/auth/login", json={"email": user["email"].upper().replace("@TEST.COM", "@test.com"), "password": "secret123"})
    assert res.status_code == 200


def test_forgot_password_is_rate_limited_per_email(client, monkeypatch):
    from app.ratelimit import limiter
    monkeypatch.setattr("app.routers.auth._deliver_code", lambda email, code: None)
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    limiter.reset()
    try:
        user = register(client)
        for _ in range(3):
            assert client.post("/auth/forgot-password", json={"email": user["email"]}).status_code == 200
        blocked = client.post("/auth/forgot-password", json={"email": user["email"]})
        assert blocked.status_code == 429 and blocked.json()["detail"] == "rate_limited"
    finally:
        limiter.reset()


def test_security_headers_are_present(client):
    res = client.get("/health")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert "referrer-policy" in res.headers


def test_startup_refuses_a_weak_jwt_secret(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setattr(settings, "jwt_secret", "change-me")
    monkeypatch.setattr(settings, "demo_mode", False)
    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass


def test_student_chat_blocks_links_and_contact_details(client):
    a, b = register(client), register(client)
    make_friends(client, a, b)
    for text, kind in [("www.example.com", "link"), ("0791234567", "contact"), ("ضيفني واتساب", "contact")]:
        res = client.post(f"/community/messages/{b['id']}", json={"body": text}, headers=a["headers"])
        assert res.status_code == 422 and res.json()["detail"] == f"message_not_allowed:{kind}", text
    ok = client.post(f"/community/messages/{b['id']}", json={"body": "7 + (-3) = 4"}, headers=a["headers"])
    assert ok.status_code == 200


def test_block_hides_users_and_stops_messages(client):
    a, b = register(client), register(client)
    make_friends(client, a, b)
    assert client.post(f"/community/block/{a['id']}", headers=a["headers"]).status_code == 400
    assert client.post(f"/community/block/{b['id']}", headers=a["headers"]).status_code == 200
    assert client.post(f"/community/messages/{a['id']}", json={"body": "hi"}, headers=b["headers"]).status_code == 403
    assert client.post(f"/community/messages/{b['id']}", json={"body": "hi"}, headers=a["headers"]).status_code == 403
    assert client.get("/community/search", params={"q": handle_of(client, a)}, headers=b["headers"]).json() == []
    assert client.post(f"/community/request/{a['id']}", headers=b["headers"]).status_code == 404
    again = client.post(f"/community/request/{b['id']}", headers=a["headers"])
    assert again.status_code == 409 and again.json()["detail"] == "unblock_first"
    assert len(client.get("/community/blocked", headers=a["headers"]).json()) == 1
    assert client.get("/community/blocked", headers=b["headers"]).json() == []
    assert client.get("/community/conversations", headers=a["headers"]).json() == []
    assert client.delete(f"/community/block/{a['id']}", headers=b["headers"]).status_code == 404
    assert client.delete(f"/community/block/{b['id']}", headers=a["headers"]).status_code == 200
    assert client.post(f"/community/request/{b['id']}", headers=a["headers"]).status_code == 200


def test_report_flow_and_internal_moderation_review(client, db):
    a, b = register(client), register(client)
    make_friends(client, a, b)
    sent = client.post(f"/community/messages/{b['id']}", json={"body": "you are annoying"}, headers=a["headers"]).json()
    bad = client.post("/community/report", json={"user_id": a["id"], "message_id": sent["message_id"], "reason": "nope"}, headers=b["headers"])
    assert bad.status_code == 422
    body = {"user_id": a["id"], "message_id": sent["message_id"], "reason": "bullying", "details": "keeps insulting me", "also_block": True}
    first = client.post("/community/report", json=body, headers=b["headers"])
    assert first.status_code == 200 and first.json()["duplicate"] is False
    assert client.post("/community/report", json=body, headers=b["headers"]).json()["duplicate"] is True
    assert client.post("/community/report", json={"user_id": b["id"], "reason": "spam"}, headers=b["headers"]).status_code == 400
    wrong = client.post("/community/report", json={"user_id": b["id"], "message_id": sent["message_id"], "reason": "spam"}, headers=a["headers"])
    assert wrong.status_code == 404
    assert client.post(f"/community/messages/{a['id']}", json={"body": "hi"}, headers=b["headers"]).status_code == 403
    moderator = register(client)
    make_internal_admin(db, moderator["id"])
    reports = client.get("/moderation/reports", headers=moderator["headers"]).json()
    assert len(reports) == 1 and reports[0]["reason"] == "bullying" and reports[0]["reported"]["user_id"] == a["id"]
    rid = reports[0]["report_id"]
    thread = client.get(f"/moderation/reports/{rid}", headers=moderator["headers"]).json()["thread"]
    assert any(m["flagged"] and m["body"] == "you are annoying" for m in thread)
    parent = register_parent(client)
    for outsider in (parent, a, b):
        assert client.get("/moderation/reports", headers=outsider["headers"]).status_code == 403
        assert client.post(f"/moderation/reports/{rid}/resolve", json={"action": "resolved"}, headers=outsider["headers"]).status_code == 403
    assert client.get(f"/moderation/reports/{uuid.uuid4()}", headers=moderator["headers"]).status_code == 404
    resolved = client.post(f"/moderation/reports/{rid}/resolve", json={"action": "resolved", "note": "talked to both"}, headers=moderator["headers"])
    assert resolved.status_code == 200 and resolved.json()["status"] == "resolved"
    assert client.get("/moderation/reports", headers=moderator["headers"]).json() == []
    done = client.get("/moderation/reports", params={"status_filter": "resolved"}, headers=moderator["headers"]).json()
    assert len(done) == 1 and done[0]["resolution_note"] == "talked to both"


def test_a_named_gap_reaches_the_learner_and_their_parent_only(client, db):
    from app.models.adaptive import StudentAdaptiveState
    from app.models.org import User
    from scripts import seed_demo
    kid = register(client)
    parent = register_parent(client, kid)
    set_plan(db, kid["id"], "pro")
    row = db.get(StudentAdaptiveState, uuid.UUID(kid["id"]))
    row.current_skill = "mult_div_integers"
    db.commit()
    seed_demo.miss_until_gap(db, db.get(User, uuid.UUID(kid["id"])))
    state = client.get(f"/students/{kid['id']}/adaptive/state", headers=kid["headers"]).json()
    gaps = [k["skill_id"] for k in state["skills"] if k["status"] == "gap"]
    assert gaps
    tree = client.get(f"/students/{kid['id']}/adaptive/tree", headers=parent["headers"]).json()
    assert tree["root_gap"]["found"] and not tree["root_gap"]["locked"] and tree["root_gap"]["skill"] in gaps
    report = client.get(f"/students/{kid['id']}/adaptive/report", headers=parent["headers"]).json()
    assert report["gap_locked"] is False and report["plan"]["plan"] == "pro"
    stranger = register_parent(client)  # parent of another child
    assert client.get(f"/students/{kid['id']}/adaptive/tree", headers=stranger["headers"]).status_code == 403


def test_health_reports_judge_flag(client, monkeypatch):
    monkeypatch.setattr(settings, "judge_mode", True)
    assert client.get("/health").json()["judge"] is True
    monkeypatch.setattr(settings, "judge_mode", False)
    assert client.get("/health").json()["judge"] is False


def test_judge_mode_never_returns_429(client, monkeypatch):
    from app.ratelimit import limiter
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "judge_mode", True)
    limiter.reset()
    try:
        user = register(client)
        for _ in range(12):
            res = client.post("/auth/login", json={"email": user["email"], "password": "wrong-pass"})
            assert res.status_code == 401
        assert client.post("/auth/login", json={"email": user["email"], "password": "secret123"}).status_code == 200
        for _ in range(6):
            assert client.post("/auth/forgot-password", json={"email": user["email"]}).status_code == 200
    finally:
        limiter.reset()


def test_off_topic_tutor_message_gets_fixed_fallback_without_using_quota(client):
    from app.services.rag.guardrail import FALLBACK
    user = register(client)
    sid = user["id"]
    chat = client.post(f"/students/{sid}/chat/start", json={"skill_context": "adding_integers"}, headers=user["headers"]).json()
    before = client.get("/auth/me", headers=user["headers"]).json()
    first = client.post(f"/students/{sid}/chat/message", json={"session_id": chat["session_id"], "message": "ما هي عاصمة فرنسا"}, headers=user["headers"])
    assert first.status_code == 200 and first.json()["reply"] == FALLBACK
    remaining = first.json()["remaining_today"]
    for _ in range(8):
        again = client.post(f"/students/{sid}/chat/message", json={"session_id": chat["session_id"], "message": "write me a poem about the sea"}, headers=user["headers"])
        assert again.status_code == 200 and again.json()["reply"] == FALLBACK and again.json()["remaining_today"] == remaining
    ontopic = client.post(f"/students/{sid}/chat/message", json={"session_id": chat["session_id"], "message": "5 + (-2)"}, headers=user["headers"])
    assert ontopic.status_code == 200 and ontopic.json()["reply"] != FALLBACK
    assert ontopic.json()["source"] == "solver" and first.json()["source"] == "guardrail"
    assert before["user_id"] == sid
