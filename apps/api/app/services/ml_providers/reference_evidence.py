from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.schemas.clinical import (
    AssociatedFeatureEvidence,
    EvidenceAvailability,
    PatternEvidence,
    ProfileEvidence,
)
from app.services.ml_providers.base import (
    BaseMLProvider,
    MLProviderAvailability,
    MLProviderContext,
    MLProviderResult,
)
from app.services.ml_providers.reference_feature_adapter import (
    RUNTIME_TO_CANONICAL,
    adapt_runtime_features,
)


ARTIFACT_TYPE = "ml_reference_evidence"
FEATURE_SCHEMA_VERSION = "reference-core-14-v1"
SUPPORTED_LANGUAGE = "eng"
SUPPORTED_RUNTIME_FEATURE_SCHEMAS = {"features-basic-v1"}
SUPPORTED_PROFILE_CODES = {"TD", "DD", "ASD", "LT", "STI", "HL"}
SESSION_TYPE_TO_TASK_TYPE = {
    "free_play": "toyplay",
    "parent_child_interaction": "toyplay",
    "therapy_session": "toyplay",
    "structured_assessment": "narrative",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _optional_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _is_true(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def iqr_position(value: float, q1: float, q3: float) -> str:
    """Classify a value against a reference IQR (inclusive band boundaries).

    Single source of truth for below/within/above positions so the ML profile
    evidence review, AI-assisted Progress Summary, and printed report always
    classify a value the same way.
    """
    if value < q1:
        return "below_iqr"
    if value > q3:
        return "above_iqr"
    return "within_iqr"


def _age_band_12mo(age_months: int | None) -> str:
    if age_months is None or age_months < 0:
        return ""
    lower = int(age_months // 12) * 12
    return f"{lower}-{lower + 11}"


def _language_code(language: str) -> str:
    normalized = str(language or "").strip().casefold()
    return "eng" if normalized in {"eng", "en", "english"} else normalized


def _language_codes(language: str) -> list[str]:
    normalized = str(language or "").replace(";", ",")
    return [
        _language_code(item)
        for item in normalized.split(",")
        if str(item).strip()
    ]


def _task_type(context: MLProviderContext) -> str:
    if context.task_type:
        return str(context.task_type).strip().casefold().replace(" ", "_")
    return SESSION_TYPE_TO_TASK_TYPE.get(str(context.session_type).strip().casefold(), "")


class ReferenceEvidenceProvider(BaseMLProvider):
    provider_id = "reference_evidence_review"
    provider_name = "ReferenceEvidenceProvider"
    provider_version = "0.9.0"

    def __init__(self, artifact_dir: str | Path | None = None) -> None:
        configured = (
            artifact_dir
            or os.getenv("THERAPIST_APP_V2_REFERENCE_ARTIFACT_DIR")
            or get_settings().reference_artifact_dir
        )
        self.artifact_dir = Path(configured)
        self._manifest: dict[str, Any] | None = None
        self._cells: list[dict[str, str]] | None = None
        self._availability: MLProviderAvailability | None = None

    def check_availability(self) -> MLProviderAvailability:
        if self._availability is not None:
            return self._availability
        try:
            self._load_and_validate()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self._availability = MLProviderAvailability(False, str(exc))
        else:
            self._availability = MLProviderAvailability(True)
        return self._availability

    def get_model_metadata(self) -> dict:
        return {
            "provider_type": "local_descriptive_reference_evidence",
            "network_calls": False,
            "default_config": {},
            "artifact_dir": str(self.artifact_dir),
            "not_diagnostic": True,
        }

    def predict(
        self,
        features,
        context: MLProviderContext,
        config: dict | None = None,
    ) -> MLProviderResult:
        del config
        availability = self.check_availability()
        if not availability:
            return self._unavailable_result(
                state="system_unavailable",
                reason_code="artifact_manifest_invalid",
                message=f"Reference evidence is unavailable. {availability.reason}".strip(),
            )

        assert self._manifest is not None
        assert self._cells is not None
        language_codes = _language_codes(context.language)
        language = language_codes[0] if len(language_codes) == 1 else ""
        if len(set(language_codes)) > 1:
            return self._unavailable_result(
                state="unsupported_scope",
                reason_code="unsupported_code_switching",
                message="Mixed-language samples are outside the current reference evidence scope.",
            )
        if language != SUPPORTED_LANGUAGE:
            return self._unavailable_result(
                state="unsupported_scope",
                reason_code="unsupported_language",
                message="Reference evidence is currently limited to English language samples.",
            )

        band = _age_band_12mo(context.age_months)
        task_type = _task_type(context)
        if not band or not task_type:
            return self._unavailable_result(
                state="input_action_required",
                reason_code="missing_reference_context",
                message="Age and task metadata are required for reference evidence.",
            )

        adapted = adapt_runtime_features(features)
        if adapted.schema_version not in SUPPORTED_RUNTIME_FEATURE_SCHEMAS:
            return self._unavailable_result(
                state="system_unavailable",
                reason_code="feature_schema_incompatible",
                message="The runtime feature schema is not compatible with this reference evidence provider.",
            )
        matching = [
            row
            for row in self._cells
            if row.get("language") == language
            and row.get("age_band_12mo") == band
            and row.get("task_type") == task_type
            and row.get("original_group") in SUPPORTED_PROFILE_CODES
        ]
        profile_evidence = [
            self._profile_evidence(row, adapted.values, adapted.missing_required)
            for row in matching
        ]
        gate1 = self._manifest.get("gate1") or {}
        if gate1.get("status") == "research_only":
            pattern = PatternEvidence(
                status="not_available",
                availability=EvidenceAvailability(
                    state="system_unavailable",
                    reason_code="gate1_research_only",
                    message="Additional pattern evidence remains research-only and is not active in therapist workflow.",
                    workflow_can_continue=True,
                    next_step="Continue transcript and feature review using available descriptive evidence.",
                ),
            )
        else:
            pattern = PatternEvidence(
                status="not_available",
                availability=EvidenceAvailability(
                    state="system_unavailable",
                    reason_code="pattern_model_not_activated",
                    message="No promoted pattern model is active for this evidence package.",
                    workflow_can_continue=True,
                    next_step="Continue transcript and feature review using available descriptive evidence.",
                ),
            )

        return MLProviderResult(
            status="completed",
            pattern_evidence=pattern,
            profile_evidence=profile_evidence,
            artifact_provenance={
                "artifact_type": str(self._manifest["artifact_type"]),
                "artifact_version": str(self._manifest["artifact_version"]),
                "dataset_hash": str(self._manifest.get("dataset_hash", "")),
                "feature_schema_version": str(self._manifest["feature_schema_version"]),
            },
            warnings=(
                ["No matching supported or unsupported reference profiles were found for this age/task cell."]
                if not matching
                else []
            ),
            limitations=[
                "Reference evidence is descriptive and based on public English-language corpora.",
                "No diagnostic classification, probability, or ranking output is produced.",
            ],
        )

    def td_reference_band(
        self,
        age_months: int | None,
        session_type: str | None,
    ) -> dict[str, Any] | None:
        """
        Return the typical-development (TD) IQR band for an age/task cell.

        Used by read-only surfaces (e.g. the dashboard trend chart) to overlay
        the reference range a child's trajectory can be compared against.
        Returns None when the artifact is unavailable or no supported TD row
        matches the age and session type.
        """
        if not self.check_availability() or self._cells is None:
            return None
        band = _age_band_12mo(age_months)
        task_type = SESSION_TYPE_TO_TASK_TYPE.get(
            str(session_type or "").strip().casefold(), ""
        )
        if not band or not task_type:
            return None
        matching = [
            row
            for row in self._cells
            if row.get("language") == SUPPORTED_LANGUAGE
            and row.get("age_band_12mo") == band
            and row.get("task_type") == task_type
            and row.get("original_group") == "TD"
            and _is_true(row.get("supported"))
        ]
        if not matching:
            return None
        row = matching[0]
        features: dict[str, dict[str, float]] = {}
        for canonical_name in RUNTIME_TO_CANONICAL.values():
            q1 = _optional_float(row.get(f"{canonical_name}_q1"))
            median = _optional_float(row.get(f"{canonical_name}_median"))
            q3 = _optional_float(row.get(f"{canonical_name}_q3"))
            if q1 is not None and median is not None and q3 is not None:
                features[canonical_name] = {"q1": q1, "median": median, "q3": q3}
        if not features:
            return None
        return {"age_band": band, "task_type": task_type, "features": features}

    def readiness_issues(
        self,
        features,
        context: MLProviderContext,
    ) -> list[tuple[str, str]]:
        issues: list[tuple[str, str]] = []
        if features.schema_version not in SUPPORTED_RUNTIME_FEATURE_SCHEMAS:
            issues.append(
                (
                    "feature_schema_incompatible",
                    "The extracted feature schema is not compatible with reference evidence.",
                )
            )
        band = _age_band_12mo(context.age_months)
        if not band:
            issues.append(("missing_age_band", "A valid child age is required."))
        task_type = _task_type(context)
        if not task_type:
            code = "missing_task_type" if not context.session_type else "unsupported_task_type"
            issues.append((code, "A supported session task type is required."))
        if self.check_availability() and band and self._cells is not None:
            covered_bands = {
                row.get("age_band_12mo", "")
                for row in self._cells
                if row.get("language") == SUPPORTED_LANGUAGE
            }
            if band not in covered_bands:
                issues.append(
                    (
                        "age_outside_reference_coverage",
                        "The child age is outside the available reference evidence coverage.",
                    )
                )
        return issues

    def _load_and_validate(self) -> None:
        manifest_path = self.artifact_dir / "manifest.json"
        if not manifest_path.is_file():
            raise ValueError(f"Reference artifact manifest is missing: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("artifact_type") != ARTIFACT_TYPE:
            raise ValueError("Reference artifact manifest has an unsupported artifact type.")
        if manifest.get("supported_language") != SUPPORTED_LANGUAGE:
            raise ValueError("Reference artifact manifest has an unsupported language.")
        if manifest.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
            raise ValueError("Reference artifact feature schema is incompatible.")
        files = manifest.get("files")
        if not isinstance(files, dict) or "reference_cells" not in files:
            raise ValueError("Reference artifact manifest does not declare reference cells.")
        for name, metadata in files.items():
            if not isinstance(metadata, dict):
                raise ValueError(f"Invalid file metadata for {name}.")
            filename = metadata.get("filename")
            expected_hash = metadata.get("sha256")
            if not filename or not expected_hash:
                raise ValueError(f"Missing filename or checksum for {name}.")
            path = self.artifact_dir / str(filename)
            if not path.is_file():
                raise ValueError(f"Declared reference artifact file is missing: {filename}")
            if _sha256_file(path) != expected_hash:
                raise ValueError(f"Checksum mismatch for reference artifact file: {filename}")

        cells_path = self.artifact_dir / str(files["reference_cells"]["filename"])
        with cells_path.open(encoding="utf-8", newline="") as handle:
            cells = list(csv.DictReader(handle))
        required_columns = {
            "language",
            "age_band_12mo",
            "task_type",
            "original_group",
            "presentation_group",
            "participant_count",
            "corpus_count",
            "supported",
            "reason_code",
            *{
                f"{feature}_{stat}"
                for feature in RUNTIME_TO_CANONICAL.values()
                for stat in ("q1", "median", "q3")
            },
        }
        if not cells or not required_columns.issubset(cells[0]):
            raise ValueError("Reference cells file is empty or has an incompatible schema.")
        self._manifest = manifest
        self._cells = cells

    def _profile_evidence(
        self,
        row: dict[str, str],
        values: dict[str, float | int],
        missing_required: list[str],
    ) -> ProfileEvidence:
        supported = _is_true(row.get("supported"))
        participant_count = int(float(row.get("participant_count") or 0))
        corpus_count = int(float(row.get("corpus_count") or 0))
        if not supported:
            return ProfileEvidence(
                profile_code=row["original_group"],
                presentation_group=row["presentation_group"],
                status="not_available",
                availability=EvidenceAvailability(
                    state="insufficient_reference_data",
                    reason_code=row.get("reason_code") or "insufficient_reference_data",
                    message="This public-corpus profile does not have enough independent support for comparison.",
                    workflow_can_continue=True,
                    next_step="Continue therapist review without this profile comparison.",
                ),
                participant_count=participant_count,
                corpus_count=corpus_count,
            )

        associated = self._associated_features(row, values)
        limited = bool(missing_required)
        return ProfileEvidence(
            profile_code=row["original_group"],
            presentation_group=row["presentation_group"],
            status="limited_comparison" if limited else "comparable_patterns_observed",
            availability=EvidenceAvailability(
                state="available",
                reason_code="mapped_feature_subset_only" if limited else None,
                message=(
                    "A limited descriptive comparison is available from exact-mapped features."
                    if limited
                    else "A descriptive comparison is available for this profile."
                ),
                workflow_can_continue=True,
                next_step="Review associated features in transcript context.",
            ),
            participant_count=participant_count,
            corpus_count=corpus_count,
            associated_features=associated,
        )

    @staticmethod
    def _associated_features(
        row: dict[str, str],
        values: dict[str, float | int],
    ) -> list[AssociatedFeatureEvidence]:
        candidates: list[tuple[float, AssociatedFeatureEvidence]] = []
        for canonical_name in RUNTIME_TO_CANONICAL.values():
            value = _optional_float(values.get(canonical_name))
            q1 = _optional_float(row.get(f"{canonical_name}_q1"))
            median = _optional_float(row.get(f"{canonical_name}_median"))
            q3 = _optional_float(row.get(f"{canonical_name}_q3"))
            if value is None or q1 is None or q3 is None:
                continue
            position = iqr_position(value, q1, q3)
            if position == "within_iqr":
                continue
            if position == "below_iqr":
                distance = q1 - value
            else:
                distance = value - q3
            scale = max(q3 - q1, 1e-9)
            candidates.append(
                (
                    distance / scale,
                    AssociatedFeatureEvidence(
                        feature_name=canonical_name,
                        observed_value=value,
                        position=position,
                        q1=q1,
                        median=median,
                        q3=q3,
                        caveat="Descriptive public-corpus comparison; interpret with transcript context.",
                    ),
                )
            )
        candidates.sort(key=lambda item: (-item[0], item[1].feature_name))
        return [item for _, item in candidates[:3]]

    @staticmethod
    def _unavailable_result(
        *,
        state: str,
        reason_code: str,
        message: str,
    ) -> MLProviderResult:
        return MLProviderResult(
            status="unavailable",
            pattern_evidence=PatternEvidence(
                status="not_available",
                availability=EvidenceAvailability(
                    state=state,
                    reason_code=reason_code,
                    message=message,
                    workflow_can_continue=True,
                    next_step="Continue the therapist review without reference evidence.",
                ),
            ),
            limitations=["Reference evidence was not used for this result."],
        )


def runtime_td_reference_band(
    age_months: int | None,
    session_type: str | None,
) -> dict[str, Any] | None:
    """
    Typical-development (TD) reference band keyed by runtime feature names.

    Shared by report drafting and AI-assisted review so every surface (dashboard
    chart, printed report, Findings) speaks the same reference language. Returns
    None when the artifact is unavailable or no supported TD cell matches, so
    callers degrade silently to their current behavior.
    """
    provider = ReferenceEvidenceProvider()
    band = provider.td_reference_band(age_months, session_type)
    if not band:
        return None
    canonical_to_runtime = {
        canonical: runtime_name
        for runtime_name, canonical in RUNTIME_TO_CANONICAL.items()
    }
    runtime_features: dict[str, dict[str, float]] = {}
    for canonical, stats in band.get("features", {}).items():
        runtime_name = canonical_to_runtime.get(canonical)
        if runtime_name is not None:
            runtime_features[runtime_name] = stats
    if not runtime_features:
        return None
    return {
        "age_band": band["age_band"],
        "task_type": band["task_type"],
        "features": runtime_features,
    }
