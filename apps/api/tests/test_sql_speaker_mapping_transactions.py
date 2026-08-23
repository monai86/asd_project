from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
from threading import Barrier, Event, Lock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.core.config import get_settings
from app.main import app
from app.repositories.base import SpeakerMappingVersionConflictError, TranscriptVersionConflictError
from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
from app.schemas.clinical import (
    AiReview,
    ChildCaseCreate,
    ChildCaseUpdate,
    FeatureSet,
    FeatureValue,
    MLResult,
    Report,
    ReviewStatus,
    TherapySessionCreate,
    TherapySessionUpdate,
    Transcript,
    TranscriptionJobRequest,
    Utterance,
    utc_now,
    AudioProcessRequest,
    AudioFileMetadata,
    AudioUploadCompleteRequest,
    AudioUploadRequest,
    JobStatus,
    ProcessingJob,
    PrivacyOperation,
    PrivacyOperationPatch,
)
from app.schemas.speaker_mapping import (
    MappingEffectiveStatus,
    MappingPersistedStatus,
    SpeakerMapping,
    SpeakerMappingConfirmRequest,
    SpeakerMappingDraftUpdate,
)
from app.services.speaker_mapping_service import (
    SpeakerMappingError,
    build_confirmed_transcript,
    confirm_mapping,
    get_mapping,
    require_confirmed_mapping,
    save_mapping_draft,
)
from app.services.audio_job_service import (
    complete_audio_upload,
    create_audio_upload_job,
    create_audio_processing_job,
    run_audio_processing_job,
)
from app.services.consent_service import withdraw_consent


@pytest.fixture
def sql_repo(tmp_path, monkeypatch) -> SqlAlchemyRepository:
    pytest.importorskip("sqlalchemy")
    monkeypatch.setenv("LINGUALENS_STORAGE_MODE", "local_private")
    monkeypatch.setenv("LINGUALENS_LOCAL_STORAGE_ROOT", str(tmp_path / "private-audio"))
    get_settings.cache_clear()
    yield SqlAlchemyRepository(f"sqlite:///{tmp_path / 'speaker-mapping.db'}")
    get_settings.cache_clear()


def materialize_local_audio(audio: AudioFileMetadata) -> str:
    path = get_settings().resolved_local_storage_root / audio.object_key
    path.parent.mkdir(parents=True, exist_ok=True)
    content = b"RIFFxxxxWAVE"
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def seed_temporary_asr_transcript(
    repo: SqlAlchemyRepository,
    *,
    transcript_id: str = "tr-spmap-sql",
    session_date: str = "2026-08-23",
) -> Transcript:
    case = repo.create_case(
        ChildCaseCreate(child_code=f"CASE-{transcript_id}", age_months=60, consent_status="granted"),
        actor_id="therapist-demo",
    )
    session = repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date=session_date, session_type="language_sample"),
        actor_id="therapist-demo",
    )
    transcript = Transcript(
        transcript_id=transcript_id,
        session_id=session.session_id,
        case_id=case.case_id,
        organization_id=case.organization_id,
        source="asr_draft:manual",
        raw_text="",
        utterances=[
            Utterance(
                utterance_id="utt-0",
                speaker="UNK",
                text="Synthetic zero",
                temporary_speaker_id="speaker-0",
                source_speaker_label="provider zero",
            ),
            Utterance(
                utterance_id="utt-1",
                speaker="UNK",
                text="Synthetic one",
                temporary_speaker_id="speaker-1",
                source_speaker_label="provider one",
            ),
        ],
        review_status=ReviewStatus.needs_review,
    )
    return repo.create_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="system",
        audit_action="transcript.create",
        audit_message="Synthetic SQL transcript created.",
    )


def test_sql_transcript_provenance_round_trips_losslessly(sql_repo) -> None:
    case = sql_repo.create_case(
        ChildCaseCreate(child_code="CASE-PROVENANCE", age_months=60, consent_status="granted"),
        actor_id="therapist-demo",
    )
    session = sql_repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-08-24", session_type="language_sample"),
        actor_id="therapist-demo",
    )
    imported_at = utc_now().replace(microsecond=123456)
    transcript = Transcript(
        transcript_id="tr-provenance-sql",
        session_id=session.session_id,
        case_id=case.case_id,
        organization_id=case.organization_id,
        source="imported_chat",
        raw_text="@Begin\n*CHI:\tsynthetic .\n@End",
        utterances=[Utterance(utterance_id="utt-provenance", speaker="CHI", text="synthetic")],
        chat_metadata={"languages": ["eng"], "participants": {"CHI": "Target_Child"}},
        orphan_dependent_tiers=[
            {
                "tier": "%mor",
                "raw_text": "%mor:\tn|synthetic",
                "line_number": 3,
                "parser_action": "preserved_unattached",
            }
        ],
        malformed_lines=[{"line_number": 4, "raw_text": "synthetic malformed"}],
        parser_version="chat-parser-synthetic-v9",
        import_timestamp=imported_at,
    )

    saved = sql_repo.create_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="system",
        audit_action="transcript.create",
        audit_message="Synthetic provenance transcript created.",
    )
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    restored = reopened.get_transcript(saved.transcript_id)

    assert restored is not None
    assert restored.model_dump(mode="json") == saved.model_dump(mode="json")


def test_stale_sql_worker_cannot_create_session_after_consent_withdrawal(sql_repo) -> None:
    case = sql_repo.create_case(
        ChildCaseCreate(child_code="CASE-SESSION-WITHDRAW", age_months=60, consent_status="granted"),
        actor_id="therapist-demo",
    )
    stale = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    withdraw_consent(sql_repo, case.case_id, "Synthetic withdrawal")
    before_audits = len(SqlAlchemyRepository(sql_repo.database_url, create_schema=False).audit_log)

    with pytest.raises(ValueError, match="consent"):
        stale.create_session(
            case.case_id,
            TherapySessionCreate(session_date="2026-08-24", session_type="language_sample"),
            actor_id="therapist-demo",
        )

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert not any(item.case_id == case.case_id for item in reopened.sessions.values())
    assert len(reopened.audit_log) == before_audits


def test_public_gates_ignore_stale_mirror_published_after_withdrawal(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-publish-race")
    case = sql_repo.get_case(transcript.case_id)
    repo_a = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    repo_b = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    committed = Event()
    release = Event()

    class PausingCaseMirror(dict):
        def __setitem__(self, key, value):
            if key == case.case_id:
                committed.set()
                assert release.wait(timeout=10)
            return super().__setitem__(key, value)

    repo_a.cases = PausingCaseMirror(repo_a.cases)
    with ThreadPoolExecutor(max_workers=1) as executor:
        stale_publication = executor.submit(
            repo_a.update_case,
            case.case_id,
            ChildCaseUpdate(notes="Synthetic stale publication."),
            expected_version=case.version,
            actor_id="therapist-demo",
        )
        assert committed.wait(timeout=10)
        withdraw_consent(repo_b, case.case_id, "Synthetic race withdrawal")
        release.set()
        stale_publication.result(timeout=10)

    assert repo_a.cases[case.case_id].consent_status == "granted"
    app.dependency_overrides[get_repository] = lambda: repo_a
    try:
        test_client = TestClient(app)
        assert test_client.get(f"/api/v1/sessions/{transcript.session_id}").status_code == 400
        assert test_client.get(f"/api/v1/transcripts/{transcript.transcript_id}").status_code == 400
        assert test_client.post(
            f"/api/v1/cases/{case.case_id}/sessions",
            json={"session_date": "2026-08-24", "session_type": "language_sample"},
        ).status_code == 400
        assert test_client.post(
            f"/api/v1/sessions/{transcript.session_id}/audio/process",
            json={"provider": "mock", "draft_text": "CHI: synthetic"},
        ).status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_sql_privacy_operation_can_complete_after_withdrawal(sql_repo) -> None:
    from app.services.privacy_operation_service import patch_privacy_operation

    case = sql_repo.create_case(
        ChildCaseCreate(child_code="CASE-PRIVACY-WITHDRAW", age_months=60),
        actor_id="therapist-demo",
    )
    operation = sql_repo.create_privacy_operation(
        PrivacyOperation(
            privacy_operation_id="privacy-sql-after-withdrawal",
            case_id=case.case_id,
            operation_type="deletion_review",
            requested_by="org-admin",
            requester_role="org_admin",
            reason="Synthetic deletion administration.",
        ),
        actor_id="org-admin",
        audit_action="privacy_operation.create",
        audit_message="Synthetic privacy operation created.",
    )
    withdraw_consent(sql_repo, case.case_id, "Synthetic withdrawal")
    completed = patch_privacy_operation(
        SqlAlchemyRepository(sql_repo.database_url, create_schema=False),
        operation.privacy_operation_id,
        PrivacyOperationPatch(status="completed"),
    )
    assert completed.status == "completed"
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.get_privacy_operation(operation.privacy_operation_id).status == "completed"


@pytest.mark.parametrize("restart_status", [JobStatus.processing, JobStatus.transcription_completed])
def test_sql_audio_job_resumes_nonterminal_stage_after_restart(sql_repo, restart_status) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id=f"tr-resume-{restart_status.value}")
    job = create_audio_processing_job(
        sql_repo,
        transcript.session_id,
        AudioProcessRequest(provider="mock", draft_text="CHI: resumed synthetic\nTHER: resumed reply"),
    )
    processing = sql_repo.update_processing_job(
        job.model_copy(
            update={
                "status": JobStatus.processing,
                "details": {**job.details, "status_history": ["queued", "processing"]},
            }
        ),
        actor_id="system",
        expected_version=job.version,
        expected_status="queued",
        audit_action="audio.process_started",
        audit_message="Synthetic processing stage persisted.",
    )
    if restart_status == JobStatus.transcription_completed:
        processing = sql_repo.update_processing_job(
            processing.model_copy(
                update={
                    "status": JobStatus.transcription_completed,
                    "details": {
                        **processing.details,
                        "provider_result": {
                            "status": "completed",
                            "provider_id": "mock",
                            "provider_name": "Mock ASR Provider",
                            "provider_version": "1.0",
                            "transcript_lines": [
                                {"line_id": "resume-0", "speaker": "CHI", "text": "resumed synthetic"},
                                {"line_id": "resume-1", "speaker": "THER", "text": "resumed reply"},
                            ],
                            "language": "en",
                            "speaker_segments_available": True,
                            "computed_at": utc_now().isoformat(),
                        },
                        "quality": {
                            "status": "passed",
                            "warnings": [],
                            "duration_seconds": 30.0,
                            "sample_rate_hz": 16000,
                            "channels": 1,
                        },
                        "status_history": ["queued", "processing", "transcription_completed"],
                    },
                }
            ),
            actor_id="system",
            expected_version=processing.version,
            expected_status="processing",
            audit_action="audio.transcription_completed",
            audit_message="Synthetic provider result persisted.",
        )

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    completed = run_audio_processing_job(reopened, job.job_id)
    after_restart = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)

    assert completed.status == JobStatus.needs_review
    assert after_restart.jobs[job.job_id].status == JobStatus.needs_review
    assert after_restart.sessions[transcript.session_id].transcript_id != transcript.transcript_id
    assert after_restart.jobs[job.job_id].details["status_history"].count("needs_review") == 1


