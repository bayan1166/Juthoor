import uuid
from datetime import datetime  # noqa: F401

from app.schemas.common import OptUtcDateTime, UtcDateTime  # noqa: F401

from pydantic import BaseModel, Field, model_validator


class ChallengeOut(BaseModel):
    id: uuid.UUID
    skill_id: str
    difficulty: int
    question_count: int
    time_limit_seconds: int
    status: str


class ChallengeSubmitRequest(BaseModel):
    challenge_id: uuid.UUID
    correct_count: int = Field(ge=0)
    total_count: int = Field(ge=1)
    duration_seconds: float = Field(ge=0)

    @model_validator(mode="after")
    def _correct_not_above_total(self):
        if self.correct_count > self.total_count:
            raise ValueError("correct_count cannot exceed total_count")
        return self


class ChallengeSubmitResponse(BaseModel):
    score: float
    coins_awarded: int
    rank_in_challenge: int


class LeaderboardEntryOut(BaseModel):
    rank: int
    student_id: uuid.UUID
    display_name: str
    score: float
    correct_count: int
    duration_seconds: float


class LeaderboardOut(BaseModel):
    challenge_id: uuid.UUID
    entries: list[LeaderboardEntryOut]
    generated_at: UtcDateTime
