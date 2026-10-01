"""Create demo accounts with realistic history for judging day.

    python scripts/init_db.py && python scripts/seed_shop.py && python scripts/seed_demo.py

All passwords: demo1234
  teacher@demo.jo          teacher of "demo-school" (sees all 3 students)
  parent@demo.jo           parent of student1
  student1@demo.jo         has a diagnosed root gap (mult/div -> ... -> absolute value)
  student2@demo.jo         progressing well on absolute value
  student3@demo.jo         brand new, for the live walkthrough
Safe to re-run: does nothing if the demo org already exists.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app import models  # noqa: E402,F401
from app.database import SessionLocal  # noqa: E402
from app.models.adaptive import StudentAdaptiveState  # noqa: E402
from app.models.economy import AvatarConfig  # noqa: E402
from app.models.org import Organization, User, UserRole  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services import engine_bridge  # noqa: E402
from app.services.economy_service import get_or_create_wallet  # noqa: E402

PASSWORD = "demo1234"


def _user(db, org, email, name, role, guardian=None, plan=None):
    from app.models.org import PlanTierUser
    from datetime import datetime, timedelta
    u = User(email=email, hashed_password=hash_password(PASSWORD), full_name=name, role=role,
             organization_id=org.id, guardian_id=guardian.id if guardian else None, grade_level=6,
             plan=PlanTierUser(plan) if plan else PlanTierUser.basic,
             plan_expires_at=(datetime.utcnow() + timedelta(days=365)) if plan and plan != "basic" else None)
    db.add(u)
    db.flush()
    if role == UserRole.student:
        db.add(StudentAdaptiveState(student_id=u.id, current_skill="absolute_value", difficulty=1))
        db.add(AvatarConfig(student_id=u.id))
        get_or_create_wallet(db, u.id)
    return u


def _answer(db, student, correct: bool) -> dict:
    q = engine_bridge.next_question(db, student.id)   # internal dict still holds the answer
    return engine_bridge.submit_answer(db, student.id, q["correct_answer"] if correct else "zzz")


def _play(db, student, correct_pattern):
    for is_correct in correct_pattern:
        r = _answer(db, student, is_correct)
        if r["round_over"]:
            engine_bridge.start_new_round(db, student.id)


def _miss_until_root_gap(db, student, limit=120):
    for _ in range(limit):
        r = _answer(db, student, False)
        if r["round_over"]:
            engine_bridge.start_new_round(db, student.id)
        if r["new_gaps"]:
            return r["new_gaps"]
    return []


def main():
    db = SessionLocal()
    try:
        if db.scalar(select(Organization).where(Organization.slug == "demo-school")):
            print("demo data already exists; nothing to do")
            return
        org = Organization(name="Demo School", slug="demo-school")
        db.add(org)
        db.flush()
        _user(db, org, "teacher@demo.jo", "المعلمة سارة", UserRole.teacher)
        parent = _user(db, org, "parent@demo.jo", "ولي الأمر أحمد", UserRole.parent)
        s1 = _user(db, org, "student1@demo.jo", "ليان", UserRole.student, guardian=parent, plan="pro")
        s2 = _user(db, org, "student2@demo.jo", "عمر", UserRole.student, plan="max")
        _user(db, org, "student3@demo.jo", "طالب جديد", UserRole.student, plan="basic")
        db.commit()

        # student1: working on mult/div, keeps missing -> engine walks back to the root gap
        db.get(StudentAdaptiveState, s1.id).current_skill = "mult_div_integers"
        db.commit()
        gaps = _miss_until_root_gap(db, s1)
        print("student1 root gap:", gaps)
        # student2: mostly correct
        _play(db, s2, [True, True, False, True, True, True])

        print("demo accounts created (password: demo1234)")
        for e in ("teacher@demo.jo", "parent@demo.jo", "student1@demo.jo", "student2@demo.jo", "student3@demo.jo"):
            print("  ", e)
        print("org id:", org.id)
    finally:
        db.close()


if __name__ == "__main__":
    main()
