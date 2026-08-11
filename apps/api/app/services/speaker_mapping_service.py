from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.core.security import CurrentUser
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    QaIssue,
    SpeakerMappingConfirmRequest,
    SpeakerMappingDraftRequest,
    SpeakerMappingResponse,
    SpeakerMappingReviewEntry,
    Transcript,
)
from app.schemas.speech_pipeline import MappingStatus, ReviewedSpeakerMapping, SpeakerMappingEntry


REQUIRED_ROLE_CODES = {
    "target_child": "CHI",
    "therapist": "THE",
}


def get_mapping(repo: MockRepository, transcript_id: str) -> SpeakerMappingResponse:
    transcript = repo.transcripts[transcript_id]
    latest = _latest_mapping(repo, transcript_id)
    if latest is None:
        return SpeakerMappingResponse(
            transcript_id=transcript_id,
            transcript_version=transcript.version,
            status="draft",
            entries=_initial_entries(transcript),
        )
    return _response_from_record(
        latest,
        issues=_mapping_status_issues(repo, transcript),
    )


def save_mapping_draft(
    repo: MockRepository,
    transcript_id: str,
    payload: SpeakerMappingDraftRequest,
) -> SpeakerMappingResponse:
    transcript = repo.transcripts[transcript_id]
    _assert_transcript_version(transcript, payload.expected_transcript_version)
    latest = _latest_mapping(repo, transcript_id)
    if latest is not None and payload.expected_mapping_version != latest.mapping_version:
        raise ValueError("SPEAKER_MAPPING_STALE: mapping version does not match the current draft.")
    entries = _normalize_requested_entries(transcript, payload.entries)
    mapping_id = latest.mapping_id if latest is not None else f"mapping_{uuid4().hex[:12]}"
    mapping_version = 1 if latest is None else latest.mapping_version + 1
    record = ReviewedSpeakerMapping(
        organization_id=transcript.organization_id,
        session_id=transcript.session_id,
        mapping_id=mapping_id,
        mapping_version=mapping_version,
        transcript_id=transcript_id,
        transcript_version=transcript.version,
        entries=entries,
        confirmed_by_user_id="",
        confirmed_by_role="",
        confirmed_at=datetime.now(timezone.utc),
        status=MappingStatus.draft,
    )
    return _response_from_record(repo.create_speaker_mapping(record))


def confirm_mapping(
    repo: MockRepository,
    transcript_id: str,
    payload: SpeakerMappingConfirmRequest,
    user: CurrentUser,
) -> SpeakerMappingResponse:
    transcript = repo.transcripts[transcript_id]
    _assert_transcript_version(transcript, payload.expected_transcript_version)
    draft = _latest_mapping(repo, transcript_id)
    if draft is None or draft.mapping_version != payload.expected_mapping_version:
        raise ValueError("SPEAKER_MAPPING_STALE: mapping version does not match the current draft.")
    issues = validate_mapping_for_confirmation(transcript, draft.entries)
    if issues:
        raise ValueError(f"{issues[0].code}: {issues[0].message}")

    _apply_reviewed_speakers(transcript, draft.entries)
    transcript.raw_text = _apply_reviewed_speakers_to_raw_text(transcript.raw_text, draft.entries)
    transcript = repo.update_transcript(
        transcript,
        session_status=repo.sessions[transcript.session_id].status,
        expected_version=transcript.version,
        actor_id=user.user_id,
        audit_action="transcript.speaker_mapping_apply",
        audit_message="Therapist-confirmed speaker mapping applied to transcript speakers.",
        invalidate_downstream=False,
    )
    updated_entries = [
        entry.model_copy(update={
            "temporary_speaker_id": entry.confirmed_chat_code or entry.temporary_speaker_id
        }) if entry.confirmed_chat_code else entry
        for entry in draft.entries
    ]
    confirmed = ReviewedSpeakerMapping(
        organization_id=draft.organization_id,
        session_id=draft.session_id,
        mapping_id=draft.mapping_id,
        mapping_version=draft.mapping_version + 1,
        transcript_id=draft.transcript_id,
        transcript_version=transcript.version,
        entries=draft.entries,
        confirmed_by_user_id=user.user_id,
        confirmed_by_role=user.role,
        confirmed_at=datetime.now(timezone.utc),
        status=MappingStatus.confirmed,
    )
    return _response_from_record(repo.create_speaker_mapping(confirmed))


