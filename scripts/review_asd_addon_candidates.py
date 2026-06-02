"""Review ASDBank ASD add-on candidates before any raw download.

This script is a research intake gate. It does not log in to TalkBank, download
files, or relax the Reference Cohort eligibility policy.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
DOCS_DIR = PROJECT_ROOT / "docs"

MATRIX_PATH = REFERENCE_DIR / "asd_addon_candidate_matrix.csv"
COVERAGE_PATH = REFERENCE_DIR / "english_child_reference_coverage.csv"
SOURCE_AUDIT_PATH = REFERENCE_DIR / "english_child_source_exhaustion_audit.csv"
NYU_REFRESH_REVIEW_PATH = REFERENCE_DIR / "nyu_emerson_official_refresh_review.csv"
AAC_ACCESS_TASK_REVIEW_PATH = REFERENCE_DIR / "aac_access_task_review.csv"
REPORT_PATH = REFERENCE_DIR / "asd_addon_review_report.csv"
MARKDOWN_PATH = DOCS_DIR / "ASD_ADDON_REVIEW.md"

REPORT_COLUMNS = [
    "candidate_corpus",
    "matrix_decision",
    "review_status",
    "recommended_next_action",
    "official_url",
    "access_level",
    "task_match",
    "expected_gap_cells",
    "asd_toyplay_low_n_cell_count",
    "asd_toyplay_low_n_row_gap_to_20",
    "source_audit_summary",
    "official_refresh_status",
    "aac_review_status",
]

BLOCKED_TERMS = {
    "diagnostic norm",
    "clinical validation",
    "model benchmark",
    "validated score",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _int_value(value: object) -> int:
    try:
        return int(float(str(value or "0")))
    except ValueError:
        return 0


def asd_toyplay_low_n_summary(coverage_rows: list[dict[str, str]]) -> tuple[int, int]:
    rows = [
        row
        for row in coverage_rows
        if row.get("task_type") == "toyplay"
        and row.get("group") == "ASD"
        and row.get("coverage_status") == "low_n"
    ]
    return len(rows), sum(max(20 - _int_value(row.get("cohort_n")), 0) for row in rows)


def source_audit_summary(source_audit_rows: list[dict[str, str]]) -> dict[str, str]:
    grouped: dict[str, dict[str, int]] = {}
    for row in source_audit_rows:
        corpus = str(row.get("target_corpus") or "").strip()
        status = str(row.get("audit_status") or "").strip()
        if not corpus or not status:
            continue
        counts = grouped.setdefault(corpus, {})
        counts[status] = counts.get(status, 0) + 1
    return {
        corpus: ";".join(f"{status}:{count}" for status, count in sorted(counts.items()))
        for corpus, counts in sorted(grouped.items())
    }


def nyu_refresh_status(refresh_review_rows: list[dict[str, str]]) -> str:
    for row in refresh_review_rows:
        if row.get("corpus") == "NYU-Emerson":
            return str(row.get("refresh_status") or "")
    return ""


def aac_review_status(aac_review_rows: list[dict[str, str]]) -> str:
    for row in aac_review_rows:
        if row.get("corpus") == "AAC":
            return str(row.get("review_status") or "")
    return ""


def review_status_for(
    row: dict[str, str],
    *,
    official_refresh_status: str = "",
    aac_status: str = "",
) -> tuple[str, str]:
    corpus = row.get("candidate_corpus", "")
    decision = row.get("decision", "")
    if decision == "download_candidate":
        return (
            "download_candidate",
            "Prepare a manual TalkBank download only after project-owner access and official-source review are documented.",
        )
    if corpus == "NYU-Emerson" or decision == "review_source_refresh":
        if official_refresh_status == "no_official_refresh_available":
            return (
                "no_official_refresh_available",
                "Official NYU-Emerson transcript count matches local transcript count; do not download new NYU-Emerson data in this round.",
            )
        if official_refresh_status == "download_candidate":
            return (
                "download_candidate",
                "Official NYU-Emerson transcript count exceeds local transcript count; prepare manual TalkBank download after project-owner access review.",
            )
        if official_refresh_status == "needs_local_artifact_rebuild":
            return (
                "needs_local_artifact_rebuild",
                "Local NYU-Emerson transcripts are present, but derived feature or CLAN artifacts need rebuilding before any download decision.",
            )
        return (
            "needs_official_refresh_check",
            "Check whether the official NYU-Emerson transcript package has newer shareable transcripts than the local ingest before any download.",
        )
    if corpus == "AAC" or decision == "review_access_and_task_fit":
        if aac_status == "separate_task_candidate_requires_access":
            return (
                "separate_task_candidate_requires_access",
                "Keep AAC out of toyplay Reference Cohorts; require project-owner access confirmation and separate aac_intervention task policy before any intake.",
            )
        return (
            "needs_access_and_task_review",
            "Confirm project-owner access eligibility and decide whether AAC intervention samples belong in a separate Reference Cohort task before any download.",
        )
    if corpus == "Rollins" or decision == "source_audit_then_keep_low_confidence":
        return (
            "keep_low_confidence",
            "Keep Rollins ASD toyplay cells low-confidence because source-exhaustion audit found no additional analysis-ready local rows under current policy.",
        )
    if decision in {"already_ingested_or_known_limitation", "known_task_mismatch"}:
        return (
            "blocked_known_limitation",
            "Do not redownload for current ASD toyplay gaps unless official metadata or the candidate matrix changes.",
        )
    return (
        "needs_matrix_review",
        "Review the candidate matrix decision before any download or Reference Cohort intake work.",
    )


def build_review_rows(
    matrix_rows: list[dict[str, str]],
    coverage_rows: list[dict[str, str]],
    source_audit_rows: list[dict[str, str]],
    official_refresh_rows: list[dict[str, str]] | None = None,
    aac_review_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, object]]:
    low_n_cell_count, low_n_row_gap = asd_toyplay_low_n_summary(coverage_rows)
    audit_by_corpus = source_audit_summary(source_audit_rows)
    official_refresh_by_corpus = {"NYU-Emerson": nyu_refresh_status(official_refresh_rows or [])}
    aac_review_by_corpus = {"AAC": aac_review_status(aac_review_rows or [])}
    rows: list[dict[str, object]] = []
    for matrix_row in matrix_rows:
        corpus = matrix_row.get("candidate_corpus", "")
        official_refresh_status = official_refresh_by_corpus.get(corpus, "")
        aac_status = aac_review_by_corpus.get(corpus, "")
        review_status, next_action = review_status_for(
            matrix_row,
            official_refresh_status=official_refresh_status,
            aac_status=aac_status,
        )
        rows.append(
            {
                "candidate_corpus": corpus,
                "matrix_decision": matrix_row.get("decision", ""),
                "review_status": review_status,
                "recommended_next_action": next_action,
                "official_url": matrix_row.get("official_url", ""),
                "access_level": matrix_row.get("access_level", ""),
                "task_match": matrix_row.get("task_match", ""),
                "expected_gap_cells": matrix_row.get("expected_gap_cells", ""),
                "asd_toyplay_low_n_cell_count": low_n_cell_count,
                "asd_toyplay_low_n_row_gap_to_20": low_n_row_gap,
                "source_audit_summary": audit_by_corpus.get(corpus, ""),
                "official_refresh_status": official_refresh_status,
                "aac_review_status": aac_status,
            }
        )
    return sorted(rows, key=lambda row: str(row["candidate_corpus"]))


def _markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    output = ["| " + " | ".join(columns) + " |"]
    output.append("| " + " | ".join("---" for _ in columns) + " |")
    for row in rows:
        output.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(output)


def build_markdown(rows: list[dict[str, object]]) -> str:
    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("review_status") or "")
        status_counts[status] = status_counts.get(status, 0) + 1
    count_rows = [
        {"review_status": status, "candidate_count": count}
        for status, count in sorted(status_counts.items())
    ]
    parts = [
        "# ASD Add-on Review",
        "",
        (
            "This research intake report combines the ASD Add-on Candidate Matrix, "
            "Reference Cohort coverage, and source-exhaustion audit results before any raw ASDBank download."
        ),
        "",
        "It is not a clinical output, access approval, or reason to relax Reference Cohort policy.",
        "",
        "## Review Status",
        "",
        _markdown_table(count_rows, ["review_status", "candidate_count"]),
        "",
        "## Candidate Actions",
        "",
        _markdown_table(
            rows,
            [
                "candidate_corpus",
                "matrix_decision",
                "review_status",
                "expected_gap_cells",
                "source_audit_summary",
                "official_refresh_status",
                "aac_review_status",
                "recommended_next_action",
            ],
        ),
        "",
        "## Notes",
        "",
        "- `download_candidate` is the only status that can trigger a manual TalkBank download.",
        "- `needs_access_and_task_review` requires project-owner eligibility review before any AAC intake.",
        "- `separate_task_candidate_requires_access` keeps AAC out of toyplay Reference Cohorts pending access confirmation and a separate AAC intervention task policy.",
        "- `needs_official_refresh_check` requires checking whether the official package has newer shareable transcripts.",
        "- `no_official_refresh_available` means the current official transcript count already matches local intake.",
        "- Raw TalkBank content must remain separate from user uploads and public app content.",
    ]
    markdown = "\n".join(parts).rstrip() + "\n"
    lower = markdown.lower()
    blocked = [term for term in BLOCKED_TERMS if term in lower]
    if blocked:
        raise ValueError(f"Blocked safety term in ASD add-on review markdown: {', '.join(blocked)}")
    return markdown


def write_review_outputs(
    *,
    matrix_path: Path = MATRIX_PATH,
    coverage_path: Path = COVERAGE_PATH,
    source_audit_path: Path = SOURCE_AUDIT_PATH,
    official_refresh_path: Path = NYU_REFRESH_REVIEW_PATH,
    aac_review_path: Path = AAC_ACCESS_TASK_REVIEW_PATH,
    report_path: Path = REPORT_PATH,
    markdown_path: Path = MARKDOWN_PATH,
) -> tuple[list[dict[str, object]], str]:
    rows = build_review_rows(
        _read_csv(matrix_path),
        _read_csv(coverage_path),
        _read_csv(source_audit_path),
        _read_csv(official_refresh_path),
        _read_csv(aac_review_path),
    )
    markdown = build_markdown(rows)
    _write_csv(report_path, rows, REPORT_COLUMNS)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")
    return rows, markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=MATRIX_PATH)
    parser.add_argument("--coverage", type=Path, default=COVERAGE_PATH)
    parser.add_argument("--source-audit", type=Path, default=SOURCE_AUDIT_PATH)
    parser.add_argument("--official-refresh", type=Path, default=NYU_REFRESH_REVIEW_PATH)
    parser.add_argument("--aac-review", type=Path, default=AAC_ACCESS_TASK_REVIEW_PATH)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    parser.add_argument("--markdown-output", type=Path, default=MARKDOWN_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows, _markdown = write_review_outputs(
        matrix_path=args.matrix,
        coverage_path=args.coverage,
        source_audit_path=args.source_audit,
        official_refresh_path=args.official_refresh,
        aac_review_path=args.aac_review,
        report_path=args.output,
        markdown_path=args.markdown_output,
    )
    print(f"Saved: {args.output} ({len(rows)} rows)")
    print(f"Saved: {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
