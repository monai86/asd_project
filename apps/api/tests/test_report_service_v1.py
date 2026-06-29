import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.dependencies import get_repository_singleton
from app.schemas.clinical import (
    ReportGenerationRequest,
    ReportFinalizeRequest,
    ReviewStatus,
    Transcript,
    Utterance,
    FeatureSet,
    FeatureValue,
)
from app.repositories.mock_repository import MockRepository, new_id
from app.core.config import get_settings
from app.services.report_safety_validator import ReportSafetyValidator
from app.services.providers.report_providers import TemplateReportProvider, LocalLLMReportProvider
from app.services.providers.report_registry import report_provider_registry
from app.services.report_service import draft_report, sign_off_report, patch_report
from app.services.transcript_service import patch_transcript
from app.schemas.clinical import TranscriptPatch

client = TestClient(app)


def _setup_mock_repo():
    repo = MockRepository()
    
    # 1. Create a child case
    case_id = new_id("case")
    repo.cases[case_id] = repo.clone(repo.cases["case_demo_001"])
    repo.cases[case_id].case_id = case_id
    repo.cases[case_id].child_code = "C-TEST-V1"
    repo.cases[case_id].consent_status = "granted"
    repo.cases[case_id].primary_therapist_user_id = "therapist-demo"
    
    # 2. Create a session
    session_id = new_id("ses")
    repo.sessions[session_id] = repo.clone(repo.sessions["session_demo_001"])
    repo.sessions[session_id].session_id = session_id
    repo.sessions[session_id].case_id = case_id
    
    # 3. Create a transcript
    transcript_id = new_id("tr")
    transcript = Transcript(
        transcript_id=transcript_id,
        session_id=session_id,
        case_id=case_id,
        source="manual",
        raw_text="@Begin\n*CHI:\thello.\n@End",
        utterances=[Utterance(utterance_id="utt_1", speaker="CHI", text="hello")],
        therapist_attested=True,
        review_status=ReviewStatus.attested
    )
    repo.transcripts[transcript_id] = transcript
    repo.sessions[session_id].transcript_id = transcript_id
    
    # 4. Create features
    feature_set_id = new_id("feat")
    feature_set = FeatureSet(
        feature_set_id=feature_set_id,
        session_id=session_id,
        transcript_id=transcript_id,
        transcript_version=1,
        therapist_attested=True,
        features=[
            FeatureValue(name="mean_length_of_utterance_words", value=2.5, unit="words"),
            FeatureValue(name="type_token_ratio", value=0.5, unit="ratio")
        ]
    )
    repo.features[feature_set_id] = feature_set
    repo.sessions[session_id].feature_set_id = feature_set_id
    
    return repo, case_id, session_id, transcript_id


def test_safety_validator_direct():
    validator = ReportSafetyValidator()
    
    # Test prohibited claim
    res1 = validator.validate_report("Child is ASD positive", source="generation")
    assert res1.status == "failed"
    assert res1.prohibited_claims_found is True
    assert any(issue.code == "RULE_ASD_POS_NEG" for issue in res1.issues)
    
    # Test negation/allowlist context bypass
    res2 = validator.validate_report("this system does not diagnose ASD and is for decision support only", source="generation")
    # Prohibited matching should be bypassed due to disclaimer
    assert res2.prohibited_claims_found is False
    
    # Test missing disclaimers phase-aware behavior
    # Generation: warning only, not blocking
    res3 = validator.validate_report("# Safe report\n\nNo disclaimers.", source="edit")
    assert res3.status == "warning"
    assert res3.finalization_blocked is False
    
    # Finalization: error, blocks finalization
    res4 = validator.validate_report("# Safe report\n\nNo disclaimers.", source="finalization")
    assert res4.status == "failed"
    assert res4.finalization_blocked is True
    assert len(res4.issues) > 0


def test_template_provider_output():
    repo, case_id, session_id, transcript_id = _setup_mock_repo()
    
    provider = TemplateReportProvider()
    input_data = report_provider_registry.get("template").check_availability()
    assert input_data.available is True
    
    report = draft_report(repo, session_id, report_type="Session Review Report")
    assert report.status == ReviewStatus.draft
    assert report.actual_provider == "template"
    
    # Check 11 sections
    assert len(report.sections) == 11
    section_ids = [s.section_id for s in report.sections]
    assert "session_overview" in section_ids
    assert "limitations" in section_ids
    assert "decision_support_disclaimer" in section_ids
    
    # Ensure no diagnostic claims are in the template output
    validator = ReportSafetyValidator()
    safety_result = validator.validate_report(report.markdown, source="finalization")
    assert safety_result.status == "passed"
    assert safety_result.finalization_blocked is False


