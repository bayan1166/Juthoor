import math
import re
from fractions import Fraction

from app.engine import knowledge_graph as kg
from app.services import curriculum_map as cur
from app.services.rag.textutil import ar_norm
from app.services.rag.turn import SocraticTurn

LRI = "\u2066"
PDI = "\u2069"
MINUS = "\u2212"
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


class ParseError(Exception):
    pass


class NotInteger(Exception):
    pass


def iso(text) -> str:
    return f"{LRI}{text}{PDI}"


def fmt(n: int) -> str:
    return str(n).replace("-", MINUS)


def fmt_p(n: int) -> str:
    return f"({fmt(n)})" if n < 0 else fmt(n)


def normalize(text: str) -> str:
    t = (text or "").translate(_DIGITS)
    for ch in ("\u2212", "\u2013", "\u2014", "\u2012", "\uFE63", "\uFF0D"):
        t = t.replace(ch, "-")
    for ch in ("\u00D7", "\u00B7", "\u2217", "\u22C5"):
        t = t.replace(ch, "*")
    t = t.replace("\u00F7", "/").replace("\uFF0B", "+")
    t = re.sub(r"(?<=\d)\s*[xX]\s*(?=[\d(\-])", "*", t)
    t = re.sub(r"(?<=\d)\s*في\s*(?=[\d(\-])", " * ", t)
    t = re.sub(r"\s*(زائد|زايد)\s*", " + ", t)
    t = re.sub(r"\s*ناقص\s*", " - ", t)
    t = re.sub(r"\s*(مضروبا? في|مضروب في|ضرب)\s*", " * ", t)
    t = re.sub(r"\s*(مقسوما? على|مقسوم على|قسمة)\s*", " / ", t)
    return t


def tokenize(s: str) -> list[tuple]:
    out: list[tuple] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c.isdigit():
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            if j - i > 6:
                raise ParseError("big")
            out.append(("num", int(s[i:j])))
            i = j
            continue
        if c in "+-*/()|":
            out.append((c, c))
            i += 1
            continue
        raise ParseError("char")
    if len(out) > 40:
        raise ParseError("long")
    return out


