"""Rule/template based speech therapist decision-support assistant.

This module summarizes existing project outputs for therapist review. It is
not a diagnostic system and does not claim Thai clinical validation.
"""

from __future__ import annotations

from typing import Any

UNCERTAIN_LOW = 0.40
UNCERTAIN_HIGH = 0.60

DISCLAIMER_TH = (
    "ข้อความนี้เป็น clinical decision-support สำหรับนักบำบัดด้านภาษาและการสื่อสาร "
    "ไม่ใช่เครื่องมือสรุปผลทางการแพทย์ ต้องใช้ร่วมกับ human-in-the-loop "
    "และการประเมินโดยผู้เชี่ยวชาญ ผลลัพธ์ยังไม่ได้ผ่าน external validation "
    "กับข้อมูลเด็กไทย"
)

DISCLAIMER_EN = (
    "This is clinical decision support for speech-language therapists. It is "
    "not a medical conclusion and must be used with human-in-the-loop expert "
    "assessment. The system has not completed external validation with Thai "
    "child clinical data."
)


def _num(features: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = features.get(key, default)
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _concern_from_probability(probability: float | None, concern_count: int) -> str:
    if probability is None:
        if concern_count >= 3:
            return "uncertain"
        if concern_count >= 1:
            return "moderate"
        return "low"
    if UNCERTAIN_LOW <= probability <= UNCERTAIN_HIGH:
        return "uncertain"
    if probability >= 0.70:
        return "high"
    if probability >= 0.50:
        return "moderate"
    return "low"


def interpret_screening_result(
    features: dict[str, Any],
    probability: float | None = None,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Interpret transcript-derived screening output with safe therapist wording."""
    del threshold  # Kept for API compatibility with caller-controlled thresholds.
    key_patterns: list[str] = []
    protective_patterns: list[str] = []

    if _num(features, "unintelligible_ratio") >= 0.15:
        key_patterns.append(
            "มีสัดส่วนคำพูดที่ฟังไม่ชัดสูง ควรตรวจคุณภาพ transcript และประเมิน articulation/language เพิ่ม"
        )
    if _num(features, "zero_vocalization_count") >= 20:
        key_patterns.append(
            "พบช่วงที่เด็กไม่มี verbal response หลายครั้ง ควรดูบริบทการสนทนาและ task demand"
        )
    if _num(features, "echolalia_ratio") >= 0.08:
        key_patterns.append(
            "พบรูปแบบการพูดซ้ำ ควรประเมินร่วมกับพฤติกรรมทางสังคมและบริบท"
        )
    if _num(features, "pronoun_reversal_count") >= 1:
        key_patterns.append(
            "พบ pronoun reversal heuristic ควรให้ผู้เชี่ยวชาญตรวจบริบทก่อนตีความ"
        )
    if _num(features, "total_words") < 100:
        key_patterns.append(
            "ปริมาณคำพูดค่อนข้างน้อย อาจสะท้อนข้อจำกัดด้านภาษา หรือบริบทการเก็บข้อมูล"
        )
    if _num(features, "total_utterances") < 75:
        key_patterns.append(
            "จำนวน utterance ค่อนข้างน้อย ควรตรวจระยะเวลา session และโอกาสในการสื่อสาร"
        )

    if _num(features, "mlu") >= 2.5:
        protective_patterns.append("MLU ค่อนข้างสูง สะท้อนความยาว utterance ที่เป็นจุดแข็งด้านภาษา")
    if _num(features, "mluw") >= 2.0:
        protective_patterns.append("MLUw อยู่ในระดับที่ช่วยสนับสนุน expressive language production")
    if _num(features, "ttr") >= 0.35:
        protective_patterns.append("TTR สูงขึ้น สะท้อนความหลากหลายของคำใน transcript")
    if _num(features, "total_words") >= 300:
        protective_patterns.append("จำนวนคำพูดรวมค่อนข้างดีเมื่อเทียบกับ session sample")
    if _num(features, "total_utterances") >= 150:
        protective_patterns.append("จำนวน utterance สะท้อนการมีส่วนร่วมในการสื่อสาร")
    if _num(features, "question_ratio") >= 0.05:
        protective_patterns.append("มีสัดส่วนคำถามจากเด็ก ซึ่งอาจสะท้อน pragmatic/social initiation")

    concern_level = _concern_from_probability(probability, len(key_patterns))
    probability_text = (
        "ไม่มี model probability ในรอบนี้ จึงตีความจาก speech-language pattern เท่านั้น"
        if probability is None
        else f"risk estimate จากโมเดลอยู่ที่ {probability:.2f}"
    )
    en_probability_text = (
        "No model probability was provided, so this interpretation is feature-only and should be treated as uncertain."
        if probability is None
        else f"The model risk estimate is {probability:.2f}."
    )
    if probability is not None and UNCERTAIN_LOW <= probability <= UNCERTAIN_HIGH:
        en_probability_text += " This falls inside the uncertainty band."

    next_steps = [
        "review transcript quality before feature extraction",
        "interpret speech-language patterns with session context",
        "recommend further expert assessment",
        "use human-in-the-loop therapist/clinician judgment",
    ]

    return {
        "concern_level": concern_level,
        "key_patterns": key_patterns,
        "protective_patterns": protective_patterns,
        "recommended_next_steps": next_steps,
        "safe_summary_th": (
            f"ระดับข้อกังวลเชิง decision support: {concern_level}. "
            f"{probability_text}. ผลนี้ควรใช้เป็น screening support และ progress tracking "
            "ร่วมกับการอ่าน transcript และการประเมินโดยผู้เชี่ยวชาญ"
        ),
        "safe_summary_en": (
            f"Decision-support concern level: {concern_level}. "
            f"{en_probability_text} Use this as screening support and speech-language pattern review, "
            "with expert interpretation."
        ),
        "disclaimer_th": DISCLAIMER_TH,
        "disclaimer_en": DISCLAIMER_EN,
    }


def interpret_transcript_review(review_result: dict[str, Any]) -> dict[str, Any]:
    """Summarize transcript-review output for therapist workflow decisions."""
    status = review_result.get("status")
    qa_level = {
        "pass": "usable",
        "needs_review": "needs_human_review",
        "fail": "not_usable",
    }.get(status, "needs_human_review")

    issues = review_result.get("issues", []) or []
    main_issues = [
        f"{issue.get('code', 'ISSUE')}: {issue.get('message', '')}".strip()
        for issue in issues[:5]
    ]
    if not main_issues:
        main_issues = ["No major transcript QA issues were flagged by the rule-based reviewer."]

    if qa_level == "usable":
        actions = [
            "keep human confirmation before clinical interpretation",
            "proceed to feature extraction if transcript context is appropriate",
        ]
    elif qa_level == "needs_human_review":
        actions = [
            "perform human transcript review before feature extraction",
            "check speaker labels, utterance segmentation, and CHAT markers",
        ]
    else:
        actions = [
            "do not use this transcript for model/report outputs yet",
            "fix structural CHAT issues and confirm child speaker tiers",
            "rerun transcript QA after correction",
        ]

    return {
        "qa_level": qa_level,
        "main_issues": main_issues,
        "recommended_actions": actions,
        "safe_summary_th": (
            f"ผลตรวจ transcript อยู่ระดับ {qa_level}. คุณภาพ transcript ที่ต่ำอาจกระทบ "
            "feature extraction และ risk estimate จึงควรให้ผู้เชี่ยวชาญตรวจยืนยันก่อนใช้งาน"
        ),
        "safe_summary_en": (
            f"Transcript QA level: {qa_level}. Poor transcript quality can affect feature extraction "
            "and model risk estimates, so human review is required before interpretation."
        ),
    }


def interpret_progress_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Interpret first-vs-last progress summary for therapist review."""
    n_sessions = int(summary.get("n_sessions") or 0)
    if n_sessions < 2:
        return {
            "progress_direction": "insufficient_data",
            "positive_changes": [],
            "watch_items": ["ต้องมีอย่างน้อยสอง session เพื่อดูแนวโน้ม progress tracking"],
            "recommended_next_steps": ["collect another comparable session", "review goals with therapist"],
            "safe_summary_th": "ข้อมูลยังไม่พอสำหรับสรุปแนวโน้ม progress tracking",
            "safe_summary_en": "There is insufficient longitudinal data to summarize progress direction.",
        }

    metric_changes = summary.get("metric_changes", {}) or {}
    positive_changes: list[str] = []
    watch_items: list[str] = []
    for metric, change in metric_changes.items():
        if change.get("improved") is True:
            positive_changes.append(f"{metric} changed in a positive tracking direction")
        elif change.get("improved") is False:
            watch_items.append(f"{metric} should be monitored in future sessions")

    tracked = len(metric_changes)
    positive = len(positive_changes)
    if tracked == 0:
        direction = "insufficient_data"
    elif positive >= max(2, tracked * 0.6):
        direction = "improving"
    elif positive <= tracked * 0.25 and watch_items:
        direction = "declining"
    else:
        direction = "mixed"

    next_steps = [
        "compare with therapy goals and session context",
        "review transcript quality for each session",
        "continue progress tracking over comparable sessions",
        "use therapist judgment before changing intervention plan",
    ]

    return {
        "progress_direction": direction,
        "positive_changes": positive_changes,
        "watch_items": watch_items,
        "recommended_next_steps": next_steps,
        "safe_summary_th": (
            f"แนวโน้ม progress tracking: {direction}. ควรตีความร่วมกับเป้าหมายบำบัด "
            "บริบท session และการประเมินโดยนักบำบัด"
        ),
        "safe_summary_en": (
            f"Progress tracking direction: {direction}. Interpret this trend with therapy goals, "
            "session context, and therapist review."
        ),
    }


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "- No major items flagged."
    return "\n".join(f"- {item}" for item in items)


def generate_case_brief(
    features: dict[str, Any] | None = None,
    probability: float | None = None,
    transcript_review: dict[str, Any] | None = None,
    progress_summary: dict[str, Any] | None = None,
    language: str = "th",
) -> str:
    """Generate a concise therapist-facing Markdown case brief."""
    screening = interpret_screening_result(features or {}, probability) if features is not None else None
    transcript = interpret_transcript_review(transcript_review) if transcript_review is not None else None
    progress = interpret_progress_summary(progress_summary) if progress_summary is not None else None

    if language.lower().startswith("en"):
        return f"""# AI Speech Therapist Assistant Case Brief

## Purpose
Summarize transcript quality, speech-language patterns, screening risk estimate, and progress tracking for therapist review.

## Transcript quality
{transcript["safe_summary_en"] if transcript else "No transcript QA result was provided."}
{_bullet_list(transcript["recommended_actions"] if transcript else [])}

## Speech-language pattern summary
{screening["safe_summary_en"] if screening else "No feature set was provided."}
{_bullet_list(screening["key_patterns"] if screening else [])}

## Screening/risk estimate
{("Concern level: " + screening["concern_level"]) if screening else "No screening interpretation available."}

## Progress trend
{progress["safe_summary_en"] if progress else "No progress summary was provided."}
{_bullet_list(progress["positive_changes"] if progress else [])}

## Suggested next steps
{_bullet_list((screening["recommended_next_steps"] if screening else []) + (progress["recommended_next_steps"] if progress else []))}

## Safety disclaimer
{DISCLAIMER_EN}
"""

    return f"""# AI Speech Therapist Assistant Case Brief

## Purpose
สรุปคุณภาพ transcript, speech-language pattern, risk estimate และ progress tracking เพื่อให้นักบำบัดใช้ทบทวนแบบ human-in-the-loop

## Transcript quality
{transcript["safe_summary_th"] if transcript else "ยังไม่มีผล Transcript QA"}
{_bullet_list(transcript["recommended_actions"] if transcript else [])}

## Speech-language pattern summary
{screening["safe_summary_th"] if screening else "ยังไม่มีชุด feature สำหรับสรุป speech-language pattern"}
{_bullet_list(screening["key_patterns"] if screening else [])}

## Screening/risk estimate
{("Concern level: " + screening["concern_level"]) if screening else "ยังไม่มี screening interpretation"}

## Progress trend
{progress["safe_summary_th"] if progress else "ยังไม่มี progress summary"}
{_bullet_list(progress["positive_changes"] if progress else [])}

## Suggested next steps
{_bullet_list((screening["recommended_next_steps"] if screening else []) + (progress["recommended_next_steps"] if progress else []))}

## Safety disclaimer
{DISCLAIMER_TH}
"""
