"""
providers/base.py
-----------------
Abstract base class (protocol) for all FeatureProviders.

A FeatureProvider is responsible for:
  - Declaring the features it can compute (FeatureDefinition list)
  - Checking its own availability (e.g. CLAN binary present or not)
  - Extracting FeatureValues from a Transcript and returning a structured
    FeatureExtractionResult envelope.

Adding a new provider (e.g. ClanFeatureProvider):
  1. Subclass BaseFeatureProvider.
  2. Implement all abstract methods.
  3. Register the instance with ProviderRegistry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.schemas.clinical import FeatureDefinition, FeatureValue, Transcript


# ---------------------------------------------------------------------------
# Provider availability
# ---------------------------------------------------------------------------

@dataclass
class ProviderAvailability:
    """Reports whether a provider is usable in the current runtime."""

    available: bool
    reason: str = ""
    missing_dependencies: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.available


# ---------------------------------------------------------------------------
# Extraction result envelope
# ---------------------------------------------------------------------------

@dataclass
class FeatureExtractionResult:
    """
    Structured envelope returned by BaseFeatureProvider.extract_features().

    Callers must check ``valid`` before consuming ``values``.
    ``warnings`` are non-blocking informational messages; blocking errors
    raise exceptions (see BaseFeatureProvider docstring).
    """

    provider_id: str
    provider_name: str
    provider_version: str
    feature_schema_version: str
    tokenizer_version: str | None
    transcript_id: str
    session_id: str
    computed_at: datetime
    values: list[FeatureValue]
    warnings: list[str] = field(default_factory=list)
    validation_issues: list[str] = field(default_factory=list)
    insufficient_data: bool = False
    valid: bool = True
    config_used: dict = field(default_factory=dict)

    @classmethod
    def empty(
        cls,
        provider_id: str,
        provider_name: str,
        provider_version: str,
        transcript_id: str,
        session_id: str,
        reason: str = "insufficient_data",
    ) -> "FeatureExtractionResult":
        """Return an empty, invalid result for error / insufficient-data cases."""
        return cls(
            provider_id=provider_id,
            provider_name=provider_name,
            provider_version=provider_version,
            feature_schema_version="features-basic-v0.7",
            tokenizer_version=None,
            transcript_id=transcript_id,
            session_id=session_id,
            computed_at=datetime.now(timezone.utc),
            values=[],
            warnings=[reason],
            valid=False,
            insufficient_data=True,
        )


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class BaseFeatureProvider(ABC):
    """
    Abstract base class for language-sample feature providers.

    Blocking errors (e.g. QA not run, attestation missing) must raise
    ``ValueError`` — the service layer catches these and converts them
    to HTTP 422 responses.

    Non-blocking issues (low token count, unsupported tiers) must be
    appended to ``FeatureExtractionResult.warnings`` and must NOT raise.
    """

    # ------------------------------------------------------------------
    # Identity (must be unique across all registered providers)
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Machine-readable identifier, e.g. 'basic_feature_provider'."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name, e.g. 'BasicFeatureProvider'."""
        ...

    @property
    @abstractmethod
    def provider_version(self) -> str:
        """Semantic version string, e.g. 'v0.7.0'."""
        ...

    @property
    @abstractmethod
    def feature_schema_version(self) -> str:
        """Schema version tag stamped on every FeatureValue, e.g. 'features-basic-v0.7'."""
        ...

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @abstractmethod
    def get_provider_metadata(self) -> dict:
        """Return a dict suitable for the /features/providers/{id} endpoint."""
        ...

    @abstractmethod
    def check_availability(self) -> ProviderAvailability:
        """
        Return ProviderAvailability.

        Called at startup (health-check) and before each extraction.
        Must be fast and must not raise.
        """
        ...

    @abstractmethod
    def get_feature_definitions(self) -> list[FeatureDefinition]:
        """
        Return the full catalogue of features this provider can compute.

        The list is used to power the /features/definitions endpoint and
        to validate that all expected features appear in the output.
        """
        ...

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    @abstractmethod
    def extract_features(
        self,
        transcript: Transcript,
        config: dict | None = None,
    ) -> FeatureExtractionResult:
        """
        Compute features from *transcript* and return a
        FeatureExtractionResult envelope.

        Parameters
        ----------
        transcript:
            The persisted Transcript object (utterances already cleaned).
        config:
            Optional provider-specific configuration dict (thresholds etc.).
            Providers must fall back to sensible defaults when None.

        Returns
        -------
        FeatureExtractionResult
            Always returns an envelope — never raises on insufficient data.
            Raises ``ValueError`` only for gating violations (QA not run etc.).
        """
        ...
