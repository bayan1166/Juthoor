"""Juthoor web UI (Streamlit). Run from the repository root:

    streamlit run web/streamlit_app.py

All learning state lives in the FastAPI backend (JUTHOOR_API_URL, default
http://localhost:8000). This file only renders and calls the REST API; the curriculum
tree/avatar drawing code is shared with the backend's app/engine package.
"""
import html
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st  # noqa: E402

from app.engine import adaptive_engine as ae  # noqa: E402
from app.engine import avatar as av  # noqa: E402
from app.engine import knowledge_graph as kg  # noqa: E402

import api  # noqa: E402
import brand  # noqa: E402
import curriculum as cur  # noqa: E402
import theme  # noqa: E402
import tree_component as tc  # noqa: E402
import tree_view as tv  # noqa: E402

st.set_page_config(page_title="جذور | Juthoor", layout="centered", page_icon="🌳", initial_sidebar_state="collapsed")

S = st.session_state
if "dark_mode" not in S:
    S.dark_mode = True
C = theme.get_palette(S.dark_mode)

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Aref+Ruqaa:wght@400;700&display=swap');

    * {{ direction: rtl; text-align: right; }}
    html, body, p, span, div, h1, h2, h3, h4, h5, h6, input, label, select, button, .stMarkdown, .stTabs {{
        font-family: 'Tajawal', sans-serif !important;
    }}

    /* استثناء أيقونات الخطوط من خط تجوال حتى لا تتحول إلى نصوص مقروءة */
    .material-symbols-rounded, .material-symbols-outlined, [data-testid*="Icon"] {{
        font-family: "Material Symbols Rounded", "Material Symbols Outlined", sans-serif !important;
        direction: ltr !important;
    }}

    .stApp {{ background-color: {C['night']}; color: {C['text']}; }}

    /* تصميم الشعار (Lockup) */
    .jt-lockup {{ display: flex; align-items: center; gap: 12px; margin-bottom: 25px; }}
    .jt-lockup-word b {{ font-family: 'Aref Ruqaa', serif !important; font-size: 32px; color: {C['gold']}; }}
    .jt-lockup-word i {{ display: block; font-family: sans-serif !important; font-size: 14px; font-style: normal; letter-spacing: 2px; color: {C['muted']}; margin-top: -8px; direction: ltr; text-align: left; }}

    /* الكروت الأنيقة */
    .clean-card {{
        background-color: {C['deep']};
        border: 1px solid rgba(230,190,106,.28);
        border-radius: 16px; padding: 20px; margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }}

    /* أزرار الإجابات */
    div[data-testid="stButton"] > button {{
        background-color: {C['lift']}; color: {C['text']};
        border: 1px solid {C['muted']}; border-radius: 10px; font-weight: bold; padding: 12px; transition: 0.2s;
        width: 100%;
    }}
    div[data-testid="stButton"] > button:hover {{ border-color: {C['gold']}; color: {C['gold_pale']}; }}

    /* زر تبديل الثيم الأنيق (Theme Pill Button) */
    .jt-theme-pill div[data-testid="stButton"] > button {{
        background: rgba(31, 201, 138, 0.12) !important;
        border: 1px solid rgba(230, 190, 106, 0.45) !important;
        border-radius: 30px !important;
        padding: 5px 16px !important;
        color: {C['gold']} !important;
        font-size: 13.5px !important;
        font-weight: 800 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
        transition: all 0.25s ease !important;
        width: auto !important;
        min-height: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin-right: auto !important;
        cursor: pointer !important;
    }}
    .jt-theme-pill div[data-testid="stButton"] > button:hover {{
        background: rgba(31, 201, 138, 0.25) !important;
        border-color: {C['emerald']} !important;
        color: #FFFFFF !important;
        transform: translateY(-1px) !important;
    }}

    /* إزالة أي إطار أو خطوط مشوهة من عناصر الـ Toggle */
    div[data-testid="stToggle"] * {{
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
    }}
    div[data-testid="stToggle"] {{
        background: transparent !important;
        border: none !important;
        display: flex !important;
        justify-content: flex-end !important;
    }}
    div[data-testid="stToggle"] p {{
        color: {C['gold']} !important;
        font-weight: 700 !important;
        font-size: 14px !important;
    }}

    /* رسائل التغذية الراجعة */
    .feedback-box {{ padding: 15px; border-radius: 8px; font-weight: bold; margin-bottom: 15px; }}
    .success-box {{ background-color: rgba(31, 201, 138, 0.1); border-right: 4px solid {C['emerald']}; color: {C['emerald']}; }}
    .error-box {{ background-color: rgba(217, 132, 102, 0.1); border-right: 4px solid {C['rose']}; color: {C['rose']}; }}
    .fb-sub {{ font-size: 14px; font-weight: normal; color: {C['muted']}; margin-top: 6px; line-height: 1.8; }}

    /* بطاقة شرح الخطأ */
    .mistake-card {{ background: linear-gradient(160deg, {C['deep']}, {C['lift']}); border: 1px solid rgba(230,190,106,.45);
        border-radius: 16px; padding: 16px 18px; margin-bottom: 16px; box-shadow: 0 6px 14px rgba(0,0,0,.28); }}
    .mc-head {{ font-size: 17px; font-weight: 800; color: {C['gold']}; margin-bottom: 10px; }}
    .mc-answers {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }}
    .mc-chip {{ padding: 6px 12px; border-radius: 999px; font-size: 14px; font-weight: 700; }}
    .mc-chip.bad {{ background: rgba(217,132,102,.16); color: {C['rose']}; }}
    .mc-chip.good {{ background: rgba(31,201,138,.16); color: {C['emerald']}; }}
    .mc-why {{ background: rgba(230,190,106,.10); border-right: 3px solid {C['gold']}; padding: 8px 12px; border-radius: 8px;
        font-size: 14px; line-height: 1.8; margin-bottom: 10px; color: {C['gold_pale']}; }}
    .mc-sec {{ margin-top: 8px; }}
    .mc-sec b {{ display: block; font-size: 13px; color: {C['mint']}; margin-bottom: 2px; }}
    .mc-sec p {{ margin: 0; font-size: 14.5px; line-height: 1.9; color: {C['text']}; }}
    .q-banner {{ background: rgba(31,201,138,.10); border: 1px dashed {C['emerald']}; color: {C['mint']};
        padding: 8px 12px; border-radius: 10px; font-size: 14px; font-weight: 700; margin-bottom: 12px; }}
    .q-hint {{ margin-top: 10px; font-size: 14px; color: {C['gold_pale']}; }}

    /* المتجر */
    .shop-card {{ background: {C['deep']}; border: 1px solid rgba(230,190,106,.22); border-radius: 14px; padding: 8px 6px 2px; text-align: center; margin-bottom: 4px; }}
    .shop-card.on {{ border-color: {C['emerald']}; box-shadow: 0 0 0 2px rgba(31,201,138,.25); }}
    .shop-card svg {{ width: 88px; height: 88px; }}
    .shop-name {{ font-size: 13px; font-weight: 700; text-align: center; min-height: 34px; line-height: 1.35; }}
    .shop-card * {{ text-align: center; }}

    header {{ visibility: hidden; }}

    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background-color: {C['night']}; }}
    [data-testid="stForm"] {{
        background-color: {C['deep']}; border: 1px solid rgba(230,190,106,.28);
        border-radius: 16px; padding: 28px 26px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }}
    div[data-testid="stTextInput"] label, div[data-testid="stForm"] label,
    div[data-testid="stRadio"] label, div[data-testid="stExpander"] summary p {{ color: {C['muted']} !important; }}
    div[data-testid="stTextInput"] input {{
        background-color: {C['lift']} !important; color: {C['text']} !important;
        border: 1px solid {C['muted']} !important; border-radius: 10px !important;
    }}
    div[data-testid="stTextInput"] input::placeholder {{ color: {C['muted']} !important; opacity: .8; }}
    div[data-testid="stFormSubmitButton"] > button {{
        background-color: {C['gold_deep']}; color: {C['ink' if C['mode']=='dark' else 'text']};
        border: none; border-radius: 10px; font-weight: bold; width: 100%; padding: 12px;
    }}
    div[data-testid="stFormSubmitButton"] > button:hover {{ background-color: {C['gold']}; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {C['lift']}; border-radius: 10px 10px 0 0; color: {C['text']}; opacity: .6; font-weight: 700;
    }}
    .stTabs [aria-selected="true"] {{ background-color: {C['deep']}; color: {C['gold']} !important; opacity: 1; }}
    div[data-testid="stExpander"] {{ background-color: {C['deep']}; border: 1px solid rgba(230,190,106,.22); border-radius: 12px; }}
    div[data-baseweb="select"] > div {{ background-color: {C['lift']} !important; color: {C['text']} !important; border-color: {C['muted']} !important; }}
    div[role="radiogroup"] label {{ color: {C['text']} !important; }}
    .theme-caption {{ color: {C['muted']}; font-size: 12px; margin-top: -10px; }}

    /* ====================================================================
       إزالة أي أثر لكلمة keyboard_ar نهائياً وتصحيح أيقونة القوائم
       ==================================================================== */
    [data-testid="stExpanderToggleIcon"],
    summary span[class*="material"],
    summary [data-testid="stIconMaterial"],
    span[data-testid="stExpanderToggleIcon"] {{
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        font-size: 0 !important;
        line-height: 0 !important;
        color: transparent !important;
        opacity: 0 !important;
    }}
    div[data-testid="stExpander"] summary {{
        position: relative !important;
        padding-left: 30px !important;
        cursor: pointer !important;
    }}
    div[data-testid="stExpander"] summary::before {{
        content: "▾" !important;
        position: absolute !important;
        left: 12px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        font-size: 16px !important;
        color: {C['gold']} !important;
        font-weight: 900 !important;
    }}

    /* الأعمدة تبقى بجانب بعضها على الجوال */
    @media (max-width: 640px) {{
        div[data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: .4rem !important; }}
        div[data-testid="stColumn"], div[data-testid="column"] {{ min-width: 0 !important; flex: 1 1 0 !important; }}
        div[data-testid="stButton"] > button {{ padding: 8px 4px; font-size: 13px; }}
    }}

    /* CSS الشجرة الذي تم تضمينه من tree_view.py */
    {tv.TREE_CSS}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""<style>
    /* --- global fixes for the reported issues --------------------------- */
    [data-testid="stMarkdownContainer"] a[href^="#"],
    .stMarkdown a[href^="#"], h1 a, h2 a, h3 a, h4 a, h5 a,
    .stMarkdown svg[class*="link"], [data-testid="stHeaderActionElements"] {{ display: none !important; }}

    [data-testid="InputInstructions"], [class*="keyboard"], [aria-label*="keyboard" i],
    [title*="keyboard" i], [data-baseweb="input"] + div[data-testid],
    span[data-testid="InputInstructions"] {{ display: none !important; }}

    .stTextInput > label + div > div > div > span {{ visibility: hidden; }}
    body, .stApp, .stMarkdown, .stMarkdown p {{ color: {C['text']} !important; }}
    .stMarkdown p, .stMarkdown li {{ line-height: 1.85; }}
    small, .fb-sub, .theme-caption, [data-testid="stCaptionContainer"] {{ color: {C['muted']} !important; }}

    .jt-logout {{ text-align: left; margin-top: 6px; }}
    .jt-logout div[data-testid="stButton"] > button {{ width: auto !important; padding: 6px 14px; }}

    .jt-metric {{ background: linear-gradient(160deg, {C['deep']}, {C['lift']});
        border: 1px solid rgba(61,220,145,.32); border-radius: 18px; padding: 16px 12px;
        text-align: center; box-shadow: 0 4px 14px rgba(0,0,0,.24); }}
    .jt-metric .jt-metric-val {{ font-size: 30px; font-weight: 900; color: {C['emerald']};
        line-height: 1.1; display: flex; align-items: center; justify-content: center; gap: 8px; }}
    .jt-metric .jt-metric-val .jt-metric-icon {{ font-size: 30px; }}
    .jt-metric .jt-metric-label {{ font-size: 13px; color: {C['muted']}; margin-top: 6px; letter-spacing: .5px; }}

    .jt-tree-wrap {{ width: 100%; overflow-x: auto; }}
    .jt-tree-wrap svg {{ width: 100% !important; height: auto !important; max-width: none !important;
        display: block; margin: 0 auto; }}

    div[data-testid="stButton"] > button {{ transition: transform .08s ease, border-color .15s ease; }}
    div[data-testid="stButton"] > button:active {{ transform: scale(.98); }}
    [data-testid="stChatInput"] {{ direction: rtl; }}
    .jt-alert {{ background: rgba(217,132,102,.12); border-right: 4px solid {C['rose']}; padding: 10px 14px;
        border-radius: 10px; margin-bottom: 12px; font-weight: 700; color: {C['rose']}; }}
    .jt-trace {{ background: rgba(31,201,138,.08); border-right: 4px solid {C['emerald']}; padding: 10px 14px;
        border-radius: 10px; margin-bottom: 12px; color: {C['mint']}; font-weight: 700; line-height: 1.9; }}
    .jt-path {{ display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 6px 0 14px; }}
    .jt-node {{ background: {C['lift']}; border: 1px solid rgba(230,190,106,.35); border-radius: 999px;
        padding: 4px 12px; font-size: 14px; font-weight: 700; }}
    .jt-node.root {{ border-color: {C['rose']}; color: {C['rose']}; }}
    .jt-arrow {{ color: {C['muted']}; font-weight: 800; }}
