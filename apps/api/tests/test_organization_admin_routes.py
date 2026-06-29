from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
import pytest

from app.api.v1.dependencies import get_repository
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import OrganizationInvitationCreate, utc_now


def _client_with_repo(repo: MockRepository) -> TestClient:
    app.dependency_overrides[get_repository] = lambda: repo
    return TestClient(app)


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _headers(user_id: str, organization_id: str, role: str = "therapist") -> dict[str, str]:
    return {
        "x-mock-user-id": user_id,
        "x-mock-role": role,
        "x-organization-id": organization_id,
    }


def test_org_admin_can_manage_memberships_within_organization():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    therapist = _headers("clinician_a", "org_a")
    try:
        denied = client.post(
            "/api/v1/organizations/current/memberships",
            headers=therapist,
            json={"user_id": "clinician_b", "display_name": "Clinician B", "role": "therapist"},
        )
        created = client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "clinician_b", "display_name": "Clinician B", "role": "therapist"},
        )
        listed = client.get("/api/v1/organizations/current/memberships", headers=admin)
    finally:
        _clear_overrides()

    assert denied.status_code == 403
    assert created.status_code == 200
    assert created.json()["organization_id"] == "org_a"
    assert created.json()["user_id"] == "clinician_b"
    assert created.json()["active"] is True
    assert [item["user_id"] for item in listed.json()] == ["clinician_b"]


def test_org_admin_can_assign_case_care_team_and_assigned_clinician_can_read_case():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    clinician_a = _headers("clinician_a", "org_a")
    clinician_b = _headers("clinician_b", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician_a, json={"child_code": "C-TEAM", "age_months": 54}).json()
        before_assignment = client.get(f"/api/v1/cases/{case['case_id']}", headers=clinician_b)
        client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "clinician_b", "display_name": "Clinician B", "role": "therapist"},
        )
        assignment = client.post(
            f"/api/v1/cases/{case['case_id']}/care-team",
            headers=admin,
            json={"user_id": "clinician_b", "role": "therapist"},
        )
        after_assignment = client.get(f"/api/v1/cases/{case['case_id']}", headers=clinician_b)
        listed = client.get(f"/api/v1/cases/{case['case_id']}/care-team", headers=admin)
    finally:
        _clear_overrides()

    assert before_assignment.status_code == 403
    assert assignment.status_code == 200
    assert assignment.json()["case_id"] == case["case_id"]
    assert assignment.json()["user_id"] == "clinician_b"
    assert after_assignment.status_code == 200
    assert [item["user_id"] for item in listed.json()] == ["clinician_b"]


def test_primary_therapist_assignment_is_explicit_and_revocation_clears_case_signer():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    clinician_a = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician_a, json={"child_code": "C-PRIMARY", "age_months": 54}).json()
        client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "clinician_b", "display_name": "Clinician B", "role": "therapist"},
        )
        promoted = client.post(
            f"/api/v1/cases/{case['case_id']}/care-team",
            headers=admin,
            json={"user_id": "clinician_b", "role": "therapist", "is_primary": True},
        )
        listed = client.get(f"/api/v1/cases/{case['case_id']}/care-team", headers=admin)
        membership_id = next(
            item["membership_id"]
            for item in client.get("/api/v1/organizations/current/memberships", headers=admin).json()
            if item["user_id"] == "clinician_b"
        )
        revoked = client.post(
            f"/api/v1/organizations/current/memberships/{membership_id}/revoke",
            headers=admin,
        )
        case_after_revoke = client.get(f"/api/v1/cases/{case['case_id']}", headers=clinician_a)
    finally:
        _clear_overrides()

    assert promoted.status_code == 200
    assert promoted.json()["is_primary"] is True
    assert listed.json()[0]["user_id"] == "clinician_b"
    assert listed.json()[0]["is_primary"] is True
    assert revoked.status_code == 200
    assert case_after_revoke.status_code == 200
    assert case_after_revoke.json()["primary_therapist_user_id"] is None


def test_clinical_supervisor_can_manage_case_assignment_without_full_org_admin_role():
    repo = MockRepository()
    client = _client_with_repo(repo)
    supervisor = _headers("supervisor_a", "org_a", "clinical_supervisor")
    org_admin = _headers("admin_a", "org_a", "org_admin")
    clinician_a = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician_a, json={"child_code": "C-SUP", "age_months": 54}).json()
        client.post(
            "/api/v1/organizations/current/memberships",
            headers=org_admin,
            json={"user_id": "clinician_b", "display_name": "Clinician B", "role": "therapist"},
        )
        assignment = client.post(
            f"/api/v1/cases/{case['case_id']}/care-team",
            headers=supervisor,
            json={"user_id": "clinician_b", "role": "therapist"},
        )
        memberships = client.get("/api/v1/organizations/current/memberships", headers=supervisor)
    finally:
        _clear_overrides()

    assert assignment.status_code == 200
    assert memberships.status_code == 403


def test_org_admin_requires_explicit_care_team_grant_for_clinical_access():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    clinician_a = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician_a, json={"child_code": "C-GRANT", "age_months": 54}).json()
        before_assignment = client.get(f"/api/v1/cases/{case['case_id']}", headers=admin)
        client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "admin_a", "display_name": "Admin A", "role": "org_admin"},
        )
        assignment = client.post(
            f"/api/v1/cases/{case['case_id']}/care-team",
            headers=admin,
            json={"user_id": "admin_a", "role": "org_admin"},
        )
        after_assignment = client.get(f"/api/v1/cases/{case['case_id']}", headers=admin)
        updated = client.patch(
            f"/api/v1/cases/{case['case_id']}",
            headers=admin,
            json={"notes": "Explicit org-admin clinical grant."},
        )
    finally:
        _clear_overrides()

    assert before_assignment.status_code == 403
    assert assignment.status_code == 200
    assert after_assignment.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["notes"] == "Explicit org-admin clinical grant."


