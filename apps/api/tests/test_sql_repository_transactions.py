from __future__ import annotations

import pytest

from app.repositories.base import CaseVersionConflictError, SessionVersionConflictError
from app.schemas.clinical import ChildCaseCreate, ChildCaseUpdate, ReviewStatus, TherapySessionCreate, TherapySessionUpdate


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
