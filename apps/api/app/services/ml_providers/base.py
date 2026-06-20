from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.schemas.clinical import (
    FeatureSet,
    PatternEvidence,
    ProfileEvidence,
    ReviewCue,
)


@dataclass(frozen=True)
class MLProviderAvailability:
    available: bool
    reason: str = ""

    def __bool__(self) -> bool:
        return self.available


@dataclass(frozen=True)
class MLProviderResult:
    status: str
    cues: list[ReviewCue] = field(default_factory=list)
    pattern_evidence: PatternEvidence | None = None
    profile_evidence: list[ProfileEvidence] = field(default_factory=list)
    artifact_provenance: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MLProviderContext:
    case_id: str
    session_id: str
    transcript_id: str
    age_months: int | None
    language: str
    session_type: str
    task_type: str | None


class BaseMLProvider(ABC):
    provider_id: str
    provider_name: str
    provider_version: str

    @abstractmethod
    def check_availability(self) -> MLProviderAvailability: ...

    @abstractmethod
    def get_model_metadata(self) -> dict: ...

    @abstractmethod
    def predict(
        self,
        features: FeatureSet,
        context: MLProviderContext,
        config: dict | None = None,
    ) -> MLProviderResult: ...
