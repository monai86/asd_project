from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from typing import TypedDict

from app.schemas.clinical import QaStatus, ReviewStatus, Transcript, utc_now
from app.repositories.base import (
    ClinicalRepository,
    SpeakerMappingVersionConflictError,
    TranscriptVersionConflictError,
)
from app.schemas.speaker_mapping import (
    MappingEffectiveStatus,
    MappingPersistedStatus,
    SpeakerMapping,
    SpeakerMappingConfirmRequest,
    SpeakerMappingDraftUpdate,
    SpeakerMappingEntry,
    SpeakerMappingResponse,
)
from app.services.cha_service import build_cha_text, chat_build_options, parse_cha_document


class SpeakerMappingError(ValueError):
    """Privacy-safe, stable domain error for speaker-mapping workflows."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


_ERROR_MESSAGES = {
    "SPEAKER_MAPPING_INCOMPLETE": "Speaker mapping review is incomplete.",
    "SPEAKER_MAPPING_TARGET_REQUIRED": "Speaker mapping requires exactly one target child.",
    "SPEAKER_MAPPING_DUPLICATE_CODE": "Speaker mapping codes must be unique.",
    "SPEAKER_MAPPING_VERSION_CONFLICT": "Speaker mapping changed. Reload and review it again.",
    "SPEAKER_MAPPING_REQUIRED": "Confirm speaker roles before continuing.",
    "SPEAKER_MAPPING_STALE": "Speaker mapping is stale. Reload and review it again.",
}


def _mapping_error(code: str) -> SpeakerMappingError:
    return SpeakerMappingError(code, _ERROR_MESSAGES[code])


class _SpeakerGroup(TypedDict):
    source_speaker_label: str | None
    affected_utterance_ids: list[str]


def _temporary_speaker_id(value: str | None) -> str:
    return (value or "").strip()


def requires_speaker_mapping(transcript: Transcript) -> bool:
    """Return whether a real draft-ASR transcript needs speaker mapping."""

    return transcript.source.startswith("asr_draft:") and any(
        bool(_temporary_speaker_id(utterance.temporary_speaker_id))
        for utterance in transcript.utterances
    )


def derive_mapping_draft(transcript: Transcript) -> SpeakerMappingResponse:
    """Derive an unsaved, server-owned mapping draft from a transcript."""

    required = requires_speaker_mapping(transcript)
    provider_id = transcript.source.split(":", 1)[1].strip() if ":" in transcript.source else ""
    provider_metadata = {"provider_id": provider_id} if required and provider_id else {}
    grouped: OrderedDict[str, _SpeakerGroup] = OrderedDict()

    for utterance in transcript.utterances:
        temporary_id = _temporary_speaker_id(utterance.temporary_speaker_id)
        if not temporary_id:
            continue
        group = grouped.setdefault(
            temporary_id,
            _SpeakerGroup(source_speaker_label=None, affected_utterance_ids=[]),
        )
        if group["source_speaker_label"] is None:
            label = (utterance.source_speaker_label or "").strip()
            if label:
                group["source_speaker_label"] = label
        group["affected_utterance_ids"].append(utterance.utterance_id)

    entries = [
        SpeakerMappingEntry(
            temporary_speaker_id=temporary_id,
            source_speaker_label=values["source_speaker_label"],
            provider_metadata=provider_metadata,
            affected_utterance_ids=values["affected_utterance_ids"],
        )
        for temporary_id, values in grouped.items()
    ]
    record = SpeakerMapping(
        mapping_id=f"speaker_mapping_{transcript.transcript_id}_v{transcript.version}",
        organization_id=transcript.organization_id,
        transcript_id=transcript.transcript_id,
        source_transcript_version=transcript.version,
        entries=entries,
    )
    return SpeakerMappingResponse(
        **record.model_dump(),
        required=required,
        persisted=False,
        effective_status=(MappingEffectiveStatus.draft if required else MappingEffectiveStatus.not_required),
    )


def _mapping_response(transcript: Transcript, mapping: SpeakerMapping) -> SpeakerMappingResponse:
    if mapping.status == "draft" and mapping.source_transcript_version == transcript.version:
        status = MappingEffectiveStatus.draft
        issue_code = None
        issue_message = None
    elif mapping.status == "confirmed" and mapping.applied_transcript_version == transcript.version:
        status = MappingEffectiveStatus.confirmed
        issue_code = None
        issue_message = None
    else:
        status = MappingEffectiveStatus.stale
        issue_code = "SPEAKER_MAPPING_STALE"
        issue_message = "The speaker mapping is no longer current. Reload and review the transcript."
    return SpeakerMappingResponse(
        **mapping.model_dump(),
        required=True,
        persisted=True,
        effective_status=status,
        issue_code=issue_code,
        issue_message=issue_message,
    )


def get_mapping(repo: ClinicalRepository, transcript_id: str) -> SpeakerMappingResponse:
    """Return the persisted mapping effective for the transcript, if any."""

    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise KeyError(transcript_id)
    mapping = repo.get_latest_speaker_mapping(transcript_id)
    if mapping is not None:
        return _mapping_response(transcript, mapping)
    derived = derive_mapping_draft(transcript)
    if not derived.required:
        return derived
    return derived


def save_mapping_draft(
    repo: ClinicalRepository,
    transcript_id: str,
    update: SpeakerMappingDraftUpdate,
    *,
    actor_id: str = "system",
    trusted_system: bool = True,
) -> SpeakerMappingResponse:
    """Persist the therapist-editable portion of a mapping draft."""

    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise KeyError(transcript_id)
    if transcript.version != update.expected_transcript_version:
        raise TranscriptVersionConflictError(
            f"Transcript {transcript_id} expected version {update.expected_transcript_version}, found {transcript.version}."
        )
    if not requires_speaker_mapping(transcript):
        raise ValueError("This transcript does not require speaker mapping.")

    derived = derive_mapping_draft(transcript)
    editable_entries = {_temporary_speaker_id(entry.temporary_speaker_id): entry for entry in update.entries}
    entries: list[SpeakerMappingEntry] = []
    for derived_entry in derived.entries:
        editable = editable_entries.get(derived_entry.temporary_speaker_id)
        if editable is None:
            entries.append(derived_entry)
            continue
        entries.append(
            SpeakerMappingEntry(
                temporary_speaker_id=derived_entry.temporary_speaker_id,
                source_speaker_label=derived_entry.source_speaker_label,
                provider_metadata=derived_entry.provider_metadata,
                affected_utterance_ids=derived_entry.affected_utterance_ids,
                confirmed_chat_code=editable.confirmed_chat_code,
                participant_role=editable.participant_role,
                reviewed_utterance_ids=[
                    utterance_id
                    for utterance_id in editable.reviewed_utterance_ids
                    if utterance_id in derived_entry.affected_utterance_ids
                ],
            )
        )

    mapping = SpeakerMapping(
        mapping_id=repo.new_id("speaker_mapping"),
        organization_id=transcript.organization_id,
        transcript_id=transcript.transcript_id,
        source_transcript_version=transcript.version,
        entries=entries,
    )
    saved = repo.save_speaker_mapping_draft(
        mapping,
        expected_mapping_version=update.expected_mapping_version,
        actor_id=actor_id,
        trusted_system=trusted_system,
    )
    return _mapping_response(transcript, saved)


def validate_mapping_confirmation(transcript: Transcript, mapping: SpeakerMapping) -> None:
    """Validate exact, one-to-one temporary-speaker confirmation coverage."""

    utterance_ids = [utterance.utterance_id for utterance in transcript.utterances]
    if (
        any(not utterance_id.strip() for utterance_id in utterance_ids)
        or len(utterance_ids) != len(set(utterance_ids))
    ):
        raise _mapping_error("SPEAKER_MAPPING_INCOMPLETE")

    affected_by_temporary_id: OrderedDict[str, list[str]] = OrderedDict()
    for utterance in transcript.utterances:
        temporary_id = _temporary_speaker_id(utterance.temporary_speaker_id)
        if temporary_id:
            affected_by_temporary_id.setdefault(temporary_id, []).append(utterance.utterance_id)

    expected_ids = set(affected_by_temporary_id)
    submitted_ids = [_temporary_speaker_id(entry.temporary_speaker_id) for entry in mapping.entries]
    if (
        not expected_ids
        or len(expected_ids) > 3
        or len(submitted_ids) != len(set(submitted_ids))
        or set(submitted_ids) != expected_ids
    ):
        raise _mapping_error("SPEAKER_MAPPING_INCOMPLETE")

    if any(
        _temporary_speaker_id(utterance.temporary_speaker_id) not in expected_ids
        for utterance in transcript.utterances
    ):
        raise _mapping_error("SPEAKER_MAPPING_INCOMPLETE")

    for entry in mapping.entries:
        if entry.confirmed_chat_code is None or entry.participant_role is None:
            raise _mapping_error("SPEAKER_MAPPING_INCOMPLETE")
        expected_utterances = affected_by_temporary_id[_temporary_speaker_id(entry.temporary_speaker_id)]
        if (
            len(entry.reviewed_utterance_ids) != len(set(entry.reviewed_utterance_ids))
            or set(entry.reviewed_utterance_ids) != set(expected_utterances)
            or set(entry.affected_utterance_ids) != set(expected_utterances)
        ):
            raise _mapping_error("SPEAKER_MAPPING_INCOMPLETE")

    codes = [entry.confirmed_chat_code for entry in mapping.entries]
    if len(codes) != len(set(codes)):
        raise _mapping_error("SPEAKER_MAPPING_DUPLICATE_CODE")

    expected_roles = {"CHI": "target_child", "THER": "therapist", "OTH": "other"}
    if any(entry.participant_role != expected_roles[entry.confirmed_chat_code] for entry in mapping.entries):
        if any(entry.confirmed_chat_code == "CHI" for entry in mapping.entries):
            chi_entries = [entry for entry in mapping.entries if entry.confirmed_chat_code == "CHI"]
            if any(entry.participant_role != "target_child" for entry in chi_entries):
                raise _mapping_error("SPEAKER_MAPPING_TARGET_REQUIRED")
        raise _mapping_error("SPEAKER_MAPPING_INCOMPLETE")

    targets = [
        entry
        for entry in mapping.entries
        if entry.confirmed_chat_code == "CHI" and entry.participant_role == "target_child"
    ]
    if len(targets) != 1:
        raise _mapping_error("SPEAKER_MAPPING_TARGET_REQUIRED")


def _confirmed_participants(mapping: SpeakerMapping) -> str:
    participant_by_code = {
        "CHI": "CHI Child Target_Child",
        "THER": "THER Therapist Therapist",
        "OTH": "OTH Other Other",
    }
    return ", ".join(
        participant_by_code[entry.confirmed_chat_code]
        for entry in mapping.entries
        if entry.confirmed_chat_code is not None
    )


def build_confirmed_transcript(transcript: Transcript, mapping: SpeakerMapping) -> Transcript:
    """Build a provenance-preserving transcript with confirmed CHAT speakers."""

    code_by_temporary_id = {
        _temporary_speaker_id(entry.temporary_speaker_id): entry.confirmed_chat_code
        for entry in mapping.entries
    }
    utterances = []
    for utterance in transcript.utterances:
        temporary_id = _temporary_speaker_id(utterance.temporary_speaker_id)
        code = code_by_temporary_id.get(temporary_id)
        if code is None:
            raise _mapping_error("SPEAKER_MAPPING_INCOMPLETE")
        utterances.append(utterance.model_copy(deep=True, update={"speaker": code}))
    options = chat_build_options(transcript.raw_text)
    options["participants"] = _confirmed_participants(mapping)
    options["participant_ids"] = []
    raw_text = build_cha_text(utterances, **options)
    parsed = parse_cha_document(raw_text)
    chat_metadata = deepcopy(transcript.chat_metadata)
    for stale_review_key in ("qa_override", "attestation", "attestation_reason"):
        chat_metadata.pop(stale_review_key, None)
    chat_metadata.update(parsed.metadata)
    now = utc_now()
    return transcript.model_copy(
        deep=True,
        update={
            "raw_text": raw_text,
            "utterances": utterances,
            "chat_metadata": chat_metadata,
            "malformed_lines": parsed.malformed_lines,
            "orphan_dependent_tiers": parsed.orphan_dependent_tiers,
            "qa_status": QaStatus.not_run,
            "qa_issues": [],
            "therapist_attested": False,
            "attestation_reason": "",
            "review_status": ReviewStatus.needs_review,
            "version": transcript.version + 1,
            "updated_at": now,
        },
    )


def confirm_mapping(
    repo: ClinicalRepository,
    transcript_id: str,
    request: SpeakerMappingConfirmRequest,
    *,
    actor_id: str,
    actor_role: str,
    trusted_system: bool = False,
) -> SpeakerMappingResponse:
    """Validate and atomically apply the latest speaker-mapping draft."""

    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise KeyError(transcript_id)
    mapping = repo.get_latest_speaker_mapping(transcript_id)
    if mapping is None or mapping.status != "draft":
        raise _mapping_error("SPEAKER_MAPPING_REQUIRED")
    if (
        transcript.version != request.expected_transcript_version
        or mapping.mapping_version != request.expected_mapping_version
        or mapping.source_transcript_version != transcript.version
    ):
        raise _mapping_error("SPEAKER_MAPPING_VERSION_CONFLICT")

    validate_mapping_confirmation(transcript, mapping)
    updated_transcript = build_confirmed_transcript(transcript, mapping)
    now = utc_now()
    confirmed_mapping = mapping.model_copy(
        deep=True,
        update={
            "status": MappingPersistedStatus.confirmed,
            "applied_transcript_version": updated_transcript.version,
            "confirmed_by_user_id": actor_id,
            "confirmed_by_role": actor_role,
            "confirmed_at": now,
            "updated_at": now,
        },
    )
    try:
        saved = repo.confirm_speaker_mapping(
            confirmed_mapping,
            updated_transcript,
            expected_transcript_version=request.expected_transcript_version,
            expected_mapping_version=request.expected_mapping_version,
            actor_id=actor_id,
            trusted_system=trusted_system,
        )
    except (TranscriptVersionConflictError, SpeakerMappingVersionConflictError) as exc:
        raise _mapping_error("SPEAKER_MAPPING_VERSION_CONFLICT") from exc
    return _mapping_response(updated_transcript, saved)


def require_confirmed_mapping(repo: ClinicalRepository, transcript: Transcript) -> None:
    """Fail closed when a role-dependent workflow lacks a current confirmation."""

    if not requires_speaker_mapping(transcript):
        return
    mapping = repo.get_latest_speaker_mapping(transcript.transcript_id)
    if mapping is None:
        raise _mapping_error("SPEAKER_MAPPING_REQUIRED")
    if mapping.status == "confirmed" and mapping.applied_transcript_version == transcript.version:
        return
    if mapping.status == "draft" and mapping.source_transcript_version == transcript.version:
        raise _mapping_error("SPEAKER_MAPPING_REQUIRED")
    raise _mapping_error("SPEAKER_MAPPING_STALE")
