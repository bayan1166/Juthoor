"""
Juthoor knowledge graph: 6th-grade Integers & Operations (Jordan Curriculum)
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional
import networkx as nx

@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    name_ar: str
    description: str
    prerequisites: tuple[str, ...]
    ladder: tuple[str, str, str]      
    typical_errors: tuple[str, ...]   
    intervention: str                 
    x: float                          

DIFFICULTY_LABELS = {1: "لغز تسخين", 2: "تحدي الجذور", 3: "لغز العباقرة"}

SKILLS: dict[str, Skill] = {
    s.id: s
    for s in [
        # ------------------------------------------------------------ الدرس 1
        Skill(
            id="absolute_value",
            name="Absolute Value & Integers",
            name_ar="الأعداد الصحيحة والقيمة المطلقة",
            description="التمييز بين الأعداد الموجبة والسالبة والصفر، وإيجاد القيمة المطلقة والمعكوس بناء على البعد عن الصفر.",
            prerequisites=(),
            ladder=(
                "تحديد موقع عدد موجب أو سالب على خط الأعداد.",
                "إيجاد القيمة المطلقة لعدد سالب.",
                "حل حزورة مسافة بين جسمين (مثل طائر وسمكة) باستخدام القيمة المطلقة.",
            ),
            typical_errors=(
                "يعتقد أن القيمة المطلقة للعدد السالب تكون سالبة",
                "يخلط بين موقع العدد الموجب والسالب على خط الأعداد",
            ),
            intervention="استخدم خط الأعداد الأرضي، اطلب من الطالب المشي خطوات للأمام (موجب) وللخلف (سالب).",
            x=-1.0,
        ),
        # ------------------------------------------------------------ الدرس 2
        Skill(
            id="comparing_integers",
            name="Comparing & Ordering",
            name_ar="مقارنة الأعداد الصحيحة وترتيبها",
            description="مقارنة الأعداد الموجبة والسالبة والصفر، وترتيبها تصاعدياً وتنازلياً.",
            prerequisites=("absolute_value",),
            ladder=(
                "مقارنة بين عدد سالب وعدد موجب أو صفر.",
                "مقارنة بين عددين سالبين (أيهما أقرب للصفر).",
                "ترتيب 4 أعداد مختلطة الإشارات تنازلياً أو تصاعدياً.",
            ),
            typical_errors=(
                "يعتقد أن -10 أكبر من -2 لأن 10 أكبر من 2",
                "يخلط بين الترتيب التصاعدي والتنازلي في الأعداد السالبة",
            ),
            intervention="ارسم ميزان حرارة، وضح أن الدرجة -2 أدفأ (أعلى) من الدرجة -10.",
            x=0.0,
        ),
        # ------------------------------------------------------------ الدرس 3
        Skill(
            id="adding_integers",
            name="Adding Integers",
            name_ar="جمع الأعداد الصحيحة",
            description="جمع عددين متشابهين أو مختلفين في الإشارة باستخدام خط الأعداد أو القيمة المطلقة.",
            prerequisites=("comparing_integers",),
            ladder=(
                "جمع عددين سالبين.",
                "جمع عدد موجب وعدد سالب (القيمة المطلقة الأكبر للموجب).",
                "جمع عدد موجب وعدد سالب (القيمة المطلقة الأكبر للسالب) ضمن مسألة حياتية.",
            ),
            typical_errors=(
                "يجمع العددين دائماً متجاهلاً الإشارة السالبة",
                "يعطي الناتج إشارة العدد الأصغر بدل الأكبر عند اختلاف الإشارات",
            ),
            intervention="استخدم قطع العد (حمراء وزرقاء) لتشكيل الأزواج الصفرية.",
            x=1.0,
        ),
        # ------------------------------------------------------------ الدرس 4
        Skill(
            id="subtracting_integers",
            name="Subtracting Integers",
            name_ar="طرح الأعداد الصحيحة",
            description="طرح عدد صحيح من آخر عن طريق إضافة معكوسه.",
            prerequisites=("adding_integers",),
            ladder=(
                "طرح عدد موجب من عدد سالب.",
                "طرح عدد سالب من عدد موجب (تحويل الطرح لجمع).",
                "حل لغز فرق درجات الحرارة (مثال المريخ والأرض).",
            ),
            typical_errors=(
                "يطرح القيم المطلقة ويتجاهل تحويل العملية إلى جمع المعكوس",
                "يخطئ في إشارة الناتج عندما يكون المطروح منه أصغر من المطروح",
            ),
            intervention="علم الطالب قاعدة (ثبّت، اعكس، اعكس) لتحويل الطرح إلى جمع المعكوس.",
            x=2.0,
        ),
        # ------------------------------------------------------------ الدرس 5
        Skill(
            id="mult_div_integers",
            name="Multiplying & Dividing Integers",
            name_ar="ضرب الأعداد الصحيحة وقسمتها",
            description="ضرب وقسمة الأعداد الصحيحة وتطبيق قواعد الإشارات.",
            prerequisites=("subtracting_integers",),
            ladder=(
                "ضرب/قسمة عدد موجب في عدد سالب.",
                "ضرب/قسمة عددين سالبين.",
                "استخدام أولويات العمليات في مسألة تحتوي ضرب وجمع أعداد صحيحة.",
            ),
            typical_errors=(
                "يعتقد أن ضرب عددين سالبين يعطي ناتجاً سالباً",
                "يجمع بدل أن يضرب عندما يرى الأقواس الملتصقة مثل 3(-4)",
            ),
            intervention="اربط ضرب سالب في سالب بمفهوم لغوي: (نفي النفي إثبات).",
            x=3.0,
        ),
    ]
}

def _build_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_nodes_from(SKILLS)
    for skill in SKILLS.values():
        for pre in skill.prerequisites:
            if pre not in SKILLS:
                raise ValueError(f"{skill.id}: unknown prerequisite '{pre}'")
            g.add_edge(pre, skill.id)
    if not nx.is_directed_acyclic_graph(g):
        raise ValueError("Knowledge graph contains a cycle")
    return g

GRAPH: nx.DiGraph = _build_graph()

def prerequisites(skill_id: str) -> list[str]:
    return list(GRAPH.predecessors(skill_id))

def dependents(skill_id: str) -> list[str]:
    return list(GRAPH.successors(skill_id))

def ancestors(skill_id: str) -> set[str]:
    return set(nx.ancestors(GRAPH, skill_id))

def descendants(skill_id: str) -> set[str]:
    return set(nx.descendants(GRAPH, skill_id))

@lru_cache(maxsize=None)
def depth(skill_id: str) -> int:
    pres = prerequisites(skill_id)
    return 0 if not pres else 1 + max(depth(p) for p in pres)

def ordered_skills() -> list[str]:
    return sorted(SKILLS, key=lambda s: (depth(s), SKILLS[s].x))


def nearest_prerequisite_with_bank(skill_id: str, has_bank) -> Optional[str]:
    """
    Walk up the prerequisite graph from `skill_id` and return the first ancestor
    for which `has_bank(ancestor_id)` is true (used by the deep drill-down to
    cross from one skill into the previous one once a pattern chain bottoms out).
    `has_bank` is injected so this module never has to import offline_bank.
    """
    for pre in prerequisites(skill_id):
        if has_bank(pre):
            return pre
        found = nearest_prerequisite_with_bank(pre, has_bank)
        if found:
            return found
    return None