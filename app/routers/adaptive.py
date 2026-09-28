import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_student_access
from app.models.org import User
from app.schemas.adaptive import AnswerRequest, DecisionOut, QuestionOut, StudentStateOut
from app.services import engine_bridge

router = APIRouter(prefix="/students/{student_id}/adaptive", tags=["adaptive"])


@router.get("/question", response_model=QuestionOut)
def get_next_question(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    return engine_bridge.next_question(db, student_id)


@router.post("/answer", response_model=DecisionOut)
def submit_answer(student_id: uuid.UUID, payload: AnswerRequest, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    return engine_bridge.submit_answer(
        db, student_id, payload.skill_id, payload.difficulty, payload.pattern,
        payload.selected_answer, payload.correct_answer, payload.is_remedial,
    )


@router.get("/state", response_model=StudentStateOut)
def get_state(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    return engine_bridge.state_overview(db, student_id)
