from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import threading
from uuid import uuid4

from app.schemas.clinical import (
    AiReview,
    AudioFileMetadata,
    CareTeamAssignment,
    CareTeamAssignmentCreate,
    ChildCase,
    ChildCaseCreate,
    ChildCaseUpdate,
    FeatureSet,
    MLResult,
    OrganizationMembership,
    OrganizationMembershipCreate,
    OrganizationInvitation,
    OrganizationInvitationAccept,
    OrganizationInvitationCreate,
    PrivacyOperation,
    ProcessingJob,
    Report,
    ReviewStatus,
    TherapyGoal,
    TherapySession,
    TherapySessionCreate,
    TherapySessionUpdate,
    Transcript,
    utc_now,
)
from app.repositories.base import (
    CaseVersionConflictError,
    ReportVersionConflictError,
    SessionVersionConflictError,
    SpeakerMappingVersionConflictError,
    TranscriptVersionConflictError,
)
from app.schemas.speaker_mapping import MappingPersistedStatus, SpeakerMapping
from app.services.audit_safety import validate_audit_event

INVITATION_EXPIRY_DAYS = 7
ALLOWED_JOB_TRANSITIONS = {
    "queued": {"processing", "failed", "cancelled"},
    "processing": {"transcription_completed", "needs_review", "failed", "cancelled"},
    "transcription_completed": {"needs_review", "failed", "cancelled"},
    "failed": set(),
    "cancelled": set(),
    "needs_review": set(),
}


class JsonRepositoryDurabilityError(RuntimeError):
    """Raised when a JSON snapshot was replaced but directory durability is uncertain."""


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


