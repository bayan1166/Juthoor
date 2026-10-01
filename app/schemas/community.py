import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PublicUser(BaseModel):
    user_id: uuid.UUID
    handle: str | None = None
    full_name: str
    email: str
    role: str


class SearchResult(PublicUser):
    friendship_status: str | None = None    # None | pending_outgoing | pending_incoming | accepted | blocked


class FriendshipOut(BaseModel):
    friendship_id: uuid.UUID
    friend: PublicUser
    status: str
    is_incoming: bool
    created_at: datetime


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class MessageOut(BaseModel):
    message_id: uuid.UUID
    sender_id: uuid.UUID
    recipient_id: uuid.UUID
    body: str
    created_at: datetime
