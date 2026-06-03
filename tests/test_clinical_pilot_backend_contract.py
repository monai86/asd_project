from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.clinical_workflow import MockClinicalRepository  # noqa: E402


def _repo() -> MockClinicalRepository:
    current = datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc)

    def now() -> datetime:
        nonlocal current
        current = current + timedelta(minutes=1)
        return current

    return MockClinicalRepository(now_provider=now)


def test_secure_audio_upload_intent_requires_active_guardian_consent():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    try:
        repo.create_secure_audio_upload_intent(
            case_id="CASE-002",
            session_id="SESSION-002",
            user=therapist,
            original_filename="therapy.wav",
            file_size=2048,
            mime_type="audio/wav",
        )
    except PermissionError as exc:
        assert "Active guardian consent" in str(exc)
    else:
        raise AssertionError("Expected secure upload to require active consent.")


def test_secure_audio_upload_intent_creates_private_object_and_audit_event():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    intent = repo.create_secure_audio_upload_intent(
        case_id="CASE-001",
        session_id="SESSION-001",
        user=therapist,
        original_filename="child_real_name_session.wav",
        file_size=4096,
        mime_type="audio/wav",
        checksum_sha256="abc123",
    )

    audio = intent["audio_file"]
    file_object = intent["file_object"]
    upload = intent["upload"]

    assert audio["storage_mode"] == "secure_private"
    assert audio["file_object_id"] == file_object["file_object_id"]
    assert "child_real_name" not in audio["stored_filename"]
    assert "storage_key" not in file_object
    internal_file_object = repo.file_objects[file_object["file_object_id"]]
    assert internal_file_object.storage_key.startswith("private/user_therapist_001/CASE-001/SESSION-001/")
    assert file_object["encryption_status"] == "required"
    assert upload["method"] == "PUT"
    assert upload["storage_provider"] == "supabase"
    assert upload["signed_upload_url"] == upload["url"]
    assert upload["expires_in_seconds"] == 900
    assert "x-amz-server-side-encryption" in upload["headers"]
    assert any(log.event_type == "secure_upload_intent_created" for log in repo.audit_logs)


def test_processing_job_requires_consent_and_tracks_status_transition():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    job = repo.create_processing_job("SESSION-001", therapist)
    assert job.status == "queued"
    assert repo.sessions["SESSION-001"].processing_status == "processing_submitted"

    updated = repo.update_processing_job(job.job_id, therapist, status="processing", progress=35)
    assert updated is not None
    assert updated.status == "processing"
    assert updated.stage == "transcribing"
    assert updated.progress == 35
    assert repo.sessions["SESSION-001"].processing_status == "processing"

    completed = repo.update_processing_job(
        job.job_id,
        therapist,
        status="completed",
        progress=100,
        stage="awaiting_review",
        result_refs={"transcript_id": "TRANSCRIPT-001"},
    )
    assert completed is not None
    assert completed.stage == "awaiting_review"
    assert completed.result_refs["transcript_id"] == "TRANSCRIPT-001"
    assert completed.finished_at is not None
    assert repo.sessions["SESSION-001"].processing_status == "transcript_ready"
    assert any(log.event_type == "processing_job_updated" for log in repo.audit_logs)


def test_transcript_signoff_records_human_review_gate():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    signoff = repo.signoff_transcript_for_session(
        "SESSION-001",
        therapist,
        "Transcript reviewed against CHAT tiers before feature interpretation.",
    )

    assert signoff.target_type == "transcript"
    assert signoff.session_id == "SESSION-001"
    assert signoff.signed_by_user_id == therapist.user_id
    assert repo.transcripts["TRANSCRIPT-001"].review_status == "reviewed"
    assert repo.sessions["SESSION-001"].feature_extraction_status == "pending"
    assert repo.latest_signoff_for_target("transcript", "TRANSCRIPT-001") is not None
    assert any(log.event_type == "clinical_signoff_created" for log in repo.audit_logs)


def test_model_run_metadata_is_recorded_with_non_diagnostic_thresholds():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None
    repo.signoff_transcript_for_session("SESSION-001", therapist)
    repo.extract_features_for_session("SESSION-001", therapist)

    output = repo.generate_ai_screening_output_for_session("SESSION-001", therapist)
    model_run = next(iter(repo.model_runs.values()))

    assert output.concern_level in {"low_concern", "watchful_review", "moderate_concern"}
    assert "not a diagnosis" in output.explanation.lower()
    assert "diagnosed with" not in output.explanation.lower()
    assert model_run.model_card_version == "prototype-screening-support-v1"
    assert model_run.calibration_metadata["validation_status"] == "not_validated_for_thai_children"


def test_backend_cors_middleware_is_configured():
    from fastapi.testclient import TestClient
    from src.therapist_backend.app import create_app
    client = TestClient(create_app(_repo()))
    response = client.options(
        "/api/me",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-User-Id",
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

