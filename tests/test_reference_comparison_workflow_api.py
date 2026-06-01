from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.clinical_workflow import MockClinicalRepository  # noqa: E402
from src.reference_engine import (  # noqa: E402
    INSUFFICIENT_REFERENCE_DATA,
    OK,
    REFERENCE_TERM,
    assert_descriptive_wording,
)
from src.therapist_backend.app import create_app  # noqa: E402


def _repo() -> MockClinicalRepository:
    return MockClinicalRepository()


def _therapist(repo: MockClinicalRepository):
    user = repo.authenticate("therapist@example.test", "demo-password")
    assert user is not None
    return user


def _clinician(repo: MockClinicalRepository):
    user = repo.authenticate("clinician@example.test", "demo-password")
    assert user is not None
    return user


def _admin(repo: MockClinicalRepository):
    user = repo.authenticate("admin@example.test", "demo-password")
    assert user is not None
    return user


def test_reference_comparison_returns_after_features_are_available():
    repo = _repo()
    therapist = _therapist(repo)

    result = repo.get_reference_comparison_for_session_for_user("SESSION-001", therapist)

    assert result is not None
    assert result.status == OK
    assert result.reference_term == REFERENCE_TERM
    assert result.age_band_12mo == "48-59"
    assert result.task_type == "toyplay"
    assert result.cohorts
    assert any(
        cohort.clan_metric_comparisons for cohort in result.cohorts if cohort.confidence_flag == OK
    )
    assert_descriptive_wording(result.to_dict())


def test_reference_comparison_requires_extracted_features():
    repo = _repo()
    therapist = _therapist(repo)

    try:
        repo.get_reference_comparison_for_session_for_user("SESSION-002", therapist)
    except ValueError as exc:
        assert "Extracted features are required" in str(exc)
    else:
        raise AssertionError("Expected ValueError before feature extraction.")


def test_reference_comparison_respects_owner_and_admin_access():
    repo = _repo()
    therapist = _therapist(repo)
    admin = _admin(repo)

    assert repo.get_reference_comparison_for_session_for_user("SESSION-003", therapist) is None
    assert repo.get_reference_comparison_for_session_for_user("SESSION-001", admin) is not None


def test_reference_comparison_uses_feature_age_before_case_age():
    repo = _repo()
    therapist = _therapist(repo)
    repo.cases["CASE-001"] = replace(repo.cases["CASE-001"], age_months=84)

    result = repo.get_reference_comparison_for_session_for_user("SESSION-001", therapist)

    assert result is not None
    assert result.age_band_12mo == "48-59"


def test_reference_comparison_maps_structured_assessment_to_narrative():
    repo = _repo()
    clinician = _clinician(repo)
    seed = repo.extracted_features["FEATURE-001"]
    repo.extracted_features["FEATURE-structured"] = replace(
        seed,
        feature_id="FEATURE-structured",
        session_id="SESSION-003",
        case_id="CASE-003",
        owner_user_id="user_clinician_001",
    )

    result = repo.get_reference_comparison_for_session_for_user("SESSION-003", clinician)

    assert result is not None
    assert result.task_type == "narrative"


def test_reference_comparison_insufficient_data_is_result_not_exception():
    repo = _repo()
    therapist = _therapist(repo)
    seed = repo.extracted_features["FEATURE-001"]
    features = dict(seed.core_features)
    features["age_months"] = 240
    repo.extracted_features["FEATURE-001"] = replace(seed, core_features=features, features=features)

    result = repo.get_reference_comparison_for_session_for_user("SESSION-001", therapist)

    assert result is not None
    assert result.status == INSUFFICIENT_REFERENCE_DATA
    assert "no_matching_reference_cohort" in result.warnings


def test_reference_comparison_does_not_write_audit_log():
    repo = _repo()
    therapist = _therapist(repo)
    audit_count = len(repo.audit_logs)

    repo.get_reference_comparison_for_session_for_user("SESSION-001", therapist)

    assert len(repo.audit_logs) == audit_count


def test_reference_comparison_api_returns_200_payload():
    repo = _repo()
    app = create_app(repo)
    client = TestClient(app)

    response = client.get(
        "/api/sessions/SESSION-001/reference-comparison",
        headers={"X-User-Id": "user_therapist_001"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reference_term"] == REFERENCE_TERM
    assert payload["status"] == OK
    assert payload["cohorts"]
    assert payload["cohorts"][0]["feature_comparisons"]
    ok_cohorts = [cohort for cohort in payload["cohorts"] if cohort["confidence_flag"] == OK]
    assert any(cohort["clan_metric_comparisons"] for cohort in ok_cohorts)
    assert all("clan_metric_comparisons" in cohort for cohort in payload["cohorts"])
    assert_descriptive_wording(payload)


def test_reference_comparison_api_missing_features_returns_400():
    repo = _repo()
    app = create_app(repo)
    client = TestClient(app)

    response = client.get(
        "/api/sessions/SESSION-002/reference-comparison",
        headers={"X-User-Id": "user_therapist_001"},
    )

    assert response.status_code == 400
    assert "Extracted features are required" in response.json()["detail"]


def test_reference_comparison_api_unknown_or_unauthorized_session_returns_404():
    repo = _repo()
    app = create_app(repo)
    client = TestClient(app)

    unknown = client.get(
        "/api/sessions/SESSION-999/reference-comparison",
        headers={"X-User-Id": "user_therapist_001"},
    )
    unauthorized = client.get(
        "/api/sessions/SESSION-003/reference-comparison",
        headers={"X-User-Id": "user_therapist_001"},
    )

    assert unknown.status_code == 404
    assert unauthorized.status_code == 404


def test_transcript_qa_api_returns_backend_readiness_payload_without_mutating():
    repo = _repo()
    app = create_app(repo)
    client = TestClient(app)
    audit_count = len(repo.audit_logs)
    stored_status = repo.transcripts["TRANSCRIPT-001"].qa_status
    stored_score = repo.transcripts["TRANSCRIPT-001"].qa_score

    response = client.get(
        "/api/sessions/SESSION-001/qa",
        headers={"X-User-Id": "user_therapist_001"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript_id"] == "TRANSCRIPT-001"
    assert payload["session_id"] == "SESSION-001"
    assert payload["status"] in {"pass", "needs_review"}
    assert payload["qa_status"] == payload["status"]
    assert payload["qa_score"] == payload["quality_score"]
    assert payload["summary"]["child_utterance_count"] > 0
    assert payload["summary"]["child_token_count"] > 0
    assert payload["readiness"]["feature_extraction_ready"] is True
    assert "reference_comparison_ready" in payload["readiness"]
    assert "clan_metric_ready" in payload["readiness"]
    assert len(repo.audit_logs) == audit_count
    assert repo.transcripts["TRANSCRIPT-001"].qa_status == stored_status
    assert repo.transcripts["TRANSCRIPT-001"].qa_score == stored_score


def test_transcript_qa_api_unknown_no_transcript_or_unauthorized_returns_404():
    repo = _repo()
    app = create_app(repo)
    client = TestClient(app)

    unknown = client.get(
        "/api/sessions/SESSION-999/qa",
        headers={"X-User-Id": "user_therapist_001"},
    )
    no_transcript = client.get(
        "/api/sessions/SESSION-002/qa",
        headers={"X-User-Id": "user_therapist_001"},
    )
    unauthorized = client.get(
        "/api/sessions/SESSION-003/qa",
        headers={"X-User-Id": "user_therapist_001"},
    )

    assert unknown.status_code == 404
    assert no_transcript.status_code == 404
    assert unauthorized.status_code == 404
