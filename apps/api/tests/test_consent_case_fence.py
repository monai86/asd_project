from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.main import app
from app.repositories.base import ProcessingJobStateConflictError
from app.repositories.mock_repository import JsonFileRepository, MockRepository
from app.schemas.clinical import (
    AiReview,
    AudioFileMetadata,
    ChildCaseUpdate,
    FeatureSet,
    JobStatus,
    MLResult,
    ProcessingJob,
    Report,
    ReviewStatus,
    TherapyGoal,
    TherapySessionCreate,
    Transcript,
    Utterance,
    utc_now,
)
from app.schemas.speech_pipeline import NormalizedAudioAsset
from app.services.audio_media_service import verify_and_normalize_audio
from app.services.consent_service import withdraw_consent
from app.services.storage_service import (
    LocalPrivateStorageAdapter,
    MetadataOnlyStorageAdapter,
    StorageProcessingError,
)


class CountingConsentFenceRepository(MockRepository):
    def __init__(self) -> None:
        self.case_fence_entries = 0
        self.audio_fence_entries = 0
        self.fence_order: list[str] = []
        super().__init__()

    @contextmanager
    def case_consent_fence(self, case_id: str):
        del case_id
        self.case_fence_entries += 1
        self.fence_order.append("case")
        yield

    @contextmanager
    def audio_upload_fence(self, audio_file_id: str):
        del audio_file_id
        self.audio_fence_entries += 1
        self.fence_order.append("audio")
        yield


def test_generic_case_patch_cannot_bypass_consent_cleanup() -> None:
    repo = CountingConsentFenceRepository()
    audio = AudioFileMetadata(
        audio_file_id="aud_patch_bypass_guard",
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=16,
        object_key="audio/still-retained.wav",
    )
    repo.audio_files[audio.audio_file_id] = audio
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        response = TestClient(app).patch(
            "/api/v1/cases/case_demo_001",
            json={"consent_status": "withdrawn"},
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)

    assert response.status_code == 400
    assert "dedicated consent withdrawal workflow" in str(
        response.json()["detail"]
    )
    assert repo.cases["case_demo_001"].consent_status == "granted"
    assert repo.audio_files[audio.audio_file_id].retained
    assert repo.audio_files[audio.audio_file_id].object_key is not None


def test_withdrawal_route_uses_single_case_fence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = CountingConsentFenceRepository()
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        MetadataOnlyStorageAdapter,
    )
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        response = TestClient(app).post(
            "/api/v1/cases/case_demo_001/withdraw-consent",
            json={
                "reason": "Synthetic guardian request.",
                "redact_notes": True,
            },
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)

    assert response.status_code == 200
    assert repo.case_fence_entries == 1
    assert repo.audio_fence_entries == 0


def test_normalization_uses_case_then_audio_fence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = CountingConsentFenceRepository()
    repo.audio_files["aud_fenced_normalization"] = AudioFileMetadata(
        audio_file_id="aud_fenced_normalization",
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=16,
    )
    sentinel = object()
    monkeypatch.setattr(
        "app.services.audio_media_service._verify_and_normalize_audio_locked",
        lambda *args, **kwargs: sentinel,
    )

    result = verify_and_normalize_audio(
        repo,
        "aud_fenced_normalization",
        storage_adapter=MetadataOnlyStorageAdapter(),
        settings=object(),
    )

    assert result is sentinel
    assert repo.fence_order == ["case", "audio"]


def test_postgres_composite_case_audio_fence_uses_one_connection() -> None:
    from app.repositories.sqlalchemy_repository import (
        SqlAlchemyRepository,
    )

    executions: list[tuple[str, int]] = []
    session_entries = 0

    class FakeSession:
        def __enter__(self):
            nonlocal session_entries
            session_entries += 1
            return self

        def __exit__(self, exc_type, exc, traceback):
            del exc_type, exc, traceback

        def execute(self, statement, parameters):
            executions.append(
                (str(statement), int(parameters["lock_key"]))
            )

    repo = SqlAlchemyRepository.__new__(SqlAlchemyRepository)
    repo.engine = SimpleNamespace(
        dialect=SimpleNamespace(name="postgresql")
    )
    repo.FenceSessionLocal = FakeSession

    def fail_main_pool_session():
        raise AssertionError("advisory fences must not use the work pool")

    repo.SessionLocal = fail_main_pool_session

    case_id = "case_composite_fence"
    audio_file_id = "aud_composite_fence"
    with repo.case_audio_fence(case_id, audio_file_id):
        assert session_entries == 1

    assert session_entries == 1
    assert executions == [
        (
            "SELECT pg_advisory_lock(:lock_key)",
            repo._postgres_case_consent_fence_key(case_id),
        ),
        (
            "SELECT pg_advisory_lock(:lock_key)",
            repo._postgres_upload_fence_key(audio_file_id),
        ),
        (
            "SELECT pg_advisory_unlock(:lock_key)",
            repo._postgres_upload_fence_key(audio_file_id),
        ),
        (
            "SELECT pg_advisory_unlock(:lock_key)",
            repo._postgres_case_consent_fence_key(case_id),
        ),
    ]


