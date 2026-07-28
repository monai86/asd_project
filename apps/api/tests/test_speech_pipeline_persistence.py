from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import threading

import pytest

from app.repositories.mock_repository import JsonFileRepository, MockRepository
from app.schemas.clinical import (
    AsrProfile,
    AsrProvenance,
    ArtifactStatus,
    AudioFileMetadata,
    ChatExport,
    ChatRoundTripError,
    ChatSemanticRoundTripResult,
    FeatureSet,
    FeatureResult,
    FeatureResultStatus,
    FindingsProjection,
    LimitationAcknowledgment,
    NormalizedAudioAsset,
    QaDisposition,
    ReviewStatus,
    ReviewedSpeakerMapping,
    RoundTripStatus,
    SpeakerMappingEntry,
    StalenessCause,
    TokenizerProfileReference,
    Transcript,
    TranscriptAttestation,
)


NOW = datetime(2026, 7, 25, 8, 0, tzinfo=timezone.utc)
SOURCE_SHA = "a" * 64
NORMALIZED_SHA = "b" * 64
CHAT_SHA = "c" * 64
TOKENIZER_SHA = "d" * 64


def _seed_sources(repo) -> None:
    session = repo.sessions["session_demo_001"]
    transcript = Transcript(
        transcript_id="transcript_synthetic_001",
        session_id=session.session_id,
        case_id=session.case_id,
        organization_id=session.organization_id,
        source="synthetic_test",
        raw_text="",
        version=3,
    )
    audio = AudioFileMetadata(
        audio_file_id="audio_synthetic_001",
        organization_id=session.organization_id,
        session_id=session.session_id,
        case_id=session.case_id,
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=32044,
        checksum_sha256=SOURCE_SHA,
        source_asset_version=1,
    )
    repo.transcripts[transcript.transcript_id] = transcript
    repo.audio_files[audio.audio_file_id] = audio
    session.transcript_id = transcript.transcript_id
    if hasattr(repo, "save"):
        repo.save()


def _records() -> dict[str, object]:
    normalized = NormalizedAudioAsset(
        organization_id="pilot_org_001",
        session_id="session_demo_001",
        asset_version=1,
        object_key="synthetic-test-object",
        source_checksum_sha256=SOURCE_SHA,
        normalized_checksum_sha256=NORMALIZED_SHA,
        format="wav_pcm_s16le",
        duration_ms=1000,
        sample_rate_hz=16000,
        channels=1,
        frame_count=16000,
        decoder_name="ffmpeg",
        decoder_version="7.1",
        conversion_command_profile="lingualens-wav-mono-16k-v1.7.0",
        source_audio_file_id="audio_synthetic_001",
        source_asset_version=1,
        created_at=NOW,
    )
    mapping = ReviewedSpeakerMapping(
        organization_id="pilot_org_001",
        session_id="session_demo_001",
        mapping_id="mapping_synthetic_001",
        mapping_version=2,
        transcript_id="transcript_synthetic_001",
        transcript_version=3,
        entries=[
            SpeakerMappingEntry(
                temporary_speaker_id="SPK_01",
                confirmed_chat_code="CHI",
                participant_role="target_child",
                disposition="target",
                affected_utterance_ids=["utt_synthetic_001"],
            )
        ],
        confirmed_by_user_id="therapist_synthetic",
        confirmed_by_role="therapist",
        confirmed_at=NOW,
        status="confirmed",
    )
    acknowledgment = LimitationAcknowledgment(
        organization_id="pilot_org_001",
        session_id="session_demo_001",
        transcript_id="transcript_synthetic_001",
        transcript_version=3,
        acknowledgment_id="ack_synthetic_001",
        acknowledgment_version=1,
        limitation_code="SYNTHETIC_LOW_SIGNAL",
        severity="warning",
        disposition=QaDisposition.acknowledgeable_limitation,
        affected_resource_id="transcript_synthetic_001",
        affected_resource_version="3",
        affected_stage="speech_qa",
        therapist_user_id="therapist_synthetic",
        therapist_role="therapist",
        acknowledged_at=NOW,
        structured_reason="synthetic_fixture_limitation_reviewed",
        validator_version="speech-qa-v1.7.0",
        request_audit_id="audit_synthetic_001",
        status="current",
    )
    attestation = TranscriptAttestation(
        organization_id="pilot_org_001",
        session_id="session_demo_001",
        attestation_id="attestation_synthetic_001",
        attestation_version=1,
        transcript_id="transcript_synthetic_001",
        transcript_version=3,
        speaker_mapping_id="mapping_synthetic_001",
        speaker_mapping_version=2,
        qa_validator_version="speech-qa-v1.7.0",
        acknowledgment_refs=[("ack_synthetic_001", 1)],
        attested_by_user_id="therapist_synthetic",
        attested_by_role="therapist",
        attested_at=NOW,
        request_audit_id="audit_synthetic_002",
        status="current",
    )
    asr_profile = AsrProfile(
        provider_name="faster-whisper",
        provider_version="1.1.0",
        model_id="synthetic-model",
        model_version="v1",
        model_checksum_sha256="e" * 64,
        language_profile="th-en",
    )
    provenance = AsrProvenance(
        job_id="job_synthetic_001",
        profile=asr_profile,
        source_audio_file_id="audio_synthetic_001",
        source_asset_version=1,
        source_checksum_sha256=SOURCE_SHA,
        normalized_asset_version=1,
        normalized_checksum_sha256=NORMALIZED_SHA,
        raw_speaker_labels=["SPK_01"],
        generated_at=NOW,
    )
    chat_export = ChatExport(
        organization_id="pilot_org_001",
        session_id="session_demo_001",
        export_id="chat_synthetic_001",
        export_version=1,
        transcript_id="transcript_synthetic_001",
        transcript_version=3,
        speaker_mapping_id="mapping_synthetic_001",
        speaker_mapping_version=2,
        attestation_id="attestation_synthetic_001",
        attestation_version=1,
        parser_version="lingualens-chat-parser-v1.7.0",
        serializer_version="lingualens-chat-serializer-v1.7.0",
        subset_version="lingualens-chat-v1.7.0",
        canonical_checksum_sha256=CHAT_SHA,
        source_audio_file_id="audio_synthetic_001",
        source_asset_version=1,
        source_checksum_sha256=SOURCE_SHA,
        normalized_asset_version=1,
        normalized_checksum_sha256=NORMALIZED_SHA,
        asr_provenance=provenance,
        round_trip=ChatSemanticRoundTripResult(
            status="verified",
            parser_version="lingualens-chat-parser-v1.7.0",
            serializer_version="lingualens-chat-serializer-v1.7.0",
            subset_version="lingualens-chat-v1.7.0",
            input_semantic_checksum_sha256=CHAT_SHA,
            output_semantic_checksum_sha256=CHAT_SHA,
            deterministic_export_checksum_sha256=CHAT_SHA,
        ),
        status="current",
        created_at=NOW,
    )
    tokenizer = TokenizerProfileReference(
        profile_id="thai-tokenizer-v1.7.0",
        profile_version=1,
        profile_checksum_sha256=TOKENIZER_SHA,
        engine="pythainlp",
        package_version="5.1.2",
        artifact_id="newmm",
        artifact_checksum_sha256="f" * 64,
        custom_vocabulary_version="synthetic-v1",
        custom_vocabulary_checksum_sha256="1" * 64,
    )
    findings = FindingsProjection(
        organization_id="pilot_org_001",
        session_id="session_demo_001",
        findings_id="findings_synthetic_001",
        findings_version=1,
        transcript_id="transcript_synthetic_001",
        transcript_version=3,
        speaker_mapping_id="mapping_synthetic_001",
        speaker_mapping_version=2,
        source_audio_file_id="audio_synthetic_001",
        source_asset_version=1,
        source_checksum_sha256=SOURCE_SHA,
        normalized_asset_version=1,
        normalized_checksum_sha256=NORMALIZED_SHA,
        attestation_id="attestation_synthetic_001",
        attestation_version=1,
        chat_export_id="chat_synthetic_001",
        chat_export_version=1,
        chat_export_checksum_sha256=CHAT_SHA,
        parser_version="lingualens-chat-parser-v1.7.0",
        serializer_version="lingualens-chat-serializer-v1.7.0",
        tokenizer_profile=tokenizer,
        feature_schema_version="descriptive-features-v1.7.0",
        algorithm_version="descriptive-features-v1.7.0",
        algorithm_checksum_sha256="2" * 64,
        features=[
            FeatureResult(
                feature_id="target_token_count",
                feature_version=1,
                status=FeatureResultStatus.unavailable,
                value=None,
                unit="tokens",
                reason_code="TOKENIZER_PROFILE_UNAVAILABLE",
                remediation="Install and verify the pinned tokenizer profile.",
                transcript_id="transcript_synthetic_001",
                transcript_version=3,
                speaker_mapping_id="mapping_synthetic_001",
                speaker_mapping_version=2,
                source_audio_file_id="audio_synthetic_001",
                source_asset_version=1,
                source_checksum_sha256=SOURCE_SHA,
                normalized_asset_version=1,
                normalized_checksum_sha256=NORMALIZED_SHA,
                attestation_id="attestation_synthetic_001",
                attestation_version=1,
                chat_export_id="chat_synthetic_001",
                chat_export_version=1,
                chat_export_checksum_sha256=CHAT_SHA,
                parser_version="lingualens-chat-parser-v1.7.0",
                serializer_version="lingualens-chat-serializer-v1.7.0",
                tokenizer_profile=tokenizer,
                algorithm_version="descriptive-features-v1.7.0",
                algorithm_checksum_sha256="2" * 64,
                generated_at=NOW,
            )
        ],
        acknowledgment_refs=[("ack_synthetic_001", 1)],
        generation_service_version="findings-projector-v1.7.0",
        generated_at=NOW,
        status="current",
    )
    return {
        "normalized": normalized,
        "mapping": mapping,
        "acknowledgment": acknowledgment,
        "attestation": attestation,
        "chat_export": chat_export,
        "findings": findings,
    }


