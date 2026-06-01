from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.transcript_reviewer import review_cha_text


VALID_CHAT = """@Begin
@Languages:\teng
@Participants:\tCHI Child Target_Child, MOT Mother Mother
@ID:\teng|Test|CHI|4;00.00|male|||Target_Child|||
@ID:\teng|Test|MOT|||||Mother|||
*CHI:\thello .
*MOT:\tyes .
@End
"""


def issue_codes(result: dict) -> set[str]:
    return {issue["code"] for issue in result["issues"]}


def test_valid_minimal_chat_passes_structure_checks():
    result = review_cha_text(VALID_CHAT)

    assert result["status"] in {"pass", "needs_review"}
    assert result["quality_score"] >= 85
    assert result["summary"]["utterance_count"] == 2
    assert result["summary"]["child_utterance_count"] == 1
    assert not issue_codes(result) & {
        "MISSING_BEGIN",
        "MISSING_END",
        "MISSING_LANGUAGES",
        "MISSING_PARTICIPANTS",
        "MISSING_ID",
        "MISSING_CHI_TIER",
    }
    assert result["summary"]["child_token_count"] == 1
    assert result["readiness"]["feature_extraction_ready"] is True
    assert result["readiness"]["reference_comparison_ready"] is True
    assert result["readiness"]["clan_metric_ready"] is False


def test_missing_begin_and_end_fails():
    text = """@Participants:\tCHI Child Target_Child
@ID:\teng|Test|CHI|4;00.00|male|||Target_Child|||
*CHI:\thello .
"""

    result = review_cha_text(text)

    assert result["status"] == "fail"
    assert {"MISSING_BEGIN", "MISSING_END"} <= issue_codes(result)


def test_missing_child_tier_fails():
    text = """@Begin
@Participants:\tMOT Mother Mother
@ID:\teng|Test|MOT|||||Mother|||
*MOT:\thello .
@End
"""

    result = review_cha_text(text)

    assert result["status"] == "fail"
    assert "MISSING_CHI_TIER" in issue_codes(result)
    assert result["summary"]["child_utterance_count"] == 0


def test_suspicious_child_speaker_question_is_warning():
    text = VALID_CHAT.replace("*CHI:\thello .", "*CHI:\twhat is this ?")

    result = review_cha_text(text)

    suspicious = [
        issue for issue in result["issues"]
        if issue["code"] == "SUSPICIOUS_CHI_PROMPT"
    ]
    assert suspicious
    assert suspicious[0]["severity"] == "warning"
    assert result["status"] == "needs_review"


def test_marker_counts_are_reported():
    text = """@Begin
@Languages:\teng
@Participants:\tCHI Child Target_Child, MOT Mother Mother
@ID:\teng|Test|CHI|4;00.00|male|||Target_Child|||
@ID:\teng|Test|MOT|||||Mother|||
*CHI:\txxx yyy .
*CHI:\t0 .
*CHI:\t&=laugh &=gasp .
*CHI:\tball [/] ball .
@End
"""

    result = review_cha_text(text)

    assert result["summary"]["marker_counts"] == {
        "xxx": 1,
        "yyy": 1,
        "www": 0,
        "zero_vocalization": 1,
        "laugh": 1,
        "gasp": 1,
        "repetition": 1,
    }


def test_thai_characters_without_tha_language_tag_warns():
    text = VALID_CHAT.replace("*CHI:\thello .", "*CHI:\tสวัสดี .")

    result = review_cha_text(text)

    assert "LANG_TAG_MISMATCH" in issue_codes(result)
    assert result["quality_score"] == 85


def test_thai_characters_with_tha_language_tag_do_not_warn():
    text = VALID_CHAT.replace("@Languages:\teng", "@Languages:\teng, tha")
    text = text.replace("*CHI:\thello .", "*CHI:\tสวัสดี .")

    result = review_cha_text(text)

    assert "LANG_TAG_MISMATCH" not in issue_codes(result)


def test_low_asr_confidence_warns_and_reports_average():
    text = VALID_CHAT.replace("*CHI:\thello .", "*CHI:\thello .\n%conf:\t0.45")

    result = review_cha_text(text)

    assert "LOW_ASR_CONFIDENCE" in issue_codes(result)
    assert result["summary"]["average_confidence"] == 0.45
    assert result["quality_score"] == 85


def test_missing_languages_is_structural_error():
    text = VALID_CHAT.replace("@Languages:\teng\n", "")

    result = review_cha_text(text)

    assert result["status"] == "fail"
    assert "MISSING_LANGUAGES" in issue_codes(result)
    assert result["readiness"]["feature_extraction_ready"] is False


def test_child_age_and_target_role_block_reference_readiness_not_features():
    text = VALID_CHAT.replace(
        "@ID:\teng|Test|CHI|4;00.00|male|||Target_Child|||",
        "@ID:\teng|Test|CHI|four|male||||||",
    ).replace(
        "@Participants:\tCHI Child Target_Child, MOT Mother Mother",
        "@Participants:\tCHI Child Child, MOT Mother Mother",
    )

    result = review_cha_text(text)

    assert {"UNPARSEABLE_CHILD_AGE", "MISSING_TARGET_CHILD_ROLE"} <= issue_codes(result)
    assert result["readiness"]["feature_extraction_ready"] is True
    assert result["readiness"]["reference_comparison_ready"] is False


def test_participant_id_count_mismatch_blocks_features():
    text = VALID_CHAT.replace("@ID:\teng|Test|MOT|||||Mother|||\n", "")

    result = review_cha_text(text)

    assert result["status"] == "fail"
    assert "PARTICIPANT_ID_COUNT_MISMATCH" in issue_codes(result)
    assert result["readiness"]["feature_extraction_ready"] is False


def test_www_without_explanation_is_counted_and_warns():
    text = VALID_CHAT.replace("*CHI:\thello .", "*CHI:\twww .")

    result = review_cha_text(text)

    assert result["summary"]["marker_counts"]["www"] == 1
    assert "WWW_WITHOUT_EXPLANATION" in issue_codes(result)


def test_media_basename_mismatch_warns_when_source_name_is_known():
    text = VALID_CHAT.replace("@Participants", "@Media:\tother_file, audio\n@Participants")

    result = review_cha_text(text, source_name="sample.cha")

    assert "MEDIA_BASENAME_MISMATCH" in issue_codes(result)
