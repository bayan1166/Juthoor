import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engine import knowledge_graph as kg
from app.models.adaptive import AttemptLog, DiagnosisEvent, DrillDownEvent, MasteryStatus, SkillMastery
from app.models.org import User

SEVERITY_THRESHOLDS = {"high": 0.35, "medium": 0.55}


def _severity(p_mastery: float, consecutive_misses: int) -> str:
    if p_mastery < SEVERITY_THRESHOLDS["high"] or consecutive_misses >= 4:
        return "high"
    if p_mastery < SEVERITY_THRESHOLDS["medium"] or consecutive_misses >= 2:
        return "medium"
    return "low"


def _consecutive_misses(db: Session, student_id: uuid.UUID, skill_id: str) -> int:
    rows = db.scalars(
        select(AttemptLog.is_correct)
        .where(AttemptLog.student_id == student_id, AttemptLog.skill_id == skill_id)
        .order_by(AttemptLog.created_at.desc())
        .limit(10)
    ).all()
    streak = 0
    for is_correct in rows:
        if is_correct:
            break
        streak += 1
    return streak


def struggle_alerts(db: Session, student_id: uuid.UUID) -> list[dict]:
    masteries = db.scalars(
        select(SkillMastery).where(
            SkillMastery.student_id == student_id,
            SkillMastery.status.in_([MasteryStatus.gap, MasteryStatus.learning, MasteryStatus.parked]),
        )
    ).all()

    events = db.scalars(
        select(DrillDownEvent)
        .where(DrillDownEvent.student_id == student_id)
        .order_by(DrillDownEvent.created_at.desc())
        .limit(200)
    ).all()
    depth_by_skill: dict[str, list[int]] = defaultdict(list)
    for e in events:
        depth_by_skill[e.from_skill].append(e.depth)

    # The predicted cause comes from the persisted evidence-based diagnoses, never a guess.
    diagnosed: dict[str, str] = {}
    for ev in db.scalars(select(DiagnosisEvent).where(DiagnosisEvent.student_id == student_id)
                         .order_by(DiagnosisEvent.created_at)):
        diagnosed[ev.origin_skill] = ev.root_skill
        diagnosed[ev.root_skill] = ev.root_skill

    alerts = []
    for m in masteries:
        misses = _consecutive_misses(db, student_id, m.skill_id)
        severity = _severity(m.p_mastery, misses)
        if severity == "low":
            continue
        depths = depth_by_skill.get(m.skill_id, [])
        avg_depth = sum(depths) / len(depths) if depths else 0.0
        predicted_cause = diagnosed.get(m.skill_id)
        skill = kg.SKILLS.get(m.skill_id)
        alerts.append({
            "skill_id": m.skill_id,
            "skill_name_ar": skill.name_ar if skill else m.skill_id,
            "severity": severity,
            "p_mastery": round(m.p_mastery, 3),
            "consecutive_misses": misses,
            "drill_down_depth_avg": round(avg_depth, 2),
            "predicted_root_cause_skill": predicted_cause,
            "recommended_action": skill.intervention if skill else "",
        })
    alerts.sort(key=lambda a: (a["severity"] != "high", -a["consecutive_misses"]))
    return alerts


def remediation_progress(db: Session, student_id: uuid.UUID) -> list[dict]:
    events = db.scalars(
        select(DrillDownEvent).where(DrillDownEvent.student_id == student_id)
    ).all()
    by_skill: dict[str, list[DrillDownEvent]] = defaultdict(list)
    for e in events:
        by_skill[e.from_skill].append(e)

    results = []
    for skill_id, ev_list in by_skill.items():
        descents = [e for e in ev_list if e.direction == "descend"]
        ascents = [e for e in ev_list if e.direction == "ascend"]
        resolved = min(len(ascents), len(descents))
        rate = resolved / len(descents) if descents else 0.0
        durations = []
        for d, a in zip(sorted(descents, key=lambda e: e.created_at), sorted(ascents, key=lambda e: e.created_at)):
            if a.created_at > d.created_at:
                durations.append((a.created_at - d.created_at).total_seconds() / 60)
        avg_minutes = sum(durations) / len(durations) if durations else 0.0
        skill = kg.SKILLS.get(skill_id)
        results.append({
            "skill_id": skill_id,
            "skill_name_ar": skill.name_ar if skill else skill_id,
            "drill_down_events": len(descents),
            "resolved_events": resolved,
            "resolution_rate": round(rate, 3),
            "avg_minutes_to_resolve": round(avg_minutes, 2),
        })
    return results


def engagement_summary(db: Session, student_id: uuid.UUID) -> dict:
    since_30 = datetime.utcnow() - timedelta(days=30)
    since_7 = datetime.utcnow() - timedelta(days=7)

    active_days = db.scalar(
        select(func.count(func.distinct(func.date(AttemptLog.created_at))))
        .where(AttemptLog.student_id == student_id, AttemptLog.created_at >= since_30)
    ) or 0
    questions_7 = db.scalar(
        select(func.count()).where(AttemptLog.student_id == student_id, AttemptLog.created_at >= since_7)
    ) or 0

    day_rows = db.scalars(
        select(func.date(AttemptLog.created_at)).where(AttemptLog.student_id == student_id).distinct()
        .order_by(func.date(AttemptLog.created_at).desc())
    ).all()
    streak = 0
    cursor = datetime.utcnow().date()
    day_set = set(day_rows)
    while cursor in day_set:
        streak += 1
        cursor -= timedelta(days=1)

    return {
        "active_days_last_30": int(active_days),
        "avg_session_minutes": None,
        "questions_answered_last_7": int(questions_7),
        "current_streak": streak,
    }


def student_insights(db: Session, student_id: uuid.UUID) -> dict:
    from app.services.engine_bridge import state_overview
    overview = state_overview(db, student_id)
    return {
        "student_id": student_id,
        "generated_at": datetime.utcnow(),
        "tree_health": overview["tree_health"],
        "struggle_alerts": struggle_alerts(db, student_id),
        "remediation_progress": remediation_progress(db, student_id),
        "engagement": engagement_summary(db, student_id),
    }


def cohort_insights(db: Session, organization_id: uuid.UUID) -> dict:
    student_ids = db.scalars(
        select(User.id).where(User.organization_id == organization_id, User.role == "student")
    ).all()
    if not student_ids:
        return {"organization_id": organization_id, "generated_at": datetime.utcnow(),
                "student_count": 0, "avg_tree_health": 0.0, "top_struggle_skills": []}

    from app.services.engine_bridge import state_overview
    healths = []
    skill_hits: dict[str, int] = defaultdict(int)
    worst_alert_by_skill: dict[str, dict] = {}
    for sid in student_ids:
        overview = state_overview(db, sid)
        healths.append(overview["tree_health"])
        for alert in struggle_alerts(db, sid):
            skill_hits[alert["skill_id"]] += 1
            current = worst_alert_by_skill.get(alert["skill_id"])
            if current is None or alert["p_mastery"] < current["p_mastery"]:
                worst_alert_by_skill[alert["skill_id"]] = alert

    top_skills = sorted(skill_hits.items(), key=lambda kv: -kv[1])[:5]
    top_alerts = [worst_alert_by_skill[sid] for sid, _ in top_skills]

    return {
        "organization_id": organization_id,
        "generated_at": datetime.utcnow(),
        "student_count": len(student_ids),
        "avg_tree_health": round(sum(healths) / len(healths), 3),
        "top_struggle_skills": top_alerts,
    }
