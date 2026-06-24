import pytest

from app.repositories.mock_repository import MockRepository
from app.services.audit_safety import AuditSafetyError, validate_audit_event


def test_repository_audit_event_has_production_shape_without_clinical_content():
    repo = MockRepository()

    repo.add_audit("report.sign_off", "report_123", "Report signed off.", actor_id="user_123", correlation_id="req_123")

    event = repo.audit_log[-1]
    assert event["actor_id"] == "user_123"
    assert event["action"] == "report.sign_off"
    assert event["target_id"] == "report_123"
    assert event["outcome"] == "success"
    assert event["correlation_id"] == "req_123"
    assert event["timestamp"]
    assert "clinical_content" not in event


def test_audit_event_blocks_clinical_content_without_echoing_it():
    with pytest.raises(AuditSafetyError) as error:
        validate_audit_event(
            actor_id="user_123",
            action="transcript.patch",
            target_id="transcript_123",
            outcome="success",
            correlation_id="req_123",
            message="Updated transcript CHI: I want blue truck.",
        )

    assert "blue truck" not in str(error.value)
    assert "CHI:" not in str(error.value)
