import pytest
import sqlite3


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
