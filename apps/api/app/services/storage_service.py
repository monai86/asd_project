from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
from typing import BinaryIO
from uuid import uuid4

from app.core.config import get_settings
from app.schemas.clinical import AudioFileMetadata, SignedUploadIntent


class StorageProcessingError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        remediation: str,
        actual_value: object | None = None,
        configured_limit: object | None = None,
        unit: str | None = None,
    ) -> None:
        self.code = code
        self.remediation = remediation
        self.actual_value = actual_value
        self.configured_limit = configured_limit
        self.unit = unit
        super().__init__(code)


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

    def open_source_for_processing(
        self,
        audio_file: AudioFileMetadata,
    ) -> BinaryIO:
        raise NotImplementedError

    def open_normalized_for_processing(
        self,
        object_key: str,
        *,
        max_size_bytes: int,
    ) -> BinaryIO:
        raise NotImplementedError

    def persist_normalized_asset(
        self,
        audio_file: AudioFileMetadata,
        source: BinaryIO,
        *,
        content_type: str,
    ) -> str:
        raise NotImplementedError

    def persist_source_upload(
        self,
        audio_file: AudioFileMetadata,
        source: BinaryIO,
        *,
        max_size_bytes: int,
    ) -> int:
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

    def open_source_for_processing(
        self,
        audio_file: AudioFileMetadata,
    ) -> BinaryIO:
        raise StorageProcessingError(
            "storage_capability_unavailable",
            remediation="Configure private byte storage before audio verification.",
        )

    def open_normalized_for_processing(
        self,
        object_key: str,
        *,
        max_size_bytes: int,
    ) -> BinaryIO:
        raise StorageProcessingError(
            "storage_capability_unavailable",
            remediation="Configure private byte storage before normalized-audio verification.",
        )

    def persist_normalized_asset(
        self,
        audio_file: AudioFileMetadata,
        source: BinaryIO,
        *,
        content_type: str,
    ) -> str:
        raise StorageProcessingError(
            "storage_capability_unavailable",
            remediation="Configure private byte storage before audio normalization.",
        )

    def persist_source_upload(
        self,
        audio_file: AudioFileMetadata,
        source: BinaryIO,
        *,
        max_size_bytes: int,
    ) -> int:
        raise StorageProcessingError(
            "storage_capability_unavailable",
            remediation="Configure private byte storage before audio upload.",
        )


