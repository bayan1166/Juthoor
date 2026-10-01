import csv
import io
import random
import uuid
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.engine import knowledge_graph as kg
from app.models.adaptive import AttemptLog
from app.models.classroom import (
    Assignment, Classroom, ClassroomMember, Quiz, QuizAttempt, QuizQuestion, Submission, new_join_code,
)
from app.models.community import DirectMessage
from app.models.org import User, UserRole
from app.models.safety import UserReport
from app.schemas.classroom import (
    AssignmentCreate, ClassroomCreate, GradeIn, JoinRequest, QuizCreate, QuizGenerate, QuizPatch, QuizSubmit,
    RemediationCreate, ReportResolve,
)
from app.schemas.common import z
from app.services import avatar_render, class_analytics, engine_bridge, plans, quiz_scoring, remediation

router = APIRouter(prefix="/classrooms", tags=["classrooms"])

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".txt", ".xlsx", ".pptx"}


def _is_staff(user: User) -> bool:
    return user.role in plans.STAFF_ROLES


def _classroom(db: Session, classroom_id: uuid.UUID) -> Classroom:
    room = db.get(Classroom, classroom_id)
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "classroom_not_found")
    return room


def _owner(db: Session, classroom_id: uuid.UUID, user: User) -> Classroom:
    room = _classroom(db, classroom_id)
    if room.teacher_id != user.id and user.role != UserRole.platform_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "teacher_only")
    return room


def _is_member(db: Session, classroom_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    return db.scalar(select(ClassroomMember.id).where(
        ClassroomMember.classroom_id == classroom_id, ClassroomMember.student_id == user_id).limit(1)) is not None


def _access(db: Session, classroom_id: uuid.UUID, user: User) -> Classroom:
    room = _classroom(db, classroom_id)
    if room.teacher_id == user.id or user.role == UserRole.platform_admin:
        return room
    if user.role == UserRole.student and _is_member(db, room.id, user.id):
        return room
    raise HTTPException(status.HTTP_404_NOT_FOUND, "classroom_not_found")


def _members(db: Session, classroom_id: uuid.UUID) -> list[User]:
    return list(db.scalars(
        select(User).join(ClassroomMember, ClassroomMember.student_id == User.id)
        .where(ClassroomMember.classroom_id == classroom_id).order_by(User.full_name)
    ))


def _person(user: User, svgs: dict) -> dict:
    return {"user_id": str(user.id), "handle": user.handle, "full_name": user.full_name, "avatar_svg": svgs.get(user.id)}


def _classroom_out(db: Session, room: Classroom, owner: bool) -> dict:
    members = db.scalar(select(func.count(ClassroomMember.id)).where(ClassroomMember.classroom_id == room.id)) or 0
    assigns = db.scalar(select(func.count(Assignment.id)).where(Assignment.classroom_id == room.id)) or 0
    quizzes = db.scalar(select(func.count(Quiz.id)).where(Quiz.classroom_id == room.id)) or 0
    teacher = db.get(User, room.teacher_id)
    return {
        "classroom_id": str(room.id), "name": room.name, "join_code": room.join_code if owner else None,
        "teacher_name": teacher.full_name if teacher else "", "member_count": int(members),
        "assignment_count": int(assigns), "quiz_count": int(quizzes), "created_at": z(room.created_at),
    }


@router.post("")
def create_classroom(payload: ClassroomCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not _is_staff(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "teacher_role_required")
    plans.require_school(db, user)
    room = Classroom(teacher_id=user.id, name=payload.name.strip())
    for _ in range(5):
        if db.scalar(select(Classroom.id).where(Classroom.join_code == room.join_code)) is None:
            break
        room.join_code = new_join_code()
    db.add(room)
    db.commit()
    db.refresh(room)
    return _classroom_out(db, room, True)


@router.post("/join")
def join_classroom(payload: JoinRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != UserRole.student:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "student_role_required")
    room = db.scalar(select(Classroom).where(Classroom.join_code == payload.join_code.strip().upper()))
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "classroom_not_found")
    if not _is_member(db, room.id, user.id):
        size = db.scalar(select(func.count(ClassroomMember.id)).where(ClassroomMember.classroom_id == room.id)) or 0
        if size >= plans.STUDENTS_PER_SEAT:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "class_full")
        db.add(ClassroomMember(classroom_id=room.id, student_id=user.id))
        db.commit()
    return _classroom_out(db, room, False)


