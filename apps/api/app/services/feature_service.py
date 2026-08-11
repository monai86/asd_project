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
    FeatureValue,
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
    upload_first_v170 = transcript.source.startswith("asr_draft:")
    if upload_first_v170 and debug_override_requested:
        raise ValueError(
            "Feature debug output is test-only and cannot be used by the v1.7.0 upload-first workflow."
        )

    # ------------------------------------------------------------------
    # Gate 3 — Speaker mapping required
    # ------------------------------------------------------------------
    mapping = speaker_mapping_service.require_confirmed_mapping(repo, transcript_id)

    if upload_first_v170 and repo.get_current_transcript_attestation(transcript_id) is None:
        raise ValueError(
            "Feature extraction requires a current typed transcript attestation."
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

    # ------------------------------------------------------------------
    # Provider selection & extraction
    # ------------------------------------------------------------------
    versioned_results = []
    if upload_first_v170:
        from app.services.providers.descriptive_v170_provider import (
            FEATURE_SCHEMA_VERSION,
            extract_descriptive_feature_results,
        )

        versioned_results = extract_descriptive_feature_results(repo, transcript_id)
        provider_name = "DescriptiveV170Provider"
        schema_version = FEATURE_SCHEMA_VERSION
        computed_at = versioned_results[0].generated_at
        values = [
            FeatureValue(
                name=item.feature_id,
                value=item.value,
                unit=item.unit,
                value_type="ratio" if item.unit == "ratio" else "float" if isinstance(item.value, float) else "integer",
                numerator=item.numerator,
                denominator=item.denominator,
                calculation_method=item.algorithm_version,
                provider_name=provider_name,
                feature_version=schema_version,
                transcript_id=transcript.transcript_id,
                session_id=transcript.session_id,
                computed_at=item.generated_at,
                insufficient_data=item.status.value != "available",
                warnings=[value for value in [item.reason_code, *item.limitations] if value],
                interpretation_hint=item.clinical_caution,
            )
            for item in versioned_results
        ]
        result_warnings: list[str] = []
        result_insufficient = any(item.status.value != "available" for item in versioned_results)
        result_config = {"algorithm_version": versioned_results[0].algorithm_version}
    else:
        provider = provider_registry.get_default()
        availability = provider.check_availability()
        if not availability:
            raise ValueError(
                f"Provider '{provider.provider_name}' is not available: "
                f"{availability.reason}"
            )
        result = provider.extract_features(transcript)
        provider_name = result.provider_name
        schema_version = result.feature_schema_version
        computed_at = result.computed_at
        values = result.values
        result_warnings = list(result.warnings)
        result_insufficient = result.insufficient_data
        result_config = result.config_used

    # ------------------------------------------------------------------
    # Compose service-level warnings
    # ------------------------------------------------------------------
    service_warnings: list[str] = result_warnings
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
        schema_version=schema_version,
        therapist_attested=transcript.therapist_attested,
        extracted_at=computed_at,
        warnings=service_warnings,
        features=values,
        review_status=ReviewStatus.ready,
        insufficient_data=result_insufficient,
        provider_name=provider_name,
        config_used=result_config,
        speaker_mapping_id=mapping.mapping_id if mapping is not None else None,
        speaker_mapping_version=mapping.mapping_version if mapping is not None else None,
        attestation_id=versioned_results[0].attestation_id if versioned_results else None,
        attestation_version=versioned_results[0].attestation_version if versioned_results else None,
        chat_export_id=versioned_results[0].chat_export_id if versioned_results else None,
        chat_export_version=versioned_results[0].chat_export_version if versioned_results else None,
        tokenizer_profile_id=next((item.tokenizer_profile.profile_id for item in versioned_results if item.tokenizer_profile), None),
        tokenizer_profile_version=next((item.tokenizer_profile.profile_version for item in versioned_results if item.tokenizer_profile), None),
        tokenizer_profile_checksum_sha256=next((item.tokenizer_profile.profile_checksum_sha256 for item in versioned_results if item.tokenizer_profile), None),
        versioned_results=versioned_results,
    )
    return repo.create_feature_set(
        feature_set,
        actor_id="system",
        audit_action="features.extract",
        audit_message=(
            f"Language sample features extracted by {provider_name} "
            f"from reviewed transcript (schema: {schema_version})."
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
