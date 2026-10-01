from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.adaptive import AttemptLog
from app.models.chat import ChatMessage, ChatRole, ChatSession
from app.models.classroom import Classroom, ClassroomMember
from app.models.community import Friendship, FriendshipStatus
from app.models.org import PlanTierUser, User, UserRole
from app.services.plan_rules import (
    LIMITS, LOCAL_UTC_OFFSET_HOURS, PERIOD_DAYS, PLAN_CATALOG, STUDENTS_PER_SEAT, TRIAL_DAYS, USP, PlanState,
    day_start_utc, forecast_days, limits_for, mask_drilldowns, plan_from_fields, price_for, trial_days_left,
)

STAFF_ROLES = (UserRole.teacher, UserRole.org_admin, UserRole.platform_admin)


def _class_sponsored(db: Session, student_id, now: datetime) -> bool:
    row = db.scalar(
        select(func.count(ClassroomMember.id))
        .join(Classroom, Classroom.id == ClassroomMember.classroom_id)
        .join(User, User.id == Classroom.teacher_id)
        .where(
            ClassroomMember.student_id == student_id,
            User.plan == PlanTierUser.school,
            or_(User.plan_expires_at.is_(None), User.plan_expires_at > now),
        )
    )
    return bool(row)


def effective_plan(db: Session, user: User, now: datetime | None = None) -> PlanState:
    now = now or datetime.utcnow()
    own = plan_from_fields(user.plan, user.plan_expires_at, now)
    if own != "basic":
        left = trial_days_left(user.trial_ends_at, now)
        return PlanState(own, "trial" if left else "own", user.plan_expires_at, left)
    if user.role == UserRole.student and _class_sponsored(db, user.id, now):
        return PlanState("pro", "class", None, None)
    return PlanState("basic", "own", None, None)


def usage_today(db: Session, user_id, now: datetime | None = None) -> dict:
    start = day_start_utc(now)
    questions = db.scalar(
        select(func.count(AttemptLog.id)).where(AttemptLog.student_id == user_id, AttemptLog.created_at >= start)
    ) or 0
    tutor = db.scalar(
        select(func.count(ChatMessage.id))
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(ChatSession.student_id == user_id, ChatMessage.role == ChatRole.student,
               ChatMessage.created_at >= start)
    ) or 0
    return {"questions": int(questions), "tutor": int(tutor)}


def _remaining(limit, used):
    return None if limit is None else max(0, limit - used)


def snapshot(db: Session, user: User) -> dict:
    state = effective_plan(db, user)
    limits = limits_for(state.plan)
    used = usage_today(db, user.id)
    return {
        "plan": state.plan,
        "source": state.source,
        "expires_at": state.expires_at.isoformat() + "Z" if state.expires_at else None,
        "trial_days_left": state.trial_days_left,
        "limits": limits,
        "usage": used,
        "remaining": {
            "questions": _remaining(limits["questions_per_day"], used["questions"]),
            "tutor": _remaining(limits["tutor_per_day"], used["tutor"]),
        },
    }


def require_quota(db: Session, student: User, kind: str) -> None:
    limit = LIMITS[effective_plan(db, student).plan][f"{kind}_per_day"]
    if limit is None:
        return
    if usage_today(db, student.id)[kind] >= limit:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, f"daily_limit_reached:{kind}")


def has_full_gap_access(db: Session, viewer: User, student: User) -> bool:
    if viewer.role in STAFF_ROLES:
        return True
    return LIMITS[effective_plan(db, student).plan]["full_gap_report"]


def require_school(db: Session, user: User) -> None:
    if user.role == UserRole.platform_admin:
        return
    if effective_plan(db, user).plan != "school":
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "plan_upgrade_required:school")


def friend_cap_reached(db: Session, user: User) -> bool:
    cap = LIMITS[effective_plan(db, user).plan]["max_friends"]
    if cap is None:
        return False
    accepted = db.scalar(
        select(func.count(Friendship.id)).where(
            Friendship.status == FriendshipStatus.accepted,
            or_(Friendship.requester_id == user.id, Friendship.addressee_id == user.id),
        )
    ) or 0
    outgoing = db.scalar(
        select(func.count(Friendship.id)).where(
            Friendship.status == FriendshipStatus.pending, Friendship.requester_id == user.id
        )
    ) or 0
    return (accepted + outgoing) >= cap
