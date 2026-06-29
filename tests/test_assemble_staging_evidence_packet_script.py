from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "assemble_staging_evidence_packet.sh"


def test_assemble_staging_evidence_packet_uses_base_url_aliases(tmp_path: Path) -> None:
    output_dir = tmp_path / "packet"
    env = os.environ.copy()
    env.update(
        {
            "OUTPUT_DIR": str(output_dir),
            "STAGING_API_BASE_URL": "https://staging-api.example.com/api/v1",
            "STAGING_APP_BASE_URL": "https://staging-app.example.com",
            "PACKET_RESULT": "pass",
            "OPERATOR_NAME": "Test Operator",
        }
    )

    result = subprocess.run(
        ["bash", str(SCRIPT), "alias-check"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    packet_path = Path(result.stdout.strip())
    assert packet_path.is_file()
    content = packet_path.read_text(encoding="utf-8")
    assert "- Staging API URL: https://staging-api.example.com/api/v1" in content
    assert "- Staging therapist app URL: https://staging-app.example.com" in content
