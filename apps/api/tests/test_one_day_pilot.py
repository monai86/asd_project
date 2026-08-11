from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.core.config import Settings
from app.core.config import get_settings
from app.main import app
from app.repositories.mock_repository import MockRepository


def _client_with_repo(repo: MockRepository) -> TestClient:
    app.dependency_overrides[get_repository] = lambda: repo
    return TestClient(app)


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_non_mock_runtime_rejects_mock_auth_mode():
    with pytest.raises(ValueError, match="auth mode"):
        Settings(
            mock_mode=False,
            auth_mode="mock",
            cors_allowed_origins="https://clinic.example",
            repository_mode="sql",
            database_url="postgresql+psycopg://prod_user:prod_password@db.example/therapist_app_v2",
            sql_create_schema=False,
            storage_mode="private",
            job_queue_mode="redis",
            redis_url="rediss://redis.example:6379/0",
            observability_enabled=True,
            observability_provider="sentry",
            critical_alert_route="pagerduty-critical",
            secret_store_provider="aws_secrets_manager",
            credential_rotation_runbook="docs/SECRET_ROTATION_RUNBOOK.md",
        ).validate_runtime_security()


def test_evaluation_routes_are_disabled_in_production_like_runtime():
    repo = MockRepository()
    production_settings = Settings(
        mock_mode=False,
        auth_mode="supabase",
        supabase_jwt_secret="test-supabase-jwt-secret",
        supabase_jwt_issuer="https://project-ref.supabase.co/auth/v1",
        cors_allowed_origins="https://clinic.example",
        repository_mode="sql",
        database_url="postgresql+psycopg://prod_user:prod_password@db.example/therapist_app_v2",
        sql_create_schema=False,
        storage_mode="private",
        job_queue_mode="redis",
        redis_url="rediss://redis.example:6379/0",
        observability_enabled=True,
        observability_provider="sentry",
        critical_alert_route="pagerduty-critical",
        secret_store_provider="aws_secrets_manager",
        credential_rotation_runbook="docs/SECRET_ROTATION_RUNBOOK.md",
    )
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = lambda: production_settings
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/evaluation/asr",
            json={"reference_text": "*CHI:\thello .", "hypothesis_text": "*CHI:\thello .", "reference_speakers": ["CHI"]},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 403
    assert response.json()["detail"] == "Evaluation routes are not available in production-like runtime."


def test_provider_discovery_routes_require_authenticated_runtime_session():
    repo = MockRepository()
    production_settings = Settings(
        mock_mode=False,
        auth_mode="supabase",
        supabase_jwt_secret="test-supabase-jwt-secret",
        supabase_jwt_issuer="https://project-ref.supabase.co/auth/v1",
        cors_allowed_origins="https://clinic.example",
        repository_mode="sql",
        database_url="postgresql+psycopg://prod_user:prod_password@db.example/therapist_app_v2",
        sql_create_schema=False,
        storage_mode="private",
        job_queue_mode="redis",
        redis_url="rediss://redis.example:6379/0",
        observability_enabled=True,
        observability_provider="sentry",
        critical_alert_route="pagerduty-critical",
        secret_store_provider="aws_secrets_manager",
        credential_rotation_runbook="docs/SECRET_ROTATION_RUNBOOK.md",
    )
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = lambda: production_settings
    client = TestClient(app)
    try:
        responses = [
            client.get("/api/v1/reports/providers"),
            client.get("/api/v1/features/providers"),
            client.get("/api/v1/features/definitions"),
            client.get("/api/v1/ml/providers"),
            client.get("/api/v1/transcription-providers"),
        ]
    finally:
        _clear_overrides()

    for response in responses:
        assert response.status_code == 401
        assert response.json()["detail"] == "Bearer token required."


def test_case_routes_are_tenant_and_care_team_scoped():
    repo = MockRepository()
    client = _client_with_repo(repo)
    try:
        case_a = client.post(
            "/api/v1/cases",
            headers={"x-mock-user-id": "clinician_a", "x-organization-id": "org_a"},
            json={"child_code": "C-PILOT-A", "age_months": 48},
        ).json()
        case_b = client.post(
            "/api/v1/cases",
            headers={"x-mock-user-id": "clinician_b", "x-organization-id": "org_b"},
            json={"child_code": "C-PILOT-B", "age_months": 60},
        ).json()

        visible = client.get(
            "/api/v1/cases",
            headers={"x-mock-user-id": "clinician_a", "x-organization-id": "org_a"},
        )
        cross_org = client.get(
            f"/api/v1/cases/{case_b['case_id']}",
            headers={"x-mock-user-id": "clinician_a", "x-organization-id": "org_a"},
        )
        same_org_unassigned = client.get(
            f"/api/v1/cases/{case_a['case_id']}",
            headers={"x-mock-user-id": "other_clinician", "x-organization-id": "org_a"},
        )
        admin = client.get(
            f"/api/v1/cases/{case_a['case_id']}",
            headers={"x-mock-user-id": "admin_a", "x-mock-role": "org_admin", "x-organization-id": "org_a"},
        )
        platform = client.get(
            f"/api/v1/cases/{case_a['case_id']}",
            headers={"x-mock-user-id": "platform_1", "x-mock-role": "platform_operator", "x-organization-id": "org_a"},
        )
    finally:
        _clear_overrides()

    assert visible.status_code == 200
    assert [item["case_id"] for item in visible.json()] == [case_a["case_id"]]
    assert cross_org.status_code == 404
    assert same_org_unassigned.status_code == 403
    assert admin.status_code == 403
    assert platform.status_code == 403


