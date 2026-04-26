"""
Voice Activity Detection (VAD) using Silero-VAD.

Silero-VAD is a small (~1 MB) open-source PyTorch JIT model that
detects speech regions in audio.  It is **far** more accurate than
energy-based VAD on noisy child-therapy recordings, and unlike
pyannote it does **not** require a HuggingFace token.

The VAD output drives:
  1. Hallucination suppression (skip Whisper on silent regions)
  2. Clean utterance boundaries (independent of Whisper segmentation)
  3. Diarization windows (only embed speech, not silence)

Usage
-----
>>> regions = detect_speech_regions("session.wav")
>>> for start, end in regions:
...     print(f"speech: {start:.2f} -> {end:.2f}")
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class VADConfig:
    """Tunable parameters for child-therapy recordings."""
    # Probability threshold for "is this speech?"
    threshold: float = 0.5
    # Drop speech regions shorter than this (likely lip smacks / clicks)
    min_speech_ms: int = 200
    # Merge adjacent speech regions separated by less than this
    min_silence_ms: int = 400
    # Pad each region to avoid clipping word boundaries
    speech_pad_ms: int = 100
    # Sample rate Silero expects (16 kHz only — we resample if needed)
    sample_rate: int = 16000


# Module-level cache so we only download/load Silero once per process
_VAD_MODEL = None
_VAD_UTILS = None


def _load_silero():
    """Load Silero-VAD via torch.hub (downloads weights once, ~1 MB)."""
    global _VAD_MODEL, _VAD_UTILS
    if _VAD_MODEL is not None:
        return _VAD_MODEL, _VAD_UTILS
    try:
        import torch
    except ImportError as e:
        raise ImportError(
            "torch is required for Silero-VAD.\n  pip install torch"
        ) from e

    # torch.hub.load downloads weights to ~/.cache/torch/hub/snakers4_silero-vad
    model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        trust_repo=True,
        onnx=False,
    )
    _VAD_MODEL, _VAD_UTILS = model, utils
    return model, utils


def detect_speech_regions(
    audio_path: str | Path,
    config: Optional[VADConfig] = None,
) -> List[Tuple[float, float]]:
    """Detect speech regions in an audio file.

    Returns
    -------
    list of (start_sec, end_sec)
        Sorted, non-overlapping speech regions.
    """
    config = config or VADConfig()
    try:
        import torch
        import librosa
    except ImportError as e:
        raise ImportError(
            "torch + librosa are required for the VAD stage.\n"
            "  pip install torch librosa"
        ) from e

    model, utils = _load_silero()
    get_speech_timestamps = utils[0]

    # Silero requires 16 kHz mono
    y, sr = librosa.load(str(audio_path), sr=config.sample_rate, mono=True)
    audio_tensor = torch.from_numpy(y).float()

    timestamps = get_speech_timestamps(
        audio_tensor,
        model,
        sampling_rate=config.sample_rate,
        threshold=config.threshold,
        min_speech_duration_ms=config.min_speech_ms,
        min_silence_duration_ms=config.min_silence_ms,
        speech_pad_ms=config.speech_pad_ms,
    )

    return [
        (ts["start"] / config.sample_rate, ts["end"] / config.sample_rate)
        for ts in timestamps
    ]


def speech_coverage(regions: List[Tuple[float, float]], total_duration: float) -> float:
    """Return the fraction of total_duration covered by speech regions."""
    if total_duration <= 0:
        return 0.0
    speech = sum(max(0.0, e - s) for s, e in regions)
    return min(1.0, speech / total_duration)


# ----------------------------------------------------------------------
# CLI quick-test
# ----------------------------------------------------------------------
def _cli() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Silero-VAD speech detection.")
    ap.add_argument("audio", type=Path)
    ap.add_argument("--threshold", type=float, default=0.5)
    args = ap.parse_args()

    cfg = VADConfig(threshold=args.threshold)
    regions = detect_speech_regions(args.audio, cfg)
    for s, e in regions:
        print(f"[{s:7.2f} -> {e:7.2f}]  ({e - s:.2f}s)")
    print(f"\n{len(regions)} regions, total speech: "
          f"{sum(e - s for s, e in regions):.1f}s")


if __name__ == "__main__":
    _cli()