def test_sql_stale_repository_cannot_create_session_after_withdrawal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.sqlalchemy_repository import (
        SqlAlchemyRepository,
    )

    database_url = f"sqlite:///{tmp_path / 'stale-session.db'}"
    SqlAlchemyRepository(database_url)
    stale_repo = SqlAlchemyRepository(database_url)
    withdrawal_repo = SqlAlchemyRepository(database_url)
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        MetadataOnlyStorageAdapter,
    )

    withdraw_consent(
        withdrawal_repo,
        "case_demo_001",
        "Synthetic withdrawal before stale write.",
    )

    with pytest.raises(ValueError, match="Consent is inactive"):
        stale_repo.create_session(
            "case_demo_001",
            TherapySessionCreate(
                session_date="2026-08-11",
                session_type="synthetic",
                notes="synthetic private late session",
            ),
            actor_id="therapist-demo",
        )

    durable = SqlAlchemyRepository(database_url)
    assert durable.cases["case_demo_001"].consent_status == "withdrawn"
    assert {
        item.session_id for item in durable.sessions.values()
    } == {"session_demo_001"}


def test_sql_stale_repository_cannot_edit_case_after_withdrawal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.sqlalchemy_repository import (
        SqlAlchemyRepository,
    )

    database_url = f"sqlite:///{tmp_path / 'stale-case-edit.db'}"
    SqlAlchemyRepository(database_url)
    stale_repo = SqlAlchemyRepository(database_url)
    withdrawal_repo = SqlAlchemyRepository(database_url)
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        MetadataOnlyStorageAdapter,
    )

    withdraw_consent(
        withdrawal_repo,
        "case_demo_001",
        "Synthetic withdrawal before stale case edit.",
    )

    with pytest.raises(ValueError, match="Consent is inactive"):
        stale_repo.update_case(
            "case_demo_001",
            ChildCaseUpdate(notes="synthetic private late case note"),
            expected_version=None,
            actor_id="therapist-demo",
        )

    durable = SqlAlchemyRepository(database_url)
    assert durable.cases["case_demo_001"].consent_status == "withdrawn"
    assert durable.cases["case_demo_001"].notes == ""


def test_withdrawn_case_cannot_be_edited_through_normal_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = MockRepository()
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        MetadataOnlyStorageAdapter,
    )
    withdraw_consent(
        repo,
        "case_demo_001",
        "Synthetic withdrawal before normal case edit.",
    )
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        response = TestClient(app).patch(
            "/api/v1/cases/case_demo_001",
            json={"notes": "synthetic private late case note"},
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)

    assert response.status_code == 400
    assert repo.cases["case_demo_001"].consent_status == "withdrawn"
    assert repo.cases["case_demo_001"].notes == ""


def test_sql_stale_job_cancel_cannot_erase_withdrawal_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.sqlalchemy_repository import (
        SqlAlchemyRepository,
    )

    database_url = f"sqlite:///{tmp_path / 'stale-job-cancel.db'}"
    seed_repo = SqlAlchemyRepository(database_url)
    job = ProcessingJob(
        job_id="job_completed_before_withdrawal",
        session_id="session_demo_001",
        status=JobStatus.transcription_completed,
        message="Synthetic completed transcription.",
        details={
            "status_history": [JobStatus.transcription_completed.value],
        },
    )
    seed_repo.create_processing_job(
        job,
        audit_action="job.synthetic_completed",
        audit_message="Synthetic completed transcription seeded.",
    )
    stale_repo = SqlAlchemyRepository(database_url)
    withdrawal_repo = SqlAlchemyRepository(database_url)
    stale_job = stale_repo.get_processing_job(job.job_id)
    assert stale_job is not None
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        MetadataOnlyStorageAdapter,
    )

    withdraw_consent(
        withdrawal_repo,
        "case_demo_001",
        "Synthetic withdrawal before stale job cancellation.",
    )
    stale_job.status = JobStatus.cancelled
    stale_job.message = "Synthetic stale therapist cancellation."

    with pytest.raises(ProcessingJobStateConflictError):
        stale_repo.update_processing_job(
            stale_job,
            expected_status=JobStatus.transcription_completed,
            audit_action="job.cancel",
            audit_message="Synthetic stale cancellation.",
        )

    durable_job = SqlAlchemyRepository(database_url).get_processing_job(
        job.job_id
    )
    assert durable_job is not None
    assert durable_job.status is JobStatus.transcription_completed
    assert durable_job.details["consent_withdrawn"] is True
    assert durable_job.details["storage_unlinked"] is True


