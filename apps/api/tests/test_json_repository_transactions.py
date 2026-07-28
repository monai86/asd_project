from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from threading import Event

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.main import app
from app.repositories.mock_repository import JsonFileRepository
from app.schemas.clinical import (
    AudioFileMetadata,
    AudioUploadCleanupRemediation,
    ChildCaseUpdate,
    JobStatus,
    OrganizationInvitationAccept,
    OrganizationInvitationCreate,
    ProcessingJob,
    ReviewStatus,
    TherapySessionUpdate,
    Transcript,
    utc_now,
)
from app.services.storage_service import (
    LocalPrivateStorageAdapter,
    StorageDeletionResult,
    get_storage_adapter,
)
from app.services.consent_service import withdraw_consent


def _job(job_id: str) -> ProcessingJob:
    return ProcessingJob(
        job_id=job_id,
        session_id="session_demo_001",
        status=JobStatus.queued,
        message="Synthetic queued job.",
        details={"attempt_number": 1},
    )


def test_stale_json_repository_audit_preserves_newer_job(tmp_path: Path) -> None:
    path = tmp_path / "repository.json"
    first = JsonFileRepository(path)
    stale = JsonFileRepository(path)

    first.create_processing_job(
        _job("job_newer"),
        audit_action="test.job.create",
        audit_message="Synthetic job created.",
    )
    stale.add_audit(
        "test.stale.audit",
        "session_demo_001",
        "Synthetic stale-repository audit.",
    )

    durable = JsonFileRepository(path)
    assert "job_newer" in durable.jobs
    assert {event["action"] for event in durable.audit_log} >= {
        "test.job.create",
        "test.stale.audit",
    }


def test_two_json_instances_serialize_job_transcript_session_and_audit_mutations(
    tmp_path: Path,
) -> None:
    path = tmp_path / "repository.json"
    JsonFileRepository(path)
    first = JsonFileRepository(path)
    second = JsonFileRepository(path)

    transcript = Transcript(
        transcript_id="tr_concurrent",
        session_id="session_demo_001",
        case_id="case_demo_001",
        source="manual",
        raw_text="synthetic",
    )

    def mutate_job_and_session() -> None:
        first.create_processing_job(
            _job("job_concurrent"),
            audit_action="test.concurrent.job",
            audit_message="Synthetic concurrent job.",
        )
        first.update_session(
            "session_demo_001",
            TherapySessionUpdate(notes="updated concurrently"),
            expected_version=None,
            actor_id="system",
        )

    def mutate_transcript_and_audit() -> None:
        second.create_transcript(
            transcript,
            session_status=ReviewStatus.needs_review,
            actor_id="system",
            audit_action="test.concurrent.transcript",
            audit_message="Synthetic concurrent transcript.",
        )
        second.add_audit(
            "test.concurrent.audit",
            "session_demo_001",
            "Synthetic concurrent audit.",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda fn: fn(), (mutate_job_and_session, mutate_transcript_and_audit)))

    durable = JsonFileRepository(path)
    assert "job_concurrent" in durable.jobs
    assert "tr_concurrent" in durable.transcripts
    assert durable.sessions["session_demo_001"].notes == "updated concurrently"
    assert durable.sessions["session_demo_001"].transcript_id == "tr_concurrent"
    assert {event["action"] for event in durable.audit_log} >= {
        "test.concurrent.job",
        "session.patch",
        "test.concurrent.transcript",
        "test.concurrent.audit",
    }


def test_direct_save_rejects_same_field_stale_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "repository.json"
    current = JsonFileRepository(path)
    stale = JsonFileRepository(path)

    current.update_session(
        "session_demo_001",
        TherapySessionUpdate(notes="newer"),
        expected_version=1,
        actor_id="system",
    )
    stale.sessions["session_demo_001"].notes = "stale"

    with pytest.raises(RuntimeError, match="concurrent JSON repository change"):
        stale.save()

    durable = JsonFileRepository(path)
    assert durable.sessions["session_demo_001"].notes == "newer"
    assert durable.sessions["session_demo_001"].version == 2


def test_direct_save_merges_disjoint_changes_without_data_loss(
    tmp_path: Path,
) -> None:
    path = tmp_path / "repository.json"
    first = JsonFileRepository(path)
    stale = JsonFileRepository(path)

    first.update_session(
        "session_demo_001",
        TherapySessionUpdate(notes="newer"),
        expected_version=1,
        actor_id="system",
    )
    stale.organization_settings["pilot_org_001"]["test_flag"] = True
    stale.save()

    durable = JsonFileRepository(path)
    assert durable.sessions["session_demo_001"].notes == "newer"
    assert durable.organization_settings["pilot_org_001"]["test_flag"] is True


