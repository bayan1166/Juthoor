from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://juthoor:juthoor@localhost:5432/juthoor"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120
    # OpenAI is the primary tutor model (smarter than the Groq fallback).
    # Set OPENAI_API_KEY in .env; the app also runs fully offline without any key.
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    # Legacy fallback: used only if OPENAI_API_KEY is not set and GROQ_API_KEY is.
    groq_api_key: str = ""
    groq_chat_model: str = "llama-3.3-70b-versatile"
    # Real payments in Stripe TEST mode when set. Test cards work; no merchant account needed.
    # Get a test key from https://dashboard.stripe.com/test/apikeys — it starts with sk_test_.
    stripe_secret_key: str = ""
    chroma_persist_dir: str = "./chroma_store"
    chroma_collection: str = "juthoor_curriculum"
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
