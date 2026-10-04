from app.engine import adaptive_engine as ae
from app.engine import config as ecfg
from app.engine import knowledge_graph as kg
from app.services import curriculum_map as cur


def public_map() -> dict:
    return {
        "course": ecfg.course_meta(),
        "units": [
            {
                "no": u.no,
                "title": u.title,
                "lessons": [
                    {"key": cur.lesson_key(u, l), "no": l.no, "title": l.title, "skill": l.skill}
                    for l in u.lessons
                ],
            }
            for u in cur.UNITS
        ]
    }


def _root_gap(state, full: bool):
    gaps = [g for g in state.gaps if g in kg.SKILLS]
    if not gaps:
        return {"found": False, "locked": False, "skill": None, "name_ar": None, "steps_back": 0}
    gap = sorted(gaps, key=kg.depth)[0]
    steps = max(1, kg.depth(state.current_skill) - kg.depth(gap)) if state.current_skill in kg.SKILLS else 1
    if not full:
        return {"found": True, "locked": True, "skill": None, "name_ar": None, "steps_back": steps}
    return {"found": True, "locked": False, "skill": gap, "name_ar": kg.SKILLS[gap].name_ar, "steps_back": steps}


def build_tree(state, full_gap_access: bool) -> dict:
    units = []
    for u in cur.UNITS:
        lessons = []
        for l in u.lessons:
            key = cur.lesson_key(u, l)
            skill = l.skill if l.skill in kg.SKILLS else None
            attempts = state.attempts.get(skill, 0) if skill else 0
            correct = state.correct.get(skill, 0) if skill else 0
            lessons.append({
                "key": key,
                "no": l.no,
                "title": l.title,
                "skill": skill,
                "status": cur.status(state, l),
                "progress": round(cur.progress(state, l), 3),
                "current": cur.is_current(state, l),
                "gap": bool(skill) and skill in state.gaps and full_gap_access,
                "p_mastery": round(state.mastery(skill), 3) if skill else 0.0,
                "attempts": attempts,
                "correct": correct,
                "accuracy": round(correct / attempts, 3) if attempts else None,
                "missing": cur.missing_prerequisites(state, l),
                "concepts": [
                    {"title": c.title, "segments": cur.segments(c.text)} for c in cur.concepts_for(key)
                ],
            })
        units.append({"no": u.no, "title": u.title, "lessons": lessons})
    return {
        "course": ecfg.course_meta(),
        "units": units,
        "summary": cur.summary(state),
        "tree_health": round(ae.tree_health(state), 3),
        "root_gap": _root_gap(state, full_gap_access),
    }
