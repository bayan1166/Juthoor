from __future__ import annotations

import json
import os
import random
from typing import Optional

from app.engine import config
from app.engine import offline_bank as ob
from app.engine import prompts

_client = None
_client_checked = False


def _get_client():
    global _client, _client_checked
    if _client_checked:
        return _client
    _client_checked = True

    if not config.LLM.get("enabled"):
        return None
    try:
        from app.config import settings
        oa_key = os.environ.get("OPENAI_API_KEY") or settings.openai_api_key
        gq_key = os.environ.get("GROQ_API_KEY") or settings.groq_api_key
    except Exception:
        oa_key = os.environ.get("OPENAI_API_KEY", "")
        gq_key = os.environ.get("GROQ_API_KEY", "")
    if oa_key:
        try:
            from openai import OpenAI
            _client = ("openai", OpenAI(api_key=oa_key))
        except Exception:
            _client = None
    elif gq_key:
        try:
            from groq import Groq
            _client = ("groq", Groq(api_key=gq_key))
        except Exception:
            _client = None
    return _client


def _parse(raw: str, skill_id: str, difficulty: int, pattern: str) -> Optional[dict]:
    try:
        data = json.loads(raw)
        correct = str(data["correct_answer"]).strip()
        distractors = []
        for d in data["distractors"]:
            text = str(d["text"]).strip()
            if ob.norm(text) == ob.norm(correct):
                continue
            distractors.append({"text": text, "misconception": str(d.get("misconception", "")).strip()})
        if not correct or not str(data.get("question", "")).strip() or len(distractors) < 2:
            return None
        return {
            "question": str(data["question"]).strip(),
            "correct_answer": correct,
            "distractors": distractors[:3],
            "explanation": str(data.get("explanation", "")).strip(),
            "hint": str(data.get("hint", "")).strip(),
            "type": "mcq",
            "traps": {ob.norm(d["text"]): d["misconception"] for d in distractors},
            "skill": skill_id,
            "difficulty": difficulty,
            "pattern": pattern,
            "template": "llm_dynamic",
            "source": "llm",
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def generate(skill_id: str, difficulty: int, rng: random.Random, avoid=None,
             pattern: Optional[str] = None, misconception: Optional[str] = None,
             language: str = "Arabic") -> dict:
    picked = _get_client()
    if picked is not None:
        provider, client = picked
        try:
            from app.config import settings
            model = settings.openai_chat_model if provider == "openai" else config.LLM["model"]
            messages = prompts.build_messages(
                skill_id, difficulty, language=language,
                recent=list(avoid or []), misconception=misconception,
            )
            resp = client.chat.completions.create(
                model=model, messages=messages, temperature=0.6, max_tokens=500,
                timeout=config.LLM["timeout_seconds"],
                response_format={"type": "json_object"},
            )
            parsed = _parse(resp.choices[0].message.content, skill_id, difficulty, pattern or "llm_dynamic")
            if parsed is not None:
                return parsed
        except Exception:
            pass

    return ob.generate_offline(skill_id, difficulty, rng, avoid, pattern)
