from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import stat
import threading

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.repositories.mock_repository as mock_repository_module
from app.schemas.clinical import (
    AttestationRequest,
    AiReview,
    FeatureExtractionRequest,
    FeatureSet,
    MLResult,
    OrganizationMembershipCreate,
    QaStatus,
    Report,
    ReviewStatus,
    TherapySession,
    TherapySessionUpdate,
    Transcript,
    TranscriptPatch,
    TranscriptMergeRequest,
    TranscriptSplitRequest,
    Utterance,
)
from app.repositories.base import SpeakerMappingVersionConflictError, TranscriptVersionConflictError
from app.repositories.mock_repository import JsonFileRepository, JsonRepositoryDurabilityError, MockRepository
from app.api.v1.dependencies import get_repository
from app.main import app
from app.services.speaker_mapping_service import (
    SpeakerMappingError,
    build_confirmed_transcript,
    confirm_mapping,
    derive_mapping_draft,
    get_mapping,
    require_confirmed_mapping,
    requires_speaker_mapping,
    save_mapping_draft,
    validate_mapping_confirmation,
)
from app.schemas.speaker_mapping import (
    MappingPersistedStatus,
    SpeakerMapping,
    SpeakerMappingConfirmRequest,
    SpeakerMappingDraftUpdate,
)
from app.services.feature_service import extract_features
from app.services.transcript_service import attest, export_cha, merge_utterances, patch_transcript, run_qa, split_utterance
import app.services.feature_service as feature_service_module
import app.services.transcript_service as transcript_service_module


def _route_client(repo: MockRepository) -> TestClient:
    app.dependency_overrides[get_repository] = lambda: repo
    return TestClient(app)


def _route_headers(*, user_id: str = "therapist-demo", claimed_role: str = "therapist") -> dict[str, str]:
    return {
        "x-mock-user-id": user_id,
        "x-mock-role": claimed_role,
        "x-organization-id": "pilot_org_001",
    }


def _clear_route_overrides() -> None:
    app.dependency_overrides.clear()


def _seed_route_temporary_asr_transcript(repo: MockRepository) -> Transcript:
    transcript = Transcript(
        transcript_id=repo.new_id("transcript"),
        session_id="session_demo_001",
        case_id="case_demo_001",
        organization_id="pilot_org_001",
        source="asr_draft:synthetic",
        raw_text="*UNK:\tSynthetic sample.\n",
        utterances=[
            _utterance(0, temporary_speaker_id="tmp-a", source_speaker_label="Synthetic A"),
            _utterance(1, temporary_speaker_id="tmp-b", source_speaker_label="Synthetic B"),
        ],
    )
    return repo.create_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="therapist-demo",
        audit_action="transcript.create",
        audit_message="Synthetic transcript created.",
    )


def _save_route_mapping_draft(client: TestClient, transcript_id: str, headers: dict[str, str]) -> dict:
    current = client.get(f"/api/v1/transcripts/{transcript_id}/speaker-mapping", headers=headers)
    assert current.status_code == 200
    return client.put(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping",
        headers=headers,
        json={
            "expected_transcript_version": current.json()["source_transcript_version"],
            "entries": [
                {
                    "temporary_speaker_id": "tmp-a",
                    "confirmed_chat_code": "CHI",
                    "participant_role": "target_child",
                    "reviewed_utterance_ids": ["utt-0"],
                    "source_speaker_label": "forged provider label",
                    "provider_metadata": {"provider_id": "forged"},
                },
                {
                    "temporary_speaker_id": "tmp-b",
                    "confirmed_chat_code": "THER",
                    "participant_role": "therapist",
                    "reviewed_utterance_ids": ["utt-1"],
                },
            ],
        },
    ).json()


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
    repo.cases[transcript.case_id].latest_session_status = ReviewStatus.attested

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


def test_stale_json_repository_cannot_overwrite_mapping_confirmation(tmp_path) -> None:
    path = tmp_path / "speaker-mapping-generation.json"
    first = JsonFileRepository(path)
    transcript, draft, request = _ready_confirmation(first)
    stale = JsonFileRepository(path)

    confirmed = confirm_mapping(
        first,
        transcript.transcript_id,
        request,
        actor_id="therapist-demo",
        actor_role="therapist",
    )
    with pytest.raises(SpeakerMappingError) as exc_info:
        confirm_mapping(
            stale,
            transcript.transcript_id,
            request,
            actor_id="therapist-demo",
            actor_role="therapist",
        )
    assert exc_info.value.code == "SPEAKER_MAPPING_REQUIRED"

    reopened = JsonFileRepository(path)
    restored = reopened.get_latest_speaker_mapping(transcript.transcript_id)
    assert restored is not None
    assert restored.mapping_version == confirmed.mapping_version
    assert restored.status == MappingPersistedStatus.confirmed


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
    assert get_mapping(repo, transcript.transcript_id).effective_status == "stale"


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


def test_json_file_fsync_failure_keeps_old_mapping_and_audit_state(tmp_path, monkeypatch) -> None:
    path = tmp_path / "speaker-mapping.json"
    repo = JsonFileRepository(path)
    transcript = _persisted_transcript(repo)
    mappings_before = deepcopy(repo.speaker_mappings)
    audit_before = list(repo.audit_log)

    def fail_file_fsync(_fd: int) -> None:
        raise OSError("file fsync failed")

    monkeypatch.setattr(mock_repository_module.os, "fsync", fail_file_fsync)

    with pytest.raises(OSError, match="file fsync failed"):
        save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript))

    assert repo.speaker_mappings == mappings_before
    assert repo.audit_log == audit_before
    assert JsonFileRepository(path).speaker_mappings == mappings_before
    assert not list(tmp_path.glob(".*.tmp"))


def test_json_directory_fsync_failure_keeps_committed_mapping_and_audit_state(tmp_path, monkeypatch) -> None:
    path = tmp_path / "speaker-mapping.json"
    repo = JsonFileRepository(path)
    transcript = _persisted_transcript(repo)
    original_fsync = mock_repository_module.os.fsync
    fsync_calls = 0

    def fail_directory_fsync(fd: int) -> None:
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 2:
            raise OSError("directory fsync failed")
        original_fsync(fd)

    monkeypatch.setattr(mock_repository_module.os, "fsync", fail_directory_fsync)

    with pytest.raises(JsonRepositoryDurabilityError, match="directory durability"):
        save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript))

    assert len(repo.speaker_mappings) == 1
    assert any(event["action"] == "speaker_mapping.draft_save" for event in repo.audit_log)
    reopened = JsonFileRepository(path)
    assert reopened.speaker_mappings == repo.speaker_mappings
    assert reopened.audit_log == repo.audit_log
    assert not list(tmp_path.glob(".*.tmp"))


