"""
PlaceholderTranscriptionProvider — placeholders for whisper/faster_whisper/whisperx/batchalign.
"""
from __future__ import annotations

from app.services.asr_providers.base import (
    BaseTranscriptionProvider,
    ProviderDefinitiveError,
    ProviderAvailability,
    TranscriptLine,
    TranscriptionResult,
)


class PlaceholderTranscriptionProvider(BaseTranscriptionProvider):
    """
    Placeholder ASR provider for compatibility.
    Always available, but fails if draft_text is empty to mirror old testing stubs.
    """

    def __init__(self, provider_id: str) -> None:
        self._provider_id = provider_id

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def provider_name(self) -> str:
        return f"Placeholder{self._provider_id.capitalize()}Provider"

    @property
    def provider_version(self) -> str:
        return "v1-placeholder"

    def get_provider_metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "description": f"Placeholder provider for {self.provider_id}.",
            "is_placeholder": True,
            "external_dependencies": [],
            "clinical_caution": "Placeholder only.",
        }

    def check_availability(self) -> ProviderAvailability:
        return ProviderAvailability(
            available=True, reason="Placeholder provider is always available."
        )

    def transcribe(
        self,
        audio_ref: str,
        config: dict | None = None,
    ) -> TranscriptionResult:
        draft_text = ""
        if config and "draft_text" in config:
            draft_text = config["draft_text"] or ""

        if not draft_text.strip():
            # Raise exception to trigger the asr_failed path in job runner
            raise ProviderDefinitiveError("ASR failed")

        lines = [
            TranscriptLine(
                line_id="place-001",
                speaker="UNK",
                text=draft_text.strip(),
                source="asr",
            )
        ]
        return TranscriptionResult(
            status="completed",
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            transcript_lines=lines,
        )
