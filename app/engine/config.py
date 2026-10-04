DEFAULT_START_SKILL = "absolute_value"
START_DIFFICULTY = 1
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 3
PROBE_DIFFICULTY = 1
SESSION_LENGTH = 5

MASTERY_THRESHOLD = 0.85


BKT = {
    "p_init": 0.3,
    "p_slip": 0.1,
    "p_guess": 0.2,
    "p_learn": 0.2
}


MAX_DRILL_DEPTH = 4


MIN_CHAIN_EVIDENCE = 3

# A single wrong probe is not enough to blame a skill: the root needs this many wrong answers.
MIN_ROOT_EVIDENCE = 2

# A prerequisite counts as secure only with this many observed correct answers and none wrong
# (one lucky correct answer is not evidence). See diagnosis.solid().
MIN_SOLID_EVIDENCE = 2

# Likelihood-ratio the root's own answers must reach before it is named (see diagnosis.py).
MIN_ROOT_LR = 20.0

# A mastered skill whose BKT estimate falls below this is treated as contested again.
CONTEST_THRESHOLD = 0.5


LLM = {
    "enabled": True,
    "provider": "groq",
    "model": "llama-3.1-8b-instant",
    "timeout_seconds": 4,
}


# Subject/course wording lives here (not in prompts or plan text) so a second subject or grade band
# is a configuration change. The diagnosis engine itself knows nothing about any subject.
# The values below describe the CURRENT content pack (demo/seed content), not the product. Juthoor is a
# general adaptive-learning platform; the UI shows these only as content metadata ("current course").
COURSE = {
    "id": "jo-math-g6",
    "subject": "mathematics",
    "subject_ar": "الرياضيات",
    "grade": 6,
    "grade_ar": "الصف السادس",
    "title_ar": "رياضيات الصف السادس",
    "curriculum_ar": "المنهج الأردني",
    "is_demo_content": True,
    "description_ar": "الرياضيات (المسار المتاح حالياً: الأعداد الصحيحة ثم الكسور)",
    "full_tree_label_ar": "شجرة المنهج الكاملة",
}


def course_meta() -> dict:
    """Public, display-only metadata of the current content pack."""
    keys = ("id", "subject", "subject_ar", "grade", "grade_ar", "title_ar", "curriculum_ar", "is_demo_content")
    return {k: COURSE[k] for k in keys}
