"""Synchronous execution seam for reviewed-transcript research analysis.

Authorization, consent checks, transcript loading, and persistence stay with the
calling application. This module only builds the versioned scientific request
and returns a serializable execution envelope.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from .models import AnalysisInput, AnalysisInputKind, AnalysisRequest, AnalysisResult
from .transcript import (
    TranscriptAnalysisProfile,
    analyze_reviewed_chat,
    transcript_analysis_profile,
)


@dataclass(frozen=True)
class ReviewedTranscriptAnalysisExecution:
    """Request, profile, and result produced by one synchronous execution."""

    request: AnalysisRequest
    profile: TranscriptAnalysisProfile
    result: AnalysisResult

    def to_dict(self) -> dict[str, object]:
        return {
            "request": self.request.to_dict(),
            "profile": self.profile.to_dict(),
            "result": self.result.to_dict(),
        }


def execute_reviewed_transcript_analysis(
    *,
    input_ref: str,
    session_ref: str,
    transcript_version: int,
    chat_text: str,
    analyzed_at: datetime | None = None,
) -> ReviewedTranscriptAnalysisExecution:
    """Run the maintained descriptive transcript profile synchronously."""

    profile = transcript_analysis_profile()
    request = AnalysisRequest(
        input=AnalysisInput(
            input_ref=input_ref,
            input_kind=AnalysisInputKind.REVIEWED_TRANSCRIPT,
            session_ref=session_ref,
            transcript_version=transcript_version,
            content_sha256=sha256(chat_text.encode("utf-8")).hexdigest(),
        ),
        pipeline_version=profile.pipeline_version,
        feature_schema_version=profile.feature_definition_version,
    )
    result = analyze_reviewed_chat(request, chat_text, analyzed_at=analyzed_at)
    return ReviewedTranscriptAnalysisExecution(
        request=request,
        profile=profile,
        result=result,
    )
