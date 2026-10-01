"""Teacher-owned classrooms + assignments. School-plan feature.

Only teachers can create. Students join with a 6-char code. Both see the member list.
Assignments are a (classroom, skill, due_at, target_questions) tuple; a student's
progress against them is derived from AttemptLog on the fly.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_plan
from app.engine import knowledge_graph as kg
from app.models.classroom import Assignment, Classroom, ClassroomMember
from app.models.org import PlanTierUser, User, UserRole
from app.schemas.classroom import (
    AssignmentCreate, AssignmentOut, ClassroomCreate, ClassroomOut, JoinRequest,
)

router = APIRouter(prefix="/classrooms", tags=["classrooms"])


def _classroom_out(db: Session, c: Classroom) -> ClassroomOut:
    members = db.scalar(select(func.count(ClassroomMember.id)).where(ClassroomMember.classroom_id == c.id)) or 0
    assigns = db.scalar(select(func.count(Assignment.id)).where(Assignment.classroom_id == c.id)) or 0
    return ClassroomOut(classroom_id=c.id, name=c.name, join_code=c.join_code,
                        teacher_id=c.teacher_id, member_count=int(members),
                        assignment_count=int(assigns), created_at=c.created_at)


@router.post("", response_model=ClassroomOut)
def create_classroom(payload: ClassroomCreate, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Teachers / org admins only. Returns the new classroom with its 6-char join code."""
    if user.role not in (UserRole.teacher, UserRole.org_admin, UserRole.platform_admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "teacher_role_required")
    c = Classroom(teacher_id=user.id, name=payload.name.strip())
    db.add(c); db.commit(); db.refresh(c)
    return _classroom_out(db, c)


@router.post("/join", response_model=ClassroomOut)
def join_classroom(payload: JoinRequest, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    if user.role != UserRole.student:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "student_role_required")
    c = db.scalar(select(Classroom).where(Classroom.join_code == payload.join_code.upper()))
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "classroom_not_found")
    exists = db.scalar(select(ClassroomMember).where(
        ClassroomMember.classroom_id == c.id, ClassroomMember.student_id == user.id))
    if exists is None:
        db.add(ClassroomMember(classroom_id=c.id, student_id=user.id))
        db.commit()
    return _classroom_out(db, c)


@router.get("", response_model=list[ClassroomOut])
def my_classrooms(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Teacher: classrooms they own. Student: classrooms they're a member of."""
    if user.role == UserRole.student:
        rows = db.scalars(select(Classroom).join(ClassroomMember,
            Classroom.id == ClassroomMember.classroom_id).where(ClassroomMember.student_id == user.id)
            .order_by(Classroom.created_at.desc())).all()
    else:
        rows = db.scalars(select(Classroom).where(Classroom.teacher_id == user.id)
            .order_by(Classroom.created_at.desc())).all()
    return [_classroom_out(db, c) for c in rows]


@router.get("/{classroom_id}/members")
def list_members(classroom_id: uuid.UUID, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    c = _access(db, classroom_id, user)
    rows = db.scalars(select(User).join(ClassroomMember, User.id == ClassroomMember.student_id)
                      .where(ClassroomMember.classroom_id == c.id).order_by(User.full_name)).all()
    return [{"user_id": str(u.id), "handle": u.handle, "full_name": u.full_name} for u in rows]


@router.post("/{classroom_id}/assignments", response_model=AssignmentOut)
def create_assignment(classroom_id: uuid.UUID, payload: AssignmentCreate,
                      db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = _access(db, classroom_id, user, teacher_only=True)
    if payload.skill_id not in kg.SKILLS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown_skill")
    a = Assignment(classroom_id=c.id, title=payload.title.strip(),
                   skill_id=payload.skill_id, target_questions=payload.target_questions,
                   due_at=payload.due_at)
    db.add(a); db.commit(); db.refresh(a)
    return _assignment_out(c, a)


@router.get("/assignments", response_model=list[AssignmentOut])
def my_assignments(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Everything the caller should see: their classrooms' assignments."""
    if user.role == UserRole.student:
        rows = db.execute(select(Assignment, Classroom).join(Classroom, Assignment.classroom_id == Classroom.id)
            .join(ClassroomMember, Classroom.id == ClassroomMember.classroom_id)
            .where(ClassroomMember.student_id == user.id)
            .order_by(Assignment.due_at.is_(None), Assignment.due_at, Assignment.created_at.desc())).all()
    else:
        rows = db.execute(select(Assignment, Classroom).join(Classroom, Assignment.classroom_id == Classroom.id)
            .where(Classroom.teacher_id == user.id).order_by(Assignment.created_at.desc())).all()
    return [_assignment_out(c, a) for a, c in rows]


def _access(db: Session, classroom_id: uuid.UUID, user: User, teacher_only: bool = False) -> Classroom:
    c = db.get(Classroom, classroom_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "classroom_not_found")
    if c.teacher_id == user.id:
        return c
    if teacher_only:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "teacher_only")
    is_member = db.scalar(select(ClassroomMember).where(
        ClassroomMember.classroom_id == c.id, ClassroomMember.student_id == user.id))
    if is_member is None and user.role != UserRole.platform_admin:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "classroom_not_found")
    return c


def _assignment_out(c: Classroom, a: Assignment) -> AssignmentOut:
    return AssignmentOut(assignment_id=a.id, classroom_id=c.id, classroom_name=c.name,
                         title=a.title, skill_id=a.skill_id,
                         skill_name_ar=kg.SKILLS[a.skill_id].name_ar if a.skill_id in kg.SKILLS else a.skill_id,
                         target_questions=a.target_questions, due_at=a.due_at, created_at=a.created_at)
