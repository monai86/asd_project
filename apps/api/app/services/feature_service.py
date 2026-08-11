"""
feature_service.py
------------------
Service-layer orchestrator for feature extraction.

Responsibilities
----------------
- Enforce clinical workflow gates (QA must have run, attestation required,
  debug-override guard).
- Delegate actual feature computation to the ProviderRegistry.
- Persist the resulting FeatureSet and update the session record.
- Write an audit log entry.

Feature calculation logic lives entirely inside the FeatureProvider classes
(app/services/providers/).  This module must NOT contain any linguistic
computation.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.repositories.mock_repository import MockRepository, new_id
from app.schemas.clinical import (
    FeatureExtractionRequest,
    FeatureSet,
    QaStatus,
    ReviewStatus,
)
from app.services.providers.registry import provider_registry
from app.services import speaker_mapping_service


def extract_features(
    repo: MockRepository,
    transcript_id: str,
    payload: FeatureExtractionRequest,
) -> FeatureSet:
    """
    Orchestrate feature extraction for a transcript.

    Workflow gates (in order)
    -------------------------
    1. QA must have been run.
    2. Debug-override request requires the setting to be enabled.
    3. QA failures block extraction unless debug-override is active.
    4. Therapist attestation is required unless debug-override is active.

    Parameters
    ----------
    repo:
        MockRepository instance for the current request scope.
    transcript_id:
        ID of the Transcript to extract features from.
    payload:
        FeatureExtractionRequest (may include debug-override flags).

    Returns
    -------
    FeatureSet
        Persisted and returned as a deep-cloned value object.

    Raises
    ------
    KeyError
        If *transcript_id* does not exist in the repo.
    ValueError
        If any clinical workflow gate is not satisfied.
    """
    transcript = repo.transcripts[transcript_id]
    input_transcript_version = transcript.version
    settings = get_settings()

    # ------------------------------------------------------------------
    # Gate 1 — QA must have been run
    # ------------------------------------------------------------------
    if transcript.qa_status == QaStatus.not_run:
        raise ValueError("Run transcript QA before feature extraction.")

    # ------------------------------------------------------------------
    # Gate 2 — debug-override guard
    # ------------------------------------------------------------------
    debug_override_requested = bool(
        payload.force_debug_override and payload.override_reason.strip()
    )
    debug_override_allowed = debug_override_requested and settings.debug_feature_override

    if debug_override_requested and not debug_override_allowed:
        raise ValueError(
            "Feature extraction debug override is disabled in this runtime."
        )

    # ------------------------------------------------------------------
    # Gate 3 — QA failure blocks extraction (unless debug override)
    # ------------------------------------------------------------------
    if transcript.qa_status == QaStatus.fail and not debug_override_allowed:
        raise ValueError(
            "Feature extraction is blocked because transcript QA failed."
        )

    # ------------------------------------------------------------------
    # Gate 4 — Attestation required (unless debug override)
    # ------------------------------------------------------------------
    if not transcript.therapist_attested and not debug_override_allowed:
        raise ValueError(
            "Feature extraction requires therapist transcript attestation."
        )

    mapping = speaker_mapping_service.require_confirmed_mapping(repo, transcript_id)

    # ------------------------------------------------------------------
    # Provider selection & extraction
    # ------------------------------------------------------------------
    provider = provider_registry.get_default()
    availability = provider.check_availability()
    if not availability:
        raise ValueError(
            f"Provider '{provider.provider_name}' is not available: "
            f"{availability.reason}"
        )

    result = provider.extract_features(transcript)

    # ------------------------------------------------------------------
    # Compose service-level warnings
    # ------------------------------------------------------------------
    service_warnings: list[str] = list(result.warnings)
    if debug_override_allowed:
        service_warnings.append(
            f"Feature set produced with debug override: {payload.override_reason.strip()}"
        )
    if not transcript.therapist_attested:
        service_warnings.append(
            "Feature set produced with debug override from an unattested transcript."
        )

    # ------------------------------------------------------------------
    # Persist FeatureSet
    # ------------------------------------------------------------------
    feature_set = FeatureSet(
        feature_set_id=new_id("fs"),
        session_id=transcript.session_id,
        transcript_id=transcript_id,
        transcript_version=input_transcript_version,
        schema_version=result.feature_schema_version,
        therapist_attested=transcript.therapist_attested,
        extracted_at=result.computed_at,
        warnings=service_warnings,
        features=result.values,
        review_status=ReviewStatus.ready,
        insufficient_data=result.insufficient_data,
        provider_name=result.provider_name,
        config_used=result.config_used,
        speaker_mapping_id=mapping.mapping_id if mapping is not None else None,
        speaker_mapping_version=mapping.mapping_version if mapping is not None else None,
    )
    return repo.create_feature_set(
        feature_set,
        actor_id="system",
        audit_action="features.extract",
        audit_message=(
            f"Language sample features extracted by {result.provider_name} "
            f"v{result.provider_version} from reviewed transcript "
            f"(schema: {result.feature_schema_version})."
        ),
    )


def get_feature_definitions() -> list[dict]:
    """
    Return all feature definitions from all registered providers.

    Used by GET /features/definitions.
    """
    return provider_registry.all_feature_definitions()


def get_providers() -> list[dict]:
    """
    Return provider metadata including live availability status.

    Used by GET /features/providers.
    """
    return provider_registry.list_providers()
