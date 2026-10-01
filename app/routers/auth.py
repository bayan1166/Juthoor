from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.adaptive import StudentAdaptiveState
from app.models.economy import AvatarConfig, Wallet
from app.models.org import Organization, User, UserRole
from app.schemas.auth import ForgotPasswordRequest, LoginRequest, MeOut, RegisterRequest, ResetPasswordRequest, TokenResponse
from app.security import create_access_token, hash_password, verify_password
from app.services.economy_service import get_or_create_wallet

import hashlib
import os
import secrets
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["auth"])


def _unique_handle(db: Session, length: int = 4, max_tries: int = 10) -> str:
    """Random numeric handle, grown by 1 digit after every collision streak."""
    for _ in range(max_tries):
        candidate = str(secrets.randbelow(10 ** length - 10 ** (length - 1)) + 10 ** (length - 1))
        if db.scalar(select(User).where(User.handle == candidate)) is None:
            return candidate
        length += 1
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "handle_generation_failed")


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _send_reset_email(email: str, link: str) -> None:
    """Deliver via SMTP if configured; otherwise log so the demo still works end-to-end."""
    import logging
    logger = logging.getLogger("juthoor.auth")
    host = os.environ.get("SMTP_HOST")
    if not host:
        logger.warning("PASSWORD RESET for %s -> %s  (set SMTP_HOST to send real emails)", email, link)
        return
    import smtplib
    from email.mime.text import MIMEText
    msg = MIMEText(f"رابط إعادة تعيين كلمة المرور في جذور (صالح لـ 30 دقيقة):\n\n{link}", "plain", "utf-8")
    msg["Subject"] = "إعادة تعيين كلمة المرور — جذور"
    msg["From"] = os.environ.get("SMTP_FROM", "no-reply@juthoor.jo")
    msg["To"] = email
    try:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=10) as srv:
            srv.starttls()
            if os.environ.get("SMTP_USER"):
                srv.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            srv.send_message(msg)
    except Exception:
        logger.exception("SMTP failed; token still valid: %s", link)



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

    guardian_id = payload.guardian_id
    if payload.guardian_email is not None and guardian_id is None:
        g = db.scalar(select(User).where(User.email == str(payload.guardian_email).lower()))
        if g is None or g.role != UserRole.parent:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "guardian_must_be_existing_parent")
        guardian_id = g.id
    if guardian_id is not None:
        guardian = db.get(User, guardian_id)
        if guardian is None or guardian.role != UserRole.parent:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "guardian_must_be_existing_parent")

    user = User(
        email=payload.email, hashed_password=hash_password(payload.password),
        full_name=payload.full_name, role=payload.role, grade_level=payload.grade_level,
        guardian_id=guardian_id, organization_id=org.id if org else None,
    )
    db.add(user)
    db.flush()

    if payload.role == UserRole.student:
        db.add(StudentAdaptiveState(student_id=user.id, current_skill="absolute_value", difficulty=1))
        cfg = AvatarConfig(student_id=user.id)
        if payload.gender:
            cfg.gender = payload.gender
        db.add(cfg)
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


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)):
    return MeOut(user_id=user.id, handle=user.handle, email=user.email, full_name=user.full_name,
                 role=user.role, organization_id=user.organization_id,
                 organization_name=user.organization.name if user.organization else None,
                 grade_level=user.grade_level,
                 plan=user.plan.value if hasattr(user.plan, "value") else str(user.plan),
                 plan_expires_at=user.plan_expires_at)


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Always 200, even if the email doesn't exist (prevents account enumeration)."""
    from app.models.password_reset import PasswordResetToken
    from datetime import datetime
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is not None:
        raw = secrets.token_urlsafe(32)
        token = PasswordResetToken(user_id=user.id, token_hash=_hash_token(raw),
                                   expires_at=datetime.utcnow() + timedelta(minutes=30))
        db.add(token); db.commit()
        base = os.environ.get("PUBLIC_URL", "http://localhost:8501")
        _send_reset_email(user.email, f"{base}/?reset_token={raw}")
    return {"status": "if that email exists, a reset link has been sent"}


@router.post("/reset-password", response_model=TokenResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    from app.models.password_reset import PasswordResetToken
    from app.security import create_access_token, hash_password
    from datetime import datetime
    tok = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_token(payload.token)))
    if tok is None or tok.used or tok.expires_at < datetime.utcnow():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid_or_expired_token")
    user = db.get(User, tok.user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    user.hashed_password = hash_password(payload.new_password)
    tok.used = True
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.role),
                         user_id=user.id, role=user.role)
