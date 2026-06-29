from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTH_CORE_SCRIPT = ROOT / "scripts" / "run_staging_auth_verifier_core_gate.sh"
TENANT_CORE_SCRIPT = ROOT / "scripts" / "run_staging_tenant_safety_core_gate.sh"


def _write_fake_auth_probe(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
scenario="$1"
mkdir -p "${OUTPUT_DIR:?}"
cat >"${OUTPUT_DIR}/${scenario}.meta.txt" <<EOF
scenario=${scenario}
result=pass
expected_status=200
status_code=200
sent_auth_header=true
EOF
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_fake_tenant_probe(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
scenario="$1"
mkdir -p "${OUTPUT_DIR:?}"
cat >"${OUTPUT_DIR}/${scenario}.meta.txt" <<EOF
scenario=${scenario}
result=pass
expected_status=200
status_code=200
EOF
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_fake_auth_summary(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
probe_dir="$1"
output_file="$2"
printf 'probe_dir=%s\\n' "$probe_dir" >"$output_file"
ls "$probe_dir"/*.meta.txt | xargs -n1 basename >>"$output_file"
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_fake_tenant_summary(path: Path) -> None:
    _write_fake_auth_summary(path)


def test_auth_core_gate_uses_run_specific_probe_subdirectory(tmp_path: Path) -> None:
    probe_script = tmp_path / "probe.sh"
    summary_script = tmp_path / "summary.sh"
    output_base_dir = tmp_path / "auth-probes"
    stale_meta = output_base_dir / "stale.meta.txt"
    output_base_dir.mkdir(parents=True)
    stale_meta.write_text("scenario=stale\n", encoding="utf-8")
    _write_fake_auth_probe(probe_script)
    _write_fake_auth_summary(summary_script)

    env = os.environ.copy()
    env.update(
        {
            "PROBE_SCRIPT": str(probe_script),
            "SUMMARY_SCRIPT": str(summary_script),
            "OUTPUT_BASE_DIR": str(output_base_dir),
            "RUN_STAMP": "run-001",
        }
    )

    result = subprocess.run(
        ["bash", str(AUTH_CORE_SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    run_dir = output_base_dir / "run-001"
    summary_file = run_dir / "run-001_core_gate_summary.md"
    assert run_dir.is_dir()
    assert summary_file.is_file()
    content = summary_file.read_text(encoding="utf-8")
    assert f"probe_dir={run_dir}" in content
    assert "accepted_aal2_case_read.meta.txt" in content
    assert "missing_bearer_case_read.meta.txt" in content
    assert "wrong_org_case_read.meta.txt" in content
    assert "stale.meta.txt" not in content


def test_tenant_core_gate_uses_run_specific_probe_subdirectory(tmp_path: Path) -> None:
    probe_script = tmp_path / "probe.sh"
    summary_script = tmp_path / "summary.sh"
    output_base_dir = tmp_path / "tenant-probes"
    stale_meta = output_base_dir / "stale.meta.txt"
    output_base_dir.mkdir(parents=True)
    stale_meta.write_text("scenario=stale\n", encoding="utf-8")
    _write_fake_tenant_probe(probe_script)
    _write_fake_tenant_summary(summary_script)

    env = os.environ.copy()
    env.update(
        {
            "PROBE_SCRIPT": str(probe_script),
            "SUMMARY_SCRIPT": str(summary_script),
            "OUTPUT_BASE_DIR": str(output_base_dir),
            "RUN_STAMP": "run-tenant-001",
        }
    )

    result = subprocess.run(
        ["bash", str(TENANT_CORE_SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    run_dir = output_base_dir / "run-tenant-001"
    summary_file = run_dir / "run-tenant-001_core_gate_summary.md"
    assert run_dir.is_dir()
    assert summary_file.is_file()
    content = summary_file.read_text(encoding="utf-8")
    assert f"probe_dir={run_dir}" in content
    assert "assigned_case_read.meta.txt" in content
    assert "platform_case_read.meta.txt" in content
    assert "stale.meta.txt" not in content