@router.get("")
def my_classrooms(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == UserRole.student:
        rows = db.scalars(
            select(Classroom).join(ClassroomMember, ClassroomMember.classroom_id == Classroom.id)
            .where(ClassroomMember.student_id == user.id).order_by(Classroom.created_at.desc())
        ).all()
        return [_classroom_out(db, r, False) for r in rows]
    if not _is_staff(user):
        return []
    rows = db.scalars(select(Classroom).where(Classroom.teacher_id == user.id).order_by(Classroom.created_at.desc())).all()
    return [_classroom_out(db, r, True) for r in rows]


@router.get("/assignments")
def my_assignments(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    now = datetime.utcnow()
    if user.role == UserRole.student:
        pairs = db.execute(
            select(Assignment, Classroom).join(Classroom, Classroom.id == Assignment.classroom_id)
            .join(ClassroomMember, ClassroomMember.classroom_id == Classroom.id)
            .where(ClassroomMember.student_id == user.id)
            .order_by(Assignment.due_at.is_(None), Assignment.due_at, Assignment.created_at.desc())
        ).all()
        mine = {s.assignment_id: s for s in db.scalars(select(Submission).where(Submission.student_id == user.id))}
        out = []
        for a, c in pairs:
            if not _applies(a, user.id):
                continue
            sub = mine.get(a.id)
            if sub is not None and sub.graded_at is not None:
                state = "graded"
            elif sub is not None:
                state = "submitted"
            elif a.due_at is not None and a.due_at < now:
                state = "overdue"
            else:
                state = "open"
            out.append({**_assignment_dict(a, c), "state": state, "submission": _submission_dict(sub, a) if sub else None})
        return out
    if not _is_staff(user):
        return []
    pairs = db.execute(
        select(Assignment, Classroom).join(Classroom, Classroom.id == Assignment.classroom_id)
        .where(Classroom.teacher_id == user.id).order_by(Assignment.created_at.desc())
    ).all()
    out = []
    for a, c in pairs:
        total = db.scalar(select(func.count(Submission.id)).where(Submission.assignment_id == a.id)) or 0
        graded = db.scalar(select(func.count(Submission.id)).where(
            Submission.assignment_id == a.id, Submission.graded_at.is_not(None))) or 0
        members = len(a.target_ids) if a.target_ids is not None else (
            db.scalar(select(func.count(ClassroomMember.id)).where(ClassroomMember.classroom_id == c.id)) or 0)
        out.append({**_assignment_dict(a, c), "submissions": int(total), "graded": int(graded), "members": int(members)})
    return out


@router.get("/assignments/{assignment_id}")
def assignment_detail(assignment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = _assignment(db, assignment_id)
    c = _access(db, a.classroom_id, user)
    base = _assignment_dict(a, c)
    if user.role == UserRole.student:
        if not _applies(a, user.id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "assignment_not_found")
        sub = db.scalar(select(Submission).where(Submission.assignment_id == a.id, Submission.student_id == user.id))
        return {**base, "submission": _submission_dict(sub, a) if sub else None}
    members = [m for m in _members(db, c.id) if _applies(a, m.id)]
    svgs = avatar_render.svgs_for(db, members)
    subs = {s.student_id: s for s in db.scalars(select(Submission).where(Submission.assignment_id == a.id))}
    rows = []
    for m in members:
        sub = subs.get(m.id)
        rows.append({**_person(m, svgs), "submission": _submission_dict(sub, a) if sub else None})
    return {**base, "students": rows}


def _assignment(db: Session, assignment_id: uuid.UUID) -> Assignment:
    a = db.get(Assignment, assignment_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "assignment_not_found")
    return a


def _applies(a: Assignment, student_id) -> bool:
    return a.target_ids is None or str(student_id) in a.target_ids


def _assignment_dict(a: Assignment, c: Classroom) -> dict:
    return {
        "kind": a.kind or "homework", "targeted": a.target_ids is not None,
        "target_count": len(a.target_ids) if a.target_ids is not None else None,
        "assignment_id": str(a.id), "classroom_id": str(c.id), "classroom_name": c.name, "title": a.title,
        "description": a.description, "skill_id": a.skill_id,
        "skill_name_ar": kg.SKILLS[a.skill_id].name_ar if a.skill_id in kg.SKILLS else None,
        "target_questions": a.target_questions, "max_score": a.max_score, "due_at": z(a.due_at),
        "created_at": z(a.created_at),
    }


def _submission_dict(s: Submission, a: Assignment) -> dict:
    return {
        "submission_id": str(s.id), "text": s.text, "file_name": s.file_name, "has_file": bool(s.file_path),
        "submitted_at": z(s.submitted_at), "late": bool(a.due_at and s.submitted_at > a.due_at),
        "score": s.score, "feedback": s.feedback, "graded_at": z(s.graded_at),
    }


@router.post("/{classroom_id}/assignments")
def create_assignment(classroom_id: uuid.UUID, payload: AssignmentCreate, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    room = _owner(db, classroom_id, user)
    plans.require_school(db, user)
    if payload.skill_id is not None and payload.skill_id not in kg.SKILLS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown_skill")
    a = Assignment(
        classroom_id=room.id, title=payload.title.strip(), description=payload.description.strip(),
        skill_id=payload.skill_id, target_questions=payload.target_questions, max_score=payload.max_score,
        due_at=payload.due_at,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _assignment_dict(a, room)


@router.post("/assignments/{assignment_id}/submit")
def submit_assignment(assignment_id: uuid.UUID, text: str = Form(""), file: UploadFile | None = File(None),
                      db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = _assignment(db, assignment_id)
    if user.role != UserRole.student or not _is_member(db, a.classroom_id, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "student_role_required")
    if not _applies(a, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not_assigned")
    text = (text or "").strip()[:8000]
    has_file = file is not None and bool(file.filename)
    if not text and not has_file:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "empty_submission")
    sub = db.scalar(select(Submission).where(Submission.assignment_id == a.id, Submission.student_id == user.id))
    if sub is not None and sub.graded_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "already_graded")
    stored_name = stored_path = None
    if has_file:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "file_type_not_allowed")
        data = file.file.read(settings.max_upload_bytes + 1)
        if len(data) > settings.max_upload_bytes:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
        folder = Path(settings.upload_dir)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{uuid.uuid4().hex}{ext}"
        target.write_bytes(data)
        stored_name, stored_path = Path(file.filename).name[:200], str(target)
    if sub is None:
        sub = Submission(assignment_id=a.id, student_id=user.id)
        db.add(sub)
    sub.text = text
    if stored_path:
        sub.file_name, sub.file_path = stored_name, stored_path
    sub.submitted_at = datetime.utcnow()
    db.commit()
    db.refresh(sub)
    return _submission_dict(sub, a)


@router.post("/submissions/{submission_id}/grade")
def grade_submission(submission_id: uuid.UUID, payload: GradeIn, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "submission_not_found")
    a = _assignment(db, sub.assignment_id)
    _owner(db, a.classroom_id, user)
    if payload.score > a.max_score:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "score_out_of_range")
    sub.score = payload.score
    sub.feedback = payload.feedback.strip()
    sub.graded_at = datetime.utcnow()
    db.commit()
    return _submission_dict(sub, a)


@router.get("/submissions/{submission_id}/file")
def download_submission(submission_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sub = db.get(Submission, submission_id)
    if sub is None or not sub.file_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file_not_found")
    a = _assignment(db, sub.assignment_id)
    room = _classroom(db, a.classroom_id)
    if user.id != sub.student_id and user.id != room.teacher_id and user.role != UserRole.platform_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "cannot_access_file")
    path = Path(sub.file_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file_not_found")
    return FileResponse(path, filename=sub.file_name or path.name)


def _class_report(db: Session, room: Classroom) -> dict:
    members = _members(db, room.id)
    ids = [m.id for m in members]
    svgs = avatar_render.svgs_for(db, members)
    now = datetime.utcnow()
    week_start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    stats, activity = {}, {}
    if ids:
        grouped = db.execute(
            select(AttemptLog.student_id, func.count(AttemptLog.id),
                   func.sum(case((AttemptLog.is_correct.is_(True), 1), else_=0)), func.max(AttemptLog.created_at))
            .where(AttemptLog.student_id.in_(ids)).group_by(AttemptLog.student_id)
        ).all()
        stats = {sid: (int(n), int(right or 0), last) for sid, n, right, last in grouped}
        daily = db.execute(
            select(func.date(AttemptLog.created_at), func.count(AttemptLog.id))
            .where(AttemptLog.student_id.in_(ids), AttemptLog.created_at >= week_start)
            .group_by(func.date(AttemptLog.created_at))
        ).all()
        activity = {str(day): int(n) for day, n in daily}
    assignment_rows = list(db.scalars(select(Assignment).where(Assignment.classroom_id == room.id)))
    assignment_ids = [a.id for a in assignment_rows]
    done = Counter()
    if assignment_ids:
        for sid in db.scalars(select(Submission.student_id).where(Submission.assignment_id.in_(assignment_ids))):
            done[sid] += 1
    quiz_ids = list(db.scalars(select(Quiz.id).where(Quiz.classroom_id == room.id)))
    points = Counter()
    if quiz_ids:
        for sid, score in db.execute(select(QuizAttempt.student_id, QuizAttempt.score).where(
                QuizAttempt.quiz_id.in_(quiz_ids), QuizAttempt.submitted_at.is_not(None))):
            points[sid] += score
    rows, gap_counter, mastery_sum = [], Counter(), Counter()
    for m in members:
        overview = engine_bridge.state_overview(db, m.id)
        answered, right, last = stats.get(m.id, (0, 0, None))
        days = (now - last).days if last else None
        gaps = [s for s in overview["skills"] if s["status"] == "gap"]
        for s in overview["skills"]:
            mastery_sum[s["skill_id"]] += s["p_mastery"]
        for s in gaps:
            gap_counter[s["skill_id"]] += 1
        rows.append({
            **_person(m, svgs),
            "tree_health": overview["tree_health"],
            "mastered": sum(1 for s in overview["skills"] if s["status"] == "mastered"),
            "current_skill": kg.SKILLS[overview["current_skill"]].name_ar if overview["current_skill"] in kg.SKILLS else "",
            "accuracy": round(right / answered, 3) if answered else None,
            "answered": answered,
            "last_active": z(last),
            "days_since_active": days,
            "root_gaps": [s["name_ar"] for s in gaps],
            "root_gap_ids": [s["skill_id"] for s in gaps],
            "risk": class_analytics.risk_level(overview["tree_health"], answered, days, len(gaps)),
            "submissions_done": done.get(m.id, 0),
            "assignments_total": sum(1 for a in assignment_rows if _applies(a, m.id)),
            "quiz_points": int(points.get(m.id, 0)),
        })
    count = len(rows)
    active = [r for r in rows if r["accuracy"] is not None]
    last_days = [(week_start + timedelta(days=i)).date().isoformat() for i in range(7)]
    db.commit()
    return {
        "classroom": _classroom_out(db, room, True),
        "kpis": {
            "students": count,
            "avg_tree_health": round(sum(r["tree_health"] for r in rows) / count, 3) if count else 0.0,
            "avg_accuracy": round(sum(r["accuracy"] for r in active) / len(active), 3) if active else None,
            "active_last_7": sum(1 for r in rows if r["days_since_active"] is not None and r["days_since_active"] <= 7),
            "at_risk": sum(1 for r in rows if r["risk"] == "high"),
        },
        "students": rows,
        "top_gaps": [{"skill_id": sid, "name_ar": kg.SKILLS[sid].name_ar, "students": n} for sid, n in gap_counter.most_common(5)],
        "skill_mastery": [
            {"skill_id": sid, "name_ar": kg.SKILLS[sid].name_ar, "avg": round(mastery_sum[sid] / count, 3) if count else 0.0}
            for sid in kg.ordered_skills()
        ],
        "activity": [{"date": d, "answers": activity.get(d, 0)} for d in last_days],
    }


@router.get("/{classroom_id}/analytics")
def analytics(classroom_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = _owner(db, classroom_id, user)
    plans.require_school(db, user)
    return _class_report(db, room)


@router.get("/{classroom_id}/export.csv")
def export_csv(classroom_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = _owner(db, classroom_id, user)
    plans.require_school(db, user)
    report = _class_report(db, room)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["handle", "name", "tree_health", "mastered_skills", "accuracy", "answered", "last_active",
                     "risk", "root_gaps", "submissions", "quiz_points"])
    for r in report["students"]:
        writer.writerow([r["handle"], r["full_name"], r["tree_health"], r["mastered"], r["accuracy"], r["answered"],
                         r["last_active"], r["risk"], " | ".join(r["root_gaps"]), r["submissions_done"], r["quiz_points"]])
    body = "\ufeff" + buffer.getvalue()
    return Response(content=body.encode("utf-8"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="class-{room.join_code}.csv"'})


@router.get("/{classroom_id}/members")
def list_members(classroom_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = _access(db, classroom_id, user)
    members = _members(db, room.id)
    svgs = avatar_render.svgs_for(db, members)
    return [_person(m, svgs) for m in members]


@router.delete("/{classroom_id}/members/{student_id}")
def remove_member(classroom_id: uuid.UUID, student_id: uuid.UUID, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    room = _owner(db, classroom_id, user)
    row = db.scalar(select(ClassroomMember).where(
        ClassroomMember.classroom_id == room.id, ClassroomMember.student_id == student_id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "member_not_found")
    db.delete(row)
    db.commit()
    return {"status": "removed"}


def _quiz_questions(db: Session, quiz_id: uuid.UUID) -> list[QuizQuestion]:
    return list(db.scalars(select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.position)))


def _quiz(db: Session, quiz_id: uuid.UUID) -> Quiz:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "quiz_not_found")
    return quiz


def _quiz_dict(db: Session, quiz: Quiz, user: User) -> dict:
    questions = db.scalar(select(func.count(QuizQuestion.id)).where(QuizQuestion.quiz_id == quiz.id)) or 0
    attempts = db.scalar(select(func.count(QuizAttempt.id)).where(
        QuizAttempt.quiz_id == quiz.id, QuizAttempt.submitted_at.is_not(None))) or 0
    mine = None
    if user.role == UserRole.student:
        attempt = db.scalar(select(QuizAttempt).where(QuizAttempt.quiz_id == quiz.id, QuizAttempt.student_id == user.id))
        if attempt is not None:
            mine = {"submitted": attempt.submitted_at is not None, "score": attempt.score, "correct": attempt.correct,
                    "total": attempt.total}
    return {
        "quiz_id": str(quiz.id), "classroom_id": str(quiz.classroom_id), "title": quiz.title,
        "description": quiz.description, "mode": quiz.mode, "time_limit_seconds": quiz.time_limit_seconds,
        "is_open": quiz.is_open, "question_count": int(questions), "attempts": int(attempts),
        "created_at": z(quiz.created_at), "mine": mine,
    }


def _save_quiz(db: Session, room: Classroom, title: str, description: str, mode: str, limit: int, items: list[dict]) -> Quiz:
    quiz = Quiz(classroom_id=room.id, title=title.strip(), description=description.strip(), mode=mode,
                time_limit_seconds=limit)
    db.add(quiz)
    db.flush()
    for position, item in enumerate(items):
        db.add(QuizQuestion(quiz_id=quiz.id, position=position, prompt=item["prompt"], options=item["options"],
                            correct_index=item["correct_index"], points=item["points"]))
    db.commit()
    db.refresh(quiz)
    return quiz


@router.post("/{classroom_id}/quizzes")
def create_quiz(classroom_id: uuid.UUID, payload: QuizCreate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    room = _owner(db, classroom_id, user)
    plans.require_school(db, user)
    items = [q.model_dump() for q in payload.questions]
    quiz = _save_quiz(db, room, payload.title, payload.description, payload.mode, payload.time_limit_seconds, items)
    return _quiz_dict(db, quiz, user)


@router.post("/{classroom_id}/quizzes/generate")
def generate_quiz(classroom_id: uuid.UUID, payload: QuizGenerate, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    room = _owner(db, classroom_id, user)
    plans.require_school(db, user)
    if payload.skill_id not in kg.SKILLS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown_skill")
    items = quiz_scoring.generate_questions(payload.skill_id, payload.count, random.Random())
    if len(items) < 3:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "generation_failed")
    quiz = _save_quiz(db, room, payload.title, kg.SKILLS[payload.skill_id].name_ar, payload.mode,
                      payload.time_limit_seconds, items)
    return _quiz_dict(db, quiz, user)


@router.get("/{classroom_id}/quizzes")
def list_quizzes(classroom_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = _access(db, classroom_id, user)
    rows = db.scalars(select(Quiz).where(Quiz.classroom_id == room.id).order_by(Quiz.created_at.desc())).all()
    return [_quiz_dict(db, q, user) for q in rows]


@router.patch("/quizzes/{quiz_id}")
def patch_quiz(quiz_id: uuid.UUID, payload: QuizPatch, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    quiz = _quiz(db, quiz_id)
    _owner(db, quiz.classroom_id, user)
    quiz.is_open = payload.is_open
    db.commit()
    return _quiz_dict(db, quiz, user)


@router.delete("/quizzes/{quiz_id}/attempts/{student_id}")
def reset_attempt(quiz_id: uuid.UUID, student_id: uuid.UUID, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    quiz = _quiz(db, quiz_id)
    _owner(db, quiz.classroom_id, user)
    attempt = db.scalar(select(QuizAttempt).where(QuizAttempt.quiz_id == quiz.id, QuizAttempt.student_id == student_id))
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "attempt_not_found")
    db.delete(attempt)
    db.commit()
    return {"status": "reset"}


def _public_questions(questions: list[QuizQuestion]) -> list[dict]:
    return [{"id": str(q.id), "position": q.position, "prompt": q.prompt, "options": q.options, "points": q.points}
            for q in questions]


def _seconds_left(quiz: Quiz, attempt: QuizAttempt, now: datetime):
    if quiz.time_limit_seconds <= 0:
        return None
    return max(0, int(quiz.time_limit_seconds - (now - attempt.started_at).total_seconds()))


@router.post("/quizzes/{quiz_id}/start")
def start_quiz(quiz_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    quiz = _quiz(db, quiz_id)
    if user.role != UserRole.student or not _is_member(db, quiz.classroom_id, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "student_role_required")
    attempt = db.scalar(select(QuizAttempt).where(QuizAttempt.quiz_id == quiz.id, QuizAttempt.student_id == user.id))
    if attempt is not None and attempt.submitted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "already_submitted")
    if attempt is None:
        if not quiz.is_open:
            raise HTTPException(status.HTTP_409_CONFLICT, "quiz_closed")
        attempt = QuizAttempt(quiz_id=quiz.id, student_id=user.id, started_at=datetime.utcnow())
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
    now = datetime.utcnow()
    return {
        "quiz_id": str(quiz.id), "title": quiz.title, "mode": quiz.mode, "time_limit_seconds": quiz.time_limit_seconds,
        "seconds_left": _seconds_left(quiz, attempt, now), "questions": _public_questions(_quiz_questions(db, quiz.id)),
    }


@router.post("/quizzes/{quiz_id}/submit")
def submit_quiz(quiz_id: uuid.UUID, payload: QuizSubmit, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    quiz = _quiz(db, quiz_id)
    attempt = db.scalar(select(QuizAttempt).where(QuizAttempt.quiz_id == quiz.id, QuizAttempt.student_id == user.id))
    if attempt is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "attempt_not_started")
    if attempt.submitted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "already_submitted")
    questions = _quiz_questions(db, quiz.id)
    now = datetime.utcnow()
    duration = (now - attempt.started_at).total_seconds()
    if quiz.time_limit_seconds > 0:
        duration = min(duration, float(quiz.time_limit_seconds))
    plain = [{"id": q.id, "correct_index": q.correct_index, "points": q.points} for q in questions]
    result = quiz_scoring.score_attempt(plain, payload.answers, duration, quiz.mode, quiz.time_limit_seconds)
    attempt.score, attempt.correct, attempt.total = result["score"], result["correct"], result["total"]
    attempt.duration_seconds, attempt.submitted_at = round(duration, 2), now
    db.commit()
    board = _board(db, quiz)
    rank = next((r["rank"] for r in board if r["user_id"] == str(user.id)), None)
    review = [{"id": str(q.id), "correct_index": q.correct_index, "picked": payload.answers.get(str(q.id))} for q in questions]
    return {**result, "duration_seconds": round(duration, 2), "rank": rank, "participants": len(board), "review": review}


def _board(db: Session, quiz: Quiz) -> list[dict]:
    pairs = db.execute(
        select(QuizAttempt, User).join(User, User.id == QuizAttempt.student_id)
        .where(QuizAttempt.quiz_id == quiz.id, QuizAttempt.submitted_at.is_not(None))
    ).all()
    svgs = avatar_render.svgs_for(db, [u for _, u in pairs])
    rows = [{
        "user_id": str(u.id), "handle": u.handle, "full_name": u.full_name, "avatar_svg": svgs.get(u.id),
        "score": a.score, "correct": a.correct, "total": a.total, "duration_seconds": a.duration_seconds,
    } for a, u in pairs]
    return class_analytics.rank_rows(rows)


@router.get("/quizzes/{quiz_id}/leaderboard")
def quiz_leaderboard(quiz_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    quiz = _quiz(db, quiz_id)
    _access(db, quiz.classroom_id, user)
    return {"quiz": _quiz_dict(db, quiz, user), "rows": _board(db, quiz)}


@router.get("/{classroom_id}/leaderboard")
def class_leaderboard(classroom_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = _access(db, classroom_id, user)
    members = _members(db, room.id)
    svgs = avatar_render.svgs_for(db, members)
    quiz_ids = list(db.scalars(select(Quiz.id).where(Quiz.classroom_id == room.id)))
    totals, taken, spent = Counter(), Counter(), Counter()
    if quiz_ids:
        for sid, score, duration in db.execute(select(QuizAttempt.student_id, QuizAttempt.score, QuizAttempt.duration_seconds).where(
                QuizAttempt.quiz_id.in_(quiz_ids), QuizAttempt.submitted_at.is_not(None))):
            totals[sid] += score
            taken[sid] += 1
            spent[sid] += duration
    rows = [{**_person(m, svgs), "score": int(totals.get(m.id, 0)), "quizzes_taken": taken.get(m.id, 0),
             "duration_seconds": float(spent.get(m.id, 0.0))} for m in members]
    return {"quiz_count": len(quiz_ids), "rows": class_analytics.rank_rows(rows)}


@router.post("/{classroom_id}/remediation")
def assign_remediation(classroom_id: uuid.UUID, payload: RemediationCreate, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    room = _owner(db, classroom_id, user)
    plans.require_school(db, user)
    if payload.skill_id not in kg.SKILLS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown_skill")
    members = _members(db, room.id)
    overviews = {m.id: engine_bridge.state_overview(db, m.id) for m in members}
    ids = remediation.students_with_gap(overviews, payload.skill_id)
    if payload.student_ids is not None:
        wanted = set(payload.student_ids)
        ids = [i for i in ids if i in wanted]
    if not ids:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "no_students_with_gap")
    spec = remediation.build_remediation(payload.skill_id, datetime.utcnow(), payload.due_days)
    tip = spec.pop("tip")
    assignment = Assignment(classroom_id=room.id, target_ids=[str(i) for i in ids], **spec)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    names = {m.id: m.full_name for m in members}
    return {
        "assignment": _assignment_dict(assignment, room),
        "students": [{"user_id": str(i), "full_name": names[i]} for i in ids],
        "count": len(ids),
        "tip": tip,
    }


def _report_in_class(db: Session, room: Classroom, report_id: uuid.UUID) -> UserReport:
    report = db.get(UserReport, report_id)
    member_ids = {m.id for m in _members(db, room.id)}
    if report is None or not ({report.reporter_id, report.reported_user_id} & member_ids):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "report_not_found")
    return report


def _report_dict(report: UserReport, users: dict) -> dict:
    def who(uid):
        u = users.get(uid)
        return {"user_id": str(uid), "full_name": u.full_name if u else "", "handle": u.handle if u else None}
    return {
        "report_id": str(report.id), "reason": report.reason, "details": report.details, "status": report.status,
        "created_at": z(report.created_at), "reporter": who(report.reporter_id), "reported": who(report.reported_user_id),
        "has_message": report.message_id is not None, "resolution_note": report.resolution_note,
        "resolved_at": z(report.resolved_at),
    }


@router.get("/{classroom_id}/safety/reports")
def safety_reports(classroom_id: uuid.UUID, status_filter: str = "open", db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    room = _owner(db, classroom_id, user)
    member_ids = [m.id for m in _members(db, room.id)]
    if not member_ids:
        return []
    query = select(UserReport).where(or_(UserReport.reporter_id.in_(member_ids), UserReport.reported_user_id.in_(member_ids)))
    if status_filter in ("open", "resolved", "dismissed"):
        query = query.where(UserReport.status == status_filter)
    rows = list(db.scalars(query.order_by(UserReport.created_at.desc()).limit(100)))
    wanted = {r.reporter_id for r in rows} | {r.reported_user_id for r in rows}
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(wanted)))} if wanted else {}
    return [_report_dict(r, users) for r in rows]


@router.get("/{classroom_id}/safety/reports/{report_id}")
def safety_report_thread(classroom_id: uuid.UUID, report_id: uuid.UUID, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    room = _owner(db, classroom_id, user)
    report = _report_in_class(db, room, report_id)
    a, b = report.reporter_id, report.reported_user_id
    thread = db.scalars(
        select(DirectMessage)
        .where(or_(and_(DirectMessage.sender_id == a, DirectMessage.recipient_id == b),
                   and_(DirectMessage.sender_id == b, DirectMessage.recipient_id == a)))
        .order_by(DirectMessage.created_at.desc()).limit(30)
    ).all()
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_([a, b])))}
    return {
        **_report_dict(report, users),
        "thread": [
            {"message_id": str(m.id), "sender_id": str(m.sender_id), "sender_name": users[m.sender_id].full_name,
             "body": m.body, "created_at": z(m.created_at), "flagged": m.id == report.message_id}
            for m in reversed(thread)
        ],
    }


@router.post("/{classroom_id}/safety/reports/{report_id}/resolve")
def resolve_report(classroom_id: uuid.UUID, report_id: uuid.UUID, payload: ReportResolve,
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = _owner(db, classroom_id, user)
    report = _report_in_class(db, room, report_id)
    report.status = payload.action
    report.resolution_note = payload.note.strip()
    report.resolved_by = user.id
    report.resolved_at = datetime.utcnow()
    db.commit()
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_([report.reporter_id, report.reported_user_id])))}
    return _report_dict(report, users)
