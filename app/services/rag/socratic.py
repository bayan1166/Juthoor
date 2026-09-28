import json
from dataclasses import dataclass

from app.config import settings
from app.engine import knowledge_graph as kg
from app.services.rag.retriever import retrieve

SYSTEM_PROMPT = """\
You are Juthoor's Socratic Math Tutor for a 6th-grade student aged 11-12, speaking Arabic.

Non-negotiable rule: NEVER state the final numeric answer or the completed solution to the
student's current problem, even if asked directly or pressured. Instead:
- Ask one guiding question at a time that moves the student one step closer to the idea.
- Reference the retrieved curriculum context below when it is relevant.
- If the student is correct, confirm briefly and ask them to explain why, or extend the idea.
- If the student repeats the same wrong reasoning twice, or their message reveals they do not
  understand a PREREQUISITE skill (not just this one), set gap_detected to true and name the
  exact skill_id from the provided skill list that seems to be the real blocker.
- Keep replies to at most 3 short sentences. No LaTeX, no markdown, no emojis.

Return ONE JSON object and nothing else:
{
  "reply": "<socratic reply in Arabic>",
  "gap_detected": <true or false>,
  "gap_skill": "<skill_id from the list below, or empty string>",
  "misconception": "<short description of the exact misconception, or empty string>"
}
"""

USER_TEMPLATE = """\
Known skill ids: {skill_ids}
Current lesson context: {skill_name}
Retrieved curriculum context:
{context}

Conversation so far:
{history}

Student's latest message: {message}
"""


@dataclass
class SocraticTurn:
    reply: str
    gap_detected: bool
    gap_skill: str
    misconception: str
    retrieved_ids: list[str]


def _client():
    if not settings.groq_api_key:
        return None
    try:
        from groq import Groq
        return Groq(api_key=settings.groq_api_key)
    except Exception:
        return None


def _fallback_turn(retrieved_ids: list[str]) -> SocraticTurn:
    return SocraticTurn(
        reply="ممتاز، خبريني كيف بدك تبدئي بحل هذا السؤال، خطوة خطوة؟",
        gap_detected=False, gap_skill="", misconception="", retrieved_ids=retrieved_ids,
    )


def _parse(raw: str, retrieved_ids: list[str]) -> SocraticTurn | None:
    try:
        data = json.loads(raw)
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
    chunks = retrieve(message, skill_id=skill_context or None, top_k=5)
    retrieved_ids = [c["id"] for c in chunks]
    context_block = "\n".join(f"- {c['text']}" for c in chunks) or "- (no matching context)"
    history_block = "\n".join(f"{h['role']}: {h['content']}" for h in history[-8:]) or "(new conversation)"
    skill_name = kg.SKILLS[skill_context].name_ar if skill_context in kg.SKILLS else "غير محدد"

    client = _client()
    if client is not None:
        try:
            user_prompt = USER_TEMPLATE.format(
                skill_ids=", ".join(kg.SKILLS.keys()),
                skill_name=skill_name,
                context=context_block,
                history=history_block,
                message=message,
            )
            resp = client.chat.completions.create(
                model=settings.groq_chat_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=400,
                timeout=6,
            )
            parsed = _parse(resp.choices[0].message.content, retrieved_ids)
            if parsed is not None:
                return parsed
        except Exception:
            pass

    return _fallback_turn(retrieved_ids)
