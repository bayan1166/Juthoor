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


def next_question(db: Session, student_id: uuid.UUID) -> dict:
    state = _load_state(db, student_id)
    from app.engine import offline_bank as ob
    import random
    q = ob.generate_offline(state.current_skill, state.difficulty, random.Random())
    db.commit()
    return q


def submit_answer(db: Session, student_id: uuid.UUID, skill_id: str, difficulty: int,
                   pattern: str, selected: str, correct: str, is_remedial: bool) -> dict:
    from app.engine import practice
    state = _load_state(db, student_id)
    is_correct = practice.is_correct({"correct_answer": correct}, selected)

    prev_gaps = set(state.gaps)
    decision = ae.decide_next(state, is_correct)
    new_gaps = set(state.gaps) - prev_gaps

    _save_state(db, student_id, state)
    db.add(AttemptLog(
        student_id=student_id, skill_id=skill_id, pattern=pattern, difficulty=difficulty,
        is_correct=is_correct, selected_answer=str(selected), correct_answer=correct,
        misconception="", source="offline", remedial_stage="remedial" if is_remedial else "",
        action=decision.action,
    ))

    if decision.action == "backtrack":
        db.add(DrillDownEvent(student_id=student_id, from_skill=skill_id, to_skill=decision.next_skill,
                               depth=1, direction="descend", triggered_by="engine"))
    if decision.action == "return_up":
        db.add(DrillDownEvent(student_id=student_id, from_skill=skill_id, to_skill=decision.next_skill,
                               depth=1, direction="ascend", triggered_by="engine"))

    reward = grant_reward(db, student_id, is_correct=is_correct, action=decision.action)
    db.commit()

    return {
        "action": decision.action,
        "next_skill": decision.next_skill,
        "next_difficulty": decision.next_difficulty,
        "reason": decision.reason,
        "breadcrumb": getattr(decision, "breadcrumb", ""),
        "gap_skill": decision.gap_skill,
        "round_over": decision.round_over,
        "coins_awarded": reward.coins,
        "gems_awarded": reward.gems,
        "new_gaps": list(new_gaps),
    }


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
        "skills": skills,
    }


def trigger_manual_drill_down(db: Session, student_id: uuid.UUID, from_skill: str, misconception: str) -> dict | None:
    from app.engine import practice as pr
    state = _load_state(db, student_id)
    plan_row = db.get(StudentAdaptiveState, student_id)
    fake_q = {"skill": from_skill, "difficulty": state.difficulty, "pattern": kg.SKILLS[from_skill].ladder[0] and ""}
    plan = pr.start({**fake_q, "pattern": (ob_patterns(from_skill) or "")}, selected=None)
    plan["misconception"] = misconception
    advanced = pr.advance(plan, answered_correctly=False)
    if advanced is None:
        return None
    plan_row.remediation_plan = advanced
    plan_row.current_skill = advanced["skill"]
    plan_row.difficulty = advanced["difficulty"]
    db.add(DrillDownEvent(
        student_id=student_id, from_skill=from_skill, to_skill=advanced["skill"],
        to_pattern=advanced.get("pattern", ""), depth=len(advanced.get("stack", [])) + 1,
        direction="descend", triggered_by="rag_tutor",
    ))
    db.commit()
    return advanced


def ob_patterns(skill_id: str) -> str:
    from app.engine import offline_bank as ob
    patterns = ob.patterns_of(skill_id)
    return patterns[0] if patterns else ""