@pytest.mark.parametrize(
    "malformed_history",
    [None, "queued", {"queued": True}, 42],
)
def test_withdrawal_normalizes_malformed_job_status_history(
    malformed_history: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = MockRepository()
    job = ProcessingJob(
        job_id="job_malformed_withdrawal_history",
        session_id="session_demo_001",
        status=JobStatus.queued,
        message="Synthetic queued job with malformed history.",
        details={"status_history": malformed_history},
    )
    repo.jobs[job.job_id] = job
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        MetadataOnlyStorageAdapter,
    )

    withdraw_consent(
        repo,
        "case_demo_001",
        "Synthetic withdrawal with malformed job history.",
    )

    withdrawn = repo.jobs[job.job_id]
    assert withdrawn.status is JobStatus.cancelled
    assert withdrawn.details["status_history"] == [
        JobStatus.cancelled.value
    ]
    assert withdrawn.details["consent_withdrawn"] is True
    assert withdrawn.details["storage_unlinked"] is True


def test_stale_audio_metadata_routes_block_after_durable_withdrawal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'stale-audio-read.db'}"
    seed_repo = SqlAlchemyRepository(database_url)
    audio = AudioFileMetadata(
        audio_file_id="aud_stale_sensitive_metadata",
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="Child Name.wav",
        content_type="audio/wav",
        size_bytes=1024,
        storage_mode="local_private",
        object_key="audio/private-sensitive.wav",
        upload_status="uploaded",
        retained=True,
    )
    seed_repo.audio_files[audio.audio_file_id] = audio
    seed_repo.save()
    stale_repo = SqlAlchemyRepository(database_url)
    withdrawal_repo = SqlAlchemyRepository(database_url)
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        MetadataOnlyStorageAdapter,
    )
    withdraw_consent(
        withdrawal_repo,
        audio.case_id,
        "Synthetic withdrawal before stale audio read.",
    )
    app.dependency_overrides[get_repository] = lambda: stale_repo
    try:
        client = TestClient(app)
        audio_response = client.get(
            f"/api/v1/audio/{audio.audio_file_id}"
        )
        list_response = client.get(
            f"/api/v1/sessions/{audio.session_id}/audio"
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)

    assert audio_response.status_code == 400
    assert list_response.status_code == 400
    durable = SqlAlchemyRepository(database_url)
    assert durable.audio_files[audio.audio_file_id].original_filename == (
        "withdrawn-audio"
    )


def test_stale_case_metadata_routes_hide_durable_withdrawal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'stale-case-read.db'}"
    seed_repo = SqlAlchemyRepository(database_url)
    seed_repo.cases["case_demo_001"].notes = "synthetic private case note"
    seed_repo.save()
    stale_repo = SqlAlchemyRepository(database_url)
    withdrawal_repo = SqlAlchemyRepository(database_url)
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        MetadataOnlyStorageAdapter,
    )
    withdraw_consent(
        withdrawal_repo,
        "case_demo_001",
        "Synthetic withdrawal before stale case read.",
        redact_notes=True,
    )
    app.dependency_overrides[get_repository] = lambda: stale_repo
    try:
        client = TestClient(app)
        list_response = client.get("/api/v1/cases")
        detail_response = client.get(
            "/api/v1/cases/case_demo_001"
        )
        timeline_response = client.get(
            "/api/v1/cases/case_demo_001/timeline"
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)

    assert list_response.status_code == 200
    assert list_response.json() == []
    assert detail_response.status_code == 400
    assert timeline_response.status_code == 400
    durable = SqlAlchemyRepository(database_url)
    assert durable.cases["case_demo_001"].consent_status == "withdrawn"
    assert durable.cases["case_demo_001"].notes == ""


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (
            "/api/v1/cases/case_demo_001/sessions",
            {
                "session_date": "2026-08-11",
                "session_type": "synthetic",
                "notes": "synthetic private late session",
            },
        ),
        (
            "/api/v1/cases/case_demo_001/goals",
            {
                "title": "synthetic private late goal",
                "target": "synthetic private target",
            },
        ),
        (
            "/api/v1/sessions/session_demo_001/transcripts/manual",
            {
                "text": "SPK_01: synthetic private late transcript",
                "language": "Thai",
            },
        ),
    ],
)
def test_stale_case_linked_write_routes_reload_within_consent_fence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    payload: dict[str, object],
) -> None:
    from app.repositories.sqlalchemy_repository import (
        SqlAlchemyRepository,
    )

    suffix = sha256(path.encode("utf-8")).hexdigest()[:8]
    database_url = f"sqlite:///{tmp_path / f'stale-route-{suffix}.db'}"
    SqlAlchemyRepository(database_url)
    stale_repo = SqlAlchemyRepository(database_url)
    withdrawal_repo = SqlAlchemyRepository(database_url)
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        MetadataOnlyStorageAdapter,
    )
    withdraw_consent(
        withdrawal_repo,
        "case_demo_001",
        "Synthetic withdrawal before stale route write.",
    )
    app.dependency_overrides[get_repository] = lambda: stale_repo
    try:
        response = TestClient(app).post(path, json=payload)
    finally:
        app.dependency_overrides.pop(get_repository, None)

    assert response.status_code == 400
    durable = SqlAlchemyRepository(database_url)
    assert durable.cases["case_demo_001"].consent_status == "withdrawn"
    assert {
        item.session_id for item in durable.sessions.values()
    } == {"session_demo_001"}
    assert not durable.therapy_goals
    assert not durable.transcripts


