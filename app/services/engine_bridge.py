import json
import logging
import uuid
from datetime import datetime
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from app.engine import adaptive_engine as ae
from app.engine import config as ecfg
from app.engine import knowledge_graph as kg
from app.models.adaptive import (AnswerReceipt, AttemptLog, DiagnosisEvent, DrillDownEvent, MasteryStatus, SkillMastery,
                                 StudentAdaptiveState)
from app.schemas.common import z
from app.services import workflow as wf
from app.services.economy_service import grant_reward

logger = logging.getLogger("juthoor.engine")


_DEFAULT_ROW = dict(consec_wrong=0, total_answered=0, round_answered=0)


def _insert_state_row(db: Session, student_id: uuid.UUID) -> bool:
    """``INSERT ... ON CONFLICT DO NOTHING`` the student's state row; True when this call created it.

    The primary key (student_id) is the UNIQUE guarantee. With the conflict clause, two simultaneous
    first requests cannot both insert: the loser waits for the winner's transaction, then does
    nothing (it used to hit a primary-key violation and return a 500).
    """
    dialect = db.get_bind().dialect.name
    insert = {"postgresql": postgresql.insert, "sqlite": sqlite.insert}.get(dialect)
    if insert is None:  # other dialects are unsupported; keep a correct (non-atomic) fallback
        if db.get(StudentAdaptiveState, student_id) is not None:
            return False
        db.add(StudentAdaptiveState(student_id=student_id, current_skill=ecfg.DEFAULT_START_SKILL,
                                    difficulty=ecfg.START_DIFFICULTY))
        db.flush()
        return True
    result = db.execute(insert(StudentAdaptiveState).values(
        student_id=student_id, current_skill=ecfg.DEFAULT_START_SKILL, difficulty=ecfg.START_DIFFICULTY,
        return_stack=[], recent_questions=[], updated_at=datetime.utcnow(), **_DEFAULT_ROW,
    ).on_conflict_do_nothing(index_elements=["student_id"]))
    return result.rowcount == 1


def provision_state(db: Session, student_id: uuid.UUID) -> bool:
    """Create and **commit** the student's state row if it is missing (idempotent, race-free).

    Called when a learner opens their own state/bootstrap: the row exists afterwards exactly once, however
    many first requests arrive together. Read paths for anyone else never write (see ``_load_state``).
    """
    if db.get(StudentAdaptiveState, student_id) is not None:
        return False
    created = _insert_state_row(db, student_id)
    db.commit()
    return created


def lock_student_state(db: Session, student_id: uuid.UUID) -> StudentAdaptiveState:
    """Take the per-student row lock (``SELECT ... FOR UPDATE``) and return the *fresh* row.

    Every write path (question served, answer graded, new round, tutor drill-down) calls this first,
    so concurrent requests for one student run one after another instead of both reading the same
    stale state and overwriting each other. The lock is held until the transaction commits or rolls
    back. If the row does not exist yet it is created with ``ON CONFLICT DO NOTHING`` and then locked
    (the creation commits with the caller's transaction). SQLite (explicit non-production mode only)
    ignores FOR UPDATE.
    """
    stmt = (select(StudentAdaptiveState).where(StudentAdaptiveState.student_id == student_id)
            .with_for_update().execution_options(populate_existing=True))
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        _insert_state_row(db, student_id)
        row = db.execute(stmt).scalar_one()
    return row


def _load_state(db: Session, student_id: uuid.UUID, lock: bool = False) -> ae.StudentState:
    """Rebuild the engine state. ``lock=True`` is the write path (locks, creates the row if needed).

    ``lock=False`` is **read-only**: a learner with no stored row is shown the default starting state
    and nothing is written (so teacher/parent views and the integrity checker never create rows).
    """
    if lock:
        row = lock_student_state(db, student_id)
    else:
        row = db.get(StudentAdaptiveState, student_id)
        if row is None:
            row = SimpleNamespace(current_skill=ecfg.DEFAULT_START_SKILL, difficulty=ecfg.START_DIFFICULTY,
                                  return_stack=[], **_DEFAULT_ROW)
    masteries = db.scalars(select(SkillMastery).where(SkillMastery.student_id == student_id)).all()

    # Stale state (a skill removed from the curriculum graph, a corrupted difficulty) must never
    # crash the learner's session: unknown skills are dropped and the position is repaired.
    current = row.current_skill if row.current_skill in kg.SKILLS else ecfg.DEFAULT_START_SKILL
    if current != row.current_skill:
        logger.warning("student %s: unknown current skill %r reset to %s", student_id, row.current_skill, current)
    state = ae.StudentState(
        current_skill=current,
        difficulty=min(max(int(row.difficulty or ecfg.START_DIFFICULTY), ecfg.MIN_DIFFICULTY), ecfg.MAX_DIFFICULTY),
        consec_wrong=max(0, row.consec_wrong or 0),
        total_answered=max(0, row.total_answered or 0),
        round_answered=max(0, row.round_answered or 0),
        return_stack=[s for s in (row.return_stack or []) if s in kg.SKILLS],
    )
    for m in masteries:
        if m.skill_id not in kg.SKILLS:
            continue
        state.p_mastery[m.skill_id] = m.p_mastery
        state.attempts[m.skill_id] = m.attempts
        state.correct[m.skill_id] = m.correct
        if m.status == MasteryStatus.mastered:
            state.mastered.add(m.skill_id)
        elif m.status == MasteryStatus.inferred:
            state.inferred.add(m.skill_id)
        elif m.status == MasteryStatus.gap:
            state.gaps.add(m.skill_id)
        elif m.status == MasteryStatus.parked:
            state.parked.add(m.skill_id)
    return state


