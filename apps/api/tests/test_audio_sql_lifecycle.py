from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.core.config import Settings
from app.main import app
from app.schemas.clinical import (
    AudioUploadCleanupRemediation,
    AudioUploadCompleteRequest,
    AudioUploadRequest,
)
from app.services.audio_job_service import (
    complete_audio_upload,
    create_audio_upload_job,
)
from app.services.audio_media_service import verify_and_normalize_audio
from app.services.consent_service import withdraw_consent
from app.services.storage_service import (
    LocalPrivateStorageAdapter,
    get_storage_adapter,
)


def _wav_bytes(
    samples: np.ndarray,
    *,
    sample_rate_hz: int = 16_000,
) -> bytes:
    destination = BytesIO()
    sf.write(
        destination,
        samples,
        sample_rate_hz,
        format="WAV",
        subtype="PCM_16",
    )
    return destination.getvalue()


def _persist_pending_sql_upload(
    database_url: str,
    storage_root: Path,
    source_bytes: bytes,
    *,
    claimed_duration_seconds: float | None = None,
    claimed_sample_rate_hz: int | None = None,
    claimed_channels: int | None = None,
):
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(database_url)
    storage = LocalPrivateStorageAdapter(storage_root)
    job = create_audio_upload_job(
        repo,
        "session_demo_001",
        AudioUploadRequest(
            filename="synthetic.wav",
            content_type="audio/wav",
            size_bytes=len(source_bytes),
            duration_seconds=claimed_duration_seconds,
            sample_rate_hz=claimed_sample_rate_hz,
            channels=claimed_channels,
        ),
        storage_adapter=storage,
    )
    audio_file_id = job.details["audio_file"]["audio_file_id"]
    audio_file = repo.audio_files[audio_file_id]
    storage.persist_source_upload(
        audio_file,
        BytesIO(source_bytes),
        max_size_bytes=100 * 1024 * 1024,
    )
    repo.mark_audio_upload_persisted(
        audio_file_id,
        expected_upload_status="pending",
        expected_source_asset_version=audio_file.source_asset_version,
        actor_id="therapist-synthetic",
    )
    return audio_file_id, storage


def _create_pending_sql_audio(
    database_url: str,
    *,
    storage_root: Path | None = None,
) -> str:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(database_url)
    job = create_audio_upload_job(
        repo,
        "session_demo_001",
        AudioUploadRequest(
            filename="synthetic.wav",
            content_type="audio/wav",
            size_bytes=12,
        ),
        storage_adapter=(
            LocalPrivateStorageAdapter(storage_root)
            if storage_root is not None
            else None
        ),
    )
    return str(job.details["audio_file"]["audio_file_id"])


def test_sql_upload_persistence_transition_rejects_stale_status(
    tmp_path: Path,
) -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'upload-status-cas.db'}"
    audio_file_id = _create_pending_sql_audio(
        database_url,
        storage_root=tmp_path / "private",
    )
    first = SqlAlchemyRepository(database_url)
    stale = SqlAlchemyRepository(database_url)

    first.mark_audio_upload_persisted(
        audio_file_id,
        expected_upload_status="pending",
        expected_source_asset_version=1,
        actor_id="therapist",
    )
    with pytest.raises(ValueError, match="no longer writable"):
        stale.mark_audio_upload_persisted(
            audio_file_id,
            expected_upload_status="pending",
            expected_source_asset_version=1,
            actor_id="therapist",
        )

    durable = SqlAlchemyRepository(database_url)
    assert durable.audio_files[audio_file_id].upload_status == (
        "pending_verification"
    )


