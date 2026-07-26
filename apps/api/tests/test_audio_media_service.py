from __future__ import annotations

from hashlib import sha256
import importlib.util
from io import BytesIO
from pathlib import Path
import struct

import numpy as np
import pytest
import soundfile as sf


def test_audio_media_service_is_available() -> None:
    assert importlib.util.find_spec("app.services.audio_media_service") is not None


def _wav_bytes(
    samples: np.ndarray,
    *,
    sample_rate_hz: int,
) -> bytes:
    destination = BytesIO()
    sf.write(
        destination,
        samples,
        sample_rate_hz,
        format="WAV",
        subtype="PCM_16",
    )
    return destination.getvalue()


def test_registry_verifies_only_committed_wav_and_mp3_decoder_fixtures() -> None:
    from app.services.audio_media_service import get_decoder_capability_registry

    registry = get_decoder_capability_registry()

    assert registry.verified_formats == ("wav", "mp3")
    assert registry.runtime.soundfile_version == "0.14.0"
    assert registry.runtime.libsndfile_version == "1.2.2"
    assert registry.capability("wav").fixture_verified is True
    assert registry.capability("mp3").fixture_verified is True
    assert registry.capability("m4a").available is False
    assert registry.capability("webm").available is False


def test_probe_reads_actual_wav_and_mp3_bytes() -> None:
    from app.services.audio_media_service import probe_audio

    root = Path(__file__).resolve().parents[3]
    wav_path = root / "tests/fixtures/audio/v1.7.0/seed/thai_only.wav"
    mp3_path = root / "tests/fixtures/audio/v1.7.0/formats/verified_sample.mp3"

    with wav_path.open("rb") as source:
        wav = probe_audio(source)
    with mp3_path.open("rb") as source:
        mp3 = probe_audio(source)

    assert wav.detected_format == "wav"
    assert mp3.detected_format == "mp3"
    assert wav.duration_ms == mp3.duration_ms == 8_221
    assert wav.frame_count == mp3.frame_count == 131_547
    assert wav.sample_rate_hz == mp3.sample_rate_hz == 16_000
    assert wav.channels == mp3.channels == 1


def test_committed_mp3_normalizes_to_verified_working_wav() -> None:
    from app.services.audio_media_service import normalize_audio, probe_audio

    root = Path(__file__).resolve().parents[3]
    mp3_path = root / "tests/fixtures/audio/v1.7.0/formats/verified_sample.mp3"
    source_bytes = mp3_path.read_bytes()
    decoded = probe_audio(BytesIO(source_bytes))
    destination = BytesIO()

    normalized = normalize_audio(
        BytesIO(source_bytes),
        destination,
        decoded=decoded,
        target_sample_rate_hz=16_000,
    )

    info = sf.info(BytesIO(destination.getvalue()))
    assert decoded.detected_format == "mp3"
    assert normalized.boundary_frames_verified is True
    assert normalized.frame_count == decoded.frame_count
    assert normalized.duration_ms == decoded.duration_ms
    assert info.format == "WAV"
    assert info.subtype == "PCM_16"
    assert info.channels == 1
    assert info.samplerate == 16_000


def test_probe_rejects_renamed_flac_by_decoded_format_not_filename() -> None:
    from app.services.audio_media_service import AudioIntakeError, probe_audio

    source = BytesIO()
    source.name = "renamed.wav"
    sf.write(
        source,
        np.zeros(800, dtype=np.float64),
        8_000,
        format="FLAC",
    )
    source.seek(0)

    with pytest.raises(AudioIntakeError) as captured:
        probe_audio(source)

    assert captured.value.code == "audio_format_unavailable"
    assert captured.value.details["actual_value"] == "flac"
    assert captured.value.details["supported_formats"] == ["wav", "mp3"]
    assert "WAV or MP3" in captured.value.details["remediation"]


