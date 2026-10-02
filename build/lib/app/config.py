"""Application settings: one source of truth, read from environment variables and `.env`.

Precedence: real environment variables > the `.env` file at the repository root > defaults.

* The `.env` path is absolute (repository root), so the result does not depend on the working
  directory a command is started from.
* `JUTHOOR_ENV_FILE` overrides which file is read; set it to an empty value to read no file at
  all. The test suite does this so a developer's `.env` can never leak into test runs.
* Blank values (``DEMO_MODE=``) mean "use the default" for every non-text setting instead of
  crashing start-up with a validation error.
"""
import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = "postgresql://postgres:1234@localhost:5432/Juthoor"


def env_file() -> str | None:
    chosen = os.environ.get("JUTHOOR_ENV_FILE")
    if chosen is None:
        return str(ROOT / ".env")
    return chosen or None


class Settings(BaseSettings):
    database_url: str = DEFAULT_DATABASE_URL
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 720
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    groq_api_key: str = ""
    groq_chat_model: str = "llama-3.3-70b-versatile"
    stripe_secret_key: str = ""
    chroma_persist_dir: str = "./chroma_store"
    chroma_collection: str = "juthoor_curriculum"
    enable_vector_store: bool = False
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    demo_mode: bool = False
    judge_mode: bool = False
    llm_questions_enabled: bool = False
    llm_timeout_seconds: float = 6.0
    public_url: str = "http://localhost:8000"
    upload_dir: str = "./uploads"
    max_upload_bytes: int = 5 * 1024 * 1024
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    rate_limit_enabled: bool = True
    trust_proxy: bool = False
    smtp_from: str = "no-reply@juthoor.jo"

    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), env_file_encoding="utf-8", extra="ignore")

    @field_validator(
        "enable_vector_store", "demo_mode", "judge_mode", "llm_questions_enabled", "rate_limit_enabled",
        "trust_proxy", "access_token_minutes", "llm_timeout_seconds", "max_upload_bytes", "smtp_port",
        mode="before",
    )
    @classmethod
    def _blank_means_default(cls, value, info):
        if isinstance(value, str) and not value.strip():
            return cls.model_fields[info.field_name].default
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def _database_url(cls, value):
        if isinstance(value, str) and not value.strip():
            return DEFAULT_DATABASE_URL
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def load_settings() -> Settings:
    return Settings(_env_file=env_file())


settings = load_settings()
