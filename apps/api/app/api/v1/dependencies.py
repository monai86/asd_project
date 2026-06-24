from functools import lru_cache

from app.core.config import get_settings
from app.repositories.mock_repository import JsonFileRepository, MockRepository


@lru_cache
def get_repository_singleton():
    settings = get_settings()
    if settings.repository_mode == "json":
        return JsonFileRepository(settings.resolved_json_repository_path)
    if settings.repository_mode in {"sql", "sqlalchemy"}:
        from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

        return SqlAlchemyRepository(settings.database_url, create_schema=settings.sql_create_schema)
    if settings.repository_mode in {"memory", "mock"}:
        return MockRepository()
    raise RuntimeError(f"Unsupported repository mode: {settings.repository_mode}")


def get_repository():
    return get_repository_singleton()
