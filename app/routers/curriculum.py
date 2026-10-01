from fastapi import APIRouter
from pydantic import BaseModel

from app.engine import knowledge_graph as kg
from app.services import tree_service

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


@router.get("/map")
def curriculum_map():
    return tree_service.public_map()
