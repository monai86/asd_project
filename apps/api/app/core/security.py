import time

from pydantic import BaseModel
from fastapi import Depends, Request
from fastapi import Header, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.auth.supabase_auth import authenticate_supabase_bearer
from app.core.config import Settings, get_settings


UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
BREAK_GLASS_MAX_DURATION_SECONDS = 60 * 60
ALLOWED_LAUNCH_ROLES = {"therapist", "clinical_supervisor", "org_admin", "platform_operator"}


class CurrentUser(BaseModel):
    user_id: str = "therapist-demo"
    role: str = "therapist"
    display_name: str = "Demo Therapist"
    organization_id: str = "pilot_org_001"
    aal: str = "aal1"
    invitation_status: str = "local_mock"
    membership_active: bool = True
    break_glass_category: str | None = None
    break_glass_reason: str | None = None
    break_glass_case_id: str | None = None
    break_glass_expires_at: int | None = None


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_mock_user_id: str | None = Header(default=None),
    x_mock_role: str | None = Header(default=None),
    x_mock_display_name: str | None = Header(default=None),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
    x_break_glass_category: str | None = Header(default=None),
    x_break_glass_reason: str | None = Header(default=None),
    x_break_glass_case_id: str | None = Header(default=None),
    x_break_glass_expires_at: int | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if settings.auth_mode != "mock":
        principal = authenticate_supabase_bearer(
            authorization,
            settings,
            selected_organization_id=x_organization_id,
        )
        return CurrentUser(
            user_id=principal.user_id,
            role=principal.role,
            display_name=principal.display_name,
            organization_id=principal.organization_id,
            aal=principal.aal,
            invitation_status=principal.invitation_status,
            membership_active=principal.membership_active,
            break_glass_category=principal.break_glass_category,
            break_glass_reason=principal.break_glass_reason,
            break_glass_case_id=principal.break_glass_case_id,
            break_glass_expires_at=principal.break_glass_expires_at,
        )
    role = _validate_mock_role(x_mock_role or "therapist")
    user = CurrentUser(
        user_id=x_user_id or x_mock_user_id or "therapist-demo",
        role=role,
        display_name=x_mock_display_name or "Demo Therapist",
        organization_id=x_organization_id or "pilot_org_001",
        break_glass_category=x_break_glass_category.strip() if x_break_glass_category else None,
        break_glass_reason=x_break_glass_reason.strip() if x_break_glass_reason else None,
        break_glass_case_id=x_break_glass_case_id.strip() if x_break_glass_case_id else None,
        break_glass_expires_at=x_break_glass_expires_at,
    )
    _validate_mock_break_glass(user)
    return user


def require_org_admin(user: CurrentUser) -> CurrentUser:
    if user.role != "org_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization admin role required.")
    return user


def require_therapist(user: CurrentUser) -> CurrentUser:
    if user.role != "therapist":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Therapist role required.")
    return user


def _validate_mock_role(role: str) -> str:
    normalized = role.strip()
    if normalized not in ALLOWED_LAUNCH_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Mock role '{normalized or role}' is invalid.",
        )
    return normalized


def _validate_mock_break_glass(user: CurrentUser) -> None:
    if user.role != "platform_operator" or user.break_glass_expires_at is None:
        return
    if not user.break_glass_category:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Break-glass access requires a category.")
    if not user.break_glass_reason:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Break-glass access requires a reason.")
    if not user.break_glass_case_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Break-glass access requires a scoped case.")
    if user.break_glass_expires_at <= int(time.time()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Break-glass access is expired.")
    if user.break_glass_expires_at - int(time.time()) > BREAK_GLASS_MAX_DURATION_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Break-glass access exceeds the one-hour limit.",
        )


class OriginGuardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, allowed_origins: list[str], enabled: bool = True) -> None:
        super().__init__(app)
        self.allowed_origins = set(allowed_origins)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next):
        if not self.enabled or request.method not in UNSAFE_METHODS:
            return await call_next(request)
        origin = request.headers.get("origin")
        if origin is not None and origin not in self.allowed_origins:
            return JSONResponse({"detail": "Origin is not allowed."}, status_code=status.HTTP_403_FORBIDDEN)
        return await call_next(request)
