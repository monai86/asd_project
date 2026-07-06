"""Smoke-check the active FastAPI Alembic migrations on a fresh database."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
HEAD_REVISION = "0012_report_runtime_fields"
REQUIRED_TABLES = {
    "alembic_version",
    "organizations",
    "user_profiles",
    "organization_memberships",
    "organization_invitations",
    "organization_settings",
    "case_care_team_assignments",
    "identity_profiles",
    "regional_retention_policies",
    "consent_records",
    "notifications",
    "job_attempts",
    "child_cases",
    "sessions",
    "transcripts",
    "reports",
    "audit_logs",
}
REQUIRED_COLUMNS = {
    "reports": {
        "requested_provider",
        "actual_provider",
        "provider_version",
        "fallback_reason",
        "rewrite_attempted",
        "rewrite_succeeded",
        "safety_validation_result",
        "finalized_safety_result",
        "finalization_blocked",
        "validator_version",
        "rule_set_version",
        "input_hash",
        "version",
        "transcript_id",
        "feature_result_id",
        "ml_result_id",
        "ml_skipped_reason",
        "validation_summary",
        "feature_schema_version",
        "therapist_notes",
        "session_goals",
        "generated_from_versions",
        "sections",
    },
}
LEGACY_DATABASE_URL_ENV = "THERAPIST_APP" "_V2_DATABASE_URL"
CANONICAL_DATABASE_URL_ENV = "LINGUALENS_DATABASE_URL"


@dataclass(frozen=True)
class MigrationSmokeResult:
    database_path: Path
    head_revision: str
    tables: list[str]


def run_migration_smoke(database_path: Path) -> MigrationSmokeResult:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()

    previous_database_url = os.environ.get(CANONICAL_DATABASE_URL_ENV)
    previous_legacy_database_url = os.environ.get(LEGACY_DATABASE_URL_ENV)
    os.environ[CANONICAL_DATABASE_URL_ENV] = f"sqlite:///{database_path}"
    try:
        _clear_settings_cache()
        alembic_config = Config(str(API_ROOT / "alembic.ini"))
        alembic_config.set_main_option("script_location", str(API_ROOT / "app" / "db" / "migrations"))
        command.upgrade(alembic_config, "head")
    finally:
        if previous_database_url is None:
            os.environ.pop(CANONICAL_DATABASE_URL_ENV, None)
        else:
            os.environ[CANONICAL_DATABASE_URL_ENV] = previous_database_url
        if previous_legacy_database_url is None:
            os.environ.pop(LEGACY_DATABASE_URL_ENV, None)
        else:
            os.environ[LEGACY_DATABASE_URL_ENV] = previous_legacy_database_url
        _clear_settings_cache()

    tables = _tables(database_path)
    missing = sorted(REQUIRED_TABLES.difference(tables))
    if missing:
        raise RuntimeError(f"Migration smoke missing required tables: {', '.join(missing)}")
    for table_name, expected_columns in REQUIRED_COLUMNS.items():
        columns = _columns(database_path, table_name)
        missing_columns = sorted(expected_columns.difference(columns))
        if missing_columns:
            raise RuntimeError(
                "Migration smoke missing required columns on "
                f"{table_name}: {', '.join(missing_columns)}"
            )

    stored_revision = _stored_revision(database_path)
    if stored_revision != HEAD_REVISION:
        raise RuntimeError(f"Migration smoke reached {stored_revision}, expected {HEAD_REVISION}.")

    return MigrationSmokeResult(database_path=database_path, head_revision=stored_revision, tables=sorted(tables))


def _clear_settings_cache() -> None:
    try:
        from app.core.config import get_settings
    except ImportError:
        return
    get_settings.cache_clear()


def _tables(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("select name from sqlite_master where type = 'table'").fetchall()
    return {row[0] for row in rows}


def _columns(database_path: Path, table_name: str) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(f"pragma table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _stored_revision(database_path: Path) -> str:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute("select version_num from alembic_version").fetchone()
    if row is None:
        raise RuntimeError("Migration smoke did not create alembic_version.")
    return str(row[0])


def main() -> int:
    with TemporaryDirectory(prefix="therapist-api-migration-smoke-") as temp_dir:
        result = run_migration_smoke(Path(temp_dir) / "migration-smoke.db")
        print(
            "API migration smoke passed: "
            f"{result.head_revision} with {len(result.tables)} tables on fresh SQLite database."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
