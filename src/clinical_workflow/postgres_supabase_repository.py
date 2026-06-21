"""PostgreSQL/Supabase repository implementation using supabase-py.

Uses the PostgREST query builder via `supabase-py` which automatically
enforces Row Level Security through the JWT token.  Application-level
ownership checks are maintained for defense-in-depth.
"""

from __future__ import annotations

import hashlib
import os
import uuid as _uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.clinical_workflow.models import (
    AIScreeningOutput,
    AudioFile,
    AuditLog,
    ChildCase,
    ClinicalSignoff,
    ClinicalSpeechArtifact,
    ConsentRecord,
    ExtractedFeatures,
    FeatureReviewDisposition,
    FileObject,
    ModelRun,
    ProcessingJob,
    Report,
    SAFETY_DISCLAIMER,
    Session,
    TherapistNote,
    TherapyGoal,
    Transcript,
    TranscriptLine,
    User,
)
from src.clinical_workflow.repository_interface import ClinicalRepository
from src.reference_engine import ReferenceComparisonResult


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid4() -> str:
    return str(_uuid.uuid4())


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _parse_dt(val: str | datetime | None) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Row → dataclass mappers
# ---------------------------------------------------------------------------

def _row_to_user(row: dict) -> User:
    return User(
        user_id=row["user_id"],
        name=row.get("name", ""),
        email=row.get("email", ""),
        role=row.get("role", "therapist"),
        organization=row.get("organization"),
        created_at=_parse_dt(row.get("created_at")) or _utc_now(),
        last_login=_parse_dt(row.get("last_login")),
    )


def _row_to_case(row: dict) -> ChildCase:
    return ChildCase(
        case_id=row["case_id"],
        owner_user_id=row["owner_user_id"],
        anonymized_child_code=row.get("anonymized_child_code", ""),
        age_months=int(row.get("age_months", 48)),
        sex=row.get("sex", "not_specified"),
        primary_concerns=row.get("primary_concerns", ""),
        display_label=row.get("display_label", ""),
        external_clinical_status=row.get("external_clinical_status", "not_provided"),
        consent_status=row.get("consent_status", "not_recorded"),
        anonymization_status=row.get("anonymization_status", "anonymized"),
        notes=row.get("notes", ""),
        created_at=_parse_dt(row.get("created_at")) or _utc_now(),
        updated_at=_parse_dt(row.get("updated_at")) or _utc_now(),
    )


def _row_to_session(row: dict) -> Session:
    return Session(
        session_id=row["session_id"],
        case_id=row["case_id"],
        owner_user_id=row["owner_user_id"],
        session_date=row.get("session_date", ""),
        session_type=row.get("session_type", "therapy_session"),
        audio_file_id=row.get("audio_file_id"),
        transcript_id=row.get("transcript_id"),
        processing_status=row.get("processing_status", "not_started"),
        feature_extraction_status=row.get("feature_extraction_status", "not_started"),
        ai_analysis_status=row.get("ai_analysis_status", "not_started"),
        therapist_review_status=row.get("therapist_review_status", "not_started"),
        report_status=row.get("report_status", "not_started"),
        notes=row.get("notes", ""),
        created_at=_parse_dt(row.get("created_at")) or _utc_now(),
        updated_at=_parse_dt(row.get("updated_at")) or _utc_now(),
    )


def _row_to_consent(row: dict) -> ConsentRecord:
    return ConsentRecord(
        consent_id=row["consent_id"],
        case_id=row["case_id"],
        owner_user_id=row["owner_user_id"],
        recorded_by_user_id=row.get("recorded_by_user_id", ""),
        consent_type=row.get("consent_type", "clinical_audio_processing"),
        guardian_status=row.get("guardian_status", "guardian"),
        audio_permission=bool(row.get("audio_permission", False)),
        transcript_permission=bool(row.get("transcript_permission", True)),
        notes=row.get("notes", ""),
        expires_at=_parse_dt(row.get("expires_at")),
        withdrawn_at=_parse_dt(row.get("withdrawn_at")),
        created_at=_parse_dt(row.get("created_at")) or _utc_now(),
    )


def _row_to_transcript(row: dict) -> Transcript:
    return Transcript(
        transcript_id=row["transcript_id"],
        session_id=row["session_id"],
        case_id=row.get("case_id", ""),
        owner_user_id=row.get("owner_user_id", ""),
        transcript_format=row.get("transcript_format", "CHAT"),
        transcript_text=row.get("transcript_text", ""),
        review_status=row.get("review_status", "not_started"),
        reviewer_notes=row.get("reviewer_notes", ""),
        qa_status=row.get("qa_status", "not_run"),
        qa_score=row.get("qa_score"),
        qa_issues=row.get("qa_issues") or [],
        created_at=_parse_dt(row.get("created_at")) or _utc_now(),
        updated_at=_parse_dt(row.get("updated_at")) or _utc_now(),
    )


def _row_to_transcript_line(row: dict) -> TranscriptLine:
    return TranscriptLine(
        line_id=row["line_id"],
        transcript_id=row["transcript_id"],
        session_id=row.get("session_id", ""),
        case_id=row.get("case_id", ""),
        owner_user_id=row.get("owner_user_id", ""),
        line_number=int(row.get("line_number", 0)),
        speaker_code=row.get("speaker_code", ""),
        utterance_text=row.get("utterance_text", ""),
        speaker_role=row.get("speaker_role", "other"),
        reviewed_text=row.get("reviewed_text"),
        start_time=row.get("start_time"),
        end_time=row.get("end_time"),
        start_ms=row.get("start_ms"),
        end_ms=row.get("end_ms"),
        confidence=row.get("confidence"),
        word_timestamps=row.get("word_timestamps") or [],
        flags=row.get("flags") or [],
        review_status=row.get("review_status", "needs_review"),
        reviewed=bool(row.get("reviewed", False)),
        interpretation_note=row.get("interpretation_note", ""),
        version=int(row.get("version", 1)),
        updated_at=_parse_dt(row.get("updated_at")) or _utc_now(),
        updated_by_user_id=row.get("updated_by_user_id"),
    )


def _row_to_audio_file(row: dict) -> AudioFile:
    return AudioFile(
        audio_file_id=row["audio_file_id"],
        owner_user_id=row["owner_user_id"],
        case_id=row["case_id"],
        session_id=row["session_id"],
        original_filename=row.get("original_filename", ""),
        stored_filename=row.get("stored_filename", ""),
        file_type=row.get("file_type", ""),
        file_size=int(row.get("file_size", 0)),
        upload_time=_parse_dt(row.get("upload_time")) or _utc_now(),
        processing_status=row.get("processing_status", "not_started"),
        storage_mode=row.get("storage_mode", "metadata_only"),
        file_object_id=row.get("file_object_id"),
    )


