from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.services.asr_profiles import (
    AsrRuntimeVersions,
    PinnedAsrProfile,
    PinnedVadParameters,
    canonical_profile_checksum,
    hash_model_artifact,
)
from app.services.asr_providers.base import (
    AsrProfileProvenanceProjection,
    AsrUnavailability,
    CanonicalTranscriptionSegment,
    CanonicalTranscriptionDraft,
    PublicCanonicalTranscriptionDraft,
    RawProviderSegment,
    TranscriptionInput,
    VerifiedNormalizedAudioHandle,
)
import app.services.asr_providers.local_whisper_provider as local_provider_module
from app.services.asr_providers.local_whisper_provider import LocalWhisperProvider


class FakeWhisperModel:
    def __init__(self, *, language_probability: float = 0.97) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.language_probability = language_probability

    def transcribe(self, audio: str, **kwargs):
        self.calls.append((audio, kwargs))
        segments = [
            SimpleNamespace(
                id=7,
                seek=0,
                start=0.125,
                end=1.375,
                text=" สวัสดี ",
                tokens=[1, 2],
                temperature=0.0,
                avg_logprob=-0.2,
                compression_ratio=1.0,
                no_speech_prob=0.01,
                words=[
                    SimpleNamespace(
                        start=0.125,
                        end=0.75,
                        word=" สวัสดี",
                        probability=0.91,
                    )
                ],
            ),
            SimpleNamespace(
                id=8,
                seek=0,
                start=1.5,
                end=2.25,
                text=" hello ",
                tokens=[3],
                temperature=0.0,
                avg_logprob=-0.1,
                compression_ratio=0.9,
                no_speech_prob=0.02,
                words=[
                    SimpleNamespace(
                        start=1.5,
                        end=2.25,
                        word=" hello",
                        probability=0.89,
                    )
                ],
            ),
        ]
        info = SimpleNamespace(
            language="th",
            language_probability=self.language_probability,
            duration=2.5,
            duration_after_vad=2.5,
            all_language_probs=None,
            transcription_options=SimpleNamespace(),
            vad_options=None,
        )
        return iter(segments), info


def _write_model_artifact(tmp_path: Path) -> Path:
    model_dir = tmp_path / "whisper-model"
    model_dir.mkdir()
    (model_dir / "config.json").write_text('{"model":"synthetic"}', encoding="utf-8")
    (model_dir / "model.bin").write_bytes(b"synthetic-model-weights")
    return model_dir


def _profile(model_path: Path, **overrides: object) -> PinnedAsrProfile:
    values: dict[str, object] = {
        "profile_id": "v170-test-profile",
        "profile_version": 1,
        "model_identifier": "synthetic-whisper",
        "model_revision": "fixture-revision-001",
        "model_artifact_path": model_path,
        "model_checksum_sha256": hash_model_artifact(model_path),
        "faster_whisper_version": "1.2.1",
        "ctranslate2_version": "4.8.1",
        "decoder_name": "soundfile",
        "decoder_version": "0.14.0",
        "device": "cpu",
        "device_index": 0,
        "compute_type": "int8",
        "cpu_threads": 2,
        "num_workers": 1,
        "language_mode": "th",
        "task": "transcribe",
        "log_progress": False,
        "beam_size": 5,
        "best_of": 5,
        "patience": 1.0,
        "length_penalty": 1.0,
        "repetition_penalty": 1.0,
        "no_repeat_ngram_size": 0,
        "temperature": 0.0,
        "compression_ratio_threshold": 2.4,
        "log_prob_threshold": -1.0,
        "no_speech_threshold": 0.6,
        "vad_filter": False,
        "vad_parameters": None,
        "word_timestamps": True,
        "condition_on_previous_text": False,
        "prompt_reset_on_temperature": 0.5,
        "initial_prompt": None,
        "prefix": None,
        "suppress_blank": True,
        "suppress_tokens": [-1],
        "without_timestamps": False,
        "max_initial_timestamp": 1.0,
        "prepend_punctuations": "\"'“¿([{-",
        "append_punctuations": "\"'.。,，!！?？:：”)]}、",
        "multilingual": False,
        "max_new_tokens": None,
        "chunk_length": None,
        "clip_timestamps": "0",
        "hallucination_silence_threshold": None,
        "hotwords": None,
        "language_detection_threshold": 0.5,
        "language_detection_segments": 1,
    }
    values.update(overrides)
    values["profile_checksum_sha256"] = canonical_profile_checksum(values)
    return PinnedAsrProfile.model_validate(values)


def _input(tmp_path: Path, profile: PinnedAsrProfile) -> TranscriptionInput:
    normalized_path = tmp_path / "normalized.wav"
    normalized_path.write_bytes(b"deterministic-normalized-audio")
    return TranscriptionInput(
        normalized_audio=VerifiedNormalizedAudioHandle(
            source_audio_file_id="audio_synthetic_001",
            source_asset_version=1,
            source_checksum_sha256=sha256(b"source-audio").hexdigest(),
            normalized_asset_version=1,
            normalized_checksum_sha256=sha256(
                b"deterministic-normalized-audio"
            ).hexdigest(),
            normalized_object_key="normalized/synthetic-001.wav",
            local_processing_path=normalized_path,
            verification_status="verified",
            is_current=True,
        ),
        profile=profile,
    )


def _runtime(**overrides: object) -> AsrRuntimeVersions:
    values: dict[str, object] = {
        "faster_whisper_version": "1.2.1",
        "ctranslate2_version": "4.8.1",
        "decoder_name": "soundfile",
        "decoder_version": "0.14.0",
        "decoder_available": True,
    }
    values.update(overrides)
    return AsrRuntimeVersions(**values)


