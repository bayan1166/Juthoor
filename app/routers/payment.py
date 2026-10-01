"""Checkout endpoints. See app/models/payment.py for the two-backend design."""
import os
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models.org import PlanTierUser, User
from app.models.payment import CheckoutSession, CheckoutStatus
from app.schemas.payment import (
    CheckoutConfirmRequest, CheckoutStartRequest, CheckoutStartResponse, CheckoutStatusOut,
)

router = APIRouter(prefix="/payments", tags=["payments"])

# Per-student annual price in JOD minor units (fils). 1 JOD = 1000 fils.
PLAN_PRICES = {"pro": 12_000, "max": 20_000}


def _stripe_secret() -> str | None:
    return os.environ.get("STRIPE_SECRET_KEY") or getattr(settings, "stripe_secret_key", None)


@router.post("/checkout", response_model=CheckoutStartResponse)
def start_checkout(payload: CheckoutStartRequest, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Create a pending checkout session. If STRIPE_SECRET_KEY is set, also create a
    Stripe Checkout Session in test mode and return its hosted-checkout URL. Otherwise
    the frontend's own mock form handles the collection and calls /confirm."""
    if payload.plan not in PLAN_PRICES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown_plan")
    amount = PLAN_PRICES[payload.plan]

    stripe_key = _stripe_secret()
    provider, provider_ref, stripe_url = "mock", None, None
    if stripe_key:
        try:
            import stripe
            stripe.api_key = stripe_key
            base = os.environ.get("PUBLIC_URL", "http://localhost:8501")
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": "jod",
                        "product_data": {"name": f"Juthoor {payload.plan.title()} — annual per student"},
                        "unit_amount": amount,
                    },
                    "quantity": 1,
                }],
                success_url=f"{base}/?payment=success",
                cancel_url=f"{base}/?payment=cancel",
                metadata={"user_id": str(user.id), "plan": payload.plan},
            )
            provider, provider_ref, stripe_url = "stripe", session.id, session.url
        except Exception:
            provider, provider_ref, stripe_url = "mock", None, None

    row = CheckoutSession(user_id=user.id, plan=payload.plan, amount_minor=amount,
                          currency="JOD", provider=provider, provider_ref=provider_ref,
                          status=CheckoutStatus.pending)
    db.add(row); db.commit(); db.refresh(row)
    return CheckoutStartResponse(session_id=row.id, provider=provider, plan=row.plan,
                                 amount_minor=row.amount_minor, currency=row.currency,
                                 stripe_url=stripe_url)


@router.post("/confirm", response_model=CheckoutStatusOut)
def confirm_checkout(payload: CheckoutConfirmRequest, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Mock-processor completion. Card details never touch the server in real Stripe
    mode; here we only store the last-4 and holder name for the receipt."""
    row = db.get(CheckoutSession, payload.session_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session_not_found")
    if row.provider != "mock":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "confirm_only_for_mock_provider")
    if row.status != CheckoutStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "session_not_pending")
    if not payload.card_last4.isdigit():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "bad_card")
    row.status = CheckoutStatus.succeeded
    row.provider_ref = f"mock_{payload.card_last4}_{payload.card_holder[:32]}"

    # Grant the plan.
    user.plan = PlanTierUser(row.plan)
    user.plan_expires_at = datetime.utcnow() + timedelta(days=365)
    db.commit()
    return _status_of(row)


@router.get("/session/{session_id}", response_model=CheckoutStatusOut)
def session_status(session_id: uuid.UUID, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    row = db.get(CheckoutSession, session_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session_not_found")
    return _status_of(row)


def _status_of(row: CheckoutSession) -> CheckoutStatusOut:
    return CheckoutStatusOut(session_id=row.id, plan=row.plan, status=row.status.value,
                             amount_minor=row.amount_minor, currency=row.currency,
                             provider=row.provider, created_at=row.created_at)