def test_withdrawal_uses_one_case_fence_not_one_connection_per_audio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = CountingConsentFenceRepository()
    for index in range(24):
        audio = AudioFileMetadata(
            audio_file_id=f"aud_pool_bound_{index:02d}",
            session_id="session_demo_001",
            case_id="case_demo_001",
            original_filename="synthetic.wav",
            content_type="audio/wav",
            size_bytes=16,
            storage_mode="metadata_only",
            object_key=None,
        )
        repo.audio_files[audio.audio_file_id] = audio
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        MetadataOnlyStorageAdapter,
    )

    withdraw_consent(repo, "case_demo_001", "Synthetic withdrawal.")

    assert repo.case_fence_entries == 1
    assert repo.audio_fence_entries == 0
    assert all(
        audio.upload_status == "withdrawn"
        for audio in repo.audio_files.values()
    )


def _commit_audio_while_holding_case_fence(
    repo,
    storage: LocalPrivateStorageAdapter,
    *,
    committed: Event,
    release: Event,
) -> tuple[str, object]:
    audio = AudioFileMetadata(
        audio_file_id="aud_new_during_withdrawal",
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=16,
        storage_mode="local_private",
        object_key="audio/new-during-withdrawal.wav",
        storage_backend_identity_sha256=(
            storage.storage_backend_identity_sha256
        ),
    )
    payload = b"private-race-audio"
    with repo.case_consent_fence(audio.case_id):
        load = getattr(repo, "load", None)
        if callable(load):
            load()
        repo.audio_files[audio.audio_file_id] = audio
        repo.save()
        receipt = storage.build_source_upload_receipt(
            audio,
            expected_consent_version=repo.cases[audio.case_id].version,
            checksum_sha256=sha256(payload).hexdigest(),
            size_bytes=len(payload),
        )
        with repo.audio_upload_fence(audio.audio_file_id):
            storage.stage_source_upload(
                receipt,
                BytesIO(payload),
                max_size_bytes=1024,
                reserve=lambda: repo.reserve_audio_upload_attempt(
                    receipt,
                    actor_id="therapist-demo",
                ),
            )
            repo.finalize_audio_upload_attempt(
                receipt,
                promote=lambda: storage.promote_source_upload(receipt),
                actor_id="therapist-demo",
            )
        committed.set()
        assert release.wait(timeout=5)
    return audio.audio_file_id, receipt


def _assert_stale_withdrawal_cleans_new_audio(
    stale_repo,
    creator_repo,
    storage: LocalPrivateStorageAdapter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert callable(getattr(creator_repo, "case_consent_fence", None))
    committed = Event()
    release = Event()
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        lambda: storage,
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        creator_future = executor.submit(
            _commit_audio_while_holding_case_fence,
            creator_repo,
            storage,
            committed=committed,
            release=release,
        )
        assert committed.wait(timeout=5)
        withdrawal_future = executor.submit(
            withdraw_consent,
            stale_repo,
            "case_demo_001",
            "Synthetic concurrent withdrawal.",
        )
        release.set()
        audio_file_id, receipt = creator_future.result(timeout=5)
        withdrawal_future.result(timeout=5)

    durable_repo = type(stale_repo)(
        stale_repo.path
        if isinstance(stale_repo, JsonFileRepository)
        else stale_repo.database_url
    )
    durable = durable_repo.audio_files[audio_file_id]
    assert durable.upload_status == "withdrawn"
    assert durable.object_key is None
    assert durable.upload_cleanup_remediation is None
    assert not (storage.root / receipt.staging_object_key).exists()
    assert not (storage.root / receipt.intended_final_object_key).exists()


def test_json_stale_withdrawal_cleans_audio_committed_before_case_fence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "repository.json"
    stale_repo = JsonFileRepository(path)
    creator_repo = JsonFileRepository(path)
    _assert_stale_withdrawal_cleans_new_audio(
        stale_repo,
        creator_repo,
        LocalPrivateStorageAdapter(tmp_path / "private"),
        monkeypatch,
    )


def test_sqlite_stale_withdrawal_cleans_audio_committed_before_case_fence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'consent-race.db'}"
    stale_repo = SqlAlchemyRepository(database_url)
    creator_repo = SqlAlchemyRepository(database_url)
    _assert_stale_withdrawal_cleans_new_audio(
        stale_repo,
        creator_repo,
        LocalPrivateStorageAdapter(tmp_path / "private"),
        monkeypatch,
    )