def test_normalization_is_repeatable_mono_16khz_pcm16_and_preserves_boundaries() -> None:
    from app.services.audio_media_service import normalize_audio, probe_audio

    frame_count = 8_001
    stereo = np.zeros((frame_count, 2), dtype=np.float64)
    stereo[0] = (0.8, 0.4)
    stereo[-1] = (-0.8, -0.4)
    source_bytes = _wav_bytes(stereo, sample_rate_hz=8_000)
    source_checksum = sha256(source_bytes).hexdigest()
    decoded = probe_audio(BytesIO(source_bytes))

    first_destination = BytesIO()
    first = normalize_audio(
        BytesIO(source_bytes),
        first_destination,
        decoded=decoded,
        target_sample_rate_hz=16_000,
    )
    second_destination = BytesIO()
    second = normalize_audio(
        BytesIO(source_bytes),
        second_destination,
        decoded=decoded,
        target_sample_rate_hz=16_000,
    )

    assert sha256(source_bytes).hexdigest() == source_checksum
    assert first.normalized_checksum_sha256 == second.normalized_checksum_sha256
    assert first_destination.getvalue() == second_destination.getvalue()
    info = sf.info(BytesIO(first_destination.getvalue()))
    normalized, _ = sf.read(BytesIO(first_destination.getvalue()), dtype="float64")
    assert info.format == "WAV"
    assert info.subtype == "PCM_16"
    assert info.channels == 1
    assert info.samplerate == 16_000
    assert info.frames == 16_002
    assert first.boundary_frames_verified is True
    assert normalized[0] != 0
    assert normalized[-1] != 0
    assert first.mixer_version == np.__version__
    assert first.resampler_version == "1.17.1"
    assert first.writer_version == "0.14.0"


def test_resampling_reads_only_bounded_source_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.audio_media_service import normalize_audio, probe_audio

    source_bytes = _wav_bytes(
        np.zeros((180_000, 2), dtype=np.float32),
        sample_rate_hz=48_000,
    )
    decoded = probe_audio(BytesIO(source_bytes))
    original_read = sf.SoundFile.read
    largest_requested_read = 0

    def reject_unbounded_read(self, frames=-1, *args, **kwargs):
        nonlocal largest_requested_read
        if frames < 0:
            raise AssertionError("normalization attempted an unbounded decoded read")
        largest_requested_read = max(largest_requested_read, frames)
        return original_read(self, frames, *args, **kwargs)

    monkeypatch.setattr(sf.SoundFile, "read", reject_unbounded_read)
    destination = BytesIO()

    normalized = normalize_audio(
        BytesIO(source_bytes),
        destination,
        decoded=decoded,
        target_sample_rate_hz=16_000,
    )

    assert largest_requested_read <= 80_000
    assert normalized.frame_count == 60_000
    assert "streaming_block_frames=" in normalized.conversion_profile
    assert "overlap_frames=" in normalized.conversion_profile
    assert "processing_dtype=float32" in normalized.conversion_profile
    assert "filter_profile=firwin-20x-max-rate-plus-1" in (
        normalized.conversion_profile
    )


def _decoded_profile(
    *,
    sample_rate_hz: int,
    channels: int,
    frame_count: int = 48_000,
):
    from app.services.audio_media_service import DecodedAudioMetadata

    return DecodedAudioMetadata(
        detected_format="wav",
        duration_ms=frame_count * 1000 // sample_rate_hz,
        frame_count=frame_count,
        sample_rate_hz=sample_rate_hz,
        channels=channels,
        decoder_name="soundfile",
        decoder_version="0.14.0",
        decoder_library_name="libsndfile",
        decoder_library_version="1.2.2",
    )


@pytest.mark.parametrize("sample_rate_hz", [8_000, 16_000, 44_100, 48_000])
@pytest.mark.parametrize("channels", [1, 2])
def test_verified_v170_source_media_profile_matrix_passes(
    sample_rate_hz: int,
    channels: int,
) -> None:
    from app.core.config import Settings
    from app.services.audio_media_service import validate_source_media_profile

    evidence = validate_source_media_profile(
        _decoded_profile(
            sample_rate_hz=sample_rate_hz,
            channels=channels,
        ),
        target_sample_rate_hz=16_000,
        settings=Settings(),
    )

    assert evidence.rational_factor <= 441
    assert evidence.filter_tap_count <= 8_821
    assert evidence.estimated_working_bytes <= 8 * 1024 * 1024


