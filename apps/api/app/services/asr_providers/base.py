"""
Abstract base classes for ASR (Automatic Speech Recognition) providers.

Adding a new provider:
  1. Subclass BaseTranscriptionProvider
  2. Implement all abstract methods
  3. Register with asr_provider_registry.register(MyProvider())
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


class ProviderDefinitiveError(RuntimeError):
    """The provider definitively rejected or failed the request."""


class ProviderOutcomeUnknownError(RuntimeError):
    """The provider may have accepted the request, but its outcome is unknown."""


@dataclass
class ProviderAvailability:
    """Result of a provider's availability check."""

    available: bool
    reason: str = ""
    missing_dependencies: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.available


@dataclass
class TranscriptLine:
    """One utterance line from an ASR provider."""

    line_id: str
    speaker: str  # "CHI" | "THER" | "UNK"
    text: str
    start_ms: int | None = None
    end_ms: int | None = None
    confidence: float | None = None
    source: str = "asr"  # "asr" | "mock" | "manual"
    unclear: bool = False
    temporary_speaker_id: str | None = None
    source_speaker_label: str | None = None


@dataclass
class TranscriptionResult:
    """Structured output from a provider's transcribe() call."""

    status: str  # "completed" | "failed" | "unavailable"
    provider_id: str
    provider_name: str
    provider_version: str
    transcript_lines: list[TranscriptLine]
    language: str = "en"
    confidence_available: bool = False
    word_timestamps_available: bool = False
    speaker_segments_available: bool = False
    warnings: list[str] = field(default_factory=list)
    error_message: str = ""
    provider_metadata: dict = field(default_factory=dict)
    raw_artifact_refs: list[str] = field(default_factory=list)
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseTranscriptionProvider(ABC):
    """Abstract base for all ASR providers."""

    @property
    def supports_idempotent_replay(self) -> bool:
        """Whether replaying one stable request key is safe after an unknown outcome."""
        return False

    @property
    @abstractmethod
    def provider_id(self) -> str: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def provider_version(self) -> str: ...

    @abstractmethod
    def get_provider_metadata(self) -> dict: ...

    @abstractmethod
    def check_availability(self) -> ProviderAvailability: ...

    @abstractmethod
    def transcribe(
        self,
        audio_ref: str,
        config: dict | None = None,
    ) -> TranscriptionResult: ...
