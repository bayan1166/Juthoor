import uuid

from pydantic import BaseModel


class QuestionOut(BaseModel):
    question: str
    correct_answer: str
    distractors: list[dict]
    hint: str
    explanation: str
    skill: str
    difficulty: int
    pattern: str
    source: str
    remedial: str | None = None
    banner: str = ""
    guided: bool = False


class AnswerRequest(BaseModel):
    skill_id: str
    difficulty: int
    pattern: str
    selected_answer: str
    correct_answer: str
    is_remedial: bool = False


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
    skills: list[SkillStatusOut]
