"""
Audio-to-CHAT pipeline for the ASD project.

End-to-end flow:
    .wav / .mp3  ->  Whisper ASR  ->  diarization  ->  CHAT formatter  ->  .cha

The resulting .cha is consumable by the existing data_loader + classifier
+ progress_tracking pipeline, turning the whole project into a real end-to-end
system (audio in -> clinical assessment out) instead of one that requires
manually-annotated transcripts.
"""

from .whisper_transcribe import WhisperTranscriber, WordSegment, UtteranceSegment
from .chat_formatter import utterances_to_chat
from .diarization import (
    BaseDiarizer,
    EmbeddingDiarizer,
    EmbeddingDiarizerConfig,
    PitchHeuristicDiarizer,
    age_aware_child_f0_threshold,
    get_diarizer,
)
from .vad import VADConfig, detect_speech_regions, speech_coverage
from .segmentation import clean_segments, filter_to_speech_regions
from .chatter_validator import (
    ValidationReport,
    ValidationIssue,
    auto_fix as chat_auto_fix,
    validate_chat_file,
)
from .pipeline import audio_to_cha

__all__ = [
    "WhisperTranscriber",
    "WordSegment",
    "UtteranceSegment",
    "utterances_to_chat",
    "audio_to_cha",
    "BaseDiarizer",
    "EmbeddingDiarizer",
    "EmbeddingDiarizerConfig",
    "PitchHeuristicDiarizer",
    "age_aware_child_f0_threshold",
    "get_diarizer",
    "VADConfig",
    "detect_speech_regions",
    "speech_coverage",
    "clean_segments",
    "filter_to_speech_regions",
    "ValidationReport",
    "ValidationIssue",
    "chat_auto_fix",
    "validate_chat_file",
]
