from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import get_settings


def _ensure_alembic_version_column_capacity() -> None:
    engine = create_engine(get_settings().database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'alembic_version'
                          AND column_name = 'version_num'
                    ) THEN
                        ALTER TABLE alembic_version
                        ALTER COLUMN version_num TYPE VARCHAR(128);
                    END IF;
                END
                $$;
                """
            )
        )


def run_alembic_upgrade_head() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    alembic_ini = root_dir / "alembic.ini"
    _ensure_alembic_version_column_capacity()
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(root_dir / "app" / "db" / "migrations"))
    config.set_main_option("prepend_sys_path", str(root_dir))
    command.upgrade(config, "head")
