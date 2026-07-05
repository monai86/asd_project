from __future__ import annotations

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.core.security import get_current_user
from app.main import app


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_case_list_checks_auth_before_repository_resolution():
    def fail_auth():
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    def fail_repository():
        raise AssertionError("repository should not resolve before authentication")

    app.dependency_overrides[get_current_user] = fail_auth
    app.dependency_overrides[get_repository] = fail_repository
    client = TestClient(app)
    try:
        response = client.get("/api/v1/cases")
    finally:
        _clear_overrides()

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token."


def test_report_list_checks_auth_before_repository_resolution():
    def fail_auth():
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    def fail_repository():
        raise AssertionError("repository should not resolve before authentication")

    app.dependency_overrides[get_current_user] = fail_auth
    app.dependency_overrides[get_repository] = fail_repository
    client = TestClient(app)
    try:
        response = client.get("/api/v1/reports")
    finally:
        _clear_overrides()

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token."
