from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
from hashlib import sha256
import os
from pathlib import Path
import tempfile
from threading import Lock, RLock
from typing import BinaryIO, Callable, Iterator
from urllib.parse import quote
from uuid import uuid4

import httpx

from app.core.config import get_settings
from app.schemas.clinical import (
    AudioFileMetadata,
    AudioUploadOwnershipReceipt,
    SignedUploadIntent,
)


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


@dataclass(frozen=True)
class UploadAttemptCleanupResult:
    staging: StorageDeletionResult
    final: StorageDeletionResult

    @property
    def succeeded(self) -> bool:
        successful_statuses = {
            "deleted",
            "object_not_found",
            "missing_object_key",
        }
        return (
            self.staging.status in successful_statuses
            and self.final.status in successful_statuses
        )


class BaseStorageAdapter:
    storage_mode = "metadata_only"

    @property
    def storage_backend_identity_sha256(self) -> str | None:
        return None

    def validate_storage_backend_identity(
        self,
        expected_identity_sha256: str | None,
    ) -> None:
        if expected_identity_sha256 is None:
            raise StorageProcessingError(
                "storage_receipt_backend_identity_missing",
                remediation=(
                    "Escalate legacy private storage cleanup for manual "
                    "backend provenance verification."
                ),
            )
        current_identity = self.storage_backend_identity_sha256
        if current_identity is None:
            raise StorageProcessingError(
                "storage_capability_unavailable",
                remediation=(
                    "Configure a private storage backend identity before "
                    "processing private objects."
                ),
            )
        if current_identity != expected_identity_sha256:
            raise StorageProcessingError(
                "storage_receipt_backend_mismatch",
                remediation=(
                    "Preserve private objects and escalate backend namespace "
                    "provenance review."
                ),
            )

    def ensure_available(self) -> None:
        """Fail closed before accepting metadata for a configured backend."""

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
        object_key: str | None = None,
    ) -> str:
        raise NotImplementedError

    def build_normalized_object_key(
        self,
        audio_file: AudioFileMetadata,
    ) -> str:
        del audio_file
        return f"normalized/{uuid4().hex}.wav"

    def persist_source_upload(
        self,
        audio_file: AudioFileMetadata,
        source: BinaryIO,
        *,
        max_size_bytes: int,
    ) -> int:
        raise NotImplementedError

    def build_source_upload_receipt(
        self,
        audio_file: AudioFileMetadata,
        *,
        expected_consent_version: int,
        checksum_sha256: str,
        size_bytes: int,
    ) -> AudioUploadOwnershipReceipt:
        backend_identity = self.storage_backend_identity_sha256
        if backend_identity is None:
            raise StorageProcessingError(
                "storage_capability_unavailable",
                remediation=(
                    "Configure a private storage backend identity before "
                    "issuing an upload receipt."
                ),
            )
        if audio_file.storage_backend_identity_sha256 is None:
            if (
                audio_file.upload_status != "pending"
                or audio_file.active_upload_receipt is not None
            ):
                raise StorageProcessingError(
                    "storage_receipt_backend_identity_missing",
                    remediation=(
                        "Escalate legacy private storage provenance before "
                        "issuing a new receipt."
                    ),
                )
            audio_file.storage_backend_identity_sha256 = backend_identity
        self.validate_storage_backend_identity(
            audio_file.storage_backend_identity_sha256
        )
        nonce = uuid4().hex
        base_key = audio_file.object_key or f"audio/{uuid4().hex}"
        return AudioUploadOwnershipReceipt(
            receipt_id=f"upr_{uuid4().hex}",
            audio_file_id=audio_file.audio_file_id,
            source_asset_version=audio_file.source_asset_version,
            expected_upload_status=audio_file.upload_status,
            expected_consent_version=expected_consent_version,
            staging_object_key=f".upload-attempts/{nonce}.stage",
            intended_final_object_key=(
                f"{base_key}.attempt-{nonce}"
            ),
            checksum_sha256=checksum_sha256,
            size_bytes=size_bytes,
            nonce=nonce,
            storage_provider=self.storage_mode,
            storage_backend_identity_sha256=backend_identity,
            storage_protocol_version="private-upload-attempt-v2",
        )

    @contextmanager
    def upload_attempt_fence(
        self,
        audio_file_id: str,
    ) -> Iterator[None]:
        del audio_file_id
        yield

    def stage_source_upload(
        self,
        receipt: AudioUploadOwnershipReceipt,
        source: BinaryIO,
        *,
        max_size_bytes: int,
        reserve: Callable[[], None],
    ) -> int:
        del receipt, source, max_size_bytes, reserve
        raise StorageProcessingError(
            "storage_capability_unavailable",
            remediation=(
                "Configure receipt-fenced private byte storage."
            ),
        )

    def promote_source_upload(
        self,
        receipt: AudioUploadOwnershipReceipt,
    ) -> None:
        del receipt
        raise StorageProcessingError(
            "storage_capability_unavailable",
            remediation=(
                "Configure receipt-fenced private byte storage."
            ),
        )

    def cleanup_upload_attempt(
        self,
        receipt: AudioUploadOwnershipReceipt,
    ) -> UploadAttemptCleanupResult:
        del receipt
        raise StorageProcessingError(
            "storage_capability_unavailable",
            remediation=(
                "Configure receipt-fenced private byte storage."
            ),
        )

    def cleanup_upload_staging(
        self,
        receipt: AudioUploadOwnershipReceipt,
    ) -> StorageDeletionResult:
        del receipt
        raise StorageProcessingError(
            "storage_capability_unavailable",
            remediation=(
                "Configure receipt-fenced private byte storage."
            ),
        )


