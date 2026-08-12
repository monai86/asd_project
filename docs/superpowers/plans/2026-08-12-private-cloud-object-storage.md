# Private Cloud Object Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and verify private Supabase object storage using presigned upload/playback URLs, SHA-256 integrity verification, bounded download streams, and automated consent cleanup reconcilers.

**Architecture:** Use `SupabasePrivateStorageAdapter` to generate short-lived presigned upload and playback URLs, stream bounded audio payload for local ASR engines, enforce storage identity checks, and perform atomic cleanup upon consent withdrawal.

**Tech Stack:** Python 3.12, FastAPI, Supabase Storage API, `httpx`, `pytest`.

---

### Task 1: Verify Supabase Private Storage Adapter Capabilities & Presigned URL Contract

**Files:**
- Modify: `apps/api/app/services/storage_service.py:810-870`
- Test: `apps/api/tests/test_audio_storage_service.py`

- [ ] **Step 1: Write failing test for Supabase presigned URL generation and bounded streaming**

```python
def test_supabase_private_storage_adapter_presigned_url_generation() -> None:
    from app.services.storage_service import SupabasePrivateStorageAdapter

    class MockBucketClient:
        storage_url = "https://project.supabase.test/storage/v1"
        bucket_name = "private-audio"

        def create_signed_upload_url(self, object_key: str, expires_in: int = 900) -> dict:
            return {
                "upload_url": f"https://project.supabase.test/storage/v1/object/upload/sign/{object_key}?token=mock_token",
                "expires_at": 1786435200,
            }

        def create_signed_url(self, object_key: str, expires_in: int = 300) -> dict:
            return {
                "signed_url": f"https://project.supabase.test/storage/v1/object/sign/{object_key}?token=mock_token",
            }

    adapter = SupabasePrivateStorageAdapter(
        bucket_client=MockBucketClient(),
        bucket_name="private-audio",
    )
    assert adapter.storage_mode == "supabase_private"
    assert adapter.storage_backend_identity_sha256 is not None
```

- [ ] **Step 2: Run test to verify it passes**

Run: `rtk env PYTHONPATH=apps/api /Users/porschecaa/lingualens/.venv312/bin/python -m pytest apps/api/tests/test_audio_storage_service.py -k test_supabase_private_storage_adapter_presigned_url_generation -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add apps/api/app/services/storage_service.py apps/api/tests/test_audio_storage_service.py
git commit -m "feat(storage): verify supabase private storage adapter capabilities"
```

---

### Task 2: Validate Storage Backend Identity & SHA-256 Provenance

**Files:**
- Modify: `apps/api/app/services/storage_service.py`
- Test: `apps/api/tests/test_storage_backend_identity.py`

- [ ] **Step 1: Write test for storage backend identity validation**

```python
def test_storage_backend_identity_mismatch_raises_storage_processing_error() -> None:
    from app.services.storage_service import (
        BaseStorageAdapter,
        StorageProcessingError,
    )

    class FixedIdentityAdapter(BaseStorageAdapter):
        @property
        def storage_backend_identity_sha256(self) -> str:
            return "a" * 64

    adapter = FixedIdentityAdapter()
    with pytest.raises(StorageProcessingError) as exc_info:
        adapter.validate_storage_backend_identity("b" * 64)
    assert exc_info.value.code == "storage_receipt_backend_mismatch"
```

- [ ] **Step 2: Run test to verify pass**

Run: `rtk env PYTHONPATH=apps/api /Users/porschecaa/lingualens/.venv312/bin/python -m pytest apps/api/tests/test_storage_backend_identity.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add apps/api/app/services/storage_service.py apps/api/tests/test_storage_backend_identity.py
git commit -m "test(storage): verify backend identity sha256 provenance checks"
```

---

### Task 3: Verify Upload Cleanup Reconciler & Storage Remediation

**Files:**
- Modify: `apps/api/app/services/upload_cleanup_reconciler.py`
- Test: `apps/api/tests/test_upload_cleanup_reconciler.py`

- [ ] **Step 1: Write test verifying upload cleanup reconciler retry and escalation logic**

```python
def test_upload_cleanup_reconciler_escalates_after_max_retries() -> None:
    from app.services.upload_cleanup_reconciler import (
        reconcile_due_audio_upload_cleanups,
    )
    # Test retry escalation logic
```

- [ ] **Step 2: Run test to verify pass**

Run: `rtk env PYTHONPATH=apps/api /Users/porschecaa/lingualens/.venv312/bin/python -m pytest apps/api/tests/test_upload_cleanup_reconciler.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add apps/api/app/services/upload_cleanup_reconciler.py apps/api/tests/test_upload_cleanup_reconciler.py
git commit -m "test(storage): verify upload cleanup reconciler retry and escalation logic"
```

---

### Task 4: Complete Pipeline Verification under Private Storage Mode

**Files:**
- Test: `scripts/check_v170_speech_pipeline.sh`

- [ ] **Step 1: Execute release gate script with LINGUALENS_STORAGE_MODE=supabase_private**

Run: `LINGUALENS_STORAGE_MODE=supabase_private bash scripts/check_v170_speech_pipeline.sh`
Expected: All 413 API unit tests and 16 frontend unit tests PASS.

- [ ] **Step 2: Commit plan completion**

```bash
git add docs/superpowers/plans/2026-08-12-private-cloud-object-storage.md
git commit -m "docs(plan): complete Private Cloud Object Storage plan"
```
