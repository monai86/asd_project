"""
MockTranscriptionProvider — deterministic demo transcription.

WARNING: THIS IS A MOCK PROVIDER.
Output is synthetic and does not represent real ASR.
All output must be reviewed by a qualified therapist.
"""
from __future__ import annotations

from app.services.asr_providers.base import (
    BaseTranscriptionProvider,
    ProviderAvailability,
    TranscriptLine,
    TranscriptionResult,
)

_MOCK_LINES: list[TranscriptLine] = [
    TranscriptLine(
        line_id="mock-001",
        speaker="UNK",
        start_ms=0,
        end_ms=2400,
        text="Mock ASR output — therapist must listen to the recording and correct this text.",
        source="mock",
        confidence=None,
        unclear=True,
    ),
    TranscriptLine(
        line_id="mock-002",
        speaker="CHI",
        start_ms=2500,
        end_ms=4000,
        text="xxx yyy",
        source="mock",
        confidence=None,
        unclear=True,
    ),
    TranscriptLine(
        line_id="mock-003",
        speaker="UNK",
        start_ms=4100,
        end_ms=5500,
        text="This is placeholder output from the mock ASR provider.",
        source="mock",
        confidence=None,
        unclear=False,
    ),
]


class MockTranscriptionProvider(BaseTranscriptionProvider):
    """
    Deterministic mock ASR provider for demo/test use.

    Always available. Returns fixed synthetic lines so tests are reproducible.
    Output must never be treated as clinical data.
    """

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def provider_name(self) -> str:
        return "MockTranscriptionProvider"

    @property
    def provider_version(self) -> str:
        return "v0.8.0-mock"

    def get_provider_metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "description": (
                "Synthetic demo transcription provider. NOT real ASR. Therapist review required."
            ),
            "is_mock": True,
            "external_dependencies": [],
            "clinical_caution": (
                "Output is synthetic and not clinically valid. "
                "Therapist must listen to the audio and correct all content."
            ),
        }

    def check_availability(self) -> ProviderAvailability:
        return ProviderAvailability(available=True, reason="Mock provider always available.")

    def transcribe(
        self,
        audio_ref: str,
        config: dict | None = None,
    ) -> TranscriptionResult:
        language = "en"
        if config and isinstance(config.get("language"), str) and config["language"]:
            language = config["language"]

        return TranscriptionResult(
            status="completed",
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            transcript_lines=list(_MOCK_LINES),
            language=language,
            confidence_available=False,
            word_timestamps_available=True,
            speaker_segments_available=False,
            warnings=[
                "MOCK PROVIDER: This output is synthetic and not real ASR.",
                "Therapist must listen to the recording and correct all content.",
                "Speaker labels are placeholders only.",
            ],
        )