def test_cross_org_admin_cannot_assign_care_team_to_other_org_case():
    repo = MockRepository()
    client = _client_with_repo(repo)
    try:
        case = client.post(
            "/api/v1/cases",
            headers=_headers("clinician_a", "org_a"),
            json={"child_code": "C-XORG", "age_months": 54},
        ).json()
        blocked = client.post(
            f"/api/v1/cases/{case['case_id']}/care-team",
            headers=_headers("admin_b", "org_b", "org_admin"),
            json={"user_id": "clinician_b", "role": "therapist"},
        )
        platform = client.post(
            "/api/v1/organizations/current/memberships",
            headers=_headers("platform", "org_a", "platform_operator"),
            json={"user_id": "clinician_b", "display_name": "Clinician B", "role": "therapist"},
        )
    finally:
        _clear_overrides()

    assert blocked.status_code == 404
    assert platform.status_code == 403


def test_org_admin_and_platform_operator_cannot_create_cases():
    repo = MockRepository()
    client = _client_with_repo(repo)
    try:
        org_admin = client.post(
            "/api/v1/cases",
            headers=_headers("admin_a", "org_a", "org_admin"),
            json={"child_code": "C-ADMIN", "age_months": 54},
        )
        platform = client.post(
            "/api/v1/cases",
            headers=_headers("platform_a", "org_a", "platform_operator"),
            json={"child_code": "C-PLATFORM", "age_months": 54},
        )
    finally:
        _clear_overrides()

    assert org_admin.status_code == 403
    assert org_admin.json()["detail"] == "Case creation requires therapist or clinical supervisor role."
    assert platform.status_code == 403
    assert platform.json()["detail"] == "Case creation requires therapist or clinical supervisor role."


def test_clinical_supervisor_must_set_primary_therapist_when_creating_case():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    try:
        missing_primary = client.post(
            "/api/v1/cases",
            headers=_headers("supervisor_a", "org_a", "clinical_supervisor"),
            json={"child_code": "C-SUP-NOPRIMARY", "age_months": 54},
        )
        client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "clinician_a", "display_name": "Clinician A", "role": "therapist"},
        )
        created = client.post(
            "/api/v1/cases",
            headers=_headers("supervisor_a", "org_a", "clinical_supervisor"),
            json={
                "child_code": "C-SUP-PRIMARY",
                "age_months": 54,
                "primary_therapist_user_id": "clinician_a",
                "care_team_user_ids": ["clinician_a"],
            },
        )
    finally:
        _clear_overrides()

    assert missing_primary.status_code == 409
    assert missing_primary.json()["detail"] == "Primary therapist assignment required at case creation."
    assert created.status_code == 200
    assert created.json()["primary_therapist_user_id"] == "clinician_a"
    assert created.json()["care_team_user_ids"] == ["clinician_a"]


def test_case_creation_rejects_noncanonical_care_team_bootstrap():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    try:
        therapist_extra = client.post(
            "/api/v1/cases",
            headers=_headers("clinician_a", "org_a"),
            json={
                "child_code": "C-THER-EXTRA",
                "age_months": 54,
                "care_team_user_ids": ["clinician_a", "clinician_b"],
            },
        )
        therapist_override = client.post(
            "/api/v1/cases",
            headers=_headers("clinician_a", "org_a"),
            json={
                "child_code": "C-THER-PRIMARY",
                "age_months": 54,
                "primary_therapist_user_id": "clinician_b",
            },
        )
        client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "clinician_a", "display_name": "Clinician A", "role": "therapist"},
        )
        supervisor_extra = client.post(
            "/api/v1/cases",
            headers=_headers("supervisor_a", "org_a", "clinical_supervisor"),
            json={
                "child_code": "C-SUP-EXTRA",
                "age_months": 54,
                "primary_therapist_user_id": "clinician_a",
                "care_team_user_ids": ["clinician_a", "clinician_b"],
            },
        )
        supervisor_nonmember = client.post(
            "/api/v1/cases",
            headers=_headers("supervisor_a", "org_a", "clinical_supervisor"),
            json={
                "child_code": "C-SUP-NONMEMBER",
                "age_months": 54,
                "primary_therapist_user_id": "clinician_b",
            },
        )
    finally:
        _clear_overrides()

    assert therapist_extra.status_code == 409
    assert therapist_extra.json()["detail"] == "Additional care-team members must be assigned through the care-team route."
    assert therapist_override.status_code == 409
    assert therapist_override.json()["detail"] == "Therapist-created cases must keep the authenticated therapist as primary."
    assert supervisor_extra.status_code == 409
    assert supervisor_extra.json()["detail"] == "Additional care-team members must be assigned through the care-team route."
    assert supervisor_nonmember.status_code == 409
    assert supervisor_nonmember.json()["detail"] == "Primary therapist assignment must be an active therapist membership."


def test_primary_assignment_requires_active_therapist_role():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    clinician_a = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician_a, json={"child_code": "C-NONTHER", "age_months": 54}).json()
        client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "admin_b", "display_name": "Admin B", "role": "org_admin"},
        )
        invalid = client.post(
            f"/api/v1/cases/{case['case_id']}/care-team",
            headers=admin,
            json={"user_id": "admin_b", "role": "org_admin", "is_primary": True},
        )
    finally:
        _clear_overrides()

    assert invalid.status_code == 409
    assert invalid.json()["detail"] == "Primary therapist assignment must be an active therapist."