def require_confirmed_mapping(repo: MockRepository, transcript_id: str) -> ReviewedSpeakerMapping | None:
    transcript = repo.transcripts[transcript_id]
    if not requires_speaker_mapping(transcript):
        return None
    mapping = repo.get_current_speaker_mapping(transcript_id)
    if mapping is None:
        latest = _latest_mapping(repo, transcript_id)
        code = "SPEAKER_MAPPING_STALE" if latest is not None and latest.status is MappingStatus.stale else "SPEAKER_MAPPING_REQUIRED"
        raise ValueError(f"{code}: therapist-confirmed speaker mapping is required.")
    if mapping.transcript_version != transcript.version:
        raise ValueError("SPEAKER_MAPPING_STALE: mapping belongs to an older transcript version.")
    issues = validate_mapping_for_confirmation(transcript, mapping.entries)
    if issues:
        raise ValueError(f"{issues[0].code}: {issues[0].message}")
    return mapping


def mapping_qa_issues(repo: MockRepository, transcript: Transcript) -> list[QaIssue]:
    if not requires_speaker_mapping(transcript):
        return []
    latest = _latest_mapping(repo, transcript.transcript_id)
    if latest is None:
        return [_issue(
            "SPEAKER_MAPPING_REQUIRED",
            "Therapist-confirmed speaker mapping is required before QA can pass.",
        )]
    if latest.status is MappingStatus.stale or latest.transcript_version != transcript.version:
        return [_issue(
            "SPEAKER_MAPPING_STALE",
            "Speaker mapping belongs to an older transcript version.",
        )]
    if latest.status is not MappingStatus.confirmed:
        return [_issue(
            "SPEAKER_MAPPING_INCOMPLETE",
            "Speaker mapping draft must be confirmed by the therapist before QA can pass.",
        )]
    return validate_mapping_for_confirmation(transcript, latest.entries)


def requires_speaker_mapping(transcript: Transcript) -> bool:
    if transcript.source.startswith("asr_draft:") or transcript.raw_speaker_labels:
        return True
    return any(
        utterance.temporary_speaker_id
        or str(utterance.speaker).upper().startswith("SPK_")
        or str(utterance.speaker).upper() == "UNK"
        for utterance in transcript.utterances
    )


