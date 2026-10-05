import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.engine import adaptive_engine as ae
from app.engine import knowledge_graph as kg
from app.services import tree_service as ts

path = Path(__file__).resolve().parent / "fixtures" / "py.json"
data = json.loads(path.read_text(encoding="utf-8"))
state = ae.StudentState(current_skill="adding_integers", difficulty=1)
for unit in data["tree_full"]["units"]:
    for lesson in unit["lessons"]:
        skill = lesson["skill"]
        if not skill:
            continue
        if lesson["status"] == "mastered":
            state.mastered.add(skill)
        if lesson["attempts"]:
            state.attempts[skill] = lesson["attempts"]
            state.correct[skill] = lesson["correct"]
        if lesson["current"]:
            state.current_skill = skill
        if lesson["gap"]:
            state.gaps.add(skill)
data["tree_full"] = ts.build_tree(state, True)
data["tree_locked"] = ts.build_tree(state, False)
data["map"] = ts.public_map()
sample = data["skills"][0]
data["skills"] = [
    {k: (i if k == "skill_id" else getattr(kg.SKILLS[i], k, None)) for k in sample}
    for i in kg.ordered_skills()
]
from app.services import plan_rules as pr  # noqa: E402
data["plans"] = {"plans": [{**plan, "limits": pr.LIMITS[plan["id"]]} for plan in pr.PLAN_CATALOG], "usp": pr.USP,
                 "currency": "JOD", "provider": "mock"}
path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
print("fixtures refreshed:", len(data["skills"]), "skills")
