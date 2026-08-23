from app.schemas.clinical import ReviewStatus, Transcript, Utterance
from app.repositories.mock_repository import MockRepository
from app.services.speaker_mapping_service import derive_mapping_draft, speaker_mapping_required


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

    assert speaker_mapping_required(transcript) is True
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
    assert speaker_mapping_required(_transcript(source="mock_asr_draft:manual", utterances=temporary)) is False
    assert speaker_mapping_required(_transcript(source="manual", utterances=temporary)) is False
    assert speaker_mapping_required(_transcript(source="asr:canonical", utterances=[])) is False
    assert speaker_mapping_required(_transcript(source="asr:canonical", utterances=temporary)) is False


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
