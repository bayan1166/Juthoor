"""SIMULATED backend for browser checks where FastAPI/PostgreSQL are not available.

What is real here: the static single-page app (served from app/static), the diagnosis engine, the
practice session, the workflow stage, the curriculum tree (app/engine, app/services/session_core.py,
workflow.py, tree_service.py) — exactly the code the real API calls.
What is simulated: HTTP routing, authentication (token = email), persistence (in memory) and the
teacher's class report. It is NOT the product backend; use it only to exercise the UI in a real
browser. The real end-to-end check is `python tests/e2e/browser_e2e.py` against `run_demo.py`.

    python tests/e2e/sim_server.py --port 8765
"""
import argparse
import json
import random
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.engine import adaptive_engine as ae  # noqa: E402
from app.engine import knowledge_graph as kg  # noqa: E402
from app.services import session_core as sc  # noqa: E402
from app.services import tree_service  # noqa: E402
from app.services import workflow as wf  # noqa: E402

STATIC = ROOT / "app" / "static"
OMAR, TEACHER = "00000000-0000-4000-8000-000000000002", "00000000-0000-4000-8000-0000000000aa"
USERS = {
    "student2@demo.jo": {"user_id": OMAR, "full_name": "عمر", "role": "student", "handle": "1002"},
    "teacher@demo.jo": {"user_id": TEACHER, "full_name": "المعلمة سارة", "role": "teacher", "handle": "7001"},
}
TYPES = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png"}

rng = random.Random(5)
state = ae.StudentState(current_skill="mult_div_integers", difficulty=1)
state.mastered.update({"absolute_value", "comparing_integers"})
for skill in ("absolute_value", "comparing_integers"):
    state.attempts[skill], state.correct[skill], state.p_mastery[skill] = 3, 3, 0.99
session = sc.Session(state=state)
diagnoses: list[dict] = []
attempts: list[dict] = []
unknown_paths: list[str] = []


def now_z():
    return datetime.utcnow().isoformat() + "Z"


def name(skill):
    return kg.SKILLS[skill].name_ar if skill in kg.SKILLS else skill


def latest():
    return diagnoses[-1] if diagnoses else None


def overview():
    skills = [{"skill_id": s, "name_ar": name(s), "status": ae.skill_status(state, s),
               "p_mastery": round(state.mastery(s), 3), "attempts": state.attempts.get(s, 0),
               "correct": state.correct.get(s, 0)} for s in kg.SKILLS]
    last = latest()
    return {"student_id": OMAR, "current_skill": state.current_skill, "difficulty": state.difficulty,
            "total_answered": state.total_answered, "tree_health": round(ae.tree_health(state), 3),
            "round_answered": state.round_answered, "round_over": ae.round_over(state),
            "in_remediation": bool(session.plan), "skills": skills,
            "workflow": wf.workflow(state, last and {"origin": last["origin_skill"], "root": last["root_skill"],
                                                     "confidence": last["confidence"]})}


def plan():
    return {"plan": "pro", "source": "class", "expires_at": None, "trial_days_left": None,
            "limits": {"questions_per_day": None, "tutor_per_day": None, "max_friends": None, "history_days": None,
                       "full_gap_report": True, "classrooms": False},
            "usage": {"questions": 0, "tutor": 0}, "remaining": {"questions": None, "tutor": None}}


def history():
    out = []
    for d in reversed(diagnoses):
        after = [a for a in attempts if a["at"] > d["at"]]
        on_root = [a for a in after if a["skill"] == d["root_skill"]]
        on_origin = [a for a in after if a["skill"] == d["origin_skill"]] if d["origin_skill"] != d["root_skill"] else []
        status = ae.skill_status(state, d["root_skill"])
        stage = "resolved" if status == "mastered" else ("remediating" if on_root else "pending")
        tally = lambda rows: {"right": sum(r["ok"] for r in rows), "wrong": sum(not r["ok"] for r in rows)}  # noqa: E731
        out.append({**{k: v for k, v in d.items() if k != "at"},
                    "outcome": {"stage": stage, "root_status": status, "root_after": tally(on_root),
                                "origin_retry": tally(on_origin)}})
    return out


