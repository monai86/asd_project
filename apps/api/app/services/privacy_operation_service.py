from __future__ import annotations

from app.core.security import CurrentUser
from app.repositories.mock_repository import MockRepository, new_id
from app.schemas.clinical import PrivacyOperation, PrivacyOperationCreate, PrivacyOperationPatch, utc_now


def create_privacy_operation(
    repo: MockRepository,
    case_id: str,
    payload: PrivacyOperationCreate,
    user: CurrentUser,
) -> PrivacyOperation:
    operation = PrivacyOperation(
        privacy_operation_id=new_id("priv"),
        case_id=case_id,
        operation_type=payload.operation_type,
        requested_by=user.user_id,
        requester_role=user.role,
        reason=payload.reason,
        retention_days=payload.retention_days,
        legal_hold=payload.legal_hold,
    )
    repo.privacy_operations[operation.privacy_operation_id] = operation
    repo.add_audit("privacy_operation.create", operation.privacy_operation_id, "Privacy operation requested.")
    return repo.clone(operation)


def list_case_privacy_operations(repo: MockRepository, case_id: str) -> list[PrivacyOperation]:
    operations = [operation for operation in repo.privacy_operations.values() if operation.case_id == case_id]
    operations.sort(key=lambda item: item.created_at, reverse=True)
    return [repo.clone(operation) for operation in operations]


def list_privacy_operations(repo: MockRepository) -> list[PrivacyOperation]:
    operations = list(repo.privacy_operations.values())
    operations.sort(key=lambda item: item.created_at, reverse=True)
    return [repo.clone(operation) for operation in operations]


def patch_privacy_operation(repo: MockRepository, privacy_operation_id: str, payload: PrivacyOperationPatch) -> PrivacyOperation:
    operation = repo.privacy_operations[privacy_operation_id]
    updates = payload.model_dump(exclude_unset=True)
    next_status = updates.get("status", operation.status)
    next_legal_hold = updates.get("legal_hold", operation.legal_hold)
    if operation.operation_type == "deletion_review" and next_status == "completed" and next_legal_hold:
        raise ValueError("Deletion review cannot be completed while legal hold is active.")
    for key, value in updates.items():
        if value is not None:
            setattr(operation, key, value)
    if operation.operation_type == "deletion_review" and operation.status == "completed":
        operation.completed_at = operation.completed_at or utc_now()
        operation.preserve_evidence = True
        operation.evidence_retained = _deletion_review_evidence(repo, operation.case_id)
    operation.updated_at = utc_now()
    repo.add_audit("privacy_operation.patch", privacy_operation_id, f"Privacy operation status is {operation.status}.")
    return repo.clone(operation)


def _deletion_review_evidence(repo: MockRepository, case_id: str) -> dict[str, int]:
    signed_reports = sum(
        1
        for report in repo.reports.values()
        if report.case_id == case_id and report.signed_snapshot_hash
    )
    return {
        "audit_events": len(repo.audit_log),
        "signed_reports": signed_reports,
    }
