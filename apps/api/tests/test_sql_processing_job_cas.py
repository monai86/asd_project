from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
from pathlib import Path
from uuid import uuid4

import pytest

from app.repositories.base import ProcessingJobStateConflictError
from app.repositories.sqlalchemy_repository import (
    SqlAlchemyRepository,
    _processing_job_cas_statement,
)
from app.schemas.clinical import JobStatus, ProcessingJob


def _job(
    job_id: str,
    status: JobStatus,
    *,
    attempt_number: int | None = 7,
) -> ProcessingJob:
    details = {"status_history": [status.value]}
    if attempt_number is not None:
        details["attempt_number"] = attempt_number
    return ProcessingJob(
        job_id=job_id,
        session_id="session_demo_001",
        status=status,
        message=f"transition to {status.value}",
        details=details,
    )


def test_postgresql_cas_statement_pins_job_status_and_attempt_predicates() -> None:
    postgresql = pytest.importorskip("sqlalchemy.dialects.postgresql")
    statement = _processing_job_cas_statement(
        _job("job_cas_compile", JobStatus.processing),
        expected_status=JobStatus.queued,
    )

    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert sql.startswith("UPDATE processing_jobs SET")
    assert "processing_jobs.job_id =" in sql
    assert "processing_jobs.status =" in sql
    assert "processing_jobs.details ->>" in sql
    assert "AS INTEGER" in sql
    assert "RETURNING processing_jobs.job_id" in sql
    assert compiled.params["job_id_1"] == "job_cas_compile"
    assert compiled.params["status_1"] == JobStatus.queued.value
    assert compiled.params["details_1"] == "attempt_number"
    assert compiled.params["coalesce_1"] == 1
    assert compiled.params["coalesce_2"] == 7


def test_postgresql_cas_treats_missing_legacy_attempt_as_attempt_one() -> None:
    postgresql = pytest.importorskip("sqlalchemy.dialects.postgresql")
    statement = _processing_job_cas_statement(
        _job(
            "job_legacy_compile",
            JobStatus.processing,
            attempt_number=None,
        ),
        expected_status=JobStatus.queued,
    )

    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert "coalesce" in sql.lower()
    assert 1 in compiled.params.values()


def test_sqlite_legacy_job_without_attempt_number_can_transition(
    tmp_path,
) -> None:
    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'legacy-cas.db'}")
    queued = _job(
        "job_legacy_sqlite",
        JobStatus.queued,
        attempt_number=None,
    )
    repo.create_processing_job(
        queued,
        audit_action="test.legacy.queued",
        audit_message="Legacy attempt fixture queued.",
    )
    candidate = repo.get_processing_job(queued.job_id)
    assert candidate is not None
    assert "attempt_number" not in candidate.details
    candidate.status = JobStatus.cancelled

    updated = repo.update_processing_job(
        candidate,
        expected_status=JobStatus.queued,
        audit_action="test.legacy.cancelled",
        audit_message="Legacy attempt fixture cancelled.",
    )

    assert updated.status is JobStatus.cancelled


def test_pre_0014_legacy_job_upgrades_and_transitions_as_attempt_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alembic = pytest.importorskip("alembic")
    sqlalchemy = pytest.importorskip("sqlalchemy")
    from alembic import command
    from alembic.config import Config

    database_path = tmp_path / "pre-0014.db"
    database_url = f"sqlite:///{database_path}"
    from app.core.config import get_settings

    monkeypatch.setenv("LINGUALENS_DATABASE_URL", database_url)
    get_settings.cache_clear()
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option(
        "script_location",
        str(api_root / "app" / "db" / "migrations"),
    )
    command.upgrade(config, "0013_v170_speech_pipeline")
    now = datetime.now(timezone.utc)
    engine = sqlalchemy.create_engine(database_url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO organizations
                (organization_id, name, pilot_mode, created_at)
            VALUES (?, ?, ?, ?)
            """,
            ("pilot_org_001", "Pilot", False, now),
        )
        connection.exec_driver_sql(
            """
            INSERT INTO child_cases
                (case_id, organization_id, child_code, age_months, language,
                 consent_status, review_priority, notes, version,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "case_legacy",
                "pilot_org_001",
                "LEGACY",
                60,
                "Thai",
                "granted",
                "low",
                "",
                1,
                now,
                now,
            ),
        )
        connection.exec_driver_sql(
            """
            INSERT INTO sessions
                (session_id, case_id, organization_id, session_date,
                 session_type, status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "session_legacy",
                "case_legacy",
                "pilot_org_001",
                "2026-07-01",
                "therapy_session",
                "Draft",
                "",
                now,
                now,
            ),
        )
        connection.exec_driver_sql(
            """
            INSERT INTO processing_jobs
                (job_id, organization_id, session_id, status, message,
                 error_code, details, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "job_pre_0014",
                "pilot_org_001",
                "session_legacy",
                "queued",
                "Legacy queued job.",
                None,
                "{}",
                now,
                now,
            ),
        )
    command.upgrade(config, "0015_audio_storage_identity")

    repo = SqlAlchemyRepository(database_url, create_schema=False)
    candidate = repo.get_processing_job("job_pre_0014")
    assert candidate is not None
    assert "attempt_number" not in candidate.details
    candidate.status = JobStatus.cancelled
    updated = repo.update_processing_job(
        candidate,
        expected_status=JobStatus.queued,
        audit_action="test.legacy.upgraded_cancel",
        audit_message="Upgraded legacy job cancelled.",
    )
    assert updated.status is JobStatus.cancelled
    get_settings.cache_clear()


