from pathlib import Path


def test_incident_response_runbook_contains_stop_rollout_criteria():
    runbook = Path("docs/INCIDENT_RESPONSE_RUNBOOK.md").read_text(encoding="utf-8")
    lower = runbook.lower()

    assert "stop rollout" in lower
    assert "cross-tenant exposure" in lower
    assert "consent bypass" in lower
    assert "audit loss" in lower
    assert "fabricated asr output" in lower
    assert "preserve audit" in lower
    assert "no child identifiers" in lower
