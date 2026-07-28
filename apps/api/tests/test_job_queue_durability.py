from __future__ import annotations

import json
import os
from pathlib import Path
import pickle
import signal
from threading import Lock
import time

import pytest
from pydantic import ValidationError

from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import JobStatus, ProcessingJob
from app.tasks import job_queue as job_queue_module
from app.tasks import worker as worker_module
from app.tasks.job_queue import (
    AsrExecutionMetrics,
    AsrExecutionTimeout,
    AsrExecutionUnavailable,
    QueuedJob,
    RedisJobQueue,
    SyntheticAsrExecutionRequest,
    execute_test_asr_with_evidence_timeout,
)


class FakeRedis:
    def __init__(self) -> None:
        self.pending: list[str] = []
        self.processing: dict[str, str] = {}

    def rpush(self, key: str, value: str) -> None:
        assert key == RedisJobQueue.key
        self.pending.append(value)

    def eval(self, script: str, key_count: int, *args):
        del key_count
        if "LPOP" in script:
            if not self.pending:
                return None
            item = self.pending.pop(0)
            payload = json.loads(item)
            claim_id, owner_id, expires_at = args[2:]
            payload.update(
                claim_id=claim_id,
                owner_id=owner_id,
                lease_expires_at=float(expires_at),
            )
            encoded = json.dumps(payload, sort_keys=True)
            self.processing[claim_id] = encoded
            return encoded
        if "RPUSH" in script:
            claim_id = args[2]
            encoded = self.processing.get(claim_id)
            expected = args[3]
            if encoded is None or encoded != expected:
                return 0
            payload = json.loads(encoded)
            del self.processing[claim_id]
            self.pending.append(
                json.dumps(
                    {
                        "job_id": payload["job_id"],
                        "recovered_from_claim_id": claim_id,
                    },
                    sort_keys=True,
                )
            )
            return 1
        claim_id = args[1]
        encoded = self.processing.get(claim_id)
        if encoded is None:
            return 0
        payload = json.loads(encoded)
        owner_id = args[2]
        if payload["owner_id"] != owner_id:
            return 0
        if "lease_expires_at" in script:
            payload["lease_expires_at"] = float(args[3])
            self.processing[claim_id] = json.dumps(
                payload,
                sort_keys=True,
            )
        else:
            del self.processing[claim_id]
        return 1

    def hgetall(self, key: str) -> dict[str, str]:
        assert key == RedisJobQueue.processing_key
        return dict(self.processing)

    def llen(self, key: str) -> int:
        assert key == RedisJobQueue.key
        return len(self.pending)

    def hlen(self, key: str) -> int:
        assert key == RedisJobQueue.processing_key
        return len(self.processing)

    def delete(self, *keys: str) -> None:
        assert set(keys) == {
            RedisJobQueue.key,
            RedisJobQueue.processing_key,
        }
        self.pending.clear()
        self.processing.clear()


def _queue(client: FakeRedis | None = None) -> RedisJobQueue:
    return RedisJobQueue(
        "redis://unused",
        client=client or FakeRedis(),
    )


def _job(job_id: str, status: JobStatus) -> ProcessingJob:
    return ProcessingJob(
        job_id=job_id,
        session_id="session_demo_001",
        status=status,
        message="synthetic queue test",
        details={"attempt_number": 1, "status_history": [status.value]},
    )


_PARENT_HELD_LOCK = Lock()


def _native_like_hang(payload: dict[str, object]) -> None:
    pid_path = str(payload["pid_path"])
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    Path(pid_path).write_text(str(os.getpid()), encoding="utf-8")
    while True:
        time.sleep(0.05)


def _acquire_module_lock(_payload: dict[str, object]) -> bool:
    with _PARENT_HELD_LOCK:
        return True


