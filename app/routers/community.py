import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.community import DirectMessage, Friendship, FriendshipStatus
from app.models.org import User, UserRole
from app.models.safety import UserReport
from app.ratelimit import throttle
from app.schemas.community import (
    ConversationOut, FriendshipOut, MessageIn, MessageOut, PublicUser, ReportIn, SearchResult, SummaryOut,
)
from app.services import avatar_render, chat_safety, plans

router = APIRouter(prefix="/community", tags=["community"])


def _public(user: User, svgs: dict) -> PublicUser:
    return PublicUser(
        user_id=user.id, handle=user.handle, full_name=user.full_name or "", role=user.role.value,
        avatar_svg=svgs.get(user.id),
    )


def _pair(a: uuid.UUID, b: uuid.UUID):
    return or_(
        and_(Friendship.requester_id == a, Friendship.addressee_id == b),
        and_(Friendship.requester_id == b, Friendship.addressee_id == a),
    )


def _find(db: Session, a: uuid.UUID, b: uuid.UUID) -> Friendship | None:
    return db.scalar(select(Friendship).where(_pair(a, b)))


def _thread(a: uuid.UUID, b: uuid.UUID):
    return or_(
        and_(DirectMessage.sender_id == a, DirectMessage.recipient_id == b),
        and_(DirectMessage.sender_id == b, DirectMessage.recipient_id == a),
    )


def _message_out(m: DirectMessage) -> MessageOut:
    return MessageOut(
        message_id=m.id, sender_id=m.sender_id, recipient_id=m.recipient_id, body=m.body,
        created_at=m.created_at, read_at=m.read_at,
    )


def _friendship_out(me: uuid.UUID, fs: Friendship, other: User, svgs: dict) -> FriendshipOut:
    return FriendshipOut(
        friendship_id=fs.id, friend=_public(other, svgs), status=fs.status.value,
        is_incoming=(fs.addressee_id == me and fs.status == FriendshipStatus.pending), created_at=fs.created_at,
    )


def _own(db: Session, friendship_id: uuid.UUID, user: User, incoming_only: bool = False) -> Friendship:
    fs = db.get(Friendship, friendship_id)
    if fs is None or user.id not in (fs.requester_id, fs.addressee_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "friendship_not_found")
    if incoming_only and fs.addressee_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not_your_incoming_request")
    return fs


def _require_friends(db: Session, a: uuid.UUID, b: uuid.UUID) -> None:
    fs = _find(db, a, b)
    if fs is None or fs.status != FriendshipStatus.accepted:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not_friends")


def _accepted(db: Session, me: uuid.UUID) -> list[Friendship]:
    return list(db.scalars(
        select(Friendship)
        .where(or_(Friendship.requester_id == me, Friendship.addressee_id == me),
               Friendship.status == FriendshipStatus.accepted)
        .order_by(Friendship.created_at.desc())
        .limit(100)
    ))


def _other_id(me: uuid.UUID, fs: Friendship) -> uuid.UUID:
    return fs.addressee_id if fs.requester_id == me else fs.requester_id


def _users(db: Session, ids: list[uuid.UUID]) -> dict:
    if not ids:
        return {}
    return {u.id: u for u in db.scalars(select(User).where(User.id.in_(ids)))}


def _parse_after(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "").split("+")[0])
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "bad_after")


