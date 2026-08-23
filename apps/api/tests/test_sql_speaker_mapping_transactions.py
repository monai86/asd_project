from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier

import pytest

from app.repositories.base import SpeakerMappingVersionConflictError, TranscriptVersionConflictError
from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
from app.schemas.clinical import (
    AiReview,
    ChildCaseCreate,
    FeatureSet,
    FeatureValue,
    MLResult,
    Report,
    ReviewStatus,
    TherapySessionCreate,
    TherapySessionUpdate,
    Transcript,
    Utterance,
    utc_now,
)
from app.schemas.speaker_mapping import (
    MappingPersistedStatus,
    SpeakerMapping,
    SpeakerMappingConfirmRequest,
    SpeakerMappingDraftUpdate,
)
from app.services.speaker_mapping_service import (
    build_confirmed_transcript,
    confirm_mapping,
    save_mapping_draft,
)


@pytest.fixture
def sql_repo(tmp_path) -> SqlAlchemyRepository:
    pytest.importorskip("sqlalchemy")
    return SqlAlchemyRepository(f"sqlite:///{tmp_path / 'speaker-mapping.db'}")


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
    barrier = Barrier(2)

    def save(repo):
        barrier.wait()
        try:
            return save_complete_mapping(repo, transcript).mapping_version
        except SpeakerMappingVersionConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, (first, second)))

    assert sorted(results, key=str) == [1, "conflict"]
    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert len(reopened.speaker_mappings) == 1
    assert len([event for event in reopened.audit_log if event["action"] == "speaker_mapping.draft_save"]) == 1


def test_stale_sql_snapshot_save_cannot_erase_mapping_committed_by_another_process(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    stale = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    saved = save_complete_mapping(sql_repo, transcript)

    stale.add_audit(
        "speaker_mapping.concurrent_audit",
        transcript.transcript_id,
        "Concurrent synthetic audit stored.",
        actor_id="therapist-demo",
        organization_id=transcript.organization_id,
    )

    reopened = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    assert reopened.get_latest_speaker_mapping(transcript.transcript_id) == SpeakerMapping.model_validate(
        saved.model_dump()
    )
    assert any(event["action"] == "speaker_mapping.concurrent_audit" for event in reopened.audit_log)


def test_concurrent_sql_repositories_allow_exactly_one_confirmation(sql_repo) -> None:
    transcript = seed_temporary_asr_transcript(sql_repo)
    draft = save_complete_mapping(sql_repo, transcript)
    first = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    second = SqlAlchemyRepository(sql_repo.database_url, create_schema=False)
    barrier = Barrier(2)

    def confirm(repo):
        barrier.wait()
        try:
            return confirm_complete_mapping(repo, transcript, draft).status
        except Exception as exc:  # service translates repository CAS to its stable domain error
            return getattr(exc, "code", type(exc).__name__)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(confirm, (first, second)))

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
