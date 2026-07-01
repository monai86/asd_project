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
