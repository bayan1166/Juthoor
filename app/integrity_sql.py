"""Database integrity checks as plain SQL (pure data; no driver import).

``scripts/check_integrity.py`` runs them through SQLAlchemy against the configured database;
``scripts/verify_integrity_sql.sh`` runs the very same statements through psql against a scratch
database seeded with deliberate corruption, to prove each check actually detects its defect.

Severity ERROR  = a persisted state the application can never legitimately produce.
Severity WARN   = unusual but possible (e.g. data seeded by a script); reported, does not fail.
Every query returns one number: how many offending rows were found.
"""
from __future__ import annotations

from app.engine import knowledge_graph as kg


def _skills_sql() -> str:
    return "(" + ", ".join("'" + s.replace("'", "''") + "'" for s in sorted(kg.SKILLS)) + ")"


def checks() -> list[tuple[str, str, str]]:
    sk = _skills_sql()
    return [
        ("ERROR", "duplicate skill_mastery rows for one (student, skill)",
         "SELECT count(*) FROM (SELECT 1 FROM skill_mastery GROUP BY student_id, skill_id HAVING count(*) > 1) d"),
        ("ERROR", "skill_mastery with impossible values",
         "SELECT count(*) FROM skill_mastery WHERE p_mastery IS NULL OR p_mastery <= 0 OR p_mastery >= 1 "
         "OR attempts < 0 OR correct < 0 OR correct > attempts"),
        ("ERROR", "skill_mastery for an unknown skill",
         f"SELECT count(*) FROM skill_mastery WHERE skill_id NOT IN {sk}"),
        ("ERROR", "orphan skill_mastery (no such user)",
         "SELECT count(*) FROM skill_mastery m LEFT JOIN users u ON u.id = m.student_id WHERE u.id IS NULL"),
        ("ERROR", "orphan attempt_logs (no such user)",
         "SELECT count(*) FROM attempt_logs a LEFT JOIN users u ON u.id = a.student_id WHERE u.id IS NULL"),
        ("ERROR", "orphan diagnosis_events (no such user)",
         "SELECT count(*) FROM diagnosis_events a LEFT JOIN users u ON u.id = a.student_id WHERE u.id IS NULL"),
        ("ERROR", "orphan student_adaptive_states (no such user)",
         "SELECT count(*) FROM student_adaptive_states a LEFT JOIN users u ON u.id = a.student_id WHERE u.id IS NULL"),
        ("ERROR", "invalid session state (difficulty or counters out of range, unknown current skill)",
         f"SELECT count(*) FROM student_adaptive_states WHERE difficulty NOT BETWEEN 1 AND 3 "
         f"OR consec_wrong < 0 OR total_answered < 0 OR round_answered < 0 OR current_skill NOT IN {sk}"),
        ("ERROR", "pending question refers to an unknown skill",
         f"SELECT count(*) FROM student_adaptive_states WHERE pending_question IS NOT NULL "
         f"AND (pending_question::jsonb ->> 'skill') NOT IN {sk}"),
        ("ERROR", "diagnosis with unknown origin/root or invalid confidence level",
         f"SELECT count(*) FROM diagnosis_events WHERE origin_skill NOT IN {sk} OR root_skill NOT IN {sk} "
         f"OR (confidence_level IS NOT NULL AND confidence_level NOT IN ('high', 'medium', 'low'))"),
        ("ERROR", "diagnosis without evidence or whose path does not end at its root",
         "SELECT count(*) FROM diagnosis_events WHERE evidence IS NULL OR json_array_length(evidence::json) = 0 "
         "OR path IS NULL OR json_array_length(path::json) = 0 "
         "OR (path::jsonb ->> (json_array_length(path::json) - 1)) <> root_skill"),
        ("ERROR", "learning data owned by a non-student (cross-user contamination)",
         "SELECT (SELECT count(*) FROM attempt_logs a JOIN users u ON u.id = a.student_id WHERE u.role::text <> 'student') "
         "+ (SELECT count(*) FROM skill_mastery a JOIN users u ON u.id = a.student_id WHERE u.role::text <> 'student') "
         "+ (SELECT count(*) FROM diagnosis_events a JOIN users u ON u.id = a.student_id WHERE u.role::text <> 'student')"),
        ("ERROR", "answer receipt for a missing user",
         "SELECT count(*) FROM answer_receipts a LEFT JOIN users u ON u.id = a.student_id WHERE u.id IS NULL"),
        ("WARN", "gap status without any diagnosis event for that skill",
         "SELECT count(*) FROM skill_mastery m WHERE m.status::text = 'gap' AND NOT EXISTS "
         "(SELECT 1 FROM diagnosis_events d WHERE d.student_id = m.student_id AND d.root_skill = m.skill_id)"),
        ("WARN", "skill_mastery.attempts differs from the number of attempt_logs for that skill",
         "SELECT count(*) FROM skill_mastery m WHERE m.attempts <> (SELECT count(*) FROM attempt_logs a "
         "WHERE a.student_id = m.student_id AND a.skill_id = m.skill_id)"),
    ]
