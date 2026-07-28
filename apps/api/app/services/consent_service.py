from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta

from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    AudioUploadCleanupRemediation,
    ConsentWithdrawalResult,
    JobStatus,
    QaStatus,
    ReviewStatus,
    utc_now,
)
from app.services.storage_service import (
    StorageProcessingError,
    get_storage_adapter,
)


CONSENT_WITHDRAWN_MESSAGE = "Case consent has been withdrawn; new uploads, processing, edits, and exports are blocked."
UPLOAD_CLEANUP_MAX_ATTEMPTS = 5
UPLOAD_CLEANUP_BACKOFF_BASE_SECONDS = 30
UPLOAD_CLEANUP_BACKOFF_MAX_SECONDS = 3600


def refresh_repository(repo: MockRepository) -> None:
    load = getattr(repo, "load", None)
    if callable(load):
        load()


def ensure_case_consent_active(repo: MockRepository, case_id: str) -> None:
    assert_active = getattr(repo, "assert_case_consent_active", None)
    if callable(assert_active):
        try:
            assert_active(case_id)
            return
        except ValueError as exc:
            raise ValueError(CONSENT_WITHDRAWN_MESSAGE) from exc
    case = repo.cases[case_id]
    if case.consent_status.lower() == "withdrawn":
        raise ValueError(CONSENT_WITHDRAWN_MESSAGE)


def ensure_session_consent_active(repo: MockRepository, session_id: str) -> None:
    ensure_case_consent_active(repo, repo.sessions[session_id].case_id)


def ensure_transcript_consent_active(repo: MockRepository, transcript_id: str) -> None:
    ensure_case_consent_active(repo, repo.transcripts[transcript_id].case_id)


def ensure_report_consent_active(repo: MockRepository, report_id: str) -> None:
    ensure_case_consent_active(repo, repo.reports[report_id].case_id)


def ensure_audio_file_consent_active(repo: MockRepository, audio_file_id: str) -> None:
    ensure_case_consent_active(repo, repo.audio_files[audio_file_id].case_id)


@contextmanager
def active_case_consent_fence(repo: MockRepository, case_id: str):
    """Serialize a case-linked mutation and recheck current consent."""

    with repo.case_consent_fence(case_id):
        refresh_repository(repo)
        ensure_case_consent_active(repo, case_id)
        yield