def test_simultaneous_sql_workers_invoke_asr_provider_once(sql_repo, monkeypatch) -> None:
    from app.services.asr_providers.registry import asr_provider_registry

    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-provider-lease")
    queued = create_audio_processing_job(
        sql_repo,
        transcript.session_id,
        AudioProcessRequest(provider="mock", draft_text="CHI: synthetic\nTHER: synthetic"),
    )
    processing = sql_repo.update_processing_job(
        queued.model_copy(update={"status": JobStatus.processing}),
        actor_id="system",
        expected_version=queued.version,
        expected_status=JobStatus.queued.value,
        audit_action="audio.process_started",
        audit_message="Synthetic processing stage entered.",
    )
    first = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    second = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    provider = asr_provider_registry.get("mock")
    original_transcribe = provider.transcribe
    entered = Event()
    release = Event()
    count_lock = Lock()
    provider_calls = 0

    def blocked_transcribe(*args, **kwargs):
        nonlocal provider_calls
        with count_lock:
            provider_calls += 1
        entered.set()
        assert release.wait(timeout=10)
        return original_transcribe(*args, **kwargs)

    monkeypatch.setattr(provider, "transcribe", blocked_transcribe)
    with ThreadPoolExecutor(max_workers=2) as executor:
        winner = executor.submit(run_audio_processing_job, first, processing.job_id)
        assert entered.wait(timeout=10)
        observer = executor.submit(run_audio_processing_job, second, processing.job_id)
        observed = observer.result(timeout=10)
        release.set()
        completed = winner.result(timeout=10)

    assert provider_calls == 1
    assert observed.status == JobStatus.processing
    assert completed.status == JobStatus.needs_review
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.get_processing_job(processing.job_id).status == JobStatus.needs_review


@pytest.mark.parametrize("durable", [False, True])
def test_provider_request_id_survives_lease_reclaim(tmp_path, durable) -> None:
    from datetime import timedelta
    from app.repositories.mock_repository import JsonFileRepository, MockRepository

    repo = JsonFileRepository(tmp_path / "lease.json") if durable else MockRepository()
    queued = create_audio_processing_job(
        repo, "session_demo_001", AudioProcessRequest(provider="mock", draft_text="CHI: synthetic")
    )
    processing = repo.update_processing_job(
        queued.model_copy(update={"status": JobStatus.processing}), actor_id="system",
        expected_version=queued.version, expected_status="queued", audit_action="audio.process_started",
        audit_message="Synthetic start.",
    )
    first = repo.claim_processing_job(processing.job_id, actor_id="worker-a", lease_seconds=1)
    first_key = first.details["provider_request_id"]
    expired = first.model_copy(deep=True)
    expired.details["provider_lease"]["expires_at"] = (utc_now() - timedelta(seconds=1)).isoformat()
    repo.jobs[processing.job_id] = expired
    if durable:
        repo.save()
        repo = JsonFileRepository(tmp_path / "lease.json")
    second = repo.claim_processing_job(processing.job_id, actor_id="worker-b", lease_seconds=30)
    assert second.details["provider_lease"]["token"] != first.details["provider_lease"]["token"]
    assert second.details["provider_request_id"] == first_key
    assert second.details["provider_lease"]["idempotency_key"] == first_key


def test_sql_provider_request_id_survives_lease_reclaim(sql_repo) -> None:
    from datetime import timedelta
    from app.db.models import ProcessingJobRecord

    queued = create_audio_processing_job(
        sql_repo, "session_demo_001", AudioProcessRequest(provider="mock", draft_text="CHI: synthetic")
    )
    processing = sql_repo.update_processing_job(
        queued.model_copy(update={"status": JobStatus.processing}), actor_id="system",
        expected_version=queued.version, expected_status="queued", audit_action="audio.process_started",
        audit_message="Synthetic start.",
    )
    first = sql_repo.claim_processing_job(processing.job_id, actor_id="worker-a", lease_seconds=1)
    with sql_repo.SessionLocal() as db:
        row = db.get(ProcessingJobRecord, processing.job_id)
        details = dict(row.details)
        details["provider_lease"] = dict(details["provider_lease"])
        details["provider_lease"]["expires_at"] = (utc_now() - timedelta(seconds=1)).isoformat()
        row.details = details
        db.commit()
    second = SqlAlchemyRepository(sql_repo.database_url, create_schema=False).claim_processing_job(
        processing.job_id, actor_id="worker-b", lease_seconds=30
    )
    assert second.details["provider_request_id"] == first.details["provider_request_id"]
    assert second.details["provider_lease"]["token"] != first.details["provider_lease"]["token"]


def test_sql_reclaim_reuses_provider_idempotency_after_crash_before_result_persistence(sql_repo, monkeypatch) -> None:
    from datetime import timedelta
    from app.db.models import ProcessingJobRecord
    from app.services.asr_providers.registry import asr_provider_registry

    queued = create_audio_processing_job(
        sql_repo, "session_demo_001", AudioProcessRequest(provider="mock", draft_text="CHI: synthetic\nTHER: synthetic")
    )
    provider = asr_provider_registry.get("mock")
    original_transcribe = provider.transcribe
    calls: list[str] = []
    external_executions: set[str] = set()

    def idempotent_transcribe(*args, **kwargs):
        key = kwargs["config"]["idempotency_key"]
        calls.append(key)
        external_executions.add(key)
        return original_transcribe(*args, **kwargs)

    original_update = sql_repo.update_processing_job
    crashed = False

    def crash_before_result(*args, **kwargs):
        nonlocal crashed
        if kwargs.get("audit_action") == "audio.transcription_completed" and not crashed:
            crashed = True
            raise RuntimeError("synthetic crash before result persistence")
        return original_update(*args, **kwargs)

    monkeypatch.setattr(provider, "transcribe", idempotent_transcribe)
    monkeypatch.setattr(sql_repo, "update_processing_job", crash_before_result)
    with pytest.raises(RuntimeError, match="synthetic crash"):
        run_audio_processing_job(sql_repo, queued.job_id)
    with sql_repo.SessionLocal() as db:
        row = db.get(ProcessingJobRecord, queued.job_id)
        details = dict(row.details)
        details["provider_lease"] = dict(details["provider_lease"])
        details["provider_lease"]["expires_at"] = (utc_now() - timedelta(seconds=1)).isoformat()
        row.details = details
        db.commit()

    completed = run_audio_processing_job(
        SqlAlchemyRepository(sql_repo.database_url, create_schema=False), queued.job_id
    )
    assert completed.status == JobStatus.needs_review
    assert len(calls) == 2
    assert calls[0] == calls[1]
    assert len(external_executions) == 1


