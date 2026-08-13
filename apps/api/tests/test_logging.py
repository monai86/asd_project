import logging

from fastapi.testclient import TestClient

from app.core.logging import sanitize_log_path
from app.main import app


client = TestClient(app)


def test_request_logging_uses_route_template_without_record_ids(caplog):
    caplog.set_level(logging.INFO, logger="therapist_app_v2.request")

    client.get("/api/v1/cases/nonexistent-case-id/timeline")

    records = [record for record in caplog.records if record.name == "therapist_app_v2.request"]
    assert records
    logged_path = getattr(records[-1], "path")
    assert logged_path == "/api/v1/cases/{case_id}/timeline"
    assert "nonexistent-case-id" not in logged_path


def test_sanitize_log_path_redacts_unknown_sensitive_segments():
    raw_path = "/api/v1/audio/private/org-123/child-Somchai/storage_key=session/audio.raw"

    sanitized = sanitize_log_path(raw_path)

    assert "Somchai" not in sanitized
    assert "storage_key" not in sanitized
    assert "audio.raw" not in sanitized
    assert sanitized == "/api/v1/audio/private/[redacted]/[redacted]/[redacted]/[redacted]"


def test_request_log_record_keeps_sensitive_path_values_out_of_structured_fields(caplog):
    caplog.set_level(logging.INFO, logger="therapist_app_v2.request")

    client.get("/api/v1/cases/C-CHILD-SECRET/transcripts")

    records = [record for record in caplog.records if record.name == "therapist_app_v2.request"]
    assert records
    assert "C-CHILD-SECRET" not in getattr(records[-1], "path")
    assert "C-CHILD-SECRET" not in "\n".join(record.getMessage() for record in records)
