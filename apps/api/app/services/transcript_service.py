from __future__ import annotations

import re
from datetime import datetime, timezone

from app.repositories.mock_repository import MockRepository, new_id
from app.schemas.clinical import (
    AttestationRequest,
    QaIssue,
    QaReport,
    QaStatus,
    ReviewStatus,
    Transcript,
    TranscriptExport,
    TranscriptManualCreate,
    TranscriptMergeRequest,
    TranscriptPatch,
    TranscriptSplitRequest,
    TranscriptUploadCha,
    Utterance,
    AudioFileMetadata,
)
from app.services.cha_service import (
    build_cha_text,
    chat_build_options,
    manual_text_to_utterances,
    parse_cha_document,
    parse_cha_metadata,
    parse_cha_utterances,
)
from app.services.speaker_mapping_service import require_confirmed_mapping

SUPPORTED_LANGUAGE_CODES = {"eng", "tha"}


def create_from_cha(repo: MockRepository, session_id: str, payload: TranscriptUploadCha) -> Transcript:
    session = repo.sessions[session_id]
    if session.transcript_id and not payload.replace_existing:
        return repo.clone(repo.transcripts[session.transcript_id])
    parsed = parse_cha_document(payload.cha_text)
    transcript = Transcript(
        transcript_id=new_id("tr"),
        session_id=session_id,
        case_id=session.case_id,
        source=f"cha_upload:{payload.filename}",
        raw_text=payload.cha_text,
        utterances=parsed.utterances,
        chat_metadata=parsed.metadata,
        orphan_dependent_tiers=parsed.orphan_dependent_tiers,
        malformed_lines=parsed.malformed_lines,
        review_status=ReviewStatus.needs_review,
    )
    return repo.create_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="system",
        audit_action="transcript.upload_cha",
        audit_message="CHA transcript uploaded for therapist review.",
    )


def create_from_manual(repo: MockRepository, session_id: str, payload: TranscriptManualCreate) -> Transcript:
    session = repo.sessions[session_id]
    if session.transcript_id and not payload.replace_existing:
        return repo.clone(repo.transcripts[session.transcript_id])
    utterances = manual_text_to_utterances(payload.text)
    raw_text = build_cha_text(utterances, language="eng" if payload.language.lower().startswith("english") else payload.language)
    transcript = Transcript(
        transcript_id=new_id("tr"),
        session_id=session_id,
        case_id=session.case_id,
        source="manual_entry",
        raw_text=raw_text,
        utterances=utterances,
        review_status=ReviewStatus.needs_review,
    )
    return repo.create_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="system",
        audit_action="transcript.manual",
        audit_message="Manual transcript converted to reviewable CHAT draft.",
    )


def patch_transcript(repo: MockRepository, transcript_id: str, payload: TranscriptPatch) -> Transcript:
    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise KeyError(transcript_id)
    expected_version = transcript.version
    has_server_provenance = transcript.source.startswith("asr_draft:") and any(
        bool((item.temporary_speaker_id or "").strip()) for item in transcript.utterances
    )
    if payload.raw_text is not None and has_server_provenance:
        raise ValueError("Raw CHAT edits are unavailable for this transcript.")
    if payload.utterances is not None:
        submitted = payload.utterances
        if has_server_provenance:
            stored_by_id = {item.utterance_id: item for item in transcript.utterances}
            submitted_ids = [item.utterance_id for item in submitted]
            if (
                len(stored_by_id) != len(transcript.utterances)
                or len(submitted_ids) != len(set(submitted_ids))
                or set(submitted_ids) != set(stored_by_id)
            ):
                raise ValueError("Transcript utterance set does not match the current record.")
            submitted = [
                item.model_copy(
                    deep=True,
                    update={
                        "temporary_speaker_id": stored_by_id[item.utterance_id].temporary_speaker_id,
                        "source_speaker_label": stored_by_id[item.utterance_id].source_speaker_label,
                    },
                )
                for item in submitted
            ]
        transcript.utterances = submitted
        transcript.raw_text = build_cha_text(submitted, **chat_build_options(transcript.raw_text))
    if payload.raw_text is not None:
        transcript.raw_text = payload.raw_text
        transcript.utterances = parse_cha_utterances(payload.raw_text)
    transcript.version += 1
    transcript.qa_status = QaStatus.not_run
    transcript.qa_issues = []
    transcript.therapist_attested = False
    transcript.review_status = ReviewStatus.needs_review
    return repo.update_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        expected_version=expected_version,
        actor_id="system",
        audit_action="transcript.patch",
        audit_message="Transcript edited; prior attestation and outputs are stale.",
    )


