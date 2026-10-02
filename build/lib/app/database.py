from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def normalize_url(url: str) -> str:
    """Accept the common postgres:// spelling; SQLAlchemy 2 only knows postgresql://."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def _make_engine(url: str):
    url = normalize_url(url)

    if url.startswith("sqlite"):
        import logging
        logging.getLogger("juthoor.database").warning(
            "SQLite is NOT supported for real use: no row locking, no migrations. PostgreSQL is the official database.")
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Columns added after the first release. create_all() creates missing tables but never adds
# columns to an existing table, so an older database would fail at query time. Each entry is
# additive and nullable, which keeps the upgrade safe to run on every start.
ADDED_COLUMNS = {
    "diagnosis_events": {"confidence_level": "VARCHAR(10)", "explanation": "TEXT"},
}


def ensure_schema(bind=None) -> list[str]:
    """Create missing tables and add known missing columns. Returns the columns it added."""
    bind = bind or engine
    Base.metadata.create_all(bind=bind)
    added = []
    inspector = inspect(bind)
    with bind.begin() as conn:
        for table, columns in ADDED_COLUMNS.items():
            if not inspector.has_table(table):
                continue
            present = {c["name"] for c in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in present:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                    added.append(f"{table}.{name}")
    # Converge older databases (constraints, new tables/columns). PostgreSQL only; see app/migrations.py.
    from app.migrations import apply_pending
    added.extend(f"migration {v}" for v in apply_pending(bind))
    return added
