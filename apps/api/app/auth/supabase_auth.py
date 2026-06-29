from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib import request as urllib_request
from urllib.error import URLError

from fastapi import HTTPException, status
import jwt
from jwt import PyJWK

from app.core.config import Settings

ALLOWED_SUPABASE_ROLES = {
    "therapist",
    "clinical_supervisor",
    "org_admin",
    "platform_operator",
}
ALLOWED_INVITATION_STATUSES = {
    "pending",
    "accepted",
    "revoked",
    "expired",
}
BREAK_GLASS_MAX_DURATION_SECONDS = 60 * 60
_JWKS_CACHE: dict[str, tuple[float, str]] = {}


@dataclass(frozen=True)
class SupabasePrincipal:
    user_id: str
    role: str
    display_name: str
    organization_id: str
    aal: str
    invitation_status: str
    membership_active: bool
    break_glass_category: str | None = None
    break_glass_reason: str | None = None
    break_glass_case_id: str | None = None
    break_glass_expires_at: int | None = None


def authenticate_supabase_bearer(
    authorization: str | None,
    settings: Settings,
    *,
    selected_organization_id: str | None = None,
) -> SupabasePrincipal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _unauthorized("Bearer token required.")
    token = authorization.split(" ", 1)[1].strip()
    claims = _decode_supabase_jwt(token, settings)
    metadata = claims.get("app_metadata")
    if not isinstance(metadata, dict):
        raise _unauthorized("Supabase app metadata is required.")

    memberships = _normalized_memberships(metadata)
    user_id = _required_str(claims, "sub")
    organization_id, role = _resolve_active_organization_context(
        metadata,
        memberships,
        selected_organization_id=selected_organization_id,
    )
    display_name = _display_name(claims, metadata, user_id)
    aal = _required_str(claims, "aal")
    membership_active = _required_bool(metadata, "membership_active")
    invitation_status = _required_invitation_status(metadata)

    if not membership_active:
        raise _forbidden("Membership is not active.")
    if settings.supabase_require_mfa and aal != "aal2":
        raise _forbidden("AAL2 session is required.")
    if settings.supabase_require_invitation and invitation_status != "accepted":
        raise _forbidden("Invitation must be accepted.")

    (
        break_glass_category,
        break_glass_reason,
        break_glass_case_id,
        break_glass_expires_at,
    ) = _parse_break_glass_claim(metadata, role)

    return SupabasePrincipal(
        user_id=user_id,
        role=role,
        display_name=display_name,
        organization_id=organization_id,
        aal=aal,
        invitation_status=invitation_status,
        membership_active=membership_active,
        break_glass_category=break_glass_category,
        break_glass_reason=break_glass_reason,
        break_glass_case_id=break_glass_case_id,
        break_glass_expires_at=break_glass_expires_at,
    )


def _decode_supabase_jwt(token: str, settings: Settings) -> dict[str, Any]:
    if settings.supabase_jwt_verification_mode == "jwks_url":
        return _decode_jwks_url_jwt(token, settings)
    if settings.supabase_jwt_verification_mode == "jwks_json":
        return _decode_jwks_jwt(token, settings)
    return _decode_hs256_jwt(token, settings)


def _decode_hs256_jwt(token: str, settings: Settings) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise _unauthorized("Invalid bearer token.")
    header = _json_part(parts[0])
    if header.get("alg") != "HS256":
        raise _unauthorized("Unsupported token algorithm.")
    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    expected = hmac.new(settings.supabase_jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64decode(parts[2]), expected):
        raise _unauthorized("Invalid bearer token.")

    claims = _json_part(parts[1])
    now = int(time.time())
    if int(claims.get("exp") or 0) <= now:
        raise _unauthorized("Bearer token expired.")
    if "nbf" in claims and int(claims["nbf"]) > now:
        raise _unauthorized("Bearer token not yet valid.")
    if settings.supabase_jwt_issuer and claims.get("iss") != settings.supabase_jwt_issuer:
        raise _unauthorized("Invalid token issuer.")
    if not _audience_matches(claims.get("aud"), settings.supabase_jwt_audience):
        raise _unauthorized("Invalid token audience.")
    return claims