</style>""", unsafe_allow_html=True)

for _k, _v in (("token", None), ("me", None), ("q", None), ("fb", None), ("qn", 0), ("chat", None),
               ("avatar", None), ("selected_lesson", None), ("open_lesson", None), ("_last_click", None)):
    if _k not in S:
        S[_k] = _v

ROLE_AR = {"student": "طالب", "parent": "ولي أمر", "teacher": "معلم", "org_admin": "مدير مدرسة",
           "platform_admin": "مشرف المنصة"}
STATUS_AR = {"mastered": "✅ متقن", "gap": "🔴 فجوة جذرية", "learning": "🟡 قيد التعلّم", "untouched": "⚪ لم يبدأ"}
SEVERITY_AR = {"critical": "🔴 حرج", "high": "🟠 مرتفع", "medium": "🟡 متوسط", "low": "🟢 منخفض"}
NEXT_LABEL = {None: "التحدي التالي 🚀", "same_pattern": "سؤال على الفكرة نفسها 🔁", "easier": "سؤال أبسط 🌱"}
DIAGNOSTIC_ACTIONS = {"backtrack", "remediate", "park", "return_up"}


def e(text) -> str:
    return html.escape(str(text if text is not None else ""))


def skill_ar(skill_id) -> str:
    return kg.SKILLS[skill_id].name_ar if skill_id in kg.SKILLS else str(skill_id or "—")


def logout():
    for k in ("token", "me", "q", "fb", "chat", "avatar", "selected_lesson", "open_lesson", "_last_click"):
        S[k] = None
    S.qn = 0


def call(fn, *args, quiet_codes=(), **kw):
    """Run an API call; show a friendly Arabic error and return None on failure."""
    try:
        return fn(*args, **kw)
    except api.ApiError as err:
        if err.code in ("invalid_token", "user_not_found"):
            logout()
            st.warning(err.message)
            st.stop()
        if err.code not in quiet_codes:
            st.error(err.message)
        S["_last_error_code"] = err.code
        return None


def state_object(js: dict) -> ae.StudentState:
    """Rebuild a StudentState from GET /adaptive/state so the shared tree code can draw it."""
    s = ae.StudentState(current_skill=js["current_skill"], difficulty=js["difficulty"])
    s.total_answered = js.get("total_answered", 0)
    for sk in js["skills"]:
        sid = sk["skill_id"]
        s.p_mastery[sid] = sk["p_mastery"]
        s.attempts[sid] = sk["attempts"]
        s.correct[sid] = sk["correct"]
        if sk["status"] == "mastered":
            s.mastered.add(sid)
        elif sk["status"] == "gap":
            s.gaps.add(sid)
    return s


def theme_toggle_button(key_suffix: str = ""):
    """زر كبسولة أنيق وفخم لتبديل الثيم بدون أي مربعات مشوهة."""
    theme_label = "🌙 ليلي" if S.dark_mode else "☀️ نهاري"
    st.markdown("<div class='jt-theme-pill'>", unsafe_allow_html=True)
    if st.button(theme_label, key=f"theme_btn_{key_suffix}"):
        S.dark_mode = not S.dark_mode
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def theme_toggle_row():
    _, col_toggle = st.columns([6, 1])
    with col_toggle:
        theme_toggle_button("auth")


def metric(col, icon, value, label):
    col.markdown(
        f"<div class='jt-metric'><div class='jt-metric-val'>"
        f"<span class='jt-metric-icon'>{icon}</span><span>{value}</span></div>"
        f"<div class='jt-metric-label'>{label}</div></div>",
        unsafe_allow_html=True,
    )


def path_html(events: list) -> str:
    chain = []
    for ev in events:
        if ev["direction"] != "descend":
            continue
        if not chain:
            chain.append(ev["from_name_ar"])
        if chain[-1] != ev["to_name_ar"]:
            chain.append(ev["to_name_ar"])
    if len(chain) < 2:
        return ""
    parts = []
    for i, name in enumerate(chain):
        cls = "jt-node root" if i == len(chain) - 1 else "jt-node"
        parts.append(f"<span class='{cls}'>{e(name)}</span>")
    return "<div class='jt-path'>" + "<span class='jt-arrow'>←</span>".join(parts) + "</div>"


def gaps_html(state_js: dict) -> str:
    gaps = [sk["name_ar"] for sk in state_js["skills"] if sk["status"] == "gap"]
    if not gaps:
        return ""
    return f"<div class='jt-alert'>🎯 الفجوة الجذرية المكتشفة: {'، '.join(e(g) for g in gaps)}</div>"


# ======================================================================== auth

def _forgot_password_wizard():
    step = S.get("_pw_step", 1)

    def _cancel():
        for k in ("_pw_step", "_pw_email", "_pw_token"):
            S.pop(k, None)

    st.markdown("### 🔑 إعادة تعيين كلمة المرور")

    if step == 1:
        st.markdown("أدخل بريدك الإلكتروني وسنرسل لك رمزاً للتحقق.")
        with st.form("fp_step1"):
            email = st.text_input("البريد الإلكتروني", key="fp_email",
                                  placeholder="example@email.com", label_visibility="visible")
            c1, c2 = st.columns(2)
            go = c1.form_submit_button("إرسال الرمز ←")
            c2.form_submit_button("إلغاء", on_click=_cancel)
        if go:
            if not email.strip():
                st.error("أدخل بريدك الإلكتروني أولاً.")
            else:
                call(api.forgot_password, email.strip().lower())
                S["_pw_email"] = email.strip().lower()
                S["_pw_step"] = 2
                st.rerun()

    elif step == 2:
        email = S.get("_pw_email", "")
        st.success(f"✅ إذا كان البريد **{email}** مسجّلاً، سيصلك رمز صالح لـ 30 دقيقة. تحقّق من بريدك.")
        st.markdown("أدخل الرمز الذي وصلك:")
        with st.form("fp_step2"):
            code = st.text_input("رمز التحقق", key="fp_code",
                                 placeholder="الصق الرمز هنا", label_visibility="visible")
            c1, c2 = st.columns(2)
            go = c1.form_submit_button("التالي ←")
            c2.form_submit_button("إلغاء", on_click=_cancel)
        if go:
            if not code.strip():
                st.error("أدخل الرمز أولاً.")
            else:
                S["_pw_token"] = code.strip()
                S["_pw_step"] = 3
                st.rerun()

    elif step == 3:
        st.markdown("اختر كلمة مرور جديدة:")
        with st.form("fp_step3"):
            pw1 = st.text_input("كلمة المرور الجديدة (6 أحرف على الأقل)", type="password",
                                key="fp_pw1", label_visibility="visible")
            pw2 = st.text_input("تأكيد كلمة المرور", type="password",
                                key="fp_pw2", label_visibility="visible")
            c1, c2 = st.columns(2)
            go = c1.form_submit_button("حفظ كلمة المرور الجديدة ✅")
            c2.form_submit_button("إلغاء", on_click=_cancel)
        if go:
            if not pw1 or len(pw1) < 6:
                st.error("كلمة المرور يجب أن تكون 6 أحرف على الأقل.")
            elif pw1 != pw2:
                st.error("كلمتا المرور غير متطابقتين.")
            else:
                tok = call(api.reset_password, S.get("_pw_token", ""), pw1)
                if tok:
                    _cancel()
                    _finish_login(tok["access_token"])
                    st.success("✅ تم تحديث كلمة المرور وتسجيل الدخول.")


def auth_page():
    if S.get('_pw_step'):
        _forgot_password_wizard()
        return
    theme_toggle_row()
    st.markdown(f"<div style='display:flex; justify-content:center; margin-top:10px;'>{brand.lockup_html(80)}</div>",
                unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:{C['muted']}; margin-top:-10px;'>"
                "منصة ذكاء المناهج — نكتشف من أين بدأت الفجوة، لا أين ظهرت فقط</p>", unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 4, 1])
    with mid:
        t_login, t_signup = st.tabs(["🔑 تسجيل الدخول", "✨ حساب جديد"])
        with t_login:
            with st.form("login_form"):
                email = st.text_input("البريد الإلكتروني", placeholder="student1@demo.jo", key="login_email")
                password = st.text_input("كلمة المرور", type="password", key="login_pw")
                go = st.form_submit_button("دخول 🚀")
            if go:
                if not email.strip() or not password:
                    st.error("يرجى إدخال البريد الإلكتروني وكلمة المرور.")
                else:
                    tok = call(api.login, email.strip(), password)
                    if tok:
                        _finish_login(tok["access_token"])
            if st.button("نسيت كلمة المرور؟", key="open_forgot"):
                S["_pw_step"] = 1
                st.rerun()

        with t_signup:
            with st.form("signup_form"):
                name = st.text_input("الاسم الكامل", placeholder="مثال: سارة أحمد", key="su_name")
                email2 = st.text_input("البريد الإلكتروني", key="su_email")
                pw2 = st.text_input("كلمة المرور (6 أحرف على الأقل)", type="password", key="su_pw")
                role_ar = st.radio("نوع الحساب", ["طالب", "ولي أمر", "معلم"], horizontal=True, key="su_role")
                gender_ar = st.radio("نوع الشخصية", ["ولد", "بنت"], horizontal=True, key="su_gender")
                org = st.text_input("رمز المدرسة (اختياري)", placeholder="demo-school", key="su_org")
                guardian = st.text_input("بريد ولي الأمر (للطالب، اختياري)", key="su_guardian")
                go2 = st.form_submit_button("إنشاء الحساب ✅")
            if go2:
                role = {"طالب": "student", "ولي أمر": "parent", "معلم": "teacher"}[role_ar]
                if not name.strip() or not email2.strip() or not pw2:
                    st.error("يرجى تعبئة الاسم والبريد وكلمة المرور.")
                elif len(pw2) < 6:
                    st.error("كلمة المرور يجب أن تكون 6 أحرف على الأقل.")
                else:
                    tok = call(api.register, email2.strip(), pw2, name.strip(), role,
                               org_slug=org.strip() or None,
                               guardian_email=(guardian.strip() or None) if role == "student" else None,
                               gender=gender_ar if role == "student" else None)
                    if tok:
                        _finish_login(tok["access_token"])

        with st.expander("حسابات تجريبية (بعد تشغيل seed_demo.py)"):
            st.markdown("كلمة المرور لجميعها: `demo1234`\n\n"
                        "- `student1@demo.jo` — طالبة تم تشخيص فجوتها الجذرية\n"
                        "- `student2@demo.jo` — طالب يتقدّم جيداً\n"
                        "- `student3@demo.jo` — طالب جديد للتجربة الحيّة\n"
                        "- `teacher@demo.jo` — معلمة المدرسة التجريبية\n"
                        "- `parent@demo.jo` — ولي أمر student1")


def _finish_login(token):
    info = call(api.me, token)
    if info:
        S.token, S.me = token, info
        st.rerun()


PLAN_COLOR = {"basic": "#8FB09B", "pro": "#F0C674", "max": "#3DDC91"}
PLAN_LABEL_UI = {"basic": "Basic", "pro": "Pro ✨", "max": "Max 👑"}


def _plan_badge():
    plan = (S.me or {}).get("plan", "basic")
    return (f"<span style='background:{PLAN_COLOR.get(plan)}; color:#07160E; padding:3px 10px; "
            f"border-radius:999px; font-weight:900; font-size:12px; margin-inline-start:8px'>"
            f"{PLAN_LABEL_UI.get(plan, plan)}</span>")


def header(title_line: str):
    c_logout, c_brand, c_toggle = st.columns([1, 4, 1])
    with c_logout:
        st.markdown("<div class='jt-logout'>", unsafe_allow_html=True)
        if st.button("خروج", key="logout_btn"):
            logout()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with c_brand:
        st.markdown(f"<div style='text-align:center'>{brand.lockup_html(52)}</div>", unsafe_allow_html=True)
    with c_toggle:
        st.markdown("<div style='display:flex; justify-content:flex-end;'>", unsafe_allow_html=True)
        theme_toggle_button("hdr")
        st.markdown("</div>", unsafe_allow_html=True)
    handle = (S.me or {}).get("handle")
    hbit = f"<span style='background:#1E9E63; color:#07160E; padding:2px 10px; border-radius:999px; font-weight:900; font-size:12px; margin-inline-start:8px'>#{handle}</span>" if handle else ""
    st.markdown(f"<p style='text-align:center; margin:-6px 0 8px'>{title_line} {hbit} {_plan_badge()}</p>",
                unsafe_allow_html=True)


# ======================================================================== student
def feedback_html(fb: dict, show_detail: bool = False) -> str:
    if fb["is_correct"]:
        head = "أحسنت، فهمت الفكرة!" if fb.get("remedial") else "إجابة دقيقة!"
        if fb.get("coins_awarded"):
            head += f" (+{fb['coins_awarded']} 🪙)"
        if fb.get("gems_awarded"):
            head += f" (+{fb['gems_awarded']} 💎)"
        return f"<div class='feedback-box success-box'>{e(head)}</div>"
    head = {None: "عثرة بسيطة!",
            "same_pattern": "ما زالت الفكرة تحتاج تثبيتاً.",
            "easier": "لا بأس — نرجع للأساس أولاً."}.get(fb.get("remedial"), "راجع إجابتك.")
    c = fb.get("mistake_card") or {}
    chosen = str(c.get("chosen", "")).strip() or "—"
    quick = (f"<div class='feedback-box error-box'>{e(head)}</div>"
             f"<div class='clean-card' style='margin-top:8px'>"
             f"<div class='mc-answers'><span class='mc-chip bad'>إجابتك: {e(chosen)}</span>"
             f"<span class='mc-chip good'>الصحيح: {e(fb.get('correct_answer'))}</span></div></div>")
    if not show_detail:
        return quick
    why = f"<div class='mc-why'>💡 غالباً فكّرت هكذا: {e(c['why'])}</div>" if c.get("why") else ""
    detail = (f"<div class='mistake-card'><div class='mc-head'>🍃 بطاقة شرح: {e(c.get('title', 'راجع الفكرة'))}</div>"
              f"{why}<div class='mc-sec'><b>القاعدة</b><p>{e(c.get('rule'))}</p></div>"
              f"<div class='mc-sec'><b>مثال محلول</b><p>{e(c.get('example'))}</p></div>"
              f"<div class='mc-sec'><b>حل سؤالك</b><p>{e(c.get('solution') or fb.get('explanation'))}</p></div></div>")
    return quick + detail


def _invalidate():
    for k in ("_state", "_wallet", "_drilldowns", "_boot"):
        S[k] = None


def _cached(key, fetch):
    if S.get(key) is None:
        S[key] = fetch()
    return S[key]


def submit(selected: str):
    fb = call(api.answer, S.token, S.me["user_id"], selected, quiet_codes=("no_active_question",))
    if fb is None:
        if S.get("_last_error_code") == "no_active_question":
            st.info(api.MESSAGES["no_active_question"])
            S.q = None
        return
    S.fb, S.q = fb, None
    _invalidate()
    st.rerun()


def practice_tab(state_js: dict):
    sid = S.me["user_id"]
    fb = S.fb
    if fb:
        show_detail = S.get("_show_detail", False) and not fb.get("is_correct")
        st.markdown(feedback_html(fb, show_detail=show_detail), unsafe_allow_html=True)
        if not fb.get("is_correct") and not show_detail:
            if st.button("📖 اعرض الشرح", key="show_detail_btn"):
                S["_show_detail"] = True
                st.rerun()
        if fb.get("new_gaps"):
            st.markdown(f"<div class='jt-alert'>🎯 تم تحديد الفجوة الجذرية: "
                        f"{'، '.join(e(skill_ar(g)) for g in fb['new_gaps'])}</div>", unsafe_allow_html=True)
        elif fb.get("action") in DIAGNOSTIC_ACTIONS and fb.get("breadcrumb"):
            st.markdown(f"<div class='jt-trace'>🧭 {e(fb['breadcrumb'])}</div>", unsafe_allow_html=True)
        if fb.get("round_over") and not fb.get("next_stage"):
            st.success("أحسنت! أنهيت جولة اليوم. أوراق شجرتك تنمو 🌱")
            if st.button("جلسة جديدة 🌱", key="new_round_btn"):
                if call(api.new_round, S.token, sid) is not None:
                    S.fb = S.q = None
                    _invalidate()
                    st.rerun()
        elif st.button(NEXT_LABEL.get(fb.get("next_stage"), "التالي"), key="next_btn"):
            S.fb = None
            S["_show_detail"] = False
            st.rerun()
        return

    if S.q is None:
        if state_js.get("round_over") and not state_js.get("in_remediation"):
            st.success("أنهيت جولة التحديات الحالية 🎉")
            if st.button("ابدأ جولة جديدة 🌱", key="new_round_btn2"):
                if call(api.new_round, S.token, sid) is not None:
                    _invalidate(); st.rerun()
            return
        q = call(api.question, S.token, sid)
        if q is None:
            return
        S.q = q
        S.qn += 1

    q, qid = S.q, S.qn
    if q.get("banner"):
        st.markdown(f"<div class='q-banner'>{e(q['banner'])}</div>", unsafe_allow_html=True)
    hint = f"<div class='q-hint'>💡 {e(q['hint'])}</div>" if q.get("guided") and q.get("hint") else ""
    level = {1: "🌱 سهل", 2: "🌿 متوسط", 3: "🌳 متقدّم"}.get(q.get("difficulty"), "")
    st.markdown(f"<div class='clean-card'><span style='color:{C['gold']}; font-size:14px; font-weight:bold;'>"
                f"🎯 {e(q.get('skill_name') or skill_ar(q['skill']))} · {level}</span>"
                f"<h3 style='margin-top:10px;'>{e(q['question'])}</h3>{hint}</div>", unsafe_allow_html=True)

    kind = q.get("type", "mcq")
    if kind == "mcq":
        for i, opt in enumerate(q.get("options") or []):
            if st.button(opt, key=f"opt_{qid}_{i}"):
                submit(opt)
    elif kind == "tf":
        b1, b2 = st.columns(2)
        if b1.button("✔️ صح", key=f"t_{qid}"):
            submit("صح")
        if b2.button("❌ خطأ", key=f"f_{qid}"):
            submit("خطأ")
    else:
        typed = st.text_input("اكتب إجابتك هنا:", key=f"inp_{qid}")
        if st.button("تأكيد الإجابة 🚀", key=f"ok_{qid}"):
            if not typed.strip():
                st.error("يرجى كتابة إجابة أولاً.")
            else:
                submit(typed.strip())


def tree_tab(state_js: dict, events: list):
    state = state_object(state_js)
    st.markdown(gaps_html(state_js), unsafe_allow_html=True)
    chain = path_html(events)
    if chain:
        st.markdown("**🧭 مسار تتبّع الجذر:**", unsafe_allow_html=True)
        st.markdown(chain, unsafe_allow_html=True)

    current_key = next((cur.lesson_key(u, l) for u, l in cur.all_lessons() if l.skill == state.current_skill), None)
    selected = S.selected_lesson or current_key
    st.markdown("<div class='jt-tree-wrap'>", unsafe_allow_html=True)
    clicked = tc.clickable_tree(state, selected)
    st.markdown("</div>", unsafe_allow_html=True)
    if clicked and clicked != S._last_click:
        S._last_click = clicked
        S.selected_lesson = clicked
        st.rerun()

    with st.expander("أو اختر الدرس من القائمة"):
        keys = [cur.lesson_key(u, l) for u, l in cur.all_lessons()]
        labels = {cur.lesson_key(u, l): f"الوحدة {u.no} · الدرس {l.no}: {l.title}" for u, l in cur.all_lessons()}
        pick = st.selectbox("الدرس", keys, index=keys.index(selected) if selected in keys else 0,
                            format_func=lambda k: labels[k], label_visibility="collapsed")
        if pick != selected:
            S.selected_lesson = pick
            st.rerun()
    if selected:
        st.markdown(tv.detail_html(state, selected), unsafe_allow_html=True)


def tutor_tab(state_js: dict):
    sid = S.me["user_id"]
    st.markdown("<div class='clean-card'><h3 style='margin:0'>🤖 المعلم الذكي</h3></div>",
                unsafe_allow_html=True)
    if S.me.get("plan") == "basic" and S.me.get("role") == "student":
        st.warning("🔒 المعلم الذكي متاح لباقة Pro أو Max. جرّب إرسال رسالة لترى معاينة، ثم رقّي الاشتراك من تبويب الباقات.")
    skills = kg.ordered_skills()
    default = skills.index(state_js["current_skill"]) if state_js["current_skill"] in skills else 0
    skill = st.selectbox("الدرس الذي تحتاج مساعدة فيه", skills, index=default, format_func=skill_ar, key="tutor_skill")
    if S.chat is not None and S.chat["skill"] != skill:
        S.chat = None
    chat = S.chat
    if chat is None:
        if st.button("ابدأ المحادثة 💬", key="chat_start"):
            res = call(api.chat_start, S.token, sid, skill)
            if res:
                S.chat = {"id": res["session_id"], "skill": skill, "msgs": [("assistant", res["opening_message"])]}
                st.rerun()
        return
    my_av = av.avatar_svg(size=48, uid="chatme", **av_kwargs(S.avatar)) if S.avatar else ""
    for role, text in chat["msgs"]:
        if role == "user":
            with st.chat_message("user", avatar="🧑‍🎓"):
                st.markdown(f"<div style='display:flex; gap:10px; align-items:flex-start'>"
                            f"<div style='flex-shrink:0; width:44px'>{my_av}</div>"
                            f"<div><b>أنا</b><br>{e(text)}</div></div>", unsafe_allow_html=True)
        else:
            with st.chat_message("assistant", avatar="🌳"):
                st.markdown(f"<b>المعلم الذكي</b><br>{e(text)}", unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        prompt = st.text_input("رسالتك", placeholder="اكتب ما تفكر فيه أو أين علقت...",
                               key="chat_text", label_visibility="collapsed")
        sent = st.form_submit_button("إرسال ✉️")
    if sent and not (prompt or "").strip():
        st.error("اكتب رسالة أولاً.")
    if sent and prompt and prompt.strip():
        res = call(api.chat_message, S.token, sid, chat["id"], prompt.strip()[:1000])
        if res:
            chat["msgs"].append(("user", prompt.strip()))
            chat["msgs"].append(("assistant", res["reply"]))
            if res.get("drill_down_triggered"):
                chat["msgs"].append(("assistant", f"🧭 لاحظت أن الأساس يحتاج تثبيتاً في «{skill_ar(res.get('gap_skill'))}». "
                                                  "أضفت لك أسئلة تأسيسية في تبويب التحديات."))
                S.q = S.fb = None
            st.rerun()
        elif S.get("_last_error_code") == "session_not_found":
            S.chat = None


SHOP_SECTIONS = {
    "👕 الملابس": [("tees", "تيشيرتات"), ("hoodies", "هوديات"), ("jackets", "جاكيتات ومعاطف"), ("heritage", "الزي التراثي")],
    "💼 الوظائف": [("jobs", "بدلات الوظائف (مع قبعتها)")],
    "🧢 أغطية الرأس": [("caps", "قبعات"), ("winter", "طواقي الشتاء"), ("heritage_head", "الشماغ والحطة"),
                     ("hijab", "الحجاب"), ("jobcaps", "قبعات الوظائف")],
    "🧣 اللفحات": [("scarves", "لفحات")],
    "👓 النظارات": [("glasses", "نظارات")],
}


def av_kwargs(g: dict, **over) -> dict:
    kw = {k: g[k] for k in ("gender", "skin", "clothing", "accessories", "top", "hair", "hair_color", "neck")}
    kw.update(over)
    return kw


def save_avatar(new_cfg: dict) -> bool:
    import threading
    S.avatar = dict(new_cfg)
    token, sid = S.token, S.me["user_id"]
    cfg = dict(new_cfg)

    def _bg():
        try:
            api.set_avatar(token, sid, cfg)
        except api.ApiError:
            pass

    threading.Thread(target=_bg, daemon=True).start()
    return True


def shop_tab(wallet: dict):
    sid = S.me["user_id"]
    g = S.avatar
    st.markdown(f"<div class='clean-card'><h3>🛒 المتجر</h3><p class='fb-sub'>رصيدك: {wallet['coins']} 🪙 · "
                f"{wallet['gems']} 💎 — الجواهر تُكسب عند إتقان درس كامل.</p></div>", unsafe_allow_html=True)
    catalog = call(api.shop, S.token, sid) or []
    by_id = {it["id"]: it for it in catalog}
    if not by_id:
        st.warning("المتجر فارغ. شغّل: python scripts/seed_shop.py")
        return

    with st.expander("تعديل مظهرك (مجاني)"):
        new = dict(g)
        skins = [s[0] for s in av.SKIN_OPTIONS]
        new["skin"] = st.radio("لون البشرة", skins, index=skins.index(g["skin"]) if g["skin"] in skins else 0,
                               format_func=dict(av.SKIN_OPTIONS).get, horizontal=True, key="av_skin")
        hairs = [k for k, v in av.HAIR_STYLES.items() if v[1] in (None, g["gender"])]
        new["hair"] = st.radio("تسريحة الشعر", hairs, index=hairs.index(g["hair"]) if g["hair"] in hairs else 0,
                               format_func=lambda k: av.HAIR_STYLES[k][0], horizontal=True, key="av_hair")
        colors = list(av.HAIR_COLORS)
        new["hair_color"] = st.radio("لون الشعر", colors, index=colors.index(g["hair_color"]) if g["hair_color"] in colors else 0,
                                     format_func=lambda k: av.HAIR_COLORS[k][0], horizontal=True, key="av_hc")
        if new != g and save_avatar(new):
            st.rerun()

    section = st.radio("القسم", list(SHOP_SECTIONS), horizontal=True, key="shop_section", label_visibility="collapsed")
    for group, title in SHOP_SECTIONS[section]:
        items = av.items(group, g["gender"])
        if not items:
            continue
        st.markdown(f"#### {title}")
        for row in range(0, len(items), 3):
            cols = st.columns(3)
            for col, it in zip(cols, items[row:row + 3]):
                info = by_id.get(it.id)
                if info is None:
                    continue
                with col:
                    kw = av_kwargs(g, **{it.cat: it.id})
                    for cat, iid in it.bundle:
                        kw[cat] = iid
                    on = g.get(it.cat) == it.id
                    svg = av.avatar_svg(uid=f"pv{group}{it.id}", **kw)
                    st.markdown(f"<div class='shop-card {'on' if on else ''}'>{svg}"
                                f"<div class='shop-name'>{e(info['name'] or it.name)}</div></div>", unsafe_allow_html=True)
                    price = f"{info['price_gems']} 💎" if info["price_gems"] else f"{info['price_coins']} 🪙"
                    label = "✅ مُلبَّس" if on else ("ارتداء" if info["owned"] else price)
                    if st.button(label, key=f"shop_{it.cat}_{it.id}", disabled=on):
                        if not info["owned"]:
                            currency = "gems" if info["price_gems"] else "coins"
                            if call(api.purchase, S.token, sid, it.id, currency) is None:
                                continue
                            st.toast("تم الشراء! 🎉"); _invalidate()
                        new = dict(g)
                        new[it.cat] = it.id
                        for cat, iid in it.bundle:
                            new[cat] = iid
                        if save_avatar(new):
                            st.rerun()


def student_page():
    sid = S.me["user_id"]
    boot = _cached("_boot", lambda: call(api.bootstrap, S.token, sid))
    if boot is None:
        return
    state_js = boot["state"]
    wallet   = boot["wallet"] or {"coins": 0, "gems": 0}
    events   = boot["drilldowns"] or []
    if S.avatar is None:
        S.avatar = boot.get("avatar") or dict(av.DEFAULTS, gender="ولد")

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1.3])
    metric(c1, "🪙", wallet['coins'], "العملات")
    metric(c2, "💎", wallet['gems'], "الجواهر")
    metric(c3, "🌳", f"{int(round(state_js['tree_health'] * 100))}%", "صحة الشجرة")
    with c4:
        st.markdown(f"<div style='text-align:center;'>{av.avatar_svg(size=100, **av_kwargs(S.avatar))}</div>",
                    unsafe_allow_html=True)

    t_tree, t_quiz, t_tutor, t_shop = st.tabs(["🌳 شجرتي", "🧩 التحديات", "🤖 المعلم الذكي", "🛒 المتجر"])
    with t_tree:
        tree_tab(state_js, events)
    with t_quiz:
        practice_tab(state_js)
    with t_tutor:
        tutor_tab(state_js)
    with t_shop:
        shop_tab(wallet)


# ======================================================================== teacher / parent
def student_report(sid: str, name: str):
    state_js = call(api.state, S.token, sid)
    report = call(api.insights, S.token, sid)
    events = call(api.drilldowns, S.token, sid) or []
    if state_js is None or report is None:
        return
    st.markdown(f"### 📋 تقرير: {e(name)}")
    c1, c2, c3 = st.columns(3)
    metric(c1, "🌳", f"{int(round(state_js['tree_health'] * 100))}%", "صحة الشجرة")
    metric(c2, "📝", state_js["total_answered"], "إجابات")
    metric(c3, "🎯", e(skill_ar(state_js["current_skill"])), "الدرس الحالي")
    st.markdown(gaps_html(state_js), unsafe_allow_html=True)

    chain = path_html(events)
    st.markdown("#### 🧭 مسار تتبّع الجذر")
    if chain:
        st.markdown(chain, unsafe_allow_html=True)
        st.caption("من الدرس الذي ظهرت فيه الصعوبة ← إلى المتطلب السابق الذي بدأت منه الفجوة.")
    else:
        st.caption("لا توجد عمليات تتبّع بعد.")

    st.markdown("#### ⚠️ تنبيهات التعثّر والتوصيات")
    alerts = report.get("struggle_alerts") or []
    if alerts:
        st.dataframe([{
            "الدرس": a["skill_name_ar"], "الخطورة": SEVERITY_AR.get(a["severity"], a["severity"]),
            "الإتقان": f"{int(round(a['p_mastery'] * 100))}%", "أخطاء متتالية": a["consecutive_misses"],
            "الجذر المتوقع": skill_ar(a.get("predicted_root_cause_skill")) if a.get("predicted_root_cause_skill") else "—",
            "الإجراء المقترح": a["recommended_action"],
        } for a in alerts], use_container_width=True, hide_index=True)
    else:
        st.caption("لا توجد تنبيهات حالياً.")

    st.markdown("#### 📊 حالة المهارات")
    st.dataframe([{
        "المهارة": sk["name_ar"], "الحالة": STATUS_AR.get(sk["status"], sk["status"]),
        "الإتقان": f"{int(round(sk['p_mastery'] * 100))}%", "محاولات": sk["attempts"], "صحيحة": sk["correct"],
    } for sk in state_js["skills"]], use_container_width=True, hide_index=True)

    eng = report.get("engagement") or {}
    if eng:
        st.caption(f"نشاط آخر 30 يوماً: {eng.get('active_days_last_30', 0)} يوم · "
                   f"أسئلة آخر 7 أيام: {eng.get('questions_answered_last_7', 0)}")
    with st.expander("🌳 شجرة الطالب"):
        st.markdown(f"<div class='jt-tree-wrap'>{tv.tree_html(state_object(state_js))}</div>",
                    unsafe_allow_html=True)


def staff_page():
    me = S.me
    if me["role"] in ("teacher", "org_admin") and me.get("organization_id"):
        co = call(api.cohort, S.token, me["organization_id"])
        if co:
            c1, c2 = st.columns(2)
            metric(c1, "👥", co["student_count"], "طلاب المدرسة")
            metric(c2, "🌳", f"{int(round(co['avg_tree_health'] * 100))}%", "متوسط صحة الشجرة")
            top = co.get("top_struggle_skills") or []
            if top:
                st.markdown("#### 🏫 أكثر الدروس تعثّراً في المدرسة")
                st.dataframe([{"الدرس": a["skill_name_ar"], "الخطورة": SEVERITY_AR.get(a["severity"], a["severity"]),
                               "الإتقان": f"{int(round(a['p_mastery'] * 100))}%",
                               "الجذر المتوقع": skill_ar(a.get("predicted_root_cause_skill")) if a.get("predicted_root_cause_skill") else "—"}
                              for a in top], use_container_width=True, hide_index=True)

    roster = call(api.my_students, S.token)
    if roster is None:
        return
    if not roster:
        if me["role"] == "parent":
            st.info("لا يوجد أبناء مرتبطون بحسابك. عند إنشاء حساب الطالب اكتب بريدك في خانة «بريد ولي الأمر».")
        else:
            st.info("لا يوجد طلاب في مدرستك بعد. يسجّل الطلاب باستخدام رمز المدرسة.")
        return
    names = {r["student_id"]: f"{r['full_name']} ({r['email']})" for r in roster}
    sid = st.selectbox("اختر الطالب", list(names), format_func=names.get, key="staff_pick")
    student_report(sid, names[sid])


# ======================================================================== community
def classrooms_page():
    me = S.me
    st.markdown(f"<div class='clean-card'><h3 style='margin:0'>🏫 الصفوف</h3>"
                f"<p class='fb-sub'>مجموعات صفّية بين المعلم وطلابه — واجبات ومسابقات، كلها متصلة بشجرة الدرس.</p>"
                f"</div>", unsafe_allow_html=True)
    rooms = call(api.classrooms_mine, S.token) or []

    if me["role"] == "student":
        with st.expander("انضم إلى صف بواسطة الرمز", expanded=not rooms):
            with st.form("join_cls"):
                code = st.text_input("رمز الصف", key="join_code", placeholder="مثال: HK3P9W", max_chars=8)
                go = st.form_submit_button("انضم")
            if go and code.strip():
                if call(api.classroom_join, S.token, code.strip().upper()):
                    st.success("✅ تم الانضمام!"); st.rerun()
        if not rooms:
            st.caption("لم تنضم إلى أي صف بعد. اطلب الرمز من معلّمك.")
        for r in rooms:
            st.markdown(f"**{e(r['name'])}** · عدد الطلاب: {r['member_count']} · عدد الواجبات: {r['assignment_count']}")
        st.markdown("### 📝 واجباتي")
        assignments = call(api.assignments_mine, S.token) or []
        if not assignments:
            st.caption("لا توجد واجبات حالياً.")
        for a in assignments:
            due = f" · التسليم: {a['due_at'][:10]}" if a.get('due_at') else ""
            st.markdown(f"- **{e(a['title'])}** — {e(a['skill_name_ar'])} ({a['target_questions']} سؤال){due}")
        return

    if me["role"] not in ("teacher", "org_admin", "platform_admin"):
        st.info("مجموعات الصفوف متاحة للطلاب والمعلمين فقط.")
        return
    with st.expander("إنشاء صف جديد", expanded=not rooms):
        with st.form("create_cls"):
            name = st.text_input("اسم الصف", key="cls_name", placeholder="مثال: السادس أ — رياضيات")
            go = st.form_submit_button("إنشاء")
        if go and name.strip():
            r = call(api.classroom_create, S.token, name.strip())
            if r: st.success(f"✅ تم إنشاء الصف. الرمز: **{r['join_code']}**"); st.rerun()
    for r in rooms:
        st.markdown("---")
        st.markdown(f"### {e(r['name'])}")
        st.caption(f"رمز الدخول: **{r['join_code']}** · {r['member_count']} طالب · {r['assignment_count']} واجب")
        with st.expander("الطلاب"):
            members = call(api.classroom_members, S.token, r["classroom_id"]) or []
            if not members:
                st.caption("لا طلاب بعد. شارك رمز الدخول.")
            for m in members:
                st.markdown(f"- #{m.get('handle','----')} · {e(m['full_name'])}")
        with st.expander("إنشاء واجب / مسابقة"):
            skills = kg.ordered_skills()
            with st.form(f"as_{r['classroom_id']}"):
                title = st.text_input("عنوان الواجب", key=f"at_{r['classroom_id']}", placeholder="مسابقة الأعداد الصحيحة")
                sk = st.selectbox("الدرس", skills, format_func=skill_ar, key=f"ask_{r['classroom_id']}")
                qc = st.number_input("عدد الأسئلة المستهدف", min_value=1, max_value=100, value=10, key=f"aqc_{r['classroom_id']}")
                go = st.form_submit_button("إنشاء الواجب")
            if go and title.strip():
                if call(api.assignment_create, S.token, r["classroom_id"], title.strip(), sk, int(qc)):
                    st.success("✅ تم إنشاء الواجب."); st.rerun()


def community_page():
    st.markdown("<div class='clean-card'><h3 style='margin:0'>👥 المجتمع</h3>"
                "<p class='fb-sub'>ابحث عن زملاء، أرسل طلبات صداقة، وتحدّث معهم بعد القبول.</p></div>",
                unsafe_allow_html=True)

    tab_friends, tab_requests, tab_find, tab_dm = st.tabs(["أصدقائي", "الطلبات الواردة", "بحث", "المحادثات"])

    with tab_requests:
        reqs = call(api.friend_requests, S.token) or []
        if not reqs:
            st.caption("لا توجد طلبات صداقة حالياً.")
        for r in reqs:
            c1, c2, c3 = st.columns([4, 1, 1])
            handle = r['friend'].get('handle')
            label = f"#{handle}" if handle else "—"
            c1.markdown(f"**{label}** · {e(r['friend']['full_name'])} ({ROLE_AR.get(r['friend']['role'], '')})")
            if c2.button("قبول ✅", key=f"acc_{r['friendship_id']}"):
                if call(api.friend_accept, S.token, r['friendship_id']):
                    st.rerun()
            if c3.button("رفض ❌", key=f"rej_{r['friendship_id']}"):
                if call(api.friend_reject, S.token, r['friendship_id']):
                    st.rerun()

    with tab_friends:
        friends = call(api.friends_list, S.token) or []
        if not friends:
            st.caption("لا أصدقاء بعد. ابحث عن زملائك في تبويب «بحث».")
        for f in friends:
            c1, c2, c3 = st.columns([4, 1, 1])
            handle = f.get('friend', {}).get('handle')
            label = f"#{handle}" if handle else "—"
            c1.markdown(f"**{label}** · {e(f['friend']['full_name'])}")
            if c2.button("💬 محادثة", key=f"dm_{f['friend']['user_id']}"):
                S["_dm_open_with"] = f['friend']
                st.rerun()
            if c3.button("إزالة", key=f"rm_{f['friendship_id']}"):
                if call(api.friend_remove, S.token, f['friendship_id']):
                    st.rerun()

    with tab_find:
        st.caption("ابحث برقم المستخدم (الموجود تحت اسمك في الأعلى) أو ببريد إلكتروني كامل.")
        q = st.text_input("رقم المستخدم أو البريد", key="community_q", placeholder="مثال: 7429 أو friend@email.com")
        if q and len(q.strip()) >= 2:
            results = call(api.search_users, S.token, q.strip().lstrip("#")) or []
            if not results:
                st.caption("لا توجد نتائج.")
            for r in results:
                c1, c2 = st.columns([4, 1])
                label = f"#{r.get('handle') or '----'}" if r.get('handle') else "—"
                c1.markdown(f"**{label}** · {e(r['full_name'])} ({ROLE_AR.get(r['role'], '')})")
                fs = r.get("friendship_status")
                if fs == "accepted":
                    c2.success("صديق")
                elif fs == "pending_outgoing":
                    c2.info("بانتظار الرد")
                elif fs == "pending_incoming":
                    c2.warning("طلب لك (تبويب الطلبات)")
                else:
                    if c2.button("إضافة", key=f"add_{r['user_id']}"):
                        if call(api.friend_request, S.token, r['user_id']):
                            st.rerun()

    with tab_dm:
        friends = call(api.friends_list, S.token) or []
        if not friends:
            st.caption("أضف صديقاً أولاً للبدء بالمحادثة.")
            return
        opts = {f['friend']['user_id']: (f"#{f['friend'].get('handle') or '----'} · {f['friend']['full_name']}") for f in friends}
        default = S.get("_dm_open_with", {}).get("user_id") if S.get("_dm_open_with") else next(iter(opts))
        pick = st.selectbox("محادثة مع", list(opts), index=list(opts).index(default) if default in opts else 0,
                            format_func=opts.get, key="dm_pick")
        thread = call(api.dm_thread, S.token, pick) or []
        for m in thread:
            mine = m["sender_id"] == S.me["user_id"]
            role = "user" if mine else "assistant"
            with st.chat_message(role):
                st.markdown(e(m["body"]))
        with st.form("dm_form", clear_on_submit=True):
            body = st.text_input("رسالتك", key="dm_body", label_visibility="collapsed",
                                 placeholder="اكتب رسالة...")
            sent = st.form_submit_button("إرسال ✉️")
        if sent and body and body.strip():
            if call(api.dm_send, S.token, pick, body.strip()[:1000]):
                st.rerun()


# ======================================================================== plans / checkout
CHECKOUT_KEY = "_checkout_plan"


def _checkout(plan_name: str, amount_jod: float):
    st.markdown(f"### إتمام الاشتراك — الباقة {plan_name}")
    st.markdown(f"<div class='clean-card'><b>المبلغ الإجمالي:</b> {amount_jod:.2f} د.أ / سنة</div>",
                unsafe_allow_html=True)
    with st.form("checkout_form"):
        c1, c2 = st.columns(2)
        holder = c1.text_input("اسم صاحب البطاقة", key="ck_name", placeholder="مثال: سارة أحمد")
        card   = c2.text_input("رقم البطاقة", key="ck_card", placeholder="4242 4242 4242 4242")
        c3, c4, c5 = st.columns([2, 1, 1])
        billing = c3.text_input("العنوان", key="ck_addr", placeholder="عمّان، الأردن")
        expiry  = c4.text_input("تاريخ الانتهاء", key="ck_exp", placeholder="MM/YY")
        cvv     = c5.text_input("CVV", key="ck_cvv", placeholder="123", max_chars=4, type="password")
        st.caption("💳 هذه شاشة عرض تجاري. لا يتم تحصيل مبالغ فعلية حالياً — بوابة الدفع (HyperPay/Stripe) ستُفعّل بعد التحكيم.")
        pay = st.form_submit_button(f"ادفع {amount_jod:.2f} د.أ 💳")
    if pay:
        card_clean = "".join(card.split())
        if not holder.strip():
            st.error("يرجى إدخال اسم صاحب البطاقة.")
        elif not card_clean.isdigit() or len(card_clean) not in (15, 16):
            st.error("رقم البطاقة يجب أن يتكوّن من 15 أو 16 رقماً.")
        elif "/" not in expiry or len(expiry) != 5:
            st.error("تاريخ الانتهاء بصيغة MM/YY.")
        elif not cvv.isdigit() or len(cvv) not in (3, 4):
            st.error("CVV غير صحيح.")
        else:
            plan_code = "pro" if plan_name == "Pro" else "max"
            session = call(api.checkout_start, S.token, plan_code)
            if session:
                if session.get("stripe_url"):
                    st.markdown(f"[💳 اذهب إلى بوابة الدفع الآمنة]({session['stripe_url']})")
                    st.info("بعد إتمام الدفع في Stripe (استخدم بطاقة الاختبار 4242 4242 4242 4242 + أي تاريخ مستقبلي)، عد إلى هذه الصفحة.")
                else:
                    result = call(api.checkout_confirm, S.token, session["session_id"],
                                  card_clean[-4:], holder.strip())
                    if result and result.get("status") == "succeeded":
                        st.balloons()
                        S[CHECKOUT_KEY] = None
                        me = call(api.me, S.token)
                        if me: S.me = me
                        st.success(f"✅ تم تفعيل الباقة {plan_name} — رقم العملية: {result['session_id'][:8]}. "
                                   f"صالحة لسنة كاملة.")
                        if st.button("العودة", key="ck_back"):
                            st.rerun()

PLAN_TAB = "📦 الباقات"


def plans_page():
    if S.get(CHECKOUT_KEY):
        name, amount = S[CHECKOUT_KEY]
        _checkout(name, amount)
        if st.button("← رجوع إلى الباقات", key="ck_back_top"):
            S[CHECKOUT_KEY] = None
            st.rerun()
        return
    st.markdown(f"""