class _Parser:
    def __init__(self, tokens: list[tuple]):
        self.t = tokens
        self.i = 0

    def peek(self):
        return self.t[self.i][0] if self.i < len(self.t) else None

    def take(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def parse(self):
        node = self.expr()
        if self.i != len(self.t):
            raise ParseError("trailing")
        return node

    def expr(self):
        node = self.term()
        while self.peek() in ("+", "-"):
            op = self.take()[0]
            node = ("bin", op, node, self.term())
        return node

    def term(self):
        node = self.factor()
        while self.peek() in ("*", "/"):
            op = self.take()[0]
            node = ("bin", op, node, self.factor())
        return node

    def factor(self):
        p = self.peek()
        if p in ("+", "-"):
            self.take()
            inner = self.factor()
            return ("neg", inner) if p == "-" else inner
        if p == "num":
            return ("num", self.take()[1])
        if p == "(":
            self.take()
            node = self.expr()
            if self.peek() != ")":
                raise ParseError("paren")
            self.take()
            return node
        if p == "|":
            self.take()
            node = self.expr()
            if self.peek() != "|":
                raise ParseError("bar")
            self.take()
            return ("abs", node)
        raise ParseError("factor")


_RUN = re.compile(r"[\d()|+\-*/\s]+")


def _candidates(run: str):
    s = run.strip()
    yield s
    t = s.rstrip("+-*/( ")
    if t != s:
        yield t
    u = t.lstrip("*/) ")
    if u != t:
        yield u


def find_expression(text: str):
    norm = normalize(text)
    best = None
    for found in _RUN.finditer(norm):
        for cand in _candidates(found.group()):
            if not cand:
                continue
            nums = re.findall(r"\d+", cand)
            bars = cand.count("|")
            has_op = bool(re.search(r"[+*/]", cand)) or bool(re.search(r"[\d)|]\s*-\s*[\d(|]", cand)) or bars >= 2
            if not nums or not has_op:
                continue
            if len(nums) < 2 and bars < 2:
                continue
            try:
                tree = _Parser(tokenize(cand)).parse()
            except ParseError:
                continue
            if best is None or len(cand) > len(best[0]):
                best = (cand, tree)
            break
    return best


def _add_rule(a: int, b: int, r: int) -> str:
    if a == 0 or b == 0:
        return "الصفر لا يغيّر قيمة العدد."
    if (a > 0) == (b > 0):
        total = abs(a) + abs(b)
        return f"الإشارتان متشابهتان، فنجمع القيمتين المطلقتين {iso(f'{abs(a)} + {abs(b)} = {total}')} ونُبقي الإشارة نفسها."
    big, small = max(abs(a), abs(b)), min(abs(a), abs(b))
    if r == 0:
        return "العددان متقابلان (معكوسان)، فمجموعهما صفر."
    far = a if abs(a) > abs(b) else b
    side = "موجب" if far > 0 else "سالب"
    return (f"الإشارتان مختلفتان، فنطرح الأصغر من الأكبر بالقيمة المطلقة {iso(f'{big} {MINUS} {small} = {big - small}')} "
            f"ونأخذ إشارة العدد الأبعد عن الصفر وهو {side}.")


def _mul_rule(a: int, b: int) -> str:
    if a == 0 or b == 0:
        return "أي عدد مضروب في صفر يساوي صفراً."
    mag = iso(f"{abs(a)} \u00D7 {abs(b)} = {abs(a) * abs(b)}")
    if (a > 0) == (b > 0):
        return f"إشارتان متشابهتان تعطيان ناتجاً موجباً: {mag}."
    return f"إشارتان مختلفتان تعطيان ناتجاً سالباً: {mag} ثم نضع الإشارة السالبة."


def _div_rule(a: int, b: int) -> str:
    if a == 0:
        return "الصفر مقسوماً على أي عدد غير صفري يساوي صفراً."
    mag = iso(f"{abs(a)} \u00F7 {abs(b)} = {abs(a) // abs(b)}")
    if (a > 0) == (b > 0):
        return f"إشارتان متشابهتان تعطيان ناتجاً موجباً: {mag}."
    return f"إشارتان مختلفتان تعطيان ناتجاً سالباً: {mag} ثم نضع الإشارة السالبة."


def evaluate(node, steps: list[str]) -> int:
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "neg":
        return -evaluate(node[1], steps)
    if kind == "abs":
        v = evaluate(node[1], steps)
        r = abs(v)
        steps.append(f"القيمة المطلقة هي بُعد العدد عن الصفر فلا تكون سالبة: {iso(f'|{fmt(v)}| = {fmt(r)}')}")
        return r
    _, op, left, right = node
    a = evaluate(left, steps)
    b = evaluate(right, steps)
    if op == "+":
        r = a + b
        steps.append(f"{iso(f'{fmt(a)} + {fmt_p(b)} = {fmt(r)}')}: {_add_rule(a, b, r)}")
    elif op == "-":
        r = a - b
        steps.append(f"{iso(f'{fmt(a)} {MINUS} {fmt_p(b)} = {fmt(r)}')}: نحوّل الطرح إلى جمع معكوس العدد الثاني، "
                     f"أي {iso(f'{fmt(a)} + {fmt_p(-b)}')}. {_add_rule(a, -b, r)}")
    elif op == "*":
        r = a * b
        steps.append(f"{iso(f'{fmt(a)} × {fmt_p(b)} = {fmt(r)}')}: {_mul_rule(a, b)}")
    else:
        if b == 0:
            raise ParseError("zero")
        if a % b != 0:
            raise NotInteger()
        r = a // b
        steps.append(f"{iso(f'{fmt(a)} ÷ {fmt_p(b)} = {fmt(r)}')}: {_div_rule(a, b)}")
    return r


def solve_lines(expr_text: str):
    found = find_expression(expr_text)
    if not found:
        return None
    steps: list[str] = []
    try:
        result = evaluate(found[1], steps)
    except ParseError:
        return (["لا يمكن القسمة على صفر."], None, found)
    except NotInteger:
        return (["ناتج القسمة ليس عدداً صحيحاً، وهذا خارج نطاق دروس الأعداد الصحيحة."], None, found)
    if not steps:
        return None
    return (steps, result, found)


def solve_reply(text: str):
    solved = solve_lines(text)
    if solved is None:
        return None
    steps, result, _ = solved
    if result is None:
        return steps[0]
    lines = ["لنحلّ المسألة خطوة بخطوة:"]
    lines += [f"{i}) {step}" for i, step in enumerate(steps, 1)]
    lines.append(f"الناتج النهائي: {iso(fmt(result))}")
    lines.append("اكتب «مسألة» لأعطيك تمريناً مشابهاً، أو اسألني عن أي خطوة لم تتضح.")
    return "\n".join(lines)


def solution_hint(text: str) -> str:
    frac = solve_fraction(text)
    if frac is not None and frac[1] is not None:
        return f"الناتج الصحيح: {fr_text(frac[1])} | خطوات التحقق: " + " / ".join(frac[0])
    solved = solve_lines(text)
    if solved is None or solved[1] is None:
        return ""
    steps, result, found = solved
    return f"التعبير: {found[0]} | الناتج الصحيح: {result} | خطوات التحقق: " + " / ".join(steps)


def compare_reply(a: int, b: int) -> str:
    if a == b:
        return f"العددان {iso(fmt(a))} و {iso(fmt(b))} متساويان."
    bigger, smaller = (a, b) if a > b else (b, a)
    lines = ["على خط الأعداد، العدد الأبعد إلى اليمين هو الأكبر."]
    if a < 0 and b < 0:
        lines.append(f"العددان سالبان، فالأصغر في القيمة المطلقة هو الأكبر: {iso(f'|{fmt(a)}| = {abs(a)}')} و {iso(f'|{fmt(b)}| = {abs(b)}')}.")
    elif a >= 0 and b >= 0:
        lines.append("العددان موجبان، فالأكبر في القيمة المطلقة هو الأكبر.")
    else:
        lines.append("أي عدد موجب أكبر من أي عدد سالب، والصفر أكبر من كل عدد سالب.")
    lines.append(f"إذن {iso(fmt(bigger))} أكبر من {iso(fmt(smaller))}.")
    return "\n".join(lines)


_FR_TOKEN = r"\d+(?:\s*/\s*\d+)?"
_FR_EXPR = re.compile(rf"({_FR_TOKEN})\s*([+\-*:])\s*({_FR_TOKEN})")


def display_fr(expr: str) -> str:
    return expr.replace("-", MINUS).replace("*", "\u00D7").replace(":", "\u00F7")


def fr_text(value: Fraction) -> str:
    sign = MINUS if value < 0 else ""
    value = abs(value)
    body = str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
    return sign + body


def _fr_value(token: str):
    parts = [int(x) for x in re.split(r"\s*/\s*", token.strip())]
    if len(parts) == 2:
        if parts[1] == 0:
            return None
        return Fraction(parts[0], parts[1])
    return Fraction(parts[0])


def _fr_parts(token: str):
    parts = [int(x) for x in re.split(r"\s*/\s*", token.strip())]
    return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], 1)