def _complete_entries(*, speaker_count: int = 2) -> list[dict]:
    entries = [
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
    ]
    if speaker_count >= 3:
        entries.append(
            {
                "temporary_speaker_id": "tmp-c",
                "confirmed_chat_code": "OTH",
                "participant_role": "other",
                "reviewed_utterance_ids": ["utt-2"],
            }
        )
    return entries


def _ready_confirmation(repo: MockRepository, *, speaker_count: int = 2):
    transcript = _transcript(
        utterances=[
            _utterance(index, temporary_speaker_id=f"tmp-{chr(97 + index)}", source_speaker_label=f"ASR {index}")
            for index in range(speaker_count)
        ],
    )
    transcript.raw_text = (
        "@Begin\n@Languages:\ttha, eng\n@Participants:\tOLD Prior Adult\n"
        "@ID:\ttha|Legacy|OLD|||||Adult|||\n@Media:\tsynthetic_session, audio\n@End"
    )
    transcript.qa_status = QaStatus.pass_
    transcript.therapist_attested = True
    transcript.attestation_reason = "Previously reviewed."
    transcript.review_status = ReviewStatus.attested
    repo.create_transcript(
        transcript,
        session_status=ReviewStatus.attested,
        actor_id="therapist-demo",
        audit_action="transcript.create",
        audit_message="Synthetic transcript created.",
    )
    draft = save_mapping_draft(
        repo,
        transcript.transcript_id,
        _draft_update(transcript, entries=_complete_entries(speaker_count=speaker_count)),
        actor_id="therapist-demo",
    )
    request = SpeakerMappingConfirmRequest(
        expected_transcript_version=transcript.version,
        expected_mapping_version=draft.mapping_version,
    )
    return transcript, draft, request


@pytest.mark.parametrize(
    ("entries", "expected_code"),
    [
        (_complete_entries()[:1], "SPEAKER_MAPPING_INCOMPLETE"),
        ([{**_complete_entries()[0], "confirmed_chat_code": None}, _complete_entries()[1]], "SPEAKER_MAPPING_INCOMPLETE"),
        ([{**_complete_entries()[0], "participant_role": None}, _complete_entries()[1]], "SPEAKER_MAPPING_INCOMPLETE"),
        ([{**_complete_entries()[0], "reviewed_utterance_ids": []}, _complete_entries()[1]], "SPEAKER_MAPPING_INCOMPLETE"),
        ([{**_complete_entries()[0], "reviewed_utterance_ids": ["utt-0", "extra"]}, _complete_entries()[1]], "SPEAKER_MAPPING_INCOMPLETE"),
        ([{**_complete_entries()[0], "confirmed_chat_code": "OTH", "participant_role": "other"}, _complete_entries()[1]], "SPEAKER_MAPPING_TARGET_REQUIRED"),
        ([{**_complete_entries()[1], "temporary_speaker_id": "tmp-a", "reviewed_utterance_ids": ["utt-0"]}, _complete_entries()[1]], "SPEAKER_MAPPING_DUPLICATE_CODE"),
    ],
)
def test_confirmation_validation_fails_closed_with_stable_codes(entries, expected_code) -> None:
    transcript = _transcript(
        utterances=[
            _utterance(0, temporary_speaker_id="tmp-a"),
            _utterance(1, temporary_speaker_id="tmp-b"),
        ]
    )
    derived = derive_mapping_draft(transcript)
    server_entries = {entry.temporary_speaker_id: entry for entry in derived.entries}
    completed_entries = []
    for entry in entries:
        server_entry = server_entries.get(entry["temporary_speaker_id"])
        completed_entries.append(
            {
                **(server_entry.model_dump() if server_entry is not None else {}),
                **entry,
            }
        )
    mapping = SpeakerMapping.model_validate({**derived.model_dump(), "entries": completed_entries})

    with pytest.raises(SpeakerMappingError) as exc_info:
        validate_mapping_confirmation(transcript, mapping)

    assert exc_info.value.code == expected_code
    assert str(exc_info.value) == exc_info.value.message
    assert "Synthetic sample" not in str(exc_info.value)


def test_confirmation_rejects_more_than_three_speakers_without_merge_or_split() -> None:
    transcript = _transcript(
        utterances=[_utterance(index, temporary_speaker_id=f"tmp-{index}") for index in range(4)]
    )
    mapping = derive_mapping_draft(transcript)

    with pytest.raises(SpeakerMappingError) as exc_info:
        validate_mapping_confirmation(transcript, mapping)

    assert exc_info.value.code == "SPEAKER_MAPPING_INCOMPLETE"


@pytest.mark.parametrize("speaker_count", [2, 3])
def test_confirm_mapping_rebuilds_chat_and_resets_review_state(speaker_count: int) -> None:
    repo = MockRepository()
    transcript, draft, request = _ready_confirmation(repo, speaker_count=speaker_count)

    response = confirm_mapping(
        repo,
        transcript.transcript_id,
        request,
        actor_id="therapist-demo",
        actor_role="therapist",
    )

    saved = repo.get_transcript(transcript.transcript_id)
    assert saved is not None
    assert saved.version == transcript.version + 1
    assert [str(item.speaker) for item in saved.utterances] == ["CHI", "THER"] + (["OTH"] if speaker_count == 3 else [])
    assert [item.temporary_speaker_id for item in saved.utterances] == [f"tmp-{chr(97 + index)}" for index in range(speaker_count)]
    assert [item.source_speaker_label for item in saved.utterances] == [f"ASR {index}" for index in range(speaker_count)]
    assert "@Languages:\ttha, eng" in saved.raw_text
    assert "@Participants:\tCHI Child Target_Child, THER Therapist Therapist" in saved.raw_text
    if speaker_count == 3:
        assert ", OTH Other Other" in saved.raw_text
    assert "|OLD|" not in saved.raw_text
    assert "*CHI:\tSynthetic sample 0 ." in saved.raw_text
    assert "*THER:\tSynthetic sample 1 ." in saved.raw_text
    assert "@Media:\tsynthetic_session, audio" in saved.raw_text
    assert saved.qa_status == QaStatus.not_run
    assert saved.qa_issues == []
    assert saved.therapist_attested is False
    assert saved.attestation_reason == ""
    assert saved.review_status == ReviewStatus.needs_review
    assert repo.sessions[saved.session_id].status == ReviewStatus.needs_review
    assert repo.cases[saved.case_id].latest_session_status == ReviewStatus.needs_review
    assert response.mapping_id == draft.mapping_id
    assert response.status == MappingPersistedStatus.confirmed
    assert response.mapping_version == draft.mapping_version + 1
    assert response.applied_transcript_version == saved.version
    assert response.confirmed_by_user_id == "therapist-demo"
    assert response.confirmed_by_role == "therapist"
    assert response.confirmed_at is not None
    assert response.effective_status == "confirmed"

    event = repo.audit_log[-1]
    assert event["action"] == "speaker_mapping.confirm"
    assert event["actor_id"] == "therapist-demo"
    assert event["target_id"] == draft.mapping_id
    assert event["correlation_id"] != "local"
    assert transcript.raw_text not in event["message"]
    assert "Synthetic sample" not in event["message"]


