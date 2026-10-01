import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import OptUtcDateTime, UtcDateTime


class PublicUser(BaseModel):
    user_id: uuid.UUID
    handle: str | None = None
    full_name: str
    role: str
    avatar_svg: str | None = None


class SearchResult(PublicUser):
    friendship_status: str | None = None


class FriendshipOut(BaseModel):
    friendship_id: uuid.UUID
    friend: PublicUser
    status: str
    is_incoming: bool
    created_at: UtcDateTime


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class MessageOut(BaseModel):
    message_id: uuid.UUID
    sender_id: uuid.UUID
    recipient_id: uuid.UUID
    body: str
    created_at: UtcDateTime
    read_at: OptUtcDateTime = None


class ConversationOut(BaseModel):
    friendship_id: uuid.UUID
    friend: PublicUser
    last_message: MessageOut | None = None
    unread: int = 0


class SummaryOut(BaseModel):
    unread_messages: int
    pending_requests: int


class ReportIn(BaseModel):
    user_id: uuid.UUID
    message_id: uuid.UUID | None = None
    reason: Literal["bullying", "inappropriate", "contact_info", "spam", "other"]
    details: str = Field(default="", max_length=1000)
    also_block: bool = False