def test_local_llm_provider_unavailability(monkeypatch):
    monkeypatch.setenv("THERAPIST_APP_V2_AI_REPORT_DRAFTING_ENABLED", "true")
    get_settings.cache_clear()
    repo, case_id, session_id, transcript_id = _setup_mock_repo()
    
    # Local LLM with invalid port to guarantee connection failure
    provider = LocalLLMReportProvider(base_url="http://localhost:59999", model_name="llama3")
    availability = provider.check_availability()
    assert availability.available is False
    assert "Connection failed" in availability.reason
    
    # Generation fails when fallback is false
    payload = ReportGenerationRequest(provider_id="local_llm", allow_fallback_to_template=False)
    try:
        with pytest.raises(ValueError, match="is unavailable and fallback is not allowed"):
            draft_report(repo, session_id, payload)
    finally:
        monkeypatch.delenv("THERAPIST_APP_V2_AI_REPORT_DRAFTING_ENABLED", raising=False)
        get_settings.cache_clear()


def test_local_llm_drafting_requires_explicit_opt_in_even_with_fallback():
    repo, case_id, session_id, transcript_id = _setup_mock_repo()

    payload = ReportGenerationRequest(provider_id="local_llm", allow_fallback_to_template=True)
    with pytest.raises(ValueError, match="AI report drafting is not enabled"):
        draft_report(repo, session_id, payload)


def test_local_llm_fallback_to_template_when_ai_drafting_is_enabled(monkeypatch):
    monkeypatch.setenv("THERAPIST_APP_V2_AI_REPORT_DRAFTING_ENABLED", "true")
    get_settings.cache_clear()
    try:
        repo, case_id, session_id, transcript_id = _setup_mock_repo()

        # Generation falls back to template when allow_fallback_to_template is true
        payload = ReportGenerationRequest(provider_id="local_llm", allow_fallback_to_template=True)
        report = draft_report(repo, session_id, payload)
    finally:
        monkeypatch.delenv("THERAPIST_APP_V2_AI_REPORT_DRAFTING_ENABLED", raising=False)
        get_settings.cache_clear()

    assert report.status == ReviewStatus.draft
    assert report.actual_provider == "template"
    assert "is unavailable" in report.fallback_reason
    assert report.ai_drafting_requested is True
    assert report.ai_drafting_enabled is True
    assert report.ai_drafting_provider == "local_llm"


def test_readiness_gates_validation():
    repo, case_id, session_id, transcript_id = _setup_mock_repo()
    
    # 1. Un-attest transcript
    repo.transcripts[transcript_id].therapist_attested = False
    
    with pytest.raises(ValueError, match="requires attested/reviewed transcript"):
        draft_report(repo, session_id, "Session Review Report")
        
    # Transcript QA Report ignores attestation requirement
    report = draft_report(repo, session_id, "Transcript QA Report")
    assert report.status == ReviewStatus.draft


def test_strict_finalization_safety_gate():
    repo, case_id, session_id, transcript_id = _setup_mock_repo()
    
    # Generate draft successfully
    report = draft_report(repo, session_id, "Session Review Report")
    report_id = report.report_id
    
    # 1. Edit the report to contain prohibited diagnostic words
    patch_report(repo, report_id, payload=patch_report_payload("ASD positive claim text. ## Limitations\nNo limitations."))
    
    # 2. Try to sign-off: must block due to safety validation errors
    with pytest.raises(ValueError, match="Report sign-off is blocked due to safety violations"):
        sign_off_report(repo, report_id, signed_by="Demo Therapist")
        
    # 3. Clean draft to include disclaimers and remove prohibited words
    clean_markdown = (
        "# Clean Report\n\n"
        "Descriptive speech patterns observed. "
        "It is for clinical decision-support only and is not diagnostic. "
        "Therapist review required before clinical use.\n\n"
        "## Limitations\nSome limitations."
    )
    patch_report(repo, report_id, payload=patch_report_payload(clean_markdown))
    
    # 4. Sign-off succeeds
    signed = sign_off_report(repo, report_id, signed_by="Demo Therapist")
    assert signed.status_code if hasattr(signed, "status_code") else signed.status == ReviewStatus.signed_off
    assert signed.therapist_signoff_status == ReviewStatus.signed_off