def test_org_admin_invitation_acceptance_creates_active_membership():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    try:
        invited = client.post(
            "/api/v1/organizations/current/invitations",
            headers=admin,
            json={"email": "clinician-b@example.test", "display_name": "Clinician B", "role": "therapist"},
        )
        invitation_id = invited.json()["invitation_id"]
        accepted = client.post(
            f"/api/v1/organizations/current/invitations/{invitation_id}/accept",
            headers=admin,
            json={"user_id": "clinician_b"},
        )
        listed = client.get("/api/v1/organizations/current/memberships", headers=admin)
    finally:
        _clear_overrides()

    assert invited.status_code == 200
    assert invited.json()["status"] == "pending"
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    assert [item["user_id"] for item in listed.json()] == ["clinician_b"]
    assert listed.json()[0]["active"] is True
    assert any(event["action"] == "invitation.accept" for event in repo.audit_log)


def test_org_admin_invitation_expiry_is_fixed_to_seven_days_and_custom_expiry_is_ignored():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    custom_expiry = (utc_now() + timedelta(days=30)).isoformat()
    try:
        invited = client.post(
            "/api/v1/organizations/current/invitations",
            headers=admin,
            json={
                "email": "clinician-b@example.test",
                "display_name": "Clinician B",
                "role": "therapist",
                "expires_at": custom_expiry,
            },
        )
    finally:
        _clear_overrides()

    assert invited.status_code == 200
    expires_at = invited.json()["expires_at"]
    created_at = invited.json()["created_at"]
    remaining = (
        datetime.fromisoformat(expires_at) - datetime.fromisoformat(created_at)
    ).total_seconds()
    assert remaining <= 7 * 24 * 60 * 60 + 5
    assert remaining >= 7 * 24 * 60 * 60 - 5


def test_expired_invitation_requires_newly_issued_invitation():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    invitation = repo.create_invitation(
        "org_a",
        OrganizationInvitationCreate(
            email="expired@example.test",
            display_name="Expired Invite",
            role="therapist",
            expires_at=utc_now() - timedelta(minutes=1),
        ),
        actor_id="admin_a",
    )
    repo.invitations[invitation.invitation_id].expires_at = utc_now() - timedelta(minutes=1)
    try:
        accepted = client.post(
            f"/api/v1/organizations/current/invitations/{invitation.invitation_id}/accept",
            headers=admin,
            json={"user_id": "clinician_b"},
        )
        replacement = client.post(
            "/api/v1/organizations/current/invitations",
            headers=admin,
            json={"email": "expired@example.test", "display_name": "Expired Invite", "role": "therapist"},
        )
    finally:
        _clear_overrides()

    assert accepted.status_code == 409
    assert accepted.json()["detail"] == "Expired invitations require a newly issued invitation."
    assert replacement.status_code == 200
    assert replacement.json()["invitation_id"] != invitation.invitation_id
    assert replacement.json()["status"] == "pending"


def test_accepted_invitation_cannot_be_accepted_twice():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    try:
        invited = client.post(
            "/api/v1/organizations/current/invitations",
            headers=admin,
            json={"email": "clinician-b@example.test", "display_name": "Clinician B", "role": "therapist"},
        )
        invitation_id = invited.json()["invitation_id"]
        accepted = client.post(
            f"/api/v1/organizations/current/invitations/{invitation_id}/accept",
            headers=admin,
            json={"user_id": "clinician_b"},
        )
        accepted_again = client.post(
            f"/api/v1/organizations/current/invitations/{invitation_id}/accept",
            headers=admin,
            json={"user_id": "clinician_b"},
        )
    finally:
        _clear_overrides()

    assert accepted.status_code == 200
    assert accepted_again.status_code == 409
    assert accepted_again.json()["detail"] == "Invitation has already been accepted."


def test_identity_email_cannot_bind_to_different_user_across_organizations():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin_a = _headers("admin_a", "org_a", "org_admin")
    admin_b = _headers("admin_b", "org_b", "org_admin")
    try:
        invited_a = client.post(
            "/api/v1/organizations/current/invitations",
            headers=admin_a,
            json={"email": "shared@example.test", "display_name": "Shared Identity", "role": "therapist"},
        )
        accepted_a = client.post(
            f"/api/v1/organizations/current/invitations/{invited_a.json()['invitation_id']}/accept",
            headers=admin_a,
            json={"user_id": "clinician_a"},
        )
        invited_b = client.post(
            "/api/v1/organizations/current/invitations",
            headers=admin_b,
            json={"email": "shared@example.test", "display_name": "Shared Identity", "role": "therapist"},
        )
        accepted_b = client.post(
            f"/api/v1/organizations/current/invitations/{invited_b.json()['invitation_id']}/accept",
            headers=admin_b,
            json={"user_id": "clinician_b"},
        )
    finally:
        _clear_overrides()

    assert accepted_a.status_code == 200
    assert invited_b.status_code == 200
    assert accepted_b.status_code == 409
    assert accepted_b.json()["detail"] == "Identity email is already bound to a different user."


