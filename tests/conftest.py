"""Test configuration.

The suite is self-contained: it never reads the developer's `.env` for application settings
(JUTHOOR_ENV_FILE is set to empty) and pins every behaviour-changing setting to a valid value.

Database: PostgreSQL by default.
  TEST_DATABASE_URL (environment or `.env`) if set, otherwise the server/credentials of
  DATABASE_URL (or the project default postgresql://postgres:1234@localhost:5432/Juthoor) with the
  database name `juthoor_test`. The test database is created if missing and wiped between tests,
  so it must never be the application database (guarded below).
  If PostgreSQL is unreachable the run stops with a clear message; there is no silent fallback.
  SQLite is used only when explicitly requested with TEST_DATABASE_URL=sqlite://
"""
import os
import sys
import types
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APP_URL = "postgresql://postgres:1234@localhost:5432/Juthoor"


def _dotenv(key: str) -> str:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _normalise(url: str) -> str:
    return "postgresql://" + url[len("postgres://"):] if url.startswith("postgres://") else url


def _with_database(url: str, name: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "/" + name, parts.query, parts.fragment))


def _same_database(a: str, b: str) -> bool:
    pa, pb = urlsplit(a.replace("+psycopg2", "")), urlsplit(b.replace("+psycopg2", ""))
    if pa.scheme.startswith("sqlite") or pb.scheme.startswith("sqlite"):
        return a.rstrip("/") == b.rstrip("/")
    return (pa.hostname, pa.port or 5432, pa.path) == (pb.hostname, pb.port or 5432, pb.path)


APP_DATABASE_URL = _normalise(os.environ.get("DATABASE_URL") or _dotenv("DATABASE_URL") or DEFAULT_APP_URL)
TEST_DATABASE_URL = _normalise(os.environ.get("TEST_DATABASE_URL") or _dotenv("TEST_DATABASE_URL")
                               or _with_database(APP_DATABASE_URL, "juthoor_test"))
if _same_database(TEST_DATABASE_URL, APP_DATABASE_URL):
    raise SystemExit("TEST_DATABASE_URL must point to a different database than DATABASE_URL: tests wipe it.")

# Deterministic, valid settings for every test run (booleans as 0/1, never blank).
os.environ.update({
    "JUTHOOR_ENV_FILE": "",
    "DATABASE_URL": TEST_DATABASE_URL,
    "DEMO_MODE": "0",
    "JWT_SECRET": "test-secret-for-pytest-only-0123456789abcdefghijklmnopqrstuv",
    "JUDGE_MODE": "0",
    "RATE_LIMIT_ENABLED": "0",
    "LLM_QUESTIONS_ENABLED": "0",
    "ENABLE_VECTOR_STORE": "0",
    "TRUST_PROXY": "0",
    "GROQ_API_KEY": "",
    "OPENAI_API_KEY": "",
    "STRIPE_SECRET_KEY": "",
    "SMTP_HOST": "",
})


try:
    import chromadb
except Exception:
    stub = types.ModuleType("chromadb")
    stub.utils = types.ModuleType("chromadb.utils")
    stub.utils.embedding_functions = types.ModuleType("chromadb.utils.embedding_functions")
    sys.modules["chromadb"] = stub
    sys.modules["chromadb.utils"] = stub.utils
    sys.modules["chromadb.utils.embedding_functions"] = stub.utils.embedding_functions

import pytest

sys.path.insert(0, str(ROOT))
from scripts.check_env import DEV, RUNTIME, missing  # noqa: E402

_MISSING = missing(RUNTIME + DEV)
if _MISSING:
    sys.stderr.write("\nJuthoor tests cannot start. Missing Python packages: " + ", ".join(p for p, _ in _MISSING)
                     + f"\nInstall them with: {sys.executable} -m pip install -r requirements-dev.txt\n\n")
    raise SystemExit(4)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import close_all_sessions, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.main import app
from tests.helpers import register

IS_POSTGRES = TEST_DATABASE_URL.startswith("postgresql")


def _make_test_engine():
    if not IS_POSTGRES:
        return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    url = make_url(TEST_DATABASE_URL)
    eng = create_engine(url, pool_pre_ping=True)
    try:
        with eng.connect():
            pass
    except OperationalError as exc:
        if "does not exist" not in str(exc):
            sys.stderr.write(f"\nJuthoor tests cannot start: PostgreSQL is unreachable at "
                             f"{url.render_as_string(hide_password=True)}\n  {exc.orig}\n"
                             "Start PostgreSQL (or set TEST_DATABASE_URL to a reachable test database).\n\n")
            raise SystemExit(3)
        admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
        admin.dispose()
    return eng


engine = _make_test_engine()
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


def pytest_report_header(config):
    target = make_url(TEST_DATABASE_URL).render_as_string(hide_password=True)
    return f"juthoor test database: {target} ({'PostgreSQL' if IS_POSTGRES else 'SQLite quick mode'})"


if IS_POSTGRES:
    # One schema per run; rows are truncated between tests (fast and isolates every test).
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    Base.metadata.create_all(bind=engine)
    _TABLES = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)


@pytest.fixture(autouse=True)
def fresh_db():
    if IS_POSTGRES:
        yield
        close_all_sessions()
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))
        return
    Base.metadata.create_all(bind=engine)
    yield
    close_all_sessions()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def session_factory():
    return TestingSession


@pytest.fixture
def db():
    s = TestingSession()
    yield s
    s.close()


@pytest.fixture
def student(client):
    return register(client)