def split_utterance(repo: MockRepository, transcript_id: str, payload: TranscriptSplitRequest) -> Transcript:
    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise KeyError(transcript_id)
    utterances = list(transcript.utterances)
    index = next((idx for idx, item in enumerate(utterances) if item.utterance_id == payload.utterance_id), None)
    if index is None:
        raise ValueError("Utterance not found.")
    original = utterances[index]
    if payload.split_at_character >= len(original.text):
        raise ValueError("Split point must be inside the utterance text.")
    left = original.text[: payload.split_at_character].strip()
    right = original.text[payload.split_at_character :].strip()
    if not left or not right:
        raise ValueError("Split point must leave text on both sides.")
    utterances[index : index + 1] = [
        original.model_copy(update={"text": left, "utterance_id": f"{original.utterance_id}_a"}),
        original.model_copy(update={"text": right, "utterance_id": f"{original.utterance_id}_b"}),
    ]
    return _persist_utterance_edit(repo, transcript, utterances, "Transcript utterance split.")


def merge_utterances(repo: MockRepository, transcript_id: str, payload: TranscriptMergeRequest) -> Transcript:
    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise KeyError(transcript_id)
    utterances = list(transcript.utterances)
    first_index = next((idx for idx, item in enumerate(utterances) if item.utterance_id == payload.first_utterance_id), None)
    second_index = next((idx for idx, item in enumerate(utterances) if item.utterance_id == payload.second_utterance_id), None)
    if first_index is None or second_index is None:
        raise ValueError("Utterance not found.")
    if second_index != first_index + 1:
        raise ValueError("Only adjacent utterances can be merged.")
    first = utterances[first_index]
    second = utterances[second_index]
    if str(first.speaker).upper() != str(second.speaker).upper():
        raise ValueError("Only utterances with the same speaker can be merged.")
    if (first.temporary_speaker_id or "").strip() != (second.temporary_speaker_id or "").strip():
        raise ValueError("Only utterances from the same temporary speaker can be merged.")
    merged = first.model_copy(
        update={
            "text": f"{first.text.rstrip()} {second.text.lstrip()}".strip(),
            "end_ms": second.end_ms or first.end_ms,
            "unintelligible": first.unintelligible or second.unintelligible,
            "notes": "; ".join(item for item in [first.notes, second.notes] if item),
        }
    )
    utterances[first_index : second_index + 1] = [merged]
    return _persist_utterance_edit(repo, transcript, utterances, "Transcript utterances merged.")


def _persist_utterance_edit(
    repo: MockRepository,
    transcript: Transcript,
    utterances: list[Utterance],
    audit_message: str,
) -> Transcript:
    expected_version = transcript.version
    transcript.utterances = utterances
    transcript.raw_text = build_cha_text(utterances, **chat_build_options(transcript.raw_text))
    transcript.version += 1
    transcript.qa_status = QaStatus.not_run
    transcript.qa_issues = []
    transcript.therapist_attested = False
    transcript.attestation_reason = ""
    transcript.review_status = ReviewStatus.needs_review
    return repo.update_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        expected_version=expected_version,
        actor_id="system",
        audit_action="transcript.patch",
        audit_message=audit_message,
    )


