from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.main import app
from app.schemas.clinical import ChildCaseCreate


def test_create_case_route_uses_transactional_sql_repository_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, ChildCaseRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'case-route-create.db'}")

    def fail_snapshot_save() -> None:
        raise AssertionError("case route create must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        response = TestClient(app).post(
            "/api/v1/cases",
            json={"child_code": "C-ROUTE-001", "age_months": 48, "language": "English"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    case_id = response.json()["case_id"]
    with repo.SessionLocal() as db:
        row = db.get(ChildCaseRecord, case_id)
        audit = db.query(AuditLogRecord).filter_by(action="case.create", target_id=case_id).one()

    assert row is not None
    assert row.child_code == "C-ROUTE-001"
    assert row.consent_status == "pending"
    assert response.json()["consent_status"] == "pending"
    assert row.version == 1
    assert audit.actor_id == "system"


def test_create_case_route_rejects_blank_case_code():
    response = TestClient(app).post(
        "/api/v1/cases",
        json={"child_code": "   ", "age_months": 48, "language": "Thai"},
    )

    assert response.status_code == 422


def test_update_case_route_uses_transactional_sql_repository_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, ChildCaseRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'case-route-update.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-ROUTE-002", age_months=48), actor_id="user_tx")

    def fail_snapshot_save() -> None:
        raise AssertionError("case route update must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        response = TestClient(app).patch(
            f"/api/v1/cases/{case.case_id}",
            headers={"x-mock-user-id": "user_tx", "x-organization-id": case.organization_id},
            json={"notes": "Route update."},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    with repo.SessionLocal() as db:
        row = db.get(ChildCaseRecord, case.case_id)
        audit = db.query(AuditLogRecord).filter_by(action="case.update", target_id=case.case_id).one()

    assert body["version"] == case.version + 1
    assert row is not None
    assert row.notes == "Route update."
    assert row.version == case.version + 1
    assert audit.actor_id == "system"
