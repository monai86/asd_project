from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from app.core.config import Settings


@dataclass(frozen=True)
class SupabasePrincipal:
    user_id: str
    role: str
    display_name: str
    organization_id: str
    mfa_verified: bool
    invitation_status: str
    membership_active: bool
    break_glass_reason: str | None = None
    break_glass_expires_at: int | None = None


def authenticate_supabase_bearer(authorization: str | None, settings: Settings) -> SupabasePrincipal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _unauthorized("Bearer token required.")
    token = authorization.split(" ", 1)[1].strip()
    claims = _decode_hs256_jwt(token, settings)
    metadata = claims.get("app_metadata")
    if not isinstance(metadata, dict):
        raise _unauthorized("Supabase app metadata is required.")

    user_id = _required_str(claims, "sub")
    organization_id = _required_str(metadata, "organization_id")
    role = _required_str(metadata, "role")
    display_name = _display_name(claims, metadata, user_id)
    membership_active = bool(metadata.get("membership_active"))
    mfa_verified = bool(metadata.get("mfa_verified"))
    invitation_status = str(metadata.get("invitation_status", ""))

    if not membership_active:
        raise _forbidden("Membership is not active.")
    if settings.supabase_require_mfa and not mfa_verified:
        raise _forbidden("MFA is required.")
    if settings.supabase_require_invitation and invitation_status != "accepted":
        raise _forbidden("Invitation must be accepted.")

    break_glass = metadata.get("break_glass")
    break_glass_reason = None
    break_glass_expires_at = None
    if isinstance(break_glass, dict) and break_glass.get("active"):
        break_glass_reason = str(break_glass.get("reason", "")).strip() or None
        if break_glass_reason is None:
            raise _forbidden("Break-glass access requires a reason.")
        break_glass_expires_at = int(break_glass.get("expires_at") or 0)
        if break_glass_expires_at <= int(time.time()):
            raise _forbidden("Break-glass access is expired.")

    return SupabasePrincipal(
        user_id=user_id,
        role=role,
        display_name=display_name,
        organization_id=organization_id,
        mfa_verified=mfa_verified,
        invitation_status=invitation_status,
        membership_active=membership_active,
        break_glass_reason=break_glass_reason,
        break_glass_expires_at=break_glass_expires_at,
    )


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


def _display_name(claims: dict[str, Any], metadata: dict[str, Any], user_id: str) -> str:
    for value in (metadata.get("display_name"), claims.get("email")):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return user_id


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
