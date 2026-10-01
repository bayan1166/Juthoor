from datetime import datetime, timedelta

from app.engine import knowledge_graph as kg


def students_with_gap(overviews, skill_id):
    return [
        student_id for student_id, overview in overviews.items()
        if any(s["skill_id"] == skill_id and s["status"] == "gap" for s in overview["skills"])
    ]


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