def _persist_pending_audio(repo: JsonFileRepository) -> AudioFileMetadata:
    session = repo.sessions["session_demo_001"]
    audio = AudioFileMetadata(
        audio_file_id="aud_concurrent",
        organization_id=session.organization_id,
        session_id=session.session_id,
        case_id=session.case_id,
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=12,
        storage_mode="local_private",
        object_key="audio/synthetic.wav",
    )
    repo.audio_files[audio.audio_file_id] = audio
    repo.add_audit(
        "test.audio.create",
        audio.audio_file_id,
        "Synthetic pending audio created.",
    )
    return audio


def test_audio_upload_status_transition_rejects_stale_status(
    tmp_path: Path,
) -> None:
    path = tmp_path / "repository.json"
    creator = JsonFileRepository(path)
    audio = _persist_pending_audio(creator)
    first = JsonFileRepository(path)
    stale = JsonFileRepository(path)

    assert callable(
        getattr(stale, "mark_audio_upload_persisted", None)
    ), "repository must expose a typed upload persistence transition"
    first.mark_audio_upload_persisted(
        audio.audio_file_id,
        expected_upload_status="pending",
        expected_source_asset_version=1,
        actor_id="system",
    )

    with pytest.raises(ValueError, match="no longer writable"):
        stale.mark_audio_upload_persisted(
            audio.audio_file_id,
            expected_upload_status="pending",
            expected_source_asset_version=1,
            actor_id="system",
        )

    durable = JsonFileRepository(path)
    assert durable.audio_files[audio.audio_file_id].upload_status == (
        "pending_verification"
    )


def test_audio_upload_status_transition_rechecks_consent_under_lock(
    tmp_path: Path,
) -> None:
    path = tmp_path / "repository.json"
    creator = JsonFileRepository(path)
    audio = _persist_pending_audio(creator)
    consent_writer = JsonFileRepository(path)
    stale_upload = JsonFileRepository(path)

    withdraw_consent(
        consent_writer,
        audio.case_id,
        "Synthetic guardian withdrawal.",
    )

    assert callable(
        getattr(stale_upload, "mark_audio_upload_persisted", None)
    ), "repository must expose a typed upload persistence transition"
    with pytest.raises(ValueError, match="consent has been withdrawn"):
        stale_upload.mark_audio_upload_persisted(
            audio.audio_file_id,
            expected_upload_status="pending",
            expected_source_asset_version=1,
            actor_id="system",
        )

    durable = JsonFileRepository(path)
    assert durable.cases[audio.case_id].consent_status == "withdrawn"
    assert durable.audio_files[audio.audio_file_id].upload_status == (
        "withdrawn"
    )


def test_upload_route_serializes_with_consent_withdrawal_and_removes_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "repository.json"
    route_repo = JsonFileRepository(path)
    audio = _persist_pending_audio(route_repo)
    consent_writer = JsonFileRepository(path)
    staged = Event()
    allow_upload_finalize = Event()
    captured_receipts = []

    class ConsentWithdrawalDuringPersist(LocalPrivateStorageAdapter):
        def _pause_for_withdrawal(self) -> None:
            staged.set()
            assert allow_upload_finalize.wait(timeout=5)

        def persist_source_upload(self, audio_file, source, *, max_size_bytes):
            # Legacy behavior writes the final key only after withdrawal.
            self._pause_for_withdrawal()
            return super().persist_source_upload(
                audio_file,
                source,
                max_size_bytes=max_size_bytes,
            )

        def stage_source_upload(
            self,
            receipt,
            source,
            *,
            max_size_bytes,
            reserve,
        ):
            staged_bytes = super().stage_source_upload(
                receipt,
                source,
                max_size_bytes=max_size_bytes,
                reserve=reserve,
            )
            captured_receipts.append(receipt)
            self._pause_for_withdrawal()
            return staged_bytes

    storage = ConsentWithdrawalDuringPersist(tmp_path / "private")
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        lambda: storage,
    )
    app.dependency_overrides[get_repository] = lambda: route_repo
    app.dependency_overrides[get_storage_adapter] = lambda: storage
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            response_future = executor.submit(
                TestClient(app).put,
                f"/api/v1/audio/{audio.audio_file_id}/upload-file",
                content=b"synthetic-audio",
            )
            assert staged.wait(timeout=5)
            withdrawal_future = executor.submit(
                withdraw_consent,
                consent_writer,
                audio.case_id,
                "Synthetic concurrent withdrawal.",
            )
            allow_upload_finalize.set()
            response = response_future.result(timeout=5)
            withdrawal_future.result(timeout=5)
    finally:
        app.dependency_overrides.pop(get_repository, None)
        app.dependency_overrides.pop(get_storage_adapter, None)

    assert response.status_code == 200
    durable = JsonFileRepository(path)
    assert durable.audio_files[audio.audio_file_id].upload_status == "withdrawn"
    assert durable.cases[audio.case_id].consent_status == "withdrawn"
    assert durable.audio_files[audio.audio_file_id].retained is False
    assert durable.audio_files[audio.audio_file_id].object_key is None
    assert captured_receipts
    receipt = captured_receipts[0]
    assert not (
        storage.root / receipt.staging_object_key
    ).exists()
    assert not (
        storage.root / receipt.intended_final_object_key
    ).exists()


