import pytest

from app.core.config import Settings
from app.services.observability import ObservabilitySafetyError, validate_observability_event


def test_observability_event_allows_privacy_safe_operational_fields():
    event = validate_observability_event(
        name="api.request_error",
        severity="error",
        correlation_id="req-20260624-001",
        tags={"route": "/api/v1/transcripts/{transcript_id}/attest", "component": "api"},
        measurements={"duration_ms": 124.5},
        details="Request failed after policy check.",
    )

    assert event.name == "api.request_error"
    assert event.severity == "error"
    assert event.correlation_id == "req-20260624-001"
    assert event.tags["route"] == "/api/v1/transcripts/{transcript_id}/attest"
    assert event.measurements["duration_ms"] == 124.5


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("details", "Transcript line CHI: I want a car."),
        ("tag", "sessions/case-1/audio.raw"),
    ],
)
def test_observability_event_blocks_clinical_or_identifier_content(field_name, field_value):
    kwargs = {
        "name": "worker.failure",
        "severity": "critical",
        "correlation_id": "req-20260624-002",
        "tags": {"component": "worker"},
        "details": "Worker failed without clinical content.",
    }
    if field_name == "details":
        kwargs["details"] = field_value
    else:
        kwargs["tags"] = {"component": field_value}

    with pytest.raises(ObservabilitySafetyError) as error:
        validate_observability_event(**kwargs)

    assert field_value not in str(error.value)


def test_production_requires_observability_provider_and_critical_alert_route():
    base = {
        "mock_mode": False,
        "auth_mode": "supabase",
        "cors_allowed_origins": "https://clinic.example",
        "repository_mode": "sql",
        "database_url": "postgresql+psycopg://prod_user:prod_secret@db.example/therapist_app_v2",
        "storage_mode": "private",
        "job_queue_mode": "redis",
        "redis_url": "rediss://redis.example:6379/0",
    }

    with pytest.raises(ValueError, match="observability provider"):
        Settings(**base).validate_runtime_security()

    with pytest.raises(ValueError, match="critical alert route"):
        Settings(
            **base,
            observability_enabled=True,
            observability_provider="sentry",
        ).validate_runtime_security()