def _seed_normalized_private_asset(
    repo: JsonFileRepository,
    storage: LocalPrivateStorageAdapter,
    *,
    audio_file_id: str,
):
    audio = AudioFileMetadata(
        audio_file_id=audio_file_id,
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=16,
    )
    repo.audio_files[audio.audio_file_id] = audio
    audio.storage_mode = storage.storage_mode
    audio.storage_backend_identity_sha256 = (
        storage.storage_backend_identity_sha256
    )
    audio.upload_status = "uploaded"
    audio.object_key = "audio/source.wav"
    audio.checksum_sha256 = "a" * 64
    normalized_key = "normalized/current.wav"
    source_path = storage.root / audio.object_key
    normalized_path = storage.root / normalized_key
    source_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"private-source")
    normalized_path.write_bytes(b"private-normalized")
    asset = NormalizedAudioAsset(
        organization_id=audio.organization_id,
        session_id=audio.session_id,
        asset_version=1,
        object_key=normalized_key,
        source_checksum_sha256="a" * 64,
        normalized_checksum_sha256="b" * 64,
        format="wav_pcm_s16le",
        duration_ms=100,
        sample_rate_hz=16_000,
        channels=1,
        frame_count=1_600,
        decoder_name="synthetic",
        decoder_version="1",
        conversion_command_profile="synthetic-v1",
        source_audio_file_id=audio.audio_file_id,
        source_asset_version=audio.source_asset_version,
        created_at=utc_now(),
    )
    repo.normalized_audio_assets[(audio.audio_file_id, 1)] = asset
    audio.current_normalized_asset_version = 1
    audio.current_normalized_checksum_sha256 = (
        asset.normalized_checksum_sha256
    )
    save = getattr(repo, "save", None)
    if callable(save):
        save()
    return audio, source_path, normalized_path


def _seed_sensitive_case_outputs(repo) -> dict[str, str]:
    session = repo.sessions["session_demo_001"]
    transcript = Transcript(
        transcript_id="transcript_consent_atomic",
        session_id=session.session_id,
        case_id=session.case_id,
        source="synthetic_asr",
        raw_text="synthetic private transcript",
        utterances=[
            Utterance(
                utterance_id="utt_consent_atomic",
                speaker="SPK_01",
                text="synthetic private utterance",
            )
        ],
        qa_issues=[
            {
                "code": "synthetic_private_issue",
                "severity": "warning",
                "message": "synthetic private QA content",
            }
        ],
        attestation_reason="synthetic private attestation reason",
        chat_metadata={"private_header": "synthetic private metadata"},
        malformed_lines=[{"text": "synthetic private malformed line"}],
        raw_speaker_labels=["synthetic-private-speaker"],
    )
    feature = FeatureSet(
        feature_set_id="feature_consent_atomic",
        session_id=session.session_id,
        transcript_id=transcript.transcript_id,
        transcript_version=transcript.version,
        therapist_attested=True,
        features=[],
    )
    ml_result = MLResult(
        result_id="ml_consent_atomic",
        transcript_id=transcript.transcript_id,
        session_id=session.session_id,
        feature_result_id=feature.feature_set_id,
        provider_id="synthetic-provider",
        provider_name="Synthetic provider",
        provider_version="1",
        input_feature_schema_version=feature.schema_version,
        input_feature_hash="a" * 64,
        status="completed",
    )
    ai_review = AiReview(
        ai_review_id="ai_consent_atomic",
        session_id=session.session_id,
        summary="synthetic private AI review",
        key_findings=["synthetic private finding"],
        concerns=["synthetic private concern"],
        strengths=["synthetic private strength"],
        limitations=["synthetic private limitation"],
        recommended_review_actions=["synthetic private action"],
        confidence_level="synthetic",
        input_transcript_version=transcript.version,
    )
    report = Report(
        report_id="report_consent_atomic",
        session_id=session.session_id,
        case_id=session.case_id,
        report_type="synthetic",
        title="Synthetic private report",
        markdown="Synthetic private report body.",
        html="<p>Synthetic private report body.</p>",
        therapist_notes="Synthetic private therapist note.",
        validation_summary="Synthetic private validation summary.",
        session_goals=["Synthetic private session goal."],
        signed_by="Synthetic Therapist",
        signed_snapshot={
            "markdown": "Synthetic private signed clinical content."
        },
    )
    goal = TherapyGoal(
        goal_id="goal_consent_atomic",
        case_id=session.case_id,
        title="Synthetic private goal",
        target="Synthetic private target",
        notes="Synthetic private goal note",
    )
    job = ProcessingJob(
        job_id="job_consent_atomic",
        session_id=session.session_id,
        status=JobStatus.queued,
        message="Synthetic queued job.",
        details={
            "audio_file": {
                "original_filename": "synthetic-private.wav",
                "object_key": "audio/synthetic-private.wav",
            },
            "upload_intent": {
                "object_key": "audio/synthetic-private.wav",
                "upload_url": "https://private.invalid/upload-token",
            },
            "status_history": [
                JobStatus.queued.value,
                "synthetic-private-history-note",
            ],
        },
    )
    repo.transcripts[transcript.transcript_id] = transcript
    repo.features[feature.feature_set_id] = feature
    repo.ml_results[ml_result.result_id] = ml_result
    repo.ai_reviews[ai_review.ai_review_id] = ai_review
    repo.reports[report.report_id] = report
    repo.therapy_goals[goal.goal_id] = goal
    repo.jobs[job.job_id] = job
    session.transcript_id = transcript.transcript_id
    session.feature_set_id = feature.feature_set_id
    session.ml_result_id = ml_result.result_id
    session.ai_review_id = ai_review.ai_review_id
    session.report_id = report.report_id
    save = getattr(repo, "save", None)
    if callable(save):
        save()
    return {
        "transcript_id": transcript.transcript_id,
        "feature_set_id": feature.feature_set_id,
        "ml_result_id": ml_result.result_id,
        "ai_review_id": ai_review.ai_review_id,
        "report_id": report.report_id,
        "goal_id": goal.goal_id,
        "job_id": job.job_id,
    }