def _provider(
    profile: PinnedAsrProfile,
    model: FakeWhisperModel,
    *,
    runtime: AsrRuntimeVersions | None = None,
) -> LocalWhisperProvider:
    return LocalWhisperProvider(
        profile=profile,
        runtime_inspector=lambda: runtime or _runtime(),
        model_factory=lambda **_: model,
    )


def test_provider_returns_canonical_draft_with_pinned_provenance(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    model = FakeWhisperModel()

    result = _provider(profile, model).transcribe(_input(tmp_path, profile))

    assert result.status == "completed"
    assert result.provider_id == "local_faster_whisper"
    assert [segment.temporary_speaker_id for segment in result.segments] == [
        "UNK",
        "UNK",
    ]
    assert [segment.source_speaker_label for segment in result.segments] == [
        "UNK",
        "UNK",
    ]
    assert result.segments[0].start_ms == 125
    assert result.segments[0].end_ms == 1375
    assert result.segments[0].segment_id.startswith("asrseg-000001-")
    assert result.provenance is not None
    assert result.provenance.model_checksum_sha256 == profile.model_checksum_sha256
    assert result.provenance.temperature == 0.0
    assert result.provenance.word_timestamps is True
    assert result.provenance.normalized_audio_asset_version == 1
    assert result.provenance.detected_language_probability == 0.97
    assert result.raw_provider_payload is not None
    assert result.raw_provider_payload.segments[0].provider_segment_id == "7"

    for field_name in (
        "device",
        "device_index",
        "compute_type",
        "cpu_threads",
        "num_workers",
        "language_mode",
        "task",
        "log_progress",
        "beam_size",
        "best_of",
        "patience",
        "length_penalty",
        "repetition_penalty",
        "no_repeat_ngram_size",
        "temperature",
        "compression_ratio_threshold",
        "log_prob_threshold",
        "no_speech_threshold",
        "vad_filter",
        "vad_parameters",
        "word_timestamps",
        "condition_on_previous_text",
        "prompt_reset_on_temperature",
        "initial_prompt",
        "prefix",
        "suppress_blank",
        "suppress_tokens",
        "without_timestamps",
        "max_initial_timestamp",
        "prepend_punctuations",
        "append_punctuations",
        "multilingual",
        "max_new_tokens",
        "chunk_length",
        "clip_timestamps",
        "hallucination_silence_threshold",
        "hotwords",
        "language_detection_threshold",
        "language_detection_segments",
    ):
        assert getattr(result.provenance, field_name) == getattr(
            profile,
            field_name,
        )


def test_decoding_projection_covers_every_non_path_profile_field() -> None:
    assert set(AsrProfileProvenanceProjection.model_fields) == (
        set(PinnedAsrProfile.model_fields) - {"model_artifact_path"}
    )


def test_auto_language_mode_preserves_low_confidence_warning(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path, language_mode="auto")
    model = FakeWhisperModel(language_probability=0.2)

    result = _provider(profile, model).transcribe(_input(tmp_path, profile))

    assert result.status == "completed"
    assert result.language == "th"
    assert result.provenance is not None
    assert result.provenance.detected_language_probability == 0.2
    assert any(
        warning.code == "asr_language_confidence_below_threshold"
        for warning in result.warnings
    )


def test_provider_passes_every_profile_parameter_explicitly(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    model = FakeWhisperModel()

    result = _provider(profile, model).transcribe(_input(tmp_path, profile))

    assert result.status == "completed"
    assert len(model.calls) == 1
    _, kwargs = model.calls[0]
    assert kwargs == {
        "language": "th",
        "task": "transcribe",
        "log_progress": False,
        "beam_size": 5,
        "best_of": 5,
        "patience": 1.0,
        "length_penalty": 1.0,
        "repetition_penalty": 1.0,
        "no_repeat_ngram_size": 0,
        "temperature": 0.0,
        "compression_ratio_threshold": 2.4,
        "log_prob_threshold": -1.0,
        "no_speech_threshold": 0.6,
        "vad_filter": False,
        "vad_parameters": None,
        "word_timestamps": True,
        "condition_on_previous_text": False,
        "prompt_reset_on_temperature": 0.5,
        "initial_prompt": None,
        "prefix": None,
        "suppress_blank": True,
        "suppress_tokens": [-1],
        "without_timestamps": False,
        "max_initial_timestamp": 1.0,
        "prepend_punctuations": "\"'“¿([{-",
        "append_punctuations": "\"'.。,，!！?？:：”)]}、",
        "multilingual": False,
        "max_new_tokens": None,
        "chunk_length": None,
        "clip_timestamps": "0",
        "hallucination_silence_threshold": None,
        "hotwords": None,
        "language_detection_threshold": 0.5,
        "language_detection_segments": 1,
    }


def test_canonical_segment_ids_are_stable_for_repeated_transcription(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    transcription_input = _input(tmp_path, profile)

    first = _provider(profile, FakeWhisperModel()).transcribe(transcription_input)
    second = _provider(profile, FakeWhisperModel()).transcribe(transcription_input)

    assert [segment.segment_id for segment in first.segments] == [
        segment.segment_id for segment in second.segments
    ]


def test_public_draft_serialization_excludes_private_provider_payload_and_storage_key(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)

    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )

    public_projection = result.to_public_projection()
    public_payload = public_projection.model_dump(mode="json")
    assert "raw_provider_payload" not in public_payload
    assert (
        "normalized_audio_object_key"
        not in public_payload["provenance"]
    )
    assert result.raw_provider_payload is not None
    assert result.provenance is not None
    private_payload = result.raw_provider_payload.model_dump(mode="json")
    private_checksum = sha256(
        json.dumps(
            private_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert (
        private_checksum
        == result.provenance.raw_provider_payload_checksum_sha256
    )
    assert len(result.provenance.input_lineage_checksum_sha256) == 64
    assert public_projection.provenance is not None
    assert (
        public_projection.provenance.input_lineage_checksum_sha256
        == result.provenance.input_lineage_checksum_sha256
    )
    safe_repr = repr(result)
    assert "raw_provider_payload=RawProviderPayload" not in safe_repr
    assert "normalized/synthetic-001.wav" not in safe_repr

    serialized_public = public_projection.model_dump_json()
    rebuilt_public = PublicCanonicalTranscriptionDraft.model_validate_json(
        serialized_public
    )
    assert rebuilt_public == public_projection
    with pytest.raises(ValidationError):
        CanonicalTranscriptionDraft.model_validate_json(serialized_public)


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("provider_id", "different_provider"),
        ("source_audio_file_id", "audio_synthetic_002"),
        ("source_audio_asset_version", 2),
        ("source_audio_checksum_sha256", "a" * 64),
        ("normalized_audio_asset_version", 2),
        ("normalized_audio_checksum_sha256", "b" * 64),
        ("profile_id", "different-profile"),
        ("profile_version", 2),
        ("profile_checksum_sha256", "c" * 64),
    ],
)
def test_input_lineage_checksum_rejects_private_and_public_reassignment(
    tmp_path: Path,
    field_name: str,
    replacement: object,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )
    assert result.provenance is not None

    with pytest.raises(ValidationError, match="input lineage checksum"):
        result.provenance.model_copy(update={field_name: replacement})

    private_record = result.to_private_record()
    private_record["provenance"][field_name] = replacement
    with pytest.raises(ValidationError, match="input lineage checksum"):
        CanonicalTranscriptionDraft.model_validate_json(
            json.dumps(private_record, ensure_ascii=False)
        )

    public = result.to_public_projection()
    assert public.provenance is not None
    with pytest.raises(ValidationError, match="input lineage checksum"):
        public.provenance.model_copy(update={field_name: replacement})

    public_record = public.model_dump(mode="json")
    public_record["provenance"][field_name] = replacement
    with pytest.raises(ValidationError, match="input lineage checksum"):
        PublicCanonicalTranscriptionDraft.model_validate_json(
            json.dumps(public_record, ensure_ascii=False)
        )


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("provider_id", ""),
        ("source_audio_file_id", "unsafe/source"),
        ("source_audio_asset_version", 0),
        ("normalized_audio_asset_version", 0),
        ("profile_id", "unsafe profile"),
        ("profile_version", 0),
        ("source_audio_checksum_sha256", "not-a-sha256"),
        ("normalized_audio_checksum_sha256", "not-a-sha256"),
        ("profile_checksum_sha256", "not-a-sha256"),
        ("raw_provider_payload_checksum_sha256", "not-a-sha256"),
    ],
)
def test_provenance_rejects_unsafe_lineage_fields(
    tmp_path: Path,
    field_name: str,
    replacement: object,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )
    private_record = result.to_private_record()
    private_record["provenance"][field_name] = replacement

    with pytest.raises(ValidationError):
        CanonicalTranscriptionDraft.model_validate(private_record)


