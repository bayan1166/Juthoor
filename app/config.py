from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://juthoor:juthoor@localhost:5432/juthoor"
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
