from __future__ import annotations

from pathlib import Path
import sys

import joblib
import pandas as pd
import pytest
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.cha.parser import parse_cha_file, parse_cha_text  # noqa: E402
from packages.features.transcript_features import extract_transcript_features  # noqa: E402
from packages.ml.predict import predict_reference_cohort_similarity  # noqa: E402
from packages.ml.train_model import build_dataset_from_metadata, validate_training_dataset  # noqa: E402
from src.feature_schema import FEATURES  # noqa: E402


CHAT_TEXT = """@UTF8
@Begin
@Languages:\teng
@Participants:\tCHI Child Target_Child, INV Investigator Investigator, MOT Mother Mother
@ID:\teng|Example|CHI|4;00.00|male|||Target_Child|||
@ID:\teng|Example|INV|||||Investigator|||
*INV:\twhat do you want ? \x150_1000\x15
*CHI:\tyou want cookie . \x151500_2500\x15
*MOT:\tgood talking . \x152800_3400\x15
*CHI:\tcookie cookie +... \x153700_4300\x15
@End
"""


def test_cha_parser_extracts_speaker_roles_timestamps_and_tokens(tmp_path):
    cha_path = tmp_path / "sample.cha"
    cha_path.write_text(CHAT_TEXT, encoding="utf-8")

    parsed = parse_cha_file(cha_path)

    assert parsed.file_id == "sample"
    assert len(parsed.utterances) == 4
    child = parsed.utterances[1]
    assert child.speaker_code == "CHI"
    assert child.speaker_role == "child"
    assert child.start_ms == 1500
    assert child.end_ms == 2500
    assert child.raw_text.startswith("you want cookie")
    assert child.normalized_text == "you want cookie"
    assert child.tokens == ["you", "want", "cookie"]


def test_transcript_feature_aliases_and_extended_indicators():
    parsed = parse_cha_text(CHAT_TEXT, file_id="sample")
    features = extract_transcript_features(parsed, age_months=48)

    assert features["canonical_features"]["total_utterances"] == 2
    assert features["feature_aliases"]["child_utterance_count"] == 2
    assert features["feature_aliases"]["mean_length_utterance_child"] == features["canonical_features"]["mluw"]
    assert features["optional_indicators"]["adult_utterance_count"] == 2
    assert features["optional_indicators"]["child_adult_turn_ratio"] == 1.0
    assert features["optional_indicators"]["response_ratio"] > 0
    assert features["optional_indicators"]["repetitive_phrase_count"] >= 1
    assert features["optional_indicators"]["incomplete_utterance_rate"] == 0.5


def test_dataset_builder_rejects_missing_labels(tmp_path):
    (tmp_path / "sample.cha").write_text(CHAT_TEXT, encoding="utf-8")
    metadata = tmp_path / "metadata.csv"
    metadata.write_text(
        "file_id,label,age,sex,language,notes\nsample,,48,male,eng,missing label\n",
        encoding="utf-8",
    )

    df = build_dataset_from_metadata(tmp_path, metadata)
    validation = validate_training_dataset(df)

    assert validation.ok is False
    assert any(error.startswith("missing_labels") for error in validation.errors)


def test_empty_and_short_transcripts_return_low_quality_features():
    parsed = parse_cha_text("@Begin\n@End\n", file_id="empty")
    features = extract_transcript_features(parsed, age_months=48)

    assert features["canonical_features"]["total_utterances"] == 0
    assert features["feature_aliases"]["child_utterance_count"] == 0


def test_prediction_output_uses_reference_similarity_language(tmp_path):
    rows = []
    for idx, label in enumerate(["ASD", "ASD", "TD", "TD"]):
        row = {feature: 0.0 for feature in FEATURES}
        row.update({
            "age_months": 48 + idx,
            "total_utterances": 8 + idx,
            "mluw": 2.0 + idx * 0.1,
            "mlu": 2.0 + idx * 0.1,
            "ttr": 0.4,
            "total_words": 30 + idx,
            "echolalia_ratio": 0.2 if label == "ASD" else 0.01,
            "question_ratio": 0.01 if label == "ASD" else 0.2,
        })
        rows.append(row)
    X = pd.DataFrame(rows, columns=FEATURES)
    y = ["ASD", "ASD", "TD", "TD"]
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(max_iter=1000)),
    ])
    model.fit(X, y)
    bundle = {
        "model": model,
        "model_version": "test-reference-model",
        "model_type": "LogisticRegression",
        "features": FEATURES,
        "classes": list(model.classes_),
    }
    model_path = tmp_path / "model.joblib"
    joblib.dump(bundle, model_path)

    result = predict_reference_cohort_similarity(rows[0], model_path=model_path, inference_status="preliminary")

    assert result["inference_status"] == "preliminary"
    assert set(result["reference_cohort_probabilities"]) == {"ASD", "TD"}
    assert "most similar" in result["plain_language_explanation"]
    assert "not a diagnosis" in result["plain_language_explanation"]
    assert any(warning["code"] == "PRELIMINARY_TRANSCRIPT" for warning in result["safety_warnings"])