def test_drafts_revalidate_injected_provenance_lineage_instances(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )
    assert result.provenance is not None
    private_values = {
        field_name: getattr(result.provenance, field_name)
        for field_name in type(result.provenance).model_fields
    }
    private_values["source_audio_asset_version"] = 2
    unverified_private = type(result.provenance).model_construct(
        **private_values
    )

    with pytest.raises(ValidationError, match="input lineage checksum"):
        result.model_copy(update={"provenance": unverified_private})

    public = result.to_public_projection()
    assert public.provenance is not None
    public_values = {
        field_name: getattr(public.provenance, field_name)
        for field_name in type(public.provenance).model_fields
    }
    public_values["source_audio_asset_version"] = 2
    unverified_public = type(public.provenance).model_construct(**public_values)

    with pytest.raises(ValidationError, match="input lineage checksum"):
        public.model_copy(update={"provenance": unverified_public})

    private_values = {
        field_name: getattr(result.provenance, field_name)
        for field_name in type(result.provenance).model_fields
    }
    private_values["model_identifier"] = "different/model"
    unverified_private = type(result.provenance).model_construct(
        **private_values
    )
    with pytest.raises(ValidationError, match="decoding provenance checksum"):
        result.model_copy(update={"provenance": unverified_private})

    public_values = {
        field_name: getattr(public.provenance, field_name)
        for field_name in type(public.provenance).model_fields
    }
    public_values["model_identifier"] = "different/model"
    unverified_public = type(public.provenance).model_construct(**public_values)
    with pytest.raises(ValidationError, match="decoding provenance checksum"):
        public.model_copy(update={"provenance": unverified_public})


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("model_identifier", "different/model"),
        ("model_revision", "different-revision"),
        ("model_checksum_sha256", "d" * 64),
        ("faster_whisper_version", "9.9.9"),
        ("ctranslate2_version", "9.9.9"),
        ("decoder_name", "different-decoder"),
        ("decoder_version", "9.9.9"),
        ("device", "cuda"),
        ("compute_type", "float32"),
        ("beam_size", 6),
        ("best_of", 6),
        ("word_timestamps", False),
        ("condition_on_previous_text", True),
    ],
)
def test_decoding_provenance_checksum_rejects_private_and_public_mutation(
    tmp_path: Path,
    field_name: str,
    replacement: object,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )
    assert result.provenance is not None

    with pytest.raises(ValidationError, match="decoding provenance checksum"):
        result.provenance.model_copy(update={field_name: replacement})

    private_record = result.to_private_record()
    private_record["provenance"][field_name] = replacement
    with pytest.raises(ValidationError, match="decoding provenance checksum"):
        CanonicalTranscriptionDraft.model_validate_json(
            json.dumps(private_record, ensure_ascii=False)
        )

    public = result.to_public_projection()
    assert public.provenance is not None
    with pytest.raises(ValidationError, match="decoding provenance checksum"):
        public.provenance.model_copy(update={field_name: replacement})

    public_record = public.model_dump(mode="json")
    public_record["provenance"][field_name] = replacement
    with pytest.raises(ValidationError, match="decoding provenance checksum"):
        PublicCanonicalTranscriptionDraft.model_validate_json(
            json.dumps(public_record, ensure_ascii=False)
        )


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("model_identifier", ""),
        ("model_revision", ""),
        ("faster_whisper_version", ""),
        ("ctranslate2_version", ""),
        ("decoder_name", ""),
        ("decoder_version", ""),
        ("device", "quantum"),
        ("beam_size", 0),
        ("best_of", 0),
        ("temperature", 0.1),
        ("cpu_threads", -1),
        ("num_workers", 0),
    ],
)
def test_provenance_rejects_impossible_runtime_and_decoding_values(
    tmp_path: Path,
    field_name: str,
    replacement: object,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )
    private_record = result.to_private_record()
    private_record["provenance"][field_name] = replacement

    with pytest.raises(ValidationError):
        CanonicalTranscriptionDraft.model_validate(private_record)