def test_sql_upload_persistence_transition_rechecks_consent(
    tmp_path: Path,
) -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'upload-consent-cas.db'}"
    audio_file_id = _create_pending_sql_audio(
        database_url,
        storage_root=tmp_path / "private",
    )
    consent_writer = SqlAlchemyRepository(database_url)
    stale_upload = SqlAlchemyRepository(database_url)
    case_id = stale_upload.audio_files[audio_file_id].case_id

    withdraw_consent(
        consent_writer,
        case_id,
        "Synthetic guardian withdrawal.",
    )

    with pytest.raises(
        ValueError,
        match="consent has been withdrawn|no longer retained",
    ):
        stale_upload.mark_audio_upload_persisted(
            audio_file_id,
            expected_upload_status="pending",
            expected_source_asset_version=1,
            actor_id="therapist",
        )

    durable = SqlAlchemyRepository(database_url)
    assert durable.audio_files[audio_file_id].upload_status == "withdrawn"
    assert durable.cases[case_id].consent_status == "withdrawn"


def test_sql_post_commit_refresh_failure_preserves_committed_upload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'upload-refresh.db'}"
    audio_file_id = _create_pending_sql_audio(
        database_url,
        storage_root=tmp_path / "private",
    )
    repo = SqlAlchemyRepository(database_url)
    storage = LocalPrivateStorageAdapter(tmp_path / "private")
    session_class = repo.SessionLocal.class_
    original_commit = session_class.commit
    original_refresh = session_class.refresh

    def commit_with_boundary_marker(session) -> None:
        original_commit(session)
        session.info["synthetic_commit_completed"] = True

    def fail_refresh_after_commit(session, *args, **kwargs):
        if session.info.get("synthetic_commit_completed"):
            raise RuntimeError("synthetic post-commit refresh failure")
        return original_refresh(session, *args, **kwargs)

    monkeypatch.setattr(session_class, "commit", commit_with_boundary_marker)
    monkeypatch.setattr(session_class, "refresh", fail_refresh_after_commit)
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_storage_adapter] = lambda: storage
    try:
        response = TestClient(
            app,
            raise_server_exceptions=False,
        ).put(
            f"/api/v1/audio/{audio_file_id}/upload-file",
            content=b"sql-post-commit-audio",
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)
        app.dependency_overrides.pop(get_storage_adapter, None)

    durable = SqlAlchemyRepository(database_url).audio_files[audio_file_id]
    assert durable.upload_status == "pending_verification"
    assert durable.object_key is not None
    assert durable.active_upload_receipt is None
    assert response.status_code == 200
    assert (storage.root / durable.object_key).read_bytes() == (
        b"sql-post-commit-audio"
    )


def test_sql_precommit_failure_cleans_attempt_without_completing_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'upload-commit.db'}"
    audio_file_id = _create_pending_sql_audio(
        database_url,
        storage_root=tmp_path / "private",
    )
    repo = SqlAlchemyRepository(database_url)
    storage = LocalPrivateStorageAdapter(tmp_path / "private")
    session_class = repo.SessionLocal.class_
    original_commit = session_class.commit
    commit_calls = 0

    def fail_finalize_commit(session) -> None:
        nonlocal commit_calls
        commit_calls += 1
        if commit_calls == 2:
            raise RuntimeError("synthetic precommit failure")
        original_commit(session)

    monkeypatch.setattr(session_class, "commit", fail_finalize_commit)
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_storage_adapter] = lambda: storage
    try:
        response = TestClient(
            app,
            raise_server_exceptions=False,
        ).put(
            f"/api/v1/audio/{audio_file_id}/upload-file",
            content=b"sql-precommit-audio",
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)
        app.dependency_overrides.pop(get_storage_adapter, None)

    assert response.status_code == 500
    durable = SqlAlchemyRepository(database_url).audio_files[audio_file_id]
    assert durable.upload_status == "pending"
    assert durable.active_upload_receipt is None
    assert durable.upload_cleanup_remediation is None
    assert not list((storage.root / ".upload-attempts").glob("*.stage"))
    assert not list((storage.root / "audio").glob("*attempt-*"))


