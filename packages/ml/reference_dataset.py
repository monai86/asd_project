"""Build deterministic, auditable rows for the ML reference dataset."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime
import hashlib
import json
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

_HASH_IDENTITY_COLUMNS = (
    "participant_id",
    "child",
    "file_id",
    "session_id",
)
_SOURCE_PRIORITY = {"combined": 0, "curated": 1}


@dataclass(frozen=True)
class CanonicalDatasetResult:
    rows: pd.DataFrame
    audit: pd.DataFrame
    dataset_hash: str


@dataclass(frozen=True)
class _CandidateRow:
    source_dataset: str
    source_priority: int
    raw_source_path: str
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
    def __init__(self, path: str, value: object):
        self.path = path
        self.type_name = (
            f"{type(value).__module__}.{type(value).__qualname__}"
        )
        super().__init__(
            f"Unsupported value type at {path}: {self.type_name}."
        )


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(result) if isinstance(result, bool) else False


def _normalize_text(value: str, *, casefold: bool = False) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    return normalized.casefold() if casefold else normalized


def _normalize_value(value: object, path: str) -> Any:
    if _is_missing(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        return float(value)
    if isinstance(value, str):
        return unicodedata.normalize("NFKC", value)
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [
            _normalize_value(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, Mapping):
        normalized_items = [
            (
                _normalize_value(key, f"{path}.<key>"),
                _normalize_value(item, f"{path}[value]"),
            )
            for key, item in value.items()
        ]
        normalized_items.sort(key=lambda pair: _json_bytes(pair[0]))
        return {"__mapping__": normalized_items}
    raise _UnsupportedValueType(path, value)


def _json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_payload(payload: object) -> str:
    return hashlib.sha256(_json_bytes(payload)).hexdigest()


def _normalized_row_content(row: pd.Series) -> dict[str, object]:
    content: dict[str, object] = {}
    for column, value in sorted(row.items(), key=lambda item: str(item[0])):
        column_name = str(column)
        content[column_name] = _normalize_value(value, column_name)
    return content


def _source_row_hash(hash_content: Mapping[str, object]) -> str:
    return _sha256_payload(
        {"domain": "canonical-source-row-v1", "row": hash_content}
    )


def _prevalidation_hash_content(
    normalized_content: Mapping[str, object],
) -> dict[str, object]:
    included_columns = set(_HASH_IDENTITY_COLUMNS) | {
        "corpus",
        "group",
        "age_months",
        "language",
        "task_type",
        "extractor_version",
        "feature_schema_version",
        *CANONICAL_FEATURE_COLUMNS,
    }
    return {
        column: normalized_content.get(column)
        for column in sorted(included_columns)
    }


def _canonical_hash_content(
    *,
    row: pd.Series,
    corpus: str,
    group: str,
    age_months: object,
    language: str,
    task_type: str,
    extractor_version: str,
    feature_schema_version: str,
    features: Mapping[str, object],
) -> dict[str, object]:
    return {
        "identity": {
            column: _identifier_text(row.get(column)) or None
            for column in _HASH_IDENTITY_COLUMNS
        },
        "canonical": {
            "corpus": corpus,
            "original_group": group,
            "age_months": age_months,
            "language": language,
            "task_type": task_type,
            "extractor_version": extractor_version,
            "feature_schema_version": feature_schema_version,
            "features": dict(features),
        },
    }


def _clean_text(value: object) -> str:
    if _is_missing(value):
        return ""
    if isinstance(value, str):
        return _normalize_text(value)
    if isinstance(value, (bool, Integral, Real, pd.Timestamp, datetime, date)):
        return _normalize_text(str(value))
    raise _UnsupportedValueType("text", value)


def _identifier_text(value: object) -> str:
    text = _clean_text(value)
    return _normalize_text(text, casefold=True) if text else ""


def _opaque_reference(domain: str, kind: str, value: str) -> str:
    return hashlib.sha256(
        f"{domain}:{kind}:{value}".encode("utf-8")
    ).hexdigest()


def _first_identifier(
    row: pd.Series,
    columns: tuple[str, ...],
) -> tuple[str, str]:
    for column in columns:
        value = _identifier_text(row.get(column))
        if value:
            return column, value
    return "", ""


def _raw_source_path(row: pd.Series) -> str:
    _, value = _first_identifier(row, ("source_path", "curated_path"))
    return value


def _source_reference(raw_source_path: str) -> str:
    if not raw_source_path:
        return ""
    digest = _opaque_reference("source", "path", raw_source_path)
    return f"source-{digest}"


def _participant_key(row: pd.Series, corpus: str) -> str:
    kind, value = _first_identifier(
        row,
        ("participant_id", "child", "file_id"),
    )
    if not value:
        return ""
    digest = _opaque_reference("participant", kind, value)
    return f"{corpus}:participant-{digest[:16]}"


def _session_key(
    row: pd.Series,
    raw_source_path: str,
    source_row_hash: str,
) -> str:
    if raw_source_path:
        kind, value = "source_path", raw_source_path
    else:
        kind, value = _first_identifier(row, ("file_id", "session_id"))
    if not value:
        kind, value = "content", source_row_hash
    digest = _opaque_reference("session", kind, value)
    return f"session-{digest[:16]}"


def _unsupported_row_hash(error: _UnsupportedValueType) -> str:
    return _sha256_payload(
        {
            "domain": "unsupported-source-row-v1",
            "path": error.path,
            "type": error.type_name,
        }
    )


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
) -> tuple[_CandidateRow | None, dict[str, str] | None]:
    try:
        raw_source_path = _raw_source_path(row)
        source_reference = _source_reference(raw_source_path)
        normalized_content = _normalized_row_content(row)
    except _UnsupportedValueType as exc:
        try:
            raw_source_path = _raw_source_path(row)
            source_reference = _source_reference(raw_source_path)
        except _UnsupportedValueType:
            source_reference = ""
        return None, _audit_entry(
            source_dataset=source_dataset,
            source_path=source_reference,
            source_row_hash=_unsupported_row_hash(exc),
            reason_code="unsupported_value_type",
            detail=str(exc),
        )

    prevalidation_hash = _source_row_hash(
        _prevalidation_hash_content(normalized_content)
    )
    corpus = _clean_text(row.get("corpus"))
    if not corpus:
        return None, _audit_entry(
            source_dataset=source_dataset,
            source_path=source_reference,
            source_row_hash=prevalidation_hash,
            reason_code="missing_corpus",
            detail="Source row has no nonblank corpus.",
        )

    participant_key = _participant_key(row, corpus)
    if not participant_key:
        return None, _audit_entry(
            source_dataset=source_dataset,
            source_path=source_reference,
            source_row_hash=prevalidation_hash,
            reason_code="missing_participant_key",
            detail="Source row has no participant_id, child, or file_id.",
        )

    try:
        group = normalize_original_group(row.get("group"))
    except ValueError:
        return None, _audit_entry(
            source_dataset=source_dataset,
            source_path=source_reference,
            source_row_hash=prevalidation_hash,
            reason_code="unsupported_group",
            detail="Source row has an unsupported group label.",
        )

    age_months = normalized_content.get("age_months")
    language = _clean_text(row.get("language"))
    task_type = _clean_text(row.get("task_type"))
    extractor_version = (
        _clean_text(row.get("extractor_version"))
        or "legacy-project-extractor"
    )
    feature_schema_version = (
        _clean_text(row.get("feature_schema_version"))
        or "reference-core-14-v1"
    )
    features = {
        feature: normalized_content.get(feature)
        for feature in CANONICAL_FEATURE_COLUMNS
    }
    row_hash = _source_row_hash(
        _canonical_hash_content(
            row=row,
            corpus=corpus,
            group=group,
            age_months=age_months,
            language=language,
            task_type=task_type,
            extractor_version=extractor_version,
            feature_schema_version=feature_schema_version,
            features=features,
        )
    )

    return (
        _CandidateRow(
            source_dataset=source_dataset,
            source_priority=_SOURCE_PRIORITY[source_dataset],
            raw_source_path=raw_source_path,
            source_path=source_reference,
            source_row_hash=row_hash,
            corpus=corpus,
            participant_key=participant_key,
            session_key=_session_key(row, raw_source_path, row_hash),
            original_group=group,
            presentation_group=normalize_presentation_group(group),
            age_months=age_months,
            language=language,
            task_type=task_type,
            extractor_version=extractor_version,
            feature_schema_version=feature_schema_version,
            features=features,
        ),
        None,
    )


def _candidate_priority(candidate: _CandidateRow) -> tuple[object, ...]:
    return (
        candidate.source_priority,
        candidate.raw_source_path,
        candidate.source_row_hash,
    )


def _deduplicate_candidates(
    candidates: list[_CandidateRow],
) -> tuple[list[_CandidateRow], list[dict[str, str]]]:
    kept_by_path: dict[str, _CandidateRow] = {}
    path_survivors: list[_CandidateRow] = []
    audit: list[dict[str, str]] = []

    for candidate in sorted(candidates, key=_candidate_priority):
        if (
            candidate.raw_source_path
            and candidate.raw_source_path in kept_by_path
        ):
            winner = kept_by_path[candidate.raw_source_path]
            audit.append(
                _audit_entry(
                    source_dataset=candidate.source_dataset,
                    source_path=candidate.source_path,
                    source_row_hash=candidate.source_row_hash,
                    reason_code="duplicate_source_row",
                    detail=(
                        "Duplicate opaque source reference; kept "
                        f"{winner.source_dataset} row "
                        f"{winner.source_row_hash[:12]}."
                    ),
                )
            )
            continue
        if candidate.raw_source_path:
            kept_by_path[candidate.raw_source_path] = candidate
        path_survivors.append(candidate)

    kept_hashes: dict[str, _CandidateRow] = {}
    survivors: list[_CandidateRow] = []
    for candidate in sorted(path_survivors, key=_candidate_priority):
        winner = kept_hashes.get(candidate.source_row_hash)
        if winner is not None and winner.source_dataset != candidate.source_dataset:
            audit.append(
                _audit_entry(
                    source_dataset=candidate.source_dataset,
                    source_path=candidate.source_path,
                    source_row_hash=candidate.source_row_hash,
                    reason_code="duplicate_row_hash",
                    detail="Duplicate normalized canonical row content.",
                )
            )
            continue
        kept_hashes.setdefault(candidate.source_row_hash, candidate)
        survivors.append(candidate)

    return survivors, audit


def _make_session_keys_unique(
    candidates: list[_CandidateRow],
) -> list[_CandidateRow]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.session_key] = counts.get(candidate.session_key, 0) + 1

    unique_candidates: list[_CandidateRow] = []
    for candidate in candidates:
        if counts[candidate.session_key] == 1:
            unique_candidates.append(candidate)
            continue
        digest = _opaque_reference(
            "session",
            "collision",
            f"{candidate.session_key}:{candidate.source_row_hash}",
        )
        unique_candidates.append(
            replace(candidate, session_key=f"session-{digest[:16]}")
        )
    return unique_candidates


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
) -> CanonicalDatasetResult:
    """Combine source tables into deterministic, privacy-safe reference rows."""
    candidates: list[_CandidateRow] = []
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
    candidates = _make_session_keys_unique(candidates)

    rows = _canonical_frame(candidates)
    audit = _audit_frame(audit_entries)
    return CanonicalDatasetResult(
        rows=rows,
        audit=audit,
        dataset_hash=_dataset_hash(rows),
    )