def _persist_bundle(repo) -> None:
    records = _records()
    repo.create_normalized_audio_asset(records["normalized"])
    repo.create_speaker_mapping(records["mapping"])
    repo.create_limitation_acknowledgment(records["acknowledgment"])
    repo.create_transcript_attestation(records["attestation"])
    repo.create_chat_export(records["chat_export"])
    repo.create_findings_result(records["findings"])


def _speech_lineage_state(repo) -> dict[str, dict[str, object]]:
    stores = {
        "sessions": repo.sessions,
        "transcripts": repo.transcripts,
        "features": repo.features,
        "audio_files": repo.audio_files,
        "normalized_audio_assets": repo.normalized_audio_assets,
        "speaker_mappings": repo.speaker_mappings,
        "limitation_acknowledgments": repo.limitation_acknowledgments,
        "transcript_attestations": repo.transcript_attestations,
        "chat_exports": repo.chat_exports,
        "findings_results": repo.findings_results,
    }
    return {
        store_name: {
            repr(key): value.model_dump(mode="json")
            for key, value in store.items()
        }
        for store_name, store in stores.items()
    }


def _assert_round_trip(repo) -> None:
    audio = repo.get_current_normalized_audio_asset("audio_synthetic_001")
    mapping = repo.get_current_speaker_mapping("transcript_synthetic_001")
    acknowledgments = repo.list_current_acknowledgments("transcript_synthetic_001")
    attestation = repo.get_current_transcript_attestation("transcript_synthetic_001")
    export = repo.get_current_chat_export("transcript_synthetic_001")
    findings = repo.get_current_findings_result("transcript_synthetic_001")

    assert audio.source_checksum_sha256 == SOURCE_SHA
    assert audio.normalized_checksum_sha256 == NORMALIZED_SHA
    assert mapping.transcript_version == 3
    assert mapping.entries[0].temporary_speaker_id == "SPK_01"
    assert mapping.entries[0].confirmed_chat_code == "CHI"
    assert attestation.speaker_mapping_version == 2
    assert acknowledgments[0].validator_version == "speech-qa-v1.7.0"
    assert acknowledgments[0].disposition is QaDisposition.acknowledgeable_limitation
    assert export.round_trip.status == "verified"
    assert export.source_checksum_sha256 == SOURCE_SHA
    assert export.normalized_checksum_sha256 == NORMALIZED_SHA
    assert findings.features[0].status is FeatureResultStatus.unavailable
    assert findings.features[0].value is None
    assert findings.features[0].normalized_checksum_sha256 == NORMALIZED_SHA
    assert findings.features[0].attestation_version == 1
    assert findings.features[0].chat_export_version == 1
    assert findings.features[0].parser_version == "lingualens-chat-parser-v1.7.0"


def test_json_repository_round_trip_preserves_typed_speech_pipeline_records(tmp_path: Path) -> None:
    path = tmp_path / "speech-pipeline.json"
    repo = JsonFileRepository(path)
    _seed_sources(repo)
    _persist_bundle(repo)

    _assert_round_trip(JsonFileRepository(path))


def test_sql_repository_round_trip_preserves_typed_speech_pipeline_records(tmp_path: Path) -> None:
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'speech-pipeline.db'}"
    repo = SqlAlchemyRepository(database_url)
    _seed_sources(repo)
    _persist_bundle(repo)

    _assert_round_trip(SqlAlchemyRepository(database_url))


@pytest.mark.parametrize("repository_kind", ["json", "sql"])
def test_versions_are_unique_and_current_selection_preserves_history(
    tmp_path: Path,
    repository_kind: str,
) -> None:
    if repository_kind == "sql":
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'history.db'}")
    else:
        repo = JsonFileRepository(tmp_path / "history.json")
    _seed_sources(repo)
    records = _records()
    first = records["mapping"].model_copy(update={"mapping_version": 1})
    repo.create_speaker_mapping(first)
    repo.create_speaker_mapping(records["mapping"])

    with pytest.raises(ValueError, match="version"):
        repo.create_speaker_mapping(records["mapping"])

    assert repo.get_current_speaker_mapping("transcript_synthetic_001").mapping_version == 2
    assert {
        item.mapping_version
        for item in repo.list_speaker_mapping_history("transcript_synthetic_001")
    } == {1, 2}


@pytest.mark.parametrize("repository_kind", ["json", "sql"])
def test_mark_downstream_stale_retains_history_and_does_not_change_transcript(
    tmp_path: Path,
    repository_kind: str,
) -> None:
    if repository_kind == "sql":
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        database_url = f"sqlite:///{tmp_path / 'stale.db'}"
        repo = SqlAlchemyRepository(database_url)
    else:
        database_url = None
        repo = JsonFileRepository(tmp_path / "stale.json")
    _seed_sources(repo)
    _persist_bundle(repo)
    original_transcript = repo.transcripts["transcript_synthetic_001"].model_dump()

    repo.mark_downstream_stale(
        "transcript_synthetic_001",
        [
            StalenessCause(
                code="TRANSCRIPT_VERSION_CHANGED",
                affected_resource_id="transcript_synthetic_001",
                affected_resource_version="4",
                validator_or_rule_version="speech-lineage-v1.7.0",
            )
        ],
    )
    if database_url:
        repo = SqlAlchemyRepository(database_url)
    else:
        repo = JsonFileRepository(tmp_path / "stale.json")

    assert repo.get_current_speaker_mapping("transcript_synthetic_001") is None
    assert repo.list_current_acknowledgments("transcript_synthetic_001") == []
    assert repo.get_current_transcript_attestation("transcript_synthetic_001") is None
    assert repo.get_current_chat_export("transcript_synthetic_001") is None
    assert repo.get_current_findings_result("transcript_synthetic_001") is None
    assert repo.transcripts["transcript_synthetic_001"].model_dump() == original_transcript
    stale_findings = repo.list_findings_history("transcript_synthetic_001")[0]
    assert stale_findings.status == "stale"
    assert stale_findings.features[0].status is FeatureResultStatus.unavailable
    assert stale_findings.features[0].value is None
    assert stale_findings.stale_causes[0].code == "TRANSCRIPT_VERSION_CHANGED"
    assert stale_findings.stale_causes[0].validator_or_rule_version == "speech-lineage-v1.7.0"