def validate_mapping_for_confirmation(
    transcript: Transcript,
    entries: list[SpeakerMappingEntry],
) -> list[QaIssue]:
    issues: list[QaIssue] = []
    inventory = _speaker_inventory(transcript)
    entry_by_temp = {entry.temporary_speaker_id: entry for entry in entries}
    missing = sorted(set(inventory) - set(entry_by_temp))
    if missing:
        issues.append(_issue(
            "SPEAKER_MAPPING_INCOMPLETE",
            f"Speaker mapping is missing temporary speaker(s): {', '.join(missing)}.",
            field="temporary_speaker_id",
        ))
    for temporary_speaker_id, entry in entry_by_temp.items():
        if temporary_speaker_id not in inventory:
            issues.append(_issue(
                "SPEAKER_MAPPING_UNKNOWN_SPEAKER",
                f"Temporary speaker {temporary_speaker_id} is not present in the transcript.",
                field="temporary_speaker_id",
            ))
        if entry.disposition != "merged" and not entry.confirmed_chat_code:
            issues.append(_issue(
                "SPEAKER_MAPPING_INCOMPLETE",
                f"Temporary speaker {temporary_speaker_id} has no confirmed CHAT code.",
                field="confirmed_chat_code",
            ))
        canonical_affected_segments = set(inventory.get(temporary_speaker_id, []))
        unknown_segments = sorted(set(entry.affected_utterance_ids) - canonical_affected_segments)
        if unknown_segments:
            issues.append(_issue(
                "SPEAKER_MAPPING_UNKNOWN_SEGMENT",
                f"Temporary speaker {temporary_speaker_id} references unknown segment(s): {', '.join(unknown_segments)}.",
                field="affected_utterance_ids",
            ))
        unknown_reviewed_segments = sorted(set(entry.reviewed_utterance_ids) - canonical_affected_segments)
        if unknown_reviewed_segments:
            issues.append(_issue(
                "SPEAKER_MAPPING_UNKNOWN_SEGMENT",
                f"Temporary speaker {temporary_speaker_id} marks unassigned segment(s) reviewed: {', '.join(unknown_reviewed_segments)}.",
                field="reviewed_utterance_ids",
            ))
        unreviewed_segments = sorted(canonical_affected_segments - set(entry.reviewed_utterance_ids))
        if unreviewed_segments:
            issues.append(_issue(
                "SPEAKER_MAPPING_SEGMENTS_UNREVIEWED",
                f"Temporary speaker {temporary_speaker_id} has unreviewed segment(s): {', '.join(unreviewed_segments)}.",
                field="reviewed_utterance_ids",
            ))
        if entry.disposition == "merged":
            if not entry.merged_into_temporary_speaker_id:
                issues.append(_issue(
                    "SPEAKER_MAPPING_MERGE_TARGET_REQUIRED",
                    f"Temporary speaker {temporary_speaker_id} is marked merged but has no merge target.",
                    field="merged_into_temporary_speaker_id",
                ))
            elif entry.merged_into_temporary_speaker_id == temporary_speaker_id:
                issues.append(_issue(
                    "SPEAKER_MAPPING_MERGE_TARGET_REQUIRED",
                    f"Temporary speaker {temporary_speaker_id} cannot merge into itself.",
                    field="merged_into_temporary_speaker_id",
                ))
            elif entry.merged_into_temporary_speaker_id not in entry_by_temp:
                issues.append(_issue(
                    "SPEAKER_MAPPING_UNKNOWN_SPEAKER",
                    f"Temporary speaker {temporary_speaker_id} references unknown merge target {entry.merged_into_temporary_speaker_id}.",
                    field="merged_into_temporary_speaker_id",
                ))
            elif entry_by_temp[entry.merged_into_temporary_speaker_id].disposition == "merged":
                issues.append(_issue(
                    "SPEAKER_MAPPING_MERGE_TARGET_REQUIRED",
                    f"Temporary speaker {temporary_speaker_id} merge target cannot itself be merged.",
                    field="merged_into_temporary_speaker_id",
                ))

    for role, chat_code in REQUIRED_ROLE_CODES.items():
        role_entries = [
            entry
            for entry in entries
            if entry.participant_role == role and entry.disposition != "merged"
        ]
        if not role_entries:
            issues.append(_issue(
                "SPEAKER_MAPPING_INCOMPLETE",
                f"Required participant role {role} is unmapped.",
                field="participant_role",
            ))
            continue
        if len(role_entries) > 1:
            issues.append(_issue(
                "SPEAKER_MAPPING_AMBIGUOUS_ROLE",
                f"Multiple speakers map to required participant role {role} without an explicit merge.",
                field="participant_role",
            ))
        for entry in role_entries:
            if entry.confirmed_chat_code != chat_code:
                issues.append(_issue(
                    "SPEAKER_MAPPING_AMBIGUOUS_ROLE",
                    f"Role {role} must use CHAT code {chat_code}.",
                    field="confirmed_chat_code",
                ))
    return issues


