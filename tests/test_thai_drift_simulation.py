"""
Unit test suite for validating the Thai ASR drift simulation data.
Verifies JSON schema integrity, numeric constraints, and drift trend consistency.
"""

import json
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "presentation-dashboard" / "src" / "data" / "thai_validation_drift.json"

@pytest.fixture
def drift_data():
    assert DATA_PATH.exists(), f"Simulated data file does not exist at: {DATA_PATH}"
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def test_json_structure(drift_data):
    # Verify main sections exist
    required_keys = {"metadata", "scatter_data", "drift_summary", "error_distribution"}
    assert required_keys.issubset(drift_data.keys()), "Missing critical keys in simulation data JSON"

def test_metadata(drift_data):
    meta = drift_data["metadata"]
    assert "n_cases" in meta
    assert meta["n_cases"] == 40
    assert "generated_at" in meta

def test_scatter_data_cases(drift_data):
    scatter = drift_data["scatter_data"]
    assert len(scatter) == 40
    
    # Check individual case fields
    groups = {"TD", "ASD", "DD"}
    for item in scatter:
        assert "case_id" in item
        assert item["case_id"].startswith("TH-")
        assert "group" in item
        assert item["group"] in groups
        
        # Verify gold speech metrics are positive and bounded
        assert 0.5 <= item["gold_mlu"] <= 6.0
        assert 0.2 <= item["gold_ttr"] <= 0.8
        assert 0.0 <= item["gold_echolalia"] <= 0.6
        
        # Check simulated WER tiers
        for tier in ["wer_10", "wer_25", "wer_40"]:
            assert tier in item
            asr = item[tier]
            assert "asr_mlu" in asr
            assert "asr_ttr" in asr
            assert "asr_echolalia" in asr
            
            assert 0.1 <= asr["asr_mlu"] <= 6.0
            assert 0.2 <= asr["asr_ttr"] <= 1.0
            assert 0.0 <= asr["asr_echolalia"] <= 0.6

def test_drift_summary_metrics(drift_data):
    summary = drift_data["drift_summary"]
    assert len(summary) == 3
    
    # Check tiers and error trends
    summary_by_wer = {item["wer_value"]: item for item in summary}
    assert set(summary_by_wer.keys()) == {10, 25, 40}
    
    s_10 = summary_by_wer[10]
    s_25 = summary_by_wer[25]
    s_40 = summary_by_wer[40]
    
    # Verify MLU MAE increases monotonically with WER
    assert s_10["mlu_mae"] < s_25["mlu_mae"] < s_40["mlu_mae"]
    
    # Verify TTR MAE increases monotonically with WER due to spelling noise
    assert s_10["ttr_mae"] < s_25["ttr_mae"] < s_40["ttr_mae"]
    
    # MLU bias should be negative (ASR misses words)
    assert s_10["mlu_bias"] < 0
    assert s_25["mlu_bias"] < 0
    assert s_40["mlu_bias"] < 0
    
    # TTR bias should be positive (ASR spelling errors inflate word types)
    assert s_10["ttr_bias"] > 0
    assert s_25["ttr_bias"] > 0
    assert s_40["ttr_bias"] > 0

def test_error_distribution_details(drift_data):
    errors = drift_data["error_distribution"]
    assert len(errors) >= 3
    
    required_error_keys = {"error_type", "frequency", "effect", "solution"}
    for err in errors:
        assert required_error_keys.issubset(err.keys())
        assert isinstance(err["frequency"], int)
        assert err["frequency"] > 0
        
        # Enforce descriptive terms, block diagnostic terms in errors
        for val in [err["error_type"], err["effect"], err["solution"]]:
            lower_val = val.lower()
            assert "วินิจฉัย" not in lower_val, f"Diagnostic terms found in: {val}"
            assert "เกณฑ์มาตรฐาน" not in lower_val, f"Diagnostic claims found in: {val}"
