import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CheckoutStartRequest(BaseModel):
    plan: str = Field(pattern=r"^(pro|max)$")


class CheckoutStartResponse(BaseModel):
    session_id: uuid.UUID
    provider: str
    plan: str
    amount_minor: int
    currency: str
    stripe_url: str | None = None       # if the mode is Stripe, redirect here


class CheckoutConfirmRequest(BaseModel):
    """Sent by the mock processor from the client after client-side validation. Ignored
    when the mode is Stripe (Stripe confirms via webhook / redirect)."""
    session_id: uuid.UUID
    card_last4: str = Field(min_length=4, max_length=4)
    card_holder: str = Field(min_length=1, max_length=120)


class CheckoutStatusOut(BaseModel):
    session_id: uuid.UUID
    plan: str
    status: str
    amount_minor: int
    currency: str
    provider: str
    created_at: datetime
