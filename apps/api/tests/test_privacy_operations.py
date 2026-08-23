import json

from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository, get_repository_singleton
from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import ChildCaseCreate, OrganizationMembershipCreate
from app.services.privacy_operation_service import _deletion_review_evidence


client = TestClient(app)
ORG_ADMIN_HEADERS = {"x-mock-role": "org_admin", "x-mock-user-id": "privacy-org-admin"}


def _seed_privacy_admin(repo: MockRepository) -> None:
    repo.upsert_membership(
        "pilot_org_001",
        OrganizationMembershipCreate(
            user_id="privacy-org-admin",
            display_name="Privacy Administrator",
            role="org_admin",
        ),
        actor_id="system",
    )


def test_deletion_review_cannot_complete_while_legal_hold_is_active():
    _seed_privacy_admin(get_repository_singleton())
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
        headers=ORG_ADMIN_HEADERS,
        json={"status": "completed", "admin_note": "Reviewed by privacy admin."},
    )

    assert completed.status_code == 400
    assert completed.json()["detail"] == "Deletion review cannot be completed while legal hold is active."


def test_completed_deletion_review_preserves_audit_and_signed_report_evidence():
    _seed_privacy_admin(get_repository_singleton())
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
    client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})
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
        headers=ORG_ADMIN_HEADERS,
        json={"status": "completed", "admin_note": "Deletion review approved."},
    )

    assert completed.status_code == 200
    body = completed.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None
    assert body["preserve_evidence"] is True
    assert body["evidence_retained"]["audit_events"] >= 1
    assert body["evidence_retained"]["signed_reports"] == 1
    assert "requested_by" not in body
    assert "reason" not in body
    assert "admin_note" not in body

    repo = get_repository_singleton()
    assert report_id in repo.reports
    assert repo.reports[report_id].signed_snapshot_hash == signed_report["signed_snapshot_hash"]
    serialized_audit = json.dumps(repo.audit_log)
    assert "Guardian deletion request" not in serialized_audit


def test_deletion_review_evidence_counts_only_case_linked_audits():
    repo = MockRepository()
    first_case = repo.create_case(
        ChildCaseCreate(
            organization_id="pilot_org_001", child_code="C-SCOPE-A", age_months=54
        ),
        actor_id="system",
    )
    second_case = repo.create_case(
        ChildCaseCreate(
            organization_id="pilot_org_001", child_code="C-SCOPE-B", age_months=54
        ),
        actor_id="system",
    )
    repo.add_audit("case.scope_a", first_case.case_id, "Scoped audit.", actor_id="system")
    repo.add_audit("case.scope_b", second_case.case_id, "Other case audit.", actor_id="system")

    evidence = _deletion_review_evidence(repo, first_case.case_id)
    expected = repo.list_audit_events(first_case.organization_id, {first_case.case_id})

    assert evidence["audit_events"] == len(expected)
    assert evidence["audit_events"] < len(repo.list_audit_events(first_case.organization_id))


def test_revoked_org_admin_cannot_list_privacy_queue_and_denial_is_audited():
    repo = MockRepository()
    _seed_privacy_admin(repo)
    membership = next(item for item in repo.memberships.values() if item.user_id == "privacy-org-admin")
    repo.revoke_membership("pilot_org_001", membership.membership_id, actor_id="system")
    original_audit_count = len(repo.audit_log)
    app.dependency_overrides[get_repository] = lambda: repo
    test_client = TestClient(app)
    try:
        response = test_client.get("/api/v1/privacy/requests", headers=ORG_ADMIN_HEADERS)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized for organization administration."
    assert len(repo.audit_log) == original_audit_count + 1
    assert repo.audit_log[-1]["action"] == "organization.privacy.list_denied"
    assert repo.audit_log[-1]["outcome"] == "denied"


def test_inactive_org_admin_cannot_update_privacy_request_and_denial_is_audited():
    repo = MockRepository()
    _seed_privacy_admin(repo)
    original_audit_count = len(repo.audit_log)
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="privacy-org-admin",
        role="org_admin",
        organization_id="pilot_org_001",
        membership_active=False,
    )
    test_client = TestClient(app)
    try:
        response = test_client.patch(
            "/api/v1/privacy/requests/privacy_operation",
            json={"status": "completed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized for organization administration."
    assert len(repo.audit_log) == original_audit_count + 1
    assert repo.audit_log[-1]["action"] == "organization.privacy.update_denied"
    assert repo.audit_log[-1]["outcome"] == "denied"
