from pathlib import Path
import pytest
from src.clinical_workflow.paths import validate_uploads_path

def test_validate_uploads_path_safe():
    safe_path = Path("data/uploads/session_1/audio.wav")
    resolved = validate_uploads_path(safe_path)
    assert resolved.name == "audio.wav"

def test_validate_uploads_path_traversal():
    traversal_path = Path("data/uploads/../../raw/talkbank/secret.cha")
    with pytest.raises(ValueError) as exc:
        validate_uploads_path(traversal_path)
    assert "Directory traversal detected" in str(exc.value)


from fastapi.testclient import TestClient
from src.clinical_workflow import MockClinicalRepository
from src.therapist_backend.app import create_app

def test_upload_intent_endpoint_blocks_traversal():
    repo = MockClinicalRepository()
    app = create_app(repo)
    client = TestClient(app)
    response = client.post(
        "/api/sessions/SESSION-002/audio/upload-intent",
        headers={"X-User-Id": "user_therapist_001"},
        json={
            "original_filename": "../../raw/talkbank/escape.cha",
            "file_size": 1024,
            "mime_type": "audio/wav",
            "checksum_sha256": "abc123sha",
            "retention_days": 90
        }
    )
    assert response.status_code == 400
    assert "Directory traversal detected" in response.json()["detail"]
