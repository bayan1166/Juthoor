import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models.org import PlanTierUser, User, UserRole
from app.models.payment import CheckoutSession, CheckoutStatus
from app.schemas.payment import (
    CheckoutConfirmRequest, CheckoutStartRequest, CheckoutStartResponse, CheckoutStatusOut, StripeConfirmRequest,
)
from app.services import plans

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/plans")
def catalogue():
    return {"plans": [{**p, "limits": plans.LIMITS[p["id"]]} for p in plans.PLAN_CATALOG], "usp": plans.USP, "currency": "JOD"}


def _beneficiary(db: Session, payload: CheckoutStartRequest, user: User) -> User:
    if payload.plan == "school":
        if user.role not in plans.STAFF_ROLES:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "school_plan_for_teachers")
        return user
    if user.role in plans.STAFF_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "pro_plan_for_students")
    if user.role == UserRole.parent:
        if payload.for_student_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "child_required")
        child = db.get(User, payload.for_student_id)
        if child is None or child.guardian_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "cannot_access_student")
        return child
    return user


def _grant(db: Session, row: CheckoutSession) -> None:
    target = db.get(User, row.beneficiary_id or row.user_id)
    now = datetime.utcnow()
    current = target.plan.value if hasattr(target.plan, "value") else str(target.plan)
    start = now
    if current == row.plan and target.plan_expires_at and target.plan_expires_at > now and target.trial_ends_at is None:
        start = target.plan_expires_at
    target.plan = PlanTierUser(row.plan)
    target.plan_expires_at = start + timedelta(days=plans.PERIOD_DAYS[row.period])
    target.trial_ends_at = None
    row.status = CheckoutStatus.succeeded


def _out(row: CheckoutSession) -> CheckoutStatusOut:
    return CheckoutStatusOut(
        session_id=row.id, plan=row.plan, period=row.period, status=row.status.value,
        amount_minor=row.amount_minor, currency=row.currency, provider=row.provider, created_at=row.created_at,
    )


def _own(db: Session, session_id: uuid.UUID, user: User) -> CheckoutSession:
    row = db.get(CheckoutSession, session_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session_not_found")
    return row


@router.post("/checkout", response_model=CheckoutStartResponse)
def start_checkout(payload: CheckoutStartRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    target = _beneficiary(db, payload, user)
    amount = plans.price_for(payload.plan, payload.period)
    provider, ref, url = "mock", None, None
    if settings.stripe_secret_key:
        try:
            import stripe

            stripe.api_key = settings.stripe_secret_key
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": "jod",
                        "product_data": {"name": f"Juthoor {payload.plan} ({payload.period})"},
                        "unit_amount": amount,
                    },
                    "quantity": 1,
                }],
                success_url=f"{settings.public_url}/app/#/plans?paid=1",
                cancel_url=f"{settings.public_url}/app/#/plans",
                metadata={"user_id": str(user.id), "plan": payload.plan},
            )
            provider, ref, url = "stripe", session.id, session.url
        except Exception:
            provider, ref, url = "mock", None, None
    row = CheckoutSession(
        user_id=user.id, beneficiary_id=target.id, plan=payload.plan, period=payload.period,
        amount_minor=amount, currency="JOD", provider=provider, provider_ref=ref, status=CheckoutStatus.pending,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return CheckoutStartResponse(
        session_id=row.id, provider=provider, plan=row.plan, period=row.period,
        amount_minor=row.amount_minor, currency=row.currency, stripe_url=url,
    )


@router.post("/confirm", response_model=CheckoutStatusOut)
def confirm_checkout(payload: CheckoutConfirmRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = _own(db, payload.session_id, user)
    if row.provider != "mock":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "confirm_only_for_mock_provider")
    if row.status != CheckoutStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "session_not_pending")
    if len(payload.card_last4) != 4 or not payload.card_last4.isdigit() or not payload.card_holder.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "bad_card")
    row.provider_ref = f"mock_{payload.card_last4}"
    _grant(db, row)
    db.commit()
    return _out(row)


@router.post("/confirm-stripe", response_model=CheckoutStatusOut)
def confirm_stripe(payload: StripeConfirmRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = _own(db, payload.session_id, user)
    if row.provider != "stripe" or not row.provider_ref:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "not_a_stripe_session")
    if row.status == CheckoutStatus.pending:
        try:
            import stripe

            stripe.api_key = settings.stripe_secret_key
            remote = stripe.checkout.Session.retrieve(row.provider_ref)
            paid = remote.payment_status == "paid"
        except Exception:
            paid = False
        if not paid:
            raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "payment_not_completed")
        _grant(db, row)
        db.commit()
    return _out(row)


@router.get("/session/{session_id}", response_model=CheckoutStatusOut)
def session_status(session_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _out(_own(db, session_id, user))
