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

__all__ = [
    "ANALYSIS_CONTRACT_VERSION",
    "AnalysisInput",
    "AnalysisInputKind",
    "AnalysisProvenance",
    "AnalysisRequest",
    "AnalysisResult",
    "AnalysisStatus",
]