<div class='clean-card'>
  <h3 style='margin-top:0'>ثلاث باقات، مبنية على استخدام حقيقي</h3>
  <p class='fb-sub'>الأسعار أدناه اقتراحية لأغراض العرض التجاري في الحكم. الدفع الفعلي غير مفعّل في هذه النسخة.</p>
</div>""", unsafe_allow_html=True)
    cols = st.columns(3)
    plans = [
        ("Basic", "مجاناً للأبد", 0.0, "ابدأ اليوم",
         ["شجرة المنهج الأساسية (الصف السادس)",
          "20 سؤال تحدٍ في اليوم",
          "تاريخ أسبوع واحد",
          "معلم ذكي: 5 رسائل / يوم",
          "متجر الشخصية الأساسي",
          "— بدون تشخيص الفجوة الجذرية —",
          "— بدون مجموعات الصف —"]),
        ("Pro", "4.99 د.أ / شهر", 4.99, "الأكثر طلباً",
         ["كل محتوى Basic",
          "تشخيص الفجوة الجذرية الكامل",
          "أسئلة تحدٍ بلا حد",
          "معلم ذكي بلا حد يومي",
          "تاريخ تعلّم كامل + تقارير",
          "خزائن مظهر مميّزة",
          "صداقات + رسائل خاصة",
          "دعم عبر البريد (24 ساعة)"]),
        ("School", "1.49 د.أ / طالب شهرياً", 1.49, "للمعلّمين والمدارس",
         ["كل ميزات Pro",
          "إنشاء مجموعات صف (مثل Teams)",
          "واجبات لكل درس بموعد تسليم",
          "مسابقات صفّية + لوحة متصدّرين",
          "لوحة متابعة لكل طالب في الصف",
          "تقارير أولياء الأمور آلياً",
          "تصدير النتائج PDF/Excel",
          "دعم عبر الواتساب"]),
    ]
    for col, (name, price, price_jod, tag, feats) in zip(cols, plans):
        with col:
            is_pro = (name == "Pro")
            border = f"2px solid {C['emerald']}" if is_pro else "1px solid rgba(143,176,155,.45)"
            badge  = f"<div style='position:absolute; top:-12px; left:50%; transform:translateX(-50%); background:{C['emerald']}; color:#07160E; padding:3px 12px; border-radius:999px; font-weight:900; font-size:11px'>الأكثر طلباً</div>" if is_pro else ""
            st.markdown(f"""
