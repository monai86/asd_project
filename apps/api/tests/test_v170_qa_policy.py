from __future__ import annotations

import pytest

from app.schemas.clinical import (
    AttestationRequest,
    LimitationAcknowledgmentRequest,
    QaIssue,
    Transcript,
    Utterance,
    FeatureExtractionRequest,
)
from app.repositories.mock_repository import MockRepository
from app.schemas.speech_pipeline import QaDisposition
from app.services.qa_policy_service import acknowledge_limitation, classify_qa_issues


@pytest.mark.parametrize(
    ("legacy_code", "expected_code"),
    [
        ("MISSING_BEGIN", "TRANSCRIPT_MATERIALLY_INCOMPLETE"),
        ("MISSING_END", "TRANSCRIPT_MATERIALLY_INCOMPLETE"),
        ("MISSING_CHILD_SPEAKER", "SPEAKER_MAPPING_INCOMPLETE"),
        ("TIMESTAMP_ORDER", "TIMESTAMP_ORDER_INVALID"),
        ("TIMESTAMP_OUT_OF_RANGE", "TIMESTAMP_RANGE_INVALID"),
    ],
)
def test_structural_qa_failures_are_typed_integrity_blockers(
    legacy_code: str,
    expected_code: str,
) -> None:
    outcomes = classify_qa_issues(
        [QaIssue(code=legacy_code, severity="error", message="unsafe", blocking=True)]
    )

    assert outcomes[0].code == expected_code
    assert outcomes[0].disposition is QaDisposition.integrity_blocker
    assert outcomes[0].severity == "error"
    assert outcomes[0].rule_version == "speech-qa-v1.7.0"


@pytest.mark.parametrize(
    ("legacy_code", "expected_code"),
    [
        ("SHORT_TRANSCRIPT", "SHORT_SAMPLE"),
        ("TOO_FEW_CHILD_UTTERANCES", "SHORT_SAMPLE"),
        ("HIGH_UNINTELLIGIBLE_RATIO", "LOW_INTELLIGIBILITY"),
        ("MISSING_LANGUAGE", "OPTIONAL_CHAT_METADATA_ABSENT"),
        ("UNSUPPORTED_DEPENDENT_TIER", "OPTIONAL_FEATURE_UNAVAILABLE"),
    ],
)
def test_reviewable_qa_warnings_are_typed_acknowledgeable_limitations(
    legacy_code: str,
    expected_code: str,
) -> None:
    outcomes = classify_qa_issues(
        [QaIssue(code=legacy_code, severity="warning", message="limited")]
    )

    assert outcomes[0].code == expected_code
    assert outcomes[0].disposition is QaDisposition.acknowledgeable_limitation
    assert outcomes[0].severity == "warning"
    assert outcomes[0].remediation


def test_unknown_blocking_issue_fails_closed() -> None:
    outcome = classify_qa_issues(
        [QaIssue(code="NEW_UNCLASSIFIED_FAILURE", severity="error", message="unknown", blocking=True)]
    )[0]

    assert outcome.code == "PROVENANCE_VERSION_MISMATCH"
    assert outcome.disposition is QaDisposition.integrity_blocker


def test_attestation_contract_has_no_generic_qa_override() -> None:
    assert "override_qa_failure" not in AttestationRequest.model_fields


def test_acknowledgment_is_bound_to_current_transcript_and_validator_versions() -> None:
    repo = MockRepository()
    session = repo.sessions["session_demo_001"]
    transcript = Transcript(
        transcript_id="transcript-qa-policy",
        session_id=session.session_id,
        case_id=session.case_id,
        source="manual_entry",
        raw_text="@Begin\n@Languages:\teng\n@Participants:\tCHI Child Target_Child\n*CHI:\thi .\n@End",
        utterances=[Utterance(utterance_id="u-1", speaker="CHI", text="hi")],
    )
    repo.transcripts[transcript.transcript_id] = transcript
    session.transcript_id = transcript.transcript_id

    record = acknowledge_limitation(
        repo,
        transcript.transcript_id,
        "SHORT_SAMPLE",
        LimitationAcknowledgmentRequest(
            expected_transcript_version=transcript.version,
            structured_reason="reviewed_and_accepted",
        ),
        therapist_user_id="therapist_demo_001",
        therapist_role="therapist",
    )

    assert record.limitation_code == "SHORT_SAMPLE"
    assert record.transcript_version == transcript.version
    assert record.validator_version == "speech-qa-v1.7.0"
    assert record.disposition is QaDisposition.acknowledgeable_limitation


