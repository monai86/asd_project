# Clinical Speech Artifact Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an offline Clinical Speech Artifact Package contract and CLI that turns a reviewed `.cha` file, and later an audio-derived ASR draft, into auditable transcript, feature, QA, and provenance artifacts without invoking ML decision support.

**Architecture:** Start with a local/offline package builder under `packages/clinical_speech_artifacts` and a repository-root CLI in `scripts/`. The first implementation path accepts reviewed CHAT (`.cha`) and writes a stable package folder; the audio path can be added after the contract is test-covered, using existing `src/audio_pipeline` code and keeping ASR output labeled as a draft.

**Tech Stack:** Python 3, `dataclasses`, `json`, `pathlib`, existing `packages.cha`, existing `packages.features`, pytest, repository-root `rtk` command wrapper.

---

## Context For Zcode

Read these files before implementation:

- `AGENTS.md`
- `docs/PROJECT_SOURCE_OF_TRUTH.md`
- `CONTEXT.md`
- `docs/AUDIO_PIPELINE.md`
- `docs/adr/0009-use-reviewed-transcript-lines-as-clinical-speech-source.md`
- `docs/adr/0010-store-clinical-speech-artifact-content-outside-primary-records.md`
- `docs/adr/0012-separate-research-model-results-from-decision-support.md`

Current decisions already made:

- Canonical term: `Clinical Speech Artifact Pipeline`
- Trusted source: `Reviewed Transcript Source`, not the raw ASR draft and not a stale `.cha` snapshot
- Normal workflow gate: no feature extraction from unattested ASR draft
- Output unit: `Clinical Speech Artifact Package`
- First deliverable: offline CLI/package contract
- Explicit non-goal: no ML decision support, no diagnosis, no ASD probability, no production deploy/runtime changes

Current dirty worktree notes:

- There may be unrelated dirty files from Supabase/project setup work.
- Do not revert, stage, or commit unrelated files.
- Keep this work scoped to the files listed in this plan.

## Package Contract

The package folder for a session is:

```text
artifacts/clinical_speech/<session_id>/
  manifest.json
  reviewed.cha
  linguistic_features.json
  acoustic_context.json
  qa_report.json
  provenance.json
```

When the source is an audio-derived ASR run, the package also includes:

```text
  asr_draft.cha
```

Do not fabricate `asr_draft.cha` for a reviewed-CHA-only run. The manifest must record that the draft artifact is absent.

Minimum `manifest.json` shape:

```json
{
  "schema_version": "clinical-speech-artifact-package-v1",
  "session_id": "session-fixture",
  "input_kind": "reviewed_cha",
  "review_state": "reviewed_attested",
  "artifacts": {
    "asr_draft": null,
    "reviewed_cha": {
      "path": "reviewed.cha",
      "sha256": "64 lowercase hex chars"
    },
    "linguistic_features": {
      "path": "linguistic_features.json",
      "sha256": "64 lowercase hex chars"
    },
    "acoustic_context": {
      "path": "acoustic_context.json",
      "sha256": "64 lowercase hex chars"
    },
    "qa_report": {
      "path": "qa_report.json",
      "sha256": "64 lowercase hex chars"
    },
    "provenance": {
      "path": "provenance.json",
      "sha256": "64 lowercase hex chars"
    }
  },
  "warnings": [],
  "created_by": "scripts/build_clinical_speech_artifact_package.py"
}
```

Minimum `linguistic_features.json` shape:

```json
{
  "schema_version": "features-basic-v1",
  "source": "reviewed_transcript_source",
  "feature_groups": {
    "canonical_features": {},
    "optional_indicators": {},
    "feature_aliases": {}
  },
  "review_flags": [],
  "safety_labels": []
}
```

Minimum `acoustic_context.json` shape when no audio is provided:

```json
{
  "schema_version": "acoustic-context-v1",
  "source": "not_provided",
  "available": false,
  "features": {},
  "warnings": ["No linked audio artifact was provided for acoustic context extraction."]
}
```

Minimum `qa_report.json` shape:

```json
{
  "schema_version": "clinical-speech-qa-v1",
  "source": "reviewed_transcript_source",
  "utterance_count": 2,
  "child_utterance_count": 1,
  "adult_utterance_count": 1,
  "unknown_speaker_count": 0,
  "timestamped_utterance_count": 2,
  "warnings": [],
  "validation_issues": []
}
```

Minimum `provenance.json` shape:

```json
{
  "schema_version": "clinical-speech-provenance-v1",
  "source_input": {
    "kind": "reviewed_cha",
    "path": "tests/fixtures/reference_feature_parity/english_toyplay.cha"
  },
  "pipeline": {
    "name": "Clinical Speech Artifact Pipeline",
    "mode": "offline_cli",
    "ml_decision_support_invoked": false
  },
  "components": {
    "cha_parser": "packages.cha.parser",
    "feature_extractor": "packages.features.transcript_features"
  }
}
```

## File Structure

Create:

- `packages/clinical_speech_artifacts/__init__.py`
- `packages/clinical_speech_artifacts/package.py`
- `scripts/build_clinical_speech_artifact_package.py`
- `tests/test_clinical_speech_artifact_package.py`
- `tests/test_build_clinical_speech_artifact_package_script.py`

Modify:

- `docs/AUDIO_PIPELINE.md` only if implementation changes the documented CLI command or package shape.

Do not modify:

- `apps/api/`
- `apps/lingualens-app/`
- `packages/ml/`
- production deployment docs
- Supabase/Render/env migration files

## Task 1: Add The Artifact Package Contract

**Files:**
- Create: `packages/clinical_speech_artifacts/__init__.py`
- Create: `packages/clinical_speech_artifacts/package.py`
- Test: `tests/test_clinical_speech_artifact_package.py`

- [ ] **Step 1: Write the failing contract tests**

Create `tests/test_clinical_speech_artifact_package.py`:

```python
from pathlib import Path

from packages.clinical_speech_artifacts.package import (
    ArtifactRef,
    build_manifest,
    sha256_file,
    write_json,
)


def test_sha256_file_returns_lowercase_hex(tmp_path: Path):
    path = tmp_path / "sample.txt"
    path.write_text("hello\n", encoding="utf-8")

    digest = sha256_file(path)

    assert len(digest) == 64
    assert digest == digest.lower()
    assert digest == "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"


def test_write_json_uses_stable_indented_utf8(tmp_path: Path):
    path = tmp_path / "payload.json"

    write_json(path, {"b": 2, "a": 1})

    assert path.read_text(encoding="utf-8") == '{\n  "a": 1,\n  "b": 2\n}\n'


def test_build_manifest_records_relative_paths_and_absent_asr_draft():
    manifest = build_manifest(
        session_id="session-fixture",
        input_kind="reviewed_cha",
        review_state="reviewed_attested",
        artifacts={
            "asr_draft": None,
            "reviewed_cha": ArtifactRef(path="reviewed.cha", sha256="a" * 64),
            "linguistic_features": ArtifactRef(path="linguistic_features.json", sha256="b" * 64),
            "acoustic_context": ArtifactRef(path="acoustic_context.json", sha256="c" * 64),
            "qa_report": ArtifactRef(path="qa_report.json", sha256="d" * 64),
            "provenance": ArtifactRef(path="provenance.json", sha256="e" * 64),
        },
        warnings=["No linked audio artifact was provided for acoustic context extraction."],
    )

    assert manifest["schema_version"] == "clinical-speech-artifact-package-v1"
    assert manifest["session_id"] == "session-fixture"
    assert manifest["artifacts"]["asr_draft"] is None
    assert manifest["artifacts"]["reviewed_cha"]["path"] == "reviewed.cha"
    assert manifest["created_by"] == "scripts/build_clinical_speech_artifact_package.py"
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run:

```bash
rtk python3 -m pytest tests/test_clinical_speech_artifact_package.py -q
```

Expected: FAIL because `packages.clinical_speech_artifacts` does not exist.

- [ ] **Step 3: Add the contract implementation**

Create `packages/clinical_speech_artifacts/__init__.py`:

```python
"""Clinical Speech Artifact Package helpers."""