def test_sign_off_requires_primary_assigned_therapist_identity():
    repo, case_id, session_id, transcript_id = _setup_mock_repo()
    report = draft_report(repo, session_id, "Session Review Report")

    with pytest.raises(ValueError, match="primary assigned therapist"):
        sign_off_report(
            repo,
            report.report_id,
            signed_by="Supervisor Demo",
            signed_by_user_id="supervisor-demo",
        )


def test_sign_off_blocks_when_primary_therapist_is_missing():
    repo, case_id, session_id, transcript_id = _setup_mock_repo()
    repo.cases[case_id].primary_therapist_user_id = None
    report = draft_report(repo, session_id, "Session Review Report")

    with pytest.raises(ValueError, match="primary therapist is assigned"):
        sign_off_report(
            repo,
            report.report_id,
            signed_by="Demo Therapist",
            signed_by_user_id="therapist-demo",
        )


def test_transcript_edit_stales_downstream_outputs_and_blocks_existing_report_signoff():
    repo, case_id, session_id, transcript_id = _setup_mock_repo()
    report = draft_report(repo, session_id, "Session Review Report")

    assert repo.sessions[session_id].feature_set_id is not None
    assert repo.sessions[session_id].report_id == report.report_id
    assert repo.transcripts[transcript_id].therapist_attested is True

    patch_transcript(
        repo,
        transcript_id,
        TranscriptPatch(raw_text="@Begin\n*CHI:\tedited words.\n@End"),
    )

    session = repo.sessions[session_id]
    transcript = repo.transcripts[transcript_id]

    assert transcript.therapist_attested is False
    assert transcript.review_status == ReviewStatus.needs_review
    assert session.feature_set_id is None
    assert session.ml_result_id is None
    assert session.ai_review_id is None
    assert session.report_id is None

    with pytest.raises(ValueError, match="therapist transcript attestation exists"):
        sign_off_report(
            repo,
            report.report_id,
            signed_by="Demo Therapist",
            signed_by_user_id="therapist-demo",
        )


def patch_report_payload(markdown: str):
    from app.schemas.clinical import ReportPatch
    return ReportPatch(markdown=markdown)


def test_endpoints_via_client():
    # Setup test session in DB repo
    repo = get_repository_singleton()
    
    case_id = new_id("case")
    repo.cases[case_id] = repo.clone(repo.cases["case_demo_001"])
    repo.cases[case_id].case_id = case_id
    repo.cases[case_id].consent_status = "granted"
    
    session_id = new_id("ses")
    repo.sessions[session_id] = repo.clone(repo.sessions["session_demo_001"])
    repo.sessions[session_id].session_id = session_id
    repo.sessions[session_id].case_id = case_id
    
    transcript_id = new_id("tr")
    transcript = Transcript(
        transcript_id=transcript_id,
        session_id=session_id,
        case_id=case_id,
        source="manual",
        raw_text="@Begin\n*CHI:\thello.\n@End",
        utterances=[Utterance(utterance_id="utt_1", speaker="CHI", text="hello")],
        therapist_attested=True,
        review_status=ReviewStatus.attested
    )
    repo.transcripts[transcript_id] = transcript
    repo.sessions[session_id].transcript_id = transcript_id
    
    # 1. Post draft generation endpoint
    resp1 = client.post(f"/api/v1/sessions/{session_id}/reports/draft", json={
        "provider_id": "template",
        "allow_fallback_to_template": True
    })
    assert resp1.status_code == 200
    report_id = resp1.json()["report_id"]
    
    # 2. Get report providers endpoint
    resp2 = client.get("/api/v1/reports/providers")
    assert resp2.status_code == 200
    providers = resp2.json()
    assert any(p["provider_id"] == "template" for p in providers)
    assert any(p["provider_id"] == "local_llm" for p in providers)
    
    # 3. Patch report to safe custom content
    safe_markdown = (
        "# Safe report\n"
        "Decision-support only. Not diagnostic. Therapist review required.\n"
        "## Limitations\nNo limitations."
    )
    resp3 = client.patch(f"/api/v1/reports/{report_id}", json={
        "markdown": safe_markdown
    })
    assert resp3.status_code == 200
    
    # 4. Post sign-off endpoint with confirmation
    resp4 = client.post(f"/api/v1/reports/{report_id}/sign-off", json={
        "therapist_name": "Demo Therapist",
        "confirmation_checked": True
    })
    assert resp4.status_code == 200
    assert resp4.json()["status"] == "Signed Off"
