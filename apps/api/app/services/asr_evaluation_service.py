from __future__ import annotations

import json
import re
from pathlib import Path

from app.schemas.clinical import AsrDatasetEvaluationResult, AsrDatasetSampleResult, AsrEvaluationInput, AsrEvaluationReport
from app.services.providers.basic_provider import _tokens


def evaluate_asr(payload: AsrEvaluationInput) -> AsrEvaluationReport:
    ref_norm = normalize_text(payload.reference_text)
    hyp_norm = normalize_text(payload.hypothesis_text)
    ref_tokens = ref_norm.split()
    hyp_tokens = hyp_norm.split()
    wer = edit_distance(ref_tokens, hyp_tokens) / len(ref_tokens) if ref_tokens else 0.0
    cer = edit_distance(list(ref_norm), list(hyp_norm)) / len(ref_norm) if ref_norm else 0.0
    coverage = payload.transcribed_duration_seconds / payload.audio_duration_seconds if payload.audio_duration_seconds else 0.0
    speaker_accuracy = _speaker_accuracy(payload.reference_speakers, payload.hypothesis_speakers)
    utterance_count_error = abs(count_utterances(payload.reference_text) - count_utterances(payload.hypothesis_text))
    feature_deviation = feature_deviation_report(payload.reference_text, payload.hypothesis_text)
    json_report = {
        "coverage": round(coverage, 4),
        "utterance_count_error": utterance_count_error,
        "speaker_accuracy": round(speaker_accuracy, 4),
        "normalized_wer": round(wer, 4),
        "character_error_rate": round(cer, 4),
        "feature_deviation": feature_deviation,
    }
    markdown = "\n".join(
        [
            "# ASR Evaluation Report",
            "",
            f"- Coverage: {json_report['coverage']}",
            f"- Utterance count error: {utterance_count_error}",
            f"- Speaker accuracy: {json_report['speaker_accuracy']}",
            f"- Normalized WER: {json_report['normalized_wer']}",
            f"- Character error rate: {json_report['character_error_rate']}",
            "",
            "If ASR quality is weak, the manual transcript and CHA upload workflow remains the primary clinical path.",
        ]
    )
    return AsrEvaluationReport(markdown=markdown, json_report=json_report, **json_report)


def write_reports(report: AsrEvaluationReport, output_dir: str | Path) -> tuple[Path, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "asr_evaluation_report.json"
    md_path = root / "asr_evaluation_report.md"
    json_path.write_text(json.dumps(report.json_report, indent=2), encoding="utf-8")
    md_path.write_text(report.markdown, encoding="utf-8")
    return json_path, md_path


def evaluate_asr_dataset(dataset_dir: str | Path, hypothesis_dir: str | Path | None = None, output_dir: str | Path | None = None) -> AsrDatasetEvaluationResult:
    root = Path(dataset_dir)
    gold_root = root / "gold_transcripts"
    hypothesis_root = Path(hypothesis_dir) if hypothesis_dir else root / "hypothesis_transcripts"
    audio_root = root / "audio_samples"
    warnings: list[str] = []
    samples: list[AsrDatasetSampleResult] = []

    if not gold_root.exists():
        raise ValueError("ASR evaluation dataset requires data/evaluation/gold_transcripts or a dataset_dir with gold_transcripts.")

    gold_files = sorted(path for path in gold_root.iterdir() if path.suffix.lower() in {".cha", ".txt"})
    if not gold_files:
        warnings.append("No gold transcript files were found.")

    for gold_path in gold_files:
        sample_id = gold_path.stem
        hypothesis_path = _matching_transcript(hypothesis_root, sample_id)
        sample_warnings: list[str] = []
        hypothesis_text = ""
        if hypothesis_path is None:
            sample_warnings.append("Missing ASR hypothesis transcript; metrics compare gold transcript to an empty draft.")
        else:
            hypothesis_text = hypothesis_path.read_text(encoding="utf-8")
        audio_present = any((audio_root / f"{sample_id}{suffix}").exists() for suffix in [".wav", ".mp3", ".m4a", ".mp4", ".mov"])
        if not audio_present:
            sample_warnings.append("No matching audio sample metadata file found.")
        reference_text = gold_path.read_text(encoding="utf-8")
        report = evaluate_asr(
            AsrEvaluationInput(
                reference_text=reference_text,
                hypothesis_text=hypothesis_text,
                reference_speakers=extract_speakers(reference_text),
                hypothesis_speakers=extract_speakers(hypothesis_text),
            )
        )
        samples.append(
            AsrDatasetSampleResult(
                sample_id=sample_id,
                gold_transcript_path=str(gold_path),
                hypothesis_transcript_path=str(hypothesis_path) if hypothesis_path else None,
                audio_present=audio_present,
                report=report,
                warnings=sample_warnings,
            )
        )

    aggregate = _aggregate_metrics([sample.report for sample in samples])
    report_paths: dict[str, str] = {}
    if output_dir:
        json_path, md_path = write_dataset_reports(samples, aggregate, warnings, output_dir)
        report_paths = {"json": str(json_path), "markdown": str(md_path)}
    return AsrDatasetEvaluationResult(
        dataset_dir=str(root),
        sample_count=len(samples),
        samples=samples,
        aggregate_metrics=aggregate,
        warnings=warnings,
        report_paths=report_paths,
    )


def write_dataset_reports(
    samples: list[AsrDatasetSampleResult],
    aggregate_metrics: dict[str, float],
    warnings: list[str],
    output_dir: str | Path,
) -> tuple[Path, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "sample_count": len(samples),
        "aggregate_metrics": aggregate_metrics,
        "warnings": warnings,
        "samples": [sample.model_dump(mode="json") for sample in samples],
    }
    json_path = root / "asr_dataset_evaluation_report.json"
    md_path = root / "asr_dataset_evaluation_report.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(_dataset_markdown(samples, aggregate_metrics, warnings), encoding="utf-8")
    return json_path, md_path


def normalize_text(text: str) -> str:
    value = str(text or "").lower()
    value = re.sub(r"[^\w\sก-๙]", " ", value)
    value = re.sub(r"\b(\d+)\b", r"\1", value)
    return re.sub(r"\s+", " ", value).strip()


def count_utterances(text: str) -> int:
    return sum(1 for line in str(text or "").splitlines() if line.strip().startswith("*"))


def extract_speakers(text: str) -> list[str]:
    speakers: list[str] = []
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("*") and ":" in stripped:
            speakers.append(stripped[1:].split(":", 1)[0])
    return speakers


def feature_deviation_report(reference_text: str, hypothesis_text: str) -> dict[str, float]:
    ref_tokens = _tokens(reference_text)
    hyp_tokens = _tokens(hypothesis_text)
    ref_utt = max(count_utterances(reference_text), 1)
    hyp_utt = max(count_utterances(hypothesis_text), 1)
    ref_ttr = len(set(ref_tokens)) / len(ref_tokens) if ref_tokens else 0
    hyp_ttr = len(set(hyp_tokens)) / len(hyp_tokens) if hyp_tokens else 0
    return {
        "mlu_difference": round((len(hyp_tokens) / hyp_utt) - (len(ref_tokens) / ref_utt), 4),
        "ttr_difference": round(hyp_ttr - ref_ttr, 4),
        "ndw_difference": float(len(set(hyp_tokens)) - len(set(ref_tokens))),
        "unintelligible_ratio_difference": round(_unintelligible_ratio(hypothesis_text) - _unintelligible_ratio(reference_text), 4),
    }


def edit_distance(left, right) -> int:
    previous = list(range(len(right) + 1))
    for i, left_item in enumerate(left, start=1):
        current = [i]
        for j, right_item in enumerate(right, start=1):
            current.append(min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + (left_item != right_item),
            ))
        previous = current
    return previous[-1]