def test_canonical_draft_rejects_mismatched_raw_payload_checksum_on_rebuild(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )
    private_record = result.to_private_record()
    private_record["raw_provider_payload"]["segments"][0]["text"] = "tampered"

    CanonicalTranscriptionDraft.model_rebuild(force=True)
    with pytest.raises(
        ValidationError,
        match="raw provider payload checksum",
    ):
        CanonicalTranscriptionDraft.model_validate(private_record)
    with pytest.raises(
        ValidationError,
        match="raw provider payload checksum",
    ):
        CanonicalTranscriptionDraft.model_validate_json(
            json.dumps(
                private_record,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )


def test_canonical_draft_model_copy_revalidates_raw_payload_checksum(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )
    assert result.raw_provider_payload is not None
    tampered_payload = result.raw_provider_payload.model_copy(
        update={"language": "tampered"}
    )

    with pytest.raises(
        ValidationError,
        match="raw provider payload checksum",
    ):
        result.model_copy(
            update={"raw_provider_payload": tampered_payload}
        )


def test_completed_canonical_draft_requires_private_payload_and_provenance(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )
    private_record = result.to_private_record()

    without_raw = {**private_record, "raw_provider_payload": None}
    with pytest.raises(ValidationError, match="completed canonical draft"):
        CanonicalTranscriptionDraft.model_validate(without_raw)

    without_provenance = {**private_record, "provenance": None}
    with pytest.raises(ValidationError, match="requires provenance"):
        CanonicalTranscriptionDraft.model_validate(without_provenance)

    rebuilt = CanonicalTranscriptionDraft.model_validate(private_record)
    assert rebuilt.raw_provider_payload == result.raw_provider_payload
    assert rebuilt.provenance == result.provenance


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("text", "tampered canonical text"),
        ("start_ms", 126),
        ("end_ms", 1376),
        ("temporary_speaker_id", "SPK_01"),
        ("source_speaker_label", "SPK_01"),
        ("segment_id", "asrseg-tampered"),
        ("confidence", 0.9),
    ],
)
def test_canonical_draft_rejects_segment_content_not_derived_from_raw_evidence(
    tmp_path: Path,
    field_name: str,
    replacement: object,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )
    private_record = result.to_private_record()
    private_record["segments"][0][field_name] = replacement

    with pytest.raises(ValidationError, match="canonical segment"):
        CanonicalTranscriptionDraft.model_validate(private_record)
    with pytest.raises(ValidationError, match="canonical segment"):
        CanonicalTranscriptionDraft.model_validate_json(
            json.dumps(private_record, ensure_ascii=False)
        )


def test_canonical_draft_rejects_reordered_segments_and_language_mismatch(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )
    private_record = result.to_private_record()
    reordered = {
        **private_record,
        "segments": list(reversed(private_record["segments"])),
    }
    wrong_language = {**private_record, "language": "en"}

    with pytest.raises(ValidationError, match="canonical segment"):
        CanonicalTranscriptionDraft.model_validate(reordered)
    with pytest.raises(ValidationError, match="language"):
        CanonicalTranscriptionDraft.model_validate(wrong_language)


@pytest.mark.parametrize("replacement", [0.2, None])
def test_canonical_draft_rejects_detected_language_probability_mismatch(
    tmp_path: Path,
    replacement: float | None,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )
    private_record = result.to_private_record()
    private_record["provenance"][
        "detected_language_probability"
    ] = replacement

    with pytest.raises(ValidationError, match="language probability"):
        CanonicalTranscriptionDraft.model_validate(private_record)
    with pytest.raises(ValidationError, match="language probability"):
        CanonicalTranscriptionDraft.model_validate_json(
            json.dumps(private_record, ensure_ascii=False)
        )


def test_canonical_draft_model_copy_rejects_semantic_segment_tampering(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )
    tampered_segment = result.segments[0].model_copy(
        update={"text": "tampered canonical text"}
    )

    with pytest.raises(ValidationError, match="canonical segment"):
        result.model_copy(
            update={
                "segments": (tampered_segment, *result.segments[1:]),
            }
        )


