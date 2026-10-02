import uuid
from datetime import datetime  # noqa: F401

from app.schemas.common import OptUtcDateTime, UtcDateTime  # noqa: F401

from pydantic import BaseModel, Field


class ChatStartRequest(BaseModel):
    skill_context: str


class ChatStartResponse(BaseModel):
    session_id: uuid.UUID
    opening_message: str


class ChatMessageRequest(BaseModel):
    session_id: uuid.UUID
    message: str = Field(min_length=1, max_length=1000)


class ChatMessageResponse(BaseModel):
    reply: str
    gap_detected: bool = False
    gap_skill: str | None = None
    drill_down_triggered: bool = False
    next_skill: str | None = None
    next_difficulty: int | None = None
    breadcrumb: str = ""
    remaining_today: int | None = None
    source: str = "tutor"


class ChatHistoryItem(BaseModel):
    role: str
    content: str
    created_at: UtcDateTime
