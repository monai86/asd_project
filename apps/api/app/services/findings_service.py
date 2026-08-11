"""Service for projecting auditable v1.7.0 Findings projections."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from app.schemas.clinical import ArtifactStatus
from app.schemas.speech_pipeline import FeatureResult, FindingsProjection
from app.services.providers.descriptive_v170_provider import (
    FEATURE_SCHEMA_VERSION,
    extract_descriptive_feature_results,
)

FINDINGS_SERVICE_VERSION = "findings-projection-service-v1.7.0"


def project_findings_for_session(repo, session_id: str) -> FindingsProjection:
    session = repo.sessions.get(session_id)
    if session is None:
        raise ValueError("Session not found.")
    transcript_id = session.transcript_id
    if not transcript_id or transcript_id not in repo.transcripts:
        raise ValueError("Transcript not found for session.")

    features = extract_descriptive_feature_results(repo, transcript_id)
    if not features:
        raise ValueError("No feature results extracted.")

    first_feat: FeatureResult = features[0]

    current_findings = repo.get_current_findings_result(transcript_id)
    next_version = (current_findings.findings_version + 1) if current_findings else 1
    findings_id = current_findings.findings_id if current_findings else f"findings-{uuid.uuid4().hex[:12]}"

    chat_export = repo.get_current_chat_export(transcript_id)
    if chat_export is None:
        raise ValueError("CHAT export not found.")

    attestation = repo.get_current_transcript_attestation(transcript_id)
    if attestation is None:
        raise ValueError("Attestation not found.")

    acknowledgment_refs = list(attestation.acknowledgment_refs)

    tok_ref = next((f.tokenizer_profile for f in features if f.tokenizer_profile is not None), None)

    projection = FindingsProjection(
        organization_id=session.organization_id,
        session_id=session.session_id,
        findings_id=findings_id,
        findings_version=next_version,
        transcript_id=transcript_id,
        transcript_version=first_feat.transcript_version,
        speaker_mapping_id=first_feat.speaker_mapping_id,
        speaker_mapping_version=first_feat.speaker_mapping_version,
        source_audio_file_id=first_feat.source_audio_file_id,
        source_asset_version=first_feat.source_asset_version,
        source_checksum_sha256=first_feat.source_checksum_sha256,
        normalized_asset_version=first_feat.normalized_asset_version,
        normalized_checksum_sha256=first_feat.normalized_checksum_sha256,
        attestation_id=first_feat.attestation_id,
        attestation_version=first_feat.attestation_version,
        chat_export_id=first_feat.chat_export_id,
        chat_export_version=first_feat.chat_export_version,
        chat_export_checksum_sha256=first_feat.chat_export_checksum_sha256,
        parser_version=first_feat.parser_version,
        serializer_version=first_feat.serializer_version,
        tokenizer_profile=tok_ref,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        algorithm_version=first_feat.algorithm_version,
        algorithm_checksum_sha256=first_feat.algorithm_checksum_sha256,
        features=features,
        acknowledgment_refs=acknowledgment_refs,
        generation_service_version=FINDINGS_SERVICE_VERSION,
        generated_at=datetime.now(timezone.utc),
        status=ArtifactStatus.current,
        stale_causes=[],
    )

    stored = repo.create_findings_result(projection)
    return stored


def get_current_findings_for_session(repo, session_id: str) -> FindingsProjection | None:
    session = repo.sessions.get(session_id)
    if session is None or not session.transcript_id:
        return None
    return repo.get_current_findings_result(session.transcript_id)
