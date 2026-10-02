import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_self, require_student_access
from app.engine import knowledge_graph as kg
from app.models.adaptive import AttemptLog
from app.models.economy import AvatarConfig
from app.models.org import User
from app.schemas.adaptive import AnswerRequest, DecisionOut, DrillDownOut, QuestionOut, StudentStateOut
from app.services import avatar_render, economy_service, engine_bridge, plans, tree_service

router = APIRouter(prefix="/students/{student_id}/adaptive", tags=["adaptive"])

MASTERY_TARGET = 9


def _student(db: Session, student_id: uuid.UUID) -> User:
    student = db.get(User, student_id)
    if student is None:
        raise HTTPException(404, "user_not_found")
    return student


def _mask_workflow(workflow: dict | None) -> dict | None:
    if not workflow:
        return workflow
    hidden = {k: None for k in ("origin", "origin_name_ar", "root", "root_name_ar", "confidence")}
    return {**workflow, **hidden, "locked": workflow["stage"] not in ("practising", "gathering_evidence")}


def _mask_state(state: dict, full: bool) -> dict:
    if full:
        return state
    skills = [{**s, "status": "learning" if s["status"] == "gap" else s["status"]} for s in state["skills"]]
    return {**state, "skills": skills, "workflow": _mask_workflow(state.get("workflow"))}


def _avatar_row(db: Session, student_id: uuid.UUID) -> AvatarConfig:
    row = db.get(AvatarConfig, student_id)
    if row is None:
        row = AvatarConfig(student_id=student_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _forecast(db: Session, student_id: uuid.UUID, state: dict):
    gaps = [s for s in state["skills"] if s["status"] == "gap"]
    if not gaps:
        return None
    gap = min(gaps, key=lambda s: kg.depth(s["skill_id"]))
    since = datetime.utcnow() - timedelta(days=14)
    base = (AttemptLog.student_id == student_id, AttemptLog.created_at >= since)
    right = db.scalar(select(func.count(AttemptLog.id)).where(*base, AttemptLog.is_correct.is_(True))) or 0
    days = db.scalar(select(func.count(func.distinct(func.date(AttemptLog.created_at)))).where(*base)) or 0
    per_day = (right / days) if days else 0.0
    remaining = max(0, MASTERY_TARGET - gap["correct"])
    return {
        "skill_id": gap["skill_id"],
        "name_ar": gap["name_ar"],
        "remaining_correct": remaining,
        "per_day": round(per_day, 1),
        "days": 0 if remaining == 0 else plans.forecast_days(remaining, per_day),
    }


@router.get("/question", response_model=QuestionOut)
def get_question(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_self(student_id, user)
    plans.require_quota(db, user, "questions")
    return engine_bridge.next_question(db, student_id)


@router.post("/answer", response_model=DecisionOut)
def submit_answer(student_id: uuid.UUID, payload: AnswerRequest, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    require_self(student_id, user)
    try:
        result = engine_bridge.submit_answer(db, student_id, payload.selected_answer, payload.is_remedial)
    except engine_bridge.EngineError as exc:
        raise HTTPException(exc.status_code, exc.code)
    if not plans.has_full_gap_access(db, user, user):
        result["gap_locked"] = bool(result.get("new_gaps"))
        result["new_gaps"] = []
        result["gap_skill"] = None
        result["diagnosis"] = None
        result["workflow"] = _mask_workflow(result.get("workflow"))
        if result.get("evidence_status"):
            # Basic plan: say evidence is being gathered, without naming the suspected lesson.
            result["evidence_status"] = {"status": result["evidence_status"]["status"],
                                         "message": "نجمع أدلة من إجاباتك لنحدد مصدر الصعوبة."}
    result["remaining_questions"] = plans.snapshot(db, user)["remaining"]["questions"]
    return result


@router.get("/state", response_model=StudentStateOut)
def get_state(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    full = plans.has_full_gap_access(db, user, _student(db, student_id))
    return _mask_state(engine_bridge.state_overview(db, student_id), full)


@router.get("/tree")
def get_tree(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    full = plans.has_full_gap_access(db, user, _student(db, student_id))
    return tree_service.build_tree(engine_bridge._load_state(db, student_id), full)


@router.get("/bootstrap")
def bootstrap(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    student = _student(db, student_id)
    full = plans.has_full_gap_access(db, user, student)
    wallet = economy_service.get_or_create_wallet(db, student_id)
    row = _avatar_row(db, student_id)
    db.commit()
    events, hidden = plans.mask_drilldowns(engine_bridge.drilldown_history(db, student_id), full)
    return {
        "state": _mask_state(engine_bridge.state_overview(db, student_id), full),
        "wallet": {"coins": wallet.coins, "gems": wallet.gems},
        "avatar": avatar_render.config_dict(row),
        "avatar_svg": avatar_render.render(row, "me"),
        "drilldowns": events,
        "drilldowns_hidden": hidden,
        "plan": plans.snapshot(db, student),
    }


@router.get("/report")
def report(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    student = _student(db, student_id)
    full = plans.has_full_gap_access(db, user, student)
    raw = engine_bridge.state_overview(db, student_id)
    locked = (not full) and any(s["status"] == "gap" for s in raw["skills"])
    events, hidden = plans.mask_drilldowns(engine_bridge.drilldown_history(db, student_id), full)
    return {
        "student": {"user_id": str(student.id), "full_name": student.full_name, "handle": student.handle},
        "state": _mask_state(raw, full),
        "drilldowns": events,
        "drilldowns_hidden": hidden,
        "gap_locked": locked,
        "forecast": _forecast(db, student_id, raw) if full else None,
        "diagnoses": engine_bridge.diagnosis_history(db, student_id) if full else [],
        "plan": plans.snapshot(db, student),
    }


@router.get("/diagnoses")
def diagnoses(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Explainable diagnosis record: evidence, confidence, intervention and the outcome after it."""
    require_student_access(student_id, user, db)
    full = plans.has_full_gap_access(db, user, _student(db, student_id))
    history = engine_bridge.diagnosis_history(db, student_id)
    if not full:
        return {"locked": bool(history), "diagnoses": []}
    return {"locked": False, "diagnoses": history}


@router.post("/round", response_model=StudentStateOut)
def new_round(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_self(student_id, user)
    return engine_bridge.start_new_round(db, student_id)


@router.get("/drilldowns", response_model=list[DrillDownOut])
def drilldowns(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    full = plans.has_full_gap_access(db, user, _student(db, student_id))
    return plans.mask_drilldowns(engine_bridge.drilldown_history(db, student_id), full)[0]
