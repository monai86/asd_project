from __future__ import annotations

import hashlib
import json

from app.core.security import CurrentUser
from app.repositories.mock_repository import MockRepository, new_id
from app.schemas.clinical import (
    EvidenceReviewPatch,
    EvidenceReviewState,
    MLReadiness,
    MLResult,
    MLReviewRequest,
    ReviewCuePatch,
    ReviewCueState,
    utc_now,
)
from app.services.ml_providers.base import MLProviderContext
from app.services.ml_providers.registry import ml_provider_registry


REQUIRED_FEATURES = {"child_utterance_count", "adult_utterance_count", "total_word_count"}


class MLReadinessError(ValueError):
    def __init__(self, readiness: MLReadiness):
        super().__init__("; ".join(readiness.reasons))
        self.readiness = readiness


def check_ml_readiness(repo: MockRepository, transcript_id: str, provider_id: str | None = None) -> MLReadiness:
    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise KeyError(transcript_id)
    session = repo.get_session(transcript.session_id)
    if session is None:
        raise KeyError(transcript.session_id)
    try:
        provider = ml_provider_registry.get(provider_id) if provider_id else ml_provider_registry.get_default()
    except ValueError:
        provider = None
    reasons: list[str] = []
    codes: list[str] = []
    feature_set = repo.get_feature_set(session.feature_set_id or "") if session.feature_set_id else None
    if not transcript.therapist_attested or transcript.review_status.value == "Needs Review":
        codes.append("transcript_requires_review")
        reasons.append("ML review requires therapist-attested transcript.")
    if any(issue.blocking for issue in transcript.qa_issues):
        codes.append("blocking_chat_validation_errors")
        reasons.append("Blocking CHAT validation errors must be resolved.")
    if feature_set is None or feature_set.transcript_id != transcript_id:
        codes.append("features_not_completed")
        reasons.append("Feature extraction has not been completed.")
    elif feature_set.review_status.value == "stale":
        codes.append("features_stale")
        reasons.append("Feature extraction is stale and must be regenerated from the current transcript.")
    elif feature_set.transcript_version != transcript.version:
        codes.append("feature_transcript_version_mismatch")
        reasons.append("Feature extraction does not match the current transcript version and must be regenerated.")
    elif not feature_set.therapist_attested:
        codes.append("features_not_attested")
        reasons.append("Feature result is not based on a therapist-attested transcript.")
    elif not feature_set.schema_version:
        codes.append("unknown_feature_schema")
        reasons.append("Input feature schema version is unknown.")
    else:
        values = {item.name: item.value for item in feature_set.features}
        missing = sorted(name for name in REQUIRED_FEATURES if name not in values or values[name] is None)
        if missing:
            codes.append("required_features_missing")
            reasons.append(f"Required feature values are missing: {', '.join(missing)}.")
    if provider is None:
        codes.append("ml_provider_unsupported")
        reasons.append(f"Unsupported ML provider: {provider_id}.")
    else:
        availability = provider.check_availability()
    if provider is not None and not availability:
        codes.append("ml_provider_unavailable")
        reasons.append(f"ML provider unavailable. {availability.reason}".strip())
    if (
        provider is not None
        and availability
        and feature_set is not None
        and hasattr(provider, "readiness_issues")
    ):
        context = _provider_context(repo, transcript_id)
        for code, reason in provider.readiness_issues(feature_set, context):
            if code not in codes:
                codes.append(code)
                reasons.append(reason)
    return MLReadiness(
        ready=not codes,
        transcript_id=transcript_id,
        session_id=transcript.session_id,
        feature_result_id=feature_set.feature_set_id if feature_set else None,
        provider_id=provider.provider_id if provider else str(provider_id or ""),
        reason_codes=codes,
        reasons=reasons,
    )


def create_ml_review(repo: MockRepository, transcript_id: str, request: MLReviewRequest) -> MLResult:
    readiness = check_ml_readiness(repo, transcript_id, request.provider_id)
    if not readiness.ready:
        raise MLReadinessError(readiness)
    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise KeyError(transcript_id)
    session = repo.get_session(transcript.session_id)
    if session is None:
        raise KeyError(transcript.session_id)
    feature_set = repo.get_feature_set(readiness.feature_result_id or "")
    if feature_set is None:
        raise KeyError(readiness.feature_result_id or "")
    provider = ml_provider_registry.get(request.provider_id) if request.provider_id else ml_provider_registry.get_default()
    config = provider.get_model_metadata().get("default_config", {})
    feature_hash = input_feature_hash(feature_set, config)
    current = repo.get_ml_result(session.ml_result_id or "") if session.ml_result_id else None
    if (
        current
        and current.is_current
        and not request.force_regenerate
        and current.input_feature_hash == feature_hash
        and current.provider_id == provider.provider_id
        and current.provider_version == provider.provider_version
    ):
        return _with_current(repo, current)
    provider_context = _provider_context(repo, transcript_id)
    provider_result = provider.predict(feature_set, provider_context, config)
    result = MLResult(
        result_id=new_id("mlr"),
        transcript_id=transcript_id,
        session_id=transcript.session_id,
        feature_result_id=feature_set.feature_set_id,
        provider_id=provider.provider_id,
        provider_name=provider.provider_name,
        provider_version=provider.provider_version,
        input_feature_schema_version=feature_set.schema_version,
        input_feature_hash=feature_hash,
        status=provider_result.status,
        cues=provider_result.cues,
        pattern_evidence=provider_result.pattern_evidence,
        profile_evidence=provider_result.profile_evidence,
        artifact_provenance=provider_result.artifact_provenance,
        scores=None,
        confidence=None,
        warnings=[*feature_set.warnings, *provider_result.warnings, *[issue.code for issue in transcript.qa_issues if not issue.blocking]],
        limitations=provider_result.limitations,
        provider_config=config,
    )
    saved = repo.create_ml_result(
        result,
        actor_id="system",
        audit_action="ml_review.create",
        audit_message=f"Feature-based review cues generated by {provider.provider_name} v{provider.provider_version}.",
    )
    return _with_current(repo, saved)


