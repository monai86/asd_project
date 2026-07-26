"""Server-authoritative audio probing and normalization for v1.7.0.

The decoder registry is deliberately narrower than libsndfile's general
capabilities. A format is available only when the pinned runtime and its
committed synthetic fixture both verify.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json
import math
from pathlib import Path
import struct
import tempfile
from typing import BinaryIO

import numpy as np
from scipy import __version__ as scipy_version
from scipy.signal import firwin, resample_poly
import soundfile as sf

from app.core.config import Settings, get_settings
from app.services.storage_service import StorageProcessingError


PINNED_SOUNDFILE_VERSION = "0.14.0"
PINNED_LIBSNDFILE_VERSION = "1.2.2"
PINNED_NUMPY_VERSION = "2.4.4"
PINNED_SCIPY_VERSION = "1.17.1"
V170_FORMATS = ("wav", "mp3")
NORMALIZATION_STREAM_BLOCK_BASE_FRAMES = 65_536
NORMALIZATION_RESAMPLE_OVERLAP_BASE_FRAMES = 4_096
NORMALIZATION_PROCESSING_DTYPE = "float32"
NORMALIZATION_RESAMPLE_WINDOW = "kaiser-beta-5.0"
NORMALIZATION_FILTER_PROFILE = (
    "firwin-20x-max-rate-plus-1-cutoff-1-over-max-rate-"
    "kaiser-beta-5.0-float32"
)
NORMALIZATION_PADDING_POLICY = "constant-zero"


class AudioIntakeError(RuntimeError):
    """Actionable, non-clinical error returned by the audio intake boundary."""

    def __init__(
        self,
        code: str,
        *,
        actual_value: object | None = None,
        configured_limit: object | None = None,
        unit: str | None = None,
        supported_formats: tuple[str, ...] = V170_FORMATS,
        remediation: str,
        message: str | None = None,
    ) -> None:
        self.code = code
        self.details = {
            "error_code": code,
            "actual_value": actual_value,
            "configured_limit": configured_limit,
            "unit": unit,
            "supported_formats": list(supported_formats),
            "remediation": remediation,
        }
        super().__init__(message or code)

    def as_detail(self) -> dict[str, object | None]:
        return dict(self.details)


def audio_intake_error_from_storage(
    error: StorageProcessingError,
) -> AudioIntakeError:
    return AudioIntakeError(
        error.code,
        actual_value=error.actual_value,
        configured_limit=error.configured_limit,
        unit=error.unit,
        remediation=error.remediation,
    )


@dataclass(frozen=True)
class DecoderRuntime:
    decoder_name: str
    soundfile_version: str
    library_name: str
    libsndfile_version: str


@dataclass(frozen=True)
class DecoderCapability:
    format_id: str
    available: bool
    fixture_verified: bool
    reason_code: str | None = None


@dataclass(frozen=True)
class DecoderCapabilityRegistry:
    runtime: DecoderRuntime
    capabilities: dict[str, DecoderCapability]

    @property
    def verified_formats(self) -> tuple[str, ...]:
        return tuple(
            format_id
            for format_id in V170_FORMATS
            if self.capabilities[format_id].available
            and self.capabilities[format_id].fixture_verified
        )

    def capability(self, format_id: str) -> DecoderCapability:
        normalized = format_id.lower()
        return self.capabilities.get(
            normalized,
            DecoderCapability(
                format_id=normalized,
                available=False,
                fixture_verified=False,
                reason_code="decoder_fixture_not_verified",
            ),
        )


@dataclass(frozen=True)
class SourceMediaProfileEvidence:
    """Bounded normalization geometry derived without allocating media buffers."""

    up_factor: int
    down_factor: int
    rational_factor: int
    filter_tap_count: int
    streaming_block_frames: int
    overlap_frames: int
    estimated_working_bytes: int


@dataclass(frozen=True)
class DecodedAudioMetadata:
    detected_format: str
    duration_ms: int
    frame_count: int
    sample_rate_hz: int
    channels: int
    decoder_name: str
    decoder_version: str
    decoder_library_name: str
    decoder_library_version: str


@dataclass(frozen=True)
class NormalizationResult:
    normalized_size_bytes: int
    normalized_checksum_sha256: str
    duration_ms: int
    frame_count: int
    sample_rate_hz: int
    channels: int
    format: str
    boundary_frames_verified: bool
    mixer_name: str
    mixer_version: str
    resampler_name: str
    resampler_version: str
    writer_name: str
    writer_version: str
    writer_library_name: str
    writer_library_version: str
    processing_dtype: str
    streaming_block_frames: int
    overlap_frames: int
    resample_window: str
    filter_profile: str
    padding_policy: str
    conversion_profile: str


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _sha256_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fixture_matches(
    path: Path,
    *,
    expected_checksum: str,
    expected_frames: int,
    expected_sample_rate: int,
    expected_channels: int,
    expected_format: str,
) -> bool:
    if not path.is_file() or _sha256_path(path) != expected_checksum:
        return False
    try:
        info = sf.info(path)
    except (RuntimeError, TypeError):
        return False
    return (
        info.format.upper() == expected_format
        and info.frames == expected_frames
        and info.samplerate == expected_sample_rate
        and info.channels == expected_channels
    )


def _build_decoder_capability_registry() -> DecoderCapabilityRegistry:
    runtime = DecoderRuntime(
        decoder_name="soundfile",
        soundfile_version=sf.__version__,
        library_name="libsndfile",
        libsndfile_version=sf.__libsndfile_version__,
    )
    runtime_verified = (
        runtime.soundfile_version == PINNED_SOUNDFILE_VERSION
        and runtime.libsndfile_version == PINNED_LIBSNDFILE_VERSION
        and np.__version__ == PINNED_NUMPY_VERSION
        and scipy_version == PINNED_SCIPY_VERSION
    )
    manifest_path = (
        _repository_root() / "tests/fixtures/audio/v1.7.0/manifest.json"
    )
    manifest: dict[str, object] = {}
    if runtime_verified and manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}

    seeds = manifest.get("seeds", {}) if isinstance(manifest, dict) else {}
    formats = (
        manifest.get("format_fixtures", {}) if isinstance(manifest, dict) else {}
    )
    wav = seeds.get("thai_only", {}) if isinstance(seeds, dict) else {}
    mp3 = formats.get("mp3", {}) if isinstance(formats, dict) else {}
    mp3_decoded = mp3.get("decoded", {}) if isinstance(mp3, dict) else {}
    fixture_root = manifest_path.parent

    wav_verified = runtime_verified and isinstance(wav, dict) and _fixture_matches(
        fixture_root / str(wav.get("path", "")),
        expected_checksum=str(wav.get("sha256", "")),
        expected_frames=int(wav.get("frame_count", -1)),
        expected_sample_rate=int(wav.get("pcm", {}).get("sample_rate_hz", -1)),
        expected_channels=int(wav.get("pcm", {}).get("channels", -1)),
        expected_format="WAV",
    )
    mp3_verified = (
        runtime_verified
        and isinstance(mp3, dict)
        and isinstance(mp3_decoded, dict)
        and _fixture_matches(
            fixture_root / str(mp3.get("path", "")),
            expected_checksum=str(mp3.get("sha256", "")),
            expected_frames=int(mp3_decoded.get("frame_count", -1)),
            expected_sample_rate=int(mp3_decoded.get("sample_rate_hz", -1)),
            expected_channels=int(mp3_decoded.get("channels", -1)),
            expected_format="MP3",
        )
    )
    capabilities = {
        "wav": DecoderCapability(
            "wav",
            available=wav_verified,
            fixture_verified=wav_verified,
            reason_code=None if wav_verified else "decoder_fixture_not_verified",
        ),
        "mp3": DecoderCapability(
            "mp3",
            available=mp3_verified,
            fixture_verified=mp3_verified,
            reason_code=None if mp3_verified else "decoder_fixture_not_verified",
        ),
        "m4a": DecoderCapability(
            "m4a",
            available=False,
            fixture_verified=False,
            reason_code="decoder_fixture_not_verified",
        ),
        "webm": DecoderCapability(
            "webm",
            available=False,
            fixture_verified=False,
            reason_code="decoder_fixture_not_verified",
        ),
    }
    return DecoderCapabilityRegistry(runtime=runtime, capabilities=capabilities)


@lru_cache(maxsize=1)
def get_decoder_capability_registry() -> DecoderCapabilityRegistry:
    try:
        return _build_decoder_capability_registry()
    except Exception:  # noqa: BLE001
        runtime = DecoderRuntime(
            decoder_name="soundfile",
            soundfile_version=sf.__version__,
            library_name="libsndfile",
            libsndfile_version=sf.__libsndfile_version__,
        )
        return DecoderCapabilityRegistry(
            runtime=runtime,
            capabilities={
                format_id: DecoderCapability(
                    format_id=format_id,
                    available=False,
                    fixture_verified=False,
                    reason_code="decoder_registry_initialization_failed",
                )
                for format_id in V170_FORMATS
            },
        )


def verified_configured_audio_formats(
    settings,
    *,
    registry: DecoderCapabilityRegistry | None = None,
) -> tuple[str, ...]:
    decoder_registry = registry or get_decoder_capability_registry()
    verified = set(decoder_registry.verified_formats)
    return tuple(
        format_id
        for format_id in settings.parsed_supported_audio_formats
        if format_id in verified
    )


def _detected_format(soundfile_format: str) -> str:
    normalized = soundfile_format.upper()
    return {
        "WAV": "wav",
        "WAVEX": "wav",
        "MP3": "mp3",
        "MPEG": "mp3",
    }.get(normalized, normalized.lower())


def _rewind(source: BinaryIO) -> None:
    try:
        source.seek(0)
    except (AttributeError, OSError) as exc:
        raise AudioIntakeError(
            "audio_source_not_seekable",
            remediation="Upload the file again so the server can verify the complete asset.",
        ) from exc


def _verify_wav_container_length(
    source: BinaryIO,
    *,
    decoded_frame_count: int,
) -> None:
    """Reject a RIFF/WAVE object whose declared data extends beyond EOF."""

    _rewind(source)
    header = source.read(12)
    if len(header) != 12 or header[:4] != b"RIFF" or header[8:] != b"WAVE":
        raise AudioIntakeError(
            "audio_content_incomplete",
            actual_value=0,
            configured_limit=decoded_frame_count,
            unit="decoded_frames",
            remediation="Upload a complete WAV file whose container and audio frames agree.",
        )
    riff_size = struct.unpack("<I", header[4:8])[0]
    source.seek(0, 2)
    physical_size = source.tell()
    riff_extends_beyond_eof = riff_size + 8 > physical_size

    source.seek(12)
    block_align: int | None = None
    declared_data_size: int | None = None
    data_offset: int | None = None
    while source.tell() + 8 <= physical_size:
        chunk_header = source.read(8)
        if len(chunk_header) != 8:
            break
        chunk_id = chunk_header[:4]
        chunk_size = struct.unpack("<I", chunk_header[4:])[0]
        chunk_start = source.tell()
        if chunk_id == b"fmt ":
            fmt = source.read(min(chunk_size, 16))
            if len(fmt) >= 14:
                block_align = struct.unpack("<H", fmt[12:14])[0]
        elif chunk_id == b"data":
            declared_data_size = chunk_size
            data_offset = chunk_start
            break
        source.seek(chunk_start + chunk_size + (chunk_size % 2))

    if not block_align or declared_data_size is None or data_offset is None:
        raise AudioIntakeError(
            "audio_content_incomplete",
            actual_value=decoded_frame_count,
            unit="decoded_frames",
            remediation="Upload a complete WAV file with valid format and data chunks.",
        )
    available_data_size = max(physical_size - data_offset, 0)
    declared_frames = declared_data_size // block_align
    available_frames = min(declared_data_size, available_data_size) // block_align
    if (
        declared_data_size > available_data_size
        or declared_frames != decoded_frame_count
    ):
        raise AudioIntakeError(
            "audio_content_incomplete",
            actual_value=available_frames,
            configured_limit=declared_frames,
            unit="decoded_frames",
            remediation="Upload the complete WAV file again; decoded frames are missing.",
        )
    if riff_extends_beyond_eof:
        raise AudioIntakeError(
            "audio_content_incomplete",
            actual_value=physical_size,
            configured_limit=riff_size + 8,
            unit="bytes",
            remediation="Upload the complete WAV file again; its container is truncated.",
        )
    _rewind(source)


def probe_audio(
    source: BinaryIO,
    *,
    registry: DecoderCapabilityRegistry | None = None,
) -> DecodedAudioMetadata:
    """Decode authoritative media metadata from stored bytes."""

    decoder_registry = registry or get_decoder_capability_registry()
    _rewind(source)
    try:
        info = sf.info(source)
    except (RuntimeError, TypeError, ValueError) as exc:
        raise AudioIntakeError(
            "audio_decode_failed",
            remediation="Upload a complete WAV or MP3 file encoded by a supported tool.",
        ) from exc
    finally:
        _rewind(source)

    detected_format = _detected_format(info.format)
    capability = decoder_registry.capability(detected_format)
    if not capability.available or not capability.fixture_verified:
        raise AudioIntakeError(
            "audio_format_unavailable",
            actual_value=detected_format,
            unit="format",
            supported_formats=decoder_registry.verified_formats,
            remediation="Convert the source to a verified WAV or MP3 file and upload it again.",
        )
    if info.frames <= 0 or info.samplerate <= 0 or info.channels <= 0:
        raise AudioIntakeError(
            "audio_content_incomplete",
            actual_value=info.frames,
            unit="decoded_frames",
            supported_formats=decoder_registry.verified_formats,
            remediation="Upload a complete file containing at least one decodable audio frame.",
        )
    if detected_format == "wav":
        _verify_wav_container_length(
            source,
            decoded_frame_count=info.frames,
        )
    try:
        with sf.SoundFile(source, mode="r", closefd=False) as decoded:
            first_frame = decoded.read(1, dtype="float64", always_2d=True)
            decoded.seek(info.frames - 1)
            final_frame = decoded.read(1, dtype="float64", always_2d=True)
    except (RuntimeError, TypeError, ValueError, OSError) as exc:
        raise AudioIntakeError(
            "audio_content_incomplete",
            actual_value=0,
            configured_limit=info.frames,
            unit="decoded_frames",
            supported_formats=decoder_registry.verified_formats,
            remediation="Upload the complete audio file again; boundary frames are unreadable.",
        ) from exc
    finally:
        _rewind(source)
    if first_frame.shape != (1, info.channels) or final_frame.shape != (
        1,
        info.channels,
    ):
        raise AudioIntakeError(
            "audio_content_incomplete",
            actual_value=0,
            configured_limit=info.frames,
            unit="decoded_frames",
            supported_formats=decoder_registry.verified_formats,
            remediation="Upload the complete audio file again; boundary frames are missing.",
        )
    duration_ms = info.frames * 1000 // info.samplerate
    return DecodedAudioMetadata(
        detected_format=detected_format,
        duration_ms=duration_ms,
        frame_count=info.frames,
        sample_rate_hz=info.samplerate,
        channels=info.channels,
        decoder_name=decoder_registry.runtime.decoder_name,
        decoder_version=decoder_registry.runtime.soundfile_version,
        decoder_library_name=decoder_registry.runtime.library_name,
        decoder_library_version=decoder_registry.runtime.libsndfile_version,
    )


def _destination_size(destination: BinaryIO) -> int:
    current = destination.tell()
    destination.seek(0, 2)
    size = destination.tell()
    destination.seek(current)
    return size


def _checksum_stream(source: BinaryIO) -> str:
    digest = sha256()
    _rewind(source)
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(chunk)
    _rewind(source)
    return digest.hexdigest()


def _aligned_frame_count(base_frames: int, alignment: int) -> int:
    return ((base_frames + alignment - 1) // alignment) * alignment


def validate_source_media_profile(
    decoded: DecodedAudioMetadata,
    *,
    target_sample_rate_hz: int,
    settings: Settings,
) -> SourceMediaProfileEvidence:
    """Reject unsupported normalization geometry before allocating arrays/FIR."""

    if not (
        settings.audio_source_min_sample_rate_hz
        <= decoded.sample_rate_hz
        <= settings.audio_source_max_sample_rate_hz
    ):
        raise AudioIntakeError(
            "unsupported_audio_profile",
            actual_value=decoded.sample_rate_hz,
            configured_limit={
                "minimum": settings.audio_source_min_sample_rate_hz,
                "maximum": settings.audio_source_max_sample_rate_hz,
            },
            unit="sample_rate_hz",
            remediation=(
                "Re-encode the complete source at a verified sample rate between "
                f"{settings.audio_source_min_sample_rate_hz} and "
                f"{settings.audio_source_max_sample_rate_hz} Hz."
            ),
        )
    if not 1 <= decoded.channels <= settings.audio_source_max_channels:
        raise AudioIntakeError(
            "unsupported_audio_profile",
            actual_value=decoded.channels,
            configured_limit=settings.audio_source_max_channels,
            unit="channels",
            remediation=(
                "Re-encode the complete source as mono or stereo without "
                "changing its language-sample content."
            ),
        )
    if target_sample_rate_hz <= 0:
        raise ValueError("target sample rate must be positive")

    divisor = math.gcd(decoded.sample_rate_hz, target_sample_rate_hz)
    up = target_sample_rate_hz // divisor
    down = decoded.sample_rate_hz // divisor
    rational_factor = max(up, down)
    if rational_factor > settings.audio_normalization_max_rational_factor:
        raise AudioIntakeError(
            "unsupported_audio_profile",
            actual_value=rational_factor,
            configured_limit=settings.audio_normalization_max_rational_factor,
            unit="rational_factor",
            remediation=(
                "Re-encode the complete source using a verified sample rate "
                "whose normalization ratio is supported by this milestone."
            ),
        )

    filter_tap_count = 1 if up == down else 20 * rational_factor + 1
    if filter_tap_count > settings.audio_normalization_max_filter_taps:
        raise AudioIntakeError(
            "unsupported_audio_profile",
            actual_value=filter_tap_count,
            configured_limit=settings.audio_normalization_max_filter_taps,
            unit="filter_taps",
            remediation=(
                "Re-encode the complete source using a verified sample rate "
                "that fits the deterministic normalization filter profile."
            ),
        )

    block_frames = _aligned_frame_count(
        NORMALIZATION_STREAM_BLOCK_BASE_FRAMES,
        down,
    )
    overlap_frames = (
        0
        if up == down
        else _aligned_frame_count(
            NORMALIZATION_RESAMPLE_OVERLAP_BASE_FRAMES,
            down,
        )
    )
    context_frames = min(
        decoded.frame_count,
        block_frames + 2 * overlap_frames,
    )
    resampled_context_frames = (
        context_frames * up + down - 1
    ) // down
    estimated_working_bytes = (
        context_frames * decoded.channels * np.dtype(np.float32).itemsize
        + context_frames * np.dtype(np.float32).itemsize
        + resampled_context_frames * np.dtype(np.float32).itemsize
        + filter_tap_count * np.dtype(np.float32).itemsize
    )
    if estimated_working_bytes > settings.audio_normalization_max_working_bytes:
        raise AudioIntakeError(
            "unsupported_audio_profile",
            actual_value=estimated_working_bytes,
            configured_limit=settings.audio_normalization_max_working_bytes,
            unit="bytes",
            remediation=(
                "Re-encode the complete source using a supported mono/stereo "
                "profile within the configured normalization memory bound."
            ),
        )
    return SourceMediaProfileEvidence(
        up_factor=up,
        down_factor=down,
        rational_factor=rational_factor,
        filter_tap_count=filter_tap_count,
        streaming_block_frames=block_frames,
        overlap_frames=overlap_frames,
        estimated_working_bytes=estimated_working_bytes,
    )


def _resampling_contract(
    source_sample_rate_hz: int,
    target_sample_rate_hz: int,
) -> tuple[int, int, int, int]:
    divisor = math.gcd(source_sample_rate_hz, target_sample_rate_hz)
    up = target_sample_rate_hz // divisor
    down = source_sample_rate_hz // divisor
    block_frames = _aligned_frame_count(
        NORMALIZATION_STREAM_BLOCK_BASE_FRAMES,
        down,
    )
    overlap_frames = (
        0
        if up == down
        else _aligned_frame_count(
            NORMALIZATION_RESAMPLE_OVERLAP_BASE_FRAMES,
            down,
        )
    )
    return up, down, block_frames, overlap_frames


def _normalization_profile(
    source_sample_rate_hz: int,
    target_sample_rate_hz: int,
) -> str:
    up, down, block_frames, overlap_frames = _resampling_contract(
        source_sample_rate_hz,
        target_sample_rate_hz,
    )
    return (
        "lingualens-audio-normalization-v1.7.0;"
        f"decode=soundfile-{sf.__version__}/libsndfile-{sf.__libsndfile_version__};"
        f"mix=numpy-mean-{np.__version__};processing_dtype="
        f"{NORMALIZATION_PROCESSING_DTYPE};"
        f"resample=scipy-resample_poly-{scipy_version};"
        f"resample_ratio={up}/{down};"
        f"streaming_block_frames={block_frames};"
        f"overlap_frames={overlap_frames};"
        f"resample_window={NORMALIZATION_RESAMPLE_WINDOW};"
        f"filter_profile={NORMALIZATION_FILTER_PROFILE};"
        f"padding_policy={NORMALIZATION_PADDING_POLICY};"
        f"write=soundfile-pcm16le-wav-{sf.__version__};"
        f"source_sample_rate_hz={source_sample_rate_hz};"
        f"sample_rate_hz={target_sample_rate_hz};channels=1;"
        "boundary_policy=complete_first_through_final_source_frame"
    )


def normalize_audio(
    source: BinaryIO,
    destination: BinaryIO,
    *,
    decoded: DecodedAudioMetadata,
    target_sample_rate_hz: int,
    settings: Settings | None = None,
) -> NormalizationResult:
    """Write deterministic mono PCM-S16LE WAV without modifying ``source``."""

    if target_sample_rate_hz <= 0:
        raise ValueError("target sample rate must be positive")
    runtime_settings = settings or get_settings()
    validate_source_media_profile(
        decoded,
        target_sample_rate_hz=target_sample_rate_hz,
        settings=runtime_settings,
    )
    _rewind(source)
    destination.seek(0)
    destination.truncate(0)
    expected_frames = (
        decoded.frame_count * target_sample_rate_hz
        + decoded.sample_rate_hz
        - 1
    ) // decoded.sample_rate_hz
    up, down, block_frames, overlap_frames = _resampling_contract(
        decoded.sample_rate_hz,
        target_sample_rate_hz,
    )
    resample_filter = None
    if up != down:
        max_rate = max(up, down)
        resample_filter = firwin(
            20 * max_rate + 1,
            1 / max_rate,
            window=("kaiser", 5.0),
        ).astype(np.float32)
    written_frames = 0
    try:
        with sf.SoundFile(source, mode="r", closefd=False) as reader:
            with sf.SoundFile(
                destination,
                mode="w",
                samplerate=target_sample_rate_hz,
                channels=1,
                format="WAV",
                subtype="PCM_16",
                closefd=False,
            ) as writer:
                for core_start in range(
                    0,
                    decoded.frame_count,
                    block_frames,
                ):
                    core_end = min(
                        core_start + block_frames,
                        decoded.frame_count,
                    )
                    context_start = max(0, core_start - overlap_frames)
                    context_end = min(
                        decoded.frame_count,
                        core_end + overlap_frames,
                    )
                    reader.seek(context_start)
                    samples = reader.read(
                        context_end - context_start,
                        dtype=NORMALIZATION_PROCESSING_DTYPE,
                        always_2d=True,
                    )
                    if samples.shape[0] != context_end - context_start:
                        raise AudioIntakeError(
                            "audio_content_incomplete",
                            actual_value=samples.shape[0],
                            configured_limit=context_end - context_start,
                            unit="decoded_frames",
                            remediation=(
                                "Upload the complete audio file again; "
                                "a normalization block was incomplete."
                            ),
                        )
                    mono = np.mean(
                        samples,
                        axis=1,
                        dtype=np.float32,
                    )
                    if not np.isfinite(mono).all():
                        raise AudioIntakeError(
                            "audio_content_corrupted",
                            remediation="Re-encode the source as WAV or MP3 and upload it again.",
                        )
                    if up == down:
                        output = mono
                    else:
                        context_output = resample_poly(
                            mono,
                            up,
                            down,
                            window=resample_filter,
                            padtype="constant",
                            cval=0.0,
                        )
                        left_context_frames = core_start - context_start
                        left_output_frames = left_context_frames * up // down
                        global_output_start = core_start * up // down
                        global_output_end = (
                            core_end * up + down - 1
                        ) // down
                        core_output_frames = (
                            global_output_end - global_output_start
                        )
                        output = context_output[
                            left_output_frames:
                            left_output_frames + core_output_frames
                        ]
                    writer.write(output)
                    written_frames += len(output)
                if written_frames != expected_frames:
                    raise AudioIntakeError(
                        "normalized_audio_boundary_verification_failed",
                        actual_value=written_frames,
                        configured_limit=expected_frames,
                        unit="frames",
                        remediation=(
                            "Retry normalization from the unchanged source asset."
                        ),
                    )
    except AudioIntakeError:
        raise
    except (RuntimeError, TypeError, ValueError, OSError) as exc:
        raise AudioIntakeError(
            "audio_normalization_failed",
            remediation="Re-encode the source as WAV or MP3 and upload it again.",
        ) from exc
    finally:
        _rewind(source)

    destination.flush()
    _rewind(destination)
    try:
        normalized_info = sf.info(destination)
        _rewind(destination)
        with sf.SoundFile(destination, mode="r", closefd=False) as normalized:
            first_frame = normalized.read(1, dtype="float64", always_2d=True)
            normalized.seek(max(normalized.frames - 1, 0))
            final_frame = normalized.read(1, dtype="float64", always_2d=True)
    except (RuntimeError, TypeError, ValueError, OSError) as exc:
        raise AudioIntakeError(
            "normalized_audio_verification_failed",
            remediation="Retry normalization from the unchanged source asset.",
        ) from exc
    finally:
        _rewind(destination)

    boundary_frames_verified = (
        normalized_info.frames == expected_frames
        and first_frame.size == 1
        and final_frame.size == 1
        and np.isfinite(first_frame).all()
        and np.isfinite(final_frame).all()
    )
    if not boundary_frames_verified:
        raise AudioIntakeError(
            "normalized_audio_boundary_verification_failed",
            actual_value=normalized_info.frames,
            configured_limit=expected_frames,
            unit="frames",
            remediation="Retry normalization from the unchanged source asset.",
        )

    conversion_profile = _normalization_profile(
        decoded.sample_rate_hz,
        target_sample_rate_hz,
    )
    return NormalizationResult(
        normalized_size_bytes=_destination_size(destination),
        normalized_checksum_sha256=_checksum_stream(destination),
        duration_ms=normalized_info.frames * 1000 // normalized_info.samplerate,
        frame_count=normalized_info.frames,
        sample_rate_hz=normalized_info.samplerate,
        channels=normalized_info.channels,
        format="wav_pcm_s16le",
        boundary_frames_verified=True,
        mixer_name="numpy.mean",
        mixer_version=np.__version__,
        resampler_name="scipy.signal.resample_poly",
        resampler_version=scipy_version,
        writer_name="soundfile",
        writer_version=sf.__version__,
        writer_library_name="libsndfile",
        writer_library_version=sf.__libsndfile_version__,
        processing_dtype=NORMALIZATION_PROCESSING_DTYPE,
        streaming_block_frames=block_frames,
        overlap_frames=overlap_frames,
        resample_window=NORMALIZATION_RESAMPLE_WINDOW,
        filter_profile=NORMALIZATION_FILTER_PROFILE,
        padding_policy=NORMALIZATION_PADDING_POLICY,
        conversion_profile=conversion_profile,
    )


def _stream_size(source: BinaryIO) -> int:
    try:
        current = source.tell()
        source.seek(0, 2)
        size = source.tell()
        source.seek(current)
        return size
    except (AttributeError, OSError) as exc:
        raise AudioIntakeError(
            "audio_source_not_seekable",
            remediation="Upload the file again so the server can verify its complete size.",
        ) from exc


def enforce_audio_limits(
    *,
    actual_size_bytes: int,
    decoded: DecodedAudioMetadata | None,
    settings,
) -> None:
    """Enforce the milestone limits using server-observed values."""

    size_limit_bytes = settings.max_audio_file_size_mb * 1024 * 1024
    supported_formats = tuple(settings.parsed_supported_audio_formats)
    if actual_size_bytes > size_limit_bytes:
        raise AudioIntakeError(
            "audio_size_limit_exceeded",
            actual_value=actual_size_bytes,
            configured_limit=size_limit_bytes,
            unit="bytes",
            supported_formats=supported_formats,
            remediation=(
                f"Upload a file no larger than {settings.max_audio_file_size_mb} MiB."
            ),
        )
    if decoded is None:
        return
    if decoded.detected_format not in supported_formats:
        raise AudioIntakeError(
            "audio_format_unavailable",
            actual_value=decoded.detected_format,
            unit="format",
            supported_formats=supported_formats,
            remediation=(
                "Convert the source to one of the currently enabled verified "
                "formats and upload it again."
            ),
        )
    duration_limit_ms = settings.max_audio_duration_seconds * 1000
    if (
        decoded.frame_count
        > settings.max_audio_duration_seconds * decoded.sample_rate_hz
    ):
        actual_duration_ms = (
            decoded.frame_count * 1000 + decoded.sample_rate_hz - 1
        ) // decoded.sample_rate_hz
        raise AudioIntakeError(
            "audio_duration_limit_exceeded",
            actual_value=actual_duration_ms,
            configured_limit=duration_limit_ms,
            unit="milliseconds",
            supported_formats=supported_formats,
            remediation=(
                "Upload one complete language-sample file no longer than "
                f"{settings.max_audio_duration_seconds // 60} minutes; "
                "the server will not truncate or split it."
            ),
        )


def _current_normalized_metadata_matches(
    current,
    *,
    audio_file,
    source_checksum: str,
    actual_size_bytes: int,
    decoded: DecodedAudioMetadata,
    settings,
) -> bool:
    provenance = current.provenance
    expected_profile = _normalization_profile(
        decoded.sample_rate_hz,
        settings.audio_normalization_sample_rate_hz
    )
    expected_profile_checksum = sha256(expected_profile.encode("utf-8")).hexdigest()
    return bool(
        current.source_asset_version == audio_file.source_asset_version
        and current.source_checksum_sha256 == source_checksum
        and current.sample_rate_hz == settings.audio_normalization_sample_rate_hz
        and current.channels == settings.audio_normalization_channels
        and current.format == settings.audio_normalization_format
        and current.verification_status == "verified"
        and provenance is not None
        and provenance.source_size_bytes == actual_size_bytes
        and provenance.source_detected_format == decoded.detected_format
        and provenance.source_duration_ms == decoded.duration_ms
        and provenance.source_frame_count == decoded.frame_count
        and provenance.source_sample_rate_hz == decoded.sample_rate_hz
        and provenance.source_channels == decoded.channels
        and current.decoder_name == decoded.decoder_name
        and current.decoder_version == decoded.decoder_version
        and provenance.decoder_library_name == decoded.decoder_library_name
        and provenance.decoder_library_version == decoded.decoder_library_version
        and provenance.mixer_name == "numpy.mean"
        and provenance.mixer_version == np.__version__
        and provenance.resampler_name == "scipy.signal.resample_poly"
        and provenance.resampler_version == scipy_version
        and provenance.writer_name == "soundfile"
        and provenance.writer_version == sf.__version__
        and provenance.writer_library_name == "libsndfile"
        and provenance.writer_library_version == sf.__libsndfile_version__
        and provenance.processing_dtype == NORMALIZATION_PROCESSING_DTYPE
        and provenance.streaming_block_frames
        == _resampling_contract(
            decoded.sample_rate_hz,
            settings.audio_normalization_sample_rate_hz,
        )[2]
        and provenance.overlap_frames
        == _resampling_contract(
            decoded.sample_rate_hz,
            settings.audio_normalization_sample_rate_hz,
        )[3]
        and provenance.resample_window == NORMALIZATION_RESAMPLE_WINDOW
        and provenance.filter_profile == NORMALIZATION_FILTER_PROFILE
        and provenance.padding_policy == NORMALIZATION_PADDING_POLICY
        and current.conversion_command_profile == expected_profile
        and provenance.normalization_profile == expected_profile
        and provenance.profile_checksum_sha256 == expected_profile_checksum
    )


def _persisted_normalized_bytes_match(
    current,
    *,
    storage_adapter,
    settings,
) -> bool:
    provenance = current.provenance
    if provenance is None:
        return False
    try:
        with storage_adapter.open_normalized_for_processing(
            current.object_key,
            max_size_bytes=settings.max_audio_file_size_mb * 1024 * 1024,
        ) as normalized_source:
            actual_size = _stream_size(normalized_source)
            if actual_size != provenance.normalized_size_bytes:
                return False
            if _checksum_stream(normalized_source) != current.normalized_checksum_sha256:
                return False
            decoded = probe_audio(normalized_source)
    except StorageProcessingError as exc:
        if exc.code == "storage_capability_unavailable":
            raise audio_intake_error_from_storage(exc) from exc
        return False
    except AudioIntakeError:
        return False
    return bool(
        decoded.detected_format == "wav"
        and decoded.duration_ms == current.duration_ms
        and decoded.frame_count == current.frame_count
        and decoded.sample_rate_hz == current.sample_rate_hz
        and decoded.channels == current.channels
    )


def verify_and_normalize_audio(
    repo,
    audio_file_id: str,
    *,
    storage_adapter,
    settings,
):
    """Verify one uploaded source and persist one immutable working asset."""

    from app.schemas.clinical import utc_now
    from app.schemas.speech_pipeline import (
        ArtifactStatus,
        AudioNormalizationProvenance,
        NormalizedAudioAsset,
    )

    if audio_file_id not in repo.audio_files:
        raise AudioIntakeError(
            "source_audio_missing",
            actual_value=audio_file_id,
            unit="audio_file_id",
            remediation="Upload the source audio again before normalization.",
        )
    audio_file = repo.audio_files[audio_file_id]
    if not audio_file.retained or audio_file.upload_status != "uploaded":
        raise AudioIntakeError(
            "source_audio_unverified",
            actual_value=audio_file.upload_status,
            unit="upload_status",
            remediation="Complete source upload verification before normalization.",
        )
    if audio_file.storage_mode != storage_adapter.storage_mode:
        raise AudioIntakeError(
            "source_storage_mismatch",
            actual_value=audio_file.storage_mode,
            unit="storage_mode",
            remediation="Retry with the private storage adapter linked to this source asset.",
        )

    normalized_object_key: str | None = None
    record = None
    original_audio_fields = {
        "size_bytes": audio_file.size_bytes,
        "duration_seconds": audio_file.duration_seconds,
        "sample_rate_hz": audio_file.sample_rate_hz,
        "channels": audio_file.channels,
        "checksum_sha256": audio_file.checksum_sha256,
    }
    try:
        try:
            source_handle = storage_adapter.open_source_for_processing(audio_file)
        except StorageProcessingError as exc:
            raise audio_intake_error_from_storage(exc) from exc
        with source_handle as source:
            actual_size_bytes = _stream_size(source)
            enforce_audio_limits(
                actual_size_bytes=actual_size_bytes,
                decoded=None,
                settings=settings,
            )
            decoded = probe_audio(source)
            enforce_audio_limits(
                actual_size_bytes=actual_size_bytes,
                decoded=decoded,
                settings=settings,
            )
            validate_source_media_profile(
                decoded,
                target_sample_rate_hz=(
                    settings.audio_normalization_sample_rate_hz
                ),
                settings=settings,
            )
            if audio_file.size_bytes != actual_size_bytes:
                raise AudioIntakeError(
                    "audio_size_mismatch",
                    actual_value=actual_size_bytes,
                    configured_limit=audio_file.size_bytes,
                    unit="bytes",
                    supported_formats=tuple(settings.parsed_supported_audio_formats),
                    remediation="Upload the complete file again using a new upload intent.",
                )
            source_checksum = _checksum_stream(source)
            if (
                audio_file.checksum_sha256 is not None
                and audio_file.checksum_sha256 != source_checksum
            ):
                raise AudioIntakeError(
                    "source_checksum_mismatch",
                    actual_value=source_checksum,
                    configured_limit=audio_file.checksum_sha256,
                    unit="sha256",
                    supported_formats=tuple(settings.parsed_supported_audio_formats),
                    remediation="Upload the unchanged source again using a new upload intent.",
                )

            current = repo.get_current_normalized_audio_asset(audio_file_id)
            if (
                current is not None
                and _current_normalized_metadata_matches(
                    current,
                    audio_file=audio_file,
                    source_checksum=source_checksum,
                    actual_size_bytes=actual_size_bytes,
                    decoded=decoded,
                    settings=settings,
                )
                and _persisted_normalized_bytes_match(
                    current,
                    storage_adapter=storage_adapter,
                    settings=settings,
                )
            ):
                return current

            with tempfile.SpooledTemporaryFile(
                mode="w+b",
                max_size=16 * 1024 * 1024,
            ) as normalized_stream:
                normalized = normalize_audio(
                    source,
                    normalized_stream,
                    decoded=decoded,
                    target_sample_rate_hz=settings.audio_normalization_sample_rate_hz,
                    settings=settings,
                )
                if abs(normalized.duration_ms - decoded.duration_ms) > 1:
                    raise AudioIntakeError(
                        "normalized_audio_duration_mismatch",
                        actual_value=normalized.duration_ms,
                        configured_limit=decoded.duration_ms,
                        unit="milliseconds",
                        supported_formats=tuple(
                            settings.parsed_supported_audio_formats
                        ),
                        remediation="Retry normalization from the unchanged source asset.",
                    )
                try:
                    normalized_object_key = storage_adapter.persist_normalized_asset(
                        audio_file,
                        normalized_stream,
                        content_type="audio/wav",
                    )
                except StorageProcessingError as exc:
                    raise audio_intake_error_from_storage(exc) from exc

        profile_checksum = sha256(
            normalized.conversion_profile.encode("utf-8")
        ).hexdigest()
        provenance = AudioNormalizationProvenance(
            source_size_bytes=actual_size_bytes,
            source_detected_format=decoded.detected_format,
            source_duration_ms=decoded.duration_ms,
            source_frame_count=decoded.frame_count,
            source_sample_rate_hz=decoded.sample_rate_hz,
            source_channels=decoded.channels,
            normalized_size_bytes=normalized.normalized_size_bytes,
            boundary_frames_verified=True,
            decoder_library_name=decoded.decoder_library_name,
            decoder_library_version=decoded.decoder_library_version,
            mixer_name=normalized.mixer_name,
            mixer_version=normalized.mixer_version,
            resampler_name=normalized.resampler_name,
            resampler_version=normalized.resampler_version,
            writer_name=normalized.writer_name,
            writer_version=normalized.writer_version,
            writer_library_name=normalized.writer_library_name,
            writer_library_version=normalized.writer_library_version,
            processing_dtype=normalized.processing_dtype,
            streaming_block_frames=normalized.streaming_block_frames,
            overlap_frames=normalized.overlap_frames,
            resample_window=normalized.resample_window,
            filter_profile=normalized.filter_profile,
            padding_policy=normalized.padding_policy,
            normalization_profile=normalized.conversion_profile,
            profile_checksum_sha256=profile_checksum,
        )
        existing_versions = [
            record.asset_version
            for record in repo.normalized_audio_assets.values()
            if record.source_audio_file_id == audio_file_id
        ]
        record = NormalizedAudioAsset(
            organization_id=audio_file.organization_id,
            session_id=audio_file.session_id,
            asset_version=max(existing_versions, default=0) + 1,
            object_key=normalized_object_key,
            source_checksum_sha256=source_checksum,
            normalized_checksum_sha256=normalized.normalized_checksum_sha256,
            format="wav_pcm_s16le",
            duration_ms=normalized.duration_ms,
            sample_rate_hz=normalized.sample_rate_hz,
            channels=1,
            frame_count=normalized.frame_count,
            decoder_name=decoded.decoder_name,
            decoder_version=decoded.decoder_version,
            conversion_command_profile=normalized.conversion_profile,
            verification_status="verified",
            provenance=provenance,
            source_audio_file_id=audio_file_id,
            source_asset_version=audio_file.source_asset_version,
            created_at=utc_now(),
            status=ArtifactStatus.current,
        )
        audio_file.size_bytes = actual_size_bytes
        audio_file.duration_seconds = (
            decoded.frame_count / decoded.sample_rate_hz
        )
        audio_file.sample_rate_hz = decoded.sample_rate_hz
        audio_file.channels = decoded.channels
        audio_file.checksum_sha256 = source_checksum
        stored = repo.create_normalized_audio_asset(record)
        if current is not None:
            repo.add_audit(
                "audio.normalization_regenerated",
                audio_file_id,
                "Normalized working asset regenerated after integrity verification.",
            )
        return stored
    except Exception as exc:
        for field_name, value in original_audio_fields.items():
            setattr(audio_file, field_name, value)
        if normalized_object_key is not None:
            durable_reference_exists = False
            if record is not None:
                try:
                    durable_reference_exists = (
                        repo.has_durable_normalized_audio_reference(
                            source_audio_file_id=record.source_audio_file_id,
                            asset_version=record.asset_version,
                            object_key=record.object_key,
                            normalized_checksum_sha256=(
                                record.normalized_checksum_sha256
                            ),
                        )
                    )
                except Exception as reference_error:  # noqa: BLE001
                    durable_reference_exists = True
                    exc.add_note(
                        "Normalized-object durable reference check failed; "
                        "bytes were retained fail-closed: "
                        f"{type(reference_error).__name__}"
                    )
            if durable_reference_exists:
                exc.add_note(
                    "Normalized-object cleanup skipped because durable state "
                    "references the persisted bytes."
                )
                raise
            try:
                cleanup = storage_adapter.delete_object(normalized_object_key)
                if not cleanup.deleted:
                    exc.add_note(
                        f"Normalized-object cleanup did not complete: {cleanup.status}"
                    )
            except Exception as cleanup_error:  # noqa: BLE001
                exc.add_note(
                    "Normalized-object cleanup failed; the source asset remains unchanged: "
                    f"{type(cleanup_error).__name__}"
                )
        raise