def test_confirmation_rejects_code_role_mismatch() -> None:
    transcript = _transcript(
        utterances=[
            _utterance(0, temporary_speaker_id="tmp-a"),
            _utterance(1, temporary_speaker_id="tmp-b"),
        ]
    )
    derived = derive_mapping_draft(transcript)
    entries = [
        derived.entries[0].model_copy(
            update={
                "confirmed_chat_code": "CHI",
                "participant_role": "target_child",
                "reviewed_utterance_ids": ["utt-0"],
            }
        ),
        derived.entries[1].model_copy(
            update={
                "confirmed_chat_code": "THER",
                "participant_role": "other",
                "reviewed_utterance_ids": ["utt-1"],
            }
        ),
    ]
    mapping = SpeakerMapping.model_validate({**derived.model_dump(), "entries": entries})

    with pytest.raises(SpeakerMappingError) as exc_info:
        validate_mapping_confirmation(transcript, mapping)

    assert exc_info.value.code == "SPEAKER_MAPPING_INCOMPLETE"


def test_confirmation_normalizes_padded_temporary_id_without_changing_provenance() -> None:
    repo = MockRepository()
    transcript = _transcript(
        utterances=[
            _utterance(0, temporary_speaker_id=" tmp-a ", source_speaker_label="ASR A"),
            _utterance(1, temporary_speaker_id="tmp-b", source_speaker_label="ASR B"),
        ]
    )
    repo.create_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="therapist-demo",
        audit_action="transcript.create",
        audit_message="Synthetic transcript created.",
    )
    draft = save_mapping_draft(
        repo,
        transcript.transcript_id,
        _draft_update(transcript, entries=_complete_entries()),
        actor_id="therapist-demo",
    )

    confirm_mapping(
        repo,
        transcript.transcript_id,
        SpeakerMappingConfirmRequest(
            expected_transcript_version=transcript.version,
            expected_mapping_version=draft.mapping_version,
        ),
        actor_id="therapist-demo",
        actor_role="therapist",
    )

    saved = repo.get_transcript(transcript.transcript_id)
    assert saved is not None
    assert [str(item.speaker) for item in saved.utterances] == ["CHI", "THER"]
    assert saved.utterances[0].temporary_speaker_id == " tmp-a "
    assert saved.utterances[0].source_speaker_label == "ASR A"


def test_confirmation_rejects_mixed_missing_temporary_id_without_any_mutation() -> None:
    repo = MockRepository()
    transcript = _transcript(
        utterances=[
            _utterance(0, temporary_speaker_id="tmp-a", source_speaker_label="ASR A"),
            _utterance(1, temporary_speaker_id="   ", source_speaker_label="ASR missing"),
        ]
    )
    repo.create_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="therapist-demo",
        audit_action="transcript.create",
        audit_message="Synthetic transcript created.",
    )
    draft = save_mapping_draft(
        repo,
        transcript.transcript_id,
        _draft_update(transcript, entries=[_complete_entries()[0]]),
        actor_id="therapist-demo",
    )
    _attach_downstream_outputs(repo, transcript, ReviewStatus.draft)
    before = deepcopy(repo.snapshot())

    with pytest.raises(SpeakerMappingError) as exc_info:
        confirm_mapping(
            repo,
            transcript.transcript_id,
            SpeakerMappingConfirmRequest(
                expected_transcript_version=transcript.version,
                expected_mapping_version=draft.mapping_version,
            ),
            actor_id="therapist-demo",
            actor_role="therapist",
        )

    assert exc_info.value.code == "SPEAKER_MAPPING_INCOMPLETE"
    assert repo.snapshot() == before


def test_duplicate_utterance_ids_fail_confirmation_without_mutation() -> None:
    repo = MockRepository()
    transcript = _transcript(
        utterances=[
            _utterance(0, temporary_speaker_id="tmp-a"),
            _utterance(0, temporary_speaker_id="tmp-b"),
        ]
    )
    repo.create_transcript(transcript, session_status=ReviewStatus.needs_review, actor_id="therapist-demo", audit_action="transcript.create", audit_message="Synthetic transcript created.")
    draft = save_mapping_draft(repo, transcript.transcript_id, _draft_update(transcript, entries=[
        _complete_entries()[0], {**_complete_entries()[1], "reviewed_utterance_ids": ["utt-0"]}
    ]))
    before = deepcopy(repo.snapshot())

    with pytest.raises(SpeakerMappingError) as exc_info:
        confirm_mapping(repo, transcript.transcript_id, SpeakerMappingConfirmRequest(expected_transcript_version=1, expected_mapping_version=draft.mapping_version), actor_id="therapist-demo", actor_role="therapist")

    assert exc_info.value.code == "SPEAKER_MAPPING_INCOMPLETE"
    assert repo.snapshot() == before


