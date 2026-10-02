import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def _naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class ClassroomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class JoinRequest(BaseModel):
    join_code: str = Field(min_length=6, max_length=8)


class AssignmentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=4000)
    skill_id: str | None = None
    target_questions: int = Field(default=0, ge=0, le=200)
    max_score: int = Field(default=100, ge=1, le=1000)
    due_at: datetime | None = None

    @field_validator("due_at")
    @classmethod
    def _utc(cls, value):
        return _naive_utc(value)


class GradeIn(BaseModel):
    score: int = Field(ge=0, le=1000)
    feedback: str = Field(default="", max_length=2000)


class QuizQuestionIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(min_length=2, max_length=6)
    correct_index: int = Field(ge=0)
    points: int = Field(default=100, ge=10, le=1000)

    @field_validator("options")
    @classmethod
    def _options(cls, value):
        cleaned = [o.strip() for o in value]
        if any(not o or len(o) > 200 for o in cleaned):
            raise ValueError("options must be 1-200 characters")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("options must be unique")
        return cleaned

    @model_validator(mode="after")
    def _index(self):
        if self.correct_index >= len(self.options):
            raise ValueError("correct_index out of range")
        return self


class QuizCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=2000)
    mode: Literal["quiz", "race"] = "quiz"
    time_limit_seconds: int = Field(default=0, ge=0, le=7200)
    questions: list[QuizQuestionIn] = Field(min_length=1, max_length=50)


class QuizGenerate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    skill_id: str
    count: int = Field(default=8, ge=3, le=20)
    mode: Literal["quiz", "race"] = "quiz"
    time_limit_seconds: int = Field(default=0, ge=0, le=7200)


class QuizPatch(BaseModel):
    is_open: bool


class QuizSubmit(BaseModel):
    answers: dict[str, int] = Field(default_factory=dict)


class RemediationCreate(BaseModel):
    skill_id: str
    due_days: int = Field(default=5, ge=1, le=30)
    student_ids: list[uuid.UUID] | None = None


class ReportResolve(BaseModel):
    action: Literal["resolved", "dismissed"]
    note: str = Field(default="", max_length=1000)
