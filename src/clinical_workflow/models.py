"""Database-ready clinical workflow data models for the therapist prototype.

These dataclasses describe the eventual persistence shape without binding the
project to a database provider. Current phases store deterministic mock records
only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal


Role = Literal["therapist", "clinician", "admin"]
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
ProcessingStatus = Literal["not_started", "pending", "processing", "completed", "failed"]
ReviewStatus = Literal["not_started", "awaiting_review", "reviewed", "needs_correction"]


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
    screening_support_score: float | None = None
    explanation: str = ""
    top_contributing_features: list[str] = field(default_factory=list)
    evidence_items: list[str] = field(default_factory=list)
    therapist_review_status: ReviewStatus = "awaiting_review"
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
