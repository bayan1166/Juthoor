import hashlib
import hmac
import logging
import secrets
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.ratelimit import clear_failures, client_ip, failures_blocked, record_failure, throttle
from app.database import get_db
from app.deps import get_current_user
from app.models.adaptive import StudentAdaptiveState
from app.models.economy import AvatarConfig
from app.models.org import User, UserRole
from app.models.password_reset import PasswordResetToken
from app.schemas.auth import (
    ForgotPasswordRequest, LoginRequest, MeOut, RegisterRequest, ResetPasswordRequest,
    ResetTokenOut, TokenResponse, VerifyCodeRequest,
)
from app.security import create_access_token, hash_password, verify_password
from app.services import child_link, identity, plans

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("juthoor.auth")

CODE_MINUTES = 15
RESET_MINUTES = 10
MAX_CODE_ATTEMPTS = 5


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _code_hash(user_id, code: str) -> str:
    return _digest(f"{user_id}:{code}")


def _token_for(user: User) -> TokenResponse:
    token = create_access_token(str(user.id), user.role.value)
    return TokenResponse(access_token=token, user_id=user.id, role=user.role)


def _deliver_code(email: str, code: str) -> None:
    if not settings.smtp_host:
        # Never write a live reset code to the logs outside demo mode (anyone with log access could take over the account).
        if settings.demo_mode:
            logger.warning("SMTP not configured; demo mode: password reset code for %s is %s", email, code)
        else:
            logger.error("SMTP is not configured: password reset code for %s was NOT delivered", email)
        return
    msg = MIMEText(f"رمز إعادة تعيين كلمة المرور في جذور: {code}\nالرمز صالح لمدة {CODE_MINUTES} دقيقة.", "plain", "utf-8")
    msg["Subject"] = "رمز إعادة تعيين كلمة المرور - جذور"
    msg["From"] = settings.smtp_from
    msg["To"] = email
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except Exception:
        logger.exception("smtp delivery failed for %s", email)


@router.post("/register", response_model=TokenResponse)
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    throttle("register", client_ip(request), 20, 3600)
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "email_already_registered")

    guardian_id = None
    child = None
    if payload.role == UserRole.parent:
        # A parent/guardian account is created only together with its link to an existing learner, so the
        # database never holds a parent without a child. Everything is checked before any row is written.
        if not child_link.normalise(payload.child_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "child_id_required")
        child = child_link.resolve(db, payload.child_id, lock=True)
        if child is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "child_id_invalid")
        if child.guardian_id is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "child_already_linked")
    else:
        guardian_id = payload.guardian_id
        if payload.guardian_email is not None and guardian_id is None:
            found = db.scalar(select(User).where(User.email == str(payload.guardian_email).lower()))
            if found is None or found.role != UserRole.parent:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "guardian_must_be_existing_parent")
            guardian_id = found.id
        if guardian_id is not None:
            guardian = db.get(User, guardian_id)
            if guardian is None or guardian.role != UserRole.parent:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "guardian_must_be_existing_parent")

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
        guardian_id=guardian_id,
        grade_level=payload.grade_level,
        handle=identity.unique_handle(db),
    )
    db.add(user)
    db.flush()

    if child is not None:
        child.guardian_id = user.id  # same transaction as the parent row: both are saved or neither is
    if payload.role == UserRole.student:
        db.add(StudentAdaptiveState(student_id=user.id, current_skill="absolute_value", difficulty=1))
        cfg = AvatarConfig(student_id=user.id)
        if payload.gender:
            cfg.gender = payload.gender
        db.add(cfg)
    db.commit()
    return _token_for(user)


@router.post("/login", response_model=TokenResponse)
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    throttle("login-ip", client_ip(request), 40, 60)
    email = str(payload.email).lower()
    fail_key = f"login-fail:{email}"
    wait = failures_blocked(fail_key, 5, 900)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_attempts", headers={"Retry-After": str(wait)})
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        record_failure(fail_key, 900)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_credentials")
    clear_failures(fail_key)
    return _token_for(user)


@router.get("/me", response_model=MeOut)
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    state = plans.effective_plan(db, user)
    return MeOut(
        user_id=user.id, handle=user.handle, email=user.email, full_name=user.full_name, role=user.role,
        grade_level=user.grade_level, plan=state.plan, plan_source=state.source,
        plan_expires_at=state.expires_at, child_id=child_link.child_id_for(user),
    )


@router.post("/forgot-password")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    throttle("forgot-ip", client_ip(request), 10, 3600)
    throttle("forgot-email", email, 3, 600)
    body = {"status": "sent"}
    user = db.scalar(select(User).where(User.email == email))
    if user is not None and user.is_active:
        now = datetime.utcnow()
        for old in db.scalars(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id, PasswordResetToken.used.is_(False))
        ):
            old.used = True
        code = f"{secrets.randbelow(1_000_000):06d}"
        db.add(PasswordResetToken(
            user_id=user.id, code_hash=_code_hash(user.id, code), expires_at=now + timedelta(minutes=CODE_MINUTES)
        ))
        db.commit()
        _deliver_code(user.email, code)
        if settings.demo_mode:
            body["demo_code"] = code
    return body


@router.post("/verify-reset-code", response_model=ResetTokenOut)
def verify_reset_code(request: Request, payload: VerifyCodeRequest, db: Session = Depends(get_db)):
    throttle("verify-ip", client_ip(request), 30, 600)
    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "invalid_or_expired_code")
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is None:
        raise invalid
    now = datetime.utcnow()
    row = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used.is_(False),
               PasswordResetToken.verified.is_(False))
        .order_by(PasswordResetToken.created_at.desc())
    )
    if row is None or row.expires_at < now:
        raise invalid
    if row.attempts >= MAX_CODE_ATTEMPTS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_attempts")
    row.attempts += 1
    if not hmac.compare_digest(row.code_hash, _code_hash(user.id, payload.code)):
        db.commit()
        raise invalid
    raw = secrets.token_urlsafe(32)
    row.verified = True
    row.reset_token_hash = _digest(raw)
    row.expires_at = now + timedelta(minutes=RESET_MINUTES)
    db.commit()
    return ResetTokenOut(reset_token=raw)


@router.post("/reset-password", response_model=TokenResponse)
def reset_password(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    throttle("reset-ip", client_ip(request), 20, 600)
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.reset_token_hash == _digest(payload.reset_token)))
    if row is None or not row.verified or row.used or row.expires_at < datetime.utcnow():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid_or_expired_code")
    user = db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    user.hashed_password = hash_password(payload.new_password)
    row.used = True
    db.commit()
    return _token_for(user)
