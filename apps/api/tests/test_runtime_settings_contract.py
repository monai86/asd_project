from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.api.v1.routes import settings as settings_route
from app.core.config import Settings


client = TestClient(app)


def test_runtime_settings_response_preserves_public_contract():
    response = client.get("/api/v1/settings")

    assert response.status_code == 200
    assert {
        "mock_mode",
        "auth_mode",
        "model_version",
        "feature_schema",
        "guideline_mapping",
        "user_roles",
        "access_model",
        "data_retention",
        "consent_policy",
        "capabilities",
        "pipeline_settings",
    } <= response.json().keys()

    assert response.json()["capabilities"] == {
        "cases": "available",
        "audio_upload": "experimental",
        "transcription": "experimental",
        "transcript_qa": "available",
        "feature_extraction": "available",
        "ai_review": "disabled",
        "report_drafting": "disabled",
        "pdf_export": "unavailable",
    }


def test_runtime_settings_marks_non_operational_audio_storage_unavailable(monkeypatch):
    config = Settings().model_copy(update={"storage_mode": "private"})
    monkeypatch.setattr(settings_route, "get_settings", lambda: config)

    payload = settings_route.settings()

    assert payload["capabilities"]["audio_upload"] == "unavailable"
    assert payload["capabilities"]["transcription"] == "unavailable"


def test_runtime_settings_marks_configured_supabase_private_available(monkeypatch):
    config = Settings().model_copy(update={
        "mock_mode": False,
        "storage_mode": "supabase_private",
        "supabase_storage_url": "https://storage.example.test",
        "supabase_storage_service_role_key": "test-service-role-key",
        "supabase_storage_bucket": "test-private-bucket",
    })
    monkeypatch.setattr(settings_route, "get_settings", lambda: config)

    payload = settings_route.settings()

    assert payload["capabilities"]["audio_upload"] == "available"
    assert payload["capabilities"]["transcription"] == "unavailable"


def test_supabase_storage_timeout_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="Supabase storage request timeout must be positive",
    ):
        Settings(
            supabase_storage_request_timeout_seconds=0,
        ).validate_v170_contract()
