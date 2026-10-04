import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app import models as _models
from app.config import settings
from app.database import engine, ensure_schema
from app.services.secrets_check import suggestion, weak_secret_reason
from app.routers import (
    adaptive, auth, chat, community, curriculum, dashboard, economy, esports, moderation, payment,
)

logger = logging.getLogger("juthoor")
STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not settings.demo_mode:
        reason = weak_secret_reason(settings.jwt_secret)
        if reason:
            raise RuntimeError(f"{reason}. Set a strong JWT_SECRET in .env, for example: {suggestion()}")
    ensure_schema()
    yield


app = FastAPI(title="Juthoor API", version="2.0.0", lifespan=lifespan)

app.add_middleware(GZipMiddleware, minimum_size=600)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def harden(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/app"):
        response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.exception_handler(OperationalError)
async def database_down(request: Request, exc: OperationalError):
    logger.error("database unavailable on %s %s: %s", request.method, request.url.path, exc.__class__.__name__)
    return JSONResponse(status_code=503, content={"detail": "database_unavailable"})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "server_error"})


for module in (auth, adaptive, chat, curriculum, dashboard, economy, esports, community, payment, moderation):
    app.include_router(module.router)


@app.get("/health")
def health():
    tutor = "openai" if settings.openai_api_key else ("groq" if settings.groq_api_key else "offline_fallback")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"
    return {"status": "ok" if database == "ok" else "degraded", "database": database,
            "database_dialect": engine.dialect.name, "ai_tutor": tutor,
            "demo": settings.demo_mode, "judge": settings.judge_mode}


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/app/")


if STATIC_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(STATIC_DIR), html=True), name="app")
