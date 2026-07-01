from pathlib import Path


def test_secret_rotation_runbook_covers_production_gate_rotation_and_rollback():
    content = Path("docs/SECRET_ROTATION_RUNBOOK.md").read_text(encoding="utf-8")

    required_terms = [
        "managed secret store",
        "LINGUALENS_SECRET_STORE_PROVIDER",
        "LINGUALENS_CREDENTIAL_ROTATION_RUNBOOK",
        "Rotate service credentials at least every 90 days",
        "Rollback",
        "Do not paste real secrets",
    ]
    for term in required_terms:
        assert term in content

    assert "sk-" not in content
    assert "password=" not in content.lower()
