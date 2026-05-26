"""Lightweight checks for the shared 14-feature model schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_schema import FEATURES  # noqa: E402


def main() -> int:
    df = pd.read_csv(PROJECT_ROOT / "data" / "combined_features.csv")
    missing = [feature for feature in FEATURES if feature not in df.columns]
    assert not missing, f"combined_features.csv missing features: {missing}"
    assert len(FEATURES) == 14, f"expected 14 features, got {len(FEATURES)}"
    assert FEATURES[-3:] == [
        "echolalia_count",
        "echolalia_ratio",
        "pronoun_reversal_count",
    ]

    artifact = PROJECT_ROOT / "artifacts" / "feature_schema.json"
    if artifact.exists():
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        assert payload["features"] == FEATURES, "artifact feature order drifted"

    print("[ok] shared feature schema is aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
