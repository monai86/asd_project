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
        "pipeline_settings",
    } <= response.json().keys()
