from __future__ import annotations

import math
from fractions import Fraction

from app.engine.offline_bank import PATTERNS, _q, _tf, tpl, E, M, L, N, MINUS

FA, MA, MM, DV = "fractions_addsub", "mixed_addsub", "mixed_mult", "mixed_div"
DENS = (2, 3, 4, 5, 6, 8, 10, 12)


def fr(x) -> str:
    x = Fraction(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def mx(x) -> str:
    x = Fraction(x)
    whole, rest = divmod(x.numerator, x.denominator)
    if rest == 0:
        return str(whole)
    if whole == 0:
        return f"{rest}/{x.denominator}"
    return f"{whole} {rest}/{x.denominator}"


def mp(w, a, d) -> str:
    return f"{w} {a}/{d}"


def val(w, a, d) -> Fraction:
    return Fraction(w * d + a, d)


def proper(r, dens=DENS):
    d = r.choice([x for x in dens if x >= 3])
    a = r.choice([x for x in range(1, d) if math.gcd(x, d) == 1])
    return a, d


def mixed(r, dens=DENS):
    a, d = proper(r, dens)
    return r.randint(1, 5), a, d


def rn(r, d, lo=1, hi=None):
    hi = d - 1 if hi is None else hi
    pool = [x for x in range(lo, hi + 1) if math.gcd(x, d) == 1]
    return r.choice(pool or [1])


def coprime_pair(r):
    return r.choice([(2, 3), (3, 4), (2, 5), (3, 5), (4, 5), (3, 7), (2, 7), (5, 6), (4, 7), (5, 8)])


def f(a, b) -> str:
    return f"{a}/{b}"


PATTERNS.update({
    "fa_same": dict(
        title="جمع الكسور وطرحها بمقام واحد",
        rule="عندما يتساوى المقامان نجمع البسطين أو نطرحهما ونُبقي المقام كما هو، ثم نبسّط الناتج.",
        example=f"{M('3/8 + 2/8 = 5/8')} ، {M('5/6 - 1/6 = 4/6 = 2/3')}."),
    "fa_lcd": dict(
        title="المقام المشترك",
        rule="لتوحيد المقامين نبحث عن أصغر عدد يقبل القسمة على المقامين، ثم نضرب بسط كل كسر ومقامه في العدد نفسه.",
        example=f"المقام المشترك الأصغر للكسرين {M('1/4')} و{M('1/6')} هو 12 ، فنكتب {M('3/12')} و{M('2/12')}."),
    "fa_unlike": dict(
        title="جمع الكسور وطرحها بمقامين مختلفين",
        rule="نوحّد المقامين أولاً، ثم نجمع البسطين أو نطرحهما ونُبقي المقام المشترك، ثم نبسّط.",
        example=f"{M('1/2 + 1/3 = 3/6 + 2/6 = 5/6')}."),
    "fa_context": dict(
        title="مسائل حياتية على الكسور",
        rule="نحدد العملية من معنى المسألة (جمع للضم وطرح للأخذ)، ثم نوحّد المقامات ونحسب.",
        example=f"أكل أحمد {M('1/4')} الكعكة وأكلت سلمى {M('1/2')} ← {M('1/4 + 2/4 = 3/4')}."),
    "fa_multi": dict(
        title="عمليات متعددة على الكسور",
        rule="ننفذ العمليات من اليسار إلى اليمين بعد توحيد جميع المقامات.",
        example=f"{M('1/2 + 1/4 - 1/4 = 2/4 + 1/4 - 1/4 = 2/4 = 1/2')}."),
    "ma_convert": dict(
        title="التحويل بين العدد الكسري والكسر غير الفعلي",
        rule="لتحويل العدد الكسري نضرب العدد الصحيح في المقام ونضيف البسط ونُبقي المقام. وللعكس نقسم البسط على المقام: الناتج هو العدد الصحيح والباقي هو البسط.",
        example=f"{M('2 1/3 = (2×3+1)/3 = 7/3')} ، {M('11/4 = 2 3/4')}."),
    "ma_same": dict(
        title="جمع الأعداد الكسرية بمقام واحد",
        rule="نجمع الأجزاء الصحيحة معاً والكسور معاً، ثم نبسّط.",
        example=f"{M('1 2/7 + 2 3/7 = 3 5/7')}."),
    "ma_carry": dict(
        title="الجمع مع الاستبدال",
        rule="إذا كان مجموع الكسرين أكبر من 1 نحوّله إلى عدد كسري ونضيف جزأه الصحيح إلى مجموع الأجزاء الصحيحة.",
        example=f"{M('2 3/5 + 1 4/5 = 3 7/5 = 4 2/5')}."),
    "ma_borrow": dict(
        title="الطرح مع الاستلاف",
        rule="إذا كان الكسر المطروح منه أصغر من الكسر المطروح نستلف 1 من الجزء الصحيح ونحوّله إلى كسر بمقام المسألة.",
        example=f"{M('3 1/5 - 1 3/5 = 2 6/5 - 1 3/5 = 1 3/5')}."),
    "ma_unlike": dict(
        title="الأعداد الكسرية بمقامين مختلفين",
        rule="نوحّد مقامي الكسرين أولاً، ثم نجمع أو نطرح الأجزاء الصحيحة والكسرية مع الاستبدال أو الاستلاف عند الحاجة.",
        example=f"{M('1 1/2 + 2 1/4 = 1 2/4 + 2 1/4 = 3 3/4')}."),
    "ma_context": dict(
        title="مسائل حياتية على الأعداد الكسرية",
        rule="نحدد العملية من المعنى ثم نحسب مع تحويل الكسور عند الحاجة.",
        example=f"قطع سامر {M('1 1/2')} م ثم {M('2 1/2')} م ← المجموع 4 م."),
    "mm_frac": dict(
        title="ضرب كسر في كسر",
        rule="نضرب البسط في البسط والمقام في المقام ثم نبسّط. لا نحتاج إلى توحيد المقامات.",
        example=f"{M('2/3 × 3/4 = 6/12 = 1/2')}."),
    "mm_whole": dict(
        title="ضرب عدد صحيح في كسر",
        rule="نكتب العدد الصحيح على صورة كسر مقامه 1 ثم نضرب. أو نضرب العدد في البسط ونُبقي المقام.",
        example=f"{M('4 × 2/5 = 8/5 = 1 3/5')}."),
    "mm_cancel": dict(
        title="التبسيط قبل الضرب",
        rule="يمكننا قسمة أي بسط وأي مقام على عامل مشترك قبل الضرب لتصغير الأعداد.",
        example=f"{M('3/8 × 4/9 = (3×4)/(8×9) = 1/6')} بعد القسمة على 3 وعلى 4."),
    "mm_mixed": dict(
        title="ضرب الأعداد الكسرية",
        rule="نحوّل كل عدد كسري إلى كسر غير فعلي ثم نضرب البسط في البسط والمقام في المقام ونحوّل الناتج إلى عدد كسري. لا نضرب الأجزاء الصحيحة وحدها.",
        example=f"{M('1 1/2 × 2 1/3 = 3/2 × 7/3 = 7/2 = 3 1/2')}."),
    "mm_context": dict(
        title="مسائل حياتية على ضرب الكسور",
        rule="كلمة (من) أو (كل) أو (مساحة) تعني غالباً الضرب. نكتب العملية ثم نحوّل الأعداد الكسرية ونحسب.",
        example=f"ثلث {M('1 1/2')} كغ هو {M('1/3 × 3/2 = 1/2')} كغ."),
    "dv_recip": dict(
        title="مقلوب الكسر",
        rule="مقلوب الكسر هو الكسر الناتج عن تبديل البسط والمقام. مقلوب العدد الصحيح n هو 1/n.",
        example=f"مقلوب {M('3/5')} هو {M('5/3')} ، ومقلوب {M('4')} هو {M('1/4')}."),
    "dv_frac": dict(
        title="قسمة كسر على كسر",
        rule="القسمة تعني الضرب في مقلوب المقسوم عليه فقط: نُبقي الكسر الأول ونقلب الثاني ونضرب.",
        example=f"{M('2/3 ÷ 4/5 = 2/3 × 5/4 = 10/12 = 5/6')}."),
    "dv_whole": dict(
        title="القسمة على عدد صحيح أو قسمة عدد صحيح",
        rule="العدد الصحيح كسر مقامه 1، فنقلب المقسوم عليه ونضرب.",
        example=f"{M('3 ÷ 1/4 = 3 × 4 = 12')} ، {M('2/3 ÷ 2 = 2/3 × 1/2 = 1/3')}."),
    "dv_mixed": dict(
        title="قسمة الأعداد الكسرية",
        rule="نحوّل العددين الكسريين إلى كسرين غير فعليين، ثم نضرب الأول في مقلوب الثاني ونبسّط ونحوّل الناتج إلى عدد كسري.",
        example=f"{M('1 1/2 ÷ 3/4 = 3/2 × 4/3 = 2')}."),
    "dv_context": dict(
        title="مسائل حياتية على القسمة",
        rule="عندما نسأل كم قطعة أو كم كوباً تكفي، فنقسم الكمية الكلية على حجم الجزء الواحد.",
        example=f"حبل طوله 3 م يُقطع قطعاً طول كل منها {M('3/4')} م ← {M('3 ÷ 3/4 = 4')} قطع."),
})

PARENTS = {
    "fa_lcd": "fa_same", "fa_unlike": "fa_same", "fa_context": "fa_unlike", "fa_multi": "fa_unlike",
    "ma_convert": "fa_same", "ma_same": "ma_convert", "ma_carry": "ma_same", "ma_borrow": "ma_carry",
    "ma_unlike": "ma_carry", "ma_context": "ma_unlike",
    "mm_frac": "fa_same", "mm_whole": "mm_frac", "mm_cancel": "mm_frac", "mm_mixed": "mm_whole",
    "mm_context": "mm_mixed",
    "dv_recip": "mm_frac", "dv_frac": "dv_recip", "dv_whole": "dv_frac", "dv_mixed": "dv_frac",
    "dv_context": "dv_mixed",
}

SIMPLE = "اكتب الناتج في أبسط صورة (كسراً غير فعلي إن لزم)"


@tpl(FA, 1, "fa_same")
def _fa1_add(r):
    d = r.choice([5, 6, 7, 8, 9, 10, 12])
    a = r.randint(1, d - 3)
    b = r.randint(1, d - a - 1)
    t = Fraction(a + b, d)
    return _q(f"أوجد ناتج الجمع. {SIMPLE}: {E(f(a, d), '+', f(b, d))}", fr(t),
              [(f(a + b, 2 * d), "جمع البسطين والمقامين معاً"), (f(a + b, d), "لم يبسّط الناتج"),
               (fr(Fraction(abs(a - b), d)), "طرح بدل الجمع")],
              f"{M(f'{a}/{d} + {b}/{d} = {a + b}/{d} = {fr(t)}')}.", "المقام يبقى كما هو.", "input")


@tpl(FA, 1, "fa_same")
def _fa1_sub(r):
    d = r.choice([5, 6, 7, 8, 9, 10, 12])
    a = r.randint(3, d - 1)
    b = r.randint(1, a - 1)
    t = Fraction(a - b, d)
    return _q(f"أوجد ناتج الطرح: {E(f(a, d), MINUS, f(b, d))}", fr(t),
              [(fr(Fraction(a + b, d)), "جمع بدل الطرح"), (fr(Fraction(a - b, 2 * d)), "جمع المقامين أيضاً"),
               (fr(Fraction(a * b, d)), "ضرب البسطين")],
              f"{M(f'{a}/{d} - {b}/{d} = {a - b}/{d} = {fr(t)}')}.", "اطرح البسطين فقط.")


@tpl(FA, 1, "fa_same")
def _fa1_tf(r):
    d = r.choice([5, 6, 7, 8, 9])
    a = r.randint(1, d - 3)
    b = r.randint(1, d - a - 1)
    truth = r.random() < 0.5
    right = f"{a + b}/{d}"
    shown = right if truth else f"{a + b}/{2 * d}"
    return _tf(f"{M(f'{a}/{d} + {b}/{d} = {shown}')}", truth, "جمع المقامين مع البسطين",
               f"عند تساوي المقامين نجمع البسطين فقط: {M(f'{a}/{d} + {b}/{d} = {right}')}.", "هل يتغير المقام؟")


@tpl(FA, 1, "fa_same")
def _fa1_missing(r):
    d = r.choice([6, 7, 8, 9, 10, 12])
    c = r.randint(4, d - 1)
    a = r.randint(1, c - 2)
    t = Fraction(c - a, d)
    return _q(f"أوجد الكسر الناقص: {E(f(a, d), '+', '؟', '=', f(c, d))}", fr(t),
              [(fr(Fraction(a + c, d)), "جمع بدل الطرح"), (fr(Fraction(c, a)), "قسم البسطين"),
               (fr(Fraction(c - a + 1, d)), "أخطأ في الطرح")],
              f"{M(f'{c}/{d} - {a}/{d} = {c - a}/{d}')}.", "اطرح الكسر المعلوم من الناتج.")


@tpl(FA, 1, "fa_context")
def _fa1_context(r):
    d = r.choice([6, 8, 10, 12])
    a = r.randint(1, d - 3)
    b = r.randint(1, d - a - 1)
    name1, name2 = r.choice([("علي", "ليلى"), ("سامر", "هدى"), ("عمر", "رنا")])
    t = Fraction(a + b, d)
    return _q(f"أكل {name1} {L(f(a, d))} من كعكة وأكلت {name2} {L(f(b, d))} منها. ما الجزء الذي أُكل؟ {SIMPLE}.", fr(t),
              [(f(a + b, 2 * d), "جمع المقامين"), (f(a + b, d), "لم يبسّط") if Fraction(a + b, d).denominator != d else (fr(Fraction(abs(a - b), d)), "طرح بدل الجمع"),
               (fr(Fraction(1) - t), "حسب الجزء المتبقي")],
              f"{M(f'{a}/{d} + {b}/{d} = {fr(t)}')}.", "كلمة (ما أُكل) تعني الجمع.", "input")


@tpl(FA, 2, "fa_unlike")
def _fa2_add(r):
    d1 = r.choice([2, 3, 4, 5])
    k = r.choice([2, 3, 4])
    d2 = d1 * k
    a = rn(r, d1)
    b = rn(r, d2)
    t = Fraction(a, d1) + Fraction(b, d2)
    return _q(f"أوجد ناتج الجمع. {SIMPLE}: {E(f(a, d1), '+', f(b, d2))}", fr(t),
              [(f(a + b, d1 + d2), "جمع البسطين والمقامين"), (fr(Fraction(a + b, d2)), "جمع البسطين دون توحيد المقام"),
               (fr(Fraction(a + b, d1)), "أبقى المقام الأصغر")],
              f"{M(f'{a}/{d1} = {a * k}/{d2} ، {a * k}/{d2} + {b}/{d2} = {fr(t)}')}.", "وحّد المقامين أولاً.", "input")


@tpl(FA, 2, "fa_unlike")
def _fa2_sub(r):
    while True:
        d1 = r.choice([2, 3, 4, 5])
        k = r.choice([2, 3, 4])
        d2 = d1 * k
        a, b = rn(r, d1), rn(r, d2)
        if Fraction(a, d1) > Fraction(b, d2) and b % k != 0:
            break
    t = Fraction(a, d1) - Fraction(b, d2)
    return _q(f"أوجد ناتج الطرح: {E(f(a, d1), MINUS, f(b, d2))}", fr(t),
              [(fr(Fraction(abs(a - b), d2)), "طرح البسطين دون توحيد المقام"), (fr(Fraction(a + b, d2)), "جمع بدل الطرح"),
               (fr(Fraction(abs(a - b), d1)), "أبقى المقام الأصغر"), (fr(Fraction(a, d1) + Fraction(b, d2)), "جمع الكسرين بدل طرحهما"),
               (fr(Fraction(abs(a * k + b), d2 + d1)), "جمع المقامين")],
              f"{M(f'{a}/{d1} = {a * k}/{d2} ، {a * k}/{d2} - {b}/{d2} = {fr(t)}')}.", "وحّد المقامين أولاً.")


@tpl(FA, 2, "fa_lcd")
def _fa2_lcd(r):
    d1 = r.choice([2, 3, 4, 5])
    k = r.choice([2, 3, 4])
    d2 = d1 * k
    a, b = rn(r, d1), rn(r, d2)
    return _q(f"ما المقام المشترك الأصغر للكسرين {E(f(a, d1))} و{E(f(b, d2))}؟", d2,
              [(d1 * d2, "ضرب المقامين دون البحث عن الأصغر"), (d1 + d2, "جمع المقامين"), (d1, "اختار المقام الأصغر")],
              f"{N(d2)} يقبل القسمة على {N(d1)} وعلى {N(d2)} وهو أصغرها.", "ابحث عن أصغر عدد يقبل القسمة على المقامين.")


@tpl(FA, 2, "fa_lcd")
def _fa2_equiv_tf(r):
    d1 = r.choice([2, 3, 4, 5])
    k = r.choice([2, 3, 4])
    a = rn(r, d1)
    truth = r.random() < 0.5
    shown = f"{a * k}/{d1 * k}" if truth else f"{a + k}/{d1 * k}"
    return _tf(f"{M(f'{a}/{d1} = {shown}')}", truth, "جمع العدد بدل الضرب في البسط",
               f"نضرب البسط والمقام في العدد نفسه: {M(f'{a}/{d1} = {a * k}/{d1 * k}')}.", "اضرب البسط والمقام في العدد نفسه.")


@tpl(FA, 2, "fa_context")
def _fa2_context(r):
    d1 = r.choice([2, 4, 5])
    k = r.choice([2, 3])
    d2 = d1 * k
    a = rn(r, d1)
    b = rn(r, d2)
    t = Fraction(a, d1) + Fraction(b, d2)
    return _q(f"شرب سامر {L(f(a, d1))} لتر من العصير ثم شرب {L(f(b, d2))} لتر. ما كمية ما شربه؟ {SIMPLE}.", fr(t),
              [(f(a + b, d1 + d2), "جمع البسطين والمقامين"), (fr(Fraction(a + b, d2)), "لم يوحّد المقامين"),
               (fr(Fraction(abs(a * k - b), d2)), "طرح بدل الجمع")],
              f"{M(f'{a}/{d1} + {b}/{d2} = {a * k}/{d2} + {b}/{d2} = {fr(t)}')} لتر.", "كلمة (ثم شرب) تعني الجمع.", "input")


@tpl(FA, 3, "fa_unlike")
def _fa3_add(r):
    d1, d2 = coprime_pair(r)
    a = rn(r, d1)
    b = rn(r, d2)
    t = Fraction(a, d1) + Fraction(b, d2)
    return _q(f"أوجد ناتج الجمع. {SIMPLE}: {E(f(a, d1), '+', f(b, d2))}", fr(t),
              [(f(a + b, d1 + d2), "جمع البسطين والمقامين"), (fr(Fraction(a + b, d1 * d2)), "ضرب المقامين وجمع البسطين فقط"),
               (fr(Fraction(a * b, d1 * d2)), "ضرب بدل الجمع")],
              f"{M(f'{a}/{d1} + {b}/{d2} = {a * d2}/{d1 * d2} + {b * d1}/{d1 * d2} = {fr(t)}')}.", "المقام المشترك هنا هو حاصل ضرب المقامين.", "input")


@tpl(FA, 3, "fa_unlike")
def _fa3_sub(r):
    while True:
        d1, d2 = coprime_pair(r)
        a, b = rn(r, d1), rn(r, d2)
        if Fraction(a, d1) > Fraction(b, d2):
            break
    t = Fraction(a, d1) - Fraction(b, d2)
    return _q(f"أوجد ناتج الطرح: {E(f(a, d1), MINUS, f(b, d2))}", fr(t),
              [(fr(Fraction(abs(a - b), abs(d1 - d2))), "طرح البسطين والمقامين"), (fr(Fraction(abs(a - b), d1 * d2)), "لم يوحّد المقامين بشكل صحيح"),
               (fr(Fraction(a, d1) + Fraction(b, d2)), "جمع بدل الطرح")],
              f"{M(f'{a}/{d1} - {b}/{d2} = {a * d2}/{d1 * d2} - {b * d1}/{d1 * d2} = {fr(t)}')}.", "وحّد المقامين بالضرب.")


@tpl(FA, 3, "fa_multi")
def _fa3_three(r):
    while True:
        d1 = r.choice([2, 3, 4, 5])
        k = r.choice([2, 3])
        d2 = d1 * k
        a, c = rn(r, d1), rn(r, d1)
        b = rn(r, d2)
        if a > c and b % k != 0:
            break
    t = Fraction(a, d1) + Fraction(b, d2) - Fraction(c, d1)
    return _q(f"أوجد ناتج: {E(f(a, d1), '+', f(b, d2), MINUS, f(c, d1))}", fr(t),
              [(fr(Fraction(a, d1) + Fraction(b, d2) + Fraction(c, d1)), "جمع الكسر الأخير بدل طرحه"),
               (fr(Fraction(a - c + b, d1)), "تجاهل اختلاف المقامين"), (fr(Fraction(abs(a + b - c), d1 + d2 + d1)), "جمع المقامات")],
              f"{M(f'{a}/{d1} + {b}/{d2} - {c}/{d1} = {fr(t)}')}.", "وحّد جميع المقامات ثم احسب من اليسار.")


@tpl(FA, 3, "fa_context")
def _fa3_tank(r):
    while True:
        d1, d2 = coprime_pair(r)
        a, b = rn(r, d1), rn(r, d2)
        if Fraction(a, d1) + Fraction(b, d2) < 1:
            break
    t = 1 - Fraction(a, d1) - Fraction(b, d2)
    return _q(f"في خزان كمية ماء كاملة. استُهلك منها {L(f(a, d1))} صباحاً ثم {L(f(b, d2))} مساءً. ما الجزء المتبقي؟ {SIMPLE}.", fr(t),
              [(fr(1 - Fraction(a, d1)), "نسي طرح الكمية الثانية"), (fr(Fraction(a, d1) + Fraction(b, d2)), "حسب ما استُهلك لا المتبقي"),
               (fr(Fraction(1) - Fraction(a + b, d1 + d2)), "جمع البسطين والمقامين")],
              f"{M(f'1 - {a}/{d1} - {b}/{d2} = {fr(t)}')}.", "الكل يساوي 1.", "input")


@tpl(FA, 3, "fa_multi")
def _fa3_missing(r):
    while True:
        d1, d2 = coprime_pair(r)
        a, c = rn(r, d1), rn(r, d2)
        if Fraction(c, d2) > Fraction(a, d1):
            break
    t = Fraction(c, d2) - Fraction(a, d1)
    return _q(f"أوجد الكسر الناقص: {E(f(a, d1), '+', '؟', '=', f(c, d2))}", fr(t),
              [(fr(Fraction(c, d2) + Fraction(a, d1)), "جمع بدل الطرح"), (fr(Fraction(abs(c - a), abs(d2 - d1))), "طرح البسطين والمقامين"),
               (fr(Fraction(abs(c - a), d1 * d2)), "لم يوحّد المقامين")],
              f"{M(f'{c}/{d2} - {a}/{d1} = {fr(t)}')}.", "اطرح الكسر المعلوم من الناتج.")


@tpl(MA, 1, "ma_convert")
def _ma1_improper(r):
    w, a, d = mixed(r)
    return _q(f"حوّل العدد الكسري {E(mp(w, a, d))} إلى كسر غير فعلي.", f(w * d + a, d),
              [(f(w + a, d), "جمع العدد الصحيح مع البسط"), (f(w * a + d, d), "ضرب العدد الصحيح في البسط"),
               (f(w * d + a, w), "أخذ العدد الصحيح مقاماً")],
              f"{M(f'{w} {a}/{d} = ({w}×{d}+{a})/{d} = {w * d + a}/{d}')}.", "اضرب العدد الصحيح في المقام ثم أضف البسط.")


@tpl(MA, 1, "ma_convert")
def _ma1_tomixed(r):
    w, a, d = mixed(r)
    n = w * d + a
    return _q(f"حوّل الكسر {E(f(n, d))} إلى عدد كسري.", mp(w, a, d),
              [(mp(w + 1, a, d), "زاد العدد الصحيح واحداً"), (mp(w, d - a, d), "أخذ المتمم بدل الباقي"),
               (mp(a, w, d) if a != w else mp(w, a + 1, d), "عكس العدد الصحيح والبسط")],
              f"{M(f'{n} ÷ {d} = {w} والباقي {a}')} ← {M(f'{w} {a}/{d}')}.", "اقسم البسط على المقام.")


@tpl(MA, 1, "ma_same")
def _ma1_add(r):
    d = r.choice([5, 7, 8, 9, 10, 12])
    a1, a2 = r.choice([(x, y) for x in range(1, d) for y in range(1, d) if math.gcd(x, d) == 1 and math.gcd(y, d) == 1 and x + y < d])
    w1, w2 = r.randint(1, 5), r.randint(1, 5)
    t = val(w1, a1, d) + val(w2, a2, d)
    return _q(f"أوجد ناتج: {E(mp(w1, a1, d), '+', mp(w2, a2, d))}", mx(t),
              [(mp(w1 + w2, a1 + a2, 2 * d), "جمع المقامين"), (mp(w1 * w2, a1 + a2, d), "ضرب الأجزاء الصحيحة"),
               (mp(w1 + w2, a1 * a2, d), "ضرب البسطين")],
              f"{M(f'{w1 + w2} + {a1 + a2}/{d} = {mx(t)}')}.", "اجمع الأجزاء الصحيحة ثم الكسور.")


@tpl(MA, 2, "ma_carry")
def _ma2_carry(r):
    d = r.choice([5, 7, 8, 9, 10, 12])
    a1, a2 = r.choice([(x, y) for x in range(1, d) for y in range(1, d) if math.gcd(x, d) == 1 and math.gcd(y, d) == 1 and x + y > d])
    w1, w2 = r.randint(1, 5), r.randint(1, 5)
    t = val(w1, a1, d) + val(w2, a2, d)
    return _q(f"أوجد ناتج: {E(mp(w1, a1, d), '+', mp(w2, a2, d))}", mx(t),
              [(mp(w1 + w2, a1 + a2, d), "نسي تحويل الكسر غير الفعلي"), (mp(w1 + w2, a1 + a2 - d, d), "نسي إضافة 1 إلى الجزء الصحيح"),
               (mp(w1 + w2 + 1, a1 + a2 - d, 2 * d), "جمع المقامين")],
              f"{M(f'{w1 + w2} {a1 + a2}/{d} = {mx(t)}')}.", "إذا زاد الكسر عن 1 فحوّله.")


@tpl(MA, 2, "ma_borrow")
def _ma2_borrow(r):
    d = r.choice([5, 7, 8, 9, 10, 12])
    a1, a2 = r.choice([(x, y) for x in range(1, d) for y in range(1, d) if math.gcd(x, d) == 1 and math.gcd(y, d) == 1 and x < y])
    w2 = r.randint(1, 4)
    w1 = w2 + r.randint(2, 4)
    t = val(w1, a1, d) - val(w2, a2, d)
    return _q(f"أوجد ناتج: {E(mp(w1, a1, d), MINUS, mp(w2, a2, d))}", mx(t),
              [(mp(w1 - w2, a2 - a1, d), "طرح الكسر الأصغر من الأكبر"), (mp(w1 - w2 - 1, a2 - a1, d), "استلف لكنه طرح بالعكس"),
               (mp(w1 - w2, a1, d), "أهمل الكسر المطروح")],
              f"{M(f'{w1} {a1}/{d} = {w1 - 1} {d + a1}/{d}')} ثم نطرح: {M(mx(t))}.", "الكسر الأول أصغر، فاستلف 1 من الجزء الصحيح.")


@tpl(MA, 2, "ma_convert")
def _ma2_tf(r):
    w, a, d = mixed(r)
    truth = r.random() < 0.5
    shown = f(w * d + a, d) if truth else f(w + a, d)
    return _tf(f"{M(f'{w} {a}/{d} = {shown}')}", truth, "جمع العدد الصحيح مع البسط",
               f"{M(f'{w} {a}/{d} = ({w}×{d}+{a})/{d} = {w * d + a}/{d}')}.", "اضرب ثم اجمع.")


@tpl(MA, 2, "ma_unlike")
def _ma2_unlike(r):
    d1 = r.choice([2, 3, 4, 5])
    k = r.choice([2, 3, 4])
    d2 = d1 * k
    a1 = rn(r, d1)
    a2 = rn(r, d2)
    w1, w2 = r.randint(1, 4), r.randint(1, 4)
    t = val(w1, a1, d1) + val(w2, a2, d2)
    return _q(f"أوجد ناتج: {E(mp(w1, a1, d1), '+', mp(w2, a2, d2))}", mx(t),
              [(mp(w1 + w2, a1 + a2, d1 + d2), "جمع البسطين والمقامين"), (mp(w1 + w2, a1 + a2, d2), "جمع البسطين دون توحيد المقام"),
               (mp(w1 + w2, abs(a1 * k - a2), d2), "طرح بدل الجمع")],
              f"{M(f'{w1} {a1 * k}/{d2} + {w2} {a2}/{d2} = {mx(t)}')}.", "وحّد المقامين أولاً.")


@tpl(MA, 2, "ma_context")
def _ma2_context(r):
    d = r.choice([4, 5, 8])
    a1, a2 = rn(r, d), rn(r, d)
    w1, w2 = r.randint(1, 4), r.randint(1, 4)
    t = val(w1, a1, d) + val(w2, a2, d)
    return _q(f"ركضت سلمى {L(mp(w1, a1, d))} كم صباحاً و{L(mp(w2, a2, d))} كم مساءً. كم كيلومتراً ركضت في اليوم؟", mx(t),
              [(mp(w1 + w2, a1 + a2, d), "نسي تحويل الكسر غير الفعلي"), (mx(abs(val(w1, a1, d) - val(w2, a2, d))) if val(w1, a1, d) != val(w2, a2, d) else mp(w1 + w2 + 1, 1, d), "طرح بدل الجمع"),
               (mp(w1 + w2, a1 + a2, 2 * d), "جمع المقامين")],
              f"{M(f'{mp(w1, a1, d)} + {mp(w2, a2, d)} = {mx(t)}')} كم.", "كلمة (في اليوم) تعني الجمع.")


@tpl(MA, 3, "ma_unlike")
def _ma3_sub(r):
    while True:
        d1 = r.choice([2, 3, 4, 5])
        k = r.choice([2, 3, 4])
        d2 = d1 * k
        a1, a2 = rn(r, d1), rn(r, d2)
        w1, w2 = r.randint(2, 6), r.randint(1, 4)
        t = val(w1, a1, d1) - val(w2, a2, d2)
        if t > 0 and a2 % k != 0:
            break
    return _q(f"أوجد ناتج: {E(mp(w1, a1, d1), MINUS, mp(w2, a2, d2))}", mx(t),
              [(mp(abs(w1 - w2), abs(a1 - a2), abs(d1 - d2) or d2), "طرح الأجزاء والمقامات"), (mx(val(w1, a1, d1) + val(w2, a2, d2)), "جمع بدل الطرح"),
               (mp(w1 - w2, abs(a1 * k - a2), d2), "نسي الاستلاف")],
              f"{M(f'{w1} {a1 * k}/{d2} - {w2} {a2}/{d2} = {mx(t)}')}.", "وحّد المقامين ثم استلف عند الحاجة.")


@tpl(MA, 3, "ma_borrow")
def _ma3_whole_minus(r):
    w = r.randint(3, 9)
    a, d = proper(r)
    t = Fraction(w) - Fraction(a, d)
    return _q(f"أوجد ناتج: {E(str(w), MINUS, f(a, d))}", mx(t),
              [(mp(w - 1, a, d), "أخذ الكسر نفسه لا مكمّله"), (mp(w, d - a, d), "نسي الاستلاف"), (mp(w - a, 1, d) if w - a > 0 else mp(w, 1, d), "طرح البسط من العدد الصحيح")],
              f"{M(f'{w} = {w - 1} {d}/{d}')} ثم {M(f'{w - 1} {d}/{d} - {a}/{d} = {mx(t)}')}.", "استلف 1 وحوّله إلى كسر مقامه المقام نفسه.")


@tpl(MA, 3, "ma_unlike")
def _ma3_missing(r):
    d1 = r.choice([2, 3, 4, 5])
    k = r.choice([2, 3, 4])
    d2 = d1 * k
    a1, a2 = rn(r, d1), rn(r, d2)
    w1 = r.randint(1, 4)
    w2 = w1 + r.randint(2, 4)
    t = val(w2, a2, d2) - val(w1, a1, d1)
    if t <= 0:
        w2 += 2
        t = val(w2, a2, d2) - val(w1, a1, d1)
    return _q(f"أوجد العدد الناقص: {E(mp(w1, a1, d1), '+', '؟', '=', mp(w2, a2, d2))}", mx(t),
              [(mx(val(w2, a2, d2) + val(w1, a1, d1)), "جمع بدل الطرح"), (mp(abs(w2 - w1), abs(a2 - a1), d2), "طرح البسطين دون توحيد المقام"),
               (mp(w2 - w1, a2, d2), "أهمل الكسر المعلوم")],
              f"{M(f'{mp(w2, a2, d2)} - {mp(w1, a1, d1)} = {mx(t)}')}.", "اطرح العدد المعلوم من الناتج.")


@tpl(MA, 3, "ma_context")
def _ma3_context(r):
    while True:
        d1 = r.choice([2, 4, 5])
        k = r.choice([2, 3])
        d2 = d1 * k
        a1, a2 = rn(r, d1), rn(r, d2)
        w0, w1, w2 = r.randint(8, 12), r.randint(1, 3), r.randint(1, 3)
        t = Fraction(w0) - val(w1, a1, d1) - val(w2, a2, d2)
        if t > 0:
            break
    return _q(f"قماش طوله {w0} أمتار. قُطع منه {L(mp(w1, a1, d1))} م ثم {L(mp(w2, a2, d2))} م. كم متراً بقي؟", mx(t),
              [(mx(Fraction(w0) - val(w1, a1, d1)), "نسي طرح القطعة الثانية"), (mx(Fraction(w0) + val(w1, a1, d1) + val(w2, a2, d2)), "جمع بدل الطرح"),
               (mx(val(w1, a1, d1) + val(w2, a2, d2)), "حسب ما قُطع لا ما بقي")],
              f"{M(f'{w0} - {mp(w1, a1, d1)} - {mp(w2, a2, d2)} = {mx(t)}')} م.", "ما بقي = الكل - المقطوع.")


@tpl(MM, 1, "mm_frac")
def _mm1_frac(r):
    a, b = proper(r, (3, 4, 5, 6, 8))
    c, d = proper(r, (3, 4, 5, 6, 8))
    t = Fraction(a, b) * Fraction(c, d)
    return _q(f"أوجد ناتج الضرب. {SIMPLE}: {E(f(a, b), '×', f(c, d))}", fr(t),
              [(fr(Fraction(a * d, b * c)), "قلب الكسر الثاني وقسم"), (f(a + c, b + d), "جمع البسطين والمقامين"),
               (f(a * c, b * d), "لم يبسّط الناتج"), (fr(Fraction(a * c, b)), "ضرب البسطين وأبقى المقام الأول")],
              f"{M(f'{a}/{b} × {c}/{d} = {a * c}/{b * d} = {fr(t)}')}.", "اضرب البسط في البسط والمقام في المقام.", "input")


@tpl(MM, 1, "mm_whole")
def _mm1_whole(r):
    k = r.randint(2, 6)
    a, b = proper(r, (3, 4, 5, 7, 8))
    t = k * Fraction(a, b)
    return _q(f"أوجد ناتج: {E(str(k), '×', f(a, b))}", mx(t),
              [(mx(Fraction(a, b)), "ضرب البسط والمقام في العدد معاً"), (mx(Fraction(a, b * k)), "ضرب المقام فقط"),
               (mx(Fraction(k + a, b)), "جمع بدل الضرب")],
              f"{M(f'{k} × {a}/{b} = {k * a}/{b} = {mx(t)}')}.", "اضرب العدد في البسط.")


@tpl(MM, 1, "mm_frac")
def _mm1_tf(r):
    a, b = proper(r, (3, 4, 5, 6, 8))
    c, d = proper(r, (3, 4, 5, 6, 8))
    truth = r.random() < 0.5
    shown = f(a * c, b * d) if truth else f(a * d, b * c)
    return _tf(f"{M(f'{a}/{b} × {c}/{d} = {shown}')}", truth, "بدّل البسط والمقام في الكسر الثاني",
               f"{M(f'{a}/{b} × {c}/{d} = {a * c}/{b * d}')}.", "اضرب البسطين والمقامين دون قلب.")


@tpl(MM, 2, "mm_cancel")
def _mm2_cancel(r):
    while True:
        a, b = proper(r, (3, 4, 5, 6, 8, 10, 12))
        c, d = proper(r, (3, 4, 5, 6, 8, 10, 12))
        t = Fraction(a, b) * Fraction(c, d)
        if t.denominator < b * d and t.numerator < a * c:
            break
    return _q(f"أوجد ناتج الضرب. {SIMPLE}: {E(f(a, b), '×', f(c, d))}", fr(t),
              [(f(a * c, b * d), "لم يبسّط الناتج"), (fr(Fraction(a * d, b * c)), "قلب الكسر الثاني"), (f(a + c, b + d), "جمع البسطين والمقامين")],
              f"{M(f'{a}/{b} × {c}/{d} = {a * c}/{b * d} = {fr(t)}')}.", "ابحث عن عامل مشترك بين بسط ومقام.", "input")


@tpl(MM, 2, "mm_mixed")
def _mm2_whole(r):
    w, a, d = mixed(r, (2, 3, 4, 5, 6, 8))
    k = r.randint(2, 6)
    t = val(w, a, d) * k
    return _q(f"أوجد ناتج: {E(mp(w, a, d), '×', str(k))}", mx(t),
              [(mp(w * k, a, d), "ضرب الجزء الصحيح فقط"), (mp(w * k, a * k, d), "ضرب كل جزء على حدة دون تحويل"),
               (mx(val(w, a, d) + k), "جمع بدل الضرب")],
              f"{M(f'{mp(w, a, d)} × {k} = {w * d + a}/{d} × {k} = {mx(t)}')}.", "حوّل العدد الكسري إلى كسر غير فعلي أولاً.")


@tpl(MM, 2, "mm_mixed")
def _mm2_tf(r):
    w, a, d = mixed(r, (2, 3, 4, 5, 6, 8))
    k = r.randint(2, 5)
    t = val(w, a, d) * k
    truth = r.random() < 0.5
    shown = mx(t) if truth else mp(w * k, a, d)
    return _tf(f"{M(f'{mp(w, a, d)} × {k} = {shown}')}", truth, "ضرب الجزء الصحيح فقط",
               f"{M(f'{mp(w, a, d)} × {k} = {mx(t)}')}.", "حوّل إلى كسر غير فعلي.")


@tpl(MM, 2, "mm_context")
def _mm2_recipe(r):
    w, a, d = mixed(r, (2, 3, 4, 8))
    k = r.randint(2, 5)
    t = val(w, a, d) * k
    return _q(f"تحتاج وصفة إلى {L(mp(w, a, d))} كوباً من الطحين. كم كوباً تلزم لـ {k} وصفات؟", mx(t),
              [(mp(w * k, a, d), "ضرب الجزء الصحيح فقط"), (mx(val(w, a, d) + k), "جمع بدل الضرب"), (mp(w * k, a * k, d), "ضرب كل جزء على حدة")],
              f"{M(f'{mp(w, a, d)} × {k} = {mx(t)}')} كوباً.", "(كل) تعني الضرب.")


@tpl(MM, 2, "mm_context")
def _mm2_part_of(r):
    k = r.randint(2, 9)
    a, b = proper(r, (3, 4, 5, 8))
    t = k * Fraction(a, b)
    return _q(f"قُطع {L(f(a, b))} من خشبة طولها {k} أمتار. كم متراً قُطع؟", mx(t),
              [(mx(Fraction(k, 1) / Fraction(a, b)), "قسمة بدل الضرب"), (mx(Fraction(k) - Fraction(a, b)), "طرح بدل الضرب"), (mx(Fraction(a, b * k)), "ضرب المقام فقط")],
              f"{M(f'{a}/{b} × {k} = {mx(t)}')} م.", "(جزء من) تعني الضرب.")


@tpl(MM, 3, "mm_mixed")
def _mm3_mixed(r):
    w1, a1, b1 = mixed(r, (2, 3, 4, 5))
    w2, a2, b2 = mixed(r, (2, 3, 4, 5))
    t = val(w1, a1, b1) * val(w2, a2, b2)
    return _q(f"أوجد ناتج: {E(mp(w1, a1, b1), '×', mp(w2, a2, b2))}", mx(t),
              [(mp(w1 * w2, a1 * a2, b1 * b2), "ضرب الأجزاء الصحيحة والكسرية كلاً على حدة"),
               (mx(val(w1, a1, b1) * Fraction(a2, b2)), "نسي تحويل العدد الثاني"), (mx(val(w1, a1, b1) + val(w2, a2, b2)), "جمع بدل الضرب")],
              f"{M(f'{w1 * b1 + a1}/{b1} × {w2 * b2 + a2}/{b2} = {mx(t)}')}.", "حوّل العددين معاً إلى كسرين غير فعليين.")


@tpl(MM, 3, "mm_context")
def _mm3_area(r):
    w1, a1, b1 = mixed(r, (2, 3, 4))
    w2, a2, b2 = mixed(r, (2, 3, 4))
    t = val(w1, a1, b1) * val(w2, a2, b2)
    return _q(f"مستطيل طوله {L(mp(w1, a1, b1))} م وعرضه {L(mp(w2, a2, b2))} م. ما مساحته بالمتر المربع؟", mx(t),
              [(mp(w1 * w2, a1 * a2, b1 * b2), "ضرب الأجزاء كلاً على حدة"), (mx(val(w1, a1, b1) + val(w2, a2, b2)), "جمع الطول والعرض"),
               (mx(2 * (val(w1, a1, b1) + val(w2, a2, b2))), "حسب المحيط")],
              f"المساحة = الطول × العرض = {M(mx(t))} م².", "المساحة = الطول × العرض.")


@tpl(MM, 3, "mm_cancel")
def _mm3_cancel(r):
    while True:
        n1, d1 = r.randint(5, 17), r.randint(2, 9)
        n2, d2 = r.randint(5, 17), r.randint(2, 9)
        t = Fraction(n1, d1) * Fraction(n2, d2)
        if n1 > d1 and n2 > d2 and t.denominator < d1 * d2:
            break
    return _q(f"أوجد ناتج: {E(f(n1, d1), '×', f(n2, d2))}", mx(t),
              [(mx(Fraction(n1 * d2, d1 * n2)), "قلب الكسر الثاني"), (mx(Fraction(n1 + n2, d1 + d2)), "جمع البسطين والمقامين"),
               (mx(Fraction(n1 * n2, d1)), "ضرب البسطين وأبقى المقام الأول")],
              f"{M(f'{n1}/{d1} × {n2}/{d2} = {fr(t)} = {mx(t)}')}.", "بسّط قبل الضرب ثم حوّل الناتج.")


@tpl(MM, 3, "mm_mixed")
def _mm3_tf(r):
    w1, a1, b1 = mixed(r, (2, 3, 4, 5))
    w2, a2, b2 = mixed(r, (2, 3, 4, 5))
    t = val(w1, a1, b1) * val(w2, a2, b2)
    truth = r.random() < 0.5
    shown = mx(t) if truth else mp(w1 * w2, a1 * a2, b1 * b2)
    return _tf(f"{M(f'{mp(w1, a1, b1)} × {mp(w2, a2, b2)} = {shown}')}", truth, "ضرب الأجزاء كلاً على حدة",
               f"{M(f'{mp(w1, a1, b1)} × {mp(w2, a2, b2)} = {mx(t)}')}.", "حوّل إلى كسرين غير فعليين.")


@tpl(DV, 1, "dv_recip")
def _dv1_recip(r):
    a, b = proper(r, (3, 4, 5, 7, 8, 9))
    while a == 1:
        a, b = proper(r, (3, 4, 5, 7, 8, 9))
    return _q(f"ما مقلوب الكسر {E(f(a, b))}؟ (اكتبه على الصورة بسط/مقام)", f(b, a),
              [(f(a, b), "لم يقلب الكسر"), (f"{MINUS}{a}/{b}", "خلط بين المقلوب والمعكوس الجمعي"), (f(b - a, b), "أخذ المتمم إلى الواحد")],
              f"{M(f'مقلوب {a}/{b} هو {b}/{a}')}.", "بدّل البسط والمقام.", "input")


@tpl(DV, 1, "dv_frac")
def _dv1_frac(r):
    a, b = proper(r, (3, 4, 5, 6, 8))
    c, d = proper(r, (3, 4, 5, 6, 8))
    t = Fraction(a, b) / Fraction(c, d)
    return _q(f"أوجد ناتج القسمة. {SIMPLE}: {E(f(a, b), '÷', f(c, d))}", fr(t),
              [(fr(Fraction(a * c, b * d)), "ضرب بدل القسمة"), (fr(Fraction(b * c, a * d)), "قلب الكسر الأول بدل الثاني"), (f(a * d, b * c), "لم يبسّط الناتج")],
              f"{M(f'{a}/{b} ÷ {c}/{d} = {a}/{b} × {d}/{c} = {fr(t)}')}.", "اقلب الكسر الثاني فقط ثم اضرب.", "input")


@tpl(DV, 1, "dv_frac")
def _dv1_tf(r):
    a, b = proper(r, (3, 4, 5, 6, 8))
    c, d = proper(r, (3, 4, 5, 6, 8))
    truth = r.random() < 0.5
    shown = f"{a}/{b} × {d}/{c}" if truth else f"{a}/{b} × {c}/{d}"
    return _tf(f"{M(f'{a}/{b} ÷ {c}/{d} = {shown}')}", truth, "لم يقلب الكسر الثاني",
               f"{M(f'{a}/{b} ÷ {c}/{d} = {a}/{b} × {d}/{c}')}.", "القسمة تعني الضرب في المقلوب.")


@tpl(DV, 2, "dv_whole")
def _dv2_whole_by_frac(r):
    k = r.randint(2, 9)
    a, b = proper(r, (3, 4, 5, 8))
    t = Fraction(k) / Fraction(a, b)
    return _q(f"أوجد ناتج: {E(str(k), '÷', f(a, b))}", mx(t),
              [(mx(k * Fraction(a, b)), "ضرب بدل القسمة"), (mx(Fraction(a, b * k)), "قلب الترتيب"), (mx(Fraction(k, a * b)), "قسم على البسط والمقام")],
              f"{M(f'{k} ÷ {a}/{b} = {k} × {b}/{a} = {mx(t)}')}.", "اقلب الكسر ثم اضرب.")


@tpl(DV, 2, "dv_whole")
def _dv2_frac_by_whole(r):
    a, b = proper(r, (3, 4, 5, 7, 8))
    k = r.randint(2, 6)
    t = Fraction(a, b) / k
    return _q(f"أوجد ناتج القسمة. {SIMPLE}: {E(f(a, b), '÷', str(k))}", fr(t),
              [(fr(Fraction(a * k, b)), "ضرب بدل القسمة"), (fr(Fraction(k, a * b)), "قلب العدد الصحيح فقط"), (f(a, b * k * k), "ضرب المقام في العدد مرتين")],
              f"{M(f'{a}/{b} ÷ {k} = {a}/{b} × 1/{k} = {fr(t)}')}.", "العدد الصحيح كسر مقامه 1.", "input")


@tpl(DV, 2, "dv_mixed")
def _dv2_mixed_whole(r):
    w, a, d = mixed(r, (2, 3, 4, 5, 8))
    k = r.randint(2, 6)
    t = val(w, a, d) / k
    return _q(f"أوجد ناتج: {E(mp(w, a, d), '÷', str(k))}", mx(t),
              [(mx(val(w, a, d) * k), "ضرب بدل القسمة"), (mx(Fraction(w, k) + Fraction(a, d)), "قسم الجزء الصحيح فقط"),
               (mx(Fraction(k) / val(w, a, d)), "قلب الترتيب")],
              f"{M(f'{mp(w, a, d)} ÷ {k} = {w * d + a}/{d} × 1/{k} = {mx(t)}')}.", "حوّل إلى كسر غير فعلي ثم اقلب العدد.")


@tpl(DV, 2, "dv_context")
def _dv2_pieces(r):
    k = r.randint(2, 9)
    a, b = proper(r, (3, 4, 5, 8))
    t = Fraction(k) / Fraction(a, b)
    return _q(f"حبل طوله {k} أمتار يُقطع إلى قطع طول كل منها {L(f(a, b))} م. كم قطعة نحصل عليها؟", mx(t),
              [(mx(k * Fraction(a, b)), "ضرب بدل القسمة"), (mx(Fraction(a, b * k)), "قلب الترتيب"), (mx(Fraction(k) - Fraction(a, b)), "طرح بدل القسمة")],
              f"{M(f'{k} ÷ {a}/{b} = {mx(t)}')} قطعة.", "كم قطعة تعني قسمة الكل على حجم القطعة.")


@tpl(DV, 3, "dv_mixed")
def _dv3_mixed(r):
    w1, a1, b1 = mixed(r, (2, 3, 4, 5))
    w2, a2, b2 = mixed(r, (2, 3, 4, 5))
    t = val(w1, a1, b1) / val(w2, a2, b2)
    return _q(f"أوجد ناتج: {E(mp(w1, a1, b1), '÷', mp(w2, a2, b2))}", mx(t),
              [(mx(val(w1, a1, b1) * val(w2, a2, b2)), "ضرب بدل القسمة"), (mx(val(w2, a2, b2) / val(w1, a1, b1)), "قلب الترتيب"),
               (mx(val(w1, a1, b1) / Fraction(a2, b2)), "نسي تحويل العدد الثاني")],
              f"{M(f'{w1 * b1 + a1}/{b1} ÷ {w2 * b2 + a2}/{b2} = {w1 * b1 + a1}/{b1} × {b2}/{w2 * b2 + a2} = {mx(t)}')}.", "حوّل العددين ثم اقلب الثاني فقط.")


@tpl(DV, 3, "dv_context")
def _dv3_cups(r):
    w, a, b = mixed(r, (2, 4, 5))
    c, d = proper(r, (3, 4, 5, 8))
    t = val(w, a, b) / Fraction(c, d)
    return _q(f"في عبوة {L(mp(w, a, b))} لتر عصير نوزعه في أكواب سعة كل منها {L(f(c, d))} لتر. كم كوباً نملأ؟", mx(t),
              [(mx(val(w, a, b) * Fraction(c, d)), "ضرب بدل القسمة"), (mx(Fraction(c, d) / val(w, a, b)), "قلب الترتيب"), (mx(val(w, a, b) - Fraction(c, d)), "طرح بدل القسمة")],
              f"{M(f'{mp(w, a, b)} ÷ {c}/{d} = {mx(t)}')} كوب.", "كم كوباً تعني القسمة.")


@tpl(DV, 3, "dv_mixed")
def _dv3_tf(r):
    w1, a1, b1 = mixed(r, (2, 3, 4, 5))
    w2, a2, b2 = mixed(r, (2, 3, 4, 5))
    t = val(w1, a1, b1) / val(w2, a2, b2)
    truth = r.random() < 0.5
    shown = mx(t) if truth else mx(val(w1, a1, b1) * val(w2, a2, b2))
    return _tf(f"{M(f'{mp(w1, a1, b1)} ÷ {mp(w2, a2, b2)} = {shown}')}", truth, "ضرب بدل القسمة",
               f"{M(f'{mp(w1, a1, b1)} ÷ {mp(w2, a2, b2)} = {mx(t)}')}.", "اقلب الثاني ثم اضرب.")


@tpl(DV, 3, "dv_frac")
def _dv3_missing(r):
    a, b = proper(r, (3, 4, 5, 8))
    c, d = proper(r, (3, 4, 5, 8))
    t = Fraction(c, d) / Fraction(a, b)
    return _q(f"أوجد الكسر الناقص: {E('؟', '×', f(a, b), '=', f(c, d))}", mx(t),
              [(mx(Fraction(c, d) * Fraction(a, b)), "ضرب بدل القسمة"), (mx(Fraction(a, b) / Fraction(c, d)), "قلب الترتيب"), (mx(Fraction(c, d) - Fraction(a, b) if Fraction(c, d) > Fraction(a, b) else Fraction(c, d) + Fraction(a, b)), "جمع أو طرح بدل القسمة")],
              f"{M(f'{c}/{d} ÷ {a}/{b} = {mx(t)}')}.", "الضرب عكسه القسمة.")
