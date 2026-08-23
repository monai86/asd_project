import pytest
from pydantic import ValidationError

from app.schemas.clinical import ReviewStatus, Transcript, Utterance
from app.repositories.mock_repository import MockRepository
from app.services.speaker_mapping_service import derive_mapping_draft, requires_speaker_mapping
from app.schemas.speaker_mapping import SpeakerMapping, SpeakerMappingDraftUpdate


def _transcript(*, source: str = "asr_draft:manual", utterances: list[Utterance] | None = None) -> Transcript:
    return Transcript(
        transcript_id="transcript_synthetic_001",
        session_id="session_demo_001",
        case_id="case_demo_001",
        source=source,
        raw_text="Synthetic transcript",
        utterances=utterances or [],
    )


def _utterance(
    index: int,
    *,
    temporary_speaker_id: str | None = None,
    source_speaker_label: str | None = None,
) -> Utterance:
    return Utterance(
        utterance_id=f"utt-{index}",
        speaker="UNK",
        text=f"Synthetic sample {index}",
        temporary_speaker_id=temporary_speaker_id,
        source_speaker_label=source_speaker_label,
    )


def test_real_asr_with_temporary_ids_requires_mapping_and_derives_draft() -> None:
    transcript = _transcript(
        utterances=[
            _utterance(0, temporary_speaker_id="tmp-b", source_speaker_label="Speaker B"),
            _utterance(1, temporary_speaker_id="tmp-a", source_speaker_label="Speaker A"),
            _utterance(2, temporary_speaker_id="tmp-b"),
        ],
    )

    assert requires_speaker_mapping(transcript) is True
    draft = derive_mapping_draft(transcript)

    assert draft.required is True
    assert draft.persisted is False
    assert draft.effective_status == "draft"
    assert [entry.temporary_speaker_id for entry in draft.entries] == ["tmp-b", "tmp-a"]
    assert draft.entries[0].source_speaker_label == "Speaker B"
    assert draft.entries[0].provider_metadata == {"provider_id": "manual"}
    assert draft.entries[0].affected_utterance_ids == ["utt-0", "utt-2"]
    assert draft.entries[0].confirmed_chat_code is None
    assert draft.entries[0].participant_role is None


def test_mapping_activation_bypasses_mock_manual_and_incomplete_asr() -> None:
    temporary = [_utterance(0, temporary_speaker_id="tmp-a")]
    assert requires_speaker_mapping(_transcript(source="mock_asr_draft:manual", utterances=temporary)) is False
    assert requires_speaker_mapping(_transcript(source="manual", utterances=temporary)) is False
    assert requires_speaker_mapping(_transcript(source="asr:canonical", utterances=[])) is False
    assert requires_speaker_mapping(_transcript(source="asr:canonical", utterances=temporary)) is False


def test_mapping_input_ignores_client_server_fields_and_repository_factory_shape() -> None:
    repo = MockRepository()
    transcript = _transcript(
        utterances=[
            _utterance(0, temporary_speaker_id="tmp-a", source_speaker_label="ASR A"),
            _utterance(1, temporary_speaker_id="tmp-a"),
        ],
    )
    repo.create_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="therapist-demo",
        audit_action="transcript.create",
        audit_message="Synthetic transcript created.",
    )

    draft = derive_mapping_draft(repo.transcripts[transcript.transcript_id])

    assert draft.entries[0].source_speaker_label == "ASR A"
    assert draft.entries[0].provider_metadata == {"provider_id": "manual"}
    client_entry = {
        "temporary_speaker_id": "tmp-a",
        "source_speaker_label": "Client-controlled label",
        "provider_metadata": {"provider_id": "client-controlled"},
        "reviewed_utterance_ids": ["utt-0"],
    }
    from app.schemas.speaker_mapping import SpeakerMappingEntryInput

    parsed = SpeakerMappingEntryInput.model_validate(client_entry)
    assert not hasattr(parsed, "source_speaker_label")
    assert not hasattr(parsed, "provider_metadata")


def test_mapping_contract_uses_exact_confirmation_fields() -> None:
    mapping = SpeakerMapping(
        mapping_id="mapping_synthetic_001",
        organization_id="pilot_org_001",
        transcript_id="transcript_synthetic_001",
        source_transcript_version=1,
        status="confirmed",
        confirmed_by_user_id="therapist-demo",
        entries=[],
    )

    assert mapping.status == "confirmed"
    assert mapping.confirmed_by_user_id == "therapist-demo"
    serialized = mapping.model_dump()
    assert serialized["status"] == "confirmed"
    assert serialized["confirmed_by_user_id"] == "therapist-demo"


def test_provider_metadata_is_only_derived_for_qualifying_asr_drafts() -> None:
    temporary = [_utterance(0, temporary_speaker_id="tmp-a")]
    for source in ("manual", "mock_asr_draft:manual", "asr_draft:", "asr_draft:   "):
        draft = derive_mapping_draft(_transcript(source=source, utterances=temporary))
        assert draft.entries[0].provider_metadata == {}


def test_asr_draft_requires_nonempty_temporary_speaker_id() -> None:
    assert requires_speaker_mapping(_transcript(source="asr_draft:manual", utterances=[])) is False
    assert requires_speaker_mapping(
        _transcript(source="asr_draft:manual", utterances=[_utterance(0, temporary_speaker_id="   ")])
    ) is False


def test_mapping_records_require_entries_field() -> None:
    mapping_payload = {
        "mapping_id": "mapping_synthetic_001",
        "organization_id": "pilot_org_001",
        "transcript_id": "transcript_synthetic_001",
        "source_transcript_version": 1,
    }
    with pytest.raises(ValidationError):
        SpeakerMapping.model_validate(mapping_payload)
    with pytest.raises(ValidationError):
        SpeakerMappingDraftUpdate.model_validate({"expected_transcript_version": 1})
