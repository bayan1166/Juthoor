import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_student_access
from app.models.esports import ChallengeStatus, EsportsChallenge, EsportsSeason
from app.models.org import User
from app.schemas.esports import ChallengeOut, ChallengeSubmitRequest, ChallengeSubmitResponse, LeaderboardOut
from app.services import esports_service

router = APIRouter(tags=["esports"])


@router.get("/esports/challenges/live", response_model=list[ChallengeOut])
def live_challenges(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(EsportsChallenge).where(EsportsChallenge.status == ChallengeStatus.live)).all()
    return rows


@router.get("/esports/challenges/{challenge_id}/leaderboard", response_model=LeaderboardOut)
def get_leaderboard(challenge_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    entries = esports_service.leaderboard(db, challenge_id)
    return LeaderboardOut(challenge_id=challenge_id, entries=entries, generated_at=datetime.utcnow())


@router.post("/students/{student_id}/esports/submit", response_model=ChallengeSubmitResponse)
def submit_challenge(student_id: uuid.UUID, payload: ChallengeSubmitRequest, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    result = esports_service.submit_attempt(
        db, student_id, payload.challenge_id, payload.correct_count, payload.total_count, payload.duration_seconds,
    )
    return result


@router.post("/esports/seasons/{season_id}/challenges", status_code=status.HTTP_201_CREATED)
def create_challenge(season_id: uuid.UUID, skill_id: str, difficulty: int = 2, question_count: int = 10,
                      time_limit_seconds: int = 120, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    if user.role.value not in ("org_admin", "platform_admin", "teacher"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient_role")
    season = db.get(EsportsSeason, season_id)
    if season is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "season_not_found")
    challenge = EsportsChallenge(
        season_id=season_id, skill_id=skill_id, difficulty=difficulty,
        question_count=question_count, time_limit_seconds=time_limit_seconds,
        status=ChallengeStatus.live,
    )
    db.add(challenge)
    db.commit()
    return {"id": challenge.id}
