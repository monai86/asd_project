from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest

from app.core.config import Settings
from app.repositories.mock_repository import MockRepository
from app.repositories.mock_repository import JsonFileRepository
from app.schemas.clinical import (
    AudioFileMetadata,
    AudioUploadCleanupRemediation,
    AudioUploadCompleteRequest,
)
from app.services.audio_job_service import complete_audio_upload
from app.services.audio_media_service import (
    AudioIntakeError,
    verify_and_normalize_audio,
)
from app.services.consent_service import recover_audio_upload_cleanup
from app.services.storage_service import (
    LocalPrivateStorageAdapter,
    StorageProcessingError,
    SupabasePrivateStorageAdapter,
)


class IdentityBucket:
    def __init__(self, project_url: str, bucket_name: str) -> None:
        self.storage_url = f"{project_url.rstrip('/')}/storage/v1"
        self.bucket_name = bucket_name
        self.objects: dict[str, bytes] = {}

    def upload(self, object_key, source, file_options):
        if file_options.get("upsert") in {False, "false"}:
            if object_key in self.objects:
                raise FileExistsError(object_key)
        source.seek(0)
        self.objects[object_key] = source.read()

    def download_stream(self, object_key):
        if object_key not in self.objects:
            raise KeyError(object_key)
        yield self.objects[object_key]

    def remove(self, object_keys):
        for object_key in object_keys:
            self.objects.pop(object_key, None)


def test_supabase_adapter_rejects_miswired_client_bucket() -> None:
    adapter = SupabasePrivateStorageAdapter(
        bucket_client=IdentityBucket(
            "https://project-a.example.test",
            "actual-private-bucket",
        ),
        bucket_name="configured-different-bucket",
    )

    try:
        adapter.ensure_available()
    except StorageProcessingError as exc:
        assert exc.code == "storage_backend_configuration_mismatch"
    else:
        raise AssertionError("miswired Supabase bucket must fail closed")


def test_same_mode_wrong_local_root_cannot_complete_upload(
    tmp_path: Path,
) -> None:
    repo = MockRepository()
    original = LocalPrivateStorageAdapter(tmp_path / "private-original")
    wrong = LocalPrivateStorageAdapter(tmp_path / "private-wrong")
    audio = _pending_audio(
        "aud_wrong_root_completion",
        storage_mode=original.storage_mode,
        backend_identity=original.storage_backend_identity_sha256,
    )
    audio.upload_status = "pending_verification"
    repo.audio_files[audio.audio_file_id] = audio
    for storage in (original, wrong):
        path = storage.root / str(audio.object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"same-key-different-backend")

    with pytest.raises(StorageProcessingError) as captured:
        complete_audio_upload(
            repo,
            audio.audio_file_id,
            AudioUploadCompleteRequest(),
            storage_adapter=wrong,
            settings=Settings(),
        )

    assert captured.value.code == "storage_receipt_backend_mismatch"
    assert repo.audio_files[audio.audio_file_id].upload_status == (
        "pending_verification"
    )


def test_same_mode_wrong_local_root_cannot_normalize_source(
    tmp_path: Path,
) -> None:
    repo = MockRepository()
    original = LocalPrivateStorageAdapter(tmp_path / "private-original")
    wrong = LocalPrivateStorageAdapter(tmp_path / "private-wrong")
    audio = _pending_audio(
        "aud_wrong_root_normalization",
        storage_mode=original.storage_mode,
        backend_identity=original.storage_backend_identity_sha256,
    )
    audio.upload_status = "uploaded"
    repo.audio_files[audio.audio_file_id] = audio
    for storage in (original, wrong):
        path = storage.root / str(audio.object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"same-key-different-backend")

    with pytest.raises(AudioIntakeError) as captured:
        verify_and_normalize_audio(
            repo,
            audio.audio_file_id,
            storage_adapter=wrong,
            settings=Settings(),
        )

    assert captured.value.code == "storage_receipt_backend_mismatch"
    assert repo.normalized_audio_assets == {}


