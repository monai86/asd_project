from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def run_alembic_upgrade_head() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    alembic_ini = root_dir / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(root_dir / "app" / "db" / "migrations"))
    config.set_main_option("prepend_sys_path", str(root_dir))
    command.upgrade(config, "head")
