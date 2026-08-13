"""Versioned boundary objects for scientific analysis work.

The contract carries opaque references and provenance, not auth claims,
organization policy, storage credentials, or clinical workflow decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping


ANALYSIS_CONTRACT_VERSION = "analysis-contract-v1"
_ALLOWED_VALUE_TYPES = (bool, int, float, str, type(None))


class AnalysisInputKind(str, Enum):
    """Scientific input accepted by the future analysis boundary."""

    AUDIO_ASSET = "audio_asset"
    REVIEWED_TRANSCRIPT = "reviewed_transcript"
    FEATURE_SET = "feature_set"


class AnalysisStatus(str, Enum):
    """Result states that keep unavailable work explicit and fail-closed."""

    COMPLETED = "completed"
    INSUFFICIENT_DATA = "insufficient_data"
    FAILED = "failed"


def _require_reference(value: str, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or any(character in value for character in "\r\n")
    ):
        raise ValueError(f"{field_name} must be a non-empty opaque reference without newlines.")


def _require_version(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty version.")


def _require_utc_timestamp(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("analyzed_at must be timezone-aware.")


@dataclass(frozen=True)
class AnalysisInput:
    """Opaque input reference submitted after API authorization is complete."""

    input_ref: str
    input_kind: AnalysisInputKind
    session_ref: str
    transcript_version: int | None = None
    content_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_reference(self.input_ref, "input_ref")
        _require_reference(self.session_ref, "session_ref")
        if self.transcript_version is not None and self.transcript_version < 1:
            raise ValueError("transcript_version must be positive when provided.")
        if self.content_sha256 is not None and len(self.content_sha256) != 64:
            raise ValueError("content_sha256 must be a 64-character digest when provided.")

    def to_dict(self) -> dict[str, object]:
        return {
            "input_ref": self.input_ref,
            "input_kind": self.input_kind.value,
            "session_ref": self.session_ref,
            "transcript_version": self.transcript_version,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class AnalysisRequest:
    """Scientific request envelope; policy and persistence stay outside it."""

    input: AnalysisInput
    pipeline_version: str
    feature_schema_version: str
    model_version: str | None = None
    contract_version: str = ANALYSIS_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_version(self.pipeline_version, "pipeline_version")
        _require_version(self.feature_schema_version, "feature_schema_version")
        if self.model_version is not None:
            _require_version(self.model_version, "model_version")
        if self.contract_version != ANALYSIS_CONTRACT_VERSION:
            raise ValueError(f"Unsupported analysis contract: {self.contract_version}")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "input": self.input.to_dict(),
            "pipeline_version": self.pipeline_version,
            "feature_schema_version": self.feature_schema_version,
            "model_version": self.model_version,
        }


@dataclass(frozen=True)
class AnalysisProvenance:
    """Required provenance attached to every analysis result."""

    pipeline_version: str
    feature_schema_version: str
    analyzed_at: datetime
    input_ref: str
    session_ref: str
    model_version: str | None = None

    def __post_init__(self) -> None:
        _require_version(self.pipeline_version, "pipeline_version")
        _require_version(self.feature_schema_version, "feature_schema_version")
        _require_reference(self.input_ref, "input_ref")
        _require_reference(self.session_ref, "session_ref")
        _require_utc_timestamp(self.analyzed_at)
        if self.model_version is not None:
            _require_version(self.model_version, "model_version")

    def to_dict(self) -> dict[str, object]:
        return {
            "pipeline_version": self.pipeline_version,
            "feature_schema_version": self.feature_schema_version,
            "model_version": self.model_version,
            "analyzed_at": self.analyzed_at.astimezone(timezone.utc).isoformat(),
            "input_ref": self.input_ref,
            "session_ref": self.session_ref,
        }


@dataclass(frozen=True)
class AnalysisResult:
    """Fail-closed scientific output with no diagnostic or policy fields."""

    status: AnalysisStatus
    provenance: AnalysisProvenance
    feature_values: Mapping[str, object] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    abstention_reason: str | None = None
    contract_version: str = ANALYSIS_CONTRACT_VERSION
    not_diagnostic: bool = True
    decision_support_only: bool = True

    def __post_init__(self) -> None:
        if self.contract_version != ANALYSIS_CONTRACT_VERSION:
            raise ValueError(f"Unsupported analysis contract: {self.contract_version}")
        if not self.not_diagnostic or not self.decision_support_only:
            raise ValueError("Analysis results must remain non-diagnostic decision support.")
        if self.status in {AnalysisStatus.INSUFFICIENT_DATA, AnalysisStatus.FAILED}:
            if not self.abstention_reason or not self.abstention_reason.strip():
                raise ValueError("Unavailable analysis results require an abstention_reason.")
            if self.feature_values:
                raise ValueError("Unavailable analysis results must not include feature values.")
        if self.status == AnalysisStatus.COMPLETED and self.abstention_reason:
            raise ValueError("Completed analysis results cannot include an abstention_reason.")
        for name, value in self.feature_values.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Feature names must be non-empty strings.")
            if not isinstance(value, _ALLOWED_VALUE_TYPES):
                raise ValueError(f"Feature '{name}' has a non-serializable value.")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "status": self.status.value,
            "provenance": self.provenance.to_dict(),
            "feature_values": dict(self.feature_values),
            "warnings": list(self.warnings),
            "abstention_reason": self.abstention_reason,
            "not_diagnostic": self.not_diagnostic,
            "decision_support_only": self.decision_support_only,
        }