class MockRepository:
    """In-memory repository for local demo and contract tests."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.cases: dict[str, ChildCase] = {}
        self.sessions: dict[str, TherapySession] = {}
        self.transcripts: dict[str, Transcript] = {}
        self.speaker_mappings: dict[str, SpeakerMapping] = {}
        self.features: dict[str, FeatureSet] = {}
        self.ml_results: dict[str, MLResult] = {}
        self.ai_reviews: dict[str, AiReview] = {}
        self.reports: dict[str, Report] = {}
        self.memberships: dict[str, OrganizationMembership] = {}
        self.invitations: dict[str, OrganizationInvitation] = {}
        self.care_team_assignments: dict[str, CareTeamAssignment] = {}
        self.therapy_goals: dict[str, TherapyGoal] = {}
        self.audio_files: dict[str, AudioFileMetadata] = {}
        self.jobs: dict[str, ProcessingJob] = {}
        self.privacy_operations: dict[str, PrivacyOperation] = {}
        self.organization_settings: dict[str, dict[str, object]] = {}
        self.audit_log: list[dict] = []
        self.seed()

    def seed(self) -> None:
        if self.cases:
            return
        case = ChildCase(
            case_id="case_demo_001",
            organization_id="pilot_org_001",
            care_team_user_ids=["therapist-demo"],
            primary_therapist_user_id="therapist-demo",
            child_code="C-1024",
            nickname="Demo child",
            age_months=62,
            language="English",
            consent_status="granted",
            review_priority="moderate",
        )
        session = TherapySession(
            session_id="session_demo_001",
            case_id=case.case_id,
            session_date="2026-06-12",
            session_type="therapy_session",
            status=ReviewStatus.needs_review,
        )
        case.latest_session_date = session.session_date
        case.latest_session_status = session.status
        self.cases[case.case_id] = case
        self.sessions[session.session_id] = session
        self.organization_settings.setdefault(case.organization_id, {"ai_review_enabled": True})

    def clone(self, value):
        return deepcopy(value)

    def new_id(self, prefix: str) -> str:
        return new_id(prefix)

    def get_transcript(self, transcript_id: str) -> Transcript | None:
        with self._lock:
            transcript = self.transcripts.get(transcript_id)
            return self.clone(transcript) if transcript is not None else None

    def is_ai_review_enabled(self, organization_id: str) -> bool:
        settings = self.organization_settings.get(organization_id, {})
        return bool(settings.get("ai_review_enabled", False))

    def set_ai_review_enabled(self, organization_id: str, enabled: bool) -> None:
        settings = dict(self.organization_settings.get(organization_id, {}))
        settings["ai_review_enabled"] = enabled
        self.organization_settings[organization_id] = settings

    def add_audit(
        self,
        action: str,
        target_id: str,
        message: str,
        *,
        actor_id: str = "system",
        outcome: str = "success",
        correlation_id: str = "local",
        organization_id: str | None = None,
    ) -> None:
        with self._lock:
            event = validate_audit_event(
                actor_id=actor_id,
                action=action,
                target_id=target_id,
                outcome=outcome,
                correlation_id=correlation_id,
                message=message,
            )
            event_data = event.as_dict()
            event_data["organization_id"] = organization_id or self._organization_for_target(target_id)
            self.audit_log.append(event_data)

    def create_audio_upload(
        self,
        audio_file: AudioFileMetadata,
        job: ProcessingJob,
        *,
        actor_id: str,
    ) -> ProcessingJob:
        with self._lock:
            session = self.sessions[audio_file.session_id]
            case = self.cases[session.case_id]
            if case.consent_status.lower() == "withdrawn":
                raise ValueError("Case consent has been withdrawn.")
            if audio_file.case_id != case.case_id or job.session_id != session.session_id:
                raise ValueError("Audio upload ownership does not match the authoritative session.")
            saved_audio = self.clone(audio_file)
            saved_audio.organization_id = session.organization_id
            saved_audio.version = 1
            saved_job = self.clone(job)
            saved_job.organization_id = session.organization_id
            saved_job.version = 1
            audit = self._build_audit_data(
                "audio.upload",
                saved_job.job_id,
                "Experimental audio processing job queued.",
                actor_id=actor_id,
                organization_id=saved_job.organization_id,
            )
            self.audio_files[saved_audio.audio_file_id] = saved_audio
            self.jobs[saved_job.job_id] = saved_job
            self.audit_log.append(audit)
            return self.clone(saved_job)

    def update_audio_file_metadata(
        self,
        audio_file: AudioFileMetadata,
        *,
        actor_id: str,
        expected_version: int,
        expected_upload_status: str,
        audit_action: str | None = None,
        audit_message: str | None = None,
    ) -> AudioFileMetadata:
        with self._lock:
            if audio_file.audio_file_id not in self.audio_files:
                raise KeyError(audio_file.audio_file_id)
            current = self.audio_files[audio_file.audio_file_id]
            case = self.cases[current.case_id]
            if case.consent_status.lower() == "withdrawn":
                raise ValueError("Case consent has been withdrawn.")
            if current.version != expected_version or current.upload_status != expected_upload_status:
                raise ValueError("Audio metadata changed; reload and retry.")
            if (current.organization_id, current.session_id, current.case_id) != (
                audio_file.organization_id, audio_file.session_id, audio_file.case_id
            ):
                raise ValueError("Audio metadata ownership changed; reload and retry.")
            saved = self.clone(audio_file)
            saved.version = current.version + 1
            audit = None
            if audit_action is not None:
                audit = self._build_audit_data(
                    audit_action,
                    saved.audio_file_id,
                    audit_message or "Audio metadata updated.",
                    actor_id=actor_id,
                    organization_id=saved.organization_id,
                )
            self.audio_files[saved.audio_file_id] = saved
            if audit is not None:
                self.audit_log.append(audit)
            return self.clone(saved)

    def create_processing_job(
        self,
        job: ProcessingJob,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> ProcessingJob:
        with self._lock:
            session = self.sessions[job.session_id]
            case = self.cases[session.case_id]
            if case.consent_status.lower() == "withdrawn":
                raise ValueError("Case consent has been withdrawn.")
            if job.audio_file_id:
                audio = self.audio_files[job.audio_file_id]
                if audio.session_id != session.session_id or not audio.retained or audio.upload_status != "uploaded":
                    raise ValueError("Audio file is not available for processing.")
                if any(
                    current.active_audio_file_id == job.audio_file_id
                    for current in self.jobs.values()
                ):
                    raise ValueError("Only one active processing job is allowed per audio artifact.")
            initial_status = job.status.value if hasattr(job.status, "value") else str(job.status)
            if initial_status not in {"queued", "failed"}:
                raise ValueError("Processing jobs must begin queued or failed.")
            expected_active = job.audio_file_id if initial_status == "queued" else None
            if job.active_audio_file_id != expected_active:
                raise ValueError("Processing job active-audio claim is inconsistent.")
            saved = self.clone(job)
            saved.organization_id = session.organization_id
            saved.version = 1
            audit = self._build_audit_data(
                audit_action, saved.job_id, audit_message,
                actor_id=actor_id, organization_id=saved.organization_id,
            )
            self.jobs[saved.job_id] = saved
            self.audit_log.append(audit)
            return self.clone(saved)

    def update_processing_job(
        self,
        job: ProcessingJob,
        *,
        actor_id: str,
        expected_version: int,
        expected_status: str,
        audit_action: str,
        audit_message: str,
    ) -> ProcessingJob:
        with self._lock:
            if job.job_id not in self.jobs:
                raise KeyError(job.job_id)
            current = self.jobs[job.job_id]
            current_status = current.status.value if hasattr(current.status, "value") else str(current.status)
            next_status = job.status.value if hasattr(job.status, "value") else str(job.status)
            if current.version != expected_version or current_status != expected_status:
                raise ValueError("Processing job changed; reload and retry.")
            if next_status not in ALLOWED_JOB_TRANSITIONS.get(current_status, set()):
                raise ValueError(f"Processing job transition {current_status} -> {next_status} is not allowed.")
            case = self.cases[self.sessions[current.session_id].case_id]
            if (
                job.organization_id != current.organization_id
                or job.session_id != current.session_id
                or job.audio_file_id != current.audio_file_id
            ):
                raise ValueError("Processing job ownership changed; reload and retry.")
            if case.consent_status.lower() == "withdrawn" and next_status != "cancelled":
                raise ValueError("Case consent has been withdrawn.")
            saved = self.clone(job)
            saved.version = current.version + 1
            saved.active_audio_file_id = (
                None if next_status in {"failed", "cancelled", "needs_review"}
                else current.audio_file_id
            )
            audit = self._build_audit_data(
                audit_action, saved.job_id, audit_message,
                actor_id=actor_id, organization_id=saved.organization_id,
            )
            self.jobs[saved.job_id] = saved
            self.audit_log.append(audit)
            return self.clone(saved)

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
    ) -> ProcessingJob:
        with self._lock:
            if job.job_id not in self.jobs:
                raise KeyError(job.job_id)
            current_job = self.jobs[job.job_id]
            current_status = current_job.status.value if hasattr(current_job.status, "value") else str(current_job.status)
            if current_job.version != expected_version or current_status != expected_status:
                raise ValueError("Processing job changed; reload and retry.")
            submitted_status = job.status.value if hasattr(job.status, "value") else str(job.status)
            if expected_status not in {"processing", "transcription_completed"} or submitted_status != "needs_review":
                raise ValueError("ASR completion job transition is not allowed.")
            if job.audio_file_id != current_job.audio_file_id:
                raise ValueError("ASR completion audio ownership changed; reload and retry.")
            session = self.sessions[transcript.session_id]
            case = self.cases[session.case_id]
            if (
                current_job.session_id != session.session_id
                or transcript.case_id != session.case_id
                or job.organization_id != current_job.organization_id
                or job.session_id != current_job.session_id
            ):
                raise ValueError("ASR result ownership does not match the authoritative job.")
            if case.consent_status.lower() == "withdrawn":
                raise ValueError("Case consent has been withdrawn.")
            saved_transcript = self.clone(transcript)
            saved_transcript.organization_id = session.organization_id
            saved_job = self.clone(job)
            saved_job.organization_id = session.organization_id
            saved_job.version = current_job.version + 1
            saved_job.active_audio_file_id = None
            saved_session = self.clone(session)
            saved_session.transcript_id = saved_transcript.transcript_id
            saved_session.status = ReviewStatus.needs_review
            audit = self._build_audit_data(
                audit_action, saved_job.job_id, audit_message,
                actor_id=actor_id, organization_id=saved_job.organization_id,
            )
            prepared_invalidation_audit = self._build_audit_data(
                "workflow.invalidate_downstream",
                saved_transcript.transcript_id,
                "Derived workflow outputs marked stale after transcript change.",
                actor_id=actor_id,
                organization_id=saved_job.organization_id,
            )
            invalidated = self._mark_downstream_outputs_stale(saved_session)
            invalidation_audit = prepared_invalidation_audit if invalidated else None
            self.transcripts[saved_transcript.transcript_id] = saved_transcript
            self.sessions[saved_session.session_id] = saved_session
            self.jobs[saved_job.job_id] = saved_job
            self._recompute_case_summaries(saved_session.case_id)
            self.audit_log.append(audit)
            if invalidation_audit is not None:
                self.audit_log.append(invalidation_audit)
            return self.clone(saved_job)

    def withdraw_case_consent(
        self,
        *,
        case: ChildCase,
        sessions: dict[str, TherapySession],
        therapy_goals: dict[str, TherapyGoal],
        audio_files: dict[str, AudioFileMetadata],
        transcripts: dict[str, Transcript],
        feature_ids_to_delete: set[str],
        ml_result_ids_to_delete: set[str],
        ai_reviews: dict[str, AiReview],
        reports: dict[str, Report],
        jobs: dict[str, ProcessingJob],
        actor_id: str,
        redact_notes: bool,
    ) -> None:
        with self._lock:
            current_case = self.cases.get(case.case_id)
            if (
                current_case is None
                or current_case.consent_status.lower() == "withdrawn"
                or current_case.version + 1 != case.version
            ):
                raise ValueError("Case consent state changed; reload and retry.")
            authoritative_session_ids = {
                item.session_id for item in self.sessions.values() if item.case_id == case.case_id
            }
            if set(sessions) != authoritative_session_ids:
                raise ValueError("Consent withdrawal aggregate changed; reload and retry.")
            for session_id, submitted in sessions.items():
                if self.sessions[session_id].version + 1 != submitted.version:
                    raise ValueError("Consent withdrawal aggregate changed; reload and retry.")
            audit = self._build_audit_data(
                "consent.withdraw",
                case.case_id,
                "Consent withdrawn by authorized request; linked workflow outputs were removed or unlinked.",
                actor_id=actor_id,
                organization_id=case.organization_id,
            )
            self.cases[case.case_id] = self.clone(case)
            self.sessions.update(self.clone(sessions))
            self.therapy_goals.update(self.clone(therapy_goals))
            self.audio_files.update(self.clone(audio_files))
            self.transcripts.update(self.clone(transcripts))
            for feature_id in feature_ids_to_delete:
                self.features.pop(feature_id, None)
            for result_id in ml_result_ids_to_delete:
                self.ml_results.pop(result_id, None)
            self.ai_reviews.update(self.clone(ai_reviews))
            self.reports.update(self.clone(reports))
            self.jobs.update(self.clone(jobs))
            self._recompute_case_summaries(case.case_id)
            self.audit_log.append(audit)

    def list_pending_audio_deletions(self, case_id: str | None = None) -> list[AudioFileMetadata]:
        with self._lock:
            return [
                self.clone(audio)
                for audio in self.audio_files.values()
                if (
                    audio.storage_delete_status == "pending_deletion"
                    or str(audio.storage_delete_status).startswith("retryable:")
                )
                and (case_id is None or audio.case_id == case_id)
            ]

    def record_audio_deletion_result(
        self, audio_file_id: str, *, expected_version: int, deletion_status: str,
        deleted: bool, actor_id: str,
    ) -> AudioFileMetadata:
        with self._lock:
            current = self.audio_files[audio_file_id]
            if current.version != expected_version or not (
                current.storage_delete_status == "pending_deletion"
                or str(current.storage_delete_status).startswith("retryable:")
            ):
                raise ValueError("Audio deletion state changed; reload and retry.")
            saved = self.clone(current)
            saved.version += 1
            saved.storage_delete_status = deletion_status if deleted else f"retryable:{deletion_status}"
            if deleted:
                saved.object_key = None
            audit = self._build_audit_data(
                "audio.storage_delete", audio_file_id,
                "Audio storage deletion outcome recorded.", actor_id=actor_id,
                organization_id=saved.organization_id,
            )
            self.audio_files[audio_file_id] = saved
            self.audit_log.append(audit)
            return self.clone(saved)

    def acknowledge_session_cues(
        self, session_id: str, *, acknowledged_at: str, expected_version: int, actor_id: str
    ) -> TherapySession:
        with self._lock:
            current = self.sessions[session_id]
            if current.version != expected_version:
                raise SessionVersionConflictError("Session changed; reload and retry.")
            if self.cases[current.case_id].consent_status.lower() == "withdrawn":
                raise ValueError("Case consent has been withdrawn.")
            saved = self.clone(current)
            saved.version += 1
            saved.cues_acknowledged_at = acknowledged_at
            saved.cues_acknowledged_by = actor_id
            patch_audit = self._build_audit_data(
                "session.patch", session_id, "Session updated.", actor_id=actor_id,
                organization_id=saved.organization_id,
            )
            cue_audit = self._build_audit_data(
                "cues_acknowledged", session_id,
                "Therapist acknowledged reviewed cues in the findings workspace.",
                actor_id=actor_id, organization_id=saved.organization_id,
            )
            self.sessions[session_id] = saved
            self.audit_log.extend((patch_audit, cue_audit))
            return self.clone(saved)

    @staticmethod
    def _build_audit_data(action, target_id, message, *, actor_id, organization_id):
        event = validate_audit_event(
            actor_id=actor_id, action=action, target_id=target_id, outcome="success",
            correlation_id="local", message=message,
        ).as_dict()
        event["organization_id"] = organization_id
        return event

    def has_active_org_admin_membership(self, user_id: str, organization_id: str) -> bool:
        return any(
            membership.user_id == user_id
            and membership.organization_id == organization_id
            and membership.role == "org_admin"
            and membership.active
            for membership in self.memberships.values()
        )

    def append_organization_admin_denial_audit(
        self,
        action: str,
        target_id: str,
        message: str,
        *,
        actor_id: str,
        outcome: str,
        correlation_id: str,
        organization_id: str,
    ) -> None:
        self.add_audit(
            action,
            target_id,
            message,
            actor_id=actor_id,
            outcome=outcome,
            correlation_id=correlation_id,
            organization_id=organization_id,
        )

    def _organization_for_target(self, target_id: str) -> str:
        if target_id in self.cases:
            return self.cases[target_id].organization_id
        if target_id in self.sessions:
            return self.sessions[target_id].organization_id
        if target_id in self.transcripts:
            return self.transcripts[target_id].organization_id
        if target_id in self.speaker_mappings:
            return self.speaker_mappings[target_id].organization_id
        if target_id in self.features:
            return self.features[target_id].organization_id
        if target_id in self.ml_results:
            return self.ml_results[target_id].organization_id
        if target_id in self.ai_reviews:
            return self.ai_reviews[target_id].organization_id
        if target_id in self.reports:
            return self.reports[target_id].organization_id
        if target_id in self.memberships:
            return self.memberships[target_id].organization_id
        if target_id in self.invitations:
            return self.invitations[target_id].organization_id
        if target_id in self.care_team_assignments:
            return self.care_team_assignments[target_id].organization_id
        if target_id in self.therapy_goals:
            return self.therapy_goals[target_id].organization_id
        if target_id in self.audio_files:
            return self.audio_files[target_id].organization_id
        if target_id in self.jobs:
            return self.jobs[target_id].organization_id
        if target_id in self.privacy_operations:
            return self.privacy_operations[target_id].organization_id
        return "pilot_org_001"

    def get_latest_speaker_mapping(self, transcript_id: str) -> SpeakerMapping | None:
        with self._lock:
            mappings = [mapping for mapping in self.speaker_mappings.values() if mapping.transcript_id == transcript_id]
            if not mappings:
                return None
            return self.clone(max(mappings, key=lambda mapping: (mapping.mapping_version, mapping.mapping_id)))

    def save_speaker_mapping_draft(
        self,
        mapping: SpeakerMapping,
        *,
        expected_mapping_version: int | None,
        actor_id: str,
    ) -> SpeakerMapping:
        with self._lock:
            transcript = self.transcripts[mapping.transcript_id]
            if transcript.version != mapping.source_transcript_version:
                raise TranscriptVersionConflictError(
                    f"Transcript {mapping.transcript_id} expected version {mapping.source_transcript_version}, "
                    f"found {transcript.version}."
                )
            latest = self.get_latest_speaker_mapping(mapping.transcript_id)
            if latest is None:
                if expected_mapping_version is not None:
                    raise SpeakerMappingVersionConflictError(
                        f"Speaker mapping {mapping.transcript_id} expected no current draft."
                    )
                saved = self.clone(mapping)
                saved.mapping_version = 1
            elif latest.status == "draft" and latest.source_transcript_version == mapping.source_transcript_version:
                if expected_mapping_version != latest.mapping_version:
                    raise SpeakerMappingVersionConflictError(
                        f"Speaker mapping {mapping.transcript_id} expected version {expected_mapping_version}, "
                        f"found {latest.mapping_version}."
                    )
                saved = self.clone(mapping)
                saved.mapping_id = latest.mapping_id
                saved.created_at = latest.created_at
                saved.mapping_version = latest.mapping_version + 1
            else:
                if (
                    latest.status == "confirmed"
                    and latest.applied_transcript_version == mapping.source_transcript_version
                ):
                    raise SpeakerMappingVersionConflictError(
                        f"Speaker mapping {mapping.transcript_id} is already confirmed for this transcript version."
                    )
                if expected_mapping_version is not None:
                    raise SpeakerMappingVersionConflictError(
                        f"Speaker mapping {mapping.transcript_id} expected no current draft."
                    )
                saved = self.clone(mapping)
                saved.mapping_version = latest.mapping_version + 1
            saved.organization_id = transcript.organization_id
            saved.transcript_id = transcript.transcript_id
            saved.status = MappingPersistedStatus.draft
            saved.applied_transcript_version = None
            saved.confirmed_by_user_id = None
            saved.confirmed_by_role = None
            saved.confirmed_at = None
            saved.updated_at = utc_now()
            self.speaker_mappings[saved.mapping_id] = saved
            MockRepository.add_audit(
                self,
                "speaker_mapping.draft_save",
                saved.mapping_id,
                "Speaker mapping draft saved.",
                actor_id=actor_id,
            )
            return self.clone(saved)

    def confirm_speaker_mapping(
        self,
        mapping: SpeakerMapping,
        transcript: Transcript,
        *,
        expected_transcript_version: int,
        expected_mapping_version: int,
        actor_id: str,
    ) -> SpeakerMapping:
        """Atomically confirm a current draft and apply its rebuilt transcript."""

        with self._lock:
            current = self.transcripts.get(transcript.transcript_id)
            if current is None or current.version != expected_transcript_version:
                found = current.version if current is not None else "missing"
                raise TranscriptVersionConflictError(
                    f"Transcript {transcript.transcript_id} expected version "
                    f"{expected_transcript_version}, found {found}."
                )
            latest = self.get_latest_speaker_mapping(transcript.transcript_id)
            if (
                latest is None
                or latest.mapping_id != mapping.mapping_id
                or latest.mapping_version != expected_mapping_version
                or latest.source_transcript_version != expected_transcript_version
                or latest.status != MappingPersistedStatus.draft
            ):
                raise SpeakerMappingVersionConflictError(
                    f"Speaker mapping {transcript.transcript_id} no longer matches the expected draft."
                )
            if (
                mapping.transcript_id != current.transcript_id
                or mapping.source_transcript_version != expected_transcript_version
                or mapping.mapping_version != latest.mapping_version
                or mapping.status != MappingPersistedStatus.confirmed
                or mapping.confirmed_by_user_id != actor_id
                or not mapping.confirmed_by_role
            ):
                raise SpeakerMappingVersionConflictError(
                    f"Speaker mapping {transcript.transcript_id} confirmation payload is inconsistent."
                )
            from app.services.speaker_mapping_service import build_confirmed_transcript, validate_mapping_confirmation

            validate_mapping_confirmation(self.clone(current), latest)
            saved_transcript = build_confirmed_transcript(self.clone(current), latest)
            immutable_mapping_fields_match = (
                mapping.mapping_id == latest.mapping_id
                and mapping.organization_id == latest.organization_id
                and mapping.transcript_id == latest.transcript_id
                and mapping.source_transcript_version == latest.source_transcript_version
                and mapping.mapping_version == latest.mapping_version
                and mapping.entries == latest.entries
            )
            submitted_transcript_matches = transcript.model_dump(exclude={"updated_at"}) == saved_transcript.model_dump(
                exclude={"updated_at"}
            )
            if not immutable_mapping_fields_match or not submitted_transcript_matches:
                raise SpeakerMappingVersionConflictError(
                    f"Speaker mapping {transcript.transcript_id} confirmation payload is inconsistent."
                )
            now = utc_now()
            saved_mapping = self.clone(latest)
            saved_mapping.status = MappingPersistedStatus.confirmed
            saved_mapping.applied_transcript_version = saved_transcript.version
            saved_mapping.confirmed_by_user_id = actor_id
            saved_mapping.confirmed_by_role = mapping.confirmed_by_role
            saved_mapping.confirmed_at = now
            saved_mapping.updated_at = now
            saved_mapping.mapping_version = latest.mapping_version + 1

            correlation_id = f"speaker_mapping_confirm_{uuid4().hex[:10]}"
            confirmation_event = validate_audit_event(
                actor_id=actor_id,
                action="speaker_mapping.confirm",
                target_id=latest.mapping_id,
                outcome="success",
                correlation_id=correlation_id,
                message=(
                    f"Speaker mapping {latest.mapping_id} confirmed for transcript "
                    f"{current.transcript_id} version {expected_transcript_version} to {saved_transcript.version}."
                ),
            ).as_dict()
            confirmation_event["organization_id"] = current.organization_id
            session = self.sessions[current.session_id]
            invalidation_required = self._downstream_outputs_need_invalidation(session)
            invalidation_event = None
            if invalidation_required:
                invalidation_event = validate_audit_event(
                    actor_id=actor_id,
                    action="workflow.invalidate_downstream",
                    target_id=current.transcript_id,
                    outcome="success",
                    correlation_id=correlation_id,
                    message="Derived workflow outputs marked stale after transcript change.",
                ).as_dict()
                invalidation_event["organization_id"] = current.organization_id

            state_before = self._speaker_mapping_confirmation_snapshot()
            try:
                saved_transcript.organization_id = current.organization_id
                saved_mapping.organization_id = current.organization_id
                invalidated = self._mark_downstream_outputs_stale(session)
                session.status = ReviewStatus.needs_review
                self.transcripts[current.transcript_id] = saved_transcript
                self.speaker_mappings[latest.mapping_id] = saved_mapping
                self._recompute_case_summaries(session.case_id)
                if invalidated:
                    assert invalidation_event is not None
                    self.audit_log.append(invalidation_event)
                self.audit_log.append(confirmation_event)
                return self.clone(saved_mapping)
            except Exception:
                self._restore_speaker_mapping_confirmation_snapshot(state_before)
                raise

    def _downstream_outputs_need_invalidation(self, session: TherapySession) -> bool:
        feature_set = self.features.get(session.feature_set_id or "")
        ml_result = self.ml_results.get(session.ml_result_id or "")
        ai_review = self.ai_reviews.get(session.ai_review_id or "")
        report = self.reports.get(session.report_id or "")
        return bool(
            (feature_set is not None and feature_set.review_status != ReviewStatus.stale)
            or (ml_result is not None and ml_result.is_current)
            or (ai_review is not None and ai_review.therapist_review_status != ReviewStatus.stale)
            or (
                report is not None
                and report.status not in {ReviewStatus.signed_off, ReviewStatus.stale}
            )
        )

    def _recompute_case_summaries(self, case_id: str) -> None:
        case = self.cases[case_id]
        sessions = [item for item in self.sessions.values() if item.case_id == case_id]
        if sessions:
            latest_session = max(
                sessions,
                key=lambda item: (item.session_date, item.created_at, item.session_id),
            )
            case.latest_session_date = latest_session.session_date
            case.latest_session_status = latest_session.status
        report_sessions = [
            item for item in sessions if item.report_id and item.report_id in self.reports
        ]
        if report_sessions:
            latest_report_session = max(
                report_sessions,
                key=lambda item: (
                    item.session_date,
                    item.created_at,
                    self.reports[item.report_id or ""].created_at,
                    item.session_id,
                ),
            )
            case.latest_report_status = self.reports[latest_report_session.report_id or ""].status

    def _speaker_mapping_confirmation_snapshot(self) -> dict:
        return {
            "cases": self.clone(self.cases),
            "sessions": self.clone(self.sessions),
            "transcripts": self.clone(self.transcripts),
            "speaker_mappings": self.clone(self.speaker_mappings),
            "features": self.clone(self.features),
            "ml_results": self.clone(self.ml_results),
            "ai_reviews": self.clone(self.ai_reviews),
            "reports": self.clone(self.reports),
            "audit_log": self.clone(self.audit_log),
        }

    def _restore_speaker_mapping_confirmation_snapshot(self, snapshot: dict) -> None:
        for name, value in snapshot.items():
            setattr(self, name, value)

    def create_case(self, payload: ChildCaseCreate, *, actor_id: str) -> ChildCase:
        case = ChildCase(case_id=new_id("case"), **payload.model_dump())
        if actor_id not in case.care_team_user_ids and actor_id != "system":
            case.care_team_user_ids = [*case.care_team_user_ids, actor_id]
        if case.primary_therapist_user_id is None and actor_id != "system":
            case.primary_therapist_user_id = actor_id
        if case.primary_therapist_user_id and case.primary_therapist_user_id not in case.care_team_user_ids:
            case.care_team_user_ids = [*case.care_team_user_ids, case.primary_therapist_user_id]
        self.cases[case.case_id] = case
        self.add_audit("case.create", case.case_id, "Case created.", actor_id=actor_id)
        return self.clone(case)

    def update_case(
        self,
        case_id: str,
        patch: ChildCaseUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> ChildCase:
        case = self.cases[case_id]
        if expected_version is not None and case.version != expected_version:
            raise CaseVersionConflictError(
                f"Case {case_id} expected version {expected_version}, found {case.version}."
            )
        for key, value in patch.model_dump(exclude_unset=True).items():
            setattr(case, key, value)
        case.version += 1
        self.add_audit("case.update", case_id, "Case updated.", actor_id=actor_id)
        return self.clone(case)

    def upsert_membership(
        self,
        organization_id: str,
        payload: OrganizationMembershipCreate,
        *,
        actor_id: str,
    ) -> OrganizationMembership:
        existing = next(
            (
                membership
                for membership in self.memberships.values()
                if membership.organization_id == organization_id and membership.user_id == payload.user_id
            ),
            None,
        )
        if existing:
            existing.display_name = payload.display_name
            existing.role = payload.role
            existing.active = payload.active
            membership = existing
        else:
            membership = OrganizationMembership(
                membership_id=new_id("mbr"),
                organization_id=organization_id,
                user_id=payload.user_id,
                display_name=payload.display_name,
                role=payload.role,
                active=payload.active,
            )
            self.memberships[membership.membership_id] = membership
        self.add_audit(
            "membership.upsert",
            membership.membership_id,
            "Organization membership updated.",
            actor_id=actor_id,
        )
        return self.clone(membership)

    def list_memberships(self, organization_id: str) -> list[OrganizationMembership]:
        memberships = [item for item in self.memberships.values() if item.organization_id == organization_id]
        memberships.sort(key=lambda item: item.created_at)
        return [self.clone(item) for item in memberships]

    def revoke_membership(self, organization_id: str, membership_id: str, *, actor_id: str) -> OrganizationMembership:
        membership = self.memberships[membership_id]
        if membership.organization_id != organization_id:
            raise KeyError(membership_id)
        membership.active = False
        for assignment in self.care_team_assignments.values():
            if assignment.organization_id == organization_id and assignment.user_id == membership.user_id:
                assignment.active = False
                assignment.is_primary = False
                if assignment.case_id in self.cases:
                    case = self.cases[assignment.case_id]
                    case.care_team_user_ids = [
                        user_id for user_id in case.care_team_user_ids if user_id != membership.user_id
                    ]
                    if case.primary_therapist_user_id == membership.user_id:
                        case.primary_therapist_user_id = None
        self.add_audit(
            "membership.revoke",
            membership.membership_id,
            "Organization membership revoked.",
            actor_id=actor_id,
        )
        return self.clone(membership)

    def create_invitation(
        self,
        organization_id: str,
        payload: OrganizationInvitationCreate,
        *,
        actor_id: str,
    ) -> OrganizationInvitation:
        now = utc_now()
        invitation = OrganizationInvitation(
            invitation_id=new_id("inv"),
            organization_id=organization_id,
            email=payload.email,
            display_name=payload.display_name,
            role=payload.role,
            invited_by=actor_id,
            expires_at=now + timedelta(days=INVITATION_EXPIRY_DAYS),
        )
        self.invitations[invitation.invitation_id] = invitation
        self.add_audit(
            "invitation.create",
            invitation.invitation_id,
            "Organization invitation created.",
            actor_id=actor_id,
        )
        return self.clone(invitation)

    def list_invitations(self, organization_id: str) -> list[OrganizationInvitation]:
        invitations = [item for item in self.invitations.values() if item.organization_id == organization_id]
        invitations.sort(key=lambda item: item.created_at)
        return [self.clone(item) for item in invitations]

    def accept_invitation(
        self,
        organization_id: str,
        invitation_id: str,
        payload: OrganizationInvitationAccept,
        *,
        actor_id: str,
    ) -> OrganizationInvitation:
        invitation = self.invitations[invitation_id]
        if invitation.organization_id != organization_id:
            raise KeyError(invitation_id)
        now = utc_now()
        if invitation.status == "accepted":
            raise ValueError("Invitation has already been accepted.")
        if invitation.status == "revoked":
            raise ValueError("Invitation has been revoked.")
        if invitation.expires_at <= now:
            invitation.status = "expired"
            self.add_audit(
                "invitation.accept",
                invitation.invitation_id,
                "Organization invitation acceptance failed.",
                actor_id=actor_id,
                outcome="denied",
            )
            raise ValueError("Expired invitations require a newly issued invitation.")
        for existing in self.invitations.values():
            if existing.invitation_id == invitation.invitation_id:
                continue
            if existing.email != invitation.email:
                continue
            if existing.accepted_user_id and existing.accepted_user_id != payload.user_id:
                self.add_audit(
                    "invitation.accept",
                    invitation.invitation_id,
                    "Organization invitation acceptance failed.",
                    actor_id=actor_id,
                    outcome="denied",
                )
                raise ValueError("Identity email is already bound to a different user.")
        invitation.status = "accepted"
        invitation.accepted_user_id = payload.user_id
        invitation.accepted_at = now
        self.upsert_membership(
            organization_id,
            OrganizationMembershipCreate(
                user_id=payload.user_id,
                display_name=invitation.display_name,
                role=invitation.role,
                active=True,
            ),
            actor_id=actor_id,
        )
        self.add_audit(
            "invitation.accept",
            invitation.invitation_id,
            "Organization invitation accepted.",
            actor_id=actor_id,
        )
        return self.clone(invitation)

    def audit_break_glass_case_access(self, organization_id: str, case_id: str, *, actor_id: str) -> None:
        if case_id not in self.cases or self.cases[case_id].organization_id != organization_id:
            raise KeyError(case_id)
        self.add_audit(
            "break_glass.case_access",
            case_id,
            "Scoped break-glass case access granted.",
            actor_id=actor_id,
        )

    def assign_care_team_member(
        self,
        case_id: str,
        payload: CareTeamAssignmentCreate,
        *,
        actor_id: str,
    ) -> CareTeamAssignment:
        case = self.cases[case_id]
        if payload.is_primary and (not payload.active or payload.role != "therapist"):
            raise ValueError("Primary therapist assignment must be an active therapist.")
        existing = next(
            (
                assignment
                for assignment in self.care_team_assignments.values()
                if assignment.organization_id == case.organization_id
                and assignment.case_id == case_id
                and assignment.user_id == payload.user_id
            ),
            None,
        )
        if existing:
            existing.role = payload.role
            existing.active = payload.active
            existing.is_primary = payload.is_primary
            assignment = existing
        else:
            assignment = CareTeamAssignment(
                assignment_id=new_id("team"),
                organization_id=case.organization_id,
                case_id=case_id,
                user_id=payload.user_id,
                role=payload.role,
                active=payload.active,
                is_primary=payload.is_primary,
            )
            self.care_team_assignments[assignment.assignment_id] = assignment
        if payload.active and payload.user_id not in case.care_team_user_ids:
            case.care_team_user_ids = [*case.care_team_user_ids, payload.user_id]
        if not payload.active and payload.user_id in case.care_team_user_ids:
            case.care_team_user_ids = [user_id for user_id in case.care_team_user_ids if user_id != payload.user_id]
        if payload.is_primary:
            for other in self.care_team_assignments.values():
                if other.case_id == case_id and other.assignment_id != assignment.assignment_id:
                    other.is_primary = False
            case.primary_therapist_user_id = payload.user_id
        elif case.primary_therapist_user_id == payload.user_id and (not payload.active or payload.role != "therapist"):
            case.primary_therapist_user_id = None
            assignment.is_primary = False
        self.add_audit(
            "care_team.assign",
            assignment.assignment_id,
            "Case care-team assignment updated.",
            actor_id=actor_id,
        )
        return self.clone(assignment)

    def list_care_team_assignments(self, case_id: str) -> list[CareTeamAssignment]:
        case = self.cases[case_id]
        assignments = [
            item.model_copy(update={"is_primary": item.user_id == case.primary_therapist_user_id})
            for item in self.care_team_assignments.values()
            if item.case_id == case_id and item.active
        ]
        assignments.sort(key=lambda item: (not item.is_primary, item.created_at))
        return [self.clone(item) for item in assignments]

    def create_session(self, case_id: str, payload: TherapySessionCreate, *, actor_id: str) -> TherapySession:
        with self._lock:
            case = self.cases[case_id]
            session = TherapySession(
                session_id=new_id("session"),
                case_id=case_id,
                organization_id=case.organization_id,
                **payload.model_dump(),
            )
            self.sessions[session.session_id] = session
            case.latest_session_date = session.session_date
            case.latest_session_status = session.status
            self.add_audit("session.create", session.session_id, "Session created.", actor_id=actor_id)
            return self.clone(session)

    def update_session(
        self,
        session_id: str,
        patch: TherapySessionUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> TherapySession:
        with self._lock:
            session = self.sessions[session_id]
            if expected_version is not None and session.version != expected_version:
                raise SessionVersionConflictError(
                    f"Session {session_id} expected version {expected_version}, found {session.version}."
                )
            for key, value in patch.model_dump(exclude_unset=True).items():
                setattr(session, key, value)
            session.version += 1
            self.add_audit("session.patch", session_id, "Session updated.", actor_id=actor_id)
            return self.clone(session)

    def create_transcript(
        self,
        transcript: Transcript,
        *,
        session_status: ReviewStatus,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Transcript:
        with self._lock:
            session = self.sessions[transcript.session_id]
            invalidated = self._mark_downstream_outputs_stale(session)
            transcript.organization_id = session.organization_id
            self.transcripts[transcript.transcript_id] = transcript
            session.transcript_id = transcript.transcript_id
            session.status = session_status
            self.add_audit(audit_action, transcript.transcript_id, audit_message, actor_id=actor_id)
            if invalidated:
                self.add_audit(
                    "workflow.invalidate_downstream",
                    transcript.transcript_id,
                    "Derived workflow outputs marked stale after transcript change.",
                    actor_id=actor_id,
                )
            return self.clone(transcript)

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
    ) -> Transcript:
        with self._lock:
            current = self.transcripts[transcript.transcript_id]
            if expected_version is not None and current.version != expected_version:
                raise TranscriptVersionConflictError(
                    f"Transcript {transcript.transcript_id} expected version {expected_version}, found {current.version}."
                )
            session = self.sessions[transcript.session_id]
            invalidated = self._mark_downstream_outputs_stale(session) if invalidate_downstream else False
            session.status = session_status
            transcript.organization_id = session.organization_id
            self.transcripts[transcript.transcript_id] = self.clone(transcript)
            self.add_audit(audit_action, transcript.transcript_id, audit_message, actor_id=actor_id)
            if invalidated:
                self.add_audit(
                    "workflow.invalidate_downstream",
                    transcript.transcript_id,
                    "Derived workflow outputs marked stale after transcript change.",
                    actor_id=actor_id,
                )
            return self.clone(transcript)

    def _mark_downstream_outputs_stale(self, session: TherapySession) -> bool:
        invalidated = False
        feature_set = self.features.get(session.feature_set_id or "")
        if feature_set is not None and feature_set.review_status != ReviewStatus.stale:
            feature_set.review_status = ReviewStatus.stale
            invalidated = True
        ml_result = self.ml_results.get(session.ml_result_id or "")
        if ml_result is not None and ml_result.is_current:
            ml_result.is_current = False
            invalidated = True
        ai_review = self.ai_reviews.get(session.ai_review_id or "")
        if ai_review is not None and ai_review.therapist_review_status != ReviewStatus.stale:
            ai_review.therapist_review_status = ReviewStatus.stale
            invalidated = True
        report = self.reports.get(session.report_id or "")
        if report is not None and report.status not in {ReviewStatus.signed_off, ReviewStatus.stale}:
            report.status = ReviewStatus.stale
            report.version += 1
            report.updated_at = utc_now()
            self.cases[session.case_id].latest_report_status = ReviewStatus.stale
            invalidated = True
        return invalidated

    def create_report(
        self,
        report: Report,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report:
        with self._lock:
            session = self.sessions[report.session_id]
            transcript = self.transcripts.get(report.transcript_id or "")
            expected_transcript_version = report.generated_from_versions.get("transcript_version")
            if report.transcript_id and (
                transcript is None
                or session.transcript_id != report.transcript_id
                or expected_transcript_version != str(transcript.version)
            ):
                raise ValueError("Transcript changed during report generation; discard the stale draft and retry.")
            if report.feature_result_id and (
                session.feature_set_id != report.feature_result_id
                or report.feature_result_id not in self.features
                or self.features[report.feature_result_id].review_status == ReviewStatus.stale
                or transcript is None
                or self.features[report.feature_result_id].transcript_version != transcript.version
            ):
                raise ValueError("Findings changed during report generation; discard the stale draft and retry.")
            report.organization_id = self.cases[report.case_id].organization_id
            self.reports[report.report_id] = report
            self.sessions[report.session_id].report_id = report.report_id
            self.cases[report.case_id].latest_report_status = report.status
            self.add_audit(audit_action, report.report_id, audit_message, actor_id=actor_id)
            return self.clone(report)

    def update_report(
        self,
        report: Report,
        *,
        expected_version: int | None,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report:
        current = self.reports[report.report_id]
        if expected_version is not None:
            if current is report:
                if report.version not in {expected_version, expected_version + 1}:
                    raise ReportVersionConflictError(f"Report {report.report_id} expected version {expected_version}.")
            elif current.version != expected_version:
                raise ReportVersionConflictError(
                    f"Report {report.report_id} expected version {expected_version}, found {current.version}."
                )
        report.organization_id = self.cases[report.case_id].organization_id
        self.reports[report.report_id] = report
        self.cases[report.case_id].latest_report_status = report.status
        self.add_audit(audit_action, report.report_id, audit_message, actor_id=actor_id)
        return self.clone(report)

    def create_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal:
        goal.organization_id = self.cases[goal.case_id].organization_id
        self.therapy_goals[goal.goal_id] = goal
        self.add_audit(audit_action, goal.goal_id, audit_message, actor_id=actor_id)
        return self.clone(goal)

    def update_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal:
        goal.organization_id = self.cases[goal.case_id].organization_id
        self.therapy_goals[goal.goal_id] = goal
        self.add_audit(audit_action, goal.goal_id, audit_message, actor_id=actor_id)
        return self.clone(goal)

    def create_privacy_operation(
        self,
        operation: PrivacyOperation,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> PrivacyOperation:
        operation.organization_id = self.cases[operation.case_id].organization_id
        self.privacy_operations[operation.privacy_operation_id] = operation
        self.add_audit(audit_action, operation.privacy_operation_id, audit_message, actor_id=actor_id)
        return self.clone(operation)

    def update_privacy_operation(
        self,
        operation: PrivacyOperation,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> PrivacyOperation:
        operation.organization_id = self.cases[operation.case_id].organization_id
        self.privacy_operations[operation.privacy_operation_id] = operation
        self.add_audit(audit_action, operation.privacy_operation_id, audit_message, actor_id=actor_id)
        return self.clone(operation)

    def create_feature_set(
        self,
        feature_set: FeatureSet,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> FeatureSet:
        with self._lock:
            features_before = self.clone(self.features)
            sessions_before = self.clone(self.sessions)
            audit_before = self.clone(self.audit_log)
            try:
                session = self.sessions[feature_set.session_id]
                transcript = self.transcripts.get(feature_set.transcript_id)
                if (
                    transcript is None
                    or session.transcript_id != feature_set.transcript_id
                    or transcript.version != feature_set.transcript_version
                ):
                    raise ValueError("Transcript changed during feature extraction; discard the stale result and retry.")
                saved = self.clone(feature_set)
                saved.organization_id = session.organization_id
                self.features[saved.feature_set_id] = saved
                session.feature_set_id = saved.feature_set_id
                session.ml_result_id = None
                self.add_audit(audit_action, saved.feature_set_id, audit_message, actor_id=actor_id)
                return self.clone(saved)
            except JsonRepositoryDurabilityError:
                raise
            except Exception:
                self.features = features_before
                self.sessions = sessions_before
                self.audit_log = audit_before
                raise

    def create_ai_review(
        self,
        review: AiReview,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> AiReview:
        with self._lock:
            session = self.sessions[review.session_id]
            transcript = self.transcripts.get(session.transcript_id or "")
            feature_set = self.features.get(review.feature_set_id or "")
            if transcript is None or transcript.version != review.input_transcript_version:
                raise ValueError("Transcript changed during AI-assisted review generation; discard the stale result and retry.")
            if review.feature_set_id and (
                session.feature_set_id != review.feature_set_id
                or feature_set is None
                or feature_set.review_status == ReviewStatus.stale
                or feature_set.transcript_version != transcript.version
            ):
                raise ValueError("Findings changed during AI-assisted review generation; discard the stale result and retry.")
            review.organization_id = session.organization_id
            self.ai_reviews[review.ai_review_id] = review
            self.sessions[review.session_id].ai_review_id = review.ai_review_id
            self.cases[self.sessions[review.session_id].case_id].review_priority = review.review_priority
            self.add_audit(audit_action, review.ai_review_id, audit_message, actor_id=actor_id)
            return self.clone(review)

    def update_ai_review(
        self,
        review: AiReview,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> AiReview:
        review.organization_id = self.sessions[review.session_id].organization_id
        self.ai_reviews[review.ai_review_id] = review
        self.add_audit(audit_action, review.ai_review_id, audit_message, actor_id=actor_id)
        return self.clone(review)

    def create_ml_result(
        self,
        result: MLResult,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> MLResult:
        with self._lock:
            session = self.sessions[result.session_id]
            transcript = self.transcripts.get(result.transcript_id)
            feature_set = self.features.get(result.feature_result_id)
            if (
                transcript is None
                or session.transcript_id != result.transcript_id
                or session.feature_set_id != result.feature_result_id
                or feature_set is None
                or feature_set.review_status == ReviewStatus.stale
                or feature_set.transcript_id != transcript.transcript_id
                or feature_set.transcript_version != transcript.version
            ):
                raise ValueError("Transcript or findings changed during ML review generation; discard the stale result and retry.")
            result.organization_id = session.organization_id
            self.ml_results[result.result_id] = result
            self.sessions[result.session_id].ml_result_id = result.result_id
            self.add_audit(audit_action, result.result_id, audit_message, actor_id=actor_id)
            return self.clone(result)

    def update_ml_result(
        self,
        result: MLResult,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> MLResult:
        result.organization_id = self.sessions[result.session_id].organization_id
        self.ml_results[result.result_id] = result
        self.add_audit(audit_action, result.result_id, audit_message, actor_id=actor_id)
        return self.clone(result)

    def snapshot(self) -> dict:
        return {
            "cases": {key: value.model_dump(mode="json") for key, value in self.cases.items()},
            "sessions": {key: value.model_dump(mode="json") for key, value in self.sessions.items()},
            "transcripts": {key: value.model_dump(mode="json") for key, value in self.transcripts.items()},
            "speaker_mappings": {
                key: value.model_dump(mode="json") for key, value in self.speaker_mappings.items()
            },
            "features": {key: value.model_dump(mode="json") for key, value in self.features.items()},
            "ml_results": {key: value.model_dump(mode="json") for key, value in self.ml_results.items()},
            "ai_reviews": {key: value.model_dump(mode="json") for key, value in self.ai_reviews.items()},
            "reports": {key: value.model_dump(mode="json") for key, value in self.reports.items()},
            "memberships": {key: value.model_dump(mode="json") for key, value in self.memberships.items()},
            "invitations": {key: value.model_dump(mode="json") for key, value in self.invitations.items()},
            "care_team_assignments": {
                key: value.model_dump(mode="json") for key, value in self.care_team_assignments.items()
            },
            "therapy_goals": {key: value.model_dump(mode="json") for key, value in self.therapy_goals.items()},
            "audio_files": {key: value.model_dump(mode="json") for key, value in self.audio_files.items()},
            "jobs": {key: value.model_dump(mode="json") for key, value in self.jobs.items()},
            "privacy_operations": {key: value.model_dump(mode="json") for key, value in self.privacy_operations.items()},
            "organization_settings": self.organization_settings,
            "audit_log": self.audit_log,
        }


class JsonFileRepository(MockRepository):
    """Durable local demo repository stored as JSON outside browser storage."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._durable_depth = 0
        super().__init__()
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.save()
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.cases = {key: ChildCase.model_validate(value) for key, value in data.get("cases", {}).items()}
        self.sessions = {key: TherapySession.model_validate(value) for key, value in data.get("sessions", {}).items()}
        self.transcripts = {key: Transcript.model_validate(value) for key, value in data.get("transcripts", {}).items()}
        self.speaker_mappings = {
            key: SpeakerMapping.model_validate(value) for key, value in data.get("speaker_mappings", {}).items()
        }
        self.features = {key: FeatureSet.model_validate(value) for key, value in data.get("features", {}).items()}
        self.ml_results = {key: MLResult.model_validate(value) for key, value in data.get("ml_results", {}).items()}
        self.ai_reviews = {key: AiReview.model_validate(value) for key, value in data.get("ai_reviews", {}).items()}
        self.reports = {key: Report.model_validate(value) for key, value in data.get("reports", {}).items()}
        self.memberships = {
            key: OrganizationMembership.model_validate(value)
            for key, value in data.get("memberships", {}).items()
        }
        self.invitations = {
            key: OrganizationInvitation.model_validate(value)
            for key, value in data.get("invitations", {}).items()
        }
        self.care_team_assignments = {
            key: CareTeamAssignment.model_validate(value)
            for key, value in data.get("care_team_assignments", {}).items()
        }
        self.therapy_goals = {key: TherapyGoal.model_validate(value) for key, value in data.get("therapy_goals", {}).items()}
        self.audio_files = {key: AudioFileMetadata.model_validate(value) for key, value in data.get("audio_files", {}).items()}
        self.jobs = {key: ProcessingJob.model_validate(value) for key, value in data.get("jobs", {}).items()}
        self.privacy_operations = {key: PrivacyOperation.model_validate(value) for key, value in data.get("privacy_operations", {}).items()}
        self.organization_settings = {
            key: dict(value) for key, value in data.get("organization_settings", {}).items()
        }
        self.organization_settings.setdefault("pilot_org_001", {"ai_review_enabled": True})
        self.audit_log = list(data.get("audit_log", []))

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self.path.with_name(f".{self.path.name}.{uuid4().hex}.tmp")
            temporary_fd: int | None = None
            try:
                payload = json.dumps(self.snapshot(), indent=2)
                temporary_fd = os.open(
                    temporary_path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
                os.fchmod(temporary_fd, 0o600)
                file = os.fdopen(temporary_fd, "w", encoding="utf-8")
                temporary_fd = None
                with file:
                    file.write(payload)
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(temporary_path, self.path)
            except Exception:
                if temporary_fd is not None:
                    os.close(temporary_fd)
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
                raise

            directory_fd: int | None = None
            try:
                directory_fd = os.open(self.path.parent, os.O_RDONLY)
                os.fsync(directory_fd)
                os.close(directory_fd)
                directory_fd = None
            except Exception as exc:
                if directory_fd is not None:
                    try:
                        os.close(directory_fd)
                    except OSError:
                        pass
                raise JsonRepositoryDurabilityError(
                    "JSON snapshot was committed, but directory durability is uncertain."
                ) from exc

    def _durable_mutation(self, state_names, operation, *, commit_exceptions=()):
        with self._lock:
            outermost = self._durable_depth == 0
            before = (
                {name: self.clone(getattr(self, name)) for name in state_names}
                if outermost
                else None
            )
            self._durable_depth += 1
            try:
                result = operation()
                if outermost:
                    self.save()
                return result
            except JsonRepositoryDurabilityError:
                raise
            except Exception as exc:
                if outermost and isinstance(exc, commit_exceptions):
                    try:
                        self.save()
                    except Exception:
                        assert before is not None
                        for name, value in before.items():
                            setattr(self, name, value)
                        raise
                    raise
                if before is not None:
                    for name, value in before.items():
                        setattr(self, name, value)
                raise
            finally:
                self._durable_depth -= 1

    def create_case(self, payload, *, actor_id):
        return self._durable_mutation(
            ("cases", "audit_log"),
            lambda: super(JsonFileRepository, self).create_case(payload, actor_id=actor_id),
        )

    def update_case(self, case_id, patch, *, expected_version, actor_id):
        return self._durable_mutation(
            ("cases", "audit_log"),
            lambda: super(JsonFileRepository, self).update_case(
                case_id, patch, expected_version=expected_version, actor_id=actor_id
            ),
        )

    def set_ai_review_enabled(self, organization_id, enabled):
        return self._durable_mutation(
            ("organization_settings",),
            lambda: super(JsonFileRepository, self).set_ai_review_enabled(
                organization_id, enabled
            ),
        )

    def upsert_membership(self, organization_id, payload, *, actor_id):
        return self._durable_mutation(
            ("memberships", "audit_log"),
            lambda: super(JsonFileRepository, self).upsert_membership(
                organization_id, payload, actor_id=actor_id
            ),
        )

    def revoke_membership(self, organization_id, membership_id, *, actor_id):
        return self._durable_mutation(
            ("cases", "memberships", "care_team_assignments", "audit_log"),
            lambda: super(JsonFileRepository, self).revoke_membership(
                organization_id, membership_id, actor_id=actor_id
            ),
        )

    def create_invitation(self, organization_id, payload, *, actor_id):
        return self._durable_mutation(
            ("invitations", "audit_log"),
            lambda: super(JsonFileRepository, self).create_invitation(
                organization_id, payload, actor_id=actor_id
            ),
        )

    def accept_invitation(self, organization_id, invitation_id, payload, *, actor_id):
        return self._durable_mutation(
            ("invitations", "memberships", "audit_log"),
            lambda: super(JsonFileRepository, self).accept_invitation(
                organization_id, invitation_id, payload, actor_id=actor_id
            ),
            commit_exceptions=(ValueError,),
        )

    def assign_care_team_member(self, case_id, payload, *, actor_id):
        return self._durable_mutation(
            ("cases", "care_team_assignments", "audit_log"),
            lambda: super(JsonFileRepository, self).assign_care_team_member(
                case_id, payload, actor_id=actor_id
            ),
        )

    def create_session(self, case_id, payload, *, actor_id):
        return self._durable_mutation(
            ("cases", "sessions", "audit_log"),
            lambda: super(JsonFileRepository, self).create_session(case_id, payload, actor_id=actor_id),
        )

    def update_session(self, session_id, patch, *, expected_version, actor_id):
        return self._durable_mutation(
            ("sessions", "audit_log"),
            lambda: super(JsonFileRepository, self).update_session(
                session_id, patch, expected_version=expected_version, actor_id=actor_id
            ),
        )

    def create_transcript(self, transcript, **kwargs):
        return self._durable_mutation(
            ("cases", "sessions", "transcripts", "features", "ml_results", "ai_reviews", "reports", "audit_log"),
            lambda: super(JsonFileRepository, self).create_transcript(transcript, **kwargs),
        )

    def update_transcript(self, transcript, **kwargs):
        return self._durable_mutation(
            ("cases", "sessions", "transcripts", "features", "ml_results", "ai_reviews", "reports", "audit_log"),
            lambda: super(JsonFileRepository, self).update_transcript(transcript, **kwargs),
        )

    def create_feature_set(self, feature_set, **kwargs):
        return self._durable_mutation(
            ("sessions", "features", "audit_log"),
            lambda: super(JsonFileRepository, self).create_feature_set(feature_set, **kwargs),
        )

    def create_ai_review(self, review, **kwargs):
        return self._durable_mutation(
            ("sessions", "ai_reviews", "audit_log"),
            lambda: super(JsonFileRepository, self).create_ai_review(review, **kwargs),
        )

    def update_ai_review(self, review, **kwargs):
        return self._durable_mutation(
            ("ai_reviews", "audit_log"),
            lambda: super(JsonFileRepository, self).update_ai_review(review, **kwargs),
        )

    def create_ml_result(self, result, **kwargs):
        return self._durable_mutation(
            ("sessions", "ml_results", "audit_log"),
            lambda: super(JsonFileRepository, self).create_ml_result(result, **kwargs),
        )

    def update_ml_result(self, result, **kwargs):
        return self._durable_mutation(
            ("ml_results", "audit_log"),
            lambda: super(JsonFileRepository, self).update_ml_result(result, **kwargs),
        )

    def create_report(self, report, **kwargs):
        return self._durable_mutation(
            ("cases", "sessions", "reports", "audit_log"),
            lambda: super(JsonFileRepository, self).create_report(report, **kwargs),
        )

    def update_report(self, report, **kwargs):
        return self._durable_mutation(
            ("cases", "reports", "audit_log"),
            lambda: super(JsonFileRepository, self).update_report(report, **kwargs),
        )

    def create_therapy_goal(self, goal, **kwargs):
        return self._durable_mutation(
            ("therapy_goals", "audit_log"),
            lambda: super(JsonFileRepository, self).create_therapy_goal(goal, **kwargs),
        )

    def update_therapy_goal(self, goal, **kwargs):
        return self._durable_mutation(
            ("therapy_goals", "audit_log"),
            lambda: super(JsonFileRepository, self).update_therapy_goal(goal, **kwargs),
        )

    def create_privacy_operation(self, operation, **kwargs):
        return self._durable_mutation(
            ("privacy_operations", "audit_log"),
            lambda: super(JsonFileRepository, self).create_privacy_operation(operation, **kwargs),
        )

    def update_privacy_operation(self, operation, **kwargs):
        return self._durable_mutation(
            ("privacy_operations", "audit_log"),
            lambda: super(JsonFileRepository, self).update_privacy_operation(operation, **kwargs),
        )

    def create_audio_upload(self, audio_file, job, *, actor_id):
        return self._durable_mutation(
            ("audio_files", "jobs", "audit_log"),
            lambda: super(JsonFileRepository, self).create_audio_upload(
                audio_file, job, actor_id=actor_id
            ),
        )

    def update_audio_file_metadata(
        self, audio_file, *, actor_id, expected_version, expected_upload_status,
        audit_action=None, audit_message=None
    ):
        return self._durable_mutation(
            ("audio_files", "audit_log"),
            lambda: super(JsonFileRepository, self).update_audio_file_metadata(
                audio_file,
                actor_id=actor_id,
                expected_version=expected_version,
                expected_upload_status=expected_upload_status,
                audit_action=audit_action,
                audit_message=audit_message,
            ),
        )

    def create_processing_job(self, job, *, actor_id, audit_action, audit_message):
        return self._durable_mutation(
            ("jobs", "audit_log"),
            lambda: super(JsonFileRepository, self).create_processing_job(
                job,
                actor_id=actor_id,
                audit_action=audit_action,
                audit_message=audit_message,
            ),
        )

    def update_processing_job(
        self, job, *, actor_id, expected_version, expected_status, audit_action, audit_message
    ):
        return self._durable_mutation(
            ("jobs", "audit_log"),
            lambda: super(JsonFileRepository, self).update_processing_job(
                job,
                actor_id=actor_id,
                expected_version=expected_version,
                expected_status=expected_status,
                audit_action=audit_action,
                audit_message=audit_message,
            ),
        )

    def complete_processing_job(
        self, job, transcript, *, actor_id, expected_version, expected_status,
        audit_action, audit_message
    ):
        return self._durable_mutation(
            ("cases", "jobs", "transcripts", "sessions", "features", "ml_results", "ai_reviews", "reports", "audit_log"),
            lambda: super(JsonFileRepository, self).complete_processing_job(
                job,
                transcript,
                actor_id=actor_id,
                expected_version=expected_version,
                expected_status=expected_status,
                audit_action=audit_action,
                audit_message=audit_message,
            ),
        )

    def withdraw_case_consent(self, **kwargs):
        return self._durable_mutation(
            (
                "cases", "sessions", "therapy_goals", "audio_files", "transcripts",
                "features", "ml_results", "ai_reviews", "reports", "jobs", "audit_log",
            ),
            lambda: super(JsonFileRepository, self).withdraw_case_consent(**kwargs),
        )

    def record_audio_deletion_result(self, audio_file_id, **kwargs):
        return self._durable_mutation(
            ("audio_files", "audit_log"),
            lambda: super(JsonFileRepository, self).record_audio_deletion_result(audio_file_id, **kwargs),
        )

    def acknowledge_session_cues(self, session_id, **kwargs):
        return self._durable_mutation(
            ("sessions", "audit_log"),
            lambda: super(JsonFileRepository, self).acknowledge_session_cues(session_id, **kwargs),
        )

    def add_audit(
        self,
        action: str,
        target_id: str,
        message: str,
        *,
        actor_id: str = "system",
        outcome: str = "success",
        correlation_id: str = "local",
        organization_id: str | None = None,
    ) -> None:
        with self._lock:
            if self._durable_depth:
                MockRepository.add_audit(
                    self,
                    action,
                    target_id,
                    message,
                    actor_id=actor_id,
                    outcome=outcome,
                    correlation_id=correlation_id,
                    organization_id=organization_id,
                )
                return
            audit_before = self.clone(self.audit_log)
            try:
                super().add_audit(
                    action,
                    target_id,
                    message,
                    actor_id=actor_id,
                    outcome=outcome,
                    correlation_id=correlation_id,
                    organization_id=organization_id,
                )
                self.save()
            except JsonRepositoryDurabilityError:
                raise
            except Exception:
                self.audit_log = audit_before
                raise

    def save_speaker_mapping_draft(
        self,
        mapping: SpeakerMapping,
        *,
        expected_mapping_version: int | None,
        actor_id: str,
    ) -> SpeakerMapping:
        with self._lock:
            mappings_before = self.clone(self.speaker_mappings)
            audit_before = self.clone(self.audit_log)
            try:
                saved = super().save_speaker_mapping_draft(
                    mapping,
                    expected_mapping_version=expected_mapping_version,
                    actor_id=actor_id,
                )
                self.save()
                return saved
            except JsonRepositoryDurabilityError:
                raise
            except Exception:
                self.speaker_mappings = mappings_before
                self.audit_log = audit_before
                raise

    def confirm_speaker_mapping(
        self,
        mapping: SpeakerMapping,
        transcript: Transcript,
        *,
        expected_transcript_version: int,
        expected_mapping_version: int,
        actor_id: str,
    ) -> SpeakerMapping:
        with self._lock:
            state_before = self._speaker_mapping_confirmation_snapshot()
            try:
                saved = super().confirm_speaker_mapping(
                    mapping,
                    transcript,
                    expected_transcript_version=expected_transcript_version,
                    expected_mapping_version=expected_mapping_version,
                    actor_id=actor_id,
                )
                self.save()
                return saved
            except JsonRepositoryDurabilityError:
                raise
            except Exception:
                self._restore_speaker_mapping_confirmation_snapshot(state_before)
                raise
