import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_student_access
from app.models.org import User, UserRole
from app.schemas.dashboard import CohortInsightsOut, RosterStudentOut, StudentInsightsOut
from app.services import dashboard_service, plans

router = APIRouter(tags=["dashboard"])


@router.get("/students/{student_id}/insights", response_model=StudentInsightsOut)
def get_student_insights(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    report = dashboard_service.student_insights(db, student_id)
    student = db.get(User, student_id)
    if not plans.has_full_gap_access(db, user, student):
        alerts = []
        for alert in report["struggle_alerts"]:
            alerts.append({**alert, "predicted_root_cause_skill": None,
                           "recommended_action": "يتوفر الإجراء المقترح في باقة برو"})
        report = {**report, "struggle_alerts": alerts, "gap_report_locked": True}
    return report


@router.get("/organizations/{organization_id}/insights", response_model=CohortInsightsOut)
def get_cohort_insights(organization_id: uuid.UUID, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    if user.role not in (UserRole.org_admin, UserRole.platform_admin, UserRole.teacher):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient_role")
    if user.role != UserRole.platform_admin and user.organization_id != organization_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "cross_organization_access_denied")
    plans.require_school(db, user)
    return dashboard_service.cohort_insights(db, organization_id)


@router.get("/me/students", response_model=list[RosterStudentOut])
def my_students(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
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
    return [
        RosterStudentOut(student_id=s.id, full_name=s.full_name, email=s.email, grade_level=s.grade_level)
        for s in students
    ]
