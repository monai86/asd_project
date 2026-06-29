from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_staging_verification_env.sh"


def _write_env(tmp_path: Path, **overrides: str) -> Path:
    values = {
        "STAGING_API_BASE_URL": "https://staging-api.example.com/api/v1",
        "STAGING_APP_BASE_URL": "https://staging-app.example.com",
        "STAGING_SUPABASE_PROJECT_REF": "cbhwxklvcpgizeqriqxi",
        "ORG_A_ID": "org-real-a",
        "ORG_B_ID": "org-real-b",
        "ORG_A_CASE_ID": "case-real-a-001",
        "ORG_B_CASE_ID": "case-real-b-001",
        "TOKEN_THERAPIST_A_ASSIGNED": "aaa.bbb.ccc",
        "TOKEN_THERAPIST_A_UNASSIGNED": "ddd.eee.fff",
        "TOKEN_SUPERVISOR_A": "ggg.hhh.iii",
        "TOKEN_ORG_ADMIN_A": "jjj.kkk.lll",
        "TOKEN_PLATFORM_OPERATOR_A": "mmm.nnn.ooo",
        "TOKEN_THERAPIST_B_ASSIGNED": "ppp.qqq.rrr",
    }
    values.update(overrides)
    env_file = tmp_path / "staging.env"
    env_file.write_text(
        "\n".join(f'export {key}="{value}"' for key, value in values.items()) + "\n",
        encoding="utf-8",
    )
    return env_file


def test_staging_verification_env_validator_accepts_valid_env_file(tmp_path: Path) -> None:
    env_file = _write_env(tmp_path)

    result = subprocess.run(
        ["bash", str(SCRIPT), str(env_file)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Staging verification environment is ready." in result.stdout


def test_staging_verification_env_validator_rejects_non_api_base_url(tmp_path: Path) -> None:
    env_file = _write_env(tmp_path, STAGING_API_BASE_URL="https://staging-api.example.com")

    result = subprocess.run(
        ["bash", str(SCRIPT), str(env_file)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "expected suffix /api/v1" in result.stderr


def test_staging_verification_env_validator_rejects_non_jwt_token_shape(tmp_path: Path) -> None:
    env_file = _write_env(tmp_path, TOKEN_ORG_ADMIN_A="not-a-jwt")

    result = subprocess.run(
        ["bash", str(SCRIPT), str(env_file)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "expected JWT-like token shape" in result.stderr
