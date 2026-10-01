import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ClassroomOut(BaseModel):
    classroom_id: uuid.UUID
    name: str
    join_code: str
    teacher_id: uuid.UUID
    member_count: int = 0
    assignment_count: int = 0
    created_at: datetime


class ClassroomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class JoinRequest(BaseModel):
    join_code: str = Field(min_length=6, max_length=8)


class AssignmentOut(BaseModel):
    assignment_id: uuid.UUID
    classroom_id: uuid.UUID
    classroom_name: str
    title: str
    skill_id: str
    skill_name_ar: str
    target_questions: int
    due_at: datetime | None
    created_at: datetime


class AssignmentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    skill_id: str = Field(min_length=1, max_length=80)
    target_questions: int = Field(default=10, ge=1, le=200)
    due_at: datetime | None = None
