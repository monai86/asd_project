from pydantic import BaseModel
from fastapi import Header, HTTPException, status


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