from .package import ArtifactRef, build_manifest, sha256_file, write_json

__all__ = [
    "ArtifactRef",
    "build_manifest",
    "sha256_file",
    "write_json",
]
```

Create `packages/clinical_speech_artifacts/package.py`:

```python
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
```

- [ ] **Step 4: Run the contract tests**

Run:

```bash
rtk python3 -m pytest tests/test_clinical_speech_artifact_package.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add packages/clinical_speech_artifacts tests/test_clinical_speech_artifact_package.py
rtk git commit -m "feat: add clinical speech artifact package contract"
```

## Task 2: Build Reviewed-CHA Package Creation

**Files:**
- Modify: `packages/clinical_speech_artifacts/package.py`
- Test: `tests/test_clinical_speech_artifact_package.py`

- [ ] **Step 1: Add failing package builder test**

Append to `tests/test_clinical_speech_artifact_package.py`:

```python
import json

from packages.clinical_speech_artifacts.package import build_reviewed_cha_package


def test_build_reviewed_cha_package_writes_expected_artifacts(tmp_path: Path):
    source = Path("tests/fixtures/reference_feature_parity/english_toyplay.cha")
    package_dir = build_reviewed_cha_package(
        session_id="session-fixture",
        reviewed_cha_path=source,
        output_root=tmp_path,
    )

    assert package_dir == tmp_path / "session-fixture"
    assert (package_dir / "manifest.json").exists()
    assert (package_dir / "reviewed.cha").exists()
    assert not (package_dir / "asr_draft.cha").exists()
    assert (package_dir / "linguistic_features.json").exists()
    assert (package_dir / "acoustic_context.json").exists()
    assert (package_dir / "qa_report.json").exists()
    assert (package_dir / "provenance.json").exists()

    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    qa_report = json.loads((package_dir / "qa_report.json").read_text(encoding="utf-8"))
    acoustic = json.loads((package_dir / "acoustic_context.json").read_text(encoding="utf-8"))
    provenance = json.loads((package_dir / "provenance.json").read_text(encoding="utf-8"))

    assert manifest["artifacts"]["asr_draft"] is None
    assert manifest["input_kind"] == "reviewed_cha"
    assert qa_report["utterance_count"] > 0
    assert qa_report["child_utterance_count"] > 0
    assert acoustic["available"] is False
    assert provenance["pipeline"]["ml_decision_support_invoked"] is False
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
rtk python3 -m pytest tests/test_clinical_speech_artifact_package.py::test_build_reviewed_cha_package_writes_expected_artifacts -q
```

Expected: FAIL because `build_reviewed_cha_package` does not exist.

- [ ] **Step 3: Implement reviewed-CHA package creation**

Append these imports near the top of `packages/clinical_speech_artifacts/package.py`:

```python
import shutil

from packages.cha import parse_cha_file
from packages.features import extract_transcript_features
```

Append these functions to `packages/clinical_speech_artifacts/package.py`:

```python
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
```

Update `packages/clinical_speech_artifacts/__init__.py` exports:

```python
"""Clinical Speech Artifact Package helpers."""

from .package import (
    ArtifactRef,
    build_manifest,
    build_reviewed_cha_package,
    sha256_file,
    write_json,
)

__all__ = [
    "ArtifactRef",
    "build_manifest",
    "build_reviewed_cha_package",
    "sha256_file",
    "write_json",
]
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
rtk python3 -m pytest tests/test_clinical_speech_artifact_package.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add packages/clinical_speech_artifacts tests/test_clinical_speech_artifact_package.py
rtk git commit -m "feat: build reviewed CHA artifact packages"
```

## Task 3: Add The Offline CLI

**Files:**
- Create: `scripts/build_clinical_speech_artifact_package.py`
- Test: `tests/test_build_clinical_speech_artifact_package_script.py`

- [ ] **Step 1: Write failing CLI test**

Create `tests/test_build_clinical_speech_artifact_package_script.py`:

```python
import json
import subprocess
import sys
from pathlib import Path


