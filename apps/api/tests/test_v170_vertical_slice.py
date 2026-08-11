"""v1.7.0 End-to-End Vertical Slice Tests.

Tests the full upload-first v1.7.0 speech-to-CHAT pipeline from synthetic audio
through normalization, ASR draft creation, speaker mapping, QA policy,
typed attestation, CHAT export, feature extraction, and Findings projection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import pytest

from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    AudioFileMetadata,
    ChildCase,
    LimitationAcknowledgmentRequest,
    AttestationRequest,
    QaStatus,
    TherapySession,
    Transcript,
    Utterance,
)
from app.schemas.speech_pipeline import (
    AudioNormalizationProvenance,
    LimitationAcknowledgment,
    MappingStatus,
    NormalizedAudioAsset,
    ReviewedSpeakerMapping,
    SpeakerMappingEntry,
)
from app.services.chat_roundtrip_service import create_verified_chat_export
from app.services.findings_service import project_findings_for_session
from app.services.providers.descriptive_v170_provider import extract_descriptive_feature_results
from app.services.qa_policy_service import acknowledge_limitation, current_qa_outcomes
from app.services.transcript_service import attest


def _seed_v170_vertical_case(repo: MockRepository) -> tuple[TherapySession, AudioFileMetadata, NormalizedAudioAsset]:
    case = ChildCase(
        organization_id="org_v170",
        case_id="case_v170_001",
        child_code="C170",
        age_months=36,
        child_id_hash="hash_v170",
        consent_status="VERIFIED",
        care_team_user_ids=["therapist_v170"],
    )
    repo.cases[case.case_id] = case

    session = TherapySession(
        organization_id=case.organization_id,
        case_id=case.case_id,
        session_id="session_v170_slice",
        session_date="2026-08-11",
        session_type="assessment",
        therapist_id="therapist_v170",
    )
    repo.sessions[session.session_id] = session

    audio = AudioFileMetadata(
        organization_id=session.organization_id,
        case_id=session.case_id,
        session_id=session.session_id,
        audio_file_id="audio_v170_slice",
        original_filename="synthetic_thai_1m.wav",
        content_type="audio/wav",
        size_bytes=1920000,
        source_asset_version=1,
        checksum_sha256="c" * 64,
        upload_status="uploaded",
    )
    repo.audio_files[audio.audio_file_id] = audio

    profile_name = "v1.7.0-standard-wav-profile"
    prof_sha = sha256(profile_name.encode("utf-8")).hexdigest()
    normalized = NormalizedAudioAsset(
        organization_id=session.organization_id,
        session_id=session.session_id,
        asset_version=1,
        source_audio_file_id=audio.audio_file_id,
        source_asset_version=audio.source_asset_version,
        object_key="normalized/synthetic_thai_1m.wav",
        source_checksum_sha256=audio.checksum_sha256,
        normalized_checksum_sha256="d" * 64,
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
            source_size_bytes=audio.size_bytes,
            source_detected_format="wav",
            source_duration_ms=60000,
            source_frame_count=960000,
            source_sample_rate_hz=16000,
            source_channels=1,
            normalized_size_bytes=1920000,
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
    return session, audio, normalized


@pytest.mark.audio
def test_full_v170_synthetic_audio_to_findings_vertical_slice() -> None:
    repo = MockRepository()
    session, audio, normalized = _seed_v170_vertical_case(repo)

    # 1. Draft transcript creation
    transcript = Transcript(
        organization_id=session.organization_id,
        case_id=session.case_id,
        session_id=session.session_id,
        transcript_id="transcript_v170_slice",
        version=1,
        source="asr_draft:local_faster_whisper",
        raw_text="@Begin\n*CHI:\tน้อง กิน ข้าว.\n*THE:\tทาน อร่อย ไหม.\n@End",
        utterances=[
            Utterance(utterance_id="u1", speaker="CHI", text="น้อง กิน ข้าว.", start_ms=1000, end_ms=3000, review_status="reviewed"),
            Utterance(utterance_id="u2", speaker="THE", text="ทาน อร่อย ไหม.", start_ms=3500, end_ms=5000, review_status="reviewed"),
        ],
        qa_status=QaStatus.pass_,
        therapist_attested=False,
    )
    repo.transcripts[transcript.transcript_id] = transcript
    session.transcript_id = transcript.transcript_id

    # 2. Speaker mapping confirmation
    mapping = ReviewedSpeakerMapping(
        organization_id=session.organization_id,
        session_id=session.session_id,
        mapping_id="map_v170_slice",
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
        confirmed_by_user_id="therapist_v170",
        confirmed_by_role="therapist",
        confirmed_at=datetime.now(timezone.utc),
        status=MappingStatus.confirmed,
    )
    repo.create_speaker_mapping(mapping)

    # 3. QA policy outcomes and typed acknowledgment
    outcomes = current_qa_outcomes(repo, transcript.transcript_id)
    ack_ids = []
    for item in outcomes:
        if item.disposition.value == "acknowledgeable_limitation":
            ack = acknowledge_limitation(
                repo,
                transcript.transcript_id,
                item.code,
                LimitationAcknowledgmentRequest(expected_transcript_version=1, structured_reason="reviewed_and_accepted"),
                therapist_user_id="therapist_v170",
                therapist_role="therapist",
            )
            ack_ids.append(ack.acknowledgment_id)

    # 4. Typed attestation
    attest(repo, transcript.transcript_id, AttestationRequest(reason="clinical verification", acknowledgment_ids=ack_ids), actor_id="therapist_v170")

    # 5. Verified CHAT export
    export = create_verified_chat_export(repo, transcript.transcript_id)
    assert export is not None
    assert export.canonical_checksum_sha256

    # 6. Feature extraction
    features = extract_descriptive_feature_results(repo, transcript.transcript_id)
    assert len(features) > 0

    # 7. Findings projection
    findings = project_findings_for_session(repo, session.session_id)
    assert findings is not None
    assert findings.session_id == session.session_id
    assert findings.transcript_id == transcript.transcript_id
    assert findings.speaker_mapping_id == mapping.mapping_id
    assert len(findings.features) == len(features)
    for feat in findings.features:
        assert feat.clinical_caution == "Descriptive engineering-testbed value; it is not diagnostic or normative."


def test_v170_vertical_slice_failure_paths() -> None:
    repo = MockRepository()

    # 1. Unconfirmed speaker mapping blocks export
    session, audio, normalized = _seed_v170_vertical_case(repo)
    transcript = Transcript(
        organization_id=session.organization_id,
        case_id=session.case_id,
        session_id=session.session_id,
        transcript_id="transcript_unconfirmed",
        version=1,
        source="asr_draft:local_faster_whisper",
        raw_text="@Begin\n*CHI:\tน้อง.\n@End",
        utterances=[Utterance(utterance_id="u1", speaker="CHI", text="น้อง.", start_ms=1000, end_ms=2000)],
        qa_status=QaStatus.pass_,
    )
    repo.transcripts[transcript.transcript_id] = transcript

    with pytest.raises(ValueError, match="SPEAKER_MAPPING_REQUIRED"):
        create_verified_chat_export(repo, transcript.transcript_id)
