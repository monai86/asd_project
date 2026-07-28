"""Worker-owned reconciliation for private audio cleanup remediations."""

from __future__ import annotations

from datetime import datetime

from app.repositories.base import ClinicalRepository
from app.schemas.clinical import utc_now
from app.services.consent_service import recover_audio_upload_cleanup
from app.services.storage_service import BaseStorageAdapter


def reconcile_due_audio_upload_cleanups(
    repo: ClinicalRepository,
    storage_adapter: BaseStorageAdapter,
    *,
    now: datetime | None = None,
    limit: int = 25,
) -> dict[str, int]:
    """Retry a bounded batch without exposing receipt keys or nonces."""

    attempted_at = now or utc_now()
    audio_file_ids = repo.list_due_audio_upload_cleanups(
        attempted_at,
        limit=limit,
    )
    result = {
        "discovered": len(audio_file_ids),
        "succeeded": 0,
        "failed": 0,
        "escalated": 0,
    }
    for audio_file_id in audio_file_ids:
        try:
            succeeded = recover_audio_upload_cleanup(
                repo,
                audio_file_id,
                storage_adapter=storage_adapter,
                actor_id="upload-cleanup-worker",
                attempted_at=attempted_at,
                only_if_due_at=attempted_at,
            )
        except Exception:  # noqa: BLE001
            result["failed"] += 1
            continue
        if succeeded is None:
            continue
        if succeeded:
            result["succeeded"] += 1
            continue
        current = repo.audio_files.get(audio_file_id)
        remediation = (
            current.upload_cleanup_remediation
            if current is not None
            else None
        )
        if remediation is not None and remediation.state == "escalated":
            result["escalated"] += 1
        else:
            result["failed"] += 1
    return result