def test_integrity_models_revalidate_model_copy_and_injected_instances(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)

    with pytest.raises(ValidationError, match="temperature"):
        profile.model_copy(update={"temperature": 0.2})
    with pytest.raises(ValidationError, match="checksum"):
        profile.model_copy(update={"profile_id": "changed-with-stale-checksum"})

    vad = PinnedVadParameters(
        threshold=0.5,
        neg_threshold=None,
        min_speech_duration_ms=0,
        max_speech_duration_s=30.0,
        min_silence_duration_ms=500,
        speech_pad_ms=100,
    )
    with pytest.raises(ValidationError):
        vad.model_copy(update={"threshold": 2.0})

    stale_profile = PinnedAsrProfile.model_construct(
        **{
            **profile.model_dump(),
            "temperature": 0.2,
        }
    )
    calls: list[dict[str, object]] = []
    provider = LocalWhisperProvider(
        profile=stale_profile,
        runtime_inspector=lambda: _runtime(),
        model_factory=lambda **kwargs: calls.append(kwargs),
    )
    result = provider.transcribe(_input(tmp_path, profile))

    assert result.status == "unavailable"
    assert result.error_code == "runtime_profile_unverified"
    assert calls == []


def test_transcription_revalidates_model_constructed_input(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    valid_input = _input(tmp_path, profile)
    stale_profile = PinnedAsrProfile.model_construct(
        **{
            **profile.model_dump(),
            "profile_checksum_sha256": "0" * 64,
        }
    )
    stale_input = TranscriptionInput.model_construct(
        normalized_audio=valid_input.normalized_audio,
        profile=stale_profile,
        placeholder_profile_id=None,
    )
    provider = _provider(profile, FakeWhisperModel())

    result = provider.transcribe(stale_input)

    assert result.status == "unavailable"
    assert result.error_code == "transcription_input_unverified"


def test_provider_discovery_and_cached_model_bound_full_tree_hashes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    hash_calls = 0
    model_factory_calls = 0
    real_snapshot = local_provider_module.snapshot_model_artifact

    def counting_snapshot(path: Path):
        nonlocal hash_calls
        hash_calls += 1
        return real_snapshot(path)

    def counting_factory(**_: object) -> FakeWhisperModel:
        nonlocal model_factory_calls
        model_factory_calls += 1
        return FakeWhisperModel()

    monkeypatch.setattr(
        local_provider_module,
        "snapshot_model_artifact",
        counting_snapshot,
    )
    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=lambda: _runtime(),
        model_factory=counting_factory,
    )

    assert provider.check_availability().available is True
    assert provider.check_availability().available is True
    assert hash_calls == 1

    first = provider.transcribe(_input(tmp_path, profile))
    second = provider.transcribe(_input(tmp_path, profile))

    assert first.status == "completed"
    assert second.status == "completed"
    assert hash_calls == 2
    assert model_factory_calls == 1


def test_provider_discovery_rejects_wrong_model_checksum_before_construction(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    (model_path / "model.bin").write_bytes(b"wrong-model-weights")
    calls: list[dict[str, object]] = []
    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=lambda: _runtime(),
        model_factory=lambda **kwargs: calls.append(kwargs),
    )

    availability = provider.check_availability()

    assert availability.available is False
    assert availability.reason_code == "model_checksum_mismatch"
    assert calls == []


def test_segment_and_status_validators_reject_invalid_or_partial_states(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="end"):
        CanonicalTranscriptionSegment(
            segment_id="segment-invalid",
            temporary_speaker_id="UNK",
            source_speaker_label="UNK",
            start_ms=10,
            end_ms=9,
            text="invalid",
        )
    with pytest.raises(ValidationError):
        RawProviderSegment(
            provider_segment_id="raw-invalid",
            seek=0,
            start_seconds=float("nan"),
            end_seconds=1.0,
            text="invalid",
            token_ids=(),
            temperature=0.0,
            average_log_probability=None,
            compression_ratio=None,
            no_speech_probability=None,
            words=(),
        )

    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )
    public = result.to_public_projection()

    with pytest.raises(ValidationError, match="nonempty"):
        result.model_copy(update={"segments": ()})
    with pytest.raises(ValidationError, match="partial"):
        result.model_copy(update={"status": "failed"})
    with pytest.raises(ValidationError, match="nonempty"):
        public.model_copy(update={"segments": ()})
    with pytest.raises(ValidationError, match="partial"):
        public.model_copy(update={"status": "unavailable"})


def test_private_and_public_draft_states_are_fully_discriminated(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    completed = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )

    for update in (
        {"error_code": "unexpected"},
        {"error_message": "unexpected"},
        {
            "unavailability": AsrUnavailability(
                code="unexpected",
                message="unexpected",
                remediation="retry",
            )
        },
    ):
        with pytest.raises(ValidationError, match="completed"):
            completed.model_copy(update=update)
        invalid_record = {**completed.to_private_record(), **update}
        if "unavailability" in update:
            invalid_record["unavailability"] = update[
                "unavailability"
            ].model_dump(mode="json")
        with pytest.raises(ValidationError, match="completed"):
            CanonicalTranscriptionDraft.model_validate(invalid_record)

    unavailable = CanonicalTranscriptionDraft(
        status="unavailable",
        provider_id="local_faster_whisper",
        unavailability=AsrUnavailability(
            code="runtime_unavailable",
            message="Runtime unavailable.",
            remediation="Install the pinned runtime.",
        ),
        error_code="runtime_unavailable",
        error_message="Runtime unavailable.",
    )
    for update in (
        {"unavailability": None},
        {"error_code": "different_code"},
        {"error_message": "Different message."},
    ):
        with pytest.raises(ValidationError, match="unavailable"):
            unavailable.model_copy(update=update)
        invalid_record = {**unavailable.to_private_record(), **update}
        with pytest.raises(ValidationError, match="unavailable"):
            CanonicalTranscriptionDraft.model_validate_json(
                json.dumps(invalid_record, ensure_ascii=False)
            )

    failed = CanonicalTranscriptionDraft(
        status="failed",
        provider_id="local_faster_whisper",
        error_code="provider_failed",
        error_message="Provider failed.",
    )
    for update in (
        {"error_code": None},
        {"error_message": ""},
        {
            "unavailability": AsrUnavailability(
                code="wrong_state",
                message="Wrong state.",
                remediation="Retry.",
            )
        },
    ):
        with pytest.raises(ValidationError, match="failed"):
            failed.model_copy(update=update)
        invalid_record = {**failed.to_private_record(), **update}
        if "unavailability" in update:
            invalid_record["unavailability"] = update[
                "unavailability"
            ].model_dump(mode="json")
        with pytest.raises(ValidationError, match="failed"):
            CanonicalTranscriptionDraft.model_validate_json(
                json.dumps(invalid_record, ensure_ascii=False)
            )

    public_completed = completed.to_public_projection()
    public_unavailable = unavailable.to_public_projection()
    public_failed = failed.to_public_projection()
    for public, update, match in (
        (public_completed, {"error_message": "unexpected"}, "completed"),
        (public_unavailable, {"error_code": "different"}, "unavailable"),
        (public_failed, {"error_message": ""}, "failed"),
    ):
        with pytest.raises(ValidationError, match=match):
            public.model_copy(update=update)
        invalid_record = {
            **public.model_dump(mode="json"),
            **update,
        }
        with pytest.raises(ValidationError, match=match):
            PublicCanonicalTranscriptionDraft.model_validate_json(
                json.dumps(invalid_record, ensure_ascii=False)
            )


