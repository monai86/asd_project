"""Practice dashboard summary endpoint.

Aggregates the clinical pipeline (cases -> sessions -> reports) for the
therapist's organization into a single read model used by the therapist
dashboard surface. Read-only; no mutations.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_repository
from app.auth.authorization import filter_cases_for_user, require_case
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import ReviewStatus
from app.services.ml_providers.reference_evidence import ReferenceEvidenceProvider
from app.services.ml_providers.reference_feature_adapter import RUNTIME_TO_CANONICAL

router = APIRouter(tags=["dashboard"])

REVIEWED_STATUSES = {
    ReviewStatus.needs_review,
    ReviewStatus.attested,
    ReviewStatus.ready,
    ReviewStatus.signed_off,
}

# ---------------------------------------------------------------------------
# Session-level feature trends
#
# The dashboard plots one language feature across a case's sessions over time
# (MLU, NDW, TTR, ...). Each entry maps a canonical trend key to every alias
# produced by the extractors in this repo (the API provider uses long names
# like ``mean_length_of_utterance_words``; the root extractor uses ``mluw``).
# ---------------------------------------------------------------------------

TREND_FEATURES: list[dict[str, Any]] = [
    {
        "key": "mlu_words",
        "label": "MLU (words)",
        "unit": "words per utterance",
        "aliases": ["mean_length_of_utterance_words", "mluw", "mlu_w", "mlu"],
    },
    {
        "key": "ndw",
        "label": "NDW (different words)",
        "unit": "words",
        "aliases": ["number_of_different_words", "ndw"],
    },
    {
        "key": "ttr",
        "label": "Type–Token Ratio",
        "unit": "ratio",
        "aliases": ["type_token_ratio", "ttr"],
    },
    {
        "key": "total_words",
        "label": "Total words (child)",
        "unit": "words",
        "aliases": ["total_word_count", "total_words"],
    },
    {
        "key": "unintelligible_ratio",
        "label": "Unintelligible ratio",
        "unit": "ratio",
        "aliases": ["unintelligible_ratio"],
    },
]

_TREND_ALIAS_INDEX = {
    alias: feature["key"]
    for feature in TREND_FEATURES
    for alias in feature["aliases"]
}

# trend key -> canonical reference-cell feature name (only features the
# reference evidence package carries stats for; e.g. NDW has no cell column).
_TREND_REFERENCE_MAP: dict[str, str] = {}
for _trend_feature in TREND_FEATURES:
    for _trend_alias in _trend_feature["aliases"]:
        if _trend_alias in RUNTIME_TO_CANONICAL:
            _TREND_REFERENCE_MAP[_trend_feature["key"]] = RUNTIME_TO_CANONICAL[_trend_alias]

_REFERENCE_PROVIDER: ReferenceEvidenceProvider | None = None


def _get_reference_provider() -> ReferenceEvidenceProvider:
    """Lazily created module-level provider (artifacts are checksum-validated once)."""
    global _REFERENCE_PROVIDER
    if _REFERENCE_PROVIDER is None:
        _REFERENCE_PROVIDER = ReferenceEvidenceProvider()
    return _REFERENCE_PROVIDER


def _case_reference_band(
    provider: ReferenceEvidenceProvider | None,
    age_months: int | None,
    session_type: str | None,
) -> dict[str, Any] | None:
    """Typical-development (TD) IQR band for a case, mapped to trend keys."""
    if provider is None:
        return None
    band = provider.td_reference_band(age_months, session_type)
    if not band:
        return None
    features: dict[str, Any] = {}
    for trend_key, canonical in _TREND_REFERENCE_MAP.items():
        stats = band.get("features", {}).get(canonical)
        if stats:
            features[trend_key] = stats
    if not features:
        return None
    return {
        "age_band": band["age_band"],
        "task_type": band["task_type"],
        "features": features,
    }


def _as_number(value: object) -> float | None:
    """Coerce a feature value to a float, ignoring non-numeric values."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _build_feature_trends(
    repo: MockRepository,
    cases: list,
    sessions: list,
    case_labels: dict[str, str],
    reference_provider: ReferenceEvidenceProvider | None = None,
) -> dict[str, Any]:
    """Build per-case per-session numeric series for the trend features."""
    feature_meta = [
        {key: feature[key] for key in ("key", "label", "unit")}
        for feature in TREND_FEATURES
    ]
    series: list[dict[str, Any]] = []
    for case in cases:
        case_sessions = sorted(
            (s for s in sessions if s.case_id == case.case_id and s.feature_set_id),
            key=lambda s: (s.session_date, s.session_id),
        )
        points: list[dict[str, Any]] = []
        for session in case_sessions:
            feature_set = repo.get_feature_set(session.feature_set_id or "")
            if feature_set is None:
                continue
            values: dict[str, float] = {}
            for feature_value in feature_set.features:
                key = _TREND_ALIAS_INDEX.get(feature_value.name)
                if key is None:
                    continue
                number = _as_number(feature_value.value)
                if number is None or key in values:
                    continue
                values[key] = number
            if values:
                points.append(
                    {
                        "session_id": session.session_id,
                        "session_date": session.session_date,
                        "values": values,
                    }
                )
        if points:
            series.append(
                {
                    "case_id": case.case_id,
                    "case_label": case_labels.get(case.case_id, case.case_id),
                    "points": points,
                    "reference": _case_reference_band(
                        reference_provider,
                        case.age_months,
                        case_sessions[-1].session_type if case_sessions else None,
                    ),
                }
            )
    return {"features": feature_meta, "cases": series}


