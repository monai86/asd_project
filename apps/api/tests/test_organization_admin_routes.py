from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.main import app
from app.repositories.mock_repository import MockRepository


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


def test_break_glass_case_access_is_scoped_and_audited():
    repo = MockRepository()
    client = _client_with_repo(repo)
    clinician = _headers("clinician_a", "org_a")
    platform = _headers("platform_a", "org_a", "platform_operator")
    platform.update(
        {
            "x-break-glass-reason": "incident review",
            "x-break-glass-expires-at": "4102444800",
        }
    )
    try:
        case = client.post("/api/v1/cases", headers=clinician, json={"child_code": "C-BREAK", "age_months": 54}).json()
        normal = client.get(f"/api/v1/cases/{case['case_id']}", headers=platform)
        scoped = client.post(f"/api/v1/cases/{case['case_id']}/break-glass-access", headers=platform)
    finally:
        _clear_overrides()

    assert normal.status_code == 403
    assert scoped.status_code == 200
    assert scoped.json()["case_id"] == case["case_id"]
    assert any(
        event["action"] == "break_glass.case_access"
        and event["target_id"] == case["case_id"]
        and event["actor_id"] == "platform_a"
        for event in repo.audit_log
    )
