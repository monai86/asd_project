from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import get_repository
from app.auth.authorization import (
    assert_clinical_mutation_allowed,
    assert_sensitive_clinical_export_allowed,
    require_authoritative_therapist,
    require_session,
    require_transcript,
)
from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser, get_current_user
from app.repositories.base import (
    SpeakerMappingAuthorizationError,
    SpeakerMappingVersionConflictError,
    TranscriptVersionConflictError,
)
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    AttestationRequest,
    QaReport,
    Transcript,
    TranscriptExport,
    TranscriptManualCreate,
    TranscriptMergeRequest,
    TranscriptPatch,
    TranscriptSplitRequest,
    TranscriptUploadCha,
)
from app.schemas.speaker_mapping import SpeakerMappingConfirmRequest, SpeakerMappingDraftUpdate, SpeakerMappingResponse
from app.services.consent_service import ensure_session_consent_active, ensure_transcript_consent_active
from app.services import speaker_mapping_service, transcript_service
from app.services.speaker_mapping_service import SpeakerMappingError

router = APIRouter(tags=["transcripts"])


def speaker_mapping_http_error(exc: Exception) -> HTTPException:
    """Translate mapping failures without exposing transcript or provider content."""
    if isinstance(exc, SpeakerMappingAuthorizationError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clinical content access denied.")
    if isinstance(exc, SpeakerMappingError):
        status_code = (
            status.HTTP_409_CONFLICT
            if exc.code in {"SPEAKER_MAPPING_VERSION_CONFLICT", "SPEAKER_MAPPING_STALE"}
            else status.HTTP_400_BAD_REQUEST
        )
        return HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, (SpeakerMappingVersionConflictError, TranscriptVersionConflictError)):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SPEAKER_MAPPING_VERSION_CONFLICT",
                "message": "Transcript or mapping changed; reload and retry.",
            },
        )
    return bad_request(str(exc))


def transcript_version_http_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "TRANSCRIPT_VERSION_CONFLICT",
            "message": "Transcript changed; reload and retry.",
        },
    )


@router.post("/sessions/{session_id}/transcripts/upload-cha", response_model=Transcript)
def upload_cha(
    session_id: str,
    payload: TranscriptUploadCha,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    assert_clinical_mutation_allowed(repo, user)
    try:
        ensure_session_consent_active(repo, session_id)
        return transcript_service.create_from_cha(repo, session_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/sessions/{session_id}/transcripts/manual", response_model=Transcript)
def manual_transcript(
    session_id: str,
    payload: TranscriptManualCreate,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    assert_clinical_mutation_allowed(repo, user)
    try:
        ensure_session_consent_active(repo, session_id)
        return transcript_service.create_from_manual(repo, session_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/sessions/{session_id}/transcript", response_model=Transcript)
def get_session_transcript(
    session_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    session = require_session(repo, session_id, user)
    transcript_id = session.transcript_id
    if not transcript_id:
        raise not_found("Transcript not found.")
    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise not_found("Transcript not found.")
    return transcript


@router.get("/transcripts/{transcript_id}", response_model=Transcript)
def get_transcript(
    transcript_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    transcript = require_transcript(repo, transcript_id, user)
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return transcript
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/transcripts/{transcript_id}/speaker-mapping", response_model=SpeakerMappingResponse)
def get_speaker_mapping(
    transcript_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return speaker_mapping_service.get_mapping(repo, transcript_id)
    except SpeakerMappingError as exc:
        raise speaker_mapping_http_error(exc) from exc
    except (ValueError, SpeakerMappingVersionConflictError, TranscriptVersionConflictError) as exc:
        raise speaker_mapping_http_error(exc) from exc


@router.put("/transcripts/{transcript_id}/speaker-mapping", response_model=SpeakerMappingResponse)
def put_speaker_mapping(
    transcript_id: str,
    payload: SpeakerMappingDraftUpdate,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    assert_clinical_mutation_allowed(repo, user)
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return speaker_mapping_service.save_mapping_draft(
            repo, transcript_id, payload, actor_id=user.user_id, trusted_system=False
        )
    except SpeakerMappingAuthorizationError as exc:
        raise speaker_mapping_http_error(exc) from exc
    except SpeakerMappingError as exc:
        raise speaker_mapping_http_error(exc) from exc
    except (ValueError, SpeakerMappingVersionConflictError, TranscriptVersionConflictError) as exc:
        raise speaker_mapping_http_error(exc) from exc


@router.post("/transcripts/{transcript_id}/speaker-mapping/confirm", response_model=SpeakerMappingResponse)
def confirm_speaker_mapping(
    transcript_id: str,
    payload: SpeakerMappingConfirmRequest,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    effective_user = require_authoritative_therapist(repo, user)
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return speaker_mapping_service.confirm_mapping(
            repo,
            transcript_id,
            payload,
            actor_id=effective_user.user_id,
            actor_role=effective_user.role,
            trusted_system=False,
        )
    except SpeakerMappingAuthorizationError as exc:
        raise speaker_mapping_http_error(exc) from exc
    except SpeakerMappingError as exc:
        raise speaker_mapping_http_error(exc) from exc
    except (ValueError, SpeakerMappingVersionConflictError, TranscriptVersionConflictError) as exc:
        raise speaker_mapping_http_error(exc) from exc


@router.patch("/transcripts/{transcript_id}", response_model=Transcript)
def patch_transcript(
    transcript_id: str,
    payload: TranscriptPatch,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    assert_clinical_mutation_allowed(repo, user)
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return transcript_service.patch_transcript(repo, transcript_id, payload)
    except TranscriptVersionConflictError as exc:
        raise transcript_version_http_error() from exc
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/transcripts/{transcript_id}/split", response_model=Transcript)
def split_transcript_utterance(
    transcript_id: str,
    payload: TranscriptSplitRequest,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    assert_clinical_mutation_allowed(repo, user)
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return transcript_service.split_utterance(repo, transcript_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/transcripts/{transcript_id}/merge", response_model=Transcript)
def merge_transcript_utterances(
    transcript_id: str,
    payload: TranscriptMergeRequest,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    assert_clinical_mutation_allowed(repo, user)
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return transcript_service.merge_utterances(repo, transcript_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/transcripts/{transcript_id}/export-cha", response_model=TranscriptExport)
def export_transcript_cha(
    transcript_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    assert_sensitive_clinical_export_allowed(repo, user)
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return transcript_service.export_cha(repo, transcript_id)
    except SpeakerMappingError as exc:
        raise speaker_mapping_http_error(exc) from exc
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/transcripts/{transcript_id}/qa", response_model=QaReport)
def qa_transcript(
    transcript_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    assert_clinical_mutation_allowed(repo, user)
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return transcript_service.run_qa(repo, transcript_id)
    except SpeakerMappingError as exc:
        raise speaker_mapping_http_error(exc) from exc
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/transcripts/{transcript_id}/attest", response_model=Transcript)
def attest_transcript(
    transcript_id: str,
    payload: AttestationRequest,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    require_authoritative_therapist(repo, user)
    if payload.attested_by and user.display_name and payload.attested_by != user.display_name:
        raise bad_request("Transcript attestation must use the authenticated therapist identity.")
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        normalized_payload = payload.model_copy(update={"attested_by": user.display_name or payload.attested_by})
        return transcript_service.attest(
            repo,
            transcript_id,
            normalized_payload,
            actor_id=user.user_id,
            attested_by=user.display_name or normalized_payload.attested_by,
        )
    except SpeakerMappingError as exc:
        raise speaker_mapping_http_error(exc) from exc
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
