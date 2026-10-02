"""Database-level stability: concurrency, idempotency and repetition through HTTP -> FastAPI -> PostgreSQL.

Every test runs the real application against the real test database (no mocks). They need the same
environment as the rest of the suite (PostgreSQL + `pip install -r requirements-dev.txt`).
The engine-only counterpart that runs without a database is tests/test_stability_engine.py.
"""
import threading
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app import integrity_sql
from app.engine import integrity
from app.main import app
from app.models.adaptive import AnswerReceipt, AttemptLog, SkillMastery, StudentAdaptiveState
from app.services import engine_bridge
from tests.helpers import register, set_plan


def _question(c, s):
    r = c.get(f"/students/{s['id']}/adaptive/question", headers=s["headers"])
    assert r.status_code == 200, r.text
    return r.json()


def _pending(s):
    """The student's pending question, read through a short-lived session.

    The session is closed before returning, so no connection stays checked out (and no transaction stays
    open) while the test thread goes on to make HTTP requests that need connections of their own.
    """
    from tests.conftest import TestingSession
    with TestingSession() as fresh:
        return dict(fresh.get(StudentAdaptiveState, uuid.UUID(s["id"])).pending_question)


def _pending_correct(s):
    return _pending(s)["correct_answer"]


def _post_answer(c, s, selected, request_id=None):
    body = {"selected_answer": selected}
    if request_id:
        body["request_id"] = request_id
    return c.post(f"/students/{s['id']}/adaptive/answer", json=body, headers=s["headers"])


