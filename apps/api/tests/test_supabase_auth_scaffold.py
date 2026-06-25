from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.core.config import Settings, get_settings
from app.core.security import get_current_user
from app.main import app
from app.repositories.mock_repository import MockRepository


SECRET = "local-test-supabase-jwt-secret-with-enough-entropy"
ISSUER = "https://project-ref.supabase.co/auth/v1"
AUDIENCE = "authenticated"


def _production_settings() -> Settings:
    return Settings(
        mock_mode=False,
        auth_mode="supabase",
        supabase_jwt_secret=SECRET,
        supabase_jwt_issuer=ISSUER,
        supabase_jwt_audience=AUDIENCE,
        cors_allowed_origins="https://clinic.example",
        repository_mode="sql",
        database_url="postgresql+psycopg://prod_user:prod_password@db.example/therapist_app_v2",
        sql_create_schema=False,
        storage_mode="private",
        job_queue_mode="redis",
        redis_url="rediss://redis.example:6379/0",
        observability_enabled=True,
        observability_provider="sentry",
        critical_alert_route="pagerduty-critical",
        secret_store_provider="aws_secrets_manager",
        credential_rotation_runbook="docs/SECRET_ROTATION_RUNBOOK.md",
    )


def _jwt(claims: dict, secret: str = SECRET) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            _b64(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64(json.dumps(claims, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _claims(**metadata_overrides) -> dict:
    now = int(time.time())
    app_metadata = {
        "organization_id": "org_a",
        "role": "therapist",
        "membership_active": True,
        "mfa_verified": True,
        "invitation_status": "accepted",
        **metadata_overrides,
    }
    return {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "clinician_a",
        "email": "clinician@example.test",
        "iat": now - 30,
        "exp": now + 300,
        "app_metadata": app_metadata,
    }


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_runtime_security_requires_supabase_jwt_configuration():
    with pytest.raises(ValueError, match="Supabase JWT"):
        Settings(
            mock_mode=False,
            auth_mode="supabase",
            cors_allowed_origins="https://clinic.example",
            repository_mode="sql",
            database_url="postgresql+psycopg://prod_user:prod_password@db.example/therapist_app_v2",
            sql_create_schema=False,
            storage_mode="private",
            job_queue_mode="redis",
            redis_url="rediss://redis.example:6379/0",
            observability_enabled=True,
            observability_provider="sentry",
            critical_alert_route="pagerduty-critical",
            secret_store_provider="aws_secrets_manager",
            credential_rotation_runbook="docs/SECRET_ROTATION_RUNBOOK.md",
        ).validate_runtime_security()


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"supabase_require_mfa": False}, "Production Supabase auth must require MFA."),
        ({"supabase_require_invitation": False}, "Production Supabase auth must require invitation acceptance."),
    ],
)
def test_runtime_security_requires_mfa_and_invitation_guards(override: dict, message: str):
    values = _production_settings().model_dump()
    values.update(override)

    with pytest.raises(ValueError, match=message):
        Settings(**values).validate_runtime_security()


def test_supabase_auth_accepts_valid_token_and_ignores_mock_headers():
    repo = MockRepository()
    repo.cases["case_demo_001"].organization_id = "org_a"
    repo.cases["case_demo_001"].care_team_user_ids = ["clinician_a"]
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = _production_settings
    client = TestClient(app)
    try:
        response = client.get(
            "/api/v1/cases/case_demo_001",
            headers={
                "authorization": f"Bearer {_jwt(_claims())}",
                "x-mock-user-id": "attacker",
                "x-mock-role": "admin",
                "x-organization-id": "org_b",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["organization_id"] == "org_a"


def test_supabase_auth_mode_fails_closed_with_only_mock_headers():
    repo = MockRepository()
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = _production_settings
    client = TestClient(app)
    try:
        response = client.get(
            "/api/v1/cases/case_demo_001",
            headers={
                "x-mock-user-id": "attacker",
                "x-mock-role": "admin",
                "x-organization-id": "pilot_org_001",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 401


def test_supabase_auth_rejects_missing_invalid_and_expired_tokens():
    settings = _production_settings()
    now = int(time.time())

    with pytest.raises(HTTPException) as missing:
        get_current_user(authorization=None, settings=settings)
    with pytest.raises(HTTPException) as invalid:
        get_current_user(authorization="Bearer not-a-token", settings=settings)
    expired_claims = _claims()
    expired_claims["exp"] = now - 1
    with pytest.raises(HTTPException) as expired:
        get_current_user(authorization=f"Bearer {_jwt(expired_claims)}", settings=settings)

    assert missing.value.status_code == 401
    assert invalid.value.status_code == 401
    assert expired.value.status_code == 401


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        ({"membership_active": False}, "Membership is not active."),
        ({"mfa_verified": False}, "MFA is required."),
        ({"invitation_status": "pending"}, "Invitation must be accepted."),
    ],
)
def test_supabase_auth_rejects_incomplete_user_lifecycle(metadata: dict, message: str):
    with pytest.raises(HTTPException) as exc:
        get_current_user(
            authorization=f"Bearer {_jwt(_claims(**metadata))}",
            settings=_production_settings(),
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == message


def test_break_glass_claim_requires_reason_and_time_limit():
    with pytest.raises(HTTPException) as missing_reason:
        get_current_user(
            authorization=f"Bearer {_jwt(_claims(role='platform_operator', break_glass={'active': True, 'expires_at': int(time.time()) + 60}))}",
            settings=_production_settings(),
        )

    with pytest.raises(HTTPException) as expired:
        get_current_user(
            authorization=f"Bearer {_jwt(_claims(role='platform_operator', break_glass={'active': True, 'reason': 'incident review', 'expires_at': int(time.time()) - 1}))}",
            settings=_production_settings(),
        )

    assert missing_reason.value.status_code == 403
    assert missing_reason.value.detail == "Break-glass access requires a reason."
    assert expired.value.status_code == 403
    assert expired.value.detail == "Break-glass access is expired."
