from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from fastapi.testclient import TestClient

from app.repositories.mock_repository import MockRepository
from app.api.v1.dependencies import get_repository
from app.main import app
from app.schemas.clinical import (
    AttestationRequest,
    AudioFileMetadata,
    QaStatus,
    ReviewStatus,
    Transcript,
    Utterance,
)
from app.schemas.speech_pipeline import (
    MappingStatus,
    ReviewedSpeakerMapping,
    SpeakerMappingEntry,
    AudioNormalizationProvenance,
    NormalizedAudioAsset,
)
from app.services.chat_roundtrip_service import verify_chat_round_trip
from app.services.chat_subset import CanonicalChatDocument, CanonicalChatUtterance, CanonicalParticipant


def _document() -> CanonicalChatDocument:
    return CanonicalChatDocument(
        language_codes=("tha",),
        media_reference="fixture-roundtrip",
        participants=(
            CanonicalParticipant(
                code="CHI",
                display_name="Child",
                role="Target_Child",
                id_fields=("tha", "LinguaLens", "CHI", "", "", "", "", "Target_Child", "", ""),
            ),
            CanonicalParticipant(
                code="THE",
                display_name="Therapist",
                role="Therapist",
                id_fields=("tha", "LinguaLens", "THE", "", "", "", "", "Therapist", "", ""),
            ),
        ),
        utterances=(
            CanonicalChatUtterance(
                utterance_id="segment-1",
                speaker_code="CHI",
                reviewed_text_nfc="สวัสดี",
                start_ms=0,
                end_ms=900,
                terminator=".",
            ),
            CanonicalChatUtterance(
                utterance_id="segment-2",
                speaker_code="THE",
                reviewed_text_nfc="ขอบคุณ",
                start_ms=900,
                end_ms=1500,
                terminator=".",
            ),
        ),
    )


def test_round_trip_requires_semantic_equality_and_byte_stable_reexport() -> None:
    result = verify_chat_round_trip(_document())

    assert result.status == "verified"
    assert not result.errors
    assert result.export_a == result.export_b
    assert result.export_a_checksum_sha256 == result.export_b_checksum_sha256
    assert result.input_semantic_checksum_sha256 == result.output_semantic_checksum_sha256


def test_round_trip_reports_loss_as_structured_failure() -> None:
    result = verify_chat_round_trip(_document(), mutate_export=lambda value: value.replace("ขอบคุณ", ""))

    assert result.status == "failed"
    assert any(error.code == "CHAT_TEXT_CHANGED" for error in result.errors)
    assert all(error.disposition == "integrity_blocker" for error in result.errors)


