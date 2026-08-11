from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.api.v1.dependencies import get_repository
from app.core.security import CurrentUser
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    QaStatus,
    ReviewStatus,
    SpeakerMappingConfirmRequest,
    SpeakerMappingDraftRequest,
    Transcript,
    Utterance,
)
from app.services import speaker_mapping_service


client = TestClient(app)


@pytest.fixture()
def repo():
    repository = MockRepository()
    app.dependency_overrides[get_repository] = lambda: repository
    try:
        yield repository
    finally:
        app.dependency_overrides.pop(get_repository, None)


def _seed_asr_transcript(
    repo: MockRepository,
    *,
    transcript_id: str = "transcript_mapping_001",
    version: int = 1,
    utterances: list[Utterance] | None = None,
) -> str:
    case_id = client.post(
        "/api/v1/cases",
        json={
            "child_code": "C-MAPPING-001",
            "age_months": 60,
            "language": "Thai-English",
            "consent_status": "granted",
        },
    ).json()["case_id"]
    session_id = client.post(
        f"/api/v1/cases/{case_id}/sessions",
        json={"session_date": "2026-08-01", "session_type": "therapy_session"},
    ).json()["session_id"]
    seeded_utterances = utterances or [
        Utterance(
            utterance_id="utt_spk_01_a",
            speaker="SPK_01",
            temporary_speaker_id="SPK_01",
            source_speaker_label="speaker_0",
            text="I see the red car and the blue truck moving very fast",
            start_ms=0,
            end_ms=1200,
            source="asr",
            review_status="reviewed",
        ),
        Utterance(
            utterance_id="utt_spk_02_a",
            speaker="SPK_02",
            temporary_speaker_id="SPK_02",
            source_speaker_label="speaker_1",
            text="tell me more",
            start_ms=1300,
            end_ms=2200,
            source="asr",
            review_status="reviewed",
        ),
        Utterance(
            utterance_id="utt_spk_01_b",
            speaker="SPK_01",
            temporary_speaker_id="SPK_01",
            source_speaker_label="speaker_0",
            text="then the car stops near the small house and waits",
            start_ms=2300,
            end_ms=3200,
            source="asr",
            review_status="reviewed",
        ),
        Utterance(
            utterance_id="utt_spk_01_c",
            speaker="SPK_01",
            temporary_speaker_id="SPK_01",
            source_speaker_label="speaker_0",
            text="I want to drive the car again after lunch",
            start_ms=3300,
            end_ms=4200,
            source="asr",
            review_status="reviewed",
        ),
    ]
    raw_text = "\n".join(
        [
            "@Begin",
            "@Languages:\ttha, eng",
            "@Participants:\tCHI Child Target_Child, THE Therapist Investigator",
            "*SPK_01:\tI see the red car and the blue truck moving very fast \x150_1200\x15",
            "*SPK_02:\ttell me more \x151300_2200\x15",
            "*SPK_01:\tthen the car stops near the small house and waits \x152300_3200\x15",
            "*SPK_01:\tI want to drive the car again after lunch \x153300_4200\x15",
            "@End",
        ]
    )
    transcript = Transcript(
        transcript_id=transcript_id,
        session_id=session_id,
        case_id=case_id,
        source="asr_draft:local_faster_whisper",
        raw_text=raw_text,
        utterances=seeded_utterances,
        review_status=ReviewStatus.needs_review,
        version=version,
        raw_speaker_labels=["speaker_0", "speaker_1"],
        asr_provenance={
            "provider_id": "local_faster_whisper",
            "diarization": {
                "provider": "optional_diarizer",
                "clusters": {
                    "SPK_01": {"source_speaker_label": "speaker_0"},
                    "SPK_02": {"source_speaker_label": "speaker_1"},
                },
            },
        },
    )
    repo.transcripts[transcript_id] = transcript
    repo.sessions[session_id].transcript_id = transcript_id
    return transcript_id


def _mapping_entries() -> list[dict]:
    return [
        {
            "temporary_speaker_id": "SPK_01",
            "confirmed_chat_code": "CHI",
            "participant_role": "target_child",
            "disposition": "target",
            "source_speaker_label": "tampered-by-client",
            "source_provider": "tampered-provider",
            "source_provider_metadata": {"tampered": True},
            "affected_utterance_ids": ["utt_spk_01_a", "utt_spk_01_b", "utt_spk_01_c"],
        },
        {
            "temporary_speaker_id": "SPK_02",
            "confirmed_chat_code": "THE",
            "participant_role": "therapist",
            "disposition": "non_target",
            "affected_utterance_ids": ["utt_spk_02_a"],
        },
    ]


