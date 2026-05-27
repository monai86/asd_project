from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.clinical_workflow import (  # noqa: E402
    ALLOWED_AUDIO_FILE_TYPES,
    ALLOWED_TRANSCRIPT_FILE_TYPES,
    MAX_AUDIO_FILE_SIZE_BYTES,
    SAFETY_DISCLAIMER,
    MockClinicalRepository,
)
from src.feature_schema import FEATURES  # noqa: E402


VALID_CHAT = """@Begin
@Languages:\teng
@Participants:\tCHI Child Target_Child, MOT Mother Mother
@ID:\teng|Mock|CHI|4;00.00|male|||Target_Child|||
@ID:\teng|Mock|MOT|||||Mother|||
*CHI:\thello .
*MOT:\tyes .
@End
"""

INVALID_CHAT = """@Participants:\tMOT Mother Mother
@ID:\teng|Mock|MOT|||||Mother|||
*MOT:\thello .
"""


def _repo() -> MockClinicalRepository:
    current = datetime(2026, 5, 27, 8, 0, tzinfo=timezone.utc)

    def now() -> datetime:
        nonlocal current
        current = current + timedelta(minutes=1)
        return current

    return MockClinicalRepository(now_provider=now)


def test_mock_login_success_updates_last_login_and_audit_log():
    repo = _repo()

    user = repo.authenticate("therapist@example.test", "demo-password")

    assert user is not None
    assert user.role == "therapist"
    stored = repo.get_user(user.user_id)
    assert stored is not None
    assert stored.last_login is not None
    assert any(log.event_type == "login" and log.actor_user_id == user.user_id for log in repo.audit_logs)


def test_mock_login_failure_returns_none_without_audit_log():
    repo = _repo()

    user = repo.authenticate("therapist@example.test", "wrong-password")

    assert user is None
    assert not repo.audit_logs


def test_therapist_and_clinician_are_case_owning_roles():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    clinician = repo.authenticate("clinician@example.test", "demo-password")

    assert therapist is not None
    assert clinician is not None
    assert {case.case_id for case in repo.list_cases_for_user(therapist)} == {"CASE-001", "CASE-002"}
    assert {case.case_id for case in repo.list_cases_for_user(clinician)} == {"CASE-003"}


def test_admin_can_view_all_cases_and_audit_logs():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    admin = repo.authenticate("admin@example.test", "demo-password")

    assert therapist is not None
    assert admin is not None
    assert {case.case_id for case in repo.list_cases_for_user(admin)} == {"CASE-001", "CASE-002", "CASE-003"}
    logs = repo.list_audit_logs_for_user(admin)
    assert len(logs) == 2
    assert {log.event_type for log in logs} == {"login"}


def test_one_therapist_cannot_retrieve_another_clinical_users_case():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    clinician = repo.authenticate("clinician@example.test", "demo-password")

    assert therapist is not None
    assert clinician is not None
    assert repo.get_case_for_user("CASE-003", therapist) is None
    assert repo.get_case_for_user("CASE-003", clinician) is not None


def test_create_case_assigns_owner_anonymized_id_and_audit_event():
    repo = _repo()
    user = repo.authenticate("therapist@example.test", "demo-password")
    assert user is not None

    case = repo.create_case(
        owner_user_id=user.user_id,
        anonymized_child_code="CHI-A03",
        age_months=42,
        sex="not_specified",
        primary_concerns="Parent reports limited phrase speech.",
        consent_status="granted",
        anonymization_status="anonymized",
        external_clinical_status="under_evaluation",
        notes="Phase 1 mock case.",
    )

    assert case.case_id == "CASE-004"
    assert case.owner_user_id == user.user_id
    assert case.anonymized_child_code == "CHI-A03"
    assert case.external_clinical_status == "under_evaluation"
    owned_ids = {owned.case_id for owned in repo.list_cases_for_user(user)}
    assert "CASE-004" in owned_ids
    assert any(log.event_type == "case_created" and log.target_id == case.case_id for log in repo.audit_logs)


