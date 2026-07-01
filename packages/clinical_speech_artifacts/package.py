"""Stable artifact package contract for the Clinical Speech Artifact Pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from packages.cha import parse_cha_file
from packages.features import extract_transcript_features


PACKAGE_SCHEMA_VERSION = "clinical-speech-artifact-package-v1"
CREATED_BY = "scripts/build_clinical_speech_artifact_package.py"


@dataclass(frozen=True)
class ArtifactRef:
    path: str
    sha256: str

    def to_json(self) -> dict[str, str]:
        return asdict(self)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_manifest(
    *,
    session_id: str,
    input_kind: str,
    review_state: str,
    artifacts: dict[str, ArtifactRef | None],
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "session_id": session_id,
        "input_kind": input_kind,
        "review_state": review_state,
        "artifacts": {
            name: artifact.to_json() if artifact is not None else None
            for name, artifact in artifacts.items()
        },
        "warnings": list(warnings or []),
        "created_by": CREATED_BY,
    }


def build_reviewed_cha_package(
    *,
    session_id: str,
    reviewed_cha_path: str | Path,
    output_root: str | Path,
) -> Path:
    source_path = Path(reviewed_cha_path)
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    package_dir = Path(output_root) / session_id
    package_dir.mkdir(parents=True, exist_ok=True)

    reviewed_path = package_dir / "reviewed.cha"
    shutil.copyfile(source_path, reviewed_path)

    parsed = parse_cha_file(reviewed_path)
    extracted = extract_transcript_features(parsed)

    linguistic_payload = {
        "schema_version": extracted["feature_schema_version"],
        "source": "reviewed_transcript_source",
        "feature_groups": {
            "canonical_features": extracted["canonical_features"],
            "optional_indicators": extracted["optional_indicators"],
            "feature_aliases": extracted["feature_aliases"],
        },
        "review_flags": extracted.get("review_flags", []),
        "safety_labels": extracted.get("safety_labels", []),
    }
    acoustic_payload = {
        "schema_version": "acoustic-context-v1",
        "source": "not_provided",
        "available": False,
        "features": {},
        "warnings": ["No linked audio artifact was provided for acoustic context extraction."],
    }
    qa_payload = _qa_report_from_parsed_cha(parsed)
    provenance_payload = {
        "schema_version": "clinical-speech-provenance-v1",
        "source_input": {
            "kind": "reviewed_cha",
            "path": str(source_path),
        },
        "pipeline": {
            "name": "Clinical Speech Artifact Pipeline",
            "mode": "offline_cli",
            "ml_decision_support_invoked": False,
        },
        "components": {
            "cha_parser": "packages.cha.parser",
            "feature_extractor": "packages.features.transcript_features",
        },
    }

    write_json(package_dir / "linguistic_features.json", linguistic_payload)
    write_json(package_dir / "acoustic_context.json", acoustic_payload)
    write_json(package_dir / "qa_report.json", qa_payload)
    write_json(package_dir / "provenance.json", provenance_payload)

    artifacts = {
        "asr_draft": None,
        "reviewed_cha": _artifact_ref(package_dir, reviewed_path),
        "linguistic_features": _artifact_ref(package_dir, package_dir / "linguistic_features.json"),
        "acoustic_context": _artifact_ref(package_dir, package_dir / "acoustic_context.json"),
        "qa_report": _artifact_ref(package_dir, package_dir / "qa_report.json"),
        "provenance": _artifact_ref(package_dir, package_dir / "provenance.json"),
    }
    manifest = build_manifest(
        session_id=session_id,
        input_kind="reviewed_cha",
        review_state="reviewed_attested",
        artifacts=artifacts,
        warnings=acoustic_payload["warnings"],
    )
    write_json(package_dir / "manifest.json", manifest)
    return package_dir


def _artifact_ref(package_dir: Path, artifact_path: Path) -> ArtifactRef:
    return ArtifactRef(
        path=str(artifact_path.relative_to(package_dir)),
        sha256=sha256_file(artifact_path),
    )


def _qa_report_from_parsed_cha(parsed) -> dict[str, Any]:
    child_count = sum(1 for utterance in parsed.utterances if utterance.speaker_role == "child")
    adult_count = len(parsed.utterances) - child_count
    unknown_count = sum(1 for utterance in parsed.utterances if utterance.speaker_code == "UNK")
    timestamped_count = sum(
        1
        for utterance in parsed.utterances
        if utterance.start_ms is not None and utterance.end_ms is not None
    )
    warnings: list[str] = []
    if child_count == 0:
        warnings.append("No CHI child utterances were found.")
    if unknown_count:
        warnings.append("Unknown speaker utterances are present.")
    return {
        "schema_version": "clinical-speech-qa-v1",
        "source": "reviewed_transcript_source",
        "utterance_count": len(parsed.utterances),
        "child_utterance_count": child_count,
        "adult_utterance_count": adult_count,
        "unknown_speaker_count": unknown_count,
        "timestamped_utterance_count": timestamped_count,
        "warnings": warnings,
        "validation_issues": [],
    }
