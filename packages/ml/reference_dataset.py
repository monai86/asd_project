"""Build deterministic, auditable rows for the ML reference dataset."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import hmac
import json
import math
from numbers import Integral, Real
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
CANONICAL_FEATURE_COLUMNS = [
    feature for feature in FEATURES if feature not in CANONICAL_METADATA
]

AUDIT_COLUMNS = [
    "source_dataset",
    "source_path",
    "source_row_hash",
    "reason_code",
    "detail",
]

_IDENTITY_COLUMNS = (
    "participant_id",
    "child",
    "file_id",
    "session_id",
)
_PATH_COLUMNS = ("source_path", "curated_path")
_CANONICAL_INPUT_COLUMNS = (
    "corpus",
    "group",
    "age_months",
    "language",
    "task_type",
    "extractor_version",
    "feature_schema_version",
    *CANONICAL_FEATURE_COLUMNS,
)
_AUDIT_PROJECTION_COLUMNS = (
    *_IDENTITY_COLUMNS,
    *_PATH_COLUMNS,
    *_CANONICAL_INPUT_COLUMNS,
)
_SOURCE_PRIORITY = {"combined": 0, "curated": 1}


@dataclass(frozen=True)
class CanonicalDatasetResult:
    rows: pd.DataFrame
    audit: pd.DataFrame
    dataset_hash: str
    pseudonymization_key_version: str


@dataclass(frozen=True)
class _CandidateRow:
    source_dataset: str
    source_priority: int
    source_ordinal: int
    normalized_source_path: str
    source_path: str
    source_row_hash: str
    corpus: str
    participant_key: str
    session_key: str
    original_group: str
    presentation_group: str
    age_months: object
    language: str
    task_type: str
    extractor_version: str
    feature_schema_version: str
    features: Mapping[str, object]


class _UnsupportedValueType(ValueError):
    reason_code = "unsupported_value_type"

    def __init__(self, field: str, value: object):
        self.field = field
        self.type_name = (
            f"{type(value).__module__}.{type(value).__qualname__}"
        )
        super().__init__(
            f"Unsupported value type in {field}: {self.type_name}."
        )


class _InvalidNumericValue(ValueError):
    reason_code = "invalid_numeric_value"

    def __init__(self, field: str):
        self.field = field
        self.type_name = "non_finite_number"
        super().__init__(f"Non-finite numeric value in {field}.")


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    if hasattr(result, "__len__"):
        return False
    return bool(result)


def _normalize_text(value: str, *, casefold: bool = False) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    return normalized.casefold() if casefold else normalized


def _normalize_path(value: object, field: str) -> str:
    if _is_missing(value):
        return ""
    if not isinstance(value, str):
        raise _UnsupportedValueType(field, value)
    return value.strip().replace("\\", "/")


def _normalize_value(value: object, field: str) -> Any:
    if _is_missing(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        if not math.isfinite(number):
            raise _InvalidNumericValue(field)
        return number
    if isinstance(value, str):
        return unicodedata.normalize("NFKC", value)
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [
            _normalize_value(item, f"{field}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, Mapping):
        items = [
            (
                _normalize_value(key, f"{field}.<key>"),
                _normalize_value(item, f"{field}[value]"),
            )
            for key, item in value.items()
        ]
        items.sort(key=lambda pair: _json_bytes(pair[0]))
        return {"__mapping__": items}
    raise _UnsupportedValueType(field, value)


def _normalize_scalar_text(
    value: object,
    field: str,
    *,
    casefold: bool = False,
) -> str:
    normalized = _normalize_value(value, field)
    if normalized is None:
        return ""
    if not isinstance(normalized, (bool, int, float, str)):
        raise _UnsupportedValueType(field, value)
    return _normalize_text(str(normalized), casefold=casefold)


def _json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _opaque_reference(
    domain: str,
    raw: str,
    key: bytes,
) -> str:
    digest = hmac.new(
        key,
        domain.encode("utf-8") + b"\0" + raw.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{domain}-{digest}"


def _keyed_hash(domain: str, payload: object, key: bytes) -> str:
    reference = _opaque_reference(
        domain,
        _json_bytes(payload).decode("utf-8"),
        key,
    )
    return reference.removeprefix(f"{domain}-")


def _identity_values(row: pd.Series) -> dict[str, str]:
    return {
        column: _normalize_scalar_text(
            row.get(column),
            column,
            casefold=True,
        )
        for column in _IDENTITY_COLUMNS
    }


def _normalized_source_path(row: pd.Series) -> str:
    for column in _PATH_COLUMNS:
        value = _normalize_path(row.get(column), column)
        if value:
            return value
    return ""


def _participant_key(
    corpus: str,
    identities: Mapping[str, str],
    key: bytes,
) -> str:
    for column in ("participant_id", "child", "file_id"):
        value = identities[column]
        if value:
            reference = _opaque_reference(
                "participant",
                f"{column}\0{value}",
                key,
            )
            return f"{corpus}:{reference}"
    return ""


def _session_key(
    *,
    normalized_source_path: str,
    identities: Mapping[str, str],
    source_row_hash: str,
    key: bytes,
) -> str:
    if normalized_source_path:
        raw = f"source_path\0{normalized_source_path}"
    elif identities["file_id"]:
        raw = f"file_id\0{identities['file_id']}"
    elif identities["session_id"]:
        raw = f"session_id\0{identities['session_id']}"
    else:
        raw = f"content\0{source_row_hash}"
    return _opaque_reference("session", raw, key)


def _canonical_values(row: pd.Series) -> dict[str, object]:
    return {
        column: _normalize_value(row.get(column), column)
        for column in _CANONICAL_INPUT_COLUMNS
    }


def _safe_audit_projection(
    row: pd.Series,
    *,
    source_dataset: str,
    reason_code: str,
    rejection_field: str,
    rejection_type: str,
) -> dict[str, object]:
    projection: dict[str, object] = {"source_dataset": source_dataset}
    for column in _AUDIT_PROJECTION_COLUMNS:
        try:
            if column in _PATH_COLUMNS:
                projection[column] = _normalize_path(row.get(column), column)
            elif column in _IDENTITY_COLUMNS:
                projection[column] = _normalize_scalar_text(
                    row.get(column),
                    column,
                    casefold=True,
                )
            else:
                projection[column] = _normalize_value(
                    row.get(column),
                    column,
                )
        except (_UnsupportedValueType, _InvalidNumericValue) as exc:
            projection[column] = {
                "rejected_type": exc.type_name,
                "rejected_reason": exc.reason_code,
            }
    projection["rejection"] = {
        "field": rejection_field,
        "type": rejection_type,
        "reason": reason_code,
    }
    return projection


def _audit_entry(
    *,
    row: pd.Series,
    source_dataset: str,
    source_path: str,
    reason_code: str,
    detail: str,
    rejection_field: str,
    rejection_type: str,
    key: bytes,
) -> dict[str, str]:
    projection = _safe_audit_projection(
        row,
        source_dataset=source_dataset,
        reason_code=reason_code,
        rejection_field=rejection_field,
        rejection_type=rejection_type,
    )
    return {
        "source_dataset": source_dataset,
        "source_path": source_path,
        "source_row_hash": _keyed_hash("audit", projection, key),
        "reason_code": reason_code,
        "detail": detail,
    }


def _rejection_audit(
    *,
    row: pd.Series,
    source_dataset: str,
    normalized_source_path: str,
    error: _UnsupportedValueType | _InvalidNumericValue,
    key: bytes,
) -> dict[str, str]:
    source_reference = (
        _opaque_reference("source", normalized_source_path, key)
        if normalized_source_path
        else ""
    )
    return _audit_entry(
        row=row,
        source_dataset=source_dataset,
        source_path=source_reference,
        reason_code=error.reason_code,
        detail=str(error),
        rejection_field=error.field,
        rejection_type=error.type_name,
        key=key,
    )


def _candidate_from_row(
    row: pd.Series,
    source_dataset: str,
    source_ordinal: int,
    key: bytes,
) -> tuple[_CandidateRow | None, dict[str, str] | None]:
    normalized_source_path = ""
    try:
        normalized_source_path = _normalized_source_path(row)
        identities = _identity_values(row)
        canonical = _canonical_values(row)
    except (_UnsupportedValueType, _InvalidNumericValue) as exc:
        return None, _rejection_audit(
            row=row,
            source_dataset=source_dataset,
            normalized_source_path=normalized_source_path,
            error=exc,
            key=key,
        )

    source_reference = (
        _opaque_reference("source", normalized_source_path, key)
        if normalized_source_path
        else ""
    )
    corpus = _normalize_scalar_text(canonical["corpus"], "corpus")
    if not corpus:
        return None, _audit_entry(
            row=row,
            source_dataset=source_dataset,
            source_path=source_reference,
            reason_code="missing_corpus",
            detail="Source row has no nonblank corpus.",
            rejection_field="corpus",
            rejection_type="missing",
            key=key,
        )

    participant_key = _participant_key(corpus, identities, key)
    if not participant_key:
        return None, _audit_entry(
            row=row,
            source_dataset=source_dataset,
            source_path=source_reference,
            reason_code="missing_participant_key",
            detail="Source row has no participant_id, child, or file_id.",
            rejection_field="participant_id|child|file_id",
            rejection_type="missing",
            key=key,
        )

    group_value = _normalize_scalar_text(canonical["group"], "group")
    try:
        group = normalize_original_group(group_value)
    except ValueError:
        return None, _audit_entry(
            row=row,
            source_dataset=source_dataset,
            source_path=source_reference,
            reason_code="unsupported_group",
            detail="Source row has an unsupported group label.",
            rejection_field="group",
            rejection_type="unsupported",
            key=key,
        )

    language = _normalize_scalar_text(canonical["language"], "language")
    task_type = _normalize_scalar_text(canonical["task_type"], "task_type")
    extractor_version = (
        _normalize_scalar_text(
            canonical["extractor_version"],
            "extractor_version",
        )
        or "legacy-project-extractor"
    )
    feature_schema_version = (
        _normalize_scalar_text(
            canonical["feature_schema_version"],
            "feature_schema_version",
        )
        or "reference-core-14-v1"
    )
    features = {
        feature: canonical[feature]
        for feature in CANONICAL_FEATURE_COLUMNS
    }
    hash_content = {
        "path": normalized_source_path or None,
        "identity": identities,
        "canonical": {
            "corpus": corpus,
            "original_group": group,
            "age_months": canonical["age_months"],
            "language": language,
            "task_type": task_type,
            "extractor_version": extractor_version,
            "feature_schema_version": feature_schema_version,
            "features": features,
        },
    }
    source_row_hash = _keyed_hash("row", hash_content, key)

    return (
        _CandidateRow(
            source_dataset=source_dataset,
            source_priority=_SOURCE_PRIORITY[source_dataset],
            source_ordinal=source_ordinal,
            normalized_source_path=normalized_source_path,
            source_path=source_reference,
            source_row_hash=source_row_hash,
            corpus=corpus,
            participant_key=participant_key,
            session_key=_session_key(
                normalized_source_path=normalized_source_path,
                identities=identities,
                source_row_hash=source_row_hash,
                key=key,
            ),
            original_group=group,
            presentation_group=normalize_presentation_group(group),
            age_months=canonical["age_months"],
            language=language,
            task_type=task_type,
            extractor_version=extractor_version,
            feature_schema_version=feature_schema_version,
            features=features,
        ),
        None,
    )


def _candidate_priority(candidate: _CandidateRow) -> tuple[int, int]:
    return candidate.source_priority, candidate.source_ordinal


def _deduplicate_candidates(
    candidates: list[_CandidateRow],
) -> tuple[list[_CandidateRow], list[dict[str, str]]]:
    kept_paths: set[str] = set()
    kept_hashes: set[str] = set()
    survivors: list[_CandidateRow] = []
    audit: list[dict[str, str]] = []

    for candidate in sorted(candidates, key=_candidate_priority):
        if candidate.source_row_hash in kept_hashes:
            audit.append(
                {
                    "source_dataset": candidate.source_dataset,
                    "source_path": candidate.source_path,
                    "source_row_hash": candidate.source_row_hash,
                    "reason_code": "duplicate_row_hash",
                    "detail": "Duplicate normalized canonical row content.",
                }
            )
            continue
        if (
            candidate.normalized_source_path
            and candidate.normalized_source_path in kept_paths
        ):
            audit.append(
                {
                    "source_dataset": candidate.source_dataset,
                    "source_path": candidate.source_path,
                    "source_row_hash": candidate.source_row_hash,
                    "reason_code": "duplicate_source_row",
                    "detail": "Duplicate opaque source reference.",
                }
            )
            continue
        if candidate.normalized_source_path:
            kept_paths.add(candidate.normalized_source_path)
        kept_hashes.add(candidate.source_row_hash)
        survivors.append(candidate)

    return survivors, audit


def _canonical_frame(candidates: list[_CandidateRow]) -> pd.DataFrame:
    ordered = sorted(
        candidates,
        key=lambda candidate: (
            candidate.corpus,
            candidate.participant_key,
            candidate.session_key,
            candidate.source_row_hash,
        ),
    )
    records = [
        {
            "source_dataset": candidate.source_dataset,
            "source_path": candidate.source_path,
            "source_row_hash": candidate.source_row_hash,
            "corpus": candidate.corpus,
            "participant_key": candidate.participant_key,
            "session_key": candidate.session_key,
            "original_group": candidate.original_group,
            "presentation_group": candidate.presentation_group,
            "age_months": candidate.age_months,
            "language": candidate.language,
            "task_type": candidate.task_type,
            "extractor_version": candidate.extractor_version,
            "feature_schema_version": candidate.feature_schema_version,
            **candidate.features,
        }
        for candidate in ordered
    ]
    return pd.DataFrame(
        records,
        columns=CANONICAL_METADATA + CANONICAL_FEATURE_COLUMNS,
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
    *,
    pseudonymization_key: bytes,
    pseudonymization_key_version: str = "v1",
) -> CanonicalDatasetResult:
    """Combine source tables into deterministic, privacy-safe reference rows."""
    if not isinstance(pseudonymization_key, bytes) or not pseudonymization_key:
        raise ValueError("pseudonymization_key must be non-empty bytes")

    candidates: list[_CandidateRow] = []
    audit_entries: list[dict[str, str]] = []
    for source_dataset, frame in (
        ("combined", combined),
        ("curated", curated),
    ):
        for source_ordinal, (_, row) in enumerate(frame.iterrows()):
            candidate, audit_entry = _candidate_from_row(
                row,
                source_dataset,
                source_ordinal,
                pseudonymization_key,
            )
            if audit_entry is not None:
                audit_entries.append(audit_entry)
            elif candidate is not None:
                candidates.append(candidate)

    candidates, duplicate_audit = _deduplicate_candidates(candidates)
    audit_entries.extend(duplicate_audit)
    rows = _canonical_frame(candidates)
    audit = _audit_frame(audit_entries)
    return CanonicalDatasetResult(
        rows=rows,
        audit=audit,
        dataset_hash=_dataset_hash(rows),
        pseudonymization_key_version=pseudonymization_key_version,
    )
