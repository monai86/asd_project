"""Descriptive Reference Comparison engine for English child transcript features."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.feature_schema import FEATURES
from src.reference_task_types import normalize_task_type


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
DEFAULT_FEATURES_PATH = REFERENCE_DIR / "english_child_reference_features.csv"
DEFAULT_COHORTS_PATH = REFERENCE_DIR / "english_child_reference_cohorts.csv"
DEFAULT_CLAN_FEATURES_PATH = REFERENCE_DIR / "english_child_clan_features.csv"

REFERENCE_TERM = "Reference Comparison"
OK = "ok"
INSUFFICIENT_REFERENCE_DATA = "insufficient_reference_data"
CLAN_METRIC_SOURCE = "clan_kideval"

CLAN_METRICS: list[str] = [
    "kideval_mlu_utts",
    "kideval_freq_types",
    "kideval_freq_tokens",
    "kideval_freq_ttr",
    "kideval_vocd_score",
    "kideval_dss_utterances",
    "kideval_dss",
    "kideval_ipsyn_total",
]

SESSION_TYPE_TO_TASK_TYPE = {
    "free_play": "toyplay",
    "parent_child_interaction": "toyplay",
    "therapy_session": "toyplay",
    "structured_assessment": "narrative",
}

DIAGNOSTIC_WORDING_BLOCKLIST = {
    "diagnosis",
    "diagnostic",
    "validated clinical benchmark",
    "clinical benchmark",
    "norm",
    "risk estimate",
}


@dataclass(frozen=True)
class FeatureComparison:
    feature: str
    value: float | None
    percentile: float | None
    position: str
    q1: float | None
    median: float | None
    q3: float | None
    min: float | None
    max: float | None


@dataclass(frozen=True)
class ClanMetricComparison:
    metric: str
    value: float | None
    percentile: float | None
    position: str
    q1: float | None
    median: float | None
    q3: float | None
    min: float | None
    max: float | None
    reference_n: int
    metric_source: str


@dataclass(frozen=True)
class CohortComparison:
    group: str
    cohort_n: int
    confidence_flag: str
    corpora: str
    design_types: str
    feature_comparisons: list[FeatureComparison]
    clan_metric_comparisons: list[ClanMetricComparison]


@dataclass(frozen=True)
class ReferenceComparisonResult:
    status: str
    reference_term: str
    age_band_12mo: str
    task_type: str
    language: str
    warnings: list[str]
    cohorts: list[CohortComparison]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def age_band_12mo(age_months: Any) -> str:
    """Return a 12-month band label such as ``48-59``."""
    if age_months is None:
        return ""
    try:
        value = float(age_months)
    except (TypeError, ValueError):
        return ""
    if math.isnan(value):
        return ""
    lower = int(value // 12) * 12
    upper = lower + 11
    return f"{lower}-{upper}"


def resolve_task_type(*, session_type: str | None = None, task_type: str | None = None) -> str:
    """Resolve TalkBank task type, preferring explicit task_type over session_type."""
    if task_type:
        return normalize_task_type(task_type)
    if not session_type:
        return ""
    return SESSION_TYPE_TO_TASK_TYPE.get(session_type.strip(), "")


def _optional_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric):
        return None
    return numeric


def empirical_percentile(reference_values: pd.Series, value: float | None) -> float | None:
    """Return empirical percentile using weak ordering, rounded to 2 decimals."""
    if value is None:
        return None
    values = pd.to_numeric(reference_values, errors="coerce").dropna()
    if values.empty:
        return None
    percentile = (values <= value).sum() / len(values) * 100
    return round(float(percentile), 2)


def iqr_position(value: float | None, q1: float | None, q3: float | None) -> str:
    if value is None:
        return "missing"
    if q1 is None or q3 is None:
        return "missing"
    if value < q1:
        return "below_iqr"
    if value > q3:
        return "above_iqr"
    return "within_iqr"


def assert_descriptive_wording(payload: dict[str, Any]) -> None:
    """Guard public result wording from diagnostic/norm language."""
    text = str(payload).lower()
    blocked = [term for term in DIAGNOSTIC_WORDING_BLOCKLIST if term in text]
    if blocked:
        raise ValueError(f"Reference comparison output contains prohibited wording: {blocked}")


class ReferenceEngine:
    """Load reference CSVs and compare one feature set against matched cohorts."""

    def __init__(
        self,
        *,
        features_path: Path = DEFAULT_FEATURES_PATH,
        cohorts_path: Path = DEFAULT_COHORTS_PATH,
        clan_features_path: Path = DEFAULT_CLAN_FEATURES_PATH,
    ) -> None:
        self.features_path = Path(features_path)
        self.cohorts_path = Path(cohorts_path)
        self.clan_features_path = Path(clan_features_path)
        self.reference_features = pd.read_csv(self.features_path)
        self.reference_cohorts = pd.read_csv(self.cohorts_path)
        self.clan_features = self._load_optional_clan_features(self.clan_features_path)

    def compare(
        self,
        *,
        features: dict[str, Any],
        age_months: Any | None = None,
        session_type: str | None = None,
        task_type: str | None = None,
        language: str = "eng",
    ) -> ReferenceComparisonResult:
        resolved_age = age_months if age_months is not None else features.get("age_months")
        band = age_band_12mo(resolved_age)
        resolved_task_type = resolve_task_type(session_type=session_type, task_type=task_type)
        warnings: list[str] = []

        if not band:
            warnings.append("missing_age_band")
        if not resolved_task_type:
            warnings.append("missing_task_type")

        if not band or not resolved_task_type:
            return ReferenceComparisonResult(
                status=INSUFFICIENT_REFERENCE_DATA,
                reference_term=REFERENCE_TERM,
                age_band_12mo=band,
                task_type=resolved_task_type,
                language=language,
                warnings=warnings,
                cohorts=[],
            )

        feature_matches = self.reference_features[
            (self.reference_features["language"].astype(str) == language)
            & (self.reference_features["age_band_12mo"].astype(str) == band)
            & (self.reference_features["task_type"].astype(str) == resolved_task_type)
        ].copy()
        cohort_matches = self.reference_cohorts[
            (self.reference_cohorts["age_band_12mo"].astype(str) == band)
            & (self.reference_cohorts["task_type"].astype(str) == resolved_task_type)
        ].copy()
        clan_matches = self._matched_clan_rows(
            language=language,
            age_band=band,
            task_type=resolved_task_type,
        )

        if feature_matches.empty or cohort_matches.empty:
            warnings.append("no_matching_reference_cohort")
            return ReferenceComparisonResult(
                status=INSUFFICIENT_REFERENCE_DATA,
                reference_term=REFERENCE_TERM,
                age_band_12mo=band,
                task_type=resolved_task_type,
                language=language,
                warnings=warnings,
                cohorts=[],
            )

        cohorts: list[CohortComparison] = []
        for _, cohort_row in cohort_matches.sort_values("group").iterrows():
            group = str(cohort_row["group"])
            group_reference = feature_matches[feature_matches["group"].astype(str) == group]
            if group_reference.empty:
                continue

            confidence_flag = str(cohort_row.get("confidence_flag", ""))
            if confidence_flag == "low_n":
                warning = f"low_n:{band}|{resolved_task_type}|{group}"
                if warning not in warnings:
                    warnings.append(warning)

            feature_comparisons = [
                self._compare_feature(feature, features.get(feature), group_reference, cohort_row)
                for feature in FEATURES
            ]
            group_clan_reference = (
                clan_matches[clan_matches["group"].astype(str) == group]
                if not clan_matches.empty
                else pd.DataFrame()
            )
            clan_metric_comparisons = self._compare_clan_metrics(
                features=features,
                group_clan_reference=group_clan_reference,
                confidence_flag=confidence_flag,
            )
            cohorts.append(
                CohortComparison(
                    group=group,
                    cohort_n=int(cohort_row.get("cohort_n", len(group_reference))),
                    confidence_flag=confidence_flag,
                    corpora=str(cohort_row.get("corpora", "")),
                    design_types=str(cohort_row.get("design_types", "")),
                    feature_comparisons=feature_comparisons,
                    clan_metric_comparisons=clan_metric_comparisons,
                )
            )

        if not cohorts:
            warnings.append("no_matching_reference_group")
            return ReferenceComparisonResult(
                status=INSUFFICIENT_REFERENCE_DATA,
                reference_term=REFERENCE_TERM,
                age_band_12mo=band,
                task_type=resolved_task_type,
                language=language,
                warnings=warnings,
                cohorts=[],
            )

        result = ReferenceComparisonResult(
            status=OK,
            reference_term=REFERENCE_TERM,
            age_band_12mo=band,
            task_type=resolved_task_type,
            language=language,
            warnings=warnings,
            cohorts=cohorts,
        )
        assert_descriptive_wording(result.to_dict())
        return result

    @staticmethod
    def _load_optional_clan_features(path: Path) -> pd.DataFrame:
        if not path.exists() or path.stat().st_size == 0:
            return pd.DataFrame()
        return pd.read_csv(path)

    def _matched_clan_rows(
        self,
        *,
        language: str,
        age_band: str,
        task_type: str,
    ) -> pd.DataFrame:
        required_columns = {"language", "age_band_12mo", "task_type", "group"}
        if self.clan_features.empty or not required_columns.issubset(self.clan_features.columns):
            return pd.DataFrame()
        return self.clan_features[
            (self.clan_features["language"].astype(str) == language)
            & (self.clan_features["age_band_12mo"].astype(str) == age_band)
            & (self.clan_features["task_type"].astype(str) == task_type)
        ].copy()

    @staticmethod
    def _compare_feature(
        feature: str,
        raw_value: Any,
        group_reference: pd.DataFrame,
        cohort_row: pd.Series,
    ) -> FeatureComparison:
        value = _optional_float(raw_value)
        q1 = _optional_float(cohort_row.get(f"{feature}_q1"))
        median = _optional_float(cohort_row.get(f"{feature}_median"))
        q3 = _optional_float(cohort_row.get(f"{feature}_q3"))
        minimum = _optional_float(cohort_row.get(f"{feature}_min"))
        maximum = _optional_float(cohort_row.get(f"{feature}_max"))
        percentile = (
            empirical_percentile(group_reference[feature], value)
            if feature in group_reference
            else None
        )
        return FeatureComparison(
            feature=feature,
            value=value,
            percentile=percentile,
            position=iqr_position(value, q1, q3),
            q1=q1,
            median=median,
            q3=q3,
            min=minimum,
            max=maximum,
        )

    @staticmethod
    def _compare_clan_metrics(
        *,
        features: dict[str, Any],
        group_clan_reference: pd.DataFrame,
        confidence_flag: str,
    ) -> list[ClanMetricComparison]:
        if confidence_flag != OK or group_clan_reference.empty:
            return []

        comparisons: list[ClanMetricComparison] = []
        for metric in CLAN_METRICS:
            if metric not in group_clan_reference:
                continue
            reference_values = pd.to_numeric(group_clan_reference[metric], errors="coerce").dropna()
            reference_n = int(reference_values.count())
            if reference_n == 0:
                continue

            value = _optional_float(features.get(metric))
            q1 = float(reference_values.quantile(0.25))
            median = float(reference_values.median())
            q3 = float(reference_values.quantile(0.75))
            minimum = float(reference_values.min())
            maximum = float(reference_values.max())
            metric_source = CLAN_METRIC_SOURCE
            if "metric_source" in group_clan_reference:
                sources = [
                    str(item)
                    for item in group_clan_reference["metric_source"].dropna().unique()
                    if str(item)
                ]
                metric_source = ";".join(sorted(sources)) or CLAN_METRIC_SOURCE

            comparisons.append(
                ClanMetricComparison(
                    metric=metric,
                    value=value,
                    percentile=empirical_percentile(reference_values, value),
                    position=iqr_position(value, q1, q3),
                    q1=q1,
                    median=median,
                    q3=q3,
                    min=minimum,
                    max=maximum,
                    reference_n=reference_n,
                    metric_source=metric_source,
                )
            )
        return comparisons


def compare_reference(
    *,
    features: dict[str, Any],
    age_months: Any | None = None,
    session_type: str | None = None,
    task_type: str | None = None,
    language: str = "eng",
    features_path: Path = DEFAULT_FEATURES_PATH,
    cohorts_path: Path = DEFAULT_COHORTS_PATH,
    clan_features_path: Path = DEFAULT_CLAN_FEATURES_PATH,
) -> ReferenceComparisonResult:
    """Convenience wrapper for one-off Reference Comparison calls."""
    engine = ReferenceEngine(
        features_path=features_path,
        cohorts_path=cohorts_path,
        clan_features_path=clan_features_path,
    )
    return engine.compare(
        features=features,
        age_months=age_months,
        session_type=session_type,
        task_type=task_type,
        language=language,
    )
