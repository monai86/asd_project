"""Benchmark helpers for Clinical Speech Artifact quality reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import json
from typing import Any

from packages.cha import parse_cha_file
from .quality import build_quality_report


BENCHMARK_SCHEMA_VERSION = "clinical-speech-benchmark-v1"


@dataclass(frozen=True)
class BenchmarkCase:
    session_id: str
    asr_draft_cha: Path
    reviewed_cha: Path
    language: str | None = None
    cohort: str | None = None


def build_benchmark_report(
    cases: list[BenchmarkCase],
    *,
    output_dir: str | Path,
) -> dict[str, Any]:
    resolved_output_dir = Path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    case_rows = [_evaluate_case(case) for case in cases]
    summary = _summary(case_rows)
    report = {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "source": "asr_draft_vs_reviewed_transcript_benchmark",
        "case_count": len(case_rows),
        "summary": summary,
        "cases": case_rows,
        "safety_labels": [
            "engineering quality benchmark only",
            "does not diagnose ASD",
            "reviewed transcripts remain source of truth",
        ],
    }

    (resolved_output_dir / "benchmark_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_cases_csv(resolved_output_dir / "benchmark_cases.csv", case_rows)
    return report


def load_cases_json(path: str | Path) -> list[BenchmarkCase]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload["cases"] if isinstance(payload, dict) else payload
    return [
        BenchmarkCase(
            session_id=str(row["session_id"]),
            asr_draft_cha=Path(row["asr_draft_cha"]),
            reviewed_cha=Path(row["reviewed_cha"]),
            language=row.get("language"),
            cohort=row.get("cohort"),
        )
        for row in rows
    ]


def _evaluate_case(case: BenchmarkCase) -> dict[str, Any]:
    draft = parse_cha_file(case.asr_draft_cha)
    reviewed = parse_cha_file(case.reviewed_cha)
    quality = build_quality_report(asr_draft=draft, reviewed=reviewed)
    summary = quality["summary"]
    return {
        "session_id": case.session_id,
        "language": case.language,
        "cohort": case.cohort,
        "asr_draft_cha": str(case.asr_draft_cha),
        "reviewed_cha": str(case.reviewed_cha),
        "wer": summary["wer"],
        "cer": summary["cer"],
        "speaker_label_accuracy": summary["speaker_label_accuracy"],
        "utterance_count_draft": summary["utterance_count_draft"],
        "utterance_count_reviewed": summary["utterance_count_reviewed"],
        "utterance_count_delta": summary["utterance_count_delta"],
        "feature_drift_mean_abs": summary["feature_drift_mean_abs"],
        "line_edit_rate": summary["line_edit_rate"],
        "warnings": quality["warnings"],
    }


def _summary(case_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "wer_mean": _mean(row["wer"] for row in case_rows),
        "cer_mean": _mean(row["cer"] for row in case_rows),
        "speaker_label_accuracy_mean": _mean(
            row["speaker_label_accuracy"]
            for row in case_rows
            if row["speaker_label_accuracy"] is not None
        ),
        "feature_drift_mean_abs_mean": _mean(
            row["feature_drift_mean_abs"] for row in case_rows
        ),
        "line_edit_rate_mean": _mean(row["line_edit_rate"] for row in case_rows),
        "utterance_count_delta_mean": _mean(
            row["utterance_count_delta"] for row in case_rows
        ),
    }


def _mean(values) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    if not numbers:
        return None
    return round(sum(numbers) / len(numbers), 4)


def _write_cases_csv(path: Path, case_rows: list[dict[str, Any]]) -> None:
    fields = [
        "session_id",
        "language",
        "cohort",
        "wer",
        "cer",
        "speaker_label_accuracy",
        "feature_drift_mean_abs",
        "line_edit_rate",
        "utterance_count_delta",
        "utterance_count_draft",
        "utterance_count_reviewed",
        "asr_draft_cha",
        "reviewed_cha",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in case_rows:
            writer.writerow({field: row.get(field) for field in fields})
