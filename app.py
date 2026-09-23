import html
import random

import streamlit as st

# محرك الذكاء وبنك الأسئلة
import knowledge_graph as kg
import adaptive_engine as ae
import offline_bank as ob
import practice as pr
import config

# التصميم
<<<<<<< HEAD
import theme
=======
from theme import PALETTE as C
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23
import brand
import tree_view as tv
import tree_component as tc
import avatar as av
import avatar_items as ai
import curriculum as cur

st.set_page_config(page_title="جذور | Juthoor", layout="centered", page_icon="🌳", initial_sidebar_state="collapsed")

RNG = random.Random()

# ==========================================
<<<<<<< HEAD
# 0. الحالة اللي لازم تكون جاهزة قبل أي CSS (وضع ليلي/نهاري)
# ==========================================
S = st.session_state
if 'dark_mode' not in S: S.dark_mode = True     # الوضع الافتراضي هو الليلي (هوية الشعار الأصلية)

C = theme.get_palette(S.dark_mode)

# ==========================================
=======
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23
# 1. CSS العام للتطبيق
# ==========================================
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Aref+Ruqaa:wght@400;700&display=swap');

    * {{ font-family: 'Tajawal', sans-serif !important; direction: rtl; text-align: right; }}

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

<<<<<<< HEAD
    /* ====================================================================
       عناصر Streamlit الأصلية (حقول، نماذج، تبويبات، مفتاح الوضع الليلي...)
       تُعاد تلوينها بالكامل هنا بدل الاعتماد على مظهرها الافتراضي، حتى تبقى
       متسقة مع الهوية البصرية في كل من الوضع الليلي والنهاري.
       ==================================================================== */
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
    /* مفتاح الوضع الليلي/النهاري (st.toggle -- يظهر كـ stToggle أو stCheckbox حسب إصدار Streamlit) */
    div[data-testid="stToggle"] label p, div[data-testid="stCheckbox"] label p {{ color: {C['text']} !important; font-weight: 700; }}
    div[data-testid="stCheckbox"] label > div:not([data-testid="stWidgetLabel"]) {{ background-color: {C['lift']} !important; border: 1px solid {C['muted']}; }}
    div[data-testid="stCheckbox"] label[data-selected="true"] > div:not([data-testid="stWidgetLabel"]) {{ background-color: {C['gold_deep']} !important; border-color: {C['gold_deep']}; }}
    .theme-caption {{ color: {C['muted']}; font-size: 12px; margin-top: -10px; }}

=======
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23
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

# ==========================================
# 2. تهيئة حالة الجلسة
# ==========================================
<<<<<<< HEAD
=======
S = st.session_state
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23
if 'auth_status' not in S: S.auth_status = "login"
if 'user_data' not in S: S.user_data = {"name": "", "national_id": "", "school": ""}

if 'student_state' not in S:
    S.student_state = ae.StudentState()
    ae.start_round(S.student_state)

for _k, _v in (('current_question', None), ('feedback', None), ('remedial', None), ('round_done', False),
<<<<<<< HEAD
               ('recent_q', []), ('qn', 0), ('selected_lesson', None), ('open_lesson', None), ('_last_click', None),
               ('pending_breadcrumb', None)):
=======
               ('recent_q', []), ('qn', 0), ('selected_lesson', None), ('open_lesson', None), ('_last_click', None)):
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23
    if _k not in S: S[_k] = _v

if 'gami_state' not in S:
    S.gami_state = {
        'points': 100, 'streak': 2,
        'gender': 'ولد', 'skin': 'f8d25c', 'clothing': 'shirtCrewNeck', 'accessories': 'blank', 'top': 'hat',
        'hair': 'straight', 'hair_color': 'black', 'neck': 'none',
        'inventory': ['shirtCrewNeck', 'blank', 'hat']
    }
for _k, _v in av.DEFAULTS.items():                  # حالة قديمة بدون الحقول الجديدة
    S.gami_state.setdefault(_k, _v)