def test_org_admin_can_revoke_membership_and_assignment_requires_active_membership():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    clinician_a = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician_a, json={"child_code": "C-REVOKE", "age_months": 54}).json()
        created = client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "clinician_b", "display_name": "Clinician B", "role": "therapist"},
        )
        revoked = client.post(
            f"/api/v1/organizations/current/memberships/{created.json()['membership_id']}/revoke",
            headers=admin,
        )
        assignment = client.post(
            f"/api/v1/cases/{case['case_id']}/care-team",
            headers=admin,
            json={"user_id": "clinician_b", "role": "therapist"},
        )
    finally:
        _clear_overrides()

    assert revoked.status_code == 200
    assert revoked.json()["active"] is False
    assert assignment.status_code == 409
    assert any(event["action"] == "membership.revoke" for event in repo.audit_log)


def test_revoked_membership_fails_closed_on_next_request():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    clinician_a = _headers("clinician_a", "org_a")
    clinician_b = _headers("clinician_b", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician_a, json={"child_code": "C-REVOKE-NEXT", "age_months": 54}).json()
        created = client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "clinician_b", "display_name": "Clinician B", "role": "therapist"},
        )
        client.post(
            f"/api/v1/cases/{case['case_id']}/care-team",
            headers=admin,
            json={"user_id": "clinician_b", "role": "therapist"},
        )
        before_revoke = client.get(f"/api/v1/cases/{case['case_id']}", headers=clinician_b)
        revoked = client.post(
            f"/api/v1/organizations/current/memberships/{created.json()['membership_id']}/revoke",
            headers=admin,
        )
        after_revoke = client.get(f"/api/v1/cases/{case['case_id']}", headers=clinician_b)
    finally:
        _clear_overrides()

    assert before_revoke.status_code == 200
    assert revoked.status_code == 200
    assert after_revoke.status_code == 403
    assert after_revoke.json()["detail"] == "Care-team assignment required."


@pytest.mark.parametrize("legacy_role", ["admin", "supervisor"])
def test_mock_auth_rejects_legacy_role_aliases(legacy_role: str):
    repo = MockRepository()
    client = _client_with_repo(repo)

    try:
        response = client.get(
            "/api/v1/organizations/current/memberships",
            headers=_headers("legacy_user", "org_a", legacy_role),
        )
    finally:
        _clear_overrides()

    assert response.status_code == 403
    assert response.json()["detail"] == f"Mock role '{legacy_role}' is invalid."


def test_break_glass_case_access_is_scoped_and_audited():
    repo = MockRepository()
    client = _client_with_repo(repo)
    clinician = _headers("clinician_a", "org_a")
    platform = _headers("platform_a", "org_a", "platform_operator")
    platform.update(
        {
            "x-break-glass-category": "incident_review",
            "x-break-glass-reason": "incident review",
            "x-break-glass-case-id": "case_pending",
            "x-break-glass-expires-at": str(int((utc_now() + timedelta(minutes=30)).timestamp())),
        }
    )
    try:
        case = client.post("/api/v1/cases", headers=clinician, json={"child_code": "C-BREAK", "age_months": 54}).json()
        platform["x-break-glass-case-id"] = case["case_id"]
        normal = client.get(f"/api/v1/cases/{case['case_id']}", headers=platform)
        scoped = client.post(f"/api/v1/cases/{case['case_id']}/break-glass-access", headers=platform)
        wrong_case = client.post("/api/v1/cases/case_demo_001/break-glass-access", headers=platform)
    finally:
        _clear_overrides()

    assert normal.status_code == 403
    assert scoped.status_code == 200
    assert wrong_case.status_code == 403
    assert wrong_case.json()["detail"] == "Break-glass access is limited to the scoped case."
    assert scoped.json()["case_id"] == case["case_id"]
    assert any(
        event["action"] == "break_glass.case_access"
        and event["target_id"] == case["case_id"]
        and event["actor_id"] == "platform_a"
        for event in repo.audit_log
    )


def test_break_glass_mock_headers_require_scoped_case_and_one_hour_limit():
    repo = MockRepository()
    client = _client_with_repo(repo)
    clinician = _headers("clinician_a", "org_a")
    platform = _headers("platform_a", "org_a", "platform_operator")
    try:
        case = client.post("/api/v1/cases", headers=clinician, json={"child_code": "C-BREAK-LIMIT", "age_months": 54}).json()
        missing_case = client.post(
            f"/api/v1/cases/{case['case_id']}/break-glass-access",
            headers={
                **platform,
                "x-break-glass-category": "incident_review",
                "x-break-glass-reason": "incident review",
                "x-break-glass-expires-at": str(int((utc_now() + timedelta(minutes=30)).timestamp())),
            },
        )
        too_long = client.post(
            f"/api/v1/cases/{case['case_id']}/break-glass-access",
            headers={
                **platform,
                "x-break-glass-category": "incident_review",
                "x-break-glass-reason": "incident review",
                "x-break-glass-case-id": case["case_id"],
                "x-break-glass-expires-at": str(int((utc_now() + timedelta(hours=2)).timestamp())),
            },
        )
    finally:
        _clear_overrides()

    assert missing_case.status_code == 403
    assert missing_case.json()["detail"] == "Break-glass access requires a scoped case."
    assert too_long.status_code == 403
    assert too_long.json()["detail"] == "Break-glass access exceeds the one-hour limit."


