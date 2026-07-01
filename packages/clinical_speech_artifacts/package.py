"""Stable artifact package contract for the Clinical Speech Artifact Pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


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
