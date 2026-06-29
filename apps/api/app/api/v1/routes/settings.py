from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def settings():
    config = get_settings()
    return {
        "mock_mode": config.mock_mode,
        "auth_mode": config.auth_mode,
        "model_version": "v2-mock",
        "feature_schema": "lingualens-app.1",
        "guideline_mapping": "review-support-only",
        "user_roles": ["therapist", "clinical_supervisor", "org_admin"],
        "access_model": {
            "invitation_only": config.supabase_require_invitation,
            "required_app_aal": "aal2" if config.supabase_require_mfa else "aal1",
            "active_organization_session": "explicit_selection_when_ambiguous",
            "production_mock_mode": "forbidden" if not config.mock_mode else "local_only",
        },
        "data_retention": "local demo data only unless configured otherwise",
        "consent_policy": "visible per case; withdrawal unlinks case outputs",
        "pipeline_settings": {
            "audio_processing": "experimental_async",
            "job_queue_mode": config.job_queue_mode,
            "repository_mode": config.repository_mode,
            "storage_mode": config.storage_mode,
            "ai_review_policy": "organization_opt_in_default_off",
            "ai_report_drafting_enabled": config.ai_report_drafting_enabled,
        },
    }
