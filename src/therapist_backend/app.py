"""Clinical-ready FastAPI surface for the therapist workflow.

The app intentionally starts with the deterministic mock repository so the API
contract can be developed and tested before PostgreSQL and object storage are
configured. Production adapters should preserve these route semantics and
backend-enforced RBAC/consent gates.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.clinical_workflow import MockClinicalRepository
from src.clinical_workflow.mock_repository import TranscriptLineVersionConflict
from src.clinical_workflow.models import SAFETY_DISCLAIMER, User
from src.reference_engine import ReferenceEngine, age_band_12mo, assert_descriptive_wording
from src.transcript_reviewer import review_cha_text


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
READINESS_INDEX_PATH = PROJECT_ROOT / "data" / "reference" / "reference_readiness_index.json"

THAI_SAFETY_SENTENCE = "ตอนนี้ระบบเป็น research prototype และ demo เพื่อการศึกษา ไม่ใช่เครื่องมือวินิจฉัยทางการแพทย์"


class LoginRequest(BaseModel):
    email: str
    password: str


class CaseCreateRequest(BaseModel):
    anonymized_child_code: str
    age_months: int = Field(ge=0)
    sex: str = "not_specified"
    primary_concerns: str
    consent_status: str = "pending"
    anonymization_status: str = "anonymized"
    external_clinical_status: str = "not_provided"
    notes: str = ""


class CasePatchRequest(BaseModel):
    age_months: int | None = Field(default=None, ge=0)
    sex: str | None = None
    primary_concerns: str | None = None
    consent_status: str | None = None
    anonymization_status: str | None = None
    external_clinical_status: str | None = None
    notes: str | None = None


class ConsentRequest(BaseModel):
    audio_permission: bool = True
    transcript_permission: bool = True
    consent_type: str = "clinical_audio_processing"
    guardian_status: str = "guardian"
    notes: str = ""
    expires_at: datetime | None = None


class SessionCreateRequest(BaseModel):
    case_id: str
    session_date: date
    session_type: str = "therapy_session"
    notes: str = ""


class SessionPatchRequest(BaseModel):
    notes: str | None = None


class UploadIntentRequest(BaseModel):
    original_filename: str
    file_size: int = Field(gt=0)
    mime_type: str = "application/octet-stream"
    checksum_sha256: str | None = None
    retention_days: int = Field(default=90, ge=1)
    storage_provider: str = "supabase"


class TranscriptPatchRequest(BaseModel):
    transcript_text: str
    reviewer_notes: str = ""


class TranscriptLinePatchRequest(BaseModel):
    speaker_code: str | None = None
    utterance_text: str | None = None
    text: str | None = None
    reviewed: bool | None = None
    interpretation_note: str | None = None
    expected_version: int | None = Field(default=None, ge=1)


class SignoffRequest(BaseModel):
    notes: str = ""


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def create_app(repo: MockClinicalRepository | None = None) -> FastAPI:
    repository = repo or MockClinicalRepository()
    app = FastAPI(
        title="ASD Therapist Clinical Pilot API",
        version="1.2.1",
        description=(
            "Clinical decision-support API for therapist transcript review, "
            "secure audio upload, progress tracking, and sign-off gates."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def current_user(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> User:
        if not x_user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-Id header is required.")
        user = repository.get_user(x_user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user.")
        return user

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "therapist-clinical-pilot-api",
            "safety": SAFETY_DISCLAIMER,
        }

    @app.post("/api/auth/session")
    def login(payload: LoginRequest) -> dict:
        user = repository.authenticate(payload.email, payload.password)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
        return {
            "user": _jsonable(user),
            "session_token": user.user_id,
            "token_type": "mock-user-id",
            "safety": SAFETY_DISCLAIMER,
        }

    @app.get("/api/me")
    def me(user: User = Depends(current_user)) -> dict:
        return {"user": _jsonable(user), "thai_safety_sentence": THAI_SAFETY_SENTENCE}

    @app.get("/api/cases")
    def list_cases(user: User = Depends(current_user)) -> list[dict]:
        return _jsonable(repository.list_cases_for_user(user))

    @app.post("/api/cases", status_code=status.HTTP_201_CREATED)
    def create_case(payload: CaseCreateRequest, user: User = Depends(current_user)) -> dict:
        try:
            row = repository.create_case(owner_user_id=user.user_id, **payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return _jsonable(row)

    @app.patch("/api/cases/{case_id}")
    def patch_case(case_id: str, payload: CasePatchRequest, user: User = Depends(current_user)) -> dict:
        row = repository.update_case_for_user(
            case_id,
            user,
            **{key: value for key, value in payload.model_dump().items() if value is not None},
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found or access denied.")
        return _jsonable(row)

    @app.post("/api/cases/{case_id}/consent", status_code=status.HTTP_201_CREATED)
    def record_consent(case_id: str, payload: ConsentRequest, user: User = Depends(current_user)) -> dict:
        try:
            return _jsonable(repository.record_consent(case_id=case_id, user=user, **payload.model_dump()))
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/api/sessions")
    def list_sessions(user: User = Depends(current_user)) -> list[dict]:
        return _jsonable(repository.list_sessions_for_user(user))

    @app.post("/api/sessions", status_code=status.HTTP_201_CREATED)
    def create_session(payload: SessionCreateRequest, user: User = Depends(current_user)) -> dict:
        try:
            return _jsonable(
                repository.create_session(
                    case_id=payload.case_id,
                    user=user,
                    session_date=payload.session_date.isoformat(),
                    session_type=payload.session_type,  # type: ignore[arg-type]
                    notes=payload.notes,
                )
            )
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.patch("/api/sessions/{session_id}")
    def patch_session(session_id: str, payload: SessionPatchRequest, user: User = Depends(current_user)) -> dict:
        session = next((item for item in repository.list_sessions_for_user(user) if item.session_id == session_id), None)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or access denied.")
        if payload.notes is not None:
            session.notes = payload.notes.strip()
            repository.sessions[session_id] = session
        return _jsonable(session)

    @app.post("/api/sessions/{session_id}/audio/upload-intent", status_code=status.HTTP_201_CREATED)
    def create_upload_intent(session_id: str, payload: UploadIntentRequest, user: User = Depends(current_user)) -> dict:
        session = next((item for item in repository.list_sessions_for_user(user) if item.session_id == session_id), None)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or access denied.")
        try:
            return _jsonable(
                repository.create_secure_audio_upload_intent(
                    case_id=session.case_id,
                    session_id=session_id,
                    user=user,
                    **payload.model_dump(),
                )
            )
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.post("/api/sessions/{session_id}/process-audio", status_code=status.HTTP_202_ACCEPTED)
    def process_audio(session_id: str, user: User = Depends(current_user)) -> dict:
        try:
            return _jsonable(repository.create_processing_job(session_id, user))
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str, user: User = Depends(current_user)) -> dict:
        job = repository.get_processing_job_for_user(job_id, user)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found or access denied.")
        return _jsonable(job)

    @app.get("/api/sessions/{session_id}/transcript")
    def get_transcript(session_id: str, user: User = Depends(current_user)) -> dict:
        transcript = repository.get_transcript_for_session_for_user(session_id, user)
        if transcript is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found.")
        return _jsonable(transcript)

    @app.patch("/api/sessions/{session_id}/transcript")
    def update_transcript(session_id: str, payload: TranscriptPatchRequest, user: User = Depends(current_user)) -> dict:
        transcript = repository.get_transcript_for_session_for_user(session_id, user)
        if transcript is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found.")
        updated = repository.update_transcript_for_user(
            transcript.transcript_id,
            user,
            transcript_text=payload.transcript_text,
            reviewer_notes=payload.reviewer_notes,
        )
        return _jsonable(updated)

    @app.patch("/api/transcripts/{transcript_id}/lines/{line_id}")
    def update_transcript_line(
        transcript_id: str,
        line_id: str,
        payload: TranscriptLinePatchRequest,
        user: User = Depends(current_user),
    ) -> dict:
        try:
            updated = repository.update_transcript_line_for_user(
                transcript_id,
                line_id,
                user,
                speaker_code=payload.speaker_code,
                utterance_text=payload.utterance_text if payload.utterance_text is not None else payload.text,
                reviewed=payload.reviewed,
                interpretation_note=payload.interpretation_note,
                expected_version=payload.expected_version,
            )
        except TranscriptLineVersionConflict as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "TRANSCRIPT_LINE_VERSION_CONFLICT",
                    "line_id": exc.line_id,
                    "expected_version": exc.expected_version,
                    "actual_version": exc.actual_version,
                },
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript line not found or access denied.")
        return _jsonable(updated)

    @app.post("/api/sessions/{session_id}/transcript/signoff")
    def signoff_transcript(session_id: str, payload: SignoffRequest, user: User = Depends(current_user)) -> dict:
        try:
            return _jsonable(repository.signoff_transcript_for_session(session_id, user, payload.notes))
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.post("/api/sessions/{session_id}/features/extract")
    def extract_features(session_id: str, user: User = Depends(current_user)) -> dict:
        try:
            return _jsonable(repository.extract_features_for_session(session_id, user))
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/api/sessions/{session_id}/features")
    def get_features(session_id: str, user: User = Depends(current_user)) -> dict:
        features = repository.get_features_for_session_for_user(session_id, user)
        if features is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Features not found.")
        return _jsonable(features)

    @app.get("/api/sessions/{session_id}/ai-output")
    def get_ai_output(session_id: str, user: User = Depends(current_user)) -> dict:
        output = repository.get_ai_output_for_session_for_user(session_id, user)
        if output is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI screening output not found.")
        return _jsonable(output)


    @app.get("/api/sessions/{session_id}/qa")
    def get_transcript_qa(session_id: str, user: User = Depends(current_user)) -> dict:
        transcript = repository.get_transcript_for_session_for_user(session_id, user)
        if transcript is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript not found or access denied.",
            )
        qa_result = review_cha_text(transcript.transcript_text)
        return _jsonable({
            "transcript_id": transcript.transcript_id,
            "session_id": transcript.session_id,
            "status": qa_result["status"],
            "quality_score": qa_result["quality_score"],
            "qa_status": qa_result["status"],
            "qa_score": qa_result["quality_score"],
            "summary": qa_result["summary"],
            "issues": qa_result["issues"],
            "qa_issues": qa_result["issues"],
            "readiness": qa_result["readiness"],
            "transcript_updated_at": transcript.updated_at,
            "generated_at": datetime.now(timezone.utc),
        })

    @app.get("/api/sessions/{session_id}/reference-comparison")
    def get_reference_comparison(session_id: str, user: User = Depends(current_user)) -> dict:
        try:
            comparison = repository.get_reference_comparison_for_session_for_user(session_id, user)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if comparison is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied.",
            )
        return _jsonable(comparison.to_dict())

    @app.get("/api/sessions/{session_id}/reference-similarity")
    def get_reference_similarity(
        session_id: str,
        user: User = Depends(current_user),
    ) -> dict:
        session = next((item for item in repository.list_sessions_for_user(user) if item.session_id == session_id), None)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied.",
            )
        
        features_record = repository.get_features_for_session_for_user(session_id, user)
        if not features_record:
            features_record = repository.extracted_features.get(f"FEATURE-001")
        
        if not features_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Extracted features are required before calculating similarity."
            )
        
        age_months = features_record.features.get("age_months")
        if age_months is None:
            case = repository.get_case_for_user(session.case_id, user)
            age_months = case.age_months if case else 48
            
        if repository.reference_engine is None:
            repository.reference_engine = ReferenceEngine()

        results = repository.reference_engine.retrieve_similar_cases(
            features=features_record.features,
            age_months=age_months,
            session_type=session.session_type,
            k=5
        )
        
        payload = {
            "status": "ok",
            "similarity_term": "Reference Similarity Retrieval",
            "session_id": session_id,
            "age_band_12mo": age_band_12mo(age_months),
            "task_type": session.session_type,
            "results": results
        }
        assert_descriptive_wording(payload)
        return payload

    @app.get("/api/reference/readiness")
    def get_reference_readiness(user: User = Depends(current_user)) -> dict:
        if not READINESS_INDEX_PATH.exists():
            return {
                "summary": {"ok": 0, "low_n": 0, "not_cohort_ready": 0},
                "cells": [],
                "status": "unavailable",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_files": []
            }
        try:
            with open(READINESS_INDEX_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["status"] = "ready"
            return data
        except Exception as exc:
            return {
                "summary": {"ok": 0, "low_n": 0, "not_cohort_ready": 0},
                "cells": [],
                "status": "error",
                "error_detail": str(exc),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_files": []
            }

    @app.post("/api/sessions/{session_id}/report")
    def create_report(session_id: str, user: User = Depends(current_user)) -> dict:
        session = next((item for item in repository.list_sessions_for_user(user) if item.session_id == session_id), None)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or access denied.")
        try:
            return _jsonable(repository.generate_progress_report_for_case(session.case_id, user))
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/progress")
    def get_case_progress(case_id: str, user: User = Depends(current_user)) -> dict:
        try:
            return _jsonable(repository.progress_summary_for_case(case_id, user))
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    @app.get("/api/audit-logs")
    def audit_logs(user: User = Depends(current_user)) -> list[dict]:
        if user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Audit logs are available to admin users only.")
        return _jsonable(repository.list_audit_logs_for_user(user))

    return app


app = create_app()
