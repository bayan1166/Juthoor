import os
import sys
import types

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["GROQ_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["DEMO_MODE"] = ""
os.environ["STRIPE_SECRET_KEY"] = ""
os.environ["RATE_LIMIT_ENABLED"] = "0"
os.environ["JUDGE_MODE"] = "0"


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
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
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