_UPLOAD_FENCE_GUARD = Lock()
_UPLOAD_FENCES: dict[str, RLock] = {}


def _upload_process_lock(path: Path) -> RLock:
    key = str(path.expanduser().resolve(strict=False))
    with _UPLOAD_FENCE_GUARD:
        return _UPLOAD_FENCES.setdefault(key, RLock())


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
        object_key: str | None = None,
    ) -> str:
        del object_key
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

    @property
    def storage_backend_identity_sha256(self) -> str:
        canonical_root = str(self.root.expanduser().resolve(strict=False))
        return sha256(
            f"local-private-v1\0{canonical_root}".encode("utf-8")
        ).hexdigest()

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
        """Write exclusively to the caller-owned exact object key.

        Workflow callers durably reserve ``destination`` before private bytes
        are written. A random temporary path would place a hard-crash partial
        outside that ownership boundary. An exact-key partial is intentionally
        left addressable by the restart reconciler when the process terminates
        before this function can clean it up.
        """

        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        owns_destination = False
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(destination, flags, 0o600)
            owns_destination = True
            with os.fdopen(descriptor, "wb") as persisted:
                source.seek(0)
                total = 0
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if max_size_bytes is not None and total > max_size_bytes:
                        raise ValueError("Uploaded object exceeds the configured byte limit.")
                    persisted.write(chunk)
                persisted.flush()
                os.fsync(persisted.fileno())
            directory_descriptor = os.open(
                destination.parent,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
            owns_destination = False
            return total
        except StorageProcessingError:
            raise
        except (OSError, ValueError) as exc:
            raise StorageProcessingError(
                "storage_write_failed",
                remediation="Retry with a fresh private storage object.",
            ) from exc
        finally:
            if owns_destination:
                destination.unlink(missing_ok=True)

    @contextmanager
    def upload_attempt_fence(
        self,
        audio_file_id: str,
    ) -> Iterator[None]:
        fence_name = sha256(
            audio_file_id.encode("utf-8")
        ).hexdigest()
        fence_path = self.root / ".upload-fences" / f"{fence_name}.lock"
        fence_path.parent.mkdir(
            parents=True,
            exist_ok=True,
            mode=0o700,
        )
        process_lock = _upload_process_lock(fence_path)
        with process_lock, fence_path.open("a+b") as fence_file:
            fcntl.flock(fence_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fence_file.fileno(), fcntl.LOCK_UN)

    def _validate_receipt_provider(
        self,
        receipt: AudioUploadOwnershipReceipt,
    ) -> None:
        if (
            receipt.storage_protocol_version
            != "private-upload-attempt-v2"
        ):
            raise StorageProcessingError(
                "storage_receipt_protocol_legacy",
                remediation=(
                    "Escalate legacy receipt cleanup for manual backend "
                    "provenance verification."
                ),
            )
        if receipt.storage_provider != self.storage_mode:
            raise StorageProcessingError(
                "storage_receipt_provider_mismatch",
                remediation="Retry with the receipt's private storage provider.",
            )
        self.validate_storage_backend_identity(
            receipt.storage_backend_identity_sha256
        )

    def stage_source_upload(
        self,
        receipt: AudioUploadOwnershipReceipt,
        source: BinaryIO,
        *,
        max_size_bytes: int,
        reserve: Callable[[], None],
    ) -> int:
        self._validate_receipt_provider(receipt)
        with self.upload_attempt_fence(receipt.audio_file_id):
            reserve()
            destination = self._resolve_object_path(
                receipt.staging_object_key,
                must_exist=False,
            )
            try:
                total = self._persist_atomic(
                    destination,
                    source,
                    max_size_bytes=max_size_bytes,
                )
                actual_digest = sha256()
                with destination.open("rb") as persisted:
                    for chunk in iter(
                        lambda: persisted.read(1024 * 1024),
                        b"",
                    ):
                        actual_digest.update(chunk)
                actual_checksum = actual_digest.hexdigest()
                if (
                    total != receipt.size_bytes
                    or actual_checksum != receipt.checksum_sha256
                ):
                    raise StorageProcessingError(
                        "storage_receipt_integrity_mismatch",
                        remediation=(
                            "Retry the upload with a fresh ownership receipt."
                        ),
                    )
                return total
            except Exception:
                self.delete_object(receipt.staging_object_key)
                raise

    def promote_source_upload(
        self,
        receipt: AudioUploadOwnershipReceipt,
    ) -> None:
        self._validate_receipt_provider(receipt)
        staging = self._resolve_object_path(
            receipt.staging_object_key,
            must_exist=True,
        )
        final = self._resolve_object_path(
            receipt.intended_final_object_key,
            must_exist=False,
        )
        final.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.link(staging, final)
            staging.unlink()
        except OSError as exc:
            raise StorageProcessingError(
                "storage_promotion_failed",
                remediation=(
                    "Retry after exact receipt-owned storage cleanup."
                ),
            ) from exc

    def cleanup_upload_attempt(
        self,
        receipt: AudioUploadOwnershipReceipt,
    ) -> UploadAttemptCleanupResult:
        self._validate_receipt_provider(receipt)
        return UploadAttemptCleanupResult(
            staging=self.delete_object(receipt.staging_object_key),
            final=self.delete_object(
                receipt.intended_final_object_key
            ),
        )

    def cleanup_upload_staging(
        self,
        receipt: AudioUploadOwnershipReceipt,
    ) -> StorageDeletionResult:
        self._validate_receipt_provider(receipt)
        return self.delete_object(receipt.staging_object_key)

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
        self.validate_storage_backend_identity(
            audio_file.storage_backend_identity_sha256
        )
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
        object_key: str | None = None,
    ) -> str:
        self.validate_storage_backend_identity(
            audio_file.storage_backend_identity_sha256
        )
        if content_type != "audio/wav":
            raise ValueError("Normalized v1.7.0 assets must use audio/wav.")
        object_key = object_key or self.build_normalized_object_key(audio_file)
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
        if audio_file.storage_backend_identity_sha256 is None:
            audio_file.storage_backend_identity_sha256 = (
                self.storage_backend_identity_sha256
            )
        self.validate_storage_backend_identity(
            audio_file.storage_backend_identity_sha256
        )
        destination = self._resolve_object_path(
            audio_file.object_key,
            must_exist=False,
        )
        return self._persist_atomic(
            destination,
            source,
            max_size_bytes=max_size_bytes,
        )