<<<<<<< HEAD
def theme_toggle_row():
    """مفتاح تبديل الوضع الليلي/النهاري، يظهر في أعلى كل صفحة (تسجيل الدخول والتطبيق نفسه)."""
    col_spacer, col_toggle = st.columns([5, 2])
    with col_toggle:
        new_val = st.toggle("🌙 ليلي" if S.dark_mode else "☀️ نهاري", value=S.dark_mode, key="dark_mode_toggle")
    if new_val != S.dark_mode:
        S.dark_mode = new_val
        st.rerun()


=======
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23
def av_kwargs(g, **over):
    kw = dict(gender=g['gender'], skin=g['skin'], clothing=g['clothing'], accessories=g['accessories'],
              top=g['top'], hair=g['hair'], hair_color=g['hair_color'], neck=g['neck'])
    kw.update(over)
    return kw


# ==========================================
# 3. دوال المتجر والأفاتار
# ==========================================
def owned(item):
    return item.price == 0 or item.id in S.gami_state['inventory']


def get_item(item):
    g = S.gami_state
    if not owned(item):
        if g['points'] < item.price:
            st.error("نقاطك لا تكفي! حل المزيد من التحديات.")
            return
        g['points'] -= item.price
        g['inventory'].append(item.id)
        st.toast("تم الشراء والتجهيز! 🎉")
    else:
        st.toast("تم التجهيز بنجاح! ✅")
    g[item.cat] = item.id
    for cat, iid in item.bundle:                    # بدلة الوظيفة تأتي مع قبعتها
        if iid not in g['inventory']:
            g['inventory'].append(iid)
        g[cat] = iid


def set_option(cat, key):
    g = S.gami_state
    g[cat] = S[key]
    if cat == 'gender':
        av.fit_to_gender(g)


def option_row(label, cat, options, key):
    """خيارات مجانية (النوع، البشرة، الشعر) — الحالة تُحدَّث عبر on_change."""
    ids = [o[0] for o in options]
    cur_val = S.gami_state[cat]
    S[key] = cur_val if cur_val in ids else ids[0]
    names = dict(options)
    st.radio(label, ids, format_func=lambda i: names[i], horizontal=True, key=key, on_change=set_option, args=(cat, key))


SHOP_SECTIONS = {
    "👕 الملابس": [("tees", "تيشيرتات"), ("hoodies", "هوديات"), ("jackets", "جاكيتات ومعاطف"), ("heritage", "الزي التراثي")],
    "💼 الوظائف": [("jobs", "بدلات الوظائف (مع قبعتها)")],
    "🧢 أغطية الرأس": [("caps", "قبعات"), ("winter", "طواقي الشتاء"), ("heritage_head", "الشماغ والحطة"), ("hijab", "الحجاب"), ("jobcaps", "قبعات الوظائف")],
    "🧣 اللفحات": [("scarves", "لفحات")],
    "👓 النظارات": [("glasses", "نظارات")],
}


def shop_grid(group, title):
    g = S.gami_state
    its = av.items(group, g['gender'])
    if not its:
        return
    st.markdown(f"#### {title}")
    for row in range(0, len(its), 3):
        cols = st.columns(3)
        for col, it in zip(cols, its[row:row + 3]):
            with col:
                kw = av_kwargs(g, **{it.cat: it.id})
                for cat, iid in it.bundle:
                    kw[cat] = iid
                on = g[it.cat] == it.id
                svg = av.avatar_svg(uid=f"pv{group}{it.id}", **kw)
                st.markdown(f"<div class='shop-card {'on' if on else ''}'>{svg}<div class='shop-name'>{html.escape(it.name)}</div></div>", unsafe_allow_html=True)
                label = "✅ مُلبَّس" if on else ("ارتداء" if owned(it) else f"{it.price} 🪙")
                if st.button(label, key=f"shop_{it.cat}_{it.id}"):
                    get_item(it)
                    st.rerun()