@pytest.mark.parametrize("repository_kind", ["json", "sql"])
def test_staling_findings_preserves_historical_feature_measurement(
    tmp_path: Path,
    repository_kind: str,
) -> None:
    if repository_kind == "sql":
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        database_url = f"sqlite:///{tmp_path / 'historical-measurement.db'}"
        repo = SqlAlchemyRepository(database_url)
    else:
        database_url = None
        path = tmp_path / "historical-measurement.json"
        repo = JsonFileRepository(path)
    _seed_sources(repo)
    records = _records()
    measured_feature = records["findings"].features[0].model_copy(
        update={
            "status": FeatureResultStatus.available,
            "value": 7.5,
            "numerator": 15,
            "denominator": 2,
            "reason_code": None,
            "remediation": None,
        }
    )
    measured_findings = records["findings"].model_copy(
        update={"features": [measured_feature]}
    )
    repo.create_normalized_audio_asset(records["normalized"])
    repo.create_speaker_mapping(records["mapping"])
    repo.create_limitation_acknowledgment(records["acknowledgment"])
    repo.create_transcript_attestation(records["attestation"])
    repo.create_chat_export(records["chat_export"])
    repo.create_findings_result(measured_findings)

    repo.mark_downstream_stale(
        "transcript_synthetic_001",
        [
            StalenessCause(
                code="TRANSCRIPT_VERSION_CHANGED",
                affected_resource_id="transcript_synthetic_001",
                affected_resource_version="4",
                validator_or_rule_version="speech-lineage-v1.7.0",
            )
        ],
    )
    if database_url:
        repo = SqlAlchemyRepository(database_url)
    else:
        repo = JsonFileRepository(path)

    historical = repo.list_findings_history("transcript_synthetic_001")[0]
    assert historical.status is ArtifactStatus.stale
    assert historical.features[0].status is FeatureResultStatus.available
    assert historical.features[0].value == 7.5
    assert historical.features[0].numerator == 15
    assert historical.features[0].denominator == 2


def test_feature_unavailable_is_not_serialized_as_zero() -> None:
    feature = _records()["findings"].features[0]

    assert feature.model_dump(mode="json")["value"] is None
    with pytest.raises(ValueError, match="must not contain a value"):
        feature.model_copy(update={"value": 0}).model_validate(
            feature.model_copy(update={"value": 0}).model_dump()
        )


@pytest.mark.parametrize("repository_kind", ["json", "sql"])
def test_inserting_stale_history_does_not_displace_current_attestation(
    tmp_path: Path,
    repository_kind: str,
) -> None:
    if repository_kind == "sql":
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'historical-attestation.db'}")
    else:
        repo = JsonFileRepository(tmp_path / "historical-attestation.json")
    _seed_sources(repo)
    records = _records()
    repo.create_speaker_mapping(records["mapping"])
    repo.create_limitation_acknowledgment(records["acknowledgment"])
    repo.create_transcript_attestation(records["attestation"])
    repo.create_transcript_attestation(
        records["attestation"].model_copy(
            update={"attestation_version": 2, "status": ArtifactStatus.stale}
        )
    )

    assert (
        repo.get_current_transcript_attestation("transcript_synthetic_001").attestation_version
        == 1
    )


@pytest.mark.parametrize("repository_kind", ["json", "sql"])
def test_current_selection_never_regresses_for_versioned_inputs(
    tmp_path: Path,
    repository_kind: str,
) -> None:
    if repository_kind == "sql":
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'non-regression.db'}")
    else:
        repo = JsonFileRepository(tmp_path / "non-regression.json")
    _seed_sources(repo)
    records = _records()

    normalized_v3 = records["normalized"].model_copy(
        update={
            "asset_version": 3,
            "normalized_checksum_sha256": "3" * 64,
        }
    )
    repo.create_normalized_audio_asset(normalized_v3)
    retained_normalized = repo.create_normalized_audio_asset(records["normalized"])
    historical_normalized = repo.create_normalized_audio_asset(
        records["normalized"].model_copy(
            update={
                "asset_version": 4,
                "normalized_checksum_sha256": "4" * 64,
                "status": ArtifactStatus.stale,
            }
        )
    )
    assert retained_normalized.status is ArtifactStatus.stale
    assert historical_normalized.status is ArtifactStatus.stale
    assert repo.get_current_normalized_audio_asset("audio_synthetic_001").asset_version == 3
    assert repo.audio_files["audio_synthetic_001"].current_normalized_asset_version == 3

    mapping_v4 = records["mapping"].model_copy(
        update={"mapping_id": "mapping_high", "mapping_version": 4}
    )
    repo.create_speaker_mapping(mapping_v4)
    retained_mapping = repo.create_speaker_mapping(
        records["mapping"].model_copy(update={"mapping_id": "mapping_low"})
    )
    assert retained_mapping.status == "stale"
    assert repo.get_current_speaker_mapping("transcript_synthetic_001").mapping_version == 4

    acknowledgment_v3 = records["acknowledgment"].model_copy(
        update={"acknowledgment_version": 3}
    )
    repo.create_limitation_acknowledgment(acknowledgment_v3)
    retained_acknowledgment = repo.create_limitation_acknowledgment(
        records["acknowledgment"].model_copy(update={"acknowledgment_version": 2})
    )
    repo.create_limitation_acknowledgment(
        records["acknowledgment"].model_copy(
            update={
                "acknowledgment_id": "ack_historical",
                "acknowledgment_version": 4,
                "status": ArtifactStatus.stale,
            }
        )
    )
    assert retained_acknowledgment.status is ArtifactStatus.stale
    current_acknowledgments = repo.list_current_acknowledgments("transcript_synthetic_001")
    assert [(item.acknowledgment_id, item.acknowledgment_version) for item in current_acknowledgments] == [
        ("ack_synthetic_001", 3)
    ]


@pytest.mark.parametrize("repository_kind", ["json", "sql"])
def test_current_selection_never_regresses_for_attestation_chat_or_findings(
    tmp_path: Path,
    repository_kind: str,
) -> None:
    if repository_kind == "sql":
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'artifact-non-regression.db'}")
    else:
        repo = JsonFileRepository(tmp_path / "artifact-non-regression.json")
    _seed_sources(repo)
    records = _records()
    repo.create_normalized_audio_asset(records["normalized"])
    repo.create_speaker_mapping(records["mapping"])
    repo.create_limitation_acknowledgment(records["acknowledgment"])

    attestation_v3 = records["attestation"].model_copy(
        update={"attestation_id": "attestation_high", "attestation_version": 3}
    )
    repo.create_transcript_attestation(attestation_v3)
    retained_attestation = repo.create_transcript_attestation(
        records["attestation"].model_copy(
            update={"attestation_id": "attestation_low", "attestation_version": 2}
        )
    )
    assert retained_attestation.status is ArtifactStatus.stale
    assert repo.get_current_transcript_attestation("transcript_synthetic_001").attestation_version == 3

    chat_v3 = records["chat_export"].model_copy(
        update={
            "export_id": "chat_high",
            "export_version": 3,
            "attestation_id": "attestation_high",
            "attestation_version": 3,
        }
    )
    repo.create_chat_export(chat_v3)
    retained_chat = repo.create_chat_export(
        chat_v3.model_copy(update={"export_id": "chat_low", "export_version": 2})
    )
    assert retained_chat.status is ArtifactStatus.stale
    assert repo.get_current_chat_export("transcript_synthetic_001").export_version == 3

    feature_v3 = records["findings"].features[0].model_copy(
        update={
            "attestation_id": "attestation_high",
            "attestation_version": 3,
            "chat_export_id": "chat_high",
            "chat_export_version": 3,
        }
    )
    findings_v3 = records["findings"].model_copy(
        update={
            "findings_id": "findings_high",
            "findings_version": 3,
            "attestation_id": "attestation_high",
            "attestation_version": 3,
            "chat_export_id": "chat_high",
            "chat_export_version": 3,
            "features": [feature_v3],
        }
    )
    repo.create_findings_result(findings_v3)
    retained_findings = repo.create_findings_result(
        findings_v3.model_copy(update={"findings_id": "findings_low", "findings_version": 2})
    )
    assert retained_findings.status is ArtifactStatus.stale
    assert repo.get_current_findings_result("transcript_synthetic_001").findings_version == 3


