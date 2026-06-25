from __future__ import annotations

import pytest

from app.repositories.base import CaseVersionConflictError, SessionVersionConflictError, TranscriptVersionConflictError
from app.schemas.clinical import (
    ChildCaseCreate,
    ChildCaseUpdate,
    ReviewStatus,
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
