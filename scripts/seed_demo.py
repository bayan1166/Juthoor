import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app import models as _models
from app.database import Base, SessionLocal
from app.models.adaptive import AttemptLog, StudentAdaptiveState
from app.models.community import DirectMessage, Friendship, FriendshipStatus
from app.models.economy import AvatarConfig
from app.models.org import PlanTierUser, User, UserRole
from app.models.safety import UserReport
from app.security import hash_password, verify_password
from app.services import engine_bridge, identity

PASSWORD = "demo1234"
# Juthoor is B2C: learners and one parent/guardian (who buys Pro for a child). No teacher/school accounts.
PARENT_EMAIL = "parent@demo.jo"
CHILDREN_OF_PARENT = ("student1@demo.jo", "student2@demo.jo")


EXPECTED = [
    ("parent@demo.jo", "basic", None),
    ("student1@demo.jo", "pro", "بنت"),
    ("student2@demo.jo", "pro", "ولد"),
    ("student3@demo.jo", "basic", "بنت"),
    ("student4@demo.jo", "basic", "ولد"),
    ("student5@demo.jo", "basic", "بنت"),
    ("student6@demo.jo", "basic", "ولد"),
]


def problems(db):
    found = []
    try:
        for email, plan, gender in EXPECTED:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                found.append(f"{email}: missing")
                continue
            if not verify_password(PASSWORD, user.hashed_password):
                found.append(f"{email}: password is not {PASSWORD}")
            if user.plan.value != plan:
                found.append(f"{email}: plan is {user.plan.value}, expected {plan}")
            if plan != "basic" and (user.plan_expires_at is None or user.plan_expires_at < datetime.utcnow()):
                found.append(f"{email}: subscription expired")
            if gender is not None:
                avatar = db.get(AvatarConfig, user.id)
                if avatar is None or avatar.gender != gender:
                    found.append(f"{email}: avatar gender is {avatar.gender if avatar else 'missing'}, expected {gender}")
        parent = db.scalar(select(User).where(User.email == PARENT_EMAIL))
        for email in CHILDREN_OF_PARENT:
            child = db.scalar(select(User).where(User.email == email))
            if parent is not None and child is not None and child.guardian_id != parent.id:
                found.append(f"{email}: not linked to {PARENT_EMAIL}")
    except Exception as exc:
        found.append(f"database schema looks outdated: {type(exc).__name__}: {exc}")
    return found


def make_user(db, email, name, role, plan="basic", guardian=None, gender="ولد", skin="f8d25c"):
    user = User(
        email=email, hashed_password=hash_password(PASSWORD), full_name=name, role=role,
        guardian_id=guardian.id if guardian else None,
        plan=PlanTierUser(plan), handle=identity.unique_handle(db),
        plan_expires_at=(datetime.utcnow() + timedelta(days=365)) if plan != "basic" else None,
    )
    db.add(user)
    db.flush()
    if role == UserRole.student:
        db.add(StudentAdaptiveState(student_id=user.id, current_skill="absolute_value", difficulty=1))
        db.add(AvatarConfig(student_id=user.id, gender=gender, skin=skin))
    return user


def answer(db, student, correct):
    """Answer through the real engine. Wrong answers are realistic: the first answer the question
    bank links to a named misconception (e.g. 28 for -4 x 7, "ignored the sign rule")."""
    q = engine_bridge.next_question(db, student.id)
    mistake = next(iter(q.get("traps") or {}), None) or "0"
    result = engine_bridge.submit_answer(db, student.id, q["correct_answer"] if correct else mistake)
    if result["round_over"]:
        engine_bridge.start_new_round(db, student.id)
    return result


def play(db, student, pattern):
    for ok in pattern:
        answer(db, student, ok)


def place_student(db, student, skill):
    row = db.get(StudentAdaptiveState, student.id)
    row.current_skill = skill
    row.difficulty = 1
    row.consec_wrong = 0
    row.round_answered = 0
    row.return_stack = []
    row.remediation_plan = None
    row.pending_question = None
    row.pending_banner = None
    db.commit()


def prepare_story_student(db, student, start="mult_div_integers", limit=60):
    for _ in range(limit):
        if db.get(StudentAdaptiveState, student.id).current_skill == "adding_integers":
            break
        answer(db, student, True)
    place_student(db, student, start)


