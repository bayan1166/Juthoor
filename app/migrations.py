"""Versioned, transactional SQL migrations for PostgreSQL.

* Files live in ``migrations/versions`` and are named ``NNNN_description.sql``; they run in order.
* Applied versions are recorded in ``schema_migrations``; a version never runs twice.
* A transaction-level advisory lock serialises concurrent starters (two app instances booting).
* Every file is idempotent (IF NOT EXISTS / guarded DO blocks), so a database created by
  ``create_all`` from the current models and an older database both converge to the same schema.
* Files must not contain a percent sign (the driver treats it as a parameter marker).

SQLite (explicit non-production mode) relies on ``create_all`` only and skips migrations.
"""
from __future__ import annotations

from sqlalchemy import text

from app.migration_files import LOCK_KEY, MIGRATIONS_DIR, discover  # noqa: F401


def apply_pending(bind) -> list[str]:
    """Apply every unapplied migration; returns the versions applied by this call."""
    if bind.dialect.name != "postgresql":
        return []
    applied_now: list[str] = []
    with bind.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": LOCK_KEY})
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version VARCHAR(8) PRIMARY KEY, filename TEXT NOT NULL, "
            "applied_at TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc'))"))
        done = {row[0] for row in conn.execute(text("SELECT version FROM schema_migrations"))}
        for version, path in discover():
            if version in done:
                continue
            conn.exec_driver_sql(path.read_text(encoding="utf-8"))
            conn.execute(text("INSERT INTO schema_migrations (version, filename) VALUES (:v, :f)"),
                         {"v": version, "f": path.name})
            applied_now.append(version)
        # Receipts only need to cover the retry window.
        conn.execute(text("DELETE FROM answer_receipts WHERE created_at < (now() AT TIME ZONE 'utc') - interval '7 days'"))
    return applied_now