def test_withdrawn_case_outputs_are_hidden_from_normal_read_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = MockRepository()
    outputs = _seed_sensitive_case_outputs(repo)
    transcript_id = outputs["transcript_id"]
    for attribute in (
        "speaker_mappings",
        "limitation_acknowledgments",
        "transcript_attestations",
        "chat_exports",
        "findings_results",
    ):
        getattr(repo, attribute)[("synthetic-private", 1)] = (
            SimpleNamespace(transcript_id=transcript_id)
        )
    repo.private_asr_evidence["job_consent_atomic"] = SimpleNamespace(
        transcript_id=transcript_id
    )
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        MetadataOnlyStorageAdapter,
    )
    withdraw_consent(
        repo,
        "case_demo_001",
        "Synthetic withdrawal before normal reads.",
    )
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        client = TestClient(app)
        goals = client.get("/api/v1/cases/case_demo_001/goals")
        transcript = client.get(
            "/api/v1/sessions/session_demo_001/transcript"
        )
        reports = client.get("/api/v1/reports")
        report = client.get(
            f"/api/v1/reports/{outputs['report_id']}"
        )
        job = client.get(f"/api/v1/jobs/{outputs['job_id']}")
    finally:
        app.dependency_overrides.pop(get_repository, None)

    assert goals.status_code == 400
    assert transcript.status_code == 400
    assert reports.status_code == 200
    assert reports.json() == []
    assert report.status_code == 400
    assert job.status_code == 400
    withdrawn_job = repo.jobs[outputs["job_id"]]
    assert "audio_file" not in withdrawn_job.details
    assert "upload_intent" not in withdrawn_job.details
    assert withdrawn_job.details["consent_withdrawn"] is True
    assert withdrawn_job.details["storage_unlinked"] is True
    assert withdrawn_job.details["status_history"] == [
        JobStatus.queued.value,
        JobStatus.cancelled.value,
    ]
    assert not repo.speaker_mappings
    assert not repo.limitation_acknowledgments
    assert not repo.transcript_attestations
    assert not repo.chat_exports
    assert not repo.findings_results
    assert not repo.private_asr_evidence


def test_withdrawal_unlinks_and_deletes_normalized_private_asset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = JsonFileRepository(tmp_path / "repository.json")
    storage = LocalPrivateStorageAdapter(tmp_path / "private")
    audio, source_path, normalized_path = _seed_normalized_private_asset(
        repo,
        storage,
        audio_file_id="aud_normalized_withdrawal",
    )
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        lambda: storage,
    )

    withdraw_consent(repo, audio.case_id, "Synthetic withdrawal.")

    durable = JsonFileRepository(repo.path)
    withdrawn = durable.audio_files[audio.audio_file_id]
    assert withdrawn.upload_cleanup_remediation is None
    assert withdrawn.current_normalized_asset_version is None
    assert withdrawn.current_normalized_checksum_sha256 is None
    assert not durable.normalized_audio_assets
    assert not source_path.exists()
    assert not normalized_path.exists()


