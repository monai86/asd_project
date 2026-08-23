from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import stat
import threading

import pytest
from pydantic import ValidationError

import app.repositories.mock_repository as mock_repository_module
from app.schemas.clinical import ReviewStatus, Transcript, Utterance
from app.repositories.base import SpeakerMappingVersionConflictError, TranscriptVersionConflictError
from app.repositories.mock_repository import JsonFileRepository, MockRepository
from app.services.speaker_mapping_service import (
    derive_mapping_draft,
    get_mapping,
    requires_speaker_mapping,
    save_mapping_draft,
)
from app.schemas.speaker_mapping import MappingPersistedStatus, SpeakerMapping, SpeakerMappingDraftUpdate


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


def _persisted_transcript(repo: MockRepository) -> Transcript:
    transcript = _transcript(
        utterances=[
            _utterance(0, temporary_speaker_id="tmp-a", source_speaker_label="ASR A"),
            _utterance(1, temporary_speaker_id="tmp-b", source_speaker_label="ASR B"),
        ],
    )
    repo.create_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="therapist-demo",
        audit_action="transcript.create",
        audit_message="Synthetic transcript created.",
    )
    return transcript


def _draft_update(
    transcript: Transcript,
    *,
    expected_mapping_version: int | None = None,
    entries: list[dict] | None = None,
) -> SpeakerMappingDraftUpdate:
    return SpeakerMappingDraftUpdate.model_validate(
        {
            "expected_transcript_version": transcript.version,
            "expected_mapping_version": expected_mapping_version,
            "entries": entries
            if entries is not None
            else [
                {
                    "temporary_speaker_id": "tmp-a",
                    "confirmed_chat_code": "CHI",
                    "participant_role": "target_child",
                    "reviewed_utterance_ids": ["utt-0"],
                }
            ],
        }
    )


def test_save_mapping_draft_creates_then_versions_current_draft() -> None:
    repo = MockRepository()
    transcript = _persisted_transcript(repo)

    first = save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript), actor_id="therapist-demo")
    second = save_mapping_draft(
        repo,
        transcript.transcript_id,
        _draft_update(
            transcript,
            expected_mapping_version=first.mapping_version,
            entries=[
                {
                    "temporary_speaker_id": "tmp-a",
                    "confirmed_chat_code": "CHI",
                    "participant_role": "target_child",
                    "reviewed_utterance_ids": ["utt-0"],
                },
                {
                    "temporary_speaker_id": "tmp-b",
                    "confirmed_chat_code": "THER",
                    "participant_role": "therapist",
                    "reviewed_utterance_ids": ["utt-1"],
                },
            ],
        ),
        actor_id="therapist-demo",
    )

    assert first.persisted is True
    assert first.mapping_version == 1
    assert second.mapping_id == first.mapping_id
    assert second.mapping_version == 2
    assert [entry.temporary_speaker_id for entry in second.entries] == ["tmp-a", "tmp-b"]


def test_save_mapping_draft_derives_server_owned_fields_and_ignores_unknown_entries() -> None:
    repo = MockRepository()
    transcript = _persisted_transcript(repo)

    response = save_mapping_draft(
        repo,
        transcript.transcript_id,
        _draft_update(
            transcript,
            entries=[
                {
                    "temporary_speaker_id": "tmp-a",
                    "confirmed_chat_code": "CHI",
                    "participant_role": "target_child",
                    "reviewed_utterance_ids": ["utt-0", "client-only"],
                    "source_speaker_label": "Client-controlled",
                    "provider_metadata": {"provider_id": "client-controlled"},
                    "affected_utterance_ids": ["client-only"],
                },
                {"temporary_speaker_id": "unknown", "confirmed_chat_code": "OTH", "participant_role": "other"},
            ],
        ),
    )

    assert [entry.temporary_speaker_id for entry in response.entries] == ["tmp-a", "tmp-b"]
    first_entry = response.entries[0]
    assert first_entry.source_speaker_label == "ASR A"
    assert first_entry.provider_metadata == {"provider_id": "manual"}
    assert first_entry.affected_utterance_ids == ["utt-0"]
    assert first_entry.reviewed_utterance_ids == ["utt-0"]
    assert response.entries[1].confirmed_chat_code is None