def test_speaker_mapping_confirm_preserves_raw_provider_labels_and_records_therapist(repo):
    transcript_id = _seed_asr_transcript(repo, version=3)

    initial = client.get(f"/api/v1/transcripts/{transcript_id}/speaker-mapping")
    assert initial.status_code == 200
    assert initial.json()["status"] == "draft"
    assert {
        entry["temporary_speaker_id"]: entry["source_speaker_label"]
        for entry in initial.json()["entries"]
    } == {"SPK_01": "speaker_0", "SPK_02": "speaker_1"}

    draft = client.put(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping",
        json={
            "expected_transcript_version": 3,
            "entries": _mapping_entries(),
        },
    )
    assert draft.status_code == 200
    assert draft.json()["status"] == "draft"
    assert draft.json()["entries"][0]["source_speaker_label"] == "speaker_0"
    assert draft.json()["entries"][0]["source_provider"] == "optional_diarizer"
    assert draft.json()["entries"][0]["source_provider_metadata"] == {
        "source_speaker_label": "speaker_0"
    }

    confirmed = client.post(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping/confirm",
        json={
            "expected_transcript_version": 3,
            "expected_mapping_version": draft.json()["mapping_version"],
        },
    )
    assert confirmed.status_code == 200
    body = confirmed.json()
    assert body["status"] == "confirmed"
    assert body["confirmed_by_user_id"] == "therapist-demo"
    assert body["confirmed_by_role"] == "therapist"
    assert body["confirmed_at"]
    assert body["transcript_version"] == 3
    assert {
        entry["temporary_speaker_id"]: entry["confirmed_chat_code"]
        for entry in body["entries"]
    } == {"SPK_01": "CHI", "SPK_02": "THE"}

    updated = repo.transcripts[transcript_id]
    assert [utterance.speaker for utterance in updated.utterances] == ["CHI", "THE", "CHI", "CHI"]
    assert [utterance.temporary_speaker_id for utterance in updated.utterances] == [
        "SPK_01",
        "SPK_02",
        "SPK_01",
        "SPK_01",
    ]
    assert [utterance.source_speaker_label for utterance in updated.utterances] == [
        "speaker_0",
        "speaker_1",
        "speaker_0",
        "speaker_0",
    ]


def test_speaker_mapping_confirm_rejects_ambiguous_required_role_and_unknown_speaker(repo):
    transcript_id = _seed_asr_transcript(repo)

    unknown = client.put(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping",
        json={
            "expected_transcript_version": 1,
            "entries": [
                {
                    "temporary_speaker_id": "SPK_99",
                    "confirmed_chat_code": "CHI",
                    "participant_role": "target_child",
                    "disposition": "target",
                    "affected_utterance_ids": ["utt_spk_01_a"],
                }
            ],
        },
    )
    assert unknown.status_code == 400
    assert "SPEAKER_MAPPING_UNKNOWN_SPEAKER" in unknown.json()["detail"]

    repo.transcripts[transcript_id].utterances.append(
        Utterance(
            utterance_id="utt_spk_03_a",
            speaker="SPK_03",
            temporary_speaker_id="SPK_03",
            source_speaker_label="speaker_2",
            text="another adult comment",
            start_ms=4300,
            end_ms=5000,
            source="asr",
            review_status="reviewed",
        )
    )
    repo.transcripts[transcript_id].raw_speaker_labels.append("speaker_2")
    repo.transcripts[transcript_id].asr_provenance["diarization"]["clusters"]["SPK_03"] = {
        "source_speaker_label": "speaker_2"
    }

    duplicate_role = client.put(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping",
        json={
            "expected_transcript_version": 1,
            "entries": [
                {
                    "temporary_speaker_id": "SPK_01",
                    "confirmed_chat_code": "CHI",
                    "participant_role": "target_child",
                    "disposition": "target",
                    "affected_utterance_ids": ["utt_spk_01_a", "utt_spk_01_b", "utt_spk_01_c"],
                },
                {
                    "temporary_speaker_id": "SPK_02",
                    "confirmed_chat_code": "THE",
                    "participant_role": "therapist",
                    "disposition": "non_target",
                    "affected_utterance_ids": ["utt_spk_02_a"],
                },
                {
                    "temporary_speaker_id": "SPK_03",
                    "confirmed_chat_code": "THE",
                    "participant_role": "therapist",
                    "disposition": "non_target",
                    "affected_utterance_ids": ["utt_spk_03_a"],
                },
            ],
        },
    )
    assert duplicate_role.status_code == 200
    rejected = client.post(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping/confirm",
        json={
            "expected_transcript_version": 1,
            "expected_mapping_version": duplicate_role.json()["mapping_version"],
        },
    )
    assert rejected.status_code == 400
    assert "SPEAKER_MAPPING_AMBIGUOUS_ROLE" in rejected.json()["detail"]


