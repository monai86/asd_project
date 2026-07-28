"""
AsrProviderRegistry — central catalogue of registered transcription providers.

Usage:
    from app.services.asr_providers.registry import asr_provider_registry

    provider = asr_provider_registry.get("mock")
    result = provider.transcribe(audio_ref, config)
"""
from __future__ import annotations

from app.core.config import Settings, get_settings
from app.services.asr_providers.base import BaseTranscriptionProvider, ProviderAvailability


class AsrProviderRegistry:
    """Registry of ASR providers. Singleton instance: ``asr_provider_registry``."""

    def __init__(self, *, settings: Settings | None = None) -> None:
        self._providers: dict[str, BaseTranscriptionProvider] = {}
        self._settings = settings

    def register(self, provider: BaseTranscriptionProvider) -> None:
        """Add a provider to the registry."""
        self._providers[provider.provider_id] = provider

    def unregister(self, provider_id: str) -> None:
        """Remove a provider from the registry (no-op if not registered)."""
        self._providers.pop(provider_id, None)

    def get(self, provider_id: str) -> BaseTranscriptionProvider:
        """Return the provider with the given id. Raises KeyError if not registered."""
        try:
            return self._providers[provider_id]
        except KeyError:
            available = list(self._providers.keys())
            raise KeyError(
                f"Provider '{provider_id}' is not registered. Available: {available}"
            ) from None

    def get_default(
        self,
        *,
        workflow: str = "audio-upload",
    ) -> BaseTranscriptionProvider:
        """Resolve only the explicitly configured provider; never fall back."""

        provider_id = (
            self._settings or get_settings()
        ).default_audio_asr_provider.strip()
        disallowed_upload_providers = {
            "mock",
            "manual",
            "whisper",
            "faster_whisper",
            "whisperx",
            "batchalign",
        }
        if workflow == "audio-upload" and provider_id in disallowed_upload_providers:
            raise RuntimeError(
                f"Provider '{provider_id}' is not allowed for the audio-upload workflow."
            )
        try:
            return self.get(provider_id)
        except KeyError as exc:
            raise RuntimeError(
                f"Configured ASR provider '{provider_id}' is unavailable; no fallback is allowed."
            ) from exc

    def list_supported(self) -> list[dict]:
        """Return metadata + live availability for every registered provider."""
        result = []
        for p in self._providers.values():
            meta = p.get_provider_metadata()
            avail: ProviderAvailability = p.check_availability()
            meta["available"] = avail.available
            meta["availability_reason"] = avail.reason
            meta["missing_dependencies"] = avail.missing_dependencies
            result.append(meta)
        return result

    def list_available(self) -> list[dict]:
        """Return metadata for providers that are currently available."""
        return [p for p in self.list_supported() if p["available"]]

    def __contains__(self, provider_id: str) -> bool:
        return provider_id in self._providers


# ---------------------------------------------------------------------------
# Eager registration — runs at module import time
# ---------------------------------------------------------------------------
from app.services.asr_providers.mock_provider import MockTranscriptionProvider  # noqa: E402
from app.services.asr_providers.local_whisper_provider import LocalWhisperProvider  # noqa: E402
from app.services.asr_providers.manual_provider import ManualTranscriptionProvider  # noqa: E402
from app.services.asr_providers.placeholder_provider import PlaceholderTranscriptionProvider  # noqa: E402

asr_provider_registry = AsrProviderRegistry()
asr_provider_registry.register(MockTranscriptionProvider())
asr_provider_registry.register(LocalWhisperProvider())
asr_provider_registry.register(ManualTranscriptionProvider())
for name in ["whisper", "faster_whisper", "whisperx", "batchalign"]:
    asr_provider_registry.register(PlaceholderTranscriptionProvider(name))

