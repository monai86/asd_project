from __future__ import annotations

from app.auth.authorization import authoritative_org_user
from app.core.security import CurrentUser
from app.repositories.mock_repository import MockRepository, new_id
from app.schemas.clinical import PrivacyOperation, PrivacyOperationCreate, PrivacyOperationPatch, utc_now


def create_privacy_operation(
    repo: MockRepository,
    case_id: str,
    payload: PrivacyOperationCreate,
    user: CurrentUser,
) -> PrivacyOperation:
    user = authoritative_org_user(repo, user)
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
    return repo.create_privacy_operation(
        operation,
        actor_id=user.user_id,
        audit_action="privacy_operation.create",
        audit_message="Privacy operation requested.",
    )


def list_case_privacy_operations(repo: MockRepository, case_id: str) -> list[PrivacyOperation]:
    operations = repo.list_privacy_operations(case_id)
    operations.sort(key=lambda item: item.created_at, reverse=True)
    return [repo.clone(operation) for operation in operations]


def list_privacy_operations(repo: MockRepository) -> list[PrivacyOperation]:
    operations = repo.list_privacy_operations()
    operations.sort(key=lambda item: item.created_at, reverse=True)
    return [repo.clone(operation) for operation in operations]


def patch_privacy_operation(repo: MockRepository, privacy_operation_id: str, payload: PrivacyOperationPatch) -> PrivacyOperation:
    operation = repo.get_privacy_operation(privacy_operation_id)
    if operation is None:
        raise KeyError(privacy_operation_id)
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
    return repo.update_privacy_operation(
        operation,
        actor_id="system",
        audit_action="privacy_operation.patch",
        audit_message=f"Privacy operation status is {operation.status}.",
    )


def _deletion_review_evidence(repo: MockRepository, case_id: str) -> dict[str, int]:
    case = repo.get_case(case_id)
    if case is None:
        raise KeyError(case_id)
    reports = [report for report in repo.list_reports(case.organization_id) if report.case_id == case_id]
    signed_reports = sum(
        1
        for report in reports
        if report.signed_snapshot_hash
    )
    return {
        "audit_events": len(repo.list_case_audits(case_id, case.organization_id)),
        "signed_reports": signed_reports,
    }
