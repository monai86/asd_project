from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.schemas.clinical import AudioFileMetadata, SignedUploadIntent


@dataclass(frozen=True)
class StorageDeletionResult:
    storage_mode: str
    deleted: bool
    status: str


class BaseStorageAdapter:
    storage_mode = "metadata_only"

    def create_upload_intent(self, audio_file: AudioFileMetadata) -> SignedUploadIntent:
        raise NotImplementedError

    def delete_object(self, object_key: str | None) -> StorageDeletionResult:
        raise NotImplementedError


class MetadataOnlyStorageAdapter(BaseStorageAdapter):
    storage_mode = "metadata_only"

    def create_upload_intent(self, audio_file: AudioFileMetadata) -> SignedUploadIntent:
        return SignedUploadIntent(
            audio_file_id=audio_file.audio_file_id,
            upload_url=f"mock-signed-upload://{audio_file.object_key}",
            storage_mode=self.storage_mode,
            required_headers={"content-type": audio_file.content_type},
        )

    def delete_object(self, object_key: str | None) -> StorageDeletionResult:
        return StorageDeletionResult(storage_mode=self.storage_mode, deleted=False, status="metadata_only_no_object")


class LocalPrivateStorageAdapter(BaseStorageAdapter):
    storage_mode = "local_private"

    def __init__(self, root: Path) -> None:
        self.root = root

    def create_upload_intent(self, audio_file: AudioFileMetadata) -> SignedUploadIntent:
        return SignedUploadIntent(
            audio_file_id=audio_file.audio_file_id,
            upload_url=f"/audio/{audio_file.audio_file_id}/upload-file",
            storage_mode=self.storage_mode,
            required_headers={"content-type": audio_file.content_type},
        )

    def delete_object(self, object_key: str | None) -> StorageDeletionResult:
        if not object_key:
            return StorageDeletionResult(storage_mode=self.storage_mode, deleted=False, status="missing_object_key")
        candidate = (self.root / object_key).resolve()
        root = self.root.resolve()
        if root not in candidate.parents and candidate != root:
            return StorageDeletionResult(storage_mode=self.storage_mode, deleted=False, status="invalid_object_key")
        if not candidate.exists():
            return StorageDeletionResult(storage_mode=self.storage_mode, deleted=False, status="object_not_found")
        if candidate.is_dir():
            return StorageDeletionResult(storage_mode=self.storage_mode, deleted=False, status="object_is_directory")
        candidate.unlink()
        return StorageDeletionResult(storage_mode=self.storage_mode, deleted=True, status="deleted")


class SupabasePrivateStorageAdapter(BaseStorageAdapter):
    storage_mode = "supabase_private"

    def create_upload_intent(self, audio_file: AudioFileMetadata) -> SignedUploadIntent:
        raise RuntimeError("Supabase private storage adapter requires external project configuration.")

    def delete_object(self, object_key: str | None) -> StorageDeletionResult:
        raise RuntimeError("Supabase private storage adapter requires external project configuration.")


def get_storage_adapter() -> BaseStorageAdapter:
    settings = get_settings()
    if settings.storage_mode in {"local", "local_private"}:
        return LocalPrivateStorageAdapter(settings.resolved_local_storage_root)
    if settings.storage_mode == "supabase_private":
        return SupabasePrivateStorageAdapter()
    return MetadataOnlyStorageAdapter()
