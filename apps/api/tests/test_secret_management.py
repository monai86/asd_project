import pytest

from app.core.config import Settings


def _production_base_settings() -> dict[str, object]:
    return {
        "mock_mode": False,
        "cors_allowed_origins": "https://clinic.example",
        "repository_mode": "sql",
        "database_url": "postgresql+psycopg://prod_user:prod_password@db.example/therapist_app_v2",
        "sql_create_schema": False,
        "storage_mode": "private",
        "job_queue_mode": "redis",
        "redis_url": "rediss://redis.example:6379/0",
        "observability_enabled": True,
        "observability_provider": "sentry",
        "critical_alert_route": "pagerduty-critical",
    }


def test_production_requires_managed_secret_store_provider():
    with pytest.raises(ValueError, match="managed secret store"):
        Settings(**_production_base_settings()).validate_runtime_security()


def test_production_requires_credential_rotation_runbook_reference():
    with pytest.raises(ValueError, match="credential rotation runbook"):
        Settings(
            **_production_base_settings(),
            secret_store_provider="aws_secrets_manager",
        ).validate_runtime_security()


def test_production_accepts_managed_secret_store_with_rotation_runbook():
    settings = Settings(
        **_production_base_settings(),
        secret_store_provider="aws_secrets_manager",
        credential_rotation_runbook="docs/SECRET_ROTATION_RUNBOOK.md",
    ).validate_runtime_security()

    assert settings.secret_store_provider == "aws_secrets_manager"
    assert settings.credential_rotation_runbook == "docs/SECRET_ROTATION_RUNBOOK.md"


def test_production_rejects_sql_automatic_schema_creation():
    settings = {
        **_production_base_settings(),
        "secret_store_provider": "aws_secrets_manager",
        "credential_rotation_runbook": "docs/SECRET_ROTATION_RUNBOOK.md",
        "sql_create_schema": True,
    }
    with pytest.raises(ValueError, match="Alembic"):
        Settings(**settings).validate_runtime_security()
