import uuid
from datetime import datetime  # noqa: F401

from app.schemas.common import OptUtcDateTime, UtcDateTime  # noqa: F401
from typing import Literal

from pydantic import BaseModel, Field


class CheckoutStartRequest(BaseModel):
    plan: Literal["pro", "school"]
    period: Literal["monthly", "yearly"] = "monthly"
    for_student_id: uuid.UUID | None = None


class CheckoutStartResponse(BaseModel):
    session_id: uuid.UUID
    provider: str
    plan: str
    period: str
    amount_minor: int
    currency: str
    stripe_url: str | None = None


class CheckoutConfirmRequest(BaseModel):
    session_id: uuid.UUID
    card_last4: str = Field(max_length=8)
    card_holder: str = Field(max_length=120)


class StripeConfirmRequest(BaseModel):
    session_id: uuid.UUID


class CheckoutStatusOut(BaseModel):
    session_id: uuid.UUID
    plan: str
    period: str
    status: str
    amount_minor: int
    currency: str
    provider: str
    created_at: UtcDateTime
