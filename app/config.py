from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://juthoor:juthoor@localhost:5432/juthoor"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120
    groq_api_key: str = ""
    groq_chat_model: str = "llama-3.1-70b-versatile"
    chroma_persist_dir: str = "./chroma_store"
    chroma_collection: str = "juthoor_curriculum"
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
