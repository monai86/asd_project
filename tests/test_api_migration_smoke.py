import sqlite3


def test_api_migration_smoke_creates_fresh_database_schema(tmp_path):
    from scripts.check_api_migrations import HEAD_REVISION, run_migration_smoke

    database_path = tmp_path / "migration-smoke.db"

    result = run_migration_smoke(database_path)

    assert result.database_path == database_path
    assert result.head_revision == HEAD_REVISION
    assert {"child_cases", "sessions", "transcripts", "reports", "audit_logs"}.issubset(
        set(result.tables)
    )

    with sqlite3.connect(database_path) as connection:
        stored_revision = connection.execute("select version_num from alembic_version").fetchone()[0]
    assert stored_revision == result.head_revision