def _decode_jwks_jwt(token: str, settings: Settings) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid bearer token.") from None
    if header.get("alg") != "RS256":
        raise _unauthorized("Unsupported token algorithm.")
    kid = header.get("kid")
    if not isinstance(kid, str) or not kid.strip():
        raise _unauthorized("Bearer token kid is required.")

    jwk = _find_jwk(settings.supabase_jwt_jwks_json, kid.strip())
    try:
        key = PyJWK.from_dict(jwk).key
        claims = jwt.decode(
            token,
            key=key,
            algorithms=["RS256"],
            audience=settings.supabase_jwt_audience,
            issuer=settings.supabase_jwt_issuer,
            options={"require": ["exp", "sub", "iss", "aud"]},
        )
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid bearer token.") from None
    if not isinstance(claims, dict):
        raise _unauthorized("Invalid bearer token.")
    return claims


def _decode_jwks_url_jwt(token: str, settings: Settings) -> dict[str, Any]:
    try:
        jwks_json = _load_jwks_json_from_url(
            settings.supabase_jwt_jwks_url,
            settings.supabase_jwt_jwks_cache_ttl_seconds,
        )
        shadow_settings = settings.model_copy(update={"supabase_jwt_jwks_json": jwks_json})
        return _decode_jwks_jwt(token, shadow_settings)
    except HTTPException as exc:
        if exc.detail != "Bearer token signing key was not found.":
            raise
    jwks_json = _load_jwks_json_from_url(
        settings.supabase_jwt_jwks_url,
        settings.supabase_jwt_jwks_cache_ttl_seconds,
        force_refresh=True,
    )
    shadow_settings = settings.model_copy(update={"supabase_jwt_jwks_json": jwks_json})
    return _decode_jwks_jwt(token, shadow_settings)


def _json_part(value: str) -> dict[str, Any]:
    try:
        decoded = _b64decode(value)
        parsed = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise _unauthorized("Invalid bearer token.") from None
    if not isinstance(parsed, dict):
        raise _unauthorized("Invalid bearer token.")
    return parsed


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(f"{value}{padding}")
    except ValueError:
        raise _unauthorized("Invalid bearer token.") from None


def _find_jwk(jwks_json: str, kid: str) -> dict[str, Any]:
    try:
        payload = json.loads(jwks_json)
    except ValueError:
        raise _unauthorized("Supabase JWKS JSON is invalid.") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("keys"), list):
        raise _unauthorized("Supabase JWKS JSON is invalid.")
    for item in payload["keys"]:
        if isinstance(item, dict) and item.get("kid") == kid:
            return item
    raise _unauthorized("Bearer token signing key was not found.")


def _load_jwks_json_from_url(url: str, cache_ttl_seconds: int, *, force_refresh: bool = False) -> str:
    now = time.time()
    cached = _JWKS_CACHE.get(url)
    if not force_refresh and cached and cached[0] > now:
        return cached[1]
    payload = _fetch_jwks_json_from_url(url)
    _JWKS_CACHE[url] = (now + cache_ttl_seconds, payload)
    return payload


def _fetch_jwks_json_from_url(url: str) -> str:
    try:
        with urllib_request.urlopen(url, timeout=5) as response:
            raw = response.read().decode("utf-8")
    except (OSError, UnicodeDecodeError, URLError):
        raise _unauthorized("Unable to fetch Supabase JWKS.") from None
    return raw


def reset_jwks_cache_for_tests() -> None:
    _JWKS_CACHE.clear()


def _audience_matches(claim_audience: Any, expected: str) -> bool:
    if isinstance(claim_audience, str):
        return claim_audience == expected
    if isinstance(claim_audience, list):
        return expected in claim_audience
    return False


