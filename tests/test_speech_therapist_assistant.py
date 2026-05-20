from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.speech_therapist_assistant import (
    generate_case_brief,
    interpret_progress_summary,
    interpret_screening_result,
    interpret_transcript_review,
)


FORBIDDEN_PHRASES = [
    "วินิจฉัยว่า" + "เป็น ASD",
    "ยืนยันว่า" + "เป็น ASD",
    "diagnosed with " + "ASD",
    "confirmed " + "ASD",
]


def assert_no_forbidden_phrases(text: str) -> None:
    lowered = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase.lower() not in lowered


def high_marker_features() -> dict:
    return {
        "total_utterances": 60,
        "total_words": 80,
        "mlu": 1.2,
        "mluw": 1.4,
        "ttr": 0.2,
        "unintelligible_ratio": 0.22,
        "zero_vocalization_count": 25,
        "echolalia_ratio": 0.1,
        "question_ratio": 0.01,
    }


def test_high_probability_returns_high_concern_without_diagnostic_wording():
    result = interpret_screening_result(high_marker_features(), probability=0.82)

    assert result["concern_level"] == "high"
    assert result["key_patterns"]
    assert "recommend further expert assessment" in result["recommended_next_steps"]
    assert_no_forbidden_phrases(" ".join([
        result["safe_summary_th"],
        result["safe_summary_en"],
        result["disclaimer_th"],
        result["disclaimer_en"],
    ]))


def test_probability_in_uncertainty_band_returns_uncertain():
    result = interpret_screening_result(high_marker_features(), probability=0.45)

    assert result["concern_level"] == "uncertain"
    assert "uncertainty band" in result["safe_summary_en"]


def test_transcript_fail_returns_not_usable():
    review_result = {
        "status": "fail",
        "quality_score": 40,
        "summary": {"marker_counts": {}},
        "issues": [
            {
                "severity": "error",
                "code": "MISSING_CHI_TIER",
                "message": "No child speaker tier was found.",
                "line": None,
                "suggestion": "Add child speaker tiers.",
            }
        ],
    }

    result = interpret_transcript_review(review_result)

    assert result["qa_level"] == "not_usable"
    assert "MISSING_CHI_TIER" in result["main_issues"][0]


def test_progress_with_improved_metrics_returns_improving():
    summary = {
        "child": "Demo",
        "n_sessions": 2,
        "metric_changes": {
            "total_words": {"first": 20, "last": 100, "delta": 80, "improved": True},
            "total_utterances": {"first": 10, "last": 50, "delta": 40, "improved": True},
            "mlu": {"first": 1.0, "last": 2.0, "delta": 1.0, "improved": True},
            "unintelligible_ratio": {"first": 0.4, "last": 0.1, "delta": -0.3, "improved": True},
        },
    }

    result = interpret_progress_summary(summary)

    assert result["progress_direction"] == "improving"
    assert result["positive_changes"]


def test_single_session_progress_is_insufficient_data():
    result = interpret_progress_summary({
        "child": "Demo",
        "n_sessions": 1,
        "metric_changes": {},
    })

    assert result["progress_direction"] == "insufficient_data"


def test_generated_case_brief_contains_disclaimer_and_no_forbidden_phrases():
    brief = generate_case_brief(
        features=high_marker_features(),
        probability=0.82,
        transcript_review={"status": "pass", "issues": [], "quality_score": 98},
        progress_summary={
            "child": "Demo",
            "n_sessions": 2,
            "metric_changes": {
                "total_words": {
                    "first": 20,
                    "last": 100,
                    "delta": 80,
                    "improved": True,
                }
            },
        },
        language="en",
    )

    assert "Safety disclaimer" in brief
    assert "human-in-the-loop" in brief
    assert_no_forbidden_phrases(brief)