def find_fraction_expression(text: str):
    norm = normalize(text.replace("\u00F7", ":")).replace("x", "*")
    for found in _FR_EXPR.finditer(norm):
        if "/" in found.group(1) or "/" in found.group(3):
            return found.group(1), found.group(2), found.group(3)
    return None


def solve_fraction(expr: str):
    found = find_fraction_expression(expr)
    if found is None:
        return None
    left, op, right = found
    a, b = _fr_value(left), _fr_value(right)
    if a is None or b is None:
        return ["لا يمكن أن يكون المقام صفراً."], None
    (na, da), (nb, db) = _fr_parts(left), _fr_parts(right)
    steps: list[str] = []
    if op in "+-":
        word = "نجمع" if op == "+" else "نطرح"
        sign = "+" if op == "+" else MINUS
        if da == db:
            raw_n = na + nb if op == "+" else na - nb
            steps.append(f"المقامان متساويان، نُبقي المقام {iso(da)} و{word} البسطين: {iso(f'{na} {sign} {nb} = {fmt(raw_n)}')}.")
            raw = Fraction(raw_n, da)
        else:
            lcd = da * db // math.gcd(da, db)
            ma, mb = lcd // da, lcd // db
            steps.append(f"نوحّد المقامين، المقام المشترك الأصغر {iso(lcd)}: {iso(f'{na * ma}/{lcd}')} و{iso(f'{nb * mb}/{lcd}')}.")
            raw_n = na * ma + nb * mb if op == "+" else na * ma - nb * mb
            steps.append(f"{word} البسطين: {iso(f'{na * ma} {sign} {nb * mb} = {fmt(raw_n)}')} فيصبح الناتج {iso(f'{fmt(raw_n)}/{lcd}')}.")
            raw = Fraction(raw_n, lcd)
        result = raw
        shown = f"{fmt(raw_n)}/{raw.denominator if da == db else lcd}"
    elif op == "*":
        steps.append(f"نضرب البسطين ونضرب المقامين: {iso(f'({na}×{nb})/({da}×{db}) = {na * nb}/{da * db}')}.")
        result = a * b
        shown = f"{na * nb}/{da * db}"
    else:
        if b == 0:
            return ["لا يمكن القسمة على صفر."], None
        steps.append(f"القسمة تعني الضرب في مقلوب الكسر الثاني: {iso(f'{left} ÷ {right} = {left} × {db}/{nb}')}.")
        steps.append(f"نضرب البسطين والمقامين: {iso(f'{na * db}/{da * nb}')}.")
        result = a / b
        shown = f"{na * db}/{da * nb}"
    simple = fr_text(result)
    if shown.replace(MINUS, "-") != simple.replace(MINUS, "-"):
        steps.append(f"نبسّط الناتج بالقسمة على العامل المشترك: {iso(simple)}.")
    return steps, result


