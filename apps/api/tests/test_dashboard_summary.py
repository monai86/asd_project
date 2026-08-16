from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import ChildCase, ChildCaseCreate, ReviewStatus, TherapySession, TherapySessionCreate, TherapySessionUpdate

AUTH_HEADERS = {
    "X-Mock-User-Id": "therapist-demo",
    "X-Mock-Role": "therapist",
    "X-Organization-Id": "pilot_org_001",
}


def _fresh_client() -> TestClient:
    repo = MockRepository()
    app.dependency_overrides[get_repository] = lambda: repo
    return TestClient(app), repo


def _create_case_for_therapist(repo: MockRepository, child_code: str) -> ChildCase:
    case = repo.create_case(
        ChildCaseCreate(
            child_code=child_code,
            age_months=58,
            language="English",
            care_team_user_ids=["therapist-demo"],
            primary_therapist_user_id="therapist-demo",
        ),
        actor_id="therapist-demo",
    )
    return case


def test_dashboard_summary_returns_seeded_pipeline_counts():
    client, repo = _fresh_client()
    try:
        response = client.get("/api/v1/dashboard/summary", headers=AUTH_HEADERS)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["organization_id"] == "pilot_org_001"
    assert body["cases"]["total"] == 1
    assert body["cases"]["consent_counts"] == {"granted": 1}
    assert body["sessions"]["total"] == 1
    assert body["sessions"]["status_counts"] == {"Needs Review": 1}
    assert body["reports"]["total"] == 0
    assert body["recent_sessions"][0]["session_id"] == "session_demo_001"
    assert body["recent_sessions"][0]["has_transcript"] is False


def test_dashboard_summary_reflects_full_pipeline_after_workflow():
    client, repo = _fresh_client()
    try:
        case = _create_case_for_therapist(repo, "C-DASH-001")
        session = repo.create_session(
            case.case_id,
            TherapySessionCreate(session_date="2026-08-01", session_type="language_sample"),
            actor_id="therapist-demo",
        )
        stored = repo.sessions[session.session_id]
        stored.status = ReviewStatus.ready
        stored.transcript_id = "transcript-dash-1"
        stored.feature_set_id = "features-dash-1"
        stored.ml_result_id = "ml-dash-1"
        stored.report_id = "report-dash-1"
        case.latest_session_status = ReviewStatus.ready
        assert repo.sessions[session.session_id].transcript_id == "transcript-dash-1"
        response = client.get("/api/v1/dashboard/summary", headers=AUTH_HEADERS)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["cases"]["total"] == 2
    assert body["sessions"]["total"] == 2
    assert body["sessions"]["with_transcript"] == 1
    assert body["sessions"]["with_features"] == 1
    assert body["sessions"]["with_ml_review"] == 1
    assert body["sessions"]["with_report"] == 1
    recent = {item["session_id"]: item for item in body["recent_sessions"]}
    assert recent[session.session_id]["status"] == "Ready"
    assert recent[session.session_id]["has_features"] is True


def test_dashboard_summary_is_scoped_to_the_therapist_organization():
    client, _ = _fresh_client()
    try:
        response = client.get(
            "/api/v1/dashboard/summary",
            headers={**AUTH_HEADERS, "X-Organization-Id": "other_org_001"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["organization_id"] == "other_org_001"
    assert body["cases"]["total"] == 0
    assert body["sessions"]["total"] == 0
