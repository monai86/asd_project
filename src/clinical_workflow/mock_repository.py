"""Deterministic mock repository for the therapist clinical workspace."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
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
    ConsentStatus,
    ExternalClinicalStatus,
    ExtractedFeatures,
    MAX_AUDIO_FILE_SIZE_BYTES,
    MOCK_MODE,
    ProcessingStatus,
    Report,
    SAFETY_DISCLAIMER,
    Session,
    SessionType,
    Sex,
    TherapyGoal,
    TherapistNote,
    Transcript,
    User,
)
from src.feature_schema import FEATURE_DOCS, FEATURES
from src.therapist_report import METRIC_DIRECTIONS, REPORT_METRICS
from src.transcript_reviewer import review_cha_text


NowProvider = Callable[[], datetime]


class MockClinicalRepository:
    """In-memory clinical workflow store with explicit ownership filtering."""

    def __init__(self, now_provider: NowProvider | None = None) -> None:
        self.mock_mode = MOCK_MODE
        self._now = now_provider or (lambda: datetime.now(timezone.utc))
        self.users: dict[str, User] = {}
        self.cases: dict[str, ChildCase] = {}
        self.sessions: dict[str, Session] = {}
        self.audio_files: dict[str, AudioFile] = {}
        self.transcripts: dict[str, Transcript] = {}
        self.extracted_features: dict[str, ExtractedFeatures] = {}
        self.ai_screening_outputs: dict[str, AIScreeningOutput] = {}
        self.therapy_goals: dict[str, TherapyGoal] = {}
        self.therapist_notes: dict[str, TherapistNote] = {}
        self.reports: dict[str, Report] = {}
        self.audit_logs: list[AuditLog] = []
        self._password_by_email: dict[str, str] = {}
        self._case_sequence = 0
        self._session_sequence = 0
        self._audio_file_sequence = 0
        self._transcript_sequence = 0
        self._feature_sequence = 0
        self._ai_output_sequence = 0
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

    def get_ai_output_for_session_for_user(self, session_id: str, user: User) -> AIScreeningOutput | None:
        session = self.sessions.get(session_id)
        if session is None or self.get_case_for_user(session.case_id, user) is None:
            return None
        row = next((item for item in self.ai_screening_outputs.values() if item.session_id == session_id), None)
        return replace(row) if row else None

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
        if not anonymized_child_code.strip():
            raise ValueError("anonymized_child_code is required.")
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
        self._feature_sequence += 1
        feature_row = ExtractedFeatures(
            feature_id=f"FEATURE-{self._feature_sequence:03d}",
            session_id=session_id,
            case_id=session.case_id,
            owner_user_id=session.owner_user_id,
            feature_schema_version="14-feature-schema",
            features=self._mock_features_from_transcript(case, transcript.transcript_text),
            created_at=now,
        )
        self.extracted_features[feature_row.feature_id] = feature_row
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
            screening_support_score=score,
            explanation=(
                "Decision-support only. Review transcript QA, session context, "
                "and therapist notes before interpreting this output."
            ),
            top_contributing_features=top_features,
            evidence_items=[
                FEATURE_DOCS[feature].clinical_meaning
                for feature in top_features
                if feature in FEATURE_DOCS
            ],
            therapist_review_status="awaiting_review",
            created_at=now,
        )
        self.ai_screening_outputs[output.output_id] = output
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
        ai_outputs_by_session = {
            output.session_id: output
            for output in self.ai_screening_outputs.values()
            if output.case_id == case_id
        }
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
        if user.role == "admin":
            rows = self.audit_logs
        else:
            rows = [log for log in self.audit_logs if log.actor_user_id == user.user_id]
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
        self.sessions["SESSION-001"] = replace(
            self.sessions["SESSION-001"],
            transcript_id=seed_transcript.transcript_id,
        )
        self._transcript_sequence = len(self.transcripts)
        seed_features = ExtractedFeatures(
            feature_id="FEATURE-001",
            session_id="SESSION-001",
            case_id="CASE-001",
            owner_user_id="user_therapist_001",
            feature_schema_version="14-feature-schema",
            features=self._mock_features_from_transcript(
                self.cases["CASE-001"],
                seed_transcript.transcript_text,
            ),
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
            screening_support_score=0.68,
            explanation="Seeded prototype support output for mock dashboard review. Use as clinician review support only.",
            top_contributing_features=["unintelligible_ratio", "echolalia_ratio", "ttr"],
            evidence_items=[
                FEATURE_DOCS["unintelligible_ratio"].clinical_meaning,
                FEATURE_DOCS["echolalia_ratio"].clinical_meaning,
                FEATURE_DOCS["ttr"].clinical_meaning,
            ],
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
    def _mock_screening_support_score(features: dict[str, float]) -> float:
        marker_load = (
            features["unintelligible_ratio"] * 0.22
            + min(features["zero_vocalization_count"], 4) * 0.035
            + features["echolalia_ratio"] * 0.2
            + min(features["pronoun_reversal_count"], 3) * 0.04
        )
        language_support = max(0.0, 0.22 - min(features["mlu"], 5) * 0.025)
        return round(min(0.9, max(0.12, 0.38 + marker_load + language_support)), 2)

    @staticmethod
    def _top_contributing_features(features: dict[str, float]) -> list[str]:
        candidates = {
            "unintelligible_ratio": features["unintelligible_ratio"],
            "echolalia_ratio": features["echolalia_ratio"],
            "pronoun_reversal_count": features["pronoun_reversal_count"] / 3,
            "zero_vocalization_count": features["zero_vocalization_count"] / 4,
            "ttr": max(0, 0.55 - features["ttr"]),
            "mlu": max(0, 3.5 - features["mlu"]) / 3.5,
        }
        return [feature for feature, _ in sorted(candidates.items(), key=lambda item: item[1], reverse=True)[:3]]

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
                    "\n".join(f"- {item}" for item in row["evidence_items"])
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
