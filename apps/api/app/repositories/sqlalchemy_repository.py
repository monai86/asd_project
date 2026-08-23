from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.db.models import (
    AiReviewRecord,
    AudioFileRecord,
    AuditLogRecord,
    CaseCareTeamAssignmentRecord,
    Base,
    ChildCaseRecord,
    FeatureSetRecord,
    MLResultRecord,
    OrganizationInvitationRecord,
    OrganizationMembershipRecord,
    OrganizationRecord,
    OrganizationSettingsRecord,
    PrivacyOperationRecord,
    ProcessingJobRecord,
    ReportRecord,
    SessionRecord,
    SpeakerMappingRecord,
    TherapyGoalRecord,
    TranscriptRecord,
    UserProfileRecord,
)
from app.repositories.base import (
    CaseVersionConflictError,
    ReportVersionConflictError,
    SessionVersionConflictError,
    SpeakerMappingVersionConflictError,
    TranscriptVersionConflictError,
)
from app.repositories.mock_repository import ALLOWED_JOB_TRANSITIONS, MockRepository, new_id
from app.schemas.clinical import (
    AiReview,
    AudioFileMetadata,
    CareTeamAssignment,
    CareTeamAssignmentCreate,
    ChildCase,
    ChildCaseCreate,
    ChildCaseUpdate,
    FeatureSet,
    JobStatus,
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
from app.schemas.speaker_mapping import (
    MappingPersistedStatus,
    SpeakerMapping,
    SpeakerMappingEntry,
)
from app.services.audit_safety import validate_audit_event


class SqlAlchemyRepository(MockRepository):
    """SQLAlchemy-backed repository with targeted transactional mutations.

    Dictionaries remain compatibility mirrors for read-heavy legacy surfaces;
    durable workflow changes use explicit operations and authoritative SQL rows.
    """

    def __init__(self, database_url: str, *, create_schema: bool = True) -> None:
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("SQLAlchemy repository mode requires sqlalchemy to be installed.") from exc

        self.database_url = database_url
        self.engine = create_engine(database_url)
        if create_schema:
            Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        super().__init__()
        self.load()

    def get_case(self, case_id: str) -> ChildCase | None:
        with self.SessionLocal() as db:
            row = db.get(ChildCaseRecord, case_id)
            case = self._case_from_record(row) if row is not None else None
        return self.clone(case) if case is not None else None

    def get_session(self, session_id: str) -> TherapySession | None:
        with self.SessionLocal() as db:
            row = db.get(SessionRecord, session_id)
            session = self._session_from_record(row) if row is not None else None
        return self.clone(session) if session is not None else None

    def get_report(self, report_id: str) -> Report | None:
        with self.SessionLocal() as db:
            row = db.get(ReportRecord, report_id)
            report = self._report_from_record(row) if row is not None else None
        return self.clone(report) if report is not None else None

    def get_audio_file(self, audio_file_id: str) -> AudioFileMetadata | None:
        with self.SessionLocal() as db:
            row = db.get(AudioFileRecord, audio_file_id)
            audio_file = self._audio_from_record(row) if row is not None else None
        return self.clone(audio_file) if audio_file is not None else None

    def get_processing_job(self, job_id: str) -> ProcessingJob | None:
        with self.SessionLocal() as db:
            row = db.get(ProcessingJobRecord, job_id)
            job = self._job_from_record(row) if row is not None else None
        return self.clone(job) if job is not None else None

    def get_ai_review(self, review_id: str) -> AiReview | None:
        with self.SessionLocal() as db:
            row = db.get(AiReviewRecord, review_id)
            review = AiReview.model_validate(row.payload) if row is not None else None
        return self.clone(review) if review is not None else None

    def get_feature_set(self, feature_set_id: str) -> FeatureSet | None:
        with self.SessionLocal() as db:
            row = db.get(FeatureSetRecord, feature_set_id)
            feature_set = self._feature_from_record(row) if row is not None else None
        return self.clone(feature_set) if feature_set is not None else None

    def get_ml_result(self, result_id: str) -> MLResult | None:
        with self.SessionLocal() as db:
            row = db.get(MLResultRecord, result_id)
            result = MLResult.model_validate(row.payload) if row is not None else None
        return self.clone(result) if result is not None else None

    def get_therapy_goal(self, goal_id: str) -> TherapyGoal | None:
        with self.SessionLocal() as db:
            row = db.get(TherapyGoalRecord, goal_id)
            goal = self._goal_from_record(row) if row is not None else None
        return self.clone(goal) if goal is not None else None

    def get_privacy_operation(self, operation_id: str) -> PrivacyOperation | None:
        with self.SessionLocal() as db:
            row = db.get(PrivacyOperationRecord, operation_id)
            operation = self._privacy_operation_from_record(row) if row is not None else None
        return self.clone(operation) if operation is not None else None

    def list_reports(self, organization_id: str) -> list[Report]:
        with self.SessionLocal() as db:
            rows = db.query(ReportRecord).filter(
                ReportRecord.organization_id == organization_id
            ).all()
            return [self._report_from_record(row) for row in rows]

    def list_audio_files(self, session_id: str) -> list[AudioFileMetadata]:
        with self.SessionLocal() as db:
            rows = db.query(AudioFileRecord).filter(
                AudioFileRecord.session_id == session_id
            ).all()
            return [self._audio_from_record(row) for row in rows]

    def list_sessions(self, case_id: str) -> list[TherapySession]:
        with self.SessionLocal() as db:
            rows = db.query(SessionRecord).filter(SessionRecord.case_id == case_id).all()
            return [self._session_from_record(row) for row in rows]

    def list_therapy_goals(self, case_id: str) -> list[TherapyGoal]:
        with self.SessionLocal() as db:
            rows = db.query(TherapyGoalRecord).filter(TherapyGoalRecord.case_id == case_id).all()
            return [self._goal_from_record(row) for row in rows]

    def list_privacy_operations(self, case_id: str | None = None) -> list[PrivacyOperation]:
        with self.SessionLocal() as db:
            query = db.query(PrivacyOperationRecord)
            if case_id is not None:
                query = query.filter(PrivacyOperationRecord.case_id == case_id)
            return [self._privacy_operation_from_record(row) for row in query.all()]

    @staticmethod
    def _lock_case_row(db, case_id: str, *, organization_id: str | None = None, require_consent: bool = True):
        row = (
            db.query(ChildCaseRecord)
            .filter(ChildCaseRecord.case_id == case_id)
            .with_for_update()
            .one_or_none()
        )
        if row is None or (organization_id is not None and row.organization_id != organization_id):
            raise KeyError(case_id)
        if require_consent and row.consent_status.lower() == "withdrawn":
            raise ValueError("Case consent has been withdrawn.")
        return row

    def get_transcript(self, transcript_id: str) -> Transcript | None:
        """Read the authoritative transcript and narrowly refresh its mirror."""

        with self.SessionLocal() as db:
            row = db.get(TranscriptRecord, transcript_id)
            transcript = self._transcript_from_record(row) if row is not None else None
        if transcript is not None:
            with self._lock:
                self.transcripts[transcript_id] = transcript
            return self.clone(transcript)
        return None

    def create_audio_upload(self, audio_file, job, *, actor_id):
        audit = validate_audit_event(
            actor_id=actor_id, action="audio.upload", target_id=job.job_id,
            outcome="success", correlation_id="local",
            message="Experimental audio processing job queued.",
        ).as_dict()
        with self.SessionLocal() as db:
            case_row = self._lock_case_row(db, audio_file.case_id)
            session_row = db.get(SessionRecord, audio_file.session_id)
            if session_row is None:
                raise KeyError(audio_file.session_id)
            if session_row.case_id != case_row.case_id or job.session_id != session_row.session_id:
                raise ValueError("Audio upload ownership does not match the authoritative session.")
            if audio_file.upload_status != "pending" or not audio_file.retained:
                raise ValueError("New audio metadata must begin pending and retained.")
            saved_audio = audio_file.model_copy(
                update={"organization_id": session_row.organization_id, "version": 1}
            )
            saved_job = job.model_copy(update={"organization_id": session_row.organization_id})
            audit["organization_id"] = session_row.organization_id
            db.add(self._audio_to_record(saved_audio))
            db.add(self._job_to_record(saved_job))
            db.add(self._audit_to_record(audit))
            db.commit()
        with self._lock:
            self.audio_files[saved_audio.audio_file_id] = saved_audio
            self.jobs[saved_job.job_id] = saved_job
            self.audit_log.append(audit)
        return self.clone(saved_job)

    def update_audio_file_metadata(
        self, audio_file, *, actor_id, expected_version, expected_upload_status,
        audit_action=None, audit_message=None
    ):
        audit = None
        with self.SessionLocal() as db:
            case_id = db.query(AudioFileRecord.case_id).filter(
                AudioFileRecord.audio_file_id == audio_file.audio_file_id
            ).scalar()
            if case_id is None:
                raise KeyError(audio_file.audio_file_id)
            case_row = self._lock_case_row(db, case_id)
            row = db.get(AudioFileRecord, audio_file.audio_file_id)
            session_row = db.get(SessionRecord, row.session_id)
            if session_row is None or session_row.case_id != case_row.case_id:
                raise ValueError("Audio metadata ownership changed; reload and retry.")
            if (
                row.organization_id != audio_file.organization_id
                or row.session_id != audio_file.session_id
                or row.case_id != audio_file.case_id
            ):
                raise ValueError("Audio metadata ownership changed; reload and retry.")
            updated = (
                db.query(AudioFileRecord)
                .filter(
                    AudioFileRecord.audio_file_id == audio_file.audio_file_id,
                    AudioFileRecord.version == expected_version,
                    AudioFileRecord.upload_status == expected_upload_status,
                    AudioFileRecord.retained.is_(True),
                )
                .update(
                    {
                        AudioFileRecord.upload_status: audio_file.upload_status,
                        AudioFileRecord.checksum_sha256: audio_file.checksum_sha256,
                        AudioFileRecord.uploaded_at: audio_file.uploaded_at,
                        AudioFileRecord.version: expected_version + 1,
                    },
                    synchronize_session=False,
                )
            )
            if updated != 1:
                raise ValueError("Audio metadata changed; reload and retry.")
            saved = audio_file.model_copy(
                update={
                    "organization_id": row.organization_id,
                    "session_id": row.session_id,
                    "case_id": row.case_id,
                    "object_key": row.object_key,
                    "storage_delete_status": row.storage_delete_status,
                    "retained": row.retained,
                    "version": expected_version + 1,
                }
            )
            if audit_action is not None:
                audit = validate_audit_event(
                    actor_id=actor_id, action=audit_action, target_id=row.audio_file_id,
                    outcome="success", correlation_id="local",
                    message=audit_message or "Audio metadata updated.",
                ).as_dict()
                audit["organization_id"] = saved.organization_id
                db.add(self._audit_to_record(audit))
            db.flush()
            db.commit()
        with self._lock:
            self.audio_files[saved.audio_file_id] = saved
            if audit is not None:
                self.audit_log.append(audit)
        return self.clone(saved)

    def create_processing_job(self, job, *, actor_id, audit_action, audit_message):
        audit = validate_audit_event(
            actor_id=actor_id, action=audit_action, target_id=job.job_id,
            outcome="success", correlation_id="local", message=audit_message,
        ).as_dict()
        db = self.SessionLocal()
        try:
            case_id = db.query(SessionRecord.case_id).filter(
                SessionRecord.session_id == job.session_id
            ).scalar()
            if case_id is None:
                raise KeyError(job.session_id)
            case_row = self._lock_case_row(db, case_id)
            session_row = db.get(SessionRecord, job.session_id)
            if session_row is None:
                raise KeyError(job.session_id)
            if job.audio_file_id:
                audio_row = db.get(AudioFileRecord, job.audio_file_id)
                if (
                    audio_row is None
                    or audio_row.session_id != session_row.session_id
                    or not audio_row.retained
                    or audio_row.upload_status != "uploaded"
                ):
                    raise ValueError("Audio file is not available for processing.")
            initial_status = job.status.value if hasattr(job.status, "value") else str(job.status)
            if initial_status not in {"queued", "failed"}:
                raise ValueError("Processing jobs must begin queued or failed.")
            expected_active = job.audio_file_id if initial_status == "queued" else None
            if job.active_audio_file_id != expected_active:
                raise ValueError("Processing job active-audio claim is inconsistent.")
            saved = job.model_copy(update={"organization_id": session_row.organization_id, "version": 1})
            audit["organization_id"] = session_row.organization_id
            db.add(self._job_to_record(saved))
            db.add(self._audit_to_record(audit))
            db.flush()
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            if "uq_processing_jobs_active_audio_file_id" in str(exc) or "active_audio_file_id" in str(exc):
                raise ValueError("Only one active processing job is allowed per audio artifact.") from exc
            raise
        finally:
            db.close()
        with self._lock:
            self.jobs[saved.job_id] = saved
            self.audit_log.append(audit)
        return self.clone(saved)

    def update_processing_job(
        self, job, *, actor_id, expected_version, expected_status, audit_action, audit_message,
        expected_lease_token=None, expected_provider_request_id=None,
    ):
        audit = validate_audit_event(
            actor_id=actor_id, action=audit_action, target_id=job.job_id,
            outcome="success", correlation_id="local", message=audit_message,
        ).as_dict()
        with self.SessionLocal() as db:
            case_id = (
                db.query(SessionRecord.case_id)
                .join(ProcessingJobRecord, ProcessingJobRecord.session_id == SessionRecord.session_id)
                .filter(ProcessingJobRecord.job_id == job.job_id)
                .scalar()
            )
            if case_id is None:
                raise KeyError(job.job_id)
            case_row = self._lock_case_row(
                db, case_id, require_consent=False
            )
            row = db.get(ProcessingJobRecord, job.job_id)
            if row is None:
                raise KeyError(job.job_id)
            session_row = db.get(SessionRecord, row.session_id)
            if (
                row.organization_id != job.organization_id
                or row.session_id != job.session_id
                or row.audio_file_id != job.audio_file_id
            ):
                raise ValueError("Processing job ownership changed; reload and retry.")
            next_status = job.status.value if hasattr(job.status, "value") else str(job.status)
            if next_status not in ALLOWED_JOB_TRANSITIONS.get(expected_status, set()):
                raise ValueError(f"Processing job transition {expected_status} -> {next_status} is not allowed.")
            current_lease = (row.details or {}).get("provider_lease")
            if current_lease and expected_status == "processing" and next_status != "processing":
                if expected_lease_token != current_lease.get("token"):
                    raise ValueError("Processing provider lease changed; reload and retry.")
                if expected_provider_request_id != (row.details or {}).get("provider_request_id"):
                    raise ValueError("Processing provider request changed; reload and retry.")
            if case_row is None or (
                case_row.consent_status.lower() == "withdrawn" and next_status != "cancelled"
            ):
                raise ValueError("Case consent has been withdrawn.")
            active_audio_id = None if next_status in {"failed", "cancelled", "needs_review"} else row.audio_file_id
            updated = (
                db.query(ProcessingJobRecord)
                .filter(
                    ProcessingJobRecord.job_id == job.job_id,
                    ProcessingJobRecord.version == expected_version,
                    ProcessingJobRecord.status == expected_status,
                )
                .update(
                    {
                        ProcessingJobRecord.status: next_status,
                        ProcessingJobRecord.message: job.message,
                        ProcessingJobRecord.error_code: job.error_code,
                        ProcessingJobRecord.details: job.details,
                        ProcessingJobRecord.active_audio_file_id: active_audio_id,
                        ProcessingJobRecord.version: expected_version + 1,
                        ProcessingJobRecord.updated_at: utc_now(),
                    },
                    synchronize_session=False,
                )
            )
            if updated != 1:
                raise ValueError("Processing job changed; reload and retry.")
            saved = job.model_copy(
                update={
                    "version": expected_version + 1,
                    "audio_file_id": row.audio_file_id,
                    "active_audio_file_id": active_audio_id,
                }
            )
            audit["organization_id"] = row.organization_id
            db.add(self._audit_to_record(audit))
            db.flush()
            db.commit()
        with self._lock:
            self.jobs[saved.job_id] = saved
            self.audit_log.append(audit)
        return self.clone(saved)

    def claim_processing_job(
        self, job_id: str, *, actor_id: str, lease_seconds: int = 300
    ) -> ProcessingJob | None:
        with self.SessionLocal() as db:
            case_id = (
                db.query(SessionRecord.case_id)
                .join(ProcessingJobRecord, ProcessingJobRecord.session_id == SessionRecord.session_id)
                .filter(ProcessingJobRecord.job_id == job_id)
                .scalar()
            )
            if case_id is None:
                raise KeyError(job_id)
            case_row = self._lock_case_row(db, case_id)
            row = db.query(ProcessingJobRecord).filter(
                ProcessingJobRecord.job_id == job_id
            ).with_for_update().one_or_none()
            if row is None:
                raise KeyError(job_id)
            if row.status != JobStatus.processing.value:
                return None
            now = utc_now()
            details = dict(row.details or {})
            existing = details.get("provider_lease")
            if existing and existing.get("expires_at"):
                expires_at = _as_utc(datetime.fromisoformat(existing["expires_at"]))
                if expires_at > now:
                    return None
            token = uuid4().hex
            provider_request_id = details.get("provider_request_id") or f"asr-{job_id}-{uuid4().hex}"
            details["provider_request_id"] = provider_request_id
            details["provider_lease"] = {
                "token": token,
                "claimed_by": actor_id,
                "claimed_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=lease_seconds)).isoformat(),
                "attempt": int((existing or {}).get("attempt", 0)) + 1,
                "idempotency_key": provider_request_id,
            }
            changed = db.query(ProcessingJobRecord).filter(
                ProcessingJobRecord.job_id == job_id,
                ProcessingJobRecord.version == row.version,
                ProcessingJobRecord.status == JobStatus.processing.value,
            ).update(
                {
                    ProcessingJobRecord.details: details,
                    ProcessingJobRecord.version: row.version + 1,
                    ProcessingJobRecord.updated_at: now,
                },
                synchronize_session=False,
            )
            if changed != 1:
                return None
            saved = self._job_from_record(row).model_copy(
                update={"details": details, "version": row.version + 1, "updated_at": now}
            )
            audit = validate_audit_event(
                actor_id=actor_id, action="audio.provider_claim", target_id=job_id,
                outcome="success", correlation_id=f"audio-provider-claim-{token}",
                message="ASR provider execution lease acquired.",
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            db.add(self._audit_to_record(audit))
            db.flush()
            db.commit()
        with self._lock:
            self.jobs[job_id] = saved
            self.audit_log.append(audit)
        return self.clone(saved)

    def complete_processing_job(
        self, job, transcript, *, actor_id, expected_version, expected_status,
        audit_action, audit_message
    ):
        audit = validate_audit_event(
            actor_id=actor_id, action=audit_action, target_id=job.job_id,
            outcome="success", correlation_id="local", message=audit_message,
        ).as_dict()
        with self.SessionLocal() as db:
            case_row = self._lock_case_row(db, transcript.case_id)
            job_row = db.get(ProcessingJobRecord, job.job_id)
            session_row = db.get(SessionRecord, transcript.session_id)
            if job_row is None:
                raise KeyError(job.job_id)
            if session_row is None:
                raise KeyError(transcript.session_id)
            if job_row.session_id != session_row.session_id or transcript.case_id != session_row.case_id:
                raise ValueError("ASR result ownership does not match the authoritative job.")
            submitted_status = job.status.value if hasattr(job.status, "value") else str(job.status)
            if expected_status not in {"processing", "transcription_completed"} or submitted_status != "needs_review":
                raise ValueError("ASR completion job transition is not allowed.")
            if job.audio_file_id != job_row.audio_file_id:
                raise ValueError("ASR completion audio ownership changed; reload and retry.")
            if job_row.audio_file_id:
                audio_row = db.get(AudioFileRecord, job_row.audio_file_id)
                if audio_row is None or not audio_row.retained or audio_row.upload_status != "uploaded":
                    raise ValueError("Audio file is no longer available for processing.")
            saved_transcript = transcript.model_copy(update={"organization_id": session_row.organization_id})
            saved_job = job.model_copy(
                update={
                    "organization_id": session_row.organization_id,
                    "version": expected_version + 1,
                    "active_audio_file_id": None,
                }
            )
            invalidated = self._mark_downstream_rows_stale(db, session_row)
            job_updated = (
                db.query(ProcessingJobRecord)
                .filter(
                    ProcessingJobRecord.job_id == job.job_id,
                    ProcessingJobRecord.version == expected_version,
                    ProcessingJobRecord.status == expected_status,
                )
                .update(
                    {
                        ProcessingJobRecord.status: "needs_review",
                        ProcessingJobRecord.message: job.message,
                        ProcessingJobRecord.error_code: job.error_code,
                        ProcessingJobRecord.details: job.details,
                        ProcessingJobRecord.active_audio_file_id: None,
                        ProcessingJobRecord.version: expected_version + 1,
                        ProcessingJobRecord.updated_at: utc_now(),
                    },
                    synchronize_session=False,
                )
            )
            if job_updated != 1:
                raise ValueError("Processing job changed; reload and retry.")
            session_row.transcript_id = saved_transcript.transcript_id
            session_row.status = ReviewStatus.needs_review.value
            session_row.updated_at = _utc_now()
            audit["organization_id"] = session_row.organization_id
            db.add(self._transcript_to_record(saved_transcript))
            db.add(self._audit_to_record(audit))
            invalidation_audit = None
            if invalidated:
                invalidation_audit = validate_audit_event(
                    actor_id=actor_id,
                    action="workflow.invalidate_downstream",
                    target_id=saved_transcript.transcript_id,
                    outcome="success",
                    correlation_id="local",
                    message="Derived workflow outputs marked stale after transcript change.",
                ).as_dict()
                invalidation_audit["organization_id"] = session_row.organization_id
                db.add(self._audit_to_record(invalidation_audit))
            self._recompute_case_summary_rows(db, case_row)
            saved_session = self._session_from_record(session_row)
            saved_case = self._case_from_record(case_row)
            db.flush()
            db.commit()
        with self._lock:
            self.jobs[saved_job.job_id] = saved_job
            self.transcripts[saved_transcript.transcript_id] = saved_transcript
            self.sessions[saved_session.session_id] = saved_session
            self.cases[saved_case.case_id] = saved_case
            self._mark_downstream_outputs_stale(self.sessions[saved_session.session_id])
            self.audit_log.append(audit)
            if invalidation_audit is not None:
                self.audit_log.append(invalidation_audit)
        return self.clone(saved_job)

    def withdraw_case_consent(self, *, case_id: str, actor_id: str, redact_notes: bool):
        with self.SessionLocal() as db:
            case_row = self._lock_case_row(db, case_id, require_consent=False)
            if case_row.consent_status.lower() == "withdrawn":
                raise ValueError("Case consent has already been withdrawn.")
            case_row.consent_status = "withdrawn"
            case_row.version += 1
            case_row.updated_at = utc_now()
            if redact_notes:
                case_row.notes = ""

            session_rows = db.query(SessionRecord).filter_by(case_id=case_row.case_id).all()
            session_ids = {row.session_id for row in session_rows}
            for row in session_rows:
                row.status = ReviewStatus.withdrawn.value
                row.version += 1
                row.updated_at = utc_now()
                if redact_notes:
                    row.notes = ""

            goal_rows = db.query(TherapyGoalRecord).filter_by(case_id=case_row.case_id).all()
            for row in goal_rows:
                row.status = "withdrawn"
                row.retained = False
                if redact_notes:
                    row.notes = ""

            transcript_rows = db.query(TranscriptRecord).filter_by(case_id=case_row.case_id).all()
            for row in transcript_rows:
                row.raw_text = ""
                row.utterances = []
                row.review_status = ReviewStatus.withdrawn.value
                row.version += 1
                row.updated_at = utc_now()

            audio_rows = db.query(AudioFileRecord).filter_by(case_id=case_row.case_id).all()
            for row in audio_rows:
                row.upload_status = "withdrawn"
                row.retained = False
                row.storage_delete_status = "pending_deletion"
                row.version += 1

            feature_rows = []
            ml_rows = []
            ai_rows = []
            job_rows = []
            if session_ids:
                feature_rows = db.query(FeatureSetRecord).filter(FeatureSetRecord.session_id.in_(session_ids)).all()
                ml_rows = db.query(MLResultRecord).filter(MLResultRecord.session_id.in_(session_ids)).all()
                ai_rows = db.query(AiReviewRecord).filter(AiReviewRecord.session_id.in_(session_ids)).all()
                job_rows = db.query(ProcessingJobRecord).filter(ProcessingJobRecord.session_id.in_(session_ids)).all()
            for row in feature_rows:
                db.delete(row)
            for row in ml_rows:
                db.delete(row)
            for session_row in session_rows:
                session_row.feature_set_id = None
                session_row.ml_result_id = None
            for row in ai_rows:
                payload = dict(row.payload or {})
                payload.update({
                    "summary": "Consent withdrawn. AI-assisted review content unlinked from clinical workflow.",
                    "key_findings": [], "concerns": [], "strengths": [],
                    "limitations": ["Consent withdrawn; prior AI-assisted review support is no longer retained for workflow use."],
                    "recommended_review_actions": [], "therapist_review_status": ReviewStatus.withdrawn.value,
                    "rejected_reason": "Consent withdrawn.",
                })
                row.payload = payload
                row.therapist_review_status = ReviewStatus.withdrawn.value
            report_rows = db.query(ReportRecord).filter_by(case_id=case_row.case_id).all()
            for row in report_rows:
                row.status = ReviewStatus.withdrawn.value
                row.markdown = "Consent withdrawn. Report content unlinked from clinical workflow."
                row.html = "<p>Consent withdrawn. Report content unlinked from clinical workflow.</p>"
                row.version += 1
                row.updated_at = utc_now()
            for row in job_rows:
                details = dict(row.details or {})
                details["consent_withdrawn"] = True
                details["storage_unlinked"] = True
                history = list(details.get("status_history", []))
                if row.status not in {"failed", "cancelled", "needs_review"}:
                    row.status = "cancelled"
                    row.message = "Audio processing cancelled because case consent was withdrawn."
                    row.error_code = "consent_withdrawn"
                    if not history or history[-1] != "cancelled":
                        history.append("cancelled")
                details["status_history"] = history
                row.details = details
                row.active_audio_file_id = None
                row.version += 1
                row.updated_at = utc_now()

            self._recompute_case_summary_rows(db, case_row)

            audit = validate_audit_event(
                actor_id=actor_id, action="consent.withdraw", target_id=case_row.case_id,
                outcome="success", correlation_id="local",
                message="Consent withdrawn by authorized request; linked workflow outputs were removed or unlinked.",
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            db.add(self._audit_to_record(audit))
            db.flush()
            saved_case = self._case_from_record(case_row)
            saved_sessions = {row.session_id: self._session_from_record(row) for row in session_rows}
            saved_goals = {row.goal_id: self._goal_from_record(row) for row in goal_rows}
            saved_audio = {row.audio_file_id: self._audio_from_record(row) for row in audio_rows}
            saved_transcripts = {row.transcript_id: self._transcript_from_record(row) for row in transcript_rows}
            saved_ai = {row.ai_review_id: AiReview.model_validate(row.payload) for row in ai_rows}
            saved_reports = {row.report_id: self._report_from_record(row) for row in report_rows}
            saved_jobs = {row.job_id: self._job_from_record(row) for row in job_rows}
            deleted_features = {row.feature_set_id for row in feature_rows}
            deleted_ml = {row.result_id for row in ml_rows}
            db.commit()

        with self._lock:
            self.cases[saved_case.case_id] = saved_case
            self.sessions.update(saved_sessions)
            self.therapy_goals.update(saved_goals)
            self.audio_files.update(saved_audio)
            self.transcripts.update(saved_transcripts)
            self.ai_reviews.update(saved_ai)
            self.reports.update(saved_reports)
            self.jobs.update(saved_jobs)
            for feature_id in deleted_features:
                self.features.pop(feature_id, None)
            for result_id in deleted_ml:
                self.ml_results.pop(result_id, None)
            self.audit_log.append(audit)
        return {
            "sessions": len(saved_sessions),
            "therapy_goals": len(saved_goals),
            "audio_metadata": len(saved_audio),
            "transcripts": len(saved_transcripts),
            "features": len(deleted_features),
            "ml_results": len(deleted_ml),
            "ai_reviews": len(saved_ai),
            "reports": len(saved_reports),
            "jobs": len(saved_jobs),
        }

    def list_pending_audio_deletions(self, case_id: str | None = None):
        with self.SessionLocal() as db:
            query = db.query(AudioFileRecord).filter(
                (AudioFileRecord.storage_delete_status == "pending_deletion")
                | AudioFileRecord.storage_delete_status.like("retryable:%")
            )
            if case_id is not None:
                query = query.filter_by(case_id=case_id)
            return [self._audio_from_record(row) for row in query.all()]

    def record_audio_deletion_result(
        self, audio_file_id: str, *, expected_version: int, deletion_status: str,
        deleted: bool, actor_id: str,
    ):
        with self.SessionLocal() as db:
            case_id = db.query(AudioFileRecord.case_id).filter(
                AudioFileRecord.audio_file_id == audio_file_id
            ).scalar()
            if case_id is None:
                raise KeyError(audio_file_id)
            self._lock_case_row(db, case_id, require_consent=False)
            row = db.get(AudioFileRecord, audio_file_id)
            final_status = deletion_status if deleted else f"retryable:{deletion_status}"
            current_delete_status = row.storage_delete_status
            if not (
                current_delete_status == "pending_deletion"
                or str(current_delete_status).startswith("retryable:")
            ):
                raise ValueError("Audio deletion state changed; reload and retry.")
            values = {
                AudioFileRecord.storage_delete_status: final_status,
                AudioFileRecord.version: expected_version + 1,
            }
            if deleted:
                values[AudioFileRecord.object_key] = None
            updated = (
                db.query(AudioFileRecord)
                .filter(
                    AudioFileRecord.audio_file_id == audio_file_id,
                    AudioFileRecord.version == expected_version,
                    AudioFileRecord.storage_delete_status == current_delete_status,
                )
                .update(values, synchronize_session=False)
            )
            if updated != 1:
                raise ValueError("Audio deletion state changed; reload and retry.")
            saved = self._audio_from_record(row).model_copy(
                update={
                    "version": expected_version + 1,
                    "storage_delete_status": final_status,
                    "object_key": None if deleted else row.object_key,
                }
            )
            audit = validate_audit_event(
                actor_id=actor_id, action="audio.storage_delete", target_id=audio_file_id,
                outcome="success", correlation_id="local",
                message="Audio storage deletion outcome recorded.",
            ).as_dict()
            audit["organization_id"] = row.organization_id
            db.add(self._audit_to_record(audit))
            db.flush()
            db.commit()
        with self._lock:
            self.audio_files[audio_file_id] = saved
            self.audit_log.append(audit)
        return self.clone(saved)

    def acknowledge_session_cues(
        self, session_id: str, *, acknowledged_at: str, expected_version: int, actor_id: str
    ):
        with self.SessionLocal() as db:
            case_id = db.query(SessionRecord.case_id).filter(SessionRecord.session_id == session_id).scalar()
            if case_id is None:
                raise KeyError(session_id)
            case_row = self._lock_case_row(db, case_id)
            row = db.get(SessionRecord, session_id)
            updated = (
                db.query(SessionRecord)
                .filter(SessionRecord.session_id == session_id, SessionRecord.version == expected_version)
                .update(
                    {
                        SessionRecord.cues_acknowledged_at: acknowledged_at,
                        SessionRecord.cues_acknowledged_by: actor_id,
                        SessionRecord.version: expected_version + 1,
                        SessionRecord.updated_at: utc_now(),
                    },
                    synchronize_session=False,
                )
            )
            if updated != 1:
                raise SessionVersionConflictError("Session changed; reload and retry.")
            saved = self._session_from_record(row).model_copy(
                update={
                    "cues_acknowledged_at": acknowledged_at,
                    "cues_acknowledged_by": actor_id,
                    "version": expected_version + 1,
                }
            )
            audits = []
            for action, message in (
                ("session.patch", "Session updated."),
                ("cues_acknowledged", "Therapist acknowledged reviewed cues in the findings workspace."),
            ):
                event = validate_audit_event(
                    actor_id=actor_id, action=action, target_id=session_id,
                    outcome="success", correlation_id="local", message=message,
                ).as_dict()
                event["organization_id"] = row.organization_id
                audits.append(event)
                db.add(self._audit_to_record(event))
            db.flush()
            db.commit()
        with self._lock:
            self.sessions[session_id] = saved
            self.audit_log.extend(audits)
        return self.clone(saved)

    @staticmethod
    def _copy_record_values(row, replacement) -> None:
        for column in row.__table__.columns:
            if not column.primary_key:
                setattr(row, column.name, getattr(replacement, column.name))

    def create_case(self, payload: ChildCaseCreate, *, actor_id: str) -> ChildCase:
        now = _utc_now()
        case = ChildCase(
            case_id=new_id("case"),
            **payload.model_dump(),
            created_at=now,
            updated_at=now,
        )
        if actor_id != "system" and actor_id not in case.care_team_user_ids:
            case.care_team_user_ids = [*case.care_team_user_ids, actor_id]
        if case.primary_therapist_user_id is None and actor_id != "system":
            case.primary_therapist_user_id = actor_id
        if case.primary_therapist_user_id and case.primary_therapist_user_id not in case.care_team_user_ids:
            case.care_team_user_ids = [*case.care_team_user_ids, case.primary_therapist_user_id]
        audit = validate_audit_event(
            actor_id=actor_id,
            action="case.create",
            target_id=case.case_id,
            outcome="success",
            correlation_id=f"case-create-{case.version}",
            message="Case created.",
        ).as_dict()
        audit["organization_id"] = case.organization_id
        with self.SessionLocal() as db:
            if payload.primary_therapist_user_id:
                membership_row = db.query(OrganizationMembershipRecord).filter_by(
                    organization_id=case.organization_id,
                    user_id=payload.primary_therapist_user_id,
                    role="therapist",
                    active=True,
                ).with_for_update().one_or_none()
                if membership_row is None:
                    raise ValueError("Primary therapist assignment must be an active therapist membership.")
            db.add(self._case_to_record(case))
            db.add(self._audit_to_record(audit))
            db.commit()
        self.cases[case.case_id] = case
        self.audit_log.append(audit)
        return self.clone(case)

    def update_case(
        self,
        case_id: str,
        patch: ChildCaseUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> ChildCase:
        now = _utc_now()
        patch_values = patch.model_dump(exclude_unset=True)
        with self.SessionLocal() as db:
            row = self._lock_case_row(db, case_id)
            compare_version = row.version if expected_version is None else expected_version
            if row.version != compare_version:
                raise CaseVersionConflictError(
                    f"Case {case_id} expected version {expected_version}, found {row.version}."
                )
            updated = self._case_from_record(row).model_copy(
                update={**patch_values, "version": compare_version + 1, "updated_at": now}
            )
            values = patch_values | {"version": compare_version + 1, "updated_at": now}
            changed = (
                db.query(ChildCaseRecord)
                .filter(ChildCaseRecord.case_id == case_id, ChildCaseRecord.version == compare_version)
                .update(values, synchronize_session=False)
            )
            if changed != 1:
                raise CaseVersionConflictError(
                    f"Case {case_id} expected version {compare_version}; reload and retry."
                )
            audit = validate_audit_event(
                actor_id=actor_id,
                action="case.update",
                target_id=case_id,
                outcome="success",
                correlation_id=f"case-update-{updated.version}",
                message="Case updated.",
            ).as_dict()
            audit["organization_id"] = row.organization_id
            db.add(self._audit_to_record(audit))
            db.flush()
            db.commit()
        self.cases[case_id] = updated
        self.audit_log.append(audit)
        return self.clone(updated)

    def list_cases_for_user(self, user_id: str, organization_id: str) -> list[ChildCase]:
        with self.SessionLocal() as db:
            rows = db.query(ChildCaseRecord).filter(
                ChildCaseRecord.organization_id == organization_id
            ).all()
            return [self._case_from_record(row) for row in rows]

    def get_membership(self, organization_id: str, user_id: str) -> OrganizationMembership | None:
        with self.SessionLocal() as db:
            row = db.query(OrganizationMembershipRecord).filter_by(
                organization_id=organization_id, user_id=user_id
            ).one_or_none()
            if row is None:
                return None
            profile = db.get(UserProfileRecord, row.user_id)
            membership = self._membership_from_record(
                row, display_name=profile.display_name if profile is not None else row.user_id
            )
        return self.clone(membership)

    def list_memberships(self, organization_id: str) -> list[OrganizationMembership]:
        with self.SessionLocal() as db:
            rows = db.query(OrganizationMembershipRecord).filter_by(
                organization_id=organization_id
            ).order_by(OrganizationMembershipRecord.created_at).all()
            profiles = {row.user_id: db.get(UserProfileRecord, row.user_id) for row in rows}
            return [
                self._membership_from_record(
                    row,
                    display_name=profiles[row.user_id].display_name if profiles[row.user_id] is not None else row.user_id,
                ) for row in rows
            ]

    def list_audit_events(self, organization_id: str, target_ids: set[str] | None = None) -> list[dict]:
        with self.SessionLocal() as db:
            query = db.query(AuditLogRecord).filter(AuditLogRecord.organization_id == organization_id)
            if target_ids is not None:
                if not target_ids:
                    return []
                query = query.filter(AuditLogRecord.target_id.in_(target_ids))
            rows = query.order_by(AuditLogRecord.timestamp).all()
            return [
                {
                    "audit_id": row.audit_id, "organization_id": row.organization_id,
                    "actor_id": row.actor_id, "action": row.action, "target_id": row.target_id,
                    "outcome": row.outcome, "correlation_id": row.correlation_id,
                    "message": row.message, "timestamp": _as_utc(row.timestamp).isoformat(),
                }
                for row in rows
            ]

    def upsert_membership(
        self,
        organization_id: str,
        payload: OrganizationMembershipCreate,
        *,
        actor_id: str,
    ) -> OrganizationMembership:
        now = _utc_now()
        with self.SessionLocal() as db:
            organization = db.get(OrganizationRecord, organization_id)
            if organization is None:
                db.add(OrganizationRecord(organization_id=organization_id, name=organization_id, pilot_mode=False, created_at=now))
            profile = db.get(UserProfileRecord, payload.user_id)
            if profile is None:
                db.add(UserProfileRecord(user_id=payload.user_id, display_name=payload.display_name, created_at=now))
            else:
                profile.display_name = payload.display_name

            row = (
                db.query(OrganizationMembershipRecord)
                .filter_by(organization_id=organization_id, user_id=payload.user_id)
                .one_or_none()
            )
            if row is None:
                membership = OrganizationMembership(
                    membership_id=new_id("mbr"),
                    organization_id=organization_id,
                    user_id=payload.user_id,
                    display_name=payload.display_name,
                    role=payload.role,
                    active=payload.active,
                    created_at=now,
                )
                row = self._membership_to_record(membership)
                db.add(row)
            else:
                row.role = payload.role
                row.active = payload.active
                membership = self._membership_from_record(row, display_name=payload.display_name)

            audit = validate_audit_event(
                actor_id=actor_id,
                action="membership.upsert",
                target_id=membership.membership_id,
                outcome="success",
                correlation_id=f"membership-upsert-{membership.membership_id}",
                message="Organization membership updated.",
            ).as_dict()
            audit["organization_id"] = organization_id
            db.add(self._audit_to_record(audit))
            db.commit()

        self.memberships[membership.membership_id] = membership
        self.audit_log.append(audit)
        return self.clone(membership)

    def revoke_membership(self, organization_id: str, membership_id: str, *, actor_id: str) -> OrganizationMembership:
        now = _utc_now()
        with self.SessionLocal() as db:
            row = db.query(OrganizationMembershipRecord).filter(
                OrganizationMembershipRecord.membership_id == membership_id
            ).with_for_update().one_or_none()
            if row is None or row.organization_id != organization_id:
                raise KeyError(membership_id)
            row.active = False
            care_rows = (
                db.query(CaseCareTeamAssignmentRecord)
                .filter_by(organization_id=organization_id, user_id=row.user_id)
                .all()
            )
            for assignment_row in care_rows:
                assignment_row.active = False
                case_row = db.get(ChildCaseRecord, assignment_row.case_id)
                if case_row is not None:
                    case_row.care_team_user_ids = [
                        user_id for user_id in (case_row.care_team_user_ids or []) if user_id != row.user_id
                    ]
                    if case_row.primary_therapist_user_id == row.user_id:
                        case_row.primary_therapist_user_id = None
                    case_row.updated_at = now
            profile = db.get(UserProfileRecord, row.user_id)
            membership = self._membership_from_record(
                row,
                display_name=profile.display_name if profile is not None else row.user_id,
            )
            audit = validate_audit_event(
                actor_id=actor_id,
                action="membership.revoke",
                target_id=membership.membership_id,
                outcome="success",
                correlation_id=f"membership-revoke-{membership.membership_id}",
                message="Organization membership revoked.",
            ).as_dict()
            audit["organization_id"] = organization_id
            db.add(self._audit_to_record(audit))
            db.flush()
            updated_cases = {
                case_row.case_id: self._case_from_record(case_row)
                for assignment_row in care_rows
                if (case_row := db.get(ChildCaseRecord, assignment_row.case_id)) is not None
            }
            updated_assignments = {
                assignment_row.assignment_id: self._care_team_assignment_from_record(assignment_row)
                for assignment_row in care_rows
            }
            db.commit()

        self.memberships[membership.membership_id] = membership
        self.cases.update(updated_cases)
        self.care_team_assignments.update(updated_assignments)
        self.audit_log.append(audit)
        return self.clone(membership)

    def create_invitation(
        self,
        organization_id: str,
        payload: OrganizationInvitationCreate,
        *,
        actor_id: str,
    ) -> OrganizationInvitation:
        now = _utc_now()
        invitation = OrganizationInvitation(
            invitation_id=new_id("inv"),
            organization_id=organization_id,
            email=payload.email,
            display_name=payload.display_name,
            role=payload.role,
            invited_by=actor_id,
            expires_at=now + timedelta(days=INVITATION_EXPIRY_DAYS),
            created_at=now,
        )
        audit = validate_audit_event(
            actor_id=actor_id,
            action="invitation.create",
            target_id=invitation.invitation_id,
            outcome="success",
            correlation_id=f"invitation-create-{invitation.invitation_id}",
            message="Organization invitation created.",
        ).as_dict()
        audit["organization_id"] = organization_id
        with self.SessionLocal() as db:
            if db.get(OrganizationRecord, organization_id) is None:
                db.add(OrganizationRecord(organization_id=organization_id, name=organization_id, pilot_mode=False, created_at=now))
            db.add(self._invitation_to_record(invitation))
            db.add(self._audit_to_record(audit))
            db.commit()

        self.invitations[invitation.invitation_id] = invitation
        self.audit_log.append(audit)
        return self.clone(invitation)

    def accept_invitation(
        self,
        organization_id: str,
        invitation_id: str,
        payload: OrganizationInvitationAccept,
        *,
        actor_id: str,
    ) -> OrganizationInvitation:
        now = _utc_now()
        with self.SessionLocal() as db:
            row = db.get(OrganizationInvitationRecord, invitation_id)
            if row is None or row.organization_id != organization_id:
                raise KeyError(invitation_id)
            expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
            if row.status == "accepted":
                raise ValueError("Invitation has already been accepted.")
            if row.status == "revoked":
                raise ValueError("Invitation has been revoked.")
            if expires_at <= now:
                row.status = "expired"
                outcome = "denied"
                message = "Organization invitation acceptance failed."
                invitation = self._invitation_from_record(row)
                error_detail = "Expired invitations require a newly issued invitation."
            else:
                conflicting_identity = (
                    db.query(OrganizationInvitationRecord)
                    .filter(
                        OrganizationInvitationRecord.email == row.email,
                        OrganizationInvitationRecord.accepted_user_id.is_not(None),
                        OrganizationInvitationRecord.accepted_user_id != payload.user_id,
                    )
                    .first()
                )
                if conflicting_identity is not None:
                    outcome = "denied"
                    message = "Organization invitation acceptance failed."
                    invitation = self._invitation_from_record(row)
                    error_detail = "Identity email is already bound to a different user."
                else:
                    row.status = "accepted"
                    row.accepted_user_id = payload.user_id
                    row.accepted_at = now
                    if db.get(UserProfileRecord, payload.user_id) is None:
                        db.add(UserProfileRecord(user_id=payload.user_id, display_name=row.display_name, created_at=now))
                    membership_row = (
                        db.query(OrganizationMembershipRecord)
                        .filter_by(organization_id=organization_id, user_id=payload.user_id)
                        .one_or_none()
                    )
                    if membership_row is None:
                        membership_row = OrganizationMembershipRecord(
                            membership_id=new_id("mbr"),
                            organization_id=organization_id,
                            user_id=payload.user_id,
                            role=row.role,
                            active=True,
                            created_at=now,
                        )
                        db.add(membership_row)
                    else:
                        membership_row.role = row.role
                        membership_row.active = True
                    outcome = "success"
                    message = "Organization invitation accepted."
                    invitation = self._invitation_from_record(row)
                    error_detail = None
            audit = validate_audit_event(
                actor_id=actor_id,
                action="invitation.accept",
                target_id=invitation.invitation_id,
                outcome=outcome,
                correlation_id=f"invitation-accept-{invitation.invitation_id}",
                message=message,
            ).as_dict()
            audit["organization_id"] = organization_id
            db.add(self._audit_to_record(audit))
            db.flush()
            invitation = self._invitation_from_record(row)
            accepted_membership = None
            if error_detail is None:
                accepted_membership = self._membership_from_record(
                    membership_row, display_name=row.display_name
                )
            db.commit()

        if error_detail is not None:
            self.invitations[invitation.invitation_id] = invitation
            self.audit_log.append(audit)
            raise ValueError(error_detail)
        self.invitations[invitation.invitation_id] = invitation
        if accepted_membership is not None:
            self.memberships[accepted_membership.membership_id] = accepted_membership
        self.audit_log.append(audit)
        return self.clone(invitation)

    def audit_break_glass_case_access(self, organization_id: str, case_id: str, *, actor_id: str) -> None:
        with self.SessionLocal() as db:
            case_row = db.get(ChildCaseRecord, case_id)
            if case_row is None or case_row.organization_id != organization_id:
                raise KeyError(case_id)
            audit = validate_audit_event(
                actor_id=actor_id,
                action="break_glass.case_access",
                target_id=case_id,
                outcome="success",
                correlation_id=f"break-glass-case-{case_id}",
                message="Scoped break-glass case access granted.",
            ).as_dict()
            audit["organization_id"] = organization_id
            db.add(self._audit_to_record(audit))
            db.commit()
        self.audit_log.append(audit)

    def assign_care_team_member(
        self,
        case_id: str,
        payload: CareTeamAssignmentCreate,
        *,
        actor_id: str,
    ) -> CareTeamAssignment:
        now = _utc_now()
        if payload.is_primary and (not payload.active or payload.role != "therapist"):
            raise ValueError("Primary therapist assignment must be an active therapist.")
        with self.SessionLocal() as db:
            case_row = db.query(ChildCaseRecord).filter(
                ChildCaseRecord.case_id == case_id
            ).with_for_update().one_or_none()
            if case_row is None:
                raise KeyError(case_id)
            membership_row = db.query(OrganizationMembershipRecord).filter_by(
                organization_id=case_row.organization_id, user_id=payload.user_id, active=True
            ).with_for_update().one_or_none()
            if membership_row is None:
                raise ValueError("Active organization membership required.")
            row = (
                db.query(CaseCareTeamAssignmentRecord)
                .filter_by(organization_id=case_row.organization_id, case_id=case_id, user_id=payload.user_id)
                .one_or_none()
            )
            if row is None:
                assignment = CareTeamAssignment(
                    assignment_id=new_id("team"),
                    organization_id=case_row.organization_id,
                    case_id=case_id,
                    user_id=payload.user_id,
                    role=payload.role,
                    active=payload.active,
                    is_primary=payload.is_primary,
                    created_at=now,
                )
                row = self._care_team_assignment_to_record(assignment)
                db.add(row)
            else:
                row.role = payload.role
                row.active = payload.active
                assignment = self._care_team_assignment_from_record(row).model_copy(update={"is_primary": payload.is_primary})

            care_team = list(case_row.care_team_user_ids or [])
            if payload.active and payload.user_id not in care_team:
                care_team.append(payload.user_id)
            if not payload.active and payload.user_id in care_team:
                care_team = [user_id for user_id in care_team if user_id != payload.user_id]
            case_row.care_team_user_ids = care_team
            if payload.is_primary:
                case_row.primary_therapist_user_id = payload.user_id
            elif case_row.primary_therapist_user_id == payload.user_id and (not payload.active or payload.role != "therapist"):
                case_row.primary_therapist_user_id = None
            case_row.updated_at = now

            audit = validate_audit_event(
                actor_id=actor_id,
                action="care_team.assign",
                target_id=assignment.assignment_id,
                outcome="success",
                correlation_id=f"care-team-assign-{assignment.assignment_id}",
                message="Case care-team assignment updated.",
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            db.add(self._audit_to_record(audit))
            db.flush()
            updated_case = self._case_from_record(case_row)
            db.commit()

        assignment = assignment.model_copy(update={"is_primary": updated_case.primary_therapist_user_id == assignment.user_id})
        self.care_team_assignments[assignment.assignment_id] = assignment
        self.cases[case_id] = updated_case
        self.audit_log.append(audit)
        return self.clone(assignment)

    def create_session(self, case_id: str, payload: TherapySessionCreate, *, actor_id: str) -> TherapySession:
        now = _utc_now()
        with self.SessionLocal() as db:
            case_row = self._lock_case_row(db, case_id)
            session = TherapySession(
                session_id=new_id("session"),
                case_id=case_id,
                organization_id=case_row.organization_id,
                **payload.model_dump(),
                created_at=now,
                updated_at=now,
            )
            audit = validate_audit_event(
                actor_id=actor_id,
                action="session.create",
                target_id=session.session_id,
                outcome="success",
                correlation_id=f"session-create-{session.version}",
                message="Session created.",
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            case_row.latest_session_date = session.session_date
            case_row.latest_session_status = session.status.value if hasattr(session.status, "value") else str(session.status)
            case_row.updated_at = now
            db.add(self._session_to_record(session))
            db.add(self._audit_to_record(audit))
            db.flush()
            updated_case = self._case_from_record(case_row)
            db.commit()
        self.sessions[session.session_id] = session
        self.cases[case_id] = updated_case
        self.audit_log.append(audit)
        return self.clone(session)

    def update_session(
        self,
        session_id: str,
        patch: TherapySessionUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> TherapySession:
        now = _utc_now()
        patch_values = patch.model_dump(exclude_unset=True)
        with self.SessionLocal() as db:
            case_id = db.query(SessionRecord.case_id).filter(SessionRecord.session_id == session_id).scalar()
            if case_id is None:
                raise KeyError(session_id)
            case_row = self._lock_case_row(db, case_id)
            row = (
                db.query(SessionRecord)
                .filter(SessionRecord.session_id == session_id)
                .with_for_update()
                .one()
            )
            compare_version = row.version if expected_version is None else expected_version
            if row.version != compare_version:
                raise SessionVersionConflictError(
                    f"Session {session_id} expected version {expected_version}, found {row.version}."
                )
            normalized_patch = {
                field: value.value if hasattr(value, "value") else value
                for field, value in patch_values.items()
            }
            updated = self._session_from_record(row).model_copy(
                update={**normalized_patch, "version": compare_version + 1, "updated_at": now}
            )
            changed = (
                db.query(SessionRecord)
                .filter(SessionRecord.session_id == session_id, SessionRecord.version == compare_version)
                .update(
                    normalized_patch | {"version": compare_version + 1, "updated_at": now},
                    synchronize_session=False,
                )
            )
            if changed != 1:
                raise SessionVersionConflictError("Session changed; reload and retry.")
            audit = validate_audit_event(
                actor_id=actor_id,
                action="session.patch",
                target_id=session_id,
                outcome="success",
                correlation_id=f"session-update-{updated.version}",
                message="Session updated.",
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            db.add(self._audit_to_record(audit))
            db.flush()
            db.commit()
        self.sessions[session_id] = updated
        self.audit_log.append(audit)
        return self.clone(updated)

    def create_transcript(
        self,
        transcript: Transcript,
        *,
        session_status: ReviewStatus,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Transcript:
        with self.SessionLocal() as db:
            case_row = self._lock_case_row(db, transcript.case_id)
            session_row = db.get(SessionRecord, transcript.session_id)
            if session_row is None or session_row.case_id != case_row.case_id:
                raise KeyError(transcript.session_id)
            saved_transcript = transcript.model_copy(update={"organization_id": case_row.organization_id})
            audit = validate_audit_event(
                actor_id=actor_id,
                action=audit_action,
                target_id=saved_transcript.transcript_id,
                outcome="success",
                correlation_id=f"transcript-create-{saved_transcript.version}",
                message=audit_message,
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            invalidated = self._mark_downstream_rows_stale(db, session_row)
            session_row.transcript_id = saved_transcript.transcript_id
            session_row.status = session_status.value if hasattr(session_status, "value") else str(session_status)
            session_row.updated_at = _utc_now()
            db.add(self._transcript_to_record(saved_transcript))
            db.add(self._audit_to_record(audit))
            invalidation_audit = self._downstream_invalidation_audit(actor_id, saved_transcript.transcript_id, saved_transcript.version).as_dict() if invalidated else None
            if invalidation_audit is not None:
                invalidation_audit["organization_id"] = case_row.organization_id
                db.add(self._audit_to_record(invalidation_audit))
            db.flush()
            updated_session = self._session_from_record(session_row)
            db.commit()
        self.sessions[saved_transcript.session_id] = updated_session
        self._mark_downstream_outputs_stale(self.sessions[saved_transcript.session_id])
        self.transcripts[saved_transcript.transcript_id] = saved_transcript
        self.audit_log.append(audit)
        if invalidation_audit is not None:
            self.audit_log.append(invalidation_audit)
        return self.clone(saved_transcript)

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
        with self.SessionLocal() as db:
            case_id = db.query(TranscriptRecord.case_id).filter(
                TranscriptRecord.transcript_id == transcript.transcript_id
            ).scalar()
            if case_id is None:
                raise KeyError(transcript.transcript_id)
            case_row = self._lock_case_row(db, case_id)
            row = (
                db.query(TranscriptRecord)
                .filter(TranscriptRecord.transcript_id == transcript.transcript_id)
                .with_for_update()
                .one()
            )
            if (
                row.case_id != transcript.case_id
                or row.session_id != transcript.session_id
                or row.organization_id != case_row.organization_id
            ):
                raise ValueError("Transcript ownership changed; reload and retry.")
            compare_version = row.version if expected_version is None else expected_version
            if row.version != compare_version:
                raise TranscriptVersionConflictError(
                    f"Transcript {transcript.transcript_id} expected version {expected_version}, found {row.version}."
                )
            if transcript.version not in {compare_version, compare_version + 1}:
                raise TranscriptVersionConflictError("Transcript version changed unexpectedly.")
            session_row = db.get(SessionRecord, transcript.session_id)
            if session_row is None or session_row.case_id != case_row.case_id:
                raise KeyError(transcript.session_id)
            saved = transcript.model_copy(update={"organization_id": case_row.organization_id})
            replacement = self._transcript_to_record(saved)
            values = {
                column.name: getattr(replacement, column.name)
                for column in TranscriptRecord.__table__.columns
                if not column.primary_key
            }
            changed = (
                db.query(TranscriptRecord)
                .filter(
                    TranscriptRecord.transcript_id == transcript.transcript_id,
                    TranscriptRecord.version == compare_version,
                )
                .update(values, synchronize_session=False)
            )
            if changed != 1:
                raise TranscriptVersionConflictError("Transcript changed; reload and retry.")
            invalidated = self._mark_downstream_rows_stale(db, session_row) if invalidate_downstream else False
            session_row.status = session_status.value if hasattr(session_status, "value") else str(session_status)
            session_row.updated_at = _utc_now()
            audit = validate_audit_event(
                actor_id=actor_id,
                action=audit_action,
                target_id=saved.transcript_id,
                outcome="success",
                correlation_id=f"transcript-update-{saved.version}",
                message=audit_message,
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            db.add(self._audit_to_record(audit))
            invalidation_audit = self._downstream_invalidation_audit(actor_id, saved.transcript_id, saved.version).as_dict() if invalidated else None
            if invalidation_audit is not None:
                invalidation_audit["organization_id"] = case_row.organization_id
                db.add(self._audit_to_record(invalidation_audit))
            db.flush()
            updated_session = self._session_from_record(session_row)
            db.commit()
        self.transcripts[saved.transcript_id] = saved
        self.sessions[saved.session_id] = updated_session
        if invalidate_downstream:
            self._mark_downstream_outputs_stale(self.sessions[saved.session_id])
        self.audit_log.append(audit)
        if invalidation_audit is not None:
            self.audit_log.append(invalidation_audit)
        return self.clone(saved)

    def get_latest_speaker_mapping(self, transcript_id: str) -> SpeakerMapping | None:
        """Read the current persisted mapping instead of a possibly stale mirror."""

        with self.SessionLocal() as db:
            row = (
                db.query(SpeakerMappingRecord)
                .filter(SpeakerMappingRecord.transcript_id == transcript_id)
                .order_by(
                    SpeakerMappingRecord.mapping_version.desc(),
                    SpeakerMappingRecord.mapping_id.desc(),
                )
                .first()
            )
            mapping = self._speaker_mapping_from_record(row) if row is not None else None
        if mapping is not None:
            with self._lock:
                self.speaker_mappings[mapping.mapping_id] = mapping
            return self.clone(mapping)
        return None

    def save_speaker_mapping_draft(
        self,
        mapping: SpeakerMapping,
        *,
        expected_mapping_version: int | None,
        actor_id: str,
    ) -> SpeakerMapping:
        """Persist one current-version draft and its audit event atomically."""

        saved_mapping_id = mapping.mapping_id
        try:
            with self.SessionLocal() as db:
                case_id = db.query(TranscriptRecord.case_id).filter(
                    TranscriptRecord.transcript_id == mapping.transcript_id
                ).scalar()
                if case_id is None:
                    raise KeyError(mapping.transcript_id)
                case_row = self._lock_case_row(db, case_id)
                transcript_row = (
                    db.query(TranscriptRecord)
                    .filter(TranscriptRecord.transcript_id == mapping.transcript_id)
                    .with_for_update()
                    .one()
                )
                if transcript_row.organization_id != case_row.organization_id:
                    raise SpeakerMappingVersionConflictError(
                        "Speaker mapping ownership changed; reload and retry."
                    )
                if transcript_row.version != mapping.source_transcript_version:
                    raise TranscriptVersionConflictError(
                        f"Transcript {mapping.transcript_id} expected version "
                        f"{mapping.source_transcript_version}, found {transcript_row.version}."
                    )

                latest_row = (
                    db.query(SpeakerMappingRecord)
                    .filter(SpeakerMappingRecord.transcript_id == mapping.transcript_id)
                    .order_by(
                        SpeakerMappingRecord.mapping_version.desc(),
                        SpeakerMappingRecord.mapping_id.desc(),
                    )
                    .first()
                )
                current_draft = (
                    latest_row
                    if latest_row is not None
                    and latest_row.status == MappingPersistedStatus.draft.value
                    and latest_row.source_transcript_version == transcript_row.version
                    else None
                )
                if current_draft is None and expected_mapping_version is not None:
                    raise SpeakerMappingVersionConflictError(
                        "Speaker mapping draft version changed; reload and retry."
                    )
                if current_draft is not None and current_draft.mapping_version != expected_mapping_version:
                    raise SpeakerMappingVersionConflictError(
                        "Speaker mapping draft version changed; reload and retry."
                    )
                if (
                    current_draft is None
                    and latest_row is not None
                    and latest_row.status == MappingPersistedStatus.confirmed.value
                    and latest_row.applied_transcript_version == transcript_row.version
                ):
                    raise SpeakerMappingVersionConflictError(
                        "Speaker mapping is already confirmed for this transcript version."
                    )

                now = utc_now()
                saved = mapping.model_copy(deep=True)
                saved.organization_id = transcript_row.organization_id
                saved.transcript_id = transcript_row.transcript_id
                saved.status = MappingPersistedStatus.draft
                saved.applied_transcript_version = None
                saved.confirmed_by_user_id = None
                saved.confirmed_by_role = None
                saved.confirmed_at = None
                saved.updated_at = now
                saved.mapping_version = (latest_row.mapping_version + 1) if latest_row is not None else 1

                if current_draft is None:
                    db.add(self._speaker_mapping_to_record(saved))
                else:
                    saved_mapping_id = current_draft.mapping_id
                    saved.mapping_id = saved_mapping_id
                    saved.created_at = _as_utc(current_draft.created_at)
                    updated_count = (
                        db.query(SpeakerMappingRecord)
                        .filter(
                            SpeakerMappingRecord.mapping_id == current_draft.mapping_id,
                            SpeakerMappingRecord.mapping_version == expected_mapping_version,
                            SpeakerMappingRecord.status == MappingPersistedStatus.draft.value,
                            SpeakerMappingRecord.source_transcript_version == transcript_row.version,
                        )
                        .update(
                            {
                                SpeakerMappingRecord.organization_id: transcript_row.organization_id,
                                SpeakerMappingRecord.mapping_version: saved.mapping_version,
                                SpeakerMappingRecord.entries: [
                                    entry.model_dump(mode="json") for entry in saved.entries
                                ],
                                SpeakerMappingRecord.applied_transcript_version: None,
                                SpeakerMappingRecord.confirmed_by_user_id: None,
                                SpeakerMappingRecord.confirmed_by_role: None,
                                SpeakerMappingRecord.confirmed_at: None,
                                SpeakerMappingRecord.updated_at: now,
                            },
                            synchronize_session=False,
                        )
                    )
                    if updated_count != 1:
                        raise SpeakerMappingVersionConflictError(
                            "Speaker mapping draft version changed; reload and retry."
                        )

                audit = validate_audit_event(
                    actor_id=actor_id,
                    action="speaker_mapping.draft_save",
                    target_id=saved_mapping_id,
                    outcome="success",
                    correlation_id=f"speaker-mapping-draft-{saved_mapping_id}-v{saved.mapping_version}",
                    message="Speaker mapping draft saved.",
                ).as_dict()
                audit["organization_id"] = transcript_row.organization_id
                db.add(self._audit_to_record(audit))
                db.flush()
                db.commit()
        except IntegrityError as exc:
            if _is_speaker_mapping_version_integrity_error(exc):
                raise SpeakerMappingVersionConflictError(
                    "Speaker mapping draft version changed; reload and retry."
                ) from exc
            raise

        with self._lock:
            self.speaker_mappings[saved_mapping_id] = saved
            self.audit_log.append(audit)
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
        """Confirm the authoritative persisted draft and transcript in one transaction."""

        invalidation_audit: dict | None = None
        try:
            with self.SessionLocal() as db:
                case_id = db.query(TranscriptRecord.case_id).filter(
                    TranscriptRecord.transcript_id == transcript.transcript_id
                ).scalar()
                if case_id is None:
                    raise KeyError(transcript.transcript_id)
                case_row = self._lock_case_row(db, case_id)
                transcript_row = (
                    db.query(TranscriptRecord)
                    .filter(TranscriptRecord.transcript_id == transcript.transcript_id)
                    .with_for_update()
                    .one()
                )
                if transcript_row.version != expected_transcript_version:
                    raise TranscriptVersionConflictError(
                        f"Transcript {transcript.transcript_id} expected version "
                        f"{expected_transcript_version}, found {transcript_row.version}."
                    )
                latest_row = (
                    db.query(SpeakerMappingRecord)
                    .filter(SpeakerMappingRecord.transcript_id == transcript_row.transcript_id)
                    .order_by(
                        SpeakerMappingRecord.mapping_version.desc(),
                        SpeakerMappingRecord.mapping_id.desc(),
                    )
                    .first()
                )
                if (
                    latest_row is None
                    or latest_row.mapping_id != mapping.mapping_id
                    or latest_row.mapping_version != expected_mapping_version
                    or latest_row.source_transcript_version != expected_transcript_version
                    or latest_row.status != MappingPersistedStatus.draft.value
                ):
                    raise SpeakerMappingVersionConflictError(
                        "Speaker mapping version changed; reload and retry."
                    )
                session_row = db.get(SessionRecord, transcript_row.session_id)
                if session_row is None:
                    raise KeyError(transcript_row.session_id)
                if (
                    session_row.case_id != transcript_row.case_id
                    or session_row.organization_id != transcript_row.organization_id
                    or case_row.organization_id != transcript_row.organization_id
                    or latest_row.organization_id != transcript_row.organization_id
                    or latest_row.transcript_id != transcript_row.transcript_id
                ):
                    raise SpeakerMappingVersionConflictError(
                        "Speaker mapping ownership changed; reload and retry."
                    )

                current = self._transcript_from_record(transcript_row)
                latest = self._speaker_mapping_from_record(latest_row)
                if (
                    mapping.transcript_id != current.transcript_id
                    or mapping.source_transcript_version != expected_transcript_version
                    or mapping.mapping_version != latest.mapping_version
                    or mapping.status != MappingPersistedStatus.confirmed
                    or mapping.confirmed_by_user_id != actor_id
                    or not mapping.confirmed_by_role
                ):
                    raise SpeakerMappingVersionConflictError(
                        "Speaker mapping confirmation payload is inconsistent."
                    )

                from app.services.speaker_mapping_service import (
                    build_confirmed_transcript,
                    validate_mapping_confirmation,
                )

                validate_mapping_confirmation(current, latest)
                rebuilt = build_confirmed_transcript(current, latest)
                immutable_mapping_fields_match = (
                    mapping.mapping_id == latest.mapping_id
                    and mapping.organization_id == latest.organization_id
                    and mapping.transcript_id == latest.transcript_id
                    and mapping.source_transcript_version == latest.source_transcript_version
                    and mapping.mapping_version == latest.mapping_version
                    and mapping.entries == latest.entries
                )
                volatile_rebuild_fields = {"updated_at"}
                submitted_transcript_matches = transcript.model_dump(
                    exclude=volatile_rebuild_fields
                ) == rebuilt.model_dump(exclude=volatile_rebuild_fields)
                if not immutable_mapping_fields_match or not submitted_transcript_matches:
                    raise SpeakerMappingVersionConflictError(
                        "Speaker mapping confirmation payload is inconsistent."
                    )

                now = utc_now()
                correlation_id = f"speaker_mapping_confirm_{uuid4().hex[:10]}"
                invalidated = self._mark_downstream_rows_stale(db, session_row)
                session_row.status = ReviewStatus.needs_review.value
                session_row.updated_at = now
                self._recompute_case_summary_rows(db, case_row)

                mapping_updated = (
                    db.query(SpeakerMappingRecord)
                    .filter(
                        SpeakerMappingRecord.mapping_id == latest.mapping_id,
                        SpeakerMappingRecord.transcript_id == current.transcript_id,
                        SpeakerMappingRecord.organization_id == current.organization_id,
                        SpeakerMappingRecord.mapping_version == expected_mapping_version,
                        SpeakerMappingRecord.source_transcript_version == expected_transcript_version,
                        SpeakerMappingRecord.status == MappingPersistedStatus.draft.value,
                    )
                    .update(
                        {
                            SpeakerMappingRecord.mapping_version: expected_mapping_version + 1,
                            SpeakerMappingRecord.status: MappingPersistedStatus.confirmed.value,
                            SpeakerMappingRecord.applied_transcript_version: rebuilt.version,
                            SpeakerMappingRecord.confirmed_by_user_id: actor_id,
                            SpeakerMappingRecord.confirmed_by_role: mapping.confirmed_by_role,
                            SpeakerMappingRecord.confirmed_at: now,
                            SpeakerMappingRecord.updated_at: now,
                        },
                        synchronize_session=False,
                    )
                )
                if mapping_updated != 1:
                    raise SpeakerMappingVersionConflictError(
                        "Speaker mapping version changed; reload and retry."
                    )

                transcript_updated = (
                    db.query(TranscriptRecord)
                    .filter(
                        TranscriptRecord.transcript_id == current.transcript_id,
                        TranscriptRecord.organization_id == current.organization_id,
                        TranscriptRecord.version == expected_transcript_version,
                    )
                    .update(
                        {
                            TranscriptRecord.raw_text: rebuilt.raw_text,
                            TranscriptRecord.utterances: [
                                item.model_dump(mode="json") for item in rebuilt.utterances
                            ],
                            TranscriptRecord.qa_status: rebuilt.qa_status.value,
                            TranscriptRecord.qa_issues: [],
                            TranscriptRecord.review_status: rebuilt.review_status.value,
                            TranscriptRecord.therapist_attested: False,
                            TranscriptRecord.attestation_reason: "",
                            TranscriptRecord.version: rebuilt.version,
                            TranscriptRecord.updated_at: rebuilt.updated_at,
                        },
                        synchronize_session=False,
                    )
                )
                if transcript_updated != 1:
                    raise TranscriptVersionConflictError(
                        "Transcript version changed; reload and retry."
                    )

                confirmation_audit = validate_audit_event(
                    actor_id=actor_id,
                    action="speaker_mapping.confirm",
                    target_id=latest.mapping_id,
                    outcome="success",
                    correlation_id=correlation_id,
                    message=(
                        f"Speaker mapping {latest.mapping_id} confirmed for transcript "
                        f"{current.transcript_id} version {expected_transcript_version} "
                        f"to {rebuilt.version}."
                    ),
                ).as_dict()
                confirmation_audit["organization_id"] = current.organization_id
                if invalidated:
                    invalidation_audit = validate_audit_event(
                        actor_id=actor_id,
                        action="workflow.invalidate_downstream",
                        target_id=current.transcript_id,
                        outcome="success",
                        correlation_id=correlation_id,
                        message="Derived workflow outputs marked stale after transcript change.",
                    ).as_dict()
                    invalidation_audit["organization_id"] = current.organization_id
                    db.add(self._audit_to_record(invalidation_audit))
                db.add(self._audit_to_record(confirmation_audit))
                db.flush()

                saved_mapping = latest.model_copy(
                    deep=True,
                    update={
                        "mapping_version": expected_mapping_version + 1,
                        "status": MappingPersistedStatus.confirmed,
                        "applied_transcript_version": rebuilt.version,
                        "confirmed_by_user_id": actor_id,
                        "confirmed_by_role": mapping.confirmed_by_role,
                        "confirmed_at": now,
                        "updated_at": now,
                    },
                )
                saved_transcript = rebuilt.model_copy(
                    deep=True,
                    update={"organization_id": current.organization_id},
                )
                saved_session = self._session_from_record(session_row)
                saved_case = self._case_from_record(case_row)
                saved_feature = None
                if session_row.feature_set_id:
                    feature_row = db.get(FeatureSetRecord, session_row.feature_set_id)
                    if feature_row is not None:
                        saved_feature = self._feature_from_record(feature_row)
                saved_ml_result = None
                if session_row.ml_result_id:
                    ml_row = db.get(MLResultRecord, session_row.ml_result_id)
                    if ml_row is not None:
                        saved_ml_result = MLResult.model_validate(ml_row.payload)
                saved_ai_review = None
                if session_row.ai_review_id:
                    ai_row = db.get(AiReviewRecord, session_row.ai_review_id)
                    if ai_row is not None:
                        saved_ai_review = AiReview.model_validate(ai_row.payload)
                saved_report = None
                if session_row.report_id:
                    report_row = db.get(ReportRecord, session_row.report_id)
                    if report_row is not None:
                        saved_report = self._report_from_record(report_row)
                db.commit()
        except IntegrityError as exc:
            if _is_speaker_mapping_version_integrity_error(exc):
                raise SpeakerMappingVersionConflictError(
                    "Speaker mapping version changed; reload and retry."
                ) from exc
            raise

        with self._lock:
            self.transcripts[saved_transcript.transcript_id] = saved_transcript
            self.speaker_mappings[saved_mapping.mapping_id] = saved_mapping
            self.sessions[saved_session.session_id] = saved_session
            self.cases[saved_case.case_id] = saved_case
            if saved_feature is not None:
                self.features[saved_feature.feature_set_id] = saved_feature
            if saved_ml_result is not None:
                self.ml_results[saved_ml_result.result_id] = saved_ml_result
            if saved_ai_review is not None:
                self.ai_reviews[saved_ai_review.ai_review_id] = saved_ai_review
            if saved_report is not None:
                self.reports[saved_report.report_id] = saved_report
            if invalidation_audit is not None:
                self.audit_log.append(invalidation_audit)
            self.audit_log.append(confirmation_audit)
        return self.clone(saved_mapping)

    @staticmethod
    def _recompute_case_summary_rows(db, case_row: ChildCaseRecord) -> None:
        sessions = db.query(SessionRecord).filter(SessionRecord.case_id == case_row.case_id).all()
        if sessions:
            latest_session = max(
                sessions,
                key=lambda item: (item.session_date, item.created_at, item.session_id),
            )
            case_row.latest_session_date = latest_session.session_date
            case_row.latest_session_status = latest_session.status
        report_sessions = [item for item in sessions if item.report_id]
        if report_sessions:
            report_rows = {
                row.report_id: row
                for row in db.query(ReportRecord)
                .filter(ReportRecord.report_id.in_([item.report_id for item in report_sessions]))
                .all()
            }
            report_sessions = [item for item in report_sessions if item.report_id in report_rows]
            if report_sessions:
                latest_report_session = max(
                    report_sessions,
                    key=lambda item: (
                        item.session_date,
                        item.created_at,
                        report_rows[item.report_id].created_at,
                        item.session_id,
                    ),
                )
                case_row.latest_report_status = report_rows[latest_report_session.report_id].status
        case_row.updated_at = utc_now()

    @staticmethod
    def _mark_downstream_rows_stale(db, session_row: SessionRecord) -> bool:
        invalidated = False
        feature_row = db.get(FeatureSetRecord, session_row.feature_set_id) if session_row.feature_set_id else None
        if feature_row is not None and feature_row.review_status != ReviewStatus.stale.value:
            feature_row.review_status = ReviewStatus.stale.value
            invalidated = True

        ml_row = db.get(MLResultRecord, session_row.ml_result_id) if session_row.ml_result_id else None
        if ml_row is not None and (ml_row.payload or {}).get("is_current", True):
            payload = dict(ml_row.payload or {})
            payload["is_current"] = False
            ml_row.payload = payload
            invalidated = True

        ai_row = db.get(AiReviewRecord, session_row.ai_review_id) if session_row.ai_review_id else None
        if ai_row is not None and ai_row.therapist_review_status != ReviewStatus.stale.value:
            payload = dict(ai_row.payload or {})
            payload["therapist_review_status"] = ReviewStatus.stale.value
            ai_row.payload = payload
            ai_row.therapist_review_status = ReviewStatus.stale.value
            invalidated = True

        report_row = db.get(ReportRecord, session_row.report_id) if session_row.report_id else None
        if report_row is not None and report_row.status not in {ReviewStatus.signed_off.value, ReviewStatus.stale.value}:
            report_row.status = ReviewStatus.stale.value
            report_row.version += 1
            report_row.updated_at = _utc_now()
            case_row = db.get(ChildCaseRecord, session_row.case_id)
            if case_row is not None:
                case_row.latest_report_status = ReviewStatus.stale.value
            invalidated = True
        return invalidated

    @staticmethod
    def _downstream_invalidation_audit(actor_id: str, transcript_id: str, version: int):
        return validate_audit_event(
            actor_id=actor_id,
            action="workflow.invalidate_downstream",
            target_id=transcript_id,
            outcome="success",
            correlation_id=f"workflow-invalidate-{version}",
            message="Derived workflow outputs marked stale after transcript change.",
        )

    def create_report(
        self,
        report: Report,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report:
        with self.SessionLocal() as db:
            case_row = self._lock_case_row(db, report.case_id)
            session_row = db.get(SessionRecord, report.session_id)
            if session_row is None or session_row.case_id != case_row.case_id:
                raise KeyError(report.session_id)
            saved_report = report.model_copy(update={"organization_id": case_row.organization_id})
            audit = validate_audit_event(
                actor_id=actor_id,
                action=audit_action,
                target_id=saved_report.report_id,
                outcome="success",
                correlation_id=f"report-create-{saved_report.version}",
                message=audit_message,
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            transcript_row = db.get(TranscriptRecord, report.transcript_id) if report.transcript_id else None
            expected_transcript_version = report.generated_from_versions.get("transcript_version")
            if report.transcript_id and (
                transcript_row is None
                or session_row.transcript_id != report.transcript_id
                or expected_transcript_version != str(transcript_row.version)
            ):
                raise ValueError("Transcript changed during report generation; discard the stale draft and retry.")
            feature_row = db.get(FeatureSetRecord, report.feature_result_id) if report.feature_result_id else None
            if report.feature_result_id and (
                session_row.feature_set_id != report.feature_result_id
                or feature_row is None
                or feature_row.review_status == ReviewStatus.stale.value
                or transcript_row is None
                or feature_row.transcript_version != transcript_row.version
            ):
                raise ValueError("Findings changed during report generation; discard the stale draft and retry.")
            session_row.report_id = report.report_id
            session_row.updated_at = _utc_now()
            case_row.latest_report_status = report.status.value if hasattr(report.status, "value") else str(report.status)
            case_row.updated_at = _utc_now()
            db.add(self._report_to_record(saved_report))
            db.add(self._audit_to_record(audit))
            db.flush()
            updated_session = self._session_from_record(session_row)
            updated_case = self._case_from_record(case_row)
            db.commit()
        self.reports[saved_report.report_id] = saved_report
        self.sessions[saved_report.session_id] = updated_session
        self.cases[saved_report.case_id] = updated_case
        self.audit_log.append(audit)
        return self.clone(saved_report)

    def update_report(
        self,
        report: Report,
        *,
        expected_version: int | None,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report:
        with self.SessionLocal() as db:
            case_row = self._lock_case_row(db, report.case_id)
            row = db.get(ReportRecord, report.report_id)
            if row is None or row.case_id != case_row.case_id:
                raise KeyError(report.report_id)
            if row.status == ReviewStatus.signed_off.value:
                raise ReportVersionConflictError(
                    "Finalized reports are immutable; create a revision instead."
                )
            compare_version = row.version if expected_version is None else expected_version
            if row.version != compare_version:
                raise ReportVersionConflictError(
                    f"Report {report.report_id} expected version {expected_version}, found {row.version}."
                )
            saved_report = report.model_copy(update={"organization_id": case_row.organization_id})
            record = self._report_to_record(saved_report)
            values = {
                column.name: getattr(record, column.name)
                for column in ReportRecord.__table__.columns
                if column.name != "report_id"
            }
            changed = db.query(ReportRecord).filter(
                ReportRecord.report_id == report.report_id,
                ReportRecord.version == compare_version,
            ).update(values, synchronize_session=False)
            if changed != 1:
                raise ReportVersionConflictError("Report changed; reload and retry.")
            case_row.latest_report_status = saved_report.status.value if hasattr(saved_report.status, "value") else str(saved_report.status)
            case_row.updated_at = _utc_now()
            audit = validate_audit_event(
                actor_id=actor_id,
                action=audit_action,
                target_id=saved_report.report_id,
                outcome="success",
                correlation_id=f"report-update-{saved_report.version}",
                message=audit_message,
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            db.add(self._audit_to_record(audit))
            db.flush()
            updated_case = self._case_from_record(case_row)
            db.commit()
        self.reports[saved_report.report_id] = saved_report
        self.cases[saved_report.case_id] = updated_case
        self.audit_log.append(audit)
        return self.clone(saved_report)

    def create_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal:
        with self.SessionLocal() as db:
            case_row = self._lock_case_row(db, goal.case_id)
            saved_goal = goal.model_copy(update={"organization_id": case_row.organization_id})
            audit = validate_audit_event(
                actor_id=actor_id,
                action=audit_action,
                target_id=saved_goal.goal_id,
                outcome="success",
                correlation_id=f"therapy-goal-create-{saved_goal.goal_id}",
                message=audit_message,
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            db.add(self._goal_to_record(saved_goal))
            db.add(self._audit_to_record(audit))
            db.flush()
            db.commit()
        self.therapy_goals[saved_goal.goal_id] = saved_goal
        self.audit_log.append(audit)
        return self.clone(saved_goal)

    def update_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal:
        with self.SessionLocal() as db:
            case_id = db.query(TherapyGoalRecord.case_id).filter(
                TherapyGoalRecord.goal_id == goal.goal_id
            ).scalar()
            if case_id is None:
                raise KeyError(goal.goal_id)
            case_row = self._lock_case_row(db, case_id)
            row = db.query(TherapyGoalRecord).filter(
                TherapyGoalRecord.goal_id == goal.goal_id
            ).with_for_update().one_or_none()
            if row is None:
                raise KeyError(goal.goal_id)
            if goal.case_id != case_id:
                raise ValueError("Therapy goal cannot be moved between cases.")
            saved_goal = goal.model_copy(update={"organization_id": case_row.organization_id})
            row.case_id = saved_goal.case_id
            row.title = saved_goal.title
            row.target = saved_goal.target
            row.status = saved_goal.status
            row.notes = saved_goal.notes
            row.retained = saved_goal.retained
            row.created_at = saved_goal.created_at
            row.updated_at = saved_goal.updated_at
            audit = validate_audit_event(
                actor_id=actor_id, action=audit_action, target_id=saved_goal.goal_id,
                outcome="success", correlation_id=f"therapy-goal-update-{saved_goal.goal_id}",
                message=audit_message,
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            db.add(self._audit_to_record(audit))
            db.flush()
            updated = self._goal_from_record(row)
            db.commit()
        self.therapy_goals[goal.goal_id] = updated
        self.audit_log.append(audit)
        return self.clone(updated)

    def create_privacy_operation(
        self,
        operation: PrivacyOperation,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> PrivacyOperation:
        with self.SessionLocal() as db:
            case_row = self._lock_case_row(db, operation.case_id, require_consent=False)
            saved_operation = operation.model_copy(update={"organization_id": case_row.organization_id})
            audit = validate_audit_event(
                actor_id=actor_id, action=audit_action, target_id=saved_operation.privacy_operation_id,
                outcome="success", correlation_id=f"privacy-operation-create-{saved_operation.privacy_operation_id}",
                message=audit_message,
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            db.add(self._privacy_operation_to_record(saved_operation))
            db.add(self._audit_to_record(audit))
            db.flush()
            db.commit()
        self.privacy_operations[saved_operation.privacy_operation_id] = saved_operation
        self.audit_log.append(audit)
        return self.clone(saved_operation)

    def update_privacy_operation(
        self,
        operation: PrivacyOperation,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> PrivacyOperation:
        with self.SessionLocal() as db:
            case_id = db.query(PrivacyOperationRecord.case_id).filter(
                PrivacyOperationRecord.privacy_operation_id == operation.privacy_operation_id
            ).scalar()
            if case_id is None:
                raise KeyError(operation.privacy_operation_id)
            case_row = self._lock_case_row(db, case_id, require_consent=False)
            row = db.query(PrivacyOperationRecord).filter(
                PrivacyOperationRecord.privacy_operation_id == operation.privacy_operation_id
            ).with_for_update().one_or_none()
            if row is None:
                raise KeyError(operation.privacy_operation_id)
            if operation.case_id != case_id:
                raise ValueError("Privacy operation cannot be moved between cases.")
            saved_operation = operation.model_copy(update={"organization_id": case_row.organization_id})
            record = self._privacy_operation_to_record(saved_operation)
            for column in PrivacyOperationRecord.__table__.columns:
                if column.name != "privacy_operation_id":
                    setattr(row, column.name, getattr(record, column.name))
            audit = validate_audit_event(
                actor_id=actor_id, action=audit_action, target_id=saved_operation.privacy_operation_id,
                outcome="success", correlation_id=f"privacy-operation-update-{saved_operation.privacy_operation_id}",
                message=audit_message,
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            db.add(self._audit_to_record(audit))
            db.flush()
            updated = self._privacy_operation_from_record(row)
            db.commit()
        self.privacy_operations[operation.privacy_operation_id] = updated
        self.audit_log.append(audit)
        return self.clone(updated)

    def create_feature_set(
        self,
        feature_set: FeatureSet,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> FeatureSet:
        with self.SessionLocal() as db:
            case_id = db.query(SessionRecord.case_id).filter(
                SessionRecord.session_id == feature_set.session_id
            ).scalar()
            if case_id is None:
                raise KeyError(feature_set.session_id)
            case_row = self._lock_case_row(db, case_id)
            session_row = db.get(SessionRecord, feature_set.session_id)
            if session_row is None:
                raise KeyError(feature_set.session_id)
            transcript_row = db.get(TranscriptRecord, feature_set.transcript_id)
            if (
                transcript_row is None
                or session_row.transcript_id != feature_set.transcript_id
                or transcript_row.version != feature_set.transcript_version
            ):
                raise ValueError("Transcript changed during feature extraction; discard the stale result and retry.")
            saved_feature = feature_set.model_copy(update={"organization_id": case_row.organization_id})
            audit = validate_audit_event(
                actor_id=actor_id, action=audit_action, target_id=saved_feature.feature_set_id,
                outcome="success", correlation_id=f"feature-set-create-{saved_feature.feature_set_id}",
                message=audit_message,
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            session_row.feature_set_id = saved_feature.feature_set_id
            session_row.ml_result_id = None
            session_row.updated_at = _utc_now()
            db.add(self._feature_to_record(saved_feature))
            db.add(self._audit_to_record(audit))
            db.flush()
            updated_session = self._session_from_record(session_row)
            db.commit()
        self.features[saved_feature.feature_set_id] = saved_feature
        self.sessions[saved_feature.session_id] = updated_session
        self.audit_log.append(audit)
        return self.clone(saved_feature)

    def create_ai_review(
        self,
        review: AiReview,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> AiReview:
        with self.SessionLocal() as db:
            case_id = db.query(SessionRecord.case_id).filter(
                SessionRecord.session_id == review.session_id
            ).scalar()
            if case_id is None:
                raise KeyError(review.session_id)
            case_row = self._lock_case_row(db, case_id)
            session_row = db.get(SessionRecord, review.session_id)
            if session_row is None:
                raise KeyError(review.session_id)
            saved_review = review.model_copy(update={"organization_id": case_row.organization_id})
            audit = validate_audit_event(
                actor_id=actor_id, action=audit_action, target_id=saved_review.ai_review_id,
                outcome="success", correlation_id=f"ai-review-create-{saved_review.ai_review_id}",
                message=audit_message,
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            transcript_row = db.get(TranscriptRecord, session_row.transcript_id) if session_row.transcript_id else None
            feature_row = db.get(FeatureSetRecord, review.feature_set_id) if review.feature_set_id else None
            if transcript_row is None or transcript_row.version != review.input_transcript_version:
                raise ValueError("Transcript changed during AI-assisted review generation; discard the stale result and retry.")
            if review.feature_set_id and (
                session_row.feature_set_id != review.feature_set_id
                or feature_row is None
                or feature_row.review_status == ReviewStatus.stale.value
                or feature_row.transcript_version != transcript_row.version
            ):
                raise ValueError("Findings changed during AI-assisted review generation; discard the stale result and retry.")
            session_row.ai_review_id = review.ai_review_id
            session_row.updated_at = _utc_now()
            case_row.review_priority = review.review_priority
            case_row.updated_at = _utc_now()
            db.add(self._ai_review_to_record(saved_review))
            db.add(self._audit_to_record(audit))
            db.flush()
            updated_session = self._session_from_record(session_row)
            updated_case = self._case_from_record(case_row)
            db.commit()
        self.ai_reviews[saved_review.ai_review_id] = saved_review
        self.sessions[saved_review.session_id] = updated_session
        self.cases[updated_case.case_id] = updated_case
        self.audit_log.append(audit)
        return self.clone(saved_review)

    def update_ai_review(
        self,
        review: AiReview,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> AiReview:
        with self.SessionLocal() as db:
            case_id = db.query(SessionRecord.case_id).join(
                AiReviewRecord, AiReviewRecord.session_id == SessionRecord.session_id
            ).filter(AiReviewRecord.ai_review_id == review.ai_review_id).scalar()
            if case_id is None:
                raise KeyError(review.ai_review_id)
            case_row = self._lock_case_row(db, case_id)
            row = db.query(AiReviewRecord).filter(
                AiReviewRecord.ai_review_id == review.ai_review_id
            ).with_for_update().one_or_none()
            if row is None:
                raise KeyError(review.ai_review_id)
            if review.session_id != row.session_id:
                raise ValueError("AI review cannot be moved between sessions.")
            saved_review = review.model_copy(update={"organization_id": case_row.organization_id})
            record = self._ai_review_to_record(saved_review)
            row.session_id = record.session_id
            row.payload = record.payload
            row.review_priority = record.review_priority
            row.therapist_review_status = record.therapist_review_status
            row.created_at = record.created_at
            audit = validate_audit_event(
                actor_id=actor_id, action=audit_action, target_id=saved_review.ai_review_id,
                outcome="success", correlation_id=f"ai-review-update-{saved_review.ai_review_id}",
                message=audit_message,
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            db.add(self._audit_to_record(audit))
            db.flush()
            updated = AiReview.model_validate(row.payload)
            db.commit()
        self.ai_reviews[review.ai_review_id] = updated
        self.audit_log.append(audit)
        return self.clone(updated)

    def create_ml_result(
        self,
        result: MLResult,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> MLResult:
        with self.SessionLocal() as db:
            case_id = db.query(SessionRecord.case_id).filter(
                SessionRecord.session_id == result.session_id
            ).scalar()
            if case_id is None:
                raise KeyError(result.session_id)
            case_row = self._lock_case_row(db, case_id)
            session_row = db.get(SessionRecord, result.session_id)
            if session_row is None:
                raise KeyError(result.session_id)
            transcript_row = db.get(TranscriptRecord, result.transcript_id)
            feature_row = db.get(FeatureSetRecord, result.feature_result_id)
            if (
                transcript_row is None
                or session_row.transcript_id != result.transcript_id
                or session_row.feature_set_id != result.feature_result_id
                or feature_row is None
                or feature_row.review_status == ReviewStatus.stale.value
                or feature_row.transcript_id != transcript_row.transcript_id
                or feature_row.transcript_version != transcript_row.version
            ):
                raise ValueError("Transcript or findings changed during ML review generation; discard the stale result and retry.")
            saved_result = result.model_copy(update={"organization_id": case_row.organization_id})
            audit = validate_audit_event(
                actor_id=actor_id, action=audit_action, target_id=saved_result.result_id,
                outcome="success", correlation_id=f"ml-result-create-{saved_result.result_id}",
                message=audit_message,
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            session_row.ml_result_id = saved_result.result_id
            session_row.updated_at = _utc_now()
            db.add(self._ml_result_to_record(saved_result))
            db.add(self._audit_to_record(audit))
            db.flush()
            updated_session = self._session_from_record(session_row)
            db.commit()
        self.ml_results[saved_result.result_id] = saved_result
        self.sessions[saved_result.session_id] = updated_session
        self.audit_log.append(audit)
        return self.clone(saved_result)

    def update_ml_result(
        self,
        result: MLResult,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> MLResult:
        with self.SessionLocal() as db:
            case_id = db.query(SessionRecord.case_id).join(
                MLResultRecord, MLResultRecord.session_id == SessionRecord.session_id
            ).filter(MLResultRecord.result_id == result.result_id).scalar()
            if case_id is None:
                raise KeyError(result.result_id)
            case_row = self._lock_case_row(db, case_id)
            row = db.query(MLResultRecord).filter(
                MLResultRecord.result_id == result.result_id
            ).with_for_update().one_or_none()
            if row is None:
                raise KeyError(result.result_id)
            if result.session_id != row.session_id:
                raise ValueError("ML result cannot be moved between sessions.")
            saved_result = result.model_copy(update={"organization_id": case_row.organization_id})
            record = self._ml_result_to_record(saved_result)
            row.session_id = record.session_id
            row.transcript_id = record.transcript_id
            row.payload = record.payload
            row.created_at = record.created_at
            audit = validate_audit_event(
                actor_id=actor_id, action=audit_action, target_id=saved_result.result_id,
                outcome="success", correlation_id=f"ml-result-update-{saved_result.result_id}",
                message=audit_message,
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            db.add(self._audit_to_record(audit))
            db.flush()
            updated = MLResult.model_validate(row.payload)
            db.commit()
        self.ml_results[result.result_id] = updated
        self.audit_log.append(audit)
        return self.clone(updated)

    def load(self) -> None:
        with self.SessionLocal() as db:
            cases = db.query(ChildCaseRecord).all()
            if cases:
                self.cases = {row.case_id: self._case_from_record(row) for row in cases}
                self.sessions = {row.session_id: self._session_from_record(row) for row in db.query(SessionRecord).all()}
                self.transcripts = {row.transcript_id: self._transcript_from_record(row) for row in db.query(TranscriptRecord).all()}
                self.speaker_mappings = {
                    row.mapping_id: self._speaker_mapping_from_record(row)
                    for row in db.query(SpeakerMappingRecord).all()
                }
                self.features = {row.feature_set_id: self._feature_from_record(row) for row in db.query(FeatureSetRecord).all()}
                self.ml_results = {row.result_id: MLResult.model_validate(row.payload) for row in db.query(MLResultRecord).all()}
                self.audio_files = {row.audio_file_id: self._audio_from_record(row) for row in db.query(AudioFileRecord).all()}
                self.ai_reviews = {row.ai_review_id: AiReview.model_validate(row.payload) for row in db.query(AiReviewRecord).all()}
                self.reports = {row.report_id: self._report_from_record(row) for row in db.query(ReportRecord).all()}
                profile_names = {row.user_id: row.display_name for row in db.query(UserProfileRecord).all()}
                self.memberships = {
                    row.membership_id: self._membership_from_record(row, display_name=profile_names.get(row.user_id, row.user_id))
                    for row in db.query(OrganizationMembershipRecord).all()
                }
                self.invitations = {
                    row.invitation_id: self._invitation_from_record(row)
                    for row in db.query(OrganizationInvitationRecord).all()
                }
                self.care_team_assignments = {
                    row.assignment_id: self._care_team_assignment_from_record(row)
                    for row in db.query(CaseCareTeamAssignmentRecord).all()
                }
                self.therapy_goals = {row.goal_id: self._goal_from_record(row) for row in db.query(TherapyGoalRecord).all()}
                self.jobs = {row.job_id: self._job_from_record(row) for row in db.query(ProcessingJobRecord).all()}
                self.privacy_operations = {row.privacy_operation_id: self._privacy_operation_from_record(row) for row in db.query(PrivacyOperationRecord).all()}
                self.organization_settings = {
                    row.organization_id: dict(row.settings or {})
                    for row in db.query(OrganizationSettingsRecord).all()
                }
                self.organization_settings.setdefault("pilot_org_001", {"ai_review_enabled": True})
                self.audit_log = [
                    {
                        "audit_id": row.audit_id,
                        "organization_id": row.organization_id,
                        "actor_id": row.actor_id,
                        "action": row.action,
                        "target_id": row.target_id,
                        "outcome": row.outcome,
                        "correlation_id": row.correlation_id,
                        "message": row.message,
                        "timestamp": row.timestamp.isoformat() if hasattr(row.timestamp, "isoformat") else str(row.timestamp),
                    }
                    for row in db.query(AuditLogRecord).all()
                ]
            else:
                self._bootstrap_empty_database()

    def _bootstrap_empty_database(self) -> None:
        with self.SessionLocal() as db:
            nonempty_tables = [
                table.name
                for table in Base.metadata.sorted_tables
                if db.execute(table.select().limit(1)).first() is not None
            ]
            if nonempty_tables:
                raise RuntimeError(
                    "SQL bootstrap requires every managed table to be empty; found: "
                    + ", ".join(nonempty_tables)
                )
            for case in self.cases.values():
                db.add(self._case_to_record(case))
            for session in self.sessions.values():
                db.add(self._session_to_record(session))
            for transcript in self.transcripts.values():
                db.add(self._transcript_to_record(transcript))
            for mapping in self.speaker_mappings.values():
                db.add(self._speaker_mapping_to_record(mapping))
            for feature_set in self.features.values():
                db.add(self._feature_to_record(feature_set))
            for result in self.ml_results.values():
                db.add(MLResultRecord(
                    result_id=result.result_id,
                    session_id=result.session_id,
                    transcript_id=result.transcript_id,
                    payload=result.model_dump(mode="json"),
                    created_at=result.generated_at,
                ))
            for audio_file in self.audio_files.values():
                db.add(self._audio_to_record(audio_file))
            for review in self.ai_reviews.values():
                db.add(AiReviewRecord(
                    ai_review_id=review.ai_review_id,
                    session_id=review.session_id,
                    payload=review.model_dump(mode="json"),
                    review_priority=review.review_priority,
                    therapist_review_status=review.therapist_review_status.value,
                    created_at=review.created_at,
                ))
            for report in self.reports.values():
                db.add(self._report_to_record(report))
            for membership in self.memberships.values():
                if db.get(OrganizationRecord, membership.organization_id) is None:
                    db.add(OrganizationRecord(
                        organization_id=membership.organization_id,
                        name=membership.organization_id,
                        pilot_mode=False,
                        created_at=membership.created_at,
                    ))
                if db.get(UserProfileRecord, membership.user_id) is None:
                    db.add(UserProfileRecord(
                        user_id=membership.user_id,
                        display_name=membership.display_name,
                        created_at=membership.created_at,
                    ))
                db.add(self._membership_to_record(membership))
            for invitation in self.invitations.values():
                if db.get(OrganizationRecord, invitation.organization_id) is None:
                    db.add(OrganizationRecord(
                        organization_id=invitation.organization_id,
                        name=invitation.organization_id,
                        pilot_mode=False,
                        created_at=invitation.created_at,
                    ))
                db.add(self._invitation_to_record(invitation))
            for assignment in self.care_team_assignments.values():
                db.add(self._care_team_assignment_to_record(assignment))
            for goal in self.therapy_goals.values():
                db.add(self._goal_to_record(goal))
            for job in self.jobs.values():
                db.add(self._job_to_record(job))
            for privacy_operation in self.privacy_operations.values():
                db.add(self._privacy_operation_to_record(privacy_operation))
            for organization_id, settings in self.organization_settings.items():
                if db.get(OrganizationRecord, organization_id) is None:
                    db.add(OrganizationRecord(
                        organization_id=organization_id,
                        name=organization_id,
                        pilot_mode=False,
                        created_at=_utc_now(),
                    ))
                db.add(OrganizationSettingsRecord(
                    organization_id=organization_id,
                    ai_drafting_enabled=bool(settings.get("ai_drafting_enabled", False)),
                    default_retention_region=str(settings.get("default_retention_region", "local_pilot")),
                    settings=settings,
                    created_at=_utc_now(),
                    updated_at=_utc_now(),
                ))
            for item in self.audit_log:
                db.add(AuditLogRecord(
                    audit_id=item["audit_id"],
                    organization_id=item["organization_id"],
                    actor_id=item.get("actor_id", "system"),
                    action=item["action"],
                    target_id=item["target_id"],
                    outcome=item.get("outcome", "success"),
                    correlation_id=item.get("correlation_id", "local"),
                    message=item["message"],
                    timestamp=_parse_datetime(item["timestamp"]),
                ))
            db.commit()

    def save(self) -> None:
        raise RuntimeError(
            "Generic SQL snapshot save is not available; use an explicit transactional repository operation."
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
        event = validate_audit_event(
            actor_id=actor_id,
            action=action,
            target_id=target_id,
            outcome=outcome,
            correlation_id=correlation_id,
            message=message,
        ).as_dict()
        with self.SessionLocal() as db:
            resolved_organization_id = organization_id or self._organization_for_target_in_db(db, target_id)
            if resolved_organization_id is None:
                raise KeyError(target_id)
            event["organization_id"] = resolved_organization_id
            db.add(self._audit_to_record(event))
            db.commit()
        with self._lock:
            self.audit_log.append(event)

    @staticmethod
    def _organization_for_target_in_db(db, target_id: str) -> str | None:
        for model in (
            ChildCaseRecord,
            SessionRecord,
            TranscriptRecord,
            SpeakerMappingRecord,
            FeatureSetRecord,
            AudioFileRecord,
            AiReviewRecord,
            MLResultRecord,
            ReportRecord,
            OrganizationMembershipRecord,
            OrganizationInvitationRecord,
            CaseCareTeamAssignmentRecord,
            TherapyGoalRecord,
            ProcessingJobRecord,
            PrivacyOperationRecord,
        ):
            row = db.get(model, target_id)
            if row is not None:
                return row.organization_id
        return None

    def has_active_org_admin_membership(self, user_id: str, organization_id: str) -> bool:
        with self.SessionLocal() as db:
            return (
                db.query(OrganizationMembershipRecord)
                .filter_by(
                    organization_id=organization_id,
                    user_id=user_id,
                    role="org_admin",
                    active=True,
                )
                .first()
                is not None
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
        audit = validate_audit_event(
            actor_id=actor_id,
            action=action,
            target_id=target_id,
            outcome=outcome,
            correlation_id=correlation_id,
            message=message,
        ).as_dict()
        audit["organization_id"] = organization_id
        with self.SessionLocal() as db:
            db.add(self._audit_to_record(audit))
            db.commit()
        self.audit_log.append(audit)

    def _case_to_record(self, case: ChildCase) -> ChildCaseRecord:
        return ChildCaseRecord(
            case_id=case.case_id,
            organization_id=case.organization_id,
            care_team_user_ids=case.care_team_user_ids,
            primary_therapist_user_id=case.primary_therapist_user_id,
            child_code=case.child_code,
            nickname=case.nickname,
            age_months=case.age_months,
            language=case.language,
            consent_status=case.consent_status,
            review_priority=case.review_priority,
            notes=case.notes,
            version=case.version,
            latest_session_date=case.latest_session_date,
            latest_session_status=case.latest_session_status.value
            if hasattr(case.latest_session_status, "value")
            else str(case.latest_session_status),
            latest_report_status=case.latest_report_status.value
            if hasattr(case.latest_report_status, "value")
            else str(case.latest_report_status),
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

    def _privacy_operation_to_record(self, operation: PrivacyOperation) -> PrivacyOperationRecord:
        return PrivacyOperationRecord(
            privacy_operation_id=operation.privacy_operation_id,
            organization_id=operation.organization_id,
            case_id=operation.case_id,
            operation_type=operation.operation_type,
            status=operation.status,
            requested_by=operation.requested_by,
            requester_role=operation.requester_role,
            reason=operation.reason,
            admin_note=operation.admin_note,
            retention_days=operation.retention_days,
            legal_hold=operation.legal_hold,
            deletion_review_required=operation.deletion_review_required,
            preserve_evidence=operation.preserve_evidence,
            eligible_for_deletion_at=operation.eligible_for_deletion_at,
            completed_at=operation.completed_at,
            evidence_retained=operation.evidence_retained,
            created_at=operation.created_at,
            updated_at=operation.updated_at,
        )

    def _privacy_operation_from_record(self, row: PrivacyOperationRecord) -> PrivacyOperation:
        return PrivacyOperation(
            privacy_operation_id=row.privacy_operation_id,
            organization_id=row.organization_id,
            case_id=row.case_id,
            operation_type=row.operation_type,
            status=row.status,
            requested_by=row.requested_by,
            requester_role=row.requester_role,
            reason=row.reason,
            admin_note=row.admin_note,
            retention_days=row.retention_days,
            legal_hold=row.legal_hold,
            deletion_review_required=row.deletion_review_required,
            preserve_evidence=row.preserve_evidence,
            eligible_for_deletion_at=row.eligible_for_deletion_at,
            completed_at=row.completed_at,
            evidence_retained=row.evidence_retained,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _case_from_record(self, row: ChildCaseRecord) -> ChildCase:
        return ChildCase(
            case_id=row.case_id,
            organization_id=row.organization_id,
            care_team_user_ids=list(row.care_team_user_ids or []),
            primary_therapist_user_id=row.primary_therapist_user_id,
            child_code=row.child_code,
            nickname=row.nickname,
            age_months=row.age_months,
            language=row.language,
            consent_status=row.consent_status,
            review_priority=row.review_priority,
            notes=row.notes,
            version=row.version,
            latest_session_date=row.latest_session_date,
            latest_session_status=ReviewStatus(row.latest_session_status),
            latest_report_status=ReviewStatus(row.latest_report_status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _membership_to_record(self, membership: OrganizationMembership) -> OrganizationMembershipRecord:
        return OrganizationMembershipRecord(
            membership_id=membership.membership_id,
            organization_id=membership.organization_id,
            user_id=membership.user_id,
            role=membership.role,
            active=membership.active,
            created_at=membership.created_at,
        )

    def _membership_from_record(
        self,
        row: OrganizationMembershipRecord,
        *,
        display_name: str,
    ) -> OrganizationMembership:
        return OrganizationMembership(
            membership_id=row.membership_id,
            organization_id=row.organization_id,
            user_id=row.user_id,
            display_name=display_name,
            role=row.role,
            active=row.active,
            created_at=row.created_at,
        )

    def _invitation_to_record(self, invitation: OrganizationInvitation) -> OrganizationInvitationRecord:
        return OrganizationInvitationRecord(
            invitation_id=invitation.invitation_id,
            organization_id=invitation.organization_id,
            email=invitation.email,
            display_name=invitation.display_name,
            role=invitation.role,
            status=invitation.status,
            invited_by=invitation.invited_by,
            accepted_user_id=invitation.accepted_user_id,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
            accepted_at=invitation.accepted_at,
        )

    def _invitation_from_record(self, row: OrganizationInvitationRecord) -> OrganizationInvitation:
        return OrganizationInvitation(
            invitation_id=row.invitation_id,
            organization_id=row.organization_id,
            email=row.email,
            display_name=row.display_name,
            role=row.role,
            status=row.status,
            invited_by=row.invited_by,
            accepted_user_id=row.accepted_user_id,
            expires_at=row.expires_at,
            created_at=row.created_at,
            accepted_at=row.accepted_at,
        )

    def _care_team_assignment_to_record(
        self,
        assignment: CareTeamAssignment,
    ) -> CaseCareTeamAssignmentRecord:
        return CaseCareTeamAssignmentRecord(
            assignment_id=assignment.assignment_id,
            organization_id=assignment.organization_id,
            case_id=assignment.case_id,
            user_id=assignment.user_id,
            role=assignment.role,
            active=assignment.active,
            created_at=assignment.created_at,
        )

    def _care_team_assignment_from_record(
        self,
        row: CaseCareTeamAssignmentRecord,
    ) -> CareTeamAssignment:
        return CareTeamAssignment(
            assignment_id=row.assignment_id,
            organization_id=row.organization_id,
            case_id=row.case_id,
            user_id=row.user_id,
            role=row.role,
            active=row.active,
            created_at=row.created_at,
        )

    def _session_to_record(self, session: TherapySession) -> SessionRecord:
        return SessionRecord(**session.model_dump(mode="python"))

    def _session_from_record(self, row: SessionRecord) -> TherapySession:
        return TherapySession(
            session_id=row.session_id,
            case_id=row.case_id,
            organization_id=row.organization_id,
            version=row.version,
            session_date=row.session_date,
            session_type=row.session_type,
            notes=row.notes,
            status=row.status,
            transcript_id=row.transcript_id,
            feature_set_id=row.feature_set_id,
            ml_result_id=row.ml_result_id,
            ai_review_id=row.ai_review_id,
            report_id=row.report_id,
            cues_acknowledged_at=row.cues_acknowledged_at,
            cues_acknowledged_by=row.cues_acknowledged_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _transcript_to_record(self, transcript: Transcript) -> TranscriptRecord:
        return TranscriptRecord(
            transcript_id=transcript.transcript_id,
            session_id=transcript.session_id,
            case_id=transcript.case_id,
            organization_id=transcript.organization_id,
            source=transcript.source,
            raw_text=transcript.raw_text,
            utterances=[item.model_dump(mode="json") for item in transcript.utterances],
            qa_status=transcript.qa_status.value,
            qa_issues=[item.model_dump(mode="json") for item in transcript.qa_issues],
            review_status=transcript.review_status.value,
            therapist_attested=transcript.therapist_attested,
            attestation_reason=transcript.attestation_reason,
            version=transcript.version,
            chat_metadata=transcript.chat_metadata,
            orphan_dependent_tiers=[item.model_dump(mode="json") for item in transcript.orphan_dependent_tiers],
            malformed_lines=transcript.malformed_lines,
            parser_version=transcript.parser_version,
            import_timestamp=transcript.import_timestamp,
            created_at=transcript.created_at,
            updated_at=transcript.updated_at,
        )

    def _transcript_from_record(self, row: TranscriptRecord) -> Transcript:
        return Transcript.model_validate(
            {
                "transcript_id": row.transcript_id,
                "session_id": row.session_id,
                "case_id": row.case_id,
                "organization_id": row.organization_id,
                "source": row.source,
                "raw_text": row.raw_text,
                "utterances": row.utterances,
                "qa_status": row.qa_status,
                "qa_issues": row.qa_issues,
                "review_status": row.review_status,
                "therapist_attested": row.therapist_attested,
                "attestation_reason": row.attestation_reason,
                "version": row.version,
                "chat_metadata": row.chat_metadata,
                "orphan_dependent_tiers": row.orphan_dependent_tiers,
                "malformed_lines": row.malformed_lines,
                "parser_version": row.parser_version,
                "import_timestamp": _as_utc(row.import_timestamp),
                "created_at": _as_utc(row.created_at),
                "updated_at": _as_utc(row.updated_at),
            }
        )

    @staticmethod
    def _speaker_mapping_to_record(mapping: SpeakerMapping) -> SpeakerMappingRecord:
        return SpeakerMappingRecord(
            mapping_id=mapping.mapping_id,
            organization_id=mapping.organization_id,
            transcript_id=mapping.transcript_id,
            source_transcript_version=mapping.source_transcript_version,
            applied_transcript_version=mapping.applied_transcript_version,
            mapping_version=mapping.mapping_version,
            status=mapping.status.value,
            entries=[entry.model_dump(mode="json") for entry in mapping.entries],
            confirmed_by_user_id=mapping.confirmed_by_user_id,
            confirmed_by_role=mapping.confirmed_by_role,
            confirmed_at=mapping.confirmed_at,
            created_at=mapping.created_at,
            updated_at=mapping.updated_at,
        )

    @staticmethod
    def _speaker_mapping_from_record(row: SpeakerMappingRecord) -> SpeakerMapping:
        return SpeakerMapping(
            mapping_id=row.mapping_id,
            organization_id=row.organization_id,
            transcript_id=row.transcript_id,
            source_transcript_version=row.source_transcript_version,
            applied_transcript_version=row.applied_transcript_version,
            mapping_version=row.mapping_version,
            status=MappingPersistedStatus(row.status),
            entries=[SpeakerMappingEntry.model_validate(entry) for entry in row.entries],
            confirmed_by_user_id=row.confirmed_by_user_id,
            confirmed_by_role=row.confirmed_by_role,
            confirmed_at=_as_utc(row.confirmed_at),
            created_at=_as_utc(row.created_at),
            updated_at=_as_utc(row.updated_at),
        )

    def _feature_to_record(self, feature_set: FeatureSet) -> FeatureSetRecord:
        return FeatureSetRecord(
            feature_set_id=feature_set.feature_set_id,
            organization_id=feature_set.organization_id,
            session_id=feature_set.session_id,
            transcript_id=feature_set.transcript_id,
            transcript_version=feature_set.transcript_version,
            schema_version=feature_set.schema_version,
            therapist_attested=feature_set.therapist_attested,
            warnings=feature_set.warnings,
            features=[item.model_dump(mode="json") for item in feature_set.features],
            review_status=feature_set.review_status.value,
            extracted_at=feature_set.extracted_at,
        )

    def _feature_from_record(self, row: FeatureSetRecord) -> FeatureSet:
        return FeatureSet.model_validate(
            {
                "feature_set_id": row.feature_set_id,
                "organization_id": row.organization_id,
                "session_id": row.session_id,
                "transcript_id": row.transcript_id,
                "transcript_version": row.transcript_version,
                "schema_version": row.schema_version,
                "therapist_attested": row.therapist_attested,
                "warnings": row.warnings,
                "features": row.features,
                "review_status": row.review_status,
                "extracted_at": row.extracted_at,
            }
        )

    def _audio_to_record(self, audio_file: AudioFileMetadata) -> AudioFileRecord:
        return AudioFileRecord(**audio_file.model_dump(mode="python"))

    def _audio_from_record(self, row: AudioFileRecord) -> AudioFileMetadata:
        return AudioFileMetadata(
            audio_file_id=row.audio_file_id,
            organization_id=row.organization_id,
            session_id=row.session_id,
            case_id=row.case_id,
            original_filename=row.original_filename,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            storage_mode=row.storage_mode,
            object_key=row.object_key,
            upload_status=row.upload_status,
            duration_seconds=row.duration_seconds,
            sample_rate_hz=row.sample_rate_hz,
            channels=row.channels,
            estimated_noise_level=row.estimated_noise_level,
            silence_ratio=row.silence_ratio,
            checksum_sha256=row.checksum_sha256,
            uploaded_at=row.uploaded_at,
            storage_delete_status=row.storage_delete_status,
            retained=row.retained,
            version=row.version,
            created_at=row.created_at,
        )

    def _ai_review_to_record(self, review: AiReview) -> AiReviewRecord:
        return AiReviewRecord(
            ai_review_id=review.ai_review_id,
            organization_id=review.organization_id,
            session_id=review.session_id,
            payload=review.model_dump(mode="json"),
            review_priority=review.review_priority,
            therapist_review_status=review.therapist_review_status.value,
            created_at=review.created_at,
        )

    def _ml_result_to_record(self, result: MLResult) -> MLResultRecord:
        return MLResultRecord(
            result_id=result.result_id,
            organization_id=result.organization_id,
            session_id=result.session_id,
            transcript_id=result.transcript_id,
            payload=result.model_dump(mode="json"),
            created_at=result.generated_at,
        )

    def _report_to_record(self, report: Report) -> ReportRecord:
        data = report.model_dump(mode="python")
        json_data = report.model_dump(mode="json")
        for field in (
            "safety_validation_result",
            "finalized_safety_result",
            "signed_snapshot",
            "session_goals",
            "generated_from_versions",
            "sections",
        ):
            data[field] = json_data[field]
        return ReportRecord(**data)

    def _report_from_record(self, row: ReportRecord) -> Report:
        return Report(
            report_id=row.report_id,
            session_id=row.session_id,
            case_id=row.case_id,
            organization_id=row.organization_id,
            report_type=row.report_type,
            title=row.title,
            markdown=row.markdown,
            html=row.html,
            status=row.status,
            therapist_signoff_status=row.therapist_signoff_status,
            limitation_text=row.limitation_text,
            export_timestamp=row.export_timestamp,
            created_at=row.created_at,
            updated_at=row.updated_at,
            requested_provider=row.requested_provider,
            actual_provider=row.actual_provider,
            provider_version=row.provider_version,
            fallback_reason=row.fallback_reason,
            rewrite_attempted=row.rewrite_attempted,
            rewrite_succeeded=row.rewrite_succeeded,
            safety_validation_result=row.safety_validation_result,
            finalized_safety_result=row.finalized_safety_result,
            finalization_blocked=row.finalization_blocked,
            validator_version=row.validator_version,
            rule_set_version=row.rule_set_version,
            input_hash=row.input_hash,
            version=row.version,
            signed_by=row.signed_by,
            signed_at=row.signed_at,
            signed_snapshot_version=row.signed_snapshot_version,
            signed_snapshot_hash=row.signed_snapshot_hash,
            signed_snapshot=row.signed_snapshot,
            supersedes_report_id=row.supersedes_report_id,
            revision_number=row.revision_number,
            ai_drafting_requested=row.ai_drafting_requested,
            ai_drafting_enabled=row.ai_drafting_enabled,
            ai_drafting_provider=row.ai_drafting_provider,
            ai_drafting_model=row.ai_drafting_model,
            ai_drafting_region=row.ai_drafting_region,
            ai_drafting_input_hash=row.ai_drafting_input_hash,
            transcript_id=row.transcript_id,
            feature_result_id=row.feature_result_id,
            ml_result_id=row.ml_result_id,
            ml_skipped_reason=row.ml_skipped_reason,
            validation_summary=row.validation_summary,
            feature_schema_version=row.feature_schema_version,
            therapist_notes=row.therapist_notes,
            session_goals=row.session_goals,
            generated_from_versions=row.generated_from_versions,
            sections=row.sections,
        )

    def _goal_to_record(self, goal: TherapyGoal) -> TherapyGoalRecord:
        return TherapyGoalRecord(**goal.model_dump(mode="python"))

    def _goal_from_record(self, row: TherapyGoalRecord) -> TherapyGoal:
        return TherapyGoal(
            goal_id=row.goal_id,
            organization_id=row.organization_id,
            case_id=row.case_id,
            title=row.title,
            target=row.target,
            status=row.status,
            notes=row.notes,
            retained=row.retained,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _job_to_record(self, job: ProcessingJob) -> ProcessingJobRecord:
        return ProcessingJobRecord(**job.model_dump(mode="python"))

    def _job_from_record(self, row: ProcessingJobRecord) -> ProcessingJob:
        return ProcessingJob(
            job_id=row.job_id,
            organization_id=row.organization_id,
            session_id=row.session_id,
            audio_file_id=row.audio_file_id,
            active_audio_file_id=row.active_audio_file_id,
            version=row.version,
            status=row.status,
            message=row.message,
            error_code=row.error_code,
            details=row.details,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _audit_to_record(self, item: dict) -> AuditLogRecord:
        return AuditLogRecord(
            audit_id=item["audit_id"],
            organization_id=item["organization_id"],
            actor_id=item.get("actor_id", "system"),
            action=item["action"],
            target_id=item["target_id"],
            outcome=item.get("outcome", "success"),
            correlation_id=item.get("correlation_id", "local"),
            message=item["message"],
            timestamp=_parse_datetime(item["timestamp"]),
        )


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_speaker_mapping_version_integrity_error(exc: IntegrityError) -> bool:
    constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if constraint_name == "uq_speaker_mapping_transcript_version":
        return True
    message = str(exc.orig).lower()
    return (
        "unique constraint failed: speaker_mappings.transcript_id, "
        "speaker_mappings.mapping_version"
    ) in message


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
INVITATION_EXPIRY_DAYS = 7
