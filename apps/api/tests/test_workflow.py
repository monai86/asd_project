import json
from pathlib import Path
import warnings

from fastapi.testclient import TestClient
import pytest

from app.api.v1.dependencies import get_repository, get_repository_singleton
from app.core.config import get_settings
from app.core.rate_limit import clear_rate_limit_state
from app.main import app
from app.repositories.mock_repository import JsonFileRepository, MockRepository
from app.schemas.clinical import OrganizationMembershipCreate, QaIssue, ReviewStatus
from app.services.ai_review_service import sanitize_for_ai
from app.services.ml_providers.registry import ml_provider_registry
from app.tasks.job_queue import get_job_queue
from app.tasks.worker import run_worker_once
from tests.path_helpers import repo_root


client = TestClient(app)


def feature_map(feature_set: dict) -> dict[str, object]:
    return {item["name"]: item["value"] for item in feature_set["features"]}


def test_demo_manifest_includes_required_non_identifying_assets():
    repository_root = repo_root()
    manifest_path = repository_root / "data" / "demo" / "demo_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["demo_mode"] == "lingualens-app-local"
    assert {account["role"] for account in manifest["mock_accounts"]} == {"therapist", "org_admin"}
    assert len(manifest["cases"]) >= 2
    assert len(manifest["sessions"]) >= 2
    assert (repository_root / manifest["artifacts"]["sample_cha"]).exists()
    assert (repository_root / manifest["artifacts"]["sample_report"]).exists()

    serialized = json.dumps(manifest).lower()
    forbidden_terms = ["_".join(["audio", "bytes"]), "storage_key", "email@", "surname"]
    assert not any(term in serialized for term in forbidden_terms)
    assert all(case["child_code"].startswith("C-") for case in manifest["cases"])


def test_health_adds_request_id_header():
    response = client.get("/health", headers={"x-request-id": "req-test-001"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-test-001"


def test_acknowledge_session_cues_records_audit_trail_and_returns_ack():
    repo = MockRepository()
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        test_client = TestClient(app)
        headers = {
            "x-mock-user-id": "therapist-demo",
            "x-mock-role": "therapist",
            "x-organization-id": "pilot_org_001",
        }
        case = test_client.post(
            "/api/v1/cases",
            headers=headers,
            json={"child_code": "C-ACK-001", "age_months": 60, "consent_status": "granted"},
        ).json()
        session = test_client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=headers,
            json={"session_date": "2026-07-21", "session_type": "language_sample"},
        ).json()

        response = test_client.post(f"/api/v1/sessions/{session['session_id']}/acknowledge-cues", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["acknowledged"] is True
        assert body["session_id"] == session["session_id"]
        assert body["acknowledged_by"] == "therapist-demo"
        assert body["acknowledged_at"]

        assert any(
            event["action"] == "cues_acknowledged" and event["target_id"] == session["session_id"]
            for event in repo.audit_log
        )

        # The acknowledgment persists on the session and is readable back.
        persisted = test_client.get(f"/api/v1/sessions/{session['session_id']}", headers=headers).json()
        assert persisted["cues_acknowledged_at"] == body["acknowledged_at"]
        assert persisted["cues_acknowledged_by"] == "therapist-demo"
        status_body = test_client.get(
            f"/api/v1/sessions/{session['session_id']}/status", headers=headers
        ).json()
        assert status_body["cues_acknowledged_by"] == "therapist-demo"
    finally:
        app.dependency_overrides.clear()


def test_settings_exposes_non_sensitive_runtime_modes():
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    pipeline_settings = response.json()["pipeline_settings"]
    assert pipeline_settings["audio_processing"] == "experimental_async"
    assert pipeline_settings["repository_mode"] in {"memory", "json", "sql"}
    assert pipeline_settings["storage_mode"] in {"metadata", "local", "local_private"}
    assert pipeline_settings["ai_review_policy"] == "organization_opt_in_default_off"
    assert isinstance(pipeline_settings["ai_report_drafting_enabled"], bool)


def test_ai_review_fails_closed_when_organization_has_not_opted_in():
    repo = MockRepository()
    repo.set_ai_review_enabled("pilot_org_001", False)
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        case_id = client.post(
            "/api/v1/cases",
            json={"child_code": "C-AI-OFF-001", "age_months": 60, "language": "English", "consent_status": "granted"},
        ).json()["case_id"]
        session_id = client.post(
            f"/api/v1/cases/{case_id}/sessions",
            json={"session_date": "2026-06-13", "session_type": "therapy_session"},
        ).json()["session_id"]
        transcript_id = client.post(
            f"/api/v1/sessions/{session_id}/transcripts/upload-cha",
            json={
                "filename": "sample.cha",
                "cha_text": "\n".join(
                    [
                        "@Begin",
                        "@Languages:\teng",
                        "@Participants:\tCHI Child Target_Child, THER Therapist Investigator",
                        "*THER:\twhat do you see ?",
                        "*CHI:\tI see a red car .",
                        "@End",
                    ]
                ),
            },
        ).json()["transcript_id"]
        assert client.post(f"/api/v1/transcripts/{transcript_id}/qa").status_code == 200
        assert client.post(
            f"/api/v1/transcripts/{transcript_id}/attest",
            json={"reason": "Reviewed sample for launch policy coverage."},
        ).status_code == 200
        assert client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={}).status_code == 200

        blocked = client.post(f"/api/v1/sessions/{session_id}/ai-review")
    finally:
        app.dependency_overrides.pop(get_repository, None)

    assert blocked.status_code == 400
    assert blocked.json()["detail"] == (
        "AI-assisted review is unavailable because this organization has not enabled it."
    )


def test_rate_limiting_can_be_enabled_with_safe_429_response(monkeypatch):
    monkeypatch.setenv("THERAPIST_APP_V2_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("THERAPIST_APP_V2_RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("THERAPIST_APP_V2_RATE_LIMIT_WINDOW_SECONDS", "60")
    get_settings.cache_clear()
    headers = {"x-forwarded-for": "203.0.113.77"}
    try:
        assert client.get("/api/v1/settings", headers=headers).status_code == 200
        assert client.get("/api/v1/settings", headers=headers).status_code == 200
        limited = client.get("/api/v1/settings", headers=headers)
    finally:
        monkeypatch.delenv("THERAPIST_APP_V2_RATE_LIMIT_ENABLED", raising=False)
        monkeypatch.delenv("THERAPIST_APP_V2_RATE_LIMIT_REQUESTS", raising=False)
        monkeypatch.delenv("THERAPIST_APP_V2_RATE_LIMIT_WINDOW_SECONDS", raising=False)
        get_settings.cache_clear()
        clear_rate_limit_state()

    assert limited.status_code == 429
    assert limited.json()["detail"] == "Too many requests."
    assert limited.headers["retry-after"] == "60"
    assert limited.headers["x-ratelimit-limit"] == "2"


def test_active_api_accepts_x_user_id_header_for_user_scoped_routes():
    headers = {"X-User-Id": "user_therapist_001"}
    case_id = client.post(
        "/api/v1/cases",
        headers=headers,
        json={"child_code": "C-HEADER-001", "age_months": 48, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]

    response = client.post(
        f"/api/v1/cases/{case_id}/privacy-requests",
        headers=headers,
        json={"operation_type": "case_export", "reason": "Header compatibility test"},
    )
    assert response.status_code == 200
    assert response.json()["requested_by"] == "user_therapist_001"


def test_repository_mode_defaults_to_json_without_environment_override(monkeypatch):
    monkeypatch.delenv("LINGUALENS_REPOSITORY_MODE", raising=False)
    monkeypatch.delenv("THERAPIST_APP_V2_REPOSITORY_MODE", raising=False)
    get_settings.cache_clear()

    assert get_settings().repository_mode == "json"

    get_settings.cache_clear()


def test_repository_mode_prefers_lingualens_prefix(monkeypatch):
    monkeypatch.setenv("LINGUALENS_REPOSITORY_MODE", "sql")
    monkeypatch.setenv("THERAPIST_APP_V2_REPOSITORY_MODE", "memory")
    monkeypatch.setenv("LINGUALENS_DATABASE_URL", "sqlite:///./compat-preferred.db")
    monkeypatch.setenv("THERAPIST_APP_V2_DATABASE_URL", "sqlite:///./compat-legacy.db")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.repository_mode == "sql"
    assert settings.database_url == "sqlite:///./compat-preferred.db"

    get_settings.cache_clear()


def test_repository_mode_falls_back_to_therapist_prefix(monkeypatch):
    monkeypatch.delenv("LINGUALENS_REPOSITORY_MODE", raising=False)
    monkeypatch.delenv("LINGUALENS_DATABASE_URL", raising=False)
    monkeypatch.setenv("THERAPIST_APP_V2_REPOSITORY_MODE", "memory")
    monkeypatch.setenv("THERAPIST_APP_V2_DATABASE_URL", "sqlite:///./compat-fallback.db")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.repository_mode == "memory"
    assert settings.database_url == "sqlite:///./compat-fallback.db"

    get_settings.cache_clear()


def test_auth_mode_prefers_lingualens_prefix(monkeypatch):
    monkeypatch.setenv("LINGUALENS_AUTH_MODE", "supabase")
    monkeypatch.setenv("THERAPIST_APP_V2_AUTH_MODE", "mock")
    monkeypatch.setenv("LINGUALENS_MOCK_MODE", "true")
    get_settings.cache_clear()

    assert get_settings().auth_mode == "supabase"

    get_settings.cache_clear()


def test_debug_feature_override_falls_back_to_therapist_prefix(monkeypatch):
    monkeypatch.delenv("LINGUALENS_DEBUG_FEATURE_OVERRIDE", raising=False)
    monkeypatch.setenv("THERAPIST_APP_V2_DEBUG_FEATURE_OVERRIDE", "true")
    get_settings.cache_clear()

    assert get_settings().debug_feature_override is True

    get_settings.cache_clear()


def test_legacy_repository_mode_env_emits_deprecation_warning(monkeypatch):
    monkeypatch.delenv("LINGUALENS_REPOSITORY_MODE", raising=False)
    monkeypatch.setenv("THERAPIST_APP_V2_REPOSITORY_MODE", "memory")
    get_settings.cache_clear()

    with pytest.warns(DeprecationWarning, match="THERAPIST_APP_V2_REPOSITORY_MODE"):
        assert get_settings().repository_mode == "memory"

    get_settings.cache_clear()


def test_lingualens_repository_mode_env_does_not_emit_deprecation_warning(monkeypatch):
    monkeypatch.setenv("LINGUALENS_REPOSITORY_MODE", "memory")
    monkeypatch.delenv("THERAPIST_APP_V2_REPOSITORY_MODE", raising=False)
    get_settings.cache_clear()

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        assert get_settings().repository_mode == "memory"

    assert not [warning for warning in recorded if warning.category is DeprecationWarning]

    get_settings.cache_clear()


def test_env_example_defaults_repository_mode_to_json():
    env_example = (repo_root() / ".env.example").read_text(encoding="utf-8")

    assert "LINGUALENS_REPOSITORY_MODE=json" in env_example
    assert "LINGUALENS_REPOSITORY_MODE=memory" not in env_example


def test_case_session_transcript_feature_report_workflow():
    case_response = client.post(
        "/api/v1/cases",
        json={"child_code": "C-2001", "age_months": 54, "language": "English", "consent_status": "granted"},
    )
    assert case_response.status_code == 200
    case_id = case_response.json()["case_id"]

    session_response = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-13", "session_type": "therapy_session"},
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]

    goal_response = client.post(
        f"/api/v1/cases/{case_id}/goals",
        json={"title": "Increase reciprocal turns", "target": "Use reviewed transcript samples across sessions.", "notes": "Caregiver-prioritized goal."},
    )
    assert goal_response.status_code == 200
    assert goal_response.json()["status"] == "active"

    cha = "\n".join(
        [
            "@Begin",
            "@Languages:\teng",
            "@Participants:\tCHI Child Target_Child, THER Therapist Investigator",
            "*THER:\twhat do you see ?",
            "*CHI:\tI see a red car .",
            "*THER:\ttell me more .",
            "*CHI:\tthe car goes fast .",
            "*CHI:\tI want car again .",
            "@End",
        ]
    )
    transcript_response = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/upload-cha",
        json={"filename": "sample.cha", "cha_text": cha},
    )
    assert transcript_response.status_code == 200
    transcript_id = transcript_response.json()["transcript_id"]

    blocked = client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})
    assert blocked.status_code == 400

    qa_response = client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    assert qa_response.status_code == 200
    assert qa_response.json()["overall_status"] in {"PASS", "WARNING"}

    attest_response = client.post(
        f"/api/v1/transcripts/{transcript_id}/attest",
        json={"reason": "Reviewed sample for demo."},
    )
    assert attest_response.status_code == 200
    assert attest_response.json()["therapist_attested"] is True

    features_response = client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})
    assert features_response.status_code == 200
    assert any(item["name"] == "mean_length_of_utterance_words" for item in features_response.json()["features"])
    feature_set_id = features_response.json()["feature_set_id"]
    feature_schema_version = features_response.json()["schema_version"]

    ai_response = client.post(f"/api/v1/sessions/{session_id}/ai-review")
    assert ai_response.status_code == 200
    assert ai_response.json()["requires_therapist_review"] is True
    assert ai_response.json()["input_transcript_version"] == attest_response.json()["version"]
    assert ai_response.json()["feature_set_id"] == feature_set_id
    assert ai_response.json()["feature_schema_version"] == feature_schema_version
    assistance_areas = {area["area"]: area for area in ai_response.json()["assistance_areas"]}
    assert set(assistance_areas) == {
        "Transcript QA Assistant",
        "Feature Explanation Assistant",
        "Review Priority",
        "Progress Summary",
        "Report Drafting",
    }
    assert "MLU" in assistance_areas["Feature Explanation Assistant"]["summary"]
    assert "TTR" in assistance_areas["Feature Explanation Assistant"]["summary"]
    assert "NDW" in assistance_areas["Feature Explanation Assistant"]["summary"]
    assert "raw model probability" in assistance_areas["Review Priority"]["summary"]
    ai_review_id = ai_response.json()["ai_review_id"]

    edited_ai = client.patch(
        f"/api/v1/ai-reviews/{ai_review_id}",
        json={
            "summary": "Therapist-edited decision-support summary.",
            "therapist_review_status": "Attested",
            "therapist_notes": "Reviewed and edited before report draft.",
        },
    )
    assert edited_ai.status_code == 200
    assert edited_ai.json()["summary"] == "Therapist-edited decision-support summary."
    assert edited_ai.json()["therapist_review_status"] == "Attested"

    report_response = client.post(f"/api/v1/sessions/{session_id}/reports/draft", json={})
    assert report_response.status_code == 200
    report_id = report_response.json()["report_id"]
    assert "Increase reciprocal turns" in report_response.json()["markdown"]
    assert "## AI-Assisted Summary" in report_response.json()["markdown"]
    assert "### AI Assistance Areas" in report_response.json()["markdown"]
    assert "Feature Explanation Assistant" in report_response.json()["markdown"]

    edited_report = client.patch(
        f"/api/v1/reports/{report_id}",
        json={
            "title": "Edited Session Review Report",
            "markdown": report_response.json()["markdown"] + "\n\n## Therapist Edit\n- Reviewed for decision-support wording only.",
        },
    )
    assert edited_report.status_code == 200
    assert edited_report.json()["title"] == "Edited Session Review Report"
    assert "Reviewed for decision-support wording only" in edited_report.json()["markdown"]

    sign_response = client.post(f"/api/v1/reports/{report_id}/sign-off", json={"signed_by": "Demo Therapist"})
    assert sign_response.status_code == 200
    assert sign_response.json()["status"] == "Signed Off"
    get_repository_singleton().reports[report_id].generated_from_versions.pop("transcript_version", None)

    locked_edit = client.patch(
        f"/api/v1/reports/{report_id}",
        json={
            "markdown": "# Changed after finalization\n\nDecision-support only. Not diagnostic. Therapist review required.\n\n## Limitations\nSome limitations.",
        },
    )
    assert locked_edit.status_code == 200
    revision = locked_edit.json()
    assert revision["report_id"] != report_id
    assert revision["supersedes_report_id"] == report_id
    assert revision["revision_number"] == sign_response.json()["revision_number"] + 1
    assert revision["status"] == "Draft"
    assert revision["signed_snapshot_hash"] is None
    assert revision["generated_from_versions"]["transcript_version"] == str(attest_response.json()["version"])
    original_after_revision = client.get(f"/api/v1/reports/{report_id}").json()
    assert original_after_revision["status"] == "Signed Off"
    assert original_after_revision["signed_snapshot_hash"] == sign_response.json()["signed_snapshot_hash"]
    assert original_after_revision["markdown"] == sign_response.json()["markdown"]

    export_response = client.get(f"/api/v1/reports/{report_id}/export?format=markdown")
    assert export_response.status_code == 200
    assert export_response.json()["format"] == "markdown"
    assert export_response.json()["filename"] == f"{report_id}.md"
    assert "Signed by: Demo Therapist" in export_response.json()["content"]

    current_transcript = client.get(f"/api/v1/transcripts/{transcript_id}").json()
    current_transcript["utterances"][0]["text"] = "Changed after signed legacy revision."
    assert client.patch(
        f"/api/v1/transcripts/{transcript_id}",
        json={"utterances": current_transcript["utterances"], "reviewer_note": "Invalidate legacy revision inputs."},
    ).status_code == 200
    blocked_legacy_revision = client.patch(
        f"/api/v1/reports/{report_id}",
        json={"markdown": "# Must remain blocked"},
    )
    assert blocked_legacy_revision.status_code == 400
    assert "stale" in blocked_legacy_revision.json()["detail"].lower()


