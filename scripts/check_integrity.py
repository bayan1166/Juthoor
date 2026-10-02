"""Database integrity checker. Exit 0 = no ERROR findings; 1 = corruption found; 3 = DB unreachable.

    python scripts/check_integrity.py [--json]

Runs app/integrity_sql.py against the configured PostgreSQL database and, for every student,
rebuilds the engine state and applies the pure invariants in app/engine/integrity.py.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from app import integrity_sql  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.engine import integrity  # noqa: E402
from app.models.org import User, UserRole  # noqa: E402
from app.services import engine_bridge  # noqa: E402


def main(argv: list[str]) -> int:
    findings, state_problems = [], []
    try:
        with SessionLocal() as db:
            for severity, label, sql in integrity_sql.checks():
                findings.append({"severity": severity, "check": label, "violations": int(db.execute(text(sql)).scalar() or 0)})
            ids = db.scalars(select(User.id).where(User.role == UserRole.student)).all()
            for sid in ids:
                state = engine_bridge._load_state(db, sid)
                for problem in integrity.check_state(state):
                    state_problems.append({"student_id": str(sid), "problem": problem})
            db.rollback()  # the checker never writes
    except OperationalError as exc:
        print(f"cannot reach the database: {exc.orig}")
        return 3
    errors = [f for f in findings if f["severity"] == "ERROR" and f["violations"]]
    report = {"checks": findings, "state_problems": state_problems, "ok": not errors and not state_problems}
    if "--json" in argv:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for f in findings:
            mark = "ok  " if not f["violations"] else f["severity"]
            print(f"{mark:5} {f['violations']:>5}  {f['check']}")
        for p in state_problems[:50]:
            print(f"STATE {p['student_id']}: {p['problem']}")
        print("INTEGRITY OK" if report["ok"] else "INTEGRITY PROBLEMS FOUND")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