def recover_audio_upload_cleanup(
    repo: MockRepository,
    audio_file_id: str,
    *,
    storage_adapter=None,
    actor_id: str = "system",
    attempted_at: datetime | None = None,
    only_if_due_at: datetime | None = None,
) -> bool | None:
    """Retry one durable, exact-key private audio cleanup."""

    adapter = storage_adapter or get_storage_adapter()
    initial_audio = repo.audio_files.get(audio_file_id)
    if initial_audio is None:
        load = getattr(repo, "load", None)
        if callable(load):
            load()
        initial_audio = repo.audio_files.get(audio_file_id)
    if initial_audio is None:
        raise ValueError("Audio file not found.")
    with repo.case_audio_fence(initial_audio.case_id, audio_file_id):
        load = getattr(repo, "load", None)
        if callable(load):
            load()
        audio_file = repo.audio_files.get(audio_file_id)
        if audio_file is None:
            raise ValueError("Audio file not found.")
        expected = audio_file.upload_cleanup_remediation
        if expected is None:
            return None if only_if_due_at is not None else True
        if (
            only_if_due_at is not None
            and (
                expected.state == "escalated"
                or (
                    expected.next_retry_at is not None
                    and expected.next_retry_at > only_if_due_at
                )
            )
        ):
            return None

        succeeded = True
        deletion_statuses: list[str] = []
        cleanup_error_code: str | None = None
        receipt = expected.receipt
        pinned_backend_identity = (
            expected.storage_backend_identity_sha256
        )
        committed_reference = bool(
            receipt is not None
            and audio_file.object_key
            == receipt.intended_final_object_key
            and audio_file.upload_status
            in {"pending_verification", "uploaded"}
        )
        try:
            if committed_reference:
                staging_cleanup = adapter.cleanup_upload_staging(receipt)
                succeeded = staging_cleanup.status in {
                    "deleted",
                    "object_not_found",
                    "missing_object_key",
                }
                deletion_statuses.append(staging_cleanup.status)
            elif receipt is not None:
                attempt_cleanup = adapter.cleanup_upload_attempt(receipt)
                succeeded = attempt_cleanup.succeeded
                deletion_statuses.extend(
                    [
                        attempt_cleanup.staging.status,
                        attempt_cleanup.final.status,
                    ]
                )
            if (
                expected.final_object_key is not None
                and not committed_reference
                and (
                    receipt is None
                    or expected.final_object_key
                    != receipt.intended_final_object_key
                )
            ):
                adapter.validate_storage_backend_identity(
                    pinned_backend_identity
                    or audio_file.storage_backend_identity_sha256
                )
                final_cleanup = adapter.delete_object(
                    expected.final_object_key
                )
                deletion_statuses.append(final_cleanup.status)
                succeeded = succeeded and (
                    final_cleanup.status
                    in {
                        "deleted",
                        "object_not_found",
                        "missing_object_key",
                    }
                )
            for object_key in expected.additional_object_keys:
                if repo.has_durable_normalized_object_reference(
                    source_audio_file_id=audio_file_id,
                    object_key=object_key,
                ):
                    deletion_statuses.append(
                        "durable_reference_preserved"
                    )
                    continue
                adapter.validate_storage_backend_identity(
                    pinned_backend_identity
                )
                additional_cleanup = adapter.delete_object(object_key)
                deletion_statuses.append(additional_cleanup.status)
                succeeded = succeeded and (
                    additional_cleanup.status
                    in {
                        "deleted",
                        "object_not_found",
                        "missing_object_key",
                    }
                )
        except StorageProcessingError as exc:
            succeeded = False
            cleanup_error_code = exc.code
            deletion_statuses.append("storage_cleanup_failed")
        except Exception:  # noqa: BLE001
            succeeded = False
            deletion_statuses.append("storage_cleanup_failed")

        remediation = None
        if not succeeded:
            attempted_at = attempted_at or utc_now()
            attempt_count = expected.attempt_count + 1
            identity_failure = cleanup_error_code in {
                "storage_receipt_backend_identity_missing",
                "storage_receipt_backend_mismatch",
                "storage_receipt_protocol_legacy",
            }
            escalated = (
                identity_failure
                or attempt_count >= UPLOAD_CLEANUP_MAX_ATTEMPTS
            )
            delay_seconds = min(
                UPLOAD_CLEANUP_BACKOFF_MAX_SECONDS,
                UPLOAD_CLEANUP_BACKOFF_BASE_SECONDS
                * (2 ** max(0, attempt_count - 1)),
            )
            remediation = expected.model_copy(
                update={
                    "state": "escalated" if escalated else "failed",
                    "error_code": (
                        cleanup_error_code or "storage_cleanup_failed"
                    ),
                    "attempt_count": attempt_count,
                    "last_attempt_at": attempted_at,
                    "next_retry_at": (
                        None
                        if escalated
                        else attempted_at + timedelta(seconds=delay_seconds)
                    ),
                }
            )
        storage_delete_status = (
            "deleted"
            if "deleted" in deletion_statuses
            else (
                "durable_reference_preserved"
                if "durable_reference_preserved" in deletion_statuses
                else (
                    "object_not_found"
                    if succeeded
                    else "storage_cleanup_failed"
                )
            )
        )
        if not audio_file.retained and audio_file.upload_status == "withdrawn":
            repo.record_audio_consent_cleanup(
                audio_file_id,
                expected_remediation=expected,
                remediation=remediation,
                storage_delete_status=storage_delete_status,
                actor_id=actor_id,
            )
        elif receipt is not None:
            repo.record_audio_upload_cleanup(
                receipt,
                remediation=remediation,
                actor_id=actor_id,
            )
        elif expected.additional_object_keys:
            repo.record_normalized_audio_cleanup(
                audio_file_id,
                expected_remediation=expected,
                remediation=remediation,
                storage_delete_status=storage_delete_status,
                actor_id=actor_id,
            )
        else:
            raise ValueError(
                "Upload cleanup remediation has no ownership receipt."
            )
        return succeeded