def test_feature_extraction_calculates_phase5_core_metrics():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-FEATURE-METRICS", "age_months": 54, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-07-02", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: red car\nCHI: blue car\nCHI: car go\nTHER: tell me more\nUNK: background noise", "language": "English"},
    ).json()
    utterances = transcript["utterances"]
    utterances[1]["unintelligible"] = True
    patched = client.patch(
        f"/api/v1/transcripts/{transcript['transcript_id']}",
        json={"utterances": utterances, "reviewer_note": "Mark unintelligible for metric test."},
    )
    assert patched.status_code == 200
    client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/qa")
    client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/attest", json={"reason": "Reviewed for feature metric test."})

    features = client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/extract-features", json={})

    assert features.status_code == 200
    values = feature_map(features.json())
    assert values["total_utterance_count"] == 5
    assert values["child_utterance_count"] == 3
    assert values["adult_utterance_count"] == 1
    assert values["total_word_count"] == 6
    assert values["number_of_different_words"] == 4
    assert values["type_token_ratio"] == 0.6667
    assert values["mean_length_of_utterance_words"] == 2.0
    assert values["unintelligible_ratio"] == 0.2
    assert values["unknown_speaker_ratio"] == 0.2
    assert values["question_ratio"] == 0
    assert values["repetition_marker_count"] == 0
    assert values["echolalia_cue_count"] == 0
    assert values["pronoun_reversal_cue_count"] == 0
    assert features.json()["transcript_version"] == patched.json()["version"]


def test_ml_review_uses_features_without_diagnostic_output():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-ML-SUPPORT", "age_months": 54, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-07-03", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "THER: what do you see?\nCHI: blue car car\nCHI: I see blue car\nCHI: what is that?", "language": "English"},
    ).json()
    client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/qa")
    client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/attest", json={"reason": "Reviewed for ML support test."})
    client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/extract-features", json={})

    readiness = client.get(f"/api/v1/transcripts/{transcript['transcript_id']}/ml-readiness")
    assert readiness.status_code == 200
    assert readiness.json()["ready"] is True

    response = client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/ml-review")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["cues"]
    assert payload["not_diagnostic"] is True
    assert payload["decision_support_only"] is True
    assert payload["provider_id"] == "rule_based_review_cue"
    assert payload["input_feature_hash"]
    assert client.get(f"/api/v1/sessions/{session_id}/ml-review").json()["result_id"] == payload["result_id"]
    assert client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/ml-review").json()["result_id"] == payload["result_id"]
    serialized = str(payload).lower()
    assert "asd positive" not in serialized
    assert "asd negative" not in serialized
    assert "probability of asd" not in serialized


def test_ml_readiness_blocks_unattested_transcript_without_persisting_result():
    case_id = client.post("/api/v1/cases", json={"child_code": "C-ML-LOCK", "age_months": 54}).json()["case_id"]
    session_id = client.post(f"/api/v1/cases/{case_id}/sessions", json={"session_date": "2026-07-04"}).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: hello\nCHI: more\nCHI: play"},
    ).json()["transcript_id"]
    result_count = len(get_repository_singleton().ml_results)
    response = client.post(f"/api/v1/transcripts/{transcript_id}/ml-review")
    assert response.status_code == 409
    assert "transcript_requires_review" in response.json()["detail"]["reason_codes"]
    assert len(get_repository_singleton().ml_results) == result_count


def test_ml_provider_registry_keeps_research_classifier_unavailable():
    assert ml_provider_registry.get_default().provider_name == "RuleBasedReviewCueProvider"
    assert {provider.provider_id for provider in ml_provider_registry.list_supported()} >= {
        "rule_based_review_cue",
        "baseline_research_classifier",
        "future_ml_provider",
    }
    assert [provider.provider_id for provider in ml_provider_registry.list_available()] == ["rule_based_review_cue"]
    providers = client.get("/api/v1/ml/providers").json()
    rule_based = next(item for item in providers if item["provider_id"] == "rule_based_review_cue")
    classifier = next(item for item in providers if item["provider_id"] == "baseline_research_classifier")
    assert rule_based["available"] is True
    assert classifier["available"] is False
    assert "provenance" in classifier["unavailable_reason"].lower()


