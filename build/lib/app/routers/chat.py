import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_self
from app.engine import knowledge_graph as kg
from app.models.chat import ChatMessage, ChatRole, ChatSession
from app.models.org import User
from app.schemas.chat import (
    ChatHistoryItem, ChatMessageRequest, ChatMessageResponse, ChatStartRequest, ChatStartResponse,
)
from app.services.rag import guardrail
from app.services import engine_bridge, plans
from app.services.rag.socratic import generate_turn

router = APIRouter(prefix="/students/{student_id}/chat", tags=["chat"])

OPENING = "أهلاً بك. اسألني عن أي فكرة في الدرس، أو اكتب لي مسألة لأحلّها معك خطوة بخطوة."


def _own_session(db: Session, student_id: uuid.UUID, session_id: uuid.UUID) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if session is None or session.student_id != student_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session_not_found")
    return session


@router.post("/start", response_model=ChatStartResponse)
def start_chat(student_id: uuid.UUID, payload: ChatStartRequest, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    require_self(student_id, user)
    if payload.skill_context not in kg.SKILLS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown_skill_context")
    session = ChatSession(student_id=student_id, skill_context=payload.skill_context)
    db.add(session)
    db.flush()
    db.add(ChatMessage(session_id=session.id, role=ChatRole.tutor, content=OPENING))
    db.commit()
    return ChatStartResponse(session_id=session.id, opening_message=OPENING)


@router.get("/sessions/{session_id}/messages", response_model=list[ChatHistoryItem])
def session_messages(student_id: uuid.UUID, session_id: uuid.UUID, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    require_self(student_id, user)
    session = _own_session(db, student_id, session_id)
    rows = db.scalars(
        select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at)
    ).all()
    return [ChatHistoryItem(role=r.role.value, content=r.content, created_at=r.created_at) for r in rows]


@router.post("/message", response_model=ChatMessageResponse)
def send_message(student_id: uuid.UUID, payload: ChatMessageRequest, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    require_self(student_id, user)
    text = payload.message.strip()
    if not text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "empty_message")
    session = _own_session(db, student_id, payload.session_id)
    if guardrail.is_off_topic(text):
        return ChatMessageResponse(reply=guardrail.FALLBACK, remaining_today=plans.snapshot(db, user)["remaining"]["tutor"], source="guardrail")
    plans.require_quota(db, user, "tutor")

    rows = db.scalars(
        select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at)
    ).all()
    history = [{"role": r.role.value, "content": r.content} for r in rows]

    db.add(ChatMessage(session_id=session.id, role=ChatRole.student, content=text))
    turn = generate_turn(session.skill_context, history, text)

    drill_triggered = False
    next_skill = next_difficulty = None
    breadcrumb = ""
    if turn.gap_detected and turn.gap_skill:
        plan = engine_bridge.trigger_manual_drill_down(db, student_id, turn.gap_skill, turn.misconception)
        if plan is not None:
            drill_triggered = True
            next_skill = plan["skill"]
            next_difficulty = plan["difficulty"]
            breadcrumb = plan.get("breadcrumb", "")

    db.add(ChatMessage(
        session_id=session.id, role=ChatRole.tutor, content=turn.reply,
        retrieved_chunk_ids=turn.retrieved_ids, gap_detected=turn.gap_detected,
        gap_skill=turn.gap_skill, misconception=turn.misconception,
    ))
    db.commit()

    return ChatMessageResponse(
        reply=turn.reply, gap_detected=turn.gap_detected, gap_skill=turn.gap_skill or None,
        drill_down_triggered=drill_triggered, next_skill=next_skill, next_difficulty=next_difficulty,
        breadcrumb=breadcrumb, remaining_today=plans.snapshot(db, user)["remaining"]["tutor"],
        source=turn.source,
    )
