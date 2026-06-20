from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.clinical import (
    EvidenceAvailability,
    EvidenceReviewPatch,
    FeatureSet,
    FeatureValue,
    MLReviewRequest,
    PatternEvidence,
    ProfileEvidence,
    ReviewStatus,
    Transcript,
)
from app.repositories.mock_repository import MockRepository
from app.services.ml_providers.base import (
    BaseMLProvider,
    MLProviderAvailability,
    MLProviderContext,
    MLProviderResult,
)
from app.services.ml_providers.registry import ml_provider_registry
from app.services.ml_review_service import create_ml_review


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
