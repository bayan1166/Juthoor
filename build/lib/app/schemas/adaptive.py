import uuid
from datetime import datetime  # noqa: F401

from app.schemas.common import OptUtcDateTime, UtcDateTime  # noqa: F401

from pydantic import BaseModel, Field


class QuestionOut(BaseModel):
    question: str
    hint: str
    skill: str
    difficulty: int
    pattern: str
    source: str
    remedial: str | None = None
    banner: str = ""
    guided: bool = False
    type: str = "mcq"
    options: list[str] = []
    skill_name: str = ""


class AnswerRequest(BaseModel):
    selected_answer: str = Field(min_length=1, max_length=200)
    is_remedial: bool = False
    # Optional idempotency key chosen by the client for ONE answer attempt; resend the same value on a
    # retry and the original response is returned instead of grading the answer a second time.
    request_id: str | None = Field(default=None, min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$")


    skill_id: str | None = None
    difficulty: int | None = None
    pattern: str | None = None
    correct_answer: str | None = None


class DecisionOut(BaseModel):
    action: str
    next_skill: str
    next_difficulty: int
    reason: str
    breadcrumb: str = ""
    gap_skill: str | None = None
    round_over: bool = False
    coins_awarded: int = 0
    gems_awarded: int = 0
    is_correct: bool = False
    correct_answer: str = ""
    misconception: str = ""
    explanation: str = ""
    new_gaps: list[str] = []
    remedial: str | None = None
    next_stage: str | None = None
    mistake_card: dict | None = None
    gap_locked: bool = False
    remaining_questions: int | None = None
    diagnosis: dict | None = None
    evidence_status: dict | None = None
    workflow: dict | None = None
    idempotent_replay: bool = False


class SkillStatusOut(BaseModel):
    skill_id: str
    name_ar: str
    status: str
    p_mastery: float
    attempts: int
    correct: int


class StudentStateOut(BaseModel):
    student_id: uuid.UUID
    current_skill: str
    difficulty: int
    total_answered: int
    tree_health: float
    round_answered: int = 0
    round_over: bool = False
    in_remediation: bool = False
    skills: list[SkillStatusOut]
    workflow: dict | None = None


class DrillDownOut(BaseModel):
    from_skill: str
    from_name_ar: str
    to_skill: str
    to_name_ar: str
    direction: str
    triggered_by: str
    depth: int
    created_at: UtcDateTime
