import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine import adaptive_engine as ae
from app.engine import config as ecfg
from app.engine import knowledge_graph as kg
from app.models.adaptive import AttemptLog, DrillDownEvent, MasteryStatus, SkillMastery, StudentAdaptiveState
from app.services.economy_service import grant_reward


def _load_state(db: Session, student_id: uuid.UUID) -> ae.StudentState:
    row = db.get(StudentAdaptiveState, student_id)
    masteries = db.scalars(select(SkillMastery).where(SkillMastery.student_id == student_id)).all()
    if row is None:
        row = StudentAdaptiveState(student_id=student_id, current_skill=ecfg.DEFAULT_START_SKILL, difficulty=ecfg.START_DIFFICULTY)
        db.add(row)
        db.flush()

    state = ae.StudentState(
        current_skill=row.current_skill,
        difficulty=row.difficulty,
        consec_wrong=row.consec_wrong,
        total_answered=row.total_answered,
        round_answered=row.round_answered,
        return_stack=list(row.return_stack or []),
    )
    for m in masteries:
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
    state = _load_state(db, student_id)
    row = db.get(StudentAdaptiveState, student_id)
    sess = sc.Session(state=state, plan=row.remediation_plan, pending_banner=row.pending_banner,
                      recent=list(row.recent_questions or []), pending=row.pending_question)
    return sess, row


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


def submit_answer(db: Session, student_id: uuid.UUID, selected: str, is_remedial: bool = False) -> dict:
    from app.services import session_core as sc
    sess, row = _session(db, student_id)
    if not sess.pending:

        raise EngineError("no_active_question", 409)
    pending = dict(sess.pending)
    prev_gaps = set(sess.state.gaps)
    result = sc.grade(sess, selected)
    new_gaps = set(sess.state.gaps) - prev_gaps
    _store(db, student_id, sess, row)

    db.add(AttemptLog(
        student_id=student_id, skill_id=pending["skill"], pattern=pending.get("pattern", ""),
        difficulty=pending["difficulty"], is_correct=result["is_correct"], selected_answer=str(selected),
        correct_answer=pending["correct_answer"], misconception=result["misconception"],
        source=pending.get("source", "offline"), remedial_stage=pending.get("remedial") or "",
        action=result["action"],
    ))
    for ev in result["events"]:
        db.add(DrillDownEvent(student_id=student_id, from_skill=ev["from_skill"], from_pattern=pending.get("pattern", ""),
                              to_skill=ev["to_skill"], to_pattern=ev["to_pattern"], depth=ev["depth"],
                              direction=ev["direction"], triggered_by=ev["triggered_by"]))

    reward = grant_reward(db, student_id, is_correct=result["is_correct"], action=result["action"])
    db.commit()
    result.pop("events")
    result.pop("engine_action")
    result.update(coins_awarded=reward.coins, gems_awarded=reward.gems, new_gaps=sorted(new_gaps))
    return result


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
        "direction": r.direction, "triggered_by": r.triggered_by, "depth": r.depth, "created_at": r.created_at,
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
        "in_remediation": bool(db.get(StudentAdaptiveState, student_id).remediation_plan),
        "skills": skills,
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
    _load_state(db, student_id)
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