class SupabaseStorageHttpClient:
    """Concrete private Supabase Storage REST service client."""

    def __init__(
        self,
        *,
        project_url: str,
        service_role_key: str,
        bucket_name: str,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if (
            not project_url.strip()
            or not service_role_key.strip()
            or not bucket_name.strip()
        ):
            raise ValueError(
                "Supabase private storage configuration is incomplete."
            )
        if timeout_seconds <= 0:
            raise ValueError(
                "Supabase storage request timeout must be positive."
            )
        self.storage_url = (
            f"{project_url.rstrip('/')}/storage/v1"
            if not project_url.rstrip("/").endswith("/storage/v1")
            else project_url.rstrip("/")
        )
        self.service_role_key = service_role_key
        self.bucket_name = bucket_name
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.service_role_key,
            "authorization": f"Bearer {self.service_role_key}",
        }

    def _object_url(self, object_key: str) -> str:
        bucket = quote(self.bucket_name, safe="")
        key = quote(object_key, safe="/")
        return f"{self.storage_url}/object/{bucket}/{key}"

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout_seconds,
            transport=self.transport,
        )

    def upload(
        self,
        object_key: str,
        source: BinaryIO,
        file_options: dict,
    ) -> None:
        source.seek(0)

        def chunks():
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                yield chunk

        headers = {
            **self._headers(),
            "content-type": str(
                file_options.get(
                    "content-type",
                    "application/octet-stream",
                )
            ),
            "cache-control": str(
                file_options.get("cache-control", "private, no-store")
            ),
            "x-upsert": str(
                file_options.get("upsert", "false")
            ).lower(),
        }
        with self._client() as client:
            response = client.post(
                self._object_url(object_key),
                headers=headers,
                content=chunks(),
            )
        if response.status_code in {400, 409}:
            try:
                detail = response.json()
            except ValueError:
                detail = {}
            duplicate_text = " ".join(
                str(detail.get(key, ""))
                for key in ("error", "message", "statusCode")
            ).lower()
            if (
                response.status_code == 409
                or "duplicate" in duplicate_text
                or "already exists" in duplicate_text
            ):
                raise FileExistsError(object_key)
        response.raise_for_status()

    def download_stream(self, object_key: str):
        with self._client() as client:
            with client.stream(
                "GET",
                self._object_url(object_key),
                headers=self._headers(),
            ) as response:
                if response.status_code == 404:
                    raise KeyError(object_key)
                response.raise_for_status()
                yield from response.iter_bytes(1024 * 1024)

    def remove(self, object_keys: list[str]) -> None:
        bucket = quote(self.bucket_name, safe="")
        with self._client() as client:
            response = client.request(
                "DELETE",
                f"{self.storage_url}/object/{bucket}",
                headers={
                    **self._headers(),
                    "content-type": "application/json",
                },
                json={"prefixes": object_keys},
            )
        response.raise_for_status()


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

    @property
    def storage_backend_identity_sha256(self) -> str | None:
        storage_url = getattr(self.bucket_client, "storage_url", None)
        client_bucket_name = getattr(
            self.bucket_client,
            "bucket_name",
            None,
        )
        if not isinstance(storage_url, str) or not storage_url.strip():
            return None
        if (
            not isinstance(client_bucket_name, str)
            or not client_bucket_name.strip()
        ):
            return None
        canonical_url = storage_url.rstrip("/")
        return sha256(
            (
                f"supabase-private-v1\0{canonical_url}\0"
                f"{client_bucket_name.strip()}"
            ).encode("utf-8")
        ).hexdigest()

    def ensure_available(self) -> None:
        client = self._require_client()
        if any(
            not hasattr(client, capability)
            for capability in ("upload", "download_stream", "remove")
        ):
            raise StorageProcessingError(
                "storage_capability_unavailable",
                remediation=(
                    "Configure the standard private Supabase upload, "
                    "bounded download, and removal interfaces."
                ),
            )
        if self.storage_backend_identity_sha256 is None:
            raise StorageProcessingError(
                "storage_capability_unavailable",
                remediation=(
                    "Configure the private Supabase project and bucket "
                    "identity."
                ),
            )
        client_bucket_name = getattr(client, "bucket_name", None)
        if (
            not isinstance(client_bucket_name, str)
            or client_bucket_name.strip() != self.bucket_name.strip()
        ):
            raise StorageProcessingError(
                "storage_backend_configuration_mismatch",
                remediation=(
                    "Align the adapter bucket with the private Supabase "
                    "client operation endpoint."
                ),
            )

    def _validate_receipt_provider(
        self,
        receipt: AudioUploadOwnershipReceipt,
    ) -> None:
        if (
            receipt.storage_protocol_version
            != "private-upload-attempt-v2"
        ):
            raise StorageProcessingError(
                "storage_receipt_protocol_legacy",
                remediation=(
                    "Escalate legacy receipt cleanup for manual backend "
                    "provenance verification."
                ),
            )
        if receipt.storage_provider != self.storage_mode:
            raise StorageProcessingError(
                "storage_receipt_provider_mismatch",
                remediation=(
                    "Retry with the receipt's private storage provider."
                ),
            )
        self.validate_storage_backend_identity(
            receipt.storage_backend_identity_sha256
        )

    def _verify_receipt_object(
        self,
        object_key: str,
        *,
        receipt: AudioUploadOwnershipReceipt,
    ) -> BinaryIO:
        source = self._download_bounded(
            object_key,
            max_size_bytes=receipt.size_bytes,
        )
        digest = sha256()
        total = 0
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            total += len(chunk)
            digest.update(chunk)
        source.seek(0)
        if (
            total != receipt.size_bytes
            or digest.hexdigest() != receipt.checksum_sha256
        ):
            source.close()
            raise StorageProcessingError(
                "storage_receipt_ownership_mismatch",
                remediation=(
                    "Preserve the object and escalate private storage "
                    "ownership review."
                ),
            )
        return source

    def _delete_receipt_key(
        self,
        object_key: str,
        *,
        receipt: AudioUploadOwnershipReceipt,
    ) -> StorageDeletionResult:
        self._validate_receipt_provider(receipt)
        client = self._require_client()
        if not hasattr(client, "remove"):
            raise StorageProcessingError(
                "storage_capability_unavailable",
                remediation=(
                    "Use a private Supabase service client with object "
                    "download and removal support."
                ),
            )
        try:
            with self._verify_receipt_object(
                object_key,
                receipt=receipt,
            ):
                client.remove([object_key])
        except StorageProcessingError as exc:
            if exc.code == "storage_object_missing":
                return StorageDeletionResult(
                    self.storage_mode,
                    False,
                    "object_not_found",
                )
            if exc.code == "storage_receipt_ownership_mismatch":
                return StorageDeletionResult(
                    self.storage_mode,
                    False,
                    "ownership_mismatch",
                )
            raise
        except KeyError:
            return StorageDeletionResult(
                self.storage_mode,
                False,
                "object_not_found",
            )
        except Exception as exc:  # noqa: BLE001
            raise StorageProcessingError(
                "storage_delete_failed",
                remediation="Retry private receipt-owned cleanup.",
            ) from exc
        return StorageDeletionResult(
            self.storage_mode,
            True,
            "deleted",
        )

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
        if any(
            not hasattr(client, capability)
            for capability in ("upload", "download_stream", "remove")
        ):
            raise StorageProcessingError(
                "storage_capability_unavailable",
                remediation=(
                    "Use the standard private Supabase upload, bounded "
                    "download, and removal interfaces."
                ),
            )

        def remote_matches(*, checksum: str, size_bytes: int) -> bool:
            with self._download_bounded(
                destination_key,
                max_size_bytes=size_bytes,
            ) as persisted:
                remote_digest = sha256()
                remote_size = 0
                for chunk in iter(
                    lambda: persisted.read(1024 * 1024),
                    b"",
                ):
                    remote_size += len(chunk)
                    remote_digest.update(chunk)
            return (
                remote_size == size_bytes
                and remote_digest.hexdigest() == checksum
            )

        with tempfile.SpooledTemporaryFile(
            mode="w+b",
            max_size=min(max_size_bytes, 16 * 1024 * 1024),
        ) as bounded:
            digest = sha256()
            total = 0
            source.seek(0)
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
                        remediation=(
                            "Upload an asset within the configured byte limit."
                        ),
                    )
                digest.update(chunk)
                bounded.write(chunk)
            checksum = digest.hexdigest()
            bounded.seek(0)
            try:
                client.upload(
                    destination_key,
                    bounded,
                    {
                        "content-type": content_type,
                        "upsert": "false",
                        "cache-control": "private, no-store",
                    },
                )
            except FileExistsError as exc:
                raise StorageProcessingError(
                    "storage_write_conflict",
                    remediation=(
                        "Retry with a fresh private destination key."
                    ),
                ) from exc
            except Exception as exc:  # noqa: BLE001
                try:
                    if remote_matches(
                        checksum=checksum,
                        size_bytes=total,
                    ):
                        return total
                except Exception:  # noqa: BLE001
                    pass
                raise StorageProcessingError(
                    "storage_write_failed",
                    remediation="Retry with a fresh private storage object.",
                ) from exc
            try:
                verified = remote_matches(
                    checksum=checksum,
                    size_bytes=total,
                )
            except Exception:  # noqa: BLE001
                verified = False
            if verified:
                return total
            try:
                client.remove([destination_key])
            except Exception:  # noqa: BLE001
                pass
            raise StorageProcessingError(
                "storage_write_failed",
                remediation=(
                    "Retry after private destination verification cleanup."
                ),
            )

    def create_upload_intent(self, audio_file: AudioFileMetadata) -> SignedUploadIntent:
        self.ensure_available()
        return SignedUploadIntent(
            audio_file_id=audio_file.audio_file_id,
            upload_url=f"/audio/{audio_file.audio_file_id}/upload-file",
            storage_mode=self.storage_mode,
            required_headers={"content-type": audio_file.content_type},
        )

    def stage_source_upload(
        self,
        receipt: AudioUploadOwnershipReceipt,
        source: BinaryIO,
        *,
        max_size_bytes: int,
        reserve: Callable[[], None],
    ) -> int:
        self.ensure_available()
        client = self._require_client()
        self._validate_receipt_provider(receipt)
        if not hasattr(client, "upload"):
            raise StorageProcessingError(
                "storage_capability_unavailable",
                remediation=(
                    "Use a private Supabase service client with standard "
                    "non-upserting upload support."
                ),
            )
        reserve()
        with tempfile.SpooledTemporaryFile(
            mode="w+b",
            max_size=min(max_size_bytes, 16 * 1024 * 1024),
        ) as bounded:
            digest = sha256()
            total = 0
            source.seek(0)
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
                        remediation=(
                            "Upload an asset within the configured byte limit."
                        ),
                    )
                digest.update(chunk)
                bounded.write(chunk)
            if (
                total != receipt.size_bytes
                or digest.hexdigest() != receipt.checksum_sha256
            ):
                raise StorageProcessingError(
                    "storage_receipt_integrity_mismatch",
                    remediation=(
                        "Retry the upload with a fresh ownership receipt."
                    ),
                )
            bounded.seek(0)
            try:
                client.upload(
                    receipt.staging_object_key,
                    bounded,
                    {
                        "content-type": "application/octet-stream",
                        "upsert": "false",
                        "cache-control": "private, no-store",
                    },
                )
            except FileExistsError as exc:
                raise StorageProcessingError(
                    "storage_staging_conflict",
                    remediation=(
                        "Retry with a fresh private upload receipt."
                    ),
                ) from exc
            except Exception as exc:  # noqa: BLE001
                raise StorageProcessingError(
                    "storage_write_failed",
                    remediation=(
                        "Retry with a fresh private storage object."
                    ),
                ) from exc
            return total

    def promote_source_upload(
        self,
        receipt: AudioUploadOwnershipReceipt,
    ) -> None:
        self.ensure_available()
        client = self._require_client()
        self._validate_receipt_provider(receipt)
        if not hasattr(client, "upload") or not hasattr(client, "remove"):
            raise StorageProcessingError(
                "storage_capability_unavailable",
                remediation=(
                    "Use a private Supabase service client with standard "
                    "non-upserting upload and removal support."
                ),
            )
        try:
            with self._verify_receipt_object(
                receipt.staging_object_key,
                receipt=receipt,
            ) as staging:
                client.upload(
                    receipt.intended_final_object_key,
                    staging,
                    {
                        "content-type": "application/octet-stream",
                        "upsert": "false",
                        "cache-control": "private, no-store",
                    },
                )
            with self._verify_receipt_object(
                receipt.intended_final_object_key,
                receipt=receipt,
            ):
                client.remove([receipt.staging_object_key])
        except FileExistsError as exc:
            raise StorageProcessingError(
                "storage_promotion_conflict",
                remediation=(
                    "Retry after exact receipt-owned storage cleanup."
                ),
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise StorageProcessingError(
                "storage_promotion_failed",
                remediation=(
                    "Retry receipt-owned promotion or cleanup."
                ),
            ) from exc

    def cleanup_upload_attempt(
        self,
        receipt: AudioUploadOwnershipReceipt,
    ) -> UploadAttemptCleanupResult:
        return UploadAttemptCleanupResult(
            staging=self._delete_receipt_key(
                receipt.staging_object_key,
                receipt=receipt,
            ),
            final=self._delete_receipt_key(
                receipt.intended_final_object_key,
                receipt=receipt,
            ),
        )

    def cleanup_upload_staging(
        self,
        receipt: AudioUploadOwnershipReceipt,
    ) -> StorageDeletionResult:
        return self._delete_receipt_key(
            receipt.staging_object_key,
            receipt=receipt,
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
        self.validate_storage_backend_identity(
            audio_file.storage_backend_identity_sha256
        )
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
        object_key: str | None = None,
    ) -> str:
        self.validate_storage_backend_identity(
            audio_file.storage_backend_identity_sha256
        )
        if content_type != "audio/wav":
            raise StorageProcessingError(
                "storage_content_type_invalid",
                remediation="Persist normalized v1.7.0 assets as audio/wav.",
            )
        object_key = object_key or self.build_normalized_object_key(audio_file)
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
        if audio_file.storage_backend_identity_sha256 is None:
            audio_file.storage_backend_identity_sha256 = (
                self.storage_backend_identity_sha256
            )
        self.validate_storage_backend_identity(
            audio_file.storage_backend_identity_sha256
        )
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
        client = (
            SupabaseStorageHttpClient(
                project_url=settings.supabase_storage_url,
                service_role_key=(
                    settings.supabase_storage_service_role_key
                ),
                bucket_name=settings.supabase_storage_bucket,
                timeout_seconds=(
                    settings.supabase_storage_request_timeout_seconds
                ),
            )
            if (
                settings.supabase_storage_url.strip()
                and settings.supabase_storage_service_role_key.strip()
                and settings.supabase_storage_bucket.strip()
            )
            else None
        )
        return SupabasePrivateStorageAdapter(
            bucket_client=client,
            bucket_name=settings.supabase_storage_bucket,
            max_download_size_bytes=(
                settings.max_audio_file_size_mb * 1024 * 1024
            )
        )
    return MetadataOnlyStorageAdapter()
