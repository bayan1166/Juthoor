import uuid

import pytest

from app.config import settings
from tests.helpers import handle_of, register, set_plan

STUDENT_QUESTIONS_LIMIT = 20
TUTOR_LIMIT = 5


def teacher_with_class(client, name="Class A"):
    teacher = register(client, "teacher")
    res = client.post("/classrooms", json={"name": name}, headers=teacher["headers"])
    assert res.status_code == 200, res.text
    return teacher, res.json()


def join(client, student, room):
    res = client.post("/classrooms/join", json={"join_code": room["join_code"]}, headers=student["headers"])
    assert res.status_code == 200, res.text
    return res.json()


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


def test_teacher_gets_school_trial(client):
    teacher = register(client, "teacher")
    me = client.get("/auth/me", headers=teacher["headers"]).json()
    assert me["plan"] == "school" and me["plan_source"] == "trial" and me["trial_days_left"] in (13, 14)


def test_only_teachers_with_school_plan_create_classrooms(client, db):
    student = register(client)
    assert client.post("/classrooms", json={"name": "x1"}, headers=student["headers"]).status_code == 403
    teacher = register(client, "teacher")
    set_plan(db, teacher["id"], "basic")
    res = client.post("/classrooms", json={"name": "Expired"}, headers=teacher["headers"])
    assert res.status_code == 402 and res.json()["detail"].startswith("plan_upgrade_required")


def test_joining_a_classroom_sponsors_pro(client):
    teacher, room = teacher_with_class(client)
    student = register(client)
    assert client.get("/auth/me", headers=student["headers"]).json()["plan"] == "basic"
    join(client, student, room)
    me = client.get("/auth/me", headers=student["headers"]).json()
    assert me["plan"] == "pro" and me["plan_source"] == "class"
    assert client.post("/classrooms/join", json={"join_code": "NOPE00"}, headers=student["headers"]).status_code == 404
    assert client.post("/classrooms/join", json={"join_code": room["join_code"]}, headers=teacher["headers"]).status_code == 403


