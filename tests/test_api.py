import uuid

from app.models.adaptive import DrillDownEvent, StudentAdaptiveState
from app.models.org import Organization
from tests.helpers import register, set_plan


def q_url(s):
    return f"/students/{s['id']}/adaptive/question"


def a_url(s):
    return f"/students/{s['id']}/adaptive/answer"


def get_question(client, s):
    r = client.get(q_url(s), headers=s["headers"])
    assert r.status_code == 200, r.text
    return r.json()


def answer(client, s, selected):
    return client.post(a_url(s), json={"selected_answer": selected}, headers=s["headers"])


WRONG = "zzz"


def served_answer(db, s):
    db.expire_all()
    row = db.get(StudentAdaptiveState, uuid.UUID(s["id"]))
    return row.pending_question["correct_answer"]


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["ai_tutor"] == "offline_fallback"


def test_register_and_login(client):
    s = register(client)
    r = client.post("/auth/login", json={"email": s["email"].upper(), "password": "secret123"})
    assert r.status_code == 200
    assert r.json()["user_id"] == s["id"]


def test_wrong_password_rejected(client, student):
    r = client.post("/auth/login", json={"email": student["email"], "password": "nope"})
    assert r.status_code == 401


def test_duplicate_email_rejected(client, student):
    r = client.post("/auth/register", json={"email": student["email"], "password": "secret123",
                                            "full_name": "X"})
    assert r.status_code == 409


def test_register_validation(client):
    base = {"email": "v@test.com", "password": "secret123", "full_name": "V"}
    assert client.post("/auth/register", json={**base, "password": "123"}).status_code == 422
    assert client.post("/auth/register", json={**base, "full_name": "   "}).status_code == 422
    assert client.post("/auth/register", json={**base, "email": "not-an-email"}).status_code == 422
    assert client.post("/auth/register", json={**base, "grade_level": 40}).status_code == 422


def test_cannot_self_register_as_admin(client):
    for role in ("platform_admin", "org_admin"):
        r = client.post("/auth/register", json={"email": f"{role}@test.com", "password": "secret123",
                                                "full_name": "A", "role": role})
        assert r.status_code == 422


def test_guardian_must_be_a_parent(client, student):
    r = client.post("/auth/register", json={"email": "kid@test.com", "password": "secret123",
                                            "full_name": "Kid", "guardian_id": student["id"]})
    assert r.status_code == 400


def test_requires_token(client, student):
    assert client.get(q_url(student)).status_code in (401, 403)
    bad = {"Authorization": "Bearer garbage"}
    assert client.get(q_url(student), headers=bad).status_code == 401


def test_student_cannot_read_another_student(client, student):
    other = register(client)
    assert client.get(q_url(other), headers=student["headers"]).status_code == 403


def test_question_shape_and_no_answer_leak(client, student, db):
    for _ in range(15):
        q = get_question(client, student)
        assert q["source"] in ("offline", "llm")
        assert q["skill"] == "absolute_value"
        assert "correct_answer" not in q and "distractors" not in q and "explanation" not in q
        assert q["type"] in ("mcq", "tf", "input")
        if q["type"] == "mcq":
            assert served_answer(db, student) in q["options"]
            assert len(q["options"]) == len(set(q["options"])) >= 3
        elif q["type"] == "tf":
            assert q["options"] == ["صح", "خطأ"]
        else:
            assert q["options"] == []


def test_correct_answer_rewards_and_levels_up(client, student, db):
    get_question(client, student)
    r = answer(client, student, served_answer(db, student))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["is_correct"] is True
    assert d["action"] == "level_up"
    assert d["coins_awarded"] > 0
    wallet = client.get(f"/students/{student['id']}/economy/wallet", headers=student["headers"]).json()
    assert wallet["coins"] >= d["coins_awarded"]


def test_wrong_answer_returns_feedback_and_starts_remediation(client, student, db):
    q = get_question(client, student)
    right = served_answer(db, student)
    d = answer(client, student, WRONG).json()
    assert d["is_correct"] is False
    assert d["correct_answer"] == right
    assert d["explanation"]
    assert d["mistake_card"] and d["mistake_card"]["rule"]
    assert d["next_stage"] == "same_pattern"
    follow = get_question(client, student)
    assert follow["remedial"] == "same_pattern" and follow["banner"]
    assert follow["skill"] == q["skill"]


