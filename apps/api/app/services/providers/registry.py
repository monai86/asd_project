"""
providers/registry.py
---------------------
ProviderRegistry — central catalogue of registered FeatureProviders.

Usage
-----
    from app.services.providers.registry import provider_registry

    provider = provider_registry.get("basic_feature_provider")
    result = provider.extract_features(transcript)

    # List all registered providers
    for info in provider_registry.list_providers():
        print(info["provider_id"], info["available"])

Adding a new provider
---------------------
    from app.services.providers.registry import provider_registry
    from my_module import ClanFeatureProvider

    provider_registry.register(ClanFeatureProvider())

The registry is a singleton created at module import time. Providers
are registered eagerly so that availability checks can be performed
at startup.
"""

from __future__ import annotations

from app.services.providers.base import BaseFeatureProvider, ProviderAvailability


class ProviderRegistry:
    """
    Thread-safe (read-mostly) registry of BaseFeatureProvider instances.

    Providers are keyed by their ``provider_id``.
    """

    def __init__(self) -> None:
        self._providers: dict[str, BaseFeatureProvider] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, provider: BaseFeatureProvider) -> None:
        """
        Register a provider.

        Overwrites any existing provider with the same ``provider_id``.
        Call this once at startup (or in tests) before any extraction.
        """
        self._providers[provider.provider_id] = provider

    def unregister(self, provider_id: str) -> None:
        """Remove a provider (useful in tests)."""
        self._providers.pop(provider_id, None)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, provider_id: str) -> BaseFeatureProvider:
        """
        Return the provider with *provider_id*.

        Raises
        ------
        KeyError
            If no provider with that ID is registered.
        """
        try:
            return self._providers[provider_id]
        except KeyError:
            available = list(self._providers.keys())
            raise KeyError(
                f"Provider '{provider_id}' is not registered. "
                f"Available providers: {available}"
            ) from None

    def get_default(self) -> BaseFeatureProvider:
        """
        Return the default provider (BasicFeatureProvider).

        Raises
        ------
        RuntimeError
            If no providers have been registered at all.
        """
        default_id = "basic_feature_provider"
        if default_id in self._providers:
            return self._providers[default_id]
        if self._providers:
            # Fall back to the first registered provider
            return next(iter(self._providers.values()))
        raise RuntimeError("No feature providers registered.")

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_providers(self) -> list[dict]:
        """
        Return a list of provider metadata dicts, one per registered provider.
        Includes an ``available`` field from a live check_availability() call.
        """
        result = []
        for provider in self._providers.values():
            meta = provider.get_provider_metadata()
            availability: ProviderAvailability = provider.check_availability()
            meta["available"] = availability.available
            meta["availability_reason"] = availability.reason
            meta["missing_dependencies"] = availability.missing_dependencies
            result.append(meta)
        return result

    def all_feature_definitions(self) -> list[dict]:
        """
        Return feature definitions from all registered providers,
        tagged with their provider_id.
        """
        defs = []
        for provider in self._providers.values():
            for fd in provider.get_feature_definitions():
                defs.append(
                    {
                        **fd.model_dump(),
                        "provider_id": provider.provider_id,
                    }
                )
        return defs

    def __len__(self) -> int:
        return len(self._providers)

    def __contains__(self, provider_id: str) -> bool:
        return provider_id in self._providers


# ---------------------------------------------------------------------------
# Module-level singleton + eager registration
# ---------------------------------------------------------------------------

# Import here to avoid circular imports at class-definition time
from app.services.providers.basic_provider import BasicFeatureProvider  # noqa: E402

provider_registry = ProviderRegistry()
provider_registry.register(BasicFeatureProvider())
