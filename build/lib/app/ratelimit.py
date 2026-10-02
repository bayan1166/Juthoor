from fastapi import HTTPException, Request, status

from app.config import settings
from app.services.ratelimit_core import SlidingWindow

limiter = SlidingWindow()


def _active() -> bool:
    return settings.rate_limit_enabled and not settings.judge_mode


def client_ip(request: Request) -> str:
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def throttle(scope: str, key: str, limit: int, window: int) -> None:
    if not _active():
        return
    allowed, retry = limiter.hit(f"{scope}:{key}", limit, window)
    if not allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited", headers={"Retry-After": str(retry)})


def failures_blocked(key: str, limit: int, window: int) -> int:
    if not _active():
        return 0
    if limiter.count(key, window) >= limit:
        return limiter.retry_after(key, window)
    return 0


def record_failure(key: str, window: int) -> None:
    if _active():
        limiter.record(key, window)


def clear_failures(key: str) -> None:
    limiter.clear(key)
