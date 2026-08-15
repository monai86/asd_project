"""Versioned, analysis-only contract for reviewed transcript descriptors."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
import re
import unicodedata

from packages.cha import parse_cha_text, semantic_cha_checksum, verify_cha_round_trip

from .models import (
    AnalysisInputKind,
    AnalysisProvenance,
    AnalysisRequest,
    AnalysisResult,
    AnalysisStatus,
)


TRANSCRIPT_PIPELINE_VERSION = "reviewed-transcript-descriptors-v1"
FEATURE_DEFINITION_VERSION = "descriptive-transcript-features-v1"
THAI_TOKENIZER_VERSION = "lingualens-thai-mixed-tokenizer-v1"
TRANSCRIPT_QA_VERSION = "reviewed-transcript-qa-v1"

_THAI_VOCABULARY = tuple(
    sorted(
        {
            "สวัสดี",
            "ครับ",
            "ค่ะ",
            "ไปเที่ยว",
            "เที่ยว",
            "กัน",
            "ไหม",
            "เด็ก",
            "เล่น",
            "ของเล่น",
            "สี",
            "แดง",
            "เขียว",
            "ฟ้า",
            "แม่",
            "พ่อ",
            "เอา",
            "ให้",
            "ชอบ",
            "ไม่",
        },
        key=lambda value: (-len(value), value),
    )
)
_FEATURE_DEFINITIONS = {
    "child_utterance_count": "Count of reviewed *CHI main tiers.",
    "child_token_count": "Count of deterministic content tokens on reviewed *CHI tiers.",
    "child_unique_token_count": "Count of distinct deterministic child content tokens.",
    "mean_child_tokens_per_utterance": "child_token_count / child_utterance_count.",
    "child_type_token_ratio": "child_unique_token_count / child_token_count.",
}
_TOKEN_PART_RE = re.compile(r"[ก-๙]+|[A-Za-z0-9'-]+")
_CHAT_CODE_RE = re.compile(r"\x15\s*\d+\s*[_-]\s*\d+\s*\x15|\[[^\]]+\]|&=[^\s]+")
_UNINTELLIGIBLE = {"0", "xxx", "yyy", "www"}


class TranscriptQualityKind(str, Enum):
    BLOCKER = "blocker"
    LIMITATION = "limitation"


class TranscriptQualityCode(str, Enum):
    NO_CHILD_UTTERANCES = "NO_CHILD_UTTERANCES"
    NO_CHILD_CONTENT = "NO_CHILD_CONTENT"
    CHAT_STRUCTURE_INVALID = "CHAT_STRUCTURE_INVALID"
    INVALID_TIMESTAMP_RANGE = "INVALID_TIMESTAMP_RANGE"
    TIMESTAMP_ORDER_INVALID = "TIMESTAMP_ORDER_INVALID"
    CHAT_ROUND_TRIP_FAILED = "CHAT_ROUND_TRIP_FAILED"
    PROFILE_VERSION_MISMATCH = "PROFILE_VERSION_MISMATCH"
    INPUT_CHECKSUM_MISMATCH = "INPUT_CHECKSUM_MISMATCH"
    UNSUPPORTED_INPUT_KIND = "UNSUPPORTED_INPUT_KIND"
    SHORT_SAMPLE = "SHORT_SAMPLE"
    UNMAPPED_SPEAKER = "UNMAPPED_SPEAKER"


@dataclass(frozen=True)
class TranscriptQualityIssue:
    code: TranscriptQualityCode
    kind: TranscriptQualityKind
    message: str


_QUALITY_ISSUES = {
    TranscriptQualityCode.NO_CHILD_UTTERANCES: TranscriptQualityIssue(
        TranscriptQualityCode.NO_CHILD_UTTERANCES,
        TranscriptQualityKind.BLOCKER,
        "No reviewed child utterance is available for descriptive analysis.",
    ),
    TranscriptQualityCode.NO_CHILD_CONTENT: TranscriptQualityIssue(
        TranscriptQualityCode.NO_CHILD_CONTENT,
        TranscriptQualityKind.BLOCKER,
        "Reviewed child tiers contain no countable content tokens.",
    ),
    TranscriptQualityCode.CHAT_STRUCTURE_INVALID: TranscriptQualityIssue(
        TranscriptQualityCode.CHAT_STRUCTURE_INVALID,
        TranscriptQualityKind.BLOCKER,
        "The reviewed transcript is missing a required CHAT structural marker.",
    ),
    TranscriptQualityCode.INVALID_TIMESTAMP_RANGE: TranscriptQualityIssue(
        TranscriptQualityCode.INVALID_TIMESTAMP_RANGE,
        TranscriptQualityKind.BLOCKER,
        "A represented timestamp range is not strictly increasing.",
    ),
    TranscriptQualityCode.TIMESTAMP_ORDER_INVALID: TranscriptQualityIssue(
        TranscriptQualityCode.TIMESTAMP_ORDER_INVALID,
        TranscriptQualityKind.BLOCKER,
        "Represented transcript segments are not ordered by start time.",
    ),
    TranscriptQualityCode.CHAT_ROUND_TRIP_FAILED: TranscriptQualityIssue(
        TranscriptQualityCode.CHAT_ROUND_TRIP_FAILED,
        TranscriptQualityKind.BLOCKER,
        "The maintained CHAT subset did not survive semantic round-trip verification.",
    ),
    TranscriptQualityCode.PROFILE_VERSION_MISMATCH: TranscriptQualityIssue(
        TranscriptQualityCode.PROFILE_VERSION_MISMATCH,
        TranscriptQualityKind.BLOCKER,
        "The request versions do not match the implemented transcript analysis profile.",
    ),
    TranscriptQualityCode.INPUT_CHECKSUM_MISMATCH: TranscriptQualityIssue(
        TranscriptQualityCode.INPUT_CHECKSUM_MISMATCH,
        TranscriptQualityKind.BLOCKER,
        "The reviewed transcript bytes do not match the submitted content checksum.",
    ),
    TranscriptQualityCode.UNSUPPORTED_INPUT_KIND: TranscriptQualityIssue(
        TranscriptQualityCode.UNSUPPORTED_INPUT_KIND,
        TranscriptQualityKind.BLOCKER,
        "This analysis accepts reviewed transcript references only.",
    ),
    TranscriptQualityCode.SHORT_SAMPLE: TranscriptQualityIssue(
        TranscriptQualityCode.SHORT_SAMPLE,
        TranscriptQualityKind.LIMITATION,
        "The reviewed child sample is short; descriptive values may be unstable.",
    ),
    TranscriptQualityCode.UNMAPPED_SPEAKER: TranscriptQualityIssue(
        TranscriptQualityCode.UNMAPPED_SPEAKER,
        TranscriptQualityKind.LIMITATION,
        "A non-child speaker has an unrecognized role and is excluded from child features.",
    ),
}


@dataclass(frozen=True)
class TranscriptAnalysisProfile:
    pipeline_version: str
    feature_definition_version: str
    tokenizer_version: str
    quality_rule_version: str
    tokenizer_vocabulary_checksum_sha256: str
    profile_checksum_sha256: str
    feature_names: tuple[str, ...]
    limitations: tuple[str, ...]

    def quality_issue(self, code: TranscriptQualityCode) -> TranscriptQualityIssue:
        return _QUALITY_ISSUES[code]

    def to_dict(self) -> dict[str, object]:
        return {
            "pipeline_version": self.pipeline_version,
            "feature_definition_version": self.feature_definition_version,
            "tokenizer_version": self.tokenizer_version,
            "quality_rule_version": self.quality_rule_version,
            "tokenizer_vocabulary_checksum_sha256": self.tokenizer_vocabulary_checksum_sha256,
            "profile_checksum_sha256": self.profile_checksum_sha256,
            "feature_names": list(self.feature_names),
            "limitations": list(self.limitations),
        }


def transcript_analysis_profile() -> TranscriptAnalysisProfile:
    vocabulary_checksum = _checksum(list(_THAI_VOCABULARY))
    unsigned = {
        "pipeline_version": TRANSCRIPT_PIPELINE_VERSION,
        "feature_definition_version": FEATURE_DEFINITION_VERSION,
        "tokenizer_version": THAI_TOKENIZER_VERSION,
        "quality_rule_version": TRANSCRIPT_QA_VERSION,
        "tokenizer_vocabulary_checksum_sha256": vocabulary_checksum,
        "feature_definitions": _FEATURE_DEFINITIONS,
        "tokenizer_rules": {
            "unicode_normalization": "NFC",
            "latin_case": "lowercase",
            "thai_segmentation": "explicit longest-match vocabulary; preserve unknown runs",
            "excluded_chat_tokens": sorted(_UNINTELLIGIBLE),
        },
        "quality_rules": {
            code.value: {"kind": issue.kind.value, "message": issue.message}
            for code, issue in sorted(_QUALITY_ISSUES.items(), key=lambda item: item[0].value)
        },
    }
    return TranscriptAnalysisProfile(
        pipeline_version=TRANSCRIPT_PIPELINE_VERSION,
        feature_definition_version=FEATURE_DEFINITION_VERSION,
        tokenizer_version=THAI_TOKENIZER_VERSION,
        quality_rule_version=TRANSCRIPT_QA_VERSION,
        tokenizer_vocabulary_checksum_sha256=vocabulary_checksum,
        profile_checksum_sha256=_checksum(unsigned),
        feature_names=tuple(_FEATURE_DEFINITIONS),
        limitations=(
            "Descriptive decision support only; no diagnostic interpretation.",
            "Thai segmentation uses a small explicit research vocabulary; "
            "unseen Thai runs remain intact.",
            "Only reviewed *CHI tiers contribute to child descriptors.",
        ),
    )


def tokenize_reviewed_text(text: str) -> list[str]:
    """Tokenize mixed Thai/Latin reviewed text without runtime model downloads."""

    normalized = unicodedata.normalize("NFC", _CHAT_CODE_RE.sub(" ", str(text or "")))
    tokens: list[str] = []
    for part in _TOKEN_PART_RE.findall(normalized):
        lowered = part.lower()
        if lowered in _UNINTELLIGIBLE:
            continue
        if not _has_thai(part):
            tokens.append(lowered)
            continue
        tokens.extend(_segment_thai(part))
    return tokens


def analyze_reviewed_chat(
    request: AnalysisRequest,
    chat_text: str,
    *,
    analyzed_at: datetime | None = None,
) -> AnalysisResult:
    """Return deterministic child-only descriptors through the shared contract."""

    timestamp = analyzed_at or datetime.now(timezone.utc)
    profile = transcript_analysis_profile()
    provenance = AnalysisProvenance(
        pipeline_version=request.pipeline_version,
        feature_schema_version=request.feature_schema_version,
        analyzed_at=timestamp,
        input_ref=request.input.input_ref,
        session_ref=request.input.session_ref,
        model_version=None,
    )
    if request.input.input_kind is not AnalysisInputKind.REVIEWED_TRANSCRIPT:
        return _unavailable(
            AnalysisStatus.FAILED,
            provenance,
            TranscriptQualityCode.UNSUPPORTED_INPUT_KIND,
        )
    if (
        request.pipeline_version != profile.pipeline_version
        or request.feature_schema_version != profile.feature_definition_version
    ):
        return _unavailable(
            AnalysisStatus.FAILED,
            provenance,
            TranscriptQualityCode.PROFILE_VERSION_MISMATCH,
        )
    if (
        request.input.content_sha256 is not None
        and sha256(chat_text.encode("utf-8")).hexdigest() != request.input.content_sha256
    ):
        return _unavailable(
            AnalysisStatus.FAILED,
            provenance,
            TranscriptQualityCode.INPUT_CHECKSUM_MISMATCH,
        )

    source_transcript = parse_cha_text(chat_text, file_id=request.input.input_ref)
    if not all(marker in source_transcript.headers for marker in ("@UTF8", "@Begin", "@End")):
        return _unavailable(
            AnalysisStatus.INSUFFICIENT_DATA,
            provenance,
            TranscriptQualityCode.CHAT_STRUCTURE_INVALID,
        )
    round_trip = verify_cha_round_trip(chat_text, file_id=request.input.input_ref)
    if not round_trip.ok:
        return _unavailable(
            AnalysisStatus.FAILED,
            provenance,
            TranscriptQualityCode.CHAT_ROUND_TRIP_FAILED,
        )
    transcript = round_trip.document
    for utterance in transcript.utterances:
        if (
            utterance.start_ms is not None
            and utterance.end_ms is not None
            and utterance.start_ms >= utterance.end_ms
        ):
            return _unavailable(
                AnalysisStatus.INSUFFICIENT_DATA,
                provenance,
                TranscriptQualityCode.INVALID_TIMESTAMP_RANGE,
            )
    ordered_start_times = [
        utterance.start_ms
        for utterance in transcript.utterances
        if utterance.start_ms is not None
    ]
    if any(
        current > following
        for current, following in zip(ordered_start_times, ordered_start_times[1:])
    ):
        return _unavailable(
            AnalysisStatus.INSUFFICIENT_DATA,
            provenance,
            TranscriptQualityCode.TIMESTAMP_ORDER_INVALID,
        )

    child = [item for item in transcript.utterances if item.speaker_code == "CHI"]
    if not child:
        return _unavailable(
            AnalysisStatus.INSUFFICIENT_DATA,
            provenance,
            TranscriptQualityCode.NO_CHILD_UTTERANCES,
        )

    warnings: list[str] = []
    if len(child) < 2:
        warnings.append(TranscriptQualityCode.SHORT_SAMPLE.value)
    if any(
        item.speaker_role == "other"
        for item in transcript.utterances
        if item.speaker_code != "CHI"
    ):
        warnings.append(TranscriptQualityCode.UNMAPPED_SPEAKER.value)

    child_tokens = [
        token
        for utterance in child
        for token in tokenize_reviewed_text(utterance.normalized_text)
    ]
    if not child_tokens:
        return _unavailable(
            AnalysisStatus.INSUFFICIENT_DATA,
            provenance,
            TranscriptQualityCode.NO_CHILD_CONTENT,
        )
    unique_count = len(set(child_tokens))
    token_count = len(child_tokens)
    utterance_count = len(child)
    return AnalysisResult(
        status=AnalysisStatus.COMPLETED,
        provenance=provenance,
        feature_values={
            "child_utterance_count": utterance_count,
            "child_token_count": token_count,
            "child_unique_token_count": unique_count,
            "mean_child_tokens_per_utterance": round(token_count / utterance_count, 4),
            "child_type_token_ratio": round(unique_count / token_count, 4) if token_count else 0.0,
            "analysis_profile_checksum_sha256": profile.profile_checksum_sha256,
            "input_semantic_checksum_sha256": semantic_cha_checksum(transcript),
        },
        warnings=tuple(warnings),
    )


def _unavailable(
    status: AnalysisStatus,
    provenance: AnalysisProvenance,
    code: TranscriptQualityCode,
) -> AnalysisResult:
    issue = _QUALITY_ISSUES[code]
    return AnalysisResult(
        status=status,
        provenance=provenance,
        abstention_reason=f"{issue.code.value}: {issue.message}",
    )


def _segment_thai(value: str) -> list[str]:
    output: list[str] = []
    position = 0
    while position < len(value):
        match = next((word for word in _THAI_VOCABULARY if value.startswith(word, position)), None)
        if match is not None:
            output.append(match)
            position += len(match)
            continue
        end = position + 1
        while end < len(value) and not any(
            value.startswith(word, end) for word in _THAI_VOCABULARY
        ):
            end += 1
        output.append(value[position:end])
        position = end
    return output


def _has_thai(value: str) -> bool:
    return any("\u0e00" <= character <= "\u0e7f" for character in value)


def _checksum(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()
