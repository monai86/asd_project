"""Build deterministic, auditable rows for the ML reference dataset."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from typing import Any
import unicodedata

import pandas as pd

from packages.ml.reference_contracts import (
    original_group as normalize_original_group,
    presentation_group as normalize_presentation_group,
)
from src.feature_schema import FEATURES


CANONICAL_METADATA = [
    "source_dataset",
    "source_path",
    "source_row_hash",
    "corpus",
    "participant_key",
    "session_key",
    "original_group",
    "presentation_group",
    "age_months",
    "language",
    "task_type",
    "extractor_version",
    "feature_schema_version",
]

AUDIT_COLUMNS = [
    "source_dataset",
    "source_path",
    "source_row_hash",
    "reason_code",
    "detail",
]

_SOURCE_PRIORITY = {"combined": 0, "curated": 1}


@dataclass(frozen=True)
class CanonicalDatasetResult:
    rows: pd.DataFrame
    audit: pd.DataFrame
    dataset_hash: str


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(result) if isinstance(result, bool) else False


def _clean_text(value: object) -> str:
    if _is_missing(value):
        return ""
    return str(value).strip()


def _normalize_hash_value(value: object) -> Any:
    if _is_missing(value):
        return None
    if isinstance(value, dict):
        return {
            str(key): _normalize_hash_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_hash_value(item) for item in value]
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return _normalize_hash_value(value.item())
        except (TypeError, ValueError):
            pass
    return value


def _source_row_payload(row: pd.Series, source_dataset: str) -> dict[str, object]:
    return {
        "source_dataset": source_dataset,
        "row": {
            str(column): _normalize_hash_value(value)
            for column, value in row.items()
        },
    }


def _source_row_hash(row: pd.Series, source_dataset: str) -> str:
    payload = _source_row_payload(row, source_dataset)
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _first_nonblank(row: pd.Series, columns: tuple[str, ...]) -> str:
    for column in columns:
        value = _clean_text(row.get(column))
        if value:
            return value
    return ""


def _participant_component(row: pd.Series) -> str:
    participant_id = _clean_text(row.get("participant_id"))
    if participant_id:
        return participant_id

    child = _clean_text(row.get("child"))
    if child:
        normalized_child = " ".join(
            unicodedata.normalize("NFKC", child).casefold().split()
        )
        digest = hashlib.sha256(normalized_child.encode("utf-8")).hexdigest()
        return f"child-{digest[:16]}"

    return _clean_text(row.get("file_id"))


def _audit_entry(
    *,
    source_dataset: str,
    source_path: str,
    source_row_hash: str,
    reason_code: str,
    detail: str,
) -> dict[str, str]:
    return {
        "source_dataset": source_dataset,
        "source_path": source_path,
        "source_row_hash": source_row_hash,
        "reason_code": reason_code,
        "detail": detail,
    }


def _candidate_from_row(
    row: pd.Series,
    source_dataset: str,
) -> tuple[dict[str, object] | None, dict[str, str] | None]:
    source_path = _clean_text(row.get("source_path"))
    row_hash = _source_row_hash(row, source_dataset)
    corpus = _clean_text(row.get("corpus"))
    if not corpus:
        return None, _audit_entry(
            source_dataset=source_dataset,
            source_path=source_path,
            source_row_hash=row_hash,
            reason_code="missing_corpus",
            detail="Source row has no nonblank corpus.",
        )

    participant = _participant_component(row)
    if not participant:
        return None, _audit_entry(
            source_dataset=source_dataset,
            source_path=source_path,
            source_row_hash=row_hash,
            reason_code="missing_participant_key",
            detail="Source row has no participant_id, child, or file_id.",
        )

    try:
        group = normalize_original_group(row.get("group"))
    except ValueError as exc:
        return None, _audit_entry(
            source_dataset=source_dataset,
            source_path=source_path,
            source_row_hash=row_hash,
            reason_code="unsupported_group",
            detail=str(exc),
        )

    participant_key = f"{corpus}:{participant}"
    session_key = _first_nonblank(row, ("source_path", "file_id", "session_id"))
    if not session_key:
        session_key = f"{source_dataset}:{participant_key}:{row_hash[:12]}"

    return (
        {
            "source_dataset": source_dataset,
            "source_priority": _SOURCE_PRIORITY[source_dataset],
            "source_path": source_path,
            "source_row_hash": row_hash,
            "corpus": corpus,
            "participant_key": participant_key,
            "session_key": session_key,
            "original_group": group,
            "presentation_group": normalize_presentation_group(group),
            "age_months": row.get("age_months"),
            "language": _clean_text(row.get("language")),
            "task_type": _clean_text(row.get("task_type")),
            "extractor_version": _clean_text(row.get("extractor_version"))
            or "legacy-project-extractor",
            "feature_schema_version": _clean_text(
                row.get("feature_schema_version")
            )
            or "reference-core-14-v1",
            "features": {
                feature: None if _is_missing(row.get(feature)) else row.get(feature)
                for feature in FEATURES
            },
        },
        None,
    )


def _candidate_priority(candidate: dict[str, object]) -> tuple[object, ...]:
    return (
        candidate["source_priority"],
        candidate["source_path"],
        candidate["source_row_hash"],
    )


def _deduplicate_candidates(
    candidates: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    kept_by_path: dict[str, dict[str, object]] = {}
    path_survivors: list[dict[str, object]] = []
    audit: list[dict[str, str]] = []

    for candidate in sorted(candidates, key=_candidate_priority):
        source_path = str(candidate["source_path"])
        if source_path and source_path in kept_by_path:
            winner = kept_by_path[source_path]
            audit.append(
                _audit_entry(
                    source_dataset=str(candidate["source_dataset"]),
                    source_path=source_path,
                    source_row_hash=str(candidate["source_row_hash"]),
                    reason_code="duplicate_source_row",
                    detail=(
                        "Duplicate nonblank source_path; kept "
                        f"{winner['source_dataset']} row "
                        f"{str(winner['source_row_hash'])[:12]}."
                    ),
                )
            )
            continue
        if source_path:
            kept_by_path[source_path] = candidate
        path_survivors.append(candidate)

    kept_hashes: set[str] = set()
    survivors: list[dict[str, object]] = []
    for candidate in sorted(path_survivors, key=_candidate_priority):
        row_hash = str(candidate["source_row_hash"])
        if row_hash in kept_hashes:
            audit.append(
                _audit_entry(
                    source_dataset=str(candidate["source_dataset"]),
                    source_path=str(candidate["source_path"]),
                    source_row_hash=row_hash,
                    reason_code="duplicate_source_row",
                    detail="Duplicate normalized source row hash.",
                )
            )
            continue
        kept_hashes.add(row_hash)
        survivors.append(candidate)

    return survivors, audit


def _make_session_keys_unique(candidates: list[dict[str, object]]) -> None:
    counts: dict[str, int] = {}
    for candidate in candidates:
        session_key = str(candidate["session_key"])
        counts[session_key] = counts.get(session_key, 0) + 1

    for candidate in candidates:
        session_key = str(candidate["session_key"])
        if counts[session_key] > 1:
            candidate["session_key"] = (
                f"{session_key}:{str(candidate['source_row_hash'])[:12]}"
            )


def _canonical_frame(candidates: list[dict[str, object]]) -> pd.DataFrame:
    ordered = sorted(
        candidates,
        key=lambda candidate: (
            str(candidate["corpus"]),
            str(candidate["participant_key"]),
            str(candidate["session_key"]),
            str(candidate["source_row_hash"]),
        ),
    )
    metadata = pd.DataFrame(
        [
            {column: candidate[column] for column in CANONICAL_METADATA}
            for candidate in ordered
        ],
        columns=CANONICAL_METADATA,
    )
    features = pd.DataFrame(
        [candidate["features"] for candidate in ordered],
        columns=FEATURES,
    )
    return pd.concat(
        [metadata.reset_index(drop=True), features.reset_index(drop=True)],
        axis=1,
    )


def _audit_frame(entries: list[dict[str, str]]) -> pd.DataFrame:
    audit = pd.DataFrame(entries, columns=AUDIT_COLUMNS)
    if audit.empty:
        return audit
    return audit.sort_values(
        by=AUDIT_COLUMNS,
        kind="mergesort",
        ignore_index=True,
    )


def _dataset_hash(rows: pd.DataFrame) -> str:
    serialized = rows.to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_canonical_reference_rows(
    combined: pd.DataFrame,
    curated: pd.DataFrame,
) -> CanonicalDatasetResult:
    """Combine legacy source tables into canonical auditable reference rows."""
    candidates: list[dict[str, object]] = []
    audit_entries: list[dict[str, str]] = []

    for source_dataset, frame in (
        ("combined", combined),
        ("curated", curated),
    ):
        for _, row in frame.iterrows():
            candidate, audit_entry = _candidate_from_row(row, source_dataset)
            if audit_entry is not None:
                audit_entries.append(audit_entry)
            elif candidate is not None:
                candidates.append(candidate)

    candidates, duplicate_audit = _deduplicate_candidates(candidates)
    audit_entries.extend(duplicate_audit)
    _make_session_keys_unique(candidates)

    rows = _canonical_frame(candidates)
    audit = _audit_frame(audit_entries)
    return CanonicalDatasetResult(
        rows=rows,
        audit=audit,
        dataset_hash=_dataset_hash(rows),
    )