def miss_until_gap(db, student, limit=120):
    for _ in range(limit):
        if answer(db, student, False)["new_gaps"]:
            return


def spread_activity(db, student, rng, days=6):
    rows = list(db.scalars(select(AttemptLog).where(AttemptLog.student_id == student.id).order_by(AttemptLog.created_at)))
    if not rows:
        return
    now = datetime.utcnow()
    stamps = sorted(now - timedelta(days=rng.uniform(0, days), minutes=rng.randint(0, 600)) for _ in rows)
    for row, stamp in zip(rows, stamps):
        row.created_at = stamp


def main():
    rng = random.Random(26)
    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=db.get_bind())
        if db.scalar(select(User).where(User.email == PARENT_EMAIL)):
            issues = problems(db)
            if not issues:
                print("demo data already exists and is correct")
                return
            print("STALE DEMO DATA detected in this database:")
            for line in issues:
                print("  -", line)
            print("Run: python run_demo.py --reset   (this wipes the database and reseeds it)")
            sys.exit(2)
        parent = make_user(db, PARENT_EMAIL, "ولي الأمر أحمد", UserRole.parent)
        # Liyan and Omar: Pro bought by their parent (seeded demo subscriptions). Maryam: a Free learner.
        s1 = make_user(db, "student1@demo.jo", "ليان", UserRole.student, plan="pro", guardian=parent, gender="بنت", skin="edb98a")
        s2 = make_user(db, "student2@demo.jo", "عمر", UserRole.student, plan="pro", guardian=parent, skin="f8d25c")
        s3 = make_user(db, "student3@demo.jo", "مريم", UserRole.student, gender="بنت", skin="ffe0c2")
        s4 = make_user(db, "student4@demo.jo", "يوسف", UserRole.student, skin="c68642")
        s5 = make_user(db, "student5@demo.jo", "هبة", UserRole.student, gender="بنت", skin="8d5524")
        s6 = make_user(db, "student6@demo.jo", "زياد", UserRole.student, skin="edb98a")
        db.commit()
        prepare_story_student(db, s1, "mult_div_integers")
        miss_until_gap(db, s1)
        prepare_story_student(db, s2, "mult_div_integers")
        play(db, s4, [True, True, False, True, True, True, False, True])
        prepare_story_student(db, s6, "subtracting_integers")
        miss_until_gap(db, s6)
        for student in (s1, s2, s4, s6):
            spread_activity(db, student, rng)
        db.commit()

        now = datetime.utcnow()
        db.add(Friendship(requester_id=s1.id, addressee_id=s2.id, status=FriendshipStatus.accepted))
        db.add(Friendship(requester_id=s2.id, addressee_id=s4.id, status=FriendshipStatus.accepted))
        db.add(Friendship(requester_id=s4.id, addressee_id=s1.id, status=FriendshipStatus.pending))
        base = now - timedelta(hours=3)
        chat = [
            (s1, s2, "مرحباً عمر، هل أنهيت تدريب اليوم؟", True),
            (s2, s1, "نعم، وشجرتي صار فيها ورقتان جديدتان", True),
            (s1, s2, "جذور وجد أن صعوبتي تبدأ من الجمع، سأعالجها ثم أرجع إلى الضرب", True),
            (s2, s1, "حظاً موفقاً", False),
            (s2, s1, "حاول أن تلحق بي", False),
        ]
        for index, (sender, recipient, body, seen) in enumerate(chat):
            stamp = base + timedelta(minutes=index * 7)
            db.add(DirectMessage(sender_id=sender.id, recipient_id=recipient.id, body=body, created_at=stamp,
                                 read_at=stamp + timedelta(minutes=1) if seen else None))
        spam_ids = []
        for index in range(3):
            message_id = uuid.uuid4()
            spam_ids.append(message_id)
            db.add(DirectMessage(id=message_id, sender_id=s4.id, recipient_id=s2.id, body="تعال العب معي الآن",
                                 created_at=now - timedelta(minutes=40 - index), read_at=None))
        db.flush()
        db.add(UserReport(reporter_id=s2.id, reported_user_id=s4.id, message_id=spam_ids[-1], reason="spam",
                          details="يرسل الرسالة نفسها عدة مرات"))
        db.commit()

        print("demo data created. password for all accounts:", PASSWORD)
        for user in (parent, s1, s2, s3, s4, s5, s6):
            print(f"  {user.email:22s} handle #{user.handle}  {user.role.value}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
