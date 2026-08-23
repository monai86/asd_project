from __future__ import annotations

from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import ConsentWithdrawalResult
from app.services.storage_service import get_storage_adapter


CONSENT_WITHDRAWN_MESSAGE = "Case consent has been withdrawn; new uploads, processing, edits, and exports are blocked."


def ensure_case_consent_active(repo: MockRepository, case_id: str) -> None:
    case = repo.get_case(case_id)
    if case is None:
        raise KeyError(case_id)
    if case.consent_status.lower() == "withdrawn":
        raise ValueError(CONSENT_WITHDRAWN_MESSAGE)


def ensure_session_consent_active(repo: MockRepository, session_id: str) -> None:
    session = repo.get_session(session_id)
    if session is None:
        raise KeyError(session_id)
    ensure_case_consent_active(repo, session.case_id)


def ensure_transcript_consent_active(repo: MockRepository, transcript_id: str) -> None:
    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise KeyError(transcript_id)
    ensure_case_consent_active(repo, transcript.case_id)


def ensure_report_consent_active(repo: MockRepository, report_id: str) -> None:
    report = repo.get_report(report_id)
    if report is None:
        raise KeyError(report_id)
    ensure_case_consent_active(repo, report.case_id)


def ensure_audio_file_consent_active(repo: MockRepository, audio_file_id: str) -> None:
    audio_file = repo.get_audio_file(audio_file_id)
    if audio_file is None:
        raise KeyError(audio_file_id)
    ensure_case_consent_active(repo, audio_file.case_id)


def withdraw_consent(repo: MockRepository, case_id: str, reason: str, redact_notes: bool = True) -> ConsentWithdrawalResult:
    affected = repo.withdraw_case_consent(
        case_id=case_id,
        actor_id="system",
        redact_notes=redact_notes,
    )
    for pending_audio in repo.list_pending_audio_deletions(case_id):
        try:
            deletion = get_storage_adapter().delete_object(pending_audio.object_key)
            deletion_status = deletion.status
            deletion_confirmed = deletion.deleted or deletion.status == "object_not_found"
        except Exception:  # storage failure is retried from the durable pending record
            deletion_status = "storage_error"
            deletion_confirmed = False
        try:
            repo.record_audio_deletion_result(
                pending_audio.audio_file_id,
                expected_version=pending_audio.version,
                deletion_status=deletion_status,
                deleted=deletion_confirmed,
                actor_id="system",
            )
        except Exception:  # consent is committed; pending state remains restart-recoverable
            continue
    return ConsentWithdrawalResult(
        case_id=case_id,
        affected_records=affected,
        audit_message="Consent withdrawal applied across case-linked records.",
    )
