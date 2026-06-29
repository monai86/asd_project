from fastapi import APIRouter, Depends

from app.auth.authorization import require_case, require_org_case
from app.api.v1.dependencies import get_repository
from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser, get_current_user, require_org_admin
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import PrivacyOperation, PrivacyOperationAdminView, PrivacyOperationCreate, PrivacyOperationPatch
from app.services.privacy_operation_service import (
    create_privacy_operation,
    list_case_privacy_operations,
    list_privacy_operations,
    patch_privacy_operation,
)

router = APIRouter(tags=["privacy"])


@router.post("/cases/{case_id}/privacy-requests", response_model=PrivacyOperation)
def request_case_privacy_operation(
    case_id: str,
    payload: PrivacyOperationCreate,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    if case_id not in repo.cases:
        raise not_found("Case not found.")
    require_case(repo, case_id, user)
    return create_privacy_operation(repo, case_id, payload, user)


@router.get("/cases/{case_id}/privacy-requests", response_model=list[PrivacyOperation])
def get_case_privacy_operations(
    case_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    if case_id not in repo.cases:
        raise not_found("Case not found.")
    require_case(repo, case_id, user)
    return list_case_privacy_operations(repo, case_id)


@router.get("/privacy/requests", response_model=list[PrivacyOperationAdminView])
def get_privacy_operation_queue(
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_org_admin(user)
    return [
        PrivacyOperationAdminView.model_validate(operation.model_dump(mode="python"))
        for operation in list_privacy_operations(repo)
        if repo.cases[operation.case_id].organization_id == user.organization_id
    ]


@router.patch("/privacy/requests/{privacy_operation_id}", response_model=PrivacyOperationAdminView)
def update_privacy_operation(
    privacy_operation_id: str,
    payload: PrivacyOperationPatch,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_org_admin(user)
    if privacy_operation_id not in repo.privacy_operations:
        raise not_found("Privacy operation not found.")
    require_org_case(repo, repo.privacy_operations[privacy_operation_id].case_id, user)
    try:
        operation = patch_privacy_operation(repo, privacy_operation_id, payload)
        return PrivacyOperationAdminView.model_validate(operation.model_dump(mode="python"))
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
