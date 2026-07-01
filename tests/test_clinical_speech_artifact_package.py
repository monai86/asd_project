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
