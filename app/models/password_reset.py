"""Single-use password-reset tokens.

Flow:
  * POST /auth/forgot-password with an email -> we always return 200 (prevents email
    enumeration), and -- if the email exists -- insert a PasswordResetToken row and
    deliver the link. SMTP sends a real email if configured; otherwise the token is
    written to the server log so the demo still works end-to-end.
  * POST /auth/reset-password with the token + new password -> we verify the token
    hasn't expired or been consumed, update the hash, mark the token used.
Tokens are opaque 32-byte URL-safe strings, hashed with SHA-256 in the DB (never store
the raw token). Lifetime: 30 minutes.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)   # sha256 hex
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
