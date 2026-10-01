"""Thin HTTP client for the Juthoor FastAPI backend.

Every call returns parsed JSON or raises ApiError with a user-facing Arabic message,
so the UI never shows a raw traceback.
"""
from __future__ import annotations

import os

import requests

BASE_URL = os.environ.get("JUTHOOR_API_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = float(os.environ.get("JUTHOOR_API_TIMEOUT", "20"))

# backend error code -> message shown to the user
MESSAGES = {
    "invalid_credentials": "البريد الإلكتروني أو كلمة المرور غير صحيحة.",
    "email_already_registered": "هذا البريد مسجّل مسبقاً. جرّب تسجيل الدخول.",
    "organization_not_found": "رمز المدرسة غير صحيح.",
    "guardian_must_be_existing_parent": "بريد ولي الأمر غير مسجّل كحساب وليّ أمر.",
    "no_active_question": "انتهت صلاحية السؤال، سنعرض سؤالاً جديداً.",
    "insufficient_balance": "رصيدك لا يكفي! حلّ المزيد من التحديات.",
    "insufficient_coins": "رصيدك من العملات لا يكفي.",
    "premium_item_requires_gems": "هذه القطعة تُشترى بالجواهر فقط.",
    "already_owned": "تملك هذه القطعة مسبقاً.",
    "item_not_found": "القطعة غير موجودة في المتجر (هل تم تشغيل seed_shop.py؟).",
    "cannot_access_student": "لا تملك صلاحية عرض هذا الطالب.",
    "insufficient_role": "هذه الصفحة غير متاحة لنوع حسابك.",
    "invalid_token": "انتهت الجلسة، سجّل الدخول من جديد.",
    "user_not_found": "انتهت الجلسة، سجّل الدخول من جديد.",
    "session_not_found": "انتهت جلسة المحادثة، ابدأ محادثة جديدة.",
    "unknown_skill_context": "الدرس غير معروف.",
    "cannot_friend_self": "لا يمكنك إضافة نفسك.",
    "user_not_found": "المستخدم غير موجود.",
    "friendship_exists": "طلب الصداقة موجود مسبقاً.",
    "friendship_not_found": "طلب الصداقة غير موجود.",
    "not_your_incoming_request": "هذا الطلب ليس موجهاً لك.",
    "not_friends": "يجب قبول الصداقة أولاً قبل المراسلة.",
    "unknown_plan": "الباقة غير معروفة.",
    "session_not_found": "جلسة الدفع غير موجودة.",
    "session_not_pending": "تم استخدام جلسة الدفع مسبقاً.",
    "confirm_only_for_mock_provider": "يجب إتمام الدفع عبر بوابة Stripe.",
    "bad_card": "بيانات البطاقة غير صحيحة.",
    "invalid_or_expired_token": "رابط إعادة التعيين غير صالح أو انتهت صلاحيته.",
    "teacher_role_required": "هذه الميزة متاحة للمعلمين فقط.",
    "student_role_required": "هذه الميزة متاحة للطلاب فقط.",
    "classroom_not_found": "الصف غير موجود — تأكد من رمز الدخول.",
    "teacher_only": "هذا الإجراء يحتاج صلاحية المعلم.",
    "unknown_skill": "الدرس غير معروف.",
    "handle_generation_failed": "تعذّر توليد رقم مستخدم فريد — حاول مرة أخرى.",
}

FIELD_MESSAGES = {
    "password": "كلمة المرور يجب أن تكون 6 أحرف على الأقل.",
    "email": "صيغة البريد الإلكتروني غير صحيحة.",
    "guardian_email": "صيغة بريد ولي الأمر غير صحيحة.",
    "full_name": "يرجى كتابة الاسم.",
    "role": "نوع الحساب غير مسموح.",
    "selected_answer": "يرجى إدخال إجابة.",
    "message": "الرسالة فارغة أو طويلة جداً.",
    "grade_level": "الصف يجب أن يكون بين 1 و 12.",
}


class ApiError(Exception):
    def __init__(self, message: str, status: int = 0, code: str = ""):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


PLAN_LABEL = {"basic": "Basic", "pro": "Pro", "max": "Max"}


def _friendly(resp: requests.Response) -> ApiError:
    try:
        detail = resp.json().get("detail")
    except ValueError:
        detail = None
    if isinstance(detail, str):
        code = detail.split(":")[0]
        if code == "item_not_owned":
            return ApiError("لم تشترِ هذه القطعة بعد.", resp.status_code, code)
        if code == "plan_upgrade_required":
            required = detail.split(":", 1)[1] if ":" in detail else "pro"
            return ApiError(f"هذه الميزة تحتاج باقة {PLAN_LABEL.get(required, required)} أو أعلى.", resp.status_code, code)
        return ApiError(MESSAGES.get(code, f"حدث خطأ ({detail})."), resp.status_code, code)
    if isinstance(detail, list) and detail:            # pydantic validation errors (422)
        loc = detail[0].get("loc", [])
        field = loc[-1] if loc else ""
        return ApiError(FIELD_MESSAGES.get(field, "بعض المدخلات غير صحيحة."), resp.status_code, "validation")
    return ApiError(f"حدث خطأ غير متوقع في الخادم (رمز {resp.status_code}).", resp.status_code)


def _call(method: str, path: str, token: str | None = None, **kw):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        resp = requests.request(method, BASE_URL + path, headers=headers, timeout=TIMEOUT, **kw)
    except requests.RequestException:
        raise ApiError(f"تعذّر الاتصال بالخادم على {BASE_URL}. تأكد من تشغيله: uvicorn app.main:app")
    if resp.status_code >= 400:
        raise _friendly(resp)
    return resp.json() if resp.content else None


# ------------------------------------------------------------------ auth
def health():
    return _call("GET", "/health")


def login(email, password):
    return _call("POST", "/auth/login", json={"email": email, "password": password})


def register(email, password, full_name, role="student", org_slug=None, guardian_email=None,
             grade_level=6, gender=None):
    body = {"email": email, "password": password, "full_name": full_name, "role": role, "grade_level": grade_level}
    if org_slug:      body["org_slug"] = org_slug
    if guardian_email: body["guardian_email"] = guardian_email
    if gender:        body["gender"] = gender
    return _call("POST", "/auth/register", json=body)


def me(token):
    return _call("GET", "/auth/me", token)


# ------------------------------------------------------------------ adaptive practice
def question(token, sid):
    return _call("GET", f"/students/{sid}/adaptive/question", token)


def answer(token, sid, selected):
    return _call("POST", f"/students/{sid}/adaptive/answer", token, json={"selected_answer": selected})


def state(token, sid):
    return _call("GET", f"/students/{sid}/adaptive/state", token)


def new_round(token, sid):
    return _call("POST", f"/students/{sid}/adaptive/round", token)


def drilldowns(token, sid):
    return _call("GET", f"/students/{sid}/adaptive/drilldowns", token)


# ------------------------------------------------------------------ tutor
def chat_start(token, sid, skill_id):
    return _call("POST", f"/students/{sid}/chat/start", token, json={"skill_context": skill_id})


def chat_message(token, sid, session_id, message):
    return _call("POST", f"/students/{sid}/chat/message", token,
                 json={"session_id": session_id, "message": message})


# ------------------------------------------------------------------ dashboards
def my_students(token):
    return _call("GET", "/me/students", token)


def insights(token, sid):
    return _call("GET", f"/students/{sid}/insights", token)


def cohort(token, org_id):
    return _call("GET", f"/organizations/{org_id}/insights", token)


# ------------------------------------------------------------------ economy
def wallet(token, sid):
    return _call("GET", f"/students/{sid}/economy/wallet", token)


def shop(token, sid):
    return _call("GET", f"/students/{sid}/economy/shop", token)


def purchase(token, sid, item_id, currency):
    return _call("POST", f"/students/{sid}/economy/purchase", token, json={"item_id": item_id, "currency": currency})


def get_avatar(token, sid):
    return _call("GET", f"/students/{sid}/economy/avatar", token)


def set_avatar(token, sid, cfg):
    keys = ("gender", "skin", "clothing", "top", "neck", "accessories", "hair", "hair_color")
    return _call("PUT", f"/students/{sid}/economy/avatar", token, json={k: cfg[k] for k in keys})


# ------------------------------------------------------------------ community
def search_users(token, q):
    return _call("GET", f"/community/search?q={q}", token)


def friends_list(token):
    return _call("GET", "/community/friends", token)


def friend_requests(token):
    return _call("GET", "/community/requests", token)


def friend_request(token, other_id):
    return _call("POST", f"/community/request/{other_id}", token)


def friend_accept(token, fid):
    return _call("POST", f"/community/accept/{fid}", token)


def friend_reject(token, fid):
    return _call("POST", f"/community/reject/{fid}", token)


def friend_remove(token, fid):
    return _call("DELETE", f"/community/friend/{fid}", token)


def dm_thread(token, other_id):
    return _call("GET", f"/community/messages/{other_id}", token)


def dm_send(token, other_id, body):
    return _call("POST", f"/community/messages/{other_id}", token, json={"body": body})


# ------------------------------------------------------------------ bootstrap (fast path)
def bootstrap(token, sid):
    return _call("GET", f"/students/{sid}/adaptive/bootstrap", token)


# ------------------------------------------------------------------ payments
def checkout_start(token, plan):
    return _call("POST", "/payments/checkout", token, json={"plan": plan})


def checkout_confirm(token, session_id, card_last4, card_holder):
    return _call("POST", "/payments/confirm", token,
                 json={"session_id": session_id, "card_last4": card_last4, "card_holder": card_holder})


def checkout_status(token, session_id):
    return _call("GET", f"/payments/session/{session_id}", token)


# ------------------------------------------------------------------ password reset
def forgot_password(email):
    return _call("POST", "/auth/forgot-password", json={"email": email})


def reset_password(token, new_password):
    return _call("POST", "/auth/reset-password", json={"token": token, "new_password": new_password})


# ------------------------------------------------------------------ classrooms
def classrooms_mine(token):
    return _call("GET", "/classrooms", token)


def classroom_create(token, name):
    return _call("POST", "/classrooms", token, json={"name": name})


def classroom_join(token, code):
    return _call("POST", "/classrooms/join", token, json={"join_code": code})


def classroom_members(token, cid):
    return _call("GET", f"/classrooms/{cid}/members", token)


def assignments_mine(token):
    return _call("GET", "/classrooms/assignments", token)


def assignment_create(token, cid, title, skill_id, target_questions=10, due_at=None):
    body = {"title": title, "skill_id": skill_id, "target_questions": target_questions}
    if due_at is not None: body["due_at"] = due_at
    return _call("POST", f"/classrooms/{cid}/assignments", token, json=body)