<div class='clean-card' style='position:relative; border:{border}; text-align:center; height:460px; display:flex; flex-direction:column'>
  {badge}
  <h3 style='margin:4px 0 2px; color:{C['emerald']}; font-size:22px'>{name}</h3>
  <p class='fb-sub' style='margin:0 0 10px'>{tag}</p>
  <p style='font-size:26px; font-weight:900; margin:4px 0 2px; color:{C['gold']}'>{price}</p>
  <hr style='opacity:.2; margin:10px 0'>
  <ul style='text-align:right; padding-right:16px; margin:0; flex-grow:1; list-style:none'>
    {"".join(f"<li style='padding:3px 0'>✓ {ff}</li>" if not ff.startswith('—') else f"<li style='padding:3px 0; opacity:.4'>{ff.strip('— ')}</li>" for ff in feats)}
  </ul>
</div>""", unsafe_allow_html=True)
            if st.button(f"اختر {name}", key=f"plan_{name}", disabled=(name == "Basic")):
                S[CHECKOUT_KEY] = (name, price_jod)
                st.rerun()


if not S.token or not S.me:
    auth_page()
else:
    role_ar = ROLE_AR.get(S.me['role'], '')
    org_suffix = f" · {S.me['organization_name']}" if S.me.get('organization_name') else ''
    header(f"مرحباً {S.me['full_name']} 👋 — {role_ar}{org_suffix}")
    _boot = S.get("_boot") if S.me["role"] == "student" else None
    _pending = (_boot or {}).get("incoming_friend_requests", 0) if _boot else 0
    community_label = "👥 المجتمع" + (f" ({_pending})" if _pending else "")
    tab_home, tab_classrooms, tab_community, tab_plans = st.tabs(
        ["🏠 الرئيسية", "🏫 الصفوف", community_label, PLAN_TAB])
    with tab_home:
        if S.me["role"] == "student":
            student_page()
        else:
            staff_page()
    with tab_classrooms:
        classrooms_page()
    with tab_community:
        community_page()
    with tab_plans:
        plans_page()