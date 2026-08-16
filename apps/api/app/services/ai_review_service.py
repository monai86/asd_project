from __future__ import annotations

import re

from app.repositories.mock_repository import MockRepository, new_id
from app.schemas.clinical import AiAssistanceArea, AiReview, AiReviewPatch, FeatureSet, ReviewStatus, TherapySession
from app.services.ml_providers.reference_evidence import (
    band_number,
    iqr_position,
    runtime_td_reference_band,
)


def sanitize_for_ai(text: str, case_code: str) -> str:
    value = str(text or "")
    value = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", value)
    value = re.sub(r"\b\d{4}-\d{1,2}-\d{1,2}\b", "[DATE]", value)
    value = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "[DATE]", value)
    value = re.sub(r"\b(?:DOB|birth\s*date|date\s*of\s*birth)\s*[:#-]?\s*[A-Za-z0-9,/\-\s]{4,24}", "[DATE]", value, flags=re.I)
    value = re.sub(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE]", value)
    value = re.sub(r"\b(?:\d+\s+[A-Za-z0-9.'-]+(?:\s+[A-Za-z0-9.'-]+){0,4}\s+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Boulevard|Blvd))\b", "[ADDRESS]", value, flags=re.I)
    value = re.sub(r"\b(?:MRN|HN|hospital\s*(?:number|id)|school\s*(?:number|id)|student\s*id|record\s*id)\s*[:#-]?\s*[A-Za-z0-9-]{3,}\b", "[IDENTIFIER]", value, flags=re.I)
    value = re.sub(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", case_code, value)
    return value


def create_ai_review(repo: MockRepository, session_id: str) -> AiReview:
    session = repo.sessions[session_id]
    transcript = repo.transcripts.get(session.transcript_id or "")
    feature_set = repo.features.get(session.feature_set_id or "")
    previous_feature_set = _previous_reviewed_feature_set(repo, session)
    case = repo.cases[session.case_id]
    if transcript is None:
        raise ValueError("AI-assisted review requires a transcript.")
    if feature_set is not None and feature_set.review_status == ReviewStatus.stale:
        raise ValueError("AI-assisted review requires regenerated features; the current feature set is stale.")
    if feature_set is not None and (
        feature_set.transcript_id != transcript.transcript_id
        or feature_set.transcript_version != transcript.version
    ):
        raise ValueError("AI-assisted review requires features from the current transcript version.")
    sanitized = sanitize_for_ai(transcript.raw_text, case.child_code)
    concerns = []
    if transcript.qa_status.value != "PASS":
        concerns.append("Transcript QA has warnings or blockers that require therapist review.")
    if not transcript.therapist_attested:
        concerns.append("Transcript has not been therapist-attested.")
    if feature_set and any(item.name == "unintelligible_ratio" and float(item.value) > 0.2 for item in feature_set.features if isinstance(item.value, (int, float))):
        concerns.append("Unintelligible utterance ratio may limit interpretation.")
    priority, priority_factors = _review_priority(concerns, feature_set)
    reference_band = runtime_td_reference_band(case.age_months, session.session_type)
    assistance_areas = _assistance_areas(
        transcript,
        feature_set,
        previous_feature_set,
        priority,
        priority_factors,
        reference_band=reference_band,
    )
    review = AiReview(
        ai_review_id=new_id("air"),
        session_id=session_id,
        summary="Decision-support summary prepared for therapist review; no clinical conclusion is final.",
        assistance_areas=assistance_areas,
        key_findings=[
            "Transcript source was sanitized before AI-style summarization.",
            f"Sanitized transcript characters reviewed: {len(sanitized)}.",
            *_feature_findings(feature_set),
        ],
        concerns=concerns,
        strengths=["Manual-first workflow keeps therapist review before report use."],
        limitations=[
            "This prototype is not clinically validated for Thai diagnosis or any automated diagnosis.",
            "Review cues are descriptive and require therapist interpretation.",
        ],
        recommended_review_actions=[
            "Confirm speaker labels and unintelligible segments.",
            "Edit or reject every AI-assisted sentence before report sign-off.",
        ],
        confidence_level="limited" if concerns else "moderate",
        review_priority=priority,
        input_transcript_version=transcript.version,
        feature_set_id=feature_set.feature_set_id if feature_set else None,
        feature_schema_version=feature_set.schema_version if feature_set else None,
        therapist_review_status=ReviewStatus.needs_review,
    )
    return repo.create_ai_review(
        review,
        actor_id="system",
        audit_action="ai_review.create",
        audit_message="AI-assisted review support generated with therapist-review requirement.",
    )


def _assistance_areas(
    transcript,
    feature_set: FeatureSet | None,
    previous_feature_set: FeatureSet | None,
    priority: str,
    priority_factors: list[str],
    reference_band: dict | None = None,
) -> list[AiAssistanceArea]:
    feature_values = _feature_values(feature_set)
    return [
        AiAssistanceArea(
            area="Transcript QA Assistant",
            summary=_qa_summary(transcript),
            contributing_factors=[
                f"Transcript QA status: {transcript.qa_status.value}.",
                f"Therapist attestation: {'attested' if transcript.therapist_attested else 'not attested'}.",
                *[f"{issue.code}: {issue.message}" for issue in transcript.qa_issues[:4]],
            ],
            recommended_actions=[
                "Review speaker labels, timestamps, and unintelligible segments before using this output.",
                "Resolve QA warnings or document the therapist rationale for proceeding.",
            ],
        ),
        AiAssistanceArea(
            area="Feature Explanation Assistant",
            summary=_feature_summary(feature_values),
            contributing_factors=_feature_findings(feature_set),
            recommended_actions=[
                "Interpret MLU, TTR, NDW, unintelligibility, and question ratio as descriptive language-sample features.",
                "Check whether transcript quality or sample length limits feature interpretation.",
            ],
        ),
        AiAssistanceArea(
            area="Review Priority",
            summary=f"Review priority is {priority}; it is not a diagnostic score or raw model probability.",
            contributing_factors=priority_factors,
            recommended_actions=[
                "Use priority only to order therapist review work.",
                "Do not communicate priority as a diagnosis or screening result.",
            ],
        ),
        AiAssistanceArea(
            area="Progress Summary",
            summary=_progress_summary(feature_set, previous_feature_set, reference_band),
            contributing_factors=_progress_factors(feature_set, previous_feature_set, reference_band),
            recommended_actions=[
                "Compare only sessions with reviewed transcripts and compatible feature schema versions.",
                "Mention uncertainty when transcript QA is weak or sample size differs across sessions.",
            ],
        ),
        AiAssistanceArea(
            area="Report Drafting",
            summary="Report draft content must remain therapist-editable and requires sign-off before export.",
            contributing_factors=[
                "Required report sections include session summary, transcript quality, language sample features, clinical review cues, progress, therapist review, limitations, and sign-off.",
                "AI-assisted content is stored with transcript and feature provenance.",
            ],
            recommended_actions=[
                "Edit or reject AI-assisted text before using it in a report.",
                "Keep the mandatory limitation text in every exported report.",
            ],
        ),
    ]


def _feature_values(feature_set: FeatureSet | None) -> dict[str, object]:
    if feature_set is None:
        return {}
    return {item.name: item.value for item in feature_set.features}


def _feature_findings(feature_set: FeatureSet | None) -> list[str]:
    values = _feature_values(feature_set)
    if not values:
        return ["Feature extraction is not complete, so feature explanations are limited."]
    names = [
        ("mean_length_of_utterance_words", "MLU words"),
        ("type_token_ratio", "TTR"),
        ("number_of_different_words", "NDW"),
        ("unintelligible_ratio", "unintelligibility ratio"),
        ("question_ratio", "question ratio"),
    ]
    return [f"{label}: {values[name]}." for name, label in names if name in values]


def _feature_summary(values: dict[str, object]) -> str:
    if not values:
        return "Feature explanations are pending because no feature set is linked to this session."
    mlu = values.get("mean_length_of_utterance_words", "not available")
    ttr = values.get("type_token_ratio", "not available")
    ndw = values.get("number_of_different_words", "not available")
    unintelligible = values.get("unintelligible_ratio", "not available")
    question_ratio = values.get("question_ratio", "not available")
    return (
        f"Current reviewed transcript features include MLU {mlu}, TTR {ttr}, NDW {ndw}, "
        f"unintelligibility ratio {unintelligible}, and question ratio {question_ratio}."
    )


def _qa_summary(transcript) -> str:
    if transcript.qa_status.value == "PASS":
        return "Transcript QA passed automated checks; therapist review is still required."
    if transcript.qa_status.value == "FAIL":
        return "Transcript QA failed automated checks and needs correction or documented override before downstream use."
    return "Transcript QA has warnings that should be reviewed before feature interpretation."


def _review_priority(concerns: list[str], feature_set: FeatureSet | None) -> tuple[str, list[str]]:
    factors = list(concerns)
    values = _feature_values(feature_set)
    if not values:
        factors.append("No feature set is linked to this session.")
        return ("high" if concerns else "moderate", factors)
    if float(values.get("unintelligible_ratio", 0) or 0) > 0.2:
        factors.append("Unintelligibility ratio is above the review threshold.")
    if float(values.get("unknown_speaker_ratio", 0) or 0) > 0.2:
        factors.append("Unknown speaker ratio is above the review threshold.")
    if bool(values.get("limited_reciprocal_question_cue")):
        factors.append("Limited reciprocal question cue is present and should be interpreted by the therapist.")
    if factors:
        return "high", factors
    if int(values.get("child_utterance_count", 0) or 0) < 5:
        return "moderate", ["Child utterance count is low for stable interpretation."]
    return "low", ["Reviewed transcript and feature set did not trigger high-priority review factors."]


def _previous_reviewed_feature_set(repo: MockRepository, session: TherapySession) -> FeatureSet | None:
    previous_sessions = [
        candidate for candidate in repo.sessions.values()
        if candidate.case_id == session.case_id
        and candidate.session_id != session.session_id
        and candidate.session_date < session.session_date
        and candidate.feature_set_id
    ]
    previous_sessions.sort(key=lambda item: item.session_date, reverse=True)
    for candidate in previous_sessions:
        feature_set = repo.features.get(candidate.feature_set_id or "")
        if (
            feature_set is not None
            and feature_set.therapist_attested
            and feature_set.review_status != ReviewStatus.stale
        ):
            return feature_set
    return None


def _progress_summary(
    feature_set: FeatureSet | None,
    previous_feature_set: FeatureSet | None,
    reference_band: dict | None = None,
) -> str:
    if feature_set is None:
        return "Progress summary is pending because current session features are not available."
    if previous_feature_set is None:
        summary = "Progress summary requires a previous reviewed session with extracted features."
    else:
        deltas = _progress_deltas(feature_set, previous_feature_set)
        if not deltas:
            summary = "Progress summary could not compare the available feature values."
        else:
            summary = "Compared with the previous reviewed session: " + "; ".join(deltas) + "."
    reference_lines = _reference_band_lines(feature_set, reference_band)
    if reference_lines:
        summary += " Reference comparison: " + " ".join(reference_lines)
    return summary


def _progress_factors(
    feature_set: FeatureSet | None,
    previous_feature_set: FeatureSet | None,
    reference_band: dict | None = None,
) -> list[str]:
    if feature_set is None or previous_feature_set is None:
        factors = ["At least two reviewed sessions with feature sets are required for progress comparison."]
    else:
        factors = [
            f"Current feature schema: {feature_set.schema_version}.",
            f"Previous feature schema: {previous_feature_set.schema_version}.",
            *_progress_deltas(feature_set, previous_feature_set),
        ]
    reference_lines = _reference_band_lines(feature_set, reference_band)
    if reference_lines:
        factors.append(
            f"Reference band (typical development, ages {reference_band.get('age_band')} months, "
            f"{reference_band.get('task_type')}): "
            + " ".join(reference_lines)
        )
        factors.append("Reference comparison uses descriptive public-corpus data and requires therapist interpretation.")
    return factors


def _reference_band_lines(feature_set: FeatureSet | None, reference_band: dict | None) -> list[str]:
    """Latest-value position vs the TD reference IQR, phrased like the report."""
    if feature_set is None or not reference_band:
        return []
    values = _feature_values(feature_set)
    ref_features = reference_band.get("features") or {}
    lines = []
    for name, stats in ref_features.items():
        current = values.get(name)
        if not isinstance(current, (int, float)):
            continue
        q1 = stats.get("q1")
        median = stats.get("median")
        q3 = stats.get("q3")
        if q1 is None or q3 is None:
            continue
        position = iqr_position(current, q1, q3).replace("_iqr", "")
        q1_label = band_number(q1)
        q3_label = band_number(q3)
        median_label = band_number(median)
        current_label = band_number(current)
        lines.append(
            f"{name}: latest {current_label} is {position} the typical-development reference IQR "
            f"({q1_label}–{q3_label}, median {median_label}) for ages "
            f"{reference_band.get('age_band')} months ({reference_band.get('task_type')})."
        )
    return lines



def _progress_deltas(current: FeatureSet, previous: FeatureSet) -> list[str]:
    current_values = _feature_values(current)
    previous_values = _feature_values(previous)
    labels = {
        "mean_length_of_utterance_words": "MLU words",
        "type_token_ratio": "TTR",
        "number_of_different_words": "NDW",
        "unintelligible_ratio": "unintelligibility ratio",
        "question_ratio": "question ratio",
    }
    deltas = []
    for name, label in labels.items():
        if isinstance(current_values.get(name), (int, float)) and isinstance(previous_values.get(name), (int, float)):
            delta = round(float(current_values[name]) - float(previous_values[name]), 4)
            direction = "increased" if delta > 0 else "decreased" if delta < 0 else "was unchanged"
            deltas.append(f"{label} {direction} by {abs(delta)}")
    return deltas


def patch_ai_review(repo: MockRepository, review_id: str, payload: AiReviewPatch) -> AiReview:
    review = repo.ai_reviews[review_id]
    session = repo.sessions[review.session_id]
    if review.therapist_review_status == ReviewStatus.stale or session.ai_review_id != review_id:
        raise ValueError("Stale AI-assisted review support cannot be edited; regenerate it from current findings.")
    updates = payload.model_dump(exclude_unset=True)
    next_status = updates.get("therapist_review_status")
    if next_status == ReviewStatus.withdrawn and not str(updates.get("rejected_reason") or review.rejected_reason).strip():
        raise ValueError("Rejecting AI-assisted review support requires a therapist reason.")
    allowed_statuses = {ReviewStatus.needs_review, ReviewStatus.attested, ReviewStatus.withdrawn}
    if next_status is not None and next_status not in allowed_statuses:
        raise ValueError("AI-assisted review status must be Needs Review, Attested, or Withdrawn.")
    for key, value in updates.items():
        setattr(review, key, value)
    action = "rejected" if review.therapist_review_status == ReviewStatus.withdrawn else "edited"
    return repo.update_ai_review(
        review,
        actor_id="system",
        audit_action="ai_review.patch",
        audit_message=f"AI-assisted review support {action} by therapist.",
    )