def test_canonical_document_builder_uses_confirmed_mapping_and_reviewed_metadata() -> None:
    repo = MockRepository()
    transcript = Transcript(
        transcript_id="transcript-builder-1",
        session_id="session-builder-1",
        case_id="case-builder-1",
        source="asr_draft:local_faster_whisper",
        raw_text="\n".join(
            [
                "@Begin",
                "@Languages:\ttha",
                "@Participants:\tCHI Child Target_Child, THE Therapist Therapist",
                "@End",
            ]
        ),
        utterances=[
            Utterance(
                utterance_id="u-child",
                speaker="SPK_01",
                temporary_speaker_id="SPK_01",
                text="สวัสดี",
                start_ms=0,
                end_ms=800,
                source="asr",
                review_status="reviewed",
            ),
            Utterance(
                utterance_id="u-therapist",
                speaker="SPK_02",
                temporary_speaker_id="SPK_02",
                text="ขอบคุณ",
                start_ms=800,
                end_ms=1500,
                source="asr",
                review_status="reviewed",
            ),
        ],
        review_status=ReviewStatus.attested,
        therapist_attested=True,
    )
    repo.transcripts[transcript.transcript_id] = transcript
    repo.speaker_mappings[("mapping-builder-1", 1)] = ReviewedSpeakerMapping(
        organization_id="pilot_org_001",
        session_id=transcript.session_id,
        mapping_id="mapping-builder-1",
        mapping_version=1,
        transcript_id=transcript.transcript_id,
        transcript_version=1,
        entries=[
            SpeakerMappingEntry(
                temporary_speaker_id="SPK_01",
                confirmed_chat_code="CHI",
                participant_role="target_child",
                disposition="target",
                affected_utterance_ids=["u-child"],
                reviewed_utterance_ids=["u-child"],
            ),
            SpeakerMappingEntry(
                temporary_speaker_id="SPK_02",
                confirmed_chat_code="THE",
                participant_role="therapist",
                disposition="non_target",
                affected_utterance_ids=["u-therapist"],
                reviewed_utterance_ids=["u-therapist"],
            ),
        ],
        confirmed_by_user_id="therapist-builder",
        confirmed_by_role="therapist",
        confirmed_at=datetime.now(timezone.utc),
        status=MappingStatus.confirmed,
    )

    from app.services.chat_roundtrip_service import canonical_document_from_repo

    document = canonical_document_from_repo(repo, transcript.transcript_id)

    assert [item.speaker_code for item in document.utterances] == ["CHI", "THE"]
    assert [item.reviewed_text_nfc for item in document.utterances] == ["สวัสดี", "ขอบคุณ"]
    assert document.language_codes == ("tha",)


def test_attestation_persists_typed_current_record_for_chat_export_gate() -> None:
    from app.services import transcript_service

    repo = MockRepository()
    session = repo.sessions["session_demo_001"]
    transcript = Transcript(
        transcript_id="transcript-attestation-1",
        session_id=session.session_id,
        case_id=session.case_id,
        source="asr_draft:local_faster_whisper",
        raw_text="@Begin\n@Languages:\ttha\n@Participants:\tCHI Child Target_Child, THE Therapist Therapist\n@ID:\ttha|LinguaLens|CHI|||||Target_Child|||\n@ID:\ttha|LinguaLens|THE|||||Therapist|||\n@End",
        utterances=[
            Utterance(
                utterance_id="u-child-att",
                speaker="SPK_01",
                temporary_speaker_id="SPK_01",
                text="สวัสดี",
                source="asr",
                review_status="reviewed",
            ),
            Utterance(
                utterance_id="u-the-att",
                speaker="SPK_02",
                temporary_speaker_id="SPK_02",
                text="ขอบคุณ",
                source="asr",
                review_status="reviewed",
            ),
        ],
        qa_status=QaStatus.pass_,
        version=1,
    )
    repo.transcripts[transcript.transcript_id] = transcript
    session.transcript_id = transcript.transcript_id
    repo.create_speaker_mapping(
        ReviewedSpeakerMapping(
            organization_id=session.organization_id,
            session_id=session.session_id,
            mapping_id="mapping-attestation-1",
            mapping_version=1,
            transcript_id=transcript.transcript_id,
            transcript_version=1,
            entries=[
                SpeakerMappingEntry(
                    temporary_speaker_id="SPK_01",
                    confirmed_chat_code="CHI",
                    participant_role="target_child",
                    disposition="target",
                    affected_utterance_ids=["u-child-att"],
                    reviewed_utterance_ids=["u-child-att"],
                ),
                SpeakerMappingEntry(
                    temporary_speaker_id="SPK_02",
                    confirmed_chat_code="THE",
                    participant_role="therapist",
                    disposition="non_target",
                    affected_utterance_ids=["u-the-att"],
                    reviewed_utterance_ids=["u-the-att"],
                ),
            ],
            confirmed_by_user_id="therapist-attestation",
            confirmed_by_role="therapist",
            confirmed_at=datetime.now(timezone.utc),
            status=MappingStatus.confirmed,
        )
    )

    transcript_service.attest(
        repo,
        transcript.transcript_id,
        AttestationRequest(reason="Reviewed current draft."),
        actor_id="therapist-attestation",
        attested_by="Therapist",
    )

    typed = repo.get_current_transcript_attestation(transcript.transcript_id)
    assert typed is not None
    assert typed.transcript_version == 1
    assert typed.speaker_mapping_id == "mapping-attestation-1"


