from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from src.clinical_speech.batchalign_service import check_batchalign_dependencies, run_batchalign  # noqa: E402
from src.clinical_speech.chat_exporter import (  # noqa: E402
    ChatExportMetadata,
    build_reviewed_chat_export,
    format_chat_time,
    format_media_marker,
    parse_chat_to_lines,
)
from src.clinical_speech.clan_service import (  # noqa: E402
    StructuredClanRun,
    parse_mlu_output,
    run_clan_command,
)
from src.clinical_speech.feature_extractor import extract_clinical_features  # noqa: E402
from src.clinical_speech.models import NormalizedTranscriptLine  # noqa: E402
from src.clinical_workflow import MockClinicalRepository  # noqa: E402
from src.therapist_backend.app import create_app  # noqa: E402


def _lines(reviewed: bool = True) -> list[NormalizedTranscriptLine]:
    return [
        NormalizedTranscriptLine(
            session_id="SESSION-X",
            speaker_code="INV",
            speaker_role="therapist",
            start_ms=0,
            end_ms=1000,
            text="what do you want ?",
            is_reviewed=reviewed,
            line_id="L1",
            line_number=1,
        ),
        NormalizedTranscriptLine(
            session_id="SESSION-X",
            speaker_code="CHI",
            speaker_role="child",
            start_ms=1400,
            end_ms=2400,
            text="want cookie .",
            reviewed_text="you want cookie .",
            is_reviewed=reviewed,
            line_id="L2",
            line_number=2,
        ),
        NormalizedTranscriptLine(
            session_id="SESSION-X",
            speaker_code="CHI",
            speaker_role="child",
            start_ms=5000,
            end_ms=5600,
            text="cookie cookie .",
            is_reviewed=reviewed,
            line_id="L3",
            line_number=3,
        ),
        NormalizedTranscriptLine(
            session_id="SESSION-X",
            speaker_code="MOT",
            speaker_role="parent",
            start_ms=6200,
            end_ms=7200,
            text="good talking .",
            is_reviewed=reviewed,
            line_id="L4",
            line_number=4,
        ),
    ]


def _repo() -> MockClinicalRepository:
    current = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)

    def now() -> datetime:
        nonlocal current
        current = current + timedelta(minutes=1)
        return current

    return MockClinicalRepository(now_provider=now)


def test_timestamp_formatting_and_media_marker():
    assert format_chat_time(3723456) == "01:02:03.456"
    assert format_media_marker(1400, 2400) == "\x151400_2400\x15"


def test_chat_export_uses_reviewed_text_and_media_bullets():
    chat = build_reviewed_chat_export(
        _lines(),
        metadata=ChatExportMetadata(
            session_id="SESSION-X",
            media_filename="session.wav",
            child_id="CHI-A01",
            child_age_months=48,
            child_sex="female",
        ),
    )

    assert chat.startswith("@UTF8\n@Begin\n")
    assert "@Languages:\teng" in chat
    assert "@Participants:" in chat
    assert "@Media:\tsession, audio" in chat
    assert "*CHI:\tyou want cookie . \x151400_2400\x15" in chat
    assert "*CHI:\twant cookie ." not in chat
    assert chat.endswith("@End\n")


def test_chat_export_blocks_unreviewed_lines_by_default():
    try:
        build_reviewed_chat_export(
            _lines(reviewed=False),
            metadata=ChatExportMetadata(session_id="SESSION-X"),
        )
    except ValueError as exc:
        assert "review sign-off" in str(exc)
    else:
        raise AssertionError("Expected unreviewed export to fail.")


def test_parse_chat_to_lines_supports_media_bullets_and_tim_tiers():
    chat = (
        "@Begin\n"
        "@Languages:\teng\n"
        "*CHI:\thello . \x15100_900\x15\n"
        "*INV:\ttell me more .\n"
        "%tim:\t00:00:01.000-00:00:02.250\n"
        "@End\n"
    )
    lines = parse_chat_to_lines(chat, session_id="SESSION-X")

    assert len(lines) == 2
    assert lines[0].speaker_code == "CHI"
    assert lines[0].start_ms == 100
    assert lines[0].end_ms == 900
    assert lines[1].speaker_code == "INV"
    assert lines[1].start_ms == 1000
    assert lines[1].end_ms == 2250


def test_feature_extraction_labels_possible_markers_for_review():
    features = extract_clinical_features(_lines(), age_months=48)

    assert features["core_features"]["total_utterances"] == 2
    assert features["core_features"]["total_words"] == 5
    assert features["core_features"]["pronoun_reversal_count"] == 1
    assert features["core_features"]["echolalia_count"] >= 1
    assert features["optional_indicators"]["therapist_utterances"] == 1
    assert features["optional_indicators"]["caregiver_utterances"] == 1
    assert features["optional_indicators"]["response_latency_avg"] == 0.4
    assert all(flag["label"] == "possible" for flag in features["review_flags"])
    assert all(flag["requires_clinician_review"] is True for flag in features["review_flags"])
    assert "does not diagnose ASD" in features["safety_labels"]