def test_sql_reclaim_does_not_reinvoke_non_idempotent_provider_after_unknown_outcome(sql_repo, monkeypatch) -> None:
    from datetime import timedelta
    from app.db.models import ProcessingJobRecord
    from app.services.asr_providers.registry import asr_provider_registry

    delegate = asr_provider_registry.get("mock")

    class NonIdempotentProvider:
        provider_id = "non_idempotent_test"
        provider_name = "Non-idempotent synthetic provider"
        provider_version = "test-v1"
        supports_idempotent_replay = False

        def check_availability(self):
            return delegate.check_availability()

        def get_provider_metadata(self):
            return {"provider_id": self.provider_id}

        def transcribe(self, audio_ref, config=None):
            calls.append(config["idempotency_key"])
            return delegate.transcribe(audio_ref, config)

    calls: list[str] = []
    provider = NonIdempotentProvider()
    asr_provider_registry.register(provider)
    try:
        queued = create_audio_processing_job(
            sql_repo,
            "session_demo_001",
            AudioProcessRequest(provider=provider.provider_id, draft_text="CHI: synthetic\nTHER: synthetic"),
        )
        original_update = sql_repo.update_processing_job

        def crash_before_result(*args, **kwargs):
            if kwargs.get("audit_action") == "audio.transcription_completed":
                raise RuntimeError("synthetic crash after provider accepted request")
            return original_update(*args, **kwargs)

        monkeypatch.setattr(sql_repo, "update_processing_job", crash_before_result)
        with pytest.raises(RuntimeError, match="provider accepted"):
            run_audio_processing_job(sql_repo, queued.job_id)
        assert len(calls) == 1

        with sql_repo.SessionLocal() as db:
            row = db.get(ProcessingJobRecord, queued.job_id)
            details = dict(row.details)
            details["provider_lease"] = dict(details["provider_lease"])
            details["provider_lease"]["expires_at"] = (
                utc_now() - timedelta(seconds=1)
            ).isoformat()
            row.details = details
            db.commit()

        recovered = run_audio_processing_job(
            SqlAlchemyRepository(sql_repo.database_url, create_schema=False), queued.job_id
        )
        assert len(calls) == 1
        assert recovered.status == JobStatus.needs_review
        assert recovered.error_code == "provider_outcome_unknown"
        assert recovered.details["provider_outcome"] == "unknown"
    finally:
        asr_provider_registry.unregister(provider.provider_id)


@pytest.mark.parametrize("winner", ["edit", "confirm"])
def test_stale_transcript_edit_and_mapping_confirmation_cannot_both_commit(sql_repo, winner) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id=f"tr-edit-confirm-{winner}")
    draft = save_mapping_draft(sql_repo, transcript.transcript_id, complete_update(transcript))
    stale = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    confirm_request = SpeakerMappingConfirmRequest(
        expected_transcript_version=transcript.version,
        expected_mapping_version=draft.mapping_version,
    )
    edited = transcript.model_copy(
        update={"raw_text": "*CHI:\tsynthetic edited .", "version": transcript.version + 1, "updated_at": utc_now()}
    )

    if winner == "edit":
        sql_repo.update_transcript(
            edited,
            session_status=ReviewStatus.needs_review,
            expected_version=transcript.version,
            actor_id="therapist-demo",
            audit_action="transcript.patch",
            audit_message="Synthetic transcript edit.",
        )
        with pytest.raises((TranscriptVersionConflictError, SpeakerMappingError)):
            confirm_mapping(
                stale,
                transcript.transcript_id,
                confirm_request,
                actor_id="therapist-demo",
                actor_role="therapist",
            )
    else:
        confirm_mapping(
            sql_repo,
            transcript.transcript_id,
            confirm_request,
            actor_id="therapist-demo",
            actor_role="therapist",
        )
        with pytest.raises(TranscriptVersionConflictError):
            stale.update_transcript(
                edited,
                session_status=ReviewStatus.needs_review,
                expected_version=transcript.version,
                actor_id="therapist-demo",
                audit_action="transcript.patch",
                audit_message="Synthetic stale transcript edit.",
            )

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    actions = [event["action"] for event in reopened.audit_log]
    assert actions.count("speaker_mapping.confirm") + actions.count("transcript.patch") == 1


def complete_update(transcript: Transcript, *, expected_mapping_version: int | None = None) -> SpeakerMappingDraftUpdate:
    return SpeakerMappingDraftUpdate.model_validate(
        {
            "expected_transcript_version": transcript.version,
            "expected_mapping_version": expected_mapping_version,
            "entries": [
                {
                    "temporary_speaker_id": "speaker-0",
                    "confirmed_chat_code": "CHI",
                    "participant_role": "target_child",
                    "reviewed_utterance_ids": ["utt-0"],
                },
                {
                    "temporary_speaker_id": "speaker-1",
                    "confirmed_chat_code": "THER",
                    "participant_role": "therapist",
                    "reviewed_utterance_ids": ["utt-1"],
                },
            ],
        }
    )


def save_complete_mapping(repo: SqlAlchemyRepository, transcript: Transcript, *, expected_mapping_version=None):
    return save_mapping_draft(
        repo,
        transcript.transcript_id,
        complete_update(transcript, expected_mapping_version=expected_mapping_version),
        actor_id="therapist-demo",
    )


def confirm_complete_mapping(repo: SqlAlchemyRepository, transcript: Transcript, draft):
    return confirm_mapping(
        repo,
        transcript.transcript_id,
        SpeakerMappingConfirmRequest(
            expected_transcript_version=transcript.version,
            expected_mapping_version=draft.mapping_version,
        ),
        actor_id="therapist-demo",
        actor_role="therapist",
    )


def synchronize_mapping_reads(repositories, *, occurrence: int):
    """Pause workers after each has read the same mapping version from SQLite."""

    from sqlalchemy import event

    barrier = Barrier(len(repositories))
    listeners = []
    for repository in repositories:
        state = {"seen": 0}

        def after_cursor_execute(_connection, _cursor, statement, _parameters, _context, _many, *, state=state):
            normalized = statement.lower()
            if normalized.lstrip().startswith("select") and "speaker_mappings" in normalized:
                state["seen"] += 1
                if state["seen"] == occurrence:
                    barrier.wait(timeout=10)

        event.listen(repository.engine, "after_cursor_execute", after_cursor_execute)
        listeners.append((repository.engine, after_cursor_execute))

    def cleanup() -> None:
        for engine, listener in listeners:
            event.remove(engine, "after_cursor_execute", listener)

    return cleanup


def test_sql_audio_workflow_is_durable_across_each_restart(sql_repo, monkeypatch) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    session_id = transcript.session_id
    upload_job = create_audio_upload_job(
        sql_repo,
        session_id,
        AudioUploadRequest(filename="synthetic.wav", content_type="audio/wav", size_bytes=12),
    )
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert upload_job.job_id in reopened.jobs
    audio_id = upload_job.details["audio_file"]["audio_file_id"]
    assert audio_id in reopened.audio_files

    pending = reopened.audio_files[audio_id].model_copy(update={"upload_status": "pending_verification"})
    reopened.update_audio_file_metadata(
        pending,
        actor_id="system",
        expected_version=reopened.audio_files[audio_id].version,
        expected_upload_status="pending",
    )
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.audio_files[audio_id].upload_status == "pending_verification"

    checksum = materialize_local_audio(reopened.audio_files[audio_id])
    complete_audio_upload(
        reopened,
        audio_id,
        AudioUploadCompleteRequest(size_bytes=12, checksum_sha256=checksum),
    )
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.audio_files[audio_id].upload_status == "uploaded"

    job = create_audio_processing_job(
        reopened,
        session_id,
        AudioProcessRequest(provider="mock", audio_id=audio_id, draft_text="CHI: synthetic\nTHER: synthetic"),
    )
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.jobs[job.job_id].status == JobStatus.queued
    completed = run_audio_processing_job(reopened, job.job_id)
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert completed.status == JobStatus.needs_review
    assert reopened.jobs[job.job_id].status == JobStatus.needs_review
    transcript_id = completed.details["asr_draft"]["transcript_id"]
    assert reopened.sessions[session_id].transcript_id == transcript_id
    assert reopened.get_transcript(transcript_id) is not None
    assert get_mapping(reopened, transcript_id).transcript_id == transcript_id
    assert [event["organization_id"] for event in reopened.audit_log if event["target_id"] == job.job_id] == [
        reopened.sessions[session_id].organization_id,
        reopened.sessions[session_id].organization_id,
        reopened.sessions[session_id].organization_id,
        reopened.sessions[session_id].organization_id,
        reopened.sessions[session_id].organization_id,
    ]
    assert any(
        event["action"] == "audio.provider_claim" and event["target_id"] == job.job_id
        for event in reopened.audit_log
    )


