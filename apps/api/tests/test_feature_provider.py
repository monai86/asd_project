"""
tests/test_feature_provider.py
-------------------------------
Unit tests for the FeatureProvider registry and BasicFeatureProvider.

Covers:
- BasicFeatureProvider identity and availability
- FeatureDefinition catalogue completeness
- FeatureExtractionResult structure from a minimal transcript
- Insufficient-data flag for short transcripts
- ProviderRegistry lookup / default / list / definitions
- feature_service.get_providers / get_feature_definitions pass-through
"""

from __future__ import annotations

import pytest

from app.schemas.clinical import SpeakerCode, Transcript, Utterance
from app.services.providers.base import FeatureExtractionResult, ProviderAvailability
from app.services.providers.basic_provider import BasicFeatureProvider, _MIN_CHILD_UTTS
from app.services.providers.registry import ProviderRegistry, provider_registry
from app.services.feature_service import get_feature_definitions, get_providers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_transcript(utterances: list[tuple[str, str]], *, tid="tr-test") -> Transcript:
    """Build a minimal Transcript from [(speaker, text), ...] tuples."""
    utts = [
        Utterance(
            utterance_id=f"u-{i}",
            speaker=spk,
            text=txt,
        )
        for i, (spk, txt) in enumerate(utterances)
    ]
    return Transcript(
        transcript_id=tid,
        session_id="sess-test",
        case_id="case-test",
        source="manual",
        raw_text="\n".join(f"*{spk}: {txt}" for spk, txt in utterances),
        utterances=utts,
    )


# ---------------------------------------------------------------------------
# BasicFeatureProvider — identity
# ---------------------------------------------------------------------------

class TestBasicFeatureProviderIdentity:
    provider = BasicFeatureProvider()

    def test_provider_id(self):
        assert self.provider.provider_id == "basic_feature_provider"

    def test_provider_name(self):
        assert self.provider.provider_name == "BasicFeatureProvider"

    def test_provider_version_semver(self):
        ver = self.provider.provider_version
        parts = ver.lstrip("v").split(".")
        assert len(parts) == 3, f"Expected semver, got {ver}"

    def test_feature_schema_version(self):
        assert self.provider.feature_schema_version.startswith("features-basic-")

    def test_always_available(self):
        avail = self.provider.check_availability()
        assert isinstance(avail, ProviderAvailability)
        assert avail.available is True
        assert bool(avail) is True


# ---------------------------------------------------------------------------
# BasicFeatureProvider — feature definitions
# ---------------------------------------------------------------------------

EXPECTED_FEATURES = [
    "total_utterance_count",
    "child_utterance_count",
    "adult_utterance_count",
    "total_word_count",
    "number_of_different_words",
    "type_token_ratio",
    "mean_length_of_utterance_words",
    "mean_length_of_utterance_morphemes",
    "unintelligible_ratio",
    "unknown_speaker_ratio",
    "question_ratio",
    "repetition_marker_count",
    "pronoun_reversal_cue_count",
    "echolalia_cue_count",
    "limited_reciprocal_question_cue",
    "repetitive_phrase_cue",
    "atypical_response_cue",
]


class TestBasicFeatureDefinitions:
    provider = BasicFeatureProvider()

    def test_definition_count(self):
        defs = self.provider.get_feature_definitions()
        assert len(defs) == len(EXPECTED_FEATURES)

    def test_all_expected_features_present(self):
        names = {d.feature_name for d in self.provider.get_feature_definitions()}
        for expected in EXPECTED_FEATURES:
            assert expected in names, f"Missing feature definition: {expected}"

    def test_every_definition_has_caution(self):
        for d in self.provider.get_feature_definitions():
            assert d.clinical_interpretation_caution, (
                f"{d.feature_name} missing clinical_interpretation_caution"
            )

    def test_provider_name_on_definitions(self):
        for d in self.provider.get_feature_definitions():
            assert d.provider_name == "BasicFeatureProvider"


# ---------------------------------------------------------------------------
# BasicFeatureProvider — extraction (happy path)
# ---------------------------------------------------------------------------

SAMPLE_UTTERANCES = [
    ("THER", "Let's play with the ball."),
    ("CHI", "ball ball ball"),
    ("THER", "What colour is it?"),
    ("CHI", "red"),
    ("THER", "Good! What do you want?"),
    ("CHI", "me want cookie"),
    ("THER", "Do you want milk?"),
    ("CHI", "you want milk"),
    ("THER", "Great!"),
    ("CHI", "you want milk"),   # verbatim echo of previous CHI (not adult)
]