def _send_result_then_ignore_sigterm(
    payload: dict[str, object],
    connection,
) -> None:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    Path(str(payload["pid_path"])).write_text(
        str(os.getpid()),
        encoding="utf-8",
    )
    connection.send_bytes(
        pickle.dumps(
            ("completed", True, 0.0, 1),
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    )
    connection.close()
    while True:
        time.sleep(0.05)


def test_hard_timeout_kills_and_reaps_uncooperative_child(
    tmp_path: Path,
) -> None:
    pid_path = tmp_path / "child.pid"
    started = time.monotonic()

    with pytest.raises(AsrExecutionTimeout) as exc_info:
        execute_test_asr_with_evidence_timeout(
            SyntheticAsrExecutionRequest(
                callable_module=__name__,
                callable_name="_native_like_hang",
                payload={"pid_path": str(pid_path)},
            ),
            timeout_seconds=3,
            timeout_profile_checksum_sha256="a" * 64,
            allow_test_provider=True,
        )

    assert exc_info.value.metrics.termination_reason == "timeout"
    assert exc_info.value.metrics.cold_warm_mode == "cold"
    assert (
        exc_info.value.metrics.warm_reuse_capability
        == "unavailable_one_shot_isolation"
    )
    assert time.monotonic() - started < 8
    child_pid = int(pid_path.read_text(encoding="utf-8"))
    with pytest.raises(ProcessLookupError):
        os.kill(child_pid, 0)


def test_spawned_child_does_not_inherit_parent_held_lock() -> None:
    _PARENT_HELD_LOCK.acquire()
    try:
        outcome = execute_test_asr_with_evidence_timeout(
            SyntheticAsrExecutionRequest(
                callable_module=__name__,
                callable_name="_acquire_module_lock",
            ),
            timeout_seconds=2,
            timeout_profile_checksum_sha256="a" * 64,
            allow_test_provider=True,
        )
    finally:
        _PARENT_HELD_LOCK.release()

    assert outcome.value is True
    assert outcome.metrics.cold_warm_mode == "cold"


def test_post_result_cleanup_kills_and_reaps_uncooperative_child(
    tmp_path: Path,
) -> None:
    pid_path = tmp_path / "post-result-child.pid"

    outcome = job_queue_module._execute_serialized_request_with_evidence_timeout(
        {"pid_path": str(pid_path)},
        child_target=_send_result_then_ignore_sigterm,
        timeout_seconds=3,
        timeout_profile_checksum_sha256="a" * 64,
    )

    assert outcome.value is True
    child_pid = int(pid_path.read_text(encoding="utf-8"))
    with pytest.raises(ProcessLookupError):
        os.kill(child_pid, 0)


def test_test_provider_executor_is_fail_closed_without_test_capability() -> None:
    with pytest.raises(AsrExecutionUnavailable) as exc_info:
        execute_test_asr_with_evidence_timeout(
            SyntheticAsrExecutionRequest(
                callable_module=__name__,
                callable_name="_acquire_module_lock",
            ),
            timeout_seconds=2,
            timeout_profile_checksum_sha256="a" * 64,
        )

    assert (
        exc_info.value.metrics.termination_reason
        == "timeout_capability_unavailable"
    )


def test_spawn_capability_failure_is_typed_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable_context(_method: str):
        raise ValueError("spawn unavailable")

    monkeypatch.setattr(
        job_queue_module.multiprocessing,
        "get_context",
        unavailable_context,
    )
    with pytest.raises(AsrExecutionUnavailable) as exc_info:
        execute_test_asr_with_evidence_timeout(
            SyntheticAsrExecutionRequest(
                callable_module=__name__,
                callable_name="_acquire_module_lock",
            ),
            timeout_seconds=2,
            timeout_profile_checksum_sha256="a" * 64,
            allow_test_provider=True,
        )

    assert (
        exc_info.value.metrics.termination_reason
        == "timeout_capability_unavailable"
    )


def test_one_shot_execution_metrics_reject_fabricated_warm_reuse() -> None:
    with pytest.raises(
        ValidationError,
        match="cannot claim warm model reuse",
    ):
        AsrExecutionMetrics(
            cold_warm_mode="warm",
            execution_isolation_mode="one_shot_isolated_process",
            warm_reuse_capability="unavailable_one_shot_isolation",
            started_monotonic_seconds=1,
            ended_monotonic_seconds=2,
            wall_time_seconds=1,
            cpu_time_seconds=0.5,
            peak_resident_memory_bytes=1,
            timeout_seconds=42,
            timeout_profile_checksum_sha256="a" * 64,
            termination_reason="completed",
        )


def test_redis_claim_heartbeat_ack_and_owner_fencing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 100.0
    monkeypatch.setattr(job_queue_module, "time", lambda: now)
    queue = _queue()
    queue.enqueue("job_queue_001")
    assert queue.size() == 1

    claimed = queue.dequeue(owner_id="worker-a", lease_seconds=10)

    assert claimed is not None
    assert claimed.lease_expires_at == 110
    assert queue.size() == 1
    stale_owner = QueuedJob(
        job_id=claimed.job_id,
        claim_id=claimed.claim_id,
        owner_id="worker-b",
        lease_expires_at=claimed.lease_expires_at,
    )
    assert queue.heartbeat(stale_owner) is False
    now = 105.0
    assert queue.heartbeat(claimed, lease_seconds=10) is True
    now = 111.0
    assert queue.recover_expired() == 0
    assert queue.ack(stale_owner) is False
    assert queue.ack(claimed) is True
    assert queue.size() == 0


def test_worker_persists_claim_metadata_before_execution_and_acks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = _queue()
    queue.enqueue("job_claim_metadata")
    repo = MockRepository()
    repo.jobs["job_claim_metadata"] = _job(
        "job_claim_metadata",
        JobStatus.queued,
    )
    monkeypatch.setattr(worker_module, "get_job_queue", lambda: queue)
    monkeypatch.setattr(worker_module, "get_repository", lambda: repo)
    monkeypatch.setattr(worker_module, "get_storage_adapter", object)

    def fail_cleanup_reconciliation(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("synthetic cleanup enumeration failure")

    monkeypatch.setattr(
        worker_module,
        "reconcile_due_audio_upload_cleanups",
        fail_cleanup_reconciliation,
    )

    def complete_without_provider(repository, job_id):
        current = repository.get_processing_job(job_id)
        assert current is not None
        assert current.details["queue_claim"]["owner_id"].startswith(
            "worker-"
        )
        current.status = JobStatus.needs_review
        return current

    monkeypatch.setattr(
        worker_module,
        "run_audio_processing_job",
        complete_without_provider,
    )

    result = worker_module.run_worker_once()

    assert result["job_status"] == JobStatus.needs_review.value
    assert result["cleanup"]["failed"] == 1
    assert queue.size() == 0
    durable = repo.get_processing_job("job_claim_metadata")
    assert durable is not None
    assert durable.details["queue_claim"]["claim_id"]
    assert durable.details["queue_claim"]["lease_expires_at"] > 0
    assert any(
        item["action"] == "transcription.job_claimed"
        for item in repo.audit_log
    )


@pytest.mark.parametrize(
    ("job_status", "expected_status"),
    [
        (JobStatus.queued, JobStatus.queued),
        (JobStatus.processing, JobStatus.failed),
        (JobStatus.needs_review, JobStatus.needs_review),
    ],
)
def test_expired_redis_lease_recovers_each_worker_crash_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    job_status: JobStatus,
    expected_status: JobStatus,
) -> None:
    now = 200.0
    monkeypatch.setattr(job_queue_module, "time", lambda: now)
    monkeypatch.setattr(
        worker_module.tempfile,
        "gettempdir",
        lambda: str(tmp_path),
    )
    queue = _queue()
    job_id = f"job_crash_{job_status.value}"
    queue.enqueue(job_id)
    claimed = queue.dequeue(owner_id="worker-crashed", lease_seconds=5)
    assert claimed is not None
    repo = MockRepository()
    repo.jobs[job_id] = _job(job_id, job_status)
    staged = tmp_path / f"lingualens-asr-{job_id}-orphan.wav"
    staged.write_bytes(b"private-normalized-audio")
    now = 206.0

    assert queue.recover_expired() == 1
    redis_client = queue.client
    replacement_queue = _queue(redis_client)
    redelivered = replacement_queue.dequeue(owner_id="worker-replacement")
    assert redelivered is not None
    worker_module._recover_claimed_job(redelivered, repo)

    recovered = repo.get_processing_job(job_id)
    assert recovered is not None
    assert recovered.status is expected_status
    assert not staged.exists()
    assert queue.size() == 1
    assert redelivered.job_id == job_id
    assert redelivered.claim_id != claimed.claim_id
    assert redelivered.recovered_from_claim_id == claimed.claim_id
    assert replacement_queue.ack(redelivered) is True
    if job_status is JobStatus.processing:
        assert recovered.error_code == "worker_lease_expired"
        assert recovered.details["retry_allowed"] is True
        assert any(
            item["action"] == "transcription.worker_lease_expired"
            for item in repo.audit_log
        )