def test_wrong_mcq_option_names_the_misconception(client, student, db):
    for _ in range(30):
        q = get_question(client, student)
        if q["type"] == "mcq":
            break
        answer(client, student, served_answer(db, student))
    else:
        return
    right = served_answer(db, student)
    d = answer(client, student, next(o for o in q["options"] if o != right)).json()
    assert d["misconception"]


def test_client_cannot_forge_correct_answer(client, student):
    get_question(client, student)
    r = client.post(a_url(student), headers=student["headers"],
                    json={"selected_answer": "999", "correct_answer": "999", "skill_id": "x"})
    assert r.status_code == 200
    assert r.json()["is_correct"] is False


def test_answer_without_question_is_rejected(client, student):
    assert answer(client, student, "1").status_code == 409


def test_cannot_replay_an_answer_for_coins(client, student, db):
    get_question(client, student)
    right = served_answer(db, student)
    assert answer(client, student, right).status_code == 200
    assert answer(client, student, right).status_code == 409


def test_empty_answer_rejected(client, student):
    get_question(client, student)
    assert answer(client, student, "").status_code == 422


def test_repeated_flow_is_stable(client, student, db):
    set_plan(db, student["id"], "pro")
    normal = 0
    for i in range(60):
        q = get_question(client, student)
        pick = served_answer(db, student) if i % 3 else WRONG
        r = answer(client, student, pick)
        assert r.status_code == 200, r.text
        normal += q["remedial"] is None
        if r.json()["round_over"]:
            assert client.post(f"/students/{student['id']}/adaptive/round", headers=student["headers"]).status_code == 200
    state = client.get(f"/students/{student['id']}/adaptive/state", headers=student["headers"]).json()
    assert state["total_answered"] == normal


def test_api_backtracks_to_root_gap(client, student, db):
    row = db.get(StudentAdaptiveState, uuid.UUID(student["id"]))
    row.current_skill = "mult_div_integers"
    db.commit()
    set_plan(db, student["id"], "pro")

    engine_actions, found = [], None
    for _ in range(80):
        q = get_question(client, student)
        d = answer(client, student, WRONG).json()
        if q["remedial"] is None:
            engine_actions.append(d["action"])
        if d["new_gaps"]:
            found = d
            break
    assert found is not None, engine_actions
    assert found["gap_skill"] == "absolute_value"
    assert engine_actions[:4] == ["backtrack"] * 4

    path = client.get(f"/students/{student['id']}/adaptive/drilldowns", headers=student["headers"]).json()
    engine_path = [(p["from_skill"], p["to_skill"]) for p in path if p["triggered_by"] == "engine"]
    assert engine_path == [("mult_div_integers", "subtracting_integers"), ("subtracting_integers", "adding_integers"),
                           ("adding_integers", "comparing_integers"), ("comparing_integers", "absolute_value")]
    state = client.get(f"/students/{student['id']}/adaptive/state", headers=student["headers"]).json()
    assert {s["skill_id"]: s["status"] for s in state["skills"]}["absolute_value"] == "gap"
    assert client.get(f"/students/{student['id']}/insights", headers=student["headers"]).status_code == 200


def test_new_round_endpoint(client, student):
    r = client.post(f"/students/{student['id']}/adaptive/round", headers=student["headers"])
    assert r.status_code == 200 and r.json()["round_answered"] == 0


def test_curriculum_skills(client):
    skills = client.get("/curriculum/skills").json()
    assert len(skills) == 9
    assert skills[0]["skill_id"] == "absolute_value" and skills[0]["prerequisites"] == []
    assert all(s["ladder"] and s["intervention"] for s in skills)


def test_parent_sees_only_their_children(client):
    parent = register(client, role="parent")
    kid = register(client, guardian_id=parent["id"])
    register(client)
    roster = client.get("/me/students", headers=parent["headers"]).json()
    assert [r["student_id"] for r in roster] == [kid["id"]]

    assert client.get(f"/students/{kid['id']}/insights", headers=parent["headers"]).status_code == 200


