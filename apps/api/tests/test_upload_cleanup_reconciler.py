from __future__ import annotations

from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from threading import Lock

from app.repositories.mock_repository import JsonFileRepository
from app.schemas.clinical import AudioFileMetadata, utc_now
from app.services.storage_service import (
    LocalPrivateStorageAdapter,
    StorageProcessingError,
    SupabasePrivateStorageAdapter,
)


def _stage_pending_cleanup(
    repository_path: Path,
    storage_root: Path,
    *,
    audio_file_id: str = "aud_cleanup_reconciler",
) -> tuple[JsonFileRepository, LocalPrivateStorageAdapter, str]:
    repo = JsonFileRepository(repository_path)
    audio = AudioFileMetadata(
        audio_file_id=audio_file_id,
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=16,
        storage_mode="local_private",
        object_key=f"audio/{audio_file_id}-source.wav",
    )
    repo.audio_files[audio.audio_file_id] = audio
    repo.save()
    storage = LocalPrivateStorageAdapter(storage_root)
    payload = b"private-recovery"
    receipt = storage.build_source_upload_receipt(
        audio,
        expected_consent_version=repo.cases[audio.case_id].version,
        checksum_sha256=sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )
    storage.stage_source_upload(
        receipt,
        BytesIO(payload),
        max_size_bytes=1024,
        reserve=lambda: repo.reserve_audio_upload_attempt(
            receipt,
            actor_id="therapist-demo",
        ),
    )
    return repo, storage, audio.audio_file_id


def test_restart_reconciler_discovers_due_private_cleanup_and_removes_bytes(
    tmp_path: Path,
) -> None:
    from app.services.upload_cleanup_service import (
        reconcile_due_audio_upload_cleanups,
    )

    repo, storage, audio_file_id = _stage_pending_cleanup(
        tmp_path / "repository.json",
        tmp_path / "private",
    )
    receipt = repo.audio_files[audio_file_id].active_upload_receipt
    assert receipt is not None

    restarted = JsonFileRepository(repo.path)
    result = reconcile_due_audio_upload_cleanups(
        restarted,
        storage,
        now=utc_now(),
        limit=10,
    )

    assert result == {
        "discovered": 1,
        "succeeded": 1,
        "failed": 0,
        "escalated": 0,
    }
    durable = JsonFileRepository(repo.path).audio_files[audio_file_id]
    assert durable.upload_cleanup_remediation is None
    assert durable.active_upload_receipt is None
    assert not (storage.root / receipt.staging_object_key).exists()


def test_reconciler_failure_persists_bounded_backoff_without_private_keys(
    tmp_path: Path,
) -> None:
    from app.services.upload_cleanup_service import (
        reconcile_due_audio_upload_cleanups,
    )

    class FailingCleanupStorage(LocalPrivateStorageAdapter):
        def cleanup_upload_attempt(self, receipt):
            raise StorageProcessingError(
                "storage_delete_failed",
                remediation="Retry private cleanup.",
            )

    repo, storage, audio_file_id = _stage_pending_cleanup(
        tmp_path / "repository.json",
        tmp_path / "private",
    )
    failing = FailingCleanupStorage(storage.root)
    attempted_at = utc_now()

    result = reconcile_due_audio_upload_cleanups(
        repo,
        failing,
        now=attempted_at,
        limit=10,
    )

    assert result["failed"] == 1
    remediation = JsonFileRepository(repo.path).audio_files[
        audio_file_id
    ].upload_cleanup_remediation
    assert remediation is not None
    assert remediation.state == "failed"
    assert remediation.attempt_count == 1
    assert remediation.last_attempt_at == attempted_at
    assert remediation.next_retry_at == attempted_at + timedelta(seconds=30)
    assert remediation.backoff_version == "upload-cleanup-exp-v1"
    assert audio_file_id not in repo.list_due_audio_upload_cleanups(
        attempted_at + timedelta(seconds=29),
        limit=10,
    )
    serialized_audit = str(repo.audit_log)
    assert ".upload-attempts" not in serialized_audit
    assert "reconciler-source" not in serialized_audit

    skipped = reconcile_due_audio_upload_cleanups(
        repo,
        failing,
        now=attempted_at + timedelta(seconds=29),
        limit=10,
    )
    assert skipped == {
        "discovered": 0,
        "succeeded": 0,
        "failed": 0,
        "escalated": 0,
    }