def test_verified_chat_export_requires_current_normalized_audio_and_persists_bytes() -> None:
    from app.services import transcript_service
    from app.services.chat_roundtrip_service import create_verified_chat_export

    repo = MockRepository()
    session = repo.sessions["session_demo_001"]
    transcript = Transcript(
        transcript_id="transcript-export-1",
        session_id=session.session_id,
        case_id=session.case_id,
        source="asr_draft:local_faster_whisper",
        raw_text="@Begin\n@Languages:\ttha\n@Participants:\tCHI Child Target_Child, THE Therapist Therapist\n@ID:\ttha|LinguaLens|CHI|||||Target_Child|||\n@ID:\ttha|LinguaLens|THE|||||Therapist|||\n@End",
        utterances=[
            Utterance(utterance_id="u-export-child", speaker="SPK_01", temporary_speaker_id="SPK_01", text="สวัสดี", start_ms=0, end_ms=800, source="asr", review_status="reviewed"),
            Utterance(utterance_id="u-export-the", speaker="SPK_02", temporary_speaker_id="SPK_02", text="ขอบคุณ", start_ms=800, end_ms=1500, source="asr", review_status="reviewed"),
        ],
        qa_status=QaStatus.pass_,
        version=1,
    )
    repo.transcripts[transcript.transcript_id] = transcript
    session.transcript_id = transcript.transcript_id
    repo.create_speaker_mapping(
        ReviewedSpeakerMapping(
            organization_id=session.organization_id,
            session_id=session.session_id,
            mapping_id="mapping-export-1",
            mapping_version=1,
            transcript_id=transcript.transcript_id,
            transcript_version=1,
            entries=[
                SpeakerMappingEntry(temporary_speaker_id="SPK_01", confirmed_chat_code="CHI", participant_role="target_child", disposition="target", affected_utterance_ids=["u-export-child"], reviewed_utterance_ids=["u-export-child"]),
                SpeakerMappingEntry(temporary_speaker_id="SPK_02", confirmed_chat_code="THE", participant_role="therapist", disposition="non_target", affected_utterance_ids=["u-export-the"], reviewed_utterance_ids=["u-export-the"]),
            ],
            confirmed_by_user_id="therapist-export",
            confirmed_by_role="therapist",
            confirmed_at=datetime.now(timezone.utc),
            status=MappingStatus.confirmed,
        )
    )
    audio = AudioFileMetadata(
        audio_file_id="audio-export-1",
        session_id=session.session_id,
        case_id=session.case_id,
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=32000,
        checksum_sha256="a" * 64,
        source_asset_version=1,
        upload_status="uploaded",
        retained=True,
    )
    repo.audio_files[audio.audio_file_id] = audio
    profile = "lingualens-wav-mono-16k-v1.7.0"
    provenance = AudioNormalizationProvenance(
        source_size_bytes=32000,
        source_detected_format="wav",
        source_duration_ms=1500,
        source_frame_count=24000,
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
        normalization_profile=profile,
        profile_checksum_sha256=sha256(profile.encode()).hexdigest(),
    )
    repo.create_normalized_audio_asset(
        NormalizedAudioAsset(
            organization_id=session.organization_id,
            session_id=session.session_id,
            asset_version=1,
            object_key="normalized/export-1.wav",
            source_checksum_sha256="a" * 64,
            normalized_checksum_sha256="b" * 64,
            format="wav_pcm_s16le",
            duration_ms=1500,
            sample_rate_hz=16000,
            channels=1,
            frame_count=24000,
            decoder_name="soundfile",
            decoder_version="0.14.0",
            conversion_command_profile=profile,
            verification_status="verified",
            provenance=provenance,
            source_audio_file_id=audio.audio_file_id,
            source_asset_version=1,
            created_at=datetime.now(timezone.utc),
        )
    )
    transcript_service.attest(repo, transcript.transcript_id, AttestationRequest(reason="Reviewed."), actor_id="therapist-export", attested_by="Therapist")

    export = create_verified_chat_export(repo, transcript.transcript_id, exported_by="therapist-export")

    assert export.round_trip.status.value == "verified"
    assert export.cha_text is not None and export.cha_text.endswith("\n")
    assert export.canonical_checksum_sha256 == export.round_trip.input_semantic_checksum_sha256
    assert export.round_trip.deterministic_export_checksum_sha256 == sha256(export.cha_text.encode("utf-8")).hexdigest()
    assert export.exported_by_user_id == "therapist-export"