def test_failed_withdrawal_cleanup_is_durable_private_and_recoverable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.consent_service import (
        recover_audio_upload_cleanup,
    )

    path = tmp_path / "repository.json"
    repo = JsonFileRepository(path)
    audio = _persist_pending_audio(repo)
    storage_root = tmp_path / "private"
    repo.audio_files[
        audio.audio_file_id
    ].storage_backend_identity_sha256 = (
        LocalPrivateStorageAdapter(
            storage_root
        ).storage_backend_identity_sha256
    )
    repo.save()
    object_path = storage_root / str(audio.object_key)
    object_path.parent.mkdir(parents=True)
    object_path.write_bytes(b"synthetic-private-audio")

    class CleanupUnavailable(LocalPrivateStorageAdapter):
        def delete_object(self, object_key):
            return StorageDeletionResult(
                storage_mode=self.storage_mode,
                deleted=False,
                status="storage_cleanup_failed",
            )

    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        lambda: CleanupUnavailable(storage_root),
    )
    withdraw_consent(
        repo,
        audio.case_id,
        "Synthetic cleanup failure.",
    )

    durable = JsonFileRepository(path)
    withdrawn = durable.audio_files[audio.audio_file_id]
    assert withdrawn.object_key is None
    assert withdrawn.retained is False
    assert withdrawn.upload_cleanup_remediation is not None
    assert withdrawn.upload_cleanup_remediation.state == "failed"
    assert object_path.exists()
    public = withdrawn.model_dump(mode="json")
    assert "active_upload_receipt" not in public
    assert "upload_cleanup_remediation" not in public

    assert recover_audio_upload_cleanup(
        durable,
        audio.audio_file_id,
        storage_adapter=LocalPrivateStorageAdapter(storage_root),
        actor_id="privacy-recovery",
    )
    recovered = JsonFileRepository(path).audio_files[audio.audio_file_id]
    assert recovered.upload_cleanup_remediation is None
    assert recovered.storage_delete_status == "deleted"
    assert not object_path.exists()


