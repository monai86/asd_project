from __future__ import annotations

import pytest

from app.repositories.base import (
    CaseVersionConflictError,
    ReportVersionConflictError,
    SessionVersionConflictError,
    TranscriptVersionConflictError,
)
from app.schemas.clinical import (
    AttestationRequest,
    ChildCaseCreate,
    ChildCaseUpdate,
    PrivacyOperationCreate,
    PrivacyOperationPatch,
    QaStatus,
    ReviewStatus,
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

    signed = sign_off_report(repo, report.report_id, signed_by="Demo Therapist")

    with repo.SessionLocal() as db:
        report_row = db.get(ReportRecord, report.report_id)
        case_row = db.get(ChildCaseRecord, case.case_id)
        audit = db.query(AuditLogRecord).filter_by(action="report.sign_off", target_id=report.report_id).one()

    assert signed.status == ReviewStatus.signed_off
    assert signed.signed_snapshot_hash
    assert signed.signed_snapshot_version == report.version
    assert report_row is not None
    assert report_row.status == ReviewStatus.signed_off.value
    assert report_row.signed_snapshot_hash == signed.signed_snapshot_hash
    assert case_row is not None
    assert case_row.latest_report_status == ReviewStatus.signed_off.value
    assert audit.actor_id == "system"
    assert audit.correlation_id == f"report-update-{signed.version}"


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

    attested = attest(repo, transcript.transcript_id, AttestationRequest(attested_by="Demo Therapist"))

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
    assert audit.actor_id == "system"


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
    repo.create_transcript(
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