def test_canonical_provider_payload_is_deeply_immutable_and_json_compatible(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    result = _provider(profile, FakeWhisperModel()).transcribe(
        _input(tmp_path, profile)
    )

    assert isinstance(result.segments, tuple)
    assert isinstance(result.warnings, tuple)
    assert result.raw_provider_payload is not None
    assert isinstance(result.raw_provider_payload.segments, tuple)
    assert isinstance(result.raw_provider_payload.segments[0].token_ids, tuple)
    assert isinstance(result.raw_provider_payload.segments[0].words, tuple)

    with pytest.raises(AttributeError):
        result.segments.append(result.segments[0])
    with pytest.raises(AttributeError):
        result.raw_provider_payload.segments[0].words.append(
            result.raw_provider_payload.segments[0].words[0]
        )
    with pytest.raises(TypeError):
        result.raw_provider_payload.segments[0].token_ids[0] = 999

    public_payload = result.to_public_projection().model_dump(mode="json")
    private_payload = result.raw_provider_payload.model_dump(mode="json")
    assert isinstance(public_payload["segments"], list)
    assert isinstance(public_payload["warnings"], list)
    assert isinstance(public_payload["warnings"][0], dict)
    assert isinstance(private_payload["segments"], list)
    assert isinstance(private_payload["segments"][0]["token_ids"], list)
    assert isinstance(private_payload["segments"][0]["words"], list)


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        (lambda profile, path: path.rename(path.with_name("missing-model")), "model_artifact_missing"),
        (
            lambda profile, path: (path / "model.bin").write_bytes(
                b"unexpected-model-weights"
            ),
            "model_checksum_mismatch",
        ),
    ],
)
def test_missing_or_wrong_model_returns_structured_unavailable_without_invoking_model(
    tmp_path: Path,
    mutate,
    expected_code: str,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    mutate(profile, model_path)
    calls: list[dict[str, object]] = []
    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=lambda: _runtime(),
        model_factory=lambda **kwargs: calls.append(kwargs),
    )

    result = provider.transcribe(_input(tmp_path, profile))

    assert result.status == "unavailable"
    assert result.unavailability is not None
    assert result.unavailability.code == expected_code
    assert calls == []


def test_model_tree_with_symlink_is_rejected_before_model_load(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    external_weights = tmp_path / "external-model.bin"
    external_weights.write_bytes(b"different-external-weights")
    (model_path / "model.bin").unlink()
    (model_path / "model.bin").symlink_to(external_weights)
    calls: list[dict[str, object]] = []
    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=lambda: _runtime(),
        model_factory=lambda **kwargs: calls.append(kwargs),
    )

    result = provider.transcribe(_input(tmp_path, profile))

    assert result.status == "unavailable"
    assert result.unavailability is not None
    assert result.unavailability.code == "model_artifact_unsafe"
    assert calls == []


def test_model_root_directory_symlink_is_rejected_before_model_load(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    linked_model_path = tmp_path / "linked-whisper-model"
    linked_model_path.symlink_to(model_path, target_is_directory=True)
    profile = _profile(
        model_path,
        model_artifact_path=linked_model_path,
    )
    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=lambda: _runtime(),
        model_factory=lambda **_: pytest.fail("model factory must not be invoked"),
    )

    availability = provider.check_availability()

    assert availability.available is False
    assert availability.reason_code == "model_artifact_unsafe"


def test_relative_model_artifact_path_cannot_escape_repository(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(
        model_path,
        model_artifact_path=Path("../../../../outside-model"),
    )
    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=lambda: _runtime(),
        model_factory=lambda **_: pytest.fail("model factory must not be invoked"),
    )

    availability = provider.check_availability()

    assert availability.available is False
    assert availability.reason_code == "model_artifact_unsafe"


def test_model_tree_with_non_regular_entry_is_rejected_before_model_load(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    (model_path / "model.bin").unlink()
    os.mkfifo(model_path / "model.bin")
    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=lambda: _runtime(),
        model_factory=lambda **_: pytest.fail("model factory must not be invoked"),
    )

    availability = provider.check_availability()

    assert availability.available is False
    assert availability.reason_code == "model_artifact_unsafe"