def test_ml_unavailable_provider_returns_readiness_conflict_without_fallback():
    case_id = client.post("/api/v1/cases", json={"child_code": "C-ML-PROVIDER", "age_months": 54}).json()["case_id"]
    session_id = client.post(f"/api/v1/cases/{case_id}/sessions", json={"session_date": "2026-07-05"}).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "THER: tell me\nCHI: blue car\nCHI: more car\nCHI: car car"},
    ).json()["transcript_id"]
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed."})
    client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})
    before = len(get_repository_singleton().ml_results)
    response = client.post(
        f"/api/v1/transcripts/{transcript_id}/ml-review",
        json={"provider_id": "baseline_research_classifier"},
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["provider_id"] == "baseline_research_classifier"
    assert "ml_provider_unavailable" in detail["reason_codes"]
    assert len(get_repository_singleton().ml_results) == before


def test_ml_unknown_provider_is_structured_conflict_without_silent_fallback():
    repo = get_repository_singleton()
    transcript_id = next(
        transcript.transcript_id
        for transcript in repo.transcripts.values()
        if transcript.therapist_attested and repo.sessions[transcript.session_id].feature_set_id
    )
    before = len(repo.ml_results)
    response = client.post(
        f"/api/v1/transcripts/{transcript_id}/ml-review",
        json={"provider_id": "unknown-provider"},
    )
    assert response.status_code == 409
    assert "ml_provider_unsupported" in response.json()["detail"]["reason_codes"]
    assert len(repo.ml_results) == before


def test_ml_readiness_blocks_persisted_feature_set_with_required_value_missing():
    repo = get_repository_singleton()
    transcript = next(
        transcript
        for transcript in repo.transcripts.values()
            if transcript.therapist_attested
            and repo.sessions[transcript.session_id].feature_set_id
            and repo.features[repo.sessions[transcript.session_id].feature_set_id].review_status == ReviewStatus.ready
            and repo.features[repo.sessions[transcript.session_id].feature_set_id].transcript_version == transcript.version
        )
    feature_set = repo.features[repo.sessions[transcript.session_id].feature_set_id]
    original = list(feature_set.features)
    feature_set.features = [item for item in feature_set.features if item.name != "total_word_count"]
    try:
        readiness = client.get(f"/api/v1/transcripts/{transcript.transcript_id}/ml-readiness")
        assert readiness.status_code == 200
        assert "required_features_missing" in readiness.json()["reason_codes"]
    finally:
        feature_set.features = original


def test_ml_readiness_blocks_needs_review_even_if_attestation_flag_is_inconsistent():
    repo = get_repository_singleton()
    transcript = next(iter(repo.transcripts.values()))
    original_attested = transcript.therapist_attested
    original_status = transcript.review_status
    transcript.therapist_attested = True
    transcript.review_status = ReviewStatus.needs_review
    try:
        readiness = client.get(f"/api/v1/transcripts/{transcript.transcript_id}/ml-readiness")
        assert readiness.status_code == 200
        assert "transcript_requires_review" in readiness.json()["reason_codes"]
    finally:
        transcript.therapist_attested = original_attested
        transcript.review_status = original_status


def test_ml_readiness_blocks_any_blocking_validation_issue():
    repo = get_repository_singleton()
    transcript = next(
        item for item in repo.transcripts.values()
        if item.therapist_attested and repo.sessions[item.session_id].feature_set_id
    )
    original_issues = list(transcript.qa_issues)
    transcript.qa_issues = [QaIssue(code="BLOCKING_TEST", severity="error", message="Blocking test issue.", blocking=True)]
    try:
        readiness = client.get(f"/api/v1/transcripts/{transcript.transcript_id}/ml-readiness")
        assert readiness.status_code == 200
        assert "blocking_chat_validation_errors" in readiness.json()["reason_codes"]
    finally:
        transcript.qa_issues = original_issues


def test_consent_withdrawal_unlinks_case_records():
    response = client.post(
        "/api/v1/cases/case_demo_001/withdraw-consent",
        json={"reason": "Guardian request", "redact_notes": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Withdrawn"
    assert "sessions" in body["affected_records"]


def test_consent_withdrawal_updates_therapy_goals_and_redacts_notes():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-GOAL-WD", "age_months": 55, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    goal = client.post(
        f"/api/v1/cases/{case_id}/goals",
        json={"title": "Expand comments", "target": "Increase spontaneous comments.", "notes": "Private caregiver note."},
    ).json()

    withdrawn = client.post(
        f"/api/v1/cases/{case_id}/withdraw-consent",
        json={"reason": "Guardian request", "redact_notes": True},
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["affected_records"]["therapy_goals"] == 1

    goals = client.get(f"/api/v1/cases/{case_id}/goals")
    assert goals.status_code == 200
    [updated_goal] = [item for item in goals.json() if item["goal_id"] == goal["goal_id"]]
    assert updated_goal["status"] == "withdrawn"
    assert updated_goal["retained"] is False
    assert updated_goal["notes"] == ""


def test_consent_withdrawal_blocks_new_workflow_actions():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-WD-BLOCK", "age_months": 56, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-22", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: I see car\nCHI: more car\nCHI: car fast\nTHER: tell me more", "language": "English"},
    ).json()["transcript_id"]
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed before withdrawal."})
    feature_set_id = client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={}).json()["feature_set_id"]
    report_id = client.post(f"/api/v1/sessions/{session_id}/reports/draft", json={}).json()["report_id"]

    withdrawn = client.post(
        f"/api/v1/cases/{case_id}/withdraw-consent",
        json={"reason": "Guardian request", "redact_notes": True},
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["affected_records"]["features"] >= 1

    blocked_requests = [
        client.post(f"/api/v1/cases/{case_id}/sessions", json={"session_date": "2026-06-23", "session_type": "therapy_session"}),
        client.patch(f"/api/v1/sessions/{session_id}", json={"session_type": "blocked_update"}),
        client.post(f"/api/v1/sessions/{session_id}/transcripts/manual", json={"text": "CHI: new text", "language": "English"}),
        client.post(f"/api/v1/sessions/{session_id}/audio/upload", json={"filename": "blocked.wav", "content_type": "audio/wav", "size_bytes": 1024}),
        client.post(f"/api/v1/sessions/{session_id}/audio/process", json={"provider": "manual", "draft_text": "CHI: blocked"}),
        client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={}),
        client.get(f"/api/v1/sessions/{session_id}/features"),
        client.post(f"/api/v1/sessions/{session_id}/reports/draft", json={}),
        client.get(f"/api/v1/reports/{report_id}/export?format=markdown"),
    ]
    for response in blocked_requests:
        assert response.status_code == 400
        assert "consent has been withdrawn" in response.json()["detail"]
    assert feature_set_id not in get_repository_singleton().features
    assert get_repository_singleton().sessions[session_id].feature_set_id is None


def test_feature_debug_override_requires_runtime_debug_mode(monkeypatch):
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-DEBUG-OFF", "age_months": 56, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-28", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "THER: tell me more", "language": "English"},
    ).json()["transcript_id"]
    qa = client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    assert qa.status_code == 200
    assert qa.json()["overall_status"] == "FAIL"

    monkeypatch.setenv("THERAPIST_APP_V2_DEBUG_FEATURE_OVERRIDE", "false")
    get_settings.cache_clear()

    blocked = client.post(
        f"/api/v1/transcripts/{transcript_id}/extract-features",
        json={"force_debug_override": True, "override_reason": "Engineering QA only."},
    )

    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "Feature extraction debug override is disabled in this runtime."

    monkeypatch.delenv("THERAPIST_APP_V2_DEBUG_FEATURE_OVERRIDE")
    get_settings.cache_clear()


def test_worker_cancels_queued_audio_job_after_consent_withdrawal():
    get_job_queue().clear()
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-WD-JOB", "age_months": 56, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-26", "session_type": "therapy_session"},
    ).json()["session_id"]
    process = client.post(
        f"/api/v1/sessions/{session_id}/audio/process",
        json={"provider": "manual", "draft_text": "THER: what do you see\nCHI: I see car", "duration_seconds": 30, "channels": 1},
    )
    assert process.status_code == 200
    job_id = process.json()["job_id"]

    withdrawn = client.post(
        f"/api/v1/cases/{case_id}/withdraw-consent",
        json={"reason": "Guardian request before worker ran", "redact_notes": True},
    )
    assert withdrawn.status_code == 200

    worker_result = run_worker_once()
    assert worker_result["job_status"] == "cancelled"
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "cancelled"
    assert job["error_code"] == "consent_withdrawn"
    assert "asr_draft" not in job["details"]
    transcript = client.get(f"/api/v1/sessions/{session_id}/transcript")
    assert transcript.status_code == 404


def test_ai_review_can_be_rejected_only_with_reason():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-AI-REJECT", "age_months": 54, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-19", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: I see car\nCHI: more car\nCHI: car fast", "language": "English"},
    ).json()["transcript_id"]
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed."})
    client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})
    review = client.post(f"/api/v1/sessions/{session_id}/ai-review").json()

    blocked = client.patch(
        f"/api/v1/ai-reviews/{review['ai_review_id']}",
        json={"therapist_review_status": "Withdrawn"},
    )
    assert blocked.status_code == 400

    rejected = client.patch(
        f"/api/v1/ai-reviews/{review['ai_review_id']}",
        json={"therapist_review_status": "Withdrawn", "rejected_reason": "Summary was not clinically useful."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["therapist_review_status"] == "Withdrawn"
    assert rejected.json()["rejected_reason"] == "Summary was not clinically useful."

    report = client.post(f"/api/v1/sessions/{session_id}/reports/draft", json={})
    assert report.status_code == 200
    assert "Summary was not clinically useful" not in report.json()["markdown"]
    assert "was rejected or withdrawn by the therapist" in report.json()["markdown"]


def test_asr_evaluation_metrics():
    response = client.post(
        "/api/v1/evaluation/asr",
        json={
            "reference_text": "*CHI:\tI see car .",
            "hypothesis_text": "*CHI:\tI see a car .",
            "reference_speakers": ["CHI"],
            "hypothesis_speakers": ["CHI"],
            "audio_duration_seconds": 10,
            "transcribed_duration_seconds": 8,
        },
    )
    assert response.status_code == 200
    assert response.json()["coverage"] == 0.8
    assert response.json()["speaker_accuracy"] == 1.0


def test_asr_dataset_evaluation_endpoint(tmp_path):
    dataset = tmp_path / "evaluation"
    gold = dataset / "gold_transcripts"
    hypotheses = dataset / "hypothesis_transcripts"
    audio = dataset / "audio_samples"
    gold.mkdir(parents=True)
    hypotheses.mkdir()
    audio.mkdir()
    (gold / "sample_001.cha").write_text("*CHI:\tI see car .\n*THER:\ttell me more .\n", encoding="utf-8")
    (hypotheses / "sample_001.cha").write_text("*CHI:\tI see a car .\n*THER:\ttell me more .\n", encoding="utf-8")
    (audio / "sample_001.wav").write_text("placeholder only", encoding="utf-8")

    response = client.post("/api/v1/evaluation/asr-dataset", json={"dataset_dir": str(dataset)})

    assert response.status_code == 200
    body = response.json()
    assert body["sample_count"] == 1
    assert body["samples"][0]["sample_id"] == "sample_001"
    assert body["samples"][0]["audio_present"] is True
    assert body["aggregate_metrics"]["speaker_accuracy"] == 1.0


def test_transcript_split_merge_and_export_cha():
    case_response = client.post(
        "/api/v1/cases",
        json={"child_code": "C-3001", "age_months": 60, "language": "English", "consent_status": "granted"},
    )
    case_id = case_response.json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-14", "session_type": "assessment"},
    ).json()["session_id"]
    transcript = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: I see red car and blue truck\nCHI: more truck please\nTHER: tell me more", "language": "English"},
    ).json()
    transcript_id = transcript["transcript_id"]
    first_utterance_id = transcript["utterances"][0]["utterance_id"]

    split_response = client.post(
        f"/api/v1/transcripts/{transcript_id}/split",
        json={"utterance_id": first_utterance_id, "split_at_character": 14},
    )
    assert split_response.status_code == 200
    split_body = split_response.json()
    assert len(split_body["utterances"]) == 4
    assert split_body["therapist_attested"] is False

    merge_response = client.post(
        f"/api/v1/transcripts/{transcript_id}/merge",
        json={
            "first_utterance_id": split_body["utterances"][0]["utterance_id"],
            "second_utterance_id": split_body["utterances"][1]["utterance_id"],
        },
    )
    assert merge_response.status_code == 200
    assert len(merge_response.json()["utterances"]) == 3

    export_response = client.get(f"/api/v1/transcripts/{transcript_id}/export-cha")
    assert export_response.status_code == 200
    assert "@Begin" in export_response.json()["cha_text"]
    assert "*CHI:" in export_response.json()["cha_text"]


