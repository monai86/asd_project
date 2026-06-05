"""Deterministic mock repository for the therapist clinical workspace."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from .models import (
    ALLOWED_AUDIO_FILE_TYPES,
    ALLOWED_TRANSCRIPT_FILE_TYPES,
    AnonymizationStatus,
    AudioFile,
    AIScreeningOutput,
    AuditLog,
    ChildCase,
    ClinicalSpeechArtifact,
    ClinicalSignoff,
    ConsentRecord,
    ConsentStatus,
    ExternalClinicalStatus,
    ExtractedFeatures,
    FeatureReviewDisposition,
    FileObject,
    JobStatus,
    MAX_AUDIO_FILE_SIZE_BYTES,
    ModelRun,
    MOCK_MODE,
    ProcessingStatus,
    ProcessingJob,
    Report,
    ReviewStatus,
    SAFETY_DISCLAIMER,
    SignoffTargetType,
    Session,
    SessionType,
    Sex,
    TherapyGoal,
    TherapistNote,
    Transcript,
    TranscriptLine,
    User,
)
from .repository_interface import ClinicalRepository
from src.clinical_workflow.paths import validate_uploads_path
from src.clinical_speech.chat_exporter import ChatExportMetadata, build_reviewed_chat_export, parse_chat_to_lines
from src.clinical_speech.feature_extractor import extract_clinical_features
from src.clinical_speech.models import NormalizedTranscriptLine, speaker_role_for_code
from src.feature_schema import FEATURE_DOCS, FEATURES, OPTIONAL_INDICATORS
from packages.ml.predict import predict_reference_cohort_similarity
from src.reference_engine import ReferenceComparisonResult, ReferenceEngine
from src.therapist_report import METRIC_DIRECTIONS, REPORT_METRICS
from src.transcript_reviewer import review_cha_text


NowProvider = Callable[[], datetime]


class TranscriptLineVersionConflict(ValueError):
    def __init__(self, line_id: str, expected_version: int, actual_version: int) -> None:
        super().__init__(f"Transcript line {line_id} has version {actual_version}; expected {expected_version}.")
        self.line_id = line_id
        self.expected_version = expected_version
        self.actual_version = actual_version


class MockClinicalRepository(ClinicalRepository):
    """In-memory clinical workflow store with explicit ownership filtering."""

    def __init__(
        self,
        now_provider: NowProvider | None = None,
        reference_engine: ReferenceEngine | None = None,
    ) -> None:
        self.mock_mode = MOCK_MODE
        self._now = now_provider or (lambda: datetime.now(timezone.utc))
        self.reference_engine = reference_engine
        self.users: dict[str, User] = {}
        self.cases: dict[str, ChildCase] = {}
        self.sessions: dict[str, Session] = {}
        self.audio_files: dict[str, AudioFile] = {}
        self.consent_records: dict[str, ConsentRecord] = {}
        self.file_objects: dict[str, FileObject] = {}
        self.processing_jobs: dict[str, ProcessingJob] = {}
        self.clinical_speech_artifacts: dict[str, ClinicalSpeechArtifact] = {}
        self.transcripts: dict[str, Transcript] = {}
        self.transcript_lines: dict[str, TranscriptLine] = {}
        self.extracted_features: dict[str, ExtractedFeatures] = {}
        self.feature_review_dispositions: dict[str, FeatureReviewDisposition] = {}
        self.ai_screening_outputs: dict[str, AIScreeningOutput] = {}
        self.clinical_signoffs: dict[str, ClinicalSignoff] = {}
        self.model_runs: dict[str, ModelRun] = {}
        self.therapy_goals: dict[str, TherapyGoal] = {}
        self.therapist_notes: dict[str, TherapistNote] = {}
        self.reports: dict[str, Report] = {}
        self.audit_logs: list[AuditLog] = []
        self._password_by_email: dict[str, str] = {}
        self._case_sequence = 0
        self._session_sequence = 0
        self._audio_file_sequence = 0
        self._consent_sequence = 0
        self._file_object_sequence = 0
        self._processing_job_sequence = 0
        self._clinical_speech_artifact_sequence = 0
        self._transcript_sequence = 0
        self._feature_sequence = 0
        self._feature_review_disposition_sequence = 0
        self._ai_output_sequence = 0
        self._signoff_sequence = 0
        self._model_run_sequence = 0
        self._goal_sequence = 0
        self._note_sequence = 0
        self._report_sequence = 0
        self._audit_sequence = 0
        self._seed()

    @property
    def safety_disclaimer(self) -> str:
        return SAFETY_DISCLAIMER

    def sample_credentials(self) -> list[dict[str, str]]:
        return [
            {
                "role": user.role,
                "email": user.email,
                "password": self._password_by_email[user.email.lower()],
            }
            for user in sorted(self.users.values(), key=lambda item: item.user_id)
        ]

    def authenticate(self, email: str, password: str) -> User | None:
        normalized = email.strip().lower()
        user = next(
            (item for item in self.users.values() if item.email.lower() == normalized),
            None,
        )
        if user is None or self._password_by_email.get(normalized) != password:
            return None

        user.last_login = self._now()
        self._audit(
            "login",
            actor_user_id=user.user_id,
            target_type="user",
            target_id=user.user_id,
            message=f"Mock login for {user.email}",
        )
        return replace(user)

    def get_user(self, user_id: str) -> User | None:
        user = self.users.get(user_id)
        return replace(user) if user else None

    def list_cases_for_user(self, user: User) -> list[ChildCase]:
        rows = self.cases.values()
        if user.role != "admin":
            rows = [case for case in rows if case.owner_user_id == user.user_id]
        return [replace(case) for case in sorted(rows, key=lambda item: item.created_at, reverse=True)]

    def get_case_for_user(self, case_id: str, user: User) -> ChildCase | None:
        case = self.cases.get(case_id)
        if case is None:
            return None
        if user.role == "admin" or case.owner_user_id == user.user_id:
            return replace(case)
        return None

    def list_sessions_for_user(self, user: User) -> list[Session]:
        rows = self.sessions.values()
        if user.role != "admin":
            rows = [session for session in rows if session.owner_user_id == user.user_id]
        return [replace(session) for session in sorted(rows, key=lambda item: item.session_date, reverse=True)]

    def list_sessions_for_case_for_user(self, case_id: str, user: User) -> list[Session]:
        if self.get_case_for_user(case_id, user) is None:
            return []
        rows = [session for session in self.sessions.values() if session.case_id == case_id]
        return [replace(session) for session in sorted(rows, key=lambda item: item.session_date, reverse=True)]

    def list_notes_for_case_for_user(self, case_id: str, user: User) -> list[TherapistNote]:
        if self.get_case_for_user(case_id, user) is None:
            return []
        rows = [note for note in self.therapist_notes.values() if note.case_id == case_id]
        return [replace(note) for note in sorted(rows, key=lambda item: item.created_at, reverse=True)]

    def list_audio_files_for_user(self, user: User) -> list[AudioFile]:
        rows = self.audio_files.values()
        if user.role != "admin":
            rows = [audio_file for audio_file in rows if audio_file.owner_user_id == user.user_id]
        return [replace(audio_file) for audio_file in sorted(rows, key=lambda item: item.upload_time, reverse=True)]

    def list_audio_files_for_case_for_user(self, case_id: str, user: User) -> list[AudioFile]:
        if self.get_case_for_user(case_id, user) is None:
            return []
        rows = [audio_file for audio_file in self.audio_files.values() if audio_file.case_id == case_id]
        return [replace(audio_file) for audio_file in sorted(rows, key=lambda item: item.upload_time, reverse=True)]

    def list_audio_files_for_session_for_user(self, session_id: str, user: User) -> list[AudioFile]:
        session = self.sessions.get(session_id)
        if session is None or self.get_case_for_user(session.case_id, user) is None:
            return []
        rows = [audio_file for audio_file in self.audio_files.values() if audio_file.session_id == session_id]
        return [replace(audio_file) for audio_file in sorted(rows, key=lambda item: item.upload_time, reverse=True)]

    def list_consent_records_for_case_for_user(self, case_id: str, user: User) -> list[ConsentRecord]:
        if self.get_case_for_user(case_id, user) is None:
            return []
        rows = [record for record in self.consent_records.values() if record.case_id == case_id]
        return [replace(record) for record in sorted(rows, key=lambda item: item.created_at, reverse=True)]

    def has_active_audio_consent(self, case_id: str, now: datetime | None = None) -> bool:
        checked_at = now or self._now()
        records = sorted(
            [record for record in self.consent_records.values() if record.case_id == case_id],
            key=lambda item: item.created_at,
            reverse=True,
        )
        return any(
            record.audio_permission
            and record.withdrawn_at is None
            and (record.expires_at is None or record.expires_at > checked_at)
            for record in records
        )

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
        case = self.cases.get(case_id)
        if case is None:
            raise ValueError(f"Unknown case_id: {case_id}")
        if user.role != "admin" and case.owner_user_id != user.user_id:
            raise PermissionError("Clinical users can only record consent for owned cases.")

        now = self._now()
        self._consent_sequence += 1
        record = ConsentRecord(
            consent_id=f"CONSENT-{self._consent_sequence:03d}",
            case_id=case_id,
            owner_user_id=case.owner_user_id,
            recorded_by_user_id=user.user_id,
            consent_type=consent_type,
            guardian_status=guardian_status,  # type: ignore[arg-type]
            audio_permission=bool(audio_permission),
            transcript_permission=bool(transcript_permission),
            notes=notes.strip(),
            expires_at=expires_at,
            created_at=now,
        )
        self.consent_records[record.consent_id] = record
        self.cases[case_id] = replace(
            case,
            consent_status="granted" if audio_permission and transcript_permission else "pending",
            updated_at=now,
        )
        self._audit(
            "consent_recorded",
            actor_user_id=user.user_id,
            target_type="consent_record",
            target_id=record.consent_id,
            message=f"Recorded consent permissions for {case_id}",
        )
        return replace(record)

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
        validate_uploads_path(Path(original_filename))
        if not self.has_active_audio_consent(case_id):
            raise PermissionError("Active guardian consent is required before secure audio upload.")

        audio_file = self.create_audio_file_metadata(
            case_id=case_id,
            session_id=session_id,
            user=user,
            original_filename=original_filename,
            file_size=file_size,
            processing_status="pending",
        )
        now = self._now()
        self._file_object_sequence += 1
        file_object = FileObject(
            file_object_id=f"FILEOBJ-{self._file_object_sequence:03d}",
            audio_file_id=audio_file.audio_file_id,
            case_id=case_id,
            session_id=session_id,
            owner_user_id=audio_file.owner_user_id,
            storage_key=(
                f"private/{audio_file.owner_user_id}/{case_id}/"
                f"{session_id}/{audio_file.stored_filename}"
            ),
            checksum_sha256=checksum_sha256,
            mime_type=mime_type,
            encryption_status="required",
            retention_delete_after=now + timedelta(days=retention_days),
            created_at=now,
        )
        self.file_objects[file_object.file_object_id] = file_object
        self.audio_files[audio_file.audio_file_id] = replace(
            self.audio_files[audio_file.audio_file_id],
            storage_mode="secure_private",
            file_object_id=file_object.file_object_id,
        )
        self._audit(
            "secure_upload_intent_created",
            actor_user_id=user.user_id,
            target_type="file_object",
            target_id=file_object.file_object_id,
            message=f"Created private signed-upload intent for {audio_file.audio_file_id}",
        )
        client_file_object = file_object.to_dict()
        client_file_object.pop("storage_key", None)
        return {
            "audio_file": self.audio_files[audio_file.audio_file_id].to_dict(),
            "file_object": client_file_object,
            "upload": {
                "method": "PUT",
                "url": f"https://private-storage.local/upload/{file_object.file_object_id}",
                "signed_upload_url": f"https://private-storage.local/upload/{file_object.file_object_id}",
                "expires_in_seconds": 900,
                "storage_provider": storage_provider,
                "file_object_id": file_object.file_object_id,
                "headers": {
                    "content-type": mime_type,
                    "x-amz-server-side-encryption": "AES256",
                    "x-upload-retention-days": str(retention_days),
                },
            },
        }

    def create_processing_job(
        self,
        session_id: str,
        user: User,
        job_type: str = "audio_to_chat",
        *,
        engine: str = "local_whisper",
        operation: str | None = None,
        operation_config: dict | None = None,
        dependency_check: dict | None = None,
        source_revision: str | None = None,
    ) -> ProcessingJob:
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session_id: {session_id}")
        if user.role != "admin" and session.owner_user_id != user.user_id:
            raise PermissionError("Clinical users can only process owned sessions.")
        if not session.audio_file_id:
            raise ValueError("Audio file metadata is required before creating a processing job.")
        if not self.has_active_audio_consent(session.case_id):
            raise PermissionError("Active guardian consent is required before audio processing.")

        now = self._now()
        self._processing_job_sequence += 1
        job = ProcessingJob(
            job_id=f"JOB-{self._processing_job_sequence:04d}",
            session_id=session_id,
            case_id=session.case_id,
            owner_user_id=session.owner_user_id,
            audio_file_id=session.audio_file_id,
            job_type=job_type,
            engine=engine,
            operation=operation or job_type,
            operation_config=operation_config or {},
            dependency_check=dependency_check or {},
            source_revision=source_revision,
            status="queued",
            progress=0,
            created_at=now,
            updated_at=now,
        )
        self.processing_jobs[job.job_id] = job
        self.sessions[session_id] = replace(
            session,
            processing_status="processing_submitted",
            updated_at=now,
        )
        self._audit(
            "processing_job_created",
            actor_user_id=user.user_id,
            target_type="processing_job",
            target_id=job.job_id,
            message=f"Queued {job_type} job for {session_id}",
        )
        return replace(job)

    def get_processing_job_for_user(self, job_id: str, user: User) -> ProcessingJob | None:
        job = self.processing_jobs.get(job_id)
        if job is None:
            return None
        if user.role != "admin" and job.owner_user_id != user.user_id:
            return None

        now = self._now()
        if job.status == "queued":
            job = replace(
                job,
                status="processing",
                progress=50,
                stage="transcribing",
                started_at=now,
                updated_at=now,
            )
            self.processing_jobs[job_id] = job
            
            session = self.sessions.get(job.session_id)
            if session:
                self.sessions[job.session_id] = replace(
                    session,
                    processing_status="processing",
                    updated_at=now,
                )
                
            self._audit(
                "processing_job_updated",
                actor_user_id=user.user_id,
                target_type="processing_job",
                target_id=job_id,
                message=f"Statefully transitioned processing job {job_id} to processing",
            )
        elif job.status == "processing":
            session = self.sessions.get(job.session_id)
            if session is None:
                raise ValueError(f"Unknown session_id: {job.session_id}")
            case = self.cases.get(session.case_id)
            if case is None:
                raise ValueError(f"Unknown case_id: {session.case_id}")
                
            transcript = None
            if session.transcript_id:
                transcript = self.transcripts.get(session.transcript_id)
            if transcript is None:
                transcript = next((t for t in self.transcripts.values() if t.session_id == session.session_id), None)
                
            if transcript is None:
                chat_text = self._mock_chat_text(
                    child_id=case.anonymized_child_code,
                    age_months=case.age_months,
                    sex=case.sex,
                )
                transcript = self.create_transcript_for_session(
                    session_id=session.session_id,
                    user=user,
                    transcript_text=chat_text,
                    original_filename=f"{case.anonymized_child_code}_transcript.cha",
                )
            
            job = replace(
                job,
                status="completed",
                progress=100,
                stage="awaiting_review",
                finished_at=now,
                updated_at=now,
                result_refs={"transcript_id": transcript.transcript_id},
            )
            self.processing_jobs[job_id] = job
            
            feature_row = next((item for item in self.extracted_features.values() if item.session_id == session.session_id), None)
            if feature_row is None:
                core_features = self._mock_features_from_transcript(case, transcript.transcript_text)
                optional_indicators = self._mock_optional_indicators_from_transcript(transcript.transcript_text)
                self._feature_sequence += 1
                feature_id = f"FEATURE-{self._feature_sequence:03d}"
                feature_row = ExtractedFeatures(
                    feature_id=feature_id,
                    session_id=session.session_id,
                    case_id=session.case_id,
                    owner_user_id=session.owner_user_id,
                    feature_schema_version="14-feature-schema",
                    features={**core_features, **optional_indicators},
                    core_features=core_features,
                    optional_indicators=optional_indicators,
                    created_at=now,
                )
                self.extracted_features[feature_id] = feature_row
                
            ai_output = next((item for item in self.ai_screening_outputs.values() if item.session_id == session.session_id), None)
            if ai_output is None:
                score = self._mock_screening_support_score(feature_row.features)
                if score >= 0.67:
                    concern_level = "moderate_concern"
                elif score >= 0.4:
                    concern_level = "watchful_review"
                else:
                    concern_level = "low_concern"
                top_features = self._top_contributing_features(feature_row.features)
                
                self._ai_output_sequence += 1
                ai_output_id = f"AI-OUTPUT-{self._ai_output_sequence:03d}"
                ai_output = AIScreeningOutput(
                    output_id=ai_output_id,
                    session_id=session.session_id,
                    case_id=session.case_id,
                    owner_user_id=session.owner_user_id,
                    concern_level=concern_level,
                    model_version="screening-support-v0.2.0",
                    screening_support_score=score,
                    confidence_interval=None,
                    explanation=(
                        "Decision-support only. Review transcript QA, session context, "
                        "and therapist notes before interpreting this output. It is not a diagnosis."
                    ),
                    plain_language_explanation=(
                        "This output highlights speech-language patterns that may warrant closer "
                        "clinical review. It is not a diagnosis."
                    ),
                    top_contributing_features=top_features,
                    evidence_items=[
                        {
                            "type": "feature",
                            "feature_key": feature,
                            "value": feature_row.features.get(feature),
                            "explanation": FEATURE_DOCS[feature].clinical_meaning,
                        }
                        for feature in top_features
                        if feature in FEATURE_DOCS
                    ],
                    therapist_review_status="awaiting_review",
                    differential_probabilities=self._mock_differential_probabilities(feature_row.features),
                    created_at=now,
                )
                self.ai_screening_outputs[ai_output_id] = ai_output
                
                self._model_run_sequence += 1
                self.model_runs[f"MODEL-RUN-{self._model_run_sequence:03d}"] = ModelRun(
                    model_run_id=f"MODEL-RUN-{self._model_run_sequence:03d}",
                    session_id=session.session_id,
                    case_id=session.case_id,
                    owner_user_id=session.owner_user_id,
                    model_card_version="prototype-screening-support-v1",
                    feature_schema_version=feature_row.feature_schema_version,
                    thresholds={
                        "low_upper": 0.4,
                        "watchful_upper": 0.67,
                        "uncertainty_lower": 0.4,
                        "uncertainty_upper": 0.6,
                    },
                    calibration_metadata={
                        "validation_status": "not_validated_for_thai_children",
                        "output_type": "clinical_decision_support",
                    },
                    created_at=now,
                )

            session = self.sessions[job.session_id]
            self.sessions[job.session_id] = replace(
                session,
                processing_status="transcript_ready",
                feature_extraction_status="completed",
                ai_analysis_status="completed",
                report_status="pending",
                updated_at=now,
            )
            
            self._audit(
                "processing_job_updated",
                actor_user_id=user.user_id,
                target_type="processing_job",
                target_id=job_id,
                message=f"Statefully transitioned processing job {job_id} to completed",
            )

        return replace(job)

    def list_processing_jobs_for_session_for_user(self, session_id: str, user: User) -> list[ProcessingJob]:
        session = self.sessions.get(session_id)
        if session is None:
            return []
        if user.role != "admin" and session.owner_user_id != user.user_id:
            return []
        rows = [
            job
            for job in self.processing_jobs.values()
            if job.session_id == session_id
        ]
        return [replace(job) for job in sorted(rows, key=lambda item: item.created_at, reverse=True)]

    def update_processing_job(
        self,
        job_id: str,
        user: User,
        *,
        status: JobStatus,
        progress: int | None = None,
        error_code: str | None = None,
        error_message: str = "",
        stage: str | None = None,
        result_refs: dict | None = None,
    ) -> ProcessingJob | None:
        job = self.processing_jobs.get(job_id)
        if job is None:
            return None
        if user.role != "admin" and job.owner_user_id != user.user_id:
            return None

        now = self._now()
        updated = replace(
            job,
            status=status,
            stage=stage or self._default_job_stage(status),
            progress=max(0, min(100, job.progress if progress is None else progress)),
            error_code=error_code,
            error_message=error_message,
            result_refs=result_refs or job.result_refs,
            started_at=job.started_at or (now if status == "processing" else None),
            finished_at=now if status in {"completed", "failed", "cancelled"} else job.finished_at,
            updated_at=now,
        )
        self.processing_jobs[job_id] = updated
        session = self.sessions[updated.session_id]
        session_status: ProcessingStatus = "processing"
        if status == "completed":
            session_status = "transcript_ready"
        elif status == "failed":
            session_status = "failed"
        elif status == "cancelled":
            session_status = "pending"
        self.sessions[updated.session_id] = replace(session, processing_status=session_status, updated_at=now)
        self._audit(
            "processing_job_updated",
            actor_user_id=user.user_id,
            target_type="processing_job",
            target_id=job_id,
            message=f"Updated processing job {job_id} to {status}",
        )
        return replace(updated)

    @staticmethod
    def _default_job_stage(status: JobStatus) -> str:
        if status == "queued":
            return "queued"
        if status == "processing":
            return "transcribing"
        if status == "completed":
            return "awaiting_review"
        if status == "cancelled":
            return "failed"
        return "failed"

    def list_clinical_speech_artifacts_for_session_for_user(
        self,
        session_id: str,
        user: User,
    ) -> list[ClinicalSpeechArtifact]:
        session = self.sessions.get(session_id)
        if session is None:
            return []
        if user.role != "admin" and session.owner_user_id != user.user_id:
            return []
        rows = [
            artifact
            for artifact in self.clinical_speech_artifacts.values()
            if artifact.session_id == session_id
        ]
        return [replace(artifact) for artifact in sorted(rows, key=lambda item: item.created_at, reverse=True)]

    def create_clinical_speech_artifact(
        self,
        session_id: str,
        user: User,
        *,
        artifact_type: str,
        freshness: str = "current",
        transcript_id: str | None = None,
        feature_id: str | None = None,
        job_id: str | None = None,
        source_revision: str | None = None,
        source_hash: str | None = None,
        content_type: str = "application/json",
        content_text: str = "",
        parsed_metrics: dict | None = None,
        metadata: dict | None = None,
        review_status: ReviewStatus = "awaiting_review",
    ) -> ClinicalSpeechArtifact:
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session_id: {session_id}")
        if user.role != "admin" and session.owner_user_id != user.user_id:
            raise PermissionError("Clinical users can only create artifacts for owned sessions.")

        now = self._now()
        if freshness == "current":
            self._supersede_current_artifacts(session_id, artifact_type, now=now)

        self._clinical_speech_artifact_sequence += 1
        artifact = ClinicalSpeechArtifact(
            artifact_id=f"ARTIFACT-{self._clinical_speech_artifact_sequence:04d}",
            session_id=session_id,
            case_id=session.case_id,
            owner_user_id=session.owner_user_id,
            artifact_type=artifact_type,
            freshness=freshness,  # type: ignore[arg-type]
            transcript_id=transcript_id,
            feature_id=feature_id,
            job_id=job_id,
            source_revision=source_revision,
            source_hash=source_hash,
            content_type=content_type,
            content_text=content_text,
            parsed_metrics=parsed_metrics or {},
            metadata=metadata or {},
            review_status=review_status,
            created_by_user_id=user.user_id,
            created_at=now,
            updated_at=now,
        )
        self.clinical_speech_artifacts[artifact.artifact_id] = artifact

        if job_id and job_id in self.processing_jobs:
            job = self.processing_jobs[job_id]
            artifact_ids = [*job.artifact_ids, artifact.artifact_id]
            self.processing_jobs[job_id] = replace(
                job,
                artifact_ids=artifact_ids,
                result_refs={**job.result_refs, "artifact_ids": artifact_ids},
                updated_at=now,
            )

        self._audit(
            "clinical_speech_artifact_created",
            actor_user_id=user.user_id,
            target_type="clinical_speech_artifact",
            target_id=artifact.artifact_id,
            message=f"Created {artifact_type} artifact for {session_id}",
        )
        return replace(artifact)

    def update_feature_review_disposition(
        self,
        feature_id: str,
        flag_key: str,
        user: User,
        *,
        disposition: str,
        note: str = "",
    ) -> FeatureReviewDisposition | None:
        allowed_dispositions = {"needs_review", "accepted", "rejected", "needs_context"}
        if disposition not in allowed_dispositions:
            raise ValueError(f"disposition must be one of: {', '.join(sorted(allowed_dispositions))}")
        if not flag_key.strip():
            raise ValueError("flag_key is required.")

        feature = self.extracted_features.get(feature_id)
        if feature is None:
            return None
        if user.role != "admin" and feature.owner_user_id != user.user_id:
            return None

        now = self._now()
        normalized_flag_key = flag_key.strip()
        existing = next(
            (
                item
                for item in self.feature_review_dispositions.values()
                if item.feature_id == feature_id and item.flag_key == normalized_flag_key
            ),
            None,
        )
        if existing is None:
            self._feature_review_disposition_sequence += 1
            updated = FeatureReviewDisposition(
                disposition_id=f"FEATURE-DISP-{self._feature_review_disposition_sequence:03d}",
                session_id=feature.session_id,
                case_id=feature.case_id,
                owner_user_id=feature.owner_user_id,
                feature_id=feature_id,
                flag_key=normalized_flag_key,
                disposition=disposition,  # type: ignore[arg-type]
                note=note.strip(),
                reviewed_by_user_id=user.user_id,
                source_revision=feature.source_revision,
                created_at=now,
                updated_at=now,
            )
        else:
            updated = replace(
                existing,
                disposition=disposition,  # type: ignore[arg-type]
                note=note.strip(),
                reviewed_by_user_id=user.user_id,
                source_revision=feature.source_revision,
                updated_at=now,
            )
        self.feature_review_dispositions[updated.disposition_id] = updated
        self._audit(
            "feature_review_disposition_updated",
            actor_user_id=user.user_id,
            target_type="feature_review_disposition",
            target_id=updated.disposition_id,
            message=f"Marked feature flag {normalized_flag_key} as {disposition}",
        )
        return replace(updated)

    def list_feature_review_dispositions_for_feature_for_user(
        self,
        feature_id: str,
        user: User,
    ) -> list[FeatureReviewDisposition]:
        feature = self.extracted_features.get(feature_id)
        if feature is None:
            return []
        if user.role != "admin" and feature.owner_user_id != user.user_id:
            return []
        rows = [
            item
            for item in self.feature_review_dispositions.values()
            if item.feature_id == feature_id
        ]
        return [replace(item) for item in sorted(rows, key=lambda item: item.updated_at, reverse=True)]

    def _supersede_current_artifacts(self, session_id: str, artifact_type: str, *, now: datetime) -> None:
        for artifact_id, artifact in list(self.clinical_speech_artifacts.items()):
            if artifact.session_id == session_id and artifact.artifact_type == artifact_type and artifact.freshness == "current":
                self.clinical_speech_artifacts[artifact_id] = replace(
                    artifact,
                    freshness="superseded",
                    updated_at=now,
                )

    def _mark_clinical_speech_artifacts_stale(
        self,
        session_id: str,
        *,
        transcript_id: str | None = None,
        reason: str,
    ) -> None:
        now = self._now()
        for artifact_id, artifact in list(self.clinical_speech_artifacts.items()):
            if artifact.session_id != session_id:
                continue
            if transcript_id is not None and artifact.transcript_id not in {None, transcript_id}:
                continue
            if artifact.freshness not in {"current", "preliminary"}:
                continue
            self.clinical_speech_artifacts[artifact_id] = replace(
                artifact,
                freshness="stale",
                metadata={**artifact.metadata, "stale_reason": reason},
                updated_at=now,
            )

    def _transcript_source_revision_for_session(self, session_id: str) -> str | None:
        session = self.sessions.get(session_id)
        if session is None or session.transcript_id is None:
            return None
        return self._transcript_source_revision(session.transcript_id)

    def _transcript_source_revision(self, transcript_id: str) -> str:
        payload = [
            {
                "line_id": line.line_id,
                "version": line.version,
                "speaker_code": line.speaker_code,
                "speaker_role": line.speaker_role,
                "text": line.reviewed_text if line.reviewed_text is not None else line.utterance_text,
                "start_ms": line.start_ms,
                "end_ms": line.end_ms,
                "reviewed": line.reviewed,
            }
            for line in self.list_transcript_lines_for_transcript(transcript_id)
        ]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def list_transcripts_for_user(self, user: User) -> list[Transcript]:
        rows = self.transcripts.values()
        if user.role != "admin":
            rows = [transcript for transcript in rows if transcript.owner_user_id == user.user_id]
        return [replace(transcript) for transcript in sorted(rows, key=lambda item: item.created_at, reverse=True)]

    def get_transcript_for_user(self, transcript_id: str, user: User) -> Transcript | None:
        transcript = self.transcripts.get(transcript_id)
        if transcript is None:
            return None
        if user.role == "admin" or transcript.owner_user_id == user.user_id:
            return replace(transcript)
        return None

    def get_transcript_for_session_for_user(self, session_id: str, user: User) -> Transcript | None:
        session = self.sessions.get(session_id)
        if session is None or self.get_case_for_user(session.case_id, user) is None:
            return None
        if session.transcript_id is None:
            return None
        transcript = self.transcripts.get(session.transcript_id)
        return replace(transcript) if transcript else None

    def get_features_for_session_for_user(self, session_id: str, user: User) -> ExtractedFeatures | None:
        session = self.sessions.get(session_id)
        if session is None or self.get_case_for_user(session.case_id, user) is None:
            return None
        row = next((item for item in self.extracted_features.values() if item.session_id == session_id), None)
        return replace(row) if row else None

    def list_transcript_lines_for_transcript(self, transcript_id: str) -> list[TranscriptLine]:
        rows = [
            line
            for line in self.transcript_lines.values()
            if line.transcript_id == transcript_id
        ]
        return [replace(line) for line in sorted(rows, key=lambda item: item.line_number)]

    def get_ai_output_for_session_for_user(self, session_id: str, user: User) -> AIScreeningOutput | None:
        session = self.sessions.get(session_id)
        if session is None or self.get_case_for_user(session.case_id, user) is None:
            return None
        row = next((item for item in self.ai_screening_outputs.values() if item.session_id == session_id), None)
        return replace(row) if row else None

    def get_report_eligible_similarity_for_session(
        self,
        session_id: str,
        user: User,
    ) -> AIScreeningOutput | None:
        session = self.sessions.get(session_id)
        if session is None or self.get_case_for_user(session.case_id, user) is None:
            return None
        rows = [
            output
            for output in self.ai_screening_outputs.values()
            if output.session_id == session_id
            and output.output_kind == "reference_cohort_similarity"
            and output.inference_status == "reviewed"
            and output.report_eligible
        ]
        if not rows:
            return None
        return replace(max(rows, key=lambda item: item.created_at))

    def get_reference_comparison_for_session_for_user(
        self,
        session_id: str,
        user: User,
    ) -> ReferenceComparisonResult | None:
        session = self.sessions.get(session_id)
        if session is None or self.get_case_for_user(session.case_id, user) is None:
            return None
        case = self.cases.get(session.case_id)
        if case is None:
            raise ValueError(f"Unknown case_id: {session.case_id}")
        feature_row = self.get_features_for_session_for_user(session_id, user)
        if feature_row is None:
            raise ValueError("Extracted features are required before Reference Comparison.")

        features = dict(feature_row.core_features or feature_row.features)
        feature_age = features.get("age_months")
        age_months = feature_age if feature_age is not None else case.age_months
        if self.reference_engine is None:
            self.reference_engine = ReferenceEngine()
        return self.reference_engine.compare(
            features=features,
            age_months=age_months,
            session_type=session.session_type,
        )

    def list_goals_for_case_for_user(self, case_id: str, user: User) -> list[TherapyGoal]:
        if self.get_case_for_user(case_id, user) is None:
            return []
        rows = [goal for goal in self.therapy_goals.values() if goal.case_id == case_id]
        return [replace(goal) for goal in sorted(rows, key=lambda item: item.created_at)]

    def list_reports_for_case_for_user(self, case_id: str, user: User) -> list[Report]:
        if self.get_case_for_user(case_id, user) is None:
            return []
        rows = [report for report in self.reports.values() if report.case_id == case_id]
        return [replace(report) for report in sorted(rows, key=lambda item: item.created_at, reverse=True)]

    def create_case(
        self,
        *,
        owner_user_id: str,
        anonymized_child_code: str,
        age_months: int,
        sex: Sex,
        primary_concerns: str,
        consent_status: ConsentStatus,
        anonymization_status: AnonymizationStatus,
        external_clinical_status: ExternalClinicalStatus = "not_provided",
        notes: str = "",
    ) -> ChildCase:
        owner = self.users.get(owner_user_id)
        if owner is None:
            raise ValueError(f"Unknown owner_user_id: {owner_user_id}")
        if owner.role not in {"therapist", "clinician", "admin"}:
            raise ValueError("Cases must be owned by a clinical user.")
        import re
        stripped_code = anonymized_child_code.strip()
        if not stripped_code:
            raise ValueError("anonymized_child_code is required.")
        if not re.match(r"^[a-zA-Z0-9\-]+$", stripped_code):
            raise ValueError(
                "anonymized_child_code must contain only letters, numbers, and hyphens (e.g. CHI-A01). "
                "Real child names or identifiers are strictly prohibited."
            )
        if age_months < 0:
            raise ValueError("age_months must be non-negative.")

        now = self._now()
        self._case_sequence += 1
        case = ChildCase(
            case_id=f"CASE-{self._case_sequence:03d}",
            owner_user_id=owner_user_id,
            anonymized_child_code=anonymized_child_code.strip(),
            age_months=int(age_months),
            sex=sex,
            primary_concerns=primary_concerns.strip(),
            external_clinical_status=external_clinical_status,
            consent_status=consent_status,
            anonymization_status=anonymization_status,
            notes=notes.strip(),
            created_at=now,
            updated_at=now,
        )
        self.cases[case.case_id] = case
        self._audit(
            "case_created",
            actor_user_id=owner_user_id,
            target_type="child_case",
            target_id=case.case_id,
            message=f"Created anonymized mock case {case.case_id}",
        )
        return replace(case)

    def update_case_for_user(
        self,
        case_id: str,
        user: User,
        *,
        age_months: int | None = None,
        sex: Sex | None = None,
        primary_concerns: str | None = None,
        consent_status: ConsentStatus | None = None,
        anonymization_status: AnonymizationStatus | None = None,
        external_clinical_status: ExternalClinicalStatus | None = None,
        notes: str | None = None,
    ) -> ChildCase | None:
        case = self.cases.get(case_id)
        if case is None:
            return None
        if user.role != "admin" and case.owner_user_id != user.user_id:
            return None
        if age_months is not None and age_months < 0:
            raise ValueError("age_months must be non-negative.")

        updated = replace(
            case,
            age_months=case.age_months if age_months is None else int(age_months),
            sex=case.sex if sex is None else sex,
            primary_concerns=case.primary_concerns if primary_concerns is None else primary_concerns.strip(),
            consent_status=case.consent_status if consent_status is None else consent_status,
            anonymization_status=case.anonymization_status if anonymization_status is None else anonymization_status,
            external_clinical_status=case.external_clinical_status if external_clinical_status is None else external_clinical_status,
            notes=case.notes if notes is None else notes.strip(),
            updated_at=self._now(),
        )
        self.cases[case_id] = updated
        
        if consent_status == "declined":
            for af_id, af in list(self.audio_files.items()):
                if af.case_id == case_id:
                    self.audio_files[af_id] = replace(af, processing_status="deleted")
                    if af.file_object_id and af.file_object_id in self.file_objects:
                        fo = self.file_objects[af.file_object_id]
                        self.file_objects[af.file_object_id] = replace(fo, deleted_at=self._now())
            
            for t_id, t in list(self.transcripts.items()):
                if t.case_id == case_id:
                    self.transcripts[t_id] = replace(
                        t,
                        case_id="orphaned-due-to-withdrawn-consent",
                        owner_user_id="orphaned-due-to-withdrawn-consent",
                        reviewer_notes="[ANONYMIZED] Consent withdrawn. Identifiers unlinked."
                    )
            
            for tl_id, tl in list(self.transcript_lines.items()):
                if tl.case_id == case_id:
                    self.transcript_lines[tl_id] = replace(
                        tl,
                        case_id="orphaned-due-to-withdrawn-consent",
                        owner_user_id="orphaned-due-to-withdrawn-consent",
                    )
            
            for ef_id, ef in list(self.extracted_features.items()):
                if ef.case_id == case_id:
                    self.extracted_features[ef_id] = replace(
                        ef,
                        case_id="orphaned-due-to-withdrawn-consent",
                        owner_user_id="orphaned-due-to-withdrawn-consent",
                    )
                    
            for art_id, art in list(self.clinical_speech_artifacts.items()):
                if art.case_id == case_id:
                    self.clinical_speech_artifacts[art_id] = replace(
                        art,
                        case_id="orphaned-due-to-withdrawn-consent",
                        owner_user_id="orphaned-due-to-withdrawn-consent",
                    )
                    
            for aso_id, aso in list(self.ai_screening_outputs.items()):
                if aso.case_id == case_id:
                    self.ai_screening_outputs[aso_id] = replace(
                        aso,
                        case_id="orphaned-due-to-withdrawn-consent",
                        owner_user_id="orphaned-due-to-withdrawn-consent",
                    )

        self._audit(
            "case_updated",
            actor_user_id=user.user_id,
            target_type="child_case",
            target_id=case_id,
            message=f"Updated anonymized mock case {case_id}",
        )
        return replace(updated)

    def create_session(
        self,
        *,
        case_id: str,
        user: User,
        session_date: str,
        session_type: SessionType,
        notes: str = "",
    ) -> Session:
        case = self.cases.get(case_id)
        if case is None:
            raise ValueError(f"Unknown case_id: {case_id}")
        if user.role != "admin" and case.owner_user_id != user.user_id:
            raise PermissionError("Clinical users can only create sessions for owned cases.")

        now = self._now()
        self._session_sequence += 1
        session = Session(
            session_id=f"SESSION-{self._session_sequence:03d}",
            case_id=case_id,
            owner_user_id=case.owner_user_id,
            session_date=session_date,
            session_type=session_type,
            therapist_review_status="not_started",
            report_status="not_started",
            notes=notes.strip(),
            created_at=now,
            updated_at=now,
        )
        self.sessions[session.session_id] = session
        self._audit(
            "session_created",
            actor_user_id=user.user_id,
            target_type="session",
            target_id=session.session_id,
            message=f"Created mock session {session.session_id}",
        )
        return replace(session)

    def add_therapist_note(
        self,
        *,
        case_id: str,
        user: User,
        note_text: str,
        session_id: str | None = None,
    ) -> TherapistNote:
        case = self.cases.get(case_id)
        if case is None:
            raise ValueError(f"Unknown case_id: {case_id}")
        if user.role != "admin" and case.owner_user_id != user.user_id:
            raise PermissionError("Clinical users can only add notes to owned cases.")
        if session_id is not None:
            session = self.sessions.get(session_id)
            if session is None or session.case_id != case_id:
                raise ValueError("session_id must belong to the selected case.")
        if not note_text.strip():
            raise ValueError("note_text is required.")

        now = self._now()
        self._note_sequence += 1
        note = TherapistNote(
            note_id=f"NOTE-{self._note_sequence:03d}",
            case_id=case_id,
            owner_user_id=case.owner_user_id,
            note_text=note_text.strip(),
            session_id=session_id,
            created_at=now,
            updated_at=now,
        )
        self.therapist_notes[note.note_id] = note
        self._audit(
            "therapist_note_created",
            actor_user_id=user.user_id,
            target_type="therapist_note",
            target_id=note.note_id,
            message=f"Added therapist note {note.note_id}",
        )
        return replace(note)

    def create_audio_file_metadata(
        self,
        *,
        case_id: str,
        session_id: str,
        user: User,
        original_filename: str,
        file_size: int,
        processing_status: ProcessingStatus = "pending",
    ) -> AudioFile:
        case = self.cases.get(case_id)
        session = self.sessions.get(session_id)
        if case is None:
            raise ValueError(f"Unknown case_id: {case_id}")
        if session is None:
            raise ValueError(f"Unknown session_id: {session_id}")
        if session.case_id != case_id:
            raise ValueError("session_id must belong to the selected case.")
        if user.role != "admin" and case.owner_user_id != user.user_id:
            raise PermissionError("Clinical users can only attach files to owned cases.")

        file_type = self._validated_file_type(original_filename)
        if file_size <= 0:
            raise ValueError("file_size must be positive.")
        if file_size > MAX_AUDIO_FILE_SIZE_BYTES:
            raise ValueError("File exceeds the maximum configured size.")

        now = self._now()
        self._audio_file_sequence += 1
        audio_file_id = f"AUDIO-{self._audio_file_sequence:03d}"
        audio_file = AudioFile(
            audio_file_id=audio_file_id,
            owner_user_id=case.owner_user_id,
            case_id=case_id,
            session_id=session_id,
            original_filename=Path(original_filename).name,
            stored_filename=f"{case_id}_{session_id}_{audio_file_id}.{file_type}",
            file_type=file_type,
            file_size=int(file_size),
            upload_time=now,
            processing_status=processing_status,
        )
        self.audio_files[audio_file_id] = audio_file
        self.sessions[session_id] = replace(
            session,
            audio_file_id=audio_file_id,
            feature_extraction_status="pending",
            updated_at=now,
        )
        self._audit(
            "file_uploaded",
            actor_user_id=user.user_id,
            target_type="audio_file",
            target_id=audio_file_id,
            message=f"Created metadata-only mock upload record {audio_file_id}",
        )
        return replace(audio_file)

    def create_transcript_for_session(
        self,
        *,
        session_id: str,
        user: User,
        transcript_text: str,
        original_filename: str | None = None,
        reviewer_notes: str = "",
    ) -> Transcript:
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session_id: {session_id}")
        case = self.cases.get(session.case_id)
        if case is None:
            raise ValueError(f"Unknown case_id: {session.case_id}")
        if user.role != "admin" and session.owner_user_id != user.user_id:
            raise PermissionError("Clinical users can only attach transcripts to owned sessions.")
        if original_filename is not None:
            self._validated_transcript_type(original_filename)
        if not transcript_text.strip():
            raise ValueError("transcript_text is required.")

        qa_result = review_cha_text(transcript_text)
        review_status = self._review_status_from_qa(qa_result["status"])
        now = self._now()
        self._transcript_sequence += 1
        transcript = Transcript(
            transcript_id=f"TRANSCRIPT-{self._transcript_sequence:03d}",
            session_id=session_id,
            case_id=session.case_id,
            owner_user_id=session.owner_user_id,
            transcript_text=transcript_text,
            review_status=review_status,
            reviewer_notes=reviewer_notes.strip(),
            qa_status=qa_result["status"],
            qa_score=qa_result["quality_score"],
            qa_issues=qa_result["issues"],
            created_at=now,
            updated_at=now,
        )
        self.transcripts[transcript.transcript_id] = transcript
        self._replace_transcript_lines(transcript)
        self._mark_clinical_speech_artifacts_stale(
            session_id,
            reason="new_transcript_attached",
        )
        self.sessions[session_id] = replace(
            session,
            transcript_id=transcript.transcript_id,
            therapist_review_status=review_status,
            feature_extraction_status="pending" if review_status == "awaiting_review" else "not_started",
            updated_at=now,
        )
        self._audit(
            "transcript_uploaded",
            actor_user_id=user.user_id,
            target_type="transcript",
            target_id=transcript.transcript_id,
            message=f"Created CHAT transcript record {transcript.transcript_id}",
        )
        return replace(transcript)

    def update_transcript_for_user(
        self,
        transcript_id: str,
        user: User,
        *,
        transcript_text: str,
        reviewer_notes: str = "",
    ) -> Transcript | None:
        transcript = self.transcripts.get(transcript_id)
        if transcript is None:
            return None
        if user.role != "admin" and transcript.owner_user_id != user.user_id:
            return None
        if not transcript_text.strip():
            raise ValueError("transcript_text is required.")

        qa_result = review_cha_text(transcript_text)
        review_status = self._review_status_from_qa(qa_result["status"])
        now = self._now()
        updated = replace(
            transcript,
            transcript_text=transcript_text,
            reviewer_notes=reviewer_notes.strip(),
            review_status=review_status,
            qa_status=qa_result["status"],
            qa_score=qa_result["quality_score"],
            qa_issues=qa_result["issues"],
            updated_at=now,
        )
        self.transcripts[transcript_id] = updated
        self._replace_transcript_lines(updated)
        self._mark_clinical_speech_artifacts_stale(
            updated.session_id,
            transcript_id=transcript_id,
            reason="transcript_text_updated",
        )
        session = self.sessions[updated.session_id]
        self.sessions[updated.session_id] = replace(
            session,
            therapist_review_status=review_status,
            feature_extraction_status="pending" if review_status == "awaiting_review" else "not_started",
            updated_at=now,
        )
        self._audit(
            "transcript_edited",
            actor_user_id=user.user_id,
            target_type="transcript",
            target_id=transcript_id,
            message=f"Edited CHAT transcript {transcript_id}",
        )
        return replace(updated)

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
        transcript = self.transcripts.get(transcript_id)
        if transcript is None:
            return None
        if user.role != "admin" and transcript.owner_user_id != user.user_id:
            return None

        line = self.transcript_lines.get(line_id)
        if line is None or line.transcript_id != transcript_id:
            return None
        if expected_version is not None and expected_version != line.version:
            raise TranscriptLineVersionConflict(line_id, expected_version, line.version)

        now = self._now()
        updated_reviewed = bool(reviewed) if reviewed is not None else line.reviewed
        updated_speaker_code = (speaker_code or line.speaker_code).strip().upper()
        corrected_text = utterance_text.strip() if utterance_text is not None else line.reviewed_text
        updated = replace(
            line,
            speaker_code=updated_speaker_code,
            speaker_role=speaker_role_for_code(updated_speaker_code),
            reviewed_text=corrected_text,
            reviewed=updated_reviewed,
            review_status="reviewed" if updated_reviewed else "needs_review",
            interpretation_note=(interpretation_note if interpretation_note is not None else line.interpretation_note).strip(),
            version=line.version + 1,
            updated_at=now,
            updated_by_user_id=user.user_id,
        )
        if not updated.speaker_code:
            raise ValueError("speaker_code is required.")
        if not (updated.reviewed_text or updated.utterance_text):
            raise ValueError("utterance_text is required.")

        self.transcript_lines[line_id] = updated
        self._mark_clinical_speech_artifacts_stale(
            transcript.session_id,
            transcript_id=transcript_id,
            reason="transcript_line_updated",
        )
        transcript = replace(transcript, review_status="awaiting_review", updated_at=now)
        self.transcripts[transcript_id] = transcript
        session = self.sessions[transcript.session_id]
        self.sessions[transcript.session_id] = replace(
            session,
            therapist_review_status="awaiting_review",
            feature_extraction_status="stale",
            ai_analysis_status="stale",
            updated_at=now,
        )
        self._audit(
            "transcript_line_edited",
            actor_user_id=user.user_id,
            target_type="transcript_line",
            target_id=line_id,
            message=f"Edited transcript line {line_id}",
        )
        return replace(updated)

    def mark_transcript_reviewed(self, transcript_id: str, user: User, reviewer_notes: str = "") -> Transcript | None:
        transcript = self.transcripts.get(transcript_id)
        if transcript is None:
            return None
        if user.role != "admin" and transcript.owner_user_id != user.user_id:
            return None

        now = self._now()
        updated = replace(
            transcript,
            review_status="reviewed",
            reviewer_notes=reviewer_notes.strip() or transcript.reviewer_notes,
            updated_at=now,
        )
        self.transcripts[transcript_id] = updated
        for line_id, line in list(self.transcript_lines.items()):
            if line.transcript_id == transcript_id:
                self.transcript_lines[line_id] = replace(
                    line,
                    reviewed=True,
                    review_status="reviewed",
                    version=line.version + 1,
                    updated_at=now,
                    updated_by_user_id=user.user_id,
                )
        session = self.sessions[updated.session_id]
        self.sessions[updated.session_id] = replace(
            session,
            therapist_review_status="reviewed",
            feature_extraction_status="pending",
            updated_at=now,
        )
        self._audit(
            "transcript_reviewed",
            actor_user_id=user.user_id,
            target_type="transcript",
            target_id=transcript_id,
            message=f"Marked CHAT transcript {transcript_id} reviewed",
        )
        return replace(updated)

    def create_clinical_signoff(
        self,
        *,
        target_type: SignoffTargetType,
        target_id: str,
        user: User,
        notes: str = "",
    ) -> ClinicalSignoff:
        session_id: str | None = None
        case_id: str | None = None
        owner_user_id: str | None = None

        if target_type == "transcript":
            transcript = self.transcripts.get(target_id)
            if transcript is None:
                raise ValueError(f"Unknown transcript_id: {target_id}")
            session_id = transcript.session_id
            case_id = transcript.case_id
            owner_user_id = transcript.owner_user_id
            if transcript.review_status != "reviewed":
                raise ValueError("Transcript must be reviewed before clinical sign-off.")
        elif target_type == "features":
            feature_row = self.extracted_features.get(target_id)
            if feature_row is None:
                raise ValueError(f"Unknown feature_id: {target_id}")
            session_id = feature_row.session_id
            case_id = feature_row.case_id
            owner_user_id = feature_row.owner_user_id
        elif target_type == "report":
            report = self.reports.get(target_id)
            if report is None:
                raise ValueError(f"Unknown report_id: {target_id}")
            session_id = report.session_id
            case_id = report.case_id
            owner_user_id = report.owner_user_id
        if owner_user_id is None or case_id is None:
            raise ValueError("Unable to resolve sign-off target ownership.")
        if user.role != "admin" and owner_user_id != user.user_id:
            raise PermissionError("Clinical users can only sign off owned records.")

        now = self._now()
        self._signoff_sequence += 1
        signoff = ClinicalSignoff(
            signoff_id=f"SIGNOFF-{self._signoff_sequence:03d}",
            target_type=target_type,
            target_id=target_id,
            session_id=session_id,
            case_id=case_id,
            owner_user_id=owner_user_id,
            signed_by_user_id=user.user_id,
            notes=notes.strip(),
            created_at=now,
        )
        self.clinical_signoffs[signoff.signoff_id] = signoff
        self._audit(
            "clinical_signoff_created",
            actor_user_id=user.user_id,
            target_type=target_type,
            target_id=target_id,
            message=f"Created clinical sign-off for {target_type} {target_id}",
        )
        return replace(signoff)

    def signoff_transcript_for_session(self, session_id: str, user: User, notes: str = "") -> ClinicalSignoff:
        transcript = self.get_transcript_for_session_for_user(session_id, user)
        if transcript is None:
            raise ValueError("A transcript is required before transcript sign-off.")
        reviewed = self.mark_transcript_reviewed(transcript.transcript_id, user, notes)
        if reviewed is None:
            raise PermissionError("Clinical users can only sign off owned transcripts.")
        signoff = self.create_clinical_signoff(
            target_type="transcript",
            target_id=reviewed.transcript_id,
            user=user,
            notes=notes,
        )
        try:
            self.extract_features_for_session(session_id, user)
            self.generate_reference_cohort_similarity_for_session(
                session_id,
                user,
                inference_status="reviewed",
            )
        except Exception as exc:  # noqa: BLE001
            session = self.sessions.get(session_id)
            if session is not None:
                self.sessions[session_id] = replace(
                    session,
                    ai_analysis_status="failed",
                    report_status="pending",
                    updated_at=self._now(),
                )
            self._audit(
                "reference_cohort_similarity_unavailable",
                actor_user_id=user.user_id,
                target_type="session",
                target_id=session_id,
                message=f"Reviewed reference cohort similarity failed after sign-off: {exc}",
            )
        return signoff

    def export_reviewed_chat_for_session(
        self,
        session_id: str,
        user: User,
        *,
        allow_preliminary: bool = False,
    ) -> str:
        transcript = self.get_transcript_for_session_for_user(session_id, user)
        if transcript is None:
            raise ValueError("A transcript is required before CHAT export.")
        if transcript.review_status != "reviewed" and not allow_preliminary:
            raise ValueError("Transcript review sign-off is required before reviewed CHAT export.")
        case = self.cases.get(transcript.case_id)
        if case is None:
            raise ValueError(f"Unknown case_id: {transcript.case_id}")
        lines = [
            self._normalized_line(line)
            for line in self.list_transcript_lines_for_transcript(transcript.transcript_id)
        ]
        if allow_preliminary:
            lines = [
                NormalizedTranscriptLine(
                    session_id=line.session_id,
                    speaker_code=line.speaker_code,
                    speaker_role=line.speaker_role,
                    start_ms=line.start_ms,
                    end_ms=line.end_ms,
                    text=line.text,
                    reviewed_text=line.reviewed_text,
                    confidence=line.confidence,
                    is_reviewed=True,
                    word_timestamps=line.word_timestamps,
                    line_id=line.line_id,
                    line_number=line.line_number,
                    flags=line.flags,
                )
                for line in lines
            ]
        source_revision = self._transcript_source_revision(transcript.transcript_id)
        chat_text = build_reviewed_chat_export(
            lines,
            metadata=ChatExportMetadata(
                session_id=session_id,
                media_filename=self._media_filename_for_session(session_id),
                child_id=case.anonymized_child_code,
                child_age_months=case.age_months,
                child_sex=case.sex,
                child_group="",
                allow_preliminary=allow_preliminary,
            ),
        )
        self.create_clinical_speech_artifact(
            session_id,
            user,
            artifact_type="preliminary_chat" if allow_preliminary else "reviewed_chat",
            freshness="preliminary" if allow_preliminary else "current",
            transcript_id=transcript.transcript_id,
            source_revision=source_revision,
            source_hash=source_revision,
            content_type="text/x-chat; charset=utf-8",
            content_text=chat_text,
            metadata={"allow_preliminary": allow_preliminary},
            review_status="awaiting_review" if allow_preliminary else "reviewed",
        )
        return chat_text

    def latest_signoff_for_target(self, target_type: SignoffTargetType, target_id: str) -> ClinicalSignoff | None:
        rows = [
            signoff
            for signoff in self.clinical_signoffs.values()
            if signoff.target_type == target_type and signoff.target_id == target_id
        ]
        if not rows:
            return None
        return replace(max(rows, key=lambda item: item.created_at))

    def rerun_feature_extraction_after_transcript_review(self, session_id: str, user: User) -> Session | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        if user.role != "admin" and session.owner_user_id != user.user_id:
            return None
        if session.transcript_id is None:
            raise ValueError("A reviewed transcript is required before feature extraction.")

        updated = replace(
            session,
            feature_extraction_status="completed",
            updated_at=self._now(),
        )
        self.sessions[session_id] = updated
        self._audit(
            "features_extracted",
            actor_user_id=user.user_id,
            target_type="session",
            target_id=session_id,
            message=f"Re-ran mock feature extraction after transcript review for {session_id}",
        )
        return replace(updated)

    def extract_features_for_session(self, session_id: str, user: User) -> ExtractedFeatures:
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session_id: {session_id}")
        case = self.cases.get(session.case_id)
        if case is None:
            raise ValueError(f"Unknown case_id: {session.case_id}")
        if user.role != "admin" and session.owner_user_id != user.user_id:
            raise PermissionError("Clinical users can only extract features for owned sessions.")
        transcript = self.get_transcript_for_session_for_user(session_id, user)
        if transcript is None or transcript.review_status != "reviewed":
            raise ValueError("A therapist-reviewed transcript is required before feature extraction.")

        now = self._now()
        normalized_lines = [
            self._normalized_line(line)
            for line in self.list_transcript_lines_for_transcript(transcript.transcript_id)
        ]
        source_revision = self._transcript_source_revision(transcript.transcript_id)
        extracted = extract_clinical_features(normalized_lines, age_months=case.age_months)
        core_features = extracted["core_features"]
        optional_indicators = {
            key: extracted["optional_indicators"].get(key, 0)
            for key in OPTIONAL_INDICATORS
        }
        self._feature_sequence += 1
        feature_row = ExtractedFeatures(
            feature_id=f"FEATURE-{self._feature_sequence:03d}",
            session_id=session_id,
            case_id=session.case_id,
            owner_user_id=session.owner_user_id,
            feature_schema_version="14-feature-schema",
            features={**core_features, **optional_indicators},
            core_features=core_features,
            optional_indicators=optional_indicators,
            source_revision=source_revision,
            source_hash=source_revision,
            created_at=now,
        )
        self.extracted_features[feature_row.feature_id] = feature_row
        self.create_clinical_speech_artifact(
            session_id,
            user,
            artifact_type="feature_output",
            freshness="current",
            transcript_id=transcript.transcript_id,
            feature_id=feature_row.feature_id,
            source_revision=source_revision,
            source_hash=source_revision,
            content_type="application/json",
            parsed_metrics=feature_row.features,
            metadata={
                "feature_schema_version": feature_row.feature_schema_version,
                "core_feature_count": len(feature_row.core_features),
                "optional_indicator_count": len(feature_row.optional_indicators),
            },
            review_status="awaiting_review",
        )
        self.sessions[session_id] = replace(
            session,
            feature_extraction_status="completed",
            updated_at=now,
        )
        self._audit(
            "features_extracted",
            actor_user_id=user.user_id,
            target_type="session",
            target_id=session_id,
            message=f"Extracted mock 14-feature schema output for {session_id}",
        )
        return replace(feature_row)

    def generate_ai_screening_output_for_session(self, session_id: str, user: User) -> AIScreeningOutput:
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session_id: {session_id}")
        if user.role != "admin" and session.owner_user_id != user.user_id:
            raise PermissionError("Clinical users can only generate AI support for owned sessions.")
        feature_row = self.get_features_for_session_for_user(session_id, user)
        if feature_row is None:
            raise ValueError("Extracted features are required before AI decision-support output.")

        score = self._mock_screening_support_score(feature_row.features)
        if score >= 0.67:
            concern_level = "moderate_concern"
        elif score >= 0.4:
            concern_level = "watchful_review"
        else:
            concern_level = "low_concern"
        top_features = self._top_contributing_features(feature_row.features)
        now = self._now()
        self._ai_output_sequence += 1
        output = AIScreeningOutput(
            output_id=f"AI-OUTPUT-{self._ai_output_sequence:03d}",
            session_id=session_id,
            case_id=session.case_id,
            owner_user_id=session.owner_user_id,
            concern_level=concern_level,
            model_version="screening-support-v0.2.0",
            screening_support_score=score,
            confidence_interval=None,
            explanation=(
                "Decision-support only. Review transcript QA, session context, "
                "and therapist notes before interpreting this output. It is not a diagnosis."
            ),
            plain_language_explanation=(
                "This output highlights speech-language patterns that may warrant closer "
                "clinical review. It is not a diagnosis."
            ),
            top_contributing_features=top_features,
            evidence_items=[
                {
                    "type": "feature",
                    "feature_key": feature,
                    "value": feature_row.features.get(feature),
                    "explanation": FEATURE_DOCS[feature].clinical_meaning,
                }
                for feature in top_features
                if feature in FEATURE_DOCS
            ],
            therapist_review_status="awaiting_review",
            differential_probabilities=self._mock_differential_probabilities(feature_row.features),
            created_at=now,
        )
        self.ai_screening_outputs[output.output_id] = output
        self._model_run_sequence += 1
        self.model_runs[f"MODEL-RUN-{self._model_run_sequence:03d}"] = ModelRun(
            model_run_id=f"MODEL-RUN-{self._model_run_sequence:03d}",
            session_id=session_id,
            case_id=session.case_id,
            owner_user_id=session.owner_user_id,
            model_card_version="prototype-screening-support-v1",
            feature_schema_version=feature_row.feature_schema_version,
            thresholds={
                "low_upper": 0.4,
                "watchful_upper": 0.67,
                "uncertainty_lower": 0.4,
                "uncertainty_upper": 0.6,
            },
            calibration_metadata={
                "validation_status": "not_validated_for_thai_children",
                "output_type": "clinical_decision_support",
            },
            created_at=now,
        )
        self.sessions[session_id] = replace(
            session,
            ai_analysis_status="completed",
            report_status="pending",
            updated_at=now,
        )
        self._audit(
            "ai_output_generated",
            actor_user_id=user.user_id,
            target_type="ai_screening_output",
            target_id=output.output_id,
            message=f"Generated mock AI decision-support output for {session_id}",
        )
        return replace(output)

    def generate_reference_cohort_similarity_for_session(
        self,
        session_id: str,
        user: User,
        *,
        inference_status: str = "preliminary",
    ) -> AIScreeningOutput:
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session_id: {session_id}")
        if user.role != "admin" and session.owner_user_id != user.user_id:
            raise PermissionError("Clinical users can only generate similarity for owned sessions.")
        feature_row = self.get_features_for_session_for_user(session_id, user)
        if feature_row is None:
            feature_row = self.extract_features_for_session(session_id, user)

        now = self._now()
        try:
            result = predict_reference_cohort_similarity(
                feature_row.core_features or feature_row.features,
                inference_status=inference_status,
            )
            report_eligible = inference_status == "reviewed"
            therapist_review_status = "reviewed" if report_eligible else "awaiting_review"
            model_version = result["model_version"]
            cohort_probabilities = result["reference_cohort_probabilities"]
            most_similar = result["most_similar_reference_cohort"]
            similarity_probability = result["similarity_probability"]
            top_feature_items = result.get("top_contributing_features", [])
            plain_language = result["plain_language_explanation"]
            safety_warnings = result.get("safety_warnings", [])
        except Exception as exc:  # noqa: BLE001
            report_eligible = False
            therapist_review_status = "needs_correction"
            model_version = "unavailable"
            cohort_probabilities = {}
            most_similar = None
            similarity_probability = None
            top_feature_items = []
            plain_language = "Reference cohort similarity is unavailable for this transcript."
            safety_warnings = [{"code": "SIMILARITY_UNAVAILABLE", "message": str(exc)}]

        self._ai_output_sequence += 1
        output = AIScreeningOutput(
            output_id=f"AI-OUTPUT-{self._ai_output_sequence:03d}",
            session_id=session_id,
            case_id=session.case_id,
            owner_user_id=session.owner_user_id,
            concern_level="review_support",
            model_version=model_version,
            screening_support_score=similarity_probability,
            confidence_interval=None,
            explanation=(
                "Reference cohort similarity is clinical decision support only. "
                "It is not a diagnosis and must be interpreted with transcript QA and session context."
            ),
            plain_language_explanation=plain_language,
            top_contributing_features=[
                item["feature_key"] if isinstance(item, dict) else str(item)
                for item in top_feature_items
            ],
            evidence_items=[
                item for item in top_feature_items if isinstance(item, dict)
            ],
            therapist_review_status=therapist_review_status,
            differential_probabilities=cohort_probabilities,
            output_kind="reference_cohort_similarity",
            inference_status=inference_status,
            reference_cohort_probabilities=cohort_probabilities,
            most_similar_reference_cohort=most_similar,
            similarity_probability=similarity_probability,
            report_eligible=report_eligible,
            safety_warnings=safety_warnings,
            created_at=now,
        )
        self.ai_screening_outputs[output.output_id] = output

        self._model_run_sequence += 1
        self.model_runs[f"MODEL-RUN-{self._model_run_sequence:03d}"] = ModelRun(
            model_run_id=f"MODEL-RUN-{self._model_run_sequence:03d}",
            session_id=session_id,
            case_id=session.case_id,
            owner_user_id=session.owner_user_id,
            model_card_version=model_version,
            feature_schema_version=feature_row.feature_schema_version,
            thresholds={"report_eligible": float(report_eligible)},
            calibration_metadata={
                "output_kind": "reference_cohort_similarity",
                "inference_status": inference_status,
                "report_eligible": int(report_eligible),
            },
            created_at=now,
        )
        similarity_unavailable = any(
            warning.get("code") == "SIMILARITY_UNAVAILABLE"
            for warning in safety_warnings
            if isinstance(warning, dict)
        )
        self.sessions[session_id] = replace(
            session,
            ai_analysis_status="failed" if similarity_unavailable else "completed",
            report_status="pending",
            updated_at=now,
        )
        self._audit(
            "reference_cohort_similarity_generated",
            actor_user_id=user.user_id,
            target_type="ai_screening_output",
            target_id=output.output_id,
            message=f"Generated {inference_status} reference cohort similarity for {session_id}.",
        )
        return replace(output)

    def progress_summary_for_case(self, case_id: str, user: User) -> dict:
        case = self.get_case_for_user(case_id, user)
        if case is None:
            raise PermissionError("Clinical users can only summarize owned cases.")

        sessions = list(reversed(self.list_sessions_for_case_for_user(case_id, user)))
        feature_rows_by_session = {
            feature.session_id: feature
            for feature in self.extracted_features.values()
            if feature.case_id == case_id
        }
        ai_outputs_by_session: dict[str, AIScreeningOutput] = {}
        for output in sorted(
            (item for item in self.ai_screening_outputs.values() if item.case_id == case_id),
            key=lambda item: item.created_at,
        ):
            if (
                output.output_kind == "reference_cohort_similarity"
                and (output.inference_status != "reviewed" or not output.report_eligible)
            ):
                continue
            ai_outputs_by_session[output.session_id] = output
        goals = self.list_goals_for_case_for_user(case_id, user)
        timeline = [
            {
                "session_id": session.session_id,
                "session_date": session.session_date,
                "screening_support_score": (
                    ai_outputs_by_session[session.session_id].screening_support_score
                    if session.session_id in ai_outputs_by_session
                    else None
                ),
                "feature_extraction_status": session.feature_extraction_status,
                "therapist_review_status": session.therapist_review_status,
                "notes": session.notes,
                "ai_explanation": (
                    ai_outputs_by_session[session.session_id].explanation
                    if session.session_id in ai_outputs_by_session
                    else ""
                ),
                "evidence_items": (
                    ai_outputs_by_session[session.session_id].evidence_items
                    if session.session_id in ai_outputs_by_session
                    else []
                ),
            }
            for session in sessions
        ]
        feature_trends = self._feature_trends(sessions, feature_rows_by_session)
        before_after_radar = self._before_after_radar(sessions, feature_rows_by_session)
        completed = sum(goal.status == "completed" for goal in goals)
        active = sum(goal.status == "active" for goal in goals)
        paused = sum(goal.status == "paused" for goal in goals)
        return {
            "case_id": case.case_id,
            "anonymized_child_code": case.anonymized_child_code,
            "n_sessions": len(sessions),
            "score_timeline": timeline,
            "feature_trends": feature_trends,
            "therapy_goal_progress": {
                "total": len(goals),
                "active": active,
                "paused": paused,
                "completed": completed,
            },
            "before_after_radar": before_after_radar,
            "consent_status": case.consent_status,
            "anonymization_status": case.anonymization_status,
            "safety_disclaimer": SAFETY_DISCLAIMER,
        }

    def generate_progress_report_for_case(self, case_id: str, user: User) -> Report:
        case = self.get_case_for_user(case_id, user)
        if case is None:
            raise PermissionError("Clinical users can only generate reports for owned cases.")
        summary = self.progress_summary_for_case(case_id, user)
        now = self._now()
        self._report_sequence += 1
        report = Report(
            report_id=f"REPORT-{self._report_sequence:03d}",
            case_id=case.case_id,
            owner_user_id=case.owner_user_id,
            report_type="progress",
            title=f"Progress Report: {case.anonymized_child_code}",
            content_markdown=self._render_progress_report_markdown(case, summary),
            export_status="completed",
            created_at=now,
        )
        self.reports[report.report_id] = report
        self._audit(
            "report_exported",
            actor_user_id=user.user_id,
            target_type="report",
            target_id=report.report_id,
            message=f"Generated mock progress report {report.report_id} for {case.case_id}",
        )
        return replace(report)

    def dashboard_summary(self, user: User) -> dict[str, int]:
        cases = self.list_cases_for_user(user)
        case_ids = {case.case_id for case in cases}
        sessions = [
            session for session in self.list_sessions_for_user(user)
            if session.case_id in case_ids
        ]
        return {
            "active_cases": len(cases),
            "sessions_awaiting_transcript_review": sum(
                session.therapist_review_status == "awaiting_review"
                for session in sessions
            ),
            "sessions_awaiting_report_generation": sum(
                session.report_status == "pending"
                for session in sessions
            ),
            "high_review_priority_cases": sum(
                session.therapist_review_status in {"awaiting_review", "needs_correction"}
                for session in sessions
            ),
            "uploaded_files": len(self.list_audio_files_for_user(user)),
        }

    def list_audit_logs_for_user(self, user: User) -> list[AuditLog]:
        if user.role != "admin":
            return []
        rows = self.audit_logs
        return [replace(log) for log in sorted(rows, key=lambda item: item.created_at, reverse=True)]

    def _seed(self) -> None:
        created = datetime(2026, 5, 1, tzinfo=timezone.utc)
        seed_users = [
            User("user_therapist_001", "Dr. Anya Therapist", "therapist@example.test", "therapist", "Mock Speech Clinic", created),
            User("user_clinician_001", "Dr. Ben Clinician", "clinician@example.test", "clinician", "Mock Speech Clinic", created),
            User("user_admin_001", "Research Admin", "admin@example.test", "admin", "Prototype Admin", created),
        ]
        for user in seed_users:
            self.users[user.user_id] = user
            self._password_by_email[user.email.lower()] = "demo-password"

        for case in [
            ChildCase(
                case_id="CASE-001",
                owner_user_id="user_therapist_001",
                anonymized_child_code="CHI-A01",
                age_months=48,
                sex="not_specified",
                primary_concerns="Limited spontaneous utterances; parent reports reduced social initiation.",
                external_clinical_status="under_evaluation",
                consent_status="granted",
                anonymization_status="anonymized",
                notes="Mock clinical case. No real child identifiers.",
                created_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
            ),
            ChildCase(
                case_id="CASE-002",
                owner_user_id="user_therapist_001",
                anonymized_child_code="CHI-A02",
                age_months=60,
                sex="not_specified",
                primary_concerns="Transcript review pending after mock therapy session.",
                external_clinical_status="not_provided",
                consent_status="pending",
                anonymization_status="anonymized",
                notes="Mock clinical case. No real child identifiers.",
                created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
            ),
            ChildCase(
                case_id="CASE-003",
                owner_user_id="user_clinician_001",
                anonymized_child_code="CHI-B01",
                age_months=54,
                sex="not_specified",
                primary_concerns="Monitoring language sample quality over repeated sessions.",
                external_clinical_status="external_non_asd_recorded",
                consent_status="granted",
                anonymization_status="anonymized",
                notes="Mock clinical case. No real child identifiers.",
                created_at=datetime(2026, 5, 4, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 4, tzinfo=timezone.utc),
            ),
        ]:
            self.cases[case.case_id] = case
        self._case_sequence = len(self.cases)

        for consent in [
            ConsentRecord(
                consent_id="CONSENT-001",
                case_id="CASE-001",
                owner_user_id="user_therapist_001",
                recorded_by_user_id="user_therapist_001",
                audio_permission=True,
                transcript_permission=True,
                notes="Seeded consent for secure pilot upload workflow.",
                created_at=datetime(2026, 5, 2, 9, tzinfo=timezone.utc),
            ),
            ConsentRecord(
                consent_id="CONSENT-002",
                case_id="CASE-003",
                owner_user_id="user_clinician_001",
                recorded_by_user_id="user_clinician_001",
                audio_permission=True,
                transcript_permission=True,
                notes="Seeded consent for clinician role workflow.",
                created_at=datetime(2026, 5, 4, 9, tzinfo=timezone.utc),
            ),
        ]:
            self.consent_records[consent.consent_id] = consent
        self._consent_sequence = len(self.consent_records)

        for session in [
            Session(
                session_id="SESSION-001",
                case_id="CASE-001",
                owner_user_id="user_therapist_001",
                session_date="2026-05-05",
                session_type="free_play",
                feature_extraction_status="completed",
                ai_analysis_status="completed",
                therapist_review_status="awaiting_review",
                report_status="pending",
                notes="Seeded mock session; no uploaded file in Phase 1.",
                created_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
            ),
            Session(
                session_id="SESSION-002",
                case_id="CASE-002",
                owner_user_id="user_therapist_001",
                session_date="2026-05-06",
                session_type="therapy_session",
                feature_extraction_status="not_started",
                ai_analysis_status="not_started",
                therapist_review_status="not_started",
                report_status="not_started",
                notes="Seeded mock session; create-session workflow deferred.",
                created_at=datetime(2026, 5, 6, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 6, tzinfo=timezone.utc),
            ),
            Session(
                session_id="SESSION-003",
                case_id="CASE-003",
                owner_user_id="user_clinician_001",
                session_date="2026-05-07",
                session_type="structured_assessment",
                feature_extraction_status="completed",
                ai_analysis_status="completed",
                therapist_review_status="needs_correction",
                report_status="pending",
                notes="Seeded mock session; transcript correction deferred.",
                created_at=datetime(2026, 5, 7, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 7, tzinfo=timezone.utc),
            ),
        ]:
            self.sessions[session.session_id] = session
        self._session_sequence = len(self.sessions)

        seed_audio = AudioFile(
            audio_file_id="AUDIO-001",
            owner_user_id="user_therapist_001",
            case_id="CASE-001",
            session_id="SESSION-001",
            original_filename="session_sample.wav",
            stored_filename="CASE-001_SESSION-001_AUDIO-001.wav",
            file_type="wav",
            file_size=18400000,
            upload_time=datetime(2026, 5, 5, 9, 15, tzinfo=timezone.utc),
            processing_status="completed",
        )
        self.audio_files[seed_audio.audio_file_id] = seed_audio
        seed_file_object = FileObject(
            file_object_id="FILEOBJ-001",
            audio_file_id=seed_audio.audio_file_id,
            case_id=seed_audio.case_id,
            session_id=seed_audio.session_id,
            owner_user_id=seed_audio.owner_user_id,
            storage_key=f"private/{seed_audio.owner_user_id}/{seed_audio.case_id}/{seed_audio.session_id}/{seed_audio.stored_filename}",
            mime_type="audio/wav",
            encryption_status="verified",
            retention_delete_after=datetime(2027, 5, 5, tzinfo=timezone.utc),
            created_at=datetime(2026, 5, 5, 9, 15, tzinfo=timezone.utc),
        )
        self.file_objects[seed_file_object.file_object_id] = seed_file_object
        self.audio_files[seed_audio.audio_file_id] = replace(
            self.audio_files[seed_audio.audio_file_id],
            storage_mode="secure_private",
            file_object_id=seed_file_object.file_object_id,
        )
        self._file_object_sequence = len(self.file_objects)
        self.sessions["SESSION-001"] = replace(
            self.sessions["SESSION-001"],
            audio_file_id=seed_audio.audio_file_id,
        )
        self._audio_file_sequence = len(self.audio_files)

        seed_transcript = Transcript(
            transcript_id="TRANSCRIPT-001",
            session_id="SESSION-001",
            case_id="CASE-001",
            owner_user_id="user_therapist_001",
            transcript_text=self._mock_chat_text("CHI-A01", 48, "not_specified"),
            review_status="awaiting_review",
            qa_status="pass",
            qa_score=100,
            qa_issues=[],
            created_at=datetime(2026, 5, 5, 9, 30, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 5, 9, 30, tzinfo=timezone.utc),
        )
        self.transcripts[seed_transcript.transcript_id] = seed_transcript
        self._replace_transcript_lines(seed_transcript)
        self.sessions["SESSION-001"] = replace(
            self.sessions["SESSION-001"],
            transcript_id=seed_transcript.transcript_id,
        )
        self._transcript_sequence = len(self.transcripts)
        seed_core_features = self._mock_features_from_transcript(
            self.cases["CASE-001"],
            seed_transcript.transcript_text,
        )
        seed_optional_indicators = self._mock_optional_indicators_from_transcript(seed_transcript.transcript_text)
        seed_features = ExtractedFeatures(
            feature_id="FEATURE-001",
            session_id="SESSION-001",
            case_id="CASE-001",
            owner_user_id="user_therapist_001",
            feature_schema_version="14-feature-schema",
            features={**seed_core_features, **seed_optional_indicators},
            core_features=seed_core_features,
            optional_indicators=seed_optional_indicators,
            created_at=datetime(2026, 5, 5, 9, 35, tzinfo=timezone.utc),
        )
        self.extracted_features[seed_features.feature_id] = seed_features
        self._feature_sequence = len(self.extracted_features)
        seed_ai = AIScreeningOutput(
            output_id="AI-OUTPUT-001",
            session_id="SESSION-001",
            case_id="CASE-001",
            owner_user_id="user_therapist_001",
            concern_level="moderate_concern",
            model_version="screening-support-v0.2.0",
            screening_support_score=0.68,
            confidence_interval=None,
            explanation="Seeded prototype support output for mock dashboard review. It is not a diagnosis.",
            plain_language_explanation="This output highlights speech-language patterns for clinician review. It is not a diagnosis.",
            top_contributing_features=["unintelligible_ratio", "echolalia_ratio", "ttr"],
            evidence_items=[
                {
                    "type": "feature",
                    "feature_key": "unintelligible_ratio",
                    "value": seed_features.features["unintelligible_ratio"],
                    "explanation": FEATURE_DOCS["unintelligible_ratio"].clinical_meaning,
                },
                {
                    "type": "feature",
                    "feature_key": "echolalia_ratio",
                    "value": seed_features.features["echolalia_ratio"],
                    "explanation": FEATURE_DOCS["echolalia_ratio"].clinical_meaning,
                },
                {
                    "type": "feature",
                    "feature_key": "ttr",
                    "value": seed_features.features["ttr"],
                    "explanation": FEATURE_DOCS["ttr"].clinical_meaning,
                },
            ],
            differential_probabilities={"ASD": 0.68, "DD": 0.20, "TD": 0.12},
            created_at=datetime(2026, 5, 5, 9, 40, tzinfo=timezone.utc),
        )
        self.ai_screening_outputs[seed_ai.output_id] = seed_ai
        self._ai_output_sequence = len(self.ai_screening_outputs)

        for goal in [
            TherapyGoal(
                goal_id="GOAL-001",
                case_id="CASE-001",
                owner_user_id="user_therapist_001",
                goal_text="Increase spontaneous two-word utterances during play.",
                status="active",
                created_at=datetime(2026, 5, 5, 10, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 5, 10, tzinfo=timezone.utc),
            ),
            TherapyGoal(
                goal_id="GOAL-002",
                case_id="CASE-002",
                owner_user_id="user_therapist_001",
                goal_text="Improve transcript-ready session sampling consistency.",
                status="active",
                created_at=datetime(2026, 5, 6, 10, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 6, 10, tzinfo=timezone.utc),
            ),
            TherapyGoal(
                goal_id="GOAL-003",
                case_id="CASE-003",
                owner_user_id="user_clinician_001",
                goal_text="Monitor intelligibility and speaker-label quality.",
                status="active",
                created_at=datetime(2026, 5, 7, 10, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 7, 10, tzinfo=timezone.utc),
            ),
            TherapyGoal(
                goal_id="GOAL-004",
                case_id="CASE-001",
                owner_user_id="user_therapist_001",
                goal_text="Improve response to open WH-questions.",
                status="completed",
                created_at=datetime(2026, 5, 8, 10, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 18, 10, tzinfo=timezone.utc),
            ),
        ]:
            self.therapy_goals[goal.goal_id] = goal
        self._goal_sequence = len(self.therapy_goals)

        for note in [
            TherapistNote(
                note_id="NOTE-001",
                case_id="CASE-001",
                owner_user_id="user_therapist_001",
                note_text="Parent reports more requesting at home; verify in next session.",
                created_at=datetime(2026, 5, 6, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 6, tzinfo=timezone.utc),
            ),
            TherapistNote(
                note_id="NOTE-002",
                case_id="CASE-003",
                owner_user_id="user_clinician_001",
                note_text="Correct low-confidence child line before interpreting features.",
                session_id="SESSION-003",
                created_at=datetime(2026, 5, 7, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 7, tzinfo=timezone.utc),
            ),
        ]:
            self.therapist_notes[note.note_id] = note
        self._note_sequence = len(self.therapist_notes)

    def _audit(
        self,
        event_type: str,
        *,
        actor_user_id: str,
        target_type: str,
        target_id: str,
        message: str,
    ) -> None:
        self._audit_sequence += 1
        self.audit_logs.append(
            AuditLog(
                audit_id=f"AUDIT-{self._audit_sequence:04d}",
                event_type=event_type,
                actor_user_id=actor_user_id,
                target_type=target_type,
                target_id=target_id,
                message=message,
                created_at=self._now(),
            )
        )

    def _replace_transcript_lines(self, transcript: Transcript) -> None:
        for line_id in [
            line_id
            for line_id, line in self.transcript_lines.items()
            if line.transcript_id == transcript.transcript_id
        ]:
            del self.transcript_lines[line_id]

        for parsed in parse_chat_to_lines(transcript.transcript_text, session_id=transcript.session_id):
            raw_index = parsed.line_number or 0
            line_id = f"{transcript.transcript_id}_L{raw_index:04d}"
            self.transcript_lines[line_id] = TranscriptLine(
                line_id=line_id,
                transcript_id=transcript.transcript_id,
                session_id=transcript.session_id,
                case_id=transcript.case_id,
                owner_user_id=transcript.owner_user_id,
                line_number=raw_index,
                speaker_code=parsed.speaker_code,
                speaker_role=parsed.speaker_role,
                utterance_text=parsed.text,
                start_time=(parsed.start_ms / 1000.0) if parsed.start_ms is not None else None,
                end_time=(parsed.end_ms / 1000.0) if parsed.end_ms is not None else None,
                start_ms=parsed.start_ms,
                end_ms=parsed.end_ms,
                confidence=1.0,
                updated_at=transcript.updated_at,
            )

    def _normalized_line(self, line: TranscriptLine) -> NormalizedTranscriptLine:
        return NormalizedTranscriptLine(
            session_id=line.session_id,
            speaker_code=line.speaker_code,
            speaker_role=line.speaker_role or speaker_role_for_code(line.speaker_code),
            start_ms=line.start_ms,
            end_ms=line.end_ms,
            text=line.utterance_text,
            reviewed_text=line.reviewed_text,
            confidence=line.confidence,
            is_reviewed=line.reviewed,
            word_timestamps=[],
            line_id=line.line_id,
            line_number=line.line_number,
            flags=line.flags,
        )

    def _media_filename_for_session(self, session_id: str) -> str | None:
        session = self.sessions.get(session_id)
        if session and session.audio_file_id and session.audio_file_id in self.audio_files:
            return self.audio_files[session.audio_file_id].stored_filename
        return None

    @staticmethod
    def _validated_file_type(original_filename: str) -> str:
        filename = Path(original_filename).name
        if not filename or "." not in filename:
            raise ValueError("A filename with an allowed extension is required.")
        file_type = filename.rsplit(".", 1)[-1].lower()
        if file_type not in ALLOWED_AUDIO_FILE_TYPES:
            allowed = ", ".join(ALLOWED_AUDIO_FILE_TYPES)
            raise ValueError(f"Unsupported file type .{file_type}. Allowed: {allowed}.")
        return file_type

    @staticmethod
    def _validated_transcript_type(original_filename: str) -> str:
        filename = Path(original_filename).name
        if not filename or "." not in filename:
            raise ValueError("A .cha transcript filename is required.")
        file_type = filename.rsplit(".", 1)[-1].lower()
        if file_type not in ALLOWED_TRANSCRIPT_FILE_TYPES:
            raise ValueError("Unsupported transcript file type. Allowed: cha.")
        return file_type

    @staticmethod
    def _review_status_from_qa(qa_status: str) -> str:
        if qa_status == "fail":
            return "needs_correction"
        return "awaiting_review"

    @staticmethod
    def _mock_chat_text(child_id: str, age_months: int, sex: str) -> str:
        age_years = age_months // 12
        age_remainder = age_months % 12
        chat_sex = "male" if sex == "male" else "female" if sex == "female" else ""
        return f"""@Begin