def test_sql_restart_recovery_preserves_committed_referenced_final(
    tmp_path: Path,
) -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.consent_service import recover_audio_upload_cleanup

    database_url = f"sqlite:///{tmp_path / 'upload-recovery.db'}"
    audio_file_id = _create_pending_sql_audio(
        database_url,
        storage_root=tmp_path / "private",
    )
    repo = SqlAlchemyRepository(database_url)
    audio = repo.audio_files[audio_file_id]
    storage = LocalPrivateStorageAdapter(tmp_path / "private")
    payload = b"sql-committed-recovery-audio"
    receipt = storage.build_source_upload_receipt(
        audio,
        expected_consent_version=repo.cases[audio.case_id].version,
        checksum_sha256=sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )
    storage.stage_source_upload(
        receipt,
        BytesIO(payload),
        max_size_bytes=1024,
        reserve=lambda: repo.reserve_audio_upload_attempt(
            receipt,
            actor_id="therapist",
        ),
    )
    with storage.upload_attempt_fence(audio_file_id):
        repo.finalize_audio_upload_attempt(
            receipt,
            promote=lambda: storage.promote_source_upload(receipt),
            actor_id="therapist",
        )
    repo.audio_files[
        audio_file_id
    ].upload_cleanup_remediation = AudioUploadCleanupRemediation(
        state="pending",
        receipt=receipt,
    )
    repo.add_audit(
        "test.synthetic_stale_cleanup",
        audio_file_id,
        "Synthetic stale cleanup marker persisted.",
    )

    restarted = SqlAlchemyRepository(database_url)
    assert recover_audio_upload_cleanup(
        restarted,
        audio_file_id,
        storage_adapter=storage,
        actor_id="privacy-recovery",
    )
    durable = SqlAlchemyRepository(database_url).audio_files[
        audio_file_id
    ]
    assert durable.upload_status == "pending_verification"
    assert durable.object_key == receipt.intended_final_object_key
    assert durable.upload_cleanup_remediation is None
    assert (
        storage.root / receipt.intended_final_object_key
    ).read_bytes() == payload


def test_sql_upload_completion_is_durable_before_normalization(
    tmp_path: Path,
) -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'audio-lifecycle.db'}"
    source_bytes = _wav_bytes(
        np.linspace(-0.25, 0.25, 16_000, dtype=np.float32)
    )
    audio_file_id, storage = _persist_pending_sql_upload(
        database_url,
        tmp_path / "private",
        source_bytes,
        claimed_duration_seconds=777,
        claimed_sample_rate_hz=8_000,
        claimed_channels=2,
    )

    completion_repo = SqlAlchemyRepository(database_url)
    completed = complete_audio_upload(
        completion_repo,
        audio_file_id,
        AudioUploadCompleteRequest(),
        storage_adapter=storage,
        settings=Settings(),
        actor_id="therapist-synthetic",
    )

    assert completed.upload_status == "uploaded"
    assert completed.size_bytes == len(source_bytes)
    assert completed.checksum_sha256 == sha256(source_bytes).hexdigest()
    assert completed.uploaded_at is not None

    normalization_repo = SqlAlchemyRepository(database_url)
    durable_source = normalization_repo.audio_files[audio_file_id]
    assert durable_source.upload_status == "uploaded"
    assert durable_source.checksum_sha256 == sha256(source_bytes).hexdigest()
    normalized = verify_and_normalize_audio(
        normalization_repo,
        audio_file_id,
        storage_adapter=storage,
        settings=Settings(),
    )

    fresh = SqlAlchemyRepository(database_url)
    durable_normalized = fresh.get_current_normalized_audio_asset(audio_file_id)
    assert durable_normalized is not None
    assert durable_normalized.object_key == normalized.object_key
    assert durable_normalized.normalized_checksum_sha256 == (
        normalized.normalized_checksum_sha256
    )
    assert durable_normalized.provenance is not None
    assert durable_normalized.provenance.source_duration_ms == 1_000
    assert durable_normalized.provenance.source_frame_count == 16_000
    assert durable_normalized.provenance.source_sample_rate_hz == 16_000
    assert durable_normalized.provenance.source_channels == 1
    assert fresh.audio_files[audio_file_id].current_normalized_asset_version == 1
    assert fresh.audio_files[audio_file_id].duration_seconds == 1
    assert fresh.audio_files[audio_file_id].sample_rate_hz == 16_000
    assert fresh.audio_files[audio_file_id].channels == 1