@pytest.mark.parametrize(
    ("runtime", "expected_code"),
    [
        (_runtime(faster_whisper_version=None), "faster_whisper_unavailable"),
        (_runtime(ctranslate2_version=None), "ctranslate2_unavailable"),
        (_runtime(decoder_available=False), "decoder_unavailable"),
        (_runtime(ctranslate2_version="4.7.1"), "runtime_version_mismatch"),
    ],
)
def test_runtime_capability_failures_are_structured_and_do_not_invoke_model(
    tmp_path: Path,
    runtime: AsrRuntimeVersions,
    expected_code: str,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    calls: list[dict[str, object]] = []
    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=lambda: runtime,
        model_factory=lambda **kwargs: calls.append(kwargs),
    )

    result = provider.transcribe(_input(tmp_path, profile))

    assert result.status == "unavailable"
    assert result.unavailability is not None
    assert result.unavailability.code == expected_code
    assert calls == []


def test_runtime_inspector_exception_is_structured_and_never_invokes_model(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    calls: list[dict[str, object]] = []

    def raise_runtime_error() -> AsrRuntimeVersions:
        raise RuntimeError("sensitive runtime detail")

    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=raise_runtime_error,
        model_factory=lambda **kwargs: calls.append(kwargs),
    )

    availability = provider.check_availability()
    result = provider.transcribe(_input(tmp_path, profile))

    assert availability.available is False
    assert availability.reason_code == "runtime_inspection_failed"
    assert availability.remediation
    assert "sensitive runtime detail" not in availability.reason
    assert result.status == "unavailable"
    assert result.unavailability is not None
    assert result.unavailability.code == "runtime_inspection_failed"
    assert calls == []


def test_profile_configuration_exception_is_structured_unavailable(
    tmp_path: Path,
) -> None:
    class BrokenSettings:
        @property
        def asr_runtime_profile_path(self) -> str:
            raise RuntimeError("sensitive configuration detail")

    provider = LocalWhisperProvider(
        settings=BrokenSettings(),
        runtime_inspector=lambda: _runtime(),
        model_factory=lambda **_: pytest.fail("model factory must not be invoked"),
    )

    availability = provider.check_availability()

    assert availability.available is False
    assert availability.reason_code == "runtime_inspection_failed"
    assert availability.remediation
    assert "sensitive configuration detail" not in availability.reason


def test_transcription_uses_the_exact_runtime_context_that_passed_the_gate(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    inspections = 0

    def inspect_runtime_once() -> AsrRuntimeVersions:
        nonlocal inspections
        inspections += 1
        if inspections > 1:
            return _runtime(ctranslate2_version="unexpected-second-runtime")
        return _runtime()

    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=inspect_runtime_once,
        model_factory=lambda **_: FakeWhisperModel(),
    )

    result = provider.transcribe(_input(tmp_path, profile))

    assert result.status == "completed"
    assert result.provenance is not None
    assert result.provenance.ctranslate2_version == "4.8.1"
    assert inspections == 1


def test_model_mutation_during_runtime_inspection_blocks_model_load(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    calls: list[dict[str, object]] = []

    def mutate_model_during_inspection() -> AsrRuntimeVersions:
        (model_path / "model.bin").write_bytes(b"mutated-during-inspection")
        return _runtime()

    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=mutate_model_during_inspection,
        model_factory=lambda **kwargs: calls.append(kwargs),
    )

    result = provider.transcribe(_input(tmp_path, profile))

    assert result.status == "unavailable"
    assert result.error_code == "model_artifact_changed_before_transcription"
    assert result.segments == ()
    assert result.provenance is None
    assert result.raw_provider_payload is None
    assert calls == []


def test_model_mutation_during_model_factory_blocks_partial_success(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)

    def mutate_model_in_factory(**_: object) -> FakeWhisperModel:
        (model_path / "model.bin").write_bytes(b"mutated-during-model-load")
        return FakeWhisperModel()

    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=lambda: _runtime(),
        model_factory=mutate_model_in_factory,
    )

    result = provider.transcribe(_input(tmp_path, profile))

    assert result.status == "failed"
    assert result.error_code == "model_artifact_changed_during_load"
    assert result.segments == ()
    assert result.provenance is None
    assert result.raw_provider_payload is None


def test_model_mutation_during_inference_blocks_partial_success(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)

    class MutatingModelWhisperModel(FakeWhisperModel):
        def transcribe(self, audio: str, **kwargs):
            (model_path / "model.bin").write_bytes(
                b"mutated-during-inference"
            )
            return super().transcribe(audio, **kwargs)

    provider = _provider(profile, MutatingModelWhisperModel())

    result = provider.transcribe(_input(tmp_path, profile))

    assert result.status == "failed"
    assert result.error_code == "model_artifact_changed_during_transcription"
    assert result.segments == ()
    assert result.provenance is None
    assert result.raw_provider_payload is None


def test_normalized_audio_mutation_during_model_factory_blocks_partial_success(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    transcription_input = _input(tmp_path, profile)
    assert transcription_input.normalized_audio is not None

    def mutate_audio_in_factory(**_: object) -> FakeWhisperModel:
        transcription_input.normalized_audio.local_processing_path.write_bytes(
            b"mutated-before-transcribe"
        )
        return FakeWhisperModel()

    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=lambda: _runtime(),
        model_factory=mutate_audio_in_factory,
    )

    result = provider.transcribe(transcription_input)

    assert result.status == "failed"
    assert result.error_code == "normalized_asset_changed_during_transcription"
    assert result.segments == ()
    assert result.provenance is None
    assert result.raw_provider_payload is None