def test_reconciler_escalates_after_bounded_attempts_with_generic_audit(
    tmp_path: Path,
) -> None:
    from app.services.upload_cleanup_service import (
        reconcile_due_audio_upload_cleanups,
    )

    class FailingCleanupStorage(LocalPrivateStorageAdapter):
        def cleanup_upload_attempt(self, receipt):
            raise StorageProcessingError(
                "storage_delete_failed",
                remediation="Retry private cleanup.",
            )

    repo, storage, audio_file_id = _stage_pending_cleanup(
        tmp_path / "repository.json",
        tmp_path / "private",
    )
    failing = FailingCleanupStorage(storage.root)
    attempted_at = utc_now()
    result = None
    for _ in range(5):
        result = reconcile_due_audio_upload_cleanups(
            repo,
            failing,
            now=attempted_at,
            limit=10,
        )
        current = JsonFileRepository(repo.path).audio_files[audio_file_id]
        remediation = current.upload_cleanup_remediation
        assert remediation is not None
        if remediation.next_retry_at is not None:
            attempted_at = remediation.next_retry_at

    assert result is not None
    assert result["escalated"] == 1
    durable_repo = JsonFileRepository(repo.path)
    remediation = durable_repo.audio_files[
        audio_file_id
    ].upload_cleanup_remediation
    assert remediation is not None
    assert remediation.state == "escalated"
    assert remediation.attempt_count == 5
    assert remediation.next_retry_at is None
    escalation_events = [
        event
        for event in durable_repo.audit_log
        if event["action"] == "audio.upload_cleanup_escalated"
    ]
    assert len(escalation_events) == 1
    assert "storage_cleanup_failed" not in str(escalation_events[0])
    assert ".upload-attempts" not in str(escalation_events[0])


def test_concurrent_reconcilers_have_one_cleanup_winner(
    tmp_path: Path,
) -> None:
    from app.services.upload_cleanup_service import (
        reconcile_due_audio_upload_cleanups,
    )

    repo, storage, audio_file_id = _stage_pending_cleanup(
        tmp_path / "repository.json",
        tmp_path / "private",
    )
    cleanup_calls: list[str] = []
    cleanup_calls_lock = Lock()

    class CountingCleanupStorage(LocalPrivateStorageAdapter):
        def cleanup_upload_attempt(self, receipt):
            with cleanup_calls_lock:
                cleanup_calls.append(receipt.receipt_id)
            return super().cleanup_upload_attempt(receipt)

    counting = CountingCleanupStorage(storage.root)
    now = utc_now()
    repositories = [
        JsonFileRepository(repo.path),
        JsonFileRepository(repo.path),
    ]
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda candidate: reconcile_due_audio_upload_cleanups(
                    candidate,
                    counting,
                    now=now,
                    limit=10,
                ),
                repositories,
            )
        )

    assert cleanup_calls and len(cleanup_calls) == 1
    assert sum(item["succeeded"] for item in results) == 1
    durable = JsonFileRepository(repo.path)
    assert durable.audio_files[audio_file_id].upload_cleanup_remediation is None
    cleanup_events = [
        event
        for event in durable.audit_log
        if event["action"] == "audio.upload_attempt_cleaned"
    ]
    assert len(cleanup_events) == 1


def test_one_cleanup_exception_does_not_block_other_due_records(
    tmp_path: Path,
) -> None:
    from app.services.upload_cleanup_service import (
        reconcile_due_audio_upload_cleanups,
    )

    repository_path = tmp_path / "repository.json"
    storage_root = tmp_path / "private"
    repo, storage, first_audio_id = _stage_pending_cleanup(
        repository_path,
        storage_root,
        audio_file_id="aud_cleanup_fails",
    )
    repo, storage, second_audio_id = _stage_pending_cleanup(
        repository_path,
        storage_root,
        audio_file_id="aud_cleanup_succeeds",
    )

    class OneFailureStorage(LocalPrivateStorageAdapter):
        def cleanup_upload_attempt(self, receipt):
            if receipt.audio_file_id == first_audio_id:
                raise RuntimeError("synthetic provider failure")
            return super().cleanup_upload_attempt(receipt)

    attempted_at = utc_now()
    result = reconcile_due_audio_upload_cleanups(
        repo,
        OneFailureStorage(storage.root),
        now=attempted_at,
        limit=10,
    )

    assert result["discovered"] == 2
    assert result["failed"] == 1
    assert result["succeeded"] == 1
    durable = JsonFileRepository(repository_path)
    failed = durable.audio_files[
        first_audio_id
    ].upload_cleanup_remediation
    assert failed is not None
    assert failed.attempt_count == 1
    assert durable.audio_files[
        second_audio_id
    ].upload_cleanup_remediation is None


