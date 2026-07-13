from fastapi.testclient import TestClient

from app.main import app


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