def test_transcript_attestation_and_report_signoff_remain_therapist_only():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    clinician = _headers("clinician_a", "org_a")
    supervisor = _headers("supervisor_a", "org_a", "clinical_supervisor")
    try:
        case = client.post("/api/v1/cases", headers=clinician, json={"child_code": "C-THER-ONLY", "age_months": 54}).json()
        client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "admin_a", "display_name": "Admin A", "role": "org_admin"},
        )
        client.post(
            f"/api/v1/cases/{case['case_id']}/care-team",
            headers=admin,
            json={"user_id": "admin_a", "role": "org_admin"},
        )
        session = client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=clinician,
            json={"session_date": "2026-06-28", "session_type": "therapy_session"},
        ).json()
        transcript = client.post(
            f"/api/v1/sessions/{session['session_id']}/transcripts/manual",
            headers=clinician,
            json={"text": "THER: prompt\nCHI: reviewed words", "language": "English"},
        ).json()
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/qa", headers=clinician)

        supervisor_attest = client.post(
            f"/api/v1/transcripts/{transcript['transcript_id']}/attest",
            headers=supervisor,
            json={"reason": "Supervisor review."},
        )
        admin_attest = client.post(
            f"/api/v1/transcripts/{transcript['transcript_id']}/attest",
            headers=admin,
            json={"reason": "Admin review."},
        )
        therapist_attest = client.post(
            f"/api/v1/transcripts/{transcript['transcript_id']}/attest",
            headers=clinician,
            json={"reason": "Therapist reviewed."},
        )
        report = client.post(
            f"/api/v1/sessions/{session['session_id']}/reports/draft",
            headers=clinician,
            json={},
        ).json()
        supervisor_signoff = client.post(
            f"/api/v1/reports/{report['report_id']}/sign-off",
            headers=supervisor,
            json={"confirmation_checked": True},
        )
        admin_signoff = client.post(
            f"/api/v1/reports/{report['report_id']}/sign-off",
            headers=admin,
            json={"confirmation_checked": True},
        )
    finally:
        _clear_overrides()

    assert supervisor_attest.status_code == 403
    assert supervisor_attest.json()["detail"] == "Therapist role required."
    assert admin_attest.status_code == 403
    assert admin_attest.json()["detail"] == "Therapist role required."
    assert therapist_attest.status_code == 200
    assert therapist_attest.json()["therapist_attested"] is True
    assert supervisor_signoff.status_code == 403
    assert supervisor_signoff.json()["detail"] == "Therapist role required."
    assert admin_signoff.status_code == 403
    assert admin_signoff.json()["detail"] == "Therapist role required."


def test_transcript_attestation_uses_authenticated_therapist_identity_and_audit_actor():
    repo = MockRepository()
    client = _client_with_repo(repo)
    clinician = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician, json={"child_code": "C-ATTEST-ACTOR", "age_months": 54}).json()
        session = client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=clinician,
            json={"session_date": "2026-06-28", "session_type": "therapy_session"},
        ).json()
        transcript = client.post(
            f"/api/v1/sessions/{session['session_id']}/transcripts/manual",
            headers=clinician,
            json={"text": "THER: prompt\nCHI: reviewed words", "language": "English"},
        ).json()
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/qa", headers=clinician)
        mismatched = client.post(
            f"/api/v1/transcripts/{transcript['transcript_id']}/attest",
            headers=clinician,
            json={"attested_by": "Someone Else", "reason": "Reviewed sample."},
        )
        attested = client.post(
            f"/api/v1/transcripts/{transcript['transcript_id']}/attest",
            headers=clinician,
            json={"attested_by": "Demo Therapist", "reason": "Reviewed sample."},
        )
    finally:
        _clear_overrides()

    assert mismatched.status_code == 400
    assert mismatched.json()["detail"] == "Transcript attestation must use the authenticated therapist identity."
    assert attested.status_code == 200
    assert any(
        event["action"] == "transcript.attest"
        and event["target_id"] == transcript["transcript_id"]
        and event["actor_id"] == "clinician_a"
        for event in repo.audit_log
    )


def test_explicit_org_admin_clinical_grant_allows_reads_but_not_clinical_mutations():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    clinician = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician, json={"child_code": "C-READ-NOT-MUTATE", "age_months": 54}).json()
        client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "admin_a", "display_name": "Admin A", "role": "org_admin"},
        )
        client.post(
            f"/api/v1/cases/{case['case_id']}/care-team",
            headers=admin,
            json={"user_id": "admin_a", "role": "org_admin"},
        )
        session = client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=clinician,
            json={"session_date": "2026-06-28", "session_type": "therapy_session"},
        ).json()
        transcript = client.post(
            f"/api/v1/sessions/{session['session_id']}/transcripts/manual",
            headers=clinician,
            json={"text": "THER: prompt\nCHI: reviewed words", "language": "English"},
        ).json()
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/qa", headers=clinician)
        client.post(
            f"/api/v1/transcripts/{transcript['transcript_id']}/attest",
            headers=clinician,
            json={"reason": "Therapist reviewed."},
        )
        report = client.post(
            f"/api/v1/sessions/{session['session_id']}/reports/draft",
            headers=clinician,
            json={},
        ).json()

        read_case = client.get(f"/api/v1/cases/{case['case_id']}", headers=admin)
        read_session = client.get(f"/api/v1/sessions/{session['session_id']}", headers=admin)
        read_transcript = client.get(f"/api/v1/transcripts/{transcript['transcript_id']}", headers=admin)
        read_report = client.get(f"/api/v1/reports/{report['report_id']}", headers=admin)

        create_session = client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=admin,
            json={"session_date": "2026-06-29", "session_type": "therapy_session"},
        )
        patch_transcript = client.patch(
            f"/api/v1/transcripts/{transcript['transcript_id']}",
            headers=admin,
            json={"reviewer_note": "Admin edit"},
        )
        create_goal = client.post(
            f"/api/v1/cases/{case['case_id']}/goals",
            headers=admin,
            json={"title": "Goal", "target": "Target"},
        )
        draft_report = client.post(
            f"/api/v1/sessions/{session['session_id']}/reports/draft",
            headers=admin,
            json={},
        )
        update_report = client.patch(
            f"/api/v1/reports/{report['report_id']}",
            headers=admin,
            json={"therapist_notes": "Admin note"},
        )
        upload_audio = client.post(
            f"/api/v1/sessions/{session['session_id']}/audio/upload",
            headers=admin,
            json={"filename": "sample.wav", "content_type": "audio/wav", "size_bytes": 128},
        )
    finally:
        _clear_overrides()

    assert read_case.status_code == 200
    assert read_session.status_code == 200
    assert read_transcript.status_code == 200
    assert read_report.status_code == 200
    for response in [create_session, patch_transcript, create_goal, draft_report, update_report, upload_audio]:
        assert response.status_code == 403
        assert response.json()["detail"] == "Clinical mutation requires therapist or clinical supervisor role."