def test_normalized_cleanup_survives_restart_after_deletion_outage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.consent_service import recover_audio_upload_cleanup

    class FailingDeleteStorage(LocalPrivateStorageAdapter):
        def delete_object(self, object_key):
            raise StorageProcessingError(
                "storage_delete_failed",
                remediation="Retry exact-key cleanup.",
            )

    repo = JsonFileRepository(tmp_path / "repository.json")
    storage = LocalPrivateStorageAdapter(tmp_path / "private")
    audio, source_path, normalized_path = _seed_normalized_private_asset(
        repo,
        storage,
        audio_file_id="aud_normalized_restart",
    )
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        lambda: FailingDeleteStorage(storage.root),
    )

    withdraw_consent(repo, audio.case_id, "Synthetic withdrawal.")

    restarted = JsonFileRepository(repo.path)
    withdrawn = restarted.audio_files[audio.audio_file_id]
    remediation = withdrawn.upload_cleanup_remediation
    assert remediation is not None
    assert remediation.state == "failed"
    assert remediation.final_object_key == "audio/source.wav"
    assert remediation.additional_object_keys == ["normalized/current.wav"]
    assert withdrawn.current_normalized_asset_version is None
    assert not restarted.normalized_audio_assets
    assert source_path.exists()
    assert normalized_path.exists()

    assert recover_audio_upload_cleanup(
        restarted,
        audio.audio_file_id,
        storage_adapter=storage,
        actor_id="cleanup-worker",
    )

    durable = JsonFileRepository(repo.path).audio_files[audio.audio_file_id]
    assert durable.upload_cleanup_remediation is None
    assert not source_path.exists()
    assert not normalized_path.exists()


def test_wrong_backend_preserves_source_and_normalized_exact_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = JsonFileRepository(tmp_path / "repository.json")
    original = LocalPrivateStorageAdapter(tmp_path / "private-original")
    wrong = LocalPrivateStorageAdapter(tmp_path / "private-wrong")
    audio, source_path, normalized_path = _seed_normalized_private_asset(
        repo,
        original,
        audio_file_id="aud_normalized_wrong_backend",
    )
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        lambda: wrong,
    )

    withdraw_consent(repo, audio.case_id, "Synthetic withdrawal.")

    durable_repo = JsonFileRepository(repo.path)
    withdrawn = durable_repo.audio_files[audio.audio_file_id]
    remediation = withdrawn.upload_cleanup_remediation
    assert remediation is not None
    assert remediation.state == "escalated"
    assert remediation.error_code == "storage_receipt_backend_mismatch"
    assert remediation.final_object_key == "audio/source.wav"
    assert remediation.additional_object_keys == ["normalized/current.wav"]
    assert not durable_repo.normalized_audio_assets
    assert source_path.exists()
    assert normalized_path.exists()


def test_sql_withdrawal_rolls_back_everything_when_audit_insert_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.sqlalchemy_repository import (
        SqlAlchemyRepository,
    )

    database_url = f"sqlite:///{tmp_path / 'consent-rollback.db'}"
    repo = SqlAlchemyRepository(database_url)
    storage = LocalPrivateStorageAdapter(tmp_path / "private")
    audio, source_path, normalized_path = _seed_normalized_private_asset(
        repo,
        storage,
        audio_file_id="aud_sql_consent_rollback",
    )
    outputs = _seed_sensitive_case_outputs(repo)
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        lambda: storage,
    )

    def fail_audit_insert(*args, **kwargs):
        raise RuntimeError("synthetic audit insert failure")

    monkeypatch.setattr(repo, "_audit_to_record", fail_audit_insert)
    with pytest.raises(
        RuntimeError,
        match="synthetic audit insert failure",
    ):
        withdraw_consent(
            repo,
            audio.case_id,
            "Synthetic guardian withdrawal.",
        )

    restarted = SqlAlchemyRepository(database_url)
    retained = restarted.audio_files[audio.audio_file_id]
    transcript = restarted.transcripts[outputs["transcript_id"]]
    report = restarted.reports[outputs["report_id"]]
    ai_review = restarted.ai_reviews[outputs["ai_review_id"]]
    goal = restarted.therapy_goals[outputs["goal_id"]]
    job = restarted.jobs[outputs["job_id"]]
    assert restarted.cases[audio.case_id].consent_status == "granted"
    assert retained.upload_status == "uploaded"
    assert retained.object_key == "audio/source.wav"
    assert retained.retained
    assert retained.upload_cleanup_remediation is None
    assert retained.current_normalized_asset_version == 1
    assert restarted.normalized_audio_assets
    assert transcript.raw_text == "synthetic private transcript"
    assert transcript.utterances
    assert outputs["feature_set_id"] in restarted.features
    assert outputs["ml_result_id"] in restarted.ml_results
    assert ai_review.summary == "synthetic private AI review"
    assert report.title == "Synthetic private report"
    assert report.therapist_notes == "Synthetic private therapist note."
    assert goal.title == "Synthetic private goal"
    assert goal.target == "Synthetic private target"
    assert goal.retained
    assert job.status is JobStatus.queued
    assert job.details["audio_file"]["original_filename"] == (
        "synthetic-private.wav"
    )
    assert job.details["audio_file"]["object_key"] == (
        "audio/synthetic-private.wav"
    )
    assert "upload_intent" in job.details
    assert repo.cases[audio.case_id].consent_status == "granted"
    assert repo.transcripts[outputs["transcript_id"]].raw_text == (
        "synthetic private transcript"
    )
    assert outputs["feature_set_id"] in repo.features
    assert outputs["ml_result_id"] in repo.ml_results
    assert repo.ai_reviews[outputs["ai_review_id"]].summary == (
        "synthetic private AI review"
    )
    assert repo.reports[outputs["report_id"]].title == (
        "Synthetic private report"
    )
    assert repo.therapy_goals[outputs["goal_id"]].title == (
        "Synthetic private goal"
    )
    assert repo.jobs[outputs["job_id"]].status is JobStatus.queued
    assert not [
        item
        for item in restarted.audit_log
        if item["action"] == "consent.withdraw"
    ]
    assert source_path.exists()
    assert normalized_path.exists()


