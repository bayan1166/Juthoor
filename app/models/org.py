import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.engine import config as ecfg


class UserRole(str, enum.Enum):
    """Juthoor is B2C: the student is the user and the parent/guardian is the buyer.

    ``platform_admin`` is an internal operations account (content moderation); it cannot be self-registered
    and has no screen in the product.
    """

    student = "student"
    parent = "parent"
    platform_admin = "platform_admin"


class PlanTierUser(str, enum.Enum):
    basic = "basic"
    pro = "pro"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), default="")
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.student)
    guardian_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Grade of the learner; the default comes from the current content pack (content metadata, not product scope).
    grade_level: Mapped[int] = mapped_column(default=ecfg.COURSE["grade"])
    plan: Mapped[PlanTierUser] = mapped_column(Enum(PlanTierUser), default=PlanTierUser.basic, index=True)
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    handle: Mapped[str | None] = mapped_column(String(12), unique=True, nullable=True, index=True)
    locale: Mapped[str] = mapped_column(String(8), default="ar")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
