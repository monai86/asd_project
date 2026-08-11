"""Contract tests for auditable v1.7.0 Findings projections."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import pytest
from app.schemas.clinical import Transcript, Utterance
from app.schemas.speech_pipeline import AudioNormalizationProvenance
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    AudioFileMetadata,
    ChildCase,
    TherapySession,
    MappingStatus,
    NormalizedAudioAsset,
    QaStatus,
    ReviewedSpeakerMapping,
    SpeakerMappingEntry,
    TranscriptAttestation,
)
from app.services.findings_service import project_findings_for_session
from fastapi.testclient import TestClient
from app.main import app


def _seed_attested_v170_session(repo: MockRepository) -> tuple[TherapySession, Transcript]:
    case = ChildCase(
        organization_id="org_test",
        case_id="case_test_001",
        child_code="C01",
        age_months=36,
        child_id_hash="hash_001",
        consent_status="VERIFIED",
        care_team_user_ids=["therapist_001"],
    )
    repo.cases[case.case_id] = case

    session = TherapySession(
        organization_id=case.organization_id,
        case_id=case.case_id,
        session_id="session_findings_001",
        session_date="2026-08-11",
        session_type="assessment",
        therapist_id="therapist_001",
    )
    repo.sessions[session.session_id] = session

    audio = AudioFileMetadata(
        organization_id=session.organization_id,
        case_id=session.case_id,
        session_id=session.session_id,
        audio_file_id="audio_001",
        original_filename="sample.wav",
        content_type="audio/wav",
        size_bytes=1000,
        source_asset_version=1,
        checksum_sha256="a" * 64,
    )
    repo.audio_files["audio_001"] = audio

    profile_name = "v1.7.0-standard-wav-profile"
    prof_sha = sha256(profile_name.encode("utf-8")).hexdigest()
    normalized = NormalizedAudioAsset(
        organization_id=session.organization_id,
        session_id=session.session_id,
        asset_version=1,
        source_audio_file_id=audio.audio_file_id,
        source_asset_version=audio.source_asset_version,
        object_key="normalized/sample.wav",
        source_checksum_sha256="a" * 64,
        normalized_checksum_sha256="b" * 64,
        format="wav_pcm_s16le",
        duration_ms=60000,
        sample_rate_hz=16000,
        channels=1,
        frame_count=960000,
        decoder_name="soundfile",
        decoder_version="0.14.0",
        conversion_command_profile=profile_name,
        verification_status="verified",
        provenance=AudioNormalizationProvenance(
            source_size_bytes=32000,
            source_detected_format="wav",
            source_duration_ms=60000,
            source_frame_count=960000,
            source_sample_rate_hz=16000,
            source_channels=1,
            normalized_size_bytes=48000,
            boundary_frames_verified=True,
            decoder_library_name="soundfile",
            decoder_library_version="0.14.0",
            mixer_name="numpy",
            mixer_version="2",
            resampler_name="none",
            resampler_version="none",
            writer_name="wave",
            writer_version="stdlib",
            writer_library_name="python",
            writer_library_version="3.12",
            processing_dtype="float32",
            streaming_block_frames=4096,
            overlap_frames=0,
            resample_window="none",
            filter_profile="none",
            padding_policy="none",
            normalization_profile=profile_name,
            profile_checksum_sha256=prof_sha,
        ),
        created_at=datetime.now(timezone.utc),
    )
    repo.create_normalized_audio_asset(normalized)

    transcript = Transcript(
        organization_id=session.organization_id,
        case_id=session.case_id,
        session_id=session.session_id,
        transcript_id="transcript_findings_001",
        version=1,
        source="asr_draft:local_faster_whisper",
        raw_text="@Begin\n*CHI:\tน้อง กิน ข้าว.\n*THE:\tทาน อร่อย ไหม.\n@End",
        utterances=[
            Utterance(utterance_id="u1", speaker="CHI", text="น้อง กิน ข้าว.", start_ms=1000, end_ms=3000, review_status="reviewed"),
            Utterance(utterance_id="u2", speaker="THE", text="ทาน อร่อย ไหม.", start_ms=3500, end_ms=5000, review_status="reviewed"),
        ],
        qa_status=QaStatus.pass_,
        therapist_attested=True,
    )
    repo.transcripts[transcript.transcript_id] = transcript
    session.transcript_id = transcript.transcript_id

    mapping = ReviewedSpeakerMapping(
        organization_id=session.organization_id,
        session_id=session.session_id,
        mapping_id="map_001",
        mapping_version=1,
        transcript_id=transcript.transcript_id,
        transcript_version=1,
        entries=[
            SpeakerMappingEntry(
                temporary_speaker_id="CHI",
                confirmed_chat_code="CHI",
                participant_role="target_child",
                disposition="target",
                affected_utterance_ids=["u1"],
                reviewed_utterance_ids=["u1"],
            ),
            SpeakerMappingEntry(
                temporary_speaker_id="THE",
                confirmed_chat_code="THE",
                participant_role="therapist",
                disposition="non_target",
                affected_utterance_ids=["u2"],
                reviewed_utterance_ids=["u2"],
            ),
        ],
        confirmed_by_user_id="therapist_001",
        confirmed_by_role="therapist",
        confirmed_at=datetime.now(timezone.utc),
        status=MappingStatus.confirmed,
    )
    repo.create_speaker_mapping(mapping)

    from app.services.qa_policy_service import current_qa_outcomes, acknowledge_limitation
    from app.schemas.clinical import LimitationAcknowledgmentRequest, AttestationRequest
    from app.services.transcript_service import attest
    current_outcomes = current_qa_outcomes(repo, transcript.transcript_id)
    ack_ids = []
    for item in current_outcomes:
        if item.disposition.value == "acknowledgeable_limitation":
            ack = acknowledge_limitation(
                repo,
                transcript.transcript_id,
                item.code,
                LimitationAcknowledgmentRequest(expected_transcript_version=1, structured_reason="reviewed_and_accepted"),
                therapist_user_id="therapist_001",
                therapist_role="therapist",
            )
            ack_ids.append(ack.acknowledgment_id)

    attest(repo, transcript.transcript_id, AttestationRequest(reason="clinical review", acknowledgment_ids=ack_ids), actor_id="therapist_001")

    from app.services.chat_roundtrip_service import create_verified_chat_export
    create_verified_chat_export(repo, transcript.transcript_id)

    return session, transcript


def test_project_findings_for_session_creates_auditable_projection() -> None:
    repo = MockRepository()
    session, transcript = _seed_attested_v170_session(repo)

    findings = project_findings_for_session(repo, session.session_id)

    assert findings is not None
    assert findings.session_id == session.session_id
    assert findings.transcript_id == transcript.transcript_id
    assert findings.transcript_version == 1
    assert findings.speaker_mapping_id == "map_001"
    assert findings.attestation_id.startswith("att_")
    assert len(findings.features) > 0
    for feat in findings.features:
        assert feat.clinical_caution == "Descriptive engineering-testbed value; it is not diagnostic or normative."


def test_findings_route_returns_200_for_authenticated_therapist() -> None:
    repo = MockRepository()
    session, _ = _seed_attested_v170_session(repo)

    client = TestClient(app)

    from app.api.v1.dependencies import get_repository
    from app.core.security import CurrentUser, get_current_user
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user_id="therapist_001", role="therapist", organization_id="org_test")

    try:
        response = client.post(f"/api/v1/sessions/{session.session_id}/findings")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session.session_id
        assert len(data["features"]) > 0

        get_resp = client.get(f"/api/v1/sessions/{session.session_id}/findings")
        assert get_resp.status_code == 200
        assert get_resp.json()["findings_id"] == data["findings_id"]
    finally:
        app.dependency_overrides.clear()