def test_transcript_edit_invalidates_attestation_and_downstream_outputs():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-STALE", "age_months": 60, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-07-01", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: I see car\nCHI: more car\nCHI: car fast\nTHER: tell me more", "language": "English"},
    ).json()
    transcript_id = transcript["transcript_id"]
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    attested = client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed before edit."}).json()
    features = client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={}).json()
    ml_result = client.post(f"/api/v1/transcripts/{transcript_id}/ml-review").json()
    from app.schemas.clinical import EvidenceAvailability, ProfileEvidence, ReviewCue
    persisted_ml_result = get_repository_singleton().ml_results[ml_result["result_id"]]
    persisted_ml_result.cues.append(ReviewCue(
        cue_code="stale-mutation-gate",
        severity="review",
        title="Fixture review cue",
        explanation="Fixture cue used only to verify the stale mutation gate.",
        recommended_next_review_step="Regenerate current findings.",
    ))
    persisted_ml_result.profile_evidence = [ProfileEvidence(
        profile_code="TD",
        presentation_group="TD",
        status="not_available",
        availability=EvidenceAvailability(
            state="system_unavailable",
            message="Fixture profile for stale mutation gate.",
            workflow_can_continue=True,
        ),
        participant_count=0,
        corpus_count=0,
    )]
    ai_review = client.post(f"/api/v1/sessions/{session_id}/ai-review").json()
    report = client.post(f"/api/v1/sessions/{session_id}/reports/draft", json={}).json()

    assert client.post(f"/api/v1/transcripts/{transcript_id}/qa").status_code == 200
    assert client.post(
        f"/api/v1/transcripts/{transcript_id}/attest",
        json={"reason": "Metadata-only re-attestation must preserve derived outputs."},
    ).status_code == 200
    preserved_session = get_repository_singleton().sessions[session_id]
    assert preserved_session.feature_set_id == features["feature_set_id"]
    assert preserved_session.ml_result_id == ml_result["result_id"]
    assert preserved_session.ai_review_id == ai_review["ai_review_id"]
    assert preserved_session.report_id == report["report_id"]
    assert client.get(f"/api/v1/sessions/{session_id}/features").json()["review_status"] == "Ready"
    assert client.get(f"/api/v1/sessions/{session_id}/ml-review").status_code == 200
    assert client.get(f"/api/v1/sessions/{session_id}/ai-review").json()["therapist_review_status"] != "stale"
    assert client.get(f"/api/v1/reports/{report['report_id']}").json()["status"] == "Draft"

    patched_utterances = transcript["utterances"]
    patched_utterances[0]["text"] = "I see a red car"
    patched = client.patch(
        f"/api/v1/transcripts/{transcript_id}",
        json={"utterances": patched_utterances, "reviewer_note": "Edited after outputs were generated."},
    )

    assert patched.status_code == 200
    body = patched.json()
    assert body["version"] == attested["version"] + 1
    assert body["qa_status"] == "NOT_RUN"
    assert body["qa_issues"] == []
    assert body["therapist_attested"] is False

    session = get_repository_singleton().sessions[session_id]
    assert session.feature_set_id == features["feature_set_id"]
    assert session.ai_review_id == ai_review["ai_review_id"]
    assert session.report_id == report["report_id"]
    assert features["feature_set_id"] in get_repository_singleton().features
    assert ai_review["ai_review_id"] in get_repository_singleton().ai_reviews
    assert report["report_id"] in get_repository_singleton().reports

    stale_features = client.get(f"/api/v1/sessions/{session_id}/features")
    assert stale_features.status_code == 200
    assert stale_features.json()["review_status"] == "stale"
    stale_ai = client.get(f"/api/v1/sessions/{session_id}/ai-review")
    assert stale_ai.status_code == 200
    assert stale_ai.json()["therapist_review_status"] == "stale"
    stale_report = client.get(f"/api/v1/reports/{report['report_id']}")
    assert stale_report.status_code == 200
    assert stale_report.json()["status"] == "stale"
    assert stale_report.json()["version"] == report["version"] + 1
    stale_ai_patch = client.patch(
        f"/api/v1/ai-reviews/{ai_review['ai_review_id']}",
        json={"therapist_review_status": "Attested"},
    )
    assert stale_ai_patch.status_code == 400
    assert "stale" in stale_ai_patch.json()["detail"].lower()
    stale_cue_patch = client.patch(
        f"/api/v1/ml-results/{ml_result['result_id']}/cues/stale-mutation-gate",
        json={"status": "acknowledged"},
    )
    assert stale_cue_patch.status_code == 404
    assert "stale" in stale_cue_patch.json()["detail"].lower()
    stale_profile_patch = client.patch(
        f"/api/v1/ml-results/{ml_result['result_id']}/profiles/TD/review-state",
        json={"status": "reviewed", "therapist_note": "Must not persist."},
    )
    assert stale_profile_patch.status_code == 404
    assert "stale" in stale_profile_patch.json()["detail"].lower()
    assert persisted_ml_result.profile_evidence[0].review_state.status == "unreviewed"
    signoff = client.post(f"/api/v1/reports/{report['report_id']}/sign-off", json={"signed_by": "Demo Therapist"})
    assert signoff.status_code == 400
    assert "stale" in signoff.json()["detail"]
def test_feature_extraction_rejects_transcript_change_during_provider_work(monkeypatch):
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-RACE", "age_months": 60, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-07-05", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: one\nCHI: two\nCHI: three", "language": "English"},
    ).json()["transcript_id"]
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed before race."})

    provider = __import__("app.services.feature_service", fromlist=["provider_registry"]).provider_registry.get_default()
    original_extract = provider.extract_features

    def edit_during_extraction(transcript):
        result = original_extract(transcript)
        repo = get_repository_singleton()
        repo.transcripts[transcript_id].version += 1
        repo.transcripts[transcript_id].therapist_attested = False
        return result

    monkeypatch.setattr(provider, "extract_features", edit_during_extraction)
    response = client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})

    assert response.status_code == 400
    assert "changed during feature extraction" in response.json()["detail"].lower()
    assert get_repository_singleton().sessions[session_id].feature_set_id is None


def test_report_generation_rejects_transcript_change_during_provider_work(monkeypatch):
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-REPORT-RACE", "age_months": 60, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-07-05", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: one\nCHI: two\nCHI: three", "language": "English"},
    ).json()["transcript_id"]
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed before report race."})
    client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})

    registry = __import__("app.services.report_service", fromlist=["report_provider_registry"]).report_provider_registry
    provider = registry.get("template")
    original_generate = provider.generate_report

    def edit_during_report_generation(input_data, config):
        result = original_generate(input_data, config)
        get_repository_singleton().transcripts[transcript_id].version += 1
        return result

    monkeypatch.setattr(provider, "generate_report", edit_during_report_generation)
    response = client.post(f"/api/v1/sessions/{session_id}/reports/draft", json={})

    assert response.status_code == 400
    assert "changed during report generation" in response.json()["detail"].lower()
    assert get_repository_singleton().sessions[session_id].report_id is None


def test_ai_and_ml_creation_cannot_repoint_after_transcript_edit(monkeypatch):
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-DERIVED-RACE", "age_months": 60, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-07-05", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: one\nCHI: two\nCHI: three", "language": "English"},
    ).json()["transcript_id"]
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed before derived race."})
    client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})
    repo = get_repository_singleton()

    original_create_ai = repo.create_ai_review
    def edit_before_ai_create(review, **kwargs):
        repo.transcripts[transcript_id].version += 1
        return original_create_ai(review, **kwargs)
    monkeypatch.setattr(repo, "create_ai_review", edit_before_ai_create)
    ai_response = client.post(f"/api/v1/sessions/{session_id}/ai-review")
    assert ai_response.status_code == 400
    assert repo.sessions[session_id].ai_review_id is None

    repo.transcripts[transcript_id].version -= 1
    original_create_ml = repo.create_ml_result
    def edit_before_ml_create(result, **kwargs):
        repo.transcripts[transcript_id].version += 1
        return original_create_ml(result, **kwargs)
    monkeypatch.setattr(repo, "create_ml_result", edit_before_ml_create)
    ml_response = client.post(f"/api/v1/transcripts/{transcript_id}/ml-review")
    assert ml_response.status_code == 409 or ml_response.status_code == 400
    assert repo.sessions[session_id].ml_result_id is None


def test_ai_and_ml_readiness_reject_feature_transcript_version_mismatch():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-VERSION-GATE", "age_months": 60, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-07-06", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: one\nCHI: two\nCHI: three", "language": "English"},
    ).json()["transcript_id"]
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed for version gate."})
    feature_set_id = client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={}).json()["feature_set_id"]
    repo = get_repository_singleton()
    transcript = repo.transcripts[transcript_id]
    feature_set = repo.features[feature_set_id]
    original_feature_transcript_version = feature_set.transcript_version
    feature_set.transcript_version = transcript.version - 1
    try:
        readiness = client.get(f"/api/v1/transcripts/{transcript_id}/ml-readiness")
        ai_review = client.post(f"/api/v1/sessions/{session_id}/ai-review")

        assert readiness.status_code == 200
        assert readiness.json()["ready"] is False
        assert "feature_transcript_version_mismatch" in readiness.json()["reason_codes"]
        assert ai_review.status_code == 400
        assert "transcript version" in ai_review.json()["detail"].lower()
    finally:
        feature_set.transcript_version = original_feature_transcript_version


