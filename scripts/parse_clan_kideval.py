"""Parse CLAN KIDEVAL output into a separate CLAN-Derived Metrics table."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_reference_cohorts import transcript_uid  # noqa: E402


RUN_MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "english_child_clan_run_manifest.csv"
TRANSCRIPT_MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "english_child_transcript_manifest.csv"
REFERENCE_FEATURES_PATH = PROJECT_ROOT / "data" / "reference" / "english_child_reference_features.csv"
CLAN_FEATURES_PATH = PROJECT_ROOT / "data" / "reference" / "english_child_clan_features.csv"
CLAN_QC_PATH = PROJECT_ROOT / "data" / "reference" / "english_child_clan_features_qc.csv"

METRIC_SOURCE = "clan_kideval"

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
    "age_band_12mo",
    "child_utterance_count",
    "child_token_count",
    "metric_source",
    "clan_output_path",
]

KIDEVAL_METRIC_COLUMNS = [
    "kideval_mlu_utts",
    "kideval_freq_types",
    "kideval_freq_tokens",
    "kideval_freq_ttr",
    "kideval_vocd_score",
    "kideval_dss_utterances",
    "kideval_dss",
    "kideval_ipsyn_total",
]

FEATURE_COLUMNS = METADATA_COLUMNS + KIDEVAL_METRIC_COLUMNS
QC_COLUMNS = ["qc_scope", "source_path", "clan_output_path", "qc_status", "reason", "detail"]

FILE_COLUMN_ALIASES = {"file", "filename", "file_name", "transcript", "transcript_file"}

METRIC_ALIASES = {
    "mlu_utts": "kideval_mlu_utts",
    "mlu_utterances": "kideval_mlu_utts",
    "freq_types": "kideval_freq_types",
    "freq_tokens": "kideval_freq_tokens",
    "freq_ttr": "kideval_freq_ttr",
    "vocd_score": "kideval_vocd_score",
    "vocd_d_optimum_average": "kideval_vocd_score",
    "vocd": "kideval_vocd_score",
    "dss_utterances": "kideval_dss_utterances",
    "dss_utts": "kideval_dss_utterances",
    "dss": "kideval_dss",
    "ipsyn_total": "kideval_ipsyn_total",
    "ipsyn": "kideval_ipsyn_total",
}


@dataclass(frozen=True)
class ParsedKidevalTable:
    rows: list[dict[str, str]]
    file_column: str


def _relative(path: Path, root: Path = PROJECT_ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _resolve_path(value: str, project_root: Path = PROJECT_ROOT) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def _normalize_header(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_")


def _optional_number(value: object) -> str:
    text = str(value or "").strip()
    if not text or text.upper() in {"N/A", "NA", "NAN", "."}:
        return ""
    try:
        numeric = float(text)
    except ValueError:
        return ""
    if math.isnan(numeric):
        return ""
    return str(int(numeric)) if numeric.is_integer() else str(numeric)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _candidate_delimiters(line: str) -> list[str]:
    delimiters = []
    if "\t" in line:
        delimiters.append("\t")
    if "," in line:
        delimiters.append(",")
    return delimiters


def parse_kideval_table(text: str) -> ParsedKidevalTable:
    """Parse the first KIDEVAL table with a file/transcript column."""
    stripped = text.lstrip()
    if stripped.startswith("<?xml") or stripped.startswith("<Workbook"):
        return parse_kideval_xml_spreadsheet(text)

    lines = [line for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        for delimiter in _candidate_delimiters(line):
            headers = next(csv.reader([line], delimiter=delimiter))
            normalized_headers = [_normalize_header(header) for header in headers]
            file_column_index = next(
                (i for i, header in enumerate(normalized_headers) if header in FILE_COLUMN_ALIASES),
                None,
            )
            if file_column_index is None:
                continue
            reader = csv.DictReader(lines[index:], delimiter=delimiter)
            rows = [row for row in reader if any(str(value or "").strip() for value in row.values())]
            return ParsedKidevalTable(rows=rows, file_column=headers[file_column_index])
    return ParsedKidevalTable(rows=[], file_column="")


def parse_kideval_xml_spreadsheet(text: str) -> ParsedKidevalTable:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return ParsedKidevalTable(rows=[], file_column="")

    rows: list[list[str]] = []
    spreadsheet_ns = "{urn:schemas-microsoft-com:office:spreadsheet}"
    index_attr = f"{spreadsheet_ns}Index"
    for row_node in root.findall(f".//{spreadsheet_ns}Row"):
        values: list[str] = []
        for cell_node in row_node.findall(f"{spreadsheet_ns}Cell"):
            cell_index = cell_node.attrib.get(index_attr)
            if cell_index and cell_index.isdigit():
                while len(values) < int(cell_index) - 1:
                    values.append("")
            data_node = cell_node.find(f"{spreadsheet_ns}Data")
            values.append(data_node.text if data_node is not None and data_node.text is not None else "")
        if any(value.strip() for value in values):
            rows.append(values)

    if not rows:
        return ParsedKidevalTable(rows=[], file_column="")

    headers = rows[0]
    normalized_headers = [_normalize_header(header) for header in headers]
    file_column_index = next(
        (i for i, header in enumerate(normalized_headers) if header in FILE_COLUMN_ALIASES),
        None,
    )
    if file_column_index is None:
        return ParsedKidevalTable(rows=[], file_column="")

    records = []
    for values in rows[1:]:
        if len(values) < len(headers):
            values = [*values, *([""] * (len(headers) - len(values)))]
        record = dict(zip(headers, values[: len(headers)]))
        if any(str(value or "").strip() for value in record.values()):
            records.append(record)
    return ParsedKidevalTable(rows=records, file_column=headers[file_column_index])


def completed_kideval_jobs(run_manifest_rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in run_manifest_rows
        if row.get("command") == "kideval"
        and row.get("status") == "completed"
        and (row.get("artifact_path") or row.get("output_path"))
    ]


def _row_aliases(row: dict[str, str]) -> set[tuple[str, str]]:
    aliases: set[tuple[str, str]] = set()
    corpus = row.get("corpus", "")
    for key in ("curated_path", "source_path"):
        value = row.get(key, "")
        if not value:
            continue
        path = Path(value)
        aliases.add((corpus, value))
        aliases.add((corpus, path.name))
        aliases.add((corpus, path.stem))
    return aliases


def build_manifest_index(rows: Iterable[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    index: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        for alias in _row_aliases(row):
            index.setdefault(alias, row)
    return index


def build_reference_index(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row.get("sha256", ""): row for row in rows if row.get("sha256")}


def _lookup_manifest_row(
    *,
    file_value: str,
    corpus: str,
    manifest_index: dict[tuple[str, str], dict[str, str]],
) -> dict[str, str] | None:
    path = Path(file_value.strip())
    candidates = [
        file_value.strip(),
        path.as_posix(),
        path.name,
        path.stem,
    ]
    for candidate in candidates:
        row = manifest_index.get((corpus, candidate))
        if row is not None:
            return row
    return None


def _metric_values(kideval_row: dict[str, str]) -> dict[str, str]:
    values = {column: "" for column in KIDEVAL_METRIC_COLUMNS}
    for raw_key, raw_value in kideval_row.items():
        metric_column = METRIC_ALIASES.get(_normalize_header(raw_key or ""))
        if metric_column:
            values[metric_column] = _optional_number(raw_value)
    return values


def _metadata_values(
    *,
    manifest_row: dict[str, str],
    reference_row: dict[str, str] | None,
    clan_output_path: str,
) -> dict[str, str]:
    merged = {**manifest_row, **(reference_row or {})}
    return {
        "transcript_uid": merged.get("transcript_uid") or transcript_uid(manifest_row),
        "source_path": manifest_row.get("source_path", ""),
        "curated_path": manifest_row.get("curated_path", ""),
        "bank": manifest_row.get("bank", ""),
        "corpus": manifest_row.get("corpus", ""),
        "download_date": manifest_row.get("download_date", ""),
        "sha256": manifest_row.get("sha256", ""),
        "language": merged.get("language", ""),
        "design_type": merged.get("design_type", ""),
        "task_type": merged.get("task_type", ""),
        "group_type": merged.get("group_type", ""),
        "group": merged.get("group", ""),
        "sex": merged.get("sex", ""),
        "age_band_12mo": merged.get("age_band_12mo", ""),
        "child_utterance_count": manifest_row.get("child_utterance_count", ""),
        "child_token_count": manifest_row.get("child_token_count", ""),
        "metric_source": METRIC_SOURCE,
        "clan_output_path": clan_output_path,
    }


def build_clan_feature_rows(
    *,
    run_manifest_rows: Iterable[dict[str, str]],
    transcript_manifest_rows: Iterable[dict[str, str]],
    reference_feature_rows: Iterable[dict[str, str]],
    project_root: Path = PROJECT_ROOT,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    feature_rows: list[dict[str, str]] = []
    qc_rows: list[dict[str, str]] = []
    manifest_index = build_manifest_index(transcript_manifest_rows)
    reference_index = build_reference_index(reference_feature_rows)
    jobs = completed_kideval_jobs(run_manifest_rows)

    if not jobs:
        qc_rows.append(
            {
                "qc_scope": "kideval",
                "source_path": "",
                "clan_output_path": "",
                "qc_status": "warn",
                "reason": "no_completed_kideval_jobs",
                "detail": "Run CLAN KIDEVAL before parsing CLAN-Derived Metrics.",
            }
        )
        return feature_rows, qc_rows

    for job in jobs:
        clan_path_value = job.get("artifact_path") or job.get("output_path", "")
        output_path = _resolve_path(clan_path_value, project_root)
        output_value = _relative(output_path, project_root)
        if not output_path.exists():
            qc_rows.append(
                {
                    "qc_scope": "kideval_output",
                    "source_path": "",
                    "clan_output_path": output_value,
                    "qc_status": "fail",
                    "reason": "missing_kideval_output",
                    "detail": output_value,
                }
            )
            continue

        parsed = parse_kideval_table(output_path.read_text(encoding="utf-8", errors="replace"))
        if not parsed.rows:
            qc_rows.append(
                {
                    "qc_scope": "kideval_output",
                    "source_path": "",
                    "clan_output_path": output_value,
                    "qc_status": "fail",
                    "reason": "missing_kideval_table",
                    "detail": output_value,
                }
            )
            continue

        job_feature_count = 0
        for parsed_row in parsed.rows:
            metric_values = _metric_values(parsed_row)
            if not any(metric_values.values()):
                continue
            file_value = parsed_row.get(parsed.file_column, "")
            if job.get("run_scope") == "file":
                manifest_row = _lookup_manifest_row(
                    file_value=job.get("curated_path") or job.get("source_path", ""),
                    corpus=job.get("corpus", ""),
                    manifest_index=manifest_index,
                )
            else:
                manifest_row = _lookup_manifest_row(
                    file_value=file_value,
                    corpus=job.get("corpus", ""),
                    manifest_index=manifest_index,
                )
            if manifest_row is None:
                qc_rows.append(
                    {
                        "qc_scope": "kideval_row",
                        "source_path": file_value,
                        "clan_output_path": output_value,
                        "qc_status": "fail",
                        "reason": "unmatched_kideval_file",
                        "detail": job.get("corpus", ""),
                    }
                )
                continue

            reference_row = reference_index.get(manifest_row.get("sha256", ""))
            feature_rows.append(
                {
                    **_metadata_values(
                        manifest_row=manifest_row,
                        reference_row=reference_row,
                        clan_output_path=output_value,
                    ),
                    **metric_values,
                }
            )
            job_feature_count += 1

        if job_feature_count == 0:
            qc_rows.append(
                {
                    "qc_scope": "kideval_output",
                    "source_path": job.get("curated_path", ""),
                    "clan_output_path": output_value,
                    "qc_status": "fail",
                    "reason": "missing_kideval_metrics",
                    "detail": output_value,
                }
            )

    return feature_rows, qc_rows


def parse_clan_kideval(
    *,
    run_manifest_path: Path = RUN_MANIFEST_PATH,
    transcript_manifest_path: Path = TRANSCRIPT_MANIFEST_PATH,
    reference_features_path: Path = REFERENCE_FEATURES_PATH,
    output_path: Path = CLAN_FEATURES_PATH,
    qc_path: Path = CLAN_QC_PATH,
    project_root: Path = PROJECT_ROOT,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    feature_rows, qc_rows = build_clan_feature_rows(
        run_manifest_rows=read_csv(run_manifest_path),
        transcript_manifest_rows=read_csv(transcript_manifest_path),
        reference_feature_rows=read_csv(reference_features_path),
        project_root=project_root,
    )
    write_csv(output_path, feature_rows, FEATURE_COLUMNS)
    write_csv(qc_path, qc_rows, QC_COLUMNS)
    return feature_rows, qc_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-manifest", type=Path, default=RUN_MANIFEST_PATH)
    parser.add_argument("--transcript-manifest", type=Path, default=TRANSCRIPT_MANIFEST_PATH)
    parser.add_argument("--reference-features", type=Path, default=REFERENCE_FEATURES_PATH)
    parser.add_argument("--output", type=Path, default=CLAN_FEATURES_PATH)
    parser.add_argument("--qc-output", type=Path, default=CLAN_QC_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    feature_rows, qc_rows = parse_clan_kideval(
        run_manifest_path=args.run_manifest,
        transcript_manifest_path=args.transcript_manifest,
        reference_features_path=args.reference_features,
        output_path=args.output,
        qc_path=args.qc_output,
    )
    print(f"Parsed {len(feature_rows)} CLAN KIDEVAL metric row(s).")
    print(f"QC rows: {len(qc_rows)}")
    print(f"Output: {_relative(args.output)}")
    print(f"QC output: {_relative(args.qc_output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