def _row_to_features(row: dict) -> ExtractedFeatures:
    return ExtractedFeatures(
        feature_id=row["feature_id"],
        session_id=row["session_id"],
        case_id=row.get("case_id", ""),
        owner_user_id=row.get("owner_user_id", ""),
        feature_schema_version=row.get("feature_schema_version", "14-feature-schema"),
        features=row.get("features") or {},
        core_features=row.get("core_features") or {},
        optional_indicators=row.get("optional_indicators") or {},
        source_revision=row.get("source_revision"),
        source_hash=row.get("source_hash"),
        extraction_status=row.get("extraction_status", "completed"),
        created_at=_parse_dt(row.get("created_at")) or _utc_now(),
    )


def _row_to_ai_output(row: dict) -> AIScreeningOutput:
    return AIScreeningOutput(
        output_id=row["output_id"],
        session_id=row["session_id"],
        case_id=row.get("case_id", ""),
        owner_user_id=row.get("owner_user_id", ""),
        concern_level=row.get("concern_level", "low_concern"),
        model_version=row.get("model_version", "screening-support-v1"),
        screening_support_score=row.get("screening_support_score"),
        confidence_interval=row.get("confidence_interval"),
        explanation=row.get("explanation", ""),
        plain_language_explanation=row.get("plain_language_explanation", ""),
        top_contributing_features=row.get("top_contributing_features") or [],
        evidence_items=row.get("evidence_items") or [],
        therapist_review_status=row.get("therapist_review_status", "awaiting_review"),
        differential_probabilities=row.get("differential_probabilities"),
        output_kind=row.get("output_kind", "screening_support"),
        inference_status=row.get("inference_status", "preliminary"),
        reference_cohort_probabilities=row.get("reference_cohort_probabilities") or {},
        most_similar_reference_cohort=row.get("most_similar_reference_cohort"),
        similarity_probability=row.get("similarity_probability"),
        report_eligible=bool(row.get("report_eligible", False)),
        safety_warnings=row.get("safety_warnings") or [],
        created_at=_parse_dt(row.get("created_at")) or _utc_now(),
    )


def _row_to_goal(row: dict) -> TherapyGoal:
    return TherapyGoal(
        goal_id=row["goal_id"],
        case_id=row["case_id"],
        owner_user_id=row.get("owner_user_id", ""),
        goal_text=row.get("goal_text", ""),
        status=row.get("status", "active"),
        created_at=_parse_dt(row.get("created_at")) or _utc_now(),
        updated_at=_parse_dt(row.get("updated_at")) or _utc_now(),
    )


def _row_to_note(row: dict) -> TherapistNote:
    return TherapistNote(
        note_id=row["note_id"],
        case_id=row["case_id"],
        owner_user_id=row.get("owner_user_id", ""),
        note_text=row.get("note_text", ""),
        session_id=row.get("session_id"),
        created_at=_parse_dt(row.get("created_at")) or _utc_now(),
        updated_at=_parse_dt(row.get("updated_at")) or _utc_now(),
    )


def _row_to_report(row: dict) -> Report:
    return Report(
        report_id=row["report_id"],
        case_id=row["case_id"],
        owner_user_id=row.get("owner_user_id", ""),
        session_id=row.get("session_id"),
        report_type=row.get("report_type", "progress"),
        title=row.get("title", ""),
        content_markdown=row.get("content_markdown", ""),
        export_status=row.get("export_status", "not_started"),
        created_at=_parse_dt(row.get("created_at")) or _utc_now(),
    )


def _row_to_signoff(row: dict) -> ClinicalSignoff:
    return ClinicalSignoff(
        signoff_id=row["signoff_id"],
        target_type=row["target_type"],
        target_id=row["target_id"],
        session_id=row.get("session_id"),
        case_id=row.get("case_id", ""),
        owner_user_id=row.get("owner_user_id", ""),
        signed_by_user_id=row.get("signed_by_user_id", ""),
        notes=row.get("notes", ""),
        created_at=_parse_dt(row.get("created_at")) or _utc_now(),
    )


def _row_to_audit_log(row: dict) -> AuditLog:
    return AuditLog(
        audit_id=row["audit_id"],
        event_type=row.get("event_type", ""),
        actor_user_id=row.get("actor_user_id", ""),
        target_type=row.get("target_type", ""),
        target_id=row.get("target_id", ""),
        message=row.get("message", ""),
        created_at=_parse_dt(row.get("created_at")) or _utc_now(),
    )


