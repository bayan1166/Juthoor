from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.adaptive import StudentAdaptiveState
from app.models.economy import AvatarConfig, Wallet
from app.models.org import Organization, User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.security import create_access_token, hash_password, verify_password
from app.services.economy_service import get_or_create_wallet

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "email_already_registered")

    org = None
    if payload.org_slug:
        org = db.scalar(select(Organization).where(Organization.slug == payload.org_slug))
        if org is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "organization_not_found")

    user = User(
        email=payload.email, hashed_password=hash_password(payload.password),
        full_name=payload.full_name, role=payload.role, grade_level=payload.grade_level,
        guardian_id=payload.guardian_id, organization_id=org.id if org else None,
    )
    db.add(user)
    db.flush()

    if payload.role == UserRole.student:
        db.add(StudentAdaptiveState(student_id=user.id, current_skill="absolute_value", difficulty=1))
        db.add(AvatarConfig(student_id=user.id))
        get_or_create_wallet(db, user.id)

    db.commit()
    token = create_access_token(str(user.id), user.role.value, str(user.organization_id) if user.organization_id else None)
    return TokenResponse(access_token=token, user_id=user.id, role=user.role)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_credentials")
    token = create_access_token(str(user.id), user.role.value, str(user.organization_id) if user.organization_id else None)
    return TokenResponse(access_token=token, user_id=user.id, role=user.role)
