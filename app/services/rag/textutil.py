import re

_TASHKEEL = re.compile("[\u064B-\u065F\u0670\u0640]")
_REPLACE = {"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"}


def ar_norm(text: str) -> str:
    t = _TASHKEEL.sub("", text or "")
    for src, dst in _REPLACE.items():
        t = t.replace(src, dst)
    return t.lower()


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"\w+", ar_norm(text)) if len(w) > 1]