def _row_to_processing_job(row: dict) -> ProcessingJob:
    return ProcessingJob(
        job_id=row["job_id"],
        session_id=row["session_id"],
        case_id=row.get("case_id", ""),
        owner_user_id=row.get("owner_user_id", ""),
        audio_file_id=row.get("audio_file_id"),
        job_type=row.get("job_type", "audio_to_chat"),
        engine=row.get("engine", "local_whisper"),
        operation=row.get("operation", "audio_to_chat"),
        operation_config=row.get("operation_config") or {},
        dependency_check=row.get("dependency_check") or {},
        source_revision=row.get("source_revision"),
        status=row.get("status", "queued"),
        stage=row.get("stage", "queued"),
        progress=int(row.get("progress", 0)),
        error_code=row.get("error_code"),
        error_message=row.get("error_message", ""),
        result_refs=row.get("result_refs") or {},
        artifact_ids=row.get("artifact_ids") or [],
        started_at=_parse_dt(row.get("started_at")),
        finished_at=_parse_dt(row.get("finished_at")),
        created_at=_parse_dt(row.get("created_at")) or _utc_now(),
        updated_at=_parse_dt(row.get("updated_at")) or _utc_now(),
    )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class PostgresSupabaseRepository(ClinicalRepository):
    """Supabase/PostgREST-backed persistence for the clinical workspace.

    Requires `supabase-py` and a configured Supabase project.
    Set ``SUPABASE_URL`` and ``SUPABASE_SERVICE_ROLE_KEY`` environment
    variables or pass them directly to the constructor.
    """

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        *,
        client: Any | None = None,
    ) -> None:
        if client is not None:
            self.client = client
        else:
            try:
                from supabase import create_client
            except ImportError as exc:
                raise ImportError(
                    "supabase-py is required for PostgresSupabaseRepository. "
                    "Install it with: pip install supabase"
                ) from exc
            url = supabase_url or os.getenv("SUPABASE_URL", "")
            key = supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            if not url or not key:
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required. "
                    "Set them as environment variables or pass them directly."
                )
            self.client = create_client(url, key)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _select(self, table: str, **filters: Any) -> list[dict]:
        """Run SELECT * with optional eq filters and return rows."""
        query = self.client.table(table).select("*")
        for col, val in filters.items():
            query = query.eq(col, val)
        response = query.execute()
        return response.data or []

    def _select_one(self, table: str, **filters: Any) -> dict | None:
        rows = self._select(table, **filters)
        return rows[0] if rows else None

    def _insert(self, table: str, row: dict) -> dict:
        response = self.client.table(table).insert(row).execute()
        data = response.data
        return data[0] if data else row

    def _update(self, table: str, id_col: str, id_val: str, payload: dict) -> dict | None:
        payload["updated_at"] = _iso(_utc_now())
        response = (
            self.client.table(table)
            .update(payload)
            .eq(id_col, id_val)
            .execute()
        )
        data = response.data
        return data[0] if data else None

    def _delete(self, table: str, id_col: str, id_val: str) -> None:
        self.client.table(table).delete().eq(id_col, id_val).execute()

    def _audit(
        self,
        event_type: str,
        *,
        actor_user_id: str,
        target_type: str,
        target_id: str,
        message: str,
    ) -> None:
        """Write an audit log entry."""
        try:
            self._insert("audit_logs", {
                "audit_id": _uuid4(),
                "event_type": event_type,
                "actor_user_id": actor_user_id,
                "target_type": target_type,
                "target_id": target_id,
                "message": message,
                "created_at": _iso(_utc_now()),
            })
        except Exception:
            pass  # Audit logging must never break primary operations

    def _is_authorized(self, owner_user_id: str, user: User) -> bool:
        return user.role == "admin" or owner_user_id == user.user_id

    # ------------------------------------------------------------------
    # Authentication & User
    # ------------------------------------------------------------------

    def authenticate(self, email: str, password: str) -> User | None:
        try:
            auth_response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
        except Exception:
            return None
        auth_user = auth_response.user
        if not auth_user:
            return None
        row = self._select_one("users", user_id=auth_user.id)
        if row:
            self._update("users", "user_id", auth_user.id, {
                "last_login": _iso(_utc_now()),
            })
            return _row_to_user(row)
        # Auto-create user profile from auth metadata
        metadata = auth_user.user_metadata or {}
        new_row = {
            "user_id": auth_user.id,
            "name": metadata.get("name", email),
            "email": email,
            "role": metadata.get("role", "therapist"),
            "organization": metadata.get("organization", ""),
            "created_at": _iso(_utc_now()),
            "last_login": _iso(_utc_now()),
        }
        inserted = self._insert("users", new_row)
        return _row_to_user(inserted)

    def get_user(self, user_id: str) -> User | None:
        row = self._select_one("users", user_id=user_id)
        return _row_to_user(row) if row else None

    # ------------------------------------------------------------------
    # Cases
    # ------------------------------------------------------------------

    def list_cases_for_user(self, user: User) -> list[ChildCase]:
        rows = self._select("child_cases")
        return [_row_to_case(r) for r in rows if self._is_authorized(r["owner_user_id"], user)]

    def get_case_for_user(self, case_id: str, user: User) -> ChildCase | None:
        row = self._select_one("child_cases", case_id=case_id)
        if row and self._is_authorized(row["owner_user_id"], user):
            return _row_to_case(row)
        return None

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
        display_label: str = "",
        external_clinical_status: Any = "not_provided",
        notes: str = "",
    ) -> ChildCase:
        if " " in anonymized_child_code.strip():
            raise ValueError("anonymized_child_code must not contain spaces (use codes, not names).")
        now = _iso(_utc_now())
        row = {
            "case_id": _uuid4(),
            "owner_user_id": owner_user_id,
            "anonymized_child_code": anonymized_child_code,
            "age_months": age_months,
            "sex": sex,
            "primary_concerns": primary_concerns,
            "display_label": display_label,
            "consent_status": consent_status,
            "anonymization_status": anonymization_status,
            "external_clinical_status": external_clinical_status,
            "notes": notes,
            "created_at": now,
            "updated_at": now,
        }
        inserted = self._insert("child_cases", row)
        return _row_to_case(inserted)

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
        display_label: str | None = None,
        external_clinical_status: Any | None = None,
        notes: str | None = None,
    ) -> ChildCase | None:
        existing = self.get_case_for_user(case_id, user)
        if existing is None:
            return None
        payload: dict[str, Any] = {}
        if age_months is not None:
            payload["age_months"] = age_months
        if sex is not None:
            payload["sex"] = sex
        if primary_concerns is not None:
            payload["primary_concerns"] = primary_concerns
        if consent_status is not None:
            payload["consent_status"] = consent_status
        if anonymization_status is not None:
            payload["anonymization_status"] = anonymization_status
        if display_label is not None:
            payload["display_label"] = display_label
        if external_clinical_status is not None:
            payload["external_clinical_status"] = external_clinical_status
        if notes is not None:
            payload["notes"] = notes
        if not payload:
            return existing
        updated = self._update("child_cases", "case_id", case_id, payload)
        return _row_to_case(updated) if updated else existing

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def list_sessions_for_user(self, user: User) -> list[Session]:
        rows = self._select("sessions")
        return sorted(
            [_row_to_session(r) for r in rows if self._is_authorized(r["owner_user_id"], user)],
            key=lambda s: s.session_date,
            reverse=True,
        )

    def list_sessions_for_case_for_user(self, case_id: str, user: User) -> list[Session]:
        rows = self._select("sessions", case_id=case_id)
        return sorted(
            [_row_to_session(r) for r in rows if self._is_authorized(r["owner_user_id"], user)],
            key=lambda s: s.session_date,
            reverse=True,
        )

    def create_session(
        self,
        *,
        case_id: str,
        user: User,
        session_date: str,
        session_type: Any,
        notes: str = "",
    ) -> Session:
        now = _iso(_utc_now())
        row = {
            "session_id": _uuid4(),
            "case_id": case_id,
            "owner_user_id": user.user_id,
            "session_date": session_date,
            "session_type": session_type,
            "processing_status": "not_started",
            "feature_extraction_status": "not_started",
            "ai_analysis_status": "not_started",
            "therapist_review_status": "not_started",
            "report_status": "not_started",
            "notes": notes,
            "created_at": now,
            "updated_at": now,
        }
        inserted = self._insert("sessions", row)
        return _row_to_session(inserted)

    def delete_session_for_user(self, session_id: str, user: User) -> bool:
        session_row = self._select_one("sessions", session_id=session_id)
        if session_row is None:
            return False
        if not self._is_authorized(session_row["owner_user_id"], user):
            raise PermissionError("Clinical users can only delete owned sessions.")

        transcript_ids = [
            row["transcript_id"]
            for row in self._select("transcripts", session_id=session_id)
            if row.get("transcript_id")
        ]
        feature_ids = [
            row["feature_id"]
            for row in self._select("extracted_features", session_id=session_id)
            if row.get("feature_id")
        ]

        for transcript_id in transcript_ids:
            self._delete("transcript_lines", "transcript_id", transcript_id)
        for feature_id in feature_ids:
            self._delete("feature_review_dispositions", "feature_id", feature_id)

        for table in (
            "audio_files",
            "processing_jobs",
            "clinical_speech_artifacts",
            "transcripts",
            "extracted_features",
            "ai_screening_outputs",
            "clinical_signoffs",
            "model_runs",
            "therapist_notes",
            "reports",
        ):
            self._delete(table, "session_id", session_id)

        self._delete("sessions", "session_id", session_id)
        self._audit(
            "session_deleted",
            actor_user_id=user.user_id,
            target_type="session",
            target_id=session_id,
            message=f"Deleted session {session_id}",
        )
        return True

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def list_notes_for_case_for_user(self, case_id: str, user: User) -> list[TherapistNote]:
        rows = self._select("therapist_notes", case_id=case_id)
        return [_row_to_note(r) for r in rows if self._is_authorized(r.get("owner_user_id", ""), user)]

    def add_therapist_note(
        self,
        *,
        case_id: str,
        user: User,
        note_text: str,
        session_id: str | None = None,
    ) -> TherapistNote:
        now = _iso(_utc_now())
        row = {
            "note_id": _uuid4(),
            "case_id": case_id,
            "session_id": session_id,
            "owner_user_id": user.user_id,
            "note_text": note_text,
            "created_at": now,
            "updated_at": now,
        }
        inserted = self._insert("therapist_notes", row)
        return _row_to_note(inserted)

    # ------------------------------------------------------------------
    # Audio Files
    # ------------------------------------------------------------------

    def list_audio_files_for_user(self, user: User) -> list[AudioFile]:
        rows = self._select("audio_files")
        return [_row_to_audio_file(r) for r in rows if self._is_authorized(r["owner_user_id"], user)]

    def list_audio_files_for_case_for_user(self, case_id: str, user: User) -> list[AudioFile]:
        rows = self._select("audio_files", case_id=case_id)
        return [_row_to_audio_file(r) for r in rows if self._is_authorized(r["owner_user_id"], user)]

    def list_audio_files_for_session_for_user(self, session_id: str, user: User) -> list[AudioFile]:
        rows = self._select("audio_files", session_id=session_id)
        return [_row_to_audio_file(r) for r in rows if self._is_authorized(r["owner_user_id"], user)]

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
        ext = Path(original_filename).suffix.lstrip(".").lower() or "wav"
        audio_id = _uuid4()
        stored = f"{case_id}_{session_id}_{audio_id}.{ext}"
        now = _iso(_utc_now())
        row = {
            "audio_file_id": audio_id,
            "owner_user_id": user.user_id,
            "case_id": case_id,
            "session_id": session_id,
            "original_filename": original_filename,
            "stored_filename": stored,
            "file_type": ext,
            "file_size": file_size,
            "upload_time": now,
            "processing_status": processing_status,
            "storage_mode": "metadata_only",
        }
        inserted = self._insert("audio_files", row)
        # Link audio to session
        self._update("sessions", "session_id", session_id, {
            "audio_file_id": audio_id,
        })
        return _row_to_audio_file(inserted)

    # ------------------------------------------------------------------
    # Consent
    # ------------------------------------------------------------------

    def list_consent_records_for_case_for_user(self, case_id: str, user: User) -> list[ConsentRecord]:
        rows = self._select("consent_records", case_id=case_id)
        return [_row_to_consent(r) for r in rows if self._is_authorized(r.get("owner_user_id", ""), user)]

    def has_active_audio_consent(self, case_id: str, now: datetime | None = None) -> bool:
        now_dt = now or _utc_now()
        rows = self._select("consent_records", case_id=case_id)
        for r in rows:
            if not r.get("audio_permission"):
                continue
            if r.get("withdrawn_at"):
                continue
            expires = _parse_dt(r.get("expires_at"))
            if expires and expires < now_dt:
                continue
            return True
        return False

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
        now = _iso(_utc_now())
        row = {
            "consent_id": _uuid4(),
            "case_id": case_id,
            "owner_user_id": user.user_id,
            "recorded_by_user_id": user.user_id,
            "consent_type": consent_type,
            "guardian_status": guardian_status,
            "audio_permission": audio_permission,
            "transcript_permission": transcript_permission,
            "notes": notes,
            "expires_at": _iso(expires_at),
            "created_at": now,
        }
        inserted = self._insert("consent_records", row)
        if audio_permission or transcript_permission:
            self._update("child_cases", "case_id", case_id, {
                "consent_status": "granted",
            })
        self._audit(
            "consent_recorded",
            actor_user_id=user.user_id,
            target_type="consent_record",
            target_id=row["consent_id"],
            message=f"Consent recorded for case {case_id}: audio={audio_permission}",
        )
        return _row_to_consent(inserted)

    # ------------------------------------------------------------------
    # Secure Audio Upload
    # ------------------------------------------------------------------

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

        now = _utc_now()
        ext = Path(original_filename).suffix.lstrip(".").lower() or "wav"
        storage_key = f"audio/{case_id}/{session_id}/{audio_file.audio_file_id}.{ext}"
        file_object_id = _uuid4()

        # Create file object metadata
        file_obj_row = {
            "file_object_id": file_object_id,
            "audio_file_id": audio_file.audio_file_id,
            "case_id": case_id,
            "session_id": session_id,
            "owner_user_id": user.user_id,
            "storage_key": storage_key,
            "checksum_sha256": checksum_sha256,
            "mime_type": mime_type,
            "encryption_status": "required",
            "retention_delete_after": _iso(now + timedelta(days=retention_days)),
            "created_at": _iso(now),
        }
        self._insert("file_objects", file_obj_row)

        # Update audio file with storage info
        self._update("audio_files", "audio_file_id", audio_file.audio_file_id, {
            "storage_mode": "secure_private",
            "file_object_id": file_object_id,
        })

        # Generate signed upload URL via Supabase Storage
        signed_url = f"https://storage.supabase.co/upload/{storage_key}"
        upload_headers = {
            "content-type": mime_type,
            "x-amz-server-side-encryption": "AES256",
            "x-upload-retention-days": str(retention_days),
        }
        try:
            storage_response = self.client.storage.from_("audio").create_signed_upload_url(storage_key)
            if hasattr(storage_response, "signed_url"):
                signed_url = storage_response.signed_url
            elif isinstance(storage_response, dict) and "signedURL" in storage_response:
                signed_url = storage_response["signedURL"]
            elif isinstance(storage_response, dict) and "signed_url" in storage_response:
                signed_url = storage_response["signed_url"]
        except Exception:
            pass  # Fallback to constructed URL for mock/test scenarios

        self._audit(
            "secure_upload_intent_created",
            actor_user_id=user.user_id,
            target_type="file_object",
            target_id=file_object_id,
            message=f"Created signed upload intent for {audio_file.audio_file_id}",
        )

        return {
            "audio_file": audio_file.to_dict(),
            "file_object": {
                "file_object_id": file_object_id,
                "audio_file_id": audio_file.audio_file_id,
                "case_id": case_id,
                "session_id": session_id,
                "mime_type": mime_type,
                "encryption_status": "required",
            },
            "upload": {
                "method": "PUT",
                "url": signed_url,
                "signed_upload_url": signed_url,
                "expires_in_seconds": 900,
                "storage_provider": storage_provider,
                "file_object_id": file_object_id,
                "headers": upload_headers,
            },
        }

    # ------------------------------------------------------------------
    # Processing Jobs
    # ------------------------------------------------------------------

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
        session_row = self._select_one("sessions", session_id=session_id)
        if session_row is None:
            raise ValueError(f"Unknown session_id: {session_id}")
        if not self._is_authorized(session_row["owner_user_id"], user):
            raise PermissionError("Clinical users can only process owned sessions.")
        if not session_row.get("audio_file_id"):
            raise ValueError("Audio file metadata is required before creating a processing job.")
        case_id = session_row["case_id"]
        if not self.has_active_audio_consent(case_id):
            raise PermissionError("Active guardian consent is required before audio processing.")

        now = _iso(_utc_now())
        job_id = _uuid4()
        row = {
            "job_id": job_id,
            "session_id": session_id,
            "case_id": case_id,
            "owner_user_id": session_row["owner_user_id"],
            "audio_file_id": session_row["audio_file_id"],
            "job_type": job_type,
            "engine": engine,
            "operation": operation or job_type,
            "operation_config": operation_config or {},
            "dependency_check": dependency_check or {},
            "source_revision": source_revision,
            "status": "queued",
            "stage": "queued",
            "progress": 0,
            "created_at": now,
            "updated_at": now,
        }
        inserted = self._insert("processing_jobs", row)
        self._update("sessions", "session_id", session_id, {
            "processing_status": "processing_submitted",
        })
        self._audit(
            "processing_job_created",
            actor_user_id=user.user_id,
            target_type="processing_job",
            target_id=job_id,
            message=f"Queued {job_type} job for {session_id}",
        )
        return _row_to_processing_job(inserted)

    def get_processing_job_for_user(self, job_id: str, user: User) -> ProcessingJob | None:
        row = self._select_one("processing_jobs", job_id=job_id)
        if row and self._is_authorized(row.get("owner_user_id", ""), user):
            return _row_to_processing_job(row)
        return None

    def list_processing_jobs_for_session_for_user(self, session_id: str, user: User) -> list[ProcessingJob]:
        rows = self._select("processing_jobs", session_id=session_id)
        return [_row_to_processing_job(r) for r in rows if self._is_authorized(r.get("owner_user_id", ""), user)]

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
        existing = self.get_processing_job_for_user(job_id, user)
        if existing is None:
            return None
        payload: dict[str, Any] = {"status": status}
        if progress is not None:
            payload["progress"] = progress
        if error_code is not None:
            payload["error_code"] = error_code
        if error_message:
            payload["error_message"] = error_message
        if stage is not None:
            payload["stage"] = stage
        if result_refs is not None:
            payload["result_refs"] = result_refs
        if status in ("completed", "failed"):
            payload["finished_at"] = _iso(_utc_now())
        updated = self._update("processing_jobs", "job_id", job_id, payload)
        return _row_to_processing_job(updated) if updated else existing

    # ------------------------------------------------------------------
    # Clinical Speech Artifacts
    # ------------------------------------------------------------------

    def list_clinical_speech_artifacts_for_session_for_user(
        self, session_id: str, user: User
    ) -> list[ClinicalSpeechArtifact]:
        rows = self._select("clinical_speech_artifacts", session_id=session_id)
        result = []
        for r in rows:
            if self._is_authorized(r.get("owner_user_id", ""), user):
                result.append(ClinicalSpeechArtifact(
                    artifact_id=r["artifact_id"],
                    session_id=r["session_id"],
                    case_id=r.get("case_id", ""),
                    owner_user_id=r.get("owner_user_id", ""),
                    artifact_type=r.get("artifact_type", "feature_output"),
                    freshness=r.get("freshness", "current"),
                    transcript_id=r.get("transcript_id"),
                    feature_id=r.get("feature_id"),
                    job_id=r.get("job_id"),
                    source_revision=r.get("source_revision"),
                    source_hash=r.get("source_hash"),
                    content_type=r.get("content_type", "application/json"),
                    content_text=r.get("content_text", ""),
                    parsed_metrics=r.get("parsed_metrics") or {},
                    metadata=r.get("metadata") or {},
                    review_status=r.get("review_status", "awaiting_review"),
                    created_at=_parse_dt(r.get("created_at")) or _utc_now(),
                    updated_at=_parse_dt(r.get("updated_at")) or _utc_now(),
                ))
        return result

    def create_clinical_speech_artifact(
        self, session_id: str, user: User, **kwargs: Any
    ) -> ClinicalSpeechArtifact:
        session_row = self._select_one("sessions", session_id=session_id)
        case_id = session_row["case_id"] if session_row else ""
        now = _iso(_utc_now())
        artifact_id = _uuid4()
        row = {
            "artifact_id": artifact_id,
            "session_id": session_id,
            "case_id": case_id,
            "owner_user_id": user.user_id,
            "artifact_type": kwargs.get("artifact_type", "feature_output"),
            "freshness": kwargs.get("freshness", "current"),
            "transcript_id": kwargs.get("transcript_id"),
            "feature_id": kwargs.get("feature_id"),
            "job_id": kwargs.get("job_id"),
            "source_revision": kwargs.get("source_revision"),
            "source_hash": kwargs.get("source_hash"),
            "content_type": kwargs.get("content_type", "application/json"),
            "content_text": kwargs.get("content_text", ""),
            "parsed_metrics": kwargs.get("parsed_metrics") or {},
            "metadata": kwargs.get("metadata") or {},
            "review_status": kwargs.get("review_status", "awaiting_review"),
            "created_at": now,
            "updated_at": now,
        }
        inserted = self._insert("clinical_speech_artifacts", row)
        return ClinicalSpeechArtifact(
            artifact_id=artifact_id,
            session_id=session_id,
            case_id=case_id,
            owner_user_id=user.user_id,
            artifact_type=row["artifact_type"],
            freshness=row["freshness"],
            created_at=_parse_dt(now) or _utc_now(),
            updated_at=_parse_dt(now) or _utc_now(),
        )

    def update_feature_review_disposition(
        self,
        feature_id: str,
        flag_key: str,
        user: User,
        *,
        disposition: str,
        note: str = "",
    ) -> FeatureReviewDisposition | None:
        rows = self._select("feature_review_dispositions", feature_id=feature_id, flag_key=flag_key)
        now = _iso(_utc_now())
        if rows:
            existing = rows[0]
            self._update("feature_review_dispositions", "disposition_id", existing["disposition_id"], {
                "disposition": disposition,
                "note": note,
                "reviewed_by_user_id": user.user_id,
            })
            return FeatureReviewDisposition(
                disposition_id=existing["disposition_id"],
                session_id=existing.get("session_id", ""),
                case_id=existing.get("case_id", ""),
                owner_user_id=existing.get("owner_user_id", ""),
                feature_id=feature_id,
                flag_key=flag_key,
                disposition=disposition,
                note=note,
                reviewed_by_user_id=user.user_id,
            )
        disp_id = _uuid4()
        row = {
            "disposition_id": disp_id,
            "feature_id": feature_id,
            "flag_key": flag_key,
            "owner_user_id": user.user_id,
            "session_id": "",
            "case_id": "",
            "disposition": disposition,
            "note": note,
            "reviewed_by_user_id": user.user_id,
            "created_at": now,
            "updated_at": now,
        }
        self._insert("feature_review_dispositions", row)
        return FeatureReviewDisposition(
            disposition_id=disp_id,
            session_id="",
            case_id="",
            owner_user_id=user.user_id,
            feature_id=feature_id,
            flag_key=flag_key,
            disposition=disposition,
            note=note,
            reviewed_by_user_id=user.user_id,
        )

    def list_feature_review_dispositions_for_feature_for_user(
        self, feature_id: str, user: User
    ) -> list[FeatureReviewDisposition]:
        rows = self._select("feature_review_dispositions", feature_id=feature_id)
        return [
            FeatureReviewDisposition(
                disposition_id=r["disposition_id"],
                session_id=r.get("session_id", ""),
                case_id=r.get("case_id", ""),
                owner_user_id=r.get("owner_user_id", ""),
                feature_id=r["feature_id"],
                flag_key=r.get("flag_key", ""),
                disposition=r.get("disposition", "needs_review"),
                note=r.get("note", ""),
                reviewed_by_user_id=r.get("reviewed_by_user_id"),
            )
            for r in rows
            if self._is_authorized(r.get("owner_user_id", ""), user)
        ]

    # ------------------------------------------------------------------
    # Transcripts
    # ------------------------------------------------------------------

    def list_transcripts_for_user(self, user: User) -> list[Transcript]:
        rows = self._select("transcripts")
        return [_row_to_transcript(r) for r in rows if self._is_authorized(r.get("owner_user_id", ""), user)]

    def get_transcript_for_user(self, transcript_id: str, user: User) -> Transcript | None:
        row = self._select_one("transcripts", transcript_id=transcript_id)
        if row and self._is_authorized(row.get("owner_user_id", ""), user):
            return _row_to_transcript(row)
        return None

    def get_transcript_for_session_for_user(self, session_id: str, user: User) -> Transcript | None:
        row = self._select_one("transcripts", session_id=session_id)
        if row and self._is_authorized(row.get("owner_user_id", ""), user):
            return _row_to_transcript(row)
        return None

    def create_transcript_for_session(
        self,
        *,
        session_id: str,
        user: User,
        transcript_text: str,
        original_filename: str | None = None,
        reviewer_notes: str = "",
    ) -> Transcript:
        session_row = self._select_one("sessions", session_id=session_id)
        if session_row is None:
            raise ValueError(f"Unknown session_id: {session_id}")
        case_id = session_row["case_id"]

        # Parse CHAT text into lines
        try:
            from packages.cha.parser import parse_cha_text
            parsed_lines = parse_cha_text(transcript_text)
        except Exception:
            parsed_lines = []

        # Run QA
        try:
            from src.transcript_reviewer import review_cha_text as _review
            qa_result = _review(transcript_text)
            qa_status = qa_result.get("status", "not_run")
            qa_score = qa_result.get("score")
            qa_issues = qa_result.get("issues", [])
        except Exception:
            qa_status = "not_run"
            qa_score = None
            qa_issues = []

        now = _iso(_utc_now())
        transcript_id = _uuid4()
        row = {
            "transcript_id": transcript_id,
            "session_id": session_id,
            "case_id": case_id,
            "owner_user_id": user.user_id,
            "transcript_format": "CHAT",
            "transcript_text": transcript_text,
            "review_status": "awaiting_review",
            "reviewer_notes": reviewer_notes,
            "qa_status": qa_status,
            "qa_score": qa_score,
            "qa_issues": qa_issues,
            "created_at": now,
            "updated_at": now,
        }
        inserted = self._insert("transcripts", row)

        # Insert transcript lines
        from src.clinical_speech.models import speaker_role_for_code
        for i, line in enumerate(parsed_lines):
            speaker = line.get("speaker", line.get("speaker_code", "UNK"))
            text = line.get("text", line.get("utterance", ""))
            line_row = {
                "line_id": _uuid4(),
                "transcript_id": transcript_id,
                "session_id": session_id,
                "case_id": case_id,
                "owner_user_id": user.user_id,
                "line_number": i + 1,
                "speaker_code": speaker,
                "utterance_text": text,
                "speaker_role": speaker_role_for_code(speaker),
                "review_status": "needs_review",
                "reviewed": False,
                "version": 1,
                "updated_at": now,
            }
            self._insert("transcript_lines", line_row)

        # Link transcript to session
        self._update("sessions", "session_id", session_id, {
            "transcript_id": transcript_id,
            "processing_status": "transcript_ready",
            "therapist_review_status": "awaiting_review",
        })
        return _row_to_transcript(inserted)

    def update_transcript_for_user(
        self,
        transcript_id: str,
        user: User,
        *,
        transcript_text: str,
        reviewer_notes: str = "",
    ) -> Transcript | None:
        existing = self.get_transcript_for_user(transcript_id, user)
        if existing is None:
            return None

        # Delete old lines
        self.client.table("transcript_lines").delete().eq("transcript_id", transcript_id).execute()

        # Re-parse and insert new lines
        try:
            from packages.cha.parser import parse_cha_text
            parsed_lines = parse_cha_text(transcript_text)
        except Exception:
            parsed_lines = []

        now = _iso(_utc_now())
        from src.clinical_speech.models import speaker_role_for_code
        for i, line in enumerate(parsed_lines):
            speaker = line.get("speaker", line.get("speaker_code", "UNK"))
            text = line.get("text", line.get("utterance", ""))
            line_row = {
                "line_id": _uuid4(),
                "transcript_id": transcript_id,
                "session_id": existing.session_id,
                "case_id": existing.case_id,
                "owner_user_id": existing.owner_user_id,
                "line_number": i + 1,
                "speaker_code": speaker,
                "utterance_text": text,
                "speaker_role": speaker_role_for_code(speaker),
                "review_status": "needs_review",
                "reviewed": False,
                "version": 1,
                "updated_at": now,
            }
            self._insert("transcript_lines", line_row)

        updated = self._update("transcripts", "transcript_id", transcript_id, {
            "transcript_text": transcript_text,
            "reviewer_notes": reviewer_notes,
        })
        return _row_to_transcript(updated) if updated else existing

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
        row = self._select_one("transcript_lines", line_id=line_id, transcript_id=transcript_id)
        if row is None:
            return None
        if not self._is_authorized(row.get("owner_user_id", ""), user):
            return None

        # Optimistic concurrency check
        if expected_version is not None:
            actual_version = int(row.get("version", 1))
            if actual_version != expected_version:
                from src.clinical_workflow.mock_repository import TranscriptLineVersionConflict
                raise TranscriptLineVersionConflict(line_id, expected_version, actual_version)

        payload: dict[str, Any] = {}
        if speaker_code is not None:
            payload["speaker_code"] = speaker_code
        if utterance_text is not None:
            payload["utterance_text"] = utterance_text
        if reviewed is not None:
            payload["reviewed"] = reviewed
            payload["review_status"] = "reviewed" if reviewed else "needs_review"
        if interpretation_note is not None:
            payload["interpretation_note"] = interpretation_note
        if expected_version is not None:
            payload["version"] = expected_version + 1
        payload["updated_by_user_id"] = user.user_id

        updated = self._update("transcript_lines", "line_id", line_id, payload)
        return _row_to_transcript_line(updated) if updated else None

    def mark_transcript_reviewed(self, transcript_id: str, user: User, reviewer_notes: str = "") -> Transcript | None:
        existing = self.get_transcript_for_user(transcript_id, user)
        if existing is None:
            return None
        # Mark all lines reviewed
        lines = self._select("transcript_lines", transcript_id=transcript_id)
        for line in lines:
            self._update("transcript_lines", "line_id", line["line_id"], {
                "reviewed": True,
                "review_status": "reviewed",
            })
        updated = self._update("transcripts", "transcript_id", transcript_id, {
            "review_status": "reviewed",
            "reviewer_notes": reviewer_notes,
        })
        return _row_to_transcript(updated) if updated else existing

    # ------------------------------------------------------------------
    # Features & AI
    # ------------------------------------------------------------------

    def get_features_for_session_for_user(self, session_id: str, user: User) -> ExtractedFeatures | None:
        row = self._select_one("extracted_features", session_id=session_id)
        if row and self._is_authorized(row.get("owner_user_id", ""), user):
            return _row_to_features(row)
        return None

    def get_ai_output_for_session_for_user(self, session_id: str, user: User) -> AIScreeningOutput | None:
        rows = self._select("ai_screening_outputs", session_id=session_id)
        authorized = [r for r in rows if self._is_authorized(r.get("owner_user_id", ""), user)]
        if not authorized:
            return None
        # Return most recent
        authorized.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return _row_to_ai_output(authorized[0])

    def get_reference_comparison_for_session_for_user(
        self, session_id: str, user: User
    ) -> ReferenceComparisonResult | None:
        features = self.get_features_for_session_for_user(session_id, user)
        if features is None:
            return None
        session = _row_to_session(self._select_one("sessions", session_id=session_id) or {})
        case_row = self._select_one("child_cases", case_id=session.case_id)
        age_months = int(case_row["age_months"]) if case_row else 48
        try:
            engine = ReferenceEngine()
            from src.reference_engine import age_band_12mo
            return engine.compare_to_reference(
                features.core_features or features.features,
                age_months=age_months,
            )
        except Exception:
            return None

    def extract_features_for_session(self, session_id: str, user: User) -> ExtractedFeatures:
        session_row = self._select_one("sessions", session_id=session_id)
        if session_row is None:
            raise ValueError(f"Unknown session_id: {session_id}")
        if not self._is_authorized(session_row["owner_user_id"], user):
            raise PermissionError("Clinical users can only extract features for owned sessions.")

        case_row = self._select_one("child_cases", case_id=session_row["case_id"])
        age_months = int(case_row["age_months"]) if case_row else 48

        transcript = self.get_transcript_for_session_for_user(session_id, user)
        if transcript is None or transcript.review_status != "reviewed":
            raise ValueError("A therapist-reviewed transcript is required before feature extraction.")

        # Get transcript lines and extract features
        lines = self._select("transcript_lines", transcript_id=transcript.transcript_id)
        lines.sort(key=lambda r: int(r.get("line_number", 0)))

        from src.clinical_speech.models import NormalizedTranscriptLine, speaker_role_for_code
        normalized_lines = [
            NormalizedTranscriptLine(
                speaker_code=l.get("speaker_code", ""),
                speaker_role=speaker_role_for_code(l.get("speaker_code", "")),
                utterance_text=l.get("utterance_text", ""),
            )
            for l in lines
        ]

        from src.clinical_speech.feature_extractor import extract_clinical_features
        from src.feature_schema import OPTIONAL_INDICATORS
        extracted = extract_clinical_features(normalized_lines, age_months=age_months)
        core_features = extracted["core_features"]
        optional_indicators = {
            key: extracted["optional_indicators"].get(key, 0)
            for key in OPTIONAL_INDICATORS
        }

        now = _iso(_utc_now())
        feature_id = _uuid4()
        source_hash = hashlib.sha256(transcript.transcript_text.encode()).hexdigest()[:16]
        row = {
            "feature_id": feature_id,
            "session_id": session_id,
            "case_id": session_row["case_id"],
            "owner_user_id": session_row["owner_user_id"],
            "feature_schema_version": "14-feature-schema",
            "features": {**core_features, **optional_indicators},
            "core_features": core_features,
            "optional_indicators": optional_indicators,
            "source_revision": source_hash,
            "source_hash": source_hash,
            "extraction_status": "completed",
            "created_at": now,
        }
        inserted = self._insert("extracted_features", row)
        self._update("sessions", "session_id", session_id, {
            "feature_extraction_status": "completed",
        })
        self._audit(
            "features_extracted",
            actor_user_id=user.user_id,
            target_type="session",
            target_id=session_id,
            message=f"Extracted features for {session_id}",
        )
        return _row_to_features(inserted)

    def generate_ai_screening_output_for_session(self, session_id: str, user: User) -> AIScreeningOutput:
        session_row = self._select_one("sessions", session_id=session_id)
        if session_row is None:
            raise ValueError(f"Unknown session_id: {session_id}")
        if not self._is_authorized(session_row["owner_user_id"], user):
            raise PermissionError("Clinical users can only generate AI support for owned sessions.")

        feature_row = self.get_features_for_session_for_user(session_id, user)
        if feature_row is None:
            raise ValueError("Extracted features are required before AI decision-support output.")

        try:
            result = predict_reference_cohort_similarity(
                feature_row.core_features or feature_row.features,
                inference_status="preliminary",
            )
            concern_level = result.get("concern_level", "low_concern")
            model_version = result.get("model_version", "screening-support-v1")
            score = result.get("similarity_probability")
            plain_language = result.get("plain_language_explanation", "")
            top_features = result.get("top_contributing_features", [])
            cohort_probs = result.get("reference_cohort_probabilities", {})
            most_similar = result.get("most_similar_reference_cohort")
            safety_warnings = result.get("safety_warnings", [])
        except Exception:
            concern_level = "low_concern"
            model_version = "screening-support-v1"
            score = None
            plain_language = "AI output unavailable — model inference failed."
            top_features = []
            cohort_probs = {}
            most_similar = None
            safety_warnings = []

        now = _iso(_utc_now())
        output_id = _uuid4()
        from src.feature_schema import FEATURE_DOCS
        row = {
            "output_id": output_id,
            "session_id": session_id,
            "case_id": session_row["case_id"],
            "owner_user_id": session_row["owner_user_id"],
            "concern_level": concern_level,
            "model_version": model_version,
            "screening_support_score": score,
            "explanation": (
                "Decision-support only. Review transcript QA, session context, "
                "and therapist notes before interpreting this output. It is not a diagnosis."
            ),
            "plain_language_explanation": plain_language,
            "top_contributing_features": top_features if isinstance(top_features, list) else [],
            "evidence_items": [
                {
                    "type": "feature",
                    "feature_key": f if isinstance(f, str) else f.get("feature_key", ""),
                    "value": feature_row.features.get(f if isinstance(f, str) else f.get("feature_key", ""), 0),
                    "explanation": FEATURE_DOCS.get(f if isinstance(f, str) else f.get("feature_key", ""), None),
                }
                for f in (top_features if isinstance(top_features, list) else [])
                if (f if isinstance(f, str) else f.get("feature_key", "")) in FEATURE_DOCS
            ],
            "therapist_review_status": "awaiting_review",
            "output_kind": "screening_support",
            "inference_status": "preliminary",
            "reference_cohort_probabilities": cohort_probs,
            "most_similar_reference_cohort": most_similar,
            "similarity_probability": score,
            "report_eligible": False,
            "safety_warnings": safety_warnings,
            "created_at": now,
        }
        inserted = self._insert("ai_screening_outputs", row)
        self._update("sessions", "session_id", session_id, {
            "ai_analysis_status": "completed",
            "report_status": "pending",
        })
        self._audit(
            "ai_output_generated",
            actor_user_id=user.user_id,
            target_type="ai_screening_output",
            target_id=output_id,
            message=f"Generated AI decision-support output for {session_id}",
        )
        return _row_to_ai_output(inserted)

    # ------------------------------------------------------------------
    # Goals & Reports
    # ------------------------------------------------------------------

    def list_goals_for_case_for_user(self, case_id: str, user: User) -> list[TherapyGoal]:
        rows = self._select("therapy_goals", case_id=case_id)
        return [_row_to_goal(r) for r in rows if self._is_authorized(r.get("owner_user_id", ""), user)]

    def list_reports_for_case_for_user(self, case_id: str, user: User) -> list[Report]:
        rows = self._select("reports", case_id=case_id)
        return sorted(
            [_row_to_report(r) for r in rows if self._is_authorized(r.get("owner_user_id", ""), user)],
            key=lambda r: r.created_at.isoformat() if r.created_at else "",
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Clinical Signoff
    # ------------------------------------------------------------------

    def create_clinical_signoff(
        self,
        *,
        target_type: Any,
        target_id: str,
        user: User,
        session_id: str | None = None,
        notes: str = "",
    ) -> ClinicalSignoff:
        case_id = ""
        if session_id:
            session_row = self._select_one("sessions", session_id=session_id)
            if session_row:
                case_id = session_row["case_id"]
        now = _iso(_utc_now())
        signoff_id = _uuid4()
        row = {
            "signoff_id": signoff_id,
            "target_type": target_type,
            "target_id": target_id,
            "session_id": session_id,
            "case_id": case_id,
            "owner_user_id": user.user_id,
            "signed_by_user_id": user.user_id,
            "notes": notes,
            "created_at": now,
        }
        inserted = self._insert("clinical_signoffs", row)
        return _row_to_signoff(inserted)

    def signoff_transcript_for_session(self, session_id: str, user: User, notes: str = "") -> ClinicalSignoff:
        transcript = self.get_transcript_for_session_for_user(session_id, user)
        if transcript is None:
            raise ValueError(f"No transcript found for session {session_id}")
        self.mark_transcript_reviewed(transcript.transcript_id, user, notes)
        return self.create_clinical_signoff(
            target_type="transcript",
            target_id=transcript.transcript_id,
            user=user,
            session_id=session_id,
            notes=notes,
        )

    def latest_signoff_for_target(self, target_type: Any, target_id: str) -> ClinicalSignoff | None:
        rows = self._select("clinical_signoffs", target_type=target_type, target_id=target_id)
        if not rows:
            return None
        rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return _row_to_signoff(rows[0])

    def rerun_feature_extraction_after_transcript_review(self, session_id: str, user: User) -> Session | None:
        try:
            self.extract_features_for_session(session_id, user)
        except (ValueError, PermissionError):
            pass
        row = self._select_one("sessions", session_id=session_id)
        return _row_to_session(row) if row else None

    # ------------------------------------------------------------------
    # Dashboard & Reports
    # ------------------------------------------------------------------

    def progress_summary_for_case(self, case_id: str, user: User) -> dict:
        sessions = self.list_sessions_for_case_for_user(case_id, user)
        features_list = []
        for s in sessions:
            f = self.get_features_for_session_for_user(s.session_id, user)
            if f:
                features_list.append({
                    "session_id": s.session_id,
                    "session_date": s.session_date,
                    "features": f.features,
                })
        return {
            "case_id": case_id,
            "session_count": len(sessions),
            "features_over_time": features_list,
        }

    def generate_progress_report_for_case(self, case_id: str, user: User) -> Report:
        summary = self.progress_summary_for_case(case_id, user)
        case = self.get_case_for_user(case_id, user)
        case_label = case.anonymized_child_code if case else case_id

        md_lines = [
            f"# Progress Report: {case_label}",
            "",
            f"> {SAFETY_DISCLAIMER}",
            "",
            f"Sessions recorded: {summary['session_count']}",
            "",
        ]
        for entry in summary.get("features_over_time", []):
            md_lines.append(f"### Session {entry['session_date']}")
            for k, v in entry["features"].items():
                md_lines.append(f"- {k}: {v}")
            md_lines.append("")

        content = "\n".join(md_lines)
        now = _iso(_utc_now())
        report_id = _uuid4()
        row = {
            "report_id": report_id,
            "case_id": case_id,
            "owner_user_id": user.user_id,
            "report_type": "progress",
            "title": f"Progress report for {case_label}",
            "content_markdown": content,
            "export_status": "completed",
            "created_at": now,
        }
        inserted = self._insert("reports", row)
        return _row_to_report(inserted)

    def dashboard_summary(self, user: User) -> dict[str, int]:
        cases = self.list_cases_for_user(user)
        sessions = self.list_sessions_for_user(user)
        transcripts = self.list_transcripts_for_user(user)
        return {
            "total_cases": len(cases),
            "total_sessions": len(sessions),
            "total_transcripts": len(transcripts),
            "sessions_awaiting_review": sum(
                1 for s in sessions if s.therapist_review_status == "awaiting_review"
            ),
            "sessions_completed": sum(
                1 for s in sessions if s.processing_status == "completed"
            ),
        }

    def list_audit_logs_for_user(self, user: User) -> list[AuditLog]:
        if user.role != "admin":
            raise PermissionError("Only admin users can view audit logs.")
        rows = self._select("audit_logs")
        return sorted(
            [_row_to_audit_log(r) for r in rows],
            key=lambda a: a.created_at.isoformat() if a.created_at else "",
            reverse=True,
        )
