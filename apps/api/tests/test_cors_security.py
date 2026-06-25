from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.core.security import OriginGuardMiddleware


def test_cors_origins_are_configurable_from_environment(monkeypatch):
    monkeypatch.setenv(
        "THERAPIST_APP_V2_CORS_ALLOWED_ORIGINS",
        "https://clinic.example, https://admin.example ",
    )

    settings = Settings.from_env()

    assert settings.cors_allowed_origins == "https://clinic.example, https://admin.example "
    assert settings.parsed_cors_allowed_origins == [
        "https://clinic.example",
        "https://admin.example",
    ]


def test_production_rejects_wildcard_or_empty_cors_origins():
    with pytest.raises(ValueError, match="CORS allowed origins"):
        Settings(mock_mode=False, auth_mode="supabase", cors_allowed_origins="*").validate_runtime_security()

    with pytest.raises(ValueError, match="CORS allowed origins"):
        Settings(mock_mode=False, auth_mode="supabase", cors_allowed_origins="").validate_runtime_security()


def test_production_rejects_default_demo_database_and_redis_urls():
    with pytest.raises(ValueError, match="database URL"):
        Settings(
            mock_mode=False,
            auth_mode="supabase",
            cors_allowed_origins="https://clinic.example",
            database_url="postgresql+psycopg://therapist:therapist@localhost/therapist_app_v2",
            repository_mode="sql",
            storage_mode="private",
            job_queue_mode="redis",
            redis_url="rediss://redis.example:6379/0",
        ).validate_runtime_security()

    with pytest.raises(ValueError, match="Redis URL"):
        Settings(
            mock_mode=False,
            auth_mode="supabase",
            cors_allowed_origins="https://clinic.example",
            database_url="postgresql+psycopg://prod_user:prod_secret@db.example/therapist_app_v2",
            repository_mode="sql",
            storage_mode="private",
            job_queue_mode="redis",
            redis_url="redis://localhost:6379/0",
        ).validate_runtime_security()


def test_production_rejects_local_runtime_modes():
    with pytest.raises(ValueError, match="repository mode"):
        Settings(
            mock_mode=False,
            auth_mode="supabase",
            cors_allowed_origins="https://clinic.example",
            database_url="postgresql+psycopg://prod_user:prod_secret@db.example/therapist_app_v2",
            repository_mode="json",
            storage_mode="private",
            job_queue_mode="redis",
            redis_url="rediss://redis.example:6379/0",
        ).validate_runtime_security()

    with pytest.raises(ValueError, match="storage mode"):
        Settings(
            mock_mode=False,
            auth_mode="supabase",
            cors_allowed_origins="https://clinic.example",
            database_url="postgresql+psycopg://prod_user:prod_secret@db.example/therapist_app_v2",
            repository_mode="sql",
            storage_mode="local",
            job_queue_mode="redis",
            redis_url="rediss://redis.example:6379/0",
        ).validate_runtime_security()

    with pytest.raises(ValueError, match="job queue mode"):
        Settings(
            mock_mode=False,
            auth_mode="supabase",
            cors_allowed_origins="https://clinic.example",
            database_url="postgresql+psycopg://prod_user:prod_secret@db.example/therapist_app_v2",
            repository_mode="sql",
            storage_mode="private",
            job_queue_mode="memory",
            redis_url="rediss://redis.example:6379/0",
        ).validate_runtime_security()


def test_origin_guard_blocks_untrusted_unsafe_origin_without_clinical_detail():
    app = FastAPI()
    app.add_middleware(
        OriginGuardMiddleware,
        allowed_origins=["https://trusted.example"],
        enabled=True,
    )

    @app.post("/api/v1/cases")
    def create_case():
        return JSONResponse({"status": "ok"})

    client = TestClient(app)

    blocked = client.post(
        "/api/v1/cases",
        headers={"origin": "https://evil.example"},
        json={"child_code": "C-SHOULD-NOT-LEAK"},
    )
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "Origin is not allowed."
    assert "C-SHOULD-NOT-LEAK" not in blocked.text

    allowed = client.post(
        "/api/v1/cases",
        headers={"origin": "https://trusted.example"},
        json={"child_code": "C-LOCAL-ONLY"},
    )
    assert allowed.status_code == 200