def fraction_reply(text: str):
    solved = solve_fraction(text)
    if solved is None:
        return None
    steps, result = solved
    found = find_fraction_expression(text)
    head = f"سأحلّ لك {iso(display_fr(' '.join(found)))} خطوة بخطوة:"
    if result is None:
        return head + "\n" + "\n".join(steps)
    lines = [head] + [f"{i}) {s}" for i, s in enumerate(steps, 1)]
    lines.append(f"الناتج: {iso(fr_text(result))}")
    return "\n".join(lines)


def parse_fraction_answer(message: str):
    norm = normalize(message.replace("\u00F7", ":")).strip()
    found = re.fullmatch(r"(-?)\s*(\d+)\s*(?:/\s*(\d+))?", norm)
    if not found or len(norm) > 20:
        return None
    den = int(found.group(3)) if found.group(3) else 1
    if den == 0:
        return None
    value = Fraction(int(found.group(2)), den)
    return -value if found.group(1) else value


EXAMPLE_FR = {
    "fractions_addsub": "1/2 + 1/3",
    "mixed_addsub": "7/4 + 5/6",
    "mixed_mult": "5/2 * 3/4",
    "mixed_div": "3/2 : 3/4",
}

FR_POOL = {
    "fractions_addsub": ["1/2 + 1/3", "3/4 - 1/2", "2/5 + 1/5", "5/6 - 1/3", "1/4 + 2/3", "7/8 - 3/4"],
    "mixed_addsub": ["7/4 + 5/6", "11/4 - 3/2", "7/3 + 2/3", "13/5 - 4/5", "9/4 + 5/8", "17/6 - 3/4"],
    "mixed_mult": ["5/2 * 3/4", "1/2 * 6", "5/4 * 2/3", "3 * 2/5", "7/3 * 3/4", "9/4 * 2/3"],
    "mixed_div": ["3/2 : 3/4", "3 : 1/4", "3/4 : 2", "5/6 : 5/12", "7/2 : 7/4", "2/3 : 4/5"],
}

EXAMPLE_EXPR = {
    "absolute_value": "|-7| + |3|",
    "adding_integers": "(-4) + 9",
    "subtracting_integers": "3 - (-5)",
    "mult_div_integers": "(-6) * 4",
}

