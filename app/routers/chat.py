import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_student_access
from app.models.chat import ChatMessage, ChatRole, ChatSession
from app.models.org import User
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, ChatStartRequest, ChatStartResponse
from app.services import engine_bridge
from app.services.rag.socratic import generate_turn

router = APIRouter(prefix="/students/{student_id}/chat", tags=["chat"])


@router.post("/start", response_model=ChatStartResponse)
def start_chat(student_id: uuid.UUID, payload: ChatStartRequest, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    session = ChatSession(student_id=student_id, skill_context=payload.skill_context)
    db.add(session)
    db.flush()
    opening = "أهلاً! خبريني وين وصلت بهالمسألة، ووين حسيتي إنك تعلّقتي؟"
    db.add(ChatMessage(session_id=session.id, role=ChatRole.tutor, content=opening))
    db.commit()
    return ChatStartResponse(session_id=session.id, opening_message=opening)


@router.post("/message", response_model=ChatMessageResponse)
def send_message(student_id: uuid.UUID, payload: ChatMessageRequest, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    session = db.get(ChatSession, payload.session_id)
    if session is None or session.student_id != student_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session_not_found")

    history_rows = db.scalars(
        select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at)
    ).all()
    history = [{"role": r.role.value, "content": r.content} for r in history_rows]

    db.add(ChatMessage(session_id=session.id, role=ChatRole.student, content=payload.message))

    turn = generate_turn(session.skill_context, history, payload.message)

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
        breadcrumb=breadcrumb,
    )
