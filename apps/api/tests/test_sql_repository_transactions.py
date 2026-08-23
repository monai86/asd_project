from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest

from app.repositories.base import (
    CaseVersionConflictError,
    ReportVersionConflictError,
    SessionVersionConflictError,
    TranscriptVersionConflictError,
)
from app.schemas.clinical import (
    AiReview,
    AttestationRequest,
    AiReviewPatch,
    ChildCaseCreate,
    ChildCaseUpdate,
    FeatureExtractionRequest,
    FeatureSet,
    FeatureValue,
    MLReviewRequest,
    MLResult,
    CareTeamAssignmentCreate,
    OrganizationInvitationAccept,
    OrganizationInvitationCreate,
    OrganizationMembershipCreate,
    PrivacyOperationCreate,
    PrivacyOperationPatch,
    QaStatus,
    ReviewStatus,
    ReviewCuePatch,
    Report,
    ReportGenerationInput,
    ReportProviderAvailability,
    ReportProviderResult,
    ReportPatch,
    TherapyGoalCreate,
    TherapyGoalUpdate,
    TherapySessionCreate,
    TherapySessionUpdate,
    Transcript,
    TranscriptPatch,
    utc_now,
)


def _attach_completed_feature_set(repo, session_id: str, transcript: Transcript, feature_set_id: str) -> None:
    repo.create_feature_set(
        FeatureSet(
            feature_set_id=feature_set_id,
            session_id=session_id,
            transcript_id=transcript.transcript_id,
            transcript_version=transcript.version,
            therapist_attested=True,
            features=[FeatureValue(name="mean_length_of_utterance_words", value=1.0, unit="words")],
        ),
        actor_id="user_tx",
        audit_action="features.extract",
        audit_message="Synthetic feature fixture created for transaction test.",
    )


def test_case_update_is_record_scoped_and_does_not_call_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import ChildCaseRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'transactions.db'}")
    first = repo.create_case(ChildCaseCreate(child_code="C-TX-001", age_months=48), actor_id="user_tx")
    second = repo.create_case(ChildCaseCreate(child_code="C-TX-002", age_months=60), actor_id="user_tx")

    def fail_snapshot_save() -> None:
        raise AssertionError("transactional case updates must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    updated = repo.update_case(
        first.case_id,
        ChildCaseUpdate(notes="Scoped update only."),
        expected_version=first.version,
        actor_id="user_tx",
    )

    assert updated.version == first.version + 1
    with repo.SessionLocal() as db:
        rows = {row.case_id: row for row in db.query(ChildCaseRecord).all()}

    assert rows[first.case_id].notes == "Scoped update only."
    assert rows[first.case_id].version == first.version + 1
    assert rows[second.case_id].child_code == "C-TX-002"
    assert rows[second.case_id].version == second.version


