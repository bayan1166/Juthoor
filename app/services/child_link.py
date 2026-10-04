"""Child ID: the code a parent/guardian must give to create an account.

A parent account is created only together with the link to an existing learner, so the database never holds a
parent without a child. The Child ID is shown to the learner in their own account menu and has two parts:

    <handle>-<tag>      e.g. 4821-K7Q2M9XD

The handle is the learner's public number; the tag is an HMAC of the learner's id under the server secret
(``JWT_SECRET``), so it cannot be guessed from public data (handles and user ids are visible in the community).
Knowing a learner's handle or id is therefore not enough to attach an account to them: the family has to get
the code from the learner. A learner who already has a parent/guardian cannot be claimed again.
Rotating ``JWT_SECRET`` changes every Child ID (old codes stop working; already linked accounts are unaffected).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.org import User, UserRole

TAG_LENGTH = 8
_DOMAIN = b"juthoor-child-id:"
_SHAPE = re.compile(r"^(\d{4,12})-([A-Z2-7]{%d})$" % TAG_LENGTH)


def _tag(user: User) -> str:
    mac = hmac.new(settings.jwt_secret.encode("utf-8"), _DOMAIN + user.id.bytes, hashlib.sha256).digest()
    return base64.b32encode(mac).decode("ascii")[:TAG_LENGTH]


def child_id_for(user: User) -> str | None:
    """The learner's Child ID, or None for any other account."""
    if user.role != UserRole.student or not user.handle:
        return None
    return f"{user.handle}-{_tag(user)}"


def normalise(raw: str | None) -> str:
    return re.sub(r"\s+", "", raw or "").lstrip("#").upper()


def resolve(db: Session, raw: str | None, lock: bool = False) -> User | None:
    """The active learner this Child ID belongs to, or None (unknown, malformed, wrong tag, not a learner).

    ``lock=True`` takes the row lock on the learner so two simultaneous parent sign-ups cannot both claim them.
    """
    match = _SHAPE.match(normalise(raw))
    if not match:
        return None
    handle, tag = match.groups()
    query = select(User).where(User.handle == handle)
    if lock:
        query = query.with_for_update()
    child = db.scalar(query)
    if child is None or child.role != UserRole.student or not child.is_active:
        return None
    if not hmac.compare_digest(_tag(child), tag):
        return None
    return child
