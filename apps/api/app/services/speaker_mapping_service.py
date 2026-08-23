from __future__ import annotations

from collections import OrderedDict
from typing import TypedDict

from app.schemas.clinical import Transcript
from app.schemas.speaker_mapping import (
    MappingEffectiveStatus,
    SpeakerMapping,
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
