from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
from urllib.error import URLError

from app.api.v1.dependencies import get_repository
from app.core.config import Settings, get_settings
from app.auth.supabase_auth import reset_jwks_cache_for_tests
from app.core.security import get_current_user
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import OrganizationMembershipCreate


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


def _production_jwks_settings(jwks_json: str) -> Settings:
    return Settings(
        mock_mode=False,
        auth_mode="supabase",
        supabase_jwt_verification_mode="jwks_json",
        supabase_jwt_jwks_json=jwks_json,
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


def _production_jwks_url_settings(jwks_url: str) -> Settings:
    return Settings(
        mock_mode=False,
        auth_mode="supabase",
        supabase_jwt_verification_mode="jwks_url",
        supabase_jwt_jwks_url=jwks_url,
        supabase_jwt_jwks_cache_ttl_seconds=300,
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


def _rsa_bundle(kid: str = "test-rs256-key") -> tuple[object, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": "RS256",
                "n": _b64(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
                "e": _b64(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
            }
        ]
    }
    return private_key, json.dumps(jwks)


def _claims(**metadata_overrides) -> dict:
    now = int(time.time())
    app_metadata = {
        "organization_id": "org_a",
        "role": "therapist",
        "membership_active": True,
        "invitation_status": "accepted",
        **metadata_overrides,
    }
    return {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "aal": "aal2",
        "sub": "clinician_a",
        "email": "clinician@example.test",
        "iat": now - 30,
        "exp": now + 300,
        "app_metadata": app_metadata,
    }


def _jwt_rs256(claims: dict, private_key: object, kid: str = "test-rs256-key") -> str:
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})


def _claims_for_user(user_id: str, **metadata_overrides) -> dict:
    claims = _claims(**metadata_overrides)
    claims["sub"] = user_id
    return claims


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


def test_runtime_security_requires_jwks_json_for_asymmetric_verification():
    with pytest.raises(ValueError, match="JWKS JSON"):
        Settings(
            mock_mode=False,
            auth_mode="supabase",
            supabase_jwt_verification_mode="jwks_json",
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
            supabase_jwt_issuer=ISSUER,
        ).validate_runtime_security()


