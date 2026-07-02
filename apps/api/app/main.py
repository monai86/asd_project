from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.v1.routes import ai_review, audit, cases, evaluation, features, jobs, ml_review, organization_admin, privacy, reports, sessions, settings, therapy_goals, transcripts
from app.core.config import get_settings
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.core.rate_limit import RateLimitMiddleware
from app.core.security import OriginGuardMiddleware
from app.db.migrations_runner import run_alembic_upgrade_head


configure_logging()
settings_obj = get_settings()
logger = logging.getLogger("therapist_app_v2.startup")

app = FastAPI(
    title=settings_obj.app_name,
    version="1.6.3",
    description="Human-in-the-loop clinical decision-support API for lingualens.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_obj.parsed_cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    OriginGuardMiddleware,
    allowed_origins=settings_obj.parsed_cors_allowed_origins,
    enabled=settings_obj.csrf_origin_guard_enabled,
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(cases.router, prefix=settings_obj.api_prefix)
app.include_router(sessions.router, prefix=settings_obj.api_prefix)
app.include_router(organization_admin.router, prefix=settings_obj.api_prefix)
app.include_router(therapy_goals.router, prefix=settings_obj.api_prefix)
app.include_router(transcripts.router, prefix=settings_obj.api_prefix)
app.include_router(features.router, prefix=settings_obj.api_prefix)
app.include_router(ai_review.router, prefix=settings_obj.api_prefix)
app.include_router(ml_review.router, prefix=settings_obj.api_prefix)
app.include_router(reports.router, prefix=settings_obj.api_prefix)
app.include_router(jobs.router, prefix=settings_obj.api_prefix)
app.include_router(privacy.router, prefix=settings_obj.api_prefix)
app.include_router(settings.router, prefix=settings_obj.api_prefix)
app.include_router(evaluation.router, prefix=settings_obj.api_prefix)
app.include_router(audit.router, prefix=settings_obj.api_prefix)


@app.on_event("startup")
def apply_startup_migrations() -> None:
    if settings_obj.run_migrations_on_startup:
        try:
            run_alembic_upgrade_head()
        except Exception:
            logger.exception("Startup Alembic migration failed.")
            raise


@app.get("/health")
def health():
    return {"status": "ok", "mock_mode": settings_obj.mock_mode}
