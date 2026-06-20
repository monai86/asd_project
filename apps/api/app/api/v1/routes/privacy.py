from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_repository
from app.core.errors import not_found
from app.core.security import CurrentUser, get_current_user, require_admin
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import PrivacyOperation, PrivacyOperationCreate, PrivacyOperationPatch
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
    return create_privacy_operation(repo, case_id, payload, user)


@router.get("/cases/{case_id}/privacy-requests", response_model=list[PrivacyOperation])
def get_case_privacy_operations(case_id: str, repo: MockRepository = Depends(get_repository)):
    if case_id not in repo.cases:
        raise not_found("Case not found.")
    return list_case_privacy_operations(repo, case_id)


@router.get("/privacy/requests", response_model=list[PrivacyOperation])
def get_privacy_operation_queue(
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_admin(user)
    return list_privacy_operations(repo)


@router.patch("/privacy/requests/{privacy_operation_id}", response_model=PrivacyOperation)
def update_privacy_operation(
    privacy_operation_id: str,
    payload: PrivacyOperationPatch,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_admin(user)
    if privacy_operation_id not in repo.privacy_operations:
        raise not_found("Privacy operation not found.")
    return patch_privacy_operation(repo, privacy_operation_id, payload)
