import uuid

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.esports import ChallengeAttempt, ChallengeStatus, EsportsChallenge
from app.models.org import User

ACCURACY_WEIGHT = 0.7
SPEED_WEIGHT = 0.3


def compute_score(correct_count: int, total_count: int, duration_seconds: float, time_limit_seconds: int) -> float:
    if total_count == 0:
        return 0.0
    accuracy = correct_count / total_count
    speed = max(0.0, 1.0 - (duration_seconds / max(time_limit_seconds, 1)))
    return round((accuracy * ACCURACY_WEIGHT + speed * SPEED_WEIGHT) * 100, 2)


def submit_attempt(db: Session, student_id: uuid.UUID, challenge_id: uuid.UUID,
                    correct_count: int, total_count: int, duration_seconds: float) -> dict:
    challenge = db.get(EsportsChallenge, challenge_id)
    if challenge is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "challenge_not_found")
    if challenge.status != ChallengeStatus.live:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "challenge_not_live")
    if total_count > challenge.question_count:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "total_count_exceeds_challenge_size")

    score = compute_score(correct_count, total_count, duration_seconds, challenge.time_limit_seconds)
    db.add(ChallengeAttempt(
        challenge_id=challenge_id, student_id=student_id, correct_count=correct_count,
        total_count=total_count, duration_seconds=duration_seconds, score=score,
    ))
    db.commit()

    higher_count = len(db.scalars(select(ChallengeAttempt.id).where(
        ChallengeAttempt.challenge_id == challenge_id, ChallengeAttempt.score > score,
    )).all())
    return {"score": score, "rank_in_challenge": higher_count + 1}


def leaderboard(db: Session, challenge_id: uuid.UUID, limit: int = 50) -> list[dict]:
    rows = db.execute(
        select(ChallengeAttempt, User)
        .join(User, User.id == ChallengeAttempt.student_id)
        .where(ChallengeAttempt.challenge_id == challenge_id)
        .order_by(desc(ChallengeAttempt.score))
        .limit(limit)
    ).all()
    return [{
        "rank": i + 1,
        "student_id": attempt.student_id,
        "display_name": user.full_name or "Student",
        "score": attempt.score,
        "correct_count": attempt.correct_count,
        "duration_seconds": attempt.duration_seconds,
    } for i, (attempt, user) in enumerate(rows)]
