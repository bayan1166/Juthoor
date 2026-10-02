from datetime import datetime, timedelta

from app.engine import knowledge_graph as kg


def students_with_gap(overviews, skill_id):
    return [
        student_id for student_id, overview in overviews.items()
        if any(s["skill_id"] == skill_id and s["status"] == "gap" for s in overview["skills"])
    ]


def already_covered(student_ids, skill_id, assignments, latest_diagnosis):
    """Students who already received a remediation assignment for this gap since its latest diagnosis.

    `assignments`: existing remediation assignments of the classroom (objects with skill_id, target_ids,
    created_at). `latest_diagnosis`: {student_id: datetime of the newest diagnosis naming skill_id}.
    A newer diagnosis (fresh evidence after the assignment) makes the student eligible again, so one
    click never creates duplicate assignments for the same evidence.
    """
    covered = set()
    for sid in student_ids:
        since = latest_diagnosis.get(sid)
        for a in assignments:
            if a.skill_id != skill_id or str(sid) not in (a.target_ids or []):
                continue
            if since is None or a.created_at >= since:
                covered.add(sid)
                break
    return covered


def build_remediation(skill_id, now, due_days=5, target_questions=10):
    skill = kg.SKILLS[skill_id]
    description = (
        f"واجب علاجي موجّه للطلاب الذين رصد النظام عندهم فجوة في «{skill.name_ar}».\n"
        f"المطلوب: ادخل صفحة التدريب وأجب عن {target_questions} أسئلة على الأقل، "
        "ثم اكتب في خانة الإجابة ما الذي تعلمته من أخطائك."
    )
    return {
        "title": f"تقوية: {skill.name_ar}",
        "description": description,
        "skill_id": skill_id,
        "target_questions": target_questions,
        "max_score": 100,
        "due_at": now + timedelta(days=due_days),
        "kind": "remediation",
        "tip": skill.intervention,
    }
