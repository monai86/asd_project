from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.core.config import Settings, get_settings
from app.db.models import Base
from app.main import app
from app.repositories.mock_repository import MockRepository


def _client_with_repo(repo: MockRepository) -> TestClient:
    app.dependency_overrides[get_repository] = lambda: repo
    return TestClient(app)


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _headers(user_id: str, organization_id: str, role: str = "therapist") -> dict[str, str]:
    return {
        "x-mock-user-id": user_id,
        "x-mock-role": role,
        "x-organization-id": organization_id,
    }


def _build_attested_transcript(client: TestClient, headers: dict[str, str]) -> dict:
    case = client.post("/api/v1/cases", headers=headers, json={"child_code": "C-TENANT", "age_months": 54}).json()
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
    return {"case": case, "session": session, "transcript": transcript}


def test_all_clinical_sql_records_have_organization_scope():
    expected_tables = {
        "child_cases",
        "therapy_goals",
        "sessions",
        "transcripts",
        "feature_sets",
        "audio_files",
        "ai_reviews",
        "ml_results",
        "reports",
        "processing_jobs",
        "privacy_operations",
        "audit_logs",
    }

    missing = {
        table.name
        for table in Base.metadata.sorted_tables
        if table.name in expected_tables and "organization_id" not in table.c
    }

    assert missing == set()


def test_phase1_tenant_model_tables_exist():
    expected_tables = {
        "organizations",
        "organization_settings",
        "user_profiles",
        "organization_memberships",
        "case_care_team_assignments",
        "identity_profiles",
        "regional_retention_policies",
        "consent_records",
        "notifications",
        "job_attempts",
    }

    assert expected_tables <= set(Base.metadata.tables)


def test_clinical_audit_events_capture_target_organization():
    repo = MockRepository()
    client = _client_with_repo(repo)
    headers = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=headers, json={"child_code": "C-AUDIT", "age_months": 54}).json()
    finally:
        _clear_overrides()

    case_audits = [event for event in repo.audit_log if event["target_id"] == case["case_id"]]

    assert case_audits
    assert case_audits[-1]["organization_id"] == "org_a"


def test_phase1_clinical_endpoints_enforce_tenant_guard():
    repo = MockRepository()
    client = _client_with_repo(repo)
    owner = _headers("clinician_a", "org_a")
    cross_tenant = _headers("clinician_b", "org_b")
    try:
        built = _build_attested_transcript(client, owner)
        case_id = built["case"]["case_id"]
        session_id = built["session"]["session_id"]
        transcript_id = built["transcript"]["transcript_id"]

        goal = client.post(
            f"/api/v1/cases/{case_id}/goals",
            headers=owner,
            json={"title": "Pilot goal", "target": "Reviewed target"},
        ).json()
        feature_set = client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", headers=owner, json={}).json()
        ai_review = client.post(f"/api/v1/sessions/{session_id}/ai-review", headers=owner).json()
        privacy = client.post(
            f"/api/v1/cases/{case_id}/privacy-requests",
            headers=owner,
            json={"operation_type": "case_export", "reason": "Pilot export request."},
        ).json()

        blocked_goal = client.get(f"/api/v1/cases/{case_id}/goals", headers=cross_tenant)
        blocked_goal_patch = client.patch(
            f"/api/v1/goals/{goal['goal_id']}",
            headers=cross_tenant,
            json={"notes": "Blocked"},
        )
        blocked_features = client.get(f"/api/v1/sessions/{session_id}/features", headers=cross_tenant)
        blocked_ai = client.get(f"/api/v1/sessions/{session_id}/ai-review", headers=cross_tenant)
        blocked_ai_patch = client.patch(
            f"/api/v1/ai-reviews/{ai_review['ai_review_id']}",
            headers=cross_tenant,
            json={"therapist_notes": "Blocked"},
        )
        blocked_privacy_case = client.get(f"/api/v1/cases/{case_id}/privacy-requests", headers=cross_tenant)
        blocked_privacy_admin = client.patch(
            f"/api/v1/privacy/requests/{privacy['privacy_operation_id']}",
            headers=_headers("admin_b", "org_b", "admin"),
            json={"status": "in_review"},
        )
    finally:
        _clear_overrides()

    assert feature_set["feature_set_id"]
    assert blocked_goal.status_code == 404
    assert blocked_goal_patch.status_code == 404
    assert blocked_features.status_code == 404
    assert blocked_ai.status_code == 404
    assert blocked_ai_patch.status_code == 404
    assert blocked_privacy_case.status_code == 404
    assert blocked_privacy_admin.status_code == 404


def test_supervisor_org_admin_and_platform_operator_matrix():
    repo = MockRepository()
    client = _client_with_repo(repo)
    owner = _headers("clinician_a", "org_a")
    try:
        built = _build_attested_transcript(client, owner)
        case_id = built["case"]["case_id"]

        supervisor_unassigned = client.get(
            f"/api/v1/cases/{case_id}",
            headers=_headers("supervisor_a", "org_a", "clinical_supervisor"),
        )
        org_admin = client.get(
            f"/api/v1/cases/{case_id}",
            headers=_headers("admin_a", "org_a", "org_admin"),
        )
        platform_operator = client.get(
            f"/api/v1/cases/{case_id}",
            headers=_headers("platform_a", "org_a", "platform_operator"),
        )
    finally:
        _clear_overrides()

    assert supervisor_unassigned.status_code == 200
    assert org_admin.status_code == 200
    assert platform_operator.status_code == 403


def test_production_auth_path_rejects_mock_header_identity():
    repo = MockRepository()
    production_settings = Settings(
        mock_mode=False,
        auth_mode="supabase",
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
        response = client.get(
            "/api/v1/cases/case_demo_001",
            headers=_headers("therapist-demo", "pilot_org_001"),
        )
    finally:
        _clear_overrides()

    assert response.status_code == 401
    assert response.json()["detail"] == "Production auth integration is not configured."


def test_postgresql_rls_migration_exists_for_clinical_tables():
    migration = Path("app/db/migrations/versions/0009_add_tenant_rls_policies.py")
    text = migration.read_text(encoding="utf-8")

    for table_name in [
        "child_cases",
        "therapy_goals",
        "sessions",
        "transcripts",
        "feature_sets",
        "audio_files",
        "ai_reviews",
        "ml_results",
        "reports",
        "processing_jobs",
        "privacy_operations",
        "audit_logs",
    ]:
        assert f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY" in text
        assert f"{table_name}_tenant_isolation" in text