def test_clinical_supervisor_can_run_clinical_mutations_without_case_assignment():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    supervisor = _headers("supervisor_a", "org_a", "clinical_supervisor")
    clinician = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician, json={"child_code": "C-SUP-MUTATE", "age_months": 54}).json()
        client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "clinician_b", "display_name": "Clinician B", "role": "therapist"},
        )
        created_session = client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=supervisor,
            json={"session_date": "2026-06-29", "session_type": "therapy_session"},
        )
        session_id = created_session.json()["session_id"]
        transcript = client.post(
            f"/api/v1/sessions/{session_id}/transcripts/manual",
            headers=supervisor,
            json={"text": "THER: prompt\nCHI: reviewed words", "language": "English"},
        )
        goal = client.post(
            f"/api/v1/cases/{case['case_id']}/goals",
            headers=supervisor,
            json={"title": "Goal", "target": "Target"},
        )
        draft_report = client.post(
            f"/api/v1/sessions/{session_id}/reports/draft",
            headers=supervisor,
            json={},
        )
    finally:
        _clear_overrides()

    assert created_session.status_code == 200
    assert transcript.status_code == 200
    assert goal.status_code == 200
    assert draft_report.status_code == 400


def test_explicit_org_admin_grant_allows_artifact_reads_but_not_generation_or_review_mutations():
    repo = MockRepository()
    repo.set_ai_review_enabled("org_a", True)
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    clinician = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician, json={"child_code": "C-ARTIFACT-READ", "age_months": 54}).json()
        client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "admin_a", "display_name": "Admin A", "role": "org_admin"},
        )
        client.post(
            f"/api/v1/cases/{case['case_id']}/care-team",
            headers=admin,
            json={"user_id": "admin_a", "role": "org_admin"},
        )
        session = client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=clinician,
            json={"session_date": "2026-06-28", "session_type": "therapy_session"},
        ).json()
        transcript = client.post(
            f"/api/v1/sessions/{session['session_id']}/transcripts/manual",
            headers=clinician,
            json={"text": "THER: prompt\nCHI: reviewed words\nCHI: more words", "language": "English"},
        ).json()
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/qa", headers=clinician)
        client.post(
            f"/api/v1/transcripts/{transcript['transcript_id']}/attest",
            headers=clinician,
            json={"reason": "Therapist reviewed."},
        )
        feature_set = client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/extract-features", headers=clinician, json={}).json()
        ai_review = client.post(f"/api/v1/sessions/{session['session_id']}/ai-review", headers=clinician).json()
        ml_result = client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/ml-review", headers=clinician, json={}).json()

        get_features = client.get(f"/api/v1/sessions/{session['session_id']}/features", headers=admin)
        get_ai_review = client.get(f"/api/v1/sessions/{session['session_id']}/ai-review", headers=admin)
        get_ml_review = client.get(f"/api/v1/sessions/{session['session_id']}/ml-review", headers=admin)
        get_ml_result = client.get(f"/api/v1/ml-results/{ml_result['result_id']}", headers=admin)

        extract_features_as_admin = client.post(
            f"/api/v1/transcripts/{transcript['transcript_id']}/extract-features",
            headers=admin,
            json={},
        )
        create_ai_review_as_admin = client.post(
            f"/api/v1/sessions/{session['session_id']}/ai-review",
            headers=admin,
        )
        patch_ai_review_as_admin = client.patch(
            f"/api/v1/ai-reviews/{ai_review['ai_review_id']}",
            headers=admin,
            json={"therapist_notes": "Admin note"},
        )
        create_ml_review_as_admin = client.post(
            f"/api/v1/transcripts/{transcript['transcript_id']}/ml-review",
            headers=admin,
            json={},
        )
        patch_ml_cue_as_admin = client.patch(
            f"/api/v1/ml-results/{ml_result['result_id']}/cues/{ml_result['cues'][0]['cue_code']}",
            headers=admin,
            json={"status": "acknowledged", "therapist_note": "Admin note"},
        )
    finally:
        _clear_overrides()

    assert get_features.status_code == 200
    assert get_features.json()["feature_set_id"] == feature_set["feature_set_id"]
    assert get_ai_review.status_code == 200
    assert get_ai_review.json()["ai_review_id"] == ai_review["ai_review_id"]
    assert get_ml_review.status_code == 200
    assert get_ml_review.json()["result_id"] == ml_result["result_id"]
    assert get_ml_result.status_code == 200
    assert get_ml_result.json()["result_id"] == ml_result["result_id"]
    for response in [
        extract_features_as_admin,
        create_ai_review_as_admin,
        patch_ai_review_as_admin,
        create_ml_review_as_admin,
    ]:
        assert response.status_code == 403
        assert response.json()["detail"] == "Clinical mutation requires therapist or clinical supervisor role."
    assert patch_ml_cue_as_admin.status_code == 403
    assert patch_ml_cue_as_admin.json()["detail"] == "Therapist or clinical supervisor role required."


