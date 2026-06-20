from __future__ import annotations

from datetime import datetime

from app.db.models import (
    AiReviewRecord,
    AudioFileRecord,
    AuditLogRecord,
    Base,
    ChildCaseRecord,
    FeatureSetRecord,
    MLResultRecord,
    PrivacyOperationRecord,
    ProcessingJobRecord,
    ReportRecord,
    SessionRecord,
    TherapyGoalRecord,
    TranscriptRecord,
)
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    AiReview,
    AudioFileMetadata,
    ChildCase,
    FeatureSet,
    MLResult,
    PrivacyOperation,
    ProcessingJob,
    Report,
    TherapyGoal,
    TherapySession,
    Transcript,
)


class SqlAlchemyRepository(MockRepository):
    """SQLAlchemy-backed local/pilot scaffold using the v2 service contract.

    Services currently mutate repository dictionaries. This adapter loads SQL
    rows into those dictionaries and persists the current snapshot after audit
    events, allowing the API contract to move toward a real SQL repository
    without changing every route at once.
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

    def load(self) -> None:
        with self.SessionLocal() as db:
            cases = db.query(ChildCaseRecord).all()
            if cases:
                self.cases = {row.case_id: self._case_from_record(row) for row in cases}
                self.sessions = {row.session_id: self._session_from_record(row) for row in db.query(SessionRecord).all()}
                self.transcripts = {row.transcript_id: self._transcript_from_record(row) for row in db.query(TranscriptRecord).all()}
                self.features = {row.feature_set_id: self._feature_from_record(row) for row in db.query(FeatureSetRecord).all()}
                self.ml_results = {row.result_id: MLResult.model_validate(row.payload) for row in db.query(MLResultRecord).all()}
                self.audio_files = {row.audio_file_id: self._audio_from_record(row) for row in db.query(AudioFileRecord).all()}
                self.ai_reviews = {row.ai_review_id: AiReview.model_validate(row.payload) for row in db.query(AiReviewRecord).all()}
                self.reports = {row.report_id: self._report_from_record(row) for row in db.query(ReportRecord).all()}
                self.therapy_goals = {row.goal_id: self._goal_from_record(row) for row in db.query(TherapyGoalRecord).all()}
                self.jobs = {row.job_id: self._job_from_record(row) for row in db.query(ProcessingJobRecord).all()}
                self.privacy_operations = {row.privacy_operation_id: self._privacy_operation_from_record(row) for row in db.query(PrivacyOperationRecord).all()}
                self.audit_log = [
                    {
                        "audit_id": row.audit_id,
                        "action": row.action,
                        "target_id": row.target_id,
                        "message": row.message,
                        "timestamp": row.timestamp.isoformat() if hasattr(row.timestamp, "isoformat") else str(row.timestamp),
                    }
                    for row in db.query(AuditLogRecord).all()
                ]
            else:
                self.save()

    def save(self) -> None:
        with self.SessionLocal() as db:
            for model in (
                AuditLogRecord,
                PrivacyOperationRecord,
                ProcessingJobRecord,
                ReportRecord,
                AiReviewRecord,
                MLResultRecord,
                AudioFileRecord,
                FeatureSetRecord,
                TranscriptRecord,
                TherapyGoalRecord,
                SessionRecord,
                ChildCaseRecord,
            ):
                db.query(model).delete()
            for case in self.cases.values():
                db.add(self._case_to_record(case))
            for session in self.sessions.values():
                db.add(self._session_to_record(session))
            for transcript in self.transcripts.values():
                db.add(self._transcript_to_record(transcript))
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
            for goal in self.therapy_goals.values():
                db.add(self._goal_to_record(goal))
            for job in self.jobs.values():
                db.add(self._job_to_record(job))
            for privacy_operation in self.privacy_operations.values():
                db.add(self._privacy_operation_to_record(privacy_operation))
            for item in self.audit_log:
                db.add(AuditLogRecord(
                    audit_id=item["audit_id"],
                    action=item["action"],
                    target_id=item["target_id"],
                    message=item["message"],
                    timestamp=_parse_datetime(item["timestamp"]),
                ))
            db.commit()

    def add_audit(self, action: str, target_id: str, message: str) -> None:
        super().add_audit(action, target_id, message)
        self.save()

    def _case_to_record(self, case: ChildCase) -> ChildCaseRecord:
        return ChildCaseRecord(
            case_id=case.case_id,
            child_code=case.child_code,
            nickname=case.nickname,
            age_months=case.age_months,
            language=case.language,
            consent_status=case.consent_status,
            review_priority=case.review_priority,
            notes=case.notes,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

    def _privacy_operation_to_record(self, operation: PrivacyOperation) -> PrivacyOperationRecord:
        return PrivacyOperationRecord(
            privacy_operation_id=operation.privacy_operation_id,
            case_id=operation.case_id,
            operation_type=operation.operation_type,
            status=operation.status,
            requested_by=operation.requested_by,
            requester_role=operation.requester_role,
            reason=operation.reason,
            admin_note=operation.admin_note,
            created_at=operation.created_at,
            updated_at=operation.updated_at,
        )

    def _privacy_operation_from_record(self, row: PrivacyOperationRecord) -> PrivacyOperation:
        return PrivacyOperation(
            privacy_operation_id=row.privacy_operation_id,
            case_id=row.case_id,
            operation_type=row.operation_type,
            status=row.status,
            requested_by=row.requested_by,
            requester_role=row.requester_role,
            reason=row.reason,
            admin_note=row.admin_note,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _case_from_record(self, row: ChildCaseRecord) -> ChildCase:
        return ChildCase(
            case_id=row.case_id,
            child_code=row.child_code,
            nickname=row.nickname,
            age_months=row.age_months,
            language=row.language,
            consent_status=row.consent_status,
            review_priority=row.review_priority,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _session_to_record(self, session: TherapySession) -> SessionRecord:
        return SessionRecord(**session.model_dump(mode="python"))

    def _session_from_record(self, row: SessionRecord) -> TherapySession:
        return TherapySession(
            session_id=row.session_id,
            case_id=row.case_id,
            session_date=row.session_date,
            session_type=row.session_type,
            notes=row.notes,
            status=row.status,
            transcript_id=row.transcript_id,
            feature_set_id=row.feature_set_id,
            ml_result_id=row.ml_result_id,
            ai_review_id=row.ai_review_id,
            report_id=row.report_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _transcript_to_record(self, transcript: Transcript) -> TranscriptRecord:
        return TranscriptRecord(
            transcript_id=transcript.transcript_id,
            session_id=transcript.session_id,
            case_id=transcript.case_id,
            source=transcript.source,
            raw_text=transcript.raw_text,
            utterances=[item.model_dump(mode="json") for item in transcript.utterances],
            qa_status=transcript.qa_status.value,
            qa_issues=[item.model_dump(mode="json") for item in transcript.qa_issues],
            review_status=transcript.review_status.value,
            therapist_attested=transcript.therapist_attested,
            attestation_reason=transcript.attestation_reason,
            version=transcript.version,
            created_at=transcript.created_at,
            updated_at=transcript.updated_at,
        )

    def _transcript_from_record(self, row: TranscriptRecord) -> Transcript:
        return Transcript.model_validate(
            {
                "transcript_id": row.transcript_id,
                "session_id": row.session_id,
                "case_id": row.case_id,
                "source": row.source,
                "raw_text": row.raw_text,
                "utterances": row.utterances,
                "qa_status": row.qa_status,
                "qa_issues": row.qa_issues,
                "review_status": row.review_status,
                "therapist_attested": row.therapist_attested,
                "attestation_reason": row.attestation_reason,
                "version": row.version,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )

    def _feature_to_record(self, feature_set: FeatureSet) -> FeatureSetRecord:
        return FeatureSetRecord(
            feature_set_id=feature_set.feature_set_id,
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
            created_at=row.created_at,
        )

    def _report_to_record(self, report: Report) -> ReportRecord:
        return ReportRecord(**report.model_dump(mode="python"))

    def _report_from_record(self, row: ReportRecord) -> Report:
        return Report(
            report_id=row.report_id,
            session_id=row.session_id,
            case_id=row.case_id,
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
            session_id=row.session_id,
            status=row.status,
            message=row.message,
            error_code=row.error_code,
            details=row.details,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)
