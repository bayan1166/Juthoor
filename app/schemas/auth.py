import uuid
from datetime import datetime  # noqa: F401

from app.schemas.common import OptUtcDateTime, UtcDateTime  # noqa: F401
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.engine import config as ecfg
from app.models.org import UserRole

# B2C: only learners and their parents/guardians can create accounts.
SELF_REGISTER_ROLES = {UserRole.student, UserRole.parent}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=1, max_length=150)
    # Only student/parent: any other value (including "platform_admin" or the retired "teacher") is a 422.
    role: UserRole = UserRole.student
    guardian_id: uuid.UUID | None = None
    guardian_email: EmailStr | None = None
    grade_level: int = Field(default=ecfg.COURSE["grade"], ge=1, le=12)
    gender: Literal["ولد", "بنت"] | None = None

    @field_validator("email")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("full_name must not be blank")
        return v

    @field_validator("role")
    @classmethod
    def _only_b2c_roles(cls, v: UserRole) -> UserRole:
        if v not in SELF_REGISTER_ROLES:
            raise ValueError("this role cannot be self-registered")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return v.lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    role: UserRole


class MeOut(BaseModel):
    user_id: uuid.UUID
    handle: str | None = None
    email: str
    full_name: str
    role: UserRole
    grade_level: int
    plan: str = "basic"
    plan_source: str = "own"
    plan_expires_at: OptUtcDateTime = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class ResetTokenOut(BaseModel):
    reset_token: str


class ResetPasswordRequest(BaseModel):
    reset_token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=6, max_length=128)