def test_assignment_upload_grade_download(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    teacher, room = teacher_with_class(client)
    student = register(client)
    other = register(client)
    join(client, student, room)
    cid = room["classroom_id"]
    created = client.post(
        f"/classrooms/{cid}/assignments",
        json={"title": "Homework", "max_score": 50, "skill_id": "adding_integers"},
        headers=teacher["headers"],
    )
    assert created.status_code == 200, created.text
    aid = created.json()["assignment_id"]
    assert client.post(
        f"/classrooms/{cid}/assignments", json={"title": "Nope"}, headers=student["headers"]
    ).status_code == 403
    url = f"/classrooms/assignments/{aid}/submit"
    assert client.post(url, data={"text": ""}, headers=student["headers"]).status_code == 422
    bad = client.post(url, data={"text": "x"}, files={"file": ("x.exe", b"MZ", "application/octet-stream")}, headers=student["headers"])
    assert bad.status_code == 422 and bad.json()["detail"] == "file_type_not_allowed"
    payload = b"%PDF-1.4 student work"
    sub = client.post(url, data={"text": "my answer"}, files={"file": ("work.pdf", payload, "application/pdf")}, headers=student["headers"])
    assert sub.status_code == 200, sub.text
    sid = sub.json()["submission_id"]
    assert sub.json()["has_file"] is True
    detail = client.get(f"/classrooms/assignments/{aid}", headers=teacher["headers"]).json()
    assert detail["students"][0]["submission"]["submission_id"] == sid
    download = client.get(f"/classrooms/submissions/{sid}/file", headers=teacher["headers"])
    assert download.status_code == 200 and download.content == payload
    assert client.get(f"/classrooms/submissions/{sid}/file", headers=other["headers"]).status_code == 403
    assert client.post(f"/classrooms/submissions/{sid}/grade", json={"score": 51}, headers=teacher["headers"]).status_code == 422
    assert client.post(f"/classrooms/submissions/{sid}/grade", json={"score": 45, "feedback": "well done"}, headers=student["headers"]).status_code == 403
    graded = client.post(f"/classrooms/submissions/{sid}/grade", json={"score": 45, "feedback": "well done"}, headers=teacher["headers"])
    assert graded.status_code == 200 and graded.json()["score"] == 45
    assert client.post(url, data={"text": "late edit"}, headers=student["headers"]).status_code == 409
    mine = client.get("/classrooms/assignments", headers=student["headers"]).json()
    assert mine[0]["state"] == "graded" and mine[0]["submission"]["feedback"] == "well done"
    listing = client.get("/classrooms/assignments", headers=teacher["headers"]).json()
    assert listing[0]["submissions"] == 1 and listing[0]["graded"] == 1 and listing[0]["members"] == 1


def test_quiz_race_flow(client):
    teacher, room = teacher_with_class(client)
    student = register(client)
    join(client, student, room)
    cid = room["classroom_id"]
    made = client.post(
        f"/classrooms/{cid}/quizzes/generate",
        json={"title": "Race", "skill_id": "adding_integers", "count": 5, "mode": "race", "time_limit_seconds": 120},
        headers=teacher["headers"],
    )
    assert made.status_code == 200, made.text
    qid = made.json()["quiz_id"]
    start = client.post(f"/classrooms/quizzes/{qid}/start", headers=student["headers"])
    assert start.status_code == 200
    questions = start.json()["questions"]
    assert len(questions) >= 3 and all("correct_index" not in q for q in questions)
    resume = client.post(f"/classrooms/quizzes/{qid}/start", headers=student["headers"])
    assert [q["id"] for q in resume.json()["questions"]] == [q["id"] for q in questions]
    answers = {q["id"]: 0 for q in questions}
    done = client.post(f"/classrooms/quizzes/{qid}/submit", json={"answers": answers}, headers=student["headers"])
    assert done.status_code == 200, done.text
    body = done.json()
    assert body["total"] == len(questions) and body["rank"] == 1 and len(body["review"]) == len(questions)
    assert client.post(f"/classrooms/quizzes/{qid}/submit", json={"answers": answers}, headers=student["headers"]).status_code == 409
    assert client.post(f"/classrooms/quizzes/{qid}/start", headers=student["headers"]).status_code == 409
    board = client.get(f"/classrooms/quizzes/{qid}/leaderboard", headers=student["headers"]).json()
    assert len(board["rows"]) == 1 and board["rows"][0]["rank"] == 1
    class_board = client.get(f"/classrooms/{cid}/leaderboard", headers=teacher["headers"]).json()
    assert class_board["rows"][0]["quizzes_taken"] == 1
    assert client.delete(f"/classrooms/quizzes/{qid}/attempts/{student['id']}", headers=student["headers"]).status_code == 403
    assert client.delete(f"/classrooms/quizzes/{qid}/attempts/{student['id']}", headers=teacher["headers"]).status_code == 200
    closed = client.patch(f"/classrooms/quizzes/{qid}", json={"is_open": False}, headers=teacher["headers"])
    assert closed.status_code == 200 and closed.json()["is_open"] is False
    shut = client.post(f"/classrooms/quizzes/{qid}/start", headers=student["headers"])
    assert shut.status_code == 409 and shut.json()["detail"] == "quiz_closed"


def test_manual_quiz_validation(client):
    teacher, room = teacher_with_class(client)
    cid = room["classroom_id"]
    bad = client.post(
        f"/classrooms/{cid}/quizzes",
        json={"title": "Bad", "questions": [{"prompt": "2+2", "options": ["3", "4"], "correct_index": 5}]},
        headers=teacher["headers"],
    )
    assert bad.status_code == 422
    dup = client.post(
        f"/classrooms/{cid}/quizzes",
        json={"title": "Dup", "questions": [{"prompt": "2+2", "options": ["4", "4"], "correct_index": 0}]},
        headers=teacher["headers"],
    )
    assert dup.status_code == 422
    good = client.post(
        f"/classrooms/{cid}/quizzes",
        json={"title": "Good", "questions": [{"prompt": "2+2", "options": ["3", "4", "5"], "correct_index": 1, "points": 50}]},
        headers=teacher["headers"],
    )
    assert good.status_code == 200 and good.json()["question_count"] == 1


def test_class_analytics_and_csv_export(client):
    teacher, room = teacher_with_class(client)
    student = register(client)
    join(client, student, room)
    answer_wrong(client, student)
    cid = room["classroom_id"]
    report = client.get(f"/classrooms/{cid}/analytics", headers=teacher["headers"])
    assert report.status_code == 200, report.text
    data = report.json()
    assert data["kpis"]["students"] == 1 and len(data["activity"]) == 7
    row = data["students"][0]
    assert row["answered"] == 1 and row["risk"] in ("low", "medium", "high", "inactive")
    assert len(data["skill_mastery"]) >= 5
    assert client.get(f"/classrooms/{cid}/analytics", headers=student["headers"]).status_code == 403
    csv_res = client.get(f"/classrooms/{cid}/export.csv", headers=teacher["headers"])
    assert csv_res.status_code == 200 and csv_res.headers["content-type"].startswith("text/csv")
    assert csv_res.content.startswith(b"\xef\xbb\xbf")
    assert client.get(f"/students/{student['id']}/adaptive/report", headers=teacher["headers"]).status_code == 200


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
    assert list(by_id) == ["basic", "pro", "school"]
    assert by_id["pro"]["price_month"] == 2990 and by_id["school"]["price_year"] == 69900
    assert by_id["basic"]["limits"]["questions_per_day"] == STUDENT_QUESTIONS_LIMIT
    assert body["usp"]["name"]


def test_student_buys_pro_with_mock_card(client):
    student = register(client)
    start = client.post("/payments/checkout", json={"plan": "pro", "period": "yearly"}, headers=student["headers"])
    assert start.status_code == 200 and start.json()["amount_minor"] == 29900 and start.json()["provider"] == "mock"
    sid = start.json()["session_id"]
    bad = client.post("/payments/confirm", json={"session_id": sid, "card_last4": "42", "card_holder": "Lian"}, headers=student["headers"])
    assert bad.status_code == 422
    done = client.post("/payments/confirm", json={"session_id": sid, "card_last4": "4242", "card_holder": "Lian"}, headers=student["headers"])
    assert done.status_code == 200 and done.json()["status"] == "succeeded"
    me = client.get("/auth/me", headers=student["headers"]).json()
    assert me["plan"] == "pro" and me["plan_source"] == "own" and me["plan_expires_at"].endswith("Z")
    again = client.post("/payments/confirm", json={"session_id": sid, "card_last4": "4242", "card_holder": "Lian"}, headers=student["headers"])
    assert again.status_code == 409


def test_plan_purchase_rules_by_role(client):
    student = register(client)
    teacher = register(client, "teacher")
    assert client.post("/payments/checkout", json={"plan": "school"}, headers=student["headers"]).status_code == 403
    assert client.post("/payments/checkout", json={"plan": "pro"}, headers=teacher["headers"]).status_code == 403
    assert client.post("/payments/checkout", json={"plan": "basic"}, headers=student["headers"]).status_code == 422
    start = client.post("/payments/checkout", json={"plan": "school"}, headers=teacher["headers"])
    assert start.status_code == 200 and start.json()["amount_minor"] == 6990
    client.post("/payments/confirm", json={"session_id": start.json()["session_id"], "card_last4": "4242", "card_holder": "Sara"}, headers=teacher["headers"])
    me = client.get("/auth/me", headers=teacher["headers"]).json()
    assert me["plan"] == "school" and me["plan_source"] == "own" and me["trial_days_left"] is None


def test_parent_buys_pro_for_child(client):
    parent = register(client, "parent")
    child = register(client, "student", guardian_email=parent["email"])
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
    catalog = client.get(f"{base}/catalog", headers=student["headers"]).json()
    locked = next(item for item in catalog if not item["owned"] and item["category"] == "clothing")
    avatar = client.get(f"{base}/avatar", headers=student["headers"]).json()
    res = client.put(f"{base}/avatar", json={**avatar, "clothing": locked["id"]}, headers=student["headers"])
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


def test_report_flow_and_teacher_review(client):
    teacher, room = teacher_with_class(client)
    cid = room["classroom_id"]
    a, b = register(client), register(client)
    join(client, a, room)
    join(client, b, room)
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
    reports = client.get(f"/classrooms/{cid}/safety/reports", headers=teacher["headers"]).json()
    assert len(reports) == 1 and reports[0]["reason"] == "bullying" and reports[0]["reported"]["user_id"] == a["id"]
    rid = reports[0]["report_id"]
    thread = client.get(f"/classrooms/{cid}/safety/reports/{rid}", headers=teacher["headers"]).json()["thread"]
    assert any(m["flagged"] and m["body"] == "you are annoying" for m in thread)
    other_teacher = register(client, "teacher")
    assert client.get(f"/classrooms/{cid}/safety/reports", headers=other_teacher["headers"]).status_code == 403
    assert client.get(f"/classrooms/{cid}/safety/reports", headers=a["headers"]).status_code == 403
    resolved = client.post(f"/classrooms/{cid}/safety/reports/{rid}/resolve", json={"action": "resolved", "note": "talked to both"}, headers=teacher["headers"])
    assert resolved.status_code == 200 and resolved.json()["status"] == "resolved"
    assert client.get(f"/classrooms/{cid}/safety/reports", headers=teacher["headers"]).json() == []
    done = client.get(f"/classrooms/{cid}/safety/reports", params={"status_filter": "resolved"}, headers=teacher["headers"]).json()
    assert len(done) == 1 and done[0]["resolution_note"] == "talked to both"


def test_one_click_remediation_targets_gap_students(client, db):
    from app.models.adaptive import StudentAdaptiveState
    from app.models.org import User
    from scripts import seed_demo
    teacher, room = teacher_with_class(client)
    cid = room["classroom_id"]
    struggling, fine = register(client), register(client)
    join(client, struggling, room)
    join(client, fine, room)
    row = db.get(StudentAdaptiveState, uuid.UUID(struggling["id"]))
    row.current_skill = "mult_div_integers"
    db.commit()
    seed_demo.miss_until_gap(db, db.get(User, uuid.UUID(struggling["id"])))
    report = client.get(f"/classrooms/{cid}/analytics", headers=teacher["headers"]).json()
    rows = {r["user_id"]: r for r in report["students"]}
    gap_ids = rows[struggling["id"]]["root_gap_ids"]
    assert gap_ids and rows[fine["id"]]["root_gap_ids"] == []
    skill = gap_ids[0]
    assert client.post(f"/classrooms/{cid}/remediation", json={"skill_id": skill}, headers=struggling["headers"]).status_code == 403
    res = client.post(f"/classrooms/{cid}/remediation", json={"skill_id": skill, "due_days": 4}, headers=teacher["headers"])
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["count"] == 1 and body["students"][0]["user_id"] == struggling["id"] and body["tip"]
    assert body["assignment"]["kind"] == "remediation" and body["assignment"]["targeted"] is True
    aid = body["assignment"]["assignment_id"]
    mine = client.get("/classrooms/assignments", headers=struggling["headers"]).json()
    assert len(mine) == 1 and mine[0]["kind"] == "remediation"
    assert client.get("/classrooms/assignments", headers=fine["headers"]).json() == []
    assert client.get(f"/classrooms/assignments/{aid}", headers=fine["headers"]).status_code == 404
    assert client.post(f"/classrooms/assignments/{aid}/submit", data={"text": "done"}, headers=fine["headers"]).status_code == 403
    assert client.post(f"/classrooms/assignments/{aid}/submit", data={"text": "done"}, headers=struggling["headers"]).status_code == 200
    listing = client.get("/classrooms/assignments", headers=teacher["headers"]).json()
    assert listing[0]["members"] == 1 and listing[0]["submissions"] == 1
    later = client.get(f"/classrooms/{cid}/analytics", headers=teacher["headers"]).json()
    totals = {r["user_id"]: r["assignments_total"] for r in later["students"]}
    assert totals[struggling["id"]] == 1 and totals[fine["id"]] == 0
    empty = client.post(f"/classrooms/{cid}/remediation", json={"skill_id": "absolute_value"}, headers=teacher["headers"])
    assert empty.status_code == 422 and empty.json()["detail"] == "no_students_with_gap"


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
