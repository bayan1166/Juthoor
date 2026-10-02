import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.engine import config as ecfg


LOCAL_UTC_OFFSET_HOURS = 3


STUDENTS_PER_SEAT = 60


TRIAL_DAYS = 14


LIMITS = {
    "basic": {
        "questions_per_day": 20, "tutor_per_day": 5, "history_days": 7,
        "full_gap_report": False, "max_friends": 3, "classrooms": False,
    },
    "pro": {
        "questions_per_day": None, "tutor_per_day": None, "history_days": None,
        "full_gap_report": True, "max_friends": None, "classrooms": False,
    },
    "school": {
        "questions_per_day": None, "tutor_per_day": None, "history_days": None,
        "full_gap_report": True, "max_friends": None, "classrooms": True,
    },
}


PERIOD_DAYS = {"monthly": 31, "yearly": 366}


def _f(text: str, included: bool = True) -> dict:
    return {"text": text, "included": included}


PLAN_CATALOG = [
    {
        "id": "basic", "name": "Basic", "name_ar": "الأساسية",
        "tagline": "ابدأ مجاناً واكتشف طريقتك في التعلّم",
        "price_month": 0, "price_year": 0, "currency": "JOD", "highlight": False,
        "audience": "للطالب",
        "features": [
            _f(ecfg.COURSE["full_tree_label_ar"]),
            _f("20 سؤال تدريب يومياً"),
            _f("المعلم الذكي: 5 رسائل يومياً"),
            _f("بطاقات شرح لكل خطأ"),
            _f("حتى 3 أصدقاء ورسائل خاصة"),
            _f("سجل تعلّم لمدة 7 أيام"),
            _f("سلسلة الجذر الكاملة وتقرير الفجوة", False),
            _f("الصفوف والواجبات والاختبارات", False),
        ],
    },
    {
        "id": "pro", "name": "Pro", "name_ar": "برو",
        "tagline": "اعرف أين بدأت الفجوة، وأغلقها بخطة واضحة",
        "price_month": 2990, "price_year": 29900, "currency": "JOD", "highlight": True,
        "audience": "للطالب وولي الأمر",
        "features": [
            _f("كل ما في الأساسية"),
            _f("كشف سلسلة الجذر كاملة خطوة بخطوة"),
            _f("تدريب غير محدود يومياً"),
            _f("المعلم الذكي بلا حد يومي"),
            _f("تقرير فجوة قابل للطباعة لولي الأمر"),
            _f("توقّع المدة اللازمة لسدّ الفجوة"),
            _f("أصدقاء ورسائل بلا حد"),
            _f("كامل متجر الشخصية"),
            _f("دعم عبر البريد خلال 24 ساعة"),
        ],
    },
    {
        "id": "school", "name": "School", "name_ar": "المدرسة",
        "tagline": "صفك كاملاً على شجرة واحدة، بمقعد معلم واحد",
        "price_month": 6990, "price_year": 69900, "currency": "JOD", "highlight": False,
        "audience": "للمعلم",
        "features": [
            _f("كل ما في برو للمعلم"),
            _f("طلاب صفوفك يحصلون على برو دون أي رسوم"),
            _f("صفوف بمجموعات ورمز انضمام"),
            _f("واجبات برفع الملفات والتصحيح والتغذية الراجعة"),
            _f("اختبارات وسباقات ولوحات متصدرين"),
            _f("لوحة تحليلات: المخاطر والفجوات وأداء كل طالب"),
            _f("تصدير النتائج بصيغة CSV"),
            _f("حتى 60 طالباً لكل مقعد"),
            _f("دعم عبر واتساب"),
        ],
    },
]


USP = {
    "name": "مسح الجذر",
    "headline": "كل طالب يتعثّر في موضوع، لكن الجذر دائماً في مكان آخر",
    "body": "جذور لا يخبرك أين أخطأ الطالب، بل أين بدأ الخطأ فعلاً: يتتبّع سلسلة المتطلبات السابقة حتى يجد الدرس الأساسي الذي لم يُتقن.",
    "points": [
        "تشخيص دقيق بدل علامة رقمية",
        "خطة لسدّ الفجوة وتوقّع للمدة",
        "تقرير جاهز يشاركه الطالب مع ولي أمره",
    ],
}


@dataclass
class PlanState:
    plan: str
    source: str
    expires_at: datetime | None
    trial_days_left: int | None


def plan_from_fields(plan, expires_at, now: datetime) -> str:
    value = plan.value if hasattr(plan, "value") else str(plan)
    if value == "basic":
        return "basic"
    if expires_at is not None and expires_at < now:
        return "basic"
    return value


def trial_days_left(trial_ends_at, now: datetime):
    if trial_ends_at is None or trial_ends_at <= now:
        return None
    return max(1, math.ceil((trial_ends_at - now).total_seconds() / 86400))


def limits_for(plan: str) -> dict:
    return dict(LIMITS[plan])


def day_start_utc(now: datetime | None = None) -> datetime:
    now = now or datetime.utcnow()
    local = now + timedelta(hours=LOCAL_UTC_OFFSET_HOURS)
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight - timedelta(hours=LOCAL_UTC_OFFSET_HOURS)


def mask_drilldowns(events: list, full: bool) -> tuple[list, int]:
    if full:
        return events, 0
    return events[:1], max(0, len(events) - 1)


def forecast_days(remaining_correct: int, per_day: float):
    if per_day <= 0:
        return None
    return max(1, math.ceil(remaining_correct / per_day))


def price_for(plan_id: str, period: str) -> int:
    for plan in PLAN_CATALOG:
        if plan["id"] == plan_id:
            return plan["price_year"] if period == "yearly" else plan["price_month"]
    raise KeyError(plan_id)