def _status_for(state: ae.StudentState, skill_id: str) -> MasteryStatus:
    label = ae.skill_status(state, skill_id)
    return MasteryStatus(label if label != "learning" else "learning")


def _save_state(db: Session, student_id: uuid.UUID, state: ae.StudentState) -> None:
    row = db.get(StudentAdaptiveState, student_id)
    row.current_skill = state.current_skill
    row.difficulty = state.difficulty
    row.consec_wrong = state.consec_wrong
    row.total_answered = state.total_answered
    row.round_answered = state.round_answered
    row.return_stack = list(state.return_stack)

    touched = set(state.p_mastery) | set(state.attempts) | state.mastered | state.inferred | state.gaps | state.parked
    existing = {m.skill_id: m for m in db.scalars(select(SkillMastery).where(SkillMastery.student_id == student_id))}
    for skill_id in touched:
        row_m = existing.get(skill_id)
        if row_m is None:
            row_m = SkillMastery(student_id=student_id, skill_id=skill_id)
            db.add(row_m)
        row_m.p_mastery = state.mastery(skill_id)
        row_m.attempts = state.attempts.get(skill_id, 0)
        row_m.correct = state.correct.get(skill_id, 0)
        if skill_id in state.mastered:
            row_m.status = MasteryStatus.mastered
        elif skill_id in state.inferred:
            row_m.status = MasteryStatus.inferred
        elif skill_id in state.gaps:
            row_m.status = MasteryStatus.gap
        elif skill_id in state.parked:
            row_m.status = MasteryStatus.parked
        elif row_m.attempts > 0:
            row_m.status = MasteryStatus.learning
        else:
            row_m.status = MasteryStatus.untouched


class EngineError(Exception):

    def __init__(self, code: str, status_code: int = 409):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def _session(db: Session, student_id: uuid.UUID):
    from app.services import session_core as sc
    state = _load_state(db, student_id, lock=True)
    row = db.get(StudentAdaptiveState, student_id)
    plan, pending = row.remediation_plan, row.pending_question
    if plan and not _plan_is_valid(plan):
        logger.warning("student %s: dropping stale remediation plan %r", student_id, plan.get("skill"))
        plan = None
    if pending and (pending.get("skill") not in kg.SKILLS or "correct_answer" not in pending):
        logger.warning("student %s: dropping stale pending question", student_id)
        pending = None
    sess = sc.Session(state=state, plan=plan, pending_banner=row.pending_banner,
                      recent=list(row.recent_questions or []), pending=pending)
    return sess, row


def _plan_is_valid(plan) -> bool:
    if not isinstance(plan, dict) or plan.get("skill") not in kg.SKILLS:
        return False
    return all(isinstance(item, dict) and item.get("skill") in kg.SKILLS for item in plan.get("stack", []))


def _store(db: Session, student_id: uuid.UUID, sess, row) -> None:
    _save_state(db, student_id, sess.state)
    row.remediation_plan = sess.plan
    row.pending_banner = sess.pending_banner
    row.recent_questions = list(sess.recent)
    row.pending_question = sess.pending


def next_question(db: Session, student_id: uuid.UUID) -> dict:
    import random
    from app.services import session_core as sc
    sess, row = _session(db, student_id)
    q = sc.serve(sess, random.Random())
    _store(db, student_id, sess, row)
    db.commit()
    return q


def _json_safe(value: dict) -> dict:
    return json.loads(json.dumps(value, default=str, ensure_ascii=False))


