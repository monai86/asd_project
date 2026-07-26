from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.core.config import Settings, get_settings
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    AudioFileMetadata,
    ChildCaseCreate,
    TherapySessionCreate,
)
from app.services.storage_service import (
    LocalPrivateStorageAdapter,
    SupabasePrivateStorageAdapter,
    get_storage_adapter,
)


class FakePrivateBucket:
    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.objects = dict(objects or {})
        self.removed: list[str] = []
        self.fail_move = False
        self.streamed_bytes = 0

    def download_stream(self, object_key: str):
        if object_key not in self.objects:
            raise KeyError(object_key)
        payload = self.objects[object_key]
        for start in range(0, len(payload), 3):
            chunk = payload[start : start + 3]
            self.streamed_bytes += len(chunk)
            yield chunk

    def upload(self, object_key: str, source, file_options: dict) -> None:
        source.seek(0)
        self.objects[object_key] = source.read()

    def move(self, source_key: str, destination_key: str) -> None:
        if self.fail_move:
            raise OSError("synthetic move failure")
        self.objects[destination_key] = self.objects.pop(source_key)

    def remove(self, object_keys: list[str]) -> None:
        for object_key in object_keys:
            self.removed.append(object_key)
            self.objects.pop(object_key, None)


def _supabase_audio(object_key: str = "audio/source.wav") -> AudioFileMetadata:
    return AudioFileMetadata(
        audio_file_id="aud_supabase",
        session_id="session_supabase",
        case_id="case_supabase",
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=8,
        storage_mode="supabase_private",
        object_key=object_key,
        upload_status="uploaded",
    )


def test_supabase_private_processing_download_is_bounded() -> None:
    from app.services.storage_service import StorageProcessingError

    bucket = FakePrivateBucket({"audio/source.wav": b"12345678"})
    adapter = SupabasePrivateStorageAdapter(
        bucket_client=bucket,
        bucket_name="private-audio",
        max_download_size_bytes=8,
    )

    with adapter.open_source_for_processing(_supabase_audio()) as source:
        assert source.read() == b"12345678"

    oversized_bucket = FakePrivateBucket({"audio/source.wav": b"x" * 100})
    oversized = SupabasePrivateStorageAdapter(
        bucket_client=oversized_bucket,
        bucket_name="private-audio",
        max_download_size_bytes=7,
    )
    with pytest.raises(StorageProcessingError) as captured:
        oversized.open_source_for_processing(_supabase_audio())
    assert captured.value.code == "storage_download_size_exceeded"
    assert captured.value.remediation
    assert oversized_bucket.streamed_bytes == 9
    assert oversized_bucket.streamed_bytes < len(
        oversized_bucket.objects["audio/source.wav"]
    )


def test_supabase_rejects_nonstreaming_client_before_downloading() -> None:
    from app.services.storage_service import StorageProcessingError

    class NonStreamingBucket:
        def __init__(self) -> None:
            self.download_calls = 0

        def download(self, object_key: str) -> bytes:
            self.download_calls += 1
            raise AssertionError("full-byte download must never be called")

    bucket = NonStreamingBucket()
    adapter = SupabasePrivateStorageAdapter(
        bucket_client=bucket,
        bucket_name="private-audio",
        max_download_size_bytes=8,
    )

    with pytest.raises(StorageProcessingError) as captured:
        adapter.open_source_for_processing(_supabase_audio())

    assert captured.value.code == "storage_capability_unavailable"
    assert bucket.download_calls == 0


def test_storage_factory_passes_configured_audio_byte_limit_to_supabase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.storage_service as storage_service

    monkeypatch.setattr(
        storage_service,
        "get_settings",
        lambda: Settings(
            storage_mode="supabase_private",
            max_audio_file_size_mb=42,
        ),
    )

    adapter = storage_service.get_storage_adapter()

    assert isinstance(adapter, SupabasePrivateStorageAdapter)
    assert adapter.max_download_size_bytes == 42 * 1024 * 1024