def test_transcript_replacement_invalidates_downstream_outputs():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-REPLACE", "age_months": 60, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-07-03", "session_type": "therapy_session"},
    ).json()["session_id"]
    first_transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: I see car\nCHI: more car\nCHI: car fast\nTHER: tell me more", "language": "English"},
    ).json()["transcript_id"]
    client.post(f"/api/v1/transcripts/{first_transcript_id}/qa")
    client.post(f"/api/v1/transcripts/{first_transcript_id}/attest", json={"reason": "Reviewed before replacement."})
    feature_set_id = client.post(f"/api/v1/transcripts/{first_transcript_id}/extract-features", json={}).json()["feature_set_id"]
    ai_review_id = client.post(f"/api/v1/sessions/{session_id}/ai-review").json()["ai_review_id"]
    report_id = client.post(f"/api/v1/sessions/{session_id}/reports/draft", json={}).json()["report_id"]

    replacement = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={
            "text": "CHI: replacement sample\nCHI: more sample\nCHI: sample done",
            "language": "English",
            "replace_existing": True,
        },
    )

    assert replacement.status_code == 200
    assert replacement.json()["transcript_id"] != first_transcript_id
    session = get_repository_singleton().sessions[session_id]
    assert session.transcript_id == replacement.json()["transcript_id"]
    assert session.feature_set_id == feature_set_id
    assert session.ai_review_id == ai_review_id
    assert session.report_id == report_id
    assert feature_set_id in get_repository_singleton().features
    assert ai_review_id in get_repository_singleton().ai_reviews
    assert report_id in get_repository_singleton().reports
    assert client.get(f"/api/v1/sessions/{session_id}/features").json()["review_status"] == "stale"
    assert client.get(f"/api/v1/sessions/{session_id}/ai-review").json()["therapist_review_status"] == "stale"
    assert client.get(f"/api/v1/reports/{report_id}").json()["status"] == "stale"
    assert client.post(f"/api/v1/reports/{report_id}/sign-off", json={"signed_by": "Demo Therapist"}).status_code == 400


def test_transcript_creation_reuses_active_session_transcript_by_default():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-RETRY", "age_months": 60, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-07-04", "session_type": "therapy_session"},
    ).json()["session_id"]
    first = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: first sample", "language": "English"},
    ).json()

    retry = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: accidental retry", "language": "English"},
    )

    assert retry.status_code == 200
    assert retry.json()["transcript_id"] == first["transcript_id"]
    assert retry.json()["raw_text"] == first["raw_text"]


def test_report_draft_creation_reuses_active_draft_by_default():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-REPORT-RETRY", "age_months": 60, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-07-04", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: first sample\nCHI: more words\nCHI: sample done", "language": "English"},
    ).json()["transcript_id"]
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed."})
    features = client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})
    assert features.status_code == 200
    first_response = client.post(f"/api/v1/sessions/{session_id}/reports/draft", json={})
    assert first_response.status_code == 200
    first = first_response.json()

    retry = client.post(f"/api/v1/sessions/{session_id}/reports/draft", json={})

    assert retry.status_code == 200
    assert retry.json()["report_id"] == first["report_id"]


def test_transcript_qa_warns_on_unsupported_language_metadata():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-LANG", "age_months": 52, "language": "Spanish", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-27", "session_type": "therapy_session"},
    ).json()["session_id"]
    cha = "\n".join(
        [
            "@Begin",
            "@Languages:\tspa",
            "@Participants:\tCHI Child Target_Child, THER Therapist Investigator",
            "*CHI:\tveo un carro rojo .",
            "*CHI:\tquiero mas carro .",
            "*CHI:\tel carro va rapido .",
            "@End",
        ]
    )
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/upload-cha",
        json={"filename": "unsupported-language.cha", "cha_text": cha},
    ).json()["transcript_id"]

    qa = client.post(f"/api/v1/transcripts/{transcript_id}/qa")

    assert qa.status_code == 200
    assert any(issue["code"] == "UNSUPPORTED_LANGUAGE" for issue in qa.json()["issues"])


def test_transcript_qa_warns_on_code_switching_without_language_metadata():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-CODE-SWITCH", "age_months": 55, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-07-03", "session_type": "therapy_session"},
    ).json()["session_id"]
    cha = "\n".join(
        [
            "@Begin",
            "@Languages:\teng",
            "@Participants:\tCHI Child Target_Child, THER Therapist Investigator",
            "*CHI:\tI want รถ red .",
            "*CHI:\tmore car please .",
            "*CHI:\tgo fast .",
            "@End",
        ]
    )
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/upload-cha",
        json={"filename": "code-switch.cha", "cha_text": cha},
    ).json()["transcript_id"]

    qa = client.post(f"/api/v1/transcripts/{transcript_id}/qa")

    assert qa.status_code == 200
    assert any(issue["code"] == "CODE_SWITCHING_WARNING" for issue in qa.json()["issues"])


def test_export_cha_includes_non_identifying_media_header_when_audio_is_linked():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-MEDIA", "age_months": 52, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-25", "session_type": "therapy_session"},
    ).json()["session_id"]
    upload = client.post(
        f"/api/v1/sessions/{session_id}/audio/upload",
        json={"filename": "family_sample.wav", "content_type": "audio/wav", "size_bytes": 2048, "duration_seconds": 30},
    )
    assert upload.status_code == 200
    audio_file_id = upload.json()["details"]["audio_file"]["audio_file_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: I see car\nCHI: more car\nCHI: car fast", "language": "English"},
    ).json()["transcript_id"]

    export_response = client.get(f"/api/v1/transcripts/{transcript_id}/export-cha")

    assert export_response.status_code == 200
    cha_text = export_response.json()["cha_text"]
    assert f"@Media:\t{session_id}_{audio_file_id}, audio" in cha_text
    assert "family_sample" not in cha_text


def test_json_file_repository_round_trip(tmp_path):
    path = tmp_path / "repository.json"
    repo = JsonFileRepository(path)
    repo.cases["case_json"] = repo.cases["case_demo_001"].model_copy(update={"case_id": "case_json"})
    repo.add_audit("test.persist", "case_json", "Persisted test case.")

    restored = JsonFileRepository(path)
    assert "case_json" in restored.cases
    assert any(item["action"] == "test.persist" for item in restored.audit_log)


def test_json_repository_persists_full_workflow_across_repository_restart(tmp_path, monkeypatch):
    repository_path = tmp_path / "persistent-workflow.json"
    monkeypatch.setenv("THERAPIST_APP_V2_REPOSITORY_MODE", "json")
    monkeypatch.setenv("THERAPIST_APP_V2_JSON_REPOSITORY_PATH", str(repository_path))
    get_settings.cache_clear()
    get_repository_singleton.cache_clear()

    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-RESTART", "age_months": 60, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-19", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: blue car\nCHI: more car\nCHI: car goes fast", "language": "English"},
    ).json()["transcript_id"]
    client.patch(
        f"/api/v1/transcripts/{transcript_id}",
        json={"raw_text": "@Begin\n@Languages:\teng\n*CHI:\tblue truck\n*CHI:\tmore truck\n*CHI:\ttruck goes fast\n@End"},
    )
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed before restart."})
    client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})
    report_id = client.post(f"/api/v1/sessions/{session_id}/reports/draft", json={}).json()["report_id"]
    client.patch(f"/api/v1/reports/{report_id}", json={"markdown": "# Persisted report\n\nDecision-support only. Not diagnostic. Therapist review required.\n\n## Limitations\nNo limitations."})
    client.post(f"/api/v1/reports/{report_id}/sign-off", json={"signed_by": "Demo Therapist"})

    get_repository_singleton.cache_clear()

    restored_session = client.get(f"/api/v1/sessions/{session_id}").json()
    restored_transcript = client.get(f"/api/v1/transcripts/{transcript_id}").json()
    restored_report = client.get(f"/api/v1/reports/{report_id}").json()

    assert restored_session["transcript_id"] == transcript_id
    assert restored_session["report_id"] == report_id
    assert "blue truck" in restored_transcript["raw_text"]
    assert restored_transcript["therapist_attested"] is True
    assert restored_transcript["qa_status"] in {"PASS", "WARNING"}
    assert restored_report["status"] == "Signed Off"
    assert "Persisted report" in restored_report["markdown"]

    monkeypatch.setenv("THERAPIST_APP_V2_REPOSITORY_MODE", "memory")
    get_settings.cache_clear()
    get_repository_singleton.cache_clear()


def test_audio_process_creates_unreviewed_asr_draft_and_blocks_features():
    get_job_queue().clear()
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-4001", "age_months": 48, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-15", "session_type": "therapy_session"},
    ).json()["session_id"]

    upload = client.post(
        f"/api/v1/sessions/{session_id}/audio/upload",
        json={
            "filename": "session.wav",
            "content_type": "audio/wav",
            "size_bytes": 1024,
            "duration_seconds": 120,
            "sample_rate_hz": 16000,
            "channels": 1,
            "estimated_noise_level": 0.2,
            "silence_ratio": 0.1,
        },
    )
    assert upload.status_code == 200
    assert upload.json()["details"]["quality"]["status"] == "pass"

    process = client.post(
        f"/api/v1/sessions/{session_id}/audio/process",
        json={
            "provider": "manual",
            "draft_text": "THER: what do you see\nCHI: I see car",
            "duration_seconds": 120,
            "sample_rate_hz": 16000,
            "channels": 1,
        },
    )
    assert process.status_code == 200
    body = process.json()
    assert body["status"] == "queued"
    assert get_job_queue().size() == 1

    worker_result = run_worker_once()
    assert worker_result["status"] == "processed"
    processed = client.get(f"/api/v1/jobs/{body['job_id']}").json()
    assert processed["status"] == "needs_review"
    assert processed["details"]["status_history"] == ["queued", "processing", "transcription_completed", "needs_review"]
    assert "diarization failed" in processed["details"]["asr_draft"]["warnings"]
    assert processed["details"]["asr_draft"]["diarization_available"] is False
    transcript_id = processed["details"]["asr_draft"]["transcript_id"]

    transcript = client.get(f"/api/v1/sessions/{session_id}/transcript").json()
    assert transcript["source"] == "asr_draft:manual"
    assert transcript["therapist_attested"] is False
    assert any(item["speaker"] == "UNK" for item in transcript["utterances"])

    blocked = client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})
    assert blocked.status_code == 400


def test_audio_process_warns_when_no_child_speech_is_detected():
    get_job_queue().clear()
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-AUDIO-NO-CHI", "age_months": 48, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-30", "session_type": "therapy_session"},
    ).json()["session_id"]
    process = client.post(
        f"/api/v1/sessions/{session_id}/audio/process",
        json={
            "provider": "manual",
            "draft_text": "THER: tell me what happened",
            "duration_seconds": 30,
            "sample_rate_hz": 16000,
            "channels": 1,
        },
    )
    assert process.status_code == 200
    run_worker_once()
    processed = client.get(f"/api/v1/jobs/{process.json()['job_id']}").json()

    assert processed["status"] == "needs_review"
    assert "transcript too short" in processed["details"]["asr_draft"]["warnings"]
    assert "no child speech detected" in processed["details"]["asr_draft"]["warnings"]
    assert "diarization failed" in processed["details"]["asr_draft"]["warnings"]


