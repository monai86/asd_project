# Durable Task Queue & Worker Orchestration Design Document

- **Date:** 2026-08-12
- **Milestone:** Phase 3 Pilot Hardening — Redis Durable Job Queue & Worker Orchestration
- **Target Surfaces:** `apps/api/app/tasks/`, `apps/api/tests/`, `scripts/`
- **Status:** Approved Design Spec

---

## 1. Overview & Goal

LinguaLens requires a reliable, crash-resilient background task queue for audio transcription (ASR) jobs. ASR jobs are resource-heavy and must not block HTTP API request handlers or crash the main server process on worker timeouts/OOM.

This design specifies the configuration, execution, and verification of **Redis Durable Job Queue Mode** (`redis` mode), featuring atomic claim leases, heartbeat extension, worker crash recovery, subprocess isolation, and idle reconciler execution.

---

## 2. Queue Architecture & Data Model

### 2.1 Configuration
- Environment Mode: `LINGUALENS_JOB_QUEUE_MODE=redis` (fallback to `inline` or `memory` for lightweight local tests).
- Connection URL: `LINGUALENS_REDIS_URL` (default `redis://localhost:6379/0`).

### 2.2 Redis Data Structures & Lua Operations
1. **Pending List (`lingualens-app:jobs:pending`):** FIFO list storing queued job payloads `{"job_id": "<ID>"}`.
2. **Processing Hash (`lingualens-app:jobs:processing`):** Keyed by `claim_id`, storing active worker claim records:
   - `job_id`: Target job ID
   - `claim_id`: Unique UUID per claim attempt
   - `owner_id`: Worker instance identifier (`worker-<UUID>`)
   - `lease_expires_at`: Epoch timestamp when lease expires (default 60 seconds)
3. **Atomic Lua Scripts:**
   - **Enqueue:** `rpush` to pending list.
   - **Dequeue / Claim:** Atomically `LPOP` from pending and `HSET` to processing with `claim_id` and `lease_expires_at`.
   - **Heartbeat:** Atomically updates `lease_expires_at` for an active claim while ASR runs.
   - **ACK / Complete:** Atomically deletes claim from processing hash upon job completion.
   - **Recovery:** Scans processing hash for leases where `lease_expires_at < now`, re-enqueuing jobs to pending list with `recovered_from_claim_id`.

---

## 3. Worker Isolation, Timeouts & Idle Reconciliation

### 3.1 Subprocess Isolation (`one_shot_isolated_process`)
- Each ASR job executes inside a spawned child process (`multiprocessing.Process`), preventing PyTorch / CTranslate2 memory retention in the worker main loop.

### 3.2 Evidence Timeouts & Resource Bounds
- Captures wall time (`wall_time_seconds`), CPU time (`cpu_time_seconds`), and peak memory (`peak_resident_memory_bytes`).
- Jobs exceeding timeout abort child process and report `AsrExecutionTimeout` with a 64-character SHA-256 profile checksum.

### 3.3 Idle Reconciliation
- When no ASR jobs are pending, worker executes `reconcile_due_audio_upload_cleanups()` to process storage remediation queues.

---

## 4. Verification & Testing Strategy

- **Queue Durability Tests:** `pytest apps/api/tests/test_job_queue_durability.py` testing `RedisJobQueue` with `FakeRedis` and Lua scripts.
- **Processing Job CAS Tests:** `pytest apps/api/tests/test_sql_processing_job_cas.py` testing Compare-And-Swap job status transitions.
- **Worker Lifecycle Tests:** `pytest apps/api/tests/test_transcription_job_lifecycle.py`.
- **Full Release Gate Script:** `bash scripts/check_v170_speech_pipeline.sh`
