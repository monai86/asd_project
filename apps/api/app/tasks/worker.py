"""Worker entrypoint for local asynchronous audio jobs."""

from app.api.v1.dependencies import get_repository
from app.services.audio_job_service import run_audio_processing_job
from app.tasks.job_queue import get_job_queue


def run_worker_once() -> dict:
    queue = get_job_queue()
    queued = queue.dequeue()
    if queued is None:
        return {"status": "idle", "processed": 0}
    repo = get_repository()
    job = run_audio_processing_job(repo, queued.job_id)
    return {"status": "processed", "processed": 1, "job_id": job.job_id, "job_status": job.status.value}


def run_worker() -> str:
    result = run_worker_once()
    if result["status"] == "idle":
        return "Therapist App v2 worker is ready; no queued jobs."
    return f"Therapist App v2 worker processed job {result['job_id']} with status {result['job_status']}."