def _speaker_accuracy(reference: list[str], hypothesis: list[str]) -> float:
    if not reference:
        return 0.0
    compared = zip(reference, hypothesis)
    correct = sum(1 for left, right in compared if left == right)
    return correct / len(reference)


def _unintelligible_ratio(text: str) -> float:
    utterances = [line for line in str(text or "").splitlines() if line.strip().startswith("*")]
    if not utterances:
        return 0.0
    return sum(1 for line in utterances if re.search(r"\b(?:xxx|yyy|www)\b", line, re.I)) / len(utterances)


def _matching_transcript(root: Path, sample_id: str) -> Path | None:
    for suffix in [".cha", ".txt"]:
        candidate = root / f"{sample_id}{suffix}"
        if candidate.exists():
            return candidate
    return None


def _aggregate_metrics(reports: list[AsrEvaluationReport]) -> dict[str, float]:
    if not reports:
        return {
            "coverage": 0.0,
            "utterance_count_error": 0.0,
            "speaker_accuracy": 0.0,
            "normalized_wer": 0.0,
            "character_error_rate": 0.0,
        }
    return {
        "coverage": round(sum(report.coverage for report in reports) / len(reports), 4),
        "utterance_count_error": round(sum(report.utterance_count_error for report in reports) / len(reports), 4),
        "speaker_accuracy": round(sum(report.speaker_accuracy for report in reports) / len(reports), 4),
        "normalized_wer": round(sum(report.normalized_wer for report in reports) / len(reports), 4),
        "character_error_rate": round(sum(report.character_error_rate for report in reports) / len(reports), 4),
    }


def _dataset_markdown(samples: list[AsrDatasetSampleResult], aggregate_metrics: dict[str, float], warnings: list[str]) -> str:
    lines = [
        "# ASR Dataset Evaluation Report",
        "",
        f"- Sample count: {len(samples)}",
        f"- Mean speaker accuracy: {aggregate_metrics['speaker_accuracy']}",
        f"- Mean normalized WER: {aggregate_metrics['normalized_wer']}",
        f"- Mean character error rate: {aggregate_metrics['character_error_rate']}",
        "",
        "If ASR quality is weak, the manual transcript and CHA upload workflow remains the primary clinical path.",
    ]
    if warnings:
        lines.extend(["", "## Dataset Warnings", *[f"- {warning}" for warning in warnings]])
    lines.append("")
    lines.append("## Samples")
    for sample in samples:
        lines.append(f"- {sample.sample_id}: WER {sample.report.normalized_wer}, speaker accuracy {sample.report.speaker_accuracy}")
    return "\n".join(lines)
