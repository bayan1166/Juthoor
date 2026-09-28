import uuid
from datetime import datetime

from pydantic import BaseModel


class ChallengeOut(BaseModel):
    id: uuid.UUID
    skill_id: str
    difficulty: int
    question_count: int
    time_limit_seconds: int
    status: str


class ChallengeSubmitRequest(BaseModel):
    challenge_id: uuid.UUID
    correct_count: int
    total_count: int
    duration_seconds: float


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
    generated_at: datetime