def test_chat_export_routes_only_serve_verified_artifact(monkeypatch) -> None:
    from app.api.v1.routes import transcripts as transcript_routes
    from app.schemas.speech_pipeline import (
        ArtifactStatus,
        ChatExport,
        ChatSemanticRoundTripResult,
        RoundTripStatus,
    )

    repo = MockRepository()
    session = repo.sessions["session_demo_001"]
    transcript = Transcript(
        transcript_id="transcript-route-1",
        session_id=session.session_id,
        case_id=session.case_id,
        source="manual_entry",
        raw_text="@Begin\n@End",
        utterances=[],
        therapist_attested=True,
        qa_status=QaStatus.pass_,
    )
    repo.transcripts[transcript.transcript_id] = transcript
    session.transcript_id = transcript.transcript_id
    record = ChatExport(
        organization_id=session.organization_id,
        session_id=session.session_id,
        export_id="chat-route-1",
        export_version=1,
        transcript_id=transcript.transcript_id,
        transcript_version=1,
        speaker_mapping_id="mapping-route-1",
        speaker_mapping_version=1,
        attestation_id="att-route-1",
        attestation_version=1,
        parser_version="lingualens-chat-parser-v1.7.0",
        serializer_version="lingualens-chat-serializer-v1.7.0",
        subset_version="lingualens-chat-v1.7.0",
        canonical_checksum_sha256="c" * 64,
        source_audio_file_id="audio-route-1",
        source_asset_version=1,
        source_checksum_sha256="a" * 64,
        normalized_asset_version=1,
        normalized_checksum_sha256="b" * 64,
        cha_text="@UTF8\n@Begin\n@End\n",
        round_trip=ChatSemanticRoundTripResult(
            status=RoundTripStatus.verified,
            parser_version="lingualens-chat-parser-v1.7.0",
            serializer_version="lingualens-chat-serializer-v1.7.0",
            subset_version="lingualens-chat-v1.7.0",
            input_semantic_checksum_sha256="d" * 64,
            output_semantic_checksum_sha256="d" * 64,
            deterministic_export_checksum_sha256="c" * 64,
        ),
        status=ArtifactStatus.current,
        created_at=datetime.now(timezone.utc),
    )

    def fake_create(repo_arg, transcript_id, *, exported_by):
        repo_arg.chat_exports[(record.export_id, record.export_version)] = record
        return record

    monkeypatch.setattr(transcript_routes, "create_verified_chat_export", fake_create)
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        client = TestClient(app)
        created = client.post(f"/api/v1/transcripts/{transcript.transcript_id}/chat-exports")
        assert created.status_code == 200
        fetched = client.get(f"/api/v1/chat-exports/{record.export_id}")
        assert fetched.status_code == 200
        downloaded = client.get(f"/api/v1/chat-exports/{record.export_id}/download")
        assert downloaded.status_code == 200
        assert downloaded.text == record.cha_text
    finally:
        app.dependency_overrides.pop(get_repository, None)
