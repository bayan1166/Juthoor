"""Community: search users, send/accept/reject friend requests, direct-message a friend."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.community import DirectMessage, Friendship, FriendshipStatus
from app.models.org import User
from app.schemas.community import FriendshipOut, MessageIn, MessageOut, PublicUser, SearchResult

router = APIRouter(prefix="/community", tags=["community"])


def _public(u: User) -> PublicUser:
    return PublicUser(user_id=u.id, handle=u.handle, full_name=u.full_name or "",
                      email=u.email, role=u.role.value)


def _find_friendship(db: Session, a: uuid.UUID, b: uuid.UUID) -> Friendship | None:
    return db.scalar(select(Friendship).where(
        or_(and_(Friendship.requester_id == a, Friendship.addressee_id == b),
            and_(Friendship.requester_id == b, Friendship.addressee_id == a))))


@router.get("/search", response_model=list[SearchResult])
def search_users(q: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Find users by exact email or partial name. Excludes the caller. Limited to 20 results."""
    q = (q or "").strip()
    if len(q) < 2:
        return []
    like = f"%{q}%"
    rows = db.scalars(select(User).where(
        User.id != user.id, User.is_active.is_(True),
        or_(User.email == q.lower(), User.full_name.ilike(like))
    ).limit(20)).all()
    out = []
    for row in rows:
        fs = _find_friendship(db, user.id, row.id)
        if fs is None:
            label = None
        elif fs.status == FriendshipStatus.accepted:
            label = "accepted"
        elif fs.status == FriendshipStatus.blocked:
            label = "blocked"
        else:
            label = "pending_outgoing" if fs.requester_id == user.id else "pending_incoming"
        out.append(SearchResult(**_public(row).model_dump(), friendship_status=label))
    return out


@router.post("/request/{other_id}", response_model=FriendshipOut)
def send_request(other_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if other_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_friend_self")
    target = db.get(User, other_id)
    if target is None or not target.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    existing = _find_friendship(db, user.id, other_id)
    if existing:
        # If the OTHER user had already asked us, accept instead of creating a duplicate.
        if existing.status == FriendshipStatus.pending and existing.addressee_id == user.id:
            existing.status = FriendshipStatus.accepted
            db.commit()
            return _friendship_out(user.id, existing, target)
        raise HTTPException(status.HTTP_409_CONFLICT, "friendship_exists")
    fs = Friendship(requester_id=user.id, addressee_id=other_id, status=FriendshipStatus.pending)
    db.add(fs); db.commit(); db.refresh(fs)
    return _friendship_out(user.id, fs, target)


@router.post("/accept/{friendship_id}", response_model=FriendshipOut)
def accept(friendship_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fs = _own(db, friendship_id, user, incoming_only=True)
    fs.status = FriendshipStatus.accepted
    db.commit()
    return _friendship_out(user.id, fs, db.get(User, fs.requester_id))


@router.post("/reject/{friendship_id}")
def reject(friendship_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fs = _own(db, friendship_id, user, incoming_only=True)
    db.delete(fs); db.commit()
    return {"status": "rejected"}


@router.delete("/friend/{friendship_id}")
def remove_friend(friendship_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fs = _own(db, friendship_id, user)
    db.delete(fs); db.commit()
    return {"status": "removed"}


@router.get("/friends", response_model=list[FriendshipOut])
def list_friends(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(Friendship).where(
        or_(Friendship.requester_id == user.id, Friendship.addressee_id == user.id),
        Friendship.status == FriendshipStatus.accepted,
    ).order_by(Friendship.created_at.desc())).all()
    return [_friendship_out(user.id, r, db.get(User, r.addressee_id if r.requester_id == user.id else r.requester_id)) for r in rows]


@router.get("/requests", response_model=list[FriendshipOut])
def incoming_requests(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(Friendship).where(
        Friendship.addressee_id == user.id, Friendship.status == FriendshipStatus.pending
    ).order_by(Friendship.created_at.desc())).all()
    return [_friendship_out(user.id, r, db.get(User, r.requester_id)) for r in rows]


@router.get("/messages/{other_id}", response_model=list[MessageOut])
def thread(other_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_friends(db, user.id, other_id)
    rows = db.scalars(select(DirectMessage).where(
        or_(and_(DirectMessage.sender_id == user.id, DirectMessage.recipient_id == other_id),
            and_(DirectMessage.sender_id == other_id, DirectMessage.recipient_id == user.id))
    ).order_by(DirectMessage.created_at.desc()).limit(50)).all()
    rows = list(reversed(rows))
    return [MessageOut(message_id=r.id, sender_id=r.sender_id, recipient_id=r.recipient_id, body=r.body, created_at=r.created_at) for r in rows]


@router.post("/messages/{other_id}", response_model=MessageOut)
def send_message(other_id: uuid.UUID, payload: MessageIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_friends(db, user.id, other_id)
    msg = DirectMessage(sender_id=user.id, recipient_id=other_id, body=payload.body.strip())
    db.add(msg); db.commit(); db.refresh(msg)
    return MessageOut(message_id=msg.id, sender_id=msg.sender_id, recipient_id=msg.recipient_id, body=msg.body, created_at=msg.created_at)


# ----------------------------------------------------------------- helpers
def _own(db: Session, friendship_id: uuid.UUID, user: User, incoming_only: bool = False) -> Friendship:
    fs = db.get(Friendship, friendship_id)
    if fs is None or (user.id not in (fs.requester_id, fs.addressee_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "friendship_not_found")
    if incoming_only and fs.addressee_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not_your_incoming_request")
    return fs


def _require_friends(db: Session, a: uuid.UUID, b: uuid.UUID) -> None:
    fs = _find_friendship(db, a, b)
    if fs is None or fs.status != FriendshipStatus.accepted:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not_friends")


def _friendship_out(me: uuid.UUID, fs: Friendship, other: User) -> FriendshipOut:
    return FriendshipOut(friendship_id=fs.id, friend=_public(other), status=fs.status.value,
                         is_incoming=(fs.addressee_id == me and fs.status == FriendshipStatus.pending),
                         created_at=fs.created_at)