def test_batchalign_dependency_error_is_structured():
    check = check_batchalign_dependencies(
        env={"ASD_ENABLE_BATCHALIGN": "false"},
        command_locator=lambda _command: None,
    )

    assert check.available is False
    assert check.enabled is False
    assert any("ASD_ENABLE_BATCHALIGN" in error for error in check.errors)
    assert any("Batchalign2" in error for error in check.errors)
    assert any("FFmpeg" in error for error in check.errors)


def test_batchalign_run_without_dependencies_does_not_crash(tmp_path):
    result = run_batchalign(
        "transcribe",
        tmp_path,
        tmp_path / "out",
        env={"ASD_ENABLE_BATCHALIGN": "true"},
        command_locator=lambda command: None if command in {"batchalign", "ffmpeg"} else "/bin/true",
    )

    assert result.ok is False
    assert result.returncode is None
    assert "Batchalign2" in result.stderr


def test_clan_missing_command_returns_setup_error(tmp_path):
    chat_path = tmp_path / "sample.cha"
    chat_path.write_text("@Begin\n*CHI:\thello .\n@End\n", encoding="utf-8")

    result = run_clan_command(
        StructuredClanRun(command="mlu", chat_path=chat_path),
        command_locator=lambda _command: None,
    )

    assert result.ok is False
    assert result.returncode is None
    assert "mlu" in result.stderr
    assert result.parse_warnings == ["clan_unavailable"]


def test_clan_rejects_unsafe_kwal_terms(tmp_path):
    chat_path = tmp_path / "sample.cha"
    chat_path.write_text("@Begin\n*CHI:\thello .\n@End\n", encoding="utf-8")

    try:
        run_clan_command(
            StructuredClanRun(command="kwal", chat_path=chat_path, kwal_terms=("hello;rm",)),
            command_locator=lambda _command: "/fake/clan",
        )
    except ValueError as exc:
        assert "KWAL terms" in str(exc)
    else:
        raise AssertionError("Expected unsafe KWAL term to fail.")


def test_clan_mlu_parser_is_conservative():
    metrics, warnings, confidence = parse_mlu_output(
        "Number of utterances = 3\nMLU words = 2.50\nMLU morphemes = 3.10\n"
    )

    assert metrics["utterances"] == 3
    assert metrics["mlu_words"] == 2.5
    assert metrics["mlu_morphemes"] == 3.1
    assert warnings == []
    assert confidence == "medium"


def test_repository_export_and_feature_extraction_use_reviewed_lines():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None
    transcript = repo.create_transcript_for_session(
        session_id="SESSION-002",
        user=therapist,
        transcript_text=(
            "@Begin\n"
            "@Languages:\teng\n"
            "@Participants:\tCHI Child Target_Child, INV Investigator Investigator\n"
            "@ID:\teng|Mock|CHI|4;00.00|female|||Target_Child|||\n"
            "@ID:\teng|Mock|INV|||||Investigator|||\n"
            "*INV:\twhat do you want ?\n"
            "%tim:\t00:00:00.000-00:00:01.000\n"
            "*CHI:\twant train .\n"
            "%tim:\t00:00:01.500-00:00:02.500\n"
            "@End\n"
        ),
        original_filename="session_002.cha",
    )
    line = next(
        line
        for line in repo.transcript_lines.values()
        if line.transcript_id == transcript.transcript_id and line.speaker_code == "CHI"
    )
    repo.update_transcript_line_for_user(
        transcript.transcript_id,
        line.line_id,
        therapist,
        utterance_text="you want train .",
        reviewed=True,
        expected_version=1,
    )
    repo.signoff_transcript_for_session("SESSION-002", therapist)

    exported = repo.export_reviewed_chat_for_session("SESSION-002", therapist)
    features = repo.extract_features_for_session("SESSION-002", therapist)

    assert "*CHI:\tyou want train . \x151500_2500\x15" in exported
    assert "*CHI:\twant train ." not in exported
    assert features.core_features["pronoun_reversal_count"] == 1
    assert features.optional_indicators["response_latency_avg"] == 0.5
    artifacts = repo.list_clinical_speech_artifacts_for_session_for_user("SESSION-002", therapist)
    artifact_types = {artifact.artifact_type for artifact in artifacts}
    assert {"reviewed_chat", "feature_output"}.issubset(artifact_types)
    assert all(artifact.source_revision for artifact in artifacts if artifact.artifact_type in artifact_types)


