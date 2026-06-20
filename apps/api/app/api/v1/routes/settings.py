from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def settings():
    config = get_settings()
    return {
        "mock_mode": config.mock_mode,
        "model_version": "v2-mock",
        "feature_schema": "therapist-app-v2.1",
        "guideline_mapping": "review-support-only",
        "user_roles": ["therapist", "admin"],
        "data_retention": "local demo data only unless configured otherwise",
        "consent_policy": "visible per case; withdrawal unlinks case outputs",
        "pipeline_settings": {
            "audio_processing": "experimental_async",
            "job_queue_mode": config.job_queue_mode,
            "repository_mode": config.repository_mode,
            "storage_mode": config.storage_mode,
        },
    }