def class_report():
    ov = overview()
    gaps = [s for s in ov["skills"] if s["status"] == "gap"]
    row = {"user_id": OMAR, "handle": "1002", "full_name": "عمر", "avatar_svg": None, "tree_health": ov["tree_health"],
           "mastered": sum(s["status"] == "mastered" for s in ov["skills"]), "current_skill": name(state.current_skill),
           "accuracy": None, "answered": len(attempts), "last_active": now_z(), "days_since_active": 0,
           "root_gaps": [s["name_ar"] for s in gaps], "root_gap_ids": [s["skill_id"] for s in gaps],
           "risk": "high" if gaps else "low", "submissions_done": 0, "assignments_total": 0, "quiz_points": 0}
    room = {"classroom_id": "C1", "name": "السادس أ", "join_code": "JUTH26", "teacher_name": "سارة", "member_count": 1,
            "assignment_count": 0, "quiz_count": 0, "created_at": now_z()}
    return {"classroom": room, "kpis": {"students": 1, "avg_tree_health": ov["tree_health"], "avg_accuracy": None,
                                        "active_last_7": 1, "at_risk": int(bool(gaps))},
            "students": [row], "top_gaps": [{"skill_id": s["skill_id"], "name_ar": s["name_ar"], "students": 1} for s in gaps],
            "skill_mastery": [{"skill_id": s, "name_ar": name(s), "avg": round(state.mastery(s), 3)} for s in kg.ordered_skills()],
            "activity": [{"date": datetime.utcnow().date().isoformat(), "answers": len(attempts)}]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if "json" in ctype or "text" in ctype else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _user(self):
        token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        return USERS.get(token)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ("/", "/app"):
            self.send_response(302)
            self.send_header("Location", "/app/")
            self.end_headers()
            return
        if path.startswith("/app/"):
            rel = path[len("/app/"):] or "index.html"
            f = (STATIC / rel).resolve()
            if STATIC in f.parents and f.is_file():
                return self._send(200, f.read_bytes(), TYPES.get(f.suffix, "application/octet-stream"))
            return self._send(404, {"detail": "not_found"})
        if path == "/health":
            return self._send(200, {"status": "ok", "database": "simulated", "ai_tutor": "offline_fallback", "demo": True, "judge": True})
        if path == "/curriculum/map":
            return self._send(200, tree_service.public_map())
        if path == "/__mock__/pending":
            return self._send(200, session.pending or {})
        if path == "/curriculum/skills":
            return self._send(200, [{"skill_id": s, "name": kg.SKILLS[s].name, "name_ar": name(s), "description": "",
                                     "prerequisites": list(kg.SKILLS[s].prerequisites), "dependents": kg.dependents(s),
                                     "depth": kg.depth(s), "x": kg.SKILLS[s].x, "ladder": list(kg.SKILLS[s].ladder),
                                     "typical_errors": [], "intervention": kg.SKILLS[s].intervention} for s in kg.ordered_skills()])
        user = self._user()
        if user is None:
            return self._send(401, {"detail": "invalid_token"})
        if path == "/auth/me":
            return self._send(200, {**user, "email": next(k for k, v in USERS.items() if v is user), "organization_id": None,
                                    "organization_name": "Demo School", "grade_level": 6,
                                    "plan": "school" if user["role"] == "teacher" else "pro",
                                    "plan_source": "own" if user["role"] == "teacher" else "class",
                                    "plan_expires_at": None, "trial_days_left": None})
        if path == "/community/summary":
            return self._send(200, {"unread": 0, "requests": 0, "reports_open": 0})
        base = f"/students/{OMAR}/adaptive"
        if path == f"{base}/bootstrap":
            return self._send(200, {"state": overview(), "wallet": {"coins": 50, "gems": 0}, "avatar": {}, "avatar_svg": "",
                                    "drilldowns": [], "drilldowns_hidden": 0, "plan": plan()})
        if path == f"{base}/state":
            return self._send(200, overview())
        if path == f"{base}/tree":
            return self._send(200, tree_service.build_tree(state, True))
        if path == f"{base}/question":
            q = sc.serve(session, rng)
            return self._send(200, {k: q.get(k) for k in ("question", "hint", "skill", "difficulty", "pattern", "source", "remedial",
                                                          "banner", "guided", "type", "options", "skill_name")})
        if path in (f"{base}/report", f"{base}/diagnoses"):
            if path.endswith("diagnoses"):
                return self._send(200, {"locked": False, "diagnoses": history()})
            return self._send(200, {"student": {"user_id": OMAR, "full_name": "عمر", "handle": "1002"}, "state": overview(),
                                    "drilldowns": [], "drilldowns_hidden": 0, "gap_locked": False, "forecast": None,
                                    "diagnoses": history(), "plan": plan()})
        if path == "/classrooms":
            return self._send(200, [class_report()["classroom"]])
        if path == "/classrooms/C1/analytics":
            return self._send(200, class_report())
        unknown_paths.append(path)
        return self._send(404, {"detail": "not_found"})

    def do_POST(self):
        path = urlsplit(self.path).path
        if path == "/auth/login":
            body = self._body()
            user = USERS.get(str(body.get("email", "")).lower())
            if user is None or body.get("password") != "demo1234":
                return self._send(401, {"detail": "invalid_credentials"})
            return self._send(200, {"access_token": body["email"].lower(), "token_type": "bearer", "user_id": user["user_id"],
                                    "role": user["role"]})
        if self._user() is None:
            return self._send(401, {"detail": "invalid_token"})
        base = f"/students/{OMAR}/adaptive"
        if path == f"{base}/answer":
            body = self._body()
            selected = str(body.get("selected_answer", ""))
            if not selected.strip() or len(selected) > 200:
                return self._send(422, {"detail": [{"loc": ["body", "selected_answer"], "msg": "invalid"}]})
            if not session.pending:
                return self._send(409, {"detail": "no_active_question"})
            pending = dict(session.pending)
            before = set(state.gaps)
            r = sc.grade(session, selected)
            r.pop("events", None)
            r.pop("engine_action", None)
            at = datetime.utcnow()
            attempts.append({"skill": pending["skill"], "ok": r["is_correct"], "at": at})
            if r["diagnosis"]:
                d = r["diagnosis"]
                diagnoses.append({"diagnosis_id": f"D{len(diagnoses) + 1}", "created_at": at.isoformat() + "Z", "at": at,
                                  "origin_skill": d["origin"], "origin_name_ar": name(d["origin"]),
                                  "root_skill": d["root"], "root_name_ar": name(d["root"]),
                                  "path": [{"skill": s, "name_ar": name(s)} for s in d["path"]],
                                  "confidence": d["confidence"], "confidence_level": d["confidence_level"],
                                  "explanation": d["explanation"],
                                  "evidence": [{**e, "name_ar": name(e["skill"])} for e in d["evidence"]],
                                  "intervention": d["intervention"]})
            last = latest()
            r.update(coins_awarded=0, gems_awarded=0, new_gaps=sorted(set(state.gaps) - before), gap_locked=False,
                     remaining_questions=None,
                     workflow=wf.workflow(state, last and {"origin": last["origin_skill"], "root": last["root_skill"],
                                                           "confidence": last["confidence"]}, r, pending["skill"]))
            return self._send(200, r)
        if path == f"{base}/round":
            sc.new_round(session)
            return self._send(200, overview())
        unknown_paths.append(path)
        return self._send(404, {"detail": "not_found"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"SIMULATED backend on http://127.0.0.1:{args.port}/app/ (engine real, persistence in memory)", flush=True)
    try:
        server.serve_forever()
    finally:
        if unknown_paths:
            print("unhandled paths:", sorted(set(unknown_paths)))


if __name__ == "__main__":
    main()