@pytest.mark.parametrize("repository_mode", ["json", "sqlite"])
def test_receipt_promotion_then_withdrawal_has_repository_parity_and_no_leakage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    repository_mode: str,
) -> None:
    if repository_mode == "json":
        repository_target = tmp_path / "repository.json"
        repo = JsonFileRepository(repository_target)
        reopen = lambda: JsonFileRepository(repository_target)
    else:
        pytest.importorskip("sqlalchemy")
        from app.repositories.sqlalchemy_repository import (
            SqlAlchemyRepository,
        )

        repository_target = f"sqlite:///{tmp_path / 'repository.db'}"
        repo = SqlAlchemyRepository(repository_target)
        reopen = lambda: SqlAlchemyRepository(repository_target)

    audio = _persist_pending_audio(repo)
    storage = LocalPrivateStorageAdapter(tmp_path / "private")
    source_bytes = b"receipt-owned-private-audio"
    receipt = storage.build_source_upload_receipt(
        audio,
        expected_consent_version=repo.cases[audio.case_id].version,
        checksum_sha256=sha256(source_bytes).hexdigest(),
        size_bytes=len(source_bytes),
    )
    storage.stage_source_upload(
        receipt,
        BytesIO(source_bytes),
        max_size_bytes=1024,
        reserve=lambda: repo.reserve_audio_upload_attempt(
            receipt,
            actor_id="therapist",
        ),
    )
    with storage.upload_attempt_fence(audio.audio_file_id):
        repo.finalize_audio_upload_attempt(
            receipt,
            promote=lambda: storage.promote_source_upload(receipt),
            actor_id="therapist",
        )

    promoted_repo = reopen()
    promoted = promoted_repo.audio_files[audio.audio_file_id]
    assert promoted.upload_status == "pending_verification"
    assert promoted.object_key == receipt.intended_final_object_key
    assert promoted.active_upload_receipt is None
    assert (
        tmp_path
        / "private"
        / receipt.intended_final_object_key
    ).read_bytes() == source_bytes
    public_payload = promoted.model_dump(mode="json")
    assert "active_upload_receipt" not in public_payload
    assert "upload_cleanup_remediation" not in public_payload
    audit_payload = json.dumps(
        promoted_repo.audit_log,
        sort_keys=True,
    )
    assert receipt.nonce not in audit_payload
    assert receipt.staging_object_key not in audit_payload
    assert receipt.intended_final_object_key not in audit_payload

    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        lambda: storage,
    )
    withdraw_consent(
        promoted_repo,
        audio.case_id,
        "Synthetic promotion-before-withdrawal.",
    )
    withdrawn = reopen().audio_files[audio.audio_file_id]
    assert withdrawn.upload_status == "withdrawn"
    assert withdrawn.object_key is None
    assert withdrawn.upload_cleanup_remediation is None
    assert not (
        tmp_path
        / "private"
        / receipt.intended_final_object_key
    ).exists()


def test_stale_receipt_cleanup_cannot_delete_newer_attempt(
    tmp_path: Path,
) -> None:
    repo = JsonFileRepository(tmp_path / "repository.json")
    audio = _persist_pending_audio(repo)
    storage = LocalPrivateStorageAdapter(tmp_path / "private")

    def stage(payload: bytes):
        receipt = storage.build_source_upload_receipt(
            repo.audio_files[audio.audio_file_id],
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
                actor_id="therapist",
            ),
        )
        return receipt

    stale = stage(b"stale-attempt")
    assert storage.cleanup_upload_attempt(stale).succeeded
    repo.record_audio_upload_cleanup(
        stale,
        remediation=None,
        actor_id="therapist",
    )
    current = stage(b"current-attempt")

    assert storage.cleanup_upload_attempt(stale).succeeded
    assert (
        storage.root / current.staging_object_key
    ).read_bytes() == b"current-attempt"
    durable = JsonFileRepository(repo.path)
    assert (
        durable.audio_files[audio.audio_file_id].active_upload_receipt
        == current
    )


def test_reservation_cas_rejection_cleans_exact_attempt_keys(
    tmp_path: Path,
) -> None:
    repo = JsonFileRepository(tmp_path / "repository.json")
    audio = _persist_pending_audio(repo)
    captured = []

    class VersionChangesBeforeReserve(LocalPrivateStorageAdapter):
        def stage_source_upload(
            self,
            receipt,
            source,
            *,
            max_size_bytes,
            reserve,
        ):
            captured.append(receipt)
            repo.update_case(
                audio.case_id,
                ChildCaseUpdate(notes="Synthetic concurrent edit."),
                expected_version=1,
                actor_id="therapist",
            )
            return super().stage_source_upload(
                receipt,
                source,
                max_size_bytes=max_size_bytes,
                reserve=reserve,
            )

    storage = VersionChangesBeforeReserve(tmp_path / "private")
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_storage_adapter] = lambda: storage
    try:
        response = TestClient(app).put(
            f"/api/v1/audio/{audio.audio_file_id}/upload-file",
            content=b"cas-rejected-audio",
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)
        app.dependency_overrides.pop(get_storage_adapter, None)

    assert response.status_code == 400
    assert "no longer writable" in response.json()["detail"]
    assert captured
    receipt = captured[0]
    assert not (storage.root / receipt.staging_object_key).exists()
    assert not (
        storage.root / receipt.intended_final_object_key
    ).exists()
    durable = JsonFileRepository(repo.path).audio_files[
        audio.audio_file_id
    ]
    assert durable.upload_status == "pending"
    assert durable.active_upload_receipt is None


