import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_student_access
from app.models.org import User
from app.schemas.adaptive import AnswerRequest, DecisionOut, DrillDownOut, QuestionOut, StudentStateOut
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
    try:
        return engine_bridge.submit_answer(db, student_id, payload.selected_answer, payload.is_remedial)
    except engine_bridge.EngineError as exc:
        raise HTTPException(exc.status_code, exc.code)


@router.get("/state", response_model=StudentStateOut)
def get_state(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    return engine_bridge.state_overview(db, student_id)


@router.get("/bootstrap")
def bootstrap(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """State + wallet + drilldowns + avatar + incoming-friend-request count, in ONE call.
    Cuts every page-load from 4 round-trips to 1. The response is a plain dict (no schema)
    so we don't pay pydantic-serialization cost on the largest hot-path payload."""
    from app.models.community import Friendship, FriendshipStatus
    from app.models.economy import AvatarConfig, Wallet
    from sqlalchemy import func, select
    require_student_access(student_id, user, db)
    wallet = db.get(Wallet, student_id)
    avatar = db.get(AvatarConfig, student_id)
    incoming = db.scalar(select(func.count(Friendship.id)).where(
        Friendship.addressee_id == user.id, Friendship.status == FriendshipStatus.pending)) or 0
    return {
        "state": engine_bridge.state_overview(db, student_id),
        "wallet": {"student_id": str(student_id),
                   "coins": wallet.coins if wallet else 0,
                   "gems": wallet.gems if wallet else 0,
                   "lifetime_coins_earned": wallet.lifetime_coins_earned if wallet else 0,
                   "lifetime_gems_earned": wallet.lifetime_gems_earned if wallet else 0},
        "avatar": {"gender": avatar.gender, "skin": avatar.skin, "clothing": avatar.clothing,
                   "top": avatar.top, "neck": avatar.neck, "accessories": avatar.accessories,
                   "hair": avatar.hair, "hair_color": avatar.hair_color} if avatar else None,
        "drilldowns": engine_bridge.drilldown_history(db, student_id),
        "incoming_friend_requests": int(incoming),
    }


@router.post("/round", response_model=StudentStateOut)
def new_round(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Start a fresh practice round (keeps mastery, clears last round's detours)."""
    require_student_access(student_id, user, db)
    return engine_bridge.start_new_round(db, student_id)


@router.get("/drilldowns", response_model=list[DrillDownOut])
def drilldowns(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """The backtracking path: every move to a prerequisite (engine, practice or tutor), oldest first."""
    require_student_access(student_id, user, db)
    return engine_bridge.drilldown_history(db, student_id)
