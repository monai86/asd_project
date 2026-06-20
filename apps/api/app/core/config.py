from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Therapist App v2 API"
    api_prefix: str = "/api/v1"
    mock_mode: bool = True
    debug_feature_override: bool = False
    max_audio_file_size_mb: int = 250
    repository_mode: str = "json"
    json_repository_path: str = ".local/therapist-app-v2-repository.json"
    database_url: str = "postgresql+psycopg://therapist:therapist@localhost/therapist_app_v2"
    job_queue_mode: str = "memory"
    redis_url: str = "redis://localhost:6379/0"
    storage_mode: str = "local"
    local_storage_root: str = ".local/storage"
    reference_artifact_dir: str = "artifacts/reference_evidence/current"
    ml_inference_timeout_seconds: float = 2.0

    @property
    def resolved_json_repository_path(self) -> Path:
        return Path(self.json_repository_path)

    @property
    def resolved_local_storage_root(self) -> Path:
        return Path(self.local_storage_root)


@lru_cache
def get_settings() -> Settings:
    return Settings(
        mock_mode=os.getenv("THERAPIST_APP_V2_MOCK_MODE", "true").lower() != "false",
        debug_feature_override=os.getenv("THERAPIST_APP_V2_DEBUG_FEATURE_OVERRIDE", "false").lower() == "true",
        repository_mode=os.getenv("THERAPIST_APP_V2_REPOSITORY_MODE", "json"),
        json_repository_path=os.getenv("THERAPIST_APP_V2_JSON_REPOSITORY_PATH", ".local/therapist-app-v2-repository.json"),
        database_url=os.getenv("THERAPIST_APP_V2_DATABASE_URL", "postgresql+psycopg://therapist:therapist@localhost/therapist_app_v2"),
        job_queue_mode=os.getenv("THERAPIST_APP_V2_JOB_QUEUE_MODE", "memory"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        storage_mode=os.getenv("THERAPIST_APP_V2_STORAGE_MODE", "local"),
        local_storage_root=os.getenv("THERAPIST_APP_V2_LOCAL_STORAGE_ROOT", ".local/storage"),
        reference_artifact_dir=os.getenv(
            "THERAPIST_APP_V2_REFERENCE_ARTIFACT_DIR",
            "artifacts/reference_evidence/current",
        ),
        ml_inference_timeout_seconds=float(
            os.getenv("THERAPIST_APP_V2_ML_INFERENCE_TIMEOUT_SECONDS", "2.0")
        ),
    )