def test_asr_patch_preserves_server_provenance_and_rejects_raw_text() -> None:
    repo = MockRepository()
    transcript, _draft, _request = _ready_confirmation(repo)
    before = deepcopy(repo.snapshot())
    with pytest.raises(ValueError):
        patch_transcript(repo, transcript.transcript_id, TranscriptPatch(raw_text="@Begin\n@End"))
    assert repo.snapshot() == before
    with pytest.raises(ValueError):
        patch_transcript(repo, transcript.transcript_id, TranscriptPatch(utterances=transcript.utterances[:1]))
    assert repo.snapshot() == before

    submitted = [item.model_copy(update={"temporary_speaker_id": None, "source_speaker_label": "forged"}) for item in transcript.utterances]
    saved = patch_transcript(repo, transcript.transcript_id, TranscriptPatch(utterances=submitted))
    assert [item.temporary_speaker_id for item in saved.utterances] == ["tmp-a", "tmp-b"]
    assert [item.source_speaker_label for item in saved.utterances] == ["ASR 0", "ASR 1"]
    with pytest.raises(SpeakerMappingError) as exc_info:
        require_confirmed_mapping(repo, saved)
    assert exc_info.value.code == "SPEAKER_MAPPING_STALE"


def test_split_and_merge_preserve_and_require_compatible_temporary_clusters() -> None:
    repo = MockRepository()
    transcript, _draft, _request = _ready_confirmation(repo)
    split = split_utterance(repo, transcript.transcript_id, TranscriptSplitRequest(utterance_id="utt-0", split_at_character=9))
    assert [item.temporary_speaker_id for item in split.utterances[:2]] == ["tmp-a", "tmp-a"]
    assert [item.source_speaker_label for item in split.utterances[:2]] == ["ASR 0", "ASR 0"]
    merged = merge_utterances(repo, transcript.transcript_id, TranscriptMergeRequest(first_utterance_id="utt-0_a", second_utterance_id="utt-0_b"))
    assert merged.utterances[0].temporary_speaker_id == "tmp-a"
    before = deepcopy(repo.snapshot())
    with pytest.raises(ValueError):
        merge_utterances(repo, transcript.transcript_id, TranscriptMergeRequest(first_utterance_id="utt-0_a", second_utterance_id="utt-1"))
    assert repo.snapshot() == before


def test_post_confirmation_patch_cannot_erase_provenance_or_bypass_stale_gate() -> None:
    repo = MockRepository()
    transcript, _draft, request = _ready_confirmation(repo)
    confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")
    current = repo.get_transcript(transcript.transcript_id)
    assert current is not None
    submitted = [item.model_copy(update={"temporary_speaker_id": "forged", "source_speaker_label": None}) for item in current.utterances]
    saved = patch_transcript(repo, current.transcript_id, TranscriptPatch(utterances=submitted))
    assert [item.temporary_speaker_id for item in saved.utterances] == ["tmp-a", "tmp-b"]
    assert [item.source_speaker_label for item in saved.utterances] == ["ASR 0", "ASR 1"]
    with pytest.raises(SpeakerMappingError) as exc_info:
        require_confirmed_mapping(repo, saved)
    assert exc_info.value.code == "SPEAKER_MAPPING_STALE"


def test_repository_confirmation_rebuilds_from_authoritative_current_and_draft() -> None:
    for forged_field in ("mapping", "transcript"):
        repo = MockRepository()
        transcript, draft, _request = _ready_confirmation(repo)
        replacement = build_confirmed_transcript(transcript, draft)
        submitted_mapping = SpeakerMapping.model_validate({**draft.model_dump(), "status": "confirmed", "applied_transcript_version": replacement.version, "confirmed_by_user_id": "therapist-demo", "confirmed_by_role": "therapist", "confirmed_at": transcript.created_at})
        if forged_field == "mapping":
            submitted_mapping = submitted_mapping.model_copy(update={"entries": [entry.model_copy(update={"confirmed_chat_code": "OTH", "participant_role": "other"}) for entry in submitted_mapping.entries]})
        else:
            replacement = replacement.model_copy(update={"raw_text": "FORGED", "utterances": [item.model_copy(update={"speaker": "OTH"}) for item in replacement.utterances]})
        before = deepcopy(repo.snapshot())

        with pytest.raises(SpeakerMappingVersionConflictError):
            repo.confirm_speaker_mapping(submitted_mapping, replacement, expected_transcript_version=1, expected_mapping_version=draft.mapping_version, actor_id="therapist-demo")

        assert repo.snapshot() == before


def test_confirmation_replaces_stale_parser_and_qa_metadata_coherently() -> None:
    repo = MockRepository()
    transcript, _draft, request = _ready_confirmation(repo)
    stored = repo.transcripts[transcript.transcript_id]
    stored.chat_metadata["qa_override"] = {"reason": "stale"}
    stored.chat_metadata.update({
        "asr_provider": "synthetic-provider",
        "asr_provider_version": "v1",
        "audio_file_id": "audio_synthetic_001",
        "word_timestamps_available": True,
        "task": "play",
        "activity": "story",
        "participants": [{"code": "OLD"}],
        "languages": ["stale"],
    })
    stored.malformed_lines = [{"line_number": 1, "raw_text": "stale"}]
    from app.schemas.clinical import OrphanDependentTier
    stored.orphan_dependent_tiers = [OrphanDependentTier(tier="%mor", raw_text="stale", line_number=1)]

    confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")
    saved = repo.get_transcript(transcript.transcript_id)
    assert saved is not None
    assert "qa_override" not in saved.chat_metadata
    for key in ("asr_provider", "asr_provider_version", "audio_file_id", "word_timestamps_available", "task", "activity"):
        assert saved.chat_metadata[key] == stored.chat_metadata[key]
    assert saved.chat_metadata["languages"] == ["tha", "eng"]
    assert [item["code"] for item in saved.chat_metadata["participants"]] == ["CHI", "THER"]
    assert saved.malformed_lines == []
    assert saved.orphan_dependent_tiers == []
    assert run_qa(repo, transcript.transcript_id).transcript_id == transcript.transcript_id
    assert export_cha(repo, transcript.transcript_id).cha_text == saved.raw_text


def test_older_session_confirmation_preserves_newer_case_summaries() -> None:
    repo = MockRepository()
    transcript, _draft, request = _ready_confirmation(repo)
    _attach_downstream_outputs(repo, transcript, ReviewStatus.draft)
    newer = TherapySession(session_id="session_newer_001", case_id=transcript.case_id, session_date="2026-06-13", session_type="therapy_session", status=ReviewStatus.attested, report_id="report_newer_001")
    repo.sessions[newer.session_id] = newer
    repo.reports["report_newer_001"] = Report(report_id="report_newer_001", session_id=newer.session_id, case_id=transcript.case_id, report_type="synthetic", title="Newer", markdown="Newer", html="<p>Newer</p>", status=ReviewStatus.signed_off)
    case = repo.cases[transcript.case_id]
    case.latest_session_date = newer.session_date
    case.latest_session_status = newer.status
    case.latest_report_status = ReviewStatus.signed_off

    confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")

    assert case.latest_session_date == newer.session_date
    assert case.latest_session_status == ReviewStatus.attested
    assert case.latest_report_status == ReviewStatus.signed_off