@router.get("/search", response_model=list[SearchResult])
def search_users(q: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    throttle("search", str(user.id), 40, 60)
    term = (q or "").strip().lstrip("#")
    if len(term) < 2:
        return []
    rows = db.scalars(
        select(User).where(User.id != user.id, User.is_active.is_(True),
                           or_(User.handle == term, User.email == term.lower())).limit(20)
    ).all()
    svgs = avatar_render.svgs_for(db, rows)
    out = []
    for row in rows:
        fs = _find(db, user.id, row.id)
        if fs is None:
            label = None
        elif fs.status == FriendshipStatus.accepted:
            label = "accepted"
        elif fs.status == FriendshipStatus.blocked:
            if fs.requester_id != user.id:
                continue
            label = "blocked"
        else:
            label = "pending_outgoing" if fs.requester_id == user.id else "pending_incoming"
        out.append(SearchResult(**_public(row, svgs).model_dump(), friendship_status=label))
    return out


@router.post("/request/{other_id}", response_model=FriendshipOut)
def send_request(other_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    throttle("friend-request", str(user.id), 20, 86400)
    if other_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_friend_self")
    target = db.get(User, other_id)
    if target is None or not target.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    existing = _find(db, user.id, other_id)
    if existing is not None and existing.status == FriendshipStatus.blocked:
        if existing.requester_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
        raise HTTPException(status.HTTP_409_CONFLICT, "unblock_first")
    if existing is not None and existing.status != FriendshipStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "friendship_exists")
    if existing is not None and existing.addressee_id != user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "friendship_exists")
    if plans.friend_cap_reached(db, user):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "friend_limit_reached")
    svgs = avatar_render.svgs_for(db, [target])
    if existing is not None:
        existing.status = FriendshipStatus.accepted
        db.commit()
        return _friendship_out(user.id, existing, target, svgs)
    fs = Friendship(requester_id=user.id, addressee_id=other_id, status=FriendshipStatus.pending)
    db.add(fs)
    db.commit()
    db.refresh(fs)
    return _friendship_out(user.id, fs, target, svgs)


@router.post("/accept/{friendship_id}", response_model=FriendshipOut)
def accept(friendship_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fs = _own(db, friendship_id, user, incoming_only=True)
    if fs.status != FriendshipStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "friendship_exists")
    if plans.friend_cap_reached(db, user):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "friend_limit_reached")
    fs.status = FriendshipStatus.accepted
    db.commit()
    other = db.get(User, fs.requester_id)
    return _friendship_out(user.id, fs, other, avatar_render.svgs_for(db, [other]))