def _pending_audio(
    audio_file_id: str,
    *,
    storage_mode: str,
    backend_identity: str,
) -> AudioFileMetadata:
    return AudioFileMetadata(
        audio_file_id=audio_file_id,
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=16,
        storage_mode=storage_mode,
        object_key=f"audio/{audio_file_id}.wav",
        storage_backend_identity_sha256=backend_identity,
    )


def _stage_cleanup(repo, storage, audio, payload: bytes):
    repo.audio_files[audio.audio_file_id] = audio
    repo.save()
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
            actor_id="therapist-demo",
        ),
    )
    return receipt


def test_local_cleanup_rejects_different_canonical_root(
    tmp_path: Path,
) -> None:
    repo = JsonFileRepository(tmp_path / "repository.json")
    original = LocalPrivateStorageAdapter(tmp_path / "private-a")
    wrong = LocalPrivateStorageAdapter(tmp_path / "private-b")
    audio = _pending_audio(
        "aud_local_identity",
        storage_mode=original.storage_mode,
        backend_identity=original.storage_backend_identity_sha256,
    )
    receipt = _stage_cleanup(repo, original, audio, b"identity-bound")

    assert not recover_audio_upload_cleanup(
        repo,
        audio.audio_file_id,
        storage_adapter=wrong,
        actor_id="cleanup-worker",
    )

    durable = JsonFileRepository(repo.path).audio_files[audio.audio_file_id]
    assert durable.upload_cleanup_remediation is not None
    assert durable.upload_cleanup_remediation.state == "escalated"
    assert durable.upload_cleanup_remediation.error_code == (
        "storage_receipt_backend_mismatch"
    )
    assert (original.root / receipt.staging_object_key).read_bytes() == (
        b"identity-bound"
    )


def test_supabase_cleanup_rejects_project_or_bucket_change(
    tmp_path: Path,
) -> None:
    repo = JsonFileRepository(tmp_path / "repository.json")
    original_bucket = IdentityBucket(
        "https://project-a.example.test",
        "private-audio",
    )
    original = SupabasePrivateStorageAdapter(
        bucket_client=original_bucket,
        bucket_name="private-audio",
    )
    audio = _pending_audio(
        "aud_supabase_identity",
        storage_mode=original.storage_mode,
        backend_identity=original.storage_backend_identity_sha256,
    )
    receipt = _stage_cleanup(repo, original, audio, b"identity-bound")

    for project_url, bucket_name in (
        ("https://project-b.example.test", "private-audio"),
        ("https://project-a.example.test", "different-bucket"),
    ):
        wrong = SupabasePrivateStorageAdapter(
            bucket_client=IdentityBucket(project_url, bucket_name),
            bucket_name=bucket_name,
        )
        assert not recover_audio_upload_cleanup(
            repo,
            audio.audio_file_id,
            storage_adapter=wrong,
            actor_id="cleanup-worker",
        )
        durable = JsonFileRepository(repo.path).audio_files[
            audio.audio_file_id
        ]
        assert durable.upload_cleanup_remediation is not None
        assert durable.upload_cleanup_remediation.state == "escalated"
        assert durable.upload_cleanup_remediation.error_code == (
            "storage_receipt_backend_mismatch"
        )
        repo = JsonFileRepository(repo.path)
        repo.audio_files[
            audio.audio_file_id
        ].upload_cleanup_remediation = AudioUploadCleanupRemediation(
            state="pending",
            receipt=receipt,
        )
        repo.save()

    assert original_bucket.objects[receipt.staging_object_key] == (
        b"identity-bound"
    )


