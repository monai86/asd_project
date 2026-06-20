from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import ai_review, audit, cases, evaluation, features, jobs, ml_review, privacy, reports, sessions, settings, therapy_goals, transcripts
from app.core.config import get_settings
from app.core.logging import RequestLoggingMiddleware, configure_logging


configure_logging()
settings_obj = get_settings()

app = FastAPI(
    title=settings_obj.app_name,
    version="0.1.0",
    description="Human-in-the-loop clinical decision-support API for Therapist App v2.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(cases.router, prefix=settings_obj.api_prefix)
app.include_router(sessions.router, prefix=settings_obj.api_prefix)
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


@app.get("/health")
def health():
    return {"status": "ok", "mock_mode": settings_obj.mock_mode}
