"""
LocalWhisperProvider — architecture stub for future local Whisper integration.

check_availability() returns unavailable unless WHISPER_MODEL_PATH is configured
in app settings. This class is intentionally a non-functional stub.
"""
from __future__ import annotations

from app.services.asr_providers.base import (
    BaseTranscriptionProvider,
    ProviderAvailability,
    TranscriptionResult,
)
from app.core.config import get_settings


class LocalWhisperProvider(BaseTranscriptionProvider):
    """
    Placeholder stub. Returns unavailable unless whisper_model_path is set.
    Full implementation requires openai-whisper or faster-whisper + model file.
    """

    @property
    def provider_id(self) -> str:
        return "local_whisper"

    @property
    def provider_name(self) -> str:
        return "LocalWhisperProvider"

    @property
    def provider_version(self) -> str:
        return "v1-stub"

    def get_provider_metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "description": (
                "Local Whisper ASR provider (not yet implemented). Architecture stub only."
            ),
            "is_stub": True,
            "external_dependencies": [
                "openai-whisper or faster-whisper",
                "WHISPER_MODEL_PATH env var",
            ],
            "clinical_caution": "Not available in this build.",
        }

    def check_availability(self) -> ProviderAvailability:
        settings = get_settings()
        model_path = getattr(settings, "whisper_model_path", None)
        if not model_path:
            return ProviderAvailability(
                available=False,
                reason="WHISPER_MODEL_PATH not configured.",
                missing_dependencies=["WHISPER_MODEL_PATH"],
            )
        return ProviderAvailability(
            available=False,
            reason="LocalWhisperProvider is a stub and is not yet implemented.",
        )

    def transcribe(
        self,
        audio_ref: str,
        config: dict | None = None,
    ) -> TranscriptionResult:
        return TranscriptionResult(
            status="unavailable",
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            transcript_lines=[],
            error_message="LocalWhisperProvider is not implemented in this build.",
            warnings=["LocalWhisperProvider is a stub. Use mock provider for testing."],
        )