def test_speaker_mapping_blocks_qa_attestation_and_export_until_confirmed(repo):
    transcript_id = _seed_asr_transcript(repo)

    qa_before = client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    assert qa_before.status_code == 200
    assert qa_before.json()["overall_status"] == "FAIL"
    assert any(
        issue["code"] == "SPEAKER_MAPPING_REQUIRED" and issue["blocking"]
        for issue in qa_before.json()["issues"]
    )
    assert qa_before.json()["can_extract_features"] is False

    attest_before = client.post(
        f"/api/v1/transcripts/{transcript_id}/attest",
        json={"override_qa_failure": True, "reason": "Should not override speaker mapping."},
    )
    assert attest_before.status_code == 400
    assert "SPEAKER_MAPPING_REQUIRED" in attest_before.json()["detail"]

    export_before = client.get(f"/api/v1/transcripts/{transcript_id}/export-cha")
    assert export_before.status_code == 400
    assert "SPEAKER_MAPPING_REQUIRED" in export_before.json()["detail"]

    draft = client.put(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping",
        json={"expected_transcript_version": 1, "entries": _mapping_entries()},
    )
    confirmed = client.post(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping/confirm",
        json={
            "expected_transcript_version": 1,
            "expected_mapping_version": draft.json()["mapping_version"],
        },
    )
    assert confirmed.status_code == 200

    qa_after = client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    assert qa_after.status_code == 200
    assert not any(issue["code"] == "SPEAKER_MAPPING_REQUIRED" for issue in qa_after.json()["issues"])
    assert qa_after.json()["can_extract_features"] is True

    attest_after = client.post(
        f"/api/v1/transcripts/{transcript_id}/attest",
        json={"reason": "Mapping and transcript reviewed."},
    )
    assert attest_after.status_code == 200
    assert attest_after.json()["therapist_attested"] is True

    export_after = client.get(f"/api/v1/transcripts/{transcript_id}/export-cha")
    assert export_after.status_code == 200
    assert "*CHI:" in export_after.json()["cha_text"]
    assert "*THE:" in export_after.json()["cha_text"]


def test_speaker_mapping_becomes_stale_after_transcript_edit(repo):
    transcript_id = _seed_asr_transcript(repo)
    draft = client.put(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping",
        json={"expected_transcript_version": 1, "entries": _mapping_entries()},
    )
    confirmed = client.post(
        f"/api/v1/transcripts/{transcript_id}/speaker-mapping/confirm",
        json={
            "expected_transcript_version": 1,
            "expected_mapping_version": draft.json()["mapping_version"],
        },
    )
    assert confirmed.status_code == 200

    patched_utterances = [item.model_dump(mode="json") for item in repo.transcripts[transcript_id].utterances]
    patched_utterances[0]["text"] = "หนูเห็นรถสีแดงมาก"
    patch = client.patch(
        f"/api/v1/transcripts/{transcript_id}",
        json={"utterances": patched_utterances, "reviewer_note": "Edited after mapping."},
    )
    assert patch.status_code == 200

    mapping = client.get(f"/api/v1/transcripts/{transcript_id}/speaker-mapping")
    assert mapping.status_code == 200
    assert mapping.json()["status"] == "stale"
    assert mapping.json()["issues"][0]["code"] == "SPEAKER_MAPPING_STALE"

    qa_after_edit = client.post(f"/api/v1/transcripts/{transcript_id}/qa")
    assert qa_after_edit.status_code == 200
    assert any(
        issue["code"] == "SPEAKER_MAPPING_STALE" and issue["blocking"]
        for issue in qa_after_edit.json()["issues"]
    )