def get_current_ml_review(repo: MockRepository, session_id: str) -> MLResult:
    session = repo.get_session(session_id)
    if session is None:
        raise KeyError(session_id)
    result_id = session.ml_result_id
    result = repo.get_ml_result(result_id or "") if result_id else None
    if result is None:
        raise KeyError("ML review result not found.")
    result = _with_current(repo, result)
    if not result.is_current:
        raise KeyError("ML review result is stale.")
    return result


def get_ml_result(repo: MockRepository, result_id: str) -> MLResult:
    result = repo.get_ml_result(result_id)
    if result is None:
        raise KeyError(result_id)
    return _with_current(repo, result)


def _require_current_ml_result(repo: MockRepository, result_id: str) -> MLResult:
    result = repo.get_ml_result(result_id)
    if result is None:
        raise KeyError(result_id)
    result = _with_current(repo, result)
    if not result.is_current:
        raise KeyError("ML review result is stale and cannot be edited.")
    return result


def patch_cue_state(repo: MockRepository, result_id: str, cue_code: str, patch: ReviewCuePatch, user: CurrentUser) -> MLResult:
    if user.role not in {"therapist", "clinical_supervisor"}:
        raise PermissionError("Therapist or clinical supervisor role required.")
    result = _require_current_ml_result(repo, result_id)
    cue = next((item for item in result.cues if item.cue_code == cue_code), None)
    if cue is None:
        raise KeyError("Review cue not found.")
    cue.review_state = ReviewCueState(
        status=patch.status,
        therapist_note=patch.therapist_note,
        reviewed_by=user.user_id,
        reviewed_by_name=user.display_name,
        reviewed_at=utc_now(),
    )
    saved = repo.update_ml_result(
        result,
        actor_id=user.user_id,
        audit_action="ml_review.cue_state",
        audit_message=f"Cue {cue_code} marked {patch.status} by {user.user_id}.",
    )
    return _with_current(repo, saved)


def patch_profile_evidence_state(
    repo: MockRepository,
    result_id: str,
    profile_code: str,
    patch: EvidenceReviewPatch,
    user: CurrentUser,
) -> MLResult:
    if user.role not in {"therapist", "clinical_supervisor"}:
        raise PermissionError("Therapist or clinical supervisor role required.")
    result = _require_current_ml_result(repo, result_id)
    profile = next(
        (
            item
            for item in result.profile_evidence
            if item.profile_code == profile_code
        ),
        None,
    )
    if profile is None:
        raise KeyError("Profile evidence not found.")
    profile.review_state = EvidenceReviewState(
        status=patch.status,
        therapist_note=patch.therapist_note,
        reviewed_by=user.user_id,
        reviewed_by_name=user.display_name,
        reviewed_at=utc_now(),
    )
    saved = repo.update_ml_result(
        result,
        actor_id=user.user_id,
        audit_action="ml_review.profile_state",
        audit_message=f"Profile {profile_code} marked {patch.status} by {user.user_id}.",
    )
    return _with_current(repo, saved)


def input_feature_hash(feature_set, config: dict) -> str:
    payload = {
        "feature_set_id": feature_set.feature_set_id,
        "transcript_id": feature_set.transcript_id,
        "transcript_version": feature_set.transcript_version,
        "schema_version": feature_set.schema_version,
        "features": sorted(
            [{"name": item.name, "value": item.value, "feature_version": item.feature_version} for item in feature_set.features],
            key=lambda item: item["name"],
        ),
        "provider_config": config,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _optional_task_type(chat_metadata: dict) -> str | None:
    value = chat_metadata.get("task_type") or chat_metadata.get("activity_type")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _provider_context(repo: MockRepository, transcript_id: str) -> MLProviderContext:
    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise KeyError(transcript_id)
    session = repo.get_session(transcript.session_id)
    if session is None:
        raise KeyError(transcript.session_id)
    case = repo.get_case(session.case_id)
    if case is None:
        raise KeyError(session.case_id)
    languages = transcript.chat_metadata.get("languages")
    persisted_language = case.language
    if isinstance(languages, list) and languages:
        persisted_language = ",".join(
            str(value).strip() for value in languages if str(value).strip()
        )
    return MLProviderContext(
        case_id=case.case_id,
        session_id=session.session_id,
        transcript_id=transcript.transcript_id,
        age_months=case.age_months,
        language=persisted_language,
        session_type=session.session_type,
        task_type=_optional_task_type(transcript.chat_metadata),
    )


def _with_current(repo: MockRepository, result: MLResult) -> MLResult:
    session = repo.get_session(result.session_id)
    current_id = session.ml_result_id if session is not None else None
    return repo.clone(result.model_copy(update={"is_current": result.is_current and current_id == result.result_id}))
