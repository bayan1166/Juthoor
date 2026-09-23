"""
Dynamic, LLM-generated stepping-stone questions for Juthoor's remediation flow.

Design goal: this must NEVER be a single point of failure in front of judges.
generate() always returns a usable question dict. If the LLM is disabled,
unconfigured, unreachable, slow, or returns something malformed, it falls
back to the exact same static offline_bank.generate_offline() call the app
used before this module existed -- silently, with no exception escaping.

    from llm_remediation import generate
    q = generate(skill_id, difficulty, rng, avoid, pattern=pattern, misconception="...")

Nothing above this module needs to know whether a given question came from
Groq or from offline_bank; both return the same dict shape (see
offline_bank._finish for the canonical shape).
"""
from __future__ import annotations

import json
import os
import random
from typing import Optional

import config
import offline_bank as ob
import prompts

_client = None
_client_checked = False


def _get_client():
    """Lazily build a Groq client. Returns None if unavailable or unconfigured."""
    global _client, _client_checked
    if _client_checked:
        return _client
    _client_checked = True

    if not config.LLM.get("enabled") or not os.environ.get("GROQ_API_KEY"):
        return None
    try:
        from groq import Groq  # optional dependency -- see requirements-optional.txt
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    except Exception:
        _client = None
    return _client


def _parse(raw: str, skill_id: str, difficulty: int, pattern: str) -> Optional[dict]:
    """Validate + reshape the LLM's JSON into the app's normal question shape.
    Returns None on ANY problem -- the caller then falls back to the offline bank."""
    try:
        data = json.loads(raw)
        correct = str(data["correct_answer"]).strip()
        distractors = []
        for d in data["distractors"]:
            text = str(d["text"]).strip()
            if ob.norm(text) == ob.norm(correct):
                continue  # a distractor that matches the "correct" value is not usable
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
    """
    One question for (skill, difficulty). Tries a live, targeted Groq generation
    first; always falls back to the offline bank on any failure so this call
    can never break the demo or leave the student without a question.
    """
    client = _get_client()
    if client is not None:
        try:
            messages = prompts.build_messages(
                skill_id, difficulty, language=language,
                recent=list(avoid or []), misconception=misconception,
            )
            resp = client.chat.completions.create(
                model=config.LLM["model"],
                messages=messages,
                temperature=0.6,
                max_tokens=500,
                timeout=config.LLM["timeout_seconds"],
            )
            parsed = _parse(resp.choices[0].message.content, skill_id, difficulty, pattern or "llm_dynamic")
            if parsed is not None:
                return parsed
        except Exception:
            pass  # network error, timeout, rate limit, bad JSON -- fall through, never raise

    return ob.generate_offline(skill_id, difficulty, rng, avoid, pattern)
