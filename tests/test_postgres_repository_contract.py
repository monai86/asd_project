"""Contract tests for PostgresSupabaseRepository.

Uses a mock Supabase client to verify repository methods return correct types,
enforce ownership checks, and handle consent gates — no live DB required.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.clinical_workflow.models import (
    User,
    ChildCase,
    Session,
    ConsentRecord,
    Transcript,
    TranscriptLine,
    ExtractedFeatures,
    AIScreeningOutput,
    TherapyGoal,
    TherapistNote,
    Report,
    ClinicalSignoff,
    AuditLog,
    AudioFile,
    ProcessingJob,
)
from src.clinical_workflow.postgres_supabase_repository import PostgresSupabaseRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_mock_response(data=None):
    resp = MagicMock()
    resp.data = data or []
    return resp


class FakeTable:
    """Chainable mock for supabase .table().select().eq()... pattern."""

    def __init__(self, data=None):
        self._data = data or []

    def select(self, *args, **kwargs):
        return self

    def insert(self, row):
        self._data = [row]
        return self

    def update(self, payload):
        if self._data:
            self._data = [{**self._data[0], **payload}]
        else:
            self._data = [payload]
        return self

    def delete(self):
        self._data = []
        return self

    def eq(self, col, val):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        return _make_mock_response(self._data)


class FakeSupabaseClient:
    """Minimal mock of supabase.Client with table(), auth, and storage."""

    def __init__(self, table_data=None):
        self._table_data = table_data or {}
        self.auth = MagicMock()
        self.storage = MagicMock()

    def table(self, name):
        data = self._table_data.get(name, [])
        return FakeTable(data)

    def from_(self, *args, **kwargs):
        return FakeTable()


MOCK_USER = User(
    user_id="user-001",
    name="Dr. Test",
    email="test@clinic.local",
    role="therapist",
    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
)

MOCK_ADMIN = User(
    user_id="admin-001",
    name="Admin",
    email="admin@clinic.local",
    role="admin",
    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
)


def _make_repo(table_data=None):
    client = FakeSupabaseClient(table_data or {})
    return PostgresSupabaseRepository(client=client)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TestAuthentication:
    def test_get_user_returns_none_for_missing_user(self):
        repo = _make_repo()
        assert repo.get_user("nonexistent") is None

    def test_get_user_returns_user_when_found(self):
        repo = _make_repo({"users": [{
            "user_id": "user-001",
            "name": "Dr. Test",
            "email": "test@clinic.local",
            "role": "therapist",
            "created_at": "2024-01-01T00:00:00+00:00",
        }]})
        user = repo.get_user("user-001")
        assert user is not None
        assert isinstance(user, User)
        assert user.user_id == "user-001"
        assert user.role == "therapist"


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

class TestCases:
    def test_create_case_returns_child_case(self):
        repo = _make_repo()
        case = repo.create_case(
            owner_user_id="user-001",
            anonymized_child_code="CHI001",
            age_months=36,
            sex="male",
            primary_concerns="Language delay",
            consent_status="not_recorded",
            anonymization_status="anonymized",
        )
        assert isinstance(case, ChildCase)
        assert case.anonymized_child_code == "CHI001"
        assert case.age_months == 36

    def test_create_case_rejects_spaces_in_child_code(self):
        repo = _make_repo()
        with pytest.raises(ValueError, match="must not contain spaces"):
            repo.create_case(
                owner_user_id="user-001",
                anonymized_child_code="John Doe",
                age_months=36,
                sex="male",
                primary_concerns="Test",
                consent_status="not_recorded",
                anonymization_status="anonymized",
            )

    def test_list_cases_returns_list(self):
        repo = _make_repo({"child_cases": [{
            "case_id": "case-001",
            "owner_user_id": "user-001",
            "anonymized_child_code": "CHI001",
            "age_months": 36,
            "sex": "male",
            "primary_concerns": "Test",
        }]})
        cases = repo.list_cases_for_user(MOCK_USER)
        assert isinstance(cases, list)
        assert all(isinstance(c, ChildCase) for c in cases)

    def test_list_cases_filters_by_ownership(self):
        other_user = User(
            user_id="user-other",
            name="Other",
            email="other@test.local",
            role="therapist",
        )
        repo = _make_repo({"child_cases": [{
            "case_id": "case-001",
            "owner_user_id": "user-001",
        }]})
        cases = repo.list_cases_for_user(other_user)
        assert len(cases) == 0

    def test_admin_can_see_all_cases(self):
        repo = _make_repo({"child_cases": [{
            "case_id": "case-001",
            "owner_user_id": "user-001",
        }]})
        cases = repo.list_cases_for_user(MOCK_ADMIN)
        assert len(cases) == 1


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

class TestSessions:
    def test_create_session_returns_session(self):
        repo = _make_repo()
        session = repo.create_session(
            case_id="case-001",
            user=MOCK_USER,
            session_date="2024-06-01",
            session_type="therapy_session",
        )
        assert isinstance(session, Session)
        assert session.case_id == "case-001"
        assert session.processing_status == "not_started"

    def test_list_sessions_returns_list(self):
        repo = _make_repo({"sessions": [{
            "session_id": "sess-001",
            "case_id": "case-001",
            "owner_user_id": "user-001",
            "session_date": "2024-06-01",
            "session_type": "therapy_session",
        }]})
        sessions = repo.list_sessions_for_user(MOCK_USER)
        assert isinstance(sessions, list)
        assert len(sessions) == 1


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------

class TestConsent:
    def test_record_consent_returns_consent_record(self):
        repo = _make_repo()
        consent = repo.record_consent(
            case_id="case-001",
            user=MOCK_USER,
            audio_permission=True,
            transcript_permission=True,
        )
        assert isinstance(consent, ConsentRecord)
        assert consent.audio_permission is True

    def test_has_active_consent_returns_false_when_none(self):
        repo = _make_repo({"consent_records": []})
        assert repo.has_active_audio_consent("case-001") is False

    def test_has_active_consent_returns_true_with_valid_record(self):
        repo = _make_repo({"consent_records": [{
            "consent_id": "consent-001",
            "case_id": "case-001",
            "owner_user_id": "user-001",
            "audio_permission": True,
            "withdrawn_at": None,
            "expires_at": None,
        }]})
        assert repo.has_active_audio_consent("case-001") is True

    def test_has_active_consent_excludes_withdrawn(self):
        repo = _make_repo({"consent_records": [{
            "consent_id": "consent-001",
            "case_id": "case-001",
            "owner_user_id": "user-001",
            "audio_permission": True,
            "withdrawn_at": "2024-01-01T00:00:00+00:00",
            "expires_at": None,
        }]})
        assert repo.has_active_audio_consent("case-001") is False


# ---------------------------------------------------------------------------
# Secure Upload Intent
# ---------------------------------------------------------------------------

class TestSecureUploadIntent:
    def test_rejects_without_consent(self):
        repo = _make_repo({"consent_records": []})
        with pytest.raises(PermissionError, match="consent"):
            repo.create_secure_audio_upload_intent(
                case_id="case-001",
                session_id="sess-001",
                user=MOCK_USER,
                original_filename="test.wav",
                file_size=1024,
            )

    def test_returns_upload_dict_with_consent(self):
        repo = _make_repo({
            "consent_records": [{
                "consent_id": "c-001",
                "case_id": "case-001",
                "owner_user_id": "user-001",
                "audio_permission": True,
                "withdrawn_at": None,
                "expires_at": None,
            }],
        })
        result = repo.create_secure_audio_upload_intent(
            case_id="case-001",
            session_id="sess-001",
            user=MOCK_USER,
            original_filename="test.wav",
            file_size=1024,
        )
        assert isinstance(result, dict)
        assert "audio_file" in result
        assert "upload" in result
        assert "signed_upload_url" in result["upload"] or "url" in result["upload"]


# ---------------------------------------------------------------------------
# Transcripts
# ---------------------------------------------------------------------------

class TestTranscripts:
    def test_list_transcripts_returns_list(self):
        repo = _make_repo({"transcripts": [{
            "transcript_id": "tx-001",
            "session_id": "sess-001",
            "owner_user_id": "user-001",
        }]})
        transcripts = repo.list_transcripts_for_user(MOCK_USER)
        assert isinstance(transcripts, list)
        assert all(isinstance(t, Transcript) for t in transcripts)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class TestDashboard:
    def test_dashboard_summary_returns_dict(self):
        repo = _make_repo({
            "child_cases": [{"case_id": "c-1", "owner_user_id": "user-001"}],
            "sessions": [{"session_id": "s-1", "case_id": "c-1", "owner_user_id": "user-001",
                         "session_date": "2024-01-01", "therapist_review_status": "not_started",
                         "processing_status": "not_started"}],
            "transcripts": [],
        })
        summary = repo.dashboard_summary(MOCK_USER)
        assert isinstance(summary, dict)
        assert "total_cases" in summary
        assert "total_sessions" in summary
        assert summary["total_cases"] == 1


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

class TestAuditLogs:
    def test_audit_logs_requires_admin(self):
        repo = _make_repo()
        with pytest.raises(PermissionError, match="admin"):
            repo.list_audit_logs_for_user(MOCK_USER)

    def test_audit_logs_returns_list_for_admin(self):
        repo = _make_repo({"audit_logs": [{
            "audit_id": "aud-001",
            "event_type": "test",
            "actor_user_id": "user-001",
            "target_type": "session",
            "target_id": "sess-001",
            "message": "Test event",
        }]})
        logs = repo.list_audit_logs_for_user(MOCK_ADMIN)
        assert isinstance(logs, list)
        assert all(isinstance(l, AuditLog) for l in logs)


# ---------------------------------------------------------------------------
# Signoffs
# ---------------------------------------------------------------------------

class TestSignoffs:
    def test_create_signoff_returns_clinical_signoff(self):
        repo = _make_repo({"sessions": [{
            "session_id": "sess-001",
            "case_id": "case-001",
            "owner_user_id": "user-001",
        }]})
        signoff = repo.create_clinical_signoff(
            target_type="transcript",
            target_id="tx-001",
            user=MOCK_USER,
            session_id="sess-001",
            notes="Verified",
        )
        assert isinstance(signoff, ClinicalSignoff)
        assert signoff.target_type == "transcript"


# ---------------------------------------------------------------------------
# REPOSITORY_MODE switching
# ---------------------------------------------------------------------------

class TestRepositoryModeSwitch:
    def test_default_mode_is_mock(self):
        from src.therapist_backend.app import _build_default_repository
        from src.clinical_workflow.mock_repository import MockClinicalRepository
        repo = _build_default_repository()
        assert isinstance(repo, MockClinicalRepository)

    def test_postgres_mode_requires_env_vars(self):
        from src.therapist_backend.app import _build_default_repository
        import os
        with patch.dict(os.environ, {"REPOSITORY_MODE": "postgres"}, clear=False):
            # Without SUPABASE_URL, should raise ValueError
            with pytest.raises((ValueError, ImportError)):
                _build_default_repository()