def test_sql_local_upload_route_persists_pending_verification(sql_repo, tmp_path, monkeypatch) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-local-upload")
    monkeypatch.setenv("LINGUALENS_STORAGE_MODE", "local_private")
    monkeypatch.setenv("LINGUALENS_LOCAL_STORAGE_ROOT", str(tmp_path / "private-audio"))
    get_settings.cache_clear()
    try:
        upload_job = create_audio_upload_job(
            sql_repo,
            transcript.session_id,
            AudioUploadRequest(filename="synthetic.wav", content_type="audio/wav", size_bytes=12),
        )
        audio_id = upload_job.details["audio_file"]["audio_file_id"]
        app.dependency_overrides[get_repository] = lambda: sql_repo
        response = TestClient(app).put(
            f"/api/v1/audio/{audio_id}/upload-file",
            content=b"RIFFxxxxWAVE",
            headers={"x-mock-user-id": "therapist-demo", "x-mock-role": "therapist"},
        )
        assert response.status_code == 200
        reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
        assert reopened.audio_files[audio_id].upload_status == "pending_verification"
    finally:
        app.dependency_overrides.pop(get_repository, None)
        get_settings.cache_clear()


def test_sql_consent_withdrawal_is_atomic_and_durable(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    result = withdraw_consent(sql_repo, transcript.case_id, "Synthetic withdrawal")
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert result.affected_records["sessions"] == 1
    assert reopened.cases[transcript.case_id].consent_status == "withdrawn"
    assert reopened.sessions[transcript.session_id].status == ReviewStatus.withdrawn
    assert reopened.transcripts[transcript.transcript_id].raw_text == ""
    assert reopened.transcripts[transcript.transcript_id].utterances == []
    assert len([event for event in reopened.audit_log if event["action"] == "consent.withdraw"]) == 1


def test_sql_add_audit_cannot_resurrect_durably_deleted_case(sql_repo) -> None:
    from app.db.models import AuditLogRecord, ChildCaseRecord, SessionRecord, TranscriptRecord

    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-deleted-case")
    stale = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    with sql_repo.SessionLocal() as db:
        db.query(TranscriptRecord).filter_by(case_id=transcript.case_id).delete()
        db.query(SessionRecord).filter_by(case_id=transcript.case_id).delete()
        db.query(ChildCaseRecord).filter_by(case_id=transcript.case_id).delete()
        db.commit()
    before = len(stale.audit_log)
    with pytest.raises(KeyError):
        stale.add_audit("case.stale", transcript.case_id, "Synthetic stale mutation.")
    with sql_repo.SessionLocal() as db:
        assert db.get(ChildCaseRecord, transcript.case_id) is None
        assert db.query(AuditLogRecord).filter_by(action="case.stale").count() == 0
    assert len(stale.audit_log) == before


def test_sql_generic_save_fails_closed_without_mutating_established_database(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-save-closed")
    stale = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    stale.transcripts[transcript.transcript_id].raw_text = "stale"
    with pytest.raises(RuntimeError, match="not available"):
        stale.save()
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.transcripts[transcript.transcript_id].raw_text != "stale"


def test_sql_audio_failure_and_cancel_transitions_survive_restart(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-job-terminal")
    failed_job = create_audio_processing_job(
        sql_repo,
        transcript.session_id,
        AudioProcessRequest(provider="mock", duration_seconds=4000),
    )
    failed = run_audio_processing_job(sql_repo, failed_job.job_id)
    assert failed.status == JobStatus.failed
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.jobs[failed.job_id].status == JobStatus.failed

    cancelled = create_audio_processing_job(
        reopened,
        transcript.session_id,
        AudioProcessRequest(provider="mock"),
    ).model_copy(update={"status": JobStatus.cancelled, "message": "Synthetic cancellation."})
    cancelled = reopened.update_processing_job(
        cancelled,
        actor_id="therapist-demo",
        expected_version=cancelled.version,
        expected_status=JobStatus.queued.value,
        audit_action="job.cancel",
        audit_message="Transcription job cancelled by therapist.",
    )
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.jobs[cancelled.job_id].status == JobStatus.cancelled
    assert any(event["action"] == "job.cancel" for event in reopened.audit_log)


@pytest.mark.parametrize("operation", ["upload", "consent"])
def test_sql_domain_and_success_audit_roll_back_together(sql_repo, operation) -> None:
    from sqlalchemy import event

    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id=f"tr-rollback-{operation}")
    audit_count = len(sql_repo.audit_log)

    def fail_commit(_session):
        raise RuntimeError("synthetic commit failure")

    event.listen(sql_repo.SessionLocal.class_, "before_commit", fail_commit)
    try:
        with pytest.raises(RuntimeError, match="synthetic commit failure"):
            if operation == "upload":
                create_audio_upload_job(
                    sql_repo,
                    transcript.session_id,
                    AudioUploadRequest(filename="rollback.wav", content_type="audio/wav", size_bytes=12),
                )
            else:
                withdraw_consent(sql_repo, transcript.case_id, "Synthetic rollback")
    finally:
        event.remove(sql_repo.SessionLocal.class_, "before_commit", fail_commit)

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert len(reopened.audit_log) == audit_count
    assert reopened.cases[transcript.case_id].consent_status == "granted"
    if operation == "upload":
        assert not [job for job in reopened.jobs.values() if job.session_id == transcript.session_id]


def test_sql_asr_completion_rolls_back_job_transcript_session_and_audit(sql_repo) -> None:
    from sqlalchemy import event

    current = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-asr-before-rollback")
    job = create_audio_processing_job(
        sql_repo, current.session_id, AudioProcessRequest(provider="mock")
    ).model_copy(update={"status": JobStatus.processing, "message": "Synthetic processing."})
    job = sql_repo.update_processing_job(
        job,
        actor_id="system",
        expected_version=job.version,
        expected_status=JobStatus.queued.value,
        audit_action="audio.process_started",
        audit_message="Synthetic processing started.",
    )
    replacement = current.model_copy(
        update={"transcript_id": "tr-asr-rollback", "source": "mock_asr_draft:mock", "version": 1}
    )
    completed_job = job.model_copy(update={"status": JobStatus.needs_review, "message": "Synthetic complete."})
    before_audits = len(sql_repo.audit_log)

    def fail_commit(_session):
        raise RuntimeError("synthetic ASR completion commit failure")

    event.listen(sql_repo.SessionLocal.class_, "before_commit", fail_commit)
    try:
        with pytest.raises(RuntimeError, match="ASR completion"):
            sql_repo.complete_processing_job(
                completed_job,
                replacement,
                actor_id="system",
                expected_version=job.version,
                expected_status=JobStatus.processing.value,
                audit_action="audio.process",
                audit_message="Synthetic ASR completion.",
            )
    finally:
        event.remove(sql_repo.SessionLocal.class_, "before_commit", fail_commit)

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.jobs[job.job_id].status == JobStatus.processing
    assert reopened.sessions[current.session_id].transcript_id == current.transcript_id
    assert reopened.get_transcript(replacement.transcript_id) is None
    assert len(reopened.audit_log) == before_audits


def seed_uploaded_audio(repo, session_id: str) -> AudioFileMetadata:
    upload = create_audio_upload_job(
        repo,
        session_id,
        AudioUploadRequest(filename="cas.wav", content_type="audio/wav", size_bytes=12),
    )
    audio_id = upload.details["audio_file"]["audio_file_id"]
    current = repo.audio_files[audio_id]
    pending = current.model_copy(update={"upload_status": "pending_verification"})
    pending = repo.update_audio_file_metadata(
        pending,
        actor_id="system",
        expected_version=current.version,
        expected_upload_status="pending",
    )
    checksum = materialize_local_audio(pending)
    return complete_audio_upload(
        repo,
        audio_id,
        AudioUploadCompleteRequest(size_bytes=12, checksum_sha256=checksum),
    )


def test_two_sql_workers_enforce_one_active_job_and_late_cancel_cas(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-job-cas")
    audio = seed_uploaded_audio(sql_repo, transcript.session_id)
    first = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    stale = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    payload = TranscriptionJobRequest(provider="mock", audio_id=audio.audio_file_id)
    job = create_audio_processing_job(first, transcript.session_id, payload)
    with pytest.raises(ValueError, match="one active"):
        create_audio_processing_job(stale, transcript.session_id, payload)
    late_stale = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)

    started = first.update_processing_job(
        job.model_copy(update={"status": JobStatus.processing}),
        actor_id="system", expected_version=job.version, expected_status="queued",
        audit_action="audio.process_started", audit_message="Synthetic started.",
    )
    finished = first.update_processing_job(
        started.model_copy(update={"status": JobStatus.needs_review, "active_audio_file_id": None}),
        actor_id="system", expected_version=started.version, expected_status="processing",
        audit_action="audio.process", audit_message="Synthetic finished.",
    )
    stale_job = late_stale.jobs[job.job_id].model_copy(
        update={"status": JobStatus.cancelled, "active_audio_file_id": None}
    )
    with pytest.raises(ValueError, match="changed"):
        late_stale.update_processing_job(
            stale_job,
            actor_id="therapist-demo",
            expected_version=stale_job.version,
            expected_status="queued",
            audit_action="job.cancel",
            audit_message="Synthetic late cancel.",
        )
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.jobs[job.job_id].status == JobStatus.needs_review
    assert reopened.jobs[job.job_id].details["status_history"] == finished.details["status_history"]


def test_consent_commit_failure_prevents_storage_deletion(sql_repo, monkeypatch) -> None:
    from sqlalchemy import event
    from app.services import consent_service

    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-storage-before-commit")
    seed_uploaded_audio(sql_repo, transcript.session_id)
    calls = []

    class Adapter:
        def delete_object(self, object_key):
            calls.append(object_key)
            raise AssertionError("storage deletion ran before commit")

    monkeypatch.setattr(consent_service, "get_storage_adapter", lambda: Adapter())

    def fail_commit(_session):
        raise RuntimeError("synthetic consent commit failure")

    event.listen(sql_repo.SessionLocal.class_, "before_commit", fail_commit)
    try:
        with pytest.raises(RuntimeError, match="consent commit"):
            withdraw_consent(sql_repo, transcript.case_id, "Synthetic rollback")
    finally:
        event.remove(sql_repo.SessionLocal.class_, "before_commit", fail_commit)
    assert calls == []
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.cases[transcript.case_id].consent_status == "granted"


def test_consent_storage_deletion_partial_failure_is_retryable_after_restart(sql_repo, monkeypatch) -> None:
    from app.services import consent_service
    from app.services.storage_service import StorageDeletionResult

    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-storage-retry")
    first = seed_uploaded_audio(sql_repo, transcript.session_id)
    second = seed_uploaded_audio(sql_repo, transcript.session_id)
    outcomes = {
        first.object_key: StorageDeletionResult("local_private", True, "deleted"),
        second.object_key: StorageDeletionResult("local_private", False, "temporary_failure"),
    }

    class Adapter:
        def delete_object(self, object_key):
            return outcomes[object_key]

    monkeypatch.setattr(consent_service, "get_storage_adapter", lambda: Adapter())
    withdraw_consent(sql_repo, transcript.case_id, "Synthetic partial deletion")
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.audio_files[first.audio_file_id].object_key is None
    retryable = reopened.audio_files[second.audio_file_id]
    assert retryable.object_key == second.object_key
    assert retryable.storage_delete_status == "retryable:temporary_failure"
    pending = reopened.list_pending_audio_deletions(transcript.case_id)
    assert [item.audio_file_id for item in pending] == [second.audio_file_id]
    saved = reopened.record_audio_deletion_result(
        second.audio_file_id,
        expected_version=retryable.version,
        deletion_status="object_not_found",
        deleted=True,
        actor_id="system",
    )
    assert saved.object_key is None
    assert SqlAlchemyRepository(sql_repo.database_url, create_schema=False).list_pending_audio_deletions(
        transcript.case_id
    ) == []


def test_stale_withdrawal_redacts_confirmed_transcript_and_stales_mapping(sql_repo, monkeypatch) -> None:
    from app.services import consent_service
    from app.services.storage_service import StorageDeletionResult

    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-withdraw-after-confirm")
    draft = save_complete_mapping(sql_repo, transcript)
    stale = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    confirmed = confirm_complete_mapping(sql_repo, transcript, draft)

    class Adapter:
        def delete_object(self, _object_key):
            return StorageDeletionResult("metadata_only", False, "not_configured")

    monkeypatch.setattr(consent_service, "get_storage_adapter", lambda: Adapter())
    withdraw_consent(stale, transcript.case_id, "Synthetic withdrawal")
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    redacted = reopened.get_transcript(transcript.transcript_id)
    assert redacted.raw_text == ""
    assert redacted.version == confirmed.applied_transcript_version + 1
    assert get_mapping(reopened, transcript.transcript_id).effective_status == MappingEffectiveStatus.stale


def test_stale_audio_completion_cannot_restore_withdrawn_object_state(sql_repo, monkeypatch) -> None:
    from app.services import consent_service
    from app.services.storage_service import StorageDeletionResult

    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-stale-audio-withdraw")
    audio = seed_uploaded_audio(sql_repo, transcript.session_id)
    stale = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)

    class Adapter:
        def delete_object(self, _object_key):
            return StorageDeletionResult("local_private", False, "temporary_failure")

    monkeypatch.setattr(consent_service, "get_storage_adapter", lambda: Adapter())
    withdraw_consent(sql_repo, transcript.case_id, "Synthetic withdrawal")
    stale_audio = stale.audio_files[audio.audio_file_id]
    with pytest.raises(ValueError, match="consent"):
        stale.update_audio_file_metadata(
            stale_audio.model_copy(update={"upload_status": "uploaded"}),
            actor_id="system",
            expected_version=stale_audio.version,
            expected_upload_status="uploaded",
        )
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    persisted = reopened.audio_files[audio.audio_file_id]
    assert persisted.upload_status == "withdrawn"
    assert persisted.retained is False
    assert persisted.object_key == audio.object_key
    assert persisted.storage_delete_status == "retryable:temporary_failure"


def test_sql_bootstrap_refuses_organization_only_partial_database(tmp_path) -> None:
    from app.db.models import Base, OrganizationRecord
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    url = f"sqlite:///{tmp_path / 'partial.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(OrganizationRecord(organization_id="partial-org", name="Partial", pilot_mode=False))
        db.commit()
    with pytest.raises(RuntimeError, match="every managed table"):
        SqlAlchemyRepository(url, create_schema=False)


def test_sql_cue_acknowledgement_is_atomic_and_restart_durable(sql_repo) -> None:
    from sqlalchemy import event

    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-cue-atomic")
    session = sql_repo.sessions[transcript.session_id]

    def fail_commit(_session):
        raise RuntimeError("synthetic cue commit failure")

    event.listen(sql_repo.SessionLocal.class_, "before_commit", fail_commit)
    try:
        with pytest.raises(RuntimeError, match="cue commit"):
            sql_repo.acknowledge_session_cues(
                session.session_id,
                acknowledged_at="2026-08-23T00:00:00+00:00",
                expected_version=session.version,
                actor_id="therapist-demo",
            )
    finally:
        event.remove(sql_repo.SessionLocal.class_, "before_commit", fail_commit)
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.sessions[session.session_id].cues_acknowledged_at is None
    saved = reopened.acknowledge_session_cues(
        session.session_id,
        acknowledged_at="2026-08-23T00:00:00+00:00",
        expected_version=session.version,
        actor_id="therapist-demo",
    )
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.sessions[session.session_id].cues_acknowledged_at == saved.cues_acknowledged_at
    assert [e["action"] for e in reopened.audit_log[-2:]] == ["session.patch", "cues_acknowledged"]


def test_sql_asr_replacement_invalidates_drafts_preserves_signed_report_and_summaries(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-asr-invalidation")
    session = sql_repo.sessions[transcript.session_id]
    feature = sql_repo.create_feature_set(
        FeatureSet(
            feature_set_id="feat-asr-invalidation",
            session_id=session.session_id,
            transcript_id=transcript.transcript_id,
            transcript_version=transcript.version,
            therapist_attested=False,
            features=[FeatureValue(name="synthetic_metric", value=1.0, unit="count")],
        ),
        actor_id="therapist-demo", audit_action="features.create",
        audit_message="Synthetic findings created.",
    )
    signed = sql_repo.create_report(
        Report(
            report_id="report-asr-signed", session_id=session.session_id, case_id=session.case_id,
            report_type="Session Review Report", title="Signed synthetic report",
            markdown="# Signed", html="<h1>Signed</h1>", status=ReviewStatus.signed_off,
            therapist_signoff_status=ReviewStatus.signed_off,
            signed_by="Synthetic Therapist", signed_at=utc_now(), signed_snapshot_version=1,
            signed_snapshot_hash="d" * 64, signed_snapshot={"report_hash": "d" * 64},
        ),
        actor_id="therapist-demo", audit_action="report.create",
        audit_message="Synthetic signed report stored.",
    )
    draft_report = sql_repo.create_report(
        Report(
            report_id="report-asr-draft", session_id=session.session_id, case_id=session.case_id,
            report_type="Session Review Report", title="Draft synthetic report",
            markdown="# Draft", html="<h1>Draft</h1>",
        ),
        actor_id="therapist-demo", audit_action="report.create",
        audit_message="Synthetic draft report stored.",
    )
    job = create_audio_processing_job(
        sql_repo, session.session_id,
        AudioProcessRequest(provider="mock", draft_text="CHI: synthetic\nTHER: synthetic"),
    )
    completed = run_audio_processing_job(sql_repo, job.job_id)
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert completed.status == JobStatus.needs_review
    assert reopened.features[feature.feature_set_id].review_status == ReviewStatus.stale
    assert reopened.reports[draft_report.report_id].status == ReviewStatus.stale
    assert reopened.reports[signed.report_id].status == ReviewStatus.signed_off
    assert reopened.reports[signed.report_id].signed_snapshot_hash == "d" * 64
    assert reopened.cases[session.case_id].latest_session_status == ReviewStatus.needs_review
    assert any(event["action"] == "workflow.invalidate_downstream" for event in reopened.audit_log)


def test_expanded_sql_success_paths_do_not_depend_on_refresh(sql_repo, monkeypatch) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo, transcript_id="tr-no-refresh-expanded")
    upload = create_audio_upload_job(
        sql_repo,
        transcript.session_id,
        AudioUploadRequest(filename="no-refresh.wav", content_type="audio/wav", size_bytes=12),
    )
    audio_id = upload.details["audio_file"]["audio_file_id"]
    current = sql_repo.audio_files[audio_id]

    def fail_refresh(*_args, **_kwargs):
        raise RuntimeError("synthetic refresh failure")

    monkeypatch.setattr(sql_repo.SessionLocal.class_, "refresh", fail_refresh)
    monkeypatch.setattr(
        sql_repo,
        "load",
        lambda: (_ for _ in ()).throw(RuntimeError("synthetic global load failure")),
    )
    saved = sql_repo.update_audio_file_metadata(
        current.model_copy(update={"upload_status": "pending_verification"}),
        actor_id="system",
        expected_version=current.version,
        expected_upload_status="pending",
    )
    acknowledged = sql_repo.acknowledge_session_cues(
        transcript.session_id,
        acknowledged_at="2026-08-23T01:00:00+00:00",
        expected_version=sql_repo.sessions[transcript.session_id].version,
        actor_id="therapist-demo",
    )
    assert saved.upload_status == "pending_verification"
    assert acknowledged.cues_acknowledged_by == "therapist-demo"

    case = sql_repo.create_case(
        ChildCaseCreate(child_code="CASE-NO-REFRESH", age_months=60, consent_status="granted"),
        actor_id="therapist-demo",
    )
    updated_case = sql_repo.update_case(
        case.case_id,
        ChildCaseUpdate(language="English"),
        expected_version=case.version,
        actor_id="therapist-demo",
    )
    session = sql_repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-08-24", session_type="language_sample"),
        actor_id="therapist-demo",
    )
    updated_session = sql_repo.update_session(
        session.session_id,
        TherapySessionUpdate(status=ReviewStatus.needs_review),
        expected_version=session.version,
        actor_id="therapist-demo",
    )
    created_transcript = sql_repo.create_transcript(
        Transcript(
            transcript_id="tr-no-refresh-crud",
            session_id=session.session_id,
            case_id=case.case_id,
            organization_id=case.organization_id,
            source="manual",
            raw_text="*CHI:\tsynthetic .",
        ),
        session_status=ReviewStatus.needs_review,
        actor_id="therapist-demo",
        audit_action="transcript.create",
        audit_message="Synthetic transcript created.",
    )
    updated_transcript = sql_repo.update_transcript(
        created_transcript.model_copy(
            update={"raw_text": "*CHI:\tsynthetic update .", "version": created_transcript.version + 1}
        ),
        session_status=ReviewStatus.needs_review,
        expected_version=created_transcript.version,
        actor_id="therapist-demo",
        audit_action="transcript.update",
        audit_message="Synthetic transcript updated.",
    )
    report = sql_repo.create_report(
        Report(
            report_id="report-no-refresh-crud",
            session_id=session.session_id,
            case_id=case.case_id,
            report_type="Session Review Report",
            title="Synthetic report",
            markdown="# Draft",
            html="<h1>Draft</h1>",
        ),
        actor_id="therapist-demo",
        audit_action="report.create",
        audit_message="Synthetic report created.",
    )
    updated_report = sql_repo.update_report(
        report.model_copy(update={"markdown": "# Updated", "version": report.version + 1}),
        expected_version=report.version,
        actor_id="therapist-demo",
        audit_action="report.update",
        audit_message="Synthetic report updated.",
    )
    assert updated_case.language == "English"
    assert updated_session.status == ReviewStatus.needs_review
    assert updated_transcript.raw_text.endswith("update .")
    assert updated_report.markdown == "# Updated"


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    [
        (current, target)
        for current in ("queued", "processing", "transcription_completed", "failed", "cancelled", "needs_review")
        for target in ("processing", "transcription_completed", "failed", "cancelled", "needs_review")
    ],
)
def test_sql_processing_job_transition_matrix(sql_repo, current_status, next_status) -> None:
    from app.db.models import ProcessingJobRecord
    from app.repositories.mock_repository import ALLOWED_JOB_TRANSITIONS

    transcript = seed_temporary_asr_transcript(
        sql_repo, transcript_id=f"tr-transition-{current_status[:6]}-{next_status[:6]}"
    )
    job = ProcessingJob(
        job_id=f"job-transition-{current_status[:6]}-{next_status[:6]}",
        organization_id=transcript.organization_id,
        session_id=transcript.session_id,
        status=current_status,
        message="Synthetic current state.",
        details={"status_history": [current_status]},
    )
    with sql_repo.SessionLocal() as db:
        db.add(sql_repo._job_to_record(job))
        db.commit()
    submitted = job.model_copy(
        update={
            "status": next_status,
            "message": "Synthetic next state.",
            "details": {"status_history": [current_status, next_status]},
        }
    )
    if next_status in ALLOWED_JOB_TRANSITIONS[current_status]:
        saved = sql_repo.update_processing_job(
            submitted,
            actor_id="system", expected_version=1, expected_status=current_status,
            audit_action="job.transition", audit_message="Synthetic job transition.",
        )
        assert saved.status == next_status
        assert saved.version == 2
    else:
        with pytest.raises(ValueError, match="not allowed"):
            sql_repo.update_processing_job(
                submitted,
                actor_id="system", expected_version=1, expected_status=current_status,
                audit_action="job.transition", audit_message="Synthetic job transition.",
            )