def _required_str(container: dict[str, Any], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _unauthorized(f"Supabase claim '{key}' is required.")
    return value.strip()


def _required_bool(container: dict[str, Any], key: str) -> bool:
    value = container.get(key)
    if not isinstance(value, bool):
        raise _unauthorized(f"Supabase claim '{key}' must be a boolean.")
    return value


def _required_role(metadata: dict[str, Any]) -> str:
    role = _required_str(metadata, "role")
    if role not in ALLOWED_SUPABASE_ROLES:
        raise _unauthorized("Supabase claim 'role' is invalid.")
    return role


def _required_invitation_status(metadata: dict[str, Any]) -> str:
    invitation_status = _required_str(metadata, "invitation_status")
    if invitation_status not in ALLOWED_INVITATION_STATUSES:
        raise _unauthorized("Supabase claim 'invitation_status' is invalid.")
    return invitation_status


def _normalized_memberships(metadata: dict[str, Any]) -> list[dict[str, Any]] | None:
    memberships = metadata.get("organizations")
    if memberships is None:
        memberships = metadata.get("organization_memberships")
    if memberships is None:
        return None
    if not isinstance(memberships, list):
        raise _unauthorized("Supabase claim 'organizations' must be a list when present.")

    normalized_memberships: list[dict[str, Any]] = []
    for membership in memberships:
        if not isinstance(membership, dict):
            raise _unauthorized("Supabase claim 'organizations' contains an invalid membership entry.")
        candidate_org = membership.get("organization_id")
        candidate_role = membership.get("role")
        candidate_active = membership.get("active")
        if not isinstance(candidate_org, str) or not candidate_org.strip():
            raise _unauthorized("Supabase claim 'organizations' contains an invalid organization_id.")
        if not isinstance(candidate_role, str) or not candidate_role.strip():
            raise _unauthorized("Supabase claim 'organizations' contains an invalid role.")
        normalized_role = candidate_role.strip()
        if normalized_role not in ALLOWED_SUPABASE_ROLES:
            raise _unauthorized("Supabase claim 'organizations' contains an invalid role.")
        if candidate_active is not None and not isinstance(candidate_active, bool):
            raise _unauthorized("Supabase claim 'organizations' contains an invalid active flag.")
        normalized_memberships.append(
            {
                "organization_id": candidate_org.strip(),
                "role": normalized_role,
                "active": candidate_active,
            }
        )
    return normalized_memberships


def _resolve_active_organization_context(
    metadata: dict[str, Any],
    memberships: list[dict[str, Any]] | None,
    *,
    selected_organization_id: str | None,
) -> tuple[str, str]:
    requested_org = _optional_str(selected_organization_id)
    if memberships is None:
        if requested_org is not None and requested_org != _required_str(metadata, "organization_id"):
            raise _forbidden("Active organization is not present in the membership claims.")
        return _required_str(metadata, "organization_id"), _required_role(metadata)

    if requested_org is not None:
        return _resolve_membership_context(memberships, requested_org)

    claim_organization_id = _optional_str(metadata.get("organization_id"))
    if claim_organization_id is not None:
        claim_role = _required_role(metadata)
        return _resolve_membership_context(memberships, claim_organization_id, expected_role=claim_role)

    active_memberships = [membership for membership in memberships if membership.get("active") is not False]
    if len(active_memberships) == 1:
        return active_memberships[0]["organization_id"], active_memberships[0]["role"]

    raise _forbidden("Active organization selection is required.")


def _resolve_membership_context(
    memberships: list[dict[str, Any]],
    organization_id: str,
    *,
    expected_role: str | None = None,
) -> tuple[str, str]:
    for membership in memberships:
        if membership["organization_id"] != organization_id:
            continue
        if expected_role is not None and membership["role"] != expected_role:
            raise _unauthorized("Active organization role does not match the selected membership.")
        if membership.get("active") is False:
            raise _forbidden("Active organization membership is not active.")
        return membership["organization_id"], membership["role"]

    raise _forbidden("Active organization is not present in the membership claims.")


def _parse_break_glass_claim(
    metadata: dict[str, Any],
    role: str,
) -> tuple[str | None, str | None, str | None, int | None]:
    if "break_glass" not in metadata:
        return None, None, None, None

    break_glass = metadata.get("break_glass")
    if break_glass is None:
        return None, None, None, None
    if not isinstance(break_glass, dict):
        raise _unauthorized("Supabase claim 'break_glass' is invalid.")

    active = break_glass.get("active")
    if not isinstance(active, bool):
        raise _unauthorized("Supabase claim 'break_glass.active' must be a boolean.")
    if not active:
        return None, None, None, None

    if role != "platform_operator":
        raise _forbidden("Break-glass access is limited to platform operators.")

    category = _required_break_glass_str(break_glass, "category", "Break-glass access requires a category.")
    reason = _required_break_glass_str(break_glass, "reason", "Break-glass access requires a reason.")
    case_id = _required_break_glass_str(break_glass, "case_id", "Break-glass access requires a scoped case.")
    expires_at = break_glass.get("expires_at")
    if not isinstance(expires_at, int):
        raise _unauthorized("Supabase claim 'break_glass.expires_at' must be an integer.")
    now = int(time.time())
    if expires_at <= now:
        raise _forbidden("Break-glass access is expired.")
    if expires_at - now > BREAK_GLASS_MAX_DURATION_SECONDS:
        raise _forbidden("Break-glass access exceeds the one-hour limit.")
    return category, reason, case_id, expires_at


def _required_break_glass_str(container: dict[str, Any], key: str, detail: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _forbidden(detail)
    return value.strip()


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _display_name(claims: dict[str, Any], metadata: dict[str, Any], user_id: str) -> str:
    for value in (metadata.get("display_name"), claims.get("email")):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return user_id


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