def test_teacher_sees_their_org(client, db):
    db.add(Organization(name="Demo School", slug="demo"))
    db.commit()
    teacher = register(client, role="teacher", org_slug="demo")
    pupil = register(client, org_slug="demo")
    register(client)
    roster = client.get("/me/students", headers=teacher["headers"]).json()
    assert [r["student_id"] for r in roster] == [pupil["id"]]


def test_student_cannot_list_students(client, student):
    assert client.get("/me/students", headers=student["headers"]).status_code == 403


def test_chat_works_without_groq_or_vector_store(client, student):
    base = f"/students/{student['id']}/chat"
    start = client.post(f"{base}/start", json={"skill_context": "adding_integers"}, headers=student["headers"])
    assert start.status_code == 200
    sid = start.json()["session_id"]
    r = client.post(f"{base}/message", json={"session_id": sid, "message": "مش فاهم"},
                    headers=student["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["reply"]


def test_chat_input_validation(client, student):
    base = f"/students/{student['id']}/chat"
    assert client.post(f"{base}/start", json={"skill_context": "nope"},
                       headers=student["headers"]).status_code == 422
    sid = client.post(f"{base}/start", json={"skill_context": "adding_integers"},
                      headers=student["headers"]).json()["session_id"]
    assert client.post(f"{base}/message", json={"session_id": sid, "message": ""},
                       headers=student["headers"]).status_code == 422
    assert client.post(f"{base}/message", json={"session_id": str(uuid.uuid4()), "message": "hi"},
                       headers=student["headers"]).status_code == 404


def test_demo_seed_script_runs(db, session_factory, monkeypatch):
    import scripts.seed_demo as seed
    monkeypatch.setattr(seed, "SessionLocal", session_factory)
    seed.main()
    seed.main()
    from app.models.org import User
    assert db.query(User).count() == 8


def test_tutor_detected_gap_becomes_next_question(client, student, db):
    from app.services import engine_bridge
    plan = engine_bridge.trigger_manual_drill_down(db, uuid.UUID(student["id"]), "adding_integers", "sign confusion")
    assert plan is not None
    q = get_question(client, student)
    assert q["remedial"] == "easier" and q["skill"] == "adding_integers" and "المعلم الذكي" in q["banner"]
    assert engine_bridge.trigger_manual_drill_down(db, uuid.UUID(student["id"]), "calculus", "") is None


def test_auth_me_and_guardian_email(client):
    parent = register(client, role="parent")
    kid = register(client, guardian_email=parent["email"])
    me = client.get("/auth/me", headers=kid["headers"]).json()
    assert me["role"] == "student" and me["email"] == kid["email"]
    roster = client.get("/me/students", headers=parent["headers"]).json()
    assert [r["student_id"] for r in roster] == [kid["id"]]
    bad = client.post("/auth/register", json={"email": "k2@test.com", "password": "secret123", "full_name": "K",
                                              "guardian_email": "nobody@test.com"})
    assert bad.status_code == 400


def test_avatar_requires_ownership(client, student, db):
    from app.engine import avatar_items as ai
    from scripts.seed_shop import to_shop_item
    paid = next(i for i in ai.CATALOG if i.price > 0 and i.group not in {"jobs", "heritage", "jobcaps"})
    db.add(to_shop_item(paid))
    db.commit()
    base = f"/students/{student['id']}/economy"
    cfg = client.get(f"{base}/avatar", headers=student["headers"]).json()
    assert cfg["clothing"]
    wearing = {**cfg, paid.cat: paid.id}
    assert client.put(f"{base}/avatar", json=wearing, headers=student["headers"]).status_code == 403

    from app.models.economy import Currency, TxnReason
    from app.services.economy_service import apply_txn, get_or_create_wallet
    wallet = get_or_create_wallet(db, uuid.UUID(student["id"]))
    apply_txn(db, wallet, Currency.coins, 10_000, TxnReason.admin_grant)
    db.commit()
    buy = client.post(f"{base}/purchase", json={"item_id": paid.id, "currency": "coins"}, headers=student["headers"])
    assert buy.status_code == 200 and buy.json()["success"]
    assert client.put(f"{base}/avatar", json=wearing, headers=student["headers"]).status_code == 200
    assert client.get(f"{base}/avatar", headers=student["headers"]).json()[paid.cat] == paid.id