def export_cha(repo: MockRepository, transcript_id: str) -> TranscriptExport:
    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise KeyError(transcript_id)
    require_confirmed_mapping(repo, transcript)
    options = chat_build_options(transcript.raw_text)
    options["media_name"] = linked_media_name(repo, transcript.session_id) or options.get("media_name")
    cha_text = build_cha_text(transcript.utterances, **options)
    return TranscriptExport(
        transcript_id=transcript_id,
        filename=f"{transcript_id}_reviewed.cha",
        cha_text=cha_text,
    )


def linked_media_name(repo: MockRepository, session_id: str) -> str | None:
    linked_audio = [audio_file for audio_file in repo.audio_files.values() if audio_file.session_id == session_id and audio_file.retained]
    if not linked_audio:
        return None
    audio_file = sorted(linked_audio, key=lambda item: item.created_at)[-1]
    return f"{session_id}_{audio_file.audio_file_id}"


def run_qa(repo: MockRepository, transcript_id: str) -> QaReport:
    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise KeyError(transcript_id)
    require_confirmed_mapping(repo, transcript)
    expected_version = transcript.version
    linked_audio = [audio_file for audio_file in repo.audio_files.values() if audio_file.session_id == transcript.session_id and audio_file.retained]
    issues = qa_issues(transcript, linked_audio)
    has_error = any(issue.severity == "error" for issue in issues)
    has_warning = any(issue.severity == "warning" for issue in issues)
    status = QaStatus.fail if has_error else QaStatus.warning if has_warning else QaStatus.pass_
    transcript.qa_status = status
    transcript.qa_issues = issues
    repo.update_transcript(
        transcript,
        session_status=repo.sessions[transcript.session_id].status,
        expected_version=expected_version,
        actor_id="system",
        audit_action="transcript.qa",
        audit_message=f"Transcript QA completed with status {status.value}.",
        invalidate_downstream=False,
    )
    return QaReport(
        transcript_id=transcript_id,
        overall_status=status,
        issues=issues,
        can_extract_features=status == QaStatus.pass_,
    )


