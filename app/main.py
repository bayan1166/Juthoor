from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import adaptive, auth, chat, dashboard, economy, esports

app = FastAPI(title="Juthoor API", version="1.0.0")

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


@app.get("/health")
def health():
    return {"status": "ok"}