def test_case_update_expected_version_conflict_rolls_back_mutation_and_audit(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, ChildCaseRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'conflict.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-003", age_months=54), actor_id="user_tx")

    with pytest.raises(CaseVersionConflictError):
        repo.update_case(
            case.case_id,
            ChildCaseUpdate(notes="This stale update must not persist."),
            expected_version=case.version + 1,
            actor_id="user_tx",
        )

    with repo.SessionLocal() as db:
        row = db.get(ChildCaseRecord, case.case_id)
        audit_actions = [item.action for item in db.query(AuditLogRecord).all()]

    assert row is not None
    assert row.notes == ""
    assert row.version == case.version
    assert "case.update" not in audit_actions


def test_case_update_writes_audit_event_in_same_transaction(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, ChildCaseRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'audit.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-004", age_months=50), actor_id="user_tx")

    updated = repo.update_case(
        case.case_id,
        ChildCaseUpdate(language="English/Thai"),
        expected_version=case.version,
        actor_id="user_tx",
    )

    with repo.SessionLocal() as db:
        row = db.get(ChildCaseRecord, case.case_id)
        audit = db.query(AuditLogRecord).filter_by(action="case.update", target_id=case.case_id).one()

    assert row is not None
    assert row.language == "English/Thai"
    assert audit.actor_id == "user_tx"
    assert audit.correlation_id == f"case-update-{updated.version}"


def test_session_create_updates_case_summary_and_audit_in_same_transaction(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, ChildCaseRecord, SessionRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'session-create.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-005", age_months=52), actor_id="user_tx")

    def fail_snapshot_save() -> None:
        raise AssertionError("transactional session creation must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )

    with repo.SessionLocal() as db:
        case_row = db.get(ChildCaseRecord, case.case_id)
        session_row = db.get(SessionRecord, session.session_id)
        audit = db.query(AuditLogRecord).filter_by(action="session.create", target_id=session.session_id).one()

    assert case_row is not None
    assert case_row.latest_session_date == "2026-06-25"
    assert case_row.latest_session_status == ReviewStatus.draft.value
    assert session_row is not None
    assert session_row.case_id == case.case_id
    assert session_row.version == 1
    assert audit.actor_id == "user_tx"


def test_session_update_expected_version_conflict_rolls_back_mutation_and_audit(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, SessionRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'session-conflict.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-006", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )

    with pytest.raises(SessionVersionConflictError):
        repo.update_session(
            session.session_id,
            TherapySessionUpdate(notes="Stale session update must not persist."),
            expected_version=session.version + 1,
            actor_id="user_tx",
        )

    with repo.SessionLocal() as db:
        row = db.get(SessionRecord, session.session_id)
        audit_actions = [item.action for item in db.query(AuditLogRecord).all()]

    assert row is not None
    assert row.notes == ""
    assert row.version == session.version
    assert "session.patch" not in audit_actions


def test_session_update_is_record_scoped_and_writes_audit(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, SessionRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'session-update.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-007", age_months=52), actor_id="user_tx")
    first = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    second = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-26", session_type="therapy_session"),
        actor_id="user_tx",
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("transactional session updates must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    updated = repo.update_session(
        first.session_id,
        TherapySessionUpdate(notes="Scoped session update.", status=ReviewStatus.needs_review),
        expected_version=first.version,
        actor_id="user_tx",
    )

    with repo.SessionLocal() as db:
        rows = {row.session_id: row for row in db.query(SessionRecord).all()}
        audit = db.query(AuditLogRecord).filter_by(action="session.patch", target_id=first.session_id).one()

    assert updated.version == first.version + 1
    assert rows[first.session_id].notes == "Scoped session update."
    assert rows[first.session_id].status == ReviewStatus.needs_review.value
    assert rows[second.session_id].notes == ""
    assert rows[second.session_id].version == second.version
    assert audit.correlation_id == f"session-update-{updated.version}"


def test_transcript_create_links_session_and_audit_in_same_transaction(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, SessionRecord, TranscriptRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'transcript-create.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-008", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    transcript = Transcript(
        transcript_id="tr_tx_001",
        session_id=session.session_id,
        case_id=case.case_id,
        source="manual_entry",
        raw_text="@Begin\n*CHI: hello .\n@End",
        review_status=ReviewStatus.needs_review,
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("transactional transcript creation must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    created = repo.create_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="user_tx",
        audit_action="transcript.manual",
        audit_message="Manual transcript converted to reviewable CHAT draft.",
    )

    with repo.SessionLocal() as db:
        session_row = db.get(SessionRecord, session.session_id)
        transcript_row = db.get(TranscriptRecord, transcript.transcript_id)
        audit = db.query(AuditLogRecord).filter_by(action="transcript.manual", target_id=transcript.transcript_id).one()

    assert created.transcript_id == transcript.transcript_id
    assert transcript_row is not None
    assert transcript_row.version == 1
    assert session_row is not None
    assert session_row.transcript_id == transcript.transcript_id
    assert session_row.status == ReviewStatus.needs_review.value
    assert session_row.feature_set_id is None
    assert audit.actor_id == "user_tx"


def test_transcript_update_is_record_scoped_and_clears_session_outputs(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, SessionRecord, TranscriptRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'transcript-update.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-009", age_months=52), actor_id="user_tx")
    first_session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    second_session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-26", session_type="therapy_session"),
        actor_id="user_tx",
    )
    first = repo.create_transcript(
        Transcript(
            transcript_id="tr_tx_002",
            session_id=first_session.session_id,
            case_id=case.case_id,
            source="manual_entry",
            raw_text="@Begin\n*CHI: hello .\n@End",
        ),
        session_status=ReviewStatus.needs_review,
        actor_id="user_tx",
        audit_action="transcript.manual",
        audit_message="Manual transcript converted to reviewable CHAT draft.",
    )
    second = repo.create_transcript(
        Transcript(
            transcript_id="tr_tx_003",
            session_id=second_session.session_id,
            case_id=case.case_id,
            source="manual_entry",
            raw_text="@Begin\n*CHI: unchanged .\n@End",
        ),
        session_status=ReviewStatus.needs_review,
        actor_id="user_tx",
        audit_action="transcript.manual",
        audit_message="Manual transcript converted to reviewable CHAT draft.",
    )
    repo.sessions[first_session.session_id] = repo.sessions[first_session.session_id].model_copy(
        update={"feature_set_id": "feature_stale", "ml_result_id": "ml_stale", "ai_review_id": "ai_stale", "report_id": "report_stale"}
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("transactional transcript updates must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    updated = first.model_copy(
        update={
            "raw_text": "@Begin\n*CHI: edited .\n@End",
            "version": first.version + 1,
            "review_status": ReviewStatus.needs_review,
        }
    )
    saved = repo.update_transcript(
        updated,
        session_status=ReviewStatus.needs_review,
        expected_version=first.version,
        actor_id="user_tx",
        audit_action="transcript.patch",
        audit_message="Transcript edited; prior attestation and outputs are stale.",
    )

    with repo.SessionLocal() as db:
        rows = {row.transcript_id: row for row in db.query(TranscriptRecord).all()}
        session_row = db.get(SessionRecord, first_session.session_id)
        audit = db.query(AuditLogRecord).filter_by(action="transcript.patch", target_id=first.transcript_id).one()

    assert saved.version == first.version + 1
    assert rows[first.transcript_id].raw_text == "@Begin\n*CHI: edited .\n@End"
    assert rows[first.transcript_id].version == first.version + 1
    assert rows[second.transcript_id].raw_text == second.raw_text
    assert session_row is not None
    assert session_row.status == ReviewStatus.needs_review.value
    assert session_row.feature_set_id is None
    assert session_row.ml_result_id is None
    assert session_row.ai_review_id is None
    assert session_row.report_id is None
    assert audit.correlation_id == f"transcript-update-{saved.version}"


def test_transcript_update_version_conflict_rolls_back_mutation_and_audit(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, TranscriptRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'transcript-conflict.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-010", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    transcript = repo.create_transcript(
        Transcript(
            transcript_id="tr_tx_004",
            session_id=session.session_id,
            case_id=case.case_id,
            source="manual_entry",
            raw_text="@Begin\n*CHI: hello .\n@End",
        ),
        session_status=ReviewStatus.needs_review,
        actor_id="user_tx",
        audit_action="transcript.manual",
        audit_message="Manual transcript converted to reviewable CHAT draft.",
    )
    stale_update = transcript.model_copy(update={"raw_text": "stale edit", "version": transcript.version + 1})

    with pytest.raises(TranscriptVersionConflictError):
        repo.update_transcript(
            stale_update,
            session_status=ReviewStatus.needs_review,
            expected_version=transcript.version + 1,
            actor_id="user_tx",
            audit_action="transcript.patch",
            audit_message="Transcript edited; prior attestation and outputs are stale.",
        )

    with repo.SessionLocal() as db:
        row = db.get(TranscriptRecord, transcript.transcript_id)
        audit_actions = [item.action for item in db.query(AuditLogRecord).all()]

    assert row is not None
    assert row.raw_text == transcript.raw_text
    assert row.version == transcript.version
    assert "transcript.patch" not in audit_actions


def test_report_create_links_session_case_and_audit_in_same_transaction(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, ChildCaseRecord, ReportRecord, SessionRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'report-create.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-011", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    report = Report(
        report_id="rep_tx_001",
        session_id=session.session_id,
        case_id=case.case_id,
        report_type="Session Review Report",
        title="Session Review Report",
        markdown="# Session Review Report\n",
        html="<h1>Session Review Report</h1>",
        status=ReviewStatus.draft,
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("transactional report creation must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    created = repo.create_report(
        report,
        actor_id="user_tx",
        audit_action="report.draft",
        audit_message="Report draft generated successfully using provider 'template'.",
    )

    with repo.SessionLocal() as db:
        report_row = db.get(ReportRecord, report.report_id)
        session_row = db.get(SessionRecord, session.session_id)
        case_row = db.get(ChildCaseRecord, case.case_id)
        audit = db.query(AuditLogRecord).filter_by(action="report.draft", target_id=report.report_id).one()

    assert created.report_id == report.report_id
    assert report_row is not None
    assert report_row.status == ReviewStatus.draft.value
    assert session_row is not None
    assert session_row.report_id == report.report_id
    assert case_row is not None
    assert case_row.latest_report_status == ReviewStatus.draft.value
    assert audit.actor_id == "user_tx"


def test_report_update_is_record_scoped_and_writes_audit(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, ChildCaseRecord, ReportRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'report-update.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-012", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    first = repo.create_report(
        Report(
            report_id="rep_tx_002",
            session_id=session.session_id,
            case_id=case.case_id,
            report_type="Session Review Report",
            title="Original",
            markdown="# Original\n",
            html="<h1>Original</h1>",
        ),
        actor_id="user_tx",
        audit_action="report.draft",
        audit_message="Report draft generated successfully using provider 'template'.",
    )
    second = repo.create_report(
        Report(
            report_id="rep_tx_003",
            session_id=session.session_id,
            case_id=case.case_id,
            report_type="Session Review Report",
            title="Unchanged",
            markdown="# Unchanged\n",
            html="<h1>Unchanged</h1>",
        ),
        actor_id="user_tx",
        audit_action="report.draft",
        audit_message="Report draft generated successfully using provider 'template'.",
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("transactional report updates must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    updated = first.model_copy(
        update={
            "title": "Updated",
            "markdown": "# Updated\n",
            "html": "<h1>Updated</h1>",
            "version": first.version + 1,
        }
    )
    saved = repo.update_report(
        updated,
        expected_version=first.version,
        actor_id="user_tx",
        audit_action="report.patch",
        audit_message="Report draft edited.",
    )

    with repo.SessionLocal() as db:
        rows = {row.report_id: row for row in db.query(ReportRecord).all()}
        case_row = db.get(ChildCaseRecord, case.case_id)
        audit = db.query(AuditLogRecord).filter_by(action="report.patch", target_id=first.report_id).one()

    assert saved.version == first.version + 1
    assert rows[first.report_id].title == "Updated"
    assert rows[first.report_id].version == first.version + 1
    assert rows[second.report_id].title == "Unchanged"
    assert case_row is not None
    assert case_row.latest_report_status == ReviewStatus.draft.value
    assert audit.correlation_id == f"report-update-{saved.version}"


def test_report_update_version_conflict_rolls_back_mutation_and_audit(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, ReportRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'report-conflict.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-013", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    report = repo.create_report(
        Report(
            report_id="rep_tx_004",
            session_id=session.session_id,
            case_id=case.case_id,
            report_type="Session Review Report",
            title="Original",
            markdown="# Original\n",
            html="<h1>Original</h1>",
        ),
        actor_id="user_tx",
        audit_action="report.draft",
        audit_message="Report draft generated successfully using provider 'template'.",
    )
    stale_update = report.model_copy(update={"title": "Stale", "version": report.version + 1})

    with pytest.raises(ReportVersionConflictError):
        repo.update_report(
            stale_update,
            expected_version=report.version + 1,
            actor_id="user_tx",
            audit_action="report.patch",
            audit_message="Report draft edited.",
        )

    with repo.SessionLocal() as db:
        row = db.get(ReportRecord, report.report_id)
        audit_actions = [item.action for item in db.query(AuditLogRecord).all()]

    assert row is not None
    assert row.title == "Original"
    assert row.version == report.version
    assert "report.patch" not in audit_actions


def test_report_signoff_persists_snapshot_case_status_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, ChildCaseRecord, ReportRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.report_service import sign_off_report

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'report-signoff.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-014", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    transcript = repo.create_transcript(
        Transcript(
            transcript_id="tr_tx_005",
            session_id=session.session_id,
            case_id=case.case_id,
            source="manual_entry",
            raw_text="@Begin\n*CHI: reviewed placeholder .\n@End",
            therapist_attested=True,
            review_status=ReviewStatus.attested,
        ),
        session_status=ReviewStatus.attested,
        actor_id="user_tx",
        audit_action="transcript.attest",
        audit_message="Transcript attested.",
    )
    session = repo.sessions[session.session_id].model_copy(update={"transcript_id": transcript.transcript_id})
    _attach_completed_feature_set(repo, session.session_id, transcript, "feat_tx_005")
    report = repo.create_report(
        Report(
            report_id="rep_tx_005",
            session_id=session.session_id,
            case_id=case.case_id,
            report_type="Session Review Report",
            title="Ready for Sign-off",
            markdown=(
                "# Ready for Sign-off\n\n"
                "Descriptive speech patterns observed. "
                "It is for clinical decision-support only and is not diagnostic. "
                "Therapist review required before clinical use.\n\n"
                "## Limitations\nSome limitations."
            ),
            html="<h1>Ready for Sign-off</h1>",
        ),
        actor_id="user_tx",
        audit_action="report.draft",
        audit_message="Report draft generated successfully using provider 'template'.",
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("transactional report sign-off must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    competing = SqlAlchemyRepository(repo.database_url, create_schema=False)
    barrier = Barrier(2)
    repo_update = repo.update_report
    competing_update = competing.update_report

    def synchronized(update):
        def wrapped(*args, **kwargs):
            barrier.wait(timeout=10)
            return update(*args, **kwargs)
        return wrapped

    monkeypatch.setattr(repo, "update_report", synchronized(repo_update))
    monkeypatch.setattr(competing, "update_report", synchronized(competing_update))
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(sign_off_report, repo, report.report_id, "First Therapist"),
            executor.submit(sign_off_report, competing, report.report_id, "Second Therapist"),
        ]
        results = []
        errors = []
        for future in futures:
            try:
                results.append(future.result(timeout=10))
            except Exception as exc:
                errors.append(exc)

    assert len(results) == 1
    assert len(errors) == 1
    signed = results[0]

    with repo.SessionLocal() as db:
        report_row = db.get(ReportRecord, report.report_id)
        case_row = db.get(ChildCaseRecord, case.case_id)
        audit = db.query(AuditLogRecord).filter_by(action="report.sign_off", target_id=report.report_id).one()

    assert signed.status == ReviewStatus.signed_off
    assert signed.signed_snapshot_hash
    assert signed.version == report.version + 1
    assert signed.signed_snapshot_version == signed.version
    assert signed.signed_snapshot["report_version"] == signed.version
    assert report_row is not None
    assert report_row.status == ReviewStatus.signed_off.value
    assert report_row.signed_snapshot_hash == signed.signed_snapshot_hash
    assert case_row is not None
    assert case_row.latest_report_status == ReviewStatus.signed_off.value
    assert audit.actor_id == "system"
    assert audit.correlation_id == f"report-update-{signed.version}"

    immutable_hash = signed.signed_snapshot_hash
    with pytest.raises((ValueError, RuntimeError), match="read-only|immutable|Finalized"):
        sign_off_report(repo, report.report_id, signed_by="Second Therapist")
    reopened = SqlAlchemyRepository(repo.database_url, create_schema=False)
    assert reopened.get_report(report.report_id).signed_snapshot_hash == immutable_hash
    assert sum(
        event["action"] == "report.sign_off" and event["target_id"] == report.report_id
        for event in reopened.audit_log
    ) == 1


def test_report_revision_creates_new_draft_and_preserves_signed_snapshot_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, ChildCaseRecord, ReportRecord, SessionRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.report_service import revise_finalized_report, sign_off_report

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'report-revision.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-015", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    transcript = repo.create_transcript(
        Transcript(
            transcript_id="tr_tx_006",
            session_id=session.session_id,
            case_id=case.case_id,
            source="manual_entry",
            raw_text="@Begin\n*CHI: reviewed placeholder .\n@End",
            therapist_attested=True,
            review_status=ReviewStatus.attested,
        ),
        session_status=ReviewStatus.attested,
        actor_id="user_tx",
        audit_action="transcript.attest",
        audit_message="Transcript attested.",
    )
    session = repo.sessions[session.session_id].model_copy(update={"transcript_id": transcript.transcript_id})
    _attach_completed_feature_set(repo, session.session_id, transcript, "feat_tx_006")
    report = repo.create_report(
        Report(
            report_id="rep_tx_006",
            session_id=session.session_id,
            case_id=case.case_id,
            report_type="Session Review Report",
            title="Original Signed",
            markdown=(
                "# Original Signed\n\n"
                "Descriptive speech patterns observed. "
                "It is for clinical decision-support only and is not diagnostic. "
                "Therapist review required before clinical use.\n\n"
                "## Limitations\nSome limitations."
            ),
            html="<h1>Original Signed</h1>",
        ),
        actor_id="user_tx",
        audit_action="report.draft",
        audit_message="Report draft generated successfully using provider 'template'.",
    )
    signed = sign_off_report(repo, report.report_id, signed_by="Demo Therapist")

    def fail_snapshot_save() -> None:
        raise AssertionError("transactional report revision must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    revision = revise_finalized_report(
        repo,
        signed.report_id,
        ReportPatch(
            title="Revision Draft",
            markdown=(
                "# Revision Draft\n\n"
                "Descriptive speech patterns observed. "
                "It is for clinical decision-support only and is not diagnostic. "
                "Therapist review required before clinical use.\n\n"
                "## Limitations\nUpdated limitations."
            ),
        ),
    )

    with repo.SessionLocal() as db:
        original_row = db.get(ReportRecord, signed.report_id)
        revision_row = db.get(ReportRecord, revision.report_id)
        session_row = db.get(SessionRecord, session.session_id)
        case_row = db.get(ChildCaseRecord, case.case_id)
        audit = db.query(AuditLogRecord).filter_by(action="report.revision", target_id=revision.report_id).one()

    assert revision.report_id != signed.report_id
    assert revision.status == ReviewStatus.draft
    assert revision.supersedes_report_id == signed.report_id
    assert revision.signed_snapshot_hash is None
    assert revision.revision_number == signed.revision_number + 1
    assert original_row is not None
    assert original_row.status == ReviewStatus.signed_off.value
    assert original_row.signed_snapshot_hash == signed.signed_snapshot_hash
    assert revision_row is not None
    assert revision_row.status == ReviewStatus.draft.value
    assert session_row is not None
    assert session_row.report_id == revision.report_id
    assert case_row is not None
    assert case_row.latest_report_status == ReviewStatus.draft.value
    assert audit.actor_id == "system"


def test_transcript_qa_updates_transcript_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, TranscriptRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.transcript_service import run_qa

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'transcript-qa.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-016", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    transcript = repo.create_transcript(
        Transcript(
            transcript_id="tr_tx_007",
            session_id=session.session_id,
            case_id=case.case_id,
            source="manual_entry",
            raw_text="@Begin\n@Participants: CHI Target_Child\n@Languages: eng\n*CHI: reviewed placeholder .\n@End",
        ),
        session_status=ReviewStatus.needs_review,
        actor_id="user_tx",
        audit_action="transcript.manual",
        audit_message="Manual transcript converted to reviewable CHAT draft.",
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("transcript QA must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    qa_report = run_qa(repo, transcript.transcript_id)

    with repo.SessionLocal() as db:
        row = db.get(TranscriptRecord, transcript.transcript_id)
        audit = db.query(AuditLogRecord).filter_by(action="transcript.qa", target_id=transcript.transcript_id).one()

    assert qa_report.transcript_id == transcript.transcript_id
    assert row is not None
    assert row.qa_status == qa_report.overall_status.value
    assert row.version == transcript.version
    assert audit.actor_id == "system"


def test_transcript_attestation_updates_transcript_session_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, SessionRecord, TranscriptRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.transcript_service import attest

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'transcript-attest.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-017", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    transcript = repo.create_transcript(
        Transcript(
            transcript_id="tr_tx_008",
            session_id=session.session_id,
            case_id=case.case_id,
            source="manual_entry",
            raw_text="@Begin\n@Participants: CHI Target_Child\n@Languages: eng\n*CHI: reviewed placeholder .\n@End",
            qa_status=QaStatus.pass_,
        ),
        session_status=ReviewStatus.needs_review,
        actor_id="user_tx",
        audit_action="transcript.manual",
        audit_message="Manual transcript converted to reviewable CHAT draft.",
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("transcript attestation must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    attested = attest(
        repo,
        transcript.transcript_id,
        AttestationRequest(attested_by="Demo Therapist"),
        actor_id="user_tx",
        attested_by="Demo Therapist",
    )

    with repo.SessionLocal() as db:
        transcript_row = db.get(TranscriptRecord, transcript.transcript_id)
        session_row = db.get(SessionRecord, session.session_id)
        audit = db.query(AuditLogRecord).filter_by(action="transcript.attest", target_id=transcript.transcript_id).one()

    assert attested.therapist_attested is True
    assert attested.review_status == ReviewStatus.attested
    assert transcript_row is not None
    assert transcript_row.therapist_attested is True
    assert session_row is not None
    assert session_row.status == ReviewStatus.attested.value
    assert audit.actor_id == "user_tx"


def test_transcript_edit_atomically_stales_sql_feature_and_report_provenance(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AiReviewRecord, AuditLogRecord, FeatureSetRecord, MLResultRecord, ReportRecord, SessionRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.transcript_service import patch_transcript

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'transcript-stale-provenance.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-STALE", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-07-15", session_type="therapy_session"),
        actor_id="user_tx",
    )
    transcript = repo.create_transcript(
        Transcript(
            transcript_id="tr_tx_stale",
            session_id=session.session_id,
            case_id=case.case_id,
            source="manual_entry",
            raw_text="@Begin\n*CHI:\treviewed words.\n@End",
            qa_status=QaStatus.pass_,
            therapist_attested=True,
            review_status=ReviewStatus.attested,
        ),
        session_status=ReviewStatus.attested,
        actor_id="user_tx",
        audit_action="transcript.attest",
        audit_message="Transcript attested.",
    )
    _attach_completed_feature_set(repo, session.session_id, transcript, "feat_tx_stale")
    ai_review = repo.create_ai_review(
        AiReview(
            ai_review_id="air_tx_stale",
            session_id=session.session_id,
            summary="Synthetic review summary.",
            key_findings=[],
            concerns=[],
            strengths=[],
            limitations=[],
            recommended_review_actions=[],
            confidence_level="limited",
            input_transcript_version=transcript.version,
            feature_set_id="feat_tx_stale",
        ),
        actor_id="user_tx",
        audit_action="ai_review.create",
        audit_message="Synthetic AI review created.",
    )
    ml_result = repo.create_ml_result(
        MLResult(
            result_id="mlr_tx_stale",
            transcript_id=transcript.transcript_id,
            session_id=session.session_id,
            feature_result_id="feat_tx_stale",
            provider_id="test-provider",
            provider_name="Test provider",
            provider_version="1",
            input_feature_schema_version="features-basic-v1",
            input_feature_hash="synthetic-hash",
            status="completed",
        ),
        actor_id="user_tx",
        audit_action="ml_review.create",
        audit_message="Synthetic ML review created.",
    )
    report = repo.create_report(
        Report(
            report_id="rep_tx_stale",
            session_id=session.session_id,
            case_id=case.case_id,
            report_type="Session Review Report",
            title="Draft report",
            markdown="# Draft",
            html="<h1>Draft</h1>",
        ),
        actor_id="user_tx",
        audit_action="report.draft",
        audit_message="Draft report generated.",
    )
    report_version = report.version
    report_updated_at = report.updated_at

    patch_transcript(
        repo,
        transcript.transcript_id,
        TranscriptPatch(raw_text="@Begin\n*CHI:\tedited words.\n@End"),
    )

    with repo.SessionLocal() as db:
        session_row = db.get(SessionRecord, session.session_id)
        feature_row = db.get(FeatureSetRecord, "feat_tx_stale")
        report_row = db.get(ReportRecord, report.report_id)
        ai_row = db.get(AiReviewRecord, ai_review.ai_review_id)
        ml_row = db.get(MLResultRecord, ml_result.result_id)
        invalidation_audit = db.query(AuditLogRecord).filter_by(
            action="workflow.invalidate_downstream",
            target_id=transcript.transcript_id,
        ).one()

    assert session_row.feature_set_id == "feat_tx_stale"
    assert session_row.report_id == report.report_id
    assert feature_row.review_status == ReviewStatus.stale.value
    assert report_row.status == ReviewStatus.stale.value
    assert ai_row.therapist_review_status == ReviewStatus.stale.value
    assert ai_row.payload["therapist_review_status"] == ReviewStatus.stale.value
    assert ml_row.payload["is_current"] is False
    assert report_row.version == report_version + 1
    assert report_row.updated_at != report_updated_at.replace(tzinfo=None)
    assert invalidation_audit.message == "Derived workflow outputs marked stale after transcript change."


def test_failed_report_generation_persists_report_session_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, ReportRecord, SessionRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.providers.report_registry import report_provider_registry
    from app.services.report_service import draft_report

    class FailedTemplateProvider:
        provider_id = "template"
        provider_name = "FailedTemplateProvider"
        provider_version = "test"

        def check_availability(self) -> ReportProviderAvailability:
            return ReportProviderAvailability(provider_id=self.provider_id, available=True)

        def generate_report(self, input_data: ReportGenerationInput, config: dict) -> ReportProviderResult:
            return ReportProviderResult(
                status="failed",
                sections=[],
                provider_id=self.provider_id,
                provider_name=self.provider_name,
                provider_version=self.provider_version,
                error_message="Synthetic provider failure.",
            )

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'report-failed-generation.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-018", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    transcript = repo.create_transcript(
        Transcript(
            transcript_id="tr_tx_009",
            session_id=session.session_id,
            case_id=case.case_id,
            source="manual_entry",
            raw_text="@Begin\n*CHI: reviewed placeholder .\n@End",
            therapist_attested=True,
            review_status=ReviewStatus.attested,
        ),
        session_status=ReviewStatus.attested,
        actor_id="user_tx",
        audit_action="transcript.attest",
        audit_message="Transcript attested.",
    )
    _attach_completed_feature_set(repo, session.session_id, transcript, "feat_tx_009")

    def fail_snapshot_save() -> None:
        raise AssertionError("failed report generation must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)
    monkeypatch.setitem(report_provider_registry._providers, "template", FailedTemplateProvider())

    report = draft_report(repo, session.session_id, "Session Review Report")

    with repo.SessionLocal() as db:
        report_row = db.get(ReportRecord, report.report_id)
        session_row = db.get(SessionRecord, session.session_id)
        audit = db.query(AuditLogRecord).filter_by(action="report.failed", target_id=report.report_id).one()

    assert report.status == ReviewStatus.failed
    assert report_row is not None
    assert report_row.status == ReviewStatus.failed.value
    assert session_row is not None
    assert session_row.report_id == report.report_id
    assert audit.actor_id == "system"


def test_therapy_goal_create_persists_goal_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, TherapyGoalRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.therapy_goal_service import create_goal

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'goal-create.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-019", age_months=52), actor_id="user_tx")

    def fail_snapshot_save() -> None:
        raise AssertionError("therapy goal creation must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    goal = create_goal(
        repo,
        case.case_id,
        TherapyGoalCreate(title="Improve expressive language", target="Two-word requests", notes=""),
    )

    with repo.SessionLocal() as db:
        row = db.get(TherapyGoalRecord, goal.goal_id)
        audit = db.query(AuditLogRecord).filter_by(action="therapy_goal.create", target_id=goal.goal_id).one()

    assert row is not None
    assert row.case_id == case.case_id
    assert row.title == "Improve expressive language"
    assert audit.actor_id == "system"


def test_therapy_goal_update_is_record_scoped_and_writes_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, TherapyGoalRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.therapy_goal_service import create_goal, update_goal

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'goal-update.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-020", age_months=52), actor_id="user_tx")
    first = create_goal(
        repo,
        case.case_id,
        TherapyGoalCreate(title="Original goal", target="Original target"),
    )
    second = create_goal(
        repo,
        case.case_id,
        TherapyGoalCreate(title="Unchanged goal", target="Unchanged target"),
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("therapy goal updates must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    updated = update_goal(
        repo,
        first.goal_id,
        TherapyGoalUpdate(status="completed", notes="Reviewed and completed."),
    )

    with repo.SessionLocal() as db:
        rows = {row.goal_id: row for row in db.query(TherapyGoalRecord).all()}
        audit = db.query(AuditLogRecord).filter_by(action="therapy_goal.patch", target_id=first.goal_id).one()

    assert updated.status == "completed"
    assert rows[first.goal_id].status == "completed"
    assert rows[first.goal_id].notes == "Reviewed and completed."
    assert rows[second.goal_id].status == "active"
    assert rows[second.goal_id].notes == ""
    assert audit.actor_id == "system"


def test_privacy_operation_create_persists_request_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.core.security import CurrentUser
    from app.db.models import AuditLogRecord, PrivacyOperationRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.privacy_operation_service import create_privacy_operation

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'privacy-create.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-021", age_months=52), actor_id="user_tx")

    def fail_snapshot_save() -> None:
        raise AssertionError("privacy operation creation must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    operation = create_privacy_operation(
        repo,
        case.case_id,
        PrivacyOperationCreate(
            operation_type="case_export",
            reason="Guardian requested an export.",
            retention_days=30,
        ),
        CurrentUser(user_id="privacy_user", role="therapist"),
    )

    with repo.SessionLocal() as db:
        row = db.get(PrivacyOperationRecord, operation.privacy_operation_id)
        audit = db.query(AuditLogRecord).filter_by(
            action="privacy_operation.create",
            target_id=operation.privacy_operation_id,
        ).one()

    assert row is not None
    assert row.case_id == case.case_id
    assert row.requested_by == "privacy_user"
    assert row.retention_days == 30
    assert audit.actor_id == "privacy_user"


def test_privacy_operation_patch_persists_review_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.core.security import CurrentUser
    from app.db.models import AuditLogRecord, PrivacyOperationRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.privacy_operation_service import create_privacy_operation, patch_privacy_operation

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'privacy-patch.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-022", age_months=52), actor_id="user_tx")
    operation = create_privacy_operation(
        repo,
        case.case_id,
        PrivacyOperationCreate(
            operation_type="deletion_review",
            reason="Guardian requested deletion review.",
            retention_days=0,
        ),
        CurrentUser(user_id="privacy_user", role="therapist"),
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("privacy operation patch must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    patched = patch_privacy_operation(
        repo,
        operation.privacy_operation_id,
        PrivacyOperationPatch(status="completed", admin_note="Deletion review completed."),
    )

    with repo.SessionLocal() as db:
        row = db.get(PrivacyOperationRecord, operation.privacy_operation_id)
        audit = db.query(AuditLogRecord).filter_by(
            action="privacy_operation.patch",
            target_id=operation.privacy_operation_id,
        ).one()

    assert patched.status == "completed"
    assert patched.completed_at is not None
    assert row is not None
    assert row.status == "completed"
    assert row.admin_note == "Deletion review completed."
    assert row.preserve_evidence is True
    assert row.evidence_retained["audit_events"] >= 1
    assert audit.actor_id == "system"


def test_feature_extraction_persists_feature_session_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, FeatureSetRecord, SessionRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.feature_service import extract_features

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'feature-extract.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-023", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    transcript = repo.create_transcript(
        Transcript(
            transcript_id="tr_tx_010",
            session_id=session.session_id,
            case_id=case.case_id,
            source="manual_entry",
            raw_text="@Begin\n*CHI: reviewed placeholder .\n@End",
            qa_status=QaStatus.pass_,
            therapist_attested=True,
            review_status=ReviewStatus.attested,
        ),
        session_status=ReviewStatus.attested,
        actor_id="user_tx",
        audit_action="transcript.attest",
        audit_message="Transcript attested.",
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("feature extraction must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    feature_set = extract_features(repo, transcript.transcript_id, FeatureExtractionRequest())

    with repo.SessionLocal() as db:
        feature_row = db.get(FeatureSetRecord, feature_set.feature_set_id)
        session_row = db.get(SessionRecord, session.session_id)
        audit = db.query(AuditLogRecord).filter_by(
            action="features.extract",
            target_id=feature_set.feature_set_id,
        ).one()

    assert feature_row is not None
    assert feature_row.transcript_id == transcript.transcript_id
    assert feature_row.transcript_version == transcript.version
    assert session_row is not None
    assert session_row.feature_set_id == feature_set.feature_set_id
    assert session_row.ml_result_id is None
    assert audit.actor_id == "system"


def test_ai_review_create_persists_review_session_case_priority_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AiReviewRecord, AuditLogRecord, ChildCaseRecord, SessionRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.ai_review_service import create_ai_review

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'ai-review-create.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-024", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    repo.create_transcript(
        Transcript(
            transcript_id="tr_tx_011",
            session_id=session.session_id,
            case_id=case.case_id,
            source="manual_entry",
            raw_text="@Begin\n*CHI: reviewed placeholder .\n@End",
            qa_status=QaStatus.pass_,
            therapist_attested=True,
            review_status=ReviewStatus.attested,
        ),
        session_status=ReviewStatus.attested,
        actor_id="user_tx",
        audit_action="transcript.attest",
        audit_message="Transcript attested.",
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("AI review creation must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    review = create_ai_review(repo, session.session_id)

    with repo.SessionLocal() as db:
        review_row = db.get(AiReviewRecord, review.ai_review_id)
        session_row = db.get(SessionRecord, session.session_id)
        case_row = db.get(ChildCaseRecord, case.case_id)
        audit = db.query(AuditLogRecord).filter_by(action="ai_review.create", target_id=review.ai_review_id).one()

    assert review_row is not None
    assert review_row.session_id == session.session_id
    assert review_row.therapist_review_status == ReviewStatus.needs_review.value
    assert session_row is not None
    assert session_row.ai_review_id == review.ai_review_id
    assert case_row is not None
    assert case_row.review_priority == review.review_priority
    assert audit.actor_id == "system"


def test_ai_review_patch_persists_review_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AiReviewRecord, AuditLogRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.ai_review_service import create_ai_review, patch_ai_review

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'ai-review-patch.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-025", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    repo.create_transcript(
        Transcript(
            transcript_id="tr_tx_012",
            session_id=session.session_id,
            case_id=case.case_id,
            source="manual_entry",
            raw_text="@Begin\n*CHI: reviewed placeholder .\n@End",
            qa_status=QaStatus.pass_,
            therapist_attested=True,
            review_status=ReviewStatus.attested,
        ),
        session_status=ReviewStatus.attested,
        actor_id="user_tx",
        audit_action="transcript.attest",
        audit_message="Transcript attested.",
    )
    review = create_ai_review(repo, session.session_id)

    def fail_snapshot_save() -> None:
        raise AssertionError("AI review patch must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    patched = patch_ai_review(
        repo,
        review.ai_review_id,
        AiReviewPatch(therapist_review_status=ReviewStatus.withdrawn, rejected_reason="Therapist rejected support."),
    )

    with repo.SessionLocal() as db:
        row = db.get(AiReviewRecord, review.ai_review_id)
        audit = db.query(AuditLogRecord).filter_by(action="ai_review.patch", target_id=review.ai_review_id).one()

    assert patched.therapist_review_status == ReviewStatus.withdrawn
    assert row is not None
    assert row.therapist_review_status == ReviewStatus.withdrawn.value
    assert row.payload["rejected_reason"] == "Therapist rejected support."
    assert audit.actor_id == "system"


def test_ml_review_create_persists_result_session_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, MLResultRecord, SessionRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.feature_service import extract_features
    from app.services.ml_review_service import create_ml_review

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'ml-review-create.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-026", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    transcript = repo.create_transcript(
        Transcript(
            transcript_id="tr_tx_013",
            session_id=session.session_id,
            case_id=case.case_id,
            source="manual_entry",
            raw_text="@Begin\n*CHI: reviewed placeholder words .\n*MOT: adult prompt words .\n@End",
            qa_status=QaStatus.pass_,
            therapist_attested=True,
            review_status=ReviewStatus.attested,
        ),
        session_status=ReviewStatus.attested,
        actor_id="user_tx",
        audit_action="transcript.attest",
        audit_message="Transcript attested.",
    )
    extract_features(repo, transcript.transcript_id, FeatureExtractionRequest())

    def fail_snapshot_save() -> None:
        raise AssertionError("ML review creation must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    result = create_ml_review(repo, transcript.transcript_id, MLReviewRequest())

    with repo.SessionLocal() as db:
        row = db.get(MLResultRecord, result.result_id)
        session_row = db.get(SessionRecord, session.session_id)
        audit = db.query(AuditLogRecord).filter_by(action="ml_review.create", target_id=result.result_id).one()

    assert row is not None
    assert row.session_id == session.session_id
    assert row.transcript_id == transcript.transcript_id
    assert session_row is not None
    assert session_row.ml_result_id == result.result_id
    assert audit.actor_id == "system"


def test_ml_review_cue_patch_persists_result_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.core.security import CurrentUser
    from app.db.models import AuditLogRecord, MLResultRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.feature_service import extract_features
    from app.services.ml_review_service import create_ml_review, patch_cue_state

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'ml-review-cue.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-TX-027", age_months=52), actor_id="user_tx")
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-06-25", session_type="therapy_session"),
        actor_id="user_tx",
    )
    transcript = repo.create_transcript(
        Transcript(
            transcript_id="tr_tx_014",
            session_id=session.session_id,
            case_id=case.case_id,
            source="manual_entry",
            raw_text="@Begin\n*CHI: reviewed placeholder words .\n*MOT: adult prompt words .\n@End",
            qa_status=QaStatus.pass_,
            therapist_attested=True,
            review_status=ReviewStatus.attested,
        ),
        session_status=ReviewStatus.attested,
        actor_id="user_tx",
        audit_action="transcript.attest",
        audit_message="Transcript attested.",
    )
    extract_features(repo, transcript.transcript_id, FeatureExtractionRequest())
    result = create_ml_review(repo, transcript.transcript_id, MLReviewRequest())

    def fail_snapshot_save() -> None:
        raise AssertionError("ML cue patch must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    cue_code = result.cues[0].cue_code
    patched = patch_cue_state(
        repo,
        result.result_id,
        cue_code,
        ReviewCuePatch(status="acknowledged", therapist_note="Reviewed by therapist."),
        CurrentUser(user_id="therapist_tx", role="therapist", display_name="Therapist"),
    )

    with repo.SessionLocal() as db:
        row = db.get(MLResultRecord, result.result_id)
        audit = db.query(AuditLogRecord).filter_by(action="ml_review.cue_state", target_id=result.result_id).one()

    assert patched.cues[0].review_state.status == "acknowledged"
    assert row is not None
    assert row.payload["cues"][0]["review_state"]["reviewed_by"] == "therapist_tx"
    assert audit.actor_id == "therapist_tx"


def test_membership_upsert_persists_sql_record_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, OrganizationMembershipRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'membership.db'}")

    def fail_snapshot_save() -> None:
        raise AssertionError("membership upsert must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    membership = repo.upsert_membership(
        "org_tx",
        OrganizationMembershipCreate(user_id="clinician_tx", display_name="Clinician TX", role="therapist"),
        actor_id="admin_tx",
    )

    with repo.SessionLocal() as db:
        row = db.get(OrganizationMembershipRecord, membership.membership_id)
        audit = db.query(AuditLogRecord).filter_by(action="membership.upsert", target_id=membership.membership_id).one()

    assert row is not None
    assert row.organization_id == "org_tx"
    assert row.user_id == "clinician_tx"
    assert row.role == "therapist"
    assert audit.organization_id == "org_tx"
    assert audit.actor_id == "admin_tx"


def test_care_team_assignment_persists_sql_record_case_team_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, CaseCareTeamAssignmentRecord, ChildCaseRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'care-team.db'}")
    case = repo.create_case(
        ChildCaseCreate(
            child_code="C-SQL-TEAM",
            organization_id="org_tx",
            care_team_user_ids=["clinician_a"],
            age_months=54,
        ),
        actor_id="clinician_a",
    )
    repo.upsert_membership(
        "org_tx",
        OrganizationMembershipCreate(user_id="clinician_b", display_name="Clinician B", role="therapist"),
        actor_id="admin_tx",
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("care-team assignment must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    assignment = repo.assign_care_team_member(
        case.case_id,
        CareTeamAssignmentCreate(user_id="clinician_b", role="therapist"),
        actor_id="admin_tx",
    )

    with repo.SessionLocal() as db:
        assignment_row = db.get(CaseCareTeamAssignmentRecord, assignment.assignment_id)
        case_row = db.get(ChildCaseRecord, case.case_id)
        audit = db.query(AuditLogRecord).filter_by(action="care_team.assign", target_id=assignment.assignment_id).one()

    assert assignment_row is not None
    assert assignment_row.organization_id == "org_tx"
    assert assignment_row.case_id == case.case_id
    assert assignment_row.user_id == "clinician_b"
    assert case_row is not None
    assert case_row.care_team_user_ids == ["clinician_a", "clinician_b"]
    assert audit.organization_id == "org_tx"


def test_invitation_acceptance_persists_sql_membership_and_audit_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, OrganizationInvitationRecord, OrganizationMembershipRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'invitation.db'}")

    def fail_snapshot_save() -> None:
        raise AssertionError("invitation workflow must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    invitation = repo.create_invitation(
        "org_tx",
        OrganizationInvitationCreate(
            email="clinician-tx@example.test",
            display_name="Clinician TX",
            role="therapist",
        ),
        actor_id="admin_tx",
    )
    accepted = repo.accept_invitation(
        "org_tx",
        invitation.invitation_id,
        OrganizationInvitationAccept(user_id="clinician_tx"),
        actor_id="admin_tx",
    )

    with repo.SessionLocal() as db:
        invitation_row = db.get(OrganizationInvitationRecord, invitation.invitation_id)
        membership_row = db.query(OrganizationMembershipRecord).filter_by(user_id="clinician_tx").one()
        accepted_audit = (
            db.query(AuditLogRecord)
            .filter_by(action="invitation.accept", target_id=invitation.invitation_id)
            .one()
        )

    assert accepted.status == "accepted"
    assert invitation_row is not None
    assert invitation_row.accepted_user_id == "clinician_tx"
    assert membership_row.organization_id == "org_tx"
    assert membership_row.active is True
    assert accepted_audit.organization_id == "org_tx"


def test_invitation_expiry_is_fixed_to_seven_days_and_expired_acceptance_requires_reissue(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, OrganizationInvitationRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'invitation-expiry.db'}")
    invitation = repo.create_invitation(
        "org_tx",
        OrganizationInvitationCreate(
            email="clinician-expired@example.test",
            display_name="Clinician Expired",
            role="therapist",
            expires_at=utc_now() + timedelta(days=30),
        ),
        actor_id="admin_tx",
    )

    assert abs((invitation.expires_at - invitation.created_at).total_seconds() - (7 * 24 * 60 * 60)) < 5

    with repo.SessionLocal() as db:
        row = db.get(OrganizationInvitationRecord, invitation.invitation_id)
        assert row is not None
        row.expires_at = utc_now() - timedelta(minutes=1)
        db.commit()

    with pytest.raises(ValueError, match="Expired invitations require a newly issued invitation."):
        repo.accept_invitation(
            "org_tx",
            invitation.invitation_id,
            OrganizationInvitationAccept(user_id="clinician_tx"),
            actor_id="admin_tx",
        )

    with repo.SessionLocal() as db:
        row = db.get(OrganizationInvitationRecord, invitation.invitation_id)
        audit = (
            db.query(AuditLogRecord)
            .filter_by(action="invitation.accept", target_id=invitation.invitation_id)
            .one()
        )

    assert row is not None
    assert row.status == "expired"
    assert audit.outcome == "denied"


def test_accepted_invitation_cannot_be_accepted_twice_in_sql_repository(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'invitation-reaccept.db'}")
    invitation = repo.create_invitation(
        "org_tx",
        OrganizationInvitationCreate(
            email="clinician-repeat@example.test",
            display_name="Clinician Repeat",
            role="therapist",
        ),
        actor_id="admin_tx",
    )
    repo.accept_invitation(
        "org_tx",
        invitation.invitation_id,
        OrganizationInvitationAccept(user_id="clinician_tx"),
        actor_id="admin_tx",
    )

    with pytest.raises(ValueError, match="Invitation has already been accepted."):
        repo.accept_invitation(
            "org_tx",
            invitation.invitation_id,
            OrganizationInvitationAccept(user_id="clinician_tx"),
            actor_id="admin_tx",
        )


def test_identity_email_cannot_bind_to_different_user_in_sql_repository(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'invitation-email-identity.db'}")
    first = repo.create_invitation(
        "org_tx",
        OrganizationInvitationCreate(
            email="shared@example.test",
            display_name="Shared Identity",
            role="therapist",
        ),
        actor_id="admin_tx",
    )
    repo.accept_invitation(
        "org_tx",
        first.invitation_id,
        OrganizationInvitationAccept(user_id="clinician_a"),
        actor_id="admin_tx",
    )
    second = repo.create_invitation(
        "org_other",
        OrganizationInvitationCreate(
            email="shared@example.test",
            display_name="Shared Identity",
            role="therapist",
        ),
        actor_id="admin_other",
    )

    with pytest.raises(ValueError, match="Identity email is already bound to a different user."):
        repo.accept_invitation(
            "org_other",
            second.invitation_id,
            OrganizationInvitationAccept(user_id="clinician_b"),
            actor_id="admin_other",
        )

    with repo.SessionLocal() as db:
        denied_audit = (
            db.query(AuditLogRecord)
            .filter_by(action="invitation.accept", target_id=second.invitation_id)
            .one()
        )

    assert denied_audit.outcome == "denied"


def test_membership_revocation_persists_sql_assignment_removal_and_audit(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, CaseCareTeamAssignmentRecord, ChildCaseRecord, OrganizationMembershipRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'revoke.db'}")
    case = repo.create_case(
        ChildCaseCreate(
            child_code="C-SQL-REVOKE",
            organization_id="org_tx",
            care_team_user_ids=["clinician_a"],
            age_months=54,
        ),
        actor_id="clinician_a",
    )
    membership = repo.upsert_membership(
        "org_tx",
        OrganizationMembershipCreate(user_id="clinician_b", display_name="Clinician B", role="therapist"),
        actor_id="admin_tx",
    )
    repo.assign_care_team_member(
        case.case_id,
        CareTeamAssignmentCreate(user_id="clinician_b", role="therapist"),
        actor_id="admin_tx",
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("membership revocation must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    revoked = repo.revoke_membership("org_tx", membership.membership_id, actor_id="admin_tx")

    with repo.SessionLocal() as db:
        membership_row = db.get(OrganizationMembershipRecord, membership.membership_id)
        assignment_row = db.query(CaseCareTeamAssignmentRecord).filter_by(user_id="clinician_b").one()
        case_row = db.get(ChildCaseRecord, case.case_id)
        audit = db.query(AuditLogRecord).filter_by(action="membership.revoke", target_id=membership.membership_id).one()

    assert revoked.active is False
    assert membership_row is not None
    assert membership_row.active is False
    assert assignment_row.active is False
    assert case_row is not None
    assert case_row.care_team_user_ids == ["clinician_a"]
    assert audit.actor_id == "admin_tx"


def test_break_glass_case_access_persists_sql_audit(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'break-glass.db'}")
    case = repo.create_case(
        ChildCaseCreate(
            child_code="C-SQL-BREAK",
            organization_id="org_tx",
            care_team_user_ids=["clinician_a"],
            age_months=54,
        ),
        actor_id="clinician_a",
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("break-glass audit must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)

    repo.audit_break_glass_case_access("org_tx", case.case_id, actor_id="platform_tx")

    with repo.SessionLocal() as db:
        audit = db.query(AuditLogRecord).filter_by(action="break_glass.case_access", target_id=case.case_id).one()

    assert audit.organization_id == "org_tx"
    assert audit.actor_id == "platform_tx"


def test_stale_sql_worker_cannot_assign_revoked_membership_and_reads_audits_authoritatively(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, CaseCareTeamAssignmentRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    url = f"sqlite:///{tmp_path / 'membership-authority.db'}"
    writer = SqlAlchemyRepository(url)
    case = writer.create_case(
        ChildCaseCreate(child_code="C-MEMBER-RACE", organization_id="org_tx", age_months=54),
        actor_id="clinician_a",
    )
    membership = writer.upsert_membership(
        "org_tx",
        OrganizationMembershipCreate(user_id="clinician_b", display_name="Clinician B", role="therapist"),
        actor_id="admin_tx",
    )
    stale = SqlAlchemyRepository(url, create_schema=False)
    initial = stale.get_membership("org_tx", "clinician_b")
    assert initial is not None and initial.active is True
    before_assignment = Barrier(2)
    after_revocation = Barrier(2)

    def stale_assign():
        before_assignment.wait(timeout=5)
        after_revocation.wait(timeout=5)
        return stale.assign_care_team_member(
            case.case_id,
            CareTeamAssignmentCreate(user_id="clinician_b", role="therapist", active=True),
            actor_id="admin_tx",
        )

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(stale_assign)
        before_assignment.wait(timeout=5)
        writer.revoke_membership("org_tx", membership.membership_id, actor_id="admin_tx")
        after_revocation.wait(timeout=5)
        with pytest.raises(ValueError, match="Active organization membership"):
            future.result(timeout=5)

    authoritative = stale.get_membership("org_tx", "clinician_b")
    assert authoritative is not None and authoritative.active is False

    audits = stale.list_audit_events("org_tx")
    assert any(item["action"] == "membership.revoke" for item in audits)
    with stale.SessionLocal() as db:
        assert (
            db.query(CaseCareTeamAssignmentRecord)
            .filter_by(user_id="clinician_b")
            .count()
            == 0
        )
        assert db.query(AuditLogRecord).filter_by(action="care_team.assign").count() == 0


def test_sql_case_creation_persists_primary_assignment_and_revocation_clears_legacy_arrays(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'canonical-case-team.db'}")
    created = repo.create_case(
        ChildCaseCreate(
            organization_id="pilot_org_001",
            child_code="C-SQL-CANONICAL-TEAM",
            age_months=54,
            care_team_user_ids=["therapist-demo"],
            primary_therapist_user_id="therapist-demo",
        ),
        actor_id="system",
    )
    assignments = repo.list_care_team_assignments(created.case_id)
    assert len(assignments) == 1
    assert assignments[0].user_id == "therapist-demo"
    assert assignments[0].active is True
    assert assignments[0].is_primary is True

    membership = repo.get_membership("pilot_org_001", "therapist-demo")
    repo.revoke_membership(
        "pilot_org_001", membership.membership_id, actor_id="admin-demo"
    )

    for case_id in (created.case_id, "case_demo_001"):
        authoritative = repo.get_case(case_id)
        assert "therapist-demo" not in authoritative.care_team_user_ids
        assert authoritative.primary_therapist_user_id is None
    assert repo.list_care_team_assignments(created.case_id) == []


def test_sql_case_authorization_rejects_inactive_membership_even_with_legacy_array(tmp_path):
    pytest.importorskip("sqlalchemy")
    from fastapi import HTTPException
    from app.auth.authorization import require_case
    from app.core.security import CurrentUser
    from app.db.models import OrganizationMembershipRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'inactive-legacy-access.db'}")
    with repo.SessionLocal() as db:
        membership = db.query(OrganizationMembershipRecord).filter_by(
            organization_id="pilot_org_001", user_id="therapist-demo"
        ).one()
        membership.active = False
        db.commit()

    with pytest.raises(HTTPException) as denied:
        require_case(
            repo,
            "case_demo_001",
            CurrentUser(
                user_id="therapist-demo",
                role="therapist",
                organization_id="pilot_org_001",
            ),
        )
    assert denied.value.status_code == 403


def test_sql_case_audits_include_historical_transcripts_mappings_and_jobs(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.schemas.clinical import (
        AudioProcessRequest,
        TherapySessionCreate,
        Transcript,
    )
    from app.schemas.speaker_mapping import SpeakerMapping
    from app.services.audio_job_service import create_audio_processing_job

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'case-audit-scope.db'}")
    case = repo.create_case(
        ChildCaseCreate(child_code="C-SQL-AUDIT-SCOPE", age_months=54),
        actor_id="therapist-demo",
    )
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-08-24"),
        actor_id="therapist-demo",
    )
    old_transcript = Transcript(
        transcript_id="tr-sql-audit-old",
        session_id=session.session_id,
        case_id=case.case_id,
        source="manual",
        raw_text="*CHI:\tsynthetic old .",
    )
    repo.create_transcript(
        old_transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="therapist-demo",
        audit_action="historical.transcript",
        audit_message="Synthetic historical transcript.",
    )
    mapping = SpeakerMapping(
        mapping_id="map-sql-audit-old",
        organization_id=case.organization_id,
        transcript_id=old_transcript.transcript_id,
        source_transcript_version=1,
        entries=[],
    )
    repo.save_speaker_mapping_draft(
        mapping, expected_mapping_version=None, actor_id="therapist-demo"
    )
    job = create_audio_processing_job(
        repo, session.session_id, AudioProcessRequest(provider="manual", draft_text="CHI: synthetic")
    )
    repo.add_audit(
        "unrelated.case", "case-not-linked", "Synthetic unrelated audit.",
        actor_id="system", organization_id=case.organization_id,
    )

    audits = repo.list_case_audits(case.case_id, case.organization_id)
    targets = {item["target_id"] for item in audits}

    assert old_transcript.transcript_id in targets
    assert mapping.mapping_id in targets
    assert job.job_id in targets
    assert "case-not-linked" not in targets
