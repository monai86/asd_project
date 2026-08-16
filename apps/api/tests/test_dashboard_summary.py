from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    ChildCase,
    ChildCaseCreate,
    FeatureSet,
    FeatureValue,
    ReviewStatus,
    TherapySession,
    TherapySessionCreate,
    TherapySessionUpdate,
)

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


def test_dashboard_summary_includes_session_feature_trends():
    client, repo = _fresh_client()
    try:
        case = _create_case_for_therapist(repo, "C-TREND-001")
        session_one = repo.create_session(
            case.case_id,
            TherapySessionCreate(session_date="2026-07-01", session_type="language_sample"),
            actor_id="therapist-demo",
        )
        session_two = repo.create_session(
            case.case_id,
            TherapySessionCreate(session_date="2026-08-01", session_type="language_sample"),
            actor_id="therapist-demo",
        )
        set_one = FeatureSet(
            feature_set_id="fs-trend-1",
            session_id=session_one.session_id,
            transcript_id="transcript-trend-1",
            transcript_version=1,
            therapist_attested=True,
            features=[
                FeatureValue(name="mean_length_of_utterance_words", value=2.4),
                FeatureValue(name="number_of_different_words", value=28),
                FeatureValue(name="mean_length_of_utterance_morphemes", value="not_available"),
            ],
        )
        set_two = FeatureSet(
            feature_set_id="fs-trend-2",
            session_id=session_two.session_id,
            transcript_id="transcript-trend-2",
            transcript_version=1,
            therapist_attested=True,
            features=[
                # Alias names prove the trend endpoint normalizes extractor naming.
                FeatureValue(name="mluw", value=3.1),
                FeatureValue(name="ndw", value=41),
                FeatureValue(name="ttr", value=0.48),
            ],
        )
        repo.features[set_one.feature_set_id] = set_one
        repo.features[set_two.feature_set_id] = set_two
        repo.sessions[session_one.session_id].feature_set_id = set_one.feature_set_id
        repo.sessions[session_two.session_id].feature_set_id = set_two.feature_set_id

        response = client.get("/api/v1/dashboard/summary", headers=AUTH_HEADERS)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    trends = body["feature_trends"]
    feature_keys = [feature["key"] for feature in trends["features"]]
    assert "mlu_words" in feature_keys
    assert "ndw" in feature_keys
    assert "ttr" in feature_keys
    assert "total_words" in feature_keys
    assert "unintelligible_ratio" in feature_keys
    assert trends["features"][0]["label"] == "MLU (words)"

    assert len(trends["cases"]) == 1
    trend_case = trends["cases"][0]
    assert trend_case["case_id"] == case.case_id
    assert trend_case["case_label"] == "C-TREND-001"
    assert [point["session_date"] for point in trend_case["points"]] == ["2026-07-01", "2026-08-01"]
    # First occurrence wins — the provider order keeps long names over aliases.
    assert trend_case["points"][0]["values"]["mlu_words"] == 2.4
    assert trend_case["points"][0]["values"]["ndw"] == 28
    # String "not_available" values (e.g. morpheme MLU) are excluded.
    assert "mean_length_of_utterance_morphemes" not in trend_case["points"][0]["values"]
    # Alias names resolve to the canonical keys.
    assert trend_case["points"][1]["values"]["mlu_words"] == 3.1
    assert trend_case["points"][1]["values"]["ndw"] == 41
    assert trend_case["points"][1]["values"]["ttr"] == 0.48


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