@Languages:\teng
@Participants:\tCHI Child Target_Child, MOT Mother Mother
@ID:\teng|Mock|CHI|{age_years};{age_remainder:02d}.00|{chat_sex}|||Target_Child|||
@ID:\teng|Mock|MOT|||||Mother|||
*CHI:\twant car .
*MOT:\twhich car do you want ?
*CHI:\tred car .
@End
"""

    @staticmethod
    def _mock_features_from_transcript(case: ChildCase, transcript_text: str) -> dict[str, float]:
        child_lines = [
            line.split(":", 1)[1].strip()
            for line in transcript_text.splitlines()
            if line.startswith("*CHI:")
        ]
        words = [
            token.strip(".,?!").lower()
            for line in child_lines
            for token in line.split()
            if token.strip(".,?!")
        ]
        total_utterances = max(len(child_lines), 1)
        total_words = len(words)
        unique_words = len(set(words))
        unintelligible_count = sum("xxx" in line or "yyy" in line for line in child_lines)
        zero_count = sum(line.strip() in {"0 .", "0."} for line in child_lines)
        echolalia_count = sum("[/]" in line for line in child_lines)
        pronoun_reversal_count = sum(" you " in f" {line.lower()} " and " i " in f" {line.lower()} " for line in child_lines)
        feature_values = {
            "age_months": float(case.age_months),
            "total_utterances": float(total_utterances),
            "mlu": round(total_words / total_utterances, 3),
            "mluw": round(total_words / total_utterances, 3),
            "ttr": round(unique_words / max(total_words, 1), 3),
            "total_words": float(total_words),
            "unintelligible_count": float(unintelligible_count),
            "unintelligible_ratio": round(unintelligible_count / total_utterances, 3),
            "zero_vocalization_count": float(zero_count),
            "nonverbal_vocalization_count": float(sum("&=" in line for line in child_lines)),
            "question_ratio": round(sum("?" in line for line in child_lines) / total_utterances, 3),
            "echolalia_count": float(echolalia_count),
            "echolalia_ratio": round(echolalia_count / total_utterances, 3),
            "pronoun_reversal_count": float(pronoun_reversal_count),
        }
        return {feature: feature_values[feature] for feature in FEATURES}

    @staticmethod
    def _mock_optional_indicators_from_transcript(transcript_text: str) -> dict[str, float]:
        lines = [
            line.split(":", 1)
            for line in transcript_text.splitlines()
            if line.startswith("*") and ":" in line
        ]
        speaker_codes = [speaker.strip("*").strip() for speaker, _text in lines]
        child_lines = [text.strip() for speaker, text in lines if speaker.strip("*").strip() == "CHI"]
        restricted_terms = {
            "train",
            "trains",
            "wheel",
            "wheels",
            "number",
            "numbers",
            "letter",
            "letters",
            "map",
            "maps",
            "dinosaur",
            "dinosaurs",
            "schedule",
            "schedules",
        }
        child_word_tokens = [
            token.strip(".,?!").lower()
            for line in child_lines
            for token in line.split()
            if token.strip(".,?!")
        ]
        total_utterances = max(len(child_lines), 1)
        turns = sum(1 for index in range(len(speaker_codes) - 1) if speaker_codes[index] != speaker_codes[index + 1])
        values = {
            "pause_count": 0.0,
            "pause_ratio": 0.0,
            "therapist_utterances": float(sum(code in {"INV", "CLI"} for code in speaker_codes)),
            "caregiver_utterances": float(sum(code in {"MOT", "FAT", "PAR"} for code in speaker_codes)),
            "turn_taking_count": float(turns),
            "response_latency_avg": 0.0,
            "restricted_interest_words": float(sum(token in restricted_terms for token in child_word_tokens)),
        }
        return {feature: values[feature] for feature in OPTIONAL_INDICATORS}

    @staticmethod
    def _mock_screening_support_score(features: dict[str, float]) -> float:
        feature_keys = [
            "age_months", "total_utterances", "mlu", "mluw", "ttr", "total_words",
            "unintelligible_count", "unintelligible_ratio", "zero_vocalization_count",
            "nonverbal_vocalization_count", "question_ratio", "echolalia_count",
            "echolalia_ratio", "pronoun_reversal_count"
        ]
        
        medians = {
            "age_months": 48.215, "total_utterances": 135.0, "mlu": 2.38, "mluw": 2.395,
            "ttr": 0.3896, "total_words": 314.5, "unintelligible_count": 9.0,
            "unintelligible_ratio": 0.06435, "zero_vocalization_count": 0.0,
            "nonverbal_vocalization_count": 7.5, "question_ratio": 0.03125,
            "echolalia_count": 2.0, "echolalia_ratio": 0.01335, "pronoun_reversal_count": 0.0
        }
        
        means = {
            "age_months": 49.3177869, "total_utterances": 143.418033, "mlu": 2.29769672,
            "mluw": 2.40151639, "ttr": 0.366644262, "total_words": 324.860656,
            "unintelligible_count": 12.3196721, "unintelligible_ratio": 0.0968614754,
            "zero_vocalization_count": 0.581967213, "nonverbal_vocalization_count": 19.8770492,
            "question_ratio": 0.0555581967, "echolalia_count": 3.62295082,
            "echolalia_ratio": 0.0214122951, "pronoun_reversal_count": 0.0655737705
        }
        
        scales = {
            "age_months": 14.1992667, "total_utterances": 72.1617991, "mlu": 1.37620052,
            "mluw": 1.06738829, "ttr": 0.104924007, "total_words": 228.125408,
            "unintelligible_count": 12.034286, "unintelligible_ratio": 0.0960321663,
            "zero_vocalization_count": 2.07182569, "nonverbal_vocalization_count": 27.7221513,
            "question_ratio": 0.0615545644, "echolalia_count": 5.97580898,
            "echolalia_ratio": 0.0287674383, "pronoun_reversal_count": 0.247535555
        }
        
        coefs = {
            "age_months": 1.78276795, "total_utterances": -0.07146712, "mlu": -0.39394373,
            "mluw": -0.27608502, "ttr": -0.22178841, "total_words": -0.1965565,
            "unintelligible_count": 0.46093466, "unintelligible_ratio": 0.0826481,
            "zero_vocalization_count": -0.25510421, "nonverbal_vocalization_count": 0.4611388,
            "question_ratio": -1.39286885, "echolalia_count": 0.50644538,
            "echolalia_ratio": 0.48021253, "pronoun_reversal_count": -0.53491666
        }
        
        intercept = 0.31832555
        
        import math
        z = intercept
        for k in feature_keys:
            val = features.get(k)
            if val is None or math.isnan(val):
                val = medians[k]
            scaled = (val - means[k]) / scales[k]
            z += scaled * coefs[k]
            
        proba = 1.0 / (1.0 + math.exp(-z))
        return round(proba, 2)

    @staticmethod
    def _mock_differential_probabilities(features: dict[str, float]) -> dict[str, float]:
        feature_keys = [
            "age_months", "total_utterances", "mlu", "mluw", "ttr", "total_words",
            "unintelligible_count", "unintelligible_ratio", "zero_vocalization_count",
            "nonverbal_vocalization_count", "question_ratio", "echolalia_count",
            "echolalia_ratio", "pronoun_reversal_count"
        ]
        medians = {
            "age_months": 48.215, "total_utterances": 135.0, "mlu": 2.38, "mluw": 2.395,
            "ttr": 0.3896, "total_words": 314.5, "unintelligible_count": 9.0,
            "unintelligible_ratio": 0.06435, "zero_vocalization_count": 0.0,
            "nonverbal_vocalization_count": 7.5, "question_ratio": 0.03125,
            "echolalia_count": 2.0, "echolalia_ratio": 0.01335, "pronoun_reversal_count": 0.0
        }
        means = {
            "age_months": 49.3177869, "total_utterances": 143.418033, "mlu": 2.29769672,
            "mluw": 2.40151639, "ttr": 0.366644262, "total_words": 324.860656,
            "unintelligible_count": 12.3196721, "unintelligible_ratio": 0.0968614754,
            "zero_vocalization_count": 0.581967213, "nonverbal_vocalization_count": 19.8770492,
            "question_ratio": 0.0555581967, "echolalia_count": 3.62295082,
            "echolalia_ratio": 0.0214122951, "pronoun_reversal_count": 0.0655737705
        }
        scales = {
            "age_months": 14.1992667, "total_utterances": 72.1617991, "mlu": 1.37620052,
            "mluw": 1.06738829, "ttr": 0.104924007, "total_words": 228.125408,
            "unintelligible_count": 12.034286, "unintelligible_ratio": 0.0960321663,
            "zero_vocalization_count": 2.07182569, "nonverbal_vocalization_count": 27.7221513,
            "question_ratio": 0.0615545644, "echolalia_count": 5.97580898,
            "echolalia_ratio": 0.0287674383, "pronoun_reversal_count": 0.247535555
        }
        
        multiclassCoefs = {
            "ASD": { "intercept": 1.23930257, "age_months": 1.23811430, "total_utterances": 0.01925123, "mlu": -0.34435076, "mluw": -0.22595731, "ttr": -0.54580713, "total_words": -0.30171761, "unintelligible_count": 0.39521484, "unintelligible_ratio": 0.12235206, "zero_vocalization_count": 0.19276645, "nonverbal_vocalization_count": 0.40237295, "question_ratio": -1.09344521, "echolalia_count": 0.56915281, "echolalia_ratio": 0.24874344, "pronoun_reversal_count": -0.44519369 },
            "DD": { "intercept": -1.13479453, "age_months": 1.02134742, "total_utterances": 0.05913869, "mlu": 0.06479095, "mluw": -0.08064159, "ttr": 0.65606793, "total_words": 0.32108373, "unintelligible_count": 0.34958220, "unintelligible_ratio": -0.24009617, "zero_vocalization_count": -1.06036380, "nonverbal_vocalization_count": -0.76784960, "question_ratio": 0.86319480, "echolalia_count": -0.64516503, "echolalia_ratio": 0.34307443, "pronoun_reversal_count": 0.35196894 },
            "TD": { "intercept": -0.10450804, "age_months": -2.25946172, "total_utterances": -0.07838991, "mlu": 0.27955981, "mluw": 0.30659890, "ttr": -0.11026080, "total_words": -0.01936612, "unintelligible_count": -0.74479704, "unintelligible_ratio": 0.11774411, "zero_vocalization_count": 0.86759735, "nonverbal_vocalization_count": 0.36547666, "question_ratio": 0.23025042, "echolalia_count": 0.07601222, "echolalia_ratio": -0.59181787, "pronoun_reversal_count": 0.09322475 }
        }
        
        import math
        zs = {}
        for cls, coef in multiclassCoefs.items():
            z = coef["intercept"]
            for k in feature_keys:
                val = features.get(k)
                if val is None or math.isnan(val):
                    val = medians[k]
                scaled = (val - means[k]) / scales[k]
                z += scaled * coef.get(k, 0.0)
            zs[cls] = z
            
        exp_sum = sum(math.exp(z_val) for z_val in zs.values())
        probas = {}
        for cls, z_val in zs.items():
            probas[cls] = round(math.exp(z_val) / exp_sum, 2)
            
        return probas

    @staticmethod
    def _top_contributing_features(features: dict[str, float]) -> list[str]:
        feature_keys = [
            "age_months", "total_utterances", "mlu", "mluw", "ttr", "total_words",
            "unintelligible_count", "unintelligible_ratio", "zero_vocalization_count",
            "nonverbal_vocalization_count", "question_ratio", "echolalia_count",
            "echolalia_ratio", "pronoun_reversal_count"
        ]
        
        medians = {
            "age_months": 48.215, "total_utterances": 135.0, "mlu": 2.38, "mluw": 2.395,
            "ttr": 0.3896, "total_words": 314.5, "unintelligible_count": 9.0,
            "unintelligible_ratio": 0.06435, "zero_vocalization_count": 0.0,
            "nonverbal_vocalization_count": 7.5, "question_ratio": 0.03125,
            "echolalia_count": 2.0, "echolalia_ratio": 0.01335, "pronoun_reversal_count": 0.0
        }
        
        means = {
            "age_months": 49.3177869, "total_utterances": 143.418033, "mlu": 2.29769672,
            "mluw": 2.40151639, "ttr": 0.366644262, "total_words": 324.860656,
            "unintelligible_count": 12.3196721, "unintelligible_ratio": 0.0968614754,
            "zero_vocalization_count": 0.581967213, "nonverbal_vocalization_count": 19.8770492,
            "question_ratio": 0.0555581967, "echolalia_count": 3.62295082,
            "echolalia_ratio": 0.0214122951, "pronoun_reversal_count": 0.0655737705
        }
        
        scales = {
            "age_months": 14.1992667, "total_utterances": 72.1617991, "mlu": 1.37620052,
            "mluw": 1.06738829, "ttr": 0.104924007, "total_words": 228.125408,
            "unintelligible_count": 12.034286, "unintelligible_ratio": 0.0960321663,
            "zero_vocalization_count": 2.07182569, "nonverbal_vocalization_count": 27.7221513,
            "question_ratio": 0.0615545644, "echolalia_count": 5.97580898,
            "echolalia_ratio": 0.0287674383, "pronoun_reversal_count": 0.247535555
        }
        
        coefs = {
            "age_months": 1.78276795, "total_utterances": -0.07146712, "mlu": -0.39394373,
            "mluw": -0.27608502, "ttr": -0.22178841, "total_words": -0.1965565,
            "unintelligible_count": 0.46093466, "unintelligible_ratio": 0.0826481,
            "zero_vocalization_count": -0.25510421, "nonverbal_vocalization_count": 0.4611388,
            "question_ratio": -1.39286885, "echolalia_count": 0.50644538,
            "echolalia_ratio": 0.48021253, "pronoun_reversal_count": -0.53491666
        }
        
        contributions = {}
        import math
        for k in feature_keys:
            val = features.get(k)
            if val is None or math.isnan(val):
                val = medians[k]
            scaled = (val - means[k]) / scales[k]
            contributions[k] = scaled * coefs[k]
            
        sorted_contribs = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
        return [k for k, val in sorted_contribs[:3]]

    @staticmethod
    def _feature_trends(
        sessions: list[Session],
        feature_rows_by_session: dict[str, ExtractedFeatures],
    ) -> dict[str, dict]:
        rows = [
            feature_rows_by_session[session.session_id]
            for session in sessions
            if session.session_id in feature_rows_by_session
        ]
        trends: dict[str, dict] = {}
        for metric in [item for item in REPORT_METRICS if item in FEATURES]:
            values = [
                row.features.get(metric)
                for row in rows
                if row.features.get(metric) is not None
            ]
            if not values:
                continue
            first = float(values[0])
            last = float(values[-1])
            delta = round(last - first, 4)
            direction = METRIC_DIRECTIONS.get(metric, 1)
            trends[metric] = {
                "first": first,
                "last": last,
                "delta": delta,
                "direction": "higher_is_better" if direction > 0 else "lower_is_better",
                "improved": (delta * direction) > 0 if len(values) > 1 else None,
            }
        return trends

    @staticmethod
    def _before_after_radar(
        sessions: list[Session],
        feature_rows_by_session: dict[str, ExtractedFeatures],
    ) -> list[dict]:
        rows = [
            feature_rows_by_session[session.session_id]
            for session in sessions
            if session.session_id in feature_rows_by_session
        ]
        if not rows:
            return []
        first = rows[0].features
        last = rows[-1].features
        metrics = [
            "total_utterances",
            "total_words",
            "mlu",
            "ttr",
            "unintelligible_ratio",
            "echolalia_ratio",
        ]
        return [
            {
                "metric": metric,
                "first": float(first.get(metric, 0.0)),
                "last": float(last.get(metric, 0.0)),
            }
            for metric in metrics
        ]

    @staticmethod
    def _render_progress_report_markdown(case: ChildCase, summary: dict) -> str:
        goals = summary["therapy_goal_progress"]
        trend_rows = []
        for metric, trend in summary["feature_trends"].items():
            status = "positive direction" if trend["improved"] is True else "mixed/unchanged"
            if trend["improved"] is None:
                status = "needs more sessions"
            trend_rows.append(
                f"| {metric} | {trend['first']} | {trend['last']} | {trend['delta']} | {status} |"
            )
        if not trend_rows:
            trend_rows.append("| No reviewed feature rows yet | - | - | - | add reviewed sessions |")

        score_rows = []
        notes_rows = []
        evidence_rows = []
        for row in summary["score_timeline"]:
            score = row["screening_support_score"]
            score_rows.append(
                f"- {row['session_date']} / {row['session_id']}: "
                f"{'not generated' if score is None else score}; "
                f"transcript review {row['therapist_review_status']}; "
                f"feature status {row['feature_extraction_status']}"
            )
            notes_rows.append(f"### {row['session_id']}\n{row['notes'] or '_No therapist notes recorded._'}")
            evidence_rows.append(
                f"### {row['session_id']}\n"
                + (
                    "\n".join(f"- {MockClinicalRepository._format_evidence_item(item)}" for item in row["evidence_items"])
                    if row["evidence_items"]
                    else "- No evidence highlights recorded yet."
                )
            )

        return f"""# Progress Report: {case.anonymized_child_code}