# ==========================================
# 4. دوال التقييم
# ==========================================
def _set_question(q):
    opts = None
    if q.get('type', 'mcq') == 'mcq':
        opts = [q['correct_answer']] + [d['text'] for d in q['distractors']]
        RNG.shuffle(opts)
    S.qn += 1
    S.current_question = {**q, 'options': opts, 'skill_name': kg.SKILLS[q['skill']].name_ar}
    S.recent_q = (S.recent_q + [q['question']])[-12:]


def load_q():
    state = S.student_state
<<<<<<< HEAD
    q = ob.generate_offline(state.current_skill, state.difficulty, RNG, avoid=S.recent_q)
    if S.pending_breadcrumb:                        # المحرك انتقل بين الدروس؛ فسّر السبب للطالب
        q = {**q, "banner": S.pending_breadcrumb}
        S.pending_breadcrumb = None
    _set_question(q)
=======
    _set_question(ob.generate_offline(state.current_skill, state.difficulty, RNG, avoid=S.recent_q))
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23


def load_remedial():
    """بعد الخطأ: سؤال على نفس النمط، ثم (إن أخطأ مجدداً) سؤال من مستوى أقل."""
    plan = S.remedial
    if plan['stage'] == pr.SAME:
        _set_question(pr.same_pattern_question(plan, RNG, S.recent_q))
    else:
        _set_question(pr.easier_question(plan, S.student_state, RNG, S.recent_q))


NEXT_LABEL = {None: "التحدي التالي 🚀", pr.SAME: "سؤال على الفكرة نفسها 🔁", pr.EASIER: "سؤال أبسط 🌱"}


def ans_q(selected):
    state = S.student_state
    q = S.current_question
    ok = pr.is_correct(q, selected)
    kind = q.get('remedial')                       # None = سؤال عادي | same_pattern | easier

    if kind is None:
        dec = ae.decide_next(state, ok)            # المحرك يرى الأسئلة العادية فقط
        S.round_done = S.round_done or dec.round_over or ae.round_over(state)
<<<<<<< HEAD
        S.remedial = None if ok else pr.start(q, selected)
        # إن نقل المحرك الطالب لدرس آخر (تراجع/عودة/علاج/جديد) اعرض السبب على السؤال
        # القادم من ae.decide_next -- سيُعرض فوراً إن لم يوجد علاج فوري، أو بعد
        # انتهاء جولة العلاج الفوري في practice.py (التي تُعرض بشاراتها الخاصة أولاً).
        S.pending_breadcrumb = dec.breadcrumb or None
=======
        S.remedial = None if ok else pr.start(q)
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23
    else:
        S.remedial = pr.advance(S.remedial, ok)

    if ok:
        S.gami_state['points'] += 3 if kind is None else 2
    S.feedback = {"ok": ok, "q": q, "chosen": selected, "kind": kind,
                  "card": None if ok else pr.mistake_card(q, selected),
                  "next": NEXT_LABEL[S.remedial['stage'] if S.remedial else None]}
    S.current_question = None


def e(text):
    return html.escape(str(text))