def _parallel(n, fn):
    """Run fn(i) on n threads that start together; returns the list of results (exceptions re-raised)."""
    results, errors = [None] * n, []
    gate = threading.Barrier(n)

    def run(i):
        try:
            gate.wait(timeout=30)
            results[i] = fn(i)
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(repr(exc))

    threads = [threading.Thread(target=run, args=(i,)) for i in range(n)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors, errors
    return results


def _error_checks(db):
    bad = {}
    for severity, label, sql in integrity_sql.checks():
        if severity == "ERROR":
            n = db.execute(text(sql)).scalar() or 0
            if n:
                bad[label] = n
    return bad


@pytest.mark.parametrize("n", [5, 10])
def test_concurrent_duplicate_submissions_with_a_request_id_grade_exactly_once(client, db, n):
    s = register(client)
    _question(client, s)
    right = _pending_correct(s)
    rid = "dup-" + uuid.uuid4().hex[:12]
    results = _parallel(n, lambda i: _post_answer(TestClient(app), s, right, rid))
    assert all(r.status_code == 200 for r in results), [(r.status_code, r.text) for r in results]
    assert len({r.json()["is_correct"] for r in results}) == 1
    assert sum(1 for r in results if not r.json().get("idempotent_replay")) == 1, "exactly one real grading"
    sid = uuid.UUID(s["id"])
    db.expire_all()
    assert db.scalar(select(func.count(AttemptLog.id)).where(AttemptLog.student_id == sid)) == 1
    assert db.get(StudentAdaptiveState, sid).total_answered == 1
    assert db.scalar(select(func.count(AnswerReceipt.request_id)).where(AnswerReceipt.student_id == sid)) == 1
    assert _error_checks(db) == {}


def test_concurrent_submissions_without_a_request_id_are_graded_once_and_the_rest_rejected(client, db):
    s = register(client)
    _question(client, s)
    right = _pending_correct(s)
    results = _parallel(8, lambda i: _post_answer(TestClient(app), s, right))
    codes = sorted(r.status_code for r in results)
    assert codes == [200] + [409] * 7, codes
    assert all(r.json()["detail"] == "no_active_question" for r in results if r.status_code == 409)
    db.expire_all()
    assert db.scalar(select(func.count(AttemptLog.id)).where(AttemptLog.student_id == uuid.UUID(s["id"]))) == 1


def test_reusing_a_request_id_for_a_different_answer_is_rejected_not_replayed(client, db):
    s = register(client)
    q = _question(client, s)
    right = _pending_correct(s)
    rid = "reuse-" + uuid.uuid4().hex[:10]
    assert _post_answer(client, s, right, rid).status_code == 200
    other = next(o for o in q["options"] if o != right)
    r = _post_answer(client, s, other, rid)
    assert r.status_code == 409 and r.json()["detail"] == "request_id_reused"


def test_replayed_response_matches_the_original(client, db):
    s = register(client)
    _question(client, s)
    right = _pending_correct(s)
    rid = "same-" + uuid.uuid4().hex[:10]
    first = _post_answer(client, s, right, rid).json()
    again = _post_answer(client, s, right, rid).json()
    assert again.pop("idempotent_replay") is True and first.pop("idempotent_replay") is False
    assert {k: v for k, v in again.items() if k != "remaining_questions"} == \
        {k: v for k, v in first.items() if k != "remaining_questions"}


@pytest.mark.parametrize("students", [5, 10, 20])
def test_many_students_answer_at_the_same_time_without_corruption(client, db, students):
    people = [register(client) for _ in range(students)]
    for p in people:
        set_plan(db, p["id"], "pro")  # lift the 20-questions/day Basic cap

    def journey(i):
        c, s = TestClient(app), people[i]
        for _ in range(8):
            _question(c, s)
            r = _post_answer(c, s, _pending_correct(s))
            assert r.status_code == 200, r.text
            if r.json()["round_over"]:
                assert c.post(f"/students/{s['id']}/adaptive/round", headers=s["headers"]).status_code == 200
        return True

    assert all(_parallel(students, journey))
    _assert_no_connection_leak(db)
    db.expire_all()
    for p in people:
        sid = uuid.UUID(p["id"])
        assert db.scalar(select(func.count(AttemptLog.id)).where(AttemptLog.student_id == sid)) == 8
        row = db.get(StudentAdaptiveState, sid)
        assert row.total_answered == 8
        assert integrity.check_state(engine_bridge._load_state(db, sid)) == []
    assert _error_checks(db) == {}


def test_the_same_student_in_two_tabs_cannot_overwrite_each_other(client, db):
    """Two tabs ask for a question at once: one question is pending afterwards, state stays valid."""
    s = register(client)
    results = _parallel(6, lambda i: TestClient(app).get(f"/students/{s['id']}/adaptive/question", headers=s["headers"]))
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    assert _error_checks(db) == {}


def test_first_request_race_creates_one_state_row(client, db):
    s = register(client)
    sid = uuid.UUID(s["id"])
    db.query(StudentAdaptiveState).filter(StudentAdaptiveState.student_id == sid).delete()
    db.commit()
    results = _parallel(6, lambda i: TestClient(app).get(f"/students/{s['id']}/adaptive/state", headers=s["headers"]))
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    db.expire_all()
    assert db.scalar(select(func.count(StudentAdaptiveState.student_id)).where(StudentAdaptiveState.student_id == sid)) == 1


@pytest.mark.parametrize("runs", [10, 50, 100])
def test_core_workflow_repeated_through_the_api(client, db, runs):
    s = register(client)
    set_plan(db, s["id"], "pro")
    seen_status = set()
    for i in range(runs):
        _question(client, s)
        # mix correct and realistic wrong answers so diagnosis, remediation and return paths all run
        if i % 3 == 2:
            pending = _pending_traps(s)
            selected = next(iter(pending), "0")
        else:
            selected = _pending_correct(s)
        r = _post_answer(client, s, selected)
        assert r.status_code == 200, (i, r.status_code, r.text)
        seen_status.add((r.json().get("evidence_status") or {}).get("status"))
        if r.json()["round_over"]:
            assert client.post(f"/students/{s['id']}/adaptive/round", headers=s["headers"]).status_code == 200
    sid = uuid.UUID(s["id"])
    db.expire_all()
    assert db.scalar(select(func.count(AttemptLog.id)).where(AttemptLog.student_id == sid)) == runs
    assert integrity.check_state(engine_bridge._load_state(db, sid)) == []
    assert _error_checks(db) == {}


def _pending_traps(s):
    return _pending(s).get("traps") or {}


def test_skill_mastery_cannot_hold_duplicates_or_impossible_values(client, db):
    from sqlalchemy.exc import IntegrityError
    s = register(client)
    sid = uuid.UUID(s["id"])
    db.add(SkillMastery(student_id=sid, skill_id="absolute_value", p_mastery=0.4, attempts=2, correct=1))
    db.commit()
    for bad in (dict(skill_id="absolute_value", p_mastery=0.5, attempts=1, correct=1),   # duplicate
                dict(skill_id="adding_integers", p_mastery=1.0, attempts=1, correct=1),   # p = 1.0
                dict(skill_id="adding_integers", p_mastery=0.5, attempts=1, correct=3)):  # correct > attempts
        db.add(SkillMastery(student_id=sid, **bad))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


# ---- connection / session lifecycle ------------------------------------------------------------

def _assert_no_connection_leak(*own_sessions):
    """Every request returned its connection: nothing checked out of the pool, nothing idle in a transaction.

    The test's own sessions are rolled back first: they are not what is being measured.
    """
    from tests.conftest import engine as test_engine
    for own in own_sessions:
        own.rollback()
    assert test_engine.pool.checkedout() == 0, f"{test_engine.pool.checkedout()} connection(s) still checked out"
    with test_engine.connect() as conn:
        idle = conn.execute(text(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
            "AND pid <> pg_backend_pid() AND state LIKE 'idle in transaction%'")).scalar()
    assert idle == 0, f"{idle} connection(s) left idle in a transaction"


def test_real_get_db_always_closes_its_session():
    """The production dependency (not the test override) releases its connection on every exit path."""
    import app.database as database

    base = database.engine.pool.checkedout()
    gen = database.get_db()                       # normal end of a request
    session = next(gen)
    session.execute(text("SELECT 1"))
    assert database.engine.pool.checkedout() == base + 1
    gen.close()
    assert database.engine.pool.checkedout() == base

    gen = database.get_db()                       # the handler raised
    session = next(gen)
    session.execute(text("SELECT 1"))
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("handler crashed"))
    assert database.engine.pool.checkedout() == base


