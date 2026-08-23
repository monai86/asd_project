"""Unit tests and performance benchmarks for optimized acoustic feature extraction and diarization."""

from __future__ import annotations

import time
from pathlib import Path
import numpy as np
import pytest

from src.audio_pipeline.acoustic_profile import AcousticProfile, compute_acoustic_profile
from src.audio_pipeline.diarization import PitchHeuristicDiarizer
from src.audio_pipeline.whisper_transcribe import UtteranceSegment


def test_fast_acoustic_profile_synthetic_audio(tmp_path: Path):
    """Verify compute_acoustic_profile produces valid F0 and metrics on synthetic sine wave rapidly."""
    import soundfile as sf

    sr = 16000
    duration = 3.0  # 3 seconds of 220Hz (A3 tone)
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Sine wave 220 Hz with some silence at end
    audio = 0.5 * np.sin(2 * np.pi * 220.0 * t)
    audio[int(sr * 2.0):] = 0.0  # Last 1s silent

    test_wav = tmp_path / "test_synth_220hz.wav"
    sf.write(str(test_wav), audio, sr)

    # Warm up pass
    compute_acoustic_profile(str(test_wav))

    # Benchmark pass
    t0 = time.time()
    profile = compute_acoustic_profile(str(test_wav))
    elapsed = time.time() - t0

    assert elapsed < 0.25, f"Expected < 0.25s, took {elapsed:.3f}s"
    assert profile.duration_sec == pytest.approx(3.0, abs=0.1)
    assert profile.voiced_ratio > 0.4
    # Median F0 should be close to 220 Hz
    assert profile.f0_median_hz == pytest.approx(220.0, abs=15.0)


def test_acoustic_profile_empty_or_silent_audio(tmp_path: Path):
    """Verify acoustic profile handles silent audio safely without crashing."""
    import soundfile as sf

    sr = 16000
    audio = np.zeros(sr * 2, dtype=np.float32)  # 2 seconds of pure silence
    silent_wav = tmp_path / "silent.wav"
    sf.write(str(silent_wav), audio, sr)

    profile = compute_acoustic_profile(str(silent_wav))
    assert profile.duration_sec == pytest.approx(2.0, abs=0.1)
    assert profile.voiced_ratio == pytest.approx(0.0, abs=0.05)


def test_fast_diarization_with_precomputed_f0(tmp_path: Path):
    """Verify PitchHeuristicDiarizer assigns child/adult labels rapidly via global F0 contour."""
    import soundfile as sf

    sr = 16000
    duration = 6.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    # Segment 1 (0-3s): Adult tone (150 Hz)
    # Segment 2 (3-6s): Child tone (320 Hz)
    audio = np.zeros_like(t)
    audio[:int(sr * 3.0)] = 0.5 * np.sin(2 * np.pi * 150.0 * t[:int(sr * 3.0)])
    audio[int(sr * 3.0):] = 0.5 * np.sin(2 * np.pi * 320.0 * t[int(sr * 3.0):])

    test_wav = tmp_path / "test_diarization.wav"
    sf.write(str(test_wav), audio, sr)

    utterances = [
        UtteranceSegment(start=0.5, end=2.5, text="Adult talking"),
        UtteranceSegment(start=3.5, end=5.5, text="Child speaking"),
    ]

    diarizer = PitchHeuristicDiarizer()
    # Warm up
    diarizer.assign(test_wav, utterances)

    t0 = time.time()
    assigned = diarizer.assign(test_wav, utterances)
    elapsed = time.time() - t0

    assert elapsed < 0.1, f"Expected < 0.1s for diarization assign, took {elapsed:.4f}s"
    assert assigned[0].speaker == "MOT"  # Adult
    assert assigned[1].speaker == "CHI"  # Child