def test_session_transcript_and_report_routes_enforce_case_tenant_scope():
    repo = MockRepository()
    client = _client_with_repo(repo)
    try:
        headers_a = {"x-mock-user-id": "clinician_a", "x-organization-id": "org_a"}
        headers_b = {"x-mock-user-id": "clinician_b", "x-organization-id": "org_b"}
        case = client.post("/api/v1/cases", headers=headers_a, json={"child_code": "C-PILOT-T", "age_months": 52}).json()
        session = client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=headers_a,
            json={"session_date": "2026-06-25", "session_type": "therapy_session"},
        ).json()
        transcript = client.post(
            f"/api/v1/sessions/{session['session_id']}/transcripts/manual",
            headers=headers_a,
            json={"text": "THER: hello\nCHI: reviewed placeholder", "language": "English"},
        ).json()
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/qa", headers=headers_a)
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/attest", headers=headers_a, json={"reason": "Reviewed."})
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/extract-features", headers=headers_a)
        report = client.post(f"/api/v1/sessions/{session['session_id']}/reports/draft", headers=headers_a, json={}).json()

        blocked_session = client.get(f"/api/v1/sessions/{session['session_id']}", headers=headers_b)
        blocked_transcript = client.get(f"/api/v1/transcripts/{transcript['transcript_id']}", headers=headers_b)
        blocked_report = client.get(f"/api/v1/reports/{report['report_id']}", headers=headers_b)
    finally:
        _clear_overrides()

    assert blocked_session.status_code == 404
    assert blocked_transcript.status_code == 404
    assert blocked_report.status_code == 404


def test_local_private_upload_intent_and_completion_are_metadata_only():
    repo = MockRepository()
    client = _client_with_repo(repo)
    try:
        headers = {"x-mock-user-id": "clinician_a", "x-organization-id": "org_a"}
        case = client.post("/api/v1/cases", headers=headers, json={"child_code": "C-PILOT-AUDIO", "age_months": 52}).json()
        session = client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=headers,
            json={"session_date": "2026-06-25", "session_type": "therapy_session"},
        ).json()
        job = client.post(
            f"/api/v1/sessions/{session['session_id']}/audio/upload",
            headers=headers,
            json={"filename": "pilot-audio.wav", "content_type": "audio/wav", "size_bytes": 128},
        ).json()
        audio_file = job["details"]["audio_file"]
        intent = job["details"]["upload_intent"]
        put_resp = client.put(f"/api/v1{intent['upload_url']}", headers=headers, content=b"RIFFpilot")
        assert put_resp.status_code == 200
        completed = client.post(
            f"/api/v1/audio/{audio_file['audio_file_id']}/complete-upload",
            headers=headers,
            json={"checksum_sha256": "0" * 64, "size_bytes": 128},
        )
        stored_audio = repo.audio_files[audio_file["audio_file_id"]]
    finally:
        _clear_overrides()

    assert intent["storage_mode"] == "local_private"
    assert intent["expires_in_seconds"] <= 900
    assert intent["upload_url"].startswith("/audio/")
    assert audio_file["object_key"] is None
    assert stored_audio.object_key is not None
    assert stored_audio.object_key.startswith("audio/obj_")
    assert "pilot-audio.wav" not in stored_audio.object_key
    assert case["case_id"] not in stored_audio.object_key
    assert session["session_id"] not in stored_audio.object_key
    assert completed.status_code == 200
    assert completed.json()["upload_status"] == "uploaded"
    assert completed.json()["object_key"] is None


def test_signed_report_snapshot_remains_immutable_after_revision():
    repo = MockRepository()
    client = _client_with_repo(repo)
    try:
        headers = {"x-mock-user-id": "clinician_a", "x-organization-id": "org_a"}
        case = client.post("/api/v1/cases", headers=headers, json={"child_code": "C-PILOT-REPORT", "age_months": 52}).json()
        session = client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=headers,
            json={"session_date": "2026-06-25", "session_type": "therapy_session"},
        ).json()
        transcript = client.post(
            f"/api/v1/sessions/{session['session_id']}/transcripts/manual",
            headers=headers,
            json={"text": "THER: prompt\nCHI: reviewed placeholder words\nCHI: more words", "language": "English"},
        ).json()
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/qa", headers=headers)
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/attest", headers=headers, json={"reason": "Reviewed."})
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/extract-features", headers=headers)
        report = client.post(f"/api/v1/sessions/{session['session_id']}/reports/draft", headers=headers, json={}).json()
        signed = client.post(
            f"/api/v1/reports/{report['report_id']}/sign-off",
            headers=headers,
            json={"therapist_name": "Demo Therapist", "confirmation_checked": True},
        ).json()
        original_hash = signed["signed_snapshot_hash"]
        revised = client.patch(
            f"/api/v1/reports/{report['report_id']}",
            headers=headers,
            json={"therapist_notes": "Pilot revision note."},
        ).json()
        original = client.get(f"/api/v1/reports/{report['report_id']}", headers=headers).json()
    finally:
        _clear_overrides()

    assert revised["report_id"] != report["report_id"]
    assert revised["supersedes_report_id"] == report["report_id"]
    assert original["signed_snapshot_hash"] == original_hash
    assert original["status"] == "Signed Off"
