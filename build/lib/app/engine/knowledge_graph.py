from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional
import networkx as nx

from app.engine.diagnosis import PrereqGraph

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

        Skill(
            id="fractions_addsub",
            name="Adding & Subtracting Fractions",
            name_ar="جمع الكسور وطرحها",
            description="جمع الكسور وطرحها بمقام واحد وبمقامين مختلفين باستخدام المقام المشترك.",
            prerequisites=("mult_div_integers",),
            ladder=(
                "جمع وطرح كسرين لهما المقام نفسه.",
                "جمع وطرح كسرين أحد مقاميهما من مضاعفات الآخر.",
                "جمع وطرح كسور بمقامين مختلفين في مسألة حياتية.",
            ),
            typical_errors=(
                "يجمع البسطين والمقامين معاً",
                "يطرح البسطين دون توحيد المقامين",
            ),
            intervention="استخدم شرائح الكسور الورقية لإظهار أن الأجزاء يجب أن تكون متساوية الحجم قبل الجمع.",
            x=4.0,
        ),

        Skill(
            id="mixed_addsub",
            name="Adding & Subtracting Mixed Numbers",
            name_ar="جمع الأعداد الكسرية وطرحها",
            description="التحويل بين العدد الكسري والكسر غير الفعلي، وجمع الأعداد الكسرية وطرحها مع الاستبدال والاستلاف.",
            prerequisites=("fractions_addsub",),
            ladder=(
                "تحويل عدد كسري إلى كسر غير فعلي والعكس.",
                "جمع عددين كسريين مع الاستبدال وطرحهما مع الاستلاف.",
                "حل مسألة حياتية بأعداد كسرية بمقامين مختلفين.",
            ),
            typical_errors=(
                "ينسى تحويل الكسر غير الفعلي إلى عدد كسري عند الجمع",
                "يطرح الكسر الأصغر من الأكبر بدل الاستلاف",
            ),
            intervention="اعرض العدد الكسري على شكل أشرطة كاملة وقطع، ودرّب الطالب على استلاف شريط كامل وتجزئته.",
            x=5.0,
        ),

        Skill(
            id="mixed_mult",
            name="Multiplying Mixed Numbers",
            name_ar="ضرب الأعداد الكسرية",
            description="ضرب الكسور والأعداد الكسرية بعد تحويلها إلى كسور غير فعلية مع التبسيط قبل الضرب.",
            prerequisites=("mixed_addsub",),
            ladder=(
                "ضرب كسر في كسر وعدد صحيح في كسر.",
                "ضرب عدد كسري في عدد صحيح مع التبسيط.",
                "ضرب عددين كسريين في مسألة مساحة.",
            ),
            typical_errors=(
                "يضرب الأجزاء الصحيحة وحدها والكسور وحدها",
                "يوحّد المقامات قبل الضرب دون حاجة",
            ),
            intervention="ارسم مستطيلاً مقسماً لإظهار أن ضرب الكسور هو أخذ جزء من جزء.",
            x=6.0,
        ),

        Skill(
            id="mixed_div",
            name="Dividing Mixed Numbers",
            name_ar="قسمة الأعداد الكسرية",
            description="قسمة الكسور والأعداد الكسرية بالضرب في مقلوب المقسوم عليه.",
            prerequisites=("mixed_mult",),
            ladder=(
                "إيجاد مقلوب الكسر وقسمة كسر على كسر.",
                "قسمة عدد صحيح على كسر وكسر على عدد صحيح.",
                "قسمة عددين كسريين في مسألة حياتية.",
            ),
            typical_errors=(
                "يقلب الكسر الأول بدل الثاني",
                "يضرب بدل أن يقسم",
            ),
            intervention="اسأل: كم قطعة من الربع تلزم لملء الواحد؟ لإظهار أن القسمة على كسر تُكبّر الناتج.",
            x=7.0,
        ),
    ]
}

# Domain-agnostic view used by the diagnosis engine. Construction validates the mapping
# (unknown prerequisites, self-loops, duplicates, cycles) and fails fast at import time.
PREREQ_GRAPH: PrereqGraph = PrereqGraph({s.id: s.prerequisites for s in SKILLS.values()})


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
    for pre in prerequisites(skill_id):
        if has_bank(pre):
            return pre
        found = nearest_prerequisite_with_bank(pre, has_bank)
        if found:
            return found
    return None
