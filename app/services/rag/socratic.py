import json
from dataclasses import dataclass

from app.config import settings
from app.engine import knowledge_graph as kg
from app.services.rag.retriever import retrieve

SYSTEM_PROMPT = """أنت المعلم الذكي في منصة "جذور" لتعليم الرياضيات لطلاب الصف السادس بالأردن.

مهمتك أن تعلّم فعلاً — لست مجرد مساعد يسأل أسئلة. تصرّف حسب ما يحتاجه الطالب:

1. إذا طلب الشرح (مثل: "اشرح لي"، "ما هو"، "كيف أحسب"، "فسّر"): اشرح الفكرة بوضوح في جملتين إلى أربع، ثم أعطِ مثالاً محلولاً بأرقام صغيرة.
2. إذا أعطاك مسألة محدّدة (مثل: "ما ناتج 7 + (-3)"، "أوجد المسافة"): حلّها خطوة بخطوة بترقيم الخطوات، ثم أعطِ الجواب النهائي، ثم اسأله: "هل جربّت مسألة مشابهة؟"
3. إذا قال إنه عالق أو مش فاهم: اسأله سؤالاً واحداً محدّداً لتعرف من أين تبدأ ("أي خطوة أول خطوة ما فهمتها؟"), ثم اشرح.
4. إذا كان يعرف ما يفعل لكنه يراجع: شجّعه واسأله ماذا يريد أن يفعل تالياً.

قواعد صارمة:
- اكتب بالعربية الفصحى البسيطة، لا بالإنجليزية.
- اجعل كل رد قصيراً وواضحاً.
- لا تنتظر، لا تتهرّب، لا تُحيل الطالب إلى المعلم: علّمه الآن.
- استخدم أرقاماً صغيرة في الأمثلة (أقل من 20).
- إذا لاحظت أن سبب الصعوبة درس سابق في المنهج (مثلاً: لا يستطيع الجمع، فكيف يضرب؟)، حدّد "gap_detected": true و "gap_skill" بـ id الدرس المناسب من القائمة.

أعِد JSON فقط بالشكل التالي، بدون أي نص خارج القوسين:
{"reply": "ردّك بالعربية هنا", "gap_detected": true/false, "gap_skill": "skill_id أو null"}
"""

USER_TEMPLATE = """الدروس المتاحة (استخدم id من هنا فقط): {skill_ids}
الدرس الحالي للطالب: {skill_name}

مقتطفات من المنهج قد تساعدك:
{context}

آخر رسائل في المحادثة:
{history}

رسالة الطالب الجديدة:
{message}

الآن ردّ على الطالب."""


@dataclass
class SocraticTurn:
    reply: str
    gap_detected: bool
    gap_skill: str
    misconception: str
    retrieved_ids: list[str]


def _client():
    """Return (provider, sdk) or None. Prefers OpenAI (smarter), falls back to Groq."""
    if settings.openai_api_key:
        try:
            from openai import OpenAI
            return ("openai", OpenAI(api_key=settings.openai_api_key))
        except Exception:
            pass
    if settings.groq_api_key:
        try:
            from groq import Groq
            return ("groq", Groq(api_key=settings.groq_api_key))
        except Exception:
            pass
    return None


def _fallback_turn(retrieved_ids: list[str]) -> SocraticTurn:
    return SocraticTurn(
        reply="ممتاز، خبريني كيف بدك تبدئي بحل هذا السؤال، خطوة خطوة؟",
        gap_detected=False, gap_skill="", misconception="", retrieved_ids=retrieved_ids,
    )


def _extract_json(raw: str) -> dict:
    """Models sometimes wrap the JSON in prose or code fences; take the outermost {...}."""
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(raw[start:end + 1])


def _safe_retrieve(message: str, skill_id: str | None) -> list[dict]:
    # An empty/uningested vector store or a missing chromadb install must not 500 the chat.
    try:
        return retrieve(message, skill_id=skill_id, top_k=5)
    except Exception:
        return []


def _parse(raw: str, retrieved_ids: list[str]) -> SocraticTurn | None:
    try:
        data = _extract_json(raw)
        reply = str(data["reply"]).strip()
        if not reply:
            return None
        gap_skill = str(data.get("gap_skill", "")).strip()
        if gap_skill and gap_skill not in kg.SKILLS:
            gap_skill = ""
        return SocraticTurn(
            reply=reply,
            gap_detected=bool(data.get("gap_detected", False)) and bool(gap_skill),
            gap_skill=gap_skill,
            misconception=str(data.get("misconception", "")).strip(),
            retrieved_ids=retrieved_ids,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def generate_turn(skill_context: str, history: list[dict], message: str) -> SocraticTurn:
    chunks = _safe_retrieve(message, skill_context or None)
    retrieved_ids = [c["id"] for c in chunks]
    context_block = "\n".join(f"- {c['text']}" for c in chunks) or "- (no matching context)"
    history_block = "\n".join(f"{h['role']}: {h['content']}" for h in history[-8:]) or "(new conversation)"
    skill_name = kg.SKILLS[skill_context].name_ar if skill_context in kg.SKILLS else "غير محدد"

    picked = _client()
    if picked is not None:
        provider, client = picked
        try:
            user_prompt = USER_TEMPLATE.format(
                skill_ids=", ".join(kg.SKILLS.keys()),
                skill_name=skill_name, context=context_block,
                history=history_block, message=message,
            )
            model = settings.openai_chat_model if provider == "openai" else settings.groq_chat_model
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": user_prompt}],
                temperature=0.4, response_format={"type": "json_object"},
                max_tokens=400, timeout=6,
            )
            parsed = _parse(resp.choices[0].message.content, retrieved_ids)
            if parsed is not None:
                return parsed
        except Exception:
            pass

    return _fallback_turn(retrieved_ids)