@pytest.mark.parametrize("repository_kind", ["json", "sql"])
def test_repository_rejects_mismatched_upstream_versions_and_checksums(
    tmp_path: Path,
    repository_kind: str,
) -> None:
    if repository_kind == "sql":
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'lineage-mismatch.db'}")
    else:
        repo = JsonFileRepository(tmp_path / "lineage-mismatch.json")
    _seed_sources(repo)
    records = _records()

    with pytest.raises(ValueError, match="transcript version"):
        repo.create_speaker_mapping(
            records["mapping"].model_copy(
                update={
                    "mapping_id": "mapping_bad_transcript",
                    "transcript_version": 999,
                }
            )
        )
    with pytest.raises(ValueError, match="source checksum"):
        repo.create_normalized_audio_asset(
            records["normalized"].model_copy(
                update={"source_checksum_sha256": "9" * 64}
            )
        )

    repo.create_normalized_audio_asset(records["normalized"])
    repo.create_speaker_mapping(records["mapping"])
    repo.create_limitation_acknowledgment(records["acknowledgment"])
    with pytest.raises((KeyError, ValueError), match="mapping"):
        repo.create_transcript_attestation(
            records["attestation"].model_copy(update={"speaker_mapping_version": 999})
        )

    repo.create_transcript_attestation(records["attestation"])
    with pytest.raises((KeyError, ValueError), match="attestation"):
        repo.create_chat_export(
            records["chat_export"].model_copy(update={"attestation_version": 999})
        )

    repo.create_chat_export(records["chat_export"])
    with pytest.raises(ValueError, match="acknowledgment"):
        repo.create_findings_result(
            records["findings"].model_copy(
                update={
                    "findings_id": "findings_bad_acknowledgments",
                    "acknowledgment_refs": [],
                }
            )
        )
    with pytest.raises(ValueError, match="normalized checksum"):
        repo.create_findings_result(
            records["findings"].model_copy(
                update={"normalized_checksum_sha256": "9" * 64}
            )
        )
    mismatched_feature = records["findings"].features[0].model_copy(
        update={"chat_export_version": 999}
    )
    with pytest.raises(ValueError, match="feature.*CHAT export version"):
        repo.create_findings_result(
            records["findings"].model_copy(
                update={
                    "findings_id": "findings_bad_nested",
                    "features": [mismatched_feature],
                }
            )
        )


@pytest.mark.parametrize("repository_kind", ["json", "sql"])
def test_structured_chat_round_trip_errors_restore_exact_types(
    tmp_path: Path,
    repository_kind: str,
) -> None:
    if repository_kind == "sql":
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        database_url = f"sqlite:///{tmp_path / 'chat-errors.db'}"
        repo = SqlAlchemyRepository(database_url)
    else:
        database_url = None
        path = tmp_path / "chat-errors.json"
        repo = JsonFileRepository(path)
    _seed_sources(repo)
    records = _records()
    repo.create_normalized_audio_asset(records["normalized"])
    repo.create_speaker_mapping(records["mapping"])
    repo.create_limitation_acknowledgment(records["acknowledgment"])
    repo.create_transcript_attestation(records["attestation"])
    error = ChatRoundTripError(
        code="SEMANTIC_TIMESTAMP_MISMATCH",
        field_or_tier="media_bullet",
        utterance_or_segment_id="utt_synthetic_001",
        expected="1000",
        actual="1001",
        severity="error",
        parser_version="lingualens-chat-parser-v1.7.0",
        serializer_version="lingualens-chat-serializer-v1.7.0",
        subset_version="lingualens-chat-v1.7.0",
        message="Synthetic semantic mismatch.",
    )
    failed_export = records["chat_export"].model_copy(
        update={
            "export_id": "chat_error_history",
            "export_version": 2,
            "status": ArtifactStatus.stale,
            "round_trip": records["chat_export"].round_trip.model_copy(
                update={"status": RoundTripStatus.failed, "errors": [error]}
            ),
        }
    )
    repo.create_chat_export(failed_export)
    if database_url:
        repo = SqlAlchemyRepository(database_url)
    else:
        repo = JsonFileRepository(path)

    restored = repo.chat_exports[("chat_error_history", 2)].round_trip.errors[0]
    assert isinstance(restored, ChatRoundTripError)
    assert restored.field_or_tier == "media_bullet"
    assert restored.utterance_or_segment_id == "utt_synthetic_001"
    assert restored.expected == "1000"
    assert restored.actual == "1001"
    assert restored.parser_version == "lingualens-chat-parser-v1.7.0"


def test_staleness_cause_rejects_unbounded_detail_text() -> None:
    with pytest.raises(ValueError):
        StalenessCause.model_validate(
            {
                "code": "TRANSCRIPT_VERSION_CHANGED",
                "affected_resource_id": "transcript_synthetic_001",
                "affected_resource_version": "4",
                "validator_or_rule_version": "speech-lineage-v1.7.0",
                "clinical_text": "must not be accepted",
            }
        )


def test_sql_speech_history_rows_are_never_deleted_or_recreated(tmp_path: Path) -> None:
    pytest.importorskip("sqlalchemy")
    from app.db.models import NormalizedAudioAssetRecord, SpeakerMappingRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'physical-history.db'}")
    _seed_sources(repo)
    records = _records()
    repo.create_normalized_audio_asset(records["normalized"])
    with repo.SessionLocal() as db:
        db.connection().exec_driver_sql(
            "create table speech_delete_probe (record_key text not null)"
        )
        db.connection().exec_driver_sql(
            "create trigger probe_normalized_audio_delete "
            "after delete on normalized_audio_assets "
            "begin insert into speech_delete_probe(record_key) values (old.record_key); end"
        )
        original_row_id = db.execute(
            NormalizedAudioAssetRecord.__table__.select()
            .with_only_columns(NormalizedAudioAssetRecord.record_key)
            .where(NormalizedAudioAssetRecord.record_key == "audio_synthetic_001:1")
        ).scalar_one()
        concurrent_mapping = records["mapping"].model_copy(
            update={"mapping_id": "mapping_concurrent", "mapping_version": 7}
        )
        db.add(
            SpeakerMappingRecord(
                record_key="mapping_concurrent:7",
                organization_id=concurrent_mapping.organization_id,
                session_id=concurrent_mapping.session_id,
                mapping_id=concurrent_mapping.mapping_id,
                mapping_version=concurrent_mapping.mapping_version,
                transcript_id=concurrent_mapping.transcript_id,
                transcript_version=concurrent_mapping.transcript_version,
                status=concurrent_mapping.status.value,
                payload=concurrent_mapping.model_dump(mode="json"),
                created_at=concurrent_mapping.confirmed_at,
            )
        )
        db.commit()

    repo.create_normalized_audio_asset(
        records["normalized"].model_copy(
            update={"asset_version": 2, "normalized_checksum_sha256": "2" * 64}
        )
    )
    repo.save()
    with repo.SessionLocal() as db:
        rows = db.query(NormalizedAudioAssetRecord).order_by(
            NormalizedAudioAssetRecord.asset_version
        ).all()
        assert [row.asset_version for row in rows] == [1, 2]
        assert rows[0].record_key == original_row_id
        assert db.get(SpeakerMappingRecord, "mapping_concurrent:7") is not None
        delete_count = db.connection().exec_driver_sql(
            "select count(*) from speech_delete_probe"
        ).scalar_one()
        assert delete_count == 0


def test_sql_concurrent_repository_cannot_regress_current_audio_pointer(tmp_path: Path) -> None:
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'concurrent-current.db'}"
    first_repo = SqlAlchemyRepository(database_url)
    _seed_sources(first_repo)
    stale_repo = SqlAlchemyRepository(database_url)
    records = _records()

    first_repo.create_normalized_audio_asset(
        records["normalized"].model_copy(
            update={"asset_version": 3, "normalized_checksum_sha256": "3" * 64}
        )
    )
    stale_repo.create_normalized_audio_asset(
        records["normalized"].model_copy(
            update={"asset_version": 2, "normalized_checksum_sha256": "2" * 64}
        )
    )

    reloaded = SqlAlchemyRepository(database_url)
    assert reloaded.get_current_normalized_audio_asset("audio_synthetic_001").asset_version == 3
    assert reloaded.normalized_audio_assets[("audio_synthetic_001", 2)].status is ArtifactStatus.stale
    assert reloaded.audio_files["audio_synthetic_001"].current_normalized_asset_version == 3