def test_sql_draft_save_reloads_losslessly_and_preserves_confirmed_history(sql_repo) -> None:
    from app.db.models import SpeakerMappingRecord

    transcript = seed_temporary_asr_transcript(sql_repo)
    first = save_complete_mapping(sql_repo, transcript)
    replacement = save_complete_mapping(sql_repo, transcript, expected_mapping_version=first.mapping_version)
    confirmed = confirm_complete_mapping(sql_repo, transcript, replacement)

    current = sql_repo.transcripts[transcript.transcript_id]
    edited = current.model_copy(update={"version": current.version + 1, "updated_at": utc_now()})
    sql_repo.update_transcript(
        edited,
        session_status=ReviewStatus.needs_review,
        expected_version=current.version,
        actor_id="therapist-demo",
        audit_action="transcript.patch",
        audit_message="Synthetic transcript changed.",
    )
    latest = save_complete_mapping(sql_repo, edited)

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    with reopened.SessionLocal() as db:
        rows = (
            db.query(SpeakerMappingRecord)
            .filter_by(transcript_id=transcript.transcript_id)
            .order_by(SpeakerMappingRecord.mapping_version)
            .all()
        )

    assert first.mapping_id == replacement.mapping_id == confirmed.mapping_id
    assert [row.mapping_version for row in rows] == [confirmed.mapping_version, latest.mapping_version]
    assert rows[0].status == MappingPersistedStatus.confirmed.value
    assert reopened.speaker_mappings[confirmed.mapping_id].entries == confirmed.entries
    assert reopened.get_latest_speaker_mapping(transcript.transcript_id) == SpeakerMapping.model_validate(
        latest.model_dump()
    )