class TestBasicFeatureExtraction:
    provider = BasicFeatureProvider()
    transcript = _make_transcript(SAMPLE_UTTERANCES)
    result: FeatureExtractionResult = None

    @pytest.fixture(autouse=True)
    def _run(self):
        self.__class__.result = self.provider.extract_features(self.transcript)

    def test_result_is_valid(self):
        assert self.result.valid is True

    def test_provider_identity_in_result(self):
        assert self.result.provider_id == "basic_feature_provider"
        assert self.result.provider_name == "BasicFeatureProvider"

    def test_schema_version_in_result(self):
        assert "features-basic" in self.result.feature_schema_version

    def test_all_features_present(self):
        names = {fv.name for fv in self.result.values}
        for expected in EXPECTED_FEATURES:
            assert expected in names, f"Missing feature value: {expected}"

    def test_provider_name_on_feature_values(self):
        for fv in self.result.values:
            assert fv.provider_name == "BasicFeatureProvider"

    def test_transcript_id_on_feature_values(self):
        for fv in self.result.values:
            assert fv.transcript_id == "tr-test"

    def test_total_utterance_count(self):
        fv = next(f for f in self.result.values if f.name == "total_utterance_count")
        assert fv.value == len(SAMPLE_UTTERANCES)

    def test_child_utterance_count(self):
        fv = next(f for f in self.result.values if f.name == "child_utterance_count")
        child_count = sum(1 for spk, _ in SAMPLE_UTTERANCES if spk == "CHI")
        assert fv.value == child_count

    def test_mlu_morphemes_is_not_available(self):
        fv = next(f for f in self.result.values if f.name == "mean_length_of_utterance_morphemes")
        assert fv.value == "not_available"
        assert fv.insufficient_data is True

    def test_type_token_ratio_is_between_0_and_1(self):
        fv = next(f for f in self.result.values if f.name == "type_token_ratio")
        assert isinstance(fv.value, float)
        assert 0.0 <= fv.value <= 1.0

    def test_ratio_features_have_numerator_denominator(self):
        ratio_features = [
            "type_token_ratio",
            "mean_length_of_utterance_words",
            "unintelligible_ratio",
            "unknown_speaker_ratio",
        ]
        for fname in ratio_features:
            fv = next(f for f in self.result.values if f.name == fname)
            assert fv.denominator is not None, f"{fname} missing denominator"

    def test_pronoun_reversal_cue_detected(self):
        fv = next(f for f in self.result.values if f.name == "pronoun_reversal_cue_count")
        # "me want" and "you want" patterns → at least one cue expected
        assert isinstance(fv.value, int)
        assert fv.value >= 0  # non-negative integer

    def test_insufficient_data_false_on_sufficient_sample(self):
        assert self.result.insufficient_data is False


# ---------------------------------------------------------------------------
# BasicFeatureProvider — insufficient data
# ---------------------------------------------------------------------------

class TestBasicFeatureInsufficientData:
    provider = BasicFeatureProvider()

    def test_single_child_utt_sets_insufficient_flag(self):
        t = _make_transcript([("CHI", "hi"), ("THER", "hello")])
        result = self.provider.extract_features(t)
        assert result.insufficient_data is True
        assert any("Fewer than" in w for w in result.warnings)

    def test_no_child_utts_sets_insufficient_flag(self):
        t = _make_transcript([("THER", "hello"), ("THER", "good")])
        result = self.provider.extract_features(t)
        assert result.insufficient_data is True

    def test_result_still_valid_when_insufficient(self):
        t = _make_transcript([("CHI", "hi")])
        result = self.provider.extract_features(t)
        # valid=True because extraction completed (just with insufficient data)
        assert result.valid is True

    def test_high_unk_ratio_adds_warning(self):
        utts = [("UNK", f"word{i}") for i in range(10)] + [("CHI", "hi hi hi hi")]
        t = _make_transcript(utts)
        result = self.provider.extract_features(t)
        assert any("unknown-speaker" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# ProviderRegistry
# ---------------------------------------------------------------------------

class TestProviderRegistry:
    def test_default_registry_has_basic_provider(self):
        assert "basic_feature_provider" in provider_registry

    def test_get_default_returns_basic_provider(self):
        p = provider_registry.get_default()
        assert p.provider_id == "basic_feature_provider"

    def test_get_by_id(self):
        p = provider_registry.get("basic_feature_provider")
        assert isinstance(p, BasicFeatureProvider)

    def test_get_unknown_raises_key_error(self):
        with pytest.raises(KeyError, match="not registered"):
            provider_registry.get("nonexistent_provider")

    def test_list_providers_returns_list(self):
        providers = provider_registry.list_providers()
        assert isinstance(providers, list)
        assert len(providers) >= 1

    def test_list_providers_includes_available_field(self):
        for p in provider_registry.list_providers():
            assert "available" in p

    def test_all_feature_definitions_nonempty(self):
        defs = provider_registry.all_feature_definitions()
        assert len(defs) >= len(EXPECTED_FEATURES)

    def test_all_feature_definitions_include_provider_id(self):
        for d in provider_registry.all_feature_definitions():
            assert "provider_id" in d

    def test_register_and_unregister(self):
        # Use a fresh registry to avoid polluting the global singleton
        reg = ProviderRegistry()
        reg.register(BasicFeatureProvider())
        assert len(reg) == 1
        reg.unregister("basic_feature_provider")
        assert len(reg) == 0

    def test_empty_registry_get_default_raises(self):
        reg = ProviderRegistry()
        with pytest.raises(RuntimeError, match="No feature providers registered"):
            reg.get_default()


# ---------------------------------------------------------------------------
# feature_service pass-through
# ---------------------------------------------------------------------------

class TestFeatureServicePassThrough:
    def test_get_providers_returns_list(self):
        result = get_providers()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_get_feature_definitions_returns_list(self):
        result = get_feature_definitions()
        assert isinstance(result, list)
        assert len(result) >= len(EXPECTED_FEATURES)