def test_speaker_mapping_blocks_role_dependent_feature_extraction(repo):
    transcript_id = _seed_asr_transcript(repo)
    repo.transcripts[transcript_id].qa_status = QaStatus.pass_
    repo.transcripts[transcript_id].therapist_attested = True

    response = client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", json={})

    assert response.status_code == 400
    assert "SPEAKER_MAPPING_REQUIRED" in response.json()["detail"]


def test_sql_speaker_mapping_confirmation_persists_reviewed_speakers(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'speaker-mapping-confirmation.db'}"
    repo = SqlAlchemyRepository(database_url)
    transcript_id = "transcript_sql_mapping_001"
    session = repo.sessions["session_demo_001"]
    transcript = Transcript(
        transcript_id=transcript_id,
        session_id=session.session_id,
        case_id=session.case_id,
        organization_id=session.organization_id,
        source="asr_draft:local_faster_whisper",
        raw_text="\n".join([
            "@Begin",
            "@Languages:\ttha, eng",
            "@Participants:\tCHI Child Target_Child, THE Therapist Investigator",
            "*SPK_01:\tสวัสดีครับ \x150_1000\x15",
            "*SPK_02:\tช่วยเล่าอีกนิด \x151100_2200\x15",
            "@End",
        ]),
        utterances=[
            Utterance(
                utterance_id="utt_spk_01_a",
                speaker="SPK_01",
                temporary_speaker_id="SPK_01",
                source_speaker_label="speaker_0",
                text="สวัสดีครับ",
                start_ms=0,
                end_ms=1000,
                source="asr",
                review_status="reviewed",
            ),
            Utterance(
                utterance_id="utt_spk_02_a",
                speaker="SPK_02",
                temporary_speaker_id="SPK_02",
                source_speaker_label="speaker_1",
                text="ช่วยเล่าอีกนิด",
                start_ms=1100,
                end_ms=2200,
                source="asr",
                review_status="reviewed",
            ),
        ],
        review_status=ReviewStatus.needs_review,
        version=3,
        raw_speaker_labels=["speaker_0", "speaker_1"],
        asr_provenance={
            "provider_id": "local_faster_whisper",
            "diarization": {
                "provider": "optional_diarizer",
                "clusters": {
                    "SPK_01": {"source_speaker_label": "speaker_0"},
                    "SPK_02": {"source_speaker_label": "speaker_1"},
                },
            },
        },
    )
    repo.create_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="system",
        audit_action="test.transcript.seed",
        audit_message="Seed ASR transcript for speaker-mapping persistence regression.",
    )
    draft = speaker_mapping_service.save_mapping_draft(
        repo,
        transcript_id,
        SpeakerMappingDraftRequest(
            expected_transcript_version=3,
            entries=[
                {
                    "temporary_speaker_id": "SPK_01",
                    "confirmed_chat_code": "CHI",
                    "participant_role": "target_child",
                    "disposition": "target",
                    "affected_utterance_ids": ["utt_spk_01_a"],
                },
                {
                    "temporary_speaker_id": "SPK_02",
                    "confirmed_chat_code": "THE",
                    "participant_role": "therapist",
                    "disposition": "non_target",
                    "affected_utterance_ids": ["utt_spk_02_a"],
                },
            ],
        ),
    )

    speaker_mapping_service.confirm_mapping(
        repo,
        transcript_id,
        SpeakerMappingConfirmRequest(
            expected_transcript_version=3,
            expected_mapping_version=draft.mapping_version,
        ),
        CurrentUser(user_id="therapist-sql", role="therapist"),
    )
    reloaded = SqlAlchemyRepository(database_url)

    assert [utterance.speaker for utterance in reloaded.transcripts[transcript_id].utterances] == ["CHI", "THE"]
    assert "*CHI:\tสวัสดีครับ" in reloaded.transcripts[transcript_id].raw_text
    assert "*THE:\tช่วยเล่าอีกนิด" in reloaded.transcripts[transcript_id].raw_text
    assert "@Participants:\tCHI Child Target_Child, THE Therapist Investigator" in reloaded.transcripts[transcript_id].raw_text
    current_mapping = reloaded.get_current_speaker_mapping(transcript_id)
    assert current_mapping is not None
    assert current_mapping.confirmed_by_user_id == "therapist-sql"
