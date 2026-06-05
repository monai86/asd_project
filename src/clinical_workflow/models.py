"""Database-ready clinical workflow data models for the therapist prototype.

These dataclasses describe the eventual persistence shape without binding the
project to a database provider. Current phases store deterministic mock records
only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


Role = Literal["therapist", "clinician", "supervisor", "admin"]
Sex = Literal["female", "male", "other", "not_specified"]
ConsentStatus = Literal["not_recorded", "pending", "granted", "declined"]
AnonymizationStatus = Literal["pending", "anonymized", "needs_review"]
ExternalClinicalStatus = Literal[
    "not_provided",
    "under_evaluation",
    "external_asd_recorded",
    "external_non_asd_recorded",
]
SessionType = Literal[
    "free_play",
    "parent_child_interaction",
    "structured_assessment",
    "therapy_session",
]
ProcessingStatus = Literal[
    "not_started",
    "pending",
    "processing_submitted",
    "processing",
    "transcript_ready",
    "completed",
    "failed",
    "stale",
]
ReviewStatus = Literal["not_started", "awaiting_review", "reviewed", "needs_correction"]
LineReviewStatus = Literal["needs_review", "reviewed"]
SpeakerRole = Literal["child", "therapist", "parent", "family", "other"]
StorageMode = Literal["metadata_only", "secure_private"]
JobStatus = Literal["queued", "processing", "completed", "failed", "cancelled"]
ArtifactFreshness = Literal["current", "preliminary", "stale", "failed", "superseded"]
ArtifactType = Literal[
    "reviewed_chat",
    "preliminary_chat",
    "batchalign_cha",
    "batchalign_log",
    "clan_raw_output",
    "clan_metrics",
    "feature_output",
    "subprocess_log",
]
FeatureReviewDispositionStatus = Literal["needs_review", "accepted", "rejected", "needs_context"]
StructuredProcessingEngine = Literal["local_whisper", "batchalign2", "clan", "python"]
StructuredProcessingOperation = Literal[
    "audio_to_chat",
    "batchalign.transcribe",
    "batchalign.align",
    "batchalign.morphotag",
    "clan.mlu",
    "clan.freq",
    "clan.kwal",
    "features.extract",
    "chat.export",
]
JobStage = Literal[
    "queued",
    "transcribing",
    "diarizing",
    "chat_formatting",
    "aligning",
    "morphotagging",
    "clan_running",
    "qa_running",
    "features_running",
    "awaiting_review",
    "completed",
    "failed",
]
SignoffTargetType = Literal["transcript", "features", "report"]


MOCK_MODE = True
ALLOWED_AUDIO_FILE_TYPES = ("wav", "mp3", "m4a", "mp4", "mov")
MAX_AUDIO_FILE_SIZE_MB = 250
MAX_AUDIO_FILE_SIZE_BYTES = MAX_AUDIO_FILE_SIZE_MB * 1024 * 1024
ALLOWED_TRANSCRIPT_FILE_TYPES = ("cha",)
SAFETY_DISCLAIMER = (
    "This system is a clinical decision-support prototype. It does not "
    "diagnose ASD and does not replace qualified clinical judgment."
)


def utc_now() -> datetime:
    """Return an aware UTC timestamp for database-ready records."""
    return datetime.now(timezone.utc)


@dataclass
class User:
    user_id: str
    name: str
    email: str
    role: Role
    organization: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    last_login: datetime | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ChildCase:
    case_id: str
    owner_user_id: str
    anonymized_child_code: str
    age_months: int
    sex: Sex
    primary_concerns: str
    external_clinical_status: ExternalClinicalStatus = "not_provided"
    consent_status: ConsentStatus = "not_recorded"
    anonymization_status: AnonymizationStatus = "anonymized"
    notes: str = ""
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Session:
    session_id: str
    case_id: str
    owner_user_id: str
    session_date: str
    session_type: SessionType
    audio_file_id: str | None = None
    transcript_id: str | None = None
    processing_status: ProcessingStatus = "not_started"
    feature_extraction_status: ProcessingStatus = "not_started"
    ai_analysis_status: ProcessingStatus = "not_started"
    therapist_review_status: ReviewStatus = "not_started"
    report_status: ProcessingStatus = "not_started"
    notes: str = ""
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Transcript:
    transcript_id: str
    session_id: str
    case_id: str
    owner_user_id: str
    transcript_format: str = "CHAT"
    transcript_text: str = ""
    review_status: ReviewStatus = "not_started"
    reviewer_notes: str = ""
    qa_status: str = "not_run"
    qa_score: int | None = None
    qa_issues: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TranscriptLine:
    line_id: str
    transcript_id: str
    session_id: str
    case_id: str
    owner_user_id: str
    line_number: int
    speaker_code: str
    utterance_text: str
    speaker_role: SpeakerRole = "other"
    reviewed_text: str | None = None
    start_time: float | None = None
    end_time: float | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    confidence: float | None = None
    word_timestamps: list[dict] = field(default_factory=list)
    flags: list[dict] = field(default_factory=list)
    review_status: LineReviewStatus = "needs_review"
    reviewed: bool = False
    interpretation_note: str = ""
    version: int = 1
    updated_at: datetime = field(default_factory=utc_now)
    updated_by_user_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AudioFile:
    audio_file_id: str
    owner_user_id: str
    case_id: str
    session_id: str
    original_filename: str
    stored_filename: str
    file_type: str
    file_size: int
    upload_time: datetime = field(default_factory=utc_now)
    processing_status: ProcessingStatus = "not_started"
    storage_mode: StorageMode = "metadata_only"
    file_object_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConsentRecord:
    consent_id: str
    case_id: str
    owner_user_id: str
    recorded_by_user_id: str
    consent_type: str = "clinical_audio_processing"
    guardian_status: Literal["guardian", "parent", "clinician_attested"] = "guardian"
    audio_permission: bool = False
    transcript_permission: bool = True
    notes: str = ""
    expires_at: datetime | None = None
    withdrawn_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FileObject:
    file_object_id: str
    audio_file_id: str
    case_id: str
    session_id: str
    owner_user_id: str
    storage_key: str
    checksum_sha256: str | None = None
    mime_type: str = "application/octet-stream"
    encryption_status: Literal["required", "verified"] = "required"
    retention_delete_after: datetime | None = None
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProcessingJob:
    job_id: str
    session_id: str
    case_id: str
    owner_user_id: str
    audio_file_id: str | None = None
    job_type: str = "audio_to_chat"
    engine: StructuredProcessingEngine | str = "local_whisper"
    operation: StructuredProcessingOperation | str = "audio_to_chat"
    operation_config: dict[str, Any] = field(default_factory=dict)
    dependency_check: dict[str, Any] = field(default_factory=dict)
    source_revision: str | None = None
    status: JobStatus = "queued"
    stage: JobStage = "queued"
    progress: int = 0
    error_code: str | None = None
    error_message: str = ""
    result_refs: dict[str, Any] = field(default_factory=dict)
    artifact_ids: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ClinicalSpeechArtifact:
    artifact_id: str
    session_id: str
    case_id: str
    owner_user_id: str
    artifact_type: ArtifactType | str
    freshness: ArtifactFreshness = "current"
    transcript_id: str | None = None
    feature_id: str | None = None
    job_id: str | None = None
    source_revision: str | None = None
    source_hash: str | None = None
    storage_mode: Literal["metadata_only", "secure_private"] = "metadata_only"
    storage_key: str | None = None
    content_type: str = "application/json"
    content_text: str = ""
    parsed_metrics: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    review_status: ReviewStatus = "awaiting_review"
    created_by_user_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("storage_key", None)
        content_text = data.pop("content_text", "")
        data["content_preview"] = content_text[:500]
        return data


@dataclass
class ClinicalSignoff:
    signoff_id: str
    target_type: SignoffTargetType
    target_id: str
    session_id: str | None
    case_id: str
    owner_user_id: str
    signed_by_user_id: str
    notes: str = ""
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FeatureReviewDisposition:
    disposition_id: str
    session_id: str
    case_id: str
    owner_user_id: str
    feature_id: str
    flag_key: str
    disposition: FeatureReviewDispositionStatus = "needs_review"
    note: str = ""
    reviewed_by_user_id: str | None = None
    source_revision: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ModelRun:
    model_run_id: str
    session_id: str
    case_id: str
    owner_user_id: str
    model_card_version: str
    feature_schema_version: str
    thresholds: dict[str, float]
    calibration_metadata: dict[str, str | float | int]
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExtractedFeatures:
    feature_id: str
    session_id: str
    case_id: str
    owner_user_id: str
    feature_schema_version: str
    features: dict[str, float]
    core_features: dict[str, float] = field(default_factory=dict)
    optional_indicators: dict[str, float] = field(default_factory=dict)
    source_revision: str | None = None
    source_hash: str | None = None
    extraction_status: ProcessingStatus = "completed"
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AIScreeningOutput:
    output_id: str
    session_id: str
    case_id: str
    owner_user_id: str
    concern_level: str
    model_version: str = "screening-support-v0.2.0"
    screening_support_score: float | None = None
    confidence_interval: dict[str, float | str] | None = None
    explanation: str = ""
    plain_language_explanation: str = ""
    top_contributing_features: list[str] = field(default_factory=list)
    evidence_items: list[dict] = field(default_factory=list)
    therapist_review_status: ReviewStatus = "awaiting_review"
    differential_probabilities: dict[str, float] | None = None
    output_kind: str = "screening_support"
    inference_status: str = "preliminary"
    reference_cohort_probabilities: dict[str, float] = field(default_factory=dict)
    most_similar_reference_cohort: str | None = None
    similarity_probability: float | None = None
    report_eligible: bool = False
    safety_warnings: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TherapyGoal:
    goal_id: str
    case_id: str
    owner_user_id: str
    goal_text: str
    status: Literal["active", "paused", "completed"] = "active"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TherapistNote:
    note_id: str
    case_id: str
    owner_user_id: str
    note_text: str
    session_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class Report:
    report_id: str
    case_id: str
    owner_user_id: str
    session_id: str | None = None
    report_type: str = "progress"
    title: str = ""
    content_markdown: str = ""
    export_status: ProcessingStatus = "not_started"
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AuditLog:
    audit_id: str
    event_type: str
    actor_user_id: str
    target_type: str
    target_id: str
    message: str
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)