class LocalPrivateStorageAdapter(BaseStorageAdapter):
    storage_mode = "local_private"

    def __init__(self, root: Path) -> None:
        self.root = root

    def _resolve_object_path(
        self,
        object_key: str | None,
        *,
        must_exist: bool,
    ) -> Path:
        if not object_key:
            raise StorageProcessingError(
                "storage_object_key_invalid",
                remediation="Create a new private upload intent.",
            )
        root = self.root.resolve()
        candidate = (root / object_key).resolve()
        if root not in candidate.parents:
            raise StorageProcessingError(
                "storage_object_key_invalid",
                remediation="Create a new private upload intent.",
            )
        if must_exist and (not candidate.is_file() or candidate.is_symlink()):
            raise StorageProcessingError(
                "storage_object_missing",
                remediation="Upload the complete private audio object again.",
            )
        return candidate

    def _persist_atomic(
        self,
        destination: Path,
        source: BinaryIO,
        *,
        max_size_bytes: int | None,
    ) -> int:
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w+b",
                prefix=".upload-",
                suffix=".part",
                dir=destination.parent,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                os.chmod(temporary_path, 0o600)
                source.seek(0)
                total = 0
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if max_size_bytes is not None and total > max_size_bytes:
                        raise ValueError("Uploaded object exceeds the configured byte limit.")
                    temporary.write(chunk)
                temporary.flush()
                os.fsync(temporary.fileno())
            try:
                os.link(temporary_path, destination)
            except OSError as exc:
                raise StorageProcessingError(
                    "storage_write_failed",
                    remediation="Retry with a fresh private storage object.",
                ) from exc
            temporary_path.unlink()
            temporary_path = None
            return total
        except StorageProcessingError:
            raise
        except (OSError, ValueError) as exc:
            raise StorageProcessingError(
                "storage_write_failed",
                remediation="Retry with a fresh private storage object.",
            ) from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

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
        try:
            candidate = self._resolve_object_path(object_key, must_exist=False)
        except StorageProcessingError:
            return StorageDeletionResult(storage_mode=self.storage_mode, deleted=False, status="invalid_object_key")
        if not candidate.exists():
            return StorageDeletionResult(storage_mode=self.storage_mode, deleted=False, status="object_not_found")
        if candidate.is_dir():
            return StorageDeletionResult(storage_mode=self.storage_mode, deleted=False, status="object_is_directory")
        candidate.unlink()
        return StorageDeletionResult(storage_mode=self.storage_mode, deleted=True, status="deleted")

    def open_source_for_processing(
        self,
        audio_file: AudioFileMetadata,
    ) -> BinaryIO:
        candidate = self._resolve_object_path(
            audio_file.object_key,
            must_exist=True,
        )
        try:
            return candidate.open("rb")
        except OSError as exc:
            raise StorageProcessingError(
                "storage_read_failed",
                remediation="Retry after verifying private storage availability.",
            ) from exc

    def open_normalized_for_processing(
        self,
        object_key: str,
        *,
        max_size_bytes: int,
    ) -> BinaryIO:
        candidate = self._resolve_object_path(object_key, must_exist=True)
        try:
            actual_size = candidate.stat().st_size
        except OSError as exc:
            raise StorageProcessingError(
                "storage_read_failed",
                remediation="Retry after verifying private storage availability.",
            ) from exc
        if actual_size > max_size_bytes:
            raise StorageProcessingError(
                "storage_download_size_exceeded",
                actual_value=actual_size,
                configured_limit=max_size_bytes,
                unit="bytes",
                remediation="Regenerate the bounded normalized working asset.",
            )
        try:
            return candidate.open("rb")
        except OSError as exc:
            raise StorageProcessingError(
                "storage_read_failed",
                remediation="Retry after verifying private storage availability.",
            ) from exc

    def persist_normalized_asset(
        self,
        audio_file: AudioFileMetadata,
        source: BinaryIO,
        *,
        content_type: str,
    ) -> str:
        if content_type != "audio/wav":
            raise ValueError("Normalized v1.7.0 assets must use audio/wav.")
        object_key = f"normalized/{uuid4().hex}.wav"
        destination = self._resolve_object_path(object_key, must_exist=False)
        self._persist_atomic(destination, source, max_size_bytes=None)
        return object_key

    def persist_source_upload(
        self,
        audio_file: AudioFileMetadata,
        source: BinaryIO,
        *,
        max_size_bytes: int,
    ) -> int:
        destination = self._resolve_object_path(
            audio_file.object_key,
            must_exist=False,
        )
        return self._persist_atomic(
            destination,
            source,
            max_size_bytes=max_size_bytes,
        )


