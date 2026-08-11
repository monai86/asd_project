"""v1.7.0 ASR Benchmark Contract Tests.

Validates asr_benchmark_results.json and asr_runtime_profile.json compliance.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_RESULTS_PATH = REPO_ROOT / "artifacts" / "v1.7.0" / "asr_benchmark_results.json"
RUNTIME_PROFILE_PATH = REPO_ROOT / "artifacts" / "v1.7.0" / "asr_runtime_profile.json"


def test_v170_benchmark_results_contract() -> None:
    assert BENCHMARK_RESULTS_PATH.exists(), f"Benchmark results missing at {BENCHMARK_RESULTS_PATH}"
    result = json.loads(BENCHMARK_RESULTS_PATH.read_text(encoding="utf-8"))

    assert result["fixture_manifest_checksum"]
    assert result["machine"]["cpu_model"]
    assert result["machine"]["logical_cpu_count"]
    assert result["machine"]["memory_bytes"]
    assert result["machine"]["os"]
    assert result["runtime"]["python_version"]
    assert result["runtime"]["faster_whisper_version"]
    assert result["runtime"]["ctranslate2_version"]
    assert result["runtime"]["decoder_version"]
    assert result["measurements"]["elapsed_seconds"]
    assert result["measurements"]["cpu_seconds"]
    assert result["measurements"]["peak_rss_bytes"]
    assert result["quality"]["beginning_covered"] is True
    assert result["quality"]["ending_covered"] is True
    assert result["quality"]["timestamp_integrity_passed"] is True
    assert "segment_completeness" in result["quality"]
    assert "thai_character_error_rate" in result["quality"]
    assert "mixed_language_correction_operations" in result["quality"]
    assert result["execution"]["execution_isolation_mode"]
    assert result["execution"]["warm_reuse_capability"]


def test_v170_benchmark_fails_closed_on_one_shot_warm_reuse_unavailability() -> None:
    assert BENCHMARK_RESULTS_PATH.exists()
    result = json.loads(BENCHMARK_RESULTS_PATH.read_text(encoding="utf-8"))

    if result["execution"]["warm_reuse_capability"] == "unavailable_one_shot_isolation":
        assert RUNTIME_PROFILE_PATH.exists()
        profile = json.loads(RUNTIME_PROFILE_PATH.read_text(encoding="utf-8"))
        assert profile["verified"] is False
        assert profile["timeout_seconds"] is None
        assert "warm_reuse_unavailable" in profile["blockers"]
        assert profile["status"] == "blocked_warm_reuse_unavailable"


def test_v170_runtime_profile_checksum_provenance_linkage() -> None:
    assert BENCHMARK_RESULTS_PATH.exists()
    assert RUNTIME_PROFILE_PATH.exists()

    bench_bytes = BENCHMARK_RESULTS_PATH.read_bytes()
    import hashlib
    bench_sha = hashlib.sha256(bench_bytes).hexdigest()

    bench = json.loads(bench_bytes.decode("utf-8"))
    profile = json.loads(RUNTIME_PROFILE_PATH.read_text(encoding="utf-8"))

    assert profile["benchmark_result_checksum"] == bench_sha
    assert profile["fixture_manifest_checksum"] == bench["fixture_manifest_checksum"]
    assert "wav" in profile["supported_audio_formats"]
    assert "mp3" in profile["supported_audio_formats"]
