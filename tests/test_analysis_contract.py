from datetime import datetime, timezone

import pytest

from packages.analysis_contract import (
    AnalysisInput,
    AnalysisInputKind,
    AnalysisProvenance,
    AnalysisRequest,
    AnalysisResult,
    AnalysisStatus,
)


def _input() -> AnalysisInput:
    return AnalysisInput(
        input_ref="opaque-input-001",
        input_kind=AnalysisInputKind.REVIEWED_TRANSCRIPT,
        session_ref="opaque-session-001",
        transcript_version=3,
        content_sha256="a" * 64,
    )


def _provenance() -> AnalysisProvenance:
    return AnalysisProvenance(
        pipeline_version="transcript-features-v1",
        feature_schema_version="14-feature-schema",
        model_version="reference-evidence-v1",
        analyzed_at=datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        input_ref="opaque-input-001",
        session_ref="opaque-session-001",
    )


def test_request_serializes_only_analysis_inputs_and_versions():
    payload = AnalysisRequest(
        input=_input(),
        pipeline_version="transcript-features-v1",
        feature_schema_version="14-feature-schema",
    ).to_dict()

    assert payload["contract_version"] == "analysis-contract-v1"
    assert payload["input"]["input_kind"] == "reviewed_transcript"
    assert "organization_id" not in payload
    assert "authorization" not in payload
    assert "storage_key" not in payload


def test_completed_result_requires_provenance_and_is_non_diagnostic():
    result = AnalysisResult(
        status=AnalysisStatus.COMPLETED,
        provenance=_provenance(),
        feature_values={"total_words": 12, "question_ratio": 0.25},
    )

    payload = result.to_dict()
    assert payload["provenance"]["model_version"] == "reference-evidence-v1"
    assert payload["not_diagnostic"] is True
    assert payload["decision_support_only"] is True


def test_unavailable_result_requires_abstention_and_cannot_include_values():
    result = AnalysisResult(
        status=AnalysisStatus.INSUFFICIENT_DATA,
        provenance=_provenance(),
        abstention_reason="Transcript does not contain enough reviewed speech.",
    )

    assert result.to_dict()["feature_values"] == {}

    with pytest.raises(ValueError, match="abstention_reason"):
        AnalysisResult(status=AnalysisStatus.FAILED, provenance=_provenance())

    with pytest.raises(ValueError, match="must not include feature values"):
        AnalysisResult(
            status=AnalysisStatus.FAILED,
            provenance=_provenance(),
            feature_values={"total_words": 1},
            abstention_reason="Pipeline failed.",
        )


def test_contract_rejects_naive_timestamps_and_invalid_references():
    with pytest.raises(ValueError, match="timezone-aware"):
        AnalysisProvenance(
            pipeline_version="pipeline-v1",
            feature_schema_version="features-v1",
            analyzed_at=datetime(2026, 8, 13),
            input_ref="input",
            session_ref="session",
        )

    with pytest.raises(ValueError, match="opaque reference"):
        AnalysisInput(
            input_ref="\nraw",
            input_kind=AnalysisInputKind.AUDIO_ASSET,
            session_ref="session",
        )
