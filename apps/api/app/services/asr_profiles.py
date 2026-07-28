"""Immutable, fail-closed ASR profile loading for the v1.7.0 testbed."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from importlib import metadata
import json
from pathlib import Path
import stat
from typing import Literal, Mapping, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


_SHA256_PATTERN = r"^[a-f0-9]{64}$"
_FLOATING_IDENTIFIERS = {"latest", "main", "master", "default", "current"}


class UnsafeModelArtifactError(ValueError):
    """The artifact tree contains a link or non-regular filesystem entry."""


class ArtifactChangedDuringReadError(ValueError):
    """An artifact changed while its verification snapshot was being created."""


@dataclass(frozen=True, slots=True)
class ArtifactEntrySnapshot:
    relative_path: str
    device: int
    inode: int
    mode: int
    size_bytes: int
    modified_at_ns: int


@dataclass(frozen=True, slots=True)
class ArtifactSnapshot:
    checksum_sha256: str
    entries: tuple[ArtifactEntrySnapshot, ...]


@dataclass(frozen=True, slots=True)
class ArtifactFingerprint:
    entries: tuple[ArtifactEntrySnapshot, ...]


class ValidatedFrozenProfile(BaseModel):
    """Frozen profile model whose copies and instances are always revalidated."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    def revalidated(self) -> Self:
        values = {
            field_name: getattr(self, field_name)
            for field_name in type(self).model_fields
        }
        return type(self).model_validate(values)

    def model_copy(
        self,
        *,
        update: Mapping[str, object] | None = None,
        deep: bool = False,
    ) -> Self:
        values = {
            field_name: getattr(self, field_name)
            for field_name in type(self).model_fields
        }
        if deep:
            values = deepcopy(values)
        if update:
            values.update(update)
        return type(self).model_validate(values)


class PinnedVadParameters(ValidatedFrozenProfile):
    """Deeply immutable Silero VAD options when VAD is enabled."""

    threshold: float = Field(ge=0, le=1)
    neg_threshold: float | None = Field(default=None, ge=0, le=1)
    min_speech_duration_ms: int = Field(ge=0)
    max_speech_duration_s: float = Field(gt=0, allow_inf_nan=False)
    min_silence_duration_ms: int = Field(ge=0)
    speech_pad_ms: int = Field(ge=0)


def _json_value(value: object) -> object:
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def canonical_profile_checksum(profile: Mapping[str, object]) -> str:
    """Hash every output-affecting profile field using canonical JSON."""

    material = {
        key: _json_value(value)
        for key, value in profile.items()
        if key != "profile_checksum_sha256"
    }
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _entry_snapshot(path: Path, *, relative_path: str) -> ArtifactEntrySnapshot:
    metadata = path.stat(follow_symlinks=False)
    if stat.S_ISLNK(metadata.st_mode):
        raise UnsafeModelArtifactError(
            "artifact contains a symbolic link"
        )
    if not (
        stat.S_ISREG(metadata.st_mode)
        or stat.S_ISDIR(metadata.st_mode)
    ):
        raise UnsafeModelArtifactError(
            "artifact contains a non-regular filesystem entry"
        )
    return ArtifactEntrySnapshot(
        relative_path=relative_path,
        device=metadata.st_dev,
        inode=metadata.st_ino,
        mode=metadata.st_mode,
        size_bytes=metadata.st_size,
        modified_at_ns=metadata.st_mtime_ns,
    )


