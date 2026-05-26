from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.audio_pipeline.acoustic_profile import compute_acoustic_profile  # noqa: E402
from src.audio_pipeline.whisper_transcribe import UtteranceSegment  # noqa: E402


def test_acoustic_profile_detects_synthetic_voiced_pitch(tmp_path):
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    audio = 0.2 * np.sin(2 * np.pi * 220 * t)
    path = tmp_path / "tone.wav"
    sf.write(path, audio, sr)

    profile = compute_acoustic_profile(path)

    assert profile.duration_sec == 1.0
    assert profile.voiced_ratio > 0.5
    assert 180 <= profile.f0_median_hz <= 260


def test_acoustic_profile_handles_silent_audio(tmp_path):
    sr = 16000
    path = tmp_path / "silence.wav"
    sf.write(path, np.zeros(sr), sr)

    profile = compute_acoustic_profile(path)

    assert profile.duration_sec == 1.0
    assert profile.voiced_ratio == 0.0
    assert np.isnan(profile.f0_median_hz)


def test_acoustic_profile_uses_utterance_gaps_for_pause_and_speech_rate(tmp_path):
    sr = 16000
    path = tmp_path / "tone.wav"
    sf.write(path, np.zeros(sr * 4), sr)
    utterances = [
        UtteranceSegment(start=0.0, end=1.0, text="hello child", speaker="CHI"),
        UtteranceSegment(start=2.0, end=3.0, text="adult turn", speaker="MOT"),
    ]

    profile = compute_acoustic_profile(path, utterances)

    assert 0.24 <= profile.pause_ratio <= 0.26
    assert profile.child_speech_rate_wps == 2.0
