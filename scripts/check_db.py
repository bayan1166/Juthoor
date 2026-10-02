"""Verify the configured database is reachable before anything else runs.

For PostgreSQL it also creates the target database when the server is up but the
database does not exist yet (e.g. a fresh install with only the default `postgres` DB).
Exit codes: 0 ok, 3 database unreachable.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.database import normalize_url


def describe(url) -> str:
    return url.render_as_string(hide_password=True)


def main() -> int:
    url = make_url(normalize_url(settings.database_url))
    if url.get_backend_name() != "postgresql":
        print(f"database: {describe(url)} (WARNING: not PostgreSQL; the judged setup uses PostgreSQL)")
        return 0
    try:
        with create_engine(url).connect() as conn:
            version = conn.execute(text("SHOW server_version")).scalar()
        print(f"database: {describe(url)} reachable (PostgreSQL {version})")
        return 0
    except OperationalError as exc:
        message = str(exc.orig) if exc.orig else str(exc)
        if "does not exist" not in message or not url.database:
            print(f"ERROR: cannot reach PostgreSQL at {describe(url)}\n  {message.strip()}\n"
                  "  Start PostgreSQL, or set DATABASE_URL in .env (see .env.example).")
            return 3
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            name = url.database.replace('"', '""')
            conn.execute(text(f'CREATE DATABASE "{name}"'))
        print(f"database: created {url.database} on {url.host}:{url.port or 5432}")
        return 0
    except OperationalError as exc:
        print(f"ERROR: database {url.database} does not exist and could not be created: {exc.orig}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
