"""
Juthoor offline question bank  (Unit 1: integers and their operations, 6th grade).

Every skill has 3 difficulty levels and every level has 5-7 question *templates*.  A template builds
a fresh question from random numbers each time, so a lesson is covered from many angles:

    generate_offline(skill_id, difficulty, rng, avoid=[...], pattern="ai_diff")

Each template belongs to a **pattern** (a specific idea / typical mistake, e.g. "sign of the sum when the
signs differ").  The pattern is what lets the app, after a wrong answer, show an explanation card for that
idea and then ask another question on the *same* pattern (see practice.py).

Every wrong option carries the misconception that produces it, so the card can say *why* the student
probably chose it.

RTL note: in an Arabic sentence "-5" is drawn as "5-".  Everything mathematical is therefore wrapped in
left-to-right isolates (L / N / E below) and negatives use the real minus sign U+2212.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

LRI, PDI, MINUS = "\u2066", "\u2069", "\u2212"


# ============================================================ display helpers
def n(x: int) -> str:
    """Integer as text with a real minus sign."""
    return str(x).replace("-", MINUS)


def par(x: int) -> str:
    return f"({n(x)})" if x < 0 else n(x)


def L(s) -> str:
    """Isolate a piece of maths so it is drawn left-to-right inside an Arabic sentence."""
    return f"{LRI}{s}{PDI}"


def M(s: str) -> str:
    """A maths fragment written with ASCII '-' -> isolated LTR text with real minus signs."""
    return L(s.replace("-", MINUS))


def N(x: int) -> str:
    return L(n(x))


def E(*tokens: str) -> str:
    return L(" ".join(tokens))


def add(a, b): return E(n(a), "+", par(b))
def sub(a, b): return E(n(a), MINUS, par(b))
def mul(a, b): return E(n(a), "×", par(b))
def div(a, b): return E(n(a), "÷", par(b))
def absx(x): return f"|{n(x)}|"


def deg(x: int) -> str:
    return L(f"{n(x)}°C")


_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,")


def norm(s) -> str:
    """Canonical form used to compare answers (typed or chosen)."""
    s = str(s)
    for ch in (LRI, PDI, "\u200e", "\u200f", " ", "\u00a0", "\t"):
        s = s.replace(ch, "")
    s = s.translate(_AR_DIGITS).replace(MINUS, "-").replace("\u2013", "-").replace("\u2014", "-").replace("،", ",")
    return s[1:] if s.startswith("+") else s


def _show(v) -> str:
    s = n(v) if isinstance(v, int) and not isinstance(v, bool) else str(v)
    if LRI in s:
        return s
    return L(s) if any(ch in s for ch in "0123456789<>=|") else s


def _q(question, correct, wrong, explain, hint, kind="mcq") -> dict:
    return dict(question=question, correct_answer=_show(correct),
                distractors=[(_show(w), why) for w, why in wrong],
                explanation=explain, hint=hint, type=kind)


def _tf(statement, truth, why_wrong, explain, hint) -> dict:
    return dict(question=statement, correct_answer="صح" if truth else "خطأ",
                distractors=[("خطأ" if truth else "صح", why_wrong)],
                explanation=explain, hint=hint, type="tf")


# ================================================================== registry
@dataclass(frozen=True)
class Template:
    fn: Callable[[random.Random], dict]
    skill: str
    level: int
    pattern: str


REGISTRY: dict[str, dict[int, list[Template]]] = {}


def tpl(skill: str, level: int, pattern: str):
    def deco(fn):
        REGISTRY.setdefault(skill, {}).setdefault(level, []).append(Template(fn, skill, level, pattern))
        return fn
    return deco


# ========================================================== pattern cards
# One card per idea: title, the rule, and a worked example that is NOT one of the generated questions.
# Every equation is wrapped with M(...) so the RTL page does not flip it around the "=".
PATTERNS: dict[str, dict[str, str]] = {
    # ---- lesson 1: integers & absolute value
    "av_meaning": dict(
        title="تمثيل المواقف بأعداد صحيحة",
        rule="الزيادة والربح والإيداع والارتفاع فوق الصفر تُمثَّل بعدد موجب، والنقص والخسارة والسحب والعمق تحت الصفر تُمثَّل بعدد سالب.",
        example=f"غاصت سمكة 12 متراً تحت سطح البحر ← {M('-12')} ، وارتفع طائر 5 أمتار فوق سطح البحر ← {M('+5')}."),
    "av_line": dict(
        title="موقع العدد على خط الأعداد",
        rule="الأعداد الموجبة على يمين الصفر والسالبة على يساره. كلما ابتعدنا يميناً زاد العدد، وكلما ابتعدنا يساراً نقص.",
        example=f"العدد {M('-3')} يبعد 3 خطوات إلى يسار الصفر، والعدد {M('3')} يبعد 3 خطوات إلى يمينه."),
    "av_opposite": dict(
        title="معكوس العدد",
        rule="معكوس العدد هو العدد الذي يبعد عن الصفر المسافة نفسها لكن في الجهة المقابلة، فنغيّر الإشارة فقط. معكوس الصفر هو الصفر.",
        example=f"معكوس {M('7')} هو {M('-7')} ، ومعكوس {M('-4')} هو {M('4')}."),
    "av_abs": dict(
        title="القيمة المطلقة",
        rule="القيمة المطلقة لعدد هي بُعده عن الصفر، والمسافة لا تكون سالبة أبداً. نحذف الإشارة ونأخذ الرقم.",
        example=f"{M('|-9| = 9')} ، {M('|9| = 9')} ، {M('|0| = 0')}."),
    "av_abs_compare": dict(
        title="مقارنة القيم المطلقة",
        rule="لمقارنة القيم المطلقة نقارن بُعد كل عدد عن الصفر دون النظر إلى الإشارة. أما لمقارنة الأعداد نفسها فننظر إلى موقعها على خط الأعداد.",
        example=f"{M('|-8| = 8')} أكبر من {M('|5| = 5')} ، لكن العدد {M('-8')} أصغر من العدد {M('5')}."),
    "av_abs_expr": dict(
        title="العمليات على القيمة المطلقة",
        rule="احسب القيمة المطلقة أولاً (تصبح موجبة)، ثم نفّذ العملية المطلوبة.",
        example=M("|-6| + |2| = 6 + 2 = 8") + "."),
    "av_distance": dict(
        title="المسافة بين عددين",
        rule="إذا كان العددان على جهتين مختلفتين من الصفر نجمع قيمتيهما المطلقتين. وإذا كانا على جهة واحدة نطرح الأصغر من الأكبر (بقيمتيهما المطلقتين).",
        example=f"المسافة بين {M('8')} و {M('-6')} هي {M('8 + 6 = 14')} ، والمسافة بين {M('-2')} و {M('-9')} هي {M('9 - 2 = 7')}."),
    "av_solve_abs": dict(
        title="العدد الذي قيمته المطلقة معلومة",
        rule="عددان لهما القيمة المطلقة نفسها: العدد ومعكوسه، لأن كليهما يبعد المسافة نفسها عن الصفر.",
        example=f"إذا كانت {M('|x| = 4')} فإن {M('x = 4')} أو {M('x = -4')}."),
    # ---- lesson 2: comparing & ordering
    "ci_sign": dict(
        title="المقارنة حسب الإشارة",
        rule="أي عدد موجب أكبر من أي عدد سالب. والصفر أكبر من كل عدد سالب وأصغر من كل عدد موجب.",
        example=f"{M('-20 < 1')} و {M('0 > -3')}."),
    "ci_neg": dict(
        title="مقارنة الأعداد السالبة",
        rule="بين عددين سالبين، الأكبر هو الأقرب إلى الصفر (قيمته المطلقة أصغر). فكّر بميزان الحرارة: -2 أدفأ من -10.",
        example=f"{M('-2 > -10')} لأن {M('-2')} أقرب إلى الصفر."),
    "ci_order": dict(
        title="ترتيب الأعداد الصحيحة",
        rule="التصاعدي من الأصغر إلى الأكبر (على خط الأعداد من اليسار إلى اليمين)، والتنازلي من الأكبر إلى الأصغر. السالب الأبعد عن الصفر هو الأصغر.",
        example=f"تصاعدياً: {M('-7, -1, 0, 4')} ، وتنازلياً: {M('4, 0, -1, -7')}."),
    "ci_between": dict(
        title="الأعداد الواقعة بين عددين",
        rule="الأعداد الصحيحة بين عددين هي التي تقع بينهما على خط الأعداد دون العددين نفسيهما.",
        example=f"الأعداد الصحيحة بين {M('-3')} و {M('2')} هي {M('-2, -1, 0, 1')}."),
    # ---- lesson 3: adding
    "ai_same": dict(
        title="جمع عددين لهما الإشارة نفسها",
        rule="نجمع القيمتين المطلقتين ونضع الإشارة نفسها.",
        example=f"{M('-6 + (-3) = -9')} لأن 6 + 3 = 9 والإشارة سالبة."),
    "ai_diff": dict(
        title="جمع عددين مختلفي الإشارة",
        rule="نطرح القيمة المطلقة الأصغر من الأكبر، ونضع إشارة العدد الذي قيمته المطلقة أكبر.",
        example=f"{M('-9 + 5 = -4')} (الفرق 4 والإشارة سالبة لأن 9 هو الأكبر)، و {M('9 + (-5) = 4')}."),
    "ai_zero": dict(
        title="الأزواج الصفرية",
        rule="العدد ومعكوسه مجموعهما صفر.",
        example=f"{M('7 + (-7) = 0')} و {M('-12 + 12 = 0')}."),
    "ai_line": dict(
        title="الجمع على خط الأعداد",
        rule="نبدأ من العدد الأول ونتحرك بمقدار العدد الثاني: يميناً إذا كان موجباً ويساراً إذا كان سالباً.",
        example=f"لحساب {M('2 + (-5)')} نبدأ من 2 ونتحرك 5 خطوات يساراً فنصل إلى {M('-3')}."),
    "ai_context": dict(
        title="مسائل الجمع الحياتية",
        rule="حوّل كل معلومة إلى عدد بإشارة (ربح، صعود، إيداع = موجب؛ خسارة، نزول، سحب = سالب) ثم اجمع الأعداد.",
        example=f"كان رصيدك 10 دنانير ثم دفعت 15 ديناراً: {M('10 + (-15) = -5')}."),
    "ai_multi": dict(
        title="جمع أكثر من عددين",
        rule="اجمع من اليسار إلى اليمين خطوة خطوة، أو اجمع الأعداد الموجبة معاً والسالبة معاً ثم اجمع الناتجين.",
        example=f"{M('4 + (-9) + 7')}: الموجبة {M('4 + 7 = 11')} ، والسالبة {M('-9')} ، فالناتج {M('11 + (-9) = 2')}."),
    "ai_missing": dict(
        title="إيجاد العدد المجهول في الجمع",
        rule="لإيجاد العدد المجهول نضيف معكوس العدد المعلوم إلى الطرفين.",
        example=f"إذا كان {M('x + (-3) = 4')} فإن {M('x = 4 + 3 = 7')}."),
    # ---- lesson 4: subtracting
    "si_rule": dict(
        title="الطرح هو جمع المعكوس",
        rule="نثبّت العدد الأول، نحوّل الطرح إلى جمع، ونعكس إشارة العدد الثاني: a − b = a + (−b).",
        example=f"{M('5 - 8 = 5 + (-8) = -3')}."),
    "si_neg": dict(
        title="طرح عدد سالب",
        rule="طرح عدد سالب يعني جمع عدد موجب (ناقص الناقص زائد): a − (−b) = a + b.",
        example=f"{M('4 - (-6) = 4 + 6 = 10')} ، و {M('-4 - (-6) = -4 + 6 = 2')}."),
    "si_pos": dict(
        title="طرح عدد موجب من عدد سالب",
        rule="نحوّل الطرح إلى جمع معكوس العدد الموجب (وهو سالب)، فنجمع عددين سالبين.",
        example=f"{M('-4 - 3 = -4 + (-3) = -7')}."),
    "si_order": dict(
        title="ترتيب الطرح مهم",
        rule="الطرح ليس تبديلياً: a − b تختلف عن b − a. وإذا كان المطروح أكبر من المطروح منه فالناتج سالب.",
        example=f"{M('3 - 8 = -5')} أما {M('8 - 3 = 5')}."),
    "si_diff": dict(
        title="الفرق بين قيمتين",
        rule="الفرق = القيمة الأكبر − القيمة الأصغر. لإيجاد الفرق بين درجتي حرارة أو ارتفاعين نطرح الأدنى من الأعلى، وطرح السالب يصبح جمعاً.",
        example=f"الفرق بين 10 درجات و {M('-4')} درجات هو {M('10 - (-4) = 14')} درجة."),
    # ---- lesson 5: multiplying & dividing
    "md_sign": dict(
        title="قاعدة الإشارات",
        rule="في الضرب والقسمة: إشارتان متشابهتان ← ناتج موجب. إشارتان مختلفتان ← ناتج سالب.",
        example=f"{M('(+)(+) = +')} ، {M('(-)(-) = +')} ، {M('(+)(-) = -')} ، {M('(-)(+) = -')}."),
    "md_mult": dict(
        title="ضرب الأعداد الصحيحة",
        rule="اضرب القيمتين المطلقتين ثم حدّد الإشارة بقاعدة الإشارات.",
        example=f"{M('(-6) × (-3) = 18')} (سالب × سالب = موجب) ، و {M('6 × (-3) = -18')}."),
    "md_div": dict(
        title="قسمة الأعداد الصحيحة",
        rule="اقسم القيمتين المطلقتين ثم حدّد الإشارة بقاعدة الإشارات نفسها: متشابهتان موجب، مختلفتان سالب.",
        example=f"{M('-20 ÷ 4 = -5')} ، و {M('-20 ÷ (-4) = 5')}."),
    "md_paren": dict(
        title="الأقواس الملتصقة",
        rule="عندما يلتصق عدد بقوس دون علامة بينهما فهذا يعني ضرباً وليس جمعاً.",
        example=f"{M('3(-4)')} تعني {M('3 × (-4) = -12')}."),
    "md_multi": dict(
        title="ضرب عدة أعداد",
        rule="نعدّ العوامل السالبة: إذا كان عددها زوجياً فالناتج موجب، وإذا كان فردياً فالناتج سالب.",
        example=f"{M('(-2) × (-3) × (-1)')}: ثلاثة عوامل سالبة (عدد فردي) فالناتج {M('-6')}."),
    "md_order": dict(
        title="أولويات العمليات",
        rule="نبدأ بما داخل الأقواس، ثم الضرب والقسمة (من اليسار إلى اليمين)، ثم الجمع والطرح.",
        example=f"{M('2 + 3 × (-4) = 2 + (-12) = -10')}."),
    "md_context": dict(
        title="مسائل الضرب والقسمة الحياتية",
        rule="حوّل التغيير إلى عدد بإشارة (النقص = سالب)، ثم اضرب أو اقسم واحترم قاعدة الإشارات.",
        example=f"انخفضت الحرارة 3 درجات كل ساعة لمدة 4 ساعات: {M('(-3) × 4 = -12')} درجة."),
}


# =====================================================================================
# LESSON 1  -  absolute_value   (integers, number line, opposite, absolute value, distance)
# =====================================================================================
S1 = "absolute_value"


@tpl(S1, 1, "av_meaning")
def _av1_meaning(r):
    k = r.randint(11, 30)
    ctx = [
        (f"غاص غواص {k} م تحت سطح البحر", -k), (f"صعد متسلق {k} م فوق سطح البحر", k),
        (f"ربح تاجر {k} ديناراً", k), (f"خسر تاجر {k} ديناراً", -k),
        (f"سحب سامر {k} ديناراً من حسابه", -k), (f"أودعت سلمى {k} ديناراً في حسابها", k),
        (f"أصبحت درجة الحرارة {k} درجة تحت الصفر", -k), (f"أصبحت درجة الحرارة {k} درجة فوق الصفر", k),
    ]
    text, v = r.choice(ctx)
    why = "زيادة أو فوق الصفر فهو موجب" if v > 0 else "نقص أو تحت الصفر فهو سالب"
    return _q(f"أي عدد صحيح يمثّل الموقف: {text}؟", v,
              [(-v, "عكس إشارة الموقف"), (0, "ظن أن الموقف يمثل الصفر"),
               ((k + 1) * (1 if v > 0 else -1), "أخطأ في قراءة مقدار العدد")],
              f"الموقف {why}، فيُمثَّل بالعدد {N(v)}.", "هل الموقف زيادة (فوق الصفر) أم نقص (تحت الصفر)؟")


@tpl(S1, 1, "av_line")
def _av1_side(r):
    left, a = r.random() < 0.5, r.randint(1, 9)
    others = r.sample([x for x in range(1, 10) if x != a], 3)
    if left:
        q, correct, wrong = "على خط الأعداد، أي الأعداد التالية يقع على يسار الصفر؟", -a, [(x, "خلط بين اليمين واليسار") for x in others]
    else:
        q, correct, wrong = "على خط الأعداد، أي الأعداد التالية يقع على يمين الصفر؟", a, [(-x, "خلط بين اليمين واليسار") for x in others]
    return _q(q, correct, wrong, "الأعداد السالبة على يسار الصفر، والموجبة على يمينه.", "ابدأ من الصفر وتخيّل خط الأعداد.")


@tpl(S1, 1, "av_line")
def _av1_side_tf(r):
    a = r.randint(1, 12)
    num = r.choice([-a, a])
    right = r.random() < 0.5
    truth = (num > 0) == right
    return _tf(f"العدد {N(num)} يقع على {'يمين' if right else 'يسار'} الصفر على خط الأعداد.", truth,
               "خلط بين اليمين واليسار",
               f"العدد {N(num)} {'موجب' if num > 0 else 'سالب'} فيقع على {'يمين' if num > 0 else 'يسار'} الصفر.",
               "الموجب يمين، السالب يسار.")


@tpl(S1, 1, "av_line")
def _av1_steps(r):
    k, left = r.randint(2, 9), r.random() < 0.5
    c = -k if left else k
    return _q(f"أي عدد يبعد {k} وحدات إلى {'يسار' if left else 'يمين'} الصفر على خط الأعداد؟", c,
              [(-c, "اتجه إلى الجهة المعاكسة"), (0, "بقي عند الصفر"), (c + (-1 if left else 1), "عدّ وحدة زائدة")],
              f"نتحرك {k} وحدات {'إلى اليسار' if left else 'إلى اليمين'} من الصفر فنصل إلى {N(c)}.", "اليسار سالب واليمين موجب.")


@tpl(S1, 1, "av_opposite")
def _av1_opposite(r):
    a = r.choice([x for x in range(-15, 16) if x != 0])
    return _q(f"ما معكوس العدد {N(a)}؟ (اكتب العدد فقط)", -a,
              [(a, "ظن أن المعكوس هو العدد نفسه"), (0, "خلط بين المعكوس والصفر")],
              f"معكوس {N(a)} هو {N(-a)}: البعد نفسه عن الصفر لكن في الجهة المقابلة.", "غيّر الإشارة فقط.", "input")


@tpl(S1, 1, "av_abs")
def _av1_abs(r):
    a = r.randint(1, 15)
    return _q(f"ما القيمة المطلقة للعدد {N(-a)}؟ (اكتب الرقم فقط)", a,
              [(-a, "ظن أن القيمة المطلقة للعدد السالب تبقى سالبة")],
              f"القيمة المطلقة {M(f'|-{a}| = {a}')} تمثل المسافة عن الصفر وهي دائماً موجبة.", "المسافة لا يمكن أن تكون سالبة.", "input")


@tpl(S1, 2, "av_abs")
def _av2_abs(r):
    a = r.randint(3, 30)
    x = r.choice([-a, a])
    why = "ظن أن القيمة المطلقة للسالب تبقى سالبة" if x < 0 else "ظن أن القيمة المطلقة تعكس إشارة العدد"
    return _q(f"ما قيمة {M('|' + n(x) + '|')}؟", a,
              [(-a, why), (0, "ظن أن القيمة المطلقة تجعل العدد صفراً"), (a + 10, "خطأ في قراءة العدد")],
              f"{M(f'|{x}| = {a}')} لأن القيمة المطلقة هي البعد عن الصفر.", "ما بُعد العدد عن الصفر؟")


@tpl(S1, 2, "av_abs")
def _av2_dist0(r):
    a = r.randint(2, 25)
    x = r.choice([-a, a])
    return _q(f"كم تبعد النقطة {N(x)} عن الصفر على خط الأعداد؟", a,
              [(-a, "ظن أن المسافة قد تكون سالبة"), (0, "خلط بين الصفر والمسافة"), (2 * a, "جمع العدد مع معكوسه")],
              f"البعد عن الصفر هو القيمة المطلقة، أي {a}.", "عدّ الخطوات من الصفر حتى العدد.")


@tpl(S1, 2, "av_abs_compare")
def _av2_cmp_tf(r):
    a, b = r.randint(1, 12), r.randint(1, 12)
    x, y = r.choice([-a, a]), r.choice([-b, b])
    word, truth = r.choice([("أصغر من", abs(x) < abs(y)), ("أكبر من", abs(x) > abs(y))])
    return _tf(f"القيمة المطلقة للعدد {N(x)} {word} القيمة المطلقة للعدد {N(y)}.", truth,
               "قارن الأعداد بإشاراتها بدل قيمها المطلقة",
               f"{M(f'|{x}| = {abs(x)}')} و {M(f'|{y}| = {abs(y)}')}.", "احسب القيمة المطلقة لكل عدد أولاً.")


@tpl(S1, 2, "av_abs_compare")
def _av2_maxabs(r):
    for _ in range(80):
        vals = r.sample(range(1, 15), 4)
        nums = [v * r.choice([-1, 1]) for v in vals]
        big = max(nums, key=abs)
        if big < 0 and max(nums) != big:
            break
    wrong = [(max(nums), "اختار أكبر عدد وليس أكبر قيمة مطلقة")] + \
            [(x, "لم يقارن بُعد الأعداد عن الصفر") for x in nums if x not in (big, max(nums))]
    return _q("أي الأعداد التالية له أكبر قيمة مطلقة؟  " + M(", ".join(n(x) for x in nums)), big, wrong,
              f"القيم المطلقة: {M(', '.join(str(abs(x)) for x in nums))}. الأكبر هو {abs(big)} وهو للعدد {N(big)}.",
              "احذف الإشارات وقارن الأرقام.")


@tpl(S1, 2, "av_abs_expr")
def _av2_expr(r):
    a = r.randint(2, 15)
    b = r.choice([x for x in range(-15, 16) if x != 0])
    ans = a + abs(b)
    return _q(f"أوجد قيمة: {M('|' + n(-a) + '| + |' + n(b) + '|')}  (اكتب الجواب)", ans,
              [(-a + b, "أهمل رمز القيمة المطلقة"), (-ans, "جعل الناتج سالباً"), (a - abs(b), "طرح بدل الجمع")],
              f"{M(f'|{-a}| + |{b}| = {a} + {abs(b)} = {ans}')}.", "احسب كل قيمة مطلقة أولاً.", "input")


@tpl(S1, 2, "av_abs_expr")
def _av2_diffexpr(r):
    a, b = r.sample(range(2, 15), 2)
    return _q(f"ما ناتج {M('|' + n(-a) + '| − |' + n(-b) + '|')}؟", a - b,
              [(b - a, "أهمل القيمة المطلقة"), (a + b, "جمع بدل الطرح"), (-(a + b), "أهمل القيمة المطلقة وجمع")],
              f"{M(f'|{-a}| - |{-b}| = {a} - {b} = {a - b}')}.", "القيمة المطلقة أولاً ثم الطرح.")


CTX_VERT = [
    ("يحلّق طائر على ارتفاع {a} م فوق سطح البحر", "وتسبح سمكة على عمق {b} م تحت سطح البحر"),
    ("تطير طائرة على ارتفاع {a} م فوق سطح البحر", "وتبحر غواصة على عمق {b} م تحت سطح البحر"),
    ("يقف متسلق على ارتفاع {a} م فوق سطح البحر", "ويغوص غواص على عمق {b} م تحت سطح البحر"),
]


@tpl(S1, 3, "av_distance")
def _av3_vert(r):
    a, b = r.sample(range(3, 21), 2)
    up, down = r.choice(CTX_VERT)
    return _q(f"{up.format(a=a)}، {down.format(b=b)}. ما المسافة الرأسية بينهما بالأمتار؟", a + b,
              [(abs(a - b), "طرح بدلاً من جمع القيمتين المطلقتين"), (a, "ارتفاع الأول فقط"), (b, "عمق الثاني فقط")],
              f"هما على جهتين مختلفتين من سطح البحر: {M(f'|{a}| + |{-b}| = {a + b}')} متراً.", "اجمع بُعد كل منهما عن الصفر.")


@tpl(S1, 3, "av_distance")
def _av3_same(r):
    a, b = r.sample(range(2, 20), 2)
    A, B = (-a, -b) if r.random() < 0.5 else (a, b)
    d = abs(a - b)
    return _q(f"على خط الأعداد، النقطة س عند {N(A)} والنقطة ص عند {N(B)}. ما المسافة بينهما؟", d,
              [(a + b, "جمع القيمتين المطلقتين رغم أنهما على جهة واحدة"), (-d, "جعل المسافة سالبة"), (A + B, "جمع العددين")],
              f"العددان على الجهة نفسها من الصفر، فنطرح الأصغر من الأكبر: {M(f'{max(a, b)} - {min(a, b)} = {d}')}.",
              "على جهة واحدة: اطرح. على جهتين: اجمع.")


@tpl(S1, 3, "av_distance")
def _av3_opp(r):
    a, b = r.randint(2, 20), r.randint(2, 20)
    A, B = (-a, b) if r.random() < 0.5 else (a, -b)
    return _q(f"على خط الأعداد، أوجد المسافة بين النقطتين {N(A)} و {N(B)}. (اكتب الرقم فقط)", a + b,
              [(abs(a - b), "طرح القيمتين المطلقتين"), (A + B, "جمع العددين بإشارتيهما")],
              f"النقطتان على جهتين مختلفتين من الصفر: {M(f'{a} + {b} = {a + b}')}.", "كم خطوة من الأولى إلى الصفر ثم إلى الثانية؟", "input")


@tpl(S1, 3, "av_abs_compare")
def _av3_farther(r):
    a, b = r.sample(range(1, 16), 2)
    truth = a > b
    return _tf(f"العدد {N(-a)} أبعد عن الصفر من العدد {N(b)}.", truth,
               "قارن العددين بإشارتيهما بدل بُعدهما عن الصفر",
               f"بُعد {N(-a)} عن الصفر هو {a} وبُعد {N(b)} هو {b}، و{a} {'أكبر' if a > b else 'ليس أكبر'} من {b}.",
               "البعد عن الصفر = القيمة المطلقة.")


@tpl(S1, 3, "av_solve_abs")
def _av3_solve(r):
    a = r.randint(2, 15)
    return _q(f"ما قيم x التي تحقق {M('|x| = ' + str(a))}؟", f"{a} ,  {n(-a)}",
              [(f"{a} فقط", "نسي أن x قد تكون سالبة"), (f"{n(-a)} فقط", "نسي أن x قد تكون موجبة"), (f"0 ,  {a}", "خلط بين القيمة المطلقة والصفر")],
              f"العددان اللذان يبعدان {a} عن الصفر هما {M(f'{a} , -{a}')}.", "أي عددين يبعدان المسافة نفسها عن الصفر؟")


@tpl(S1, 3, "av_abs_compare")
def _av3_city(r):
    a = r.randint(6, 20)
    b = r.randint(1, a - 3)
    return _q(f"درجة الحرارة في المدينة الأولى {deg(-a)} وفي المدينة الثانية {deg(b)}. أي المدينتين درجة حرارتها أبعد عن الصفر؟",
              "المدينة الأولى",
              [("المدينة الثانية", "قارن العددين بإشارتيهما (الأكبر عدداً)"), ("متساويتان في البعد", "ظن أن الإشارة لا تغيّر البعد")],
              f"{M(f'|{-a}| = {a}')} أكبر من {M(f'|{b}| = {b}')}، فالأولى أبعد عن الصفر.", "قارن القيمتين المطلقتين.")


# =====================================================================================
# LESSON 2  -  comparing_integers   (comparing, ordering, integers between two numbers)
# =====================================================================================
S2 = "comparing_integers"
SYMS = [(">", "أكبر من"), ("<", "أصغر من"), ("=", "يساوي")]


def _symbol_q(a, b, why_map, explain, hint):
    """Ask for the right comparison symbol between a and b."""
    correct = ">" if a > b else "<" if a < b else "="
    wrong = [(s, why_map.get(s, "خطأ في المقارنة")) for s, _ in SYMS if s != correct]
    return _q(f"اختر الرمز المناسب:  {M(f'{n(a)}  ▢  {n(b)}')}", correct, wrong, explain, hint)


@tpl(S2, 1, "ci_sign")
def _ci1_symbol(r):
    a, b = r.randint(-12, -1), r.randint(0, 9)
    if r.random() < 0.5:
        a, b = b, a
    return _symbol_q(a, b, {(">" if a < b else "<"): "قارن الأرقام وتجاهل الإشارة"},
                     f"{M(f'{n(max(a, b))} > {n(min(a, b))}')}: العدد الموجب (أو الصفر) أكبر من أي عدد سالب.", "أين يقع كل عدد على خط الأعداد؟")


@tpl(S2, 1, "ci_sign")
def _ci1_tf(r):
    a, b = r.randint(1, 15), r.randint(1, 9)
    kind = r.choice(["zero_gt", "neg_gt_pos", "neg_lt_zero", "pos_gt_neg", "neg_gt_zero"])
    if kind == "zero_gt":
        return _tf("الصفر أكبر من أي عدد سالب.", True, "ظن أن الصفر أصغر من السالب", "الأعداد السالبة تقع يسار الصفر، فهي أصغر منه.", "ارسم خط الأعداد.")
    if kind == "neg_gt_pos":
        return _tf(f"العدد {N(-a)} أكبر من العدد {N(b)}.", False, "قارن الأرقام وتجاهل الإشارة", f"{N(b)} موجب و{N(-a)} سالب، والموجب أكبر دائماً.", "الموجب أكبر من السالب.")
    if kind == "neg_lt_zero":
        return _tf(f"{M(f'{-a} < 0')}", True, "ظن أن العدد السالب أكبر من الصفر", f"{N(-a)} يقع يسار الصفر فهو أصغر منه.", "اليسار أصغر.")
    if kind == "pos_gt_neg":
        return _tf(f"{M(f'{b} > {-a}')}", True, "قارن الأرقام وتجاهل الإشارة", f"{N(b)} موجب و{N(-a)} سالب.", "الموجب أكبر من السالب.")
    return _tf(f"أي عدد سالب أكبر من الصفر.", False, "خلط بين قيمة العدد وقيمته المطلقة", "الأعداد السالبة أصغر من الصفر.", "أين يقع السالب من الصفر؟")


@tpl(S2, 1, "ci_sign")
def _ci1_smallest(r):
    neg = -r.randint(1, 12)
    pos = r.sample(range(0, 12), 3)
    nums = pos + [neg]
    r.shuffle(nums)
    return _q("أي الأعداد التالية هو الأصغر؟  " + M(", ".join(n(x) for x in nums)), neg,
              [(x, "اختار العدد الأصغر بالرقم وتجاهل الإشارة") for x in pos],
              f"العدد السالب {N(neg)} أصغر من جميع الأعداد الموجبة والصفر.", "أين يقع السالب؟")


@tpl(S2, 1, "ci_neg")
def _ci1_largest_neg(r):
    return _q("ما أكبر عدد صحيح سالب؟ (اكتب العدد)", -1,
              [(0, "ظن أن الصفر عدد سالب"), (-10, "ظن أن الأكبر رقماً هو الأكبر"), (-100, "ظن أن الأكبر رقماً هو الأكبر")],
              f"أقرب عدد سالب إلى الصفر هو {N(-1)}، فهو الأكبر بين السالبة.", "الأكبر هو الأقرب إلى الصفر.", "input")


@tpl(S2, 1, "ci_sign")
def _ci1_warm(r):
    a, b = r.randint(2, 15), r.randint(1, 20)
    return _q(f"درجة الحرارة في مدينة (أ) {deg(-a)} وفي مدينة (ب) {deg(b)}. أي المدينتين أدفأ؟", "مدينة (ب)",
              [("مدينة (أ)", "قارن الأرقام وتجاهل الإشارة"), ("متساويتان", "ظن أن الإشارة لا تؤثر")],
              f"{N(b)} موجبة و{N(-a)} تحت الصفر، فالمدينة (ب) أدفأ.", "الموجب أدفأ من السالب.")


@tpl(S2, 2, "ci_neg")
def _ci2_max_input(r):
    a, b = r.sample(range(1, 30), 2)
    return _q(f"اكتب العدد الأكبر من العددين:  {N(-a)}  و  {N(-b)}", -min(a, b),
              [(-max(a, b), "قارن الأرقام كأن الإشارة غير موجودة")],
              f"الأقرب إلى الصفر هو الأكبر: {M(f'{-min(a, b)} > {-max(a, b)}')}.", "الأكبر هو الأقرب إلى الصفر.", "input")


@tpl(S2, 2, "ci_neg")
def _ci2_symbol(r):
    a, b = r.sample(range(-30, -1), 2)
    return _symbol_q(a, b, {(">" if a < b else "<"): "قارن الأرقام كأن الإشارة غير موجودة"},
                     f"{M(f'{n(max(a, b))} > {n(min(a, b))}')}: الأقرب إلى الصفر هو الأكبر.", "تخيّل ميزان الحرارة.")


@tpl(S2, 2, "ci_neg")
def _ci2_tf(r):
    a, b = r.sample(range(1, 30), 2)
    word = r.choice([">", "<"])
    x, y = -a, -b
    truth = x > y if word == ">" else x < y
    return _tf(M(f"{x} {word} {y}"), truth, "قارن الأرقام كأن الإشارة غير موجودة",
               f"بين عددين سالبين الأكبر هو الأقرب للصفر، فالأكبر هو {N(max(x, y))}.", "فكّر بميزان الحرارة.")


@tpl(S2, 2, "ci_neg")
def _ci2_smallest(r):
    vals = r.sample(range(1, 25), 4)
    nums = [-v for v in vals]
    small = min(nums)
    return _q("أي الأعداد التالية هو الأصغر؟  " + M(", ".join(n(x) for x in nums)), small,
              [(max(nums), "اختار الأقرب إلى الصفر ظناً أنه الأصغر")] + [(x, "لم يقارن بُعد السالب عن الصفر") for x in nums if x not in (small, max(nums))],
              f"بين السالبة الأصغر هو الأبعد عن الصفر، أي {N(small)}.", "الأبعد عن الصفر جهة اليسار هو الأصغر.")


@tpl(S2, 2, "ci_neg")
def _ci2_context(r):
    a, b = r.sample(range(5, 60), 2)
    up = "الثانية" if a > b else "الأولى"
    return _q(f"غواصة أولى على عمق {a} م تحت سطح البحر وغواصة ثانية على عمق {b} م. أي الغواصتين أعلى (أقرب إلى سطح البحر)؟",
              f"الغواصة {up}",
              [(f"الغواصة {'الأولى' if up == 'الثانية' else 'الثانية'}", "ظن أن الرقم الأكبر يعني الأعلى"), ("على المستوى نفسه", "لم يقارن العمقين")],
              f"الارتفاعان {N(-a)} و{N(-b)}، والأكبر هو الأقرب للصفر، أي {N(-min(a, b))}.", "العمق الأقل يعني أقرب إلى السطح.")


@tpl(S2, 2, "ci_between")
def _ci2_between(r):
    b = r.randint(6, 20)
    a = r.randint(1, b - 4)          # -b < ... < -a
    inside = r.randint(-b + 1, -a - 1)
    wrong = [(-b - 1, "اختار عدداً خارج الفترة (أصغر من الحد الأدنى)"), (-a + 1, "اختار عدداً خارج الفترة (أكبر من الحد الأعلى)"), (-b, "اختار أحد العددين نفسه")]
    return _q(f"أي عدد يقع بين {N(-b)} و {N(-a)}؟", inside, wrong,
              f"{M(f'{-b} < {inside} < {-a}')}.", "ارسم خط الأعداد وحدّد الفترة.")


@tpl(S2, 3, "ci_order")
def _ci3_desc(r):
    nums = r.sample(range(-9, 10), 4)
    correct = sorted(nums, reverse=True)
    pos = [x for x in correct if x >= 0]
    neg = [x for x in correct if x < 0]
    mis = pos + sorted(neg)                      # negatives ordered by their digits
    byabs = sorted(nums, key=abs, reverse=True)
    lst = lambda xs: ", ".join(n(x) for x in xs)
    return _q("رتّب الأعداد تنازلياً (من الأكبر إلى الأصغر):  " + M(lst(nums)), lst(correct),
              [(lst(sorted(nums)), "رتّبها تصاعدياً بدل تنازلياً"), (lst(mis), "رتّب السالبة كما لو كانت موجبة"), (lst(byabs), "رتّبها حسب القيمة المطلقة")],
              f"التنازلي: {M(lst(correct))}.", "ابدأ بالموجبة ثم الصفر ثم السالبة (الأقرب للصفر أولاً).")


@tpl(S2, 3, "ci_order")
def _ci3_asc(r):
    nums = r.sample(range(-9, 10), 4)
    correct = sorted(nums)
    pos = [x for x in correct if x >= 0]
    neg = [x for x in correct if x < 0]
    mis = sorted(neg, reverse=True) + pos        # negatives ordered by their digits
    lst = lambda xs: ", ".join(n(x) for x in xs)
    return _q("رتّب الأعداد تصاعدياً (من الأصغر إلى الأكبر):  " + M(lst(nums)), lst(correct),
              [(lst(sorted(nums, reverse=True)), "رتّبها تنازلياً بدل تصاعدياً"), (lst(mis), "رتّب السالبة كما لو كانت موجبة"), (lst(sorted(nums, key=abs)), "رتّبها حسب القيمة المطلقة")],
              f"التصاعدي: {M(lst(correct))}.", "الأصغر هو أبعد سالب عن الصفر.")


@tpl(S2, 3, "ci_order")
def _ci3_tf(r):
    nums = r.sample(range(-9, 10), 4)
    asc = r.random() < 0.5
    right = sorted(nums, reverse=not asc)
    shown = right if r.random() < 0.5 else (sorted(nums, reverse=asc) if r.random() < 0.5 else sorted(nums, key=abs, reverse=not asc))
    truth = shown == right
    lst = ", ".join(n(x) for x in shown)
    return _tf(f"الترتيب  {M(lst)}  هو ترتيب {'تصاعدي' if asc else 'تنازلي'}.", truth,
               "لم يرتّب الأعداد على خط الأعداد",
               f"الترتيب {'التصاعدي' if asc else 'التنازلي'} الصحيح هو {M(', '.join(n(x) for x in right))}.", "ارسم الأعداد على خط الأعداد.")


@tpl(S2, 3, "ci_between")
def _ci3_between(r):
    a, b = r.randint(3, 12), r.randint(3, 12)
    ins = r.randint(-a + 1, b - 1)
    return _q(f"أي عدد صحيح يقع بين {N(-a)} و {N(b)}؟", ins,
              [(-a - 1, "اختار عدداً أصغر من الحد الأدنى"), (b + 1, "اختار عدداً أكبر من الحد الأعلى"), (b, "اختار أحد العددين نفسه")],
              f"{M(f'{-a} < {ins} < {b}')}.", "العددان نفسهما لا يُحسبان.")


@tpl(S2, 3, "ci_between")
def _ci3_count(r):
    a, b = r.randint(2, 9), r.randint(2, 9)
    c = a + b - 1
    return _q(f"كم عدداً صحيحاً يقع بين {N(-a)} و {N(b)} (دون العددين نفسيهما)؟ (اكتب الرقم)", c,
              [(a + b, "عدّ الفرق بين العددين لا الأعداد بينهما"), (a + b + 1, "عدّ العددين نفسيهما"), (a + b - 2, "نسي الصفر")],
              f"من {N(-a + 1)} إلى {N(b - 1)}، وعددها {M(f'{a} + {b} - 1 = {c}')} (بما فيها الصفر).", "اكتب الأعداد الواقعة بينهما واحداً واحداً.", "input")


@tpl(S2, 3, "ci_order")
def _ci3_temps(r):
    nums = r.sample(range(-15, 20), 4)
    correct = sorted(nums)
    lst = lambda xs: ", ".join(n(x) for x in xs)
    return _q(f"درجات الحرارة في أربع مدن ({', '.join(str(x) for x in ['أ','ب','جـ','د'])}) هي " + M(lst(nums)) + " على الترتيب. رتّبها من الأبرد إلى الأدفأ:",
              lst(correct),
              [(lst(sorted(nums, reverse=True)), "رتّبها من الأدفأ إلى الأبرد"), (lst(sorted(nums, key=abs)), "رتّبها حسب القيمة المطلقة"), (lst(sorted(nums, key=abs, reverse=True)), "رتّبها حسب القيمة المطلقة")],
              f"من الأبرد إلى الأدفأ يعني تصاعدياً: {M(lst(correct))}.", "الأبرد هو الأصغر.")


# =====================================================================================
# LESSON 3  -  adding_integers
# =====================================================================================
S3 = "adding_integers"


def _sum_wrongs_diff(p, q_):
    """p > 0 and -q_ < 0 : common wrong sums for p + (-q_)."""
    t = p - q_
    return [(p + q_, "جمع القيمتين المطلقتين وتجاهل الإشارة"), (-t, "وضع إشارة العدد الأصغر بدل الأكبر"), (-(p + q_), "جمع القيمتين المطلقتين مع إشارة سالبة")]


@tpl(S3, 1, "ai_same")
def _ai1_input(r):
    a, b = r.randint(1, 12), r.randint(1, 12)
    return _q(f"أوجد ناتج: {add(-a, -b)}  (اكتب الرقم مع الإشارة)", -(a + b),
              [(a + b, "أهمل الإشارة السالبة"), (a - b, "طرح القيمتين بدل جمعهما"), (b - a, "طرح القيمتين بدل جمعهما")],
              f"عددان سالبان: نجمع القيمتين المطلقتين {M(f'{a} + {b} = {a + b}')} ونضع الإشارة السالبة، فالناتج {N(-(a + b))}.", "خسارة زائد خسارة.", "input")


@tpl(S3, 1, "ai_same")
def _ai1_mcq(r):
    a, b = r.randint(1, 14), r.randint(1, 14)
    return _q(f"ما ناتج {add(-a, -b)}؟", -(a + b),
              [(a + b, "أهمل الإشارة السالبة"), (a - b, "طرح القيمتين بدل جمعهما"), (b - a, "طرح القيمتين بدل جمعهما")],
              f"{M(f'{-a} + ({-b}) = {-(a + b)}')}: نجمع القيمتين ونُبقي الإشارة السالبة.", "الاتجاه نفسه: يسار ثم يسار.")


@tpl(S3, 1, "ai_zero")
def _ai1_zero(r):
    a = r.randint(2, 20)
    x = r.choice([a, -a])
    return _q(f"ما ناتج {add(x, -x)}؟", 0,
              [(2 * abs(x), "جمع القيمتين المطلقتين"), (-2 * abs(x), "جمع القيمتين المطلقتين مع إشارة سالبة"), (x, "ظن أن الناتج هو العدد نفسه")],
              f"العدد ومعكوسه مجموعهما صفر: {M(f'{x} + ({-x}) = 0')}.", "هل العددان متقابلان؟")


@tpl(S3, 1, "ai_same")
def _ai1_tf(r):
    if r.random() < 0.5:
        return _tf("مجموع عددين سالبين يكون دائماً سالباً.", True, "ظن أن الجمع يعطي دائماً ناتجاً موجباً", "جمع سالب مع سالب يعني الابتعاد أكثر نحو اليسار.", "أين تقع الأعداد السالبة؟")
    return _tf("مجموع عددين سالبين قد يكون موجباً.", False, "ظن أن الجمع يعطي دائماً ناتجاً موجباً", "جمع سالب مع سالب يعطي دائماً ناتجاً سالباً.", "أين تقع الأعداد السالبة؟")


@tpl(S3, 1, "ai_line")
def _ai1_line(r):
    s = r.choice([x for x in range(-9, 10) if x != 0])
    k, right = r.randint(2, 9), r.random() < 0.5
    correct = s + (k if right else -k)
    return _q(f"تقف عند {N(s)} على خط الأعداد ثم تتحرك {k} خطوات إلى {'اليمين' if right else 'اليسار'}. عند أي عدد تصبح؟", correct,
              [(s + (-k if right else k), "عكس اتجاه الحركة"), (abs(s) + k, "جمع القيم المطلقة"), (-correct, "أخطأ في إشارة الناتج")],
              f"{M(f'{s} {chr(43) if right else chr(45)} {k} = {correct}')}.", "اليمين يزيد واليسار ينقص.")


@tpl(S3, 2, "ai_diff")
def _ai2_mcq(r):
    p, q_ = r.randint(2, 18), r.randint(2, 18)
    while p == q_:
        q_ = r.randint(2, 18)
    x, y = (p, -q_) if r.random() < 0.5 else (-q_, p)
    t = p - q_
    return _q(f"أوجد ناتج: {add(x, y)}", t, _sum_wrongs_diff(p, q_),
              f"القيمتان المطلقتان {p} و{q_}؛ نطرح الأصغر من الأكبر فنحصل على {abs(t)} ونأخذ إشارة {'الموجب' if t > 0 else 'السالب'} (الأكبر قيمة مطلقة): {N(t)}.",
              "طرح القيمتين المطلقتين وإشارة الأكبر.")


@tpl(S3, 2, "ai_diff")
def _ai2_input(r):
    a, b = r.randint(2, 20), r.randint(2, 20)
    while a == b:
        b = r.randint(2, 20)
    x, y = (-a, b) if r.random() < 0.5 else (a, -b)
    t = x + y
    return _q(f"أوجد ناتج: {add(x, y)}  (اكتب الرقم مع الإشارة)", t,
              [(abs(x) + abs(y), "جمع القيمتين المطلقتين"), (-t, "وضع إشارة العدد الأصغر"), (x - y, "طرح بدل الجمع")],
              f"{M(f'{x} + ({y}) = {t}')}.", "أيهما أكبر قيمة مطلقة؟", "input")


@tpl(S3, 2, "ai_diff")
def _ai2_tf(r):
    a, b = r.randint(2, 15), r.randint(2, 15)
    while a == b:
        b = r.randint(2, 15)
    x, y = (-a, b) if r.random() < 0.5 else (a, -b)
    t = x + y
    claim = t if r.random() < 0.5 else r.choice([-t, abs(x) + abs(y)])
    return _tf(f"{M(f'{x} + ({y}) = {claim}')}", claim == t, "جمع القيمتين أو إشارة الناتج خاطئة",
               f"الناتج الصحيح {N(t)}: نطرح {min(a, b)} من {max(a, b)} ونأخذ إشارة العدد الأكبر قيمة مطلقة.", "احسب الناتج بنفسك أولاً.")


@tpl(S3, 2, "ai_diff")
def _ai2_sign(r):
    a, b = r.randint(2, 15), r.randint(2, 15)
    while a == b:
        b = r.randint(2, 15)
    x, y = (-a, b) if r.random() < 0.5 else (a, -b)
    t = x + y
    word = "موجبة" if t > 0 else "سالبة"
    return _q(f"ما إشارة ناتج {add(x, y)}؟", word,
              [("سالبة" if t > 0 else "موجبة", "أخذ إشارة العدد الأصغر قيمة مطلقة"), ("صفر", "ظن أن العددين يلغيان بعضهما")],
              f"القيمة المطلقة الأكبر هي {max(a, b)} وهي للعدد {N(x if abs(x) > abs(y) else y)}، فالناتج {word}.", "إشارة الناتج = إشارة الأكبر قيمة مطلقة.")


@tpl(S3, 2, "ai_zero")
def _ai2_zero_pick(r):
    a = r.randint(3, 15)
    opts = [(add(a, -a), True), (add(a, a), False), (add(-a, -a), False), (add(a, -(a - 1)), False)]
    correct = opts[0][0]
    return _q("أي العبارات التالية ناتجها صفر؟", correct,
              [(o, "لم يتحقق من أن العددين متقابلان") for o, _ in opts[1:]],
              f"العبارة {correct} فيها عددان متقابلان (كل منهما معكوس الآخر).", "ابحث عن عددين متقابلين.")


@tpl(S3, 2, "ai_context")
def _ai2_money(r):
    a, b = r.randint(11, 30), r.randint(31, 60)
    t = a - b
    return _q(f"كان في حساب سعد {a} ديناراً، ثم سحب منه {b} ديناراً (سمح له البنك بالسحب على المكشوف). ما رصيده الآن؟", t,
              [(b - a, "أخطأ في إشارة الرصيد"), (a + b, "جمع المبلغين"), (-(a + b), "جمع المبلغين مع إشارة سالبة")],
              f"{M(f'{a} + ({-b}) = {t}')}. الرصيد سالب لأن ما سحبه أكبر مما لديه.", "السحب يُمثَّل بعدد سالب.")


@tpl(S3, 3, "ai_context")
def _ai3_dive(r):
    a, b = r.randint(4, 15), r.randint(2, 10)
    while b >= a:
        b = r.randint(2, 10)
    truth = r.random() < 0.5
    claim = -(a - b) if truth else -(a + b)
    return _tf(f"غاصت فرح {a} م تحت سطح البحر ({N(-a)}) ثم صعدت {b} م ({N(b)}). عمقها الآن {N(claim)} م.", truth,
               "جمع القيمتين المطلقتين بدل الجمع بإشارتيهما",
               f"{M(f'{-a} + {b} = {-a + b}')}، أي {N(-(a - b))} م.", "اجمع الموقع الأول مع التغيير.")


@tpl(S3, 3, "ai_context")
def _ai3_temp(r):
    a, b = r.randint(3, 12), r.randint(3, 10)
    while a == b:
        b = r.randint(3, 10)
    t = -a + b
    return _q(f"كانت درجة الحرارة {deg(-a)} ثم ارتفعت {b} درجات. ما درجة الحرارة الآن؟", t,
              [(-(a + b), "عكس اتجاه التغيير (نزل بدل أن يرتفع)"), (a + b, "جمع القيمتين المطلقتين"), (-t, "أخطأ في إشارة الناتج")],
              f"{M(f'{-a} + {b} = {t}')}.", "الارتفاع يعني جمع عدد موجب.")


@tpl(S3, 3, "ai_multi")
def _ai3_three(r):
    a, b, c = r.randint(2, 12), r.randint(2, 12), r.randint(2, 12)
    x, y, z = a, -b, c
    t = x + y + z
    return _q(f"أوجد ناتج: {E(n(x), '+', par(y), '+', par(z))}", t,
              [(x + abs(y) + z, "جمع القيم المطلقة كلها"), (x - y - z, "غيّر إشارات أعداد لا يجب تغييرها"), (-t, "أخطأ في إشارة الناتج")],
              f"{M(f'{x} + ({y}) + {z} = {x + z} + ({y}) = {t}')}.", "اجمع الموجبة معاً ثم أضف السالب.")


@tpl(S3, 3, "ai_missing")
def _ai3_missing(r):
    x = r.randint(2, 15)
    b = r.randint(2, 15)
    t = x - b
    return _q(f"أوجد العدد المجهول: {M(f'x + ({-b}) = {t}')}  (اكتب العدد)", x,
              [(t - b, "جمع بدل استخدام المعكوس"), (t + (-b) * -1 * -1, "أخطأ في الإشارة"), (-x, "أخطأ في إشارة الجواب")],
              f"نضيف {b} للطرفين: {M(f'x = {t} + {b} = {x}')}.", "ما العدد الذي إذا أضفنا إليه السالب حصلنا على الناتج؟", "input")


@tpl(S3, 3, "ai_context")
def _ai3_game(r):
    a, b, c = r.randint(21, 40), r.randint(11, 20), r.randint(11, 20)
    t = a - b - c
    return _q(f"في لعبة، ربح فريق {a} نقطة ثم خسر {b} نقطة ثم خسر {c} نقطة. ما مجموع نقاطه؟", t,
              [(a + b + c, "جمع الخسارتين مع الربح"), (-(a + b + c), "جعل كل النقاط سالبة"), (a - b + c, "اعتبر إحدى الخسارتين ربحاً")],
              f"{M(f'{a} + ({-b}) + ({-c}) = {t}')}.", "الخسارة تُمثَّل بعدد سالب.")


@tpl(S3, 3, "ai_context")
def _ai3_lift(r):
    a, b = r.randint(2, 6), r.randint(1, 8)
    while b == a:
        b = r.randint(1, 8)
    t = -a + b
    return _q(f"تقف سيارة في الطابق {N(-a)} (موقف تحت الأرض)، ثم صعد بها المصعد بمقدار {b} طابق. في أي طابق تصبح؟", t,
              [(-(a + b), "تحرك نحو الأسفل بدل الأعلى"), (a + b, "جمع القيمتين المطلقتين"), (-t, "أخطأ في إشارة الناتج")],
              f"{M(f'{-a} + {b} = {t}')}.", "الصعود يزيد العدد.")


# =====================================================================================
# LESSON 4  -  subtracting_integers
# =====================================================================================
S4 = "subtracting_integers"


@tpl(S4, 1, "si_pos")
def _si1_input(r):
    a, b = r.randint(1, 12), r.randint(1, 12)
    return _q(f"أوجد ناتج: {sub(-a, b)}  (اكتب الجواب)", -(a + b),
              [(a - b, "طرح القيمتين المطلقتين"), (a + b, "أهمل الإشارة السالبة"), (b - a, "طرح بالعكس")],
              f"{M(f'{-a} - {b} = {-a} + ({-b}) = {-(a + b)}')}.", "خسارة متبوعة بخسارة.", "input")


@tpl(S4, 1, "si_rule")
def _si1_convert(r):
    a, b = r.randint(2, 12), r.randint(2, 12)
    x = r.choice([a, -a])
    return _q(f"حوّل الطرح إلى جمع: {sub(x, b)}", add(x, -b),
              [(add(x, b), "لم يعكس إشارة العدد الثاني"), (add(-x, -b), "عكس إشارة العدد الأول"), (add(-x, b), "عكس الإشارتين")],
              f"نثبّت الأول ونعكس الثاني: {M(f'{x} - {b} = {x} + ({-b})')}.", "ثبّت، غيّر، اعكس.")


@tpl(S4, 1, "si_order")
def _si1_small_big(r):
    a = r.randint(1, 9)
    b = r.randint(a + 1, 15)
    return _q(f"ما ناتج {sub(a, b)}؟", a - b,
              [(b - a, "عكس ترتيب العددين"), (a + b, "جمع بدل الطرح"), (-(a + b), "جمع بدل الطرح مع إشارة سالبة")],
              f"{M(f'{a} - {b} = {a} + ({-b}) = {a - b}')}: المطروح أكبر من المطروح منه فالناتج سالب.", "أيهما أكبر: المطروح أم المطروح منه؟")


@tpl(S4, 1, "si_order")
def _si1_tf(r):
    a = r.randint(1, 9)
    b = r.randint(a + 1, 15)
    claim = (a - b) if r.random() < 0.5 else (b - a)
    return _tf(f"{M(f'{a} - {b} = {claim}')}", claim == a - b, "عكس ترتيب الطرح",
               f"الناتج الصحيح {N(a - b)} لأن {b} أكبر من {a}.", "أيهما أكبر؟")


@tpl(S4, 1, "si_pos")
def _si1_neg_mcq(r):
    a, b = r.randint(2, 14), r.randint(2, 14)
    return _q(f"ما ناتج {sub(-a, b)}؟", -(a + b),
              [(a + b, "أهمل الإشارة السالبة"), (b - a, "طرح القيمتين المطلقتين"), (a - b, "طرح القيمتين المطلقتين")],
              f"{M(f'{-a} - {b} = {-a} + ({-b}) = {-(a + b)}')}.", "حوّل الطرح إلى جمع سالب.")


@tpl(S4, 1, "si_rule")
def _si1_zero(r):
    a = r.randint(2, 20)
    return _q(f"ما ناتج {sub(0, a)}؟", -a,
              [(a, "ظن أن الطرح من الصفر لا يغيّر الإشارة"), (0, "ظن أن الناتج صفر"), (-a - 1, "خطأ في العدّ")],
              f"{M(f'0 - {a} = 0 + ({-a}) = {-a}')}.", "الطرح هو جمع المعكوس.")


@tpl(S4, 2, "si_neg")
def _si2_pos_neg(r):
    a, b = r.randint(2, 14), r.randint(2, 14)
    return _q(f"أوجد ناتج: {sub(a, -b)}", a + b,
              [(a - b, "طرح القيمتين بدل جمعهما"), (b - a, "طرح بالعكس"), (-(a + b), "أخطأ في الإشارة")],
              f"ناقص الناقص زائد: {M(f'{a} - ({-b}) = {a} + {b} = {a + b}')}.", "ناقص الناقص يعطي زائد.")


@tpl(S4, 2, "si_neg")
def _si2_neg_neg(r):
    a, b = r.randint(2, 15), r.randint(2, 15)
    while a == b:
        b = r.randint(2, 15)
    t = -a + b
    return _q(f"أوجد ناتج: {sub(-a, -b)}", t,
              [(-(a + b), "لم يقلب إشارة العدد المطروح"), (a + b, "جمع القيمتين المطلقتين"), (-t, "أخطأ في إشارة الناتج")],
              f"{M(f'{-a} - ({-b}) = {-a} + {b} = {t}')}.", "حوّل إلى جمع ثم اجمع بإشارتين مختلفتين.")


@tpl(S4, 2, "si_neg")
def _si2_input(r):
    a, b = r.randint(2, 20), r.randint(2, 20)
    return _q(f"أوجد ناتج: {sub(a, -b)}  (اكتب الرقم)", a + b,
              [(a - b, "طرح بدل الجمع"), (-(a + b), "أخطأ في الإشارة")],
              f"{M(f'{a} - ({-b}) = {a} + {b} = {a + b}')}.", "سالب السالب موجب.", "input")


@tpl(S4, 2, "si_neg")
def _si2_tf(r):
    a, b = r.randint(2, 12), r.randint(2, 12)
    while a == b:
        b = r.randint(2, 12)
    t = -a + b
    claim = t if r.random() < 0.5 else r.choice([-a - b, -t])
    return _tf(f"{M(f'{-a} - ({-b}) = {claim}')}", claim == t, "لم يحوّل طرح السالب إلى جمع موجب",
               f"{M(f'{-a} - ({-b}) = {-a} + {b} = {t}')}.", "ناقص الناقص زائد.")


@tpl(S4, 2, "si_rule")
def _si2_equiv(r):
    a, b = r.randint(2, 12), r.randint(2, 12)
    return _q(f"أي عبارة تساوي {sub(a, -b)}؟", add(a, b),
              [(sub(a, b), "لم يغيّر الطرح إلى جمع"), (add(-a, b), "عكس إشارة العدد الأول"), (add(a, -b), "عكس الإشارة في الاتجاه الخاطئ")],
              f"طرح {N(-b)} يعني جمع {N(b)}.", "ناقص الناقص زائد.")


@tpl(S4, 2, "si_pos")
def _si2_neg_pos_mcq(r):
    a, b = r.randint(2, 12), r.randint(2, 12)
    return _q(f"أي عبارة تساوي {sub(-a, b)}؟", add(-a, -b),
              [(add(-a, b), "لم يعكس إشارة العدد الثاني"), (add(a, -b), "عكس إشارة العدد الأول"), (add(a, b), "عكس الإشارتين")],
              f"نثبّت الأول ونعكس الثاني: {M(f'{-a} - {b} = {-a} + ({-b})')}.", "الطرح هو جمع المعكوس.")


@tpl(S4, 3, "si_diff")
def _si3_temp_tf(r):
    hi, lo = r.randint(5, 30), -r.randint(10, 60)
    diff = hi - lo
    claim = diff if r.random() < 0.5 else hi + lo
    claim = abs(claim)
    return _tf(f"متوسط حرارة الأرض {deg(hi)} ومتوسط حرارة المريخ {deg(lo)}. الفرق بينهما هو {claim} درجة.", claim == diff,
              "طرح القيمتين المطلقتين بدل جمعهما",
              f"{M(f'{hi} - ({lo}) = {hi} + {-lo} = {diff}')}.", "الفرق = الأعلى − الأدنى.")


@tpl(S4, 3, "si_diff")
def _si3_heights(r):
    a, b = r.randint(20, 90), r.randint(5, 40)
    return _q(f"ارتفاع قمة جبل {a} م فوق سطح البحر، وغواصة على عمق {b} م تحت سطح البحر. ما الفرق في الارتفاع بينهما بالأمتار؟", a + b,
              [(a - b, "طرح القيمتين المطلقتين"), (b - a, "عكس ترتيب الطرح"), (-(a + b), "أخطأ في إشارة الناتج")],
              f"{M(f'{a} - ({-b}) = {a} + {b} = {a + b}')} متراً.", "الفرق = الأعلى − الأدنى.")


@tpl(S4, 3, "si_diff")
def _si3_drop(r):
    a, b = r.randint(3, 20), r.randint(3, 20)
    return _q(f"انخفضت درجة الحرارة من {deg(a)} إلى {deg(-b)}. بكم درجة انخفضت؟", a + b,
              [(abs(a - b), "طرح القيمتين المطلقتين"), (-(a + b), "أخطأ في إشارة الجواب (الانخفاض مقدار موجب)"), (a * b, "ضرب بدل الطرح")],
              f"{M(f'{a} - ({-b}) = {a + b}')} درجة.", "الانخفاض = البداية − النهاية.")


@tpl(S4, 3, "si_order")
def _si3_subtract_from(r):
    a, b = r.randint(2, 15), r.randint(2, 15)
    while a == b:
        b = r.randint(2, 15)
    # "subtract x from y"  =  y - x
    return _q(f"اطرح {N(-a)} من {N(-b)}. (اكتب الجواب)", -b + a,
              [(-a + b, "عكس ترتيب الطرح"), (-(a + b), "لم يقلب إشارة العدد المطروح"), (a + b, "جمع القيمتين المطلقتين")],
              f"اطرح x من y تعني {M('y - x')}: {M(f'{-b} - ({-a}) = {-b} + {a} = {a - b}')}.", "اطرح ... من ... : العدد بعد «من» يُكتب أولاً.", "input")


@tpl(S4, 3, "si_neg")
def _si3_debt(r):
    a, b = r.randint(11, 40), r.randint(11, 30)
    return _q(f"رصيد سامي {N(-a)} ديناراً (عليه دين)، وألغى البنك دَيناً مقداره {b} ديناراً من حسابه (يُطرح {N(-b)}). ما رصيده الآن؟", -a + b,
              [(-(a + b), "لم يقلب إشارة الدين الملغى"), (a + b, "جمع القيمتين المطلقتين"), (a - b, "أخطأ في الإشارة")],
              f"{M(f'{-a} - ({-b}) = {-a} + {b} = {-a + b}')}.", "طرح الدين = جمع موجب.")


@tpl(S4, 3, "si_neg")
def _si3_multi(r):
    a, b, c = r.randint(2, 12), r.randint(2, 12), r.randint(2, 12)
    t = a + b - c
    return _q(f"أوجد ناتج: {E(n(a), MINUS, par(-b), MINUS, n(c))}", t,
              [(a - b - c, "لم يقلب إشارة العدد السالب"), (a + b + c, "جمع الأعداد كلها"), (-t, "أخطأ في إشارة الناتج")],
              f"{M(f'{a} - ({-b}) - {c} = {a} + {b} - {c} = {t}')}.", "حوّل كل طرح إلى جمع.")


# =====================================================================================
# LESSON 5  -  mult_div_integers
# =====================================================================================
S5 = "mult_div_integers"


@tpl(S5, 1, "md_sign")
def _md1_tf(r):
    rules = [("ضرب عدد موجب في عدد سالب يعطي ناتجاً سالباً.", True), ("ضرب عدد موجب في عدد سالب يعطي ناتجاً موجباً.", False),
             ("ضرب عددين سالبين يعطي ناتجاً موجباً.", True), ("ضرب عددين سالبين يعطي ناتجاً سالباً.", False),
             ("قسمة عدد سالب على عدد موجب تعطي ناتجاً سالباً.", True), ("قسمة عدد موجب على عدد سالب تعطي ناتجاً موجباً.", False),
             ("ضرب عددين موجبين يعطي ناتجاً موجباً.", True), ("ضرب أي عدد في الصفر يعطي صفراً.", True)]
    text, truth = r.choice(rules)
    return _tf(text, truth, "قاعدة الإشارات غير صحيحة", "الإشارتان المتشابهتان تعطيان ناتجاً موجباً، والمختلفتان تعطيان ناتجاً سالباً.", "متشابهتان موجب، مختلفتان سالب.")


@tpl(S5, 1, "md_mult")
def _md1_pos_neg(r):
    a, b = r.randint(2, 9), r.randint(2, 9)
    x, y = (a, -b) if r.random() < 0.5 else (-a, b)
    return _q(f"أوجد ناتج: {mul(x, y)}", -(a * b),
              [(a * b, "تجاهل قاعدة الإشارات"), (x + y, "جمع بدل الضرب"), (-(a + b), "جمع بدل الضرب مع إشارة سالبة")],
              f"الإشارتان مختلفتان فالناتج سالب: {M(f'{x} × ({y}) = {-(a * b)}')}.","مختلفتان ← سالب.")


@tpl(S5, 1, "md_mult")
def _md1_input(r):
    a, b = r.randint(2, 9), r.randint(2, 9)
    return _q(f"أوجد ناتج: {mul(-a, b)}  (اكتب الجواب)", -(a * b),
              [(a * b, "تجاهل قاعدة الإشارات"), (-a + b, "جمع بدل الضرب")],
              f"{M(f'{-a} × {b} = {-(a * b)}')}: سالب × موجب = سالب.", "اضرب القيمتين ثم حدّد الإشارة.", "input")


@tpl(S5, 1, "md_paren")
def _md1_paren(r):
    a, b = r.randint(2, 9), r.randint(2, 9)
    return _q(f"أوجد ناتج: {M(f'{a}({-b})')}", -(a * b),
              [(a - b, "جمع بدل الضرب عند رؤية الأقواس الملتصقة"), (a * b, "تجاهل قاعدة الإشارات"), (a + (-b) * -1, "غيّر الإشارة وجمع")],
              f"الأقواس الملتصقة تعني ضرباً: {M(f'{a} × ({-b}) = {-(a * b)}')}.", "القوس الملتصق = ضرب.")


@tpl(S5, 1, "md_div")
def _md1_div(r):
    a, b = r.randint(2, 9), r.randint(2, 9)
    return _q(f"ما ناتج {div(-(a * b), b)}؟", -a,
              [(a, "تجاهل الإشارة السالبة"), (-(a * b) - b, "طرح بدل القسمة"), (-b, "قسم على العدد الخطأ")],
              f"{M(f'{-(a * b)} ÷ {b} = {-a}')}: مختلفتان ← سالب.", "اقسم القيمتين ثم حدّد الإشارة.")


@tpl(S5, 1, "md_sign")
def _md1_sign_only(r):
    a, b = r.randint(2, 9), r.randint(2, 9)
    x, y = r.choice([(a, -b), (-a, b), (-a, -b), (a, b)])
    word = "موجبة" if (x > 0) == (y > 0) else "سالبة"
    return _q(f"ما إشارة ناتج {mul(x, y)} (دون حساب القيمة)؟", word,
              [("سالبة" if word == "موجبة" else "موجبة", "طبّق قاعدة الإشارات معكوسة"), ("صفر", "ظن أن الناتج صفر")],
              f"الإشارتان {'متشابهتان' if word == 'موجبة' else 'مختلفتان'} فالناتج {word}.", "متشابهتان موجب، مختلفتان سالب.")


@tpl(S5, 2, "md_mult")
def _md2_negneg(r):
    a, b = r.randint(2, 9), r.randint(2, 9)
    return _q(f"أوجد ناتج: {mul(-a, -b)}", a * b,
              [(-(a * b), "ظن أن ضرب سالبين يعطي سالباً"), (-a - b, "جمع بدل الضرب"), (a + b, "جمع بدل الضرب")],
              f"سالب × سالب = موجب: {M(f'{-a} × ({-b}) = {a * b}')}.", "متشابهتان ← موجب.")


@tpl(S5, 2, "md_mult")
def _md2_negneg_input(r):
    a, b = r.randint(2, 12), r.randint(2, 9)
    return _q(f"أوجد ناتج: {mul(-a, -b)}  (اكتب الجواب)", a * b,
              [(-(a * b), "ظن أن ضرب سالبين يعطي سالباً"), (-a - b, "جمع بدل الضرب")],
              f"{M(f'{-a} × ({-b}) = {a * b}')}.", "نفي النفي إثبات.", "input")


@tpl(S5, 2, "md_div")
def _md2_div_negneg(r):
    a, b = r.randint(2, 9), r.randint(2, 9)
    return _q(f"ما ناتج {div(-(a * b), -b)}؟", a,
              [(-a, "ظن أن قسمة سالب على سالب تعطي سالباً"), (a * b, "ضرب بدل القسمة"), (b, "قسم على العدد الخطأ")],
              f"{M(f'{-(a * b)} ÷ ({-b}) = {a}')}: متشابهتان ← موجب.", "متشابهتان ← موجب.")


@tpl(S5, 2, "md_div")
def _md2_div_input(r):
    a, b = r.randint(2, 12), r.randint(2, 9)
    return _q(f"أوجد ناتج: {div(a * b, -b)}  (اكتب الجواب)", -a,
              [(a, "تجاهل الإشارة السالبة"), (a * b - b, "طرح بدل القسمة")],
              f"{M(f'{a * b} ÷ ({-b}) = {-a}')}: مختلفتان ← سالب.", "اقسم القيمتين ثم حدّد الإشارة.", "input")


@tpl(S5, 2, "md_mult")
def _md2_tf(r):
    a, b = r.randint(2, 9), r.randint(2, 9)
    x, y = r.choice([(-a, -b), (a, -b), (-a, b)])
    t = x * y
    claim = t if r.random() < 0.5 else -t
    return _tf(f"{M(f'({x}) × ({y}) = {claim}')}", claim == t, "قاعدة الإشارات غير صحيحة",
               f"{M(f'({x}) × ({y}) = {t}')}.", "متشابهتان موجب، مختلفتان سالب.")


@tpl(S5, 2, "md_multi")
def _md2_three(r):
    a, b, c = r.randint(2, 5), r.randint(2, 5), r.randint(2, 5)
    signs = [r.choice([-1, 1]) for _ in range(3)]
    x, y, z = a * signs[0], b * signs[1], c * signs[2]
    negs = sum(s < 0 for s in signs)
    word = "موجبة" if negs % 2 == 0 else "سالبة"
    return _q(f"ما إشارة ناتج {E(n(x), '×', par(y), '×', par(z))}؟", word,
              [("سالبة" if word == "موجبة" else "موجبة", "لم يعدّ العوامل السالبة بشكل صحيح"), ("صفر", "ظن أن الناتج صفر")],
              f"عدد العوامل السالبة {negs} ({'زوجي' if negs % 2 == 0 else 'فردي'}) فالناتج {word}.", "عدّ العوامل السالبة.")


@tpl(S5, 2, "md_multi")
def _md2_positive_pick(r):
    a, b, c = r.randint(2, 6), r.randint(2, 6), r.randint(2, 6)
    good = mul(-a, -b)
    bad = [mul(-a, b), mul(a, -b), E(n(-a), '×', par(-b), '×', par(-c))]
    return _q("أي حاصل ضرب مما يلي ناتجه موجب؟", good,
              [(x, "طبّق قاعدة الإشارات بشكل خاطئ") for x in bad],
              "سالب × سالب = موجب (عددان سالبان)، أما الباقي فعدد العوامل السالبة فيها فردي.", "عدّ العوامل السالبة.")


@tpl(S5, 3, "md_order")
def _md3_order(r):
    a, b, c = r.randint(2, 12), r.randint(2, 6), r.randint(2, 6)
    t = a - b * c
    return _q(f"أوجد ناتج: {E(str(a), '+', str(b), '×', par(-c))}", t,
              [((a + b) * -c, "جمع أولاً قبل الضرب"), (a + b * c, "تجاهل الإشارة السالبة"), (-t, "أخطأ في إشارة الناتج")],
              f"الضرب أولاً: {M(f'{a} + {b} × ({-c}) = {a} + ({-b * c}) = {t}')}.", "الضرب قبل الجمع.")


@tpl(S5, 3, "md_order")
def _md3_order_input(r):
    a, b, c = r.randint(2, 9), r.randint(2, 6), r.randint(2, 12)
    t = -a * b + c
    return _q(f"أوجد ناتج: {E(n(-a), '×', str(b), '+', str(c))}  (اكتب الجواب)", t,
              [(-a * (b + c), "جمع أولاً قبل الضرب"), (a * b + c, "تجاهل الإشارة السالبة"), (-a * b - c, "أخطأ في إشارة الحد الأخير")],
              f"{M(f'{-a} × {b} + {c} = {-a * b} + {c} = {t}')}.", "الضرب قبل الجمع.", "input")


@tpl(S5, 3, "md_order")
def _md3_paren(r):
    a, b, c = r.randint(2, 9), r.randint(2, 9), r.randint(2, 5)
    while a == b:
        b = r.randint(2, 9)
    t = (-a + b) * c
    return _q(f"أوجد ناتج: {M(f'({-a} + {b}) × {c}')}", t,
              [(-a + b * c, "تجاهل الأقواس"), (-(a + b) * c, "أخطأ في الجمع داخل القوس"), (-t, "أخطأ في إشارة الناتج")],
              f"ما داخل القوس أولاً: {M(f'({-a} + {b}) × {c} = {-a + b} × {c} = {t}')}.", "ابدأ بما داخل القوس.")


@tpl(S5, 3, "md_context")
def _md3_temp(r):
    a, h = r.randint(3, 6), r.randint(3, 8)
    return _q(f"انخفضت درجة الحرارة {a} درجات كل ساعة لمدة {h} ساعات. ما التغيّر الكلي في درجة الحرارة؟", -(a * h),
              [(a * h, "تجاهل اتجاه التغيير"), (-(a + h), "جمع بدل الضرب"), (h - a, "طرح بدل الضرب")],
              f"{M(f'({-a}) × {h} = {-(a * h)}')} درجة.", "الانخفاض = عدد سالب.")


@tpl(S5, 3, "md_context")
def _md3_installments(r):
    k, a = r.randint(3, 5), r.randint(11, 30)
    start = a * k + r.randint(5, 40)
    t = start - a * k
    return _q(f"رصيد سالم {start} ديناراً، وسدد {k} أقساط قيمة كل قسط {a} ديناراً. ما رصيده الآن؟", t,
              [(start + a * k, "جمع الأقساط بدل طرحها"), (start - a, "سدد قسطاً واحداً فقط"), (-t, "أخطأ في إشارة الناتج")],
              f"{M(f'{start} + {k} × ({-a}) = {start} + ({-a * k}) = {t}')}.", "كل قسط يُمثَّل بعدد سالب.")


@tpl(S5, 3, "md_context")
def _md3_div_context(r):
    k, a = r.randint(3, 8), r.randint(4, 25)
    return _q(f"خسر متجر {a * k} ديناراً موزعة بالتساوي على {k} أيام. ما التغيّر اليومي في أرباحه؟", -a,
              [(a, "تجاهل الخسارة"), (-(a * k) - k, "طرح بدل القسمة"), (-a * k, "لم يقسم")],
              f"{M(f'{-(a * k)} ÷ {k} = {-a}')} ديناراً يومياً.", "الخسارة تُمثَّل بعدد سالب.")


@tpl(S5, 3, "md_multi")
def _md3_tf_three(r):
    a, b, c = r.randint(2, 5), r.randint(2, 5), r.randint(2, 5)
    t = -a * -b * -c
    claim = t if r.random() < 0.5 else -t
    return _tf(f"{M(f'({-a}) × ({-b}) × ({-c}) = {claim}')}", claim == t, "لم يعدّ العوامل السالبة بشكل صحيح",
               f"ثلاثة عوامل سالبة (عدد فردي) فالناتج سالب: {N(t)}.", "عدّ العوامل السالبة.")


# =====================================================================================
# public API
# =====================================================================================
GENERATORS = {sk: (lambda d, r, _sk=sk: _pick(_sk, d, r)) for sk in REGISTRY}   # old-style access, kept for compatibility


def _finish(t: Template, rng: random.Random) -> dict | None:
    """Run one template and clean the result (unique options, misconception lookup table, metadata)."""
    raw = t.fn(rng)
    correct = raw["correct_answer"]
    seen, dist = {norm(correct)}, []
    for text, why in raw["distractors"]:
        k = norm(text)
        if k in seen:
            continue
        seen.add(k)
        dist.append({"text": text, "misconception": why})
    kind = raw["type"]
    if kind == "mcq":
        if len(dist) < 2:
            return None
        dist = dist[:3]
    elif kind == "tf" and not dist:
        return None
    return {
        "question": raw["question"], "correct_answer": correct, "distractors": dist,
        "explanation": raw["explanation"], "hint": raw["hint"], "type": kind,
        "traps": {norm(d["text"]): d["misconception"] for d in dist},
        "skill": t.skill, "difficulty": t.level, "pattern": t.pattern, "template": t.fn.__name__,
    }


def _pick(skill_id, difficulty, rng, avoid=None, pattern=None):
    avoid = set(avoid or ())
    levels = REGISTRY[skill_id]
    difficulty = min(max(difficulty, min(levels)), max(levels))
    pool = list(levels.get(difficulty, []))
    if pattern:
        same = [t for t in pool if t.pattern == pattern]
        if not same:                                   # the idea lives on another level: use the nearest one
            for lvl in sorted(levels, key=lambda l: abs(l - difficulty)):
                same = [t for t in levels[lvl] if t.pattern == pattern]
                if same:
                    break
        pool = same or pool
    fallback = None
    for _ in range(60):
        q = _finish(rng.choice(pool), rng)
        if q is None:
            continue
        if q["question"] not in avoid:
            return q
        fallback = fallback or q
    return fallback or _finish(pool[0], rng)


def generate_offline(skill_id, difficulty, rng=None, avoid=None, pattern=None):
    """
    One fresh question for (skill, difficulty).
      avoid   : question texts asked recently (not repeated when possible)
      pattern : ask about this specific idea (used for the follow-up after a mistake)
    """
    return _pick(skill_id, difficulty, rng or random.Random(), avoid, pattern)


def patterns_of(skill_id: str) -> list[str]:
    seen = []
    for lvl in sorted(REGISTRY[skill_id]):
        for t in REGISTRY[skill_id][lvl]:
            if t.pattern not in seen:
                seen.append(t.pattern)
    return seen


def template_count() -> int:
    return sum(len(ts) for lv in REGISTRY.values() for ts in lv.values())
