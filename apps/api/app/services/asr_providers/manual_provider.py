"""
ManualTranscriptionProvider — allows manual/paste transcription mapping via registry.
"""
from __future__ import annotations

from hashlib import sha256

from app.services.asr_providers.base import (
    BaseTranscriptionProvider,
    ProviderAvailability,
    TranscriptLine,
    TranscriptionResult,
)
from app.services.cha_service import manual_text_to_utterances


_CANONICAL_SPEAKER_CODES = {"CHI", "THER", "OTH"}
_TEMPORARY_SPEAKER_ID_PREFIX = "manual:sha256:"


def _manual_source_labels(text: str) -> list[str | None]:
    """Return raw speaker labels using the manual parser's line rules."""

    labels: list[str | None] = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            labels.append(None)
            continue
        left, _ = line.split(":", 1)
        label = left.strip().lstrip("*").strip()
        labels.append(label or None)
    return labels


def _temporary_speaker_id(source_speaker_label: str) -> str:
    """Return a schema-safe, stable ID without truncating source labels."""

    if len(source_speaker_label) <= 128:
        return source_speaker_label
    digest = sha256(source_speaker_label.encode("utf-8")).hexdigest()
    return f"{_TEMPORARY_SPEAKER_ID_PREFIX}{digest}"


class ManualTranscriptionProvider(BaseTranscriptionProvider):
    """
    Provider that processes manual/pasted transcript text.
    Used for backward compatibility and manual upload paths.
    """

    @property
    def supports_idempotent_replay(self) -> bool:
        return True

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
        source_labels = _manual_source_labels(draft_text)
        lines = []
        for i, (u, source_speaker_label) in enumerate(
            zip(utterances, source_labels, strict=True)
        ):
            speaker = str(u.speaker)
            is_canonical = speaker in _CANONICAL_SPEAKER_CODES
            temporary_speaker_id = (
                _temporary_speaker_id(source_speaker_label)
                if source_speaker_label is not None and not is_canonical
                else None
            )
            lines.append(
                TranscriptLine(
                    line_id=f"man-{i+1:03d}",
                    speaker=speaker,
                    text=u.text,
                    start_ms=u.start_ms,
                    end_ms=u.end_ms,
                    temporary_speaker_id=temporary_speaker_id,
                    source_speaker_label=(
                        source_speaker_label if temporary_speaker_id is not None else None
                    ),
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