def test_sql_due_enumeration_and_backoff_update_match_json(
    tmp_path: Path,
) -> None:
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
    from app.services.upload_cleanup_service import (
        reconcile_due_audio_upload_cleanups,
    )

    database_url = f"sqlite:///{tmp_path / 'cleanup.db'}"
    repo = SqlAlchemyRepository(database_url)
    storage = LocalPrivateStorageAdapter(tmp_path / "private")
    audio = AudioFileMetadata(
        audio_file_id="aud_sql_cleanup_reconciler",
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=16,
        storage_mode="local_private",
        object_key="audio/sql-reconciler-source.wav",
    )
    repo.audio_files[audio.audio_file_id] = audio
    repo.save()
    payload = b"private-recovery"
    receipt = storage.build_source_upload_receipt(
        audio,
        expected_consent_version=repo.cases[audio.case_id].version,
        checksum_sha256=sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )
    storage.stage_source_upload(
        receipt,
        BytesIO(payload),
        max_size_bytes=1024,
        reserve=lambda: repo.reserve_audio_upload_attempt(
            receipt,
            actor_id="therapist-demo",
        ),
    )

    class FailingCleanupStorage(LocalPrivateStorageAdapter):
        def cleanup_upload_attempt(self, receipt):
            raise StorageProcessingError(
                "storage_delete_failed",
                remediation="Retry private cleanup.",
            )

    attempted_at = utc_now()
    from sqlalchemy import event

    statements: list[str] = []

    def capture_statement(
        connection,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ) -> None:
        del connection, cursor, parameters, context, executemany
        statements.append(statement)

    event.listen(repo.engine, "before_cursor_execute", capture_statement)
    due = repo.list_due_audio_upload_cleanups(
        attempted_at,
        limit=10,
    )
    event.remove(repo.engine, "before_cursor_execute", capture_statement)
    assert due == [audio.audio_file_id]
    cleanup_selects = [
        statement
        for statement in statements
        if "upload_cleanup_remediation" in statement
        and statement.lstrip().upper().startswith("SELECT")
    ]
    assert cleanup_selects
    assert "LIMIT" in cleanup_selects[-1].upper()
    result = reconcile_due_audio_upload_cleanups(
        repo,
        FailingCleanupStorage(storage.root),
        now=attempted_at,
        limit=10,
    )

    assert result["failed"] == 1
    restarted = SqlAlchemyRepository(database_url)
    remediation = restarted.audio_files[
        audio.audio_file_id
    ].upload_cleanup_remediation
    assert remediation is not None
    assert remediation.attempt_count == 1
    assert remediation.next_retry_at == attempted_at + timedelta(seconds=30)
    assert restarted.list_due_audio_upload_cleanups(
        attempted_at + timedelta(seconds=29),
        limit=10,
    ) == []


def test_supabase_receipt_cleanup_uses_same_reconciler_protocol(
    tmp_path: Path,
) -> None:
    from app.services.upload_cleanup_service import (
        reconcile_due_audio_upload_cleanups,
    )

    class StandardPrivateBucket:
        def __init__(self) -> None:
            self.storage_url = "https://project.supabase.test/storage/v1"
            self.bucket_name = "private-audio"
            self.objects: dict[str, bytes] = {}
            self.removed: list[str] = []

        def upload(self, object_key, source, file_options):
            if file_options.get("upsert") in {False, "false"}:
                if object_key in self.objects:
                    raise FileExistsError(object_key)
            source.seek(0)
            self.objects[object_key] = source.read()

        def download_stream(self, object_key):
            if object_key not in self.objects:
                raise KeyError(object_key)
            yield self.objects[object_key]

        def remove(self, object_keys):
            for object_key in object_keys:
                self.removed.append(object_key)
                self.objects.pop(object_key, None)

    repo = JsonFileRepository(tmp_path / "repository.json")
    audio = AudioFileMetadata(
        audio_file_id="aud_supabase_cleanup_reconciler",
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=16,
        storage_mode="supabase_private",
        object_key="audio/supabase-reconciler-source.wav",
    )
    repo.audio_files[audio.audio_file_id] = audio
    repo.save()
    bucket = StandardPrivateBucket()
    storage = SupabasePrivateStorageAdapter(
        bucket_client=bucket,
        bucket_name="private-audio",
    )
    payload = b"private-recovery"
    receipt = storage.build_source_upload_receipt(
        audio,
        expected_consent_version=repo.cases[audio.case_id].version,
        checksum_sha256=sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )
    storage.stage_source_upload(
        receipt,
        BytesIO(payload),
        max_size_bytes=1024,
        reserve=lambda: repo.reserve_audio_upload_attempt(
            receipt,
            actor_id="therapist-demo",
        ),
    )

    result = reconcile_due_audio_upload_cleanups(
        repo,
        storage,
        now=utc_now(),
        limit=10,
    )

    assert result["succeeded"] == 1
    assert bucket.objects == {}
    assert bucket.removed == [receipt.staging_object_key]
    assert JsonFileRepository(repo.path).audio_files[
        audio.audio_file_id
    ].upload_cleanup_remediation is None