def test_stale_mapping_version_does_not_mutate_mapping_or_audit() -> None:
    repo = MockRepository()
    transcript = _persisted_transcript(repo)
    first = save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript))
    mapping_before = repo.get_latest_speaker_mapping(transcript.transcript_id)
    audit_before = list(repo.audit_log)

    with pytest.raises(SpeakerMappingVersionConflictError):
        save_mapping_draft(
            repo,
            transcript.transcript_id,
            _draft_update(transcript, expected_mapping_version=first.mapping_version + 1),
        )

    assert repo.get_latest_speaker_mapping(transcript.transcript_id) == mapping_before
    assert repo.audit_log == audit_before


def test_stale_transcript_version_does_not_mutate_mapping_or_audit() -> None:
    repo = MockRepository()
    transcript = _persisted_transcript(repo)
    mapping_before = dict(repo.speaker_mappings)
    audit_before = list(repo.audit_log)
    stale_update = _draft_update(transcript)
    transcript.version += 1

    with pytest.raises(TranscriptVersionConflictError):
        save_mapping_draft(repo, transcript.transcript_id, stale_update)

    assert repo.speaker_mappings == mapping_before
    assert repo.audit_log == audit_before


def test_json_repository_round_trips_speaker_mapping_draft_identity_version_and_entries(tmp_path) -> None:
    path = tmp_path / "speaker-mapping.json"
    repo = JsonFileRepository(path)
    transcript = _persisted_transcript(repo)
    first = save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript))
    saved = save_mapping_draft(
        repo,
        transcript.transcript_id,
        _draft_update(transcript, expected_mapping_version=first.mapping_version),
    )

    restored = JsonFileRepository(path).get_latest_speaker_mapping(transcript.transcript_id)

    assert restored is not None
    assert restored.mapping_id == saved.mapping_id
    assert restored.mapping_version == saved.mapping_version
    assert restored.entries == saved.entries


def test_confirmed_mapping_is_immutable_and_newer_transcript_draft_gets_next_version() -> None:
    repo = MockRepository()
    transcript = _persisted_transcript(repo)
    confirmed = SpeakerMapping(
        mapping_id="mapping_confirmed_001",
        organization_id=transcript.organization_id,
        transcript_id=transcript.transcript_id,
        source_transcript_version=1,
        applied_transcript_version=1,
        mapping_version=4,
        status="confirmed",
        confirmed_by_user_id="therapist-demo",
        entries=derive_mapping_draft(transcript).entries,
    )
    repo.speaker_mappings[confirmed.mapping_id] = confirmed
    transcript.version = 2

    saved = save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript))

    assert repo.speaker_mappings[confirmed.mapping_id] == confirmed
    assert saved.mapping_id != confirmed.mapping_id
    assert saved.mapping_version == 5
    assert saved.source_transcript_version == 2


def test_get_mapping_derives_draft_confirmed_stale_and_not_required_effective_statuses() -> None:
    repo = MockRepository()
    transcript = _persisted_transcript(repo)

    assert get_mapping(repo, transcript.transcript_id).effective_status == "draft"
    draft = save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript))
    assert get_mapping(repo, transcript.transcript_id).effective_status == "draft"

    repo.speaker_mappings[draft.mapping_id].status = MappingPersistedStatus.confirmed
    repo.speaker_mappings[draft.mapping_id].applied_transcript_version = transcript.version
    assert get_mapping(repo, transcript.transcript_id).effective_status == "confirmed"

    transcript.version += 1
    stale = get_mapping(repo, transcript.transcript_id)
    assert stale.effective_status == "stale"
    assert stale.issue_code == "SPEAKER_MAPPING_STALE"

    transcript.source = "manual"
    assert get_mapping(repo, transcript.transcript_id).effective_status == "not_required"


def test_non_required_mapping_save_rejects_without_mutating_mapping_or_audit() -> None:
    repo = MockRepository()
    transcript = _persisted_transcript(repo)
    transcript.source = "manual"
    mappings_before = deepcopy(repo.speaker_mappings)
    audit_before = list(repo.audit_log)

    with pytest.raises(ValueError, match="does not require speaker mapping"):
        save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript))

    assert repo.speaker_mappings == mappings_before
    assert repo.audit_log == audit_before


