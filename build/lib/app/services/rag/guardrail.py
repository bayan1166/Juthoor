import re

from app.services.rag import offline_tutor
from app.services.rag.textutil import ar_norm

FALLBACK = "عذراً، أنا مبرمج حصرياً لمساعدتك في المنهج التعليمي وتطوير مستواك الأكاديمي."

_DIGITS = str.maketrans("\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9", "01234567890123456789")
_MATH = re.compile(r"[0-9+\u00d7\u00f7*/=<>|^\u221a%\u2212]")
_TOKEN = re.compile(r"[\w\u0600-\u06ff]+")
_PREFIXES = ("وبال", "وال", "بال", "كال", "فال", "لل", "ال", "و", "ب", "ل", "ف")

_INJECTION = (
    "ignore previous", "ignore all previous", "ignore the above", "system prompt", "developer mode", "jailbreak",
    "act as", "pretend you", "you are now", "تجاهل التعليمات", "تجاهل كل", "اهمل التعليمات", "انسي التعليمات",
    "تصرف كانك", "تقمص", "وضع المطور", "التعليمات السابقه", "تعليمات النظام",
)

_STRONG = {
    "رياضيات", "اعداد", "سالب", "سالبه", "موجب", "موجبه", "صفر", "جمع", "اجمع", "طرح", "اطرح", "ضرب", "اضرب",
    "قسمه", "اقسم", "كسر", "كسور", "كسري", "كسريه", "مقام", "بسط", "مقلوب", "مطلقه", "معكوس", "مقارنه", "قارن",
    "ناتج", "مساله", "مسائل", "تمرين", "تمارين", "درس", "دروس", "اختبرني", "عشري", "عشريه", "احداثي", "دائره",
    "هندسه", "انسحاب", "انعكاس", "معادله", "مضاعف", "تبسيط", "احسب",
    "math", "maths", "add", "subtract", "multiply", "divide", "fraction", "fractions", "negative", "positive",
    "integer", "integers", "equation", "decimal",
}
_WEAK = {
    "عدد", "صحيح", "صحيحه", "حساب", "حل", "حلها", "شرح", "اشرح", "وضح", "فسر", "فهم", "افهم", "فاهم", "فهمت",
    "تعلم", "علمني", "خطا", "غلط", "صح", "مثال", "امثله", "جواب", "اجابه", "اجابتي", "معلم", "فرق", "باقي",
    "عامل", "قسم", "رتب", "صف", "نتيجه", "مراجعه", "مدرسه", "مهاره", "حاصل", "نسبه", "قاعده", "قواعد", "اشاره",
    "اشارات", "ترتيب", "اكبر", "اصغر", "سؤال", "سوال", "اسئله", "اختبار", "امتحان", "واجب", "منهج", "جذر",
    "جذور", "فجوه", "اتقان", "مجموع", "مستوي", "تدريب",
    "solve", "explain", "number", "numbers", "quiz", "practice", "lesson", "homework", "answer", "question",
    "sum", "product", "difference",
}
_STRONG_SET = frozenset(ar_norm(x) for x in _STRONG)
_WEAK_SET = frozenset(ar_norm(x) for x in _WEAK)

_SHORT_OK = frozenset(ar_norm(x) for x in (
    "ليش", "لماذا", "كيف", "ايوه", "ايوا", "لا", "نعم", "طيب", "تمام", "شكرا", "مرحبا", "اهلا", "هلا", "سلام",
    "ok", "okay", "why", "how", "yes", "no", "thanks", "thx", "hi", "hello", "hey", "اعد", "كمل", "التالي", "التالى",
))


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(ar_norm(text).translate(_DIGITS))


def _variants(token: str):
    yield token
    for prefix in _PREFIXES:
        if token.startswith(prefix) and len(token) - len(prefix) >= 2:
            yield token[len(prefix):]


def _rank(token: str) -> int:
    best = 0
    for form in _variants(token):
        if form in _STRONG_SET:
            return 2
        if form in _WEAK_SET:
            best = 1
        elif len(form) >= 5:
            if any(form.startswith(stem) for stem in _STRONG_SET if len(stem) >= 4):
                return 2
            if any(form.startswith(stem) for stem in _WEAK_SET if len(stem) >= 4):
                best = 1
    return best


def has_signal(message: str) -> bool:
    norm = ar_norm(message).translate(_DIGITS)
    if _MATH.search(norm):
        return True
    ranks = [_rank(t) for t in _tokens(message)]
    if 2 in ranks:
        return True
    if len({t for t, r in zip(_tokens(message), ranks) if r == 1}) >= 2:
        return True
    return offline_tutor._has(norm, offline_tutor.STUCK_WORDS) or offline_tutor._has(norm, offline_tutor.PRACTICE_WORDS)


def is_off_topic(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False
    norm = ar_norm(text)
    if any(marker in norm for marker in _INJECTION):
        return True
    tokens = _tokens(text)
    if not tokens:
        return False
    if has_signal(text):
        return False
    if len(tokens) == 1:
        return False
    if len(tokens) == 2:
        return not any(t in _SHORT_OK for t in tokens)
    return True
