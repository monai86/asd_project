# tests/test_asr_provider_registry.py
import pytest
from app.services.asr_providers.registry import asr_provider_registry
from app.services.asr_providers.mock_provider import MockTranscriptionProvider
from app.services.asr_providers.local_whisper_provider import LocalWhisperProvider
from app.services.asr_providers.manual_provider import ManualTranscriptionProvider


def test_default_registry_has_mock_provider():
    assert "mock" in asr_provider_registry


def test_default_registry_has_local_whisper_provider():
    assert "local_whisper" in asr_provider_registry


def test_mock_provider_is_available():
    p = asr_provider_registry.get("mock")
    avail = p.check_availability()
    assert avail.available is True


def test_local_whisper_provider_is_unavailable_by_default():
    p = asr_provider_registry.get("local_whisper")
    avail = p.check_availability()
    assert avail.available is False


def test_get_unknown_provider_raises_key_error():
    with pytest.raises(KeyError, match="not registered"):
        asr_provider_registry.get("nonexistent_xyz")


def test_list_supported_includes_both_providers():
    names = [p["provider_id"] for p in asr_provider_registry.list_supported()]
    assert "mock" in names
    assert "local_whisper" in names


def test_list_available_includes_only_mock():
    available = asr_provider_registry.list_available()
    ids = [p["provider_id"] for p in available]
    assert "mock" in ids
    assert "local_whisper" not in ids


def test_mock_provider_transcribe_returns_three_lines():
    p = MockTranscriptionProvider()
    result = p.transcribe("test-ref")
    assert result.status == "completed"
    assert len(result.transcript_lines) == 3


def test_mock_provider_transcript_has_timestamps():
    p = MockTranscriptionProvider()
    result = p.transcribe("test-ref")
    for line in result.transcript_lines:
        assert line.start_ms is not None


def test_mock_provider_has_mock_warning():
    p = MockTranscriptionProvider()
    result = p.transcribe("test-ref")
    assert any("MOCK" in w or "mock" in w.lower() for w in result.warnings)


def test_manual_provider_retains_noncanonical_speaker_labels_as_temporary_provenance():
    result = ManualTranscriptionProvider().transcribe(
        "local-audio-ref",
        {"draft_text": "SPK0: Synthetic first\nSPK1: Synthetic second"},
    )

    assert [line.speaker for line in result.transcript_lines] == ["SPK0", "SPK1"]
    assert [line.temporary_speaker_id for line in result.transcript_lines] == ["SPK0", "SPK1"]
    assert [line.source_speaker_label for line in result.transcript_lines] == ["SPK0", "SPK1"]


def test_manual_provider_does_not_mark_canonical_speaker_labels_as_temporary():
    result = ManualTranscriptionProvider().transcribe(
        "local-audio-ref",
        {"draft_text": "CHI: Synthetic child\nTHER: Synthetic therapist\nOTH: Synthetic other"},
    )

    assert [line.temporary_speaker_id for line in result.transcript_lines] == [None, None, None]
    assert [line.source_speaker_label for line in result.transcript_lines] == [None, None, None]


def test_manual_provider_preserves_distinct_punctuated_and_repeated_source_labels():
    result = ManualTranscriptionProvider().transcribe(
        "local-audio-ref",
        {
            "draft_text": (
                "longcluster01: Synthetic first\n"
                "longcluster02: Synthetic second\n"
                "*SPK-2!: Synthetic third\n"
                "longcluster01: Synthetic fourth"
            )
        },
    )

    assert [line.speaker for line in result.transcript_lines[:2]] == ["LONGCLUS", "LONGCLUS"]
    assert [line.temporary_speaker_id for line in result.transcript_lines] == [
        "longcluster01",
        "longcluster02",
        "SPK-2!",
        "longcluster01",
    ]
    assert [line.source_speaker_label for line in result.transcript_lines] == [
        "longcluster01",
        "longcluster02",
        "SPK-2!",
        "longcluster01",
    ]


def test_manual_provider_uses_stable_namespaced_digest_for_overlong_source_labels():
    raw_label = "source-" + "x" * 150
    result = ManualTranscriptionProvider().transcribe(
        "local-audio-ref",
        {"draft_text": f"{raw_label}: Synthetic first\n{raw_label}: Synthetic second"},
    )

    temporary_ids = [line.temporary_speaker_id for line in result.transcript_lines]
    assert temporary_ids[0] == temporary_ids[1]
    assert temporary_ids[0] is not None
    assert temporary_ids[0].startswith("manual:sha256:")
    assert len(temporary_ids[0]) <= 128
    assert [line.source_speaker_label for line in result.transcript_lines] == [raw_label, raw_label]


def test_manual_provider_bypasses_canonical_variants_and_colonless_lines():
    result = ManualTranscriptionProvider().transcribe(
        "local-audio-ref",
        {
            "draft_text": (
                "  * chi : Synthetic child\n"
                "ther: Synthetic therapist\n"
                " OTH : Synthetic other\n"
                "Synthetic colonless\n"
                ": Synthetic unlabeled"
            )
        },
    )

    assert [line.temporary_speaker_id for line in result.transcript_lines] == [None] * 5
    assert [line.source_speaker_label for line in result.transcript_lines] == [None] * 5


def test_local_whisper_transcribe_returns_unavailable():
    p = LocalWhisperProvider()
    result = p.transcribe("test-ref")
    assert result.status == "unavailable"
    assert len(result.transcript_lines) == 0


def test_get_default_returns_mock():
    default = asr_provider_registry.get_default()
    assert default.provider_id == "mock"


def test_registry_contains_check():
    assert "mock" in asr_provider_registry
    assert "nonexistent" not in asr_provider_registry