def withdraw_consent(repo: MockRepository, case_id: str, reason: str, redact_notes: bool = True) -> ConsentWithdrawalResult:
    del reason
    storage_adapter = get_storage_adapter()
    with repo.case_consent_fence(case_id):
        load = getattr(repo, "load", None)
        if callable(load):
            load()

        case = repo.cases[case_id]
        affected = {
            "sessions": 0,
            "therapy_goals": 0,
            "audio_metadata": 0,
            "transcripts": 0,
            "features": 0,
            "ml_results": 0,
            "ai_reviews": 0,
            "reports": 0,
            "jobs": 0,
            "speaker_mappings": 0,
            "limitation_acknowledgments": 0,
            "transcript_attestations": 0,
            "chat_exports": 0,
            "findings_results": 0,
            "private_asr_evidence": 0,
        }
        case.consent_status = "withdrawn"
        case.version += 1
        case.updated_at = utc_now()
        case.latest_session_status = ReviewStatus.withdrawn
        case.latest_report_status = ReviewStatus.withdrawn
        if redact_notes:
            case.notes = ""
        for session in repo.sessions.values():
            if session.case_id != case_id:
                continue
            affected["sessions"] += 1
            session.status = ReviewStatus.withdrawn
            if session.notes and redact_notes:
                session.notes = ""
        for goal in repo.therapy_goals.values():
            if goal.case_id == case_id:
                affected["therapy_goals"] += 1
                goal.title = "Consent withdrawn."
                goal.target = ""
                goal.status = "withdrawn"
                goal.retained = False
                goal.notes = ""
                goal.updated_at = utc_now()
        for transcript in repo.transcripts.values():
            if transcript.case_id == case_id:
                affected["transcripts"] += 1
                transcript.source = "withdrawn"
                transcript.raw_text = ""
                transcript.utterances = []
                transcript.qa_status = QaStatus.not_run
                transcript.qa_issues = []
                transcript.review_status = ReviewStatus.withdrawn
                transcript.therapist_attested = False
                transcript.attestation_reason = ""
                transcript.chat_metadata = {}
                transcript.orphan_dependent_tiers = []
                transcript.malformed_lines = []
                transcript.asr_profile = None
                transcript.asr_provenance = None
                transcript.raw_speaker_labels = []
                transcript.updated_at = utc_now()

        normalized_keys_by_audio: dict[str, list[str]] = {}
        case_audio_ids = {
            audio_file.audio_file_id
            for audio_file in repo.audio_files.values()
            if audio_file.case_id == case_id
        }
        for normalized_asset in repo.normalized_audio_assets.values():
            if normalized_asset.source_audio_file_id in case_audio_ids:
                normalized_keys_by_audio.setdefault(
                    normalized_asset.source_audio_file_id,
                    [],
                ).append(normalized_asset.object_key)

        cleanup_targets = []
        for audio_file in repo.audio_files.values():
            if audio_file.case_id != case_id:
                continue
            affected["audio_metadata"] += 1
            audio_file.original_filename = "withdrawn-audio"
            pending_cleanup = AudioUploadCleanupRemediation(
                state="pending",
                receipt=audio_file.active_upload_receipt,
                final_object_key=audio_file.object_key,
                additional_object_keys=normalized_keys_by_audio.get(
                    audio_file.audio_file_id,
                    [],
                ),
                storage_backend_identity_sha256=(
                    audio_file.storage_backend_identity_sha256
                ),
            )
            cleanup_targets.append(
                (
                    audio_file.audio_file_id,
                    audio_file.active_upload_receipt,
                    audio_file.object_key,
                    audio_file.storage_backend_identity_sha256,
                    pending_cleanup.additional_object_keys,
                    pending_cleanup,
                )
            )
            audio_file.upload_cleanup_remediation = pending_cleanup
            audio_file.object_key = None
            audio_file.upload_status = "withdrawn"
            audio_file.retained = False
            audio_file.current_normalized_asset_version = None
            audio_file.current_normalized_checksum_sha256 = None

        case_session_ids = {
            session.session_id
            for session in repo.sessions.values()
            if session.case_id == case_id
        }
        case_transcript_ids = {
            transcript.transcript_id
            for transcript in repo.transcripts.values()
            if transcript.case_id == case_id
        }
        for attribute, affected_key in (
            ("speaker_mappings", "speaker_mappings"),
            (
                "limitation_acknowledgments",
                "limitation_acknowledgments",
            ),
            ("transcript_attestations", "transcript_attestations"),
            ("chat_exports", "chat_exports"),
            ("findings_results", "findings_results"),
        ):
            records = getattr(repo, attribute)
            for record_key, record in list(records.items()):
                if record.transcript_id in case_transcript_ids:
                    affected[affected_key] += 1
                    del records[record_key]
        for evidence_key, evidence in list(
            repo.private_asr_evidence.items()
        ):
            if evidence.transcript_id in case_transcript_ids:
                affected["private_asr_evidence"] += 1
                del repo.private_asr_evidence[evidence_key]
        for feature_id, feature_set in list(repo.features.items()):
            if feature_set.session_id in case_session_ids:
                affected["features"] += 1
                del repo.features[feature_id]
                if feature_set.session_id in repo.sessions:
                    repo.sessions[feature_set.session_id].feature_set_id = None
        for review in repo.ai_reviews.values():
            if review.session_id in case_session_ids:
                affected["ai_reviews"] += 1
                review.summary = (
                    "Consent withdrawn. AI-assisted review content unlinked "
                    "from clinical workflow."
                )
                review.assistance_areas = []
                review.key_findings = []
                review.concerns = []
                review.strengths = []
                review.limitations = [
                    "Consent withdrawn; prior AI-assisted review support is "
                    "no longer retained for workflow use."
                ]
                review.recommended_review_actions = []
                review.confidence_level = "unavailable"
                review.feature_set_id = None
                review.therapist_review_status = ReviewStatus.withdrawn
                review.therapist_notes = ""
                review.rejected_reason = "Consent withdrawn."
        for result_id, result in list(repo.ml_results.items()):
            if result.session_id in case_session_ids:
                affected["ml_results"] += 1
                del repo.ml_results[result_id]
                repo.sessions[result.session_id].ml_result_id = None
        for report in repo.reports.values():
            if report.case_id == case_id:
                affected["reports"] += 1
                report.status = ReviewStatus.withdrawn
                report.therapist_signoff_status = ReviewStatus.withdrawn
                report.title = "Consent withdrawn."
                report.markdown = (
                    "Consent withdrawn. Report content unlinked from clinical "
                    "workflow."
                )
                report.html = (
                    "<p>Consent withdrawn. Report content unlinked from "
                    "clinical workflow.</p>"
                )
                report.export_timestamp = None
                report.fallback_reason = None
                report.safety_validation_result = None
                report.finalized_safety_result = None
                report.input_hash = None
                report.signed_by = None
                report.signed_at = None
                report.signed_snapshot_version = None
                report.signed_snapshot_hash = None
                report.signed_snapshot = None
                report.transcript_id = None
                report.feature_result_id = None
                report.ml_result_id = None
                report.validation_summary = None
                report.therapist_notes = None
                report.session_goals = []
                report.generated_from_versions = {}
                report.sections = []
                report.updated_at = utc_now()
        for job in repo.jobs.values():
            if job.session_id in case_session_ids:
                affected["jobs"] += 1
                allowed_history = {status.value for status in JobStatus}
                raw_history = job.details.get("status_history", [])
                history_values = (
                    raw_history if isinstance(raw_history, list) else []
                )
                history = [
                    value
                    for value in history_values
                    if isinstance(value, str)
                    and value in allowed_history
                ]
                details: dict[str, object] = {
                    "consent_withdrawn": True,
                    "storage_unlinked": True,
                    "retry_allowed": False,
                    "status_history": history,
                }
                attempt_number = job.details.get("attempt_number")
                if (
                    isinstance(attempt_number, int)
                    and not isinstance(attempt_number, bool)
                    and attempt_number > 0
                ):
                    details["attempt_number"] = attempt_number
                if job.status in {
                    JobStatus.queued,
                    JobStatus.processing,
                }:
                    job.status = JobStatus.cancelled
                    if not history or history[-1] != JobStatus.cancelled.value:
                        history.append(JobStatus.cancelled.value)
                    details["status_history"] = history
                job.error_code = "consent_withdrawn"
                job.message = (
                    "Consent withdrawn. Job history is restricted."
                )
                job.updated_at = utc_now()
                job.details = details
        repo.commit_consent_withdrawal(
            case_id=case_id,
            source_audio_file_ids=case_audio_ids,
            audit_message=(
                "Consent withdrawn by authorized request; linked workflow "
                "outputs were removed or unlinked."
            ),
        )

        for (
            audio_file_id,
            receipt,
            final_object_key,
            backend_identity_sha256,
            additional_object_keys,
            pending_cleanup,
        ) in cleanup_targets:
            cleanup_succeeded = True
            deletion_statuses: list[str] = []
            cleanup_error_code: str | None = None
            try:
                if receipt is not None:
                    attempt_cleanup = (
                        storage_adapter.cleanup_upload_attempt(receipt)
                    )
                    cleanup_succeeded = attempt_cleanup.succeeded
                    deletion_statuses.extend(
                        [
                            attempt_cleanup.staging.status,
                            attempt_cleanup.final.status,
                        ]
                    )
                if (
                    final_object_key is not None
                    and (
                        receipt is None
                        or final_object_key
                        != receipt.intended_final_object_key
                    )
                ):
                    storage_adapter.validate_storage_backend_identity(
                        backend_identity_sha256
                    )
                    final_cleanup = storage_adapter.delete_object(
                        final_object_key
                    )
                    deletion_statuses.append(final_cleanup.status)
                    cleanup_succeeded = cleanup_succeeded and (
                        final_cleanup.status
                        in {
                            "deleted",
                            "object_not_found",
                            "missing_object_key",
                        }
                    )
                for object_key in additional_object_keys:
                    storage_adapter.validate_storage_backend_identity(
                        backend_identity_sha256
                    )
                    normalized_cleanup = storage_adapter.delete_object(
                        object_key
                    )
                    deletion_statuses.append(normalized_cleanup.status)
                    cleanup_succeeded = cleanup_succeeded and (
                        normalized_cleanup.status
                        in {
                            "deleted",
                            "object_not_found",
                            "missing_object_key",
                        }
                    )
            except StorageProcessingError as exc:
                cleanup_succeeded = False
                cleanup_error_code = exc.code
                deletion_statuses.append("storage_cleanup_failed")
            except OSError:
                cleanup_succeeded = False
                deletion_statuses.append("storage_cleanup_failed")

            identity_failure = cleanup_error_code in {
                "storage_receipt_backend_identity_missing",
                "storage_receipt_backend_mismatch",
                "storage_receipt_protocol_legacy",
            }
            remediation = (
                None
                if cleanup_succeeded
                else AudioUploadCleanupRemediation(
                    state=(
                        "escalated" if identity_failure else "failed"
                    ),
                    receipt=receipt,
                    final_object_key=final_object_key,
                    additional_object_keys=additional_object_keys,
                    storage_backend_identity_sha256=(
                        backend_identity_sha256
                    ),
                    error_code=(
                        cleanup_error_code or "storage_cleanup_failed"
                    ),
                    attempt_count=1,
                    last_attempt_at=utc_now(),
                    next_retry_at=(
                        None
                        if identity_failure
                        else utc_now()
                        + timedelta(
                            seconds=UPLOAD_CLEANUP_BACKOFF_BASE_SECONDS
                        )
                    ),
                )
            )
            storage_delete_status = (
                "deleted"
                if "deleted" in deletion_statuses
                else (
                    "object_not_found"
                    if cleanup_succeeded
                    else "storage_cleanup_failed"
                )
            )
            repo.record_audio_consent_cleanup(
                audio_file_id,
                expected_remediation=pending_cleanup,
                remediation=remediation,
                storage_delete_status=storage_delete_status,
                actor_id="system",
            )

        return ConsentWithdrawalResult(
            case_id=case_id,
            affected_records=affected,
            audit_message=(
                "Consent withdrawal applied across case-linked records."
            ),
        )
