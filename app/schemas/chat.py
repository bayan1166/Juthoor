import uuid

from pydantic import BaseModel


class ChatStartRequest(BaseModel):
    skill_context: str


class ChatStartResponse(BaseModel):
    session_id: uuid.UUID
    opening_message: str


class ChatMessageRequest(BaseModel):
    session_id: uuid.UUID
    message: str


class ChatMessageResponse(BaseModel):
    reply: str
    gap_detected: bool
    gap_skill: str | None = None
    drill_down_triggered: bool = False
    next_skill: str | None = None
    next_difficulty: int | None = None
    breadcrumb: str = ""
