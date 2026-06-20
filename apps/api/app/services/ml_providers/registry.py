from __future__ import annotations

from app.services.ml_providers.base import BaseMLProvider, MLProviderAvailability
from app.services.ml_providers.reference_evidence import ReferenceEvidenceProvider
from app.services.ml_providers.rule_based import RuleBasedReviewCueProvider


class UnavailableMLProvider(BaseMLProvider):
    provider_id = "unavailable"
    provider_name = "UnavailableMLProvider"
    provider_version = "0.9.1"
    reason = "Provider unavailable."

    def check_availability(self) -> MLProviderAvailability:
        return MLProviderAvailability(False, self.reason)

    def get_model_metadata(self) -> dict:
        return {"provider_type": "placeholder", "unavailable_reason": self.reason}

    def predict(self, features, context, config=None):
        raise RuntimeError(self.reason)


class BaselineResearchClassifierProvider(UnavailableMLProvider):
    provider_id = "baseline_research_classifier"
    provider_name = "BaselineResearchClassifierProvider"
    reason = "Label provenance and runtime feature-schema compatibility are not verified."


class FutureMLProvider(UnavailableMLProvider):
    provider_id = "future_ml_provider"
    provider_name = "FutureMLProvider"
    reason = "Future provider placeholder is unavailable."


class MLProviderRegistry:
    def __init__(self):
        self.providers: dict[str, BaseMLProvider] = {}

    def register(self, provider: BaseMLProvider) -> None:
        self.providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> BaseMLProvider:
        try:
            return self.providers[provider_id]
        except KeyError as exc:
            raise ValueError(f"Unsupported ML provider: {provider_id}") from exc

    def get_default(self) -> BaseMLProvider:
        return self.providers["rule_based_review_cue"]

    def list_supported(self) -> list[BaseMLProvider]:
        return list(self.providers.values())

    def list_available(self) -> list[BaseMLProvider]:
        return [provider for provider in self.providers.values() if provider.check_availability()]

    def list_providers(self) -> list[dict]:
        rows = []
        for provider in self.list_supported():
            availability = provider.check_availability()
            rows.append({
                "provider_id": provider.provider_id,
                "provider_name": provider.provider_name,
                "provider_version": provider.provider_version,
                "available": availability.available,
                "unavailable_reason": availability.reason or None,
                "metadata": provider.get_model_metadata(),
            })
        return rows


ml_provider_registry = MLProviderRegistry()
ml_provider_registry.register(RuleBasedReviewCueProvider())
ml_provider_registry.register(ReferenceEvidenceProvider())
ml_provider_registry.register(BaselineResearchClassifierProvider())
ml_provider_registry.register(FutureMLProvider())
