from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from app.schemas.clinical import (
    AiReview,
    AudioFileMetadata,
    ChildCase,
    FeatureSet,
    MLResult,
    PrivacyOperation,
    ProcessingJob,
    Report,
    ReviewStatus,
    TherapyGoal,
    TherapySession,
    Transcript,
)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


class MockRepository:
    """In-memory repository for local demo and contract tests."""

    def __init__(self) -> None:
        self.cases: dict[str, ChildCase] = {}
        self.sessions: dict[str, TherapySession] = {}
        self.transcripts: dict[str, Transcript] = {}
        self.features: dict[str, FeatureSet] = {}
        self.ml_results: dict[str, MLResult] = {}
        self.ai_reviews: dict[str, AiReview] = {}
        self.reports: dict[str, Report] = {}
        self.therapy_goals: dict[str, TherapyGoal] = {}
        self.audio_files: dict[str, AudioFileMetadata] = {}
        self.jobs: dict[str, ProcessingJob] = {}
        self.privacy_operations: dict[str, PrivacyOperation] = {}
        self.audit_log: list[dict] = []
        self.seed()

    def seed(self) -> None:
        if self.cases:
            return
        case = ChildCase(
            case_id="case_demo_001",
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

    def clone(self, value):
        return deepcopy(value)

    def add_audit(self, action: str, target_id: str, message: str) -> None:
        self.audit_log.append(
            {
                "audit_id": new_id("audit"),
                "action": action,
                "target_id": target_id,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def snapshot(self) -> dict:
        return {
            "cases": {key: value.model_dump(mode="json") for key, value in self.cases.items()},
            "sessions": {key: value.model_dump(mode="json") for key, value in self.sessions.items()},
            "transcripts": {key: value.model_dump(mode="json") for key, value in self.transcripts.items()},
            "features": {key: value.model_dump(mode="json") for key, value in self.features.items()},
            "ml_results": {key: value.model_dump(mode="json") for key, value in self.ml_results.items()},
            "ai_reviews": {key: value.model_dump(mode="json") for key, value in self.ai_reviews.items()},
            "reports": {key: value.model_dump(mode="json") for key, value in self.reports.items()},
            "therapy_goals": {key: value.model_dump(mode="json") for key, value in self.therapy_goals.items()},
            "audio_files": {key: value.model_dump(mode="json") for key, value in self.audio_files.items()},
            "jobs": {key: value.model_dump(mode="json") for key, value in self.jobs.items()},
            "privacy_operations": {key: value.model_dump(mode="json") for key, value in self.privacy_operations.items()},
            "audit_log": self.audit_log,
        }


class JsonFileRepository(MockRepository):
    """Durable local demo repository stored as JSON outside browser storage."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
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
        self.features = {key: FeatureSet.model_validate(value) for key, value in data.get("features", {}).items()}
        self.ml_results = {key: MLResult.model_validate(value) for key, value in data.get("ml_results", {}).items()}
        self.ai_reviews = {key: AiReview.model_validate(value) for key, value in data.get("ai_reviews", {}).items()}
        self.reports = {key: Report.model_validate(value) for key, value in data.get("reports", {}).items()}
        self.therapy_goals = {key: TherapyGoal.model_validate(value) for key, value in data.get("therapy_goals", {}).items()}
        self.audio_files = {key: AudioFileMetadata.model_validate(value) for key, value in data.get("audio_files", {}).items()}
        self.jobs = {key: ProcessingJob.model_validate(value) for key, value in data.get("jobs", {}).items()}
        self.privacy_operations = {key: PrivacyOperation.model_validate(value) for key, value in data.get("privacy_operations", {}).items()}
        self.audit_log = list(data.get("audit_log", []))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.snapshot(), indent=2), encoding="utf-8")

    def add_audit(self, action: str, target_id: str, message: str) -> None:
        super().add_audit(action, target_id, message)
        self.save()