def test_same_version_confirmed_mapping_rejects_new_draft_without_mutation() -> None:
    repo = MockRepository()
    transcript = _persisted_transcript(repo)
    confirmed = SpeakerMapping(
        mapping_id="mapping_confirmed_current_001",
        organization_id=transcript.organization_id,
        transcript_id=transcript.transcript_id,
        source_transcript_version=transcript.version,
        applied_transcript_version=transcript.version,
        status="confirmed",
        entries=derive_mapping_draft(transcript).entries,
    )
    repo.speaker_mappings[confirmed.mapping_id] = confirmed
    mappings_before = deepcopy(repo.speaker_mappings)
    audit_before = list(repo.audit_log)

    with pytest.raises(SpeakerMappingVersionConflictError):
        save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript))

    assert repo.speaker_mappings == mappings_before
    assert repo.audit_log == audit_before


def _synchronize_latest_lookup(repo: MockRepository) -> None:
    barrier = threading.Barrier(2)
    original_get_latest = repo.get_latest_speaker_mapping

    def synchronized_get_latest(transcript_id: str):
        try:
            barrier.wait(timeout=0.2)
        except threading.BrokenBarrierError:
            pass
        return original_get_latest(transcript_id)

    repo.get_latest_speaker_mapping = synchronized_get_latest  # type: ignore[method-assign]


def test_concurrent_initial_draft_saves_allow_exactly_one_success() -> None:
    repo = MockRepository()
    transcript = _persisted_transcript(repo)
    _synchronize_latest_lookup(repo)

    def save() -> str:
        try:
            save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript))
        except SpeakerMappingVersionConflictError:
            return "conflict"
        return "success"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: save(), range(2)))

    assert sorted(outcomes) == ["conflict", "success"]
    assert len(repo.speaker_mappings) == 1
    assert len([event for event in repo.audit_log if event["action"] == "speaker_mapping.draft_save"]) == 1


def test_concurrent_draft_updates_allow_exactly_one_success() -> None:
    repo = MockRepository()
    transcript = _persisted_transcript(repo)
    original = save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript))
    _synchronize_latest_lookup(repo)

    def save() -> str:
        try:
            save_mapping_draft(
                repo,
                transcript.transcript_id,
                _draft_update(transcript, expected_mapping_version=original.mapping_version),
            )
        except SpeakerMappingVersionConflictError:
            return "conflict"
        return "success"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: save(), range(2)))

    assert sorted(outcomes) == ["conflict", "success"]
    assert repo.get_latest_speaker_mapping(transcript.transcript_id).mapping_version == 2


def test_json_draft_save_rolls_back_memory_when_replace_fails(tmp_path, monkeypatch) -> None:
    path = tmp_path / "speaker-mapping.json"
    repo = JsonFileRepository(path)
    transcript = _persisted_transcript(repo)
    mappings_before = deepcopy(repo.speaker_mappings)
    audit_before = list(repo.audit_log)

    def fail_replace(*_args, **_kwargs):
        raise OSError("replace failed")

    monkeypatch.setattr(mock_repository_module.os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript))

    assert repo.speaker_mappings == mappings_before
    assert repo.audit_log == audit_before
    assert JsonFileRepository(path).speaker_mappings == mappings_before
    assert not list(tmp_path.glob(".*.tmp"))


def test_json_draft_save_rolls_back_memory_when_serialization_fails(tmp_path, monkeypatch) -> None:
    path = tmp_path / "speaker-mapping.json"
    repo = JsonFileRepository(path)
    transcript = _persisted_transcript(repo)
    mappings_before = deepcopy(repo.speaker_mappings)
    audit_before = list(repo.audit_log)

    def fail_serialization(*_args, **_kwargs):
        raise TypeError("serialization failed")

    monkeypatch.setattr(mock_repository_module.json, "dumps", fail_serialization)

    with pytest.raises(TypeError, match="serialization failed"):
        save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript))

    assert repo.speaker_mappings == mappings_before
    assert repo.audit_log == audit_before
    assert JsonFileRepository(path).speaker_mappings == mappings_before
    assert not list(tmp_path.glob(".*.tmp"))