def test_placeholder_asr_provider_failure_is_recorded_as_job_failure():
    get_job_queue().clear()
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-ASR-FAILED", "age_months": 48, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-07-01", "session_type": "therapy_session"},
    ).json()["session_id"]
    process = client.post(
        f"/api/v1/sessions/{session_id}/audio/process",
        json={
            "provider": "whisper",
            "duration_seconds": 30,
            "sample_rate_hz": 16000,
            "channels": 1,
        },
    )
    assert process.status_code == 200

    worker_result = run_worker_once()
    assert worker_result["job_status"] == "failed"
    failed = client.get(f"/api/v1/jobs/{process.json()['job_id']}").json()

    assert failed["status"] == "failed"
    assert failed["error_code"] == "asr_failed"
    assert failed["message"] == "ASR failed"
    assert failed["details"]["provider_error"] == "ASR failed"
    assert failed["details"]["status_history"] == ["queued", "processing", "failed"]


def test_audio_upload_creates_metadata_only_signed_intent_and_consent_withdrawal_unlinks_it():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-AUDIO-GOV", "age_months": 52, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-17", "session_type": "therapy_session"},
    ).json()["session_id"]

    upload = client.post(
        f"/api/v1/sessions/{session_id}/audio/upload",
        json={"filename": "governance.wav", "content_type": "audio/wav", "size_bytes": 2048, "duration_seconds": 30},
    )
    assert upload.status_code == 200
    details = upload.json()["details"]
    audio_file = details["audio_file"]
    audio_file_id = audio_file["audio_file_id"]
    assert audio_file["storage_mode"] == "local_private"
    assert audio_file["duration_seconds"] == 30
    assert audio_file["object_key"] is None
    stored_audio_file = get_repository_singleton().audio_files[audio_file_id]
    assert stored_audio_file.object_key is not None
    assert stored_audio_file.object_key.startswith("audio/obj_")
    assert "governance.wav" not in stored_audio_file.object_key
    assert case_id not in stored_audio_file.object_key
    assert session_id not in stored_audio_file.object_key
    raw_audio_key = "_".join(["audio", "bytes"])
    assert raw_audio_key not in details
    assert details["upload_intent"]["upload_url"] == f"/audio/{audio_file_id}/upload-file"
    assert details["upload_intent"]["required_headers"]["content-type"] == "audio/wav"
    put_resp = client.put(f"/api/v1{details['upload_intent']['upload_url']}", content=b"RIFFxxxxWAVE")
    assert put_resp.status_code == 200

    complete = client.post(
        f"/api/v1/audio/{audio_file_id}/complete-upload",
        json={"checksum_sha256": "0" * 64, "size_bytes": 2048},
    )
    assert complete.status_code == 200
    assert complete.json()["upload_status"] == "uploaded"
    assert complete.json()["object_key"] is None
    assert complete.json()["checksum_sha256"] == "0" * 64
    assert complete.json()["uploaded_at"] is not None

    withdrawn = client.post(
        f"/api/v1/cases/{case_id}/withdraw-consent",
        json={"reason": "Guardian withdrew audio consent", "redact_notes": True},
    )
    assert withdrawn.status_code == 200
    affected = withdrawn.json()["affected_records"]
    assert affected["audio_metadata"] == 1
    assert affected["jobs"] >= 1
    metadata = client.get(f"/api/v1/audio/{audio_file_id}")
    assert metadata.status_code == 200
    assert metadata.json()["retained"] is False
    assert metadata.json()["upload_status"] == "withdrawn"
    assert metadata.json()["object_key"] is None
    assert metadata.json()["storage_delete_status"] in {"metadata_only_no_object", "object_not_found", "deleted"}


def test_audio_process_blocks_second_active_job_for_same_uploaded_audio_artifact():
    get_job_queue().clear()
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-AUDIO-LOCK", "age_months": 52, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-22", "session_type": "therapy_session"},
    ).json()["session_id"]
    upload = client.post(
        f"/api/v1/sessions/{session_id}/audio/upload",
        json={"filename": "lock.wav", "content_type": "audio/wav", "size_bytes": 2048, "duration_seconds": 30},
    )
    assert upload.status_code == 200
    audio_file_id = upload.json()["details"]["audio_file"]["audio_file_id"]
    assert client.put(
        f"/api/v1{upload.json()['details']['upload_intent']['upload_url']}",
        content=b"RIFFlock",
    ).status_code == 200
    assert client.post(
        f"/api/v1/audio/{audio_file_id}/complete-upload",
        json={"checksum_sha256": "1" * 64, "size_bytes": 2048},
    ).status_code == 200

    first = client.post(
        f"/api/v1/sessions/{session_id}/audio/process",
        json={"audio_id": audio_file_id, "provider": "manual", "draft_text": "CHI: I see car"},
    )
    assert first.status_code == 200
    assert first.json()["details"]["audio_file_id"] == audio_file_id

    blocked = client.post(
        f"/api/v1/sessions/{session_id}/audio/process",
        json={"audio_id": audio_file_id, "provider": "manual", "draft_text": "CHI: I see car again"},
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "Only one active processing job is allowed per audio artifact."


def test_audio_process_rejects_unverified_audio_artifact():
    get_job_queue().clear()
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-AUDIO-UNVERIFIED", "age_months": 52, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-23", "session_type": "therapy_session"},
    ).json()["session_id"]
    upload = client.post(
        f"/api/v1/sessions/{session_id}/audio/upload",
        json={"filename": "unverified.wav", "content_type": "audio/wav", "size_bytes": 2048, "duration_seconds": 30},
    )
    assert upload.status_code == 200
    audio_file_id = upload.json()["details"]["audio_file"]["audio_file_id"]

    blocked = client.post(
        f"/api/v1/sessions/{session_id}/audio/process",
        json={"audio_id": audio_file_id, "provider": "manual", "draft_text": "CHI: pending verification"},
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "Audio processing requires a verified uploaded audio artifact."


def test_audio_reprocess_creates_new_job_after_prior_job_reaches_terminal_state():
    get_job_queue().clear()
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-AUDIO-REPROCESS", "age_months": 52, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-23", "session_type": "therapy_session"},
    ).json()["session_id"]
    upload = client.post(
        f"/api/v1/sessions/{session_id}/audio/upload",
        json={"filename": "reprocess.wav", "content_type": "audio/wav", "size_bytes": 2048, "duration_seconds": 30},
    )
    assert upload.status_code == 200
    upload_details = upload.json()["details"]
    audio_file_id = upload_details["audio_file"]["audio_file_id"]
    put_resp = client.put(f"/api/v1{upload_details['upload_intent']['upload_url']}", content=b"RIFFxxxxWAVE")
    assert put_resp.status_code == 200
    assert client.post(
        f"/api/v1/audio/{audio_file_id}/complete-upload",
        json={"checksum_sha256": "2" * 64, "size_bytes": 2048},
    ).status_code == 200

    first = client.post(
        f"/api/v1/sessions/{session_id}/audio/process",
        json={"audio_id": audio_file_id, "provider": "manual", "draft_text": "THER: what do you see\nCHI: I see car"},
    )
    assert first.status_code == 200
    run_worker_once()
    first_job = client.get(f"/api/v1/jobs/{first.json()['job_id']}").json()
    assert first_job["status"] == "needs_review"

    second = client.post(
        f"/api/v1/sessions/{session_id}/audio/process",
        json={"audio_id": audio_file_id, "provider": "manual", "draft_text": "THER: tell me more\nCHI: I see red car"},
    )
    assert second.status_code == 200
    assert second.json()["job_id"] != first.json()["job_id"]
    assert second.json()["details"]["audio_file_id"] == audio_file_id


def test_transcript_qa_warns_when_timestamps_cover_too_little_linked_audio():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-COVERAGE", "age_months": 52, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-21", "session_type": "therapy_session"},
    ).json()["session_id"]
    upload = client.post(
        f"/api/v1/sessions/{session_id}/audio/upload",
        json={"filename": "coverage.wav", "content_type": "audio/wav", "size_bytes": 2048, "duration_seconds": 120, "sample_rate_hz": 16000, "channels": 1},
    )
    assert upload.status_code == 200
    transcript = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: I see car\nCHI: more car\nCHI: car fast\nTHER: tell me more", "language": "English"},
    ).json()
    utterances = transcript["utterances"]
    for index, utterance in enumerate(utterances):
        utterance["start_ms"] = index * 2500
        utterance["end_ms"] = (index + 1) * 2500
    patched = client.patch(
        f"/api/v1/transcripts/{transcript['transcript_id']}",
        json={"utterances": utterances, "reviewer_note": "Added draft timestamps for coverage QA."},
    )
    assert patched.status_code == 200

    qa = client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/qa")

    assert qa.status_code == 200
    assert any(issue["code"] == "LOW_TRANSCRIPT_COVERAGE" for issue in qa.json()["issues"])


def test_audio_upload_rejects_unsafe_filename():
    upload = client.post(
        "/api/v1/sessions/session_demo_001/audio/upload",
        json={"filename": "../session.wav", "content_type": "audio/wav", "size_bytes": 2048, "duration_seconds": 30},
    )
    assert upload.status_code == 400


def test_local_storage_adapter_deletes_retained_object(tmp_path, monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("THERAPIST_APP_V2_STORAGE_MODE", "local")
    monkeypatch.setenv("THERAPIST_APP_V2_LOCAL_STORAGE_ROOT", str(tmp_path))

    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-AUDIO-LOCAL", "age_months": 52, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-18", "session_type": "therapy_session"},
    ).json()["session_id"]

    upload = client.post(
        f"/api/v1/sessions/{session_id}/audio/upload",
        json={"filename": "local.wav", "content_type": "audio/wav", "size_bytes": 2048, "duration_seconds": 30},
    )
    assert upload.status_code == 200
    upload_details = upload.json()["details"]
    audio_file = upload_details["audio_file"]
    stored_audio_file = get_repository_singleton().audio_files[audio_file["audio_file_id"]]
    assert stored_audio_file.object_key is not None
    assert stored_audio_file.object_key.startswith("audio/obj_")
    assert "local.wav" not in stored_audio_file.object_key
    object_path = tmp_path / stored_audio_file.object_key
    object_path.parent.mkdir(parents=True)
    object_path.write_bytes(b"placeholder")

    withdrawn = client.post(
        f"/api/v1/cases/{case_id}/withdraw-consent",
        json={"reason": "Guardian withdrew local audio consent", "redact_notes": True},
    )
    assert withdrawn.status_code == 200
    metadata = client.get(f"/api/v1/audio/{audio_file['audio_file_id']}").json()
    assert metadata["storage_mode"] == "local_private"
    assert metadata["storage_delete_status"] == "deleted"
    assert not object_path.exists()

    monkeypatch.delenv("THERAPIST_APP_V2_STORAGE_MODE")
    monkeypatch.delenv("THERAPIST_APP_V2_LOCAL_STORAGE_ROOT")
    get_settings.cache_clear()


def test_audio_process_fails_on_quality_blocker():
    get_job_queue().clear()
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-AUDIO-QUALITY", "age_months": 52, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-24", "session_type": "therapy_session"},
    ).json()["session_id"]
    process = client.post(
        f"/api/v1/sessions/{session_id}/audio/process",
        json={"provider": "manual", "duration_seconds": 3700, "channels": 1},
    )
    assert process.status_code == 200
    assert process.json()["status"] == "queued"
    worker_result = run_worker_once()
    assert worker_result["job_status"] == "failed"
    failed = client.get(f"/api/v1/jobs/{process.json()['job_id']}").json()
    assert failed["error_code"] == "audio_quality_failed"