def test_postgresql_concurrent_cas_has_exactly_one_winner() -> None:
    database_url = os.getenv("LINGUALENS_TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("LINGUALENS_TEST_POSTGRES_URL is not configured")
    sqlalchemy = pytest.importorskip("sqlalchemy")
    schema = f"lingualens_cas_{uuid4().hex}"
    administrative_engine = sqlalchemy.create_engine(database_url)
    repositories: list[SqlAlchemyRepository] = []
    try:
        with administrative_engine.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        scoped_url = str(
            sqlalchemy.engine.make_url(database_url).update_query_dict(
                {"options": f"-csearch_path={schema}"}
            )
        )
        seed = SqlAlchemyRepository(scoped_url)
        repositories.append(seed)
        queued = _job(f"job_{uuid4().hex}", JobStatus.queued)
        seed.create_processing_job(
            queued,
            audit_action="transcription.job_queued",
            audit_message="PostgreSQL CAS integration fixture queued.",
        )
        first = SqlAlchemyRepository(scoped_url)
        second = SqlAlchemyRepository(scoped_url)
        repositories.extend((first, second))

        def transition(
            repo: SqlAlchemyRepository,
            target: JobStatus,
        ) -> str:
            candidate = repo.get_processing_job(queued.job_id)
            assert candidate is not None
            candidate.status = target
            candidate.message = f"CAS winner: {target.value}"
            try:
                repo.update_processing_job(
                    candidate,
                    expected_status=JobStatus.queued,
                    audit_action=f"test.cas.{target.value}",
                    audit_message="Concurrent PostgreSQL CAS candidate.",
                )
            except ProcessingJobStateConflictError:
                return "conflict"
            return target.value

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(
                executor.map(
                    lambda args: transition(*args),
                    (
                        (first, JobStatus.processing),
                        (second, JobStatus.cancelled),
                    ),
                )
            )

        assert outcomes.count("conflict") == 1
        winner = next(item for item in outcomes if item != "conflict")
        durable = SqlAlchemyRepository(scoped_url)
        repositories.append(durable)
        final_job = durable.get_processing_job(queued.job_id)
        assert final_job is not None
        assert final_job.status.value == winner
    finally:
        for repository in repositories:
            repository.engine.dispose()
        with administrative_engine.begin() as connection:
            connection.exec_driver_sql(
                f'DROP SCHEMA IF EXISTS "{schema}" CAS'
            )
        administrative_engine.dispose()


def test_sql_processing_job_compare_and_swap_atomic_transition(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "atomic-cas.db"
    repo = SqlAlchemyRepository(f"sqlite:///{db_path}")

    # 1. Create initial job in queued state
    job_id = f"job_cas_{uuid4().hex[:8]}"
    initial_job = _job(job_id, JobStatus.queued, attempt_number=1)
    created_job, is_new = repo.create_processing_job(
        initial_job,
        audit_action="test.cas.create",
        audit_message="Job queued for CAS atomic test.",
    )
    assert is_new is True
    assert created_job.status is JobStatus.queued

    # 2. First atomic transition: queued -> processing (matching expected_status=queued)
    candidate_1 = repo.get_processing_job(job_id)
    assert candidate_1 is not None
    candidate_1.status = JobStatus.processing
    candidate_1.message = "Job transitioning to processing."

    updated_1 = repo.update_processing_job(
        candidate_1,
        expected_status=JobStatus.queued,
        audit_action="test.cas.processing",
        audit_message="Updated to processing.",
    )
    assert updated_1.status is JobStatus.processing

    # 3. Attempt stale CAS transition: expected_status=queued (fails because current DB status is processing)
    stale_candidate = repo.get_processing_job(job_id)
    assert stale_candidate is not None
    stale_candidate.status = JobStatus.cancelled
    stale_candidate.message = "Stale attempt to cancel."

    with pytest.raises(ProcessingJobStateConflictError) as exc_info:
        repo.update_processing_job(
            stale_candidate,
            expected_status=JobStatus.queued,
            audit_action="test.cas.stale_cancel",
            audit_message="Should fail due to expected status mismatch.",
        )
    conflict_error = exc_info.value
    assert conflict_error.job.status is JobStatus.processing

    # 4. Mismatched attempt_number: expected_status=processing but attempt_number is wrong
    wrong_attempt_candidate = repo.get_processing_job(job_id)
    assert wrong_attempt_candidate is not None
    wrong_attempt_candidate.status = JobStatus.needs_review
    wrong_attempt_candidate.details["attempt_number"] = 99

    with pytest.raises(ProcessingJobStateConflictError) as exc_info:
        repo.update_processing_job(
            wrong_attempt_candidate,
            expected_status=JobStatus.processing,
            audit_action="test.cas.wrong_attempt",
            audit_message="Should fail due to attempt_number mismatch.",
        )
    assert exc_info.value.job.status is JobStatus.processing

    # 5. Successful second atomic transition: processing -> needs_review
    valid_candidate = repo.get_processing_job(job_id)
    assert valid_candidate is not None
    valid_candidate.status = JobStatus.needs_review
    valid_candidate.message = "Job processing finished successfully."

    final_job = repo.update_processing_job(
        valid_candidate,
        expected_status=JobStatus.processing,
        audit_action="test.cas.needs_review",
        audit_message="Updated to needs_review.",
    )
    assert final_job.status is JobStatus.needs_review

    # Verify database state matches
    db_job = repo.get_processing_job(job_id)
    assert db_job is not None
    assert db_job.status is JobStatus.needs_review

