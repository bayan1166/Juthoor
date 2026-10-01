import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from app import models as _models
from app.database import Base, SessionLocal
from app.models.adaptive import AttemptLog, StudentAdaptiveState
from app.models.classroom import (
    Assignment, Classroom, ClassroomMember, Quiz, QuizAttempt, QuizQuestion, Submission,
)
from app.models.community import DirectMessage, Friendship, FriendshipStatus
from app.models.economy import AvatarConfig
from app.models.org import Organization, PlanTierUser, User, UserRole
from app.models.safety import UserReport
from app.security import hash_password, verify_password
from app.services import engine_bridge, identity, quiz_scoring, remediation
from app.services.economy_service import get_or_create_wallet

PASSWORD = "demo1234"
JOIN_CODE = "JUTH26"


EXPECTED = [
    ("teacher@demo.jo", "school", None),
    ("parent@demo.jo", "basic", None),
    ("student1@demo.jo", "pro", "بنت"),
    ("student2@demo.jo", "basic", "ولد"),
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
        room = db.scalar(select(Classroom).where(Classroom.join_code == JOIN_CODE))
        if room is None:
            found.append(f"classroom {JOIN_CODE}: missing")
        else:
            members = db.scalar(select(func.count(ClassroomMember.id)).where(ClassroomMember.classroom_id == room.id)) or 0
            if members != 5:
                found.append(f"classroom {JOIN_CODE}: {members} members, expected 5")
    except Exception as exc:
        found.append(f"database schema looks outdated: {type(exc).__name__}: {exc}")
    return found


def make_user(db, org, email, name, role, plan="basic", guardian=None, gender="ولد", skin="f8d25c"):
    user = User(
        email=email, hashed_password=hash_password(PASSWORD), full_name=name, role=role,
        organization_id=org.id, guardian_id=guardian.id if guardian else None, grade_level=6,
        plan=PlanTierUser(plan), handle=identity.unique_handle(db),
        plan_expires_at=(datetime.utcnow() + timedelta(days=365)) if plan != "basic" else None,
    )
    db.add(user)
    db.flush()
    if role == UserRole.student:
        db.add(StudentAdaptiveState(student_id=user.id, current_skill="absolute_value", difficulty=1))
        db.add(AvatarConfig(student_id=user.id, gender=gender, skin=skin))
        get_or_create_wallet(db, user.id)
    return user


def answer(db, student, correct):
    q = engine_bridge.next_question(db, student.id)
    result = engine_bridge.submit_answer(db, student.id, q["correct_answer"] if correct else "zzz")
    if result["round_over"]:
        engine_bridge.start_new_round(db, student.id)
    return result


def play(db, student, pattern):
    for ok in pattern:
        answer(db, student, ok)


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


def add_attempt(db, quiz, questions, student, picks_right, seconds):
    answers = {}
    for index, q in enumerate(questions):
        if index < picks_right:
            answers[str(q.id)] = q.correct_index
        else:
            answers[str(q.id)] = (q.correct_index + 1) % len(q.options)
    plain = [{"id": q.id, "correct_index": q.correct_index, "points": q.points} for q in questions]
    result = quiz_scoring.score_attempt(plain, answers, seconds, quiz.mode, quiz.time_limit_seconds)
    now = datetime.utcnow()
    db.add(QuizAttempt(
        quiz_id=quiz.id, student_id=student.id, started_at=now - timedelta(seconds=seconds), submitted_at=now,
        score=result["score"], correct=result["correct"], total=result["total"], duration_seconds=seconds,
    ))


def main():
    rng = random.Random(26)
    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=db.get_bind())
        if db.scalar(select(Organization).where(Organization.slug == "demo-school")):
            issues = problems(db)
            if not issues:
                print("demo data already exists and is correct")
                return
            print("STALE DEMO DATA detected in this database:")
            for line in issues:
                print("  -", line)
            print("Run: python run_demo.py --reset   (this wipes the database and reseeds it)")
            sys.exit(2)
        org = Organization(name="Demo School", slug="demo-school")
        db.add(org)
        db.flush()

        teacher = make_user(db, org, "teacher@demo.jo", "المعلمة سارة", UserRole.teacher, plan="school", gender="بنت")
        parent = make_user(db, org, "parent@demo.jo", "ولي الأمر أحمد", UserRole.parent)
        s1 = make_user(db, org, "student1@demo.jo", "ليان", UserRole.student, plan="pro", guardian=parent, gender="بنت", skin="edb98a")
        s2 = make_user(db, org, "student2@demo.jo", "عمر", UserRole.student, skin="f8d25c")
        s3 = make_user(db, org, "student3@demo.jo", "مريم", UserRole.student, gender="بنت", skin="ffe0c2")
        s4 = make_user(db, org, "student4@demo.jo", "يوسف", UserRole.student, skin="c68642")
        s5 = make_user(db, org, "student5@demo.jo", "هبة", UserRole.student, gender="بنت", skin="8d5524")
        s6 = make_user(db, org, "student6@demo.jo", "زياد", UserRole.student, skin="edb98a")
        db.commit()

        db.get(StudentAdaptiveState, s1.id).current_skill = "mult_div_integers"
        db.get(StudentAdaptiveState, s6.id).current_skill = "adding_integers"
        db.get(StudentAdaptiveState, s2.id).current_skill = "mult_div_integers"
        db.commit()
        miss_until_gap(db, s1)
        play(db, s4, [True, True, False, True, True, True, False, True])
        miss_until_gap(db, s6)
        for student in (s1, s2, s4, s6):
            spread_activity(db, student, rng)
        db.commit()

        room = Classroom(teacher_id=teacher.id, name="السادس أ - رياضيات", join_code=JOIN_CODE)
        db.add(room)
        db.flush()
        for student in (s1, s2, s4, s5, s6):
            db.add(ClassroomMember(classroom_id=room.id, student_id=student.id))

        now = datetime.utcnow()
        hw1 = Assignment(
            classroom_id=room.id, title="تمارين جمع الأعداد الصحيحة",
            description="حلّ خمس مسائل من الصفحة 24 واكتب خطوات الحل لكل مسألة.",
            skill_id="adding_integers", target_questions=10, max_score=100, due_at=now + timedelta(days=3),
        )
        hw2 = Assignment(
            classroom_id=room.id, title="ورقة عمل: القيمة المطلقة",
            description="أكمل ورقة العمل وارفع صورة لحلّك.", skill_id="absolute_value",
            max_score=50, due_at=now - timedelta(days=1),
        )
        db.add_all([hw1, hw2])
        db.flush()
        overviews = {m.id: engine_bridge.state_overview(db, m.id) for m in (s1, s2, s4, s5, s6)}
        by_gap = {}
        for student_id, overview in overviews.items():
            for skill in overview["skills"]:
                if skill["status"] == "gap":
                    by_gap.setdefault(skill["skill_id"], []).append(student_id)
        for skill_id, ids in by_gap.items():
            spec = remediation.build_remediation(skill_id, now)
            spec.pop("tip")
            db.add(Assignment(classroom_id=room.id, target_ids=[str(i) for i in ids], **spec))
        db.flush()
        db.add(Submission(
            assignment_id=hw1.id, student_id=s1.id, text="المسألة الأولى: 5 + (-2) = 3 لأن الإشارتين مختلفتان.",
            submitted_at=now - timedelta(hours=5), score=92, feedback="عمل ممتاز، خطواتك واضحة ومرتبة.",
            graded_at=now - timedelta(hours=1),
        ))
        db.add(Submission(
            assignment_id=hw1.id, student_id=s2.id, text="أنهيت جميع المسائل وراجعت إجاباتي مرتين.",
            submitted_at=now - timedelta(hours=2),
        ))
        db.add(Submission(
            assignment_id=hw2.id, student_id=s4.id, text="حللت الأسئلة كلها.", submitted_at=now - timedelta(days=2),
            score=41, feedback="جيد، انتبه لإشارة القيمة المطلقة.", graded_at=now - timedelta(days=1),
        ))

        race = Quiz(classroom_id=room.id, title="سباق الجمع السريع", description="جمع الأعداد الصحيحة",
                    mode="race", time_limit_seconds=180)
        quick = Quiz(classroom_id=room.id, title="اختبار قصير: القيمة المطلقة", description="القيمة المطلقة",
                     mode="quiz", time_limit_seconds=0)
        db.add_all([race, quick])
        db.flush()
        for quiz, skill, count in ((race, "adding_integers", 6), (quick, "absolute_value", 5)):
            for position, item in enumerate(quiz_scoring.generate_questions(skill, count, rng)):
                db.add(QuizQuestion(quiz_id=quiz.id, position=position, prompt=item["prompt"], options=item["options"],
                                    correct_index=item["correct_index"], points=item["points"]))
        db.flush()
        race_questions = list(db.scalars(select(QuizQuestion).where(QuizQuestion.quiz_id == race.id).order_by(QuizQuestion.position)))
        add_attempt(db, race, race_questions, s1, 6, 74.0)
        add_attempt(db, race, race_questions, s2, 5, 61.0)
        add_attempt(db, race, race_questions, s4, 3, 95.0)

        db.add(Friendship(requester_id=s1.id, addressee_id=s2.id, status=FriendshipStatus.accepted))
        db.add(Friendship(requester_id=s2.id, addressee_id=s4.id, status=FriendshipStatus.accepted))
        db.add(Friendship(requester_id=s4.id, addressee_id=s1.id, status=FriendshipStatus.pending))
        base = now - timedelta(hours=3)
        chat = [
            (s1, s2, "مرحباً عمر، هل حللت واجب الجمع؟", True),
            (s2, s1, "نعم أنهيته أمس، كان سهلاً بعد شرح المعلم الذكي", True),
            (s1, s2, "رائع، سأجرب سباق الجمع السريع الآن", True),
            (s2, s1, "حظاً موفقاً، حصلت على 5 من 6", False),
            (s2, s1, "حاول أن تتفوق عليّ", False),
        ]
        for index, (sender, recipient, body, seen) in enumerate(chat):
            stamp = base + timedelta(minutes=index * 7)
            db.add(DirectMessage(sender_id=sender.id, recipient_id=recipient.id, body=body, created_at=stamp,
                                 read_at=stamp + timedelta(minutes=1) if seen else None))
        spam_ids = []
        for index in range(3):
            message_id = uuid.uuid4()
            spam_ids.append(message_id)
            db.add(DirectMessage(id=message_id, sender_id=s4.id, recipient_id=s2.id, body="تعال العب سباق الجمع الآن",
                                 created_at=now - timedelta(minutes=40 - index), read_at=None))
        db.flush()
        db.add(UserReport(reporter_id=s2.id, reported_user_id=s4.id, message_id=spam_ids[-1], reason="spam",
                          details="يرسل الرسالة نفسها عدة مرات"))
        db.commit()

        print("demo data created. password for all accounts:", PASSWORD)
        for user in (teacher, parent, s1, s2, s3, s4, s5, s6):
            print(f"  {user.email:22s} handle #{user.handle}  {user.role.value}")
        print("classroom join code:", JOIN_CODE)
    finally:
        db.close()


if __name__ == "__main__":
    main()