def test_sql_confirmation_is_atomic_and_survives_reload(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    draft = save_complete_mapping(sql_repo, transcript)
    confirmed = confirm_complete_mapping(sql_repo, transcript, draft)

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    persisted = reopened.get_latest_speaker_mapping(transcript.transcript_id)

    assert persisted is not None
    assert persisted.status == MappingPersistedStatus.confirmed
    assert persisted.mapping_version == draft.mapping_version + 1
    assert persisted.applied_transcript_version == transcript.version + 1
    assert reopened.transcripts[transcript.transcript_id].version == transcript.version + 1
    assert [item.speaker for item in reopened.transcripts[transcript.transcript_id].utterances] == ["CHI", "THER"]
    assert reopened.sessions[transcript.session_id].status == ReviewStatus.needs_review


@pytest.mark.parametrize("conflict", ["mapping", "transcript"])
def test_sql_confirmation_conflict_rolls_back_every_row_mirror_and_audit(sql_repo, conflict) -> None:
    from app.db.models import AuditLogRecord, SpeakerMappingRecord, TranscriptRecord

    transcript = seed_temporary_asr_transcript(sql_repo)
    draft = save_complete_mapping(sql_repo, transcript)
    mapping_before = deepcopy(sql_repo.speaker_mappings)
    transcript_before = deepcopy(sql_repo.transcripts)
    audit_before = deepcopy(sql_repo.audit_log)
    submitted = draft.model_copy(
        update={
            "status": MappingPersistedStatus.confirmed,
            "applied_transcript_version": transcript.version + 1,
            "confirmed_by_user_id": "therapist-demo",
            "confirmed_by_role": "therapist",
            "confirmed_at": utc_now(),
        }
    )
    rebuilt = build_confirmed_transcript(transcript, draft)

    expected_mapping = draft.mapping_version - 1 if conflict == "mapping" else draft.mapping_version
    expected_transcript = transcript.version - 1 if conflict == "transcript" else transcript.version
    error = SpeakerMappingVersionConflictError if conflict == "mapping" else TranscriptVersionConflictError
    with pytest.raises(error):
        sql_repo.confirm_speaker_mapping(
            submitted,
            rebuilt,
            expected_transcript_version=expected_transcript,
            expected_mapping_version=expected_mapping,
            actor_id="therapist-demo",
        )

    with sql_repo.SessionLocal() as db:
        transcript_row = db.get(TranscriptRecord, transcript.transcript_id)
        mapping_row = db.get(SpeakerMappingRecord, draft.mapping_id)
        confirmation_audits = db.query(AuditLogRecord).filter_by(action="speaker_mapping.confirm").count()
    assert transcript_row.version == transcript.version
    assert mapping_row.status == MappingPersistedStatus.draft.value
    assert confirmation_audits == 0
    assert sql_repo.speaker_mappings == mapping_before
    assert sql_repo.transcripts == transcript_before
    assert sql_repo.audit_log == audit_before


@pytest.mark.parametrize("forgery", ["mapping", "transcript", "tenant"])
def test_sql_confirmation_rejects_forged_payloads_without_mutation(sql_repo, forgery) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    draft = save_complete_mapping(sql_repo, transcript)
    submitted_mapping = draft.model_copy(
        update={
            "status": MappingPersistedStatus.confirmed,
            "applied_transcript_version": transcript.version + 1,
            "confirmed_by_user_id": "therapist-demo",
            "confirmed_by_role": "therapist",
            "confirmed_at": utc_now(),
        }
    )
    submitted_transcript = build_confirmed_transcript(transcript, draft)
    if forgery == "mapping":
        submitted_mapping = submitted_mapping.model_copy(update={"entries": list(reversed(submitted_mapping.entries))})
    elif forgery == "transcript":
        submitted_transcript = submitted_transcript.model_copy(update={"raw_text": "forged"})
    else:
        submitted_mapping = submitted_mapping.model_copy(update={"organization_id": "other-org"})

    with pytest.raises(SpeakerMappingVersionConflictError):
        sql_repo.confirm_speaker_mapping(
            submitted_mapping,
            submitted_transcript,
            expected_transcript_version=transcript.version,
            expected_mapping_version=draft.mapping_version,
            actor_id="therapist-demo",
        )

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.transcripts[transcript.transcript_id].version == transcript.version
    assert reopened.get_latest_speaker_mapping(transcript.transcript_id).status == MappingPersistedStatus.draft
    assert not any(event["action"] == "speaker_mapping.confirm" for event in reopened.audit_log)


def test_sql_draft_uses_authoritative_transcript_tenant_and_rejects_wrong_transcript(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    direct = SpeakerMapping(
        mapping_id="mapping-forged-tenant",
        organization_id="other-org",
        transcript_id=transcript.transcript_id,
        source_transcript_version=transcript.version,
        entries=[],
    )
    saved = sql_repo.save_speaker_mapping_draft(
        direct,
        expected_mapping_version=None,
        actor_id="therapist-demo",
    )
    assert saved.organization_id == transcript.organization_id

    missing = direct.model_copy(update={"mapping_id": "mapping-missing", "transcript_id": "missing-transcript"})
    with pytest.raises(KeyError):
        sql_repo.save_speaker_mapping_draft(
            missing,
            expected_mapping_version=None,
            actor_id="therapist-demo",
        )


def test_sql_confirmation_invalidates_current_outputs_and_preserves_signed_report(sql_repo) -> None:
    from app.db.models import AiReviewRecord, FeatureSetRecord, MLResultRecord, ReportRecord

    transcript = seed_temporary_asr_transcript(sql_repo)
    draft = save_complete_mapping(sql_repo, transcript)
    session = sql_repo.sessions[transcript.session_id]
    feature = sql_repo.create_feature_set(
        FeatureSet(
            feature_set_id="feat-spmap",
            session_id=session.session_id,
            transcript_id=transcript.transcript_id,
            transcript_version=transcript.version,
            therapist_attested=False,
            features=[FeatureValue(name="synthetic_metric", value=1.0, unit="count")],
        ),
        actor_id="therapist-demo",
        audit_action="features.create",
        audit_message="Synthetic findings created.",
    )
    ai = sql_repo.create_ai_review(
        AiReview(
            ai_review_id="ai-spmap",
            session_id=session.session_id,
            summary="Synthetic summary.",
            key_findings=[],
            concerns=[],
            strengths=[],
            limitations=[],
            recommended_review_actions=[],
            confidence_level="limited",
            input_transcript_version=transcript.version,
            feature_set_id=feature.feature_set_id,
        ),
        actor_id="therapist-demo",
        audit_action="ai.create",
        audit_message="Synthetic review created.",
    )
    ml = sql_repo.create_ml_result(
        MLResult(
            result_id="ml-spmap",
            transcript_id=transcript.transcript_id,
            session_id=session.session_id,
            feature_result_id=feature.feature_set_id,
            provider_id="synthetic",
            provider_name="Synthetic provider",
            provider_version="1",
            input_feature_schema_version="synthetic-v1",
            input_feature_hash="synthetic-hash",
            status="completed",
        ),
        actor_id="therapist-demo",
        audit_action="ml.create",
        audit_message="Synthetic result created.",
    )
    signed = sql_repo.create_report(
        Report(
            report_id="report-signed-spmap",
            session_id=session.session_id,
            case_id=session.case_id,
            report_type="Session Review Report",
            title="Signed synthetic report",
            markdown="# Signed synthetic report",
            html="<h1>Signed synthetic report</h1>",
            status=ReviewStatus.signed_off,
            therapist_signoff_status=ReviewStatus.signed_off,
            signed_by="Synthetic Therapist",
            signed_at=utc_now(),
            signed_snapshot_version=1,
            signed_snapshot_hash="a" * 64,
            signed_snapshot={"report_hash": "a" * 64},
        ),
        actor_id="therapist-demo",
        audit_action="report.create",
        audit_message="Synthetic signed report stored.",
    )
    current_report = sql_repo.create_report(
        Report(
            report_id="report-draft-spmap",
            session_id=session.session_id,
            case_id=session.case_id,
            report_type="Session Review Report",
            title="Draft synthetic report",
            markdown="# Draft synthetic report",
            html="<h1>Draft synthetic report</h1>",
        ),
        actor_id="therapist-demo",
        audit_action="report.create",
        audit_message="Synthetic draft report stored.",
    )

    confirm_complete_mapping(sql_repo, transcript, draft)

    with sql_repo.SessionLocal() as db:
        feature_row = db.get(FeatureSetRecord, feature.feature_set_id)
        ai_row = db.get(AiReviewRecord, ai.ai_review_id)
        ml_row = db.get(MLResultRecord, ml.result_id)
        signed_row = db.get(ReportRecord, signed.report_id)
        current_report_row = db.get(ReportRecord, current_report.report_id)
    assert feature_row.review_status == ReviewStatus.stale.value
    assert ai_row.therapist_review_status == ReviewStatus.stale.value
    assert ml_row.payload["is_current"] is False
    assert current_report_row.status == ReviewStatus.stale.value
    assert signed_row.status == ReviewStatus.signed_off.value
    assert signed_row.signed_snapshot_hash == "a" * 64
    assert sql_repo.reports[current_report.report_id].status == ReviewStatus.stale
    assert sql_repo.reports[signed.report_id].status == ReviewStatus.signed_off


def test_sql_confirmation_of_old_session_preserves_latest_case_summary(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo, session_date="2026-08-01")
    draft = save_complete_mapping(sql_repo, transcript)
    case = sql_repo.cases[transcript.case_id]
    newer = sql_repo.create_session(
        case.case_id,
        TherapySessionCreate(session_date="2026-08-22", session_type="language_sample"),
        actor_id="therapist-demo",
    )
    newer = sql_repo.update_session(
        newer.session_id,
        TherapySessionUpdate(status=ReviewStatus.attested),
        expected_version=newer.version,
        actor_id="therapist-demo",
    )

    confirm_complete_mapping(sql_repo, transcript, draft)

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    persisted_case = reopened.cases[case.case_id]
    assert persisted_case.latest_session_date == newer.session_date
    assert persisted_case.latest_session_status == ReviewStatus.attested


def test_concurrent_sql_repositories_allow_exactly_one_initial_draft(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    first = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    second = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    cleanup = synchronize_mapping_reads((first, second), occurrence=1)

    def save(repo):
        try:
            return save_complete_mapping(repo, transcript).mapping_version
        except SpeakerMappingVersionConflictError:
            return "conflict"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(save, (first, second)))
    finally:
        cleanup()

    assert sorted(results, key=str) == [1, "conflict"]
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert len(reopened.speaker_mappings) == 1
    assert len([event for event in reopened.audit_log if event["action"] == "speaker_mapping.draft_save"]) == 1


def test_stale_sql_legacy_audit_cannot_revert_confirmed_workflow_state(sql_repo) -> None:
    from app.db.models import AuditLogRecord, FeatureSetRecord, ReportRecord

    transcript = seed_temporary_asr_transcript(sql_repo)
    draft = save_complete_mapping(sql_repo, transcript)
    session = sql_repo.sessions[transcript.session_id]
    feature = sql_repo.create_feature_set(
        FeatureSet(
            feature_set_id="feat-stale-worker",
            session_id=session.session_id,
            transcript_id=transcript.transcript_id,
            transcript_version=transcript.version,
            therapist_attested=False,
            features=[FeatureValue(name="synthetic_metric", value=1.0, unit="count")],
        ),
        actor_id="therapist-demo",
        audit_action="features.create",
        audit_message="Synthetic findings created.",
    )
    signed = sql_repo.create_report(
        Report(
            report_id="report-signed-stale-worker",
            session_id=session.session_id,
            case_id=session.case_id,
            report_type="Session Review Report",
            title="Signed synthetic report",
            markdown="# Signed synthetic report",
            html="<h1>Signed synthetic report</h1>",
            status=ReviewStatus.signed_off,
            therapist_signoff_status=ReviewStatus.signed_off,
            signed_by="Synthetic Therapist",
            signed_at=utc_now(),
            signed_snapshot_version=1,
            signed_snapshot_hash="b" * 64,
            signed_snapshot={"report_hash": "b" * 64},
        ),
        actor_id="therapist-demo",
        audit_action="report.create",
        audit_message="Synthetic signed report stored.",
    )
    stale = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    prior_audit_ids = {event["audit_id"] for event in sql_repo.audit_log}

    confirmed = confirm_complete_mapping(sql_repo, transcript, draft)

    stale.transcripts[transcript.transcript_id].raw_text = "stale synthetic mirror"
    with pytest.raises(RuntimeError, match="not available"):
        stale.save()
    stale.add_audit(
        "speaker_mapping.concurrent_audit",
        transcript.transcript_id,
        "Concurrent synthetic audit stored.",
        actor_id="therapist-demo",
        organization_id=transcript.organization_id,
    )

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    persisted_mapping = reopened.get_latest_speaker_mapping(transcript.transcript_id)
    with reopened.SessionLocal() as db:
        feature_row = db.get(FeatureSetRecord, feature.feature_set_id)
        signed_row = db.get(ReportRecord, signed.report_id)
        audit_ids = {row.audit_id for row in db.query(AuditLogRecord).all()}

    assert reopened.transcripts[transcript.transcript_id].version == transcript.version + 1
    assert persisted_mapping.status == MappingPersistedStatus.confirmed
    assert persisted_mapping.mapping_version == confirmed.mapping_version
    assert persisted_mapping.applied_transcript_version == transcript.version + 1
    assert reopened.sessions[session.session_id].status == ReviewStatus.needs_review
    assert reopened.cases[session.case_id].latest_session_status == ReviewStatus.needs_review
    assert feature_row.review_status == ReviewStatus.stale.value
    assert signed_row.status == ReviewStatus.signed_off.value
    assert signed_row.signed_snapshot_hash == "b" * 64
    assert prior_audit_ids.issubset(audit_ids)
    assert any(event["action"] == "speaker_mapping.confirm" for event in reopened.audit_log)
    assert any(event["action"] == "workflow.invalidate_downstream" for event in reopened.audit_log)
    assert any(event["action"] == "speaker_mapping.concurrent_audit" for event in reopened.audit_log)


def test_stale_sql_worker_reads_confirmed_transcript_mapping_and_gate_authoritatively(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    draft = save_complete_mapping(sql_repo, transcript)
    stale = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)

    confirmed = confirm_complete_mapping(sql_repo, transcript, draft)
    response = get_mapping(stale, transcript.transcript_id)
    authoritative_transcript = stale.get_transcript(transcript.transcript_id)

    assert response.effective_status == MappingEffectiveStatus.confirmed
    assert response.mapping_version == confirmed.mapping_version
    assert authoritative_transcript.version == transcript.version + 1
    require_confirmed_mapping(stale, authoritative_transcript)
    assert stale.transcripts[transcript.transcript_id].version == transcript.version + 1
    assert stale.speaker_mappings[draft.mapping_id].mapping_version == confirmed.mapping_version


def test_sql_draft_success_does_not_depend_on_global_load(sql_repo, monkeypatch) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)

    def fail_load() -> None:
        raise RuntimeError("synthetic global load failure")

    monkeypatch.setattr(sql_repo, "load", fail_load)
    saved = save_complete_mapping(sql_repo, transcript)

    assert sql_repo.speaker_mappings[saved.mapping_id] == SpeakerMapping.model_validate(saved.model_dump())
    assert sql_repo.audit_log[-1]["action"] == "speaker_mapping.draft_save"
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.get_latest_speaker_mapping(transcript.transcript_id).mapping_version == saved.mapping_version


def test_sql_confirmation_success_does_not_depend_on_global_load(sql_repo, monkeypatch) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    draft = save_complete_mapping(sql_repo, transcript)

    def fail_load() -> None:
        raise RuntimeError("synthetic global load failure")

    monkeypatch.setattr(sql_repo, "load", fail_load)
    confirmed = confirm_complete_mapping(sql_repo, transcript, draft)

    assert sql_repo.transcripts[transcript.transcript_id].version == transcript.version + 1
    assert sql_repo.speaker_mappings[draft.mapping_id].mapping_version == confirmed.mapping_version
    assert sql_repo.sessions[transcript.session_id].status == ReviewStatus.needs_review
    assert sql_repo.cases[transcript.case_id].latest_session_status == ReviewStatus.needs_review
    assert sql_repo.audit_log[-1]["action"] == "speaker_mapping.confirm"
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.transcripts[transcript.transcript_id].version == transcript.version + 1
    assert reopened.get_latest_speaker_mapping(transcript.transcript_id).status == MappingPersistedStatus.confirmed


def test_sql_mapping_datetimes_reload_as_utc_and_serialize_with_offsets(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    draft = save_complete_mapping(sql_repo, transcript)
    confirmed = confirm_complete_mapping(sql_repo, transcript, draft)

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    persisted = reopened.get_latest_speaker_mapping(transcript.transcript_id)
    payload = persisted.model_dump(mode="json")

    assert persisted.created_at.utcoffset().total_seconds() == 0
    assert persisted.updated_at.utcoffset().total_seconds() == 0
    assert persisted.confirmed_at.utcoffset().total_seconds() == 0
    assert payload["created_at"].endswith(("Z", "+00:00"))
    assert payload["updated_at"].endswith(("Z", "+00:00"))
    assert payload["confirmed_at"].endswith(("Z", "+00:00"))


def test_unexpected_confirmation_audit_integrity_error_is_not_misclassified(sql_repo, monkeypatch) -> None:
    from sqlalchemy.exc import IntegrityError

    transcript = seed_temporary_asr_transcript(sql_repo)
    draft = save_complete_mapping(sql_repo, transcript)
    duplicate_audit = sql_repo._audit_to_record(sql_repo.audit_log[0])

    monkeypatch.setattr(sql_repo, "_audit_to_record", lambda _event: duplicate_audit)
    with pytest.raises(IntegrityError):
        confirm_complete_mapping(sql_repo, transcript, draft)

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.transcripts[transcript.transcript_id].version == transcript.version
    assert reopened.get_latest_speaker_mapping(transcript.transcript_id).status == MappingPersistedStatus.draft


def test_concurrent_sql_repositories_allow_exactly_one_confirmation(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    draft = save_complete_mapping(sql_repo, transcript)
    first = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    second = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    cleanup = synchronize_mapping_reads((first, second), occurrence=2)

    def confirm(repo):
        try:
            return confirm_complete_mapping(repo, transcript, draft).status
        except Exception as exc:  # service translates repository CAS to its stable domain error
            return getattr(exc, "code", type(exc).__name__)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(confirm, (first, second)))
    finally:
        cleanup()

    assert results.count(MappingPersistedStatus.confirmed) == 1
    assert results.count("SPEAKER_MAPPING_VERSION_CONFLICT") == 1
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.transcripts[transcript.transcript_id].version == transcript.version + 1
    assert len([event for event in reopened.audit_log if event["action"] == "speaker_mapping.confirm"]) == 1


def test_sql_confirmation_rolls_back_database_and_mirrors_when_audit_insert_fails(sql_repo, monkeypatch) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    draft = save_complete_mapping(sql_repo, transcript)
    mappings_before = deepcopy(sql_repo.speaker_mappings)
    transcripts_before = deepcopy(sql_repo.transcripts)
    audits_before = deepcopy(sql_repo.audit_log)

    def fail_audit(_event):
        raise RuntimeError("synthetic audit insert failure")

    monkeypatch.setattr(sql_repo, "_audit_to_record", fail_audit)
    with pytest.raises(RuntimeError, match="synthetic audit insert failure"):
        confirm_complete_mapping(sql_repo, transcript, draft)

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.transcripts[transcript.transcript_id].version == transcript.version
    assert reopened.get_latest_speaker_mapping(transcript.transcript_id).status == MappingPersistedStatus.draft
    assert sql_repo.speaker_mappings == mappings_before
    assert sql_repo.transcripts == transcripts_before
    assert sql_repo.audit_log == audits_before