def feedback_html(fb):
    q = fb['q']
    if fb['ok']:
        head = "إجابة دقيقة! (+3 🪙)" if fb['kind'] is None else "أحسنت، فهمت الفكرة! (+2 🪙)"
        return (f"<div class='feedback-box success-box'>{head}<div class='fb-sub'>{e(q['explanation'])}</div></div>")
    if fb['kind'] is None:
        head = "عثرة بسيطة! هذه بطاقة تشرح الفكرة 👇"
    elif fb['kind'] == pr.SAME:
        head = "ما زالت الفكرة تحتاج تثبيتاً. راجع البطاقة ثم نجرّب سؤالاً أبسط 👇"
    else:
        head = "لا بأس! سنعود لهذه الفكرة لاحقاً. راجع البطاقة 👇"
    c = fb['card']
    chosen = ob._show(c['chosen']) if c['type'] == 'input' else c['chosen']
    why = f"<div class='mc-why'>💡 غالباً فكّرت هكذا: {e(c['why'])}</div>" if c['why'] else ""
    card = (f"<div class='mistake-card'><div class='mc-head'>🍃 بطاقة شرح: {e(c['title'])}</div>"
            f"<div class='mc-answers'><span class='mc-chip bad'>إجابتك: {e(chosen) if chosen.strip() else '—'}</span>"
            f"<span class='mc-chip good'>الصحيح: {e(c['correct'])}</span></div>{why}"
            f"<div class='mc-sec'><b>القاعدة</b><p>{e(c['rule'])}</p></div>"
            f"<div class='mc-sec'><b>مثال محلول</b><p>{e(c['example'])}</p></div>"
            f"<div class='mc-sec'><b>حل سؤالك</b><p>{e(c['solution'])}</p></div></div>")
    return f"<div class='feedback-box error-box'>{head}</div>{card}"


# ==========================================
<<<<<<< HEAD
# 5. واجهة تسجيل الدخول / إنشاء حساب
# ==========================================
if S.auth_status in ("login", "signup"):
    theme_toggle_row()
    st.markdown(f"<div style='display:flex; justify-content:center; margin-top:10px;'>{brand.lockup_html(80)}</div>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:{C['muted']}; margin-top:-10px;'>منصة ذكاء المناهج — سجّلي الدخول لمتابعة رحلتك</p>", unsafe_allow_html=True)

    _, col_mid, _ = st.columns([1, 3, 1])
    with col_mid:
        tab_login, tab_signup = st.tabs(["🔑 تسجيل الدخول", "✨ حساب جديد"])

        with tab_login:
            with st.form("login_form"):
                st.markdown("##### أدخلي رقمك الوطني للمتابعة")
                nid = st.text_input("الرقم الوطني:", key="login_nid", placeholder="مثال: 9912345678")
                submitted = st.form_submit_button("دخول 🚀")
            if submitted:
                nid_clean = nid.strip()
                if not nid_clean:
                    st.error("يرجى إدخال الرقم الوطني.")
                elif not nid_clean.isdigit():
                    st.error("الرقم الوطني يجب أن يتكوّن من أرقام فقط.")
                elif len(nid_clean) < 6:
                    st.error("هذا الرقم الوطني أقصر من المتوقع، تحققي منه.")
                else:
                    S.user_data["national_id"] = nid_clean
                    S.auth_status = "logged_in"
                    st.rerun()

        with tab_signup:
            with st.form("signup_form"):
                st.markdown("##### أنشئي حساباً جديداً")
                name = st.text_input("الاسم الكامل:", key="signup_name", placeholder="مثال: سارة أحمد")
                nid2 = st.text_input("الرقم الوطني:", key="signup_nid", placeholder="مثال: 9912345678")
                submitted2 = st.form_submit_button("تأكيد وإنشاء الحساب ✅")
            if submitted2:
                name_clean, nid2_clean = name.strip(), nid2.strip()
                if not name_clean or not nid2_clean:
                    st.error("يرجى تعبئة الحقول الأساسية.")
                elif not nid2_clean.isdigit() or len(nid2_clean) < 6:
                    st.error("الرقم الوطني يجب أن يتكوّن من أرقام فقط، وبطول معقول.")
                else:
                    S.user_data = {"name": name_clean, "national_id": nid2_clean}
                    S.auth_status = "logged_in"
                    st.rerun()
