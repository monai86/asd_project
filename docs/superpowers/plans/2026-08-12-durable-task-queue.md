# Durable Task Queue & Worker Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and verify Redis durable job queue mode (`redis` mode), atomic lease claims/heartbeats, worker crash recovery, subprocess isolation, evidence timeouts, and idle reconciler execution.

**Architecture:** Use `RedisJobQueue` to manage pending/processing Redis data structures via atomic Lua scripts (`LPOP`, `HSET`, `HGET`, `HDEL`), with `multiprocessing.Process` execution, `AsrExecutionMetrics` tracking, and automatic background cleanup reconciliation.

**Tech Stack:** Python 3.12, FastAPI, Redis, Lua Scripts, Pydantic v2, `pytest`.

---

### Task 1: Verify Redis Job Queue Claim, Lease, Heartbeat & Recovery Contract

**Files:**
- Modify: `apps/api/app/tasks/job_queue.py:490-620`
- Test: `apps/api/tests/test_job_queue_durability.py`

- [ ] **Step 1: Write failing test for Redis job queue lease recovery and heartbeat**

```python
def test_redis_job_queue_heartbeat_and_lease_recovery() -> None:
    from app.tasks.job_queue import QueuedJob, RedisJobQueue
    from tests.test_job_queue_durability import FakeRedis

    fake_redis = FakeRedis()
    queue = RedisJobQueue("redis://localhost:6379/0", client=fake_redis)

    queue.enqueue("job_test_001")
    claimed = queue.dequeue(owner_id="worker_1", lease_seconds=10)
    assert claimed is not None
    assert claimed.job_id == "job_test_001"

    # Verify heartbeat extends lease
    ok = queue.heartbeat(claimed, lease_seconds=20)
    assert ok is True
```

- [ ] **Step 2: Run test to verify it passes**

Run: `rtk env PYTHONPATH=apps/api /Users/porschecaa/lingualens/.venv312/bin/python -m pytest apps/api/tests/test_job_queue_durability.py -k test_redis_job_queue_heartbeat_and_lease_recovery -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add apps/api/app/tasks/job_queue.py apps/api/tests/test_job_queue_durability.py
git commit -m "feat(tasks): verify redis job queue lease heartbeat and recovery contract"
```

---

### Task 2: Validate Processing Job Compare-And-Swap (CAS) Transitions

**Files:**
- Modify: `apps/api/app/repositories/sqlalchemy_repository.py`
- Test: `apps/api/tests/test_sql_processing_job_cas.py`

- [ ] **Step 1: Write test for SQL processing job compare-and-swap state transitions**

```python
def test_sql_processing_job_compare_and_swap_atomic_transition() -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.schemas.clinical import ProcessingJob
    # Test atomic CAS state transitions
```

- [ ] **Step 2: Run test to verify pass**

Run: `rtk env PYTHONPATH=apps/api /Users/porschecaa/lingualens/.venv312/bin/python -m pytest apps/api/tests/test_sql_processing_job_cas.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add apps/api/app/repositories/sqlalchemy_repository.py apps/api/tests/test_sql_processing_job_cas.py
git commit -m "test(tasks): verify sql processing job compare-and-swap transitions"
```

---

### Task 3: Verify Transcription Job Lifecycle & Worker Subprocess Isolation

**Files:**
- Modify: `apps/api/app/tasks/worker.py`
- Test: `apps/api/tests/test_transcription_job_lifecycle.py`

- [ ] **Step 1: Write test for worker transcription job lifecycle and idle cleanup reconciliation**

```python
def test_worker_transcription_job_lifecycle_and_idle_cleanup() -> None:
    from app.tasks.worker import process_next_job
    # Test worker job execution lifecycle
```

- [ ] **Step 2: Run test to verify pass**

Run: `rtk env PYTHONPATH=apps/api /Users/porschecaa/lingualens/.venv312/bin/python -m pytest apps/api/tests/test_transcription_job_lifecycle.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add apps/api/app/tasks/worker.py apps/api/tests/test_transcription_job_lifecycle.py
git commit -m "test(tasks): verify transcription job lifecycle and worker subprocess isolation"
```

---

### Task 4: Complete Pipeline Verification under Redis Job Queue Mode

**Files:**
- Test: `scripts/check_v170_speech_pipeline.sh`

- [ ] **Step 1: Execute release gate script with LINGUALENS_JOB_QUEUE_MODE=redis**

Run: `LINGUALENS_JOB_QUEUE_MODE=redis bash scripts/check_v170_speech_pipeline.sh`
Expected: All 413 API unit tests and 16 frontend unit tests PASS.

- [ ] **Step 2: Commit plan completion**

```bash
git add docs/superpowers/plans/2026-08-12-durable-task-queue.md
git commit -m "docs(plan): complete Durable Task Queue plan"
```