def submit_answer(db: Session, student_id: uuid.UUID, selected: str, is_remedial: bool = False,
                  request_id: str | None = None) -> dict:
    """Grade one answer atomically.

    The student's state row is locked first, so a double click, a retry or a second browser tab
    cannot grade the same question twice. With a ``request_id`` the original response is stored and
    returned for any repeat of the same id (``idempotent_replay`` = True); without one a repeat is
    rejected with ``no_active_question`` because the first request already consumed the question.
    """
    from app.services import session_core as sc
    sess, row = _session(db, student_id)
    if request_id:
        receipt = db.get(AnswerReceipt, (student_id, request_id))
        if receipt is not None:
            replay = dict(receipt.response)
            db.rollback()  # nothing was changed; release the row lock
            if replay.pop("_selected", None) != str(selected):
                raise EngineError("request_id_reused", 409)  # same key, different answer: not a retry
            replay["idempotent_replay"] = True
            return replay
    if not sess.pending:
        db.rollback()
        raise EngineError("no_active_question", 409)
    pending = dict(sess.pending)
    prev_gaps = set(sess.state.gaps)
    result = sc.grade(sess, selected)
    new_gaps = set(sess.state.gaps) - prev_gaps
    _store(db, student_id, sess, row)

    now = datetime.utcnow()
    db.add(AttemptLog(
        created_at=now, student_id=student_id, skill_id=pending["skill"], pattern=pending.get("pattern", ""),
        difficulty=pending["difficulty"], is_correct=result["is_correct"], selected_answer=str(selected),
        correct_answer=pending["correct_answer"], misconception=result["misconception"],
        source=pending.get("source", "offline"), remedial_stage=pending.get("remedial") or "",
        action=result["action"],
    ))
    for ev in result["events"]:
        db.add(DrillDownEvent(student_id=student_id, from_skill=ev["from_skill"], from_pattern=pending.get("pattern", ""),
                              to_skill=ev["to_skill"], to_pattern=ev["to_pattern"], depth=ev["depth"],
                              direction=ev["direction"], triggered_by=ev["triggered_by"]))

    found = result.get("diagnosis")
    if found:
        db.add(DiagnosisEvent(
            created_at=now, student_id=student_id, origin_skill=found["origin"], root_skill=found["root"],
            confidence=found["confidence"], confidence_level=found.get("confidence_level"),
            explanation=found.get("explanation"), p_gap=found["p_gap"], evidence=found["evidence"], path=found["path"]))

    reward = grant_reward(db, student_id, is_correct=result["is_correct"], action=result["action"])
    db.flush()  # autoflush is off: make the new rows visible to the workflow query below
    result.pop("events")
    result.pop("engine_action")
    result.update(coins_awarded=reward.coins, gems_awarded=reward.gems, new_gaps=sorted(new_gaps),
                  workflow=workflow_status(db, student_id, sess.state, result, answered_skill=pending["skill"]))
    if request_id:
        db.add(AnswerReceipt(student_id=student_id, request_id=request_id,
                             response={**_json_safe(result), "_selected": str(selected)}))
    db.commit()
    return result


def workflow_status(db: Session, student_id: uuid.UUID, state: ae.StudentState, result: dict | None = None,
                    answered_skill: str | None = None) -> dict:
    latest = db.scalar(select(DiagnosisEvent).where(DiagnosisEvent.student_id == student_id)
                       .order_by(DiagnosisEvent.created_at.desc()).limit(1))
    last = None if latest is None else {"origin": latest.origin_skill, "root": latest.root_skill,
                                         "confidence": latest.confidence}
    return wf.workflow(state, last, result, answered_skill)


def _name_ar(skill_id: str) -> str:
    return kg.SKILLS[skill_id].name_ar if skill_id in kg.SKILLS else skill_id


def _tally(rows) -> dict:
    right = sum(1 for r in rows if r.is_correct)
    return {"right": right, "wrong": len(rows) - right}


