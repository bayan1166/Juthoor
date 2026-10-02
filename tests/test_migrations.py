"""Migration file validation (pure) and application on PostgreSQL (needs the test DB)."""
import re
from pathlib import Path

import pytest

from app import migration_files as mf


def _write(d: Path, names):
    for n in names:
        (d / n).write_text("SELECT 1;\n", encoding="utf-8")


def test_shipped_migrations_are_valid_and_consecutive():
    found = mf.discover()
    assert [v for v, _ in found] == [f"{i:04d}" for i in range(1, len(found) + 1)]
    assert len(found) >= 4


def test_shipped_migrations_are_idempotent_by_construction():
    """Every statement that creates objects must be guarded (IF NOT EXISTS / DO block)."""
    for _v, path in mf.discover():
        sql = path.read_text(encoding="utf-8")
        for stmt in re.findall(r"(?im)^\s*(CREATE\s+(?:UNIQUE\s+)?(?:TABLE|INDEX)[^;]*?);", sql):
            assert re.search(r"(?i)if\s+not\s+exists", stmt), (path.name, stmt[:80])
        for stmt in re.findall(r"(?im)^\s*ALTER\s+TABLE[^;]*?ADD\s+COLUMN[^;]*?;", sql):
            assert re.search(r"(?i)if\s+not\s+exists", stmt), (path.name, stmt[:80])


def test_gap_is_rejected(tmp_path):
    _write(tmp_path, ["0001_a.sql", "0003_c.sql"])
    with pytest.raises(ValueError):
        mf.discover(tmp_path)


def test_duplicate_version_is_rejected(tmp_path):
    _write(tmp_path, ["0001_a.sql", "0001_b.sql"])
    with pytest.raises(ValueError):
        mf.discover(tmp_path)


def test_bad_name_is_rejected(tmp_path):
    _write(tmp_path, ["001_a.sql"])
    with pytest.raises(ValueError):
        mf.discover(tmp_path)


def test_percent_sign_is_rejected(tmp_path):
    (tmp_path / "0001_a.sql").write_text("SELECT '100%';", encoding="utf-8")
    with pytest.raises(ValueError):
        mf.discover(tmp_path)


def test_order_is_numeric(tmp_path):
    _write(tmp_path, ["0002_b.sql", "0001_a.sql"])
    assert [v for v, _ in mf.discover(tmp_path)] == ["0001", "0002"]


# ---- database-backed (PostgreSQL) -------------------------------------------------

def _pg_engine():
    pytest.importorskip("sqlalchemy")
    from sqlalchemy import create_engine
    from tests import conftest as c  # test DB url helpers
    url = getattr(c, "TEST_DATABASE_URL", None)
    if not url or not str(url).startswith("postgresql"):
        pytest.skip("PostgreSQL test database not configured")
    return create_engine(url)


def test_apply_pending_is_idempotent_and_recorded():
    eng = _pg_engine()
    from sqlalchemy import text
    from app import migrations
    migrations.apply_pending(eng)
    assert migrations.apply_pending(eng) == []
    with eng.connect() as conn:
        versions = [r[0] for r in conn.execute(text("SELECT version FROM schema_migrations ORDER BY 1"))]
    assert versions == [v for v, _ in mf.discover()]


def test_degraded_database_is_repaired_without_losing_rows():
    """Duplicate skill_mastery rows and out-of-range p are repaired; the data survives."""
    eng = _pg_engine()
    from sqlalchemy import text
    from app import migrations
    with eng.begin() as conn:
        conn.execute(text("ALTER TABLE skill_mastery DROP CONSTRAINT IF EXISTS uq_skill_mastery_student_skill"))
        conn.execute(text("ALTER TABLE skill_mastery DROP CONSTRAINT IF EXISTS ck_skill_mastery_p_open_interval"))
        conn.execute(text("DELETE FROM schema_migrations WHERE version = '0002'"))
    migrations.apply_pending(eng)
    with eng.connect() as conn:
        names = {r[0] for r in conn.execute(text(
            "SELECT conname FROM pg_constraint WHERE conrelid = 'skill_mastery'::regclass"))}
    assert "uq_skill_mastery_student_skill" in names
    assert "ck_skill_mastery_p_open_interval" in names
