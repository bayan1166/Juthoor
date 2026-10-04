"""Product positioning regressions.

Juthoor is a general adaptive-learning platform (prerequisite-gap detection, evidence-first root diagnosis,
targeted remediation, mastery). The Grade 6 mathematics curriculum is the CURRENT content pack only:
it may appear as content metadata, never as the product shell's identity. The public product is B2C
(student + parent); teacher/school/classroom surfaces are not part of it.
"""
import pathlib
import re

from app.engine import config as ecfg
from app.services import plan_rules, tree_service

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATIC = ROOT / "app" / "static"

# "Math." (the JavaScript Math object) is not a subject; anything else spelling a subject or grade is.
SUBJECT_OR_GRADE = re.compile(r"رياضيات|الصف السادس|سادس|[Gg]rade\s*6|(?<![\w.])[Mm]ath(?:s|ematics)?(?![\w.(])")
TEACHER_SCHOOL_PITCH = ("صفوفي", "لوحة معلم", "لوحة المعلم", "باقة المدرسة", "تجربة المدرسة", "برو عبر الصف", "اطلب من معلمك", "لمعلمك", "معلمك")


def _public_frontend():
    for path in STATIC.rglob("*"):
        if path.suffix in {".js", ".html", ".css"}:
            yield path, path.read_text(encoding="utf-8")


def test_public_frontend_shell_never_hard_codes_a_subject_or_grade():
    offenders = [(p.name, m.group(0)) for p, text in _public_frontend() for m in [SUBJECT_OR_GRADE.search(text)] if m]
    assert offenders == [], f"subject/grade must come from content metadata, found: {offenders}"


def test_public_frontend_has_no_teacher_school_or_classroom_pitch():
    offenders = [(p.name, word) for p, text in _public_frontend() for word in TEACHER_SCHOOL_PITCH if word in text]
    assert offenders == []


def test_the_teacher_school_frontend_is_gone():
    assert not (STATIC / "js" / "views" / "teacher.js").exists()
    assert not (STATIC / "js" / "views" / "classes.js").exists()
    for path, text in _public_frontend():
        lowered = text.lower()
        for word in ("teacherview", "classroom", "/classrooms", "org_admin", "school_plan", "join_code"):
            assert word not in lowered, (path.name, word)


def test_ai_tutor_is_an_assistant_not_a_teacher():
    _, text = next((p, t) for p, t in _public_frontend() if p.name == "main.js")
    assert "المساعد الذكي" in text and "المعلم الذكي" not in text


def test_public_demo_login_offers_no_teacher_account():
    auth = (STATIC / "js" / "views" / "auth.js").read_text(encoding="utf-8")
    demos = auth[auth.index("const DEMOS"):auth.index("];", auth.index("const DEMOS"))]
    assert "teacher@demo.jo" not in auth and "student2@demo.jo" in demos and "parent@demo.jo" in demos


def test_course_identity_is_data_not_product_logic():
    meta = ecfg.course_meta()
    assert {"subject", "subject_ar", "grade", "grade_ar", "title_ar", "is_demo_content"} <= set(meta)
    assert meta["is_demo_content"] is True
    assert tree_service.public_map()["course"] == meta


def test_tree_payload_carries_course_metadata_and_the_demo_content_still_works():
    from app.engine import adaptive_engine as ae

    tree = tree_service.build_tree(ae.StudentState(current_skill="absolute_value", difficulty=1), True)
    assert tree["course"]["subject"] == ecfg.COURSE["subject"]
    lessons = [lesson for unit in tree["units"] for lesson in unit["lessons"]]
    assert len(lessons) == 18 and sum(1 for lesson in lessons if lesson["skill"]) == 9


def test_plans_and_usp_sell_the_mechanism_not_a_subject():
    blob = repr(plan_rules.PLAN_CATALOG) + repr(plan_rules.USP)
    assert not SUBJECT_OR_GRADE.search(blob)
    assert "المعلم الذكي" not in blob
    assert "الجذر" in plan_rules.USP["body"] or "الجذر" in plan_rules.USP["headline"]


def test_learner_facing_engine_messages_do_not_mention_a_teacher():
    for rel in ("app/engine/adaptive_engine.py", "app/engine/practice.py", "app/services/engine_bridge.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "لمعلمك" not in text and "المعلم الذكي" not in text, rel
