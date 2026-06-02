"""Review whether NYU-Emerson has an official transcript refresh to intake.

This script compares official corpus-page facts with local project artifacts.
It does not log in to TalkBank, download files, or change Reference Cohort
eligibility rules.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifests"

TRANSCRIPT_MANIFEST_PATH = MANIFEST_DIR / "english_child_transcript_manifest.csv"
FEATURES_PATH = REFERENCE_DIR / "english_child_reference_features.csv"
CLAN_FEATURES_PATH = REFERENCE_DIR / "english_child_clan_features.csv"
OUTPUT_PATH = REFERENCE_DIR / "nyu_emerson_official_refresh_review.csv"

OFFICIAL_URL = "https://talkbank.org/asd/access/English/NYU-Emerson.html"
OFFICIAL_PUBLISHED_CORPUS_DATE = "February 2026"
OFFICIAL_PARTICIPANT_COUNT = 30
OFFICIAL_PUBLISHED_TRANSCRIPT_SETS = 30
CORPUS = "NYU-Emerson"

REVIEW_COLUMNS = [
    "corpus",
    "official_url",
    "official_published_corpus_date",
    "official_participant_count",
    "official_published_transcript_sets",
    "local_transcript_count",
    "local_analysis_ready_count",
    "local_feature_row_count",
    "local_clan_row_count",
    "local_excluded_count",
    "refresh_status",
    "recommended_next_action",
]


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in REVIEW_COLUMNS})


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _corpus_rows(rows: list[dict[str, str]], corpus: str = CORPUS) -> list[dict[str, str]]:
    return [row for row in rows if str(row.get("corpus") or "") == corpus]


def _refresh_status(
    *,
    official_published_transcript_sets: int,
    local_transcript_count: int,
    local_analysis_ready_count: int,
    local_feature_row_count: int,
    local_clan_row_count: int,
) -> tuple[str, str]:
    if local_transcript_count < official_published_transcript_sets:
        return (
            "download_candidate",
            "Official NYU-Emerson transcript count exceeds local transcript count; prepare manual TalkBank download after project-owner access review.",
        )
    if local_feature_row_count < local_analysis_ready_count or local_clan_row_count < local_feature_row_count:
        return (
            "needs_local_artifact_rebuild",
            "Local NYU-Emerson transcripts are present, but derived feature or CLAN artifacts are behind the analysis-ready manifest.",
        )
    return (
        "no_official_refresh_available",
        "Official NYU-Emerson transcript count matches local transcript count; do not download new NYU-Emerson data in this round.",
    )


def build_refresh_review_row(
    *,
    transcript_manifest_rows: list[dict[str, str]],
    feature_rows: list[dict[str, str]],
    clan_rows: list[dict[str, str]],
    official_url: str = OFFICIAL_URL,
    official_published_corpus_date: str = OFFICIAL_PUBLISHED_CORPUS_DATE,
    official_participant_count: int = OFFICIAL_PARTICIPANT_COUNT,
    official_published_transcript_sets: int = OFFICIAL_PUBLISHED_TRANSCRIPT_SETS,
) -> dict[str, object]:
    manifest_rows = _corpus_rows(transcript_manifest_rows)
    corpus_feature_rows = _corpus_rows(feature_rows)
    corpus_clan_rows = _corpus_rows(clan_rows)
    local_transcript_count = len(manifest_rows)
    local_analysis_ready_count = sum(_truthy(row.get("analysis_ready")) for row in manifest_rows)
    local_feature_row_count = len(corpus_feature_rows)
    local_clan_row_count = len(corpus_clan_rows)
    status, next_action = _refresh_status(
        official_published_transcript_sets=official_published_transcript_sets,
        local_transcript_count=local_transcript_count,
        local_analysis_ready_count=local_analysis_ready_count,
        local_feature_row_count=local_feature_row_count,
        local_clan_row_count=local_clan_row_count,
    )
    return {
        "corpus": CORPUS,
        "official_url": official_url,
        "official_published_corpus_date": official_published_corpus_date,
        "official_participant_count": official_participant_count,
        "official_published_transcript_sets": official_published_transcript_sets,
        "local_transcript_count": local_transcript_count,
        "local_analysis_ready_count": local_analysis_ready_count,
        "local_feature_row_count": local_feature_row_count,
        "local_clan_row_count": local_clan_row_count,
        "local_excluded_count": local_transcript_count - local_analysis_ready_count,
        "refresh_status": status,
        "recommended_next_action": next_action,
    }


def write_refresh_review(
    *,
    transcript_manifest_path: Path = TRANSCRIPT_MANIFEST_PATH,
    features_path: Path = FEATURES_PATH,
    clan_features_path: Path = CLAN_FEATURES_PATH,
    output_path: Path = OUTPUT_PATH,
    official_url: str = OFFICIAL_URL,
    official_published_corpus_date: str = OFFICIAL_PUBLISHED_CORPUS_DATE,
    official_participant_count: int = OFFICIAL_PARTICIPANT_COUNT,
    official_published_transcript_sets: int = OFFICIAL_PUBLISHED_TRANSCRIPT_SETS,
) -> list[dict[str, object]]:
    row = build_refresh_review_row(
        transcript_manifest_rows=_read_csv(transcript_manifest_path),
        feature_rows=_read_csv(features_path),
        clan_rows=_read_csv(clan_features_path),
        official_url=official_url,
        official_published_corpus_date=official_published_corpus_date,
        official_participant_count=official_participant_count,
        official_published_transcript_sets=official_published_transcript_sets,
    )
    rows = [row]
    _write_csv(output_path, rows)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcript-manifest", type=Path, default=TRANSCRIPT_MANIFEST_PATH)
    parser.add_argument("--features", type=Path, default=FEATURES_PATH)
    parser.add_argument("--clan-features", type=Path, default=CLAN_FEATURES_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--official-url", default=OFFICIAL_URL)
    parser.add_argument("--official-published-corpus-date", default=OFFICIAL_PUBLISHED_CORPUS_DATE)
    parser.add_argument("--official-participant-count", type=int, default=OFFICIAL_PARTICIPANT_COUNT)
    parser.add_argument(
        "--official-published-transcript-sets",
        type=int,
        default=OFFICIAL_PUBLISHED_TRANSCRIPT_SETS,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = write_refresh_review(
        transcript_manifest_path=args.transcript_manifest,
        features_path=args.features,
        clan_features_path=args.clan_features,
        output_path=args.output,
        official_url=args.official_url,
        official_published_corpus_date=args.official_published_corpus_date,
        official_participant_count=args.official_participant_count,
        official_published_transcript_sets=args.official_published_transcript_sets,
    )
    print(f"Saved: {args.output} ({len(rows)} row)")
    print(f"refresh_status: {rows[0]['refresh_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
