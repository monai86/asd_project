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