This report summarizes descriptive progress for therapist review.

## Case Overview
- Case ID: {case.case_id}
- Anonymized child code: {case.anonymized_child_code}
- Consent status: {summary["consent_status"]}
- Anonymization status: {summary["anonymization_status"]}
- External clinical status: {case.external_clinical_status}
- Sessions summarized: {summary["n_sessions"]}
- Therapy goals: {goals["completed"]}/{goals["total"]} completed, {goals["active"]} active, {goals["paused"]} paused

{"- Consent status needs review before real clinical upload or interpretation." if summary["consent_status"] != "granted" else ""}

## Screening Support Timeline
{chr(10).join(score_rows) if score_rows else "- No sessions available"}

## Feature Trends
| Metric | First | Latest | Delta | Descriptive trend |
|---|---:|---:|---:|---|
{chr(10).join(trend_rows)}

## Therapist Notes
{chr(10).join(notes_rows) if notes_rows else "_No therapist notes recorded._"}

## AI-Assisted Explanation
Prototype support label: rule-based/mock screening support, not a validated medical model.

{chr(10).join(f"- {row['session_id']}: {row['ai_explanation'] or 'No AI-assisted explanation recorded.'}" for row in summary["score_timeline"])}

## Evidence Highlights
{chr(10).join(evidence_rows) if evidence_rows else "- No evidence highlights recorded yet."}

## Safe Use Boundary
{SAFETY_DISCLAIMER}

This report is for progress tracking and clinical decision support only. It must be reviewed with transcript QA, therapist notes, session context, and qualified professional judgment. Consult qualified professionals where appropriate, especially when concern level, consent status, transcript review status, or feature status indicates review priority.
"""

    @staticmethod
    def _format_evidence_item(item: object) -> str:
        if isinstance(item, str):
            return item
        if isinstance(item, dict):
            key = item.get("feature_key") or item.get("marker_type") or item.get("type") or "evidence"
            value = "" if item.get("value") is None else f" = {item.get('value')}"
            explanation = item.get("explanation") or "Review with transcript and session context."
            return f"**{key}{value}:** {explanation}"
        return str(item)
