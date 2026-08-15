from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from packages.analysis_contract import (
    AnalysisInput,
    AnalysisInputKind,
    AnalysisRequest,
    AnalysisStatus,
    FEATURE_DEFINITION_VERSION,
    TRANSCRIPT_QA_VERSION,
    TRANSCRIPT_PIPELINE_VERSION,
    TranscriptQualityCode,
    TranscriptQualityKind,
    analyze_reviewed_chat,
    tokenize_reviewed_text,
    transcript_analysis_profile,
)
from packages.cha import (
    parse_cha_text,
    semantic_cha_checksum,
    serialize_cha_subset,
    verify_cha_round_trip,
)


FIXTURES = Path(__file__).parent / "fixtures" / "analysis_contract"


def _request(
    *,
    pipeline_version: str = TRANSCRIPT_PIPELINE_VERSION,
    content_sha256: str | None = None,
) -> AnalysisRequest:
    return AnalysisRequest(
        input=AnalysisInput(
            input_ref="opaque-transcript-001",
            input_kind=AnalysisInputKind.REVIEWED_TRANSCRIPT,
            session_ref="opaque-session-001",
            transcript_version=1,
            content_sha256=content_sha256,
        ),
        pipeline_version=pipeline_version,
        feature_schema_version=FEATURE_DEFINITION_VERSION,
    )


def test_chat_subset_round_trip_preserves_semantics_and_is_byte_stable():
    source = (FIXTURES / "synthetic_thai.cha").read_text(encoding="utf-8")
    parsed = parse_cha_text(source, file_id="synthetic")

    export_a = serialize_cha_subset(parsed)
    reparsed = parse_cha_text(export_a, file_id="synthetic")
    export_b = serialize_cha_subset(reparsed)

    assert semantic_cha_checksum(parsed) == semantic_cha_checksum(reparsed)
    assert export_a == export_b
    verification = verify_cha_round_trip(source, file_id="synthetic")
    assert verification.ok is True
    assert verification.issues == ()


def test_chat_subset_round_trip_preserves_dependent_tiers_and_order():
    source = (FIXTURES / "synthetic_thai.cha").read_text(encoding="utf-8")
    verification = verify_cha_round_trip(source, file_id="synthetic")

    assert [item.speaker_code for item in verification.document.utterances] == ["INV", "CHI", "CHI"]
    assert verification.document.utterances[1].dependent_tiers == {
        "com": ["synthetic reviewed utterance"]
    }


def test_dependent_tier_continuation_does_not_contaminate_child_speech():
    source = """@UTF8
@Begin
@Languages:\ttha
@Participants:\tCHI Target_Child Target_Child
*CHI:\tเอาของเล่นค่ะ .
%com:\tfirst note
\tcontinued note
@End
"""

    verification = verify_cha_round_trip(source, file_id="synthetic")
    utterance = verification.document.utterances[0]

    assert verification.ok is True
    assert utterance.normalized_text == "เอาของเล่นค่ะ"
    assert utterance.dependent_tiers == {"com": ["first note continued note"]}


def test_profile_checksum_and_descriptive_features_are_deterministic():
    profile_a = transcript_analysis_profile()
    profile_b = transcript_analysis_profile()

    assert profile_a.profile_checksum_sha256 == profile_b.profile_checksum_sha256
    assert len(profile_a.profile_checksum_sha256) == 64
    assert len(profile_a.tokenizer_vocabulary_checksum_sha256) == 64
    assert profile_a.feature_definition_version == FEATURE_DEFINITION_VERSION
    assert profile_a.quality_rule_version == TRANSCRIPT_QA_VERSION
    assert "diagnosis" not in " ".join(profile_a.feature_names).lower()

    source = (FIXTURES / "synthetic_mixed.cha").read_text(encoding="utf-8")
    analyzed_at = datetime(2026, 8, 16, 4, 0, tzinfo=timezone.utc)
    first = analyze_reviewed_chat(_request(), source, analyzed_at=analyzed_at)
    second = analyze_reviewed_chat(_request(), source, analyzed_at=analyzed_at)

    assert first.status is AnalysisStatus.COMPLETED
    assert first.feature_values == second.feature_values
    assert first.feature_values["child_utterance_count"] == 2
    assert first.feature_values["child_token_count"] == 6
    assert first.provenance.pipeline_version == TRANSCRIPT_PIPELINE_VERSION
    assert first.provenance.feature_schema_version == FEATURE_DEFINITION_VERSION
    assert (
        first.feature_values["analysis_profile_checksum_sha256"]
        == profile_a.profile_checksum_sha256
    )


def test_quality_types_fail_closed_without_child_speech():
    source = """@UTF8
@Begin
@Languages:\ttha
@Participants:\tINV Adult Investigator
*INV:\tสวัสดีค่ะ . \x150_900\x15
@End
"""

    result = analyze_reviewed_chat(
        _request(),
        source,
        analyzed_at=datetime(2026, 8, 16, 4, 0, tzinfo=timezone.utc),
    )

    assert result.status is AnalysisStatus.INSUFFICIENT_DATA
    assert result.feature_values == {}
    assert TranscriptQualityCode.NO_CHILD_UTTERANCES.value in result.abstention_reason
    profile = transcript_analysis_profile()
    issue = profile.quality_issue(TranscriptQualityCode.NO_CHILD_UTTERANCES)
    assert issue.kind is TranscriptQualityKind.BLOCKER


