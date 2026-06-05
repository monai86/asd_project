from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from src.clinical_speech.feature_extractor import extract_clinical_features
from src.clinical_speech.models import NormalizedTranscriptLine


def test_thai_mlu_calculations():
    # Construct some child utterances in Thai
    lines = [
        NormalizedTranscriptLine(
            session_id="S1",
            speaker_code="CHI",
            speaker_role="child",
            start_ms=0,
            end_ms=1000,
            text="สวัสดีครับ",  # 3 syllables, 2 words ("สวัสดี", "ครับ")
            reviewed_text="สวัสดีครับ",
            is_reviewed=True,
            line_id="1",
            line_number=1,
        ),
        NormalizedTranscriptLine(
            session_id="S1",
            speaker_code="CHI",
            speaker_role="child",
            start_ms=1500,
            end_ms=3000,
            text="ไปเที่ยวกันไหม", # 4 syllables, 4 words ("ไป", "เที่ยว", "กัน", "ไหม")
            reviewed_text="ไปเที่ยวกันไหม",
            is_reviewed=True,
            line_id="2",
            line_number=2,
        )
    ]
    
    result = extract_clinical_features(lines)
    features = result["features"]
    
    assert "mlu_s" in features
    assert "mlu_w" in features
    
    # 7 syllables total, 2 utterances -> MLU-s = 3.5
    assert features["mlu_s"] == pytest.approx(3.5)
    
    # 5 words total ('สวัสดี', 'ครับ', 'ไปเที่ยว', 'กัน', 'ไหม'), 2 utterances -> MLU-w = 2.5
    assert features["mlu_w"] == pytest.approx(2.5)


def test_non_thai_mlu_calculations():
    # English only
    lines = [
        NormalizedTranscriptLine(
            session_id="S1",
            speaker_code="CHI",
            speaker_role="child",
            start_ms=0,
            end_ms=1000,
            text="hello world",
            reviewed_text="hello world",
            is_reviewed=True,
            line_id="1",
            line_number=1,
        )
    ]
    
    result = extract_clinical_features(lines)
    features = result["features"]
    
    assert features["mlu_s"] == 0.0
    assert features["mlu_w"] == 2.0


def test_consent_withdrawal_orphans_sessions_and_data():
    from src.clinical_workflow import MockClinicalRepository
    from src.clinical_workflow.models import User
    from dataclasses import replace

    repo = MockClinicalRepository()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    # Verify CASE-001 has active sessions, notes, goals, etc.
    session = repo.sessions.get("SESSION-001")
    assert session is not None
    assert session.case_id == "CASE-001"
    assert session.owner_user_id == therapist.user_id

    # Create a report for CASE-001
    from src.clinical_workflow.models import Report
    repo.reports["REPORT-001"] = Report(
        report_id="REPORT-001",
        case_id="CASE-001",
        owner_user_id=therapist.user_id,
        session_id="SESSION-001",
        title="Initial Assessment Report",
        content_markdown="This is clinical content detailing child progress."
    )

    # Verify initial state of related objects
    assert repo.therapist_notes["NOTE-001"].case_id == "CASE-001"
    assert repo.therapy_goals["GOAL-001"].case_id == "CASE-001"
    assert repo.reports["REPORT-001"].case_id == "CASE-001"

    # Withdraw consent
    updated_case = repo.update_case_for_user(
        "CASE-001",
        therapist,
        consent_status="declined"
    )
    
    assert updated_case is not None
    assert updated_case.consent_status == "declined"

    # 1. sessions no longer reference the original case_id or owner_user_id
    assert repo.sessions["SESSION-001"].case_id == "orphaned-due-to-withdrawn-consent"
    assert repo.sessions["SESSION-001"].owner_user_id == "orphaned-due-to-withdrawn-consent"

    # 2. notes/details are cleared or redacted
    assert repo.sessions["SESSION-001"].notes == "[REDACTED] Consent withdrawn. Identifiers unlinked."
    assert repo.therapist_notes["NOTE-001"].note_text == "[REDACTED] Consent withdrawn. Identifiers unlinked."
    assert repo.reports["REPORT-001"].title == "[REDACTED] Report"
    assert repo.reports["REPORT-001"].content_markdown == "[REDACTED] Consent withdrawn. Identifiers unlinked."
    assert repo.therapy_goals["GOAL-001"].goal_text == "[REDACTED] Consent withdrawn. Identifiers unlinked."

    # 3. transcripts/features/artifacts cannot be linked back to the original case through session_id
    # Check that transcript is orphaned
    assert repo.transcripts["TRANSCRIPT-001"].case_id == "orphaned-due-to-withdrawn-consent"
    assert repo.transcripts["TRANSCRIPT-001"].owner_user_id == "orphaned-due-to-withdrawn-consent"
    
    # If we fetch session_id "SESSION-001" from any transcript/feature, that session itself is orphaned
    associated_session_id = repo.transcripts["TRANSCRIPT-001"].session_id
    associated_session = repo.sessions[associated_session_id]
    assert associated_session.case_id == "orphaned-due-to-withdrawn-consent"
    assert associated_session.owner_user_id == "orphaned-due-to-withdrawn-consent"


def test_consent_withdrawal_idempotency():
    from src.clinical_workflow import MockClinicalRepository
    repo = MockClinicalRepository()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    # Withdraw first time
    repo.update_case_for_user("CASE-001", therapist, consent_status="declined")
    
    # Verify orphaned
    assert repo.sessions["SESSION-001"].case_id == "orphaned-due-to-withdrawn-consent"
    assert repo.sessions["SESSION-001"].notes == "[REDACTED] Consent withdrawn. Identifiers unlinked."

    # Withdraw second time (idempotency check)
    repo.update_case_for_user("CASE-001", therapist, consent_status="declined")
    
    # Should remain orphaned and not crash
    assert repo.sessions["SESSION-001"].case_id == "orphaned-due-to-withdrawn-consent"
    assert repo.sessions["SESSION-001"].notes == "[REDACTED] Consent withdrawn. Identifiers unlinked."


def test_fastapi_signoff_queues_clan_background_task():
    from fastapi.testclient import TestClient
    from src.clinical_workflow import MockClinicalRepository
    from src.therapist_backend.app import create_app

    repo = MockClinicalRepository()
    app = create_app(repo)
    client = TestClient(app)

    # Seeding: ensure TRANSCRIPT-001 is reviewed so it can be signed off
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None
    repo.mark_transcript_reviewed("TRANSCRIPT-001", therapist)

    # Call the signoff endpoint
    response = client.post(
        "/api/sessions/SESSION-001/transcript/signoff",
        json={"notes": "Signing off for testing"},
        headers={"X-User-Id": "user_therapist_001"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "SESSION-001"
    
    # Check if run_background_clan_analysis actually ran or failed gracefully if dependencies are missing.
    # Let's inspect the clinical speech artifacts for SESSION-001!
    artifacts = repo.list_clinical_speech_artifacts_for_session_for_user("SESSION-001", therapist)
    assert len(artifacts) > 0
    clan_artifact = next((art for art in artifacts if art.artifact_type == "clan_metrics"), None)
    assert clan_artifact is not None
    assert "clan_metric_not_ready" in clan_artifact.parsed_metrics

