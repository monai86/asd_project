from __future__ import annotations

import json
import logging
import re
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import get_settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("method", "path", "status_code", "duration_ms", "request_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, separators=(",", ":"))


SAFE_PATH_SEGMENTS = {
    "api",
    "v1",
    "health",
    "settings",
    "cases",
    "sessions",
    "transcripts",
    "features",
    "reports",
    "jobs",
    "privacy-requests",
    "audit",
    "evaluation",
    "asr",
    "ai-reviews",
    "ml-review",
    "therapy-goals",
    "audio",
    "upload",
    "process",
    "complete",
    "timeline",
    "manual",
    "qa",
    "attest",
    "extract-features",
    "draft",
    "sign-off",
    "export",
    "withdraw-consent",
    "private",
}
ROUTE_PARAMETER_RE = re.compile(r"^\{[A-Za-z_][A-Za-z0-9_]*\}$")


def sanitize_log_path(path: str) -> str:
    """Return a log-safe path without record IDs, names, storage keys, or files."""

    sanitized_segments: list[str] = []
    for segment in path.split("/"):
        if segment == "":
            continue
        if segment in SAFE_PATH_SEGMENTS or ROUTE_PARAMETER_RE.match(segment):
            sanitized_segments.append(segment)
        else:
            sanitized_segments.append("[redacted]")
    return "/" + "/".join(sanitized_segments)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    for noisy_logger in ("httpx", "httpcore", "urllib3", "uvicorn.access"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.logger = logging.getLogger("therapist_app_v2.request")

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        api_prefix = get_settings().api_prefix
        if request.url.path.startswith(api_prefix) and not route_path.startswith(api_prefix):
            route_path = f"{api_prefix}{route_path}"
        self.logger.info(
            "request_complete",
            extra={
                "method": request.method,
                "path": sanitize_log_path(route_path),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "request_id": request_id,
            },
        )
        response.headers["x-request-id"] = request_id
        return response