@pytest.mark.parametrize("action_name", ["qa", "attest", "export", "features"])
def test_workflow_gate_race_uses_confirmed_clone_or_rejects_stale_write(action_name: str, monkeypatch) -> None:
    repo = MockRepository()
    transcript, _draft, request = _ready_confirmation(repo)
    confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")
    if action_name in {"attest", "features"}:
        run_qa(repo, transcript.transcript_id)
    if action_name == "features":
        attest(repo, transcript.transcript_id, AttestationRequest(), actor_id="therapist-demo")
    confirmed = repo.get_transcript(transcript.transcript_id)
    assert confirmed is not None
    old_raw_text = confirmed.raw_text
    gated = threading.Event()
    resume = threading.Event()
    module = feature_service_module if action_name == "features" else transcript_service_module
    original_gate = module.require_confirmed_mapping

    def paused_gate(target_repo, target_transcript):
        original_gate(target_repo, target_transcript)
        gated.set()
        assert resume.wait(timeout=2)

    monkeypatch.setattr(module, "require_confirmed_mapping", paused_gate)
    if action_name == "qa":
        action = lambda: run_qa(repo, transcript.transcript_id)
    elif action_name == "attest":
        action = lambda: attest(repo, transcript.transcript_id, AttestationRequest(), actor_id="therapist-demo")
    elif action_name == "export":
        action = lambda: export_cha(repo, transcript.transcript_id)
    else:
        action = lambda: extract_features(repo, transcript.transcript_id, FeatureExtractionRequest())

    with ThreadPoolExecutor(max_workers=2) as executor:
        future = executor.submit(action)
        assert gated.wait(timeout=2)
        edited = patch_transcript(repo, transcript.transcript_id, TranscriptPatch(utterances=[item.model_copy(update={"text": item.text + " concurrent"}) for item in confirmed.utterances]))
        resume.set()
        if action_name == "export":
            result = future.result(timeout=2)
            assert result.cha_text == old_raw_text
            assert "concurrent" not in result.cha_text
        else:
            with pytest.raises((TranscriptVersionConflictError, ValueError)):
                future.result(timeout=2)
            assert repo.get_transcript(transcript.transcript_id).version == edited.version


def test_attest_rechecks_mapping_after_automatic_qa_before_fresh_read(monkeypatch) -> None:
    repo = MockRepository()
    transcript, _draft, request = _ready_confirmation(repo)
    confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")
    qa_finished = threading.Event()
    resume = threading.Event()
    original_run_qa = transcript_service_module.run_qa

    def paused_run_qa(*args, **kwargs):
        result = original_run_qa(*args, **kwargs)
        qa_finished.set()
        assert resume.wait(timeout=2)
        return result

    monkeypatch.setattr(transcript_service_module, "run_qa", paused_run_qa)
    before_attest_audits = len([event for event in repo.audit_log if event["action"] == "transcript.attest"])
    with ThreadPoolExecutor(max_workers=2) as executor:
        future = executor.submit(attest, repo, transcript.transcript_id, AttestationRequest(), actor_id="therapist-demo")
        assert qa_finished.wait(timeout=2)
        current = repo.get_transcript(transcript.transcript_id)
        assert current is not None
        edited = patch_transcript(repo, transcript.transcript_id, TranscriptPatch(utterances=[item.model_copy(update={"text": item.text + " raced"}) for item in current.utterances]))
        resume.set()
        with pytest.raises(SpeakerMappingError) as exc_info:
            future.result(timeout=2)
    assert exc_info.value.code == "SPEAKER_MAPPING_STALE"
    assert repo.get_transcript(transcript.transcript_id).version == edited.version
    assert len([event for event in repo.audit_log if event["action"] == "transcript.attest"]) == before_attest_audits


def test_feature_persistence_lock_prevents_stale_attachment_during_patch(monkeypatch) -> None:
    repo = MockRepository()
    transcript, _draft, request = _ready_confirmation(repo)
    confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")
    run_qa(repo, transcript.transcript_id)
    attest(repo, transcript.transcript_id, AttestationRequest(), actor_id="therapist-demo")
    current = repo.get_transcript(transcript.transcript_id)
    assert current is not None
    version_read = threading.Event()
    resume_feature = threading.Event()
    patch_started = threading.Event()
    original_transcripts = repo.transcripts
    feature_get_count = 0

    class PausingTranscripts(dict):
        def get(self, key, default=None):
            nonlocal feature_get_count
            value = super().get(key, default)
            if key == transcript.transcript_id and threading.current_thread().name.startswith("feature-worker"):
                feature_get_count += 1
                if feature_get_count == 2:
                    version_read.set()
                    assert resume_feature.wait(timeout=2)
            return value

    repo.transcripts = PausingTranscripts(original_transcripts)
    def concurrent_patch():
        patch_started.set()
        return patch_transcript(repo, transcript.transcript_id, TranscriptPatch(utterances=[item.model_copy(update={"text": item.text + " raced"}) for item in current.utterances]))

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="feature-worker") as feature_executor, ThreadPoolExecutor(max_workers=1, thread_name_prefix="patch-worker") as patch_executor:
        feature_future = feature_executor.submit(extract_features, repo, transcript.transcript_id, FeatureExtractionRequest())
        assert version_read.wait(timeout=2)
        patch_future = patch_executor.submit(concurrent_patch)
        assert patch_started.wait(timeout=2)
        resume_feature.set()
        feature = feature_future.result(timeout=2)
        patch_future.result(timeout=2)

    assert repo.features[feature.feature_set_id].review_status == ReviewStatus.stale


