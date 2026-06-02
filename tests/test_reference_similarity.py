from __future__ import annotations

import sys
from pathlib import Path
import pytest
import pandas as pd
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.feature_schema import FEATURES
from src.reference_engine import ReferenceEngine, assert_descriptive_wording

def _feature_payload(value: float = 10.0) -> dict[str, float]:
    return {feature: value for feature in FEATURES}

def _write_reference_csvs(tmp_path: Path) -> tuple[Path, Path]:
    feature_rows = []
    # Create enough rows for 5 TD and 3 ASD
    for group, base, n in [("ASD", 10, 3), ("TD", 20, 6)]:
        for offset in range(n):
            row = {
                "language": "eng",
                "age_band_12mo": "48-59",
                "task_type": "toyplay",
                "group": group,
                "corpus": "Synthetic",
                "transcript_uid": f"uid_{group}_{offset}",
            }
            row.update(_feature_payload(base + offset))
            feature_rows.append(row)

    features_path = tmp_path / "features.csv"
    cohorts_path = tmp_path / "cohorts.csv"
    pd.DataFrame(feature_rows).to_csv(features_path, index=False)
    
    # Cohorts csv (simple skeleton)
    cohort_rows = []
    for group in ["ASD", "TD"]:
        cohort_rows.append({
            "age_band_12mo": "48-59",
            "task_type": "toyplay",
            "group": group,
            "cohort_n": 5 if group == "TD" else 3,
            "confidence_flag": "ok",
            "corpora": "Synthetic",
            "design_types": "cross",
        })
    pd.DataFrame(cohort_rows).to_csv(cohorts_path, index=False)
    return features_path, cohorts_path

def test_similarity_calculation(tmp_path):
    features_path, cohorts_path = _write_reference_csvs(tmp_path)
    engine = ReferenceEngine(features_path=features_path, cohorts_path=cohorts_path)
    
    # Test query features (same as td baseline)
    query_features = _feature_payload(21.5)
    
    results = engine.retrieve_similar_cases(
        features=query_features,
        age_months=50,
        task_type="toyplay",
        k=5
    )
    
    assert len(results) == 5
    assert results[0]["distance"] >= 0.0
    assert "transcript_uid" in results[0]
    assert "group" in results[0]
    assert "features" in results[0]
    
    # Check that distance calculations are based on matching age band and task type only
    # Let's ensure the distances are sorted
    distances = [r["distance"] for r in results]
    assert distances == sorted(distances)

def test_similarity_endpoint_auth_required():
    from src.clinical_workflow import MockClinicalRepository
    from src.therapist_backend.app import create_app
    from fastapi.testclient import TestClient

    repo = MockClinicalRepository()
    app = create_app(repo)
    client = TestClient(app)
    
    response = client.get("/api/sessions/SESSION-001/reference-similarity")
    assert response.status_code == 401

def test_similarity_endpoint_payload():
    from src.clinical_workflow import MockClinicalRepository
    from src.therapist_backend.app import create_app
    from fastapi.testclient import TestClient

    repo = MockClinicalRepository()
    app = create_app(repo)
    client = TestClient(app)
    
    response = client.get(
        "/api/sessions/SESSION-001/reference-similarity",
        headers={"X-User-Id": "user_therapist_001"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["similarity_term"] == "Reference Similarity Retrieval"
    assert len(payload["results"]) == 5
    # Check safety wording (no diagnostic words)
    text = str(payload).lower()
    assert "diagnostic" not in text
    assert "norm" not in text
    assert "benchmark" not in text
    assert "validation" not in text


