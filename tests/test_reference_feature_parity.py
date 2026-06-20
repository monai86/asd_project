from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.features.transcript_features import extract_transcript_features  # noqa: E402
from packages.ml.reference_contracts import FEATURE_TOLERANCES  # noqa: E402
from src.chat_feature_extractor import extract_chat_features  # noqa: E402


def test_golden_fixture_matches_research_and_shared_extractors():
    root = Path("tests/fixtures/reference_feature_parity")
    expected = json.loads((root / "expected.json").read_text(encoding="utf-8"))
    research = extract_chat_features(root / "english_toyplay.cha")
    shared = extract_transcript_features(
        root / "english_toyplay.cha"
    )["canonical_features"]

    assert research is not None
    for feature, rule in expected["features"].items():
        assert rule["tolerance"] == FEATURE_TOLERANCES[feature]
        assert abs(float(research[feature]) - float(shared[feature])) <= rule[
            "tolerance"
        ]
        assert abs(float(shared[feature]) - float(rule["value"])) <= rule[
            "tolerance"
        ]