def test_legacy_receipt_without_identity_escalates_without_deleting(
    tmp_path: Path,
) -> None:
    repo = JsonFileRepository(tmp_path / "repository.json")
    storage = LocalPrivateStorageAdapter(tmp_path / "private")
    audio = _pending_audio(
        "aud_legacy_identity",
        storage_mode=storage.storage_mode,
        backend_identity=storage.storage_backend_identity_sha256,
    )
    receipt = _stage_cleanup(repo, storage, audio, b"legacy-bound")
    legacy_receipt = type(receipt).model_validate(
        {
            **receipt.model_dump(mode="python"),
            "storage_backend_identity_sha256": None,
            "storage_protocol_version": "private-upload-attempt-v1",
        }
    )
    repo.audio_files[
        audio.audio_file_id
    ].active_upload_receipt = legacy_receipt
    repo.audio_files[
        audio.audio_file_id
    ].upload_cleanup_remediation = AudioUploadCleanupRemediation(
        state="pending",
        receipt=legacy_receipt,
    )
    repo.save()

    assert not recover_audio_upload_cleanup(
        repo,
        audio.audio_file_id,
        storage_adapter=storage,
        actor_id="cleanup-worker",
    )

    durable = JsonFileRepository(repo.path).audio_files[audio.audio_file_id]
    assert durable.upload_cleanup_remediation is not None
    assert durable.upload_cleanup_remediation.state == "escalated"
    assert durable.upload_cleanup_remediation.error_code == (
        "storage_receipt_protocol_legacy"
    )
    assert (storage.root / receipt.staging_object_key).read_bytes() == (
        b"legacy-bound"
    )


def test_sql_receipt_v2_and_backend_identity_survive_restart(
    tmp_path: Path,
) -> None:
    from app.repositories.sqlalchemy_repository import (
        SqlAlchemyRepository,
    )

    database_url = f"sqlite:///{tmp_path / 'identity-roundtrip.db'}"
    repo = SqlAlchemyRepository(database_url)
    storage = LocalPrivateStorageAdapter(tmp_path / "private")
    audio = _pending_audio(
        "aud_sql_identity_roundtrip",
        storage_mode=storage.storage_mode,
        backend_identity=storage.storage_backend_identity_sha256,
    )
    repo.audio_files[audio.audio_file_id] = audio
    repo.save()
    receipt = storage.build_source_upload_receipt(
        audio,
        expected_consent_version=repo.cases[audio.case_id].version,
        checksum_sha256=sha256(b"roundtrip").hexdigest(),
        size_bytes=len(b"roundtrip"),
    )
    repo.reserve_audio_upload_attempt(
        receipt,
        actor_id="therapist-demo",
    )

    restarted = SqlAlchemyRepository(database_url)
    durable = restarted.audio_files[audio.audio_file_id]
    assert durable.storage_backend_identity_sha256 == (
        storage.storage_backend_identity_sha256
    )
    assert durable.active_upload_receipt is not None
    assert (
        durable.active_upload_receipt.storage_protocol_version
        == "private-upload-attempt-v2"
    )
    assert durable.active_upload_receipt.storage_backend_identity_sha256 == (
        storage.storage_backend_identity_sha256
    )


def test_sql_legacy_null_backend_identity_loads_for_manual_cleanup(
    tmp_path: Path,
) -> None:
    from app.repositories.sqlalchemy_repository import (
        SqlAlchemyRepository,
    )

    database_url = f"sqlite:///{tmp_path / 'legacy-null.db'}"
    repo = SqlAlchemyRepository(database_url)
    audio = AudioFileMetadata(
        audio_file_id="aud_sql_legacy_null",
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="legacy.wav",
        content_type="audio/wav",
        size_bytes=16,
        storage_mode="local_private",
        object_key="audio/legacy.wav",
        storage_backend_identity_sha256=None,
    )
    repo.audio_files[audio.audio_file_id] = audio
    repo.save()

    restarted = SqlAlchemyRepository(database_url)

    assert (
        restarted.audio_files[
            audio.audio_file_id
        ].storage_backend_identity_sha256
        is None
    )


def test_storage_backend_identity_mismatch_raises_storage_processing_error() -> None:
    from app.services.storage_service import (
        BaseStorageAdapter,
        StorageProcessingError,
    )

    class FixedIdentityAdapter(BaseStorageAdapter):
        @property
        def storage_backend_identity_sha256(self) -> str:
            return "a" * 64

    adapter = FixedIdentityAdapter()
    with pytest.raises(StorageProcessingError) as exc_info:
        adapter.validate_storage_backend_identity("b" * 64)
    assert exc_info.value.code == "storage_receipt_backend_mismatch"