def test_clinical_supervisor_can_generate_and_review_artifacts_without_case_assignment():
    repo = MockRepository()
    repo.set_ai_review_enabled("org_a", True)
    client = _client_with_repo(repo)
    supervisor = _headers("supervisor_a", "org_a", "clinical_supervisor")
    clinician = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician, json={"child_code": "C-SUP-ARTIFACT", "age_months": 54}).json()
        session = client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=clinician,
            json={"session_date": "2026-06-28", "session_type": "therapy_session"},
        ).json()
        transcript = client.post(
            f"/api/v1/sessions/{session['session_id']}/transcripts/manual",
            headers=clinician,
            json={"text": "THER: prompt\nCHI: reviewed words\nCHI: more words", "language": "English"},
        ).json()
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/qa", headers=clinician)
        client.post(
            f"/api/v1/transcripts/{transcript['transcript_id']}/attest",
            headers=clinician,
            json={"reason": "Therapist reviewed."},
        )

        feature_set = client.post(
            f"/api/v1/transcripts/{transcript['transcript_id']}/extract-features",
            headers=supervisor,
            json={},
        )
        ai_review = client.post(
            f"/api/v1/sessions/{session['session_id']}/ai-review",
            headers=supervisor,
        )
        ml_result = client.post(
            f"/api/v1/transcripts/{transcript['transcript_id']}/ml-review",
            headers=supervisor,
            json={},
        )
        patched_ai = client.patch(
            f"/api/v1/ai-reviews/{ai_review.json()['ai_review_id']}",
            headers=supervisor,
            json={"therapist_review_status": "Attested", "therapist_notes": "Supervisor reviewed."},
        )
        patched_ml = client.patch(
            f"/api/v1/ml-results/{ml_result.json()['result_id']}/cues/{ml_result.json()['cues'][0]['cue_code']}",
            headers=supervisor,
            json={"status": "acknowledged", "therapist_note": "Supervisor reviewed cue."},
        )
    finally:
        _clear_overrides()

    assert feature_set.status_code == 200
    assert ai_review.status_code == 200
    assert ml_result.status_code == 200
    assert patched_ai.status_code == 200
    assert patched_ml.status_code == 200


def test_explicit_org_admin_grant_does_not_unlock_sensitive_audio_or_chat_exports():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    clinician = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician, json={"child_code": "C-SENSITIVE-EXPORT", "age_months": 54}).json()
        client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "admin_a", "display_name": "Admin A", "role": "org_admin"},
        )
        client.post(
            f"/api/v1/cases/{case['case_id']}/care-team",
            headers=admin,
            json={"user_id": "admin_a", "role": "org_admin"},
        )
        session = client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=clinician,
            json={"session_date": "2026-06-28", "session_type": "therapy_session"},
        ).json()
        upload = client.post(
            f"/api/v1/sessions/{session['session_id']}/audio/upload",
            headers=clinician,
            json={"filename": "family_sample.wav", "content_type": "audio/wav", "size_bytes": 12, "duration_seconds": 30},
        ).json()
        audio_id = upload["details"]["audio_file"]["audio_file_id"]
        client.put(f"/api/v1{upload['details']['upload_intent']['upload_url']}", headers=clinician, content=b"RIFFxxxxWAVE")
        client.post(
            f"/api/v1/audio/{audio_id}/complete-upload",
            headers=clinician,
            json={"checksum_sha256": "fake-checksum", "size_bytes": 12},
        )
        transcript = client.post(
            f"/api/v1/sessions/{session['session_id']}/transcripts/manual",
            headers=clinician,
            json={"text": "CHI: I see car\nCHI: more car\nCHI: car fast", "language": "English"},
        ).json()

        admin_audio_metadata = client.get(f"/api/v1/audio/{audio_id}", headers=admin)
        admin_audio_list = client.get(f"/api/v1/sessions/{session['session_id']}/audio", headers=admin)
        admin_audio_file = client.get(f"/api/v1/audio/{audio_id}/file", headers=admin)
        admin_chat_export = client.get(f"/api/v1/transcripts/{transcript['transcript_id']}/export-cha", headers=admin)
    finally:
        _clear_overrides()

    for response in [admin_audio_metadata, admin_audio_list, admin_audio_file, admin_chat_export]:
        assert response.status_code == 403
        assert response.json()["detail"] == "Sensitive clinical export requires therapist or clinical supervisor role."