def test_runtime_security_requires_jwks_url_for_remote_asymmetric_verification():
    with pytest.raises(ValueError, match="JWKS URL"):
        Settings(
            mock_mode=False,
            auth_mode="supabase",
            supabase_jwt_verification_mode="jwks_url",
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
            supabase_jwt_issuer=ISSUER,
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
                "x-mock-role": "org_admin",
                "x-organization-id": "org_a",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["organization_id"] == "org_a"


def test_supabase_auth_accepts_valid_rs256_token_from_local_jwks():
    repo = MockRepository()
    repo.cases["case_demo_001"].organization_id = "org_a"
    repo.cases["case_demo_001"].care_team_user_ids = ["clinician_a"]
    private_key, jwks_json = _rsa_bundle()
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = lambda: _production_jwks_settings(jwks_json)
    client = TestClient(app)
    try:
        response = client.get(
            "/api/v1/cases/case_demo_001",
            headers={
                "authorization": f"Bearer {_jwt_rs256(_claims(organizations=[{'organization_id': 'org_a', 'role': 'therapist'}]), private_key)}",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["organization_id"] == "org_a"


def test_supabase_auth_accepts_valid_rs256_token_from_fetched_jwks(monkeypatch):
    repo = MockRepository()
    repo.cases["case_demo_001"].organization_id = "org_a"
    repo.cases["case_demo_001"].care_team_user_ids = ["clinician_a"]
    private_key, jwks_json = _rsa_bundle()
    fetch_calls: list[str] = []

    def fake_fetch(url: str) -> str:
        fetch_calls.append(url)
        return jwks_json

    from app.auth import supabase_auth as supabase_auth_module

    reset_jwks_cache_for_tests()
    monkeypatch.setattr(supabase_auth_module, "_fetch_jwks_json_from_url", fake_fetch)
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = lambda: _production_jwks_url_settings("https://supabase.example/jwks")
    client = TestClient(app)
    try:
        response = client.get(
            "/api/v1/cases/case_demo_001",
            headers={
                "authorization": f"Bearer {_jwt_rs256(_claims(organizations=[{'organization_id': 'org_a', 'role': 'therapist'}]), private_key)}",
            },
        )
    finally:
        _clear_overrides()
        reset_jwks_cache_for_tests()

    assert response.status_code == 200
    assert fetch_calls == ["https://supabase.example/jwks"]


def test_supabase_auth_reuses_cached_jwks_url_payload(monkeypatch):
    private_key, jwks_json = _rsa_bundle()
    fetch_calls: list[str] = []

    def fake_fetch(url: str) -> str:
        fetch_calls.append(url)
        return jwks_json

    from app.auth import supabase_auth as supabase_auth_module

    reset_jwks_cache_for_tests()
    monkeypatch.setattr(supabase_auth_module, "_fetch_jwks_json_from_url", fake_fetch)
    settings = _production_jwks_url_settings("https://supabase.example/jwks")
    token = _jwt_rs256(_claims(), private_key)

    get_current_user(authorization=f"Bearer {token}", settings=settings)
    get_current_user(authorization=f"Bearer {token}", settings=settings)

    reset_jwks_cache_for_tests()
    assert fetch_calls == ["https://supabase.example/jwks"]


def test_supabase_auth_refreshes_jwks_url_when_cached_keys_miss_new_kid(monkeypatch):
    old_private_key, old_jwks_json = _rsa_bundle(kid="old-key")
    new_private_key, new_jwks_json = _rsa_bundle(kid="new-key")
    fetch_calls: list[str] = []
    responses = [old_jwks_json, new_jwks_json]

    def fake_fetch(url: str) -> str:
        fetch_calls.append(url)
        return responses.pop(0)

    from app.auth import supabase_auth as supabase_auth_module

    reset_jwks_cache_for_tests()
    monkeypatch.setattr(supabase_auth_module, "_fetch_jwks_json_from_url", fake_fetch)
    settings = _production_jwks_url_settings("https://supabase.example/jwks")

    get_current_user(
        authorization=f"Bearer {_jwt_rs256(_claims(), old_private_key, kid='old-key')}",
        settings=settings,
    )
    principal = get_current_user(
        authorization=f"Bearer {_jwt_rs256(_claims(), new_private_key, kid='new-key')}",
        settings=settings,
    )

    reset_jwks_cache_for_tests()
    assert principal.organization_id == "org_a"
    assert fetch_calls == [
        "https://supabase.example/jwks",
        "https://supabase.example/jwks",
    ]


def test_supabase_auth_fails_closed_when_jwks_refresh_still_lacks_signing_key(monkeypatch):
    private_key, old_jwks_json = _rsa_bundle(kid="old-key")
    fetch_calls: list[str] = []

    def fake_fetch(url: str) -> str:
        fetch_calls.append(url)
        return old_jwks_json

    from app.auth import supabase_auth as supabase_auth_module

    reset_jwks_cache_for_tests()
    monkeypatch.setattr(supabase_auth_module, "_fetch_jwks_json_from_url", fake_fetch)
    settings = _production_jwks_url_settings("https://supabase.example/jwks")

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            authorization=f"Bearer {_jwt_rs256(_claims(), private_key, kid='missing-key')}",
            settings=settings,
        )

    reset_jwks_cache_for_tests()
    assert exc.value.status_code == 401
    assert exc.value.detail == "Bearer token signing key was not found."
    assert fetch_calls == [
        "https://supabase.example/jwks",
        "https://supabase.example/jwks",
    ]


def test_supabase_auth_fails_closed_when_remote_jwks_fetch_fails(monkeypatch):
    private_key, _jwks_json = _rsa_bundle()

    def fake_urlopen(*_args, **_kwargs):
        raise URLError("temporary failure")

    from app.auth import supabase_auth as supabase_auth_module

    reset_jwks_cache_for_tests()
    monkeypatch.setattr(supabase_auth_module.urllib_request, "urlopen", fake_urlopen)
    settings = _production_jwks_url_settings("https://supabase.example/jwks")

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            authorization=f"Bearer {_jwt_rs256(_claims(), private_key)}",
            settings=settings,
        )

    reset_jwks_cache_for_tests()
    assert exc.value.status_code == 401
    assert exc.value.detail == "Unable to fetch Supabase JWKS."


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
                "x-mock-role": "org_admin",
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


def test_supabase_auth_rejects_rs256_token_when_kid_is_missing_from_jwks():
    private_key, jwks_json = _rsa_bundle(kid="known-key")
    with pytest.raises(HTTPException) as exc:
        get_current_user(
            authorization=f"Bearer {_jwt_rs256(_claims(), private_key, kid='unknown-key')}",
            settings=_production_jwks_settings(jwks_json),
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Bearer token signing key was not found."


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        ({"membership_active": False}, "Membership is not active."),
        ({}, "AAL2 session is required."),
        ({"invitation_status": "pending"}, "Invitation must be accepted."),
    ],
)
def test_supabase_auth_rejects_incomplete_user_lifecycle(metadata: dict, message: str):
    claims = _claims(**metadata)
    if message == "AAL2 session is required.":
        claims["aal"] = "aal1"
    with pytest.raises(HTTPException) as exc:
        get_current_user(
            authorization=f"Bearer {_jwt(claims)}",
            settings=_production_settings(),
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == message


def test_break_glass_claim_requires_reason_and_time_limit():
    with pytest.raises(HTTPException) as missing_category:
        get_current_user(
            authorization=f"Bearer {_jwt(_claims(role='platform_operator', break_glass={'active': True, 'case_id': 'case_demo_001', 'reason': 'incident review', 'expires_at': int(time.time()) + 60}))}",
            settings=_production_settings(),
        )

    with pytest.raises(HTTPException) as missing_reason:
        get_current_user(
            authorization=f"Bearer {_jwt(_claims(role='platform_operator', break_glass={'active': True, 'case_id': 'case_demo_001', 'category': 'incident_review', 'expires_at': int(time.time()) + 60}))}",
            settings=_production_settings(),
        )

    with pytest.raises(HTTPException) as missing_case:
        get_current_user(
            authorization=f"Bearer {_jwt(_claims(role='platform_operator', break_glass={'active': True, 'category': 'incident_review', 'reason': 'incident review', 'expires_at': int(time.time()) + 60}))}",
            settings=_production_settings(),
        )

    with pytest.raises(HTTPException) as too_long:
        get_current_user(
            authorization=f"Bearer {_jwt(_claims(role='platform_operator', break_glass={'active': True, 'case_id': 'case_demo_001', 'category': 'incident_review', 'reason': 'incident review', 'expires_at': int(time.time()) + 7200}))}",
            settings=_production_settings(),
        )

    with pytest.raises(HTTPException) as expired:
        get_current_user(
            authorization=f"Bearer {_jwt(_claims(role='platform_operator', break_glass={'active': True, 'case_id': 'case_demo_001', 'category': 'incident_review', 'reason': 'incident review', 'expires_at': int(time.time()) - 1}))}",
            settings=_production_settings(),
        )

    assert missing_category.value.status_code == 403
    assert missing_category.value.detail == "Break-glass access requires a category."
    assert missing_reason.value.status_code == 403
    assert missing_reason.value.detail == "Break-glass access requires a reason."
    assert missing_case.value.status_code == 403
    assert missing_case.value.detail == "Break-glass access requires a scoped case."
    assert too_long.value.status_code == 403
    assert too_long.value.detail == "Break-glass access exceeds the one-hour limit."
    assert expired.value.status_code == 403
    assert expired.value.detail == "Break-glass access is expired."


@pytest.mark.parametrize(
    ("metadata", "message", "status_code"),
    [
        ({"membership_active": "false"}, "Supabase claim 'membership_active' must be a boolean.", 401),
        ({"role": "admin"}, "Supabase claim 'role' is invalid.", 401),
        ({"invitation_status": "unknown"}, "Supabase claim 'invitation_status' is invalid.", 401),
        ({"break_glass": "active"}, "Supabase claim 'break_glass' is invalid.", 401),
        (
            {"break_glass": {"active": "true"}},
            "Supabase claim 'break_glass.active' must be a boolean.",
            401,
        ),
        (
            {
                "role": "platform_operator",
                "break_glass": {
                    "active": True,
                    "case_id": "case_demo_001",
                    "category": "incident_review",
                    "reason": "incident review",
                    "expires_at": "tomorrow",
                },
            },
            "Supabase claim 'break_glass.expires_at' must be an integer.",
            401,
        ),
        (
            {
                "organizations": [
                    {"organization_id": "org_b", "role": "therapist"},
                ],
            },
            "Active organization is not present in the membership claims.",
            403,
        ),
        (
            {
                "organizations": [
                    {"organization_id": "org_a", "role": "org_admin"},
                ],
            },
            "Active organization role does not match the selected membership.",
            401,
        ),
        (
            {
                "organizations": [
                    {"organization_id": "org_a", "role": "therapist", "active": "true"},
                ],
            },
            "Supabase claim 'organizations' contains an invalid active flag.",
            401,
        ),
        (
            {
                "organizations": [
                    {"organization_id": "org_a", "role": "therapist", "active": False},
                ],
            },
            "Active organization membership is not active.",
            403,
        ),
    ],
)
def test_supabase_auth_rejects_invalid_claim_shapes_and_membership_context(
    metadata: dict,
    message: str,
    status_code: int,
):
    with pytest.raises(HTTPException) as exc:
        get_current_user(
            authorization=f"Bearer {_jwt(_claims(**metadata))}",
            settings=_production_settings(),
        )

    assert exc.value.status_code == status_code
    assert exc.value.detail == message


def test_supabase_auth_uses_explicit_active_organization_header_when_membership_matches():
    token = _jwt(
        _claims(
            role="therapist",
            organization_id="org_a",
            organizations=[
                {"organization_id": "org_a", "role": "therapist", "active": True},
                {"organization_id": "org_b", "role": "clinical_supervisor", "active": True},
            ],
        )
    )
    principal = get_current_user(
        authorization=f"Bearer {token}",
        x_organization_id="org_b",
        settings=_production_settings(),
    )

    assert principal.organization_id == "org_b"
    assert principal.role == "clinical_supervisor"


def test_supabase_auth_requires_explicit_active_organization_when_multi_org_claims_are_ambiguous():
    token = _jwt(
        _claims(
            organization_id="",
            organizations=[
                {"organization_id": "org_a", "role": "therapist", "active": True},
                {"organization_id": "org_b", "role": "clinical_supervisor", "active": True},
            ],
        )
    )
    with pytest.raises(HTTPException) as exc:
        get_current_user(
            authorization=f"Bearer {token}",
            settings=_production_settings(),
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Active organization selection is required."


def test_break_glass_claim_is_rejected_for_non_platform_roles():
    with pytest.raises(HTTPException) as exc:
        get_current_user(
            authorization=(
                f"Bearer {_jwt(_claims(role='clinical_supervisor', break_glass={'active': True, 'case_id': 'case_demo_001', 'category': 'incident_review', 'reason': 'incident review', 'expires_at': int(time.time()) + 60}))}"
            ),
            settings=_production_settings(),
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Break-glass access is limited to platform operators."


def test_supabase_auth_accepts_inactive_break_glass_claim_without_scoped_access():
    principal = get_current_user(
        authorization=(
            f"Bearer {_jwt(_claims(role='platform_operator', break_glass={'active': False, 'case_id': 'case_demo_001', 'category': 'incident_review', 'reason': 'incident review', 'expires_at': int(time.time()) + 60}))}"
        ),
        settings=_production_settings(),
    )

    assert principal.role == "platform_operator"
    assert principal.break_glass_case_id is None
    assert principal.break_glass_expires_at is None


def test_supabase_claim_runtime_enforces_launch_role_matrix_on_case_access():
    repo = MockRepository()
    repo.cases["case_demo_001"].organization_id = "org_a"
    repo.cases["case_demo_001"].care_team_user_ids = ["clinician_a"]
    repo.cases["case_demo_001"].primary_therapist_user_id = "clinician_a"
    repo.upsert_membership(
        "org_a",
        OrganizationMembershipCreate(
            user_id="admin_a",
            display_name="Admin A",
            role="org_admin",
        ),
        actor_id="seed",
    )
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = _production_settings
    client = TestClient(app)
    try:
        assigned_therapist = client.get(
            "/api/v1/cases/case_demo_001",
            headers={"authorization": f"Bearer {_jwt(_claims())}"},
        )
        unassigned_therapist = client.get(
            "/api/v1/cases/case_demo_001",
            headers={"authorization": f"Bearer {_jwt(_claims_for_user('clinician_b'))}"},
        )
        supervisor = client.get(
            "/api/v1/cases/case_demo_001",
            headers={"authorization": f"Bearer {_jwt(_claims_for_user('supervisor_a', role='clinical_supervisor'))}"},
        )
        org_admin_case = client.get(
            "/api/v1/cases/case_demo_001",
            headers={"authorization": f"Bearer {_jwt(_claims_for_user('admin_a', role='org_admin'))}"},
        )
        org_admin_memberships = client.get(
            "/api/v1/organizations/current/memberships",
            headers={"authorization": f"Bearer {_jwt(_claims_for_user('admin_a', role='org_admin'))}"},
        )
    finally:
        _clear_overrides()

    assert assigned_therapist.status_code == 200
    assert unassigned_therapist.status_code == 403
    assert unassigned_therapist.json()["detail"] == "Care-team assignment required."
    assert supervisor.status_code == 200
    assert org_admin_case.status_code == 403
    assert org_admin_case.json()["detail"] == "Care-team assignment required."
    assert org_admin_memberships.status_code == 200
    assert [item["user_id"] for item in org_admin_memberships.json()] == ["admin_a"]


def test_supabase_claim_runtime_applies_selected_active_organization_to_request_scope():
    repo = MockRepository()
    repo.cases["case_demo_001"].organization_id = "org_a"
    repo.cases["case_demo_002"] = repo.cases["case_demo_001"].model_copy(
        update={
            "case_id": "case_demo_002",
            "organization_id": "org_b",
            "care_team_user_ids": ["supervisor_a"],
            "primary_therapist_user_id": "therapist_b",
        }
    )
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = _production_settings
    client = TestClient(app)
    supervisor_token = _jwt(
        _claims_for_user(
            "supervisor_a",
            role="clinical_supervisor",
            organization_id="org_a",
            organizations=[
                {"organization_id": "org_a", "role": "clinical_supervisor", "active": True},
                {"organization_id": "org_b", "role": "clinical_supervisor", "active": True},
            ],
        )
    )
    try:
        selected_org_b = client.get(
            "/api/v1/cases/case_demo_002",
            headers={
                "authorization": f"Bearer {supervisor_token}",
                "x-organization-id": "org_b",
            },
        )
        still_org_b_on_org_a_case = client.get(
            "/api/v1/cases/case_demo_001",
            headers={
                "authorization": f"Bearer {supervisor_token}",
                "x-organization-id": "org_b",
            },
        )
    finally:
        _clear_overrides()

    assert selected_org_b.status_code == 200
    assert selected_org_b.json()["case_id"] == "case_demo_002"
    assert still_org_b_on_org_a_case.status_code == 404
    assert still_org_b_on_org_a_case.json()["detail"] == "Case not found."


def test_supabase_break_glass_is_scoped_and_fails_closed_after_expiry():
    repo = MockRepository()
    repo.cases["case_demo_001"].organization_id = "org_a"
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = _production_settings
    client = TestClient(app)
    active_break_glass = {
        "authorization": f"Bearer {_jwt(_claims_for_user('platform_a', role='platform_operator', break_glass={'active': True, 'case_id': 'case_demo_001', 'category': 'incident_review', 'reason': 'incident review', 'expires_at': int(time.time()) + 60}))}",
    }
    wrong_case_break_glass = {
        "authorization": f"Bearer {_jwt(_claims_for_user('platform_a', role='platform_operator', break_glass={'active': True, 'case_id': 'case_demo_002', 'category': 'incident_review', 'reason': 'incident review', 'expires_at': int(time.time()) + 60}))}",
    }
    expired_break_glass = {
        "authorization": f"Bearer {_jwt(_claims_for_user('platform_a', role='platform_operator', break_glass={'active': True, 'case_id': 'case_demo_001', 'category': 'incident_review', 'reason': 'incident review', 'expires_at': int(time.time()) - 1}))}",
    }
    try:
        scoped_access = client.post("/api/v1/cases/case_demo_001/break-glass-access", headers=active_break_glass)
        wrong_case_access = client.post("/api/v1/cases/case_demo_001/break-glass-access", headers=wrong_case_break_glass)
        routine_case_read = client.get("/api/v1/cases/case_demo_001", headers=active_break_glass)
        expired_access = client.post("/api/v1/cases/case_demo_001/break-glass-access", headers=expired_break_glass)
    finally:
        _clear_overrides()

    assert scoped_access.status_code == 200
    assert scoped_access.json()["case_id"] == "case_demo_001"
    assert wrong_case_access.status_code == 403
    assert wrong_case_access.json()["detail"] == "Break-glass access is limited to the scoped case."
    assert routine_case_read.status_code == 403
    assert routine_case_read.json()["detail"] == "Clinical content access denied."
    assert expired_access.status_code == 403
    assert expired_access.json()["detail"] == "Break-glass access is expired."
    assert any(
        entry["target_id"] == "case_demo_001" and entry["message"] == "Scoped break-glass case access granted."
        for entry in repo.audit_log
    )