POOL = {
    "absolute_value": ["|-9|", "|5|", "|-12| + |3|", "|-4| * 2"],
    "adding_integers": ["5 + (-2)", "(-4) + 9", "(-6) + (-3)", "8 + (-8)", "(-7) + 3", "12 + (-5)"],
    "subtracting_integers": ["3 - 7", "5 - (-2)", "(-4) - (-6)", "0 - 9", "(-8) - 3", "6 - (-6)"],
    "mult_div_integers": ["(-6) * 4", "(-3) * (-5)", "20 / (-4)", "(-18) / (-3)", "7 * (-2)", "(-24) / 6"],
    "comparing_integers": ["CMP:-3,-8", "CMP:-1,2", "CMP:-5,-2", "CMP:0,-4", "CMP:-9,-10"],
}

KEYWORDS = {
    "fractions_addsub": ["كسر", "كسور", "مقام", "بسط"],
    "mixed_addsub": ["عدد كسري", "اعداد كسريه", "كسري"],
    "mixed_mult": ["ضرب الكسور", "ضرب كسر", "ضرب الاعداد الكسريه"],
    "mixed_div": ["قسمه الكسور", "قسمه كسر", "مقلوب", "قسمه الاعداد الكسريه"],
    "absolute_value": ["القيمة المطلقة", "قيمة مطلقة", "مطلقة", "معكوس", "خط الاعداد"],
    "comparing_integers": ["قارن", "مقارنة", "اكبر", "اصغر", "ترتيب"],
    "adding_integers": ["جمع", "اجمع", "زائد"],
    "subtracting_integers": ["طرح", "اطرح", "ناقص"],
    "mult_div_integers": ["ضرب", "قسمة", "اضرب", "اقسم"],
}

EXPLAIN_WORDS = ["اشرح", "شرح", "فسر", "وضح", "ما هو", "ما هي", "ما معني", "كيف", "علمني", "ايش", "شو يعني", "كيف احسب", "كيف اجمع", "كيف اطرح", "كيف اضرب", "كيف اقسم", "كيف احل"]
STUCK_WORDS = ["مش فاهم", "ما فهمت", "لم افهم", "لا افهم", "صعب", "عالق", "علقت", "ما عرفت", "لم اعرف", "ما بعرف", "مو فاهم", "محتار", "مش عارف"]
PRACTICE_WORDS = ["اختبرني", "تمرين", "مساله جديده", "اعطني مساله", "سؤال جديد", "جربني", "مسالة", "مساله"]
THANKS_WORDS = ["شكرا", "يسلمو", "مشكور", "ممنون"]
GREET_WORDS = ["مرحبا", "اهلا", "السلام", "هلا", "صباح", "مساء"]

_Q_EXPR = re.compile("كم ناتج\\s*\u2066(.+?)\u2069")
_Q_CMP = re.compile("أيهما أكبر:\\s*\u2066(.+?)\u2069\\s*أم\\s*\u2066(.+?)\u2069")
WRONG_MARK = "ليست صحيحة"


def _has(nm: str, words: list[str]) -> bool:
    return any(ar_norm(w) in nm for w in words)


def _iso_math(text: str) -> str:
    return re.sub(r"\[\[(.+?)\]\]", lambda m: iso(m.group(1)), text)


def display_expr(expr: str) -> str:
    return expr.replace("-", MINUS).replace("*", "\u00D7").replace("/", "\u00F7")


def question_text(item: str) -> str:
    if item.startswith("CMP:"):
        a, b = (int(x) for x in item[4:].split(","))
        return f"أيهما أكبر: {iso(fmt(a))} أم {iso(fmt(b))}؟"
    if item.startswith("FR:"):
        return f"كم ناتج {iso(display_fr(item[3:]))}؟ (اكتب الجواب كسراً في أبسط صورة، مثل 3/4)"
    return f"كم ناتج {iso(display_expr(item))}؟"


def _diag_count(history: list[dict]) -> int:
    return sum(1 for h in history if h["role"] == "tutor" and (_Q_EXPR.search(h["content"]) or _Q_CMP.search(h["content"])))


