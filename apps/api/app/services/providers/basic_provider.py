"""
providers/basic_provider.py
----------------------------
BasicFeatureProvider — rule-based language sample feature extraction.

Computes descriptive linguistic features from a CHAT-parsed Transcript
using the utterance list only (no external binary required).

All features are labelled as "review cues" or "descriptive counts";
none carry a diagnostic interpretation.  Clinical interpretation requires
a qualified therapist.

Feature schema version: features-basic-v0.7
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Sequence

from app.schemas.clinical import (
    FeatureDefinition,
    FeatureValue,
    Transcript,
    Utterance,
)
from app.services.providers.base import (
    BaseFeatureProvider,
    FeatureExtractionResult,
    ProviderAvailability,
)


_CAUTION = (
    "This value is a descriptive language sample measure extracted by an "
    "automated prototype. It must not be used for diagnosis. Therapist "
    "interpretation is required."
)
_SCHEMA_VERSION = "features-basic-v0.7"
_PROVIDER_ID = "basic_feature_provider"
_PROVIDER_NAME = "BasicFeatureProvider"
_PROVIDER_VERSION = "v0.7.0"

# Minimum child utterances below which we set insufficient_data=True
_MIN_CHILD_UTTS = 3


# ---------------------------------------------------------------------------
# Feature definitions catalogue
# ---------------------------------------------------------------------------

_DEFINITIONS: list[FeatureDefinition] = [
    FeatureDefinition(
        feature_name="total_utterance_count",
        display_name="Total Utterance Count",
        description="Total number of utterances in the transcript across all speakers.",
        value_type="integer",
        unit="utterances",
        calculation_method="Count of all Utterance objects in the transcript.",
        required_inputs=["utterances"],
        limitations=["Does not exclude unintelligible utterances."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="child_utterance_count",
        display_name="Child Utterance Count",
        description="Number of utterances attributed to the CHI speaker.",
        value_type="integer",
        unit="utterances",
        calculation_method="Count of utterances where speaker == 'CHI'.",
        required_inputs=["utterances"],
        limitations=["Requires correct speaker diarization."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="adult_utterance_count",
        display_name="Adult Utterance Count",
        description="Number of utterances attributed to non-CHI, non-UNK speakers.",
        value_type="integer",
        unit="utterances",
        calculation_method="Count of utterances where speaker not in {CHI, UNK}.",
        required_inputs=["utterances"],
        limitations=["Requires correct speaker diarization."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="total_word_count",
        display_name="Total Word Count (Child)",
        description="Total word tokens produced by the CHI speaker, excluding xxx/yyy/www placeholders.",
        value_type="integer",
        unit="words",
        calculation_method="Tokenise CHI utterances; exclude xxx, yyy, www.",
        required_inputs=["utterances"],
        limitations=["Word boundaries defined by \\w+ regex; does not handle clitics."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="number_of_different_words",
        display_name="Number of Different Words (NDW)",
        description="Count of unique word types produced by the CHI speaker.",
        value_type="integer",
        unit="words",
        calculation_method="Unique lower-cased tokens from CHI utterances (excluding xxx/yyy/www).",
        required_inputs=["utterances"],
        numerator_definition="Number of distinct token types",
        denominator_definition=None,
        limitations=["No lemmatisation; 'go' and 'going' count separately."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="type_token_ratio",
        display_name="Type–Token Ratio (TTR)",
        description="NDW divided by total word tokens. Measures lexical diversity.",
        value_type="ratio",
        unit="ratio",
        calculation_method="NDW / total_word_count",
        required_inputs=["utterances"],
        numerator_definition="number_of_different_words",
        denominator_definition="total_word_count",
        default_thresholds={"low": 0.4, "high": 0.8},
        limitations=["Sensitive to sample length; compare same-length samples only."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="mean_length_of_utterance_words",
        display_name="MLU (Words)",
        description="Mean number of word tokens per CHI utterance.",
        value_type="float",
        unit="words per utterance",
        calculation_method="total_word_count / child_utterance_count",
        required_inputs=["utterances"],
        numerator_definition="total_word_count",
        denominator_definition="child_utterance_count",
        limitations=["Word-based MLU; morpheme-based MLU requires %mor tier (unavailable)."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="mean_length_of_utterance_morphemes",
        display_name="MLU (Morphemes)",
        description="Mean number of morphemes per CHI utterance. Requires %mor dependent tier.",
        value_type="string",
        unit="morphemes",
        calculation_method="Not available — requires %mor tier.",
        required_inputs=["%mor dependent tier"],
        limitations=["Not computed by BasicFeatureProvider; requires CLAN/MOR."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="unintelligible_ratio",
        display_name="Unintelligible Utterance Ratio",
        description="Proportion of all utterances marked as unintelligible.",
        value_type="ratio",
        unit="ratio",
        calculation_method="count(unintelligible utterances) / total_utterance_count",
        required_inputs=["utterances"],
        numerator_definition="Utterances where unintelligible=True",
        denominator_definition="total_utterance_count",
        limitations=["Depends on accurate unintelligibility marking during review."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="unknown_speaker_ratio",
        display_name="Unknown Speaker Ratio",
        description="Proportion of utterances attributed to UNK speaker.",
        value_type="ratio",
        unit="ratio",
        calculation_method="count(speaker==UNK) / total_utterance_count",
        required_inputs=["utterances"],
        numerator_definition="Utterances where speaker == 'UNK'",
        denominator_definition="total_utterance_count",
        limitations=["High values indicate poor diarization; treat features with caution."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="question_ratio",
        display_name="Question Ratio (Child)",
        description="Proportion of CHI utterances containing a '?' character.",
        value_type="ratio",
        unit="ratio",
        calculation_method="count(CHI utterances with '?') / child_utterance_count",
        required_inputs=["utterances"],
        numerator_definition="CHI utterances containing '?'",
        denominator_definition="child_utterance_count",
        limitations=["Punctuation-based heuristic only."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="repetition_marker_count",
        display_name="Repetition Marker Count",
        description="Count of CHAT retracing markers [/] or immediate word repetitions in CHI utterances.",
        value_type="integer",
        unit="markers",
        calculation_method="Regex search for [/] and (word word) patterns in CHI utterances.",
        required_inputs=["utterances"],
        limitations=["Heuristic; may miss multi-word repetitions across utterances."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="pronoun_reversal_cue_count",
        display_name="Pronoun Reversal Cue Count",
        description="Review cue count for atypical pronoun usage patterns in CHI utterances.",
        value_type="integer",
        unit="review cues",
        calculation_method="Regex match for patterns like 'you am', 'me am', 'my want', 'i are'.",
        required_inputs=["utterances"],
        limitations=["Simple heuristic; high false-negative rate. Review cue only."],
        clinical_interpretation_caution="Review cue only; not diagnostic. Therapist context required.",
    ),
    FeatureDefinition(
        feature_name="echolalia_cue_count",
        display_name="Echolalia Cue Count",
        description="Count of CHI utterances that immediately echo the preceding adult utterance verbatim.",
        value_type="integer",
        unit="review cues",
        calculation_method="Count CHI utterances that match the preceding non-CHI utterance (lowercased, stripped).",
        required_inputs=["utterances"],
        limitations=["Detects only immediate verbatim echoes; delayed echolalia not captured."],
        clinical_interpretation_caution="Review cue only; therapist context required.",
    ),
    FeatureDefinition(
        feature_name="limited_reciprocal_question_cue",
        display_name="Limited Reciprocal Question Cue",
        description="Boolean flag: True if the child produced no questions and at least 3 utterances.",
        value_type="boolean",
        unit="boolean",
        calculation_method="question_ratio == 0 AND child_utterance_count >= 3",
        required_inputs=["utterances"],
        limitations=["Coarse flag; short samples may produce false positives."],
        clinical_interpretation_caution="Review cue only; not diagnostic.",
    ),
    FeatureDefinition(
        feature_name="repetitive_phrase_cue",
        display_name="Repetitive Phrase Cue Count",
        description="Count of immediate word-pair repetitions within CHI utterances.",
        value_type="integer",
        unit="review cues",
        calculation_method="Regex \\b(\\w+)\\s+\\1\\b applied to CHI utterances.",
        required_inputs=["utterances"],
        limitations=["Only captures adjacent single-word repetitions."],
        clinical_interpretation_caution="Review cue only; not diagnostic.",
    ),
    FeatureDefinition(
        feature_name="atypical_response_cue",
        display_name="Atypical Response Cue",
        description="Placeholder for manual therapist annotation of atypical responses.",
        value_type="string",
        unit="review status",
        calculation_method="Not automated; always returns 'needs_context'.",
        required_inputs=["therapist_review"],
        limitations=["Cannot be computed automatically from transcripts alone."],
        clinical_interpretation_caution="Requires therapist qualitative assessment.",
    ),
]


# ---------------------------------------------------------------------------
# BasicFeatureProvider
# ---------------------------------------------------------------------------

class BasicFeatureProvider(BaseFeatureProvider):
    """
    Rule-based feature provider requiring only the utterance list.

    No external binaries needed → always available.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def provider_id(self) -> str:
        return _PROVIDER_ID

    @property
    def provider_name(self) -> str:
        return _PROVIDER_NAME

    @property
    def provider_version(self) -> str:
        return _PROVIDER_VERSION

    @property
    def feature_schema_version(self) -> str:
        return _SCHEMA_VERSION

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_provider_metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "feature_schema_version": self.feature_schema_version,
            "description": (
                "Rule-based language sample feature provider. "
                "Computes descriptive linguistic features from CHAT-parsed "
                "transcripts using utterance text and speaker labels only."
            ),
            "required_inputs": ["Transcript.utterances"],
            "external_dependencies": [],
            "limitations": [
                "Does not support morpheme-based MLU (requires %mor tier / CLAN).",
                "All features are descriptive; none are diagnostic.",
                "Atypical-response cue cannot be automated.",
            ],
            "feature_count": len(_DEFINITIONS),
            "available": True,
        }

    def check_availability(self) -> ProviderAvailability:
        # BasicFeatureProvider has no external dependencies.
        return ProviderAvailability(available=True, reason="No external dependencies.")

    def get_feature_definitions(self) -> list[FeatureDefinition]:
        return list(_DEFINITIONS)

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def extract_features(
        self,
        transcript: Transcript,
        config: dict | None = None,
    ) -> FeatureExtractionResult:
        cfg = config or {}
        now = datetime.now(timezone.utc)
        warnings: list[str] = []

        # ---- Partition utterances ----------------------------------------
        all_utts = transcript.utterances
        child = [u for u in all_utts if str(u.speaker).upper() == "CHI"]
        adult = [u for u in all_utts if str(u.speaker).upper() not in {"CHI", "UNK"}]
        unk_count = sum(1 for u in all_utts if str(u.speaker).upper() == "UNK")

        # ---- Insufficient data guard -------------------------------------
        insufficient = len(child) < _MIN_CHILD_UTTS
        if insufficient:
            warnings.append(
                f"Fewer than {_MIN_CHILD_UTTS} child utterances found "
                f"({len(child)}). Feature reliability is reduced."
            )

        # ---- Tokenise -------------------------------------------------------
        child_token_lists = [_tokens(u.text) for u in child]
        flat = [tok for toks in child_token_lists for tok in toks]
        unique = set(flat)

        # ---- Denominators (guard against zero division) ----------------------
        total_utts = len(all_utts) or 1
        child_count = len(child) or 1  # used only in ratio denominators
        flat_count = len(flat) or 1

        # ---- UNK speaker warning --------------------------------------------
        unk_ratio = unk_count / total_utts
        if unk_ratio > 0.2:
            warnings.append(
                f"High unknown-speaker ratio ({unk_ratio:.0%}). "
                "Speaker diarization may be unreliable."
            )

        # ---- Build FeatureValue list ----------------------------------------
        def fv(
            name: str,
            value: float | int | str | bool | None,
            *,
            unit: str = "count",
            value_type: str = "count",
            numerator: float | int | None = None,
            denominator: float | int | None = None,
            insufficient_data: bool = False,
            hint: str = "Descriptive language sample value; therapist interpretation required.",
            extra_warnings: list[str] | None = None,
        ) -> FeatureValue:
            return FeatureValue(
                name=name,
                value=value,
                unit=unit,
                value_type=value_type,
                numerator=numerator,
                denominator=denominator,
                provider_name=_PROVIDER_NAME,
                feature_version=_SCHEMA_VERSION,
                transcript_id=transcript.transcript_id,
                session_id=transcript.session_id,
                computed_at=now,
                insufficient_data=insufficient_data or insufficient,
                interpretation_hint=hint,
                warnings=extra_warnings or [],
            )

        values: list[FeatureValue] = [
            fv("total_utterance_count", len(all_utts), unit="utterances", value_type="integer"),
            fv("child_utterance_count", len(child), unit="utterances", value_type="integer"),
            fv("adult_utterance_count", len(adult), unit="utterances", value_type="integer"),
            fv(
                "total_word_count",
                len(flat),
                unit="words",
                value_type="integer",
            ),
            fv(
                "number_of_different_words",
                len(unique),
                unit="words",
                value_type="integer",
            ),
            fv(
                "type_token_ratio",
                round(len(unique) / flat_count, 4) if flat else 0,
                unit="ratio",
                value_type="ratio",
                numerator=len(unique),
                denominator=len(flat) if flat else 0,
            ),
            fv(
                "mean_length_of_utterance_words",
                round(len(flat) / child_count, 4) if child else 0,
                unit="words per utterance",
                value_type="float",
                numerator=len(flat),
                denominator=len(child) if child else 0,
            ),
            fv(
                "mean_length_of_utterance_morphemes",
                "not_available",
                unit="morphemes",
                value_type="string",
                insufficient_data=True,
                hint="Morpheme-based MLU requires %mor tier (CLAN). Not computed by BasicFeatureProvider.",
                extra_warnings=["MLU-morphemes requires %mor dependent tier; not available."],
            ),
            fv(
                "unintelligible_ratio",
                round(
                    sum(1 for u in all_utts if u.unintelligible) / total_utts, 4
                ),
                unit="ratio",
                value_type="ratio",
                numerator=sum(1 for u in all_utts if u.unintelligible),
                denominator=total_utts,
            ),
            fv(
                "unknown_speaker_ratio",
                round(unk_count / total_utts, 4),
                unit="ratio",
                value_type="ratio",
                numerator=unk_count,
                denominator=total_utts,
            ),
            fv(
                "question_ratio",
                round(
                    sum(1 for u in child if "?" in u.text) / child_count, 4
                ) if child else 0,
                unit="ratio",
                value_type="ratio",
                numerator=sum(1 for u in child if "?" in u.text),
                denominator=len(child) if child else 0,
            ),
            fv(
                "repetition_marker_count",
                sum(
                    len(re.findall(r"\[/\]|\b(\w+)\s+\1\b", u.text, re.I))
                    for u in child
                ),
                unit="markers",
                value_type="integer",
                hint="Review cue only; not diagnostic.",
            ),
            fv(
                "pronoun_reversal_cue_count",
                sum(_pronoun_cue(u.text) for u in child),
                unit="review cues",
                value_type="integer",
                hint="Review cue only; not diagnostic. Therapist context required.",
            ),
            fv(
                "echolalia_cue_count",
                _echolalia_cues(all_utts),
                unit="review cues",
                value_type="integer",
                hint="Review cue only; therapist context required.",
            ),
            fv(
                "limited_reciprocal_question_cue",
                sum(1 for u in child if "?" in u.text) == 0 and len(child) >= _MIN_CHILD_UTTS,
                unit="boolean",
                value_type="boolean",
                hint="Review cue only; not diagnostic.",
            ),
            fv(
                "repetitive_phrase_cue",
                sum(
                    len(re.findall(r"\b(\w+)\s+\1\b", u.text, re.I))
                    for u in child
                ),
                unit="review cues",
                value_type="integer",
                hint="Review cue only; not diagnostic.",
            ),
            fv(
                "atypical_response_cue",
                "needs_context",
                unit="review status",
                value_type="string",
                hint="Cannot be automated. Requires therapist qualitative assessment.",
                extra_warnings=["atypical_response_cue cannot be computed automatically."],
            ),
        ]

        return FeatureExtractionResult(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            feature_schema_version=self.feature_schema_version,
            tokenizer_version=None,
            transcript_id=transcript.transcript_id,
            session_id=transcript.session_id,
            computed_at=now,
            values=values,
            warnings=warnings,
            insufficient_data=insufficient,
            valid=True,
            config_used=cfg,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_STOPWORDS = {"xxx", "yyy", "www"}


def _tokens(text: str) -> list[str]:
    """Tokenise utterance text, excluding unintelligibility placeholders."""
    return [
        tok.lower()
        for tok in re.findall(r"[\w']+", text)
        if tok.lower() not in _STOPWORDS
    ]


def _pronoun_cue(text: str) -> int:
    """Count atypical pronoun usage patterns in a single utterance."""
    return len(re.findall(r"\b(?:you am|me am|my want|i are)\b", text, re.I))


def _echolalia_cues(utterances: Sequence[Utterance]) -> int:
    """
    Count CHI utterances that are verbatim copies of the immediately
    preceding non-CHI utterance (lowercased, whitespace-stripped).
    """
    count = 0
    previous_adult = ""
    for utt in utterances:
        speaker = str(utt.speaker).upper()
        if speaker == "CHI" and previous_adult and utt.text.strip().lower() == previous_adult:
            count += 1
        elif speaker != "CHI":
            previous_adult = utt.text.strip().lower()
    return count
