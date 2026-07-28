from __future__ import annotations

from io import BytesIO
from hashlib import sha256
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import httpx
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
    SupabaseStorageHttpClient,
    get_storage_adapter,
)


class FakePrivateBucket:
    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.storage_url = "https://project.supabase.test/storage/v1"
        self.bucket_name = "private-audio"
        self.objects = dict(objects or {})
        self.removed: list[str] = []
        self.fail_upload_once = False
        self.corrupt_upload_once = False
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
        if self.fail_upload_once:
            self.fail_upload_once = False
            raise OSError("synthetic upload failure")
        if (
            file_options.get("upsert") in {False, "false"}
            and object_key in self.objects
        ):
            raise FileExistsError(object_key)
        source.seek(0)
        payload = source.read()
        if self.corrupt_upload_once:
            self.corrupt_upload_once = False
            payload += b"-corrupted"
        self.objects[object_key] = payload

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
        storage_backend_identity_sha256=sha256(
            (
                "supabase-private-v1\0"
                "https://project.supabase.test/storage/v1\0"
                "private-audio"
            ).encode("utf-8")
        ).hexdigest(),
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


def test_storage_factory_builds_concrete_configured_supabase_rest_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.storage_service as storage_service

    monkeypatch.setattr(
        storage_service,
        "get_settings",
        lambda: Settings(
            storage_mode="supabase_private",
            supabase_storage_url="https://project.supabase.test",
            supabase_storage_service_role_key="synthetic-service-key",
            supabase_storage_bucket="private-audio",
        ),
    )

    adapter = storage_service.get_storage_adapter()

    assert isinstance(adapter, SupabasePrivateStorageAdapter)
    assert isinstance(adapter.bucket_client, SupabaseStorageHttpClient)
    assert adapter.bucket_name == "private-audio"


def test_supabase_rest_client_uses_private_non_upserting_object_api() -> None:
    requests: list[httpx.Request] = []
    objects: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        key = request.url.path.split("/private-audio/", 1)[-1]
        if request.method == "POST":
            if key in objects:
                return httpx.Response(
                    409,
                    json={"message": "The resource already exists"},
                )
            objects[key] = request.read()
            return httpx.Response(200, json={"Key": key})
        if request.method == "GET":
            if key not in objects:
                return httpx.Response(404)
            return httpx.Response(200, content=objects[key])
        if request.method == "DELETE":
            for object_key in request.read().decode("utf-8").split('"'):
                objects.pop(object_key, None)
            return httpx.Response(200, json=[])
        return httpx.Response(405)

    client = SupabaseStorageHttpClient(
        project_url="https://project.supabase.test",
        service_role_key="synthetic-service-key",
        bucket_name="private-audio",
        transport=httpx.MockTransport(handler),
    )
    client.upload(
        "audio/receipt.stage",
        BytesIO(b"private-bytes"),
        {
            "content-type": "application/octet-stream",
            "upsert": "false",
        },
    )
    assert b"".join(client.download_stream("audio/receipt.stage")) == (
        b"private-bytes"
    )
    with pytest.raises(FileExistsError):
        client.upload(
            "audio/receipt.stage",
            BytesIO(b"replacement"),
            {"upsert": "false"},
        )
    client.remove(["audio/receipt.stage"])

    assert objects == {}
    upload_request = requests[0]
    assert upload_request.headers["x-upsert"] == "false"
    assert upload_request.headers["authorization"].startswith("Bearer ")


def test_supabase_normalized_upload_uses_standard_client_and_verifies_bytes() -> None:
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

    bucket.corrupt_upload_once = True
    with pytest.raises(StorageProcessingError) as captured:
        adapter.persist_normalized_asset(
            _supabase_audio(),
            BytesIO(b"new-normalized-wave"),
            content_type="audio/wav",
        )
    assert captured.value.code == "storage_write_failed"
    assert not any(key.startswith(".staging/") for key in bucket.objects)
    assert bucket.removed


def test_supabase_legacy_source_upload_uses_standard_client_surface() -> None:
    bucket = FakePrivateBucket()
    adapter = SupabasePrivateStorageAdapter(
        bucket_client=bucket,
        bucket_name="private-audio",
        max_download_size_bytes=1024,
    )
    audio = _supabase_audio("audio/legacy-source.wav")

    written = adapter.persist_source_upload(
        audio,
        BytesIO(b"legacy-source"),
        max_size_bytes=1024,
    )

    assert written == len(b"legacy-source")
    assert bucket.objects[audio.object_key] == b"legacy-source"


def test_supabase_receipt_upload_stages_promotes_and_cleans_exact_keys() -> None:
    bucket = FakePrivateBucket()
    adapter = SupabasePrivateStorageAdapter(
        bucket_client=bucket,
        bucket_name="private-audio",
        max_download_size_bytes=1024,
    )
    audio = _supabase_audio()
    audio.upload_status = "pending"
    payload = b"supabase-private-receipt"
    receipt = adapter.build_source_upload_receipt(
        audio,
        expected_consent_version=1,
        checksum_sha256=sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )
    reserved = []

    assert adapter.stage_source_upload(
        receipt,
        BytesIO(payload),
        max_size_bytes=1024,
        reserve=lambda: reserved.append(receipt.receipt_id),
    ) == len(payload)
    assert reserved == [receipt.receipt_id]
    assert bucket.objects[receipt.staging_object_key] == payload
    adapter.promote_source_upload(receipt)
    assert receipt.staging_object_key not in bucket.objects
    assert bucket.objects[receipt.intended_final_object_key] == payload

    cleanup = adapter.cleanup_upload_attempt(receipt)
    assert cleanup.succeeded
    assert receipt.intended_final_object_key not in bucket.objects


