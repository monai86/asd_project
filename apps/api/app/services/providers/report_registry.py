from __future__ import annotations

from app.schemas.clinical import ReportProviderAvailability, ReportProviderResult, ReportGenerationInput
from app.services.providers.report_providers import (
    BaseReportProvider,
    LocalLLMReportProvider,
    TemplateReportProvider,
)


class FutureCloudLLMReportProvider(BaseReportProvider):
    """Placeholder for future Cloud LLM integrations. Always unavailable in v1.0."""

    @property
    def provider_id(self) -> str:
        return "future_cloud_llm"

    @property
    def provider_name(self) -> str:
        return "FutureCloudLLMReportProvider"

    @property
    def provider_version(self) -> str:
        return "1.0.0"

    def check_availability(self) -> ReportProviderAvailability:
        return ReportProviderAvailability(
            provider_id=self.provider_id,
            available=False,
            reason="Cloud LLM integration is deferred to a future pilot release.",
            requires_external_service=True
        )

    def generate_report(
        self, input_data: ReportGenerationInput, config: dict
    ) -> ReportProviderResult:
        return ReportProviderResult(
            status="unavailable",
            sections=[],
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            error_message="Provider is not available."
        )


class ReportProviderRegistry:
    """Thread-safe registry for report providers."""

    def __init__(self) -> None:
        self._providers: dict[str, BaseReportProvider] = {}

    def register(self, provider: BaseReportProvider) -> None:
        """Register a report provider instance."""
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> BaseReportProvider:
        """Retrieve a registered provider by ID, defaulting to template if not found."""
        if provider_id in self._providers:
            return self._providers[provider_id]
        return self._providers["template"]

    def list_supported(self) -> list[str]:
        """List machine-readable IDs of all registered providers."""
        return list(self._providers.keys())

    def list_available(self) -> list[ReportProviderAvailability]:
        """Return availability metadata from all registered providers."""
        availabilities = []
        for provider in self._providers.values():
            availabilities.append(provider.check_availability())
        return availabilities


# Eager singleton instantiation
report_provider_registry = ReportProviderRegistry()
report_provider_registry.register(TemplateReportProvider())
report_provider_registry.register(LocalLLMReportProvider())
report_provider_registry.register(FutureCloudLLMReportProvider())
