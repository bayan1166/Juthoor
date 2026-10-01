from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from app.engine import adaptive_engine as ae
from app.engine import knowledge_graph as kg
from app.engine import offline_bank as ob
from app.engine import practice as pr

RECENT_LIMIT = 12
CORRECT_COINS_NORMAL = "normal"


@dataclass
class Session:
    state: ae.StudentState
    plan: Optional[dict] = None
    pending_banner: Optional[str] = None
    recent: list = field(default_factory=list)
    pending: Optional[dict] = None


def _options(q: dict, rng: random.Random) -> list[str]:
    kind = q.get("type", "mcq")
    if kind == "mcq":
        opts = [q["correct_answer"]] + [d["text"] for d in q.get("distractors", [])]
        rng.shuffle(opts)
        return opts
    if kind == "tf":
        return ["صح", "خطأ"]
    return []


def serve(sess: Session, rng: random.Random) -> dict:
    if sess.plan:
        if sess.plan["stage"] == pr.SAME:
            q = pr.same_pattern_question(sess.plan, rng, sess.recent)
        else:
            q = pr.easier_question(sess.plan, sess.state, rng, sess.recent)
    else:
        st = sess.state
        q = ob.generate_offline(st.current_skill, st.difficulty, rng, avoid=sess.recent)
        if sess.pending_banner:
            q = {**q, "banner": sess.pending_banner}
            sess.pending_banner = None
    q = dict(q)
    q.setdefault("source", "offline")
    q.setdefault("banner", "")
    q.setdefault("guided", False)
    q["remedial"] = q.get("remedial")
    q["type"] = q.get("type", "mcq")
    q["options"] = _options(q, rng)
    q["skill_name"] = kg.SKILLS[q["skill"]].name_ar
    sess.recent = (sess.recent + [q["question"]])[-RECENT_LIMIT:]
    sess.pending = {
        "question": q["question"], "skill": q["skill"], "difficulty": q["difficulty"],
        "pattern": q.get("pattern", ""), "type": q["type"], "correct_answer": q["correct_answer"],
        "traps": q.get("traps", {}), "explanation": q.get("explanation", ""),
        "source": q["source"], "remedial": q["remedial"],
    }
    return q


def grade(sess: Session, selected: str) -> dict:
    pending = sess.pending
    ok = pr.is_correct(pending, selected)
    kind = pending.get("remedial")
    events: list[dict] = []
    decision = None

    if kind is None:
        decision = ae.decide_next(sess.state, ok)
        sess.plan = None if ok else pr.start(pending, selected)
        sess.pending_banner = decision.breadcrumb or None
        if decision.action in ("backtrack", "return_up"):
            events.append({"from_skill": pending["skill"], "to_skill": decision.next_skill,
                           "direction": "descend" if decision.action == "backtrack" else "ascend",
                           "triggered_by": "engine", "depth": 1, "to_pattern": ""})
    else:
        old = sess.plan
        sess.plan = pr.advance(old, ok) if old else None
        if old and sess.plan and len(sess.plan["stack"]) > len(old["stack"]):
            events.append({"from_skill": old["skill"], "to_skill": sess.plan["skill"],
                           "direction": "descend", "triggered_by": "practice",
                           "depth": len(sess.plan["stack"]), "to_pattern": sess.plan["pattern"]})

    card = None if ok else pr.mistake_card(pending, selected)
    sess.pending = None
    round_over = (decision.round_over if decision else False) or ae.round_over(sess.state)
    return {
        "is_correct": ok,
        "remedial": kind,
        "action": decision.action if decision else ("remedial_correct" if ok else "remedial_wrong"),
        "next_skill": decision.next_skill if decision else (sess.plan["skill"] if sess.plan else sess.state.current_skill),
        "next_difficulty": decision.next_difficulty if decision else (sess.plan["difficulty"] if sess.plan else sess.state.difficulty),
        "reason": decision.reason if decision else "",
        "breadcrumb": (decision.breadcrumb if decision else "") or "",
        "gap_skill": decision.gap_skill if decision else None,
        "round_over": bool(round_over and sess.plan is None),
        "next_stage": sess.plan["stage"] if sess.plan else None,
        "correct_answer": pending["correct_answer"],
        "misconception": (card or {}).get("why") or "",
        "explanation": pending.get("explanation", ""),
        "mistake_card": card,
        "events": events,
        "engine_action": decision.action if decision else None,
    }


def new_round(sess: Session) -> None:
    ae.start_round(sess.state)
    sess.plan = None
    sess.pending = None
    sess.pending_banner = None