def test_cli_builds_reviewed_cha_package(tmp_path: Path):
    output_root = tmp_path / "clinical_speech"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_clinical_speech_artifact_package.py",
            "--session-id",
            "session-cli",
            "--reviewed-cha",
            "tests/fixtures/reference_feature_parity/english_toyplay.cha",
            "--output-root",
            str(output_root),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    package_dir = output_root / "session-cli"
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["session_id"] == "session-cli"
    assert manifest["input_kind"] == "reviewed_cha"
    assert "created package:" in result.stdout
```

- [ ] **Step 2: Run the CLI test and confirm it fails**

Run:

```bash
rtk python3 -m pytest tests/test_build_clinical_speech_artifact_package_script.py -q
```

Expected: FAIL because the script does not exist.

- [ ] **Step 3: Implement the CLI**

Create `scripts/build_clinical_speech_artifact_package.py`:

```python
#!/usr/bin/env python3
"""Build an offline Clinical Speech Artifact Package."""

from __future__ import annotations

import argparse
from pathlib import Path

from packages.clinical_speech_artifacts import build_reviewed_cha_package


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Clinical Speech Artifact Package from reviewed CHAT."
    )
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--reviewed-cha", required=True, type=Path)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/clinical_speech"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package_dir = build_reviewed_cha_package(
        session_id=args.session_id,
        reviewed_cha_path=args.reviewed_cha,
        output_root=args.output_root,
    )
    print(f"created package: {package_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the CLI test**

Run:

```bash
rtk python3 -m pytest tests/test_build_clinical_speech_artifact_package_script.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add scripts/build_clinical_speech_artifact_package.py tests/test_build_clinical_speech_artifact_package_script.py
rtk git commit -m "feat: add clinical speech artifact package CLI"
```

## Task 4: Add Audio-Aware Acoustic Context

**Files:**
- Modify: `packages/clinical_speech_artifacts/package.py`
- Modify: `scripts/build_clinical_speech_artifact_package.py`
- Test: `tests/test_clinical_speech_artifact_package.py`
- Test: `tests/test_build_clinical_speech_artifact_package_script.py`

- [ ] **Step 1: Add failing audio context test**

Append to `tests/test_clinical_speech_artifact_package.py`:

```python
import wave


def _write_silence_wav(path: Path, *, seconds: float = 0.25, sample_rate: int = 16000):
    frame_count = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frame_count)


def test_build_reviewed_cha_package_includes_acoustic_context_when_audio_is_provided(tmp_path: Path):
    audio_path = tmp_path / "session.wav"
    _write_silence_wav(audio_path)

    package_dir = build_reviewed_cha_package(
        session_id="session-audio",
        reviewed_cha_path=Path("tests/fixtures/reference_feature_parity/english_toyplay.cha"),
        output_root=tmp_path / "packages",
        audio_path=audio_path,
    )

    acoustic = json.loads((package_dir / "acoustic_context.json").read_text(encoding="utf-8"))
    assert acoustic["available"] is True
    assert acoustic["source"] == "linked_audio_artifact"
    assert "duration_sec" in acoustic["features"]
```

- [ ] **Step 2: Run the new test and confirm it fails**

Run:

```bash
rtk python3 -m pytest tests/test_clinical_speech_artifact_package.py::test_build_reviewed_cha_package_includes_acoustic_context_when_audio_is_provided -q
```

Expected: FAIL because `audio_path` is not accepted.

- [ ] **Step 3: Implement audio context extraction**

Update the function signature in `packages/clinical_speech_artifacts/package.py`:

```python
def build_reviewed_cha_package(
    *,
    session_id: str,
    reviewed_cha_path: str | Path,
    output_root: str | Path,
    audio_path: str | Path | None = None,
) -> Path:
```

Add this import:

```python
from packages.features import extract_acoustic_features, extract_transcript_features
```

Replace the current `acoustic_payload` block with:

```python
    acoustic_payload = _acoustic_context_payload(audio_path)
```

Append this function:

```python
def _acoustic_context_payload(audio_path: str | Path | None) -> dict[str, Any]:
    if audio_path is None:
        return {
            "schema_version": "acoustic-context-v1",
            "source": "not_provided",
            "available": False,
            "features": {},
            "warnings": ["No linked audio artifact was provided for acoustic context extraction."],
        }

    resolved_audio_path = Path(audio_path)
    features = extract_acoustic_features(resolved_audio_path)
    return {
        "schema_version": "acoustic-context-v1",
        "source": "linked_audio_artifact",
        "available": True,
        "features": features,
        "warnings": [],
    }
```

- [ ] **Step 4: Wire CLI `--audio` argument**

Update `scripts/build_clinical_speech_artifact_package.py`:

```python
    parser.add_argument("--audio", type=Path, default=None)
```

Update the builder call:

```python
    package_dir = build_reviewed_cha_package(
        session_id=args.session_id,
        reviewed_cha_path=args.reviewed_cha,
        output_root=args.output_root,
        audio_path=args.audio,
    )
```

- [ ] **Step 5: Add CLI audio argument assertion**

Append to `tests/test_build_clinical_speech_artifact_package_script.py`:

```python
def test_cli_accepts_audio_argument(tmp_path: Path):
    audio_path = tmp_path / "session.wav"
    import wave
    with wave.open(str(audio_path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * 4000)

    output_root = tmp_path / "clinical_speech"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_clinical_speech_artifact_package.py",
            "--session-id",
            "session-cli-audio",
            "--reviewed-cha",
            "tests/fixtures/reference_feature_parity/english_toyplay.cha",
            "--audio",
            str(audio_path),
            "--output-root",
            str(output_root),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    acoustic = json.loads(
        (output_root / "session-cli-audio" / "acoustic_context.json").read_text(encoding="utf-8")
    )
    assert acoustic["available"] is True
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
rtk python3 -m pytest tests/test_clinical_speech_artifact_package.py tests/test_build_clinical_speech_artifact_package_script.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
rtk git add packages/clinical_speech_artifacts scripts/build_clinical_speech_artifact_package.py tests/test_clinical_speech_artifact_package.py tests/test_build_clinical_speech_artifact_package_script.py
rtk git commit -m "feat: add acoustic context to speech artifact packages"
```

## Task 5: Add Optional ASR Draft CHAT Input

**Files:**
- Modify: `packages/clinical_speech_artifacts/package.py`
- Modify: `scripts/build_clinical_speech_artifact_package.py`
- Test: `tests/test_clinical_speech_artifact_package.py`
- Test: `tests/test_build_clinical_speech_artifact_package_script.py`

- [ ] **Step 1: Add failing ASR draft artifact test**

Append to `tests/test_clinical_speech_artifact_package.py`:

```python
def test_build_reviewed_cha_package_can_include_asr_draft_artifact(tmp_path: Path):
    source = Path("tests/fixtures/reference_feature_parity/english_toyplay.cha")
    draft = tmp_path / "draft.cha"
    draft.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    package_dir = build_reviewed_cha_package(
        session_id="session-with-draft",
        reviewed_cha_path=source,
        output_root=tmp_path / "packages",
        asr_draft_cha_path=draft,
    )

    assert (package_dir / "asr_draft.cha").exists()
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifacts"]["asr_draft"]["path"] == "asr_draft.cha"
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
rtk python3 -m pytest tests/test_clinical_speech_artifact_package.py::test_build_reviewed_cha_package_can_include_asr_draft_artifact -q
```

Expected: FAIL because `asr_draft_cha_path` is not accepted.

- [ ] **Step 3: Implement optional ASR draft copy**

Update the function signature:

```python
def build_reviewed_cha_package(
    *,
    session_id: str,
    reviewed_cha_path: str | Path,
    output_root: str | Path,
    audio_path: str | Path | None = None,
    asr_draft_cha_path: str | Path | None = None,
) -> Path:
```

After copying `reviewed.cha`, add:

```python
    draft_path: Path | None = None
    if asr_draft_cha_path is not None:
        source_draft_path = Path(asr_draft_cha_path)
        if not source_draft_path.exists():
            raise FileNotFoundError(source_draft_path)
        draft_path = package_dir / "asr_draft.cha"
        shutil.copyfile(source_draft_path, draft_path)
```

Change the manifest artifacts entry:

```python
        "asr_draft": _artifact_ref(package_dir, draft_path) if draft_path is not None else None,
```

- [ ] **Step 4: Wire CLI `--asr-draft-cha` argument**

Update `scripts/build_clinical_speech_artifact_package.py`:

```python
    parser.add_argument("--asr-draft-cha", type=Path, default=None)
```

Update the builder call:

```python
        asr_draft_cha_path=args.asr_draft_cha,
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
rtk python3 -m pytest tests/test_clinical_speech_artifact_package.py tests/test_build_clinical_speech_artifact_package_script.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add packages/clinical_speech_artifacts scripts/build_clinical_speech_artifact_package.py tests/test_clinical_speech_artifact_package.py tests/test_build_clinical_speech_artifact_package_script.py
rtk git commit -m "feat: include optional ASR draft artifacts"
```

## Task 6: Document The CLI For Operators

**Files:**
- Modify: `docs/AUDIO_PIPELINE.md`

- [ ] **Step 1: Add the package builder command to the Quickstart**

Add this subsection after the existing CLI example in `docs/AUDIO_PIPELINE.md`:

````markdown
### Clinical Speech Artifact Package

Build an offline package from a reviewed `.cha` file:

```bash
python3 scripts/build_clinical_speech_artifact_package.py \
  --session-id demo-session \
  --reviewed-cha tests/fixtures/reference_feature_parity/english_toyplay.cha \
  --output-root artifacts/clinical_speech
```

With linked audio context:

```bash
python3 scripts/build_clinical_speech_artifact_package.py \
  --session-id demo-session \
  --reviewed-cha reviewed.cha \
  --audio session.wav \
  --output-root artifacts/clinical_speech
```

With an ASR draft retained for provenance:

```bash
python3 scripts/build_clinical_speech_artifact_package.py \
  --session-id demo-session \
  --asr-draft-cha asr_draft.cha \
  --reviewed-cha reviewed.cha \
  --audio session.wav \
  --output-root artifacts/clinical_speech
```

The package is an offline artifact contract. It does not invoke ML decision
support and does not produce diagnosis, ASD probability, or clinical validation
claims.
````

- [ ] **Step 2: Run docs grep sanity check**

Run:

```bash
rtk rg -n "diagnosis pipeline|ML screening pipeline|screening risk estimate" docs/AUDIO_PIPELINE.md
```

Expected: no matches.

- [ ] **Step 3: Commit**

```bash
rtk git add docs/AUDIO_PIPELINE.md
rtk git commit -m "docs: document clinical speech artifact package CLI"
```

## Task 7: Full Local Verification

**Files:**
- No code changes expected.

- [ ] **Step 1: Run focused package tests**

Run:

```bash
rtk python3 -m pytest tests/test_clinical_speech_artifact_package.py tests/test_build_clinical_speech_artifact_package_script.py -q
```

Expected: PASS.

- [ ] **Step 2: Run existing related tests**

Run:

```bash
rtk python3 -m pytest tests/test_reference_feature_parity.py tests/test_cha_reference_cohort_pipeline.py tests/test_acoustic_profile.py -q
```

Expected: PASS.

- [ ] **Step 3: Run one manual CLI smoke command**

Run:

```bash
rtk python3 scripts/build_clinical_speech_artifact_package.py \
  --session-id smoke-reviewed-cha \
  --reviewed-cha tests/fixtures/reference_feature_parity/english_toyplay.cha \
  --output-root /tmp/lingualens-clinical-speech-artifacts
```

Expected:

```text
created package: /tmp/lingualens-clinical-speech-artifacts/smoke-reviewed-cha
```

- [ ] **Step 4: Inspect generated manifest**

Run:

```bash
rtk python3 -m json.tool /tmp/lingualens-clinical-speech-artifacts/smoke-reviewed-cha/manifest.json
```

Expected: JSON includes `"ml_decision_support_invoked": false` in `provenance.json`, and `manifest.json` records `asr_draft` as `null`.

- [ ] **Step 5: Commit verification-only doc changes if any were needed**

If Task 7 required documentation corrections, commit only those documentation corrections:

```bash
rtk git add docs/AUDIO_PIPELINE.md
rtk git commit -m "docs: clarify speech artifact package verification"
```

If Task 7 required no file changes, skip this commit.

## Task 8: Zcode Handoff Checklist

**Files:**
- No code changes expected.

- [ ] **Step 1: Confirm changed files are scoped**

Run:

```bash
rtk git status --short
```

Expected: changed files are limited to:

```text
packages/clinical_speech_artifacts/
scripts/build_clinical_speech_artifact_package.py
tests/test_clinical_speech_artifact_package.py
tests/test_build_clinical_speech_artifact_package_script.py
docs/AUDIO_PIPELINE.md
```

Existing unrelated dirty files may remain. Do not add them to these commits.

- [ ] **Step 2: Confirm ML decision support was not wired**

Run:

```bash
rtk rg -n "packages.ml|ml_providers|Reference Cohort|Screening Support Score|screening risk estimate" packages/clinical_speech_artifacts scripts/build_clinical_speech_artifact_package.py tests/test_clinical_speech_artifact_package.py tests/test_build_clinical_speech_artifact_package_script.py
```

Expected: no matches.

- [ ] **Step 3: Confirm no clinical content was added to fixtures**

Run:

```bash
rtk rg -n "first name|last name|phone|email|address|school|diagnosis|ASD probability" tests/fixtures tests/test_clinical_speech_artifact_package.py tests/test_build_clinical_speech_artifact_package_script.py
```

Expected: no matches.

- [ ] **Step 4: Final handoff summary**

Write the final handoff summary with:

```text
Implemented offline Clinical Speech Artifact Package contract and CLI.
Verified reviewed-CHA packaging, optional ASR draft retention, acoustic context, QA report, provenance, and manifest checksums.
ML decision support was not invoked or wired.
```

## Nice Ideas To Add After The Contract Is Stable

Keep these out of the first implementation unless the contract tasks above are complete:

- ASR confidence heatmap: add a `review_attention.json` artifact that ranks utterances by low confidence, unknown speaker, missing timestamp, long silence, and unclear marker.
- Speaker uncertainty report: add per-speaker counts and confidence bands so therapist review can focus on lines likely to affect `CHI`-dependent features.
- Feature drift report: compare ASR draft features against reviewed features after attestation and report which descriptive values changed most. This is a QA artifact, not a clinical interpretation.
- CHAT round-trip validator: parse `reviewed.cha`, export it again, parse the export, and verify utterance count, speaker labels, timestamps, and core text survive.
- Import adapter for `apps/api`: after the offline contract is stable, add a backend-only importer that maps package artifacts into existing transcript and feature records behind consent, auth, and audit gates.

## Self-Review

Spec coverage:

- Offline package contract: covered by Tasks 1-3.
- Reviewed transcript source boundary: covered by Task 2 and docs in Task 6.
- No feature extraction from unattested ASR draft: preserved by only extracting from `reviewed.cha`.
- Linguistic vs acoustic separation: covered by Task 2 and Task 4.
- Optional ASR draft retention: covered by Task 5.
- No ML decision support: covered by package provenance and Task 8 grep guard.

Placeholder scan:

- This plan uses no unresolved marker text, no open-ended validation instructions, and no unspecified test commands.

Type consistency:

- `ArtifactRef`, `build_manifest`, `write_json`, `sha256_file`, and `build_reviewed_cha_package` are introduced before use.
- Manifest artifact keys are consistent across tests and implementation: `asr_draft`, `reviewed_cha`, `linguistic_features`, `acoustic_context`, `qa_report`, and `provenance`.