@pytest.mark.parametrize("stale_action", ["save", "audit"])
def test_sql_stale_generic_save_preserves_durable_audio_pointer(
    tmp_path: Path,
    stale_action: str,
) -> None:
    pytest.importorskip("sqlalchemy")
    from app.db.models import AudioFileRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / f'stale-audio-{stale_action}.db'}"
    writer = SqlAlchemyRepository(database_url)
    _seed_sources(writer)
    stale_repo = SqlAlchemyRepository(database_url)
    normalized_v3 = _records()["normalized"].model_copy(
        update={"asset_version": 3, "normalized_checksum_sha256": "3" * 64}
    )
    writer.create_normalized_audio_asset(normalized_v3)

    if stale_action == "audit":
        stale_repo.add_audit(
            "synthetic.noop",
            "synthetic_target",
            "Synthetic operational audit.",
        )
    else:
        stale_repo.save()

    with writer.SessionLocal() as db:
        audio_row = db.get(AudioFileRecord, "audio_synthetic_001")
        assert audio_row is not None
        assert audio_row.current_normalized_asset_version == 3
        assert audio_row.current_normalized_checksum_sha256 == "3" * 64
    reloaded = SqlAlchemyRepository(database_url)
    assert reloaded.get_current_normalized_audio_asset("audio_synthetic_001").asset_version == 3
    assert reloaded.audio_files["audio_synthetic_001"].current_normalized_asset_version == 3
    assert reloaded.audio_files["audio_synthetic_001"].current_normalized_checksum_sha256 == "3" * 64


def test_sql_stale_save_cannot_resurrect_invalidated_lineage(tmp_path: Path) -> None:
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'stale-lifecycle.db'}"
    writer = SqlAlchemyRepository(database_url)
    _seed_sources(writer)
    _persist_bundle(writer)
    stale_repo = SqlAlchemyRepository(database_url)
    cause = StalenessCause(
        code="TRANSCRIPT_VERSION_CHANGED",
        affected_resource_id="transcript_synthetic_001",
        affected_resource_version="4",
        validator_or_rule_version="speech-lineage-v1.7.0",
    )

    writer.mark_downstream_stale("transcript_synthetic_001", [cause])
    stale_repo.save()

    reloaded = SqlAlchemyRepository(database_url)
    assert reloaded.get_current_speaker_mapping("transcript_synthetic_001") is None
    assert reloaded.list_current_acknowledgments("transcript_synthetic_001") == []
    assert reloaded.get_current_transcript_attestation("transcript_synthetic_001") is None
    assert reloaded.get_current_chat_export("transcript_synthetic_001") is None
    assert reloaded.get_current_findings_result("transcript_synthetic_001") is None
    lifecycle_records = [
        reloaded.speaker_mappings[("mapping_synthetic_001", 2)],
        reloaded.limitation_acknowledgments[("ack_synthetic_001", 1)],
        reloaded.transcript_attestations[("attestation_synthetic_001", 1)],
        reloaded.chat_exports[("chat_synthetic_001", 1)],
        reloaded.findings_results[("findings_synthetic_001", 1)],
    ]
    assert all(item.stale_causes == [cause] for item in lifecycle_records)


def test_sql_stale_save_preserves_newer_transcript_and_stale_feature_lineage(
    tmp_path: Path,
) -> None:
    pytest.importorskip("sqlalchemy")
    from app.db.models import FeatureSetRecord, TranscriptRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'stale-transcript-feature.db'}"
    writer = SqlAlchemyRepository(database_url)
    _seed_sources(writer)
    records = _records()
    writer.create_speaker_mapping(records["mapping"])
    feature_set = FeatureSet(
        feature_set_id="feature_synthetic_001",
        session_id="session_demo_001",
        transcript_id="transcript_synthetic_001",
        transcript_version=3,
        therapist_attested=True,
        features=[],
        speaker_mapping_id="mapping_synthetic_001",
        speaker_mapping_version=2,
        review_status=ReviewStatus.ready,
    )
    writer.create_feature_set(
        feature_set,
        actor_id="therapist_synthetic",
        audit_action="features.synthetic",
        audit_message="Synthetic findings created.",
    )
    stale_repo = SqlAlchemyRepository(database_url)
    current = writer.transcripts["transcript_synthetic_001"]
    updated = current.model_copy(
        update={"version": 4, "updated_at": datetime(2026, 7, 25, 9, 0, tzinfo=timezone.utc)}
    )

    writer.update_transcript(
        updated,
        session_status=ReviewStatus.needs_review,
        expected_version=3,
        actor_id="therapist_synthetic",
        audit_action="transcript.synthetic_edit",
        audit_message="Synthetic transcript edited.",
    )
    stale_repo.save()

    with writer.SessionLocal() as db:
        transcript_row = db.get(TranscriptRecord, "transcript_synthetic_001")
        feature_row = db.get(FeatureSetRecord, "feature_synthetic_001")
        assert transcript_row is not None
        assert transcript_row.version == 4
        assert feature_row is not None
        assert feature_row.review_status == ReviewStatus.stale.value
        assert feature_row.speaker_mapping_id == "mapping_synthetic_001"
        assert feature_row.speaker_mapping_version == 2
    reloaded = SqlAlchemyRepository(database_url)
    assert reloaded.get_current_speaker_mapping("transcript_synthetic_001") is None


@pytest.mark.parametrize("repository_kind", ["mock", "sql"])
def test_transcript_edit_invalidates_current_speech_lineage(
    tmp_path: Path,
    repository_kind: str,
) -> None:
    if repository_kind == "sql":
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'transcript-invalidation.db'}")
    else:
        repo = MockRepository()
    _seed_sources(repo)
    _persist_bundle(repo)
    transcript = repo.transcripts["transcript_synthetic_001"]

    repo.update_transcript(
        transcript.model_copy(update={"version": 4}),
        session_status=ReviewStatus.needs_review,
        expected_version=3,
        actor_id="therapist_synthetic",
        audit_action="transcript.synthetic_edit",
        audit_message="Synthetic transcript edited.",
    )

    assert repo.get_current_speaker_mapping("transcript_synthetic_001") is None
    assert repo.list_current_acknowledgments("transcript_synthetic_001") == []
    assert repo.get_current_transcript_attestation("transcript_synthetic_001") is None
    assert repo.get_current_chat_export("transcript_synthetic_001") is None
    assert repo.get_current_findings_result("transcript_synthetic_001") is None


@pytest.mark.parametrize("repository_kind", ["mock", "sql"])
def test_cross_version_mapping_attestation_and_chat_refs_are_rejected(
    tmp_path: Path,
    repository_kind: str,
) -> None:
    if repository_kind == "sql":
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'cross-version.db'}")
    else:
        repo = MockRepository()
    _seed_sources(repo)
    records = _records()
    repo.create_normalized_audio_asset(records["normalized"])
    repo.create_speaker_mapping(records["mapping"])
    repo.create_limitation_acknowledgment(records["acknowledgment"])
    repo.create_transcript_attestation(records["attestation"])
    repo.create_chat_export(records["chat_export"])
    transcript = repo.transcripts["transcript_synthetic_001"]
    repo.update_transcript(
        transcript.model_copy(update={"version": 4}),
        session_status=ReviewStatus.needs_review,
        expected_version=3,
        actor_id="therapist_synthetic",
        audit_action="transcript.synthetic_edit",
        audit_message="Synthetic transcript edited.",
        invalidate_downstream=False,
    )

    with pytest.raises(ValueError, match="mapping.*transcript version"):
        repo.create_transcript_attestation(
            records["attestation"].model_copy(
                update={
                    "attestation_id": "attestation_cross_version",
                    "attestation_version": 4,
                    "transcript_version": 4,
                    "acknowledgment_refs": [],
                }
            )
        )
    mapping_v4 = records["mapping"].model_copy(
        update={
            "mapping_id": "mapping_v4",
            "mapping_version": 4,
            "transcript_version": 4,
        }
    )
    repo.create_speaker_mapping(mapping_v4)
    with pytest.raises(ValueError, match="attestation.*transcript version"):
        repo.create_chat_export(
            records["chat_export"].model_copy(
                update={
                    "export_id": "chat_cross_version",
                    "export_version": 4,
                    "transcript_version": 4,
                    "speaker_mapping_id": "mapping_v4",
                    "speaker_mapping_version": 4,
                }
            )
        )
    acknowledgment_v4 = records["acknowledgment"].model_copy(
        update={
            "acknowledgment_version": 4,
            "transcript_version": 4,
            "affected_resource_version": "4",
        }
    )
    repo.create_limitation_acknowledgment(acknowledgment_v4)
    attestation_v4 = records["attestation"].model_copy(
        update={
            "attestation_id": "attestation_v4",
            "attestation_version": 4,
            "transcript_version": 4,
            "speaker_mapping_id": "mapping_v4",
            "speaker_mapping_version": 4,
            "acknowledgment_refs": [("ack_synthetic_001", 4)],
        }
    )
    repo.create_transcript_attestation(attestation_v4)
    with pytest.raises(ValueError, match="CHAT export.*transcript version"):
        repo.create_findings_result(
            records["findings"].model_copy(
                update={
                    "findings_id": "findings_cross_version",
                    "findings_version": 4,
                    "transcript_version": 4,
                    "speaker_mapping_id": "mapping_v4",
                    "speaker_mapping_version": 4,
                    "attestation_id": "attestation_v4",
                    "attestation_version": 4,
                    "acknowledgment_refs": [("ack_synthetic_001", 4)],
                }
            )
        )