@router.post("/reject/{friendship_id}")
def reject(friendship_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fs = _own(db, friendship_id, user, incoming_only=True)
    db.delete(fs)
    db.commit()
    return {"status": "rejected"}


@router.delete("/friend/{friendship_id}")
def remove_friend(friendship_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fs = _own(db, friendship_id, user)
    db.delete(fs)
    db.commit()
    return {"status": "removed"}


@router.get("/friends", response_model=list[FriendshipOut])
def list_friends(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = _accepted(db, user.id)
    users = _users(db, [_other_id(user.id, r) for r in rows])
    svgs = avatar_render.svgs_for(db, list(users.values()))
    return [_friendship_out(user.id, r, users[_other_id(user.id, r)], svgs)
            for r in rows if _other_id(user.id, r) in users]


@router.get("/requests", response_model=list[FriendshipOut])
def incoming_requests(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(
        select(Friendship)
        .where(Friendship.addressee_id == user.id, Friendship.status == FriendshipStatus.pending)
        .order_by(Friendship.created_at.desc())
    ).all()
    users = _users(db, [r.requester_id for r in rows])
    svgs = avatar_render.svgs_for(db, list(users.values()))
    return [_friendship_out(user.id, r, users[r.requester_id], svgs) for r in rows if r.requester_id in users]


@router.get("/conversations", response_model=list[ConversationOut])
def conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = _accepted(db, user.id)
    users = _users(db, [_other_id(user.id, r) for r in rows])
    svgs = avatar_render.svgs_for(db, list(users.values()))
    out = []
    for fs in rows:
        other = users.get(_other_id(user.id, fs))
        if other is None:
            continue
        last = db.scalar(select(DirectMessage).where(_thread(user.id, other.id))
                         .order_by(DirectMessage.created_at.desc()).limit(1))
        unread = db.scalar(select(func.count(DirectMessage.id)).where(
            DirectMessage.sender_id == other.id, DirectMessage.recipient_id == user.id,
            DirectMessage.read_at.is_(None))) or 0
        out.append(ConversationOut(
            friendship_id=fs.id, friend=_public(other, svgs),
            last_message=_message_out(last) if last else None, unread=int(unread),
        ))
    out.sort(key=lambda c: c.last_message.created_at if c.last_message else datetime.min, reverse=True)
    return out


@router.get("/summary", response_model=SummaryOut)
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    unread = db.scalar(select(func.count(DirectMessage.id)).where(
        DirectMessage.recipient_id == user.id, DirectMessage.read_at.is_(None))) or 0
    pending = db.scalar(select(func.count(Friendship.id)).where(
        Friendship.addressee_id == user.id, Friendship.status == FriendshipStatus.pending)) or 0
    return SummaryOut(unread_messages=int(unread), pending_requests=int(pending))


@router.get("/messages/{other_id}", response_model=list[MessageOut])
def thread(other_id: uuid.UUID, after: str | None = None, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    _require_friends(db, user.id, other_id)
    since = _parse_after(after)
    query = select(DirectMessage).where(_thread(user.id, other_id))
    if since is not None:
        rows = db.scalars(query.where(DirectMessage.created_at >= since).order_by(DirectMessage.created_at).limit(200)).all()
    else:
        rows = list(reversed(db.scalars(query.order_by(DirectMessage.created_at.desc()).limit(60)).all()))
    return [_message_out(m) for m in rows]


@router.post("/messages/{other_id}", response_model=MessageOut)
def send_message(other_id: uuid.UUID, payload: MessageIn, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    _require_friends(db, user.id, other_id)
    throttle("message", str(user.id), 60, 60)
    body = payload.body.strip()
    if not body:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "empty_message")
    other = db.get(User, other_id)
    if other is not None and user.role == UserRole.student and other.role == UserRole.student:
        reason = chat_safety.blocked_reason(body)
        if reason:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"message_not_allowed:{reason}")
    msg = DirectMessage(sender_id=user.id, recipient_id=other_id, body=body)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return _message_out(msg)


@router.post("/messages/{other_id}/read")
def mark_read(other_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_friends(db, user.id, other_id)
    now = datetime.utcnow()
    rows = db.scalars(select(DirectMessage).where(
        DirectMessage.sender_id == other_id, DirectMessage.recipient_id == user.id,
        DirectMessage.read_at.is_(None))).all()
    for m in rows:
        m.read_at = now
    db.commit()
    return {"marked": len(rows)}


def _apply_block(db: Session, blocker_id: uuid.UUID, other_id: uuid.UUID) -> None:
    fs = _find(db, blocker_id, other_id)
    if fs is None:
        db.add(Friendship(requester_id=blocker_id, addressee_id=other_id, status=FriendshipStatus.blocked))
        return
    fs.requester_id, fs.addressee_id = blocker_id, other_id
    fs.status = FriendshipStatus.blocked


@router.post("/block/{other_id}")
def block_user(other_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if other_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_block_self")
    if db.get(User, other_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    _apply_block(db, user.id, other_id)
    db.commit()
    return {"status": "blocked"}


@router.delete("/block/{other_id}")
def unblock_user(other_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fs = db.scalar(select(Friendship).where(
        Friendship.requester_id == user.id, Friendship.addressee_id == other_id,
        Friendship.status == FriendshipStatus.blocked))
    if fs is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_blocked")
    db.delete(fs)
    db.commit()
    return {"status": "unblocked"}


@router.get("/blocked", response_model=list[PublicUser])
def blocked_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(Friendship).where(
        Friendship.requester_id == user.id, Friendship.status == FriendshipStatus.blocked)).all()
    users = _users(db, [r.addressee_id for r in rows])
    svgs = avatar_render.svgs_for(db, list(users.values()))
    return [_public(u, svgs) for u in users.values()]


@router.post("/report")
def report_user(payload: ReportIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    throttle("report", str(user.id), 10, 3600)
    if payload.user_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_report_self")
    target = db.get(User, payload.user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    message_id = None
    if payload.message_id is not None:
        msg = db.get(DirectMessage, payload.message_id)
        if msg is None or msg.sender_id != target.id or msg.recipient_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "message_not_found")
        message_id = msg.id
        known = db.scalar(select(UserReport.id).where(
            UserReport.reporter_id == user.id, UserReport.message_id == message_id))
        if known is not None:
            return {"status": "received", "duplicate": True}
    db.add(UserReport(
        reporter_id=user.id, reported_user_id=target.id, message_id=message_id,
        reason=payload.reason, details=payload.details.strip()))
    if payload.also_block:
        _apply_block(db, user.id, target.id)
    db.commit()
    return {"status": "received", "duplicate": False}