def test_clinical_supervisor_can_access_sensitive_audio_and_chat_exports():
    repo = MockRepository()
    client = _client_with_repo(repo)
    supervisor = _headers("supervisor_a", "org_a", "clinical_supervisor")
    clinician = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician, json={"child_code": "C-SUP-EXPORT", "age_months": 54}).json()
        session = client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=clinician,
            json={"session_date": "2026-06-28", "session_type": "therapy_session"},
        ).json()
        upload = client.post(
            f"/api/v1/sessions/{session['session_id']}/audio/upload",
            headers=clinician,
            json={"filename": "family_sample.wav", "content_type": "audio/wav", "size_bytes": 12, "duration_seconds": 30},
        ).json()
        audio_id = upload["details"]["audio_file"]["audio_file_id"]
        payload = b"RIFFxxxxWAVE"
        client.put(f"/api/v1{upload['details']['upload_intent']['upload_url']}", headers=clinician, content=payload)
        client.post(
            f"/api/v1/audio/{audio_id}/complete-upload",
            headers=clinician,
            json={"checksum_sha256": "fake-checksum", "size_bytes": 12},
        )
        transcript = client.post(
            f"/api/v1/sessions/{session['session_id']}/transcripts/manual",
            headers=clinician,
            json={"text": "CHI: I see car\nCHI: more car\nCHI: car fast", "language": "English"},
        ).json()

        supervisor_audio_metadata = client.get(f"/api/v1/audio/{audio_id}", headers=supervisor)
        supervisor_audio_list = client.get(f"/api/v1/sessions/{session['session_id']}/audio", headers=supervisor)
        supervisor_audio_file = client.get(f"/api/v1/audio/{audio_id}/file", headers=supervisor)
        supervisor_chat_export = client.get(f"/api/v1/transcripts/{transcript['transcript_id']}/export-cha", headers=supervisor)
    finally:
        _clear_overrides()

    assert supervisor_audio_metadata.status_code == 200
    assert supervisor_audio_metadata.json()["audio_file_id"] == audio_id
    assert supervisor_audio_list.status_code == 200
    assert supervisor_audio_list.json()[0]["audio_file_id"] == audio_id
    assert supervisor_audio_file.status_code == 200
    assert supervisor_audio_file.content == payload
    assert supervisor_chat_export.status_code == 200
    assert "@Begin" in supervisor_chat_export.json()["cha_text"]


def test_explicit_org_admin_grant_does_not_unlock_report_export():
    repo = MockRepository()
    client = _client_with_repo(repo)
    admin = _headers("admin_a", "org_a", "org_admin")
    clinician = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician, json={"child_code": "C-REPORT-EXPORT", "age_months": 54}).json()
        client.post(
            "/api/v1/organizations/current/memberships",
            headers=admin,
            json={"user_id": "admin_a", "display_name": "Admin A", "role": "org_admin"},
        )
        client.post(
            f"/api/v1/cases/{case['case_id']}/care-team",
            headers=admin,
            json={"user_id": "admin_a", "role": "org_admin"},
        )
        session = client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=clinician,
            json={"session_date": "2026-06-28", "session_type": "therapy_session"},
        ).json()
        transcript = client.post(
            f"/api/v1/sessions/{session['session_id']}/transcripts/manual",
            headers=clinician,
            json={"text": "THER: prompt\nCHI: reviewed words\nCHI: more words", "language": "English"},
        ).json()
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/qa", headers=clinician)
        client.post(
            f"/api/v1/transcripts/{transcript['transcript_id']}/attest",
            headers=clinician,
            json={"reason": "Therapist reviewed."},
        )
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/extract-features", headers=clinician, json={})
        client.post(f"/api/v1/sessions/{session['session_id']}/ai-review", headers=clinician)
        report = client.post(f"/api/v1/sessions/{session['session_id']}/reports/draft", headers=clinician, json={}).json()
        client.post(
            f"/api/v1/reports/{report['report_id']}/sign-off",
            headers=clinician,
            json={"signed_by": "Demo Therapist"},
        )

        admin_report_read = client.get(f"/api/v1/reports/{report['report_id']}", headers=admin)
        admin_report_export = client.get(f"/api/v1/reports/{report['report_id']}/export?format=markdown", headers=admin)
    finally:
        _clear_overrides()

    assert admin_report_read.status_code == 200
    assert admin_report_export.status_code == 403
    assert admin_report_export.json()["detail"] == "Sensitive clinical export requires therapist or clinical supervisor role."


def test_clinical_supervisor_can_export_signed_report():
    repo = MockRepository()
    client = _client_with_repo(repo)
    supervisor = _headers("supervisor_a", "org_a", "clinical_supervisor")
    clinician = _headers("clinician_a", "org_a")
    try:
        case = client.post("/api/v1/cases", headers=clinician, json={"child_code": "C-SUP-REPORT-EXPORT", "age_months": 54}).json()
        session = client.post(
            f"/api/v1/cases/{case['case_id']}/sessions",
            headers=clinician,
            json={"session_date": "2026-06-28", "session_type": "therapy_session"},
        ).json()
        transcript = client.post(
            f"/api/v1/sessions/{session['session_id']}/transcripts/manual",
            headers=clinician,
            json={"text": "THER: prompt\nCHI: reviewed words\nCHI: more words", "language": "English"},
        ).json()
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/qa", headers=clinician)
        client.post(
            f"/api/v1/transcripts/{transcript['transcript_id']}/attest",
            headers=clinician,
            json={"reason": "Therapist reviewed."},
        )
        client.post(f"/api/v1/transcripts/{transcript['transcript_id']}/extract-features", headers=clinician, json={})
        client.post(f"/api/v1/sessions/{session['session_id']}/ai-review", headers=clinician)
        report = client.post(f"/api/v1/sessions/{session['session_id']}/reports/draft", headers=clinician, json={}).json()
        client.post(
            f"/api/v1/reports/{report['report_id']}/sign-off",
            headers=clinician,
            json={"signed_by": "Demo Therapist"},
        )

        supervisor_report_export = client.get(
            f"/api/v1/reports/{report['report_id']}/export?format=markdown",
            headers=supervisor,
        )
    finally:
        _clear_overrides()

    assert supervisor_report_export.status_code == 200
    assert supervisor_report_export.json()["content_type"] == "text/markdown"
    assert "Signed by: Demo Therapist" in supervisor_report_export.json()["content"]
