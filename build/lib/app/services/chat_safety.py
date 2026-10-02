import re

_DIGITS = str.maketrans("\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9", "01234567890123456789")
_URL = re.compile(r"(https?://|www\.|\b[\w-]+\.(?:com|net|org|io|me|app|jo|tv|gg|ly|co|info|xyz)\b)", re.I)
_EMAIL = re.compile(r"[\w.+-]{1,64}\s{0,3}@\s{0,3}[\w-]{1,63}(?:\.[\w-]{1,63}){1,8}")
_PHONE = re.compile(r"(?:\+?\d[\s\-().]*){7,}")
_SOCIAL = re.compile(r"(?:واتس|واتساب|whatsapp|snap|سناب|instagram|انستا|انستغرام|telegram|تلغرام|تيليجرام|tiktok|تيك\s*توك)", re.I)


def blocked_reason(text):
    plain = (text or "").translate(_DIGITS)
    if _URL.search(plain):
        return "link"
    if "@" in plain and _EMAIL.search(plain):
        return "contact"
    if _PHONE.search(plain):
        return "contact"
    if _SOCIAL.search(plain):
        return "contact"
    return None
