from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/settings", tags=["settings"])


def _audio_upload_capability(config) -> str:
    if config.storage_mode in {"local", "local_private"}:
        return "experimental"
    if config.storage_mode == "supabase_private" and all(
        (
            config.supabase_storage_url.strip(),
            config.supabase_storage_service_role_key.strip(),
            config.supabase_storage_bucket.strip(),
            config.supabase_signed_upload_ttl_seconds > 0,
        )
    ):
        return "experimental"
    return "unavailable"


@router.get("")
def settings():
    config = get_settings()
    audio_upload = _audio_upload_capability(config)
    transcription = "experimental" if config.mock_mode and audio_upload == "experimental" else "unavailable"
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
        "capabilities": {
            "cases": "available",
            "audio_upload": audio_upload,
            "transcription": transcription,
            "transcript_qa": "available",
            "feature_extraction": "available",
            "ai_review": "disabled",
            "report_drafting": (
                "available" if config.ai_report_drafting_enabled else "disabled"
            ),
            "pdf_export": "unavailable",
        },
        "pipeline_settings": {
            "audio_processing": "experimental_async",
            "job_queue_mode": config.job_queue_mode,
            "repository_mode": config.repository_mode,
            "storage_mode": config.storage_mode,
            "ai_review_policy": "organization_opt_in_default_off",
            "ai_report_drafting_enabled": config.ai_report_drafting_enabled,
        },
    }