def _next_practice(ctx: str, history: list[dict]) -> str:
    if ctx in FR_POOL:
        pool = ["FR:" + item for item in FR_POOL[ctx]]
    else:
        pool = POOL.get(ctx) or POOL["adding_integers"]
    return question_text(pool[_diag_count(history) % len(pool)])


def pending_question(history: list[dict]):
    for h in reversed(history):
        if h["role"] != "tutor":
            continue
        content = h["content"]
        cmp_found = _Q_CMP.search(content)
        if cmp_found:
            try:
                a = int(normalize(cmp_found.group(1)).replace(" ", ""))
                b = int(normalize(cmp_found.group(2)).replace(" ", ""))
            except ValueError:
                return None
            return ("cmp", a, b)
        expr_found = _Q_EXPR.search(content)
        if expr_found:
            fsolved = solve_fraction(expr_found.group(1))
            if fsolved and fsolved[1] is not None:
                return ("frac", expr_found.group(1), fsolved)
            solved = solve_lines(expr_found.group(1))
            if solved and solved[1] is not None:
                return ("expr", expr_found.group(1), solved)
        return None
    return None


def parse_int_answer(message: str):
    norm = normalize(message)
    nums = re.findall(r"[+-]?\s*\d+", norm)
    if len(nums) == 1 and len(norm) <= 40:
        try:
            return int(nums[0].replace(" ", ""))
        except ValueError:
            return None
    return None


def _binary_parts(tree):
    if tree[0] != "bin":
        return None
    try:
        return tree[1], evaluate(tree[2], []), evaluate(tree[3], [])
    except (ParseError, NotInteger):
        return None


def _misconception(tree, answer: int, value: int) -> str:
    parts = _binary_parts(tree)
    if parts is None:
        return ""
    op, a, b = parts
    if op == "+" and a != 0 and b != 0 and (a > 0) != (b > 0) and abs(answer) == abs(a) + abs(b):
        return "يبدو أنك جمعت القيمتين المطلقتين رغم اختلاف إشارتي العددين."
    if op == "-" and answer == a + b:
        return "يبدو أنك تعاملت مع الطرح كأنه جمع، بدل جمع معكوس العدد الثاني."
    if answer == -value and value != 0:
        if op in ("*", "/"):
            return "تذكّر: إشارتان متشابهتان تعطيان ناتجاً موجباً، ومختلفتان تعطيان ناتجاً سالباً."
        return "يبدو أن إشارة الناتج انعكست، راجع الإشارة في النهاية."
    return ""


def _turn(reply: str, gap: str = "", misconception: str = "") -> SocraticTurn:
    return SocraticTurn(reply=reply, gap_detected=bool(gap), gap_skill=gap, misconception=misconception, retrieved_ids=[])


def _gap_for_repeated_miss(ctx: str, history: list[dict]) -> str:
    if any(h["role"] == "tutor" and "أسئلة تأسيسية" in h["content"] for h in history):
        return ""
    misses = sum(1 for h in history if h["role"] == "tutor" and WRONG_MARK in h["content"])
    prereqs = kg.prerequisites(ctx) if ctx in kg.SKILLS else []
    if misses + 1 >= 2 and prereqs:
        return prereqs[0]
    return ""


def _grade_pending(ctx: str, history: list[dict], pending, answer: int) -> SocraticTurn:
    kind = pending[0]
    if kind == "cmp":
        expected = max(pending[1], pending[2])
        ok = answer == expected
        explain = compare_reply(pending[1], pending[2])
        tree = None
    else:
        steps, expected, found = pending[2]
        ok = answer == expected
        tree = found[1]
        explain = "\n".join(f"{i}) {s}" for i, s in enumerate(steps, 1))
    nxt = _next_practice(ctx, history)
    if ok:
        return _turn(f"إجابة صحيحة، {iso(fmt(expected))} هو الناتج فعلاً. أحسنت.\nجرّب هذا التمرين: {nxt}")
    note = _misconception(tree, answer, expected) if tree is not None else ""
    lines = [f"إجابتك {iso(fmt(answer))} {WRONG_MARK}، والصواب {iso(fmt(expected))}."]
    if note:
        lines.append(note)
    lines.append("هذا هو الحل خطوة بخطوة:")
    lines.append(explain)
    gap = _gap_for_repeated_miss(ctx, history)
    if gap:
        lines.append(f"لاحظت أن الأساس قد يحتاج تثبيتاً في «{kg.SKILLS[gap].name_ar}»، وأضفت لك أسئلة تأسيسية عليه في صفحة التدريب.")
    else:
        lines.append(f"جرّب تمريناً آخر: {nxt}")
    return _turn("\n".join(lines), gap, note)