def test_supabase_normalized_upload_is_private_atomic_and_cleans_staging() -> None:
    from app.services.storage_service import StorageProcessingError

    bucket = FakePrivateBucket()
    adapter = SupabasePrivateStorageAdapter(
        bucket_client=bucket,
        bucket_name="private-audio",
        max_download_size_bytes=1024,
    )

    object_key = adapter.persist_normalized_asset(
        _supabase_audio(),
        BytesIO(b"normalized-wave"),
        content_type="audio/wav",
    )

    assert object_key.startswith("normalized/")
    assert bucket.objects[object_key] == b"normalized-wave"
    assert not any(key.startswith(".staging/") for key in bucket.objects)

    bucket.fail_move = True
    with pytest.raises(StorageProcessingError) as captured:
        adapter.persist_normalized_asset(
            _supabase_audio(),
            BytesIO(b"new-normalized-wave"),
            content_type="audio/wav",
        )
    assert captured.value.code == "storage_write_failed"
    assert not any(key.startswith(".staging/") for key in bucket.objects)
    assert bucket.removed


def test_supabase_missing_client_or_object_is_typed_unavailable() -> None:
    from app.services.storage_service import StorageProcessingError

    missing_client = SupabasePrivateStorageAdapter()
    with pytest.raises(StorageProcessingError) as unavailable:
        missing_client.open_source_for_processing(_supabase_audio())
    assert unavailable.value.code == "storage_capability_unavailable"

    missing_object = SupabasePrivateStorageAdapter(
        bucket_client=FakePrivateBucket(),
        bucket_name="private-audio",
        max_download_size_bytes=1024,
    )
    with pytest.raises(StorageProcessingError) as missing:
        missing_object.open_source_for_processing(_supabase_audio())
    assert missing.value.code == "storage_object_missing"


def test_verify_route_maps_missing_private_source_to_structured_intake_error(
    tmp_path: Path,
) -> None:
    repo = MockRepository()
    case = repo.create_case(
        ChildCaseCreate(
            child_code="SYNTHETIC-MISSING-SOURCE",
            age_months=48,
            language="Thai",
            consent_status="granted",
        ),
        actor_id="therapist-demo",
    )
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(
            session_date="2026-07-26",
            session_type="synthetic_testbed",
        ),
        actor_id="therapist-demo",
    )
    audio = AudioFileMetadata(
        audio_file_id="aud_missing_source",
        organization_id=session.organization_id,
        session_id=session.session_id,
        case_id=case.case_id,
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=1024,
        storage_mode="local_private",
        object_key="audio/missing.wav",
        upload_status="uploaded",
    )
    repo.audio_files[audio.audio_file_id] = audio
    settings = Settings(local_storage_root=str(tmp_path))
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_storage_adapter] = lambda: LocalPrivateStorageAdapter(
        tmp_path
    )
    try:
        response = TestClient(app).post(
            f"/api/v1/audio/{audio.audio_file_id}/verify-and-normalize"
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_storage_adapter, None)

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "storage_object_missing"
    assert response.json()["detail"]["remediation"]
    assert repo.jobs == {}


def test_upload_intent_maps_missing_supabase_capability_to_structured_error() -> None:
    repo = MockRepository()
    case = repo.create_case(
        ChildCaseCreate(
            child_code="SYNTHETIC-SUPABASE-UNAVAILABLE",
            age_months=48,
            language="Thai",
            consent_status="granted",
        ),
        actor_id="therapist-demo",
    )
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(
            session_date="2026-07-26",
            session_type="synthetic_testbed",
        ),
        actor_id="therapist-demo",
    )
    settings = Settings(storage_mode="supabase_private")
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_storage_adapter] = (
        lambda: SupabasePrivateStorageAdapter()
    )
    try:
        response = TestClient(app).post(
            f"/api/v1/sessions/{session.session_id}/audio/upload",
            json={
                "filename": "synthetic.wav",
                "content_type": "audio/wav",
                "size_bytes": 1024,
            },
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_storage_adapter, None)

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "storage_capability_unavailable"
    assert response.json()["detail"]["remediation"]
    assert repo.audio_files == {}