def test_sql_crash_after_atomic_withdrawal_keeps_complete_durable_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.sqlalchemy_repository import (
        SqlAlchemyRepository,
    )
    from app.services.consent_service import recover_audio_upload_cleanup

    class CrashBeforeDeleteStorage(LocalPrivateStorageAdapter):
        def cleanup_upload_attempt(self, receipt):
            del receipt
            raise RuntimeError("synthetic process crash before byte delete")

        def delete_object(self, object_key):
            del object_key
            raise RuntimeError("synthetic process crash before byte delete")

    database_url = f"sqlite:///{tmp_path / 'consent-committed.db'}"
    repo = SqlAlchemyRepository(database_url)
    storage = LocalPrivateStorageAdapter(tmp_path / "private")
    audio, source_path, normalized_path = _seed_normalized_private_asset(
        repo,
        storage,
        audio_file_id="aud_sql_consent_committed",
    )
    outputs = _seed_sensitive_case_outputs(repo)
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        lambda: CrashBeforeDeleteStorage(storage.root),
    )

    with pytest.raises(
        RuntimeError,
        match="synthetic process crash before byte delete",
    ):
        withdraw_consent(
            repo,
            audio.case_id,
            "Synthetic guardian withdrawal.",
        )

    restarted = SqlAlchemyRepository(database_url)
    withdrawn = restarted.audio_files[audio.audio_file_id]
    remediation = withdrawn.upload_cleanup_remediation
    transcript = restarted.transcripts[outputs["transcript_id"]]
    report = restarted.reports[outputs["report_id"]]
    ai_review = restarted.ai_reviews[outputs["ai_review_id"]]
    goal = restarted.therapy_goals[outputs["goal_id"]]
    job = restarted.jobs[outputs["job_id"]]
    assert restarted.cases[audio.case_id].consent_status == "withdrawn"
    assert restarted.sessions[audio.session_id].status is ReviewStatus.withdrawn
    assert transcript.raw_text == ""
    assert transcript.utterances == []
    assert transcript.qa_issues == []
    assert transcript.attestation_reason == ""
    assert transcript.chat_metadata == {}
    assert transcript.malformed_lines == []
    assert transcript.raw_speaker_labels == []
    assert transcript.review_status is ReviewStatus.withdrawn
    assert outputs["feature_set_id"] not in restarted.features
    assert outputs["ml_result_id"] not in restarted.ml_results
    assert ai_review.summary.startswith("Consent withdrawn.")
    assert ai_review.therapist_review_status is ReviewStatus.withdrawn
    assert report.status is ReviewStatus.withdrawn
    assert report.title == "Consent withdrawn."
    assert report.markdown.startswith("Consent withdrawn.")
    assert report.therapist_notes is None
    assert report.validation_summary is None
    assert report.session_goals == []
    assert report.signed_by is None
    assert report.signed_snapshot is None
    assert goal.status == "withdrawn"
    assert goal.title == "Consent withdrawn."
    assert goal.target == ""
    assert not goal.retained
    assert job.status is JobStatus.cancelled
    assert job.error_code == "consent_withdrawn"
    assert "audio_file" not in job.details
    assert "upload_intent" not in job.details
    assert job.details["consent_withdrawn"] is True
    assert job.details["storage_unlinked"] is True
    assert withdrawn.upload_status == "withdrawn"
    assert withdrawn.object_key is None
    assert not withdrawn.retained
    assert remediation is not None
    assert remediation.state == "pending"
    assert remediation.final_object_key == "audio/source.wav"
    assert remediation.additional_object_keys == ["normalized/current.wav"]
    assert withdrawn.current_normalized_asset_version is None
    assert not restarted.normalized_audio_assets
    withdrawal_audits = [
        item
        for item in restarted.audit_log
        if item["action"] == "consent.withdraw"
    ]
    assert len(withdrawal_audits) == 1
    assert source_path.exists()
    assert normalized_path.exists()

    assert recover_audio_upload_cleanup(
        restarted,
        audio.audio_file_id,
        storage_adapter=storage,
        actor_id="cleanup-worker",
    )

    durable = SqlAlchemyRepository(database_url).audio_files[
        audio.audio_file_id
    ]
    assert durable.upload_cleanup_remediation is None
    assert not source_path.exists()
    assert not normalized_path.exists()
