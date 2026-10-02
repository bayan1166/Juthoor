import json
from dataclasses import replace

from app.config import settings
from app.engine import config as ecfg
from app.engine import knowledge_graph as kg
from app.services.breaker import Breaker
from app.services.rag import guardrail, offline_tutor
from app.services.rag.retriever import retrieve
from app.services.rag.turn import SocraticTurn

SYSTEM_PROMPT = """أنت المعلم الذكي في منصة "جذور" لتعليم __COURSE__.

مهمتك أن تعلّم فعلاً، لا أن تطرح أسئلة فقط. تصرّف حسب طلب الطالب:
1. إذا طلب شرحاً (اشرح، ما هو، كيف أحسب، فسّر): اشرح الفكرة بوضوح في جمل قصيرة، ثم أعطِ مثالاً محلولاً بأرقام صغيرة.
2. إذا أعطاك مسألة: فكّكها إلى خطوات مرقّمة، واذكر القاعدة المستعملة في كل خطوة، ثم اكتب الناتج النهائي. إن وصلك حقل "الحل المحقق" فاعتمده كما هو دون تغيير أي رقم.
3. إذا قال إنه عالق أو لم يفهم: اطرح عليه سؤالاً تشخيصياً واحداً محدداً بصيغة «كم ناتج ...؟»، ثم اشرح بعد جوابه.
4. إذا أجاب عن تمرين سابق: قيّم جوابه، وإن كان خاطئاً فأظهر موضع الخطأ وصحّحه.

قواعد صارمة:
- إن كان سؤال الطالب خارج منهج الرياضيات فأعد في حقل reply هذا النص حرفياً دون أي إضافة: عذراً، أنا مبرمج حصرياً لمساعدتك في المنهج التعليمي وتطوير مستواك الأكاديمي.
- اكتب بالعربية الفصحى البسيطة.
- لا تستعمل أي رموز تعبيرية.
- اجعل الرد مختصراً ومنظّماً، ولا تُحل الطالب إلى معلم آخر.
- اكتب المسائل الرياضية بأرقام لاتينية وإشارة الناقص "-" أو "−".
- إن كان سبب الصعوبة درساً سابقاً في المنهج (مثل صعوبة الجمع عند الضرب)، فعيّن "gap_detected": true و"gap_skill" بمعرّف الدرس السابق من القائمة.

أعد JSON فقط بالشكل:
{"reply": "ردّك بالعربية", "gap_detected": true أو false, "gap_skill": "معرّف الدرس أو سلسلة فارغة", "misconception": "وصف قصير للالتباس أو سلسلة فارغة"}""".replace("__COURSE__", ecfg.COURSE["description_ar"])

USER_TEMPLATE = """الدروس المتاحة (استعمل المعرّف فقط): {skill_ids}
الدرس الحالي للطالب: {skill_name}

مقتطفات من المنهج:
{context}

الحل المحقق (إن وُجد): {hint}

رسالة الطالب:
{message}"""


def _client():
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            return "openai", OpenAI(api_key=settings.openai_api_key)
        except Exception:
            pass
    if settings.groq_api_key:
        try:
            from groq import Groq

            return "groq", Groq(api_key=settings.groq_api_key)
        except Exception:
            pass
    return None


def _extract_json(raw: str) -> dict:
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(raw[start:end + 1])


def _safe_retrieve(message: str, skill_id: str | None) -> list[dict]:
    try:
        return retrieve(message, skill_id=skill_id, top_k=4)
    except Exception:
        return []


def _parse(raw: str, retrieved_ids: list[str]) -> SocraticTurn | None:
    try:
        data = _extract_json(raw)
        reply = str(data.get("reply", "")).strip()
        if not reply:
            return None
        gap_skill = str(data.get("gap_skill") or "").strip()
        if gap_skill and gap_skill not in kg.SKILLS:
            gap_skill = ""
        return SocraticTurn(
            reply=reply,
            gap_detected=bool(data.get("gap_detected", False)) and bool(gap_skill),
            gap_skill=gap_skill,
            misconception=str(data.get("misconception") or "").strip(),
            retrieved_ids=retrieved_ids,
            source="llm_rag" if retrieved_ids else "llm",
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, AttributeError):
        return None


def _llm_turn(picked, skill_context: str, history: list[dict], message: str, chunks: list[dict]) -> SocraticTurn | None:
    provider, client = picked
    skill_name = kg.SKILLS[skill_context].name_ar if skill_context in kg.SKILLS else "غير محدد"
    context_block = "\n".join(f"- {c['text']}" for c in chunks) or "- لا يوجد"
    final = USER_TEMPLATE.format(
        skill_ids=", ".join(kg.SKILLS.keys()), skill_name=skill_name, context=context_block,
        hint=offline_tutor.solution_hint(message) or "لا يوجد", message=message,
    )
    turns = [{"role": "assistant" if h["role"] == "tutor" else "user", "content": h["content"]}
             for h in history[-8:] if h["role"] in ("tutor", "student")]
    model = settings.openai_chat_model if provider == "openai" else settings.groq_chat_model
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *turns, {"role": "user", "content": final}],
        temperature=0.3, response_format={"type": "json_object"}, max_tokens=700, timeout=settings.llm_timeout_seconds,
    )
    return _parse(resp.choices[0].message.content, [c["id"] for c in chunks])


BREAKER = Breaker(threshold=2, cooldown=60.0)


def _offline_source(message: str) -> str:
    try:
        if offline_tutor.solve_fraction(message) or offline_tutor.solve_lines(message):
            return "solver"
        if offline_tutor.parse_int_answer(message) is not None or offline_tutor.parse_fraction_answer(message) is not None:
            return "solver"
    except Exception:
        pass
    return "tutor"


def generate_turn(skill_context: str, history: list[dict], message: str) -> SocraticTurn:
    if guardrail.is_off_topic(message):
        return SocraticTurn(reply=guardrail.FALLBACK, gap_detected=False, gap_skill="", misconception="", retrieved_ids=[], source="guardrail")
    picked = _client()
    if picked is not None and BREAKER.allow():
        try:
            chunks = _safe_retrieve(message, skill_context or None)
            turn = _llm_turn(picked, skill_context, history, message, chunks)
            if turn is not None:
                BREAKER.success()
                return turn
            BREAKER.failure()
        except Exception:
            BREAKER.failure()
    return replace(offline_tutor.offline_turn(skill_context, history, message), source=_offline_source(message))
