import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PlanTier(str, enum.Enum):
    free = "free"
    school = "school"
    district = "district"


class UserRole(str, enum.Enum):
    student = "student"
    parent = "parent"
    teacher = "teacher"
    org_admin = "org_admin"
    platform_admin = "platform_admin"


class PlanTierUser(str, enum.Enum):
    """A user's subscription level. Independent from organization.plan_tier so a solo
    student can upgrade without their school having to. Basic is free forever."""
    basic = "basic"
    pro = "pro"
    max = "max"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    plan_tier: Mapped[PlanTier] = mapped_column(Enum(PlanTier), default=PlanTier.free)
    seat_limit: Mapped[int] = mapped_column(default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), default="")
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.student)
    guardian_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    grade_level: Mapped[int] = mapped_column(default=6)
    plan: Mapped[PlanTierUser] = mapped_column(Enum(PlanTierUser), default=PlanTierUser.basic, index=True)
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Public handle (e.g. "7429"): the ONLY identifier other users can search by.
    # Random 4+ digit code generated at signup, unique per user, immutable.
    handle: Mapped[str | None] = mapped_column(String(12), unique=True, nullable=True, index=True)
    locale: Mapped[str] = mapped_column(String(8), default="ar")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped[Organization | None] = relationship(back_populates="users")
