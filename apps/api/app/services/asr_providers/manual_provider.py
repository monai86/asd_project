"""
ManualTranscriptionProvider — allows manual/paste transcription mapping via registry.
"""
from __future__ import annotations

from app.services.asr_providers.base import (
    BaseTranscriptionProvider,
    ProviderAvailability,
    TranscriptLine,
    TranscriptionResult,
)
from app.services.cha_service import manual_text_to_utterances


class ManualTranscriptionProvider(BaseTranscriptionProvider):
    """
    Provider that processes manual/pasted transcript text.
    Used for backward compatibility and manual upload paths.
    """

    @property
    def provider_id(self) -> str:
        return "manual"

    @property
    def provider_name(self) -> str:
        return "ManualTranscriptionProvider"

    @property
    def provider_version(self) -> str:
        return "v1-manual"

    def get_provider_metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "description": "Manual draft transcript provider for paste-in text.",
            "is_manual": True,
            "external_dependencies": [],
            "clinical_caution": "Draft transcript requires therapist review.",
        }

    def check_availability(self) -> ProviderAvailability:
        return ProviderAvailability(available=True, reason="Manual entry is always available.")

    def transcribe(
        self,
        audio_ref: str,
        config: dict | None = None,
    ) -> TranscriptionResult:
        draft_text = ""
        if config and "draft_text" in config:
            draft_text = config["draft_text"] or ""

        utterances = manual_text_to_utterances(draft_text)
        lines = []
        for i, u in enumerate(utterances):
            raw_speaker = str(u.speaker)
            temporary_speaker_id = (
                raw_speaker if raw_speaker not in {"CHI", "THER", "OTH"} else None
            )
            lines.append(
                TranscriptLine(
                    line_id=f"man-{i+1:03d}",
                    speaker=raw_speaker,
                    text=u.text,
                    start_ms=u.start_ms,
                    end_ms=u.end_ms,
                    temporary_speaker_id=temporary_speaker_id,
                    source_speaker_label=temporary_speaker_id,
                    source="manual",
                )
            )

        return TranscriptionResult(
            status="completed",
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            transcript_lines=lines,
        )
