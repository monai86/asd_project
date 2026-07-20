from fastapi import APIRouter, Depends, Request

from app.api.v1.dependencies import get_repository
from app.core.security import CurrentUser, get_current_user, require_organization_admin
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import AuditLogEntry

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogEntry])
def list_audit_logs(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    require_organization_admin(
        user,
        repo,
        organization_id=user.organization_id,
        denied_action="organization.audit.list_denied",
        target_id="organization_audit",
        request_id=request.headers.get("x-request-id"),
    )
    return [
        AuditLogEntry.model_validate(item)
        for item in repo.audit_log
        if item.get("organization_id") == user.organization_id
    ]
