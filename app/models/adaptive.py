import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MasteryStatus(str, enum.Enum):
    untouched = "untouched"
    learning = "learning"
    mastered = "mastered"
    inferred = "inferred"
    gap = "gap"
    parked = "parked"


class StudentAdaptiveState(Base):
    __tablename__ = "student_adaptive_states"

    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    current_skill: Mapped[str] = mapped_column(String(80), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    consec_wrong: Mapped[int] = mapped_column(Integer, default=0)
    total_answered: Mapped[int] = mapped_column(Integer, default=0)
    round_answered: Mapped[int] = mapped_column(Integer, default=0)
    return_stack: Mapped[list] = mapped_column(JSON, default=list)
    remediation_plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)


    pending_question: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    pending_banner: Mapped[str | None] = mapped_column(Text, nullable=True)

    recent_questions: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SkillMastery(Base):
    __tablename__ = "skill_mastery"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    skill_id: Mapped[str] = mapped_column(String(80), index=True)
    p_mastery: Mapped[float] = mapped_column(Float, default=0.3)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[MasteryStatus] = mapped_column(Enum(MasteryStatus), default=MasteryStatus.untouched)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AttemptLog(Base):
    __tablename__ = "attempt_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    skill_id: Mapped[str] = mapped_column(String(80), index=True)
    pattern: Mapped[str] = mapped_column(String(40), default="")
    difficulty: Mapped[int] = mapped_column(Integer)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    selected_answer: Mapped[str] = mapped_column(Text, default="")
    correct_answer: Mapped[str] = mapped_column(Text, default="")
    misconception: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(20), default="offline")
    remedial_stage: Mapped[str] = mapped_column(String(20), default="")
    action: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class DrillDownEvent(Base):
    __tablename__ = "drill_down_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    from_skill: Mapped[str] = mapped_column(String(80))
    from_pattern: Mapped[str] = mapped_column(String(40), default="")
    to_skill: Mapped[str] = mapped_column(String(80))
    to_pattern: Mapped[str] = mapped_column(String(40), default="")
    depth: Mapped[int] = mapped_column(Integer, default=1)
    direction: Mapped[str] = mapped_column(String(10), default="descend")
    triggered_by: Mapped[str] = mapped_column(String(20), default="engine")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class DiagnosisEvent(Base):
    __tablename__ = "diagnosis_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    origin_skill: Mapped[str] = mapped_column(String(80))
    root_skill: Mapped[str] = mapped_column(String(80))
    confidence: Mapped[str] = mapped_column(String(20), default="")
    confidence_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    p_gap: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    path: Mapped[list] = mapped_column(JSON, default=list)
    teacher_verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
