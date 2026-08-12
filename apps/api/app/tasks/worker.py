"""Worker entrypoint for local asynchronous audio jobs."""

from pathlib import Path
import re
from threading import Event, Thread
import tempfile

from app.api.v1.dependencies import get_repository
from app.repositories.base import ProcessingJobStateConflictError
from app.schemas.clinical import JobStatus
from app.services.audio_job_service import (
    append_job_status,
    run_audio_processing_job,
)
from app.tasks.job_queue import get_job_queue
from app.services.storage_service import get_storage_adapter
from app.services.upload_cleanup_service import (
    reconcile_due_audio_upload_cleanups,
)


def _remove_recovered_staged_audio(job_id: str) -> None:
    if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", job_id) is None:
        return
    temporary_root = Path(tempfile.gettempdir())
    for candidate in temporary_root.glob(
        f"lingualens-asr-{job_id}-*.wav"
    ):
        if candidate.is_file():
            candidate.unlink(missing_ok=True)


def _recover_claimed_job(queued, repo) -> None:
    if queued.recovered_from_claim_id is None:
        return
    _remove_recovered_staged_audio(queued.job_id)
    current = repo.get_processing_job(queued.job_id)
    if current is None or current.status is not JobStatus.processing:
        return
    current.status = JobStatus.failed
    current.error_code = "worker_lease_expired"
    current.message = (
        "The worker lease expired before transcription completed; "
        "start an explicit retry."
    )
    current.details = {
        **current.details,
        "retry_allowed": True,
        "worker_recovery": {
            "code": "worker_lease_expired",
            "recovered_from_claim_id": (
                queued.recovered_from_claim_id
            ),
            "staged_audio_removed": True,
        },
    }
    append_job_status(current, JobStatus.failed)
    try:
        repo.update_processing_job(
            current,
            expected_status=JobStatus.processing,
            audit_action="transcription.worker_lease_expired",
            audit_message=(
                "Expired worker lease recovered into an explicit "
                "retryable failed state."
            ),
        )
    except ProcessingJobStateConflictError:
        return


def run_worker_once() -> dict:
    queue = get_job_queue()
    repo = get_repository()
    try:
        cleanup = reconcile_due_audio_upload_cleanups(
            repo,
            get_storage_adapter(),
        )
    except Exception:  # noqa: BLE001
        cleanup = {
            "discovered": 0,
            "succeeded": 0,
            "failed": 1,
            "escalated": 0,
        }
    queue.recover_expired()
    queued = queue.dequeue()
    if queued is None:
        return {"status": "idle", "processed": 0, "cleanup": cleanup}
    _recover_claimed_job(queued, repo)
    current = repo.get_processing_job(queued.job_id)
    if (
        current is not None
        and current.status is JobStatus.queued
        and queued.claim_id is not None
    ):
        current.details = {
            **current.details,
            "queue_claim": {
                "claim_id": queued.claim_id,
                "owner_id": queued.owner_id,
                "lease_expires_at": queued.lease_expires_at,
            },
        }
        try:
            repo.update_processing_job(
                current,
                expected_status=JobStatus.queued,
                audit_action="transcription.job_claimed",
                audit_message=(
                    "Worker claimed queued transcription with a durable "
                    "lease."
                ),
            )
        except ProcessingJobStateConflictError:
            pass
    stop_heartbeat = Event()

    def heartbeat_claim() -> None:
        while not stop_heartbeat.wait(10):
            if not queue.heartbeat(queued):
                return

    heartbeat = Thread(
        target=heartbeat_claim,
        name="lingualens-job-lease-heartbeat",
        daemon=True,
    )
    heartbeat.start()
    try:
        job = run_audio_processing_job(repo, queued.job_id)
    except BaseException:
        raise
    else:
        queue.ack(queued)
    finally:
        stop_heartbeat.set()
        heartbeat.join(timeout=1)
    return {
        "status": "processed",
        "processed": 1,
        "job_id": job.job_id,
        "job_status": job.status.value,
        "cleanup": cleanup,
    }


def process_next_job() -> dict:
    """Process a single queued transcription job or reconcile cleanups if idle."""
    return run_worker_once()


def run_worker() -> str:
    result = run_worker_once()
    if result["status"] == "idle":
        return "lingualens worker is ready; no queued jobs."
    return f"lingualens worker processed job {result['job_id']} with status {result['job_status']}."

