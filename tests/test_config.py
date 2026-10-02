"""Configuration must be reproducible: blank values fall back to defaults, booleans parse the
usual spellings, invalid values fail loudly, and the test run never reads a developer's .env."""
import os

import pytest
from pydantic import ValidationError

from app.config import DEFAULT_DATABASE_URL, Settings, env_file


def build(monkeypatch, **env):
    for key in ("DEMO_MODE", "JUDGE_MODE", "RATE_LIMIT_ENABLED", "DATABASE_URL", "SMTP_PORT"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings(_env_file=None)


def test_blank_boolean_and_numeric_values_use_defaults(monkeypatch):
    s = build(monkeypatch, DEMO_MODE="", JUDGE_MODE=" ", RATE_LIMIT_ENABLED="", SMTP_PORT="")
    assert s.demo_mode is False and s.judge_mode is False and s.rate_limit_enabled is True and s.smtp_port == 587


@pytest.mark.parametrize("raw, expected", [("0", False), ("false", False), ("1", True), ("true", True), ("yes", True)])
def test_boolean_spellings(monkeypatch, raw, expected):
    assert build(monkeypatch, DEMO_MODE=raw).demo_mode is expected


def test_invalid_boolean_fails_loudly(monkeypatch):
    with pytest.raises(ValidationError):
        build(monkeypatch, DEMO_MODE="maybe")


def test_blank_database_url_means_the_postgresql_default(monkeypatch):
    assert build(monkeypatch, DATABASE_URL="").database_url == DEFAULT_DATABASE_URL == \
        "postgresql://postgres:1234@localhost:5432/Juthoor"


def test_test_suite_reads_no_env_file():
    assert os.environ["JUTHOOR_ENV_FILE"] == "" and env_file() is None


def test_app_engine_points_at_the_test_database_never_the_application_database():
    from app.database import engine
    assert engine.url.database != "Juthoor"
    assert engine.dialect.name == "postgresql" or os.environ["DATABASE_URL"].startswith("sqlite")
