import uuid
from datetime import datetime  # noqa: F401

from app.schemas.common import OptUtcDateTime, UtcDateTime  # noqa: F401

from pydantic import BaseModel


class StruggleAlert(BaseModel):
    skill_id: str
    skill_name_ar: str
    severity: str
    p_mastery: float
    consecutive_misses: int
    drill_down_depth_avg: float
    predicted_root_cause_skill: str | None
    recommended_action: str


class RemediationProgress(BaseModel):
    skill_id: str
    skill_name_ar: str
    drill_down_events: int
    resolved_events: int
    resolution_rate: float
    avg_minutes_to_resolve: float


class EngagementSummary(BaseModel):
    active_days_last_30: int
    avg_session_minutes: float | None = None
    questions_answered_last_7: int
    current_streak: int


class StudentInsightsOut(BaseModel):
    student_id: uuid.UUID
    generated_at: UtcDateTime
    tree_health: float
    struggle_alerts: list[StruggleAlert]
    remediation_progress: list[RemediationProgress]
    engagement: EngagementSummary
    gap_report_locked: bool = False


class RosterStudentOut(BaseModel):
    student_id: uuid.UUID
    full_name: str
    email: str
    grade_level: int