def test_post_promotion_failure_records_private_cleanup_and_recovers_after_restart(
    tmp_path: Path,
) -> None:
    from app.services.consent_service import (
        recover_audio_upload_cleanup,
    )

    repo = JsonFileRepository(tmp_path / "repository.json")
    audio = _persist_pending_audio(repo)

    class CleanupInitiallyUnavailable(LocalPrivateStorageAdapter):
        def cleanup_upload_attempt(self, receipt):
            raise RuntimeError("synthetic cleanup outage")

    storage = CleanupInitiallyUnavailable(tmp_path / "private")

    def fail_after_promotion(receipt, *, promote, actor_id):
        del receipt, actor_id
        promote()
        raise RuntimeError("synthetic repository commit failure")

    repo.finalize_audio_upload_attempt = fail_after_promotion
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_storage_adapter] = lambda: storage
    try:
        response = TestClient(
            app,
            raise_server_exceptions=False,
        ).put(
            f"/api/v1/audio/{audio.audio_file_id}/upload-file",
            content=b"promoted-before-failed-commit",
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)
        app.dependency_overrides.pop(get_storage_adapter, None)

    assert response.status_code == 500
    durable = JsonFileRepository(repo.path)
    pending = durable.audio_files[audio.audio_file_id]
    assert pending.upload_status == "pending"
    assert pending.active_upload_receipt is not None
    assert pending.upload_cleanup_remediation is not None
    assert pending.upload_cleanup_remediation.state == "failed"
    receipt = pending.active_upload_receipt
    assert (
        storage.root / receipt.intended_final_object_key
    ).exists()
    assert recover_audio_upload_cleanup(
        durable,
        audio.audio_file_id,
        storage_adapter=LocalPrivateStorageAdapter(storage.root),
        actor_id="privacy-recovery",
    )
    recovered = JsonFileRepository(repo.path).audio_files[
        audio.audio_file_id
    ]
    assert recovered.upload_status == "pending"
    assert recovered.active_upload_receipt is None
    assert recovered.upload_cleanup_remediation is None
    assert not (
        storage.root / receipt.intended_final_object_key
    ).exists()


def test_post_promotion_repository_failure_cleans_exact_attempt_immediately(
    tmp_path: Path,
) -> None:
    repo = JsonFileRepository(tmp_path / "repository.json")
    audio = _persist_pending_audio(repo)
    storage = LocalPrivateStorageAdapter(tmp_path / "private")

    def fail_after_promotion(receipt, *, promote, actor_id):
        del receipt, actor_id
        promote()
        raise RuntimeError("synthetic repository commit failure")

    repo.finalize_audio_upload_attempt = fail_after_promotion
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_storage_adapter] = lambda: storage
    try:
        response = TestClient(
            app,
            raise_server_exceptions=False,
        ).put(
            f"/api/v1/audio/{audio.audio_file_id}/upload-file",
            content=b"cleanup-after-failed-commit",
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)
        app.dependency_overrides.pop(get_storage_adapter, None)

    assert response.status_code == 500
    durable = JsonFileRepository(repo.path).audio_files[
        audio.audio_file_id
    ]
    assert durable.upload_status == "pending"
    assert durable.active_upload_receipt is None
    assert durable.upload_cleanup_remediation is None
    assert not list((tmp_path / "private").rglob("*.stage"))
    assert not list((tmp_path / "private" / "audio").glob("*attempt-*"))


def test_json_post_commit_response_failure_preserves_committed_upload(
    tmp_path: Path,
) -> None:
    repo = JsonFileRepository(tmp_path / "repository.json")
    audio = _persist_pending_audio(repo)
    storage = LocalPrivateStorageAdapter(tmp_path / "private")
    original_finalize = repo.finalize_audio_upload_attempt

    def commit_then_fail(receipt, *, promote, actor_id):
        original_finalize(
            receipt,
            promote=promote,
            actor_id=actor_id,
        )
        raise RuntimeError("synthetic post-commit response failure")

    repo.finalize_audio_upload_attempt = commit_then_fail
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_storage_adapter] = lambda: storage
    try:
        response = TestClient(
            app,
            raise_server_exceptions=False,
        ).put(
            f"/api/v1/audio/{audio.audio_file_id}/upload-file",
            content=b"json-committed-audio",
        )
    finally:
        app.dependency_overrides.pop(get_repository, None)
        app.dependency_overrides.pop(get_storage_adapter, None)

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Upload state could not be returned safely. "
        "Retry the upload status request."
    )
    reopened = JsonFileRepository(repo.path)
    durable = reopened.audio_files[audio.audio_file_id]
    assert durable.upload_status == "pending_verification"
    assert durable.object_key is not None
    assert (storage.root / durable.object_key).read_bytes() == (
        b"json-committed-audio"
    )
    audit_payload = json.dumps(reopened.audit_log, sort_keys=True)
    assert "audio.upload_response_retry_required" in audit_payload
    assert durable.object_key not in audit_payload
    assert ".upload-attempts/" not in audit_payload


