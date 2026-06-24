from pydantic import BaseModel
from fastapi import Request
from fastapi import Header, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp


UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class CurrentUser(BaseModel):
    user_id: str = "therapist-demo"
    role: str = "therapist"
    display_name: str = "Demo Therapist"


def get_current_user(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_mock_user_id: str | None = Header(default=None),
    x_mock_role: str | None = Header(default=None),
    x_mock_display_name: str | None = Header(default=None),
) -> CurrentUser:
    return CurrentUser(
        user_id=x_user_id or x_mock_user_id or "therapist-demo",
        role=x_mock_role or "therapist",
        display_name=x_mock_display_name or "Demo Therapist",
    )


def require_admin(user: CurrentUser) -> CurrentUser:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")
    return user


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
