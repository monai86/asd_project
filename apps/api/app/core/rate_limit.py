from __future__ import annotations

import time
from math import ceil

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.core.config import get_settings


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, tuple[float, int]] = {}

    def check(self, key: str, *, limit: int, window_seconds: int, now: float | None = None) -> tuple[bool, int]:
        current = now if now is not None else time.monotonic()
        window = max(window_seconds, 1)
        allowed_limit = max(limit, 1)
        reset_at, count = self._buckets.get(key, (current + window, 0))
        if current >= reset_at:
            reset_at = current + window
            count = 0
        if count >= allowed_limit:
            retry_after = max(1, ceil(reset_at - current))
            self._buckets[key] = (reset_at, count)
            return False, retry_after
        self._buckets[key] = (reset_at, count + 1)
        return True, max(1, ceil(reset_at - current))

    def clear(self) -> None:
        self._buckets.clear()


rate_limiter = InMemoryRateLimiter()


def clear_rate_limit_state() -> None:
    rate_limiter.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return await call_next(request)

        key = _client_key(request)
        allowed, retry_after = rate_limiter.check(
            key,
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
        headers = {
            "X-RateLimit-Limit": str(settings.rate_limit_requests),
            "X-RateLimit-Window": str(settings.rate_limit_window_seconds),
        }
        if not allowed:
            return JSONResponse(
                {"detail": "Too many requests."},
                status_code=429,
                headers={**headers, "Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(settings.rate_limit_requests))
        response.headers.setdefault("X-RateLimit-Window", str(settings.rate_limit_window_seconds))
        return response


def _client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"
