from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from src.clinical_workflow.models import (
    AIScreeningOutput,
    AudioFile,
    AuditLog,
    ChildCase,
    ClinicalSignoff,
    ConsentRecord,
    ExtractedFeatures,
    ProcessingJob,
    Report,
    Session,
    TherapistNote,
    TherapyGoal,
    Transcript,
    TranscriptLine,
    User,
)
from src.reference_engine import ReferenceComparisonResult


class ClinicalRepository(ABC):
    """Abstract base repository contract for ASD pilot persistence."""

    @abstractmethod
    def authenticate(self, email: str, password: str) -> User | None:
        """Authenticate a clinician/therapist and return the User record."""
        pass

    @abstractmethod
    def get_user(self, user_id: str) -> User | None:
        """Retrieve user profile by ID."""
        pass

    @abstractmethod
    def list_cases_for_user(self, user: User) -> list[ChildCase]:
        """List all child cases visible to the specified user."""
        pass

    @abstractmethod
    def get_case_for_user(self, case_id: str, user: User) -> ChildCase | None:
        """Get case details if authorized."""
        pass

    @abstractmethod
    def list_sessions_for_user(self, user: User) -> list[Session]:
        """List sessions visibility-gated by user ownership or admin rights."""
        pass

    @abstractmethod
    def list_sessions_for_case_for_user(self, case_id: str, user: User) -> list[Session]:
        """List all sessions belonging to a specific child case."""
        pass

    @abstractmethod
    def list_notes_for_case_for_user(self, case_id: str, user: User) -> list[TherapistNote]:
        """Retrieve notes associated with a case."""
        pass

    @abstractmethod
    def list_audio_files_for_user(self, user: User) -> list[AudioFile]:
        """List uploaded audio metadata records."""
        pass

    @abstractmethod
    def list_audio_files_for_case_for_user(self, case_id: str, user: User) -> list[AudioFile]:
        """List audio records linked to a child case."""
        pass

    @abstractmethod
    def list_audio_files_for_session_for_user(self, session_id: str, user: User) -> list[AudioFile]:
        """List audio records linked to a session."""
        pass

    @abstractmethod
    def list_consent_records_for_case_for_user(self, case_id: str, user: User) -> list[ConsentRecord]:
        """Retrieve consent history for a child case."""
        pass

    @abstractmethod
    def has_active_audio_consent(self, case_id: str, now: datetime | None = None) -> bool:
        """Check if active non-withdrawn audio consent exists for a child."""
        pass

    @abstractmethod
    def record_consent(
        self,
        *,
        case_id: str,
        user: User,
        audio_permission: bool,
        transcript_permission: bool = True,
        consent_type: str = "clinical_audio_processing",
        guardian_status: str = "guardian",
        notes: str = "",
        expires_at: datetime | None = None,
    ) -> ConsentRecord:
        """Log a new consent permission record."""
        pass

    @abstractmethod
    def create_secure_audio_upload_intent(
        self,
        *,
        case_id: str,
        session_id: str,
        user: User,
        original_filename: str,
        file_size: int,
        mime_type: str = "application/octet-stream",
        checksum_sha256: str | None = None,
        retention_days: int = 90,
        storage_provider: str = "supabase",
    ) -> dict:
        """Create private storage references and signed upload URLs."""
        pass

    @abstractmethod
    def create_processing_job(self, session_id: str, user: User, job_type: str = "audio_to_chat") -> ProcessingJob:
        """Submit an audio-to-CHAT processing job."""
        pass

    @abstractmethod
    def get_processing_job_for_user(self, job_id: str, user: User) -> ProcessingJob | None:
        """Retrieve job status."""
        pass

    @abstractmethod
    def update_processing_job(
        self,
        job_id: str,
        user: User,
        *,
        status: str,
        progress: int | None = None,
        error_code: str | None = None,
        error_message: str = "",
        stage: str | None = None,
        result_refs: dict[str, str] | None = None,
    ) -> ProcessingJob | None:
        """Update job stage or result references."""
        pass

    @abstractmethod
    def list_transcripts_for_user(self, user: User) -> list[Transcript]:
        """List all transcript records."""
        pass

    @abstractmethod
    def get_transcript_for_user(self, transcript_id: str, user: User) -> Transcript | None:
        """Get a transcript by ID."""
        pass

    @abstractmethod
    def get_transcript_for_session_for_user(self, session_id: str, user: User) -> Transcript | None:
        """Get transcript linked to a session."""
        pass

    @abstractmethod
    def get_features_for_session_for_user(self, session_id: str, user: User) -> ExtractedFeatures | None:
        """Get speech features calculated for a session."""
        pass

    @abstractmethod
    def get_ai_output_for_session_for_user(self, session_id: str, user: User) -> AIScreeningOutput | None:
        """Get latest AI decision support analysis for a session."""
        pass

    @abstractmethod
    def get_reference_comparison_for_session_for_user(
        self,
        session_id: str,
        user: User,
    ) -> ReferenceComparisonResult | None:
        """Compute descriptive Reference Comparison for an extracted feature row."""
        pass

    @abstractmethod
    def list_goals_for_case_for_user(self, case_id: str, user: User) -> list[TherapyGoal]:
        """Get intervention goals set for a case."""
        pass

    @abstractmethod
    def list_reports_for_case_for_user(self, case_id: str, user: User) -> list[Report]:
        """Retrieve generated report logs."""
        pass

    @abstractmethod
    def create_case(
        self,
        *,
        owner_user_id: str,
        anonymized_child_code: str,
        age_months: int,
        sex: Any,
        primary_concerns: str,
        consent_status: Any,
        anonymization_status: Any,
        external_clinical_status: Any = "not_provided",
        notes: str = "",
    ) -> ChildCase:
        """Create a new child case with validation."""
        pass

    @abstractmethod
    def update_case_for_user(
        self,
        case_id: str,
        user: User,
        *,
        age_months: int | None = None,
        sex: Any | None = None,
        primary_concerns: str | None = None,
        consent_status: Any | None = None,
        anonymization_status: Any | None = None,
        external_clinical_status: Any | None = None,
        notes: str | None = None,
    ) -> ChildCase | None:
        """Update case details."""
        pass

    @abstractmethod
    def create_session(
        self,
        *,
        case_id: str,
        user: User,
        session_date: str,
        session_type: Any,
        notes: str = "",
    ) -> Session:
        """Add a new evaluation or therapy session."""
        pass

    @abstractmethod
    def add_therapist_note(
        self,
        *,
        case_id: str,
        user: User,
        note_text: str,
        session_id: str | None = None,
    ) -> TherapistNote:
        """Log notes for a case/session."""
        pass

    @abstractmethod
    def create_audio_file_metadata(
        self,
        *,
        case_id: str,
        session_id: str,
        user: User,
        original_filename: str,
        file_size: int,
        processing_status: Any = "pending",
    ) -> AudioFile:
        """Write file metadata records."""
        pass

    @abstractmethod
    def create_transcript_for_session(
        self,
        *,
        session_id: str,
        user: User,
        transcript_text: str,
        original_filename: str | None = None,
        reviewer_notes: str = "",
    ) -> Transcript:
        """Upload/create CHAT transcript record."""
        pass

    @abstractmethod
    def update_transcript_for_user(
        self,
        transcript_id: str,
        user: User,
        *,
        transcript_text: str,
        reviewer_notes: str = "",
    ) -> Transcript | None:
        """Edit whole transcript text (triggers validation)."""
        pass

    @abstractmethod
    def update_transcript_line_for_user(
        self,
        transcript_id: str,
        line_id: str,
        user: User,
        *,
        speaker_code: str | None = None,
        utterance_text: str | None = None,
        reviewed: bool | None = None,
        interpretation_note: str | None = None,
        expected_version: int | None = None,
    ) -> TranscriptLine | None:
        """Edit specific transcript line with version lock."""
        pass

    @abstractmethod
    def mark_transcript_reviewed(self, transcript_id: str, user: User, reviewer_notes: str = "") -> Transcript | None:
        """Mark transcript status reviewed."""
        pass

    @abstractmethod
    def create_clinical_signoff(
        self,
        *,
        target_type: Any,
        target_id: str,
        user: User,
        session_id: str | None = None,
        notes: str = "",
    ) -> ClinicalSignoff:
        """Record formal clinician verification stamp."""
        pass

    @abstractmethod
    def signoff_transcript_for_session(self, session_id: str, user: User, notes: str = "") -> ClinicalSignoff:
        """Verify the transcript, setting its status to reviewed and recording signoff."""
        pass

    @abstractmethod
    def latest_signoff_for_target(self, target_type: Any, target_id: str) -> ClinicalSignoff | None:
        """Retrieve most recent signoff."""
        pass

    @abstractmethod
    def rerun_feature_extraction_after_transcript_review(self, session_id: str, user: User) -> Session | None:
        """Rerun feature calculations once transcript review completes."""
        pass

    @abstractmethod
    def extract_features_for_session(self, session_id: str, user: User) -> ExtractedFeatures:
        """Enforce reviewed-transcript gate and calculate derived features."""
        pass

    @abstractmethod
    def generate_ai_screening_output_for_session(self, session_id: str, user: User) -> AIScreeningOutput:
        """Generate non-diagnostic screening support values and explanations."""
        pass

    @abstractmethod
    def progress_summary_for_case(self, case_id: str, user: User) -> dict:
        """Compile longitudinal progress across all sessions."""
        pass

    @abstractmethod
    def generate_progress_report_for_case(self, case_id: str, user: User) -> Report:
        """Create a downloadable Markdown report."""
        pass

    @abstractmethod
    def dashboard_summary(self, user: User) -> dict[str, int]:
        """Aggregate summary counts for clinician dashboard landing."""
        pass

    @abstractmethod
    def list_audit_logs_for_user(self, user: User) -> list[AuditLog]:
        """Audit log reviewer. Admin role only."""
        pass
