"""Typed QA policy for blocker and limitation handling in v1.7.0."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from app.repositories.mock_repository import new_id
from app.schemas.clinical import LimitationAcknowledgmentRequest, QaIssue
from app.schemas.speech_pipeline import ArtifactStatus, LimitationAcknowledgment, QaDisposition
from app.services.qa_rules_v170 import (
    INTEGRITY_BLOCKER_CODES,
    LEGACY_BLOCKER_MAP,
    LIMITATION_MAP,
    LIMITATION_REMEDIATION,
    QA_RULE_VERSION,
)


class QaOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    disposition: QaDisposition
    severity: str
    rule_version: str = QA_RULE_VERSION
    affected_resources: list[str] = Field(default_factory=list)
    remediation: str
    message: str = ""


def classify_qa_issues(issues: list[QaIssue]) -> list[QaOutcome]:
    outcomes: list[QaOutcome] = []
    for issue in issues:
        mapped_blocker = LEGACY_BLOCKER_MAP.get(issue.code)
        if issue.code in INTEGRITY_BLOCKER_CODES or mapped_blocker or issue.blocking:
            code = issue.code if issue.code in INTEGRITY_BLOCKER_CODES else mapped_blocker
            outcomes.append(
                QaOutcome(
                    code=code or "PROVENANCE_VERSION_MISMATCH",
                    disposition=QaDisposition.integrity_blocker,
                    severity="error",
                    affected_resources=[item for item in [issue.line_id, issue.field] if item],
                    remediation=issue.recommended_action or issue.fix_suggestion or "Resolve the integrity failure and rerun QA.",
                    message=issue.message,
                )
            )
            continue
        limitation_code = LIMITATION_MAP.get(issue.code)
        if limitation_code:
            outcomes.append(
                QaOutcome(
                    code=limitation_code,
                    disposition=QaDisposition.acknowledgeable_limitation,
                    severity="warning",
                    affected_resources=[item for item in [issue.line_id, issue.field] if item],
                    remediation=LIMITATION_REMEDIATION[limitation_code],
                    message=issue.message,
                )
            )
    return outcomes


def current_qa_outcomes(repo, transcript_id: str) -> list[QaOutcome]:
    from app.services import speaker_mapping_service, transcript_service

    transcript = repo.transcripts[transcript_id]
    linked_audio = [
        item for item in repo.audio_files.values()
        if item.session_id == transcript.session_id and item.retained
    ]
    mapping_issues = speaker_mapping_service.mapping_qa_issues(repo, transcript)
    transcript_issues = transcript_service.qa_issues(transcript, linked_audio)
    if repo.get_current_speaker_mapping(transcript_id) is not None:
        # ASR drafts intentionally retain temporary provider labels. A current
        # confirmed mapping, rather than rewriting raw labels, resolves these
        # legacy CHAT-label checks.
        transcript_issues = [
            item for item in transcript_issues
            if item.code not in {"UNKNOWN_SPEAKER", "MISSING_CHILD_SPEAKER", "HIGH_UNKNOWN_SPEAKER_RATIO"}
        ]
    return classify_qa_issues([*mapping_issues, *transcript_issues])


def acknowledge_limitation(
    repo,
    transcript_id: str,
    limitation_code: str,
    payload: LimitationAcknowledgmentRequest,
    *,
    therapist_user_id: str,
    therapist_role: str,
) -> LimitationAcknowledgment:
    transcript = repo.transcripts[transcript_id]
    if payload.expected_transcript_version != transcript.version:
        raise ValueError("TRANSCRIPT_STALE: acknowledgment version does not match the current transcript.")
    if payload.expected_qa_rule_version != QA_RULE_VERSION:
        raise ValueError("PROVENANCE_VERSION_MISMATCH: QA validator version is not current.")
    current_mapping = repo.get_current_speaker_mapping(transcript_id)
    if (
        payload.expected_speaker_mapping_version is not None
        and (current_mapping is None or current_mapping.mapping_version != payload.expected_speaker_mapping_version)
    ):
        raise ValueError("SPEAKER_MAPPING_STALE: acknowledgment mapping version is not current.")
    outcomes = current_qa_outcomes(repo, transcript_id)
    outcome = next(
        (
            item for item in outcomes
            if item.code == limitation_code
            and item.disposition is QaDisposition.acknowledgeable_limitation
        ),
        None,
    )
    if outcome is None:
        raise ValueError(f"{limitation_code} is not a current acknowledgeable limitation.")
    existing = [
        item for item in repo.list_current_acknowledgments(transcript_id)
        if item.limitation_code == limitation_code
    ]
    acknowledgment_version = max((item.acknowledgment_version for item in existing), default=0) + 1
    return repo.create_limitation_acknowledgment(
        LimitationAcknowledgment(
            organization_id=transcript.organization_id,
            session_id=transcript.session_id,
            transcript_id=transcript.transcript_id,
            transcript_version=transcript.version,
            acknowledgment_id=new_id("ack"),
            acknowledgment_version=acknowledgment_version,
            limitation_code=limitation_code,
            severity=outcome.severity,
            disposition=QaDisposition.acknowledgeable_limitation,
            affected_resource_id=transcript.transcript_id,
            affected_resource_version=str(transcript.version),
            affected_stage="transcript_qa",
            therapist_user_id=therapist_user_id,
            therapist_role=therapist_role,
            acknowledged_at=datetime.now(timezone.utc),
            structured_reason=payload.structured_reason,
            note=payload.note,
            validator_version=QA_RULE_VERSION,
            request_audit_id=new_id("audit"),
            status=ArtifactStatus.current,
        )
    )
