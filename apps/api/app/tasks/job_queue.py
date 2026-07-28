from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import importlib
import json
import multiprocessing
import os
import pickle
import resource
import sys
from time import monotonic, process_time
from typing import Callable, Generic, Literal, TypeVar
from time import time
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import get_settings
from app.services.asr_providers.base import TranscriptionInput


_T = TypeVar("_T")


@dataclass(frozen=True)
class QueuedJob:
    job_id: str
    claim_id: str | None = None
    owner_id: str | None = None
    lease_expires_at: float | None = None
    recovered_from_claim_id: str | None = None


class AsrExecutionMetrics(BaseModel):
    """Resource and termination evidence for one ASR attempt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cold_warm_mode: Literal["cold", "warm"]
    execution_isolation_mode: Literal["one_shot_isolated_process"]
    warm_reuse_capability: Literal[
        "unavailable_one_shot_isolation"
    ]
    started_monotonic_seconds: float = Field(ge=0)
    ended_monotonic_seconds: float = Field(ge=0)
    wall_time_seconds: float = Field(ge=0)
    cpu_time_seconds: float = Field(ge=0)
    peak_resident_memory_bytes: int = Field(ge=0)
    timeout_seconds: int = Field(gt=0)
    timeout_profile_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    termination_reason: Literal[
        "completed",
        "timeout",
        "provider_failed",
        "timeout_capability_unavailable",
    ]

    @model_validator(mode="after")
    def validate_observed_execution_mode(self) -> "AsrExecutionMetrics":
        if self.cold_warm_mode != "cold":
            raise ValueError(
                "one-shot isolated execution cannot claim warm model reuse"
            )
        return self


@dataclass(frozen=True)
class AsrExecutionOutcome(Generic[_T]):
    value: _T
    metrics: AsrExecutionMetrics


class LocalAsrExecutionRequest(BaseModel):
    """Serializable production request reconstructed inside a spawned child."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_id: Literal["local_faster_whisper"] = "local_faster_whisper"
    transcription_input: TranscriptionInput


