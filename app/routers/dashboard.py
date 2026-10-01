import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_plan, require_student_access
from app.models.org import PlanTierUser
from app.models.org import User, UserRole
from app.schemas.dashboard import CohortInsightsOut, RosterStudentOut, StudentInsightsOut
from app.services import dashboard_service

router = APIRouter(tags=["dashboard"])


@router.get("/students/{student_id}/insights", response_model=StudentInsightsOut)
def get_student_insights(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    return dashboard_service.student_insights(db, student_id)


@router.get("/organizations/{organization_id}/insights", response_model=CohortInsightsOut)
def get_cohort_insights(organization_id: uuid.UUID, db: Session = Depends(get_db),
                        user: User = Depends(require_plan(PlanTierUser.max))):
    if user.role not in (UserRole.org_admin, UserRole.platform_admin, UserRole.teacher):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient_role")
    if user.role != UserRole.platform_admin and user.organization_id != organization_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "cross_organization_access_denied")
    return dashboard_service.cohort_insights(db, organization_id)


@router.get("/me/students", response_model=list[RosterStudentOut])
def my_students(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Students the caller may view: a parent's linked children, or a teacher's/org admin's
    organization. Replaces typing a student UUID by hand in the dashboard."""
    query = select(User).where(User.role == UserRole.student, User.is_active.is_(True))
    if user.role == UserRole.parent:
        query = query.where(User.guardian_id == user.id)
    elif user.role in (UserRole.teacher, UserRole.org_admin):
        if user.organization_id is None:
            return []
        query = query.where(User.organization_id == user.organization_id)
    elif user.role == UserRole.platform_admin:
        pass
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient_role")
    students = db.scalars(query.order_by(User.full_name).limit(500)).all()
    return [RosterStudentOut(
        student_id=s.id, full_name=s.full_name, email=s.email, grade_level=s.grade_level,
    ) for s in students]
