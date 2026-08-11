from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.api.v1.dependencies import get_repository
from app.auth.authorization import assert_clinical_mutation_allowed, assert_sensitive_clinical_export_allowed, require_session, require_transcript
from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser, get_current_user, require_therapist
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    AttestationRequest,
    LimitationAcknowledgmentRequest,
    QaReport,
    SpeakerMappingConfirmRequest,
    SpeakerMappingDraftRequest,
    SpeakerMappingResponse,
    Transcript,
    TranscriptExport,
    TranscriptManualCreate,
    TranscriptMergeRequest,
    TranscriptPatch,
    TranscriptSplitRequest,
    TranscriptUploadCha,
)
from app.schemas.speech_pipeline import ChatExport, LimitationAcknowledgment
from app.services.consent_service import (
    active_case_consent_fence,
    ensure_session_consent_active,
    ensure_transcript_consent_active,
)
from app.services import transcript_service
from app.services import speaker_mapping_service
from app.services.chat_roundtrip_service import create_verified_chat_export
from app.services.qa_policy_service import acknowledge_limitation, current_qa_outcomes

router = APIRouter(tags=["transcripts"])


@router.post("/sessions/{session_id}/transcripts/upload-cha", response_model=Transcript)
def upload_cha(
    session_id: str,
    payload: TranscriptUploadCha,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    assert_clinical_mutation_allowed(user)
    case_id = repo.sessions[session_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            require_session(repo, session_id, user)
            return transcript_service.create_from_cha(
                repo,
                session_id,
                payload,
            )
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
    assert_clinical_mutation_allowed(user)
    case_id = repo.sessions[session_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            require_session(repo, session_id, user)
            return transcript_service.create_from_manual(
                repo,
                session_id,
                payload,
            )
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/sessions/{session_id}/transcript", response_model=Transcript)
def get_session_transcript(
    session_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    transcript_id = repo.sessions[session_id].transcript_id
    if not transcript_id:
        raise not_found("Transcript not found.")
    try:
        ensure_session_consent_active(repo, session_id)
        return repo.clone(repo.transcripts[transcript_id])
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/transcripts/{transcript_id}", response_model=Transcript)
def get_transcript(
    transcript_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return repo.clone(repo.transcripts[transcript_id])
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
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.put("/transcripts/{transcript_id}/speaker-mapping", response_model=SpeakerMappingResponse)
def put_speaker_mapping(
    transcript_id: str,
    payload: SpeakerMappingDraftRequest,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    assert_clinical_mutation_allowed(user)
    case_id = repo.transcripts[transcript_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            require_transcript(repo, transcript_id, user)
            return speaker_mapping_service.save_mapping_draft(
                repo,
                transcript_id,
                payload,
            )
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/transcripts/{transcript_id}/speaker-mapping/confirm", response_model=SpeakerMappingResponse)
def confirm_speaker_mapping(
    transcript_id: str,
    payload: SpeakerMappingConfirmRequest,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    require_therapist(user)
    case_id = repo.transcripts[transcript_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            require_transcript(repo, transcript_id, user)
            return speaker_mapping_service.confirm_mapping(
                repo,
                transcript_id,
                payload,
                user,
            )
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.patch("/transcripts/{transcript_id}", response_model=Transcript)
def patch_transcript(
    transcript_id: str,
    payload: TranscriptPatch,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    assert_clinical_mutation_allowed(user)
    case_id = repo.transcripts[transcript_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            require_transcript(repo, transcript_id, user)
            return transcript_service.patch_transcript(
                repo,
                transcript_id,
                payload,
            )
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
    assert_clinical_mutation_allowed(user)
    case_id = repo.transcripts[transcript_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            require_transcript(repo, transcript_id, user)
            return transcript_service.split_utterance(
                repo,
                transcript_id,
                payload,
            )
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
    assert_clinical_mutation_allowed(user)
    case_id = repo.transcripts[transcript_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            require_transcript(repo, transcript_id, user)
            return transcript_service.merge_utterances(
                repo,
                transcript_id,
                payload,
            )
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/transcripts/{transcript_id}/export-cha", response_model=TranscriptExport)
def export_transcript_cha(
    transcript_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    assert_sensitive_clinical_export_allowed(user)
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        transcript = repo.clone(repo.transcripts[transcript_id])
        current_export = repo.get_current_chat_export(transcript_id)
        if current_export is not None and current_export.cha_text is not None:
            return TranscriptExport(
                transcript_id=transcript_id,
                filename=f"{current_export.export_id}.cha",
                cha_text=current_export.cha_text,
            )
        if transcript.source.startswith("asr_draft:") or transcript.asr_provenance:
            raise bad_request(
                "CHAT_EXPORT_REQUIRED: create a current verified CHAT export before downloading an ASR artifact."
            )
        return transcript_service.export_cha(repo, transcript_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/transcripts/{transcript_id}/chat-exports", response_model=ChatExport)
def create_chat_export(
    transcript_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    require_therapist(user)
    assert_sensitive_clinical_export_allowed(user)
    case_id = repo.transcripts[transcript_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            require_transcript(repo, transcript_id, user)
            ensure_transcript_consent_active(repo, transcript_id)
            return create_verified_chat_export(
                repo,
                transcript_id,
                exported_by=user.user_id,
            )
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/chat-exports/{export_id}", response_model=ChatExport)
def get_chat_export(
    export_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    export = next((item for item in repo.chat_exports.values() if item.export_id == export_id), None)
    if export is None:
        raise not_found("CHAT export not found.")
    require_transcript(repo, export.transcript_id, user)
    try:
        ensure_transcript_consent_active(repo, export.transcript_id)
        return repo.clone(export)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/chat-exports/{export_id}/download")
def download_chat_export(
    export_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    export = next((item for item in repo.chat_exports.values() if item.export_id == export_id), None)
    if export is None:
        raise not_found("CHAT export not found.")
    require_transcript(repo, export.transcript_id, user)
    assert_sensitive_clinical_export_allowed(user)
    try:
        ensure_transcript_consent_active(repo, export.transcript_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    if export.status.value != "current" or export.round_trip.status.value != "verified" or not export.cha_text:
        raise bad_request("CHAT export is not a current verified artifact.")
    return PlainTextResponse(
        export.cha_text,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{export.export_id}.cha"'},
    )


@router.post("/transcripts/{transcript_id}/qa", response_model=QaReport)
def qa_transcript(
    transcript_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    assert_clinical_mutation_allowed(user)
    case_id = repo.transcripts[transcript_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            require_transcript(repo, transcript_id, user)
            return transcript_service.run_qa(repo, transcript_id)
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
    require_therapist(user)
    if payload.attested_by and user.display_name and payload.attested_by != user.display_name:
        raise bad_request("Transcript attestation must use the authenticated therapist identity.")
    case_id = repo.transcripts[transcript_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            require_transcript(repo, transcript_id, user)
            normalized_payload = payload.model_copy(
                update={
                    "attested_by": user.display_name
                    or payload.attested_by
                }
            )
            return transcript_service.attest(
                repo,
                transcript_id,
                normalized_payload,
                actor_id=user.user_id,
                attested_by=(
                    user.display_name
                    or normalized_payload.attested_by
                ),
            )
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/transcripts/{transcript_id}/limitations")
def list_transcript_limitations(
    transcript_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    outcomes = current_qa_outcomes(repo, transcript_id)
    acknowledgments = repo.list_current_acknowledgments(transcript_id)
    return {
        "transcript_id": transcript_id,
        "transcript_version": repo.transcripts[transcript_id].version,
        "validator_version": "speech-qa-v1.7.0",
        "blockers": [
            item.model_dump(mode="json") for item in outcomes
            if item.disposition.value == "integrity_blocker"
        ],
        "limitations": [
            item.model_dump(mode="json") for item in outcomes
            if item.disposition.value == "acknowledgeable_limitation"
        ],
        "acknowledgments": [item.model_dump(mode="json") for item in acknowledgments],
    }


@router.post(
    "/transcripts/{transcript_id}/limitations/{limitation_code}/acknowledgments",
    response_model=LimitationAcknowledgment,
)
def acknowledge_transcript_limitation(
    transcript_id: str,
    limitation_code: str,
    payload: LimitationAcknowledgmentRequest,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_transcript(repo, transcript_id, user)
    require_therapist(user)
    case_id = repo.transcripts[transcript_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            return acknowledge_limitation(
                repo,
                transcript_id,
                limitation_code,
                payload,
                therapist_user_id=user.user_id,
                therapist_role=user.role,
            )
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
