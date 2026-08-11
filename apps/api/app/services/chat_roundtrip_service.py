"""Semantic and deterministic verification for v1.7.0 CHAT exports."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Callable

from app.services.chat_subset import (
    CHAT_PARSER_VERSION,
    CHAT_SERIALIZER_VERSION,
    CHAT_SUBSET_VERSION,
    CanonicalChatDocument,
    compare_semantics,
    parse_chat,
    semantic_checksum,
    serialize_chat,
)
from app.schemas.speech_pipeline import ChatRoundTripError
from app.schemas.speech_pipeline import (
    ArtifactStatus,
    AsrProfile,
    AsrProvenance,
    ChatExport,
    ChatSemanticRoundTripResult,
    RoundTripStatus,
)
from app.repositories.mock_repository import new_id
from app.services import speaker_mapping_service
from app.services.cha_service import parse_cha_metadata, parse_ids, parse_media, parse_participants


@dataclass(frozen=True)
class ChatRoundTripVerification:
    status: str
    export_a: str
    export_b: str
    input_semantic_checksum_sha256: str
    output_semantic_checksum_sha256: str | None
    export_a_checksum_sha256: str
    export_b_checksum_sha256: str
    errors: tuple[ChatRoundTripError, ...]
    parser_version: str = CHAT_PARSER_VERSION
    serializer_version: str = CHAT_SERIALIZER_VERSION
    subset_version: str = CHAT_SUBSET_VERSION


def verify_chat_round_trip(
    document: CanonicalChatDocument,
    *,
    mutate_export: Callable[[str], str] | None = None,
) -> ChatRoundTripVerification:
    errors: list[ChatRoundTripError] = []
    for extension in document.opaque_extensions:
        if extension.action == "unsupported_blocking":
            errors.append(
                ChatRoundTripError(
                    code="CHAT_UNSUPPORTED_CONTENT_BLOCKING",
                    field_or_tier=extension.key,
                    utterance_or_segment_id=extension.owner_utterance_id,
                    expected="supported or preserved opaque content",
                    actual=extension.content,
                    severity="error",
                    parser_version=CHAT_PARSER_VERSION,
                    serializer_version=CHAT_SERIALIZER_VERSION,
                    subset_version=CHAT_SUBSET_VERSION,
                )
            )
    export_a = serialize_chat(document)
    if mutate_export is not None:
        export_a = mutate_export(export_a)
    parsed_a = parse_chat(export_a)
    errors.extend(parsed_a.errors)
    errors.extend(compare_semantics(document, parsed_a.document))
    export_b = serialize_chat(parsed_a.document)
    parsed_b = parse_chat(export_b)
    errors.extend(parsed_b.errors)
    errors.extend(compare_semantics(parsed_a.document, parsed_b.document))
    export_a_checksum = sha256(export_a.encode("utf-8")).hexdigest()
    export_b_checksum = sha256(export_b.encode("utf-8")).hexdigest()
    output_checksum = semantic_checksum(parsed_a.document)
    if export_a_checksum != export_b_checksum:
        errors.append(
            ChatRoundTripError(
                code="CHAT_DETERMINISTIC_BYTES_CHANGED",
                field_or_tier="serialized_bytes",
                utterance_or_segment_id=None,
                expected=export_a_checksum,
                actual=export_b_checksum,
                severity="error",
                parser_version=CHAT_PARSER_VERSION,
                serializer_version=CHAT_SERIALIZER_VERSION,
                subset_version=CHAT_SUBSET_VERSION,
            )
        )
    input_checksum = semantic_checksum(document)
    if input_checksum != output_checksum:
        errors.append(
            ChatRoundTripError(
                code="CHAT_SEMANTIC_CHECKSUM_CHANGED",
                field_or_tier="canonical_document",
                utterance_or_segment_id=None,
                expected=input_checksum,
                actual=output_checksum,
                severity="error",
                parser_version=CHAT_PARSER_VERSION,
                serializer_version=CHAT_SERIALIZER_VERSION,
                subset_version=CHAT_SUBSET_VERSION,
            )
        )
    return ChatRoundTripVerification(
        status="verified" if not errors else "failed",
        export_a=export_a,
        export_b=export_b,
        input_semantic_checksum_sha256=input_checksum,
        output_semantic_checksum_sha256=output_checksum,
        export_a_checksum_sha256=export_a_checksum,
        export_b_checksum_sha256=export_b_checksum,
        errors=tuple(errors),
    )


def canonical_document_from_repo(repo, transcript_id: str) -> CanonicalChatDocument:
    """Build the canonical reviewed model from current transcript lineage."""

    transcript = repo.transcripts[transcript_id]
    mapping = speaker_mapping_service.require_confirmed_mapping(repo, transcript_id)
    headers = parse_cha_metadata(transcript.raw_text)
    language_codes = tuple(
        code.strip()
        for value in headers.get("@Languages", ["eng"])
        for code in value.replace(";", ",").split(",")
        if code.strip()
    ) or ("eng",)
    parsed_participants = parse_participants(headers.get("@Participants", []))
    parsed_by_code = {item["code"]: item for item in parsed_participants}
    id_by_code = {
        item["code"]: tuple(item["raw"].split("|"))
        for item in parse_ids(headers.get("@ID", []))
    }
    participants = []
    seen_codes: set[str] = set()
    for entry in mapping.entries:
        if entry.disposition == "merged" or not entry.confirmed_chat_code:
            continue
        code = entry.confirmed_chat_code.upper()
        if code in seen_codes:
            continue
        declared = parsed_by_code.get(code, {})
        from app.services.chat_subset import CanonicalParticipant

        default_id_fields = (
            language_codes[0],
            "LinguaLens",
            code,
            "",
            "",
            "",
            "",
            entry.participant_role,
            "",
            "",
        )

        participants.append(
            CanonicalParticipant(
                code=code,
                display_name=declared.get("name", code),
                role=declared.get("role", entry.participant_role),
                id_fields=id_by_code.get(code, default_id_fields),
            )
        )
        seen_codes.add(code)
    if not participants:
        raise ValueError("CHAT export requires at least one confirmed participant mapping.")

    optional_keys = {"@Date", "@Location", "@Situation", "@Activities", "@Comment", "@Transcriber", "@Options"}
    optional_headers = tuple(
        (key, value)
        for key, values in headers.items()
        if key in optional_keys
        for value in values
    )
    media = parse_media(headers.get("@Media", []))
    from app.services.chat_subset import CanonicalChatUtterance, CanonicalDependentTier, CanonicalOpaqueExtension

    opaque = []
    for item in transcript.orphan_dependent_tiers:
        opaque.append(CanonicalOpaqueExtension(action="unsupported_blocking", location="dependent_tier", key=item.tier, content=item.raw_text))
    for item in transcript.malformed_lines:
        opaque.append(CanonicalOpaqueExtension(action="unsupported_blocking", location="header", key="@x-lingualens-malformed-line", content=str(item.get("raw_text", ""))))
    supported_tiers = {"%mor", "%gra", "%pho", "%com", "%act", "%sit"}
    utterances = []
    for utterance in transcript.utterances:
        speaker_code = str(getattr(utterance.speaker, "value", utterance.speaker)).upper()
        if utterance.temporary_speaker_id:
            matching = next((item for item in mapping.entries if item.temporary_speaker_id == utterance.temporary_speaker_id), None)
            if matching and matching.confirmed_chat_code:
                speaker_code = matching.confirmed_chat_code.upper()
        text = utterance.text
        terminator = "."
        if text and text[-1] in ".?!;":
            terminator = text[-1]
            text = text[:-1].rstrip()
        tiers = []
        if utterance.notes:
            tiers.append(CanonicalDependentTier(tier="%com", text=utterance.notes))
        for tier in utterance.dependent_tiers:
            if tier.tier in supported_tiers:
                tiers.append(CanonicalDependentTier(tier=tier.tier, text=tier.raw_text))
            elif tier.tier == "%exp":
                tiers.append(CanonicalDependentTier(tier="%com", text=tier.raw_text))
            elif tier.tier.startswith("%x"):
                opaque.append(CanonicalOpaqueExtension(action="preserved_opaque", location="dependent_tier", key=tier.tier, content=tier.raw_text, owner_utterance_id=utterance.utterance_id))
            else:
                opaque.append(CanonicalOpaqueExtension(action="unsupported_blocking", location="dependent_tier", key=tier.tier, content=tier.raw_text, owner_utterance_id=utterance.utterance_id))
        utterances.append(
            CanonicalChatUtterance(
                utterance_id=utterance.utterance_id,
                speaker_code=speaker_code,
                reviewed_text_nfc=text,
                start_ms=utterance.start_ms,
                end_ms=utterance.end_ms,
                terminator=terminator,
                dependent_tiers=tuple(tiers),
            )
        )
    return CanonicalChatDocument(
        language_codes=language_codes,
        media_reference=media["name"] if media else None,
        participants=tuple(participants),
        utterances=tuple(utterances),
        optional_headers=optional_headers,
        opaque_extensions=tuple(opaque),
    )


def create_verified_chat_export(repo, transcript_id: str, *, exported_by: str = "system") -> ChatExport:
    """Create one current, attested, byte-stable CHAT artifact."""

    transcript = repo.transcripts[transcript_id]
    if transcript.qa_status.value not in {"PASS", "WARNING"}:
        raise ValueError("CHAT_QA_REQUIRED: transcript QA must pass before export.")
    mapping = speaker_mapping_service.require_confirmed_mapping(repo, transcript_id)
    if mapping is None:
        raise ValueError("CHAT_SPEAKER_MAPPING_REQUIRED: confirmed mapping is required before export.")
    attestation = repo.get_current_transcript_attestation(transcript_id)
    if attestation is None or attestation.transcript_version != transcript.version:
        raise ValueError("CHAT_ATTESTATION_REQUIRED: current typed attestation is required before export.")
    document = canonical_document_from_repo(repo, transcript_id)
    verification = verify_chat_round_trip(document)
    if verification.status != "verified":
        codes = ", ".join(error.code for error in verification.errors)
        raise ValueError(f"CHAT_ROUND_TRIP_FAILED: {codes}")

    audio_candidates = [
        item
        for item in repo.audio_files.values()
        if item.session_id == transcript.session_id and item.retained and item.checksum_sha256
    ]
    if not audio_candidates:
        raise ValueError("CHAT_AUDIO_REQUIRED: a verified source audio asset is required before export.")
    audio = sorted(audio_candidates, key=lambda item: (item.source_asset_version, item.created_at))[-1]
    normalized = repo.get_current_normalized_audio_asset(audio.audio_file_id)
    if normalized is None or normalized.verification_status != "verified":
        raise ValueError("CHAT_NORMALIZED_AUDIO_REQUIRED: a verified normalized asset is required before export.")

    asr = None
    provenance = transcript.asr_provenance or {}
    profile_values = transcript.asr_profile or {}
    if profile_values and provenance:
        try:
            asr = AsrProvenance(
                job_id=str(provenance.get("job_id", "unknown-job")),
                profile=AsrProfile(
                    provider_name=str(provenance.get("provider_id", "local_faster_whisper")),
                    provider_version=str(provenance.get("provider_version", "v1.7.0")),
                    model_id=str(profile_values.get("model_identifier", "local-faster-whisper")),
                    model_version=str(profile_values.get("model_revision", "pinned")),
                    model_checksum_sha256=str(profile_values.get("model_checksum_sha256", "0" * 64)),
                    language_profile=str(profile_values.get("profile_id", "v1.7.0")),
                    configuration_checksum_sha256=profile_values.get("profile_checksum_sha256"),
                ),
                source_audio_file_id=audio.audio_file_id,
                source_asset_version=audio.source_asset_version,
                source_checksum_sha256=audio.checksum_sha256,
                normalized_asset_version=normalized.asset_version,
                normalized_checksum_sha256=normalized.normalized_checksum_sha256,
                raw_speaker_labels=tuple(transcript.raw_speaker_labels),
                generated_at=transcript.updated_at,
            )
        except Exception:  # provenance remains optional but never fabricated
            asr = None

    current = repo.get_current_chat_export(transcript_id)
    export_version = current.export_version + 1 if current is not None else 1
    round_trip = ChatSemanticRoundTripResult(
        status=RoundTripStatus.verified,
        parser_version=verification.parser_version,
        serializer_version=verification.serializer_version,
        subset_version=verification.subset_version,
        input_semantic_checksum_sha256=verification.input_semantic_checksum_sha256,
        output_semantic_checksum_sha256=verification.output_semantic_checksum_sha256,
        deterministic_export_checksum_sha256=verification.export_b_checksum_sha256,
        errors=[],
    )
    record = ChatExport(
        organization_id=transcript.organization_id,
        session_id=transcript.session_id,
        export_id=new_id("chat"),
        export_version=export_version,
        transcript_id=transcript_id,
        transcript_version=transcript.version,
        speaker_mapping_id=mapping.mapping_id,
        speaker_mapping_version=mapping.mapping_version,
        attestation_id=attestation.attestation_id,
        attestation_version=attestation.attestation_version,
        parser_version=verification.parser_version,
        serializer_version=verification.serializer_version,
        subset_version=verification.subset_version,
        canonical_checksum_sha256=verification.input_semantic_checksum_sha256,
        source_audio_file_id=audio.audio_file_id,
        source_asset_version=audio.source_asset_version,
        source_checksum_sha256=audio.checksum_sha256,
        normalized_asset_version=normalized.asset_version,
        normalized_checksum_sha256=normalized.normalized_checksum_sha256,
        asr_provenance=asr,
        cha_text=verification.export_a,
        round_trip=round_trip,
        status=ArtifactStatus.current,
        created_at=transcript.updated_at,
        exported_by_user_id=exported_by,
    )
    repo.add_audit(
        "transcript.chat_export",
        record.export_id,
        "Verified deterministic CHAT export created.",
        actor_id=exported_by,
        organization_id=transcript.organization_id,
    )
    return repo.create_chat_export(record)
