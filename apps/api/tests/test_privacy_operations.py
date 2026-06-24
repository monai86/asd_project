import json

from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository_singleton
from app.main import app


client = TestClient(app)
ADMIN_HEADERS = {"x-mock-role": "admin", "x-mock-user-id": "privacy-admin"}


def test_deletion_review_cannot_complete_while_legal_hold_is_active():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-PRIVACY-HOLD", "age_months": 58, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    request = client.post(
        f"/api/v1/cases/{case_id}/privacy-requests",
        json={
            "operation_type": "deletion_review",
            "reason": "Guardian deletion request.",
            "retention_days": 90,
            "legal_hold": True,
        },
    )
    assert request.status_code == 200
    operation = request.json()
    assert operation["deletion_review_required"] is True
    assert operation["legal_hold"] is True
    assert operation["retention_days"] == 90
    assert operation["eligible_for_deletion_at"] is not None

    completed = client.patch(
        f"/api/v1/privacy/requests/{operation['privacy_operation_id']}",
        headers=ADMIN_HEADERS,
        json={"status": "completed", "admin_note": "Reviewed by privacy admin."},
    )

    assert completed.status_code == 400
    assert completed.json()["detail"] == "Deletion review cannot be completed while legal hold is active."


def test_completed_deletion_review_preserves_audit_and_signed_report_evidence():
    case_id = client.post(
        "/api/v1/cases",
        json={"child_code": "C-PRIVACY-DELETE", "age_months": 59, "language": "English", "consent_status": "granted"},
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-06-24", "session_type": "therapy_session"},
    ).json()["session_id"]
    transcript_id = client.post(
        f"/api/v1/sessions/{session_id}/transcripts/manual",
        json={"text": "THER: tell me more\nCHI: I see a train\nCHI: train goes fast", "language": "English"},
    ).json()["transcript_id"]
    client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"reason": "Reviewed."})
    report_id = client.post(f"/api/v1/sessions/{session_id}/reports/draft", json={}).json()["report_id"]
    signed_report = client.post(
        f"/api/v1/reports/{report_id}/sign-off",
        json={"therapist_name": "Demo Therapist", "confirmation_checked": True},
    ).json()

    request = client.post(
        f"/api/v1/cases/{case_id}/privacy-requests",
        json={
            "operation_type": "deletion_review",
            "reason": "Guardian deletion request.",
            "retention_days": 0,
        },
    ).json()
    completed = client.patch(
        f"/api/v1/privacy/requests/{request['privacy_operation_id']}",
        headers=ADMIN_HEADERS,
        json={"status": "completed", "admin_note": "Deletion review approved."},
    )

    assert completed.status_code == 200
    body = completed.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None
    assert body["preserve_evidence"] is True
    assert body["evidence_retained"]["audit_events"] >= 1
    assert body["evidence_retained"]["signed_reports"] == 1

    repo = get_repository_singleton()
    assert report_id in repo.reports
    assert repo.reports[report_id].signed_snapshot_hash == signed_report["signed_snapshot_hash"]
    serialized_audit = json.dumps(repo.audit_log)
    assert "Guardian deletion request" not in serialized_audit
