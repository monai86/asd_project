"""Build descriptive Reference Cohort CSVs from curated English child transcripts."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.chat_feature_extractor import extract_chat_features, normalize_group, read_chat  # noqa: E402
from src.feature_schema import FEATURES  # noqa: E402
from packages.ml.reference_contracts import evaluate_support  # noqa: E402
from src.reference_task_types import normalize_task_type  # noqa: E402


MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "english_child_transcript_manifest.csv"
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
FEATURES_PATH = REFERENCE_DIR / "english_child_reference_features.csv"
COHORTS_PATH = REFERENCE_DIR / "english_child_reference_cohorts.csv"
QC_PATH = REFERENCE_DIR / "english_child_reference_qc.csv"

SEX_VALUES = {"MALE", "FEMALE", "M", "F"}
PATH_GROUP_CODES = {"ASD", "DD", "TD", "TYP", "NT", "CONTROL", "SLI", "HL", "LT"}

METADATA_COLUMNS = [
    "transcript_uid",
    "source_path",
    "curated_path",
    "bank",
    "corpus",
    "download_date",
    "sha256",
    "language",
    "design_type",
    "task_type",
    "group_type",
    "group",
    "sex",
    "age_months_source",
    "age_months_source_detail",
    "age_band_12mo",
    "participant_key",
    "participant_key_source",
    "participant_verified",
    "child_utterance_count",
    "child_token_count",
]

QC_COLUMNS = ["qc_scope", "source_path", "cohort_key", "qc_status", "reason", "detail"]

KNOWN_UNRESOLVED_AGE_PATHS = {
    "data/raw/talkbank/CHILDES/ENNI/download_2026-05-31/TD/B/523.cha": (
        "ENNI TD/B/523.cha has no child age in the CHAT @ID header. "
        "Do not copy the SLI sidecar age for ID 523 because that sidecar row maps to SLI-A."
    ),
}


@dataclass(frozen=True)
class ChatMetadata:
    language: str
    design_type: str
    task_type: str
    group_type: str
    group_header: str
    sex: str


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _display_path(path: Path, root: Path = PROJECT_ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _resolve_path(value: str, project_root: Path = PROJECT_ROOT) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def resolve_transcript_path(row: dict[str, str], project_root: Path = PROJECT_ROOT) -> Path:
    """Return the available transcript path, preferring the original source."""
    source = _resolve_path(row.get("source_path", ""), project_root)
    if source.exists():
        return source
    curated_value = row.get("curated_path") or ""
    if curated_value:
        curated = _resolve_path(curated_value, project_root)
        if curated.exists():
            return curated
    return source


def split_types(types_value: object) -> tuple[str, str, str]:
    parts = [part.strip() for part in str(types_value or "").split(",")]
    parts = [part for part in parts if part]
    design_type = parts[0] if len(parts) >= 1 else ""
    task_type = normalize_task_type(parts[1]) if len(parts) >= 2 else ""
    group_type = ""
    if len(parts) >= 3:
        group_type = normalize_group(parts[2]) or parts[2].upper()
    return design_type, task_type, group_type


def _child_participant(reader):
    headers = reader.headers()
    if not headers:
        return None
    for participant in headers[0].participants:
        if participant.code == "CHI":
            return participant
    return None


def parse_chat_metadata(path: Path) -> ChatMetadata:
    reader = read_chat(path)
    headers = reader.headers()
    header = headers[0] if headers else None
    languages = getattr(header, "languages", []) if header else []
    language = ",".join(languages) if isinstance(languages, list) else str(languages or "")
    design_type, task_type, group_type = split_types(getattr(header, "types", "") if header else "")
    child = _child_participant(reader)
    group_header = normalize_group(getattr(child, "group", None)) or ""
    sex = getattr(child, "sex", None) or ""
    return ChatMetadata(
        language=language,
        design_type=design_type,
        task_type=task_type,
        group_type=group_type,
        group_header=group_header,
        sex=sex,
    )


def infer_group_from_path(path_value: str) -> str:
    for part in Path(path_value).parts:
        normalized = normalize_group(part)
        if normalized in PATH_GROUP_CODES:
            return normalized
    return ""


def choose_group(metadata: ChatMetadata, source_path: str) -> str:
    if metadata.group_header and metadata.group_header.upper() not in SEX_VALUES:
        return metadata.group_header
    path_group = infer_group_from_path(source_path)
    if path_group:
        return path_group
    return metadata.group_type


def age_band_12mo(age_months: object) -> str:
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


def known_unresolved_age_detail(source_path: str) -> str:
    normalized_source = Path(source_path).as_posix()
    for known_path, detail in KNOWN_UNRESOLVED_AGE_PATHS.items():
        if normalized_source == known_path or normalized_source.endswith(f"/{known_path}"):
            return detail
    return ""


def resolve_age_months(features: dict[str, object], source_path: str) -> tuple[object, str, str]:
    """Return age plus an auditable source for reference cohort matching."""
    age_months = features.get("age_months")
    if age_band_12mo(age_months):
        return age_months, "chat_header", "@ID child age"

    unresolved_detail = known_unresolved_age_detail(source_path)
    if unresolved_detail:
        return age_months, "known_unresolved", unresolved_detail

    new_england = re.search(r"/NewEngland/download_[^/]+/(14|20|32|60)(?:/|$)", source_path)
    if new_england:
        age = float(new_england.group(1))
        return age, "official_path", f"NewEngland age folder {new_england.group(1)}"

    rescorla = re.search(r"/Rescorla/download_[^/]+/(?:LT|TD)/(36|48|60|108|156)(?:/|$)", source_path)
    if rescorla:
        age = float(rescorla.group(1))
        return age, "official_path", f"Rescorla age folder {rescorla.group(1)}"

    return age_months, "missing", "No child age in CHAT header or supported official path fallback."


def transcript_uid(row: dict[str, str]) -> str:
    sha = row.get("sha256", "")
    corpus = row.get("corpus", "unknown")
    stem = Path(row.get("source_path", "")).stem or "transcript"
    return f"{corpus}:{stem}:{sha[:12] if sha else 'nohash'}"


def participant_key(row: dict[str, str]) -> tuple[str, str, bool]:
    """Return an auditable participant grouping key.

    New manifests may supply a verified participant identifier. Older
    manifests do not, so they conservatively fall back to the transcript UID
    rather than guessing that an age/task folder represents one child.
    """
    corpus = str(row.get("corpus") or "unknown").strip()
    explicit = str(row.get("participant_id") or "").strip()
    if explicit:
        return f"{corpus}:{explicit}", "manifest_participant_id", True
    return transcript_uid(row), "transcript_uid_fallback", False


def load_manifest_rows(manifest_path: Path) -> list[dict[str, str]]:
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_feature_rows(
    manifest_rows: Iterable[dict[str, str]],
    *,
    project_root: Path = PROJECT_ROOT,
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    feature_rows: list[dict[str, object]] = []
    qc_rows: list[dict[str, str]] = []

    for manifest_row in manifest_rows:
        if not _truthy(manifest_row.get("analysis_ready")):
            continue

        source_path = manifest_row.get("source_path", "")
        transcript_path = resolve_transcript_path(manifest_row, project_root)
        if not transcript_path.exists():
            qc_rows.append(
                {
                    "qc_scope": "transcript",
                    "source_path": source_path,
                    "cohort_key": "",
                    "qc_status": "fail",
                    "reason": "missing_transcript_file",
                    "detail": str(transcript_path),
                }
            )
            continue

        try:
            features = extract_chat_features(transcript_path)
            metadata = parse_chat_metadata(transcript_path)
        except Exception as exc:  # noqa: BLE001
            qc_rows.append(
                {
                    "qc_scope": "transcript",
                    "source_path": source_path,
                    "cohort_key": "",
                    "qc_status": "fail",
                    "reason": "feature_extraction_error",
                    "detail": str(exc),
                }
            )
            continue

        if features is None:
            qc_rows.append(
                {
                    "qc_scope": "transcript",
                    "source_path": source_path,
                    "cohort_key": "",
                    "qc_status": "fail",
                    "reason": "feature_extraction_skipped",
                    "detail": "",
                }
            )
            continue

        group = choose_group(metadata, source_path)
        resolved_age, age_source, age_source_detail = resolve_age_months(features, source_path)
        features["age_months"] = resolved_age
        band = age_band_12mo(resolved_age)

        if not band:
            reason = (
                "known_unresolved_age_months"
                if age_source == "known_unresolved"
                else "missing_age_months"
            )
            qc_rows.append(
                {
                    "qc_scope": "transcript",
                    "source_path": source_path,
                    "cohort_key": "",
                    "qc_status": "warn",
                    "reason": reason,
                    "detail": (
                        age_source_detail
                        if age_source == "known_unresolved"
                        else "Feature row retained; excluded from age-band cohort summary."
                    ),
                }
            )
        if not metadata.task_type:
            qc_rows.append(
                {
                    "qc_scope": "transcript",
                    "source_path": source_path,
                    "cohort_key": "",
                    "qc_status": "warn",
                    "reason": "missing_task_type",
                    "detail": "Feature row retained; excluded from task cohort summary.",
                }
            )
        if not group:
            qc_rows.append(
                {
                    "qc_scope": "transcript",
                    "source_path": source_path,
                    "cohort_key": "",
                    "qc_status": "warn",
                    "reason": "missing_group",
                    "detail": "Feature row retained; excluded from group cohort summary.",
                }
            )

        participant, participant_source, participant_verified = participant_key(
            manifest_row
        )
        feature_row: dict[str, object] = {
            "transcript_uid": transcript_uid(manifest_row),
            "source_path": source_path,
            "curated_path": manifest_row.get("curated_path", ""),
            "bank": manifest_row.get("bank", ""),
            "corpus": manifest_row.get("corpus", ""),
            "download_date": manifest_row.get("download_date", ""),
            "sha256": manifest_row.get("sha256", ""),
            "language": metadata.language or manifest_row.get("languages_raw", ""),
            "design_type": metadata.design_type,
            "task_type": metadata.task_type,
            "group_type": metadata.group_type,
            "group": group,
            "sex": metadata.sex or features.get("sex") or "",
            "age_months_source": age_source,
            "age_months_source_detail": age_source_detail,
            "age_band_12mo": band,
            "participant_key": participant,
            "participant_key_source": participant_source,
            "participant_verified": participant_verified,
            "child_utterance_count": int(manifest_row.get("child_utterance_count") or 0),
            "child_token_count": int(manifest_row.get("child_token_count") or 0),
        }
        for feature in FEATURES:
            feature_row[feature] = features.get(feature)
        feature_rows.append(feature_row)

    return feature_rows, qc_rows


def build_cohort_rows(features_df: pd.DataFrame) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    if features_df.empty:
        return [], []

    eligible = features_df[
        (features_df["age_band_12mo"].astype(str) != "")
        & (features_df["task_type"].astype(str) != "")
        & (features_df["group"].astype(str) != "")
    ].copy()
    if eligible.empty:
        return [], []

    rows: list[dict[str, object]] = []
    qc_rows: list[dict[str, str]] = []
    grouped = eligible.groupby(["age_band_12mo", "task_type", "group"], dropna=False, sort=True)
    for (band, task_type, group), cohort in grouped:
        verified = cohort[cohort["participant_verified"].astype(bool)]
        participant_count = int(verified["participant_key"].nunique())
        corpus_count = int(verified["corpus"].nunique())
        support = evaluate_support(participant_count, corpus_count)
        cohort_n = participant_count
        key = f"{band}|{task_type}|{group}"
        confidence_flag = "ok" if support.supported else "low_support"
        row: dict[str, object] = {
            "age_band_12mo": band,
            "task_type": task_type,
            "group": group,
            "cohort_n": cohort_n,
            "participant_count": participant_count,
            "session_count": int(len(cohort)),
            "confidence_flag": confidence_flag,
            "supported": support.supported,
            "reason_code": support.reason_code or "",
            "corpus_count": corpus_count,
            "corpora": ";".join(sorted(str(item) for item in cohort["corpus"].dropna().unique())),
            "design_types": ";".join(sorted(str(item) for item in cohort["design_type"].dropna().unique())),
        }
        for feature in FEATURES:
            values = pd.to_numeric(cohort[feature], errors="coerce").dropna()
            if support.supported:
                row[f"{feature}_n"] = int(values.count())
                row[f"{feature}_mean"] = values.mean() if not values.empty else ""
                row[f"{feature}_sd"] = values.std() if len(values) > 1 else ""
                row[f"{feature}_median"] = values.median() if not values.empty else ""
                row[f"{feature}_q1"] = values.quantile(0.25) if not values.empty else ""
                row[f"{feature}_q3"] = values.quantile(0.75) if not values.empty else ""
                row[f"{feature}_min"] = values.min() if not values.empty else ""
                row[f"{feature}_max"] = values.max() if not values.empty else ""
            else:
                row[f"{feature}_n"] = 0
                row[f"{feature}_mean"] = ""
                row[f"{feature}_sd"] = ""
                row[f"{feature}_median"] = ""
                row[f"{feature}_q1"] = ""
                row[f"{feature}_q3"] = ""
                row[f"{feature}_min"] = ""
                row[f"{feature}_max"] = ""
        rows.append(row)

        if not support.supported:
            qc_rows.append(
                {
                    "qc_scope": "cohort",
                    "source_path": "",
                    "cohort_key": key,
                    "qc_status": "warn",
                    "reason": support.reason_code or "insufficient_reference_data",
                    "detail": (
                        f"participant_count={participant_count};"
                        f"session_count={len(cohort)};"
                        f"corpus_count={corpus_count}"
                    ),
                }
            )

    return rows, qc_rows


def build_reference_csvs(
    *,
    manifest_path: Path = MANIFEST_PATH,
    reference_dir: Path = REFERENCE_DIR,
    project_root: Path = PROJECT_ROOT,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    manifest_rows = load_manifest_rows(manifest_path)
    feature_rows, qc_rows = build_feature_rows(manifest_rows, project_root=project_root)
    feature_columns = METADATA_COLUMNS + FEATURES
    features_df = pd.DataFrame(feature_rows, columns=feature_columns)
    cohort_rows, cohort_qc_rows = build_cohort_rows(features_df)
    qc_rows.extend(cohort_qc_rows)
    cohorts_df = pd.DataFrame(cohort_rows)
    qc_df = pd.DataFrame(qc_rows, columns=QC_COLUMNS)

    reference_dir.mkdir(parents=True, exist_ok=True)
    features_df.to_csv(reference_dir / FEATURES_PATH.name, index=False)
    cohorts_df.to_csv(reference_dir / COHORTS_PATH.name, index=False)
    qc_df.to_csv(reference_dir / QC_PATH.name, index=False)
    return features_df, cohorts_df, qc_df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--reference-dir", type=Path, default=REFERENCE_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features_df, cohorts_df, qc_df = build_reference_csvs(
        manifest_path=args.manifest,
        reference_dir=args.reference_dir,
    )
    print(f"Saved: {_display_path(args.reference_dir / FEATURES_PATH.name)} ({len(features_df)} rows)")
    print(f"Saved: {_display_path(args.reference_dir / COHORTS_PATH.name)} ({len(cohorts_df)} rows)")
    print(f"Saved: {_display_path(args.reference_dir / QC_PATH.name)} ({len(qc_df)} rows)")


if __name__ == "__main__":
    main()