=======
# 5. واجهة تسجيل الدخول
# ==========================================
if S.auth_status == "login":
    st.markdown(f"<div style='display:flex; justify-content:center; margin-top:50px;'>{brand.lockup_html(80)}</div>", unsafe_allow_html=True)
    st.markdown("<div class='clean-card'>", unsafe_allow_html=True)
    st.markdown("### تسجيل الدخول")
    nid = st.text_input("الرقم الوطني:")
    if st.button("دخول 🚀"):
        if nid: S.auth_status = "logged_in"; st.rerun()
        else: st.error("يرجى إدخال الرقم الوطني.")
    st.markdown("---")
    if st.button("ليس لديك حساب؟ إنشاء حساب جديد"):
        S.auth_status = "signup"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif S.auth_status == "signup":
    st.markdown(f"<div style='display:flex; justify-content:center; margin-top:50px;'>{brand.lockup_html(80)}</div>", unsafe_allow_html=True)
    st.markdown("<div class='clean-card'>", unsafe_allow_html=True)
    name = st.text_input("الاسم الكامل:")
    nid = st.text_input("الرقم الوطني:")
    if st.button("تأكيد وإنشاء الحساب ✅"):
        if name and nid:
            S.user_data = {"name": name, "national_id": nid}
            S.auth_status = "logged_in"; st.rerun()
        else:
            st.error("يرجى تعبئة الحقول الأساسية.")
    if st.button("العودة لتسجيل الدخول"):
        S.auth_status = "login"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23

# ==========================================
# 6. الواجهة الرئيسية
# ==========================================
elif S.auth_status == "logged_in":
    state = S.student_state
    g = S.gami_state

    # --- رأس الصفحة (الشعار، الإحصائيات، الأفاتار) ---
<<<<<<< HEAD
    theme_toggle_row()