@router.get("/dashboard/summary")
def get_dashboard_summary(
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
) -> dict:
    """Return org-scoped pipeline counts plus the most recent sessions."""
    org_id = user.organization_id
    cases = filter_cases_for_user(
        repo,
        repo.list_cases_for_user(user.user_id, org_id),
        user,
    )
    sessions = [session for case in cases for session in repo.list_sessions(case.case_id)]
    session_ids = {session.session_id for session in sessions}
    reports = [report for report in repo.list_reports(org_id) if report.session_id in session_ids]

    consent_counts = Counter(case.consent_status.lower() if case.consent_status else "unknown" for case in cases)
    session_status_counts = Counter(str(session.status.value) if isinstance(session.status, ReviewStatus) else str(session.status) for session in sessions)

    transcript_count = sum(1 for session in sessions if session.transcript_id)
    features_count = sum(1 for session in sessions if session.feature_set_id)
    ml_review_count = sum(1 for session in sessions if session.ml_result_id or session.ai_review_id)
    report_count = sum(1 for session in sessions if session.report_id)

    report_signoff_counts = Counter(
        str(report.therapist_signoff_status.value) if isinstance(report.therapist_signoff_status, ReviewStatus) else str(report.therapist_signoff_status)
        for report in reports
    )

    case_labels = {
        case.case_id: case.nickname or case.child_code for case in cases
    }

    recent_sessions = sorted(
        [
            {
                "session_id": session.session_id,
                "case_id": session.case_id,
                "case_label": case_labels.get(session.case_id, session.case_id),
                "session_date": session.session_date,
                "status": str(session.status.value) if isinstance(session.status, ReviewStatus) else str(session.status),
                "has_transcript": bool(session.transcript_id),
                "has_features": bool(session.feature_set_id),
                "has_ml_review": bool(session.ml_result_id or session.ai_review_id),
                "has_report": bool(session.report_id),
            }
            for session in sessions
        ],
        key=lambda item: item["session_date"],
        reverse=True,
    )[:10]

    return {
        "organization_id": org_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases": {
            "total": len(cases),
            "consent_counts": dict(consent_counts),
            "with_latest_reviewed_session": sum(1 for case in cases if case.latest_session_status in REVIEWED_STATUSES),
        },
        "sessions": {
            "total": len(sessions),
            "status_counts": dict(session_status_counts),
            "with_transcript": transcript_count,
            "with_features": features_count,
            "with_ml_review": ml_review_count,
            "with_report": report_count,
        },
        "reports": {
            "total": len(reports),
            "signoff_counts": dict(report_signoff_counts),
        },
        "recent_sessions": recent_sessions,
        "feature_trends": _build_feature_trends(
            repo,
            cases,
            sessions,
            case_labels,
            reference_provider=_get_reference_provider(),
        ),
    }


@router.get("/cases/{case_id}/feature-trend")
def get_case_feature_trend(
    case_id: str,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
) -> dict:
    """Per-case feature series for the CaseDetail language-progress card."""
    case = require_case(repo, case_id, user)
    sessions = repo.list_sessions(case_id)
    trends = _build_feature_trends(
        repo,
        [case],
        sessions,
        {case.case_id: case.nickname or case.child_code},
        reference_provider=_get_reference_provider(),
    )
    return {"features": trends["features"], "cases": trends["cases"]}