def test_artifact_freshness_tracks_transcript_line_revisions():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None
    repo.signoff_transcript_for_session("SESSION-001", therapist)

    repo.export_reviewed_chat_for_session("SESSION-001", therapist)
    current_artifacts = repo.list_clinical_speech_artifacts_for_session_for_user("SESSION-001", therapist)
    reviewed_chat = next(artifact for artifact in current_artifacts if artifact.artifact_type == "reviewed_chat")
    assert reviewed_chat.freshness == "current"

    line = next(
        line
        for line in repo.transcript_lines.values()
        if line.transcript_id == "TRANSCRIPT-001" and line.speaker_code == "CHI"
    )
    repo.update_transcript_line_for_user(
        "TRANSCRIPT-001",
        line.line_id,
        therapist,
        utterance_text=f"{line.utterance_text} now",
        expected_version=line.version,
    )

    stale_artifacts = repo.list_clinical_speech_artifacts_for_session_for_user("SESSION-001", therapist)
    stale_chat = next(artifact for artifact in stale_artifacts if artifact.artifact_id == reviewed_chat.artifact_id)
    assert stale_chat.freshness == "stale"
    assert stale_chat.metadata["stale_reason"] == "transcript_line_updated"


def test_feature_review_disposition_is_reviewable_not_diagnostic():
    repo = _repo()
    therapist = repo.authenticate("therapist@example.test", "demo-password")
    assert therapist is not None
    repo.signoff_transcript_for_session("SESSION-001", therapist)
    features = repo.extract_features_for_session("SESSION-001", therapist)

    disposition = repo.update_feature_review_disposition(
        features.feature_id,
        "possible_pronoun_reversal",
        therapist,
        disposition="needs_context",
        note="Needs session context before interpretation.",
    )

    assert disposition is not None
    assert disposition.disposition == "needs_context"
    assert disposition.source_revision == features.source_revision
    assert "diagnos" not in disposition.note.lower()


def test_sql_schema_has_clinical_speech_contract_tables():
    schema = (PROJECT_ROOT / "docs/sql/001_initial_clinical_schema.sql").read_text(encoding="utf-8")

    assert "speaker_role text not null default 'other'" in schema
    assert "reviewed_text text" in schema
    assert "word_timestamps jsonb not null default '[]'::jsonb" in schema
    assert "create table clinical_speech_artifacts" in schema
    assert "create table feature_review_dispositions" in schema
    assert "operation_config jsonb not null default '{}'::jsonb" in schema


def test_api_export_reviewed_chat_endpoint():
    repo = _repo()
    therapist = repo.users["user_therapist_001"]
    repo.signoff_transcript_for_session("SESSION-001", therapist)
    client = TestClient(create_app(repo))

    response = client.get(
        "/api/sessions/SESSION-001/transcript/export.cha",
        headers={"X-User-Id": therapist.user_id},
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"].endswith('filename="SESSION-001_reviewed.cha"')
    assert response.text.startswith("@UTF8\n@Begin\n")
    assert "@End" in response.text


def test_api_artifact_job_and_feature_review_contracts():
    repo = _repo()
    therapist = repo.users["user_therapist_001"]
    repo.signoff_transcript_for_session("SESSION-001", therapist)
    features = repo.extract_features_for_session("SESSION-001", therapist)
    client = TestClient(create_app(repo))

    artifacts_response = client.get(
        "/api/sessions/SESSION-001/clinical-speech-artifacts",
        headers={"X-User-Id": therapist.user_id},
    )
    assert artifacts_response.status_code == 200
    artifacts = artifacts_response.json()["artifacts"]
    assert any(artifact["artifact_type"] == "feature_output" for artifact in artifacts)
    assert "storage_key" not in artifacts[0]
    assert "content_text" not in artifacts[0]

    jobs_response = client.get(
        "/api/sessions/SESSION-001/processing-jobs",
        headers={"X-User-Id": therapist.user_id},
    )
    assert jobs_response.status_code == 200
    assert jobs_response.json() == {"jobs": []}

    disposition_response = client.patch(
        f"/api/features/{features.feature_id}/review-flags/possible_pronoun_reversal",
        headers={"X-User-Id": therapist.user_id},
        json={"disposition": "accepted", "note": "Review flag accepted for clinical discussion only."},
    )
    assert disposition_response.status_code == 200
    assert disposition_response.json()["disposition"] == "accepted"

    list_response = client.get(
        f"/api/features/{features.feature_id}/review-flags",
        headers={"X-User-Id": therapist.user_id},
    )
    assert list_response.status_code == 200
    assert list_response.json()["dispositions"][0]["flag_key"] == "possible_pronoun_reversal"
