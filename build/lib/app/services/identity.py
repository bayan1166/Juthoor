import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.org import User


def unique_handle(db: Session, length: int = 4, max_tries: int = 12) -> str:
    for _ in range(max_tries):
        low = 10 ** (length - 1)
        candidate = str(secrets.randbelow(9 * low) + low)
        if db.scalar(select(User.id).where(User.handle == candidate)) is None:
            return candidate
        length += 1
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "handle_generation_failed")