@pytest.mark.parametrize(
    ("round_trip_updates", "expected_message"),
    [
        ({"output_semantic_checksum_sha256": "9" * 64}, "semantic checksum"),
        ({"deterministic_export_checksum_sha256": "9" * 64}, "export checksum"),
        (
            {
                "errors": [
                    ChatRoundTripError(
                        code="SYNTHETIC_VERIFICATION_ERROR",
                        field_or_tier="synthetic_tier",
                        utterance_or_segment_id="utt_synthetic_001",
                        expected="expected",
                        actual="actual",
                        severity="error",
                        parser_version="lingualens-chat-parser-v1.7.0",
                        serializer_version="lingualens-chat-serializer-v1.7.0",
                        subset_version="lingualens-chat-v1.7.0",
                    )
                ]
            },
            "verification errors",
        ),
    ],
)
@pytest.mark.parametrize("repository_kind", ["json", "sql"])
def test_verified_chat_requires_semantic_and_export_integrity(
    tmp_path: Path,
    round_trip_updates: dict,
    expected_message: str,
    repository_kind: str,
) -> None:
    if repository_kind == "sql":
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        repo = SqlAlchemyRepository(
            f"sqlite:///{tmp_path / f'chat-integrity-{expected_message}.db'}"
        )
    else:
        repo = JsonFileRepository(tmp_path / f"chat-integrity-{expected_message}.json")
    _seed_sources(repo)
    records = _records()
    repo.create_normalized_audio_asset(records["normalized"])
    repo.create_speaker_mapping(records["mapping"])
    repo.create_limitation_acknowledgment(records["acknowledgment"])
    repo.create_transcript_attestation(records["attestation"])
    bad_round_trip = records["chat_export"].round_trip.model_copy(
        update=round_trip_updates
    )

    with pytest.raises(ValueError, match=expected_message):
        repo.create_chat_export(
            records["chat_export"].model_copy(
                update={"export_id": f"chat_bad_{expected_message}", "round_trip": bad_round_trip}
            )
        )


@pytest.mark.parametrize("repository_kind", ["json", "sql"])
def test_nonverified_chat_requires_structured_errors(
    tmp_path: Path,
    repository_kind: str,
) -> None:
    if repository_kind == "sql":
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'chat-failed-errors.db'}")
    else:
        repo = JsonFileRepository(tmp_path / "chat-failed-errors.json")
    _seed_sources(repo)
    records = _records()
    repo.create_normalized_audio_asset(records["normalized"])
    repo.create_speaker_mapping(records["mapping"])
    repo.create_limitation_acknowledgment(records["acknowledgment"])
    repo.create_transcript_attestation(records["attestation"])
    failed_without_errors = records["chat_export"].round_trip.model_copy(
        update={"status": RoundTripStatus.failed, "errors": []}
    )

    with pytest.raises(ValueError, match="structured errors"):
        repo.create_chat_export(
            records["chat_export"].model_copy(
                update={
                    "export_id": "chat_failed_without_errors",
                    "status": ArtifactStatus.stale,
                    "round_trip": failed_without_errors,
                }
            )
        )


def test_sql_interleaved_normalized_creates_arbitrate_current_atomically(
    tmp_path: Path,
) -> None:
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'interleaved-normalized.db'}"
    first_repo = SqlAlchemyRepository(database_url)
    _seed_sources(first_repo)
    second_repo = SqlAlchemyRepository(database_url)
    records = _records()
    barrier = threading.Barrier(2)

    for repo in (first_repo, second_repo):
        refresh = repo._refresh_speech_pipeline_state
        synchronized_once = {"done": False}

        def synchronized_refresh(
            refresh=refresh,
            synchronized_once=synchronized_once,
        ) -> None:
            refresh()
            if not synchronized_once["done"]:
                synchronized_once["done"] = True
                barrier.wait(timeout=10)

        repo._refresh_speech_pipeline_state = synchronized_refresh
        repo.engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                first_repo.create_normalized_audio_asset,
                records["normalized"].model_copy(
                    update={"asset_version": 3, "normalized_checksum_sha256": "3" * 64}
                ),
            ),
            executor.submit(
                second_repo.create_normalized_audio_asset,
                records["normalized"].model_copy(
                    update={"asset_version": 2, "normalized_checksum_sha256": "2" * 64}
                ),
            ),
        ]
        for future in futures:
            future.result(timeout=15)

    reloaded = SqlAlchemyRepository(database_url)
    current = [
        item
        for item in reloaded.normalized_audio_assets.values()
        if item.source_audio_file_id == "audio_synthetic_001"
        and item.status is ArtifactStatus.current
    ]
    assert [(item.asset_version, item.normalized_checksum_sha256) for item in current] == [
        (3, "3" * 64)
    ]
    assert reloaded.audio_files["audio_synthetic_001"].current_normalized_asset_version == 3
    assert reloaded.audio_files["audio_synthetic_001"].current_normalized_checksum_sha256 == "3" * 64


@pytest.mark.parametrize("artifact_kind", ["attestation", "chat", "findings"])
def test_sql_downstream_create_revalidates_upstream_inside_serialized_write(
    tmp_path: Path,
    artifact_kind: str,
) -> None:
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / f'upstream-race-{artifact_kind}.db'}"
    invalidator = SqlAlchemyRepository(database_url)
    _seed_sources(invalidator)
    records = _records()
    invalidator.create_normalized_audio_asset(records["normalized"])
    invalidator.create_speaker_mapping(records["mapping"])
    invalidator.create_limitation_acknowledgment(records["acknowledgment"])
    if artifact_kind in {"chat", "findings"}:
        invalidator.create_transcript_attestation(records["attestation"])
    if artifact_kind == "findings":
        invalidator.create_chat_export(records["chat_export"])

    creator = SqlAlchemyRepository(database_url)
    validated = threading.Event()
    release_write = threading.Event()
    persist = creator._speech_pipeline_changed

    def pause_after_validation() -> None:
        validated.set()
        if not release_write.wait(timeout=10):
            raise TimeoutError("Synthetic race barrier timed out.")
        persist()

    creator._speech_pipeline_changed = pause_after_validation
    creator.engine.dispose()
    if artifact_kind == "attestation":
        create = creator.create_transcript_attestation
        artifact = records["attestation"].model_copy(
            update={"attestation_id": "attestation_race"}
        )
    elif artifact_kind == "chat":
        create = creator.create_chat_export
        artifact = records["chat_export"].model_copy(update={"export_id": "chat_race"})
    else:
        create = creator.create_findings_result
        artifact = records["findings"].model_copy(update={"findings_id": "findings_race"})

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(create, artifact)
        assert validated.wait(timeout=10)
        invalidator.mark_downstream_stale(
            "transcript_synthetic_001",
            [
                StalenessCause(
                    code="TRANSCRIPT_VERSION_CHANGED",
                    affected_resource_id="transcript_synthetic_001",
                    affected_resource_version="4",
                    validator_or_rule_version="speech-lineage-v1.7.0",
                )
            ],
        )
        assert invalidator.get_current_speaker_mapping("transcript_synthetic_001") is None
        release_write.set()
        with pytest.raises(ValueError, match="durable upstream"):
            future.result(timeout=15)

    reloaded = SqlAlchemyRepository(database_url)
    if artifact_kind == "attestation":
        assert reloaded.get_current_transcript_attestation("transcript_synthetic_001") is None
    elif artifact_kind == "chat":
        assert reloaded.get_current_chat_export("transcript_synthetic_001") is None
    else:
        assert reloaded.get_current_findings_result("transcript_synthetic_001") is None