def test_seeded_sessions_power_dashboard_counts():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    summary = repo.dashboard_summary(therapist)

    assert summary["active_cases"] == 2
    assert summary["sessions_awaiting_transcript_review"] == 1
    assert summary["sessions_awaiting_report_generation"] == 1
    assert summary["uploaded_files"] == 1


def test_update_case_for_owner_changes_context_and_writes_audit_event():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    updated = repo.update_case_for_user(
        "CASE-001",
        therapist,
        age_months=49,
        primary_concerns="Updated mock concerns for review.",
        consent_status="pending",
        anonymization_status="needs_review",
        external_clinical_status="under_evaluation",
        notes="Updated Phase 2 mock note.",
    )

    assert updated is not None
    assert updated.age_months == 49
    assert updated.primary_concerns == "Updated mock concerns for review."
    assert updated.consent_status == "pending"
    assert updated.anonymization_status == "needs_review"
    assert any(log.event_type == "case_updated" and log.target_id == "CASE-001" for log in repo.audit_logs)


def test_clinical_user_cannot_update_another_owner_case():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    updated = repo.update_case_for_user("CASE-003", therapist, primary_concerns="Should not apply.")

    assert updated is None
    clinician_case = repo.cases["CASE-003"]
    assert clinician_case.primary_concerns != "Should not apply."


def test_create_session_links_to_owned_case_and_writes_audit_event():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    session = repo.create_session(
        case_id="CASE-001",
        user=therapist,
        session_date="2026-05-27",
        session_type="therapy_session",
        notes="Phase 2 session management test.",
    )

    assert session.session_id == "SESSION-004"
    assert session.case_id == "CASE-001"
    assert session.owner_user_id == therapist.user_id
    assert session.therapist_review_status == "not_started"
    assert session.report_status == "not_started"
    assert session in repo.list_sessions_for_case_for_user("CASE-001", therapist)
    assert any(log.event_type == "session_created" and log.target_id == session.session_id for log in repo.audit_logs)


