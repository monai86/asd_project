from __future__ import annotations

import pytest

from app.repositories.base import CaseVersionConflictError
from app.schemas.clinical import ChildCaseCreate, ChildCaseUpdate


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
