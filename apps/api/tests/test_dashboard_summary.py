from __future__ import annotations

import csv
import hashlib
import json

from fastapi.testclient import TestClient

import app.api.v1.routes.dashboard as dashboard_module
from app.api.v1.dependencies import get_repository
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    ChildCase,
    ChildCaseCreate,
    FeatureSet,
    FeatureValue,
    OrganizationMembershipCreate,
    ReviewStatus,
    TherapySession,
    TherapySessionCreate,
    TherapySessionUpdate,
)


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_reference_artifact(tmp_path):
    """Minimal valid reference-evidence artifact (TD row, age 60-71, toyplay)."""
    artifact_dir = tmp_path / "reference-evidence"
    artifact_dir.mkdir()
    cells_path = artifact_dir / "reference_cells.csv"
    fieldnames = [
        "language",
        "age_band_12mo",
        "task_type",
        "original_group",
        "presentation_group",
        "participant_count",
        "corpus_count",
        "supported",
        "reason_code",
    ]
    for feature in (
        "total_utterances",
        "total_words",
        "ttr",
        "mluw",
        "unintelligible_ratio",
        "question_ratio",
        "echolalia_count",
        "pronoun_reversal_count",
    ):
        fieldnames.extend([f"{feature}_q1", f"{feature}_median", f"{feature}_q3"])
    row = {
        "language": "eng",
        "age_band_12mo": "60-71",
        "task_type": "toyplay",
        "original_group": "TD",
        "presentation_group": "TD",
        "participant_count": 32,
        "corpus_count": 2,
        "supported": "true",
        "reason_code": "",
    }
    for feature in (
        "total_utterances",
        "total_words",
        "ttr",
        "mluw",
        "unintelligible_ratio",
        "question_ratio",
        "echolalia_count",
        "pronoun_reversal_count",
    ):
        row[f"{feature}_q1"] = 1.0
        row[f"{feature}_median"] = 2.0
        row[f"{feature}_q3"] = 3.0
    with cells_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)
    manifest = {
        "artifact_type": "ml_reference_evidence",
        "artifact_version": "test-v1",
        "dataset_hash": "test-dataset-hash",
        "feature_schema_version": "reference-core-14-v1",
        "supported_language": "eng",
        "gate1": {"status": "research_only"},
        "files": {
            "reference_cells": {
                "filename": cells_path.name,
                "sha256": _sha256(cells_path),
                "size_bytes": cells_path.stat().st_size,
            }
        },
    }
    (artifact_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return artifact_dir

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


def _headers(user_id: str, role: str, organization_id: str = "pilot_org_001") -> dict[str, str]:
    return {
        "X-Mock-User-Id": user_id,
        "X-Mock-Role": role,
        "X-Organization-Id": organization_id,
    }


def _upsert_membership(
    repo: MockRepository,
    user_id: str,
    role: str = "therapist",
    *,
    active: bool = True,
    organization_id: str = "pilot_org_001",
) -> None:
    repo.upsert_membership(
        organization_id,
        OrganizationMembershipCreate(
            user_id=user_id,
            display_name=f"Test {user_id}",
            role=role,
            active=active,
        ),
        actor_id="system",
    )


def _create_case_for_user(
    repo: MockRepository,
    user_id: str,
    child_code: str,
    *,
    organization_id: str = "pilot_org_001",
) -> ChildCase:
    return repo.create_case(
        ChildCaseCreate(
            child_code=child_code,
            organization_id=organization_id,
            age_months=58,
            language="English",
            care_team_user_ids=[user_id],
            primary_therapist_user_id=user_id,
        ),
        actor_id="system",
    )


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


def test_dashboard_summary_attaches_td_reference_band_to_trend_cases(tmp_path, monkeypatch):
    artifact_dir = _write_reference_artifact(tmp_path)
    monkeypatch.setenv("THERAPIST_APP_V2_REFERENCE_ARTIFACT_DIR", str(artifact_dir))
    from app.core.config import get_settings
    get_settings.cache_clear()
    dashboard_module._REFERENCE_PROVIDER = None
    client, repo = _fresh_client()
    try:
        case = _create_case_for_therapist(repo, "C-TREND-REF")
        repo.cases[case.case_id].age_months = 62
        session = repo.create_session(
            case.case_id,
            TherapySessionCreate(session_date="2026-08-01", session_type="therapy_session"),
            actor_id="therapist-demo",
        )
        feature_set = FeatureSet(
            feature_set_id="fs-ref-1",
            session_id=session.session_id,
            transcript_id="transcript-ref-1",
            transcript_version=1,
            therapist_attested=True,
            features=[
                FeatureValue(name="mean_length_of_utterance_words", value=2.4),
                FeatureValue(name="type_token_ratio", value=0.5),
            ],
        )
        repo.features[feature_set.feature_set_id] = feature_set
        repo.sessions[session.session_id].feature_set_id = feature_set.feature_set_id

        response = client.get("/api/v1/dashboard/summary", headers=AUTH_HEADERS)
    finally:
        app.dependency_overrides.clear()
        dashboard_module._REFERENCE_PROVIDER = None
        get_settings.cache_clear()

    assert response.status_code == 200
    trend_case = next(
        item for item in response.json()["feature_trends"]["cases"]
        if item["case_id"] == case.case_id
    )
    reference = trend_case["reference"]
    assert reference is not None
    assert reference["age_band"] == "60-71"
    assert reference["task_type"] == "toyplay"
    assert reference["features"]["mlu_words"] == {"q1": 1.0, "median": 2.0, "q3": 3.0}
    assert reference["features"]["ttr"] == {"q1": 1.0, "median": 2.0, "q3": 3.0}
    # NDW has no reference-cell column and is omitted.
    assert "ndw" not in reference["features"]


def test_dashboard_summary_trend_omits_reference_when_artifact_is_missing():
    client, repo = _fresh_client()
    try:
        case = _create_case_for_therapist(repo, "C-TREND-NOREF")
        session = repo.create_session(
            case.case_id,
            TherapySessionCreate(session_date="2026-08-01", session_type="therapy_session"),
            actor_id="therapist-demo",
        )
        feature_set = FeatureSet(
            feature_set_id="fs-noref-1",
            session_id=session.session_id,
            transcript_id="transcript-noref-1",
            transcript_version=1,
            therapist_attested=True,
            features=[FeatureValue(name="mean_length_of_utterance_words", value=2.4)],
        )
        repo.features[feature_set.feature_set_id] = feature_set
        repo.sessions[session.session_id].feature_set_id = feature_set.feature_set_id

        response = client.get("/api/v1/dashboard/summary", headers=AUTH_HEADERS)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    trend_case = next(
        item for item in response.json()["feature_trends"]["cases"]
        if item["case_id"] == case.case_id
    )
    assert trend_case["reference"] is None


def test_case_feature_trend_endpoint_returns_single_case_series():
    client, repo = _fresh_client()
    try:
        case = _create_case_for_therapist(repo, "C-TREND-ONLY")
        session = repo.create_session(
            case.case_id,
            TherapySessionCreate(session_date="2026-08-01", session_type="therapy_session"),
            actor_id="therapist-demo",
        )
        feature_set = FeatureSet(
            feature_set_id="fs-only-1",
            session_id=session.session_id,
            transcript_id="transcript-only-1",
            transcript_version=1,
            therapist_attested=True,
            features=[FeatureValue(name="mean_length_of_utterance_words", value=2.4)],
        )
        repo.features[feature_set.feature_set_id] = feature_set
        repo.sessions[session.session_id].feature_set_id = feature_set.feature_set_id

        response = client.get(
            f"/api/v1/cases/{case.case_id}/feature-trend",
            headers=AUTH_HEADERS,
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body["cases"]) == 1
    assert body["cases"][0]["case_id"] == case.case_id
    assert body["cases"][0]["points"][0]["values"]["mlu_words"] == 2.4
    assert [feature["key"] for feature in body["features"]][0] == "mlu_words"


def test_case_feature_trend_endpoint_is_org_scoped():
    client, _ = _fresh_client()
    try:
        response = client.get(
            "/api/v1/cases/case_demo_001/feature-trend",
            headers={**AUTH_HEADERS, "X-Organization-Id": "other_org_001"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_dashboard_uses_persisted_therapist_role_when_jwt_claims_supervisor():
    client, repo = _fresh_client()
    try:
        _upsert_membership(repo, "other-therapist")
        unrelated = _create_case_for_user(repo, "other-therapist", "C-UNRELATED")

        summary = client.get(
            "/api/v1/dashboard/summary",
            headers=_headers("therapist-demo", "clinical_supervisor"),
        )
        trend = client.get(
            f"/api/v1/cases/{unrelated.case_id}/feature-trend",
            headers=_headers("therapist-demo", "clinical_supervisor"),
        )
    finally:
        app.dependency_overrides.clear()

    assert summary.status_code == 200
    assert summary.json()["cases"]["total"] == 1
    assert trend.status_code == 403
    assert trend.json()["detail"] == "Care-team assignment required."


def test_dashboard_excludes_unrelated_cases_for_unassigned_active_therapist():
    client, repo = _fresh_client()
    try:
        _upsert_membership(repo, "unassigned-therapist")
        summary = client.get(
            "/api/v1/dashboard/summary",
            headers=_headers("unassigned-therapist", "therapist"),
        )
        trend = client.get(
            "/api/v1/cases/case_demo_001/feature-trend",
            headers=_headers("unassigned-therapist", "therapist"),
        )
    finally:
        app.dependency_overrides.clear()

    assert summary.status_code == 200
    assert summary.json()["cases"]["total"] == 0
    assert summary.json()["sessions"]["total"] == 0
    assert trend.status_code == 403


def test_dashboard_denies_inactive_authoritative_membership():
    client, repo = _fresh_client()
    try:
        _upsert_membership(repo, "therapist-demo", active=False)
        summary = client.get("/api/v1/dashboard/summary", headers=AUTH_HEADERS)
        trend = client.get(
            "/api/v1/cases/case_demo_001/feature-trend",
            headers=AUTH_HEADERS,
        )
    finally:
        app.dependency_overrides.clear()

    assert summary.status_code == 403
    assert summary.json()["detail"] == "Active organization membership required."
    assert trend.status_code == 403
    assert trend.json()["detail"] == "Active organization membership required."


def test_dashboard_allows_authoritative_supervisor_to_view_org_cases():
    client, repo = _fresh_client()
    try:
        _upsert_membership(repo, "supervisor", role="clinical_supervisor")
        _upsert_membership(repo, "other-therapist")
        unrelated = _create_case_for_user(repo, "other-therapist", "C-SUPERVISOR")

        summary = client.get(
            "/api/v1/dashboard/summary",
            headers=_headers("supervisor", "clinical_supervisor"),
        )
        trend = client.get(
            f"/api/v1/cases/{unrelated.case_id}/feature-trend",
            headers=_headers("supervisor", "clinical_supervisor"),
        )
    finally:
        app.dependency_overrides.clear()

    assert summary.status_code == 200
    assert summary.json()["cases"]["total"] == 2
    assert trend.status_code == 200


def test_dashboard_summary_is_scoped_to_the_therapist_organization():
    client, repo = _fresh_client()
    try:
        _upsert_membership(
            repo,
            "therapist-demo",
            organization_id="other_org_001",
        )
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