def test_requests_that_fail_still_release_their_connection(client, db):
    s = register(client)
    for _ in range(15):
        assert client.get(f"/students/{s['id']}/adaptive/state").status_code in (401, 403)        # no token
        assert client.get(f"/students/{uuid.uuid4()}/adaptive/state", headers=s["headers"]).status_code in (403, 404)
        assert _post_answer(client, s, "x").status_code in (409, 422)                                  # nothing pending
    _assert_no_connection_leak(db)


def test_burst_of_parallel_requests_leaves_no_connection_behind(client):
    s = register(client)
    _parallel(30, lambda i: TestClient(app).get(f"/students/{s['id']}/adaptive/state", headers=s["headers"]).status_code)
    _assert_no_connection_leak()


# ---- creation of the per-student state row -----------------------------------------------------

def test_state_row_has_a_unique_key(client, db):
    """student_id is the primary key: a second row for the same student is rejected by the database."""
    from sqlalchemy.exc import IntegrityError
    s = register(client)
    sid = uuid.UUID(s["id"])
    db.add(StudentAdaptiveState(student_id=sid, current_skill="absolute_value", difficulty=1))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_provisioning_is_atomic_idempotent_and_race_free(client, db):
    from tests.conftest import TestingSession
    s = register(client)
    sid = uuid.UUID(s["id"])
    db.query(StudentAdaptiveState).filter(StudentAdaptiveState.student_id == sid).delete()
    db.commit()

    def attempt(i):
        with TestingSession() as own:
            return engine_bridge.provision_state(own, sid)

    created = _parallel(8, attempt)
    assert created.count(True) == 1, created                    # exactly one caller inserted
    db.expire_all()
    assert db.scalar(select(func.count(StudentAdaptiveState.student_id)).where(StudentAdaptiveState.student_id == sid)) == 1
    assert engine_bridge.provision_state(db, sid) is False       # idempotent afterwards
    _assert_no_connection_leak(db)


def test_first_write_path_request_race_creates_one_locked_row(client, db):
    """Question endpoint = the locking write path: concurrent first requests, one row, one pending question."""
    s = register(client)
    sid = uuid.UUID(s["id"])
    db.query(StudentAdaptiveState).filter(StudentAdaptiveState.student_id == sid).delete()
    db.commit()
    results = _parallel(6, lambda i: TestClient(app).get(f"/students/{s['id']}/adaptive/question", headers=s["headers"]))
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    db.expire_all()
    assert db.scalar(select(func.count(StudentAdaptiveState.student_id)).where(StudentAdaptiveState.student_id == sid)) == 1
    assert _pending(s)["correct_answer"]
    _assert_no_connection_leak(db)


def test_read_paths_never_write_a_state_row(client, db):
    """Teacher/parent views and the integrity checker read with lock=False: no row is created, nothing is
    left in the transaction, and the default starting state is shown."""
    s = register(client)
    sid = uuid.UUID(s["id"])
    db.query(StudentAdaptiveState).filter(StudentAdaptiveState.student_id == sid).delete()
    db.commit()
    state = engine_bridge._load_state(db, sid)
    assert integrity.check_state(state) == []
    overview = engine_bridge.state_overview(db, sid)
    assert overview["in_remediation"] is False and overview["total_answered"] == 0
    assert engine_bridge.diagnosis_history(db, sid) == []
    db.rollback()
    assert db.scalar(select(func.count(StudentAdaptiveState.student_id)).where(StudentAdaptiveState.student_id == sid)) == 0


def test_a_learner_opening_their_own_state_gets_exactly_one_stored_row(client, db):
    s = register(client)
    sid = uuid.UUID(s["id"])
    db.query(StudentAdaptiveState).filter(StudentAdaptiveState.student_id == sid).delete()
    db.commit()
    assert client.get(f"/students/{s['id']}/adaptive/state", headers=s["headers"]).status_code == 200
    assert client.get(f"/students/{s['id']}/adaptive/state", headers=s["headers"]).status_code == 200
    db.expire_all()
    assert db.scalar(select(func.count(StudentAdaptiveState.student_id)).where(StudentAdaptiveState.student_id == sid)) == 1