def test_create_session_rejects_case_owned_by_another_clinical_user():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    try:
        repo.create_session(
            case_id="CASE-003",
            user=therapist,
            session_date="2026-05-27",
            session_type="therapy_session",
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("Expected PermissionError for cross-owner session creation.")


def test_add_therapist_note_links_to_case_or_session_and_writes_audit_event():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    note = repo.add_therapist_note(
        case_id="CASE-001",
        user=therapist,
        session_id="SESSION-001",
        note_text="Reviewed parent report and session context.",
    )

    assert note.note_id == "NOTE-003"
    assert note.case_id == "CASE-001"
    assert note.session_id == "SESSION-001"
    notes = repo.list_notes_for_case_for_user("CASE-001", therapist)
    assert {item.note_id for item in notes} >= {"NOTE-001", "NOTE-003"}
    assert any(log.event_type == "therapist_note_created" and log.target_id == note.note_id for log in repo.audit_logs)


def test_allowed_audio_file_types_match_phase_3_contract():
    assert ALLOWED_AUDIO_FILE_TYPES == ("wav", "mp3", "m4a", "mp4", "mov")


def test_create_audio_metadata_accepts_each_allowed_file_type():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    created_types = []
    for file_type in ALLOWED_AUDIO_FILE_TYPES:
        audio_file = repo.create_audio_file_metadata(
            case_id="CASE-001",
            session_id="SESSION-001",
            user=therapist,
            original_filename=f"sample.{file_type}",
            file_size=1024,
        )
        created_types.append(audio_file.file_type)

    assert tuple(created_types) == ALLOWED_AUDIO_FILE_TYPES


def test_create_audio_metadata_for_owned_session_links_record_and_writes_audit():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    audio_file = repo.create_audio_file_metadata(
        case_id="CASE-001",
        session_id="SESSION-001",
        user=therapist,
        original_filename="family_play_sample.MP3",
        file_size=2_048_000,
    )

    assert audio_file.audio_file_id == "AUDIO-002"
    assert audio_file.owner_user_id == therapist.user_id
    assert audio_file.case_id == "CASE-001"
    assert audio_file.session_id == "SESSION-001"
    assert audio_file.original_filename == "family_play_sample.MP3"
    assert audio_file.stored_filename == "CASE-001_SESSION-001_AUDIO-002.mp3"
    assert audio_file.file_type == "mp3"
    assert audio_file.processing_status == "pending"
    assert repo.sessions["SESSION-001"].audio_file_id == "AUDIO-002"
    assert any(log.event_type == "file_uploaded" and log.target_id == audio_file.audio_file_id for log in repo.audit_logs)


def test_audio_metadata_stored_filename_uses_ids_not_original_filename():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    audio_file = repo.create_audio_file_metadata(
        case_id="CASE-001",
        session_id="SESSION-001",
        user=therapist,
        original_filename="child_real_name_home_session.wav",
        file_size=1024,
    )

    assert "child_real_name" not in audio_file.stored_filename
    assert audio_file.stored_filename == "CASE-001_SESSION-001_AUDIO-002.wav"


def test_audio_metadata_rejects_unsupported_file_type():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    try:
        repo.create_audio_file_metadata(
            case_id="CASE-001",
            session_id="SESSION-001",
            user=therapist,
            original_filename="notes.pdf",
            file_size=1024,
        )
    except ValueError as exc:
        assert "Unsupported file type" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported file type.")


def test_audio_metadata_rejects_oversized_file():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    try:
        repo.create_audio_file_metadata(
            case_id="CASE-001",
            session_id="SESSION-001",
            user=therapist,
            original_filename="too_large.wav",
            file_size=MAX_AUDIO_FILE_SIZE_BYTES + 1,
        )
    except ValueError as exc:
        assert "maximum configured size" in str(exc)
    else:
        raise AssertionError("Expected ValueError for oversized file.")


def test_audio_metadata_rejects_cross_owner_session_attachment():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    try:
        repo.create_audio_file_metadata(
            case_id="CASE-003",
            session_id="SESSION-003",
            user=therapist,
            original_filename="other_case.wav",
            file_size=1024,
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("Expected PermissionError for cross-owner file metadata.")


def test_admin_can_view_all_audio_metadata():
    repo = _repo()
    clinician = repo.authenticate("clinician@example.test", "demo-password")
    admin = repo.authenticate("admin@example.test", "demo-password")
    assert clinician is not None
    assert admin is not None

    repo.create_audio_file_metadata(
        case_id="CASE-003",
        session_id="SESSION-003",
        user=clinician,
        original_filename="clinician_session.mov",
        file_size=2048,
    )

    audio_files = repo.list_audio_files_for_user(admin)

    assert {audio_file.audio_file_id for audio_file in audio_files} == {"AUDIO-001", "AUDIO-002"}


def test_allowed_transcript_file_types_match_phase_4_contract():
    assert ALLOWED_TRANSCRIPT_FILE_TYPES == ("cha",)


def test_seeded_transcript_is_available_for_owned_session():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    transcript = repo.get_transcript_for_session_for_user("SESSION-001", therapist)

    assert transcript is not None
    assert transcript.transcript_id == "TRANSCRIPT-001"
    assert transcript.qa_status == "pass"
    assert transcript.review_status == "awaiting_review"


def test_create_transcript_for_owned_session_runs_qa_and_links_session():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    transcript = repo.create_transcript_for_session(
        session_id="SESSION-002",
        user=therapist,
        transcript_text=VALID_CHAT,
        original_filename="session_002.cha",
    )

    assert transcript.transcript_id == "TRANSCRIPT-002"
    assert transcript.session_id == "SESSION-002"
    assert transcript.qa_status in {"pass", "needs_review"}
    assert transcript.qa_score is not None
    assert transcript.review_status == "awaiting_review"
    assert repo.sessions["SESSION-002"].transcript_id == transcript.transcript_id
    assert repo.sessions["SESSION-002"].therapist_review_status == "awaiting_review"
    assert any(log.event_type == "transcript_uploaded" and log.target_id == transcript.transcript_id for log in repo.audit_logs)


def test_create_transcript_rejects_non_cha_filename():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    try:
        repo.create_transcript_for_session(
            session_id="SESSION-002",
            user=therapist,
            transcript_text=VALID_CHAT,
            original_filename="session_002.txt",
        )
    except ValueError as exc:
        assert "Unsupported transcript file type" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-CHAT transcript filename.")


def test_create_transcript_rejects_cross_owner_session():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    try:
        repo.create_transcript_for_session(
            session_id="SESSION-003",
            user=therapist,
            transcript_text=VALID_CHAT,
            original_filename="other_case.cha",
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("Expected PermissionError for cross-owner transcript upload.")


def test_invalid_transcript_sets_needs_correction_status():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    transcript = repo.create_transcript_for_session(
        session_id="SESSION-002",
        user=therapist,
        transcript_text=INVALID_CHAT,
        original_filename="invalid.cha",
    )

    assert transcript.qa_status == "fail"
    assert transcript.review_status == "needs_correction"
    assert repo.sessions["SESSION-002"].therapist_review_status == "needs_correction"


def test_update_transcript_reruns_qa_and_writes_audit_event():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None
    transcript = repo.create_transcript_for_session(
        session_id="SESSION-002",
        user=therapist,
        transcript_text=INVALID_CHAT,
        original_filename="invalid.cha",
    )

    updated = repo.update_transcript_for_user(
        transcript.transcript_id,
        therapist,
        transcript_text=VALID_CHAT,
        reviewer_notes="Corrected CHAT headers and child tier.",
    )

    assert updated is not None
    assert updated.qa_status in {"pass", "needs_review"}
    assert updated.review_status == "awaiting_review"
    assert "Corrected CHAT headers" in updated.reviewer_notes
    assert any(log.event_type == "transcript_edited" and log.target_id == transcript.transcript_id for log in repo.audit_logs)


def test_mark_transcript_reviewed_and_rerun_feature_status():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None
    transcript = repo.create_transcript_for_session(
        session_id="SESSION-002",
        user=therapist,
        transcript_text=VALID_CHAT,
        original_filename="session_002.cha",
    )

    reviewed = repo.mark_transcript_reviewed(transcript.transcript_id, therapist, "Ready for mock feature extraction.")
    session = repo.rerun_feature_extraction_after_transcript_review("SESSION-002", therapist)

    assert reviewed is not None
    assert reviewed.review_status == "reviewed"
    assert session is not None
    assert session.feature_extraction_status == "completed"
    assert any(log.event_type == "transcript_reviewed" for log in repo.audit_logs)
    assert any(log.event_type == "features_extracted" for log in repo.audit_logs)


def test_extract_features_requires_reviewed_transcript():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    try:
        repo.extract_features_for_session("SESSION-002", therapist)
    except ValueError as exc:
        assert "therapist-reviewed transcript" in str(exc)
    else:
        raise AssertionError("Expected ValueError before transcript review.")


def test_extract_features_uses_full_14_feature_schema_after_review():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None
    transcript = repo.create_transcript_for_session(
        session_id="SESSION-002",
        user=therapist,
        transcript_text=VALID_CHAT,
        original_filename="session_002.cha",
    )
    repo.mark_transcript_reviewed(transcript.transcript_id, therapist)

    feature_row = repo.extract_features_for_session("SESSION-002", therapist)

    assert feature_row.feature_schema_version == "14-feature-schema"
    assert tuple(feature_row.features.keys()) == tuple(FEATURES)
    assert feature_row.extraction_status == "completed"
    assert repo.sessions["SESSION-002"].feature_extraction_status == "completed"
    assert any(log.event_type == "features_extracted" and log.target_id == "SESSION-002" for log in repo.audit_logs)


def test_generate_ai_decision_support_requires_features():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    try:
        repo.generate_ai_screening_output_for_session("SESSION-002", therapist)
    except ValueError as exc:
        assert "Extracted features are required" in str(exc)
    else:
        raise AssertionError("Expected ValueError before feature extraction.")


def test_generate_ai_decision_support_output_avoids_diagnostic_language():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None
    transcript = repo.create_transcript_for_session(
        session_id="SESSION-002",
        user=therapist,
        transcript_text=VALID_CHAT,
        original_filename="session_002.cha",
    )
    repo.mark_transcript_reviewed(transcript.transcript_id, therapist)
    repo.extract_features_for_session("SESSION-002", therapist)

    output = repo.generate_ai_screening_output_for_session("SESSION-002", therapist)

    assert output.output_id == "AI-OUTPUT-002"
    assert output.screening_support_score is not None
    assert output.concern_level in {"low_concern", "watchful_review", "moderate_concern"}
    assert output.top_contributing_features
    assert output.evidence_items
    forbidden = "diagnosis"
    assert forbidden not in output.explanation.lower()
    assert repo.sessions["SESSION-002"].ai_analysis_status == "completed"
    assert repo.sessions["SESSION-002"].report_status == "pending"
    assert any(log.event_type == "ai_output_generated" and log.target_id == output.output_id for log in repo.audit_logs)


def test_progress_summary_includes_score_timeline_goal_progress_and_radar():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None
    session = repo.create_session(
        case_id="CASE-001",
        user=therapist,
        session_date="2026-05-27",
        session_type="therapy_session",
        notes="Phase 6 progress session.",
    )
    transcript = repo.create_transcript_for_session(
        session_id=session.session_id,
        user=therapist,
        transcript_text=VALID_CHAT,
        original_filename="session_004.cha",
    )
    repo.mark_transcript_reviewed(transcript.transcript_id, therapist)
    repo.extract_features_for_session(session.session_id, therapist)
    repo.generate_ai_screening_output_for_session(session.session_id, therapist)

    summary = repo.progress_summary_for_case("CASE-001", therapist)

    assert summary["case_id"] == "CASE-001"
    assert len(summary["score_timeline"]) == 2
    assert summary["score_timeline"][-1]["screening_support_score"] is not None
    assert summary["therapy_goal_progress"]["total"] == 2
    assert summary["therapy_goal_progress"]["completed"] == 1
    assert {row["metric"] for row in summary["before_after_radar"]} >= {"mlu", "ttr"}
    assert "mlu" in summary["feature_trends"]
    assert "clinical decision-support prototype" in summary["safety_disclaimer"]


def test_progress_report_generation_creates_export_record_and_audit_event():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    report = repo.generate_progress_report_for_case("CASE-001", therapist)

    assert report.report_id == "REPORT-001"
    assert report.case_id == "CASE-001"
    assert report.export_status == "completed"
    assert "Progress Report: CHI-A01" in report.content_markdown
    assert "does not diagnose ASD" in report.content_markdown
    assert "diagnosed with" not in report.content_markdown.lower()
    assert any(log.event_type == "report_exported" and log.target_id == report.report_id for log in repo.audit_logs)


def test_clinical_user_cannot_generate_progress_report_for_another_owner_case():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    try:
        repo.generate_progress_report_for_case("CASE-003", therapist)
    except PermissionError:
        pass
    else:
        raise AssertionError("Expected PermissionError for cross-owner progress report.")


def test_clinical_user_cannot_generate_features_for_another_owner_session():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    try:
        repo.extract_features_for_session("SESSION-003", therapist)
    except PermissionError:
        pass
    else:
        raise AssertionError("Expected PermissionError for cross-owner feature extraction.")


def test_safety_disclaimer_is_available_for_ui_contract():
    assert "clinical decision-support prototype" in SAFETY_DISCLAIMER
    assert "does not diagnose ASD" in SAFETY_DISCLAIMER
    assert "qualified clinical judgment" in SAFETY_DISCLAIMER


def test_evidence_flag_detection():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None

    summary = repo.progress_summary_for_case("CASE-001", therapist)
    timeline_entry = summary["score_timeline"][0]
    assert timeline_entry["evidence_items"]

    from src.feature_schema import FEATURE_DOCS
    expected_meanings = [
        FEATURE_DOCS["unintelligible_ratio"].clinical_meaning,
        FEATURE_DOCS["echolalia_ratio"].clinical_meaning,
        FEATURE_DOCS["ttr"].clinical_meaning,
    ]
    assert timeline_entry["evidence_items"] == expected_meanings