=======
>>>>>>> f5ddd40c5c4e762e0d6f52919782547350ed0f23
    st.markdown(brand.lockup_html(52), unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1.5])
    c1.markdown(f"<div class='clean-card' style='text-align:center;'><h3 style='margin:0; color:{C['gold']};'>🔥 {g['streak']}</h3><span style='font-size:12px;'>أيام متتالية</span></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='clean-card' style='text-align:center;'><h3 style='margin:0; color:{C['gold']};'>🪙 {g['points']}</h3><span style='font-size:12px;'>النقاط</span></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div style='text-align:center;'>{av.avatar_svg(size=100, **av_kwargs(g))}</div>", unsafe_allow_html=True)

    t_tree, t_quiz, t_shop = st.tabs(["🌳 المنهج", "🧩 التحديات", "🛒 المتجر"])

    # ------------------------------------------
    # 1. شجرة المنهج — اضغط على أي ورقة لتظهر أهم مفاهيم الدرس
    # ------------------------------------------
    _dialog_deco = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)

    def _lesson_panel(key, concepts=True):
        st.markdown(tv.detail_html(S.student_state, key, concepts=concepts), unsafe_allow_html=True)

    if _dialog_deco:
        try:
            _wrap = _dialog_deco("📖 أهم مفاهيم الدرس", width="large")
        except TypeError:
            _wrap = _dialog_deco("📖 أهم مفاهيم الدرس")

        @_wrap
        def show_lesson(key):
            _lesson_panel(key)
    else:
        show_lesson = None

    with t_tree:
        current_key = next((cur.lesson_key(u, l) for u, l in cur.all_lessons() if l.skill == state.current_skill), None)
        selected = S.selected_lesson or current_key

        clicked = tc.clickable_tree(state, selected)
        if clicked and clicked != S._last_click:          # ضغطة جديدة على ورقة
            S._last_click = clicked
            S.selected_lesson = clicked
            S.open_lesson = clicked
            st.rerun()

        # طريقة ثانية لاختيار الدرس (للأجهزة/الإصدارات التي لا يعمل فيها الضغط على الورقة)
        with st.expander("أو اختر الدرس من القائمة"):
            keys = [cur.lesson_key(u, l) for u, l in cur.all_lessons()]
            labels = {cur.lesson_key(u, l): f"الوحدة {u.no} · الدرس {l.no}: {l.title}" for u, l in cur.all_lessons()}
            pick = st.selectbox("الدرس", keys, index=keys.index(selected) if selected in keys else 0,
                                format_func=lambda k: labels[k], label_visibility="collapsed")
            if pick != selected:
                S.selected_lesson = S.open_lesson = pick
                st.rerun()

        if S.open_lesson:
            key, S.open_lesson = S.open_lesson, None
            if show_lesson:
                show_lesson(key)
            else:
                _lesson_panel(key)                        # إصدارات قديمة بلا نافذة منبثقة
        elif show_lesson is None and selected:
            _lesson_panel(selected)
        if show_lesson and current_key:
            _lesson_panel(current_key, concepts=False)

    # ------------------------------------------
    # 2. ساحة التحديات
    # ------------------------------------------
    with t_quiz:
        fb, q = S.feedback, S.current_question
        if fb:
            st.markdown(feedback_html(fb), unsafe_allow_html=True)
            if st.button(fb['next'], key="next_btn"):
                S.feedback = None
                if S.remedial:
                    load_remedial()
                st.rerun()
        elif q is None:
            if S.round_done or ae.round_over(state):
                st.success("أحسنت! أوراق شجرتك تنمو بشكل ممتاز اليوم.")
                if st.button("جلسة جديدة 🌱"):
                    ae.start_round(state)
                    S.current_question = S.feedback = S.remedial = None
                    S.round_done = False
                    st.rerun()
            else:
                load_q(); st.rerun()
        else:
            qid = S.qn
            if q.get('banner'):
                st.markdown(f"<div class='q-banner'>{e(q['banner'])}</div>", unsafe_allow_html=True)
            hint = f"<div class='q-hint'>💡 {e(q['hint'])}</div>" if q.get('guided') else ""
            st.markdown(f"<div class='clean-card'><span style='color:{C['gold']}; font-size:14px; font-weight:bold;'>🎯 {q['skill_name']}</span>"
                        f"<h3 style='margin-top:10px;'>{e(q['question'])}</h3>{hint}</div>", unsafe_allow_html=True)

            q_type = q.get('type', 'mcq')
            if q_type == "mcq":
                for i, opt in enumerate(q['options']):
                    if st.button(opt, key=f"opt_{qid}_{i}"): ans_q(opt); st.rerun()
            elif q_type == "tf":
                b1, b2 = st.columns(2)
                if b1.button("✔️ صح", key=f"t_{qid}"): ans_q("صح"); st.rerun()
                if b2.button("❌ خطأ", key=f"f_{qid}"): ans_q("خطأ"); st.rerun()
            elif q_type == "input":
                user_ans = st.text_input("اكتب إجابتك هنا:", key=f"inp_{qid}")
                if st.button("تأكيد الإجابة 🚀", key=f"ok_{qid}"): ans_q(user_ans); st.rerun()

    # ------------------------------------------
    # 3. المتجر
    # ------------------------------------------
    with t_shop:
        st.markdown(f"<div class='clean-card'><h3>🛒 المتجر</h3><p class='sub-text'>اختر القطع ليتم تلبيسها لشخصيتك. رصيدك: {g['points']} 🪙</p></div>", unsafe_allow_html=True)

        with st.expander("شكلك (مجاني)", expanded=False):
            option_row("النوع", 'gender', [("ولد", "ولد 👦"), ("بنت", "بنت 👧")], "opt_gender")
            option_row("لون البشرة", 'skin', av.SKIN_OPTIONS, "opt_skin")
            option_row("تسريحة الشعر", 'hair', [(k, v[0]) for k, v in av.HAIR_STYLES.items() if v[1] in (None, g['gender'])], "opt_hair")
            option_row("لون الشعر", 'hair_color', [(k, v[0]) for k, v in av.HAIR_COLORS.items()], "opt_hair_color")
            if g['gender'] == "بنت":
                st.caption("الحجاب من قسم «أغطية الرأس» — مجاني 🧕")

        section = st.radio("القسم", list(SHOP_SECTIONS), horizontal=True, key="shop_section", label_visibility="collapsed")
        for group, title in SHOP_SECTIONS[section]:
            shop_grid(group, title)