def test_restart_recovery_never_deletes_committed_referenced_final(
    tmp_path: Path,
) -> None:
    from app.services.consent_service import (
        recover_audio_upload_cleanup,
    )

    repo = JsonFileRepository(tmp_path / "repository.json")
    audio = _persist_pending_audio(repo)
    storage = LocalPrivateStorageAdapter(tmp_path / "private")
    payload = b"durably-committed-audio"
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
            actor_id="therapist",
        ),
    )
    with storage.upload_attempt_fence(audio.audio_file_id):
        repo.finalize_audio_upload_attempt(
            receipt,
            promote=lambda: storage.promote_source_upload(receipt),
            actor_id="therapist",
        )
    repo.audio_files[
        audio.audio_file_id
    ].upload_cleanup_remediation = AudioUploadCleanupRemediation(
        state="pending",
        receipt=receipt,
    )
    repo.add_audit(
        "test.synthetic_stale_cleanup",
        audio.audio_file_id,
        "Synthetic stale cleanup marker persisted.",
    )

    restarted = JsonFileRepository(repo.path)
    assert recover_audio_upload_cleanup(
        restarted,
        audio.audio_file_id,
        storage_adapter=storage,
        actor_id="privacy-recovery",
    )
    durable = JsonFileRepository(repo.path).audio_files[
        audio.audio_file_id
    ]
    assert durable.upload_status == "pending_verification"
    assert durable.object_key == receipt.intended_final_object_key
    assert durable.upload_cleanup_remediation is None
    assert (
        storage.root / receipt.intended_final_object_key
    ).read_bytes() == payload


def test_expired_invitation_denial_commits_once_before_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "repository.json"
    repo = JsonFileRepository(path)
    invitation = repo.create_invitation(
        "pilot_org_001",
        OrganizationInvitationCreate(
            email="expired@example.test",
            display_name="Expired",
            role="therapist",
        ),
        actor_id="admin",
    )
    repo.invitations[invitation.invitation_id].expires_at = (
        utc_now() - timedelta(minutes=1)
    )
    repo.save()

    with pytest.raises(
        ValueError,
        match="Expired invitations require a newly issued invitation.",
    ):
        repo.accept_invitation(
            "pilot_org_001",
            invitation.invitation_id,
            OrganizationInvitationAccept(user_id="clinician"),
            actor_id="admin",
        )

    durable = JsonFileRepository(path)
    denial_events = [
        event
        for event in durable.audit_log
        if event["action"] == "invitation.accept"
        and event["target_id"] == invitation.invitation_id
        and event["outcome"] == "denied"
    ]
    assert durable.invitations[invitation.invitation_id].status == "expired"
    assert repo.snapshot() == durable.snapshot()
    assert len(denial_events) == 1

    repo.add_audit(
        "test.unrelated",
        "session_demo_001",
        "Unrelated later mutation.",
    )
    after_unrelated = JsonFileRepository(path)
    later_denials = [
        event
        for event in after_unrelated.audit_log
        if event["action"] == "invitation.accept"
        and event["target_id"] == invitation.invitation_id
        and event["outcome"] == "denied"
    ]
    assert len(later_denials) == 1
    assert after_unrelated.invitations[invitation.invitation_id].status == (
        "expired"
    )


def test_failed_json_transaction_restores_live_durable_state(
    tmp_path: Path,
) -> None:
    path = tmp_path / "repository.json"
    repo = JsonFileRepository(path)
    durable_before = JsonFileRepository(path).snapshot()

    with pytest.raises(RuntimeError, match="synthetic failure"):
        with repo._json_mutation_transaction():
            repo.sessions["session_demo_001"].notes = "must roll back"
            repo._json_transaction_dirty = True
            raise RuntimeError("synthetic failure")

    assert repo.snapshot() == durable_before
    repo.add_audit(
        "test.after_rollback",
        "session_demo_001",
        "Mutation after rollback.",
    )
    durable_after = JsonFileRepository(path)
    assert durable_after.sessions["session_demo_001"].notes == (
        durable_before["sessions"]["session_demo_001"]["notes"]
    )
    assert sum(
        event["action"] == "test.after_rollback"
        for event in durable_after.audit_log
    ) == 1