def test_cannot_acknowledge_integrity_blocker() -> None:
    repo = MockRepository()
    session = repo.sessions["session_demo_001"]
    transcript = Transcript(
        transcript_id="transcript-qa-blocker",
        session_id=session.session_id,
        case_id=session.case_id,
        source="manual_entry",
        raw_text="",
        utterances=[],
    )
    repo.transcripts[transcript.transcript_id] = transcript
    session.transcript_id = transcript.transcript_id
    transcript_id = transcript.transcript_id

    with pytest.raises(ValueError, match="not a current acknowledgeable limitation"):
        acknowledge_limitation(
            repo,
            transcript_id,
            "TRANSCRIPT_MATERIALLY_INCOMPLETE",
            LimitationAcknowledgmentRequest(
                expected_transcript_version=repo.transcripts[transcript_id].version,
                structured_reason="reviewed_and_accepted",
            ),
            therapist_user_id="therapist_demo_001",
            therapist_role="therapist",
        )


def test_upload_first_feature_flow_rejects_debug_override_and_requires_typed_attestation() -> None:
    from app.services.feature_service import extract_features

    repo = MockRepository()
    session = repo.sessions["session_demo_001"]
    from app.schemas.clinical import Transcript, Utterance
    transcript = Transcript(
        transcript_id="transcript-feature-gate",
        session_id=session.session_id,
        case_id=session.case_id,
        source="asr_draft:local_faster_whisper",
        raw_text="@Begin\n*SPK_01:\twords.\n*SPK_02:\tmore words.\n@End",
        utterances=[
            Utterance(utterance_id="u1", speaker="SPK_01", text="words.", start_ms=0, end_ms=1000),
            Utterance(utterance_id="u2", speaker="SPK_02", text="more words.", start_ms=1000, end_ms=2000),
        ],
        qa_status="PASS",
        therapist_attested=True,
    )
    repo.transcripts[transcript.transcript_id] = transcript
    session.transcript_id = transcript.transcript_id
    from app.schemas.clinical import ReviewedSpeakerMapping, SpeakerMappingEntry, MappingStatus
    from datetime import datetime, timezone
    repo.create_speaker_mapping(
        ReviewedSpeakerMapping(
            organization_id=session.organization_id,
            session_id=session.session_id,
            mapping_id="map-feature-gate",
            mapping_version=1,
            transcript_id=transcript.transcript_id,
            transcript_version=1,
            entries=[
                SpeakerMappingEntry(
                    temporary_speaker_id="SPK_01",
                    confirmed_chat_code="CHI",
                    participant_role="target_child",
                    disposition="target",
                    affected_utterance_ids=["u1"],
                    reviewed_utterance_ids=["u1"],
                ),
                SpeakerMappingEntry(
                    temporary_speaker_id="SPK_02",
                    confirmed_chat_code="THE",
                    participant_role="therapist",
                    disposition="non_target",
                    affected_utterance_ids=["u2"],
                    reviewed_utterance_ids=["u2"],
                ),
            ],
            confirmed_by_user_id="therapist",
            confirmed_by_role="therapist",
            confirmed_at=datetime.now(timezone.utc),
            status=MappingStatus.confirmed,
        )
    )

    with pytest.raises(ValueError, match="test-only and cannot be used"):
        extract_features(
            repo,
            transcript.transcript_id,
            FeatureExtractionRequest(force_debug_override=True, override_reason="not clinical"),
        )
    with pytest.raises(ValueError, match="current typed transcript attestation"):
        extract_features(repo, transcript.transcript_id, FeatureExtractionRequest())
