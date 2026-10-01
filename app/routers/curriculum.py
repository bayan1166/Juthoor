from fastapi import APIRouter
from pydantic import BaseModel

from app.engine import knowledge_graph as kg

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


class SkillContentOut(BaseModel):
    skill_id: str
    name: str
    name_ar: str
    description: str
    prerequisites: list[str]
    dependents: list[str]
    depth: int
    x: float
    ladder: list[str]
    typical_errors: list[str]
    intervention: str


@router.get("/skills", response_model=list[SkillContentOut])
def list_skills():
    """The knowledge graph: every skill, its prerequisites, and its teaching content.

    Public (no auth) because it is curriculum content, not student data. Ordered
    roots-first so a client can draw the tree top-down.
    """
    out = []
    for sid in kg.ordered_skills():
        s = kg.SKILLS[sid]
        out.append(SkillContentOut(
            skill_id=sid, name=s.name, name_ar=s.name_ar, description=s.description,
            prerequisites=list(s.prerequisites), dependents=kg.dependents(sid),
            depth=kg.depth(sid), x=s.x, ladder=list(s.ladder),
            typical_errors=list(s.typical_errors), intervention=s.intervention,
        ))
    return out
