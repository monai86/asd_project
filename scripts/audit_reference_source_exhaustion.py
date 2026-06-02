"""Audit whether a low-count Reference Cohort bucket has usable local source rows.

The audit keeps short samples visible as counts only. It does not relax the
Reference Cohort analysis-ready policy and does not write feature previews for
short samples.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_reference_cohorts import (  # noqa: E402
    age_band_12mo,
    choose_group,
    parse_chat_metadata,
    resolve_age_months,
    resolve_transcript_path,
)
from src.chat_feature_extractor import extract_chat_features  # noqa: E402

REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "english_child_transcript_manifest.csv"
FEATURES_PATH = REFERENCE_DIR / "english_child_reference_features.csv"
CLAN_FEATURES_PATH = REFERENCE_DIR / "english_child_clan_features.csv"
COVERAGE_PATH = REFERENCE_DIR / "english_child_reference_coverage.csv"
AUDIT_PATH = REFERENCE_DIR / "english_child_source_exhaustion_audit.csv"

AUDIT_COLUMNS = [
    "language",
    "age_band_12mo",
    "task_type",
    "group",
    "triage_bucket",
    "target_corpus",
    "coverage_feature_rows",
    "coverage_clan_rows",
    "coverage_cohort_n",
    "source_transcript_rows",
    "analysis_ready_source_rows",
    "short_sample_source_rows",
    "feature_matched_source_rows",
    "clan_matched_source_rows",
    "missing_feature_rows",
    "missing_clan_rows",
    "audit_status",
    "audit_action",
]

AUDIT_STATUSES = {
    "needs_manifest_rebuild",
    "needs_feature_rebuild",
    "needs_clan_rebuild",
    "policy_exhausted_keep_low_confidence",
    "no_local_target_source_keep_low_confidence",
}

AUDIT_KEY_COLUMNS = [
    "language",
    "age_band_12mo",
    "task_type",
    "group",
    "triage_bucket",
    "target_corpus",
]


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, keep_default_na=False)


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _clean(value: object) -> str:
    return str(value or "").strip()


def _cell_key(row: pd.Series | dict[str, object]) -> tuple[str, str, str, str]:
    return (
        _clean(row.get("language") or "eng"),
        _clean(row.get("age_band_12mo")),
        _clean(row.get("task_type")),
        _clean(row.get("group")),
    )


def _source_path_set(df: pd.DataFrame, key: tuple[str, str, str, str], target_corpus: str) -> set[str]:
    if df.empty:
        return set()
    required = {"source_path", "corpus", "age_band_12mo", "task_type", "group"}
    if not required.issubset(df.columns):
        return set()
    language, age_band, task_type, group = key
    subset = df[
        (df["corpus"].astype(str) == target_corpus)
        & (df["age_band_12mo"].astype(str) == age_band)
        & (df["task_type"].astype(str) == task_type)
        & (df["group"].astype(str) == group)
    ]
    if "language" in subset.columns:
        subset = subset[subset["language"].astype(str).replace("", "eng") == language]
    return {str(path) for path in subset["source_path"].dropna() if str(path)}


def _derive_manifest_cell(row: pd.Series, *, project_root: Path = PROJECT_ROOT) -> tuple[str, str, str, str]:
    if {"age_band_12mo", "task_type", "group"}.issubset(row.index):
        return _cell_key(row)

    transcript_path = resolve_transcript_path(row.to_dict(), project_root)
    if not transcript_path.exists():
        return ("eng", "", "", "")

    features = extract_chat_features(transcript_path) or {}
    metadata = parse_chat_metadata(transcript_path)
    resolved_age, _age_source, _age_detail = resolve_age_months(features, row.get("source_path", ""))
    return (
        metadata.language or _clean(row.get("languages_raw")) or "eng",
        age_band_12mo(resolved_age),
        metadata.task_type,
        choose_group(metadata, _clean(row.get("source_path"))),
    )


def _manifest_rows_by_key(
    manifest_df: pd.DataFrame,
    *,
    target_corpus: str,
    project_root: Path = PROJECT_ROOT,
) -> dict[tuple[str, str, str, str], dict[str, set[str] | int]]:
    by_key: dict[tuple[str, str, str, str], dict[str, set[str] | int]] = {}
    if manifest_df.empty:
        return by_key

    corpus_rows = manifest_df[manifest_df["corpus"].astype(str) == target_corpus]
    for _, row in corpus_rows.iterrows():
        if not _truthy(row.get("eligible_english_child_transcript")):
            continue
        key = _derive_manifest_cell(row, project_root=project_root)
        if not key[1] or not key[2] or not key[3]:
            continue
        record = by_key.setdefault(
            key,
            {
                "source_paths": set(),
                "analysis_ready_paths": set(),
                "short_sample_count": 0,
            },
        )
        source_path = _clean(row.get("source_path"))
        if source_path:
            record["source_paths"].add(source_path)  # type: ignore[union-attr]
        if _truthy(row.get("analysis_ready")):
            record["analysis_ready_paths"].add(source_path)  # type: ignore[union-attr]
        elif _clean(row.get("qc_status")) == "eligible_short_sample":
            record["short_sample_count"] = int(record["short_sample_count"]) + 1
    return by_key


def _audit_status_and_action(
    *,
    source_transcript_rows: int,
    analysis_ready_source_rows: int,
    feature_matched_source_rows: int,
    clan_matched_source_rows: int,
    missing_feature_rows: int,
    missing_clan_rows: int,
    target_corpus: str,
) -> tuple[str, str]:
    if source_transcript_rows == 0:
        if feature_matched_source_rows or clan_matched_source_rows:
            return (
                "needs_manifest_rebuild",
                f"{target_corpus} feature or CLAN rows exist without matching transcript-manifest rows; rebuild the transcript manifest before intake decisions.",
            )
        return (
            "no_local_target_source_keep_low_confidence",
            f"No local {target_corpus} source rows match this cell; keep it low-confidence unless a new matched source is selected.",
        )
    if feature_matched_source_rows > analysis_ready_source_rows:
        return (
            "needs_manifest_rebuild",
            f"{target_corpus} reference features exceed analysis-ready manifest rows; rebuild the transcript manifest and derived features.",
        )
    if missing_feature_rows > 0:
        return (
            "needs_feature_rebuild",
            f"Analysis-ready {target_corpus} rows are missing from Python-derived reference features; rebuild reference cohorts.",
        )
    if missing_clan_rows > 0:
        return (
            "needs_clan_rebuild",
            f"{target_corpus} feature rows are missing matched CLAN-Derived Metrics; rerun CLAN and parse KIDEVAL output.",
        )
    return (
        "policy_exhausted_keep_low_confidence",
        f"No additional analysis-ready {target_corpus} rows remain under the current Reference Cohort policy; keep this cell low-confidence.",
    )


def build_audit_rows(
    manifest_df: pd.DataFrame,
    features_df: pd.DataFrame,
    clan_df: pd.DataFrame,
    coverage_df: pd.DataFrame,
    *,
    target_corpus: str,
    triage_bucket: str,
    project_root: Path = PROJECT_ROOT,
) -> list[dict[str, object]]:
    if coverage_df.empty:
        return []
    target_coverage = coverage_df[coverage_df["triage_bucket"].astype(str) == triage_bucket]
    if target_coverage.empty and {"source_audit_status", "source_audit_action"}.issubset(coverage_df.columns):
        source_audit_action = coverage_df["source_audit_action"].astype(str)
        target_coverage = coverage_df[
            coverage_df["source_audit_status"].astype(str).isin(AUDIT_STATUSES)
            & source_audit_action.str.contains(target_corpus, case=False, regex=False)
        ]
    manifest_by_key = _manifest_rows_by_key(
        manifest_df,
        target_corpus=target_corpus,
        project_root=project_root,
    )

    rows: list[dict[str, object]] = []
    for _, coverage_row in target_coverage.iterrows():
        key = _cell_key(coverage_row)
        manifest_record = manifest_by_key.get(
            key,
            {"source_paths": set(), "analysis_ready_paths": set(), "short_sample_count": 0},
        )
        source_paths = set(manifest_record["source_paths"])  # type: ignore[arg-type]
        ready_paths = set(manifest_record["analysis_ready_paths"])  # type: ignore[arg-type]
        feature_paths = _source_path_set(features_df, key, target_corpus)
        clan_paths = _source_path_set(clan_df, key, target_corpus)
        feature_matched = len(feature_paths)
        clan_matched = len(clan_paths)
        missing_feature = len(ready_paths - feature_paths)
        missing_clan = len(feature_paths - clan_paths)
        status, action = _audit_status_and_action(
            source_transcript_rows=len(source_paths),
            analysis_ready_source_rows=len(ready_paths),
            feature_matched_source_rows=feature_matched,
            clan_matched_source_rows=clan_matched,
            missing_feature_rows=missing_feature,
            missing_clan_rows=missing_clan,
            target_corpus=target_corpus,
        )
        rows.append(
            {
                "language": key[0],
                "age_band_12mo": key[1],
                "task_type": key[2],
                "group": key[3],
                "triage_bucket": triage_bucket,
                "target_corpus": target_corpus,
                "coverage_feature_rows": int(coverage_row.get("feature_row_count") or 0),
                "coverage_clan_rows": int(coverage_row.get("clan_row_count") or 0),
                "coverage_cohort_n": int(coverage_row.get("cohort_n") or 0),
                "source_transcript_rows": len(source_paths),
                "analysis_ready_source_rows": len(ready_paths),
                "short_sample_source_rows": int(manifest_record["short_sample_count"]),
                "feature_matched_source_rows": feature_matched,
                "clan_matched_source_rows": clan_matched,
                "missing_feature_rows": missing_feature,
                "missing_clan_rows": missing_clan,
                "audit_status": status,
                "audit_action": action,
            }
        )
    return rows


def write_audit_outputs(
    *,
    transcript_manifest_path: Path = MANIFEST_PATH,
    features_path: Path = FEATURES_PATH,
    clan_features_path: Path = CLAN_FEATURES_PATH,
    coverage_path: Path = COVERAGE_PATH,
    output_path: Path = AUDIT_PATH,
    target_corpus: str,
    triage_bucket: str,
    append: bool = False,
    project_root: Path = PROJECT_ROOT,
) -> pd.DataFrame:
    audit_df = pd.DataFrame(
        build_audit_rows(
            _read_csv(transcript_manifest_path),
            _read_csv(features_path),
            _read_csv(clan_features_path),
            _read_csv(coverage_path),
            target_corpus=target_corpus,
            triage_bucket=triage_bucket,
            project_root=project_root,
        ),
        columns=AUDIT_COLUMNS,
    )
    if append:
        existing_df = _read_csv(output_path)
        if not existing_df.empty:
            audit_df = _merge_audit_rows(existing_df, audit_df)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit_df.to_csv(output_path, index=False)
    return audit_df


def _merge_audit_rows(existing_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    if existing_df.empty:
        return new_df.reindex(columns=AUDIT_COLUMNS)
    if new_df.empty:
        return existing_df.reindex(columns=AUDIT_COLUMNS)

    combined = pd.concat(
        [
            existing_df.reindex(columns=AUDIT_COLUMNS),
            new_df.reindex(columns=AUDIT_COLUMNS),
        ],
        ignore_index=True,
    )
    return (
        combined.drop_duplicates(subset=AUDIT_KEY_COLUMNS, keep="last")
        .sort_values(AUDIT_KEY_COLUMNS)
        .reset_index(drop=True)
        .reindex(columns=AUDIT_COLUMNS)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default="Gillam")
    parser.add_argument("--triage-bucket", default="candidate_gillam")
    parser.add_argument("--transcript-manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--features", type=Path, default=FEATURES_PATH)
    parser.add_argument("--clan-features", type=Path, default=CLAN_FEATURES_PATH)
    parser.add_argument("--coverage", type=Path, default=COVERAGE_PATH)
    parser.add_argument("--output", type=Path, default=AUDIT_PATH)
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to the existing audit CSV and replace rows with the same cell, bucket, and target corpus.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit_df = write_audit_outputs(
        transcript_manifest_path=args.transcript_manifest,
        features_path=args.features,
        clan_features_path=args.clan_features,
        coverage_path=args.coverage,
        output_path=args.output,
        target_corpus=args.corpus,
        triage_bucket=args.triage_bucket,
        append=args.append,
    )
    print(f"Wrote {len(audit_df)} source-exhaustion audit row(s) to {args.output}")
    if not audit_df.empty:
        print(audit_df["audit_status"].value_counts().sort_index().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
