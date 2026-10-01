import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.org import PlanTierUser, User, UserRole

PLAN_RANK = {PlanTierUser.basic: 0, PlanTierUser.pro: 1, PlanTierUser.max: 2}
from app.security import decode_access_token

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token")
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user_not_found")
    return user


def require_roles(*roles: UserRole):
    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient_role")
        return user
    return _check


def require_student_access(student_id: uuid.UUID, user: User, db: Session) -> None:
    if user.role == UserRole.student and user.id == student_id:
        return
    if user.role == UserRole.parent:
        child = db.get(User, student_id)
        if child is not None and child.guardian_id == user.id:
            return
    if user.role in (UserRole.teacher, UserRole.org_admin, UserRole.platform_admin):
        target = db.get(User, student_id)
        if target is not None and (user.role == UserRole.platform_admin or target.organization_id == user.organization_id):
            return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "cannot_access_student")


def require_plan(minimum: PlanTierUser):
    """Gate an endpoint by subscription level. Staff (teachers/admins) always pass —
    they use Juthoor on their students' behalf, not their own. Expired plans downgrade
    silently to Basic (checked at every call)."""
    from fastapi import HTTPException, status
    from datetime import datetime

    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role in (UserRole.teacher, UserRole.org_admin, UserRole.platform_admin, UserRole.parent):
            return user
        current = user.plan
        if user.plan_expires_at is not None and user.plan_expires_at < datetime.utcnow():
            current = PlanTierUser.basic
        if PLAN_RANK.get(current, 0) < PLAN_RANK[minimum]:
            raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, f"plan_upgrade_required:{minimum.value}")
        return user
    return _check