def _fraction_note(expr: str, answer: Fraction) -> str:
    found = find_fraction_expression(expr)
    if found is None:
        return ""
    left, op, right = found
    a, b = _fr_value(left), _fr_value(right)
    (na, da), (nb, db) = _fr_parts(left), _fr_parts(right)
    if op in "+-" and da != db and answer == Fraction(na + nb if op == "+" else na - nb, da + db):
        return "يبدو أنك جمعت أو طرحت البسطين والمقامين معاً، والصحيح أن نوحّد المقامين أولاً ثم نعمل على البسطين فقط."
    if op in "+-" and da == db and answer == Fraction(na + nb if op == "+" else na - nb, da + db):
        return "عند تساوي المقامين نُبقي المقام كما هو ولا نجمعه."
    if op == ":" and b != 0 and answer == a * b:
        return "يبدو أنك ضربت بدل أن تقسم، تذكّر أن نقلب الكسر الثاني قبل الضرب."
    if op == ":" and a != 0 and answer == b / a:
        return "يبدو أنك قلبت الكسر الأول بدل الثاني."
    if op == "*" and b != 0 and answer == a / b:
        return "يبدو أنك قسمت بدل أن تضرب."
    return ""


def _grade_fraction(ctx: str, history: list[dict], pending, answer: Fraction, message: str) -> SocraticTurn:
    steps, expected = pending[2]
    nxt = _next_practice(ctx, history)
    if answer == expected:
        simple = fr_text(expected)
        raw = normalize(message).replace(" ", "")
        extra = f" يمكنك كتابته في أبسط صورة هكذا: {iso(simple)}." if raw.lstrip("-") != simple.lstrip(MINUS) else ""
        return _turn(f"إجابة صحيحة، {iso(simple)} هو الناتج فعلاً.{extra} أحسنت.\nجرّب هذا التمرين: {nxt}")
    note = _fraction_note(pending[1], answer)
    lines = [f"إجابتك {iso(fr_text(answer))} {WRONG_MARK}، والصواب {iso(fr_text(expected))}."]
    if note:
        lines.append(note)
    lines.append("هذا هو الحل خطوة بخطوة:")
    lines += [f"{i}) {step}" for i, step in enumerate(steps, 1)]
    gap = _gap_for_repeated_miss(ctx, history)
    if gap:
        lines.append(f"لاحظت أن الأساس قد يحتاج تثبيتاً في «{kg.SKILLS[gap].name_ar}»، وأضفت لك أسئلة تأسيسية عليه في صفحة التدريب.")
    else:
        lines.append(f"جرّب تمريناً آخر: {nxt}")
    return _turn("\n".join(lines), gap, note)


def explain_reply(skill_id: str) -> str:
    found = cur.find_by_skill(skill_id)
    if not found:
        return "اكتب لي المسألة التي تريد حلّها، أو اسألني عن أحد دروس الأعداد الصحيحة."
    unit, lesson = found
    concepts = cur.concepts_for(cur.lesson_key(unit, lesson))
    lines = [f"سأشرح لك «{lesson.title}» باختصار:"]
    for concept in concepts[:3]:
        lines.append(f"- {concept.title}: {_iso_math(concept.text)}")
    expr = EXAMPLE_EXPR.get(skill_id)
    if expr:
        solved = solve_lines(expr)
        if solved and solved[1] is not None:
            lines.append(f"مثال محلول: {iso(display_expr(expr))}")
            lines += [f"{i}) {s}" for i, s in enumerate(solved[0], 1)]
            lines.append(f"الناتج: {iso(fmt(solved[1]))}")
    elif skill_id in EXAMPLE_FR:
        solved = solve_fraction(EXAMPLE_FR[skill_id])
        if solved and solved[1] is not None:
            lines.append(f"مثال محلول: {iso(display_fr(EXAMPLE_FR[skill_id]))}")
            lines += [f"{i}) {step}" for i, step in enumerate(solved[0], 1)]
            lines.append(f"الناتج: {iso(fr_text(solved[1]))}")
    elif skill_id == "comparing_integers":
        lines.append("مثال محلول:")
        lines.append(compare_reply(-3, -8))
    lines.append("هل تريد تمريناً للتجربة؟ اكتب «مسألة».")
    return "\n".join(lines)