def diagnosis_history(db: Session, student_id: uuid.UUID, limit: int = 10) -> list[dict]:
    """Persisted diagnoses with their evidence and what happened afterwards.

    The outcome is computed from the attempt log after each diagnosis: answers on the root
    (remediation) and answers on the original lesson (the retry), plus the root's current status.
    """
    events = db.scalars(select(DiagnosisEvent).where(DiagnosisEvent.student_id == student_id)
                        .order_by(DiagnosisEvent.created_at.desc()).limit(limit)).all()
    if not events:
        return []
    state = _load_state(db, student_id)
    # One query for every attempt since the oldest listed diagnosis (was one query per diagnosis).
    oldest = min(e.created_at for e in events)
    attempts_since = db.scalars(select(AttemptLog).where(AttemptLog.student_id == student_id,
                                                         AttemptLog.created_at > oldest)
                                .order_by(AttemptLog.created_at).limit(5000)).all()
    out = []
    for ev in events:
        after = [a for a in attempts_since if a.created_at > ev.created_at]
        on_root = [a for a in after if a.skill_id == ev.root_skill]
        on_origin = [a for a in after if a.skill_id == ev.origin_skill] if ev.origin_skill != ev.root_skill else []
        root_status = ae.skill_status(state, ev.root_skill) if ev.root_skill in kg.SKILLS else "unknown"
        if root_status in ("mastered",):
            stage = "resolved"
        elif on_root:
            stage = "remediating"
        else:
            stage = "pending"
        evidence = [{**e, "name_ar": _name_ar(e.get("skill", ""))} for e in (ev.evidence or []) if isinstance(e, dict)]
        out.append({
            "diagnosis_id": str(ev.id),
            "created_at": z(ev.created_at),
            "origin_skill": ev.origin_skill, "origin_name_ar": _name_ar(ev.origin_skill),
            "root_skill": ev.root_skill, "root_name_ar": _name_ar(ev.root_skill),
            "path": [{"skill": s, "name_ar": _name_ar(s)} for s in (ev.path or [])],
            "confidence": ev.confidence, "confidence_level": ev.confidence_level,
            "explanation": ev.explanation or "",
            "evidence": evidence,
            "intervention": kg.SKILLS[ev.root_skill].intervention if ev.root_skill in kg.SKILLS else "",
            "outcome": {
                "stage": stage,
                "root_status": root_status,
                "root_after": _tally(on_root),
                "origin_retry": _tally(on_origin),
            },
        })
    return out


def start_new_round(db: Session, student_id: uuid.UUID) -> dict:
    from app.services import session_core as sc
    sess, row = _session(db, student_id)
    sc.new_round(sess)
    _store(db, student_id, sess, row)
    db.commit()
    return state_overview(db, student_id)


def drilldown_history(db: Session, student_id: uuid.UUID, limit: int = 30) -> list[dict]:
    rows = db.scalars(select(DrillDownEvent).where(DrillDownEvent.student_id == student_id)
                      .order_by(DrillDownEvent.created_at.desc()).limit(limit)).all()
    return [{
        "from_skill": r.from_skill, "from_name_ar": kg.SKILLS[r.from_skill].name_ar if r.from_skill in kg.SKILLS else r.from_skill,
        "to_skill": r.to_skill, "to_name_ar": kg.SKILLS[r.to_skill].name_ar if r.to_skill in kg.SKILLS else r.to_skill,
        "direction": r.direction, "triggered_by": r.triggered_by, "depth": r.depth, "created_at": z(r.created_at),
    } for r in reversed(rows)]


def state_overview(db: Session, student_id: uuid.UUID) -> dict:
    state = _load_state(db, student_id)
    skills = []
    for sid, skill in kg.SKILLS.items():
        skills.append({
            "skill_id": sid,
            "name_ar": skill.name_ar,
            "status": ae.skill_status(state, sid),
            "p_mastery": round(state.mastery(sid), 3),
            "attempts": state.attempts.get(sid, 0),
            "correct": state.correct.get(sid, 0),
        })
    return {
        "student_id": student_id,
        "current_skill": state.current_skill,
        "difficulty": state.difficulty,
        "total_answered": state.total_answered,
        "tree_health": round(ae.tree_health(state), 3),
        "round_answered": state.round_answered,
        "round_over": ae.round_over(state),
        "in_remediation": bool(getattr(db.get(StudentAdaptiveState, student_id), "remediation_plan", None)),
        "skills": skills,
        "workflow": workflow_status(db, student_id, state),
    }


def trigger_manual_drill_down(db: Session, student_id: uuid.UUID, from_skill: str, misconception: str) -> dict | None:
    from app.engine import config as ecfg
    from app.engine import offline_bank as ob
    from app.engine import practice as pr
    if from_skill not in kg.SKILLS or from_skill not in ob.REGISTRY:
        return None
    patterns = ob.patterns_of(from_skill)
    if not patterns:
        return None
    _load_state(db, student_id, lock=True)
    row = db.get(StudentAdaptiveState, student_id)
    plan = {
        "stage": pr.EASIER, "skill": from_skill, "difficulty": ecfg.PROBE_DIFFICULTY,
        "pattern": patterns[0], "stack": [], "misconception": misconception or None,
        "breadcrumb": f"المعلم الذكي لاحظ أن الصعوبة تبدأ من «{kg.SKILLS[from_skill].name_ar}»، لنثبّت هذا الأساس أولاً.",
    }
    row.remediation_plan = plan
    row.pending_question = None
    db.add(DrillDownEvent(student_id=student_id, from_skill=row.current_skill, to_skill=from_skill,
                          to_pattern=patterns[0], depth=1, direction="descend", triggered_by="rag_tutor"))
    db.commit()
    return plan
