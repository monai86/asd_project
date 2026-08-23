from __future__ import annotations

import csv
from dataclasses import replace
import hashlib
import json
import time

import numpy
import pytest
from pydantic import ValidationError

from app.schemas.clinical import (
    EvidenceAvailability,
    EvidenceReviewPatch,
    FeatureSet,
    FeatureValue,
    MLReviewRequest,
    OrganizationMembershipCreate,
    PatternEvidence,
    ProfileEvidence,
    ReviewStatus,
    Transcript,
    TranscriptPatch,
    Utterance,
)
from app.repositories.mock_repository import JsonFileRepository, MockRepository
from app.core.security import CurrentUser
from app.services.ml_providers.base import (
    BaseMLProvider,
    MLProviderAvailability,
    MLProviderContext,
    MLProviderResult,
)
from app.services.ml_providers.reference_evidence import ReferenceEvidenceProvider
from app.services.ml_providers.reference_feature_adapter import adapt_runtime_features
from app.services.ml_providers.registry import ml_provider_registry
from app.services.consent_service import withdraw_consent
from app.services.ml_review_service import (
    create_ml_review,
    get_ml_result,
    patch_profile_evidence_state,
)
from app.services.transcript_service import patch_transcript
from app.services.report_service import draft_report


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_reference_artifact(tmp_path):
    artifact_dir = tmp_path / "reference-evidence"
    artifact_dir.mkdir()
    cells_path = artifact_dir / "reference_cells.csv"
    fieldnames = [
        "language",
        "age_band_12mo",
        "task_type",
        "original_group",
        "presentation_group",
        "participant_count",
        "corpus_count",
        "supported",
        "reason_code",
    ]
    for feature in (
        "total_utterances",
        "total_words",
        "ttr",
        "mluw",
        "unintelligible_ratio",
        "question_ratio",
        "echolalia_count",
        "pronoun_reversal_count",
    ):
        fieldnames.extend(
            [f"{feature}_q1", f"{feature}_median", f"{feature}_q3"]
        )
    rows = []
    for group, presentation, supported, participants, corpora in (
        ("TD", "TD", True, 32, 2),
        ("ASD", "ASD", False, 17, 1),
        ("STI", "OTHER", False, 12, 1),
    ):
        row = {
            "language": "eng",
            "age_band_12mo": "60-71",
            "task_type": "toyplay",
            "original_group": group,
            "presentation_group": presentation,
            "participant_count": participants,
            "corpus_count": corpora,
            "supported": supported,
            "reason_code": "" if supported else "insufficient_participants",
        }
        for feature in (
            "total_utterances",
            "total_words",
            "ttr",
            "mluw",
            "unintelligible_ratio",
            "question_ratio",
            "echolalia_count",
            "pronoun_reversal_count",
        ):
            row[f"{feature}_q1"] = 1
            row[f"{feature}_median"] = 2
            row[f"{feature}_q3"] = 3
        rows.append(row)
    with cells_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "artifact_type": "ml_reference_evidence",
        "artifact_version": "test-v1",
        "dataset_hash": "test-dataset-hash",
        "feature_schema_version": "reference-core-14-v1",
        "supported_language": "eng",
        "gate1": {"status": "research_only"},
        "files": {
            "reference_cells": {
                "filename": cells_path.name,
                "sha256": _sha256(cells_path),
                "size_bytes": cells_path.stat().st_size,
            }
        },
    }
    (artifact_dir / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    return artifact_dir


def _reference_feature_set():
    return FeatureSet(
        feature_set_id="features_reference_test",
        session_id="session_reference_test",
        transcript_id="transcript_reference_test",
        transcript_version=1,
        therapist_attested=True,
        features=[
            FeatureValue(name="child_utterance_count", value=10),
            FeatureValue(name="adult_utterance_count", value=4),
            FeatureValue(name="total_word_count", value=24),
            FeatureValue(name="type_token_ratio", value=0.6),
            FeatureValue(name="mean_length_of_utterance_words", value=2.4),
            FeatureValue(name="unintelligible_ratio", value=0.1),
            FeatureValue(name="question_ratio", value=0.2),
            FeatureValue(name="echolalia_cue_count", value=0),
            FeatureValue(name="pronoun_reversal_cue_count", value=0),
        ],
    )


def _reference_context():
    return MLProviderContext(
        case_id="case_reference_test",
        session_id="session_reference_test",
        transcript_id="transcript_reference_test",
        age_months=62,
        language="English",
        session_type="therapy_session",
        task_type=None,
    )


def _prepared_ml_repo():
    repo = MockRepository()
    for user_id, role in (
        ("therapist-reviewer", "therapist"),
        ("supervisor-reviewer", "clinical_supervisor"),
        ("org-admin-reviewer", "org_admin"),
    ):
        repo.upsert_membership(
            "pilot_org_001",
            OrganizationMembershipCreate(
                user_id=user_id, display_name=user_id, role=role
            ),
            actor_id="seed",
        )
    case = repo.cases["case_demo_001"]
    session = repo.sessions["session_demo_001"]
    transcript = Transcript(
        transcript_id="transcript_boundary_test",
        session_id=session.session_id,
        case_id=case.case_id,
        source="manual",
        raw_text="@Begin\n@Languages:\teng\n*CHI:\tblue car .\n@End",
        utterances=[
            Utterance(utterance_id="utt_boundary_1", speaker="CHI", text="blue car")
        ],
        therapist_attested=True,
        review_status=ReviewStatus.attested,
    )
    feature_set = _reference_feature_set().model_copy(
        update={
            "feature_set_id": "features_boundary_test",
            "session_id": session.session_id,
            "transcript_id": transcript.transcript_id,
        }
    )
    repo.transcripts[transcript.transcript_id] = transcript
    repo.features[feature_set.feature_set_id] = feature_set
    session.transcript_id = transcript.transcript_id
    session.feature_set_id = feature_set.feature_set_id
    return repo, case, session, transcript


def _created_reference_result(tmp_path):
    repo, _, _, transcript = _prepared_ml_repo()
    provider = ReferenceEvidenceProvider(_write_reference_artifact(tmp_path))
    previous = ml_provider_registry.providers.get(provider.provider_id)
    ml_provider_registry.register(provider)
    try:
        result = create_ml_review(
            repo,
            transcript.transcript_id,
            MLReviewRequest(provider_id=provider.provider_id),
        )
    finally:
        if previous is None:
            ml_provider_registry.providers.pop(provider.provider_id, None)
        else:
            ml_provider_registry.register(previous)
    return repo, result


def test_evidence_models_do_not_require_scores():
    profile = ProfileEvidence(
        profile_code="ASD",
        presentation_group="ASD",
        status="not_available",
        availability=EvidenceAvailability(
            state="insufficient_reference_data",
            reason_code="insufficient_participants",
            message="This public-corpus profile does not have enough independent participants.",
            workflow_can_continue=True,
        ),
        participant_count=17,
        corpus_count=1,
    )

    payload = profile.model_dump()
    assert payload.get("probability") is None
    assert payload.get("score") is None
    assert payload["associated_features"] == []


def test_pattern_evidence_can_be_unavailable_without_blocking_workflow():
    evidence = PatternEvidence(
        status="not_available",
        availability=EvidenceAvailability(
            state="unsupported_scope",
            reason_code="unsupported_language",
            message="Reference evidence is currently limited to English samples.",
            workflow_can_continue=True,
            next_step="Continue the therapist review without reference evidence.",
        ),
    )

    assert evidence.availability.workflow_can_continue is True
    assert evidence.associated_features == []


def test_disagreement_requires_therapist_note():
    with pytest.raises(ValidationError, match="therapist note is required"):
        EvidenceReviewPatch(status="disagreement")

    patch = EvidenceReviewPatch(
        status="disagreement",
        therapist_note="The observed interaction context does not support this cue.",
    )
    assert patch.status == "disagreement"


def test_review_service_builds_provider_context_from_persisted_records():
    class CapturingProvider(BaseMLProvider):
        provider_id = "capturing_reference_test"
        provider_name = "CapturingReferenceTestProvider"
        provider_version = "test"

        def __init__(self):
            self.context: MLProviderContext | None = None

        def check_availability(self) -> MLProviderAvailability:
            return MLProviderAvailability(True)

        def get_model_metadata(self) -> dict:
            return {"default_config": {}}

        def predict(self, features, context, config=None) -> MLProviderResult:
            self.context = context
            return MLProviderResult(status="completed")

    repo = MockRepository()
    case = repo.cases["case_demo_001"]
    session = repo.sessions["session_demo_001"]
    case.age_months = 71
    case.language = "English"
    session.session_type = "structured_assessment"
    transcript = Transcript(
        transcript_id="transcript_context_test",
        session_id=session.session_id,
        case_id=case.case_id,
        source="manual",
        raw_text="*CHI:\tblue car .",
        therapist_attested=True,
        review_status=ReviewStatus.attested,
        chat_metadata={"task_type": "narrative"},
    )
    feature_set = FeatureSet(
        feature_set_id="features_context_test",
        session_id=session.session_id,
        transcript_id=transcript.transcript_id,
        transcript_version=transcript.version,
        therapist_attested=True,
        features=[
            FeatureValue(name="child_utterance_count", value=3),
            FeatureValue(name="adult_utterance_count", value=1),
            FeatureValue(name="total_word_count", value=6),
        ],
    )
    repo.transcripts[transcript.transcript_id] = transcript
    repo.features[feature_set.feature_set_id] = feature_set
    session.transcript_id = transcript.transcript_id
    session.feature_set_id = feature_set.feature_set_id
    provider = CapturingProvider()
    ml_provider_registry.register(provider)
    try:
        create_ml_review(
            repo,
            transcript.transcript_id,
            MLReviewRequest(provider_id=provider.provider_id),
        )
    finally:
        ml_provider_registry.providers.pop(provider.provider_id, None)

    assert provider.context == MLProviderContext(
        case_id=case.case_id,
        session_id=session.session_id,
        transcript_id=transcript.transcript_id,
        age_months=71,
        language="English",
        session_type="structured_assessment",
        task_type="narrative",
    )


def test_provider_is_unavailable_when_manifest_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("THERAPIST_APP_V2_REFERENCE_ARTIFACT_DIR", str(tmp_path))
    provider = ReferenceEvidenceProvider()

    availability = provider.check_availability()

    assert availability.available is False
    assert "manifest" in availability.reason.lower()


def test_provider_rejects_checksum_mismatch(tmp_path):
    artifact_dir = _write_reference_artifact(tmp_path)
    (artifact_dir / "reference_cells.csv").write_text("tampered", encoding="utf-8")

    provider = ReferenceEvidenceProvider(artifact_dir)

    assert provider.check_availability().available is False
    assert "checksum mismatch" in provider.check_availability().reason.lower()


def test_feature_adapter_never_substitutes_zero_for_missing_values():
    feature_set = _reference_feature_set()
    feature_set.features = [
        item for item in feature_set.features if item.name != "question_ratio"
    ]

    adapted = adapt_runtime_features(feature_set)

    assert "question_ratio" not in adapted.values
    assert "question_ratio" in adapted.missing_required


def test_provider_rejects_incompatible_runtime_feature_schema(tmp_path):
    provider = ReferenceEvidenceProvider(_write_reference_artifact(tmp_path))
    feature_set = _reference_feature_set()
    feature_set.schema_version = "unknown-feature-schema"

    result = provider.predict(feature_set, _reference_context())

    assert result.status == "unavailable"
    assert result.profile_evidence == []
    assert result.pattern_evidence is not None
    assert (
        result.pattern_evidence.availability.reason_code
        == "feature_schema_incompatible"
    )


def test_provider_returns_profile_abstention_without_scores(tmp_path):
    provider = ReferenceEvidenceProvider(_write_reference_artifact(tmp_path))

    result = provider.predict(_reference_feature_set(), _reference_context())

    assert result.status == "completed"
    assert result.pattern_evidence is not None
    assert result.pattern_evidence.availability.reason_code == "gate1_research_only"
    assert [profile.profile_code for profile in result.profile_evidence] == [
        "TD",
        "ASD",
        "STI",
    ]
    td, asd, sti = result.profile_evidence
    assert td.status == "comparable_patterns_observed"
    assert len(td.associated_features) <= 3
    assert asd.status == "not_available"
    assert asd.associated_features == []
    assert sti.presentation_group == "OTHER"
    assert result.artifact_provenance["artifact_version"] == "test-v1"


def test_local_provider_p95_latency_is_within_budget(tmp_path):
    provider = ReferenceEvidenceProvider(_write_reference_artifact(tmp_path))
    feature_set = _reference_feature_set()
    context = _reference_context()
    durations = []
    for _ in range(100):
        started = time.perf_counter()
        provider.predict(feature_set, context)
        durations.append((time.perf_counter() - started) * 1000)

    assert numpy.percentile(durations, 95) <= 500


def test_thai_sample_returns_unsupported_scope_without_profile_evidence(tmp_path):
    provider = ReferenceEvidenceProvider(_write_reference_artifact(tmp_path))
    context = replace(_reference_context(), language="Thai")

    result = provider.predict(_reference_feature_set(), context)

    assert result.profile_evidence == []
    assert result.pattern_evidence is not None
    assert result.pattern_evidence.availability.state == "unsupported_scope"
    assert result.pattern_evidence.availability.reason_code == "unsupported_language"


def test_code_switched_sample_returns_explicit_unsupported_scope(tmp_path):
    provider = ReferenceEvidenceProvider(_write_reference_artifact(tmp_path))
    context = replace(_reference_context(), language="eng,tha")

    result = provider.predict(_reference_feature_set(), context)

    assert result.profile_evidence == []
    assert result.pattern_evidence is not None
    assert (
        result.pattern_evidence.availability.reason_code
        == "unsupported_code_switching"
    )


def test_readiness_issues_cover_unsupported_task_and_age(tmp_path):
    provider = ReferenceEvidenceProvider(_write_reference_artifact(tmp_path))
    context = replace(
        _reference_context(),
        age_months=24,
        session_type="unknown_activity",
    )

    codes = {
        code
        for code, _ in provider.readiness_issues(_reference_feature_set(), context)
    }

    assert "unsupported_task_type" in codes
    assert "age_outside_reference_coverage" in codes


def test_transcript_edit_marks_current_result_stale_but_keeps_restricted_history():
    repo, _, session, transcript = _prepared_ml_repo()
    result = create_ml_review(repo, transcript.transcript_id, MLReviewRequest())

    patch_transcript(
        repo,
        transcript.transcript_id,
        TranscriptPatch(
            utterances=[
                Utterance(
                    utterance_id="utt_boundary_1",
                    speaker="CHI",
                    text="changed language sample",
                )
            ]
        ),
    )

    # The session keeps provenance to the restricted historical result while
    # current-result reads reject it through the explicit stale marker.
    assert session.ml_result_id == result.result_id
    assert result.result_id in repo.ml_results
    assert get_ml_result(repo, result.result_id).is_current is False


def test_consent_withdrawal_removes_results_without_sensitive_audit_content():
    repo, case, session, transcript = _prepared_ml_repo()
    result = create_ml_review(repo, transcript.transcript_id, MLReviewRequest())

    withdrawal = withdraw_consent(
        repo,
        case.case_id,
        reason="Private guardian narrative that must not enter audit logs.",
    )

    assert withdrawal.affected_records["ml_results"] == 1
    assert result.result_id not in repo.ml_results
    # Withdrawal publishes a staged aggregate only after the durable mutation
    # succeeds, so callers must observe the authoritative repository object.
    assert repo.sessions[session.session_id].ml_result_id is None
    audit_text = " ".join(item["message"] for item in repo.audit_log)
    assert "Private guardian narrative" not in audit_text
    assert "blue car" not in audit_text


def test_reviewed_means_read_not_endorsed(tmp_path):
    repo, _, _, transcript = _prepared_ml_repo()
    provider = ReferenceEvidenceProvider(_write_reference_artifact(tmp_path))
    previous = ml_provider_registry.providers.get(provider.provider_id)
    ml_provider_registry.register(provider)
    try:
        result = create_ml_review(
            repo,
            transcript.transcript_id,
            MLReviewRequest(provider_id=provider.provider_id),
        )
    finally:
        if previous is None:
            ml_provider_registry.providers.pop(provider.provider_id, None)
        else:
            ml_provider_registry.register(previous)

    updated = patch_profile_evidence_state(
        repo,
        result.result_id,
        "TD",
        EvidenceReviewPatch(status="reviewed"),
        CurrentUser(
            user_id="therapist-reviewer",
            role="therapist",
            display_name="Review Therapist",
        ),
    )
    td = next(item for item in updated.profile_evidence if item.profile_code == "TD")

    assert td.review_state.status == "reviewed"
    assert td.review_state.therapist_note == ""
    assert td.review_state.reviewed_by == "therapist-reviewer"


def test_clinical_supervisor_can_review_ml_profiles(tmp_path):
    repo, _, _, transcript = _prepared_ml_repo()
    provider = ReferenceEvidenceProvider(_write_reference_artifact(tmp_path))
    previous = ml_provider_registry.providers.get(provider.provider_id)
    ml_provider_registry.register(provider)
    try:
        result = create_ml_review(
            repo,
            transcript.transcript_id,
            MLReviewRequest(provider_id=provider.provider_id),
        )
    finally:
        if previous is None:
            ml_provider_registry.providers.pop(provider.provider_id, None)
        else:
            ml_provider_registry.register(previous)

    updated = patch_profile_evidence_state(
        repo,
        result.result_id,
        "TD",
        EvidenceReviewPatch(status="reviewed"),
        CurrentUser(
            user_id="supervisor-reviewer",
            role="clinical_supervisor",
            display_name="Clinical Supervisor",
        ),
    )

    td = next(item for item in updated.profile_evidence if item.profile_code == "TD")
    assert td.review_state.status == "reviewed"
    assert td.review_state.reviewed_by == "supervisor-reviewer"


def test_org_admin_cannot_review_ml_profiles_without_clinical_role(tmp_path):
    repo, _, _, transcript = _prepared_ml_repo()
    provider = ReferenceEvidenceProvider(_write_reference_artifact(tmp_path))
    previous = ml_provider_registry.providers.get(provider.provider_id)
    ml_provider_registry.register(provider)
    try:
        result = create_ml_review(
            repo,
            transcript.transcript_id,
            MLReviewRequest(provider_id=provider.provider_id),
        )
    finally:
        if previous is None:
            ml_provider_registry.providers.pop(provider.provider_id, None)
        else:
            ml_provider_registry.register(previous)

    with pytest.raises(PermissionError, match="Therapist or clinical supervisor role required."):
        patch_profile_evidence_state(
            repo,
            result.result_id,
            "TD",
            EvidenceReviewPatch(status="reviewed"),
            CurrentUser(
                user_id="org-admin-reviewer",
                role="org_admin",
                display_name="Org Admin",
            ),
        )


def test_profile_disagreement_persists_note_and_does_not_delete_output(tmp_path):
    repo, _, _, transcript = _prepared_ml_repo()
    provider = ReferenceEvidenceProvider(_write_reference_artifact(tmp_path))
    previous = ml_provider_registry.providers.get(provider.provider_id)
    ml_provider_registry.register(provider)
    try:
        result = create_ml_review(
            repo,
            transcript.transcript_id,
            MLReviewRequest(provider_id=provider.provider_id),
        )
    finally:
        if previous is None:
            ml_provider_registry.providers.pop(provider.provider_id, None)
        else:
            ml_provider_registry.register(previous)

    updated = patch_profile_evidence_state(
        repo,
        result.result_id,
        "TD",
        EvidenceReviewPatch(
            status="disagreement",
            therapist_note="Interaction context does not support this comparison.",
        ),
        CurrentUser(),
    )
    td = next(item for item in updated.profile_evidence if item.profile_code == "TD")

    assert td.review_state.status == "disagreement"
    assert td.review_state.therapist_note.startswith("Interaction context")
    assert td.associated_features


def test_evidence_result_round_trips_through_json_repository(tmp_path):
    source, result = _created_reference_result(tmp_path)
    path = tmp_path / "repo.json"
    repo = JsonFileRepository(path)
    repo.cases = source.cases
    repo.sessions = source.sessions
    repo.transcripts = source.transcripts
    repo.features = source.features
    repo.ml_results = source.ml_results
    repo.audit_log = source.audit_log
    repo.save()

    loaded = JsonFileRepository(path)

    assert loaded.ml_results[result.result_id] == source.ml_results[result.result_id]
    assert loaded.sessions[result.session_id].ml_result_id == result.result_id


def test_evidence_result_round_trips_through_sqlite_repository(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    source, result = _created_reference_result(tmp_path)
    database_url = f"sqlite:///{tmp_path / 'reference-evidence.db'}"
    repo = SqlAlchemyRepository(database_url)
    transcript = source.transcripts[result.transcript_id]
    repo.create_transcript(
        transcript,
        session_status=transcript.review_status,
        actor_id="system",
        audit_action="transcript.create",
        audit_message="Synthetic evidence transcript persisted.",
    )
    feature_set = source.features[result.feature_result_id]
    repo.create_feature_set(
        feature_set,
        actor_id="system",
        audit_action="features.create",
        audit_message="Synthetic evidence features persisted.",
    )
    repo.create_ml_result(
        result,
        actor_id="system",
        audit_action="ml.create",
        audit_message="Synthetic reference evidence persisted.",
    )

    loaded = SqlAlchemyRepository(database_url)

    assert loaded.ml_results[result.result_id] == source.ml_results[result.result_id]
    assert loaded.sessions[result.session_id].ml_result_id == result.result_id


def test_evidence_audit_log_contains_no_transcript_or_raw_features(tmp_path):
    repo, result = _created_reference_result(tmp_path)
    patch_profile_evidence_state(
        repo,
        result.result_id,
        "TD",
        EvidenceReviewPatch(status="reviewed"),
        CurrentUser(),
    )

    serialized = json.dumps(repo.audit_log).lower()

    assert "blue car" not in serialized
    assert "total_word_count" not in serialized
    assert "observed_value" not in serialized


def test_report_draft_does_not_include_reference_evidence_automatically(tmp_path):
    repo, result = _created_reference_result(tmp_path)

    report = draft_report(
        repo,
        result.session_id,
        report_type="Clinical Summary",
    )
    text = report.markdown.lower()

    assert "comparable patterns observed" not in text
    assert "public-corpus profile" not in text
    assert "reference evidence" not in text