def _initial_entries(transcript: Transcript) -> list[SpeakerMappingReviewEntry]:
    raw_by_temp = _raw_metadata_by_temporary_speaker(transcript)
    entries = []
    for temporary_speaker_id, utterance_ids in _speaker_inventory(transcript).items():
        raw = raw_by_temp.get(temporary_speaker_id, {})
        entries.append(SpeakerMappingReviewEntry(
            temporary_speaker_id=temporary_speaker_id,
            participant_role="unknown",
            disposition="unknown",
            affected_utterance_ids=utterance_ids,
            source_speaker_label=raw.get("source_speaker_label"),
            source_provider=raw.get("source_provider"),
            source_provider_metadata=raw.get("source_provider_metadata", {}),
        ))
    return entries


def _normalize_requested_entries(
    transcript: Transcript,
    requested: list[SpeakerMappingReviewEntry],
) -> list[SpeakerMappingEntry]:
    issues = validate_mapping_for_confirmation(
        transcript,
        [
            SpeakerMappingEntry(**entry.model_dump(exclude={
                "source_speaker_label",
                "source_provider",
                "source_provider_metadata",
            }))
            for entry in requested
        ],
    )
    unknown = next((issue for issue in issues if issue.code in {"SPEAKER_MAPPING_UNKNOWN_SPEAKER", "SPEAKER_MAPPING_UNKNOWN_SEGMENT"}), None)
    if unknown is not None:
        raise ValueError(f"{unknown.code}: {unknown.message}")
    raw_by_temp = _raw_metadata_by_temporary_speaker(transcript)
    entries = []
    for entry in requested:
        raw = raw_by_temp.get(entry.temporary_speaker_id, {})
        payload = entry.model_dump()
        payload.update({
            "source_speaker_label": raw.get("source_speaker_label"),
            "source_provider": raw.get("source_provider"),
            "source_provider_metadata": raw.get("source_provider_metadata", {}),
            "reviewed_utterance_ids": entry.reviewed_utterance_ids,
        })
        entries.append(SpeakerMappingEntry(**payload))
    return entries


def _apply_reviewed_speakers(transcript: Transcript, entries: list[SpeakerMappingEntry]) -> None:
    entry_by_temp = {entry.temporary_speaker_id: entry for entry in entries}
    for utterance in transcript.utterances:
        temporary_speaker_id = _temporary_speaker_id(utterance)
        utterance.temporary_speaker_id = temporary_speaker_id
        entry = entry_by_temp.get(temporary_speaker_id)
        if entry is None:
            continue
        if entry.disposition == "merged" and entry.merged_into_temporary_speaker_id:
            entry = entry_by_temp.get(entry.merged_into_temporary_speaker_id, entry)
        utterance.speaker = entry.confirmed_chat_code or "UNK"


def _response_from_record(
    record: ReviewedSpeakerMapping,
    *,
    issues: list[QaIssue] | None = None,
) -> SpeakerMappingResponse:
    return SpeakerMappingResponse(
        transcript_id=record.transcript_id,
        transcript_version=record.transcript_version,
        mapping_id=record.mapping_id,
        mapping_version=record.mapping_version,
        status=record.status.value,
        entries=[SpeakerMappingReviewEntry(**entry.model_dump()) for entry in record.entries],
        issues=issues or [],
        confirmed_by_user_id=record.confirmed_by_user_id or None,
        confirmed_by_role=record.confirmed_by_role or None,
        confirmed_at=record.confirmed_at if record.status is MappingStatus.confirmed else None,
    )


def _latest_mapping(repo: MockRepository, transcript_id: str) -> ReviewedSpeakerMapping | None:
    history = repo.list_speaker_mapping_history(transcript_id)
    if not history:
        return None
    return max(history, key=lambda item: item.mapping_version)