class SupabasePrivateStorageAdapter(BaseStorageAdapter):
    storage_mode = "supabase_private"

    def __init__(
        self,
        *,
        bucket_client=None,
        bucket_name: str = "",
        max_download_size_bytes: int = 100 * 1024 * 1024,
    ) -> None:
        self.bucket_client = bucket_client
        self.bucket_name = bucket_name
        self.max_download_size_bytes = max_download_size_bytes

    def _require_client(self):
        if self.bucket_client is None:
            raise StorageProcessingError(
                "storage_capability_unavailable",
                remediation="Configure the private Supabase service client and bucket.",
            )
        return self.bucket_client

    def _download_bounded(
        self,
        object_key: str | None,
        *,
        max_size_bytes: int,
    ) -> BinaryIO:
        if not object_key:
            raise StorageProcessingError(
                "storage_object_key_invalid",
                remediation="Create a new private upload intent.",
            )
        client = self._require_client()
        temporary = tempfile.SpooledTemporaryFile(
            mode="w+b",
            max_size=min(max_size_bytes, 16 * 1024 * 1024),
        )
        try:
            if not hasattr(client, "download_stream"):
                raise StorageProcessingError(
                    "storage_capability_unavailable",
                    remediation=(
                        "Use a private storage client with a true bounded "
                        "download_stream interface."
                    ),
                )
            chunks = client.download_stream(object_key)
            total = 0
            for chunk in chunks:
                total += len(chunk)
                if total > max_size_bytes:
                    raise StorageProcessingError(
                        "storage_download_size_exceeded",
                        actual_value=total,
                        configured_limit=max_size_bytes,
                        unit="bytes",
                        remediation="Upload or regenerate an asset within the configured byte limit.",
                    )
                temporary.write(chunk)
            temporary.seek(0)
            return temporary
        except StorageProcessingError:
            temporary.close()
            raise
        except KeyError as exc:
            temporary.close()
            raise StorageProcessingError(
                "storage_object_missing",
                remediation="Upload the complete private audio object again.",
            ) from exc
        except Exception as exc:  # noqa: BLE001
            temporary.close()
            raise StorageProcessingError(
                "storage_read_failed",
                remediation="Retry after verifying private Supabase storage availability.",
            ) from exc

    def _upload_atomic(
        self,
        destination_key: str,
        source: BinaryIO,
        *,
        content_type: str,
        max_size_bytes: int,
    ) -> int:
        client = self._require_client()
        if not hasattr(client, "upload") or not hasattr(client, "move"):
            raise StorageProcessingError(
                "storage_capability_unavailable",
                remediation="Use a private Supabase client with upload and atomic move support.",
            )
        staging_key = f".staging/{uuid4().hex}"
        staged = False
        with tempfile.SpooledTemporaryFile(
            mode="w+b",
            max_size=min(max_size_bytes, 16 * 1024 * 1024),
        ) as bounded:
            try:
                source.seek(0)
                total = 0
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_size_bytes:
                        raise StorageProcessingError(
                            "storage_write_size_exceeded",
                            actual_value=total,
                            configured_limit=max_size_bytes,
                            unit="bytes",
                            remediation="Upload an asset within the configured byte limit.",
                        )
                    bounded.write(chunk)
                bounded.seek(0)
                client.upload(
                    staging_key,
                    bounded,
                    {"content-type": content_type, "upsert": "false"},
                )
                staged = True
                client.move(staging_key, destination_key)
                staged = False
                return total
            except StorageProcessingError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise StorageProcessingError(
                    "storage_write_failed",
                    remediation="Retry with a fresh private storage object.",
                ) from exc
            finally:
                if staged and hasattr(client, "remove"):
                    try:
                        client.remove([staging_key])
                    except Exception:
                        pass

    def create_upload_intent(self, audio_file: AudioFileMetadata) -> SignedUploadIntent:
        raise StorageProcessingError(
            "storage_capability_unavailable",
            remediation="Use the backend private upload path until signed upload intents are configured.",
        )

    def delete_object(self, object_key: str | None) -> StorageDeletionResult:
        if not object_key:
            return StorageDeletionResult(self.storage_mode, False, "missing_object_key")
        client = self._require_client()
        try:
            client.remove([object_key])
        except Exception as exc:  # noqa: BLE001
            raise StorageProcessingError(
                "storage_delete_failed",
                remediation="Retry private storage cleanup.",
            ) from exc
        return StorageDeletionResult(self.storage_mode, True, "deleted")

    def open_source_for_processing(
        self,
        audio_file: AudioFileMetadata,
    ) -> BinaryIO:
        return self._download_bounded(
            audio_file.object_key,
            max_size_bytes=self.max_download_size_bytes,
        )

    def open_normalized_for_processing(
        self,
        object_key: str,
        *,
        max_size_bytes: int,
    ) -> BinaryIO:
        return self._download_bounded(
            object_key,
            max_size_bytes=max_size_bytes,
        )

    def persist_normalized_asset(
        self,
        audio_file: AudioFileMetadata,
        source: BinaryIO,
        *,
        content_type: str,
    ) -> str:
        if content_type != "audio/wav":
            raise StorageProcessingError(
                "storage_content_type_invalid",
                remediation="Persist normalized v1.7.0 assets as audio/wav.",
            )
        object_key = f"normalized/{uuid4().hex}.wav"
        self._upload_atomic(
            object_key,
            source,
            content_type=content_type,
            max_size_bytes=self.max_download_size_bytes,
        )
        return object_key

    def persist_source_upload(
        self,
        audio_file: AudioFileMetadata,
        source: BinaryIO,
        *,
        max_size_bytes: int,
    ) -> int:
        if not audio_file.object_key:
            raise StorageProcessingError(
                "storage_object_key_invalid",
                remediation="Create a new private upload intent.",
            )
        return self._upload_atomic(
            audio_file.object_key,
            source,
            content_type=audio_file.content_type,
            max_size_bytes=max_size_bytes,
        )


def get_storage_adapter() -> BaseStorageAdapter:
    settings = get_settings()
    if settings.storage_mode in {"local", "local_private"}:
        return LocalPrivateStorageAdapter(settings.resolved_local_storage_root)
    if settings.storage_mode == "supabase_private":
        return SupabasePrivateStorageAdapter(
            max_download_size_bytes=(
                settings.max_audio_file_size_mb * 1024 * 1024
            )
        )
    return MetadataOnlyStorageAdapter()
