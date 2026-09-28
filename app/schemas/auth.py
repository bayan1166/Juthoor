import uuid

from pydantic import BaseModel, EmailStr

from app.models.org import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.student
    org_slug: str | None = None
    guardian_id: uuid.UUID | None = None
    grade_level: int = 6


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    role: UserRole
