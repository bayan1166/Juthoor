"""Child-safety moderation of community reports.

Reports are filed by learners from the community screen (``POST /community/report``). They are reviewed by
Juthoor's internal moderation team (``platform_admin`` accounts, which cannot be self-registered and have no
screen in the product). There is no teacher or school reviewer: Juthoor is B2C.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models.community import DirectMessage
from app.models.org import User, UserRole
from app.models.safety import UserReport
from app.schemas.common import z
from app.schemas.community import ReportResolve

router = APIRouter(prefix="/moderation", tags=["moderation"])

moderator = require_roles(UserRole.platform_admin)


def _report_dict(report: UserReport, users: dict) -> dict:
    def who(uid):
        u = users.get(uid)
        return {"user_id": str(uid), "full_name": u.full_name if u else "", "handle": u.handle if u else None}
    return {
        "report_id": str(report.id), "reason": report.reason, "details": report.details, "status": report.status,
        "created_at": z(report.created_at), "reporter": who(report.reporter_id), "reported": who(report.reported_user_id),
        "has_message": report.message_id is not None, "resolution_note": report.resolution_note,
        "resolved_at": z(report.resolved_at),
    }


def _people(db: Session, ids) -> dict:
    ids = set(ids)
    return {u.id: u for u in db.scalars(select(User).where(User.id.in_(ids)))} if ids else {}


def _report(db: Session, report_id: uuid.UUID) -> UserReport:
    report = db.get(UserReport, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "report_not_found")
    return report


@router.get("/reports")
def reports(status_filter: str = "open", db: Session = Depends(get_db), user: User = Depends(moderator)):
    query = select(UserReport)
    if status_filter in ("open", "resolved", "dismissed"):
        query = query.where(UserReport.status == status_filter)
    rows = list(db.scalars(query.order_by(UserReport.created_at.desc()).limit(100)))
    users = _people(db, [r.reporter_id for r in rows] + [r.reported_user_id for r in rows])
    return [_report_dict(r, users) for r in rows]


@router.get("/reports/{report_id}")
def report_thread(report_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(moderator)):
    report = _report(db, report_id)
    a, b = report.reporter_id, report.reported_user_id
    thread = db.scalars(
        select(DirectMessage)
        .where(or_(and_(DirectMessage.sender_id == a, DirectMessage.recipient_id == b),
                   and_(DirectMessage.sender_id == b, DirectMessage.recipient_id == a)))
        .order_by(DirectMessage.created_at.desc()).limit(30)
    ).all()
    users = _people(db, [a, b])
    return {
        **_report_dict(report, users),
        "thread": [
            {"message_id": str(m.id), "sender_id": str(m.sender_id), "sender_name": users[m.sender_id].full_name,
             "body": m.body, "created_at": z(m.created_at), "flagged": m.id == report.message_id}
            for m in reversed(thread)
        ],
    }


@router.post("/reports/{report_id}/resolve")
def resolve_report(report_id: uuid.UUID, payload: ReportResolve, db: Session = Depends(get_db),
                   user: User = Depends(moderator)):
    report = _report(db, report_id)
    report.status = payload.action
    report.resolution_note = payload.note.strip()
    report.resolved_by = user.id
    report.resolved_at = datetime.utcnow()
    db.commit()
    return _report_dict(report, _people(db, [report.reporter_id, report.reported_user_id]))