def _mentioned(nm: str) -> list[str]:
    return [sid for sid, words in KEYWORDS.items() if _has(nm, words)]


def _target_skill(nm: str, ctx: str) -> str:
    if _has(nm, KEYWORDS.get(ctx, [])):
        return ctx
    mentioned = _mentioned(nm)
    return mentioned[0] if mentioned else ctx


def _compare_numbers(message: str, nm: str):
    if not _has(nm, KEYWORDS["comparing_integers"]):
        return None
    nums = re.findall(r"-?\d+", normalize(message))
    if len(nums) >= 2:
        return int(nums[0]), int(nums[1])
    return None


def offline_turn(skill_context: str, history: list[dict], message: str) -> SocraticTurn:
    ctx = skill_context if skill_context in kg.SKILLS else "adding_integers"
    nm = ar_norm(message)

    pending = pending_question(history)
    if pending is not None and pending[0] == "frac":
        frac_answer = parse_fraction_answer(message)
        if frac_answer is not None:
            return _grade_fraction(ctx, history, pending, frac_answer, message)
    elif pending is not None:
        answer = parse_int_answer(message)
        if answer is not None:
            return _grade_pending(ctx, history, pending, answer)

    frac_solved = fraction_reply(message)
    if frac_solved:
        return _turn(frac_solved)

    solved = solve_reply(message)
    if solved:
        return _turn(solved)

    pair = _compare_numbers(message, nm)
    if pair:
        return _turn(compare_reply(*pair))

    if _has(nm, STUCK_WORDS):
        ancestors = kg.ancestors(ctx) if ctx in kg.SKILLS else set()
        for sid in _mentioned(nm):
            if sid in ancestors:
                name = kg.SKILLS[sid].name_ar
                reply = (f"لاحظت أن الصعوبة تبدأ من «{name}». أضفت لك أسئلة تأسيسية عليه في صفحة التدريب، "
                         f"وهذا شرح سريع له:\n{explain_reply(sid)}")
                return _turn(reply, sid, f"صعوبة في {name}")
        return _turn("لا بأس، سنشخّص أين تتعثّر. جرّب هذا التمرين وأخبرني بجوابك، "
                     "أو اكتب «اشرح» لأشرح لك الفكرة أولاً.\n" + _next_practice(ctx, history))

    if _has(nm, EXPLAIN_WORDS):
        return _turn(explain_reply(_target_skill(nm, ctx)))

    if _has(nm, PRACTICE_WORDS):
        return _turn("تمرين جديد لك: " + _next_practice(ctx, history))

    if _has(nm, THANKS_WORDS):
        return _turn("على الرحب والسعة. اكتب «مسألة» إن أردت تمريناً جديداً.")

    if _has(nm, GREET_WORDS):
        return _turn("أهلاً بك. أستطيع أن أشرح لك الدرس، أو أحلّ معك أي مسألة خطوة بخطوة، أو أختبرك بتمرين. ماذا تفضّل؟")

    found = cur.find_by_skill(ctx)
    lesson_title = found[1].title if found else "الدرس"
    return _turn("لم أتمكن من فهم المطلوب بدقة. جرّب أحد الأشكال التالية:\n"
                 f"- اكتب مسألة مثل {iso(display_fr(EXAMPLE_FR[ctx]) if ctx in EXAMPLE_FR else '7 + (' + MINUS + '3)')} لأحلّها لك خطوة بخطوة.\n"
                 f"- اكتب «اشرح لي {lesson_title}».\n"
                 "- اكتب «مسألة» لأختبرك بتمرين.")