@pytest.mark.parametrize("repository_kind", ["mock", "json"])
def test_failed_feature_audit_cannot_erase_concurrent_session_update(repository_kind: str, tmp_path, monkeypatch) -> None:
    path = tmp_path / "feature-rollback.json"
    repo = JsonFileRepository(path) if repository_kind == "json" else MockRepository()
    transcript, _draft, request = _ready_confirmation(repo)
    confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")
    run_qa(repo, transcript.transcript_id)
    attest(repo, transcript.transcript_id, AttestationRequest(), actor_id="therapist-demo")
    feature_audit_started = threading.Event()
    updater_reached_audit = threading.Event()
    original_validate = mock_repository_module.validate_audit_event

    def coordinated_validation(**kwargs):
        if kwargs["action"] == "features.extract":
            feature_audit_started.set()
            updater_reached_audit.wait(timeout=0.5)
            raise RuntimeError("injected feature audit failure")
        if kwargs["action"] == "session.patch":
            updater_reached_audit.set()
        return original_validate(**kwargs)

    monkeypatch.setattr(mock_repository_module, "validate_audit_event", coordinated_validation)
    with ThreadPoolExecutor(max_workers=2) as executor:
        feature_future = executor.submit(extract_features, repo, transcript.transcript_id, FeatureExtractionRequest())
        assert feature_audit_started.wait(timeout=2)
        update_future = executor.submit(
            repo.update_session,
            transcript.session_id,
            TherapySessionUpdate(notes="Concurrent safe update"),
            expected_version=repo.sessions[transcript.session_id].version,
            actor_id="therapist-demo",
        )
        with pytest.raises(RuntimeError, match="injected feature audit failure"):
            feature_future.result(timeout=3)
        updated = update_future.result(timeout=3)

    assert updated.notes == "Concurrent safe update"
    assert repo.sessions[transcript.session_id].notes == "Concurrent safe update"
    assert repo.sessions[transcript.session_id].feature_set_id is None
    assert repo.features == {}
    assert any(event["action"] == "session.patch" for event in repo.audit_log)
    assert not any(event["action"] == "features.extract" for event in repo.audit_log)
    if repository_kind == "json":
        reopened = JsonFileRepository(path)
        assert reopened.sessions[transcript.session_id].notes == "Concurrent safe update"
        assert reopened.sessions[transcript.session_id].feature_set_id is None
        assert reopened.features == {}


@pytest.mark.parametrize("conflict", ["transcript", "mapping"])
def test_confirmation_version_conflict_has_zero_mutation_or_audit(conflict: str) -> None:
    repo = MockRepository()
    transcript, _draft, request = _ready_confirmation(repo)
    before = deepcopy(repo.snapshot())
    request = request.model_copy(
        update={
            "expected_transcript_version": request.expected_transcript_version + (1 if conflict == "transcript" else 0),
            "expected_mapping_version": request.expected_mapping_version + (1 if conflict == "mapping" else 0),
        }
    )

    with pytest.raises(SpeakerMappingError) as exc_info:
        confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")

    assert exc_info.value.code == "SPEAKER_MAPPING_VERSION_CONFLICT"
    assert repo.snapshot() == before


def test_confirmation_audit_validation_failure_rolls_back_everything(monkeypatch) -> None:
    repo = MockRepository()
    transcript, _draft, request = _ready_confirmation(repo)
    before = deepcopy(repo.snapshot())

    def fail_audit(**_kwargs):
        raise ValueError("injected audit failure")

    monkeypatch.setattr(mock_repository_module, "validate_audit_event", fail_audit)
    with pytest.raises(ValueError, match="injected audit failure"):
        confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")

    assert repo.snapshot() == before


def test_mapping_gate_required_stale_current_and_compatibility_bypass() -> None:
    repo = MockRepository()
    transcript, _draft, request = _ready_confirmation(repo)

    with pytest.raises(SpeakerMappingError) as required:
        require_confirmed_mapping(repo, transcript)
    assert required.value.code == "SPEAKER_MAPPING_REQUIRED"

    confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")
    current = repo.get_transcript(transcript.transcript_id)
    assert current is not None
    require_confirmed_mapping(repo, current)

    edited = patch_transcript(
        repo,
        transcript.transcript_id,
        TranscriptPatch(utterances=[item.model_copy(update={"text": item.text + " edited"}) for item in current.utterances]),
    )
    with pytest.raises(SpeakerMappingError) as stale:
        require_confirmed_mapping(repo, edited)
    assert stale.value.code == "SPEAKER_MAPPING_STALE"

    for source in ("manual", "cha_upload:synthetic.cha", "mock_asr_draft:manual", "asr:canonical"):
        bypass = edited.model_copy(update={"source": source})
        require_confirmed_mapping(repo, bypass)


def test_role_dependent_workflow_actions_use_mapping_gate() -> None:
    repo = MockRepository()
    transcript, _draft, _request = _ready_confirmation(repo)

    actions = [
        lambda: run_qa(repo, transcript.transcript_id),
        lambda: attest(repo, transcript.transcript_id, AttestationRequest()),
        lambda: export_cha(repo, transcript.transcript_id),
        lambda: extract_features(repo, transcript.transcript_id, FeatureExtractionRequest()),
    ]
    for action in actions:
        with pytest.raises(SpeakerMappingError) as exc_info:
            action()
        assert exc_info.value.code == "SPEAKER_MAPPING_REQUIRED"


def test_mapping_get_is_read_only_and_put_derives_provider_fields() -> None:
    repo = MockRepository()
    client = _route_client(repo)
    transcript = _seed_route_temporary_asr_transcript(repo)
    headers = _route_headers()
    try:
        mappings_before = len(repo.speaker_mappings)
        audits_before = list(repo.audit_log)
        response = client.get(f"/api/v1/transcripts/{transcript.transcript_id}/speaker-mapping", headers=headers)
        assert response.status_code == 200
        assert response.json()["persisted"] is False
        assert response.json()["required"] is True
        assert len(repo.speaker_mappings) == mappings_before
        assert repo.audit_log == audits_before

        saved = _save_route_mapping_draft(client, transcript.transcript_id, headers)
    finally:
        _clear_route_overrides()

    assert saved["persisted"] is True
    assert saved["entries"][0]["source_speaker_label"] == "Synthetic A"
    assert saved["entries"][0]["provider_metadata"] == {"provider_id": "synthetic"}
    assert saved["entries"][0]["affected_utterance_ids"] == ["utt-0"]
    assert repo.audit_log[-1]["action"] == "speaker_mapping.draft_save"
    assert repo.audit_log[-1]["actor_id"] == "therapist-demo"


