"""Test setup: in-memory SQLite, no Postgres/Chroma/Groq needed.

Run from the repo root:  pip install -r requirements-dev.txt && pytest -q
"""
import os
import sys
import types

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["GROQ_API_KEY"] = ""  # force the tutor's offline fallback path

# chromadb is heavy; if it isn't installed, stub it so importing the app works.
# (The chat code already treats a failing vector store as "no context".)
try:
    import chromadb  # noqa: F401
except Exception:
    stub = types.ModuleType("chromadb")
    stub.utils = types.ModuleType("chromadb.utils")
    stub.utils.embedding_functions = types.ModuleType("chromadb.utils.embedding_functions")
    sys.modules["chromadb"] = stub
    sys.modules["chromadb.utils"] = stub.utils
    sys.modules["chromadb.utils.embedding_functions"] = stub.utils.embedding_functions

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers all tables)
from app.database import Base, get_db
from app.main import app
from tests.helpers import register

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.create_all(bind=engine)
    yield
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
