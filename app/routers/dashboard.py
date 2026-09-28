import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_student_access
from app.models.org import User, UserRole
from app.schemas.dashboard import CohortInsightsOut, StudentInsightsOut
from app.services import dashboard_service

router = APIRouter(tags=["dashboard"])


@router.get("/students/{student_id}/insights", response_model=StudentInsightsOut)
def get_student_insights(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    return dashboard_service.student_insights(db, student_id)


@router.get("/organizations/{organization_id}/insights", response_model=CohortInsightsOut)
def get_cohort_insights(organization_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in (UserRole.org_admin, UserRole.platform_admin, UserRole.teacher):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient_role")
    if user.role != UserRole.platform_admin and user.organization_id != organization_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "cross_organization_access_denied")
    return dashboard_service.cohort_insights(db, organization_id)