@pytest.mark.parametrize("repository_kind", ["mock", "json", "sql"])
@pytest.mark.parametrize(
    "replacement_kind",
    ["mapping", "attestation", "chat", "normalization", "acknowledgment"],
)
def test_upstream_replacement_invalidates_current_derived_chain(
    tmp_path: Path,
    repository_kind: str,
    replacement_kind: str,
) -> None:
    if repository_kind == "sql":
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        repo = SqlAlchemyRepository(
            f"sqlite:///{tmp_path / f'replacement-{replacement_kind}.db'}"
        )
    elif repository_kind == "json":
        repo = JsonFileRepository(tmp_path / f"replacement-{replacement_kind}.json")
    else:
        repo = MockRepository()
    _seed_sources(repo)
    _persist_bundle(repo)
    records = _records()

    if replacement_kind == "mapping":
        repo.create_speaker_mapping(
            records["mapping"].model_copy(update={"mapping_version": 3})
        )
    elif replacement_kind == "attestation":
        repo.create_transcript_attestation(
            records["attestation"].model_copy(update={"attestation_version": 2})
        )
    elif replacement_kind == "chat":
        repo.create_chat_export(
            records["chat_export"].model_copy(update={"export_version": 2})
        )
    elif replacement_kind == "normalization":
        repo.create_normalized_audio_asset(
            records["normalized"].model_copy(
                update={
                    "asset_version": 2,
                    "normalized_checksum_sha256": "2" * 64,
                }
            )
        )
    else:
        repo.create_limitation_acknowledgment(
            records["acknowledgment"].model_copy(
                update={
                    "acknowledgment_version": 2,
                    "validator_version": "qa-validator-2",
                }
            )
        )

    if replacement_kind == "mapping":
        assert repo.get_current_speaker_mapping("transcript_synthetic_001").mapping_version == 3
        assert repo.get_current_transcript_attestation("transcript_synthetic_001") is None
    elif replacement_kind == "attestation":
        assert (
            repo.get_current_transcript_attestation("transcript_synthetic_001").attestation_version
            == 2
        )
    elif replacement_kind == "chat":
        assert repo.get_current_chat_export("transcript_synthetic_001").export_version == 2
    elif replacement_kind == "normalization":
        assert repo.get_current_normalized_audio_asset("audio_synthetic_001").asset_version == 2
        assert repo.list_current_acknowledgments("transcript_synthetic_001") == []
        assert repo.get_current_transcript_attestation("transcript_synthetic_001") is None
    else:
        acknowledgments = repo.list_current_acknowledgments("transcript_synthetic_001")
        assert [(item.acknowledgment_id, item.acknowledgment_version) for item in acknowledgments] == [
            ("ack_synthetic_001", 2)
        ]
        assert repo.get_current_transcript_attestation("transcript_synthetic_001") is None

    if replacement_kind in {"mapping", "attestation", "normalization", "acknowledgment"}:
        assert repo.get_current_chat_export("transcript_synthetic_001") is None
    assert repo.get_current_findings_result("transcript_synthetic_001") is None


def test_limitation_acknowledgment_schema_rejects_integrity_blocker() -> None:
    payload = _records()["acknowledgment"].model_dump(mode="python")
    payload["disposition"] = QaDisposition.integrity_blocker

    with pytest.raises(ValueError, match="acknowledgeable_limitation"):
        LimitationAcknowledgment.model_validate(payload)


@pytest.mark.parametrize("repository_kind", ["mock", "json", "sql"])
def test_attestation_rejects_legacy_blocker_acknowledgment(
    tmp_path: Path,
    repository_kind: str,
) -> None:
    if repository_kind == "sql":
        pytest.importorskip("sqlalchemy")
        from app.db.models import LimitationAcknowledgmentRecord
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'legacy-blocker.db'}")
    elif repository_kind == "json":
        repo = JsonFileRepository(tmp_path / "legacy-blocker.json")
    else:
        repo = MockRepository()
    _seed_sources(repo)
    records = _records()
    repo.create_speaker_mapping(records["mapping"])
    repo.create_limitation_acknowledgment(records["acknowledgment"])
    blocker_payload = records["acknowledgment"].model_dump(mode="python")
    blocker_payload["disposition"] = QaDisposition.integrity_blocker

    if repository_kind == "sql":
        with repo.SessionLocal() as db:
            row = db.get(
                LimitationAcknowledgmentRecord,
                "ack_synthetic_001:1",
            )
            assert row is not None
            row.payload = {
                **row.payload,
                "disposition": QaDisposition.integrity_blocker.value,
            }
            db.commit()
    else:
        repo.limitation_acknowledgments[("ack_synthetic_001", 1)] = (
            LimitationAcknowledgment.model_construct(**blocker_payload)
        )

    with pytest.raises(ValueError, match="acknowledgeable_limitation|disposition"):
        repo.create_transcript_attestation(records["attestation"])


def test_sql_durable_revalidation_rejects_ack_changed_to_blocker_after_validation(
    tmp_path: Path,
) -> None:
    pytest.importorskip("sqlalchemy")
    from app.db.models import (
        LimitationAcknowledgmentRecord,
        TranscriptAttestationRecord,
    )
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'blocker-race.db'}"
    writer = SqlAlchemyRepository(database_url)
    _seed_sources(writer)
    records = _records()
    writer.create_speaker_mapping(records["mapping"])
    writer.create_limitation_acknowledgment(records["acknowledgment"])
    creator = SqlAlchemyRepository(database_url)
    validated = threading.Event()
    release_write = threading.Event()
    persist = creator._speech_pipeline_changed

    def pause_after_validation() -> None:
        validated.set()
        if not release_write.wait(timeout=10):
            raise TimeoutError("Synthetic blocker barrier timed out.")
        creator.limitation_acknowledgments.pop(("ack_synthetic_001", 1))
        persist()

    creator._speech_pipeline_changed = pause_after_validation
    creator.engine.dispose()
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            creator.create_transcript_attestation,
            records["attestation"],
        )
        assert validated.wait(timeout=10)
        with writer.SessionLocal() as db:
            row = db.get(LimitationAcknowledgmentRecord, "ack_synthetic_001:1")
            assert row is not None
            row.payload = {
                **row.payload,
                "disposition": QaDisposition.integrity_blocker.value,
            }
            db.commit()
        release_write.set()
        with pytest.raises(ValueError, match="durable upstream"):
            future.result(timeout=15)

    with writer.SessionLocal() as db:
        assert db.get(
            TranscriptAttestationRecord,
            "attestation_synthetic_001:1",
        ) is None


