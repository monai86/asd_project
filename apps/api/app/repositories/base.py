from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import datetime
from typing import Protocol
from typing import Callable

from app.schemas.clinical import (
    AiReview,
    AudioFileMetadata,
    AudioUploadCleanupRemediation,
    AudioUploadOwnershipReceipt,
    ChildCase,
    ChildCaseCreate,
    ChildCaseUpdate,
    FeatureSet,
    JobStatus,
    MLResult,
    ProcessingJob,
    TherapySession,
    TherapySessionCreate,
    TherapySessionUpdate,
    Transcript,
    ReviewStatus,
    Report,
    PrivacyOperation,
    TherapyGoal,
)
from app.schemas.speech_pipeline import PrivateAsrEvidenceRecord


class CaseVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale clinical record version."""


class SessionVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale session record version."""


class TranscriptVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale transcript record version."""


class ReportVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale report record version."""


class ProcessingJobStateConflictError(RuntimeError):
    """Raised when a worker attempts an invalid durable job transition."""

    def __init__(self, job: ProcessingJob) -> None:
        self.job = job
        super().__init__(
            f"Processing job {job.job_id} is already {job.status.value}."
        )


class ClinicalRepository(Protocol):
    def case_consent_fence(
        self,
        case_id: str,
    ) -> AbstractContextManager[None]: ...

    def audio_upload_fence(
        self,
        audio_file_id: str,
    ) -> AbstractContextManager[None]: ...

    def case_audio_fence(
        self,
        case_id: str,
        audio_file_id: str,
    ) -> AbstractContextManager[None]: ...

    def assert_case_consent_active(self, case_id: str) -> None: ...

    def commit_consent_withdrawal(
        self,
        *,
        case_id: str,
        source_audio_file_ids: set[str],
        audit_message: str,
        actor_id: str = "system",
    ) -> None: ...

    def list_due_audio_upload_cleanups(
        self,
        now: datetime,
        *,
        limit: int,
    ) -> list[str]: ...

    def get_case(self, case_id: str) -> ChildCase | None: ...

    def create_case(self, payload: ChildCaseCreate, *, actor_id: str) -> ChildCase: ...

    def update_case(
        self,
        case_id: str,
        patch: ChildCaseUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> ChildCase: ...

    def list_cases_for_user(self, user_id: str, organization_id: str) -> list[ChildCase]: ...

    def create_session(self, case_id: str, payload: TherapySessionCreate, *, actor_id: str) -> TherapySession: ...

    def update_session(
        self,
        session_id: str,
        patch: TherapySessionUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> TherapySession: ...

    def get_processing_job(self, job_id: str) -> ProcessingJob | None: ...

    def find_processing_job_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> ProcessingJob | None: ...

    def create_processing_job(
        self,
        job: ProcessingJob,
        *,
        audit_action: str,
        audit_message: str,
    ) -> tuple[ProcessingJob, bool]: ...

    def update_processing_job(
        self,
        job: ProcessingJob,
        *,
        expected_status: JobStatus,
        audit_action: str,
        audit_message: str,
    ) -> ProcessingJob: ...

    def finalize_transcription_draft(
        self,
        *,
        job: ProcessingJob,
        expected_status: JobStatus,
        transcript: Transcript,
        evidence: PrivateAsrEvidenceRecord,
    ) -> ProcessingJob: ...

    def get_private_asr_evidence(
        self,
        job_id: str,
    ) -> PrivateAsrEvidenceRecord | None: ...

    def mark_audio_upload_persisted(
        self,
        audio_file_id: str,
        *,
        expected_upload_status: str,
        expected_source_asset_version: int,
        actor_id: str,
    ) -> AudioFileMetadata: ...

    def reserve_audio_upload_attempt(
        self,
        receipt: AudioUploadOwnershipReceipt,
        *,
        actor_id: str,
    ) -> AudioUploadOwnershipReceipt: ...

    def finalize_audio_upload_attempt(
        self,
        receipt: AudioUploadOwnershipReceipt,
        *,
        promote: Callable[[], None],
        actor_id: str,
    ) -> AudioFileMetadata: ...

    def record_audio_upload_cleanup(
        self,
        receipt: AudioUploadOwnershipReceipt,
        *,
        remediation: AudioUploadCleanupRemediation | None,
        actor_id: str,
    ) -> None: ...

    def record_audio_consent_cleanup(
        self,
        audio_file_id: str,
        *,
        expected_remediation: AudioUploadCleanupRemediation,
        remediation: AudioUploadCleanupRemediation | None,
        storage_delete_status: str,
        actor_id: str,
    ) -> None: ...

    def reserve_normalized_audio_cleanup(
        self,
        audio_file_id: str,
        *,
        expected_source_asset_version: int,
        object_key: str,
        storage_backend_identity_sha256: str,
        actor_id: str,
    ) -> AudioUploadCleanupRemediation: ...

    def clear_normalized_audio_cleanup(
        self,
        audio_file_id: str,
        *,
        expected_source_asset_version: int,
        expected_remediation: AudioUploadCleanupRemediation,
        actor_id: str,
    ) -> None: ...

    def record_normalized_audio_cleanup(
        self,
        audio_file_id: str,
        *,
        expected_remediation: AudioUploadCleanupRemediation,
        remediation: AudioUploadCleanupRemediation | None,
        storage_delete_status: str,
        actor_id: str,
    ) -> None: ...

    def has_durable_normalized_object_reference(
        self,
        *,
        source_audio_file_id: str,
        object_key: str,
    ) -> bool: ...

    def unlink_normalized_audio_assets(
        self,
        source_audio_file_ids: set[str],
    ) -> None: ...

    def create_transcript(
        self,
        transcript: Transcript,
        *,
        session_status: ReviewStatus,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Transcript: ...

    def update_transcript(
        self,
        transcript: Transcript,
        *,
        session_status: ReviewStatus,
        expected_version: int | None,
        actor_id: str,
        audit_action: str,
        audit_message: str,
        invalidate_downstream: bool = True,
    ) -> Transcript: ...

    def create_report(
        self,
        report: Report,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report: ...

    def update_report(
        self,
        report: Report,
        *,
        expected_version: int | None,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report: ...

    def create_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal: ...

    def update_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal: ...

    def create_privacy_operation(
        self,
        operation: PrivacyOperation,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> PrivacyOperation: ...

    def update_privacy_operation(
        self,
        operation: PrivacyOperation,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> PrivacyOperation: ...

    def create_feature_set(
        self,
        feature_set: FeatureSet,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> FeatureSet: ...

    def create_ai_review(
        self,
        review: AiReview,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> AiReview: ...

    def update_ai_review(
        self,
        review: AiReview,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> AiReview: ...

    def create_ml_result(
        self,
        result: MLResult,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> MLResult: ...

    def update_ml_result(
        self,
        result: MLResult,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> MLResult: ...