def test_missing_required_chat_structure_blocks_descriptors():
    source = """@UTF8
@Begin
@Languages:\ttha
@Participants:\tCHI Target_Child Target_Child
*CHI:\tเอาของเล่นค่ะ . \x150_900\x15
"""

    result = analyze_reviewed_chat(
        _request(),
        source,
        analyzed_at=datetime(2026, 8, 16, 4, 0, tzinfo=timezone.utc),
    )

    assert result.status is AnalysisStatus.INSUFFICIENT_DATA
    assert result.feature_values == {}
    assert TranscriptQualityCode.CHAT_STRUCTURE_INVALID.value in result.abstention_reason


def test_unintelligible_only_child_sample_is_insufficient_data():
    source = """@UTF8
@Begin
@Languages:\ttha
@Participants:\tCHI Target_Child Target_Child
*CHI:\txxx . \x150_900\x15
*CHI:\t0 . \x151000_1600\x15
@End
"""

    result = analyze_reviewed_chat(
        _request(),
        source,
        analyzed_at=datetime(2026, 8, 16, 4, 0, tzinfo=timezone.utc),
    )

    assert result.status is AnalysisStatus.INSUFFICIENT_DATA
    assert result.feature_values == {}
    assert TranscriptQualityCode.NO_CHILD_CONTENT.value in result.abstention_reason


def test_version_mismatch_fails_without_returning_partial_features():
    source = (FIXTURES / "synthetic_thai.cha").read_text(encoding="utf-8")

    result = analyze_reviewed_chat(
        _request(pipeline_version="unexpected-pipeline"),
        source,
        analyzed_at=datetime(2026, 8, 16, 4, 0, tzinfo=timezone.utc),
    )

    assert result.status is AnalysisStatus.FAILED
    assert result.feature_values == {}
    assert TranscriptQualityCode.PROFILE_VERSION_MISMATCH.value in result.abstention_reason


def test_input_content_checksum_mismatch_fails_closed():
    source = (FIXTURES / "synthetic_thai.cha").read_text(encoding="utf-8")

    result = analyze_reviewed_chat(
        _request(content_sha256="a" * 64),
        source,
        analyzed_at=datetime(2026, 8, 16, 4, 0, tzinfo=timezone.utc),
    )

    assert result.status is AnalysisStatus.FAILED
    assert result.feature_values == {}
    assert TranscriptQualityCode.INPUT_CHECKSUM_MISMATCH.value in result.abstention_reason


def test_short_sample_is_a_limitation_not_a_diagnostic_conclusion():
    source = """@UTF8
@Begin
@Languages:\ttha
@Participants:\tCHI Target_Child Target_Child
*CHI:\tเอาของเล่นค่ะ . \x150_900\x15
@End
"""

    result = analyze_reviewed_chat(
        _request(),
        source,
        analyzed_at=datetime(2026, 8, 16, 4, 0, tzinfo=timezone.utc),
    )

    assert result.status is AnalysisStatus.COMPLETED
    assert TranscriptQualityCode.SHORT_SAMPLE.value in result.warnings
    assert result.not_diagnostic is True
    assert result.decision_support_only is True


def test_out_of_order_segments_block_feature_calculation():
    source = """@UTF8
@Begin
@Languages:\ttha
@Participants:\tCHI Target_Child Target_Child
*CHI:\tเอาของเล่นค่ะ . \x151000_1800\x15
*CHI:\tไม่เอาค่ะ . \x15500_900\x15
@End
"""

    result = analyze_reviewed_chat(
        _request(),
        source,
        analyzed_at=datetime(2026, 8, 16, 4, 0, tzinfo=timezone.utc),
    )

    assert result.status is AnalysisStatus.INSUFFICIENT_DATA
    assert result.feature_values == {}
    assert TranscriptQualityCode.TIMESTAMP_ORDER_INVALID.value in result.abstention_reason


def test_unknown_adult_speaker_is_explicit_and_never_contaminates_child_features():
    source = """@UTF8
@Begin
@Languages:\ttha
@Participants:\tCHI Target_Child Target_Child, XYZ Adult Other
*XYZ:\tคำของผู้ใหญ่ไม่ถูกนับ . \x150_800\x15
*CHI:\tเอาของเล่นค่ะ . \x15900_1800\x15
*CHI:\tไม่เอาค่ะ . \u0015920_2600\u0015
@End
"""

    result = analyze_reviewed_chat(
        _request(),
        source,
        analyzed_at=datetime(2026, 8, 16, 4, 0, tzinfo=timezone.utc),
    )

    assert result.status is AnalysisStatus.COMPLETED
    assert TranscriptQualityCode.UNMAPPED_SPEAKER.value in result.warnings
    assert result.feature_values["child_utterance_count"] == 2
    assert "ผู้ใหญ่" not in tokenize_reviewed_text(
        "เอาของเล่นค่ะ ไม่เอาค่ะ"
    )
    assert result.feature_values["child_token_count"] == 6