def _snapshot_artifact(
    path: Path,
    *,
    allow_directory: bool,
) -> ArtifactSnapshot:
    """Create a stable checksum and filesystem-identity snapshot."""

    try:
        root = _entry_snapshot(path, relative_path=".")
    except FileNotFoundError:
        raise
    if stat.S_ISLNK(root.mode):
        raise UnsafeModelArtifactError(
            "artifact path is a symbolic link"
        )
    if stat.S_ISREG(root.mode):
        digest = sha256()
        before = root
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        after = _entry_snapshot(path, relative_path=".")
        if after != before:
            raise ArtifactChangedDuringReadError(
                "artifact changed while its checksum was being computed"
            )
        return ArtifactSnapshot(
            checksum_sha256=digest.hexdigest(),
            entries=(after,),
        )
    if not stat.S_ISDIR(root.mode) or not allow_directory:
        raise UnsafeModelArtifactError(
            "artifact must be a regular file"
        )

    digest = sha256()
    paths = sorted(
        path.rglob("*"),
        key=lambda item: item.relative_to(path).as_posix(),
    )
    before_entries = (
        root,
        *(
            _entry_snapshot(
                item,
                relative_path=item.relative_to(path).as_posix(),
            )
            for item in paths
        ),
    )
    files = [
        item
        for item, snapshot in zip(paths, before_entries[1:])
        if stat.S_ISREG(snapshot.mode)
    ]
    if not files:
        raise FileNotFoundError(
            "model artifact directory is empty"
        )
    for item in files:
        relative = item.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with item.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    after_paths = sorted(
        path.rglob("*"),
        key=lambda item: item.relative_to(path).as_posix(),
    )
    after_entries = (
        _entry_snapshot(path, relative_path="."),
        *(
            _entry_snapshot(
                item,
                relative_path=item.relative_to(path).as_posix(),
            )
            for item in after_paths
        ),
    )
    if after_entries != before_entries:
        raise ArtifactChangedDuringReadError(
            "artifact tree changed while its checksum was being computed"
        )
    return ArtifactSnapshot(
        checksum_sha256=digest.hexdigest(),
        entries=after_entries,
    )


def snapshot_model_artifact(path: Path) -> ArtifactSnapshot:
    """Snapshot a regular model file or regular-file-only model tree."""

    return _snapshot_artifact(path, allow_directory=True)


def fingerprint_model_artifact(path: Path) -> ArtifactFingerprint:
    """Inspect model-tree identity and safety without reading model bytes."""

    root = _entry_snapshot(path, relative_path=".")
    if stat.S_ISREG(root.mode):
        return ArtifactFingerprint(entries=(root,))
    if not stat.S_ISDIR(root.mode):
        raise UnsafeModelArtifactError(
            "model artifact must be a regular file or directory"
        )
    paths = sorted(
        path.rglob("*"),
        key=lambda item: item.relative_to(path).as_posix(),
    )
    entries = (
        root,
        *(
            _entry_snapshot(
                item,
                relative_path=item.relative_to(path).as_posix(),
            )
            for item in paths
        ),
    )
    if not any(stat.S_ISREG(item.mode) for item in entries):
        raise FileNotFoundError("model artifact directory is empty")
    return ArtifactFingerprint(entries=entries)


def snapshot_regular_file(path: Path) -> ArtifactSnapshot:
    """Snapshot one regular non-symlink processing file."""

    return _snapshot_artifact(path, allow_directory=False)


def hash_model_artifact(path: Path) -> str:
    """Hash a stable model file or deterministic model tree."""

    return snapshot_model_artifact(path).checksum_sha256


