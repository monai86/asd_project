"""Descriptive acoustic profile for uploaded audio.

These values support review and future validation planning only. They are not
inputs to the current screening classifier.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from pathlib import Path
import tempfile
from typing import Any

import numpy as np


@dataclass(frozen=True)
class AcousticProfile:
    duration_sec: float
    voiced_ratio: float
    f0_median_hz: float
    f0_iqr_hz: float
    pause_ratio: float
    child_speech_rate_wps: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def _safe_float(value: float) -> float:
    if value is None or not np.isfinite(value):
        return float("nan")
    return round(float(value), 4)


def _word_count(text: str) -> int:
    return len([token for token in (text or "").split() if token.strip()])


def compute_acoustic_profile(
    audio_path: str | Path,
    utterances: list[Any] | None = None,
) -> AcousticProfile:
    """Compute descriptive acoustic values from an uploaded recording."""
    os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(tempfile.gettempdir()) / "numba_cache"))
    try:
        import librosa
    except ImportError as exc:  # pragma: no cover - dependency message path
        raise ImportError("librosa is required for acoustic profile extraction.") from exc

    y, sr = librosa.load(str(audio_path), sr=None, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr)) if sr else 0.0
    if duration <= 0 or len(y) == 0:
        return AcousticProfile(0.0, 0.0, float("nan"), float("nan"), 0.0, float("nan"))

    try:
        f0, voiced_flag, _ = librosa.pyin(
            y,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7"),
            sr=sr,
        )
    except Exception:  # noqa: BLE001
        f0 = np.asarray([], dtype=float)
        voiced_flag = np.asarray([], dtype=bool)

    voiced = np.asarray(voiced_flag, dtype=bool)
    voiced_ratio = float(voiced.mean()) if voiced.size else 0.0
    voiced_f0 = np.asarray(f0, dtype=float)
    voiced_f0 = voiced_f0[np.isfinite(voiced_f0)]
    if voiced_f0.size:
        f0_median = float(np.median(voiced_f0))
        f0_iqr = float(np.percentile(voiced_f0, 75) - np.percentile(voiced_f0, 25))
    else:
        f0_median = float("nan")
        f0_iqr = float("nan")

    pause_ratio = 0.0
    child_speech_rate = float("nan")
    if utterances:
        sorted_utts = sorted(utterances, key=lambda item: float(getattr(item, "start", 0.0)))
        speech_duration = sum(
            max(0.0, float(getattr(item, "end", 0.0)) - float(getattr(item, "start", 0.0)))
            for item in sorted_utts
        )
        gaps = []
        for prev, current in zip(sorted_utts, sorted_utts[1:]):
            gap = float(getattr(current, "start", 0.0)) - float(getattr(prev, "end", 0.0))
            if gap > 0:
                gaps.append(gap)
        pause_ratio = min(1.0, sum(gaps) / duration) if duration else 0.0

        child_utts = [
            item for item in sorted_utts
            if str(getattr(item, "speaker", "") or "").upper() == "CHI"
        ]
        child_duration = sum(
            max(0.0, float(getattr(item, "end", 0.0)) - float(getattr(item, "start", 0.0)))
            for item in child_utts
        )
        child_words = sum(_word_count(str(getattr(item, "text", "") or "")) for item in child_utts)
        if child_duration > 0:
            child_speech_rate = child_words / child_duration
        elif speech_duration > 0:
            child_speech_rate = 0.0

    return AcousticProfile(
        duration_sec=round(duration, 4),
        voiced_ratio=_safe_float(voiced_ratio),
        f0_median_hz=_safe_float(f0_median),
        f0_iqr_hz=_safe_float(f0_iqr),
        pause_ratio=_safe_float(pause_ratio),
        child_speech_rate_wps=_safe_float(child_speech_rate),
    )