def attest(
    repo: MockRepository,
    transcript_id: str,
    payload: AttestationRequest,
    *,
    actor_id: str = "system",
    attested_by: str | None = None,
) -> Transcript:
    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise KeyError(transcript_id)
    require_confirmed_mapping(repo, transcript)
    attested_by_name = (attested_by or payload.attested_by or "Demo Therapist").strip()
    if transcript.qa_status == QaStatus.not_run:
        run_qa(repo, transcript_id)
        transcript = repo.get_transcript(transcript_id)
        if transcript is None:
            raise KeyError(transcript_id)
    if transcript.qa_status == QaStatus.fail:
        if not payload.override_qa_failure or not (payload.reason and payload.reason.strip()):
            raise ValueError("Transcript failed QA; override requires therapist reason.")
        # Record override metadata
        transcript.chat_metadata["qa_override"] = {
            "overridden_by": attested_by_name,
            "reason": payload.reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        transcript.attestation_reason = f"[Override] {payload.reason}"
    else:
        transcript.attestation_reason = payload.reason
    expected_version = transcript.version
    transcript.therapist_attested = True
    transcript.review_status = ReviewStatus.attested
    return repo.update_transcript(
        transcript,
        session_status=ReviewStatus.attested,
        expected_version=expected_version,
        actor_id=actor_id,
        audit_action="transcript.attest",
        audit_message="Therapist attested transcript quality.",
        invalidate_downstream=False,
    )


def qa_issues(transcript: Transcript, audio_files: list[AudioFileMetadata] | None = None) -> list[QaIssue]:
    text = transcript.raw_text or ""
    utterances = transcript.utterances
    issues: list[QaIssue] = []
    
    headers = parse_cha_metadata(text)
    
    # 1. Header checks
    if "@Begin" not in text:
        issues.append(QaIssue(severity="error", code="MISSING_BEGIN", message="Missing @Begin header.", recommended_action="Upload or rebuild a CHAT transcript.", blocking=True))
    if "@End" not in text:
        issues.append(QaIssue(severity="error", code="MISSING_END", message="Missing @End footer.", recommended_action="Upload or rebuild a CHAT transcript.", blocking=True))
    if "@Participants" not in headers:
        issues.append(QaIssue(severity="warning", code="MISSING_PARTICIPANTS", message="Missing CHAT participants metadata.", recommended_action="Add participants metadata before export.", blocking=False))
    if "@Languages" not in headers:
        issues.append(QaIssue(severity="warning", code="MISSING_LANGUAGE", message="Missing language metadata.", recommended_action="Add session language metadata.", blocking=False))

    # 2. Speaker checks
    from app.services.cha_service import parse_participants
    participants = parse_participants(headers.get("@Participants", []))
    declared_codes = {item["code"] for item in participants}
    allowed_codes = declared_codes | {"CHI", "UNK"}
    
    for utterance in utterances:
        speaker = str(utterance.speaker).upper()
        if speaker not in allowed_codes:
            issues.append(QaIssue(
                severity="error",
                code="UNKNOWN_SPEAKER",
                message=f"Speaker {speaker} is not declared in @Participants.",
                recommended_action=f"Add {speaker} to the @Participants header.",
                line_id=utterance.utterance_id,
                blocking=True
            ))
            
    if not any(str(item.speaker).upper() == "CHI" for item in utterances):
        issues.append(QaIssue(severity="error", code="MISSING_CHILD_SPEAKER", message="No child speaker lines were detected.", recommended_action="Mark child utterances with CHI before extraction.", blocking=True))
        
    child = [item for item in utterances if str(item.speaker).upper() == "CHI"]
    if len(child) < 3:
        issues.append(QaIssue(severity="warning", code="TOO_FEW_CHILD_UTTERANCES", message="The child sample has fewer than 3 utterances.", recommended_action="Review whether the session sample is long enough.", blocking=False))
        
    if len(" ".join(item.text for item in utterances).split()) < 20:
        issues.append(QaIssue(severity="warning", code="SHORT_TRANSCRIPT", message="The transcript is short.", recommended_action="Confirm this is the complete session excerpt.", blocking=False))
        
    unknown_ratio = sum(1 for item in utterances if str(item.speaker).upper() == "UNK") / len(utterances) if utterances else 1
    if unknown_ratio > 0.25:
        issues.append(QaIssue(severity="warning", code="HIGH_UNKNOWN_SPEAKER_RATIO", message="More than 25% of utterances have unknown speaker labels.", recommended_action="Correct speaker labels before relying on features.", blocking=False))
        
    unintelligible_ratio = sum(1 for item in utterances if item.unintelligible or re.search(r"\b(?:xxx|yyy|www)\b", item.text, re.I)) / len(utterances) if utterances else 1
    if unintelligible_ratio > 0.2:
        issues.append(QaIssue(severity="warning", code="HIGH_UNINTELLIGIBLE_RATIO", message="More than 20% of utterances include unintelligible markers.", recommended_action="Review uncertain segments and add notes.", blocking=False))

    # 3. Malformed lines containing speaker-like text
    for ml in getattr(transcript, "malformed_lines", []):
        raw_line = ml.get("raw_text", "")
        line_num = ml.get("line_number", 0)
        stripped = raw_line.strip()
        is_speaker_like = stripped.startswith("*") or bool(re.match(r"^[A-Za-z0-9_]+:\s*", stripped))
        if is_speaker_like:
            issues.append(QaIssue(
                severity="error",
                code="MALFORMED_LINE_SPEAKER_LIKE",
                message=f"Line {line_num} contains speaker-like pattern but is malformed: '{stripped}'",
                recommended_action="Ensure speaker lines start with asterisk, code, colon, and space (e.g. *CHI: ).",
                blocking=True
            ))

    # 4. Dependent tiers checks
    all_dt_tiers = set()
    for utterance in utterances:
        for dt in getattr(utterance, "dependent_tiers", []):
            all_dt_tiers.add(dt.tier)
    for orphan in getattr(transcript, "orphan_dependent_tiers", []):
        all_dt_tiers.add(orphan.tier)
        
    for tier in all_dt_tiers:
        if tier in {"%mor", "%gra", "%pho", "%gla", "%xpho", "%err"}:
            issues.append(QaIssue(
                severity="warning",
                code="UNSUPPORTED_DEPENDENT_TIER",
                message=f"Dependent tier {tier} is preserved but not analyzed by BasicFeatureProvider.",
                recommended_action="Information only. Tier content will be preserved on export.",
                blocking=False
            ))

    # 5. Timestamp checks
    last_end_ms = -1
    for utterance in utterances:
        start = utterance.start_ms
        end = utterance.end_ms
        if start is not None and end is not None:
            if start > end:
                issues.append(QaIssue(
                    severity="error",
                    code="INVALID_TIMESTAMP_RANGE",
                    message=f"Utterance {utterance.utterance_id} has start timestamp ({start}ms) greater than end ({end}ms).",
                    recommended_action="Ensure start timestamp is less than or equal to end timestamp.",
                    line_id=utterance.utterance_id,
                    blocking=True
                ))
            elif start < last_end_ms:
                issues.append(QaIssue(
                    severity="error",
                    code="TIMESTAMP_OVERLAP",
                    message=f"Utterance {utterance.utterance_id} start timestamp ({start}ms) overlaps with previous utterance end ({last_end_ms}ms).",
                    recommended_action="Correct timestamps to ensure strict chronological order.",
                    line_id=utterance.utterance_id,
                    blocking=True
                ))
            last_end_ms = end
            
    audio_duration_seconds = max((item.duration_seconds or 0 for item in audio_files or []), default=0)
    transcript_end_ms = max((item.end_ms or 0 for item in utterances), default=0)
    if audio_duration_seconds:
        # If audio exists, check for missing timestamps
        has_missing_timestamps = any(item.start_ms is None or item.end_ms is None for item in utterances)
        if has_missing_timestamps:
            issues.append(QaIssue(
                severity="warning",
                code="MISSING_TIMESTAMPS",
                message="Some utterances are missing audio synchronization timestamps.",
                recommended_action="Align utterances with audio timeline for synchronization.",
                blocking=False
            ))
        if transcript_end_ms:
            coverage = transcript_end_ms / (audio_duration_seconds * 1000)
            if coverage < 0.5:
                issues.append(QaIssue(
                    severity="warning",
                    code="LOW_TRANSCRIPT_COVERAGE",
                    message="Transcript timestamps cover less than half of the linked audio duration.",
                    recommended_action="Confirm the transcript covers the intended audio segment before extraction.",
                    blocking=False
                ))

    # 6. Empty utterances
    for utterance in utterances:
        if not utterance.text.strip():
            issues.append(QaIssue(
                severity="error",
                code="EMPTY_UTTERANCE",
                message=f"Utterance {utterance.utterance_id} by speaker {utterance.speaker} is empty.",
                recommended_action="Provide text content or remove the empty utterance.",
                line_id=utterance.utterance_id,
                blocking=True
            ))

    unsupported_languages = unsupported_language_codes(headers.get("@Languages", []))
    if unsupported_languages:
        issues.append(QaIssue(
            severity="warning",
            code="UNSUPPORTED_LANGUAGE",
            message=f"Unsupported language metadata detected: {', '.join(unsupported_languages)}.",
            recommended_action="Use English or Thai metadata for supported local QA, or document interpretation limits.",
            blocking=False
        ))
    if re.search(r"[ก-๙]", text) and "tha" not in " ".join(headers.get("@Languages", [])).lower():
        issues.append(QaIssue(severity="warning", code="CODE_SWITCHING_WARNING", message="Thai or mixed-language text detected without Thai language metadata.", recommended_action="Review language metadata and interpretation limits.", blocking=False))
        
    return issues


def unsupported_language_codes(language_headers: list[str]) -> list[str]:
    codes: list[str] = []
    for header in language_headers:
        for raw_code in re.split(r"[,;\s]+", header.lower()):
            code = raw_code.strip()
            if not code:
                continue
            codes.append(code)
    return sorted({code for code in codes if code not in SUPPORTED_LANGUAGE_CODES})