def test_supabase_receipt_promotion_never_overwrites_unowned_final() -> None:
    bucket = FakePrivateBucket()
    adapter = SupabasePrivateStorageAdapter(
        bucket_client=bucket,
        bucket_name="private-audio",
        max_download_size_bytes=1024,
    )
    audio = _supabase_audio()
    payload = b"owned-staging"
    receipt = adapter.build_source_upload_receipt(
        audio,
        expected_consent_version=1,
        checksum_sha256=sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )
    bucket.objects[receipt.intended_final_object_key] = b"unowned-final"
    adapter.stage_source_upload(
        receipt,
        BytesIO(payload),
        max_size_bytes=1024,
        reserve=lambda: None,
    )

    with pytest.raises(Exception):
        adapter.promote_source_upload(receipt)
    cleanup = adapter.cleanup_upload_attempt(receipt)

    assert cleanup.staging.deleted is True
    assert cleanup.final.deleted is False
    assert (
        bucket.objects[receipt.intended_final_object_key]
        == b"unowned-final"
    )


def test_supabase_receipt_rejects_checksum_mismatch_without_remote_bytes() -> None:
    from app.services.storage_service import StorageProcessingError

    bucket = FakePrivateBucket()
    adapter = SupabasePrivateStorageAdapter(
        bucket_client=bucket,
        bucket_name="private-audio",
        max_download_size_bytes=1024,
    )
    audio = _supabase_audio()
    receipt = adapter.build_source_upload_receipt(
        audio,
        expected_consent_version=1,
        checksum_sha256=sha256(b"expected").hexdigest(),
        size_bytes=len(b"actual"),
    )

    with pytest.raises(StorageProcessingError) as captured:
        adapter.stage_source_upload(
            receipt,
            BytesIO(b"actual"),
            max_size_bytes=1024,
            reserve=lambda: None,
        )

    assert captured.value.code == "storage_receipt_integrity_mismatch"
    assert bucket.objects == {}


def test_supabase_receipt_promotion_failure_is_retryable() -> None:
    bucket = FakePrivateBucket()
    adapter = SupabasePrivateStorageAdapter(
        bucket_client=bucket,
        bucket_name="private-audio",
        max_download_size_bytes=1024,
    )
    audio = _supabase_audio()
    payload = b"retryable-promotion"
    receipt = adapter.build_source_upload_receipt(
        audio,
        expected_consent_version=1,
        checksum_sha256=sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )
    adapter.stage_source_upload(
        receipt,
        BytesIO(payload),
        max_size_bytes=1024,
        reserve=lambda: None,
    )
    bucket.fail_upload_once = True

    with pytest.raises(Exception):
        adapter.promote_source_upload(receipt)
    assert bucket.objects[receipt.staging_object_key] == payload

    adapter.promote_source_upload(receipt)
    assert bucket.objects[receipt.intended_final_object_key] == payload


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
        storage_backend_identity_sha256=(
            LocalPrivateStorageAdapter(
                tmp_path
            ).storage_backend_identity_sha256
        ),
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


def test_supabase_upload_and_withdrawal_share_repository_fence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.consent_service import withdraw_consent

    repo = MockRepository()
    audio = AudioFileMetadata(
        audio_file_id="aud_supabase_fenced_withdrawal",
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=len(b"private-audio"),
        storage_mode="supabase_private",
        object_key="audio/supabase-fenced.wav",
        upload_status="pending",
    )
    repo.audio_files[audio.audio_file_id] = audio
    promotion_started = Event()
    allow_promotion = Event()

    class PausingStandardBucket(FakePrivateBucket):
        def upload(self, object_key, source, file_options):
            super().upload(object_key, source, file_options)
            if ".attempt-" in object_key:
                promotion_started.set()
                assert allow_promotion.wait(timeout=5)

    bucket = PausingStandardBucket()
    storage = SupabasePrivateStorageAdapter(
        bucket_client=bucket,
        bucket_name="private-audio",
        max_download_size_bytes=1024,
    )
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        lambda: storage,
    )
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_storage_adapter] = lambda: storage
    app.dependency_overrides[get_settings] = lambda: Settings(
        storage_mode="supabase_private",
    )
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            upload_future = executor.submit(
                TestClient(app).put,
                f"/api/v1/audio/{audio.audio_file_id}/upload-file",
                content=b"private-audio",
            )
            assert promotion_started.wait(timeout=5)
            withdrawal_future = executor.submit(
                withdraw_consent,
                repo,
                audio.case_id,
                "Synthetic concurrent withdrawal.",
            )
            allow_promotion.set()
            upload_response = upload_future.result(timeout=5)
            withdrawal_future.result(timeout=5)
    finally:
        app.dependency_overrides.pop(get_repository, None)
        app.dependency_overrides.pop(get_storage_adapter, None)
        app.dependency_overrides.pop(get_settings, None)

    assert upload_response.status_code == 200
    assert repo.audio_files[audio.audio_file_id].upload_status == "withdrawn"
    assert repo.audio_files[audio.audio_file_id].retained is False
    assert bucket.objects == {}