def test_ml_dataset_baseline_and_model_card(tmp_path):
    source = tmp_path / "dataset"
    asd = source / "ASD"
    td = source / "TD"
    asd.mkdir(parents=True)
    td.mkdir(parents=True)
    cha = "\n".join(
        [
            "@Begin",
            "@Languages:\teng",
            "@Participants:\tCHI Child Target_Child, THER Therapist Investigator",
            "@ID:\teng|Demo|CHI|4;06.00|male|||Target_Child|||",
            "*CHI:\tI see a car .",
            "*CHI:\tmore car ?",
            "*UNK:\tbackground speech .",
            "*CHI:\tcar car [/] goes .",
            "@End",
        ]
    )
    (asd / "a.cha").write_text(cha, encoding="utf-8")
    (td / "b.cha").write_text(cha.replace("more car", "blue truck"), encoding="utf-8")

    dataset = client.post("/api/v1/evaluation/ml-dataset", json={"source_dir": str(source)}).json()
    assert dataset["dataset_size"] == 2
    assert dataset["class_distribution"] == {"ASD": 1, "TD": 1}
    assert dataset["rows"][0]["features"]["child_utterance_count"] == 3
    assert dataset["rows"][0]["features"]["unknown_speaker_ratio"] == 0.25
    assert dataset["rows"][0]["features"]["question_ratio"] == 0.3333
    assert dataset["rows"][0]["features"]["repetition_marker_count"] == 2

    baseline = client.post("/api/v1/evaluation/ml-baseline", json={"source_dir": str(source)}).json()
    assert baseline["dataset_size"] == 2
    assert baseline["models"]["Logistic Regression"]["status"] == "insufficient_data"

    card = client.post("/api/v1/evaluation/model-card", json={"source_dir": str(source)}).json()
    assert card["dataset_size"] == 2
    assert "type_token_ratio" in card["feature_list"]
    assert "unknown_speaker_ratio" in card["feature_list"]
    assert "question_ratio" in card["feature_list"]
    assert "repetition_marker_count" in card["feature_list"]


def test_repository_mode_selection_supports_memory_and_json(tmp_path, monkeypatch):
    get_settings.cache_clear()
    get_repository_singleton.cache_clear()
    monkeypatch.setenv("THERAPIST_APP_V2_REPOSITORY_MODE", "memory")
    memory_repo = get_repository_singleton()
    assert isinstance(memory_repo, MockRepository)
    assert not isinstance(memory_repo, JsonFileRepository)

    get_settings.cache_clear()
    get_repository_singleton.cache_clear()
    json_path = tmp_path / "local-demo.json"
    monkeypatch.setenv("THERAPIST_APP_V2_REPOSITORY_MODE", "json")
    monkeypatch.setenv("THERAPIST_APP_V2_JSON_REPOSITORY_PATH", str(json_path))
    json_repo = get_repository_singleton()
    assert isinstance(json_repo, JsonFileRepository)
    assert json_path.exists()

    get_settings.cache_clear()
    get_repository_singleton.cache_clear()


def test_sqlalchemy_repository_round_trip_when_available(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'therapist_v2.db'}"
    repo = SqlAlchemyRepository(database_url)
    repo.cases["case_sql"] = repo.cases["case_demo_001"].model_copy(update={"case_id": "case_sql", "child_code": "C-SQL"})
    repo.add_audit("test.sql_persist", "case_sql", "Persisted SQL repository test case.")

    restored = SqlAlchemyRepository(database_url)
    assert restored.cases["case_sql"].child_code == "C-SQL"
    assert any(item["action"] == "test.sql_persist" for item in restored.audit_log)


def test_repository_mode_selection_supports_sql_when_available(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    get_settings.cache_clear()
    get_repository_singleton.cache_clear()
    monkeypatch.setenv("THERAPIST_APP_V2_REPOSITORY_MODE", "sql")
    monkeypatch.setenv("THERAPIST_APP_V2_DATABASE_URL", f"sqlite:///{tmp_path / 'factory.db'}")
    repo = get_repository_singleton()
    assert isinstance(repo, SqlAlchemyRepository)
    get_settings.cache_clear()
    get_repository_singleton.cache_clear()


def test_sqlalchemy_metadata_contains_v2_clinical_tables():
    pytest.importorskip("sqlalchemy")
    from app.db.models import Base

    expected = {
        "child_cases",
        "therapy_goals",
        "sessions",
        "transcripts",
        "feature_sets",
        "audio_files",
        "ai_reviews",
        "reports",
        "processing_jobs",
        "privacy_operations",
        "audit_logs",
    }
    assert expected.issubset(set(Base.metadata.tables))


def test_audit_logs_are_org_admin_only():
    get_repository_singleton().upsert_membership(
        "pilot_org_001",
        OrganizationMembershipCreate(
            user_id="org-admin-audit",
            display_name="Audit Administrator",
            role="org_admin",
        ),
        actor_id="system",
    )
    org_a_case = client.post(
        "/api/v1/cases",
        json={"child_code": "C-AUDIT", "age_months": 50, "language": "English", "consent_status": "granted"},
    ).json()
    org_b_case = client.post(
        "/api/v1/cases",
        headers={"x-mock-user-id": "therapist-b", "x-mock-role": "therapist", "x-organization-id": "org_b"},
        json={"child_code": "C-AUDIT-B", "age_months": 48, "language": "English", "consent_status": "granted"},
    ).json()
    therapist_response = client.get("/api/v1/audit/logs")
    assert therapist_response.status_code == 403

    org_admin_response = client.get(
        "/api/v1/audit/logs",
        headers={"x-mock-role": "org_admin", "x-mock-user-id": "org-admin-audit"},
    )
    assert org_admin_response.status_code == 200
    assert any(item["action"] == "case.create" and item["target_id"] == org_a_case["case_id"] for item in org_admin_response.json())
    assert all(item["organization_id"] == "pilot_org_001" for item in org_admin_response.json())
    assert all(item["target_id"] != org_b_case["case_id"] for item in org_admin_response.json())

def test_privacy_operation_requests_are_case_visible_and_org_admin_managed():
    therapist_headers = {"x-mock-user-id": "therapist-privacy", "x-mock-role": "therapist"}
    case_id = client.post(
        "/api/v1/cases",
        headers=therapist_headers,
        json={"child_code": "C-PRIVACY", "age_months": 50, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    created = client.post(
        f"/api/v1/cases/{case_id}/privacy-requests",
        json={"operation_type": "case_export", "reason": "Guardian requested a copy of retained records."},
        headers=therapist_headers,
    )
    assert created.status_code == 200
    operation = created.json()
    assert operation["status"] == "requested"
    assert operation["requested_by"] == "therapist-privacy"
    assert operation["requester_role"] == "therapist"

    case_requests = client.get(f"/api/v1/cases/{case_id}/privacy-requests", headers=therapist_headers)
    assert case_requests.status_code == 200
    assert case_requests.json()[0]["privacy_operation_id"] == operation["privacy_operation_id"]

    therapist_queue = client.get("/api/v1/privacy/requests")
    assert therapist_queue.status_code == 403

    get_repository_singleton().upsert_membership(
        "pilot_org_001",
        OrganizationMembershipCreate(
            user_id="org-admin-privacy",
            display_name="Privacy Administrator",
            role="org_admin",
        ),
        actor_id="system",
    )

    org_admin_queue = client.get(
        "/api/v1/privacy/requests",
        headers={"x-mock-role": "org_admin", "x-mock-user-id": "org-admin-privacy"},
    )
    assert org_admin_queue.status_code == 200
    assert any(item["privacy_operation_id"] == operation["privacy_operation_id"] for item in org_admin_queue.json())
    assert all("requested_by" not in item for item in org_admin_queue.json())
    assert all("reason" not in item for item in org_admin_queue.json())
    assert all("admin_note" not in item for item in org_admin_queue.json())

    patched = client.patch(
        f"/api/v1/privacy/requests/{operation['privacy_operation_id']}",
        json={"status": "in_review", "admin_note": "Verifying retention policy before export."},
        headers={"x-mock-role": "org_admin", "x-mock-user-id": "org-admin-privacy"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "in_review"
    assert "admin_note" not in patched.json()
    assert "requested_by" not in patched.json()
    assert "reason" not in patched.json()


def test_report_export_requires_signoff_and_supports_formats():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-EXPORT", "age_months": 57, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-16", "session_type": "therapy_session"},
    ).json()["session_id"]
    cha = "\n".join(
        [
            "@Begin",
            "@Languages:\teng",
            "@Participants:\tCHI Child Target_Child, THER Therapist Investigator",
            "*THER:\twhat do you see ?",
            "*CHI:\tI see a red car .",
            "*CHI:\tthe car goes fast .",
            "*CHI:\tI want car again .",
            "@End",
        ]
    )
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/upload-cha",
        json={"filename": "export.cha", "cha_text": cha},
    ).json()["transcript_id"]
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed for export."})
    client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})
    client.post(f"/api/v1/sessions/{session_id}/ai-review")
    report_id = client.post(f"/api/v1/sessions/{session_id}/reports/draft", json={}).json()["report_id"]

    blocked = client.get(f"/api/v1/reports/{report_id}/export?format=markdown")
    assert blocked.status_code == 400

    signoff = client.post(f"/api/v1/reports/{report_id}/sign-off", json={"signed_by": "Demo Therapist"})
    assert signoff.status_code == 200
    signed_body = signoff.json()
    assert signed_body["export_timestamp"] is not None
    assert signed_body["signed_by"] == "Demo Therapist"
    assert signed_body["signed_at"] is not None
    assert signed_body["signed_snapshot_version"] == signed_body["version"]
    assert len(signed_body["signed_snapshot_hash"]) == 64
    assert signed_body["signed_snapshot"]["report_id"] == report_id
    assert signed_body["signed_snapshot"]["report_version"] == signed_body["version"]
    assert signed_body["signed_snapshot"]["signed_by"] == "Demo Therapist"
    assert signed_body["signed_snapshot"]["report_hash"] == signed_body["signed_snapshot_hash"]
    assert "Signed by: Demo Therapist" in signed_body["markdown"]
    assert "Export timestamp:" in signed_body["markdown"]
    markdown = client.get(f"/api/v1/reports/{report_id}/export?format=markdown")
    assert markdown.status_code == 200
    assert markdown.json()["content_type"] == "text/markdown"
    assert markdown.json()["report_hash"] == signed_body["signed_snapshot_hash"]
    assert markdown.json()["report_version"] == signed_body["version"]
    assert markdown.json()["signed_by"] == "Demo Therapist"
    assert markdown.json()["export_timestamp"] == signed_body["export_timestamp"]
    assert "clinical decision-support prototype" in markdown.json()["content"]
    assert "Signed by: Demo Therapist" in markdown.json()["content"]
    assert "Export timestamp:" in markdown.json()["content"]

    html = client.get(f"/api/v1/reports/{report_id}/export?format=html")
    assert html.status_code == 200
    assert html.json()["content_type"] == "text/html"
    assert "<h1>" in html.json()["content"]

    pdf = client.get(f"/api/v1/reports/{report_id}/export?format=pdf")
    assert pdf.status_code == 200
    assert pdf.json()["content_type"] in {"application/pdf", "text/markdown"}
    if pdf.json()["content_type"] == "application/pdf":
        assert pdf.json()["encoding"] == "base64"
    else:
        assert pdf.json()["unavailable_reason"]