@pytest.mark.parametrize(
    "artifact_kind",
    ["normalized", "mapping", "acknowledgment", "attestation", "chat_export", "findings"],
)
@pytest.mark.parametrize("failure_stage", ["hook", "dependency"])
def test_sql_failed_speech_create_recovers_same_instance_from_durable_state(
    tmp_path: Path,
    artifact_kind: str,
    failure_stage: str,
) -> None:
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = (
        f"sqlite:///{tmp_path / f'failed-{failure_stage}-{artifact_kind}.db'}"
    )
    repo = SqlAlchemyRepository(database_url)
    _seed_sources(repo)
    _persist_bundle(repo)
    records = _records()
    replacements = {
        "normalized": records["normalized"].model_copy(
            update={
                "asset_version": 2,
                "normalized_checksum_sha256": "2" * 64,
            }
        ),
        "mapping": records["mapping"].model_copy(update={"mapping_version": 3}),
        "acknowledgment": records["acknowledgment"].model_copy(
            update={
                "acknowledgment_version": 2,
                "validator_version": "qa-validator-2",
            }
        ),
        "attestation": records["attestation"].model_copy(
            update={"attestation_version": 2}
        ),
        "chat_export": records["chat_export"].model_copy(update={"export_version": 2}),
        "findings": records["findings"].model_copy(update={"findings_version": 2}),
    }
    creates = {
        "normalized": repo.create_normalized_audio_asset,
        "mapping": repo.create_speaker_mapping,
        "acknowledgment": repo.create_limitation_acknowledgment,
        "attestation": repo.create_transcript_attestation,
        "chat_export": repo.create_chat_export,
        "findings": repo.create_findings_result,
    }

    def fail_persistence(*_args) -> None:
        raise RuntimeError("forced speech persistence failure")

    if failure_stage == "hook":
        repo._speech_pipeline_changed = fail_persistence
    else:
        repo._enforce_durable_speech_dependency_closure = fail_persistence
    with pytest.raises(RuntimeError, match="forced speech persistence failure"):
        creates[artifact_kind](replacements[artifact_kind])

    fresh = SqlAlchemyRepository(database_url)
    assert _speech_lineage_state(repo) == _speech_lineage_state(fresh)


@pytest.mark.parametrize("failure_stage", ["hook", "dependency"])
def test_sql_failed_downstream_stale_recovers_same_instance_from_durable_state(
    tmp_path: Path,
    failure_stage: str,
) -> None:
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = (
        f"sqlite:///{tmp_path / f'failed-{failure_stage}-downstream-stale.db'}"
    )
    repo = SqlAlchemyRepository(database_url)
    _seed_sources(repo)
    _persist_bundle(repo)

    def fail_persistence(*_args) -> None:
        raise RuntimeError("forced speech persistence failure")

    if failure_stage == "hook":
        repo._speech_pipeline_changed = fail_persistence
    else:
        repo._enforce_durable_speech_dependency_closure = fail_persistence
    with pytest.raises(RuntimeError, match="forced speech persistence failure"):
        repo.mark_downstream_stale(
            "transcript_synthetic_001",
            [
                StalenessCause(
                    code="TRANSCRIPT_VERSION_CHANGED",
                    affected_resource_id="transcript_synthetic_001",
                    affected_resource_version="4",
                    validator_or_rule_version="speech-lineage-v1.7.0",
                )
            ],
        )

    fresh = SqlAlchemyRepository(database_url)
    assert _speech_lineage_state(repo) == _speech_lineage_state(fresh)


def test_migration_is_head_and_creates_version_unique_constraints(tmp_path: Path, monkeypatch) -> None:
    pytest.importorskip("alembic")
    sqlalchemy = pytest.importorskip("sqlalchemy")
    from alembic import command
    from alembic.config import Config
    from app.core.config import get_settings

    api_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "migration.db"
    monkeypatch.setenv("LINGUALENS_DATABASE_URL", f"sqlite:///{database_path}")
    get_settings.cache_clear()
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "app" / "db" / "migrations"))
    command.upgrade(config, "head")

    engine = sqlalchemy.create_engine(f"sqlite:///{database_path}")
    inspector = sqlalchemy.inspect(engine)
    expected_tables = {
        "normalized_audio_assets",
        "speaker_mappings",
        "transcript_attestations",
        "limitation_acknowledgments",
        "chat_exports",
        "findings_results",
        "asr_private_evidence",
    }
    assert expected_tables.issubset(set(inspector.get_table_names()))
    audio_columns = {
        column["name"]: column
        for column in inspector.get_columns("audio_files")
    }
    assert "storage_backend_identity_sha256" in audio_columns
    assert audio_columns["storage_backend_identity_sha256"]["nullable"]
    for table in expected_tables:
        assert inspector.get_unique_constraints(table), table
    chat_columns = {column["name"] for column in inspector.get_columns("chat_exports")}
    assert {
        "source_audio_file_id",
        "source_asset_version",
        "source_checksum_sha256",
        "normalized_asset_version",
        "normalized_checksum_sha256",
    }.issubset(chat_columns)
    findings_columns = {
        column["name"] for column in inspector.get_columns("findings_results")
    }
    assert {
        "speaker_mapping_id",
        "attestation_id",
        "chat_export_id",
        "source_audio_file_id",
        "source_asset_version",
        "source_checksum_sha256",
        "normalized_asset_version",
        "normalized_checksum_sha256",
        "chat_export_checksum_sha256",
        "algorithm_checksum_sha256",
        "tokenizer_profile_id",
        "tokenizer_profile_checksum_sha256",
    }.issubset(findings_columns)
    findings_indexes = {
        column
        for index in inspector.get_indexes("findings_results")
        for column in index["column_names"]
    }
    assert {
        "speaker_mapping_id",
        "speaker_mapping_version",
        "attestation_id",
        "attestation_version",
        "chat_export_id",
        "chat_export_version",
        "source_audio_file_id",
        "source_asset_version",
        "normalized_asset_version",
        "normalized_checksum_sha256",
        "algorithm_checksum_sha256",
        "tokenizer_profile_version",
    }.issubset(findings_indexes)
    with engine.connect() as connection:
        revision = connection.exec_driver_sql("select version_num from alembic_version").scalar_one()
    assert revision == "0015_audio_storage_identity"

    command.downgrade(config, "0012_report_runtime_fields")
    inspector = sqlalchemy.inspect(engine)
    assert expected_tables.isdisjoint(set(inspector.get_table_names()))
    assert "current_normalized_asset_version" not in {
        column["name"] for column in inspector.get_columns("audio_files")
    }


def test_sql_consent_withdrawal_deletes_typed_speech_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.consent_service import withdraw_consent
    from app.services.storage_service import MetadataOnlyStorageAdapter

    database_url = f"sqlite:///{tmp_path / 'consent-lineage.db'}"
    repo = SqlAlchemyRepository(database_url)
    _seed_sources(repo)
    _persist_bundle(repo)
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        MetadataOnlyStorageAdapter,
    )

    withdraw_consent(
        repo,
        "case_demo_001",
        "Synthetic withdrawal of typed speech lineage.",
    )

    durable = SqlAlchemyRepository(database_url)
    assert durable.cases["case_demo_001"].consent_status == "withdrawn"
    transcript = durable.transcripts["transcript_synthetic_001"]
    assert transcript.review_status is ReviewStatus.withdrawn
    assert transcript.raw_text == ""
    assert durable.normalized_audio_assets == {}
    assert durable.speaker_mappings == {}
    assert durable.limitation_acknowledgments == {}
    assert durable.transcript_attestations == {}
    assert durable.chat_exports == {}
    assert durable.findings_results == {}


def test_sql_consent_withdrawal_audit_failure_rolls_back_typed_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.consent_service import withdraw_consent
    from app.services.storage_service import MetadataOnlyStorageAdapter

    database_url = f"sqlite:///{tmp_path / 'consent-lineage-rollback.db'}"
    repo = SqlAlchemyRepository(database_url)
    _seed_sources(repo)
    _persist_bundle(repo)
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        MetadataOnlyStorageAdapter,
    )

    def fail_withdrawal_audit(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("synthetic typed-lineage audit failure")

    monkeypatch.setattr(repo, "_audit_to_record", fail_withdrawal_audit)
    with pytest.raises(
        RuntimeError,
        match="synthetic typed-lineage audit failure",
    ):
        withdraw_consent(
            repo,
            "case_demo_001",
            "Synthetic failed withdrawal of typed speech lineage.",
        )

    durable = SqlAlchemyRepository(database_url)
    assert durable.cases["case_demo_001"].consent_status == "granted"
    assert ("audio_synthetic_001", 1) in durable.normalized_audio_assets
    assert ("mapping_synthetic_001", 2) in durable.speaker_mappings
    assert (
        "ack_synthetic_001",
        1,
    ) in durable.limitation_acknowledgments
    assert (
        "attestation_synthetic_001",
        1,
    ) in durable.transcript_attestations
    assert ("chat_synthetic_001", 1) in durable.chat_exports
    assert ("findings_synthetic_001", 1) in durable.findings_results
