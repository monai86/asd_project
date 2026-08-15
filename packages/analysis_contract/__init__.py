"""Small, analysis-only request/result contract for future Python workers.

This package deliberately has no FastAPI, database, auth, or storage imports.
The maintained API remains responsible for authorization and orchestration.
"""

from .models import (
    ANALYSIS_CONTRACT_VERSION,
    AnalysisInput,
    AnalysisInputKind,
    AnalysisProvenance,
    AnalysisRequest,
    AnalysisResult,
    AnalysisStatus,
)
from .transcript import (
    FEATURE_DEFINITION_VERSION,
    THAI_TOKENIZER_VERSION,
    TRANSCRIPT_PIPELINE_VERSION,
    TRANSCRIPT_QA_VERSION,
    TranscriptAnalysisProfile,
    TranscriptQualityCode,
    TranscriptQualityIssue,
    TranscriptQualityKind,
    analyze_reviewed_chat,
    tokenize_reviewed_text,
    transcript_analysis_profile,
)

__all__ = [
    "ANALYSIS_CONTRACT_VERSION",
    "AnalysisInput",
    "AnalysisInputKind",
    "AnalysisProvenance",
    "AnalysisRequest",
    "AnalysisResult",
    "AnalysisStatus",
    "FEATURE_DEFINITION_VERSION",
    "THAI_TOKENIZER_VERSION",
    "TRANSCRIPT_PIPELINE_VERSION",
    "TRANSCRIPT_QA_VERSION",
    "TranscriptAnalysisProfile",
    "TranscriptQualityCode",
    "TranscriptQualityIssue",
    "TranscriptQualityKind",
    "analyze_reviewed_chat",
    "tokenize_reviewed_text",
    "transcript_analysis_profile",
]