class SyntheticAsrExecutionRequest(BaseModel):
    """Import-only test request; production callers cannot select this path."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    callable_module: str = Field(min_length=1)
    callable_name: str = Field(min_length=1)
    payload: dict[str, object] = Field(default_factory=dict)


class AsrExecutionTimeout(TimeoutError):
    def __init__(self, metrics: AsrExecutionMetrics) -> None:
        self.metrics = metrics
        super().__init__("ASR execution exceeded the evidence-derived timeout.")


class AsrExecutionFailure(RuntimeError):
    def __init__(
        self,
        metrics: AsrExecutionMetrics,
        cause: BaseException,
    ) -> None:
        self.metrics = metrics
        self.cause = cause
        super().__init__("ASR provider execution failed.")


class AsrExecutionUnavailable(RuntimeError):
    def __init__(self, metrics: AsrExecutionMetrics) -> None:
        self.metrics = metrics
        super().__init__(
            "Evidence-derived timeout enforcement is unavailable."
        )


def _peak_resident_memory_bytes() -> int:
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if sys.platform != "darwin":
        peak *= 1024
    return max(0, peak)


def _metrics(
    *,
    started_monotonic_seconds: float,
    started_cpu_seconds: float,
    timeout_seconds: int,
    timeout_profile_checksum_sha256: str,
    termination_reason: Literal[
        "completed",
        "timeout",
        "provider_failed",
        "timeout_capability_unavailable",
    ],
    child_cpu_time_seconds: float | None = None,
    child_peak_resident_memory_bytes: int | None = None,
) -> AsrExecutionMetrics:
    ended_monotonic_seconds = monotonic()
    ended_cpu_seconds = process_time()
    return AsrExecutionMetrics(
        cold_warm_mode="cold",
        execution_isolation_mode="one_shot_isolated_process",
        warm_reuse_capability="unavailable_one_shot_isolation",
        started_monotonic_seconds=started_monotonic_seconds,
        ended_monotonic_seconds=ended_monotonic_seconds,
        wall_time_seconds=max(
            0.0,
            ended_monotonic_seconds - started_monotonic_seconds,
        ),
        cpu_time_seconds=max(
            0.0,
            (
                child_cpu_time_seconds
                if child_cpu_time_seconds is not None
                else ended_cpu_seconds - started_cpu_seconds
            ),
        ),
        peak_resident_memory_bytes=max(
            0,
            (
                child_peak_resident_memory_bytes
                if child_peak_resident_memory_bytes is not None
                else _peak_resident_memory_bytes()
            ),
        ),
        timeout_seconds=timeout_seconds,
        timeout_profile_checksum_sha256=(
            timeout_profile_checksum_sha256
        ),
        termination_reason=termination_reason,
    )


_MAX_EXECUTION_MESSAGE_BYTES = 16 * 1024 * 1024
_TERMINATION_GRACE_SECONDS = 0.5


def _terminate_kill_and_reap(process) -> bool:
    """Stop an isolated child and join it before releasing process handles."""

    if process.is_alive():
        process.terminate()
    process.join(_TERMINATION_GRACE_SECONDS)
    if process.is_alive():
        process.kill()
        process.join(_TERMINATION_GRACE_SECONDS)
    return not process.is_alive()


def _send_child_outcome(
    operation: Callable[[], object],
    connection,
) -> None:
    started_cpu_seconds = process_time()
    try:
        try:
            value = operation()
            status = "completed"
        except BaseException as exc:  # child sends type only, never raw details
            status = "provider_failed"
            value = type(exc).__name__
        child_cpu_seconds = max(
            0.0,
            process_time() - started_cpu_seconds,
        )
        child_peak_bytes = _peak_resident_memory_bytes()
        try:
            payload = pickle.dumps(
                (
                    status,
                    value,
                    child_cpu_seconds,
                    child_peak_bytes,
                ),
                protocol=pickle.HIGHEST_PROTOCOL,
            )
        except BaseException:
            payload = pickle.dumps(
                (
                    "provider_failed",
                    "ResultSerializationFailed",
                    child_cpu_seconds,
                    child_peak_bytes,
                ),
                protocol=pickle.HIGHEST_PROTOCOL,
            )
        if len(payload) > _MAX_EXECUTION_MESSAGE_BYTES:
            payload = pickle.dumps(
                (
                    "provider_failed",
                    "ResultTooLarge",
                    child_cpu_seconds,
                    child_peak_bytes,
                ),
                protocol=pickle.HIGHEST_PROTOCOL,
            )
        connection.send_bytes(payload)
    finally:
        connection.close()


def _execute_local_asr_child(
    request_payload: dict[str, object],
    connection,
) -> None:
    def operation() -> object:
        from app.services.asr_providers.local_whisper_provider import (
            LocalWhisperProvider,
        )

        request = LocalAsrExecutionRequest.model_validate(request_payload)
        provider = LocalWhisperProvider(
            profile=request.transcription_input.profile
        )
        return provider.transcribe(request.transcription_input)

    _send_child_outcome(operation, connection)


def _execute_test_asr_child(
    request_payload: dict[str, object],
    connection,
) -> None:
    def operation() -> object:
        request = SyntheticAsrExecutionRequest.model_validate(
            request_payload
        )
        module = importlib.import_module(request.callable_module)
        callable_object = getattr(module, request.callable_name)
        return callable_object(dict(request.payload))

    _send_child_outcome(operation, connection)


def _execute_serialized_request_with_evidence_timeout(
    request_payload: dict[str, object],
    *,
    child_target: Callable[[dict[str, object], object], None],
    timeout_seconds: int,
    timeout_profile_checksum_sha256: str,
) -> AsrExecutionOutcome[_T]:
    """Spawn one killable child without inheriting parent threads or locks."""

    started_monotonic_seconds = monotonic()
    started_cpu_seconds = process_time()
    try:
        context = multiprocessing.get_context("spawn")
    except ValueError:
        metrics = _metrics(
            started_monotonic_seconds=started_monotonic_seconds,
            started_cpu_seconds=started_cpu_seconds,
            timeout_seconds=timeout_seconds,
            timeout_profile_checksum_sha256=(
                timeout_profile_checksum_sha256
            ),
            termination_reason="timeout_capability_unavailable",
        )
        raise AsrExecutionUnavailable(metrics)
    parent_connection, child_connection = context.Pipe(duplex=False)
    process = context.Process(
        target=child_target,
        args=(request_payload, child_connection),
        daemon=False,
    )
    process.start()
    child_connection.close()
    try:
        if not parent_connection.poll(timeout_seconds):
            if not _terminate_kill_and_reap(process):
                metrics = _metrics(
                    started_monotonic_seconds=started_monotonic_seconds,
                    started_cpu_seconds=started_cpu_seconds,
                    timeout_seconds=timeout_seconds,
                    timeout_profile_checksum_sha256=(
                        timeout_profile_checksum_sha256
                    ),
                    termination_reason="timeout_capability_unavailable",
                )
                raise AsrExecutionUnavailable(metrics)
            metrics = _metrics(
                started_monotonic_seconds=started_monotonic_seconds,
                started_cpu_seconds=started_cpu_seconds,
                timeout_seconds=timeout_seconds,
                timeout_profile_checksum_sha256=(
                    timeout_profile_checksum_sha256
                ),
                termination_reason="timeout",
            )
            raise AsrExecutionTimeout(metrics)
        payload = parent_connection.recv_bytes(
            _MAX_EXECUTION_MESSAGE_BYTES
        )
        (
            status,
            value,
            child_cpu_seconds,
            child_peak_bytes,
        ) = pickle.loads(payload)
        if not _terminate_kill_and_reap(process):
            metrics = _metrics(
                started_monotonic_seconds=started_monotonic_seconds,
                started_cpu_seconds=started_cpu_seconds,
                timeout_seconds=timeout_seconds,
                timeout_profile_checksum_sha256=(
                    timeout_profile_checksum_sha256
                ),
                termination_reason="timeout_capability_unavailable",
            )
            raise AsrExecutionUnavailable(metrics)
        if status != "completed":
            metrics = _metrics(
                started_monotonic_seconds=started_monotonic_seconds,
                started_cpu_seconds=started_cpu_seconds,
                timeout_seconds=timeout_seconds,
                timeout_profile_checksum_sha256=(
                    timeout_profile_checksum_sha256
                ),
                termination_reason="provider_failed",
                child_cpu_time_seconds=child_cpu_seconds,
                child_peak_resident_memory_bytes=child_peak_bytes,
            )
            raise AsrExecutionFailure(metrics, RuntimeError(str(value)))
    except AsrExecutionTimeout:
        raise
    except AsrExecutionFailure:
        raise
    except AsrExecutionUnavailable:
        raise
    except BaseException as exc:
        metrics = _metrics(
            started_monotonic_seconds=started_monotonic_seconds,
            started_cpu_seconds=started_cpu_seconds,
            timeout_seconds=timeout_seconds,
            timeout_profile_checksum_sha256=(
                timeout_profile_checksum_sha256
            ),
            termination_reason="provider_failed",
        )
        raise AsrExecutionFailure(metrics, exc) from exc
    finally:
        parent_connection.close()
        if not _terminate_kill_and_reap(process):
            metrics = _metrics(
                started_monotonic_seconds=started_monotonic_seconds,
                started_cpu_seconds=started_cpu_seconds,
                timeout_seconds=timeout_seconds,
                timeout_profile_checksum_sha256=(
                    timeout_profile_checksum_sha256
                ),
                termination_reason="timeout_capability_unavailable",
            )
            raise AsrExecutionUnavailable(metrics)
        process.close()
    metrics = _metrics(
        started_monotonic_seconds=started_monotonic_seconds,
        started_cpu_seconds=started_cpu_seconds,
        timeout_seconds=timeout_seconds,
        timeout_profile_checksum_sha256=(
            timeout_profile_checksum_sha256
        ),
        termination_reason="completed",
        child_cpu_time_seconds=child_cpu_seconds,
        child_peak_resident_memory_bytes=child_peak_bytes,
    )
    return AsrExecutionOutcome(value=value, metrics=metrics)


def execute_local_asr_with_evidence_timeout(
    request: LocalAsrExecutionRequest,
    *,
    timeout_seconds: int,
    timeout_profile_checksum_sha256: str,
) -> AsrExecutionOutcome[object]:
    return _execute_serialized_request_with_evidence_timeout(
        request.model_dump(mode="python"),
        child_target=_execute_local_asr_child,
        timeout_seconds=timeout_seconds,
        timeout_profile_checksum_sha256=(
            timeout_profile_checksum_sha256
        ),
    )


def execute_test_asr_with_evidence_timeout(
    request: SyntheticAsrExecutionRequest,
    *,
    timeout_seconds: int,
    timeout_profile_checksum_sha256: str,
    allow_test_provider: bool = False,
) -> AsrExecutionOutcome[object]:
    if not allow_test_provider or "PYTEST_CURRENT_TEST" not in os.environ:
        started = monotonic()
        metrics = _metrics(
            started_monotonic_seconds=started,
            started_cpu_seconds=process_time(),
            timeout_seconds=timeout_seconds,
            timeout_profile_checksum_sha256=(
                timeout_profile_checksum_sha256
            ),
            termination_reason="timeout_capability_unavailable",
        )
        raise AsrExecutionUnavailable(metrics)
    return _execute_serialized_request_with_evidence_timeout(
        request.model_dump(mode="python"),
        child_target=_execute_test_asr_child,
        timeout_seconds=timeout_seconds,
        timeout_profile_checksum_sha256=(
            timeout_profile_checksum_sha256
        ),
    )


class MemoryJobQueue:
    """In-memory queue for local worker tests and demos."""

    def __init__(self) -> None:
        self._items: deque[str] = deque()

    def enqueue(self, job_id: str) -> None:
        if job_id not in self._items:
            self._items.append(job_id)

    def dequeue(self) -> QueuedJob | None:
        if not self._items:
            return None
        return QueuedJob(job_id=self._items.popleft())

    def size(self) -> int:
        return len(self._items)

    def heartbeat(self, queued: QueuedJob) -> bool:
        return True

    def ack(self, queued: QueuedJob) -> bool:
        return True

    def recover_expired(self) -> int:
        return 0

    def clear(self) -> None:
        self._items.clear()


class RedisJobQueue:
    """Redis pending/processing lease queue with explicit ACK and recovery."""

    key = "lingualens-app:jobs:pending"
    processing_key = "lingualens-app:jobs:processing"
    default_lease_seconds = 60

    def __init__(self, redis_url: str, *, client=None) -> None:
        if client is None:
            try:
                import redis
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    "Redis job queue mode requires the redis package."
                ) from exc
            client = redis.from_url(redis_url)
        self.client = client

    def enqueue(self, job_id: str) -> None:
        self.client.rpush(
            self.key,
            json.dumps({"job_id": job_id}, sort_keys=True),
        )

    def dequeue(
        self,
        *,
        owner_id: str | None = None,
        lease_seconds: int | None = None,
    ) -> QueuedJob | None:
        claim_id = uuid4().hex
        owner = owner_id or f"worker-{uuid4().hex}"
        expires_at = time() + (
            lease_seconds or self.default_lease_seconds
        )
        script = """
        local item = redis.call('LPOP', KEYS[1])
        if not item then return nil end
        local payload = cjson.decode(item)
        payload.claim_id = ARGV[1]
        payload.owner_id = ARGV[2]
        payload.lease_expires_at = tonumber(ARGV[3])
        local encoded = cjson.encode(payload)
        redis.call('HSET', KEYS[2], ARGV[1], encoded)
        return encoded
        """
        item = self.client.eval(
            script,
            2,
            self.key,
            self.processing_key,
            claim_id,
            owner,
            str(expires_at),
        )
        if item is None:
            return None
        payload = json.loads(item)
        return QueuedJob(
            job_id=payload["job_id"],
            claim_id=payload["claim_id"],
            owner_id=payload["owner_id"],
            lease_expires_at=float(payload["lease_expires_at"]),
            recovered_from_claim_id=payload.get(
                "recovered_from_claim_id"
            ),
        )

    def heartbeat(
        self,
        queued: QueuedJob,
        *,
        lease_seconds: int | None = None,
    ) -> bool:
        if queued.claim_id is None or queued.owner_id is None:
            return False
        expires_at = time() + (
            lease_seconds or self.default_lease_seconds
        )
        script = """
        local encoded = redis.call('HGET', KEYS[1], ARGV[1])
        if not encoded then return 0 end
        local payload = cjson.decode(encoded)
        if payload.owner_id ~= ARGV[2] then return 0 end
        payload.lease_expires_at = tonumber(ARGV[3])
        redis.call('HSET', KEYS[1], ARGV[1], cjson.encode(payload))
        return 1
        """
        return bool(
            self.client.eval(
                script,
                1,
                self.processing_key,
                queued.claim_id,
                queued.owner_id,
                str(expires_at),
            )
        )

    def ack(self, queued: QueuedJob) -> bool:
        if queued.claim_id is None or queued.owner_id is None:
            return False
        script = """
        local encoded = redis.call('HGET', KEYS[1], ARGV[1])
        if not encoded then return 0 end
        local payload = cjson.decode(encoded)
        if payload.owner_id ~= ARGV[2] then return 0 end
        redis.call('HDEL', KEYS[1], ARGV[1])
        return 1
        """
        return bool(
            self.client.eval(
                script,
                1,
                self.processing_key,
                queued.claim_id,
                queued.owner_id,
            )
        )

    def recover_expired(self) -> int:
        recovered = 0
        now = time()
        for raw_claim_id, raw_payload in (
            self.client.hgetall(self.processing_key) or {}
        ).items():
            claim_id = (
                raw_claim_id.decode()
                if isinstance(raw_claim_id, bytes)
                else str(raw_claim_id)
            )
            payload = json.loads(raw_payload)
            if float(payload["lease_expires_at"]) > now:
                continue
            script = """
            local encoded = redis.call('HGET', KEYS[1], ARGV[1])
            if not encoded or encoded ~= ARGV[2] then return 0 end
            local payload = cjson.decode(encoded)
            redis.call('HDEL', KEYS[1], ARGV[1])
            redis.call('RPUSH', KEYS[2], cjson.encode({
                job_id=payload.job_id,
                recovered_from_claim_id=ARGV[1]
            }))
            return 1
            """
            did_recover = int(
                self.client.eval(
                    script,
                    2,
                    self.processing_key,
                    self.key,
                    claim_id,
                    (
                        raw_payload.decode()
                        if isinstance(raw_payload, bytes)
                        else raw_payload
                    ),
                )
            )
            recovered += did_recover
        return recovered

    def size(self) -> int:
        return int(self.client.llen(self.key)) + int(
            self.client.hlen(self.processing_key)
        )

    def clear(self) -> None:
        self.client.delete(self.key, self.processing_key)


_memory_queue = MemoryJobQueue()


def get_job_queue():
    settings = get_settings()
    if settings.job_queue_mode == "memory":
        return _memory_queue
    if settings.job_queue_mode == "redis":
        return RedisJobQueue(settings.redis_url)
    raise RuntimeError(f"Unsupported job queue mode: {settings.job_queue_mode}")