def test_report_draft_includes_descriptive_progress_comparison():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-PROGRESS", "age_months": 58, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    first_session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-01", "session_type": "therapy_session"},
    ).json()["session_id"]
    second_session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-20", "session_type": "therapy_session"},
    ).json()["session_id"]

    first_transcript_id = client.post(
        f"/api/v1/sessions/{first_session_id}/transcripts/manual",
        json={"text": "CHI: car\nCHI: more car\nCHI: go car\nTHER: tell me more", "language": "English"},
    ).json()["transcript_id"]
    second_transcript_id = client.post(
        f"/api/v1/sessions/{second_session_id}/transcripts/manual",
        json={"text": "CHI: I see red car\nCHI: the car goes fast\nCHI: I want more car\nTHER: tell me more", "language": "English"},
    ).json()["transcript_id"]
    for transcript_id in [first_transcript_id, second_transcript_id]:
        client.post(f"/api/v1/transcripts/{transcript_id}/qa")
        client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed for progress comparison."})
        client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})

    ai_review = client.post(f"/api/v1/sessions/{second_session_id}/ai-review")
    assert ai_review.status_code == 200
    progress_area = next(area for area in ai_review.json()["assistance_areas"] if area["area"] == "Progress Summary")
    assert "Compared with the previous reviewed session" in progress_area["summary"]
    assert any("MLU words" in factor for factor in progress_area["contributing_factors"])
    report = client.post(f"/api/v1/sessions/{second_session_id}/reports/draft", json={})

    assert report.status_code == 200
    markdown = report.json()["markdown"]
    assert "## Progress Comparison" in markdown
    assert "mean_length_of_utterance_words" in markdown
    assert "Progress comparison is descriptive and requires therapist interpretation." in markdown


def test_ai_review_progress_summary_includes_td_reference_band(tmp_path, monkeypatch):
    from tests.test_dashboard_summary import _write_reference_artifact

    artifact_dir = _write_reference_artifact(tmp_path)
    monkeypatch.setenv("THERAPIST_APP_V2_REFERENCE_ARTIFACT_DIR", str(artifact_dir))
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-AI-REF", "age_months": 62, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-07-02", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: I see car\nCHI: more car\nCHI: car fast", "language": "English"},
    ).json()["transcript_id"]
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed for reference band test."})
    client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})

    ai_review = client.post(f"/api/v1/sessions/{session_id}/ai-review")

    assert ai_review.status_code == 200
    progress_area = next(area for area in ai_review.json()["assistance_areas"] if area["area"] == "Progress Summary")
    assert "typical-development reference IQR" in progress_area["summary"]
    assert "ages 60-71 months (toyplay)" in progress_area["summary"]
    assert any("Reference band (typical development" in factor for factor in progress_area["contributing_factors"])
    assert any("requires therapist interpretation" in factor for factor in progress_area["contributing_factors"])
    # The AI review surface and the report draft share the same runtime feature names.
    assert any("mean_length_of_utterance_words" in factor for factor in progress_area["contributing_factors"])


def test_ai_review_progress_summary_omits_reference_band_without_artifact():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-AI-NOREF", "age_months": 62, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-07-03", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: I see car\nCHI: more car\nCHI: car fast", "language": "English"},
    ).json()["transcript_id"]
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed for no-artifact test."})
    client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})

    ai_review = client.post(f"/api/v1/sessions/{session_id}/ai-review")

    assert ai_review.status_code == 200
    progress_area = next(area for area in ai_review.json()["assistance_areas"] if area["area"] == "Progress Summary")
    assert "Reference comparison" not in progress_area["summary"]
    assert not any("typical-development" in factor for factor in progress_area["contributing_factors"])


def test_report_type_drafts_include_required_focus_sections():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-REPORT-TYPES", "age_months": 58, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-29", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "CHI: I see car\nCHI: more car\nTHER: tell me more", "language": "English"},
    ).json()["transcript_id"]
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")

    qa_report = client.post(
        f"/api/v1/sessions/{session_id}/reports/draft",
        json={"report_type": "Transcript QA Report"},
    )
    assert qa_report.status_code == 200
    qa_markdown = qa_report.json()["markdown"]
    assert "## Transcript QA Detail" in qa_markdown
    assert "## Transcript QA Report Focus" in qa_markdown
    assert "## Recommended Therapist Review" in qa_markdown
    assert "## Clinical Interpretation Notes" in qa_markdown
    assert "## Export Timestamp" in qa_markdown

    client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed for research summary draft."})
    client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})
    client.post(f"/api/v1/sessions/{session_id}/ai-review")
    research_report = client.post(
        f"/api/v1/sessions/{session_id}/reports/draft",
        json={"report_type": "Research/Model Summary Report", "replace_existing": True},
    )
    assert research_report.status_code == 200
    research_markdown = research_report.json()["markdown"]
    assert "## Research/Model Summary Report Focus" in research_markdown
    assert "Feature schema version: features-basic-v1" in research_markdown
    assert "does not establish Thai clinical validation" in research_markdown


def test_ai_sanitization_removes_direct_identifiers():
    sanitized = sanitize_for_ai(
        (
            "John Smith visited 123 Main Street on 12/31/2025. "
            "Phone 555-123-4567. Email john.smith@example.com. "
            "DOB: 2020-01-02. MRN: AB-12345. School ID S-9988."
        ),
        "C-0001",
    )
    assert "John Smith" not in sanitized
    assert "123 Main Street" not in sanitized
    assert "555-123-4567" not in sanitized
    assert "12/31/2025" not in sanitized
    assert "john.smith@example.com" not in sanitized
    assert "2020-01-02" not in sanitized
    assert "AB-12345" not in sanitized
    assert "S-9988" not in sanitized
    assert "C-0001" in sanitized


def test_json_repository_direct_restart_persistence(tmp_path):
    from app.repositories.mock_repository import JsonFileRepository
    from app.schemas.clinical import ChildCase, TherapySession, Transcript, Report, ReviewStatus
    path = tmp_path / "persistence-direct.json"
    
    repo = JsonFileRepository(path)
    # Create entities
    case = ChildCase(case_id="case_t1", child_code="C-T1", age_months=48, language="English", consent_status="granted")
    repo.cases[case.case_id] = case
    
    session = TherapySession(session_id="session_t1", case_id=case.case_id, session_date="2026-06-19", session_type="therapy_session")
    repo.sessions[session.session_id] = session
    
    transcript = Transcript(transcript_id="trans_t1", session_id=session.session_id, case_id=case.case_id, source="paste-transcript", raw_text="@Begin\n*CHI:\thello .\n@End", therapist_attested=True, qa_status="PASS")
    repo.transcripts[transcript.transcript_id] = transcript
    
    report = Report(report_id="rep_t1", session_id=session.session_id, case_id=case.case_id, report_type="Session Review Report", title="Report Title", markdown="# Report", html="<p>Report</p>", status=ReviewStatus.signed_off)
    repo.reports[report.report_id] = report
    
    repo.add_audit("test.setup", "case_t1", "Created test entities.")
    
    # Reinitialize
    reopened = JsonFileRepository(path)
    assert "case_t1" in reopened.cases
    assert reopened.cases["case_t1"].child_code == "C-T1"
    assert "session_t1" in reopened.sessions
    assert reopened.sessions["session_t1"].case_id == "case_t1"
    assert "trans_t1" in reopened.transcripts
    assert reopened.transcripts["trans_t1"].raw_text == "@Begin\n*CHI:\thello .\n@End"
    assert reopened.transcripts["trans_t1"].therapist_attested is True
    assert "rep_t1" in reopened.reports
    assert reopened.reports["rep_t1"].title == "Report Title"
    assert reopened.reports["rep_t1"].status == ReviewStatus.signed_off


def test_audio_file_upload_stream_lifecycle():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-AUDIO-LIFE", "age_months": 52, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-19", "session_type": "therapy_session"},
    ).json()["session_id"]

    # 1. Post upload intent
    upload = client.post(
        f"/api/v1/sessions/{session_id}/audio/upload",
        json={"filename": "test_audio.wav", "content_type": "audio/wav", "size_bytes": 12, "duration_seconds": 30}
    )
    assert upload.status_code == 200
    data = upload.json()
    audio_id = data["details"]["audio_file"]["audio_file_id"]
    upload_url = data["details"]["upload_intent"]["upload_url"]
    
    # 2. PUT file bytes to the upload url
    payload = b"RIFFxxxxWAVE"
    put_resp = client.put(f"/api/v1{upload_url}", content=payload)
    assert put_resp.status_code == 200

    unverified_metadata = client.get(f"/api/v1/audio/{audio_id}")
    assert unverified_metadata.status_code == 200
    assert unverified_metadata.json()["upload_status"] == "pending_verification"
    assert unverified_metadata.json()["object_key"] is None

    unverified_file = client.get(f"/api/v1/audio/{audio_id}/file")
    assert unverified_file.status_code == 400

    second_put = client.put(f"/api/v1{upload_url}", content=payload)
    assert second_put.status_code == 400
    
    # 3. Complete metadata upload
    comp = client.post(
        f"/api/v1/audio/{audio_id}/complete-upload",
        json={"checksum_sha256": "fake-checksum", "size_bytes": 12}
    )
    assert comp.status_code == 200
    
    # 4. List session audio files
    lst = client.get(f"/api/v1/sessions/{session_id}/audio")
    assert lst.status_code == 200
    assert len(lst.json()) == 1
    assert lst.json()[0]["audio_file_id"] == audio_id
    assert lst.json()[0]["object_key"] is None
    
    # 5. GET/Download audio file bytes
    get_file = client.get(f"/api/v1/audio/{audio_id}/file")
    assert get_file.status_code == 200
    assert get_file.content == payload


def test_complete_upload_requires_bytes_received_and_failed_attempt_needs_new_intent():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-AUDIO-VERIFY", "age_months": 52, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-20", "session_type": "therapy_session"},
    ).json()["session_id"]

    first_upload = client.post(
        f"/api/v1/sessions/{session_id}/audio/upload",
        json={"filename": "verify.wav", "content_type": "audio/wav", "size_bytes": 12, "duration_seconds": 30}
    )
    assert first_upload.status_code == 200
    first_audio_id = first_upload.json()["details"]["audio_file"]["audio_file_id"]

    premature_complete = client.post(
        f"/api/v1/audio/{first_audio_id}/complete-upload",
        json={"checksum_sha256": "fake-checksum", "size_bytes": 12}
    )
    assert premature_complete.status_code == 400
    assert premature_complete.json()["detail"] == (
        "Audio upload must be re-issued with a new upload intent before completion verification."
    )

    replacement_upload = client.post(
        f"/api/v1/sessions/{session_id}/audio/upload",
        json={"filename": "verify.wav", "content_type": "audio/wav", "size_bytes": 12, "duration_seconds": 30}
    )
    assert replacement_upload.status_code == 200
    assert replacement_upload.json()["details"]["audio_file"]["audio_file_id"] != first_audio_id