@pytest.mark.parametrize(
    ("decoded", "settings_updates", "expected_unit"),
    [
        (
            _decoded_profile(sample_rate_hz=7_999, channels=1),
            {},
            "sample_rate_hz",
        ),
        (
            _decoded_profile(sample_rate_hz=48_000, channels=3),
            {},
            "channels",
        ),
        (
            _decoded_profile(sample_rate_hz=44_100, channels=2),
            {"audio_normalization_max_rational_factor": 100},
            "rational_factor",
        ),
        (
            _decoded_profile(sample_rate_hz=44_100, channels=2),
            {"audio_normalization_max_filter_taps": 1_001},
            "filter_taps",
        ),
        (
            _decoded_profile(sample_rate_hz=48_000, channels=2),
            {"audio_normalization_max_working_bytes": 1_024},
            "bytes",
        ),
    ],
)
def test_unsupported_source_media_profiles_fail_before_allocation(
    decoded,
    settings_updates: dict[str, int],
    expected_unit: str,
) -> None:
    from app.core.config import Settings
    from app.services.audio_media_service import (
        AudioIntakeError,
        validate_source_media_profile,
    )

    with pytest.raises(AudioIntakeError) as captured:
        validate_source_media_profile(
            decoded,
            target_sample_rate_hz=16_000,
            settings=Settings(**settings_updates),
        )

    assert captured.value.code == "unsupported_audio_profile"
    assert captured.value.details["unit"] == expected_unit
    assert captured.value.details["remediation"]


def test_malicious_extreme_sample_rate_wav_is_rejected_as_media_profile() -> None:
    from app.core.config import Settings
    from app.services.audio_media_service import (
        AudioIntakeError,
        probe_audio,
        validate_source_media_profile,
    )

    sample_rate_hz = 2_000_000_001
    payload = (
        b"RIFF"
        + struct.pack("<I", 38)
        + b"WAVEfmt "
        + struct.pack(
            "<IHHIIHH",
            16,
            1,
            1,
            sample_rate_hz,
            sample_rate_hz * 2,
            2,
            16,
        )
        + b"data"
        + struct.pack("<Ih", 2, 0)
    )
    decoded = probe_audio(BytesIO(payload))

    with pytest.raises(AudioIntakeError) as captured:
        validate_source_media_profile(
            decoded,
            target_sample_rate_hz=16_000,
            settings=Settings(),
        )

    assert captured.value.code == "unsupported_audio_profile"
    assert captured.value.details["unit"] == "sample_rate_hz"
    assert captured.value.details["actual_value"] == sample_rate_hz


def test_probe_rejects_truncated_or_empty_media_explicitly() -> None:
    from app.services.audio_media_service import AudioIntakeError, probe_audio

    for payload in (b"", b"RIFF\x00\x00\x00\x00WAVE"):
        with pytest.raises(AudioIntakeError) as captured:
            probe_audio(BytesIO(payload))
        assert captured.value.code in {"audio_decode_failed", "audio_content_incomplete"}
        assert captured.value.details["remediation"]


def test_probe_rejects_wav_with_declared_frames_missing_from_object() -> None:
    from app.services.audio_media_service import AudioIntakeError, probe_audio

    complete = _wav_bytes(
        np.zeros(1_600, dtype=np.float64),
        sample_rate_hz=16_000,
    )
    truncated = complete[:-1_000]

    with pytest.raises(AudioIntakeError) as captured:
        probe_audio(BytesIO(truncated))

    assert captured.value.code == "audio_content_incomplete"
    assert captured.value.details["unit"] == "decoded_frames"
