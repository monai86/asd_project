from __future__ import annotations

from typing import Protocol

from app.schemas.clinical import (
    AiReview,
    AudioFileMetadata,
    ChildCase,
    ChildCaseCreate,
    ChildCaseUpdate,
    FeatureSet,
    MLResult,
    TherapySession,
    TherapySessionCreate,
    TherapySessionUpdate,
    Transcript,
    ReviewStatus,
    Report,
    PrivacyOperation,
    ProcessingJob,
    TherapyGoal,
)
from app.schemas.speaker_mapping import SpeakerMapping


class CaseVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale clinical record version."""


class SessionVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale session record version."""


class TranscriptVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale transcript record version."""


class ReportVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale report record version."""


class SpeakerMappingVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale speaker-mapping draft version."""


class ClinicalRepository(Protocol):
    def new_id(self, prefix: str) -> str: ...

    def get_transcript(self, transcript_id: str) -> Transcript | None: ...

    def create_audio_upload(
        self, audio_file: AudioFileMetadata, job: ProcessingJob, *, actor_id: str
    ) -> ProcessingJob: ...

    def update_audio_file_metadata(
        self,
        audio_file: AudioFileMetadata,
        *,
        actor_id: str,
        expected_version: int,
        expected_upload_status: str,
        audit_action: str | None = None,
        audit_message: str | None = None,
    ) -> AudioFileMetadata: ...

    def create_processing_job(
        self,
        job: ProcessingJob,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> ProcessingJob: ...

    def update_processing_job(
        self,
        job: ProcessingJob,
        *,
        actor_id: str,
        expected_version: int,
        expected_status: str,
        audit_action: str,
        audit_message: str,
    ) -> ProcessingJob: ...

    def complete_processing_job(
        self,
        job: ProcessingJob,
        transcript: Transcript,
        *,
        actor_id: str,
        expected_version: int,
        expected_status: str,
        audit_action: str,
        audit_message: str,
    ) -> ProcessingJob: ...

    def withdraw_case_consent(
        self,
        *,
        case_id: str,
        actor_id: str,
        redact_notes: bool,
    ) -> dict[str, int]: ...

    def list_pending_audio_deletions(self, case_id: str | None = None) -> list[AudioFileMetadata]: ...

    def record_audio_deletion_result(
        self,
        audio_file_id: str,
        *,
        expected_version: int,
        deletion_status: str,
        deleted: bool,
        actor_id: str,
    ) -> AudioFileMetadata: ...

    def acknowledge_session_cues(
        self,
        session_id: str,
        *,
        acknowledged_at: str,
        expected_version: int,
        actor_id: str,
    ) -> TherapySession: ...

    def get_latest_speaker_mapping(self, transcript_id: str) -> SpeakerMapping | None: ...

    def save_speaker_mapping_draft(
        self,
        mapping: SpeakerMapping,
        *,
        expected_mapping_version: int | None,
        actor_id: str,
    ) -> SpeakerMapping: ...

    def confirm_speaker_mapping(
        self,
        mapping: SpeakerMapping,
        transcript: Transcript,
        *,
        expected_transcript_version: int,
        expected_mapping_version: int,
        actor_id: str,
    ) -> SpeakerMapping: ...

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
