from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_repository
from app.core.security import CurrentUser, get_current_user, require_org_admin
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import AuditLogEntry

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogEntry])
def list_audit_logs(
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_org_admin(user)
    return [
        AuditLogEntry.model_validate(item)
        for item in repo.audit_log
        if item.get("organization_id") == user.organization_id
    ]