def test_mapping_routes_enforce_tenant_consent_and_authoritative_roles() -> None:
    repo = MockRepository()
    client = _route_client(repo)
    transcript = _seed_route_temporary_asr_transcript(repo)
    therapist_headers = _route_headers()
    try:
        foreign = client.get(
            f"/api/v1/transcripts/{transcript.transcript_id}/speaker-mapping",
            headers={**therapist_headers, "x-organization-id": "other_org"},
        )
        assert foreign.status_code == 404

        repo.upsert_membership(
            "pilot_org_001",
            OrganizationMembershipCreate(
                user_id="persisted-supervisor",
                display_name="Synthetic Supervisor",
                role="clinical_supervisor",
            ),
            actor_id="system",
        )
        supervisor_draft = client.put(
            f"/api/v1/transcripts/{transcript.transcript_id}/speaker-mapping",
            headers=_route_headers(user_id="persisted-supervisor", claimed_role="therapist"),
            json={
                "expected_transcript_version": transcript.version,
                "entries": [
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
            },
        )
        assert supervisor_draft.status_code == 200

        confirm_denied = client.post(
            f"/api/v1/transcripts/{transcript.transcript_id}/speaker-mapping/confirm",
            headers=_route_headers(user_id="persisted-supervisor", claimed_role="therapist"),
            json={
                "expected_transcript_version": supervisor_draft.json()["source_transcript_version"],
                "expected_mapping_version": supervisor_draft.json()["mapping_version"],
            },
        )
        assert confirm_denied.status_code == 403

        repo.withdraw_case_consent(
            case_id=transcript.case_id,
            actor_id="therapist-demo",
            redact_notes=False,
        )
        withdrawn_requests = (
            ("get", "", None),
            (
                "put",
                "",
                {
                    "expected_transcript_version": transcript.version,
                    "expected_mapping_version": supervisor_draft.json()["mapping_version"],
                    "entries": [],
                },
            ),
            (
                "post",
                "/confirm",
                {
                    "expected_transcript_version": transcript.version,
                    "expected_mapping_version": supervisor_draft.json()["mapping_version"],
                },
            ),
        )
        for method, suffix, payload in withdrawn_requests:
            withdrawn = client.request(
                method.upper(),
                f"/api/v1/transcripts/{transcript.transcript_id}/speaker-mapping{suffix}",
                headers=therapist_headers,
                json=payload,
            )
            assert withdrawn.status_code == 400
    finally:
        _clear_route_overrides()


def test_mapping_confirmation_uses_persisted_therapist_identity_and_stable_conflicts() -> None:
    repo = MockRepository()
    client = _route_client(repo)
    transcript = _seed_route_temporary_asr_transcript(repo)
    # The header claims supervisor, but the durable membership remains therapist.
    headers = _route_headers(claimed_role="clinical_supervisor")
    try:
        draft = _save_route_mapping_draft(client, transcript.transcript_id, headers)
        conflict = client.post(
            f"/api/v1/transcripts/{transcript.transcript_id}/speaker-mapping/confirm",
            headers=headers,
            json={
                "expected_transcript_version": draft["source_transcript_version"],
                "expected_mapping_version": 0,
            },
        )
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["code"] == "SPEAKER_MAPPING_VERSION_CONFLICT"

        confirmed = client.post(
            f"/api/v1/transcripts/{transcript.transcript_id}/speaker-mapping/confirm",
            headers=headers,
            json={
                "expected_transcript_version": draft["source_transcript_version"],
                "expected_mapping_version": draft["mapping_version"],
                "confirmed_by_user_id": "forged-user",
                "confirmed_by_role": "org_admin",
            },
        )
    finally:
        _clear_route_overrides()

    assert confirmed.status_code == 200
    assert confirmed.json()["confirmed_by_user_id"] == "therapist-demo"
    assert confirmed.json()["confirmed_by_role"] == "therapist"


def test_mapping_gated_action_routes_return_stable_codes_for_required_and_stale_mappings() -> None:
    repo = MockRepository()
    client = _route_client(repo)
    transcript = _seed_route_temporary_asr_transcript(repo)
    headers = _route_headers()
    try:
        for method, suffix, payload in (
            ("post", "qa", None),
            ("post", "attest", {"reason": "Synthetic review."}),
            ("get", "export-cha", None),
            ("post", "extract-features", {}),
        ):
            response = client.request(
                method.upper(),
                f"/api/v1/transcripts/{transcript.transcript_id}/{suffix}",
                headers=headers,
                json=payload,
            )
            assert response.status_code == 400
            assert response.json()["detail"]["code"] == "SPEAKER_MAPPING_REQUIRED"

        draft = _save_route_mapping_draft(client, transcript.transcript_id, headers)
        confirmed = client.post(
            f"/api/v1/transcripts/{transcript.transcript_id}/speaker-mapping/confirm",
            headers=headers,
            json={
                "expected_transcript_version": draft["source_transcript_version"],
                "expected_mapping_version": draft["mapping_version"],
            },
        )
        assert confirmed.status_code == 200
        current = repo.get_transcript(transcript.transcript_id)
        assert current is not None
        stale = patch_transcript(
            repo,
            current.transcript_id,
            TranscriptPatch(utterances=[item.model_copy(update={"text": item.text + " revised"}) for item in current.utterances]),
        )
        response = client.post(f"/api/v1/transcripts/{stale.transcript_id}/qa", headers=headers)
    finally:
        _clear_route_overrides()

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "SPEAKER_MAPPING_STALE"


def _attach_downstream_outputs(repo: MockRepository, transcript: Transcript, report_status: ReviewStatus) -> None:
    session = repo.sessions[transcript.session_id]
    feature = FeatureSet(
        feature_set_id="feature_synthetic_001",
        session_id=session.session_id,
        transcript_id=transcript.transcript_id,
        transcript_version=transcript.version,
        therapist_attested=True,
        features=[],
    )
    ml_result = MLResult(
        result_id="ml_synthetic_001",
        transcript_id=transcript.transcript_id,
        session_id=session.session_id,
        feature_result_id=feature.feature_set_id,
        provider_id="synthetic",
        provider_name="Synthetic",
        provider_version="1",
        input_feature_schema_version="synthetic-v1",
        input_feature_hash="synthetic-hash",
        status="completed",
    )
    ai_review = AiReview(
        ai_review_id="ai_synthetic_001",
        session_id=session.session_id,
        summary="Synthetic summary",
        key_findings=[],
        concerns=[],
        strengths=[],
        limitations=[],
        recommended_review_actions=[],
        confidence_level="low",
        input_transcript_version=transcript.version,
        feature_set_id=feature.feature_set_id,
    )
    report = Report(
        report_id="report_synthetic_001",
        session_id=session.session_id,
        case_id=transcript.case_id,
        report_type="synthetic",
        title="Synthetic report",
        markdown="Synthetic report body",
        html="<p>Synthetic report body</p>",
        status=report_status,
    )
    repo.features[feature.feature_set_id] = feature
    repo.ml_results[ml_result.result_id] = ml_result
    repo.ai_reviews[ai_review.ai_review_id] = ai_review
    repo.reports[report.report_id] = report
    session.feature_set_id = feature.feature_set_id
    session.ml_result_id = ml_result.result_id
    session.ai_review_id = ai_review.ai_review_id
    session.report_id = report.report_id
    repo.cases[transcript.case_id].latest_report_status = report_status


@pytest.mark.parametrize("report_status", [ReviewStatus.draft, ReviewStatus.signed_off])
def test_confirmation_invalidates_downstream_and_preserves_signed_report(report_status: ReviewStatus) -> None:
    repo = MockRepository()
    transcript, _draft, request = _ready_confirmation(repo)
    _attach_downstream_outputs(repo, transcript, report_status)
    old_report_version = repo.reports["report_synthetic_001"].version

    confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")

    assert repo.features["feature_synthetic_001"].review_status == ReviewStatus.stale
    assert repo.ml_results["ml_synthetic_001"].is_current is False
    assert repo.ai_reviews["ai_synthetic_001"].therapist_review_status == ReviewStatus.stale
    report = repo.reports["report_synthetic_001"]
    if report_status == ReviewStatus.signed_off:
        assert report.status == ReviewStatus.signed_off
        assert report.version == old_report_version
        assert repo.cases[transcript.case_id].latest_report_status == ReviewStatus.signed_off
    else:
        assert report.status == ReviewStatus.stale
        assert report.version == old_report_version + 1
        assert repo.cases[transcript.case_id].latest_report_status == ReviewStatus.stale


def test_confirmation_rolls_back_partial_downstream_failure(monkeypatch) -> None:
    repo = MockRepository()
    transcript, _draft, request = _ready_confirmation(repo)
    _attach_downstream_outputs(repo, transcript, ReviewStatus.draft)
    before = deepcopy(repo.snapshot())

    def fail_after_partial_mutation(session):
        repo.features[session.feature_set_id].review_status = ReviewStatus.stale
        raise RuntimeError("injected precommit failure")

    monkeypatch.setattr(repo, "_mark_downstream_outputs_stale", fail_after_partial_mutation)
    with pytest.raises(RuntimeError, match="injected precommit failure"):
        confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")

    assert repo.snapshot() == before


def test_all_role_dependent_actions_are_stale_after_edit_and_pass_after_reconfirmation() -> None:
    repo = MockRepository()
    transcript, _draft, request = _ready_confirmation(repo)
    confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")
    current = repo.get_transcript(transcript.transcript_id)
    assert current is not None
    edited = patch_transcript(
        repo,
        current.transcript_id,
        TranscriptPatch(utterances=[item.model_copy(update={"text": item.text + " edited"}) for item in current.utterances]),
    )

    actions = [
        lambda: run_qa(repo, edited.transcript_id),
        lambda: attest(repo, edited.transcript_id, AttestationRequest()),
        lambda: export_cha(repo, edited.transcript_id),
        lambda: extract_features(repo, edited.transcript_id, FeatureExtractionRequest()),
    ]
    for action in actions:
        with pytest.raises(SpeakerMappingError) as exc_info:
            action()
        assert exc_info.value.code == "SPEAKER_MAPPING_STALE"

    next_draft = save_mapping_draft(
        repo,
        edited.transcript_id,
        _draft_update(edited, entries=_complete_entries()),
        actor_id="therapist-demo",
    )
    confirm_mapping(
        repo,
        edited.transcript_id,
        SpeakerMappingConfirmRequest(
            expected_transcript_version=edited.version,
            expected_mapping_version=next_draft.mapping_version,
        ),
        actor_id="therapist-demo",
        actor_role="therapist",
    )
    run_qa(repo, edited.transcript_id)
    attest(repo, edited.transcript_id, AttestationRequest(), actor_id="therapist-demo")
    assert export_cha(repo, edited.transcript_id).cha_text.startswith("@Begin")
    assert extract_features(repo, edited.transcript_id, FeatureExtractionRequest()).transcript_id == edited.transcript_id


def test_json_confirmation_rolls_back_all_state_on_pre_replace_failure(tmp_path, monkeypatch) -> None:
    path = tmp_path / "speaker-confirmation.json"
    repo = JsonFileRepository(path)
    transcript, _draft, request = _ready_confirmation(repo)
    before = deepcopy(repo.snapshot())

    def fail_replace(*_args, **_kwargs):
        raise OSError("replace failed")

    monkeypatch.setattr(mock_repository_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")

    assert repo.snapshot() == before
    assert JsonFileRepository(path).snapshot() == before


def test_json_confirmation_post_replace_error_retains_coherent_commit(tmp_path, monkeypatch) -> None:
    path = tmp_path / "speaker-confirmation.json"
    repo = JsonFileRepository(path)
    transcript, _draft, request = _ready_confirmation(repo)
    _attach_downstream_outputs(repo, transcript, ReviewStatus.draft)
    original_fsync = mock_repository_module.os.fsync
    fsync_calls = 0

    def fail_directory_fsync(fd: int) -> None:
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 2:
            raise OSError("directory fsync failed")
        original_fsync(fd)

    monkeypatch.setattr(mock_repository_module.os, "fsync", fail_directory_fsync)
    with pytest.raises(JsonRepositoryDurabilityError):
        confirm_mapping(repo, transcript.transcript_id, request, actor_id="therapist-demo", actor_role="therapist")

    reopened = JsonFileRepository(path)
    assert reopened.snapshot() == repo.snapshot()
    assert reopened.get_transcript(transcript.transcript_id).version == transcript.version + 1
    assert reopened.get_latest_speaker_mapping(transcript.transcript_id).status == MappingPersistedStatus.confirmed
    assert reopened.features["feature_synthetic_001"].review_status == ReviewStatus.stale
    assert reopened.ml_results["ml_synthetic_001"].is_current is False
    assert reopened.ai_reviews["ai_synthetic_001"].therapist_review_status == ReviewStatus.stale
    assert reopened.reports["report_synthetic_001"].status == ReviewStatus.stale
    assert reopened.audit_log[-1]["action"] == "speaker_mapping.confirm"
