# tests/test_asr_provider_registry.py
import pytest
from app.services.asr_providers.registry import asr_provider_registry
from app.services.asr_providers.mock_provider import MockTranscriptionProvider
from app.services.asr_providers.local_whisper_provider import LocalWhisperProvider


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
