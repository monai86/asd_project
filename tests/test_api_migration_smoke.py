import pytest
import sqlite3


def _upgrade_database(database_path, revision, monkeypatch):
    from alembic import command
    from alembic.config import Config

    from scripts.check_api_migrations import API_ROOT, CANONICAL_DATABASE_URL_ENV, _clear_settings_cache

    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "app" / "db" / "migrations"))
    monkeypatch.setenv(CANONICAL_DATABASE_URL_ENV, f"sqlite:///{database_path}")
    _clear_settings_cache()
    command.upgrade(config, revision)
    _clear_settings_cache()


def _seed_0013_audio_job(connection, *, job_id, status, audio_id="audio-backfill"):
    timestamp = "2026-08-24 00:00:00+00:00"
    connection.execute(
        "INSERT OR IGNORE INTO child_cases "
        "(case_id, child_code, age_months, language, consent_status, review_priority, notes, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("case-backfill", "C-BACKFILL", 60, "English", "granted", "moderate", "", timestamp, timestamp),
    )
    connection.execute(
        "INSERT OR IGNORE INTO sessions "
        "(session_id, case_id, session_date, session_type, status, notes, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("session-backfill", "case-backfill", "2026-08-24", "language_sample", "Draft", "", timestamp, timestamp),
    )
    connection.execute(
        "INSERT OR IGNORE INTO audio_files "
        "(audio_file_id, session_id, case_id, original_filename, content_type, size_bytes, storage_mode, "
        "upload_status, retained, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (audio_id, "session-backfill", "case-backfill", "synthetic.wav", "audio/wav", 12, "metadata", "uploaded", 1, timestamp),
    )
    connection.execute(
        "INSERT INTO processing_jobs "
        "(job_id, session_id, status, message, details, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, json(?), ?, ?)",
        (job_id, "session-backfill", status, "Synthetic migration job.", f'{{"audio_file_id":"{audio_id}"}}', timestamp, timestamp),
    )
    connection.commit()


def test_api_migration_smoke_creates_fresh_database_schema(tmp_path):
    pytest.importorskip("alembic")
    from scripts.check_api_migrations import HEAD_REVISION, run_migration_smoke

    database_path = tmp_path / "migration-smoke.db"

    result = run_migration_smoke(database_path)

    assert result.database_path == database_path
    assert result.head_revision == HEAD_REVISION
    assert {"child_cases", "sessions", "transcripts", "speaker_mappings", "reports", "audit_logs"}.issubset(
        set(result.tables)
    )

    with sqlite3.connect(database_path) as connection:
        stored_revision = connection.execute("select version_num from alembic_version").fetchone()[0]
    assert stored_revision == result.head_revision


def test_speaker_mapping_migration_downgrades_cleanly_to_previous_head(tmp_path, monkeypatch):
    pytest.importorskip("alembic")
    from alembic import command
    from alembic.config import Config

    from scripts.check_api_migrations import (
        API_ROOT,
        CANONICAL_DATABASE_URL_ENV,
        HEAD_REVISION,
        _clear_settings_cache,
        run_migration_smoke,
    )

    database_path = tmp_path / "migration-downgrade.db"
    result = run_migration_smoke(database_path)
    assert result.head_revision == HEAD_REVISION == "0014_speaker_mappings"

    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "app" / "db" / "migrations"))
    monkeypatch.setenv(CANONICAL_DATABASE_URL_ENV, f"sqlite:///{database_path}")
    _clear_settings_cache()
    command.downgrade(config, "0013_session_cues_acknowledgement")
    _clear_settings_cache()

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("select name from sqlite_master where type = 'table'").fetchall()
        }
        stored_revision = connection.execute("select version_num from alembic_version").fetchone()[0]
    assert "speaker_mappings" not in tables
    assert stored_revision == "0013_session_cues_acknowledgement"


def test_0014_backfills_audio_claims_from_populated_0013(tmp_path, monkeypatch):
    pytest.importorskip("alembic")
    database_path = tmp_path / "migration-backfill.db"
    _upgrade_database(database_path, "0013_session_cues_acknowledgement", monkeypatch)
    with sqlite3.connect(database_path) as connection:
        _seed_0013_audio_job(connection, job_id="job-active", status="processing")
        _seed_0013_audio_job(connection, job_id="job-terminal", status="failed")

    _upgrade_database(database_path, "0014_speaker_mappings", monkeypatch)

    with sqlite3.connect(database_path) as connection:
        rows = {
            row[0]: row[1:]
            for row in connection.execute(
                "SELECT job_id, audio_file_id, active_audio_file_id FROM processing_jobs"
            )
        }
    assert rows["job-active"] == ("audio-backfill", "audio-backfill")
    assert rows["job-terminal"] == ("audio-backfill", None)


def test_0014_rejects_duplicate_backfilled_active_audio_claims(tmp_path, monkeypatch):
    pytest.importorskip("alembic")
    database_path = tmp_path / "migration-duplicate-backfill.db"
    _upgrade_database(database_path, "0013_session_cues_acknowledgement", monkeypatch)
    with sqlite3.connect(database_path) as connection:
        _seed_0013_audio_job(connection, job_id="job-active-one", status="queued")
        _seed_0013_audio_job(connection, job_id="job-active-two", status="processing")

    with pytest.raises(Exception, match="UNIQUE|unique"):
        _upgrade_database(database_path, "0014_speaker_mappings", monkeypatch)