class PinnedAsrProfile(ValidatedFrozenProfile):
    """Complete immutable decoding identity used by local faster-whisper."""

    profile_id: str = Field(min_length=1, max_length=128)
    profile_version: int = Field(ge=1)
    profile_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=_SHA256_PATTERN,
    )
    model_identifier: str = Field(min_length=1, max_length=256)
    model_revision: str = Field(min_length=1, max_length=256)
    model_artifact_path: Path
    model_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=_SHA256_PATTERN,
    )
    faster_whisper_version: str = Field(min_length=1, max_length=64)
    ctranslate2_version: str = Field(min_length=1, max_length=64)
    decoder_name: str = Field(min_length=1, max_length=64)
    decoder_version: str = Field(min_length=1, max_length=64)
    device: Literal["cpu", "cuda", "auto"]
    device_index: int = Field(ge=0)
    compute_type: str = Field(min_length=1, max_length=64)
    cpu_threads: int = Field(ge=0)
    num_workers: int = Field(ge=1)
    language_mode: Literal["th", "auto"]
    task: Literal["transcribe"]
    log_progress: Literal[False]
    beam_size: int = Field(ge=1)
    best_of: int = Field(ge=1)
    patience: float = Field(gt=0)
    length_penalty: float = Field(gt=0)
    repetition_penalty: float = Field(gt=0)
    no_repeat_ngram_size: int = Field(ge=0)
    temperature: float
    compression_ratio_threshold: float | None
    log_prob_threshold: float | None
    no_speech_threshold: float | None
    vad_filter: bool
    vad_parameters: PinnedVadParameters | None
    word_timestamps: bool
    condition_on_previous_text: bool
    prompt_reset_on_temperature: float = Field(ge=0)
    initial_prompt: str | None = None
    prefix: str | None
    suppress_blank: bool
    suppress_tokens: tuple[int, ...] | None
    without_timestamps: Literal[False]
    max_initial_timestamp: float = Field(ge=0)
    prepend_punctuations: str
    append_punctuations: str
    multilingual: bool
    max_new_tokens: int | None = Field(default=None, ge=1)
    chunk_length: int | None = Field(default=None, ge=1)
    clip_timestamps: str
    hallucination_silence_threshold: float | None = Field(default=None, ge=0)
    hotwords: str | None
    language_detection_threshold: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )
    language_detection_segments: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_frozen_profile(self) -> "PinnedAsrProfile":
        if self.model_identifier.strip().lower() in _FLOATING_IDENTIFIERS:
            raise ValueError("model_identifier must be immutable, not floating")
        if self.model_revision.strip().lower() in _FLOATING_IDENTIFIERS:
            raise ValueError("model_revision must be immutable, not floating")
        if self.temperature != 0.0:
            raise ValueError("v1.7.0 deterministic ASR temperature must be 0.0")
        if (
            self.language_mode == "auto"
            and self.language_detection_threshold is None
        ):
            raise ValueError(
                "language_detection_threshold is required for auto language mode"
            )
        if self.vad_filter and self.vad_parameters is None:
            raise ValueError(
                "vad_parameters are required when vad_filter is enabled"
            )
        if not self.vad_filter and self.vad_parameters is not None:
            raise ValueError(
                "vad_parameters must be null when vad_filter is disabled"
            )
        if self.initial_prompt is not None and not self.initial_prompt.strip():
            raise ValueError("initial_prompt must be null or non-empty")
        if self.prefix is not None and not self.prefix.strip():
            raise ValueError("prefix must be null or non-empty")
        if self.hotwords is not None and not self.hotwords.strip():
            raise ValueError("hotwords must be null or non-empty")
        if self.suppress_tokens is not None and len(self.suppress_tokens) != len(
            set(self.suppress_tokens)
        ):
            raise ValueError("suppress_tokens must not contain duplicates")
        if canonical_profile_checksum(self.model_dump()) != self.profile_checksum_sha256:
            raise ValueError("ASR profile checksum does not match canonical profile")
        return self


class AsrRuntimeVersions(BaseModel):
    """Observed local capability versions; absence is represented explicitly."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    faster_whisper_version: str | None
    ctranslate2_version: str | None
    decoder_name: str
    decoder_version: str | None
    decoder_available: bool


class AsrProfileLoadError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def load_pinned_asr_profile(path: Path) -> PinnedAsrProfile:
    """Load a profile without accepting absent, malformed, or relative ambiguity."""

    if not path.is_file() or path.is_symlink():
        raise AsrProfileLoadError(
            "runtime_profile_unavailable",
            "Pinned ASR runtime profile is not available.",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("profile must be a JSON object")
        return PinnedAsrProfile.model_validate(payload)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AsrProfileLoadError(
            "runtime_profile_unverified",
            "Pinned ASR runtime profile could not be verified.",
        ) from exc


def inspect_asr_runtime() -> AsrRuntimeVersions:
    """Inspect installed packages and the already verified decoder registry."""

    def package_version(name: str) -> str | None:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            return None

    try:
        from app.services.audio_media_service import (
            get_decoder_capability_registry,
        )

        decoder = get_decoder_capability_registry()
        decoder_name = decoder.runtime.decoder_name
        decoder_version: str | None = decoder.runtime.soundfile_version
        decoder_available = bool(decoder.verified_formats)
    except Exception:  # noqa: BLE001 - capability inspection must fail closed
        decoder_name = "unknown"
        decoder_version = None
        decoder_available = False

    return AsrRuntimeVersions(
        faster_whisper_version=package_version("faster-whisper"),
        ctranslate2_version=package_version("ctranslate2"),
        decoder_name=decoder_name,
        decoder_version=decoder_version,
        decoder_available=decoder_available,
    )