def test_repository_rejects_draft_save_after_coordinated_transcript_version_change() -> None:
    repo = MockRepository()
    transcript = _persisted_transcript(repo)
    draft_ready = threading.Event()
    transcript_updated = threading.Event()
    original_new_id = repo.new_id

    def pause_before_draft_save(prefix: str) -> str:
        draft_ready.set()
        assert transcript_updated.wait(timeout=1)
        return original_new_id(prefix)

    repo.new_id = pause_before_draft_save  # type: ignore[method-assign]

    def save_draft() -> str:
        try:
            save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript))
        except TranscriptVersionConflictError:
            return "conflict"
        return "saved"

    def update_transcript() -> None:
        assert draft_ready.wait(timeout=1)
        replacement = repo.get_transcript(transcript.transcript_id)
        assert replacement is not None
        replacement.version += 1
        repo.update_transcript(
            replacement,
            session_status=ReviewStatus.needs_review,
            expected_version=transcript.version,
            actor_id="therapist-demo",
            audit_action="transcript.update",
            audit_message="Synthetic transcript updated.",
        )
        transcript_updated.set()

    with ThreadPoolExecutor(max_workers=2) as executor:
        draft_future = executor.submit(save_draft)
        update_future = executor.submit(update_transcript)
        assert draft_future.result(timeout=2) == "conflict"
        update_future.result(timeout=2)

    assert repo.speaker_mappings == {}
    assert not any(event["action"] == "speaker_mapping.draft_save" for event in repo.audit_log)


def test_repository_normalizes_direct_draft_save_to_unconfirmed_draft() -> None:
    repo = MockRepository()
    transcript = _persisted_transcript(repo)
    direct_mapping = SpeakerMapping(
        mapping_id=repo.new_id("speaker_mapping"),
        organization_id="client-controlled-org",
        transcript_id=transcript.transcript_id,
        source_transcript_version=transcript.version,
        applied_transcript_version=transcript.version,
        status=MappingPersistedStatus.confirmed,
        confirmed_by_user_id="client-controlled-user",
        confirmed_by_role="client-controlled-role",
        confirmed_at=transcript.created_at,
        entries=derive_mapping_draft(transcript).entries,
    )

    saved = repo.save_speaker_mapping_draft(
        direct_mapping,
        expected_mapping_version=None,
        actor_id="therapist-demo",
    )

    assert saved.status == MappingPersistedStatus.draft
    assert saved.applied_transcript_version is None
    assert saved.confirmed_by_user_id is None
    assert saved.confirmed_by_role is None
    assert saved.confirmed_at is None


def test_json_mapping_failure_does_not_erase_concurrent_audit(tmp_path, monkeypatch) -> None:
    path = tmp_path / "speaker-mapping.json"
    repo = JsonFileRepository(path)
    transcript = _persisted_transcript(repo)
    failure_started = threading.Event()
    allow_failure = threading.Event()
    replace_calls = 0

    def fail_first_replace(*args, **kwargs):
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 1:
            failure_started.set()
            assert allow_failure.wait(timeout=1)
            raise OSError("replace failed")
        return original_replace(*args, **kwargs)

    original_replace = mock_repository_module.os.replace
    monkeypatch.setattr(mock_repository_module.os, "replace", fail_first_replace)

    def save_mapping() -> str:
        try:
            save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript))
        except OSError:
            return "failed"
        return "saved"

    with ThreadPoolExecutor(max_workers=2) as executor:
        mapping_future = executor.submit(save_mapping)
        assert failure_started.wait(timeout=1)
        audit_future = executor.submit(
            repo.add_audit,
            "speaker_mapping.concurrent_audit",
            "mapping_audit_target",
            "Concurrent operational audit.",
        )
        allow_failure.set()
        assert mapping_future.result(timeout=2) == "failed"
        audit_future.result(timeout=2)

    assert any(event["action"] == "speaker_mapping.concurrent_audit" for event in repo.audit_log)
    reopened = JsonFileRepository(path)
    assert any(event["action"] == "speaker_mapping.concurrent_audit" for event in reopened.audit_log)


def test_json_repository_snapshot_is_private_and_leaves_no_temp_file(tmp_path) -> None:
    path = tmp_path / "speaker-mapping.json"
    JsonFileRepository(path)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert not list(tmp_path.glob(".*.tmp"))
