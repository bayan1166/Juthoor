"""Where a learner is in the core loop, for the UI stepper and the API.

practising -> gathering_evidence -> root_identified -> remediation -> retry -> resolved

Pure function of the live learner state plus the latest persisted diagnosis, so it is the same
whether computed after an answer, on page load, or in a test without a database.
"""
from __future__ import annotations

from typing import Optional

from app.engine import adaptive_engine as ae
from app.engine import knowledge_graph as kg

STEPS = ("practising", "gathering_evidence", "root_identified", "remediation", "retry", "resolved")


def _name(skill: Optional[str]) -> Optional[str]:
    if skill is None:
        return None
    return kg.SKILLS[skill].name_ar if skill in kg.SKILLS else skill


def workflow(state: ae.StudentState, latest: Optional[dict] = None, result: Optional[dict] = None,
             answered_skill: Optional[str] = None) -> dict:
    out = {"stage": "practising", "current_skill": state.current_skill, "current_name_ar": _name(state.current_skill),
           "origin": None, "origin_name_ar": None, "root": None, "root_name_ar": None, "confidence": None,
           "message": None}
    if latest and latest.get("root") in kg.SKILLS and latest.get("origin") in kg.SKILLS:
        root, origin = latest["root"], latest["origin"]
        out.update(origin=origin, origin_name_ar=_name(origin), root=root, root_name_ar=_name(root),
                   confidence=latest.get("confidence"))
        if root in state.gaps or not state.is_mastered(root):
            out["stage"] = "remediation"
        elif origin != root and not state.is_mastered(origin):
            out["stage"] = "retry"
        else:
            out["stage"] = "resolved"
    if result is not None:
        if result.get("diagnosis"):
            d = result["diagnosis"]
            out.update(stage="root_identified", origin=d["origin"], origin_name_ar=_name(d["origin"]), root=d["root"],
                       root_name_ar=_name(d["root"]), confidence=d.get("confidence"))
        elif not result.get("is_correct") and result.get("evidence_status"):
            # A miss on the root already being remediated is part of remediation; any other miss
            # without a named root means evidence is still being gathered.
            if not (out["stage"] == "remediation" and answered_skill == out["root"]):
                out["stage"] = "gathering_evidence"
                out["message"] = result["evidence_status"].get("message")
    out["step"] = STEPS.index(out["stage"])
    return out