def _mapping_status_issues(repo: MockRepository, transcript: Transcript) -> list[QaIssue]:
    try:
        return mapping_qa_issues(repo, transcript)
    except KeyError:
        return [_issue("SPEAKER_MAPPING_REQUIRED", "Therapist-confirmed speaker mapping is required.")]


def _speaker_inventory(transcript: Transcript) -> dict[str, list[str]]:
    inventory: dict[str, list[str]] = {}
    for utterance in transcript.utterances:
        temporary_speaker_id = _temporary_speaker_id(utterance)
        inventory.setdefault(temporary_speaker_id, []).append(utterance.utterance_id)
    return inventory


def _raw_metadata_by_temporary_speaker(transcript: Transcript) -> dict[str, dict[str, object]]:
    provider = None
    clusters = {}
    if isinstance(transcript.asr_provenance, dict):
        diarization = transcript.asr_provenance.get("diarization")
        if isinstance(diarization, dict):
            provider = diarization.get("provider")
            raw_clusters = diarization.get("clusters")
            if isinstance(raw_clusters, dict):
                clusters = {
                    str(key): value
                    for key, value in raw_clusters.items()
                    if isinstance(value, dict)
                }
        provider = provider or transcript.asr_provenance.get("provider_id")
    raw_by_temp: dict[str, dict[str, object]] = {}
    for utterance in transcript.utterances:
        temporary_speaker_id = _temporary_speaker_id(utterance)
        cluster = clusters.get(temporary_speaker_id, {})
        raw_by_temp.setdefault(temporary_speaker_id, {
            "source_speaker_label": utterance.source_speaker_label or cluster.get("source_speaker_label") or temporary_speaker_id,
            "source_provider": provider,
            "source_provider_metadata": cluster,
        })
    return raw_by_temp


def _temporary_speaker_id(utterance) -> str:
    return str(utterance.temporary_speaker_id or utterance.speaker or "UNK").upper()


def _assert_transcript_version(transcript: Transcript, expected_version: int) -> None:
    if transcript.version != expected_version:
        raise ValueError("SPEAKER_MAPPING_STALE: mapping request targets an older transcript version.")


def _apply_reviewed_speakers_to_raw_text(raw_text: str, entries: list[SpeakerMappingEntry]) -> str:
    replacement_by_temp: dict[str, str] = {}
    entry_by_temp = {entry.temporary_speaker_id: entry for entry in entries}
    for entry in entries:
        resolved = entry
        if entry.disposition == "merged" and entry.merged_into_temporary_speaker_id:
            resolved = entry_by_temp.get(entry.merged_into_temporary_speaker_id, entry)
        replacement_by_temp[entry.temporary_speaker_id.upper()] = resolved.confirmed_chat_code or "UNK"
    lines = []
    for line in raw_text.splitlines():
        if line.startswith("@Participants:"):
            parts = line[len("@Participants:"):].split(",")
            new_parts = []
            for p in parts:
                p_strip = p.strip()
                if p_strip:
                    tokens = p_strip.split(maxsplit=2)
                    if tokens:
                        code = tokens[0].upper()
                        replacement = replacement_by_temp.get(code, tokens[0])
                        tokens[0] = replacement
                        new_parts.append(" ".join(tokens))
                else:
                    new_parts.append(p)
            line = "@Participants:\t" + ", ".join(new_parts)
        elif line.startswith("*") and ":" in line:
            speaker, rest = line[1:].split(":", 1)
            replacement = replacement_by_temp.get(speaker.strip().upper())
            if replacement:
                line = f"*{replacement}:{rest}"
        lines.append(line)
    return "\n".join(lines)


def _issue(code: str, message: str, *, field: str | None = None) -> QaIssue:
    return QaIssue(
        code=code,
        severity="error",
        message=message,
        field=field,
        blocking=True,
        validation_version="speech-qa-v1.7.0",
        recommended_action="Review and confirm the participant-to-speaker mapping.",
    )
