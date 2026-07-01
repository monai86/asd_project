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
