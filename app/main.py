from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (registers every table on Base.metadata)
from app.config import settings
from app.database import Base, engine
from app.routers import adaptive, auth, chat, classroom, community, curriculum, dashboard, economy, esports, payment


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Idempotent: creates missing tables so a fresh SQLite/Postgres works without init_db.py.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Juthoor API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(adaptive.router)
app.include_router(economy.router)
app.include_router(chat.router)
app.include_router(esports.router)
app.include_router(dashboard.router)
app.include_router(curriculum.router)
app.include_router(community.router)
app.include_router(payment.router)
app.include_router(classroom.router)


@app.get("/health")
def health():
    tutor = "openai" if settings.openai_api_key else ("groq" if settings.groq_api_key else "offline_fallback")
    return {"status": "ok", "ai_tutor": tutor}
