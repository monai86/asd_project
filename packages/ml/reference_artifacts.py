"""Build descriptive reference cells from canonical, privacy-safe rows."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from packages.ml.reference_contracts import (
    evaluate_support,
    presentation_group,
)
from src.feature_schema import FEATURES


CELL_KEY = [
    "language",
    "age_band_12mo",
    "task_type",
    "original_group",
]


def age_band_12mo(value: object) -> str:
    """Return a stable 12-month age band or an empty string."""
    if value is None:
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(numeric) or numeric < 0:
        return ""
    lower = int(numeric // 12) * 12
    return f"{lower}-{lower + 11}"


def _numeric_series(frame: pd.DataFrame, feature: str) -> pd.Series:
    if feature not in frame:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame[feature], errors="coerce").dropna()


def _distribution(values: pd.Series) -> dict[str, int | float | None]:
    if values.empty:
        return {
            "n": 0,
            "mean": None,
            "sd": None,
            "median": None,
            "q1": None,
            "q3": None,
            "min": None,
            "max": None,
        }
    return {
        "n": int(values.count()),
        "mean": float(values.mean()),
        "sd": float(values.std()) if len(values) > 1 else None,
        "median": float(values.median()),
        "q1": float(values.quantile(0.25)),
        "q3": float(values.quantile(0.75)),
        "min": float(values.min()),
        "max": float(values.max()),
    }


def _empty_distribution() -> dict[str, int | None]:
    return {
        "n": 0,
        "mean": None,
        "sd": None,
        "median": None,
        "q1": None,
        "q3": None,
        "min": None,
        "max": None,
    }


def build_reference_cells(canonical_rows: pd.DataFrame) -> pd.DataFrame:
    """Summarize independently supported age/task/language/profile cells.

    Unsupported cells retain participant/corpus support metadata, but their
    feature distributions are intentionally empty so downstream consumers
    cannot accidentally calculate or display reference positions.
    """
    output_columns = [
        *CELL_KEY,
        "presentation_group",
        "participant_count",
        "session_count",
        "corpus_count",
        "corpora",
        "supported",
        "reason_code",
        *[
            f"{feature}_{stat}"
            for feature in FEATURES
            for stat in ("n", "mean", "sd", "median", "q1", "q3", "min", "max")
        ],
    ]
    if canonical_rows.empty:
        return pd.DataFrame(columns=output_columns)

    rows = canonical_rows.copy()
    rows["age_band_12mo"] = rows["age_months"].map(age_band_12mo)
    eligible = rows[
        (rows["language"].astype(str).str.strip() != "")
        & (rows["age_band_12mo"] != "")
        & (rows["task_type"].astype(str).str.strip() != "")
        & (rows["original_group"].astype(str).str.strip() != "")
    ].copy()
    if eligible.empty:
        return pd.DataFrame(columns=output_columns)

    records: list[dict[str, Any]] = []
    grouped = eligible.groupby(CELL_KEY, dropna=False, sort=True)
    for (language, band, task_type, group), cell in grouped:
        participant_count = int(cell["participant_key"].nunique())
        corpus_count = int(cell["corpus"].nunique())
        support = evaluate_support(participant_count, corpus_count)
        record: dict[str, Any] = {
            "language": str(language),
            "age_band_12mo": str(band),
            "task_type": str(task_type),
            "original_group": str(group),
            "presentation_group": presentation_group(group),
            "participant_count": participant_count,
            "session_count": int(len(cell)),
            "corpus_count": corpus_count,
            "corpora": ";".join(
                sorted(str(value) for value in cell["corpus"].dropna().unique())
            ),
            "supported": support.supported,
            "reason_code": support.reason_code or "",
        }
        for feature in FEATURES:
            distribution = (
                _distribution(_numeric_series(cell, feature))
                if support.supported
                else _empty_distribution()
            )
            for stat, value in distribution.items():
                record[f"{feature}_{stat}"] = value
        records.append(record)

    return (
        pd.DataFrame(records, columns=output_columns)
        .sort_values(CELL_KEY, kind="mergesort", ignore_index=True)
    )
