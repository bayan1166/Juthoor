"""Subscription checkout: sessions + completed transactions.

Two backends are supported at runtime:
  * Stripe test mode (if STRIPE_SECRET_KEY is set). Real Stripe Checkout Session URLs
    that accept Stripe test cards (4242 4242 4242 4242, any future date, any CVC).
    No real money moves. No merchant account required.
  * Local mock processor (fallback). Same request/response shape as Stripe so the
    frontend code is identical; validates the card client-side and marks the session
    "succeeded" on POST /confirm. Used in the demo and in tests.

The frontend never talks to the payment provider directly — always through
/payments/* endpoints, so switching processors is a config change, not a code change.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CheckoutStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"


class CheckoutSession(Base):
    __tablename__ = "checkout_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    plan: Mapped[str] = mapped_column(String(16))
    amount_minor: Mapped[int] = mapped_column(Integer)                    # in cents / fils, currency-safe
    currency: Mapped[str] = mapped_column(String(3), default="JOD")
    provider: Mapped[str] = mapped_column(String(16), default="mock")     # mock | stripe
    provider_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[CheckoutStatus] = mapped_column(Enum(CheckoutStatus), default=CheckoutStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
