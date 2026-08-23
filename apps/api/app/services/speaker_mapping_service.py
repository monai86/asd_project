from __future__ import annotations

from collections import OrderedDict
from typing import TypedDict

from app.schemas.clinical import Transcript
from app.repositories.base import ClinicalRepository, TranscriptVersionConflictError
from app.schemas.speaker_mapping import (
    MappingEffectiveStatus,
    SpeakerMapping,
    SpeakerMappingDraftUpdate,
    SpeakerMappingEntry,
    SpeakerMappingResponse,
)


class _SpeakerGroup(TypedDict):
    source_speaker_label: str | None
    affected_utterance_ids: list[str]


def requires_speaker_mapping(transcript: Transcript) -> bool:
    """Return whether a real draft-ASR transcript needs speaker mapping."""

    return transcript.source.startswith("asr_draft:") and any(
        bool((utterance.temporary_speaker_id or "").strip())
        for utterance in transcript.utterances
    )


def derive_mapping_draft(transcript: Transcript) -> SpeakerMappingResponse:
    """Derive an unsaved, server-owned mapping draft from a transcript."""

    required = requires_speaker_mapping(transcript)
    provider_id = transcript.source.split(":", 1)[1].strip() if ":" in transcript.source else ""
    provider_metadata = {"provider_id": provider_id} if required and provider_id else {}
    grouped: OrderedDict[str, _SpeakerGroup] = OrderedDict()

    for utterance in transcript.utterances:
        temporary_id = (utterance.temporary_speaker_id or "").strip()
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
    derived = derive_mapping_draft(transcript)
    if not derived.required:
        return derived

    mapping = repo.get_latest_speaker_mapping(transcript_id)
    return _mapping_response(transcript, mapping) if mapping is not None else derived


def save_mapping_draft(
    repo: ClinicalRepository,
    transcript_id: str,
    update: SpeakerMappingDraftUpdate,
    *,
    actor_id: str = "system",
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
    editable_entries = {entry.temporary_speaker_id: entry for entry in update.entries}
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
    )
    return _mapping_response(transcript, saved)