def test_normalized_audio_mutation_during_transcription_blocks_partial_success(
    tmp_path: Path,
) -> None:
    class MutatingAudioWhisperModel(FakeWhisperModel):
        def transcribe(self, audio: str, **kwargs):
            Path(audio).write_bytes(b"mutated-during-transcribe")
            return super().transcribe(audio, **kwargs)

    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    provider = _provider(profile, MutatingAudioWhisperModel())

    result = provider.transcribe(_input(tmp_path, profile))

    assert result.status == "failed"
    assert result.error_code == "normalized_asset_changed_during_transcription"
    assert result.segments == ()
    assert result.provenance is None
    assert result.raw_provider_payload is None


def test_unverified_runtime_profile_file_returns_structured_unavailable(
    tmp_path: Path,
) -> None:
    runtime_profile = tmp_path / "runtime-profile.json"
    runtime_profile.write_text('{"model_identifier":"floating-base"}', encoding="utf-8")
    provider = LocalWhisperProvider(
        profile_path=runtime_profile,
        runtime_inspector=lambda: _runtime(),
        model_factory=lambda **_: pytest.fail("model factory must not be invoked"),
    )

    availability = provider.check_availability()
    result = provider.transcribe(
        TranscriptionInput.unverified_placeholder(profile_id="missing-profile")
    )

    assert availability.available is False
    assert availability.reason_code == "runtime_profile_unverified"
    assert result.status == "unavailable"
    assert result.unavailability is not None
    assert result.unavailability.code == "runtime_profile_unverified"


def test_input_profile_must_exactly_match_verified_provider_profile(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    different_valid_profile = _profile(
        model_path,
        profile_id="different-valid-profile",
    )
    transcription_input = _input(tmp_path, profile).model_copy(
        update={"profile": different_valid_profile}
    )
    calls: list[dict[str, object]] = []
    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=lambda: _runtime(),
        model_factory=lambda **kwargs: calls.append(kwargs),
    )

    result = provider.transcribe(transcription_input)

    assert result.status == "unavailable"
    assert result.unavailability is not None
    assert result.unavailability.code == "asr_profile_mismatch"
    assert calls == []


@pytest.mark.parametrize(
    ("handle_change", "expected_code"),
    [
        ({"verification_status": "unverified"}, "normalized_asset_unverified"),
        ({"is_current": False}, "normalized_asset_stale"),
        (
            {"normalized_checksum_sha256": "0" * 64},
            "normalized_asset_checksum_mismatch",
        ),
    ],
)
def test_provider_consumes_only_current_verified_normalized_asset(
    tmp_path: Path,
    handle_change: dict[str, object],
    expected_code: str,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    original = _input(tmp_path, profile)
    changed = original.normalized_audio.model_copy(update=handle_change)
    transcription_input = original.model_copy(update={"normalized_audio": changed})
    calls: list[dict[str, object]] = []
    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=lambda: _runtime(),
        model_factory=lambda **kwargs: calls.append(kwargs),
    )

    result = provider.transcribe(transcription_input)

    assert result.status == "unavailable"
    assert result.unavailability is not None
    assert result.unavailability.code == expected_code
    assert calls == []


@pytest.mark.parametrize("unsafe_kind", ["symlink", "directory"])
def test_provider_rejects_non_regular_normalized_working_path(
    tmp_path: Path,
    unsafe_kind: str,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    profile = _profile(model_path)
    original = _input(tmp_path, profile)
    assert original.normalized_audio is not None

    if unsafe_kind == "symlink":
        unsafe_path = tmp_path / "linked-normalized.wav"
        unsafe_path.symlink_to(original.normalized_audio.local_processing_path)
        unsafe_checksum = original.normalized_audio.normalized_checksum_sha256
    else:
        unsafe_path = tmp_path / "normalized-directory"
        unsafe_path.mkdir()
        (unsafe_path / "audio.bin").write_bytes(b"directory-is-not-audio")
        unsafe_checksum = hash_model_artifact(unsafe_path)

    unsafe_audio = original.normalized_audio.model_copy(
        update={
            "local_processing_path": unsafe_path,
            "normalized_checksum_sha256": unsafe_checksum,
        }
    )
    transcription_input = original.model_copy(
        update={"normalized_audio": unsafe_audio}
    )
    calls: list[dict[str, object]] = []
    provider = LocalWhisperProvider(
        profile=profile,
        runtime_inspector=lambda: _runtime(),
        model_factory=lambda **kwargs: calls.append(kwargs),
    )

    result = provider.transcribe(transcription_input)

    assert result.status == "unavailable"
    assert result.unavailability is not None
    assert result.unavailability.code == "normalized_asset_unsafe"
    assert calls == []


def test_profile_checksum_changes_for_each_output_affecting_setting(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)
    baseline = _profile(model_path)

    for field_name, replacement in {
        "model_revision": "fixture-revision-002",
        "language_mode": "auto",
        "beam_size": 3,
        "temperature": 0.1,
        "vad_filter": True,
        "word_timestamps": False,
        "condition_on_previous_text": True,
        "initial_prompt": "คำทดสอบ",
        "no_speech_threshold": 0.7,
        "suppress_tokens": [-1, 50363],
    }.items():
        changed = baseline.model_dump()
        changed[field_name] = replacement
        changed_checksum = canonical_profile_checksum(changed)
        assert changed_checksum != baseline.profile_checksum_sha256, field_name


def test_vad_enabled_profile_requires_all_vad_parameters(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)

    with pytest.raises(ValueError, match="vad_parameters"):
        _profile(model_path, vad_filter=True, vad_parameters=None)


def test_auto_language_profile_requires_pinned_detection_threshold(
    tmp_path: Path,
) -> None:
    model_path = _write_model_artifact(tmp_path)

    with pytest.raises(ValueError, match="language_detection_threshold"):
        _profile(
            model_path,
            language_mode="auto",
            language_detection_threshold=None,
        )