def test_worker_runs_cleanup_reconciliation_when_job_queue_is_idle(
    monkeypatch,
) -> None:
    from app.tasks import worker as worker_module

    calls: list[tuple[object, object]] = []
    storage = object()

    monkeypatch.setattr(worker_module, "get_storage_adapter", lambda: storage)
    monkeypatch.setattr(
        worker_module,
        "reconcile_due_audio_upload_cleanups",
        lambda repo, adapter, **kwargs: (
            calls.append((repo, adapter))
            or {
                "discovered": 1,
                "succeeded": 1,
                "failed": 0,
                "escalated": 0,
            }
        ),
    )

    result = worker_module.run_worker_once()

    assert len(calls) == 1
    assert result["cleanup"] == {
        "discovered": 1,
        "succeeded": 1,
        "failed": 0,
        "escalated": 0,
    }


def test_upload_cleanup_reconciler_escalates_after_max_retries(
    tmp_path: Path,
) -> None:
    from app.services.upload_cleanup_reconciler import (
        reconcile_due_audio_upload_cleanups,
    )

    class TransientFailureStorage(LocalPrivateStorageAdapter):
        def cleanup_upload_attempt(self, receipt):
            raise StorageProcessingError(
                "transient_storage_unavailable",
                remediation="Retry private upload cleanup after storage recovery.",
            )

    repo, storage, audio_file_id = _stage_pending_cleanup(
        tmp_path / "repository.json",
        tmp_path / "private",
        audio_file_id="aud_cleanup_max_retries",
    )
    failing_storage = TransientFailureStorage(storage.root)
    attempted_at = utc_now()

    for attempt in range(1, 5):
        result = reconcile_due_audio_upload_cleanups(
            repo,
            failing_storage,
            now=attempted_at,
            limit=10,
        )
        assert result["discovered"] == 1
        assert result["failed"] == 1
        assert result["succeeded"] == 0
        assert result["escalated"] == 0

        durable_audio = JsonFileRepository(repo.path).audio_files[audio_file_id]
        remediation = durable_audio.upload_cleanup_remediation
        assert remediation is not None
        assert remediation.state == "failed"
        assert remediation.attempt_count == attempt
        assert remediation.next_retry_at is not None
        assert remediation.next_retry_at > attempted_at
        attempted_at = remediation.next_retry_at

    final_result = reconcile_due_audio_upload_cleanups(
        repo,
        failing_storage,
        now=attempted_at,
        limit=10,
    )
    assert final_result["discovered"] == 1
    assert final_result["escalated"] == 1
    assert final_result["failed"] == 0
    assert final_result["succeeded"] == 0

    durable_repo = JsonFileRepository(repo.path)
    escalated_audio = durable_repo.audio_files[audio_file_id]
    remediation = escalated_audio.upload_cleanup_remediation
    assert remediation is not None
    assert remediation.state == "escalated"
    assert remediation.attempt_count == 5
    assert remediation.next_retry_at is None

    no_longer_due_result = reconcile_due_audio_upload_cleanups(
        repo,
        failing_storage,
        now=attempted_at + timedelta(hours=1),
        limit=10,
    )
    assert no_longer_due_result["discovered"] == 0
    assert no_longer_due_result["escalated"] == 0

    escalation_events = [
        event
        for event in durable_repo.audit_log
        if event["action"] == "audio.upload_cleanup_escalated"
    ]
    assert len(escalation_events) == 1
    assert escalation_events[0]["target_id"] == audio_file_id
    assert "transient_storage_unavailable" not in str(escalation_events[0])