def test_post_commit_refresh_failure_never_deletes_durably_referenced_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'post-commit-refresh.db'}"
    source_bytes = _wav_bytes(
        np.linspace(-0.5, 0.5, 8_000, dtype=np.float32),
        sample_rate_hz=8_000,
    )
    audio_file_id, storage = _persist_pending_sql_upload(
        database_url,
        tmp_path / "private",
        source_bytes,
    )
    repo = SqlAlchemyRepository(database_url)
    complete_audio_upload(
        repo,
        audio_file_id,
        AudioUploadCompleteRequest(),
        storage_adapter=storage,
        settings=Settings(),
    )

    original_refresh = repo._refresh_speech_pipeline_state
    refresh_calls = 0

    def fail_only_after_write_commit() -> None:
        nonlocal refresh_calls
        refresh_calls += 1
        if refresh_calls >= 2:
            raise RuntimeError("synthetic post-commit refresh failure")
        original_refresh()

    monkeypatch.setattr(repo, "_refresh_speech_pipeline_state", fail_only_after_write_commit)

    with pytest.raises(RuntimeError, match="post-commit refresh"):
        verify_and_normalize_audio(
            repo,
            audio_file_id,
            storage_adapter=storage,
            settings=Settings(),
        )

    fresh = SqlAlchemyRepository(database_url)
    durable = fresh.get_current_normalized_audio_asset(audio_file_id)
    assert durable is not None
    assert (storage.root / durable.object_key).is_file()
    assert (
        fresh.audio_files[audio_file_id].current_normalized_asset_version
        == durable.asset_version
    )


def test_concurrent_sql_normalization_is_serialized_and_idempotent(
    tmp_path: Path,
) -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'normalization-race.db'}"
    source_bytes = _wav_bytes(
        np.linspace(-0.25, 0.25, 48_000, dtype=np.float32),
        sample_rate_hz=48_000,
    )
    audio_file_id, storage = _persist_pending_sql_upload(
        database_url,
        tmp_path / "private",
        source_bytes,
    )
    seed = SqlAlchemyRepository(database_url)
    complete_audio_upload(
        seed,
        audio_file_id,
        AudioUploadCompleteRequest(),
        storage_adapter=storage,
        settings=Settings(),
    )
    verify_and_normalize_audio(
        seed,
        audio_file_id,
        storage_adapter=storage,
        settings=Settings(),
    )

    first = SqlAlchemyRepository(database_url)
    second = SqlAlchemyRepository(database_url)
    replacement_settings = Settings(
        audio_normalization_sample_rate_hz=8_000
    )
    outcomes: list[object] = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                verify_and_normalize_audio,
                repo,
                audio_file_id,
                storage_adapter=storage,
                settings=replacement_settings,
            )
            for repo in (first, second)
        ]
        for future in futures:
            try:
                outcomes.append(future.result(timeout=20))
            except Exception as exc:  # noqa: BLE001
                outcomes.append(exc)

    assert all(
        not isinstance(outcome, Exception) for outcome in outcomes
    )
    assert len({outcome.object_key for outcome in outcomes}) == 1

    fresh = SqlAlchemyRepository(database_url)
    durable_rows = [
        row
        for row in fresh.normalized_audio_assets.values()
        if row.source_audio_file_id == audio_file_id
    ]
    durable_object_keys = {row.object_key for row in durable_rows}
    persisted_object_keys = {
        str(path.relative_to(storage.root))
        for path in (storage.root / "normalized").glob("*.wav")
    }

    assert len(durable_rows) == 2
    assert persisted_object_keys == durable_object_keys
    current = fresh.get_current_normalized_audio_asset(audio_file_id)
    assert current is not None
    assert current.asset_version == 2
    assert current.object_key in persisted_object_keys
