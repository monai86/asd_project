from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from app.core.config import Settings
from app.schemas.clinical import AudioUploadCompleteRequest, AudioUploadRequest
from app.services.audio_job_service import (
    complete_audio_upload,
    create_audio_upload_job,
)
from app.services.audio_media_service import verify_and_normalize_audio
from app.services.storage_service import LocalPrivateStorageAdapter


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
    audio_file.upload_status = "pending_verification"
    repo.save()
    return audio_file_id, storage


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


def test_stale_sql_normalization_loser_deletes_only_its_unreferenced_object(
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
    persisted_barrier = threading.Barrier(2)
    for repo in (first, second):
        original_create = repo.create_normalized_audio_asset

        def create_after_both_objects_exist(
            record,
            *,
            original_create=original_create,
        ):
            persisted_barrier.wait(timeout=10)
            return original_create(record)

        repo.create_normalized_audio_asset = create_after_both_objects_exist

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

    successful = [
        outcome for outcome in outcomes if not isinstance(outcome, Exception)
    ]
    failed = [
        outcome for outcome in outcomes if isinstance(outcome, Exception)
    ]
    assert len(successful) == 1
    assert len(failed) == 1
    assert "conflicts with the stored version" in str(failed[0])

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
