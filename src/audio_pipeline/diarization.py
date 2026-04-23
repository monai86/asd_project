"""
Speaker diarization + child-speaker identification.

We provide TWO backends so the pipeline works with or without a
HuggingFace token:

1. `PyannoteDiarizer`   (best) — uses pyannote/speaker-diarization-3.1.
   Requires:
     - `pip install pyannote.audio`
     - HuggingFace token in env var HF_TOKEN or HUGGINGFACE_TOKEN
     - You must accept terms at
       https://huggingface.co/pyannote/speaker-diarization-3.1

2. `PitchHeuristicDiarizer`  (fallback) — uses librosa to estimate the
   fundamental frequency (F0) of each utterance.  Children have
   noticeably higher F0 (~250-400 Hz) than adults (~85-255 Hz), so a
   simple threshold works surprisingly well for 2-speaker child-adult
   recordings.  No tokens or external weights required.

Both backends expose the same interface via `BaseDiarizer.assign(...)`.

The output label used by TalkBank CHAT is:
    "CHI"  -> child
    "MOT"  -> mother (or any adult; we default to this if we only need
              one adult label)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np

from .whisper_transcribe import UtteranceSegment


CHILD_LABEL = "CHI"
ADULT_LABEL = "MOT"   # generic adult; could be INV/FAT/etc.


# ======================================================================
# Base class
# ======================================================================
class BaseDiarizer:
    """Fill in `utterance.speaker` on each `UtteranceSegment`."""

    def assign(
        self,
        audio_path: str | Path,
        utterances: Sequence[UtteranceSegment],
    ) -> List[UtteranceSegment]:
        raise NotImplementedError


# ======================================================================
# Fallback: pitch-based heuristic (no external model required)
# ======================================================================
@dataclass
class PitchDiarizerConfig:
    """Tunable thresholds for the pitch heuristic."""
    # F0 above this => likely a child
    child_f0_threshold_hz: float = 230.0
    # Minimum F0 confidence to trust a measurement
    min_voiced_frames: int = 5
    # librosa pyin bounds (Hz)
    fmin: float = 65.0
    fmax: float = 500.0


class PitchHeuristicDiarizer(BaseDiarizer):
    """Assign CHI/MOT based on median F0 of each utterance.

    Works well for:
      - clean 2-speaker recordings (child + one adult)
      - child older than ~3 years (F0 separation is reliable)

    Fails / degrades for:
      - multiple adults
      - whispered or very quiet child speech
      - heavy background noise

    In those cases, use PyannoteDiarizer instead.
    """

    def __init__(self, config: Optional[PitchDiarizerConfig] = None) -> None:
        self.config = config or PitchDiarizerConfig()

    def _median_f0(self, y: np.ndarray, sr: int) -> Optional[float]:
        """Return median F0 of voiced frames, or None if too few voiced frames."""
        import librosa
        try:
            f0, voiced_flag, _ = librosa.pyin(
                y,
                fmin=self.config.fmin,
                fmax=self.config.fmax,
                sr=sr,
            )
        except Exception:
            return None
        if f0 is None:
            return None
        voiced = f0[voiced_flag]
        voiced = voiced[~np.isnan(voiced)]
        if len(voiced) < self.config.min_voiced_frames:
            return None
        return float(np.median(voiced))

    def assign(
        self,
        audio_path: str | Path,
        utterances: Sequence[UtteranceSegment],
    ) -> List[UtteranceSegment]:
        import librosa

        y_full, sr = librosa.load(str(audio_path), sr=None, mono=True)
        out: List[UtteranceSegment] = []
        for u in utterances:
            s = max(0, int(u.start * sr))
            e = min(len(y_full), int(u.end * sr))
            clip = y_full[s:e]
            speaker = ADULT_LABEL  # default
            if len(clip) >= int(0.1 * sr):  # at least 100 ms
                f0 = self._median_f0(clip, sr)
                if f0 is not None and f0 >= self.config.child_f0_threshold_hz:
                    speaker = CHILD_LABEL
            u.speaker = speaker
            out.append(u)
        return out


# ======================================================================
# Best-effort: pyannote.audio
# ======================================================================
class PyannoteDiarizer(BaseDiarizer):
    """State-of-the-art diarization using pyannote/speaker-diarization-3.1.

    After raw diarization, we still have to decide which cluster is the
    child.  We do this by picking the cluster with the highest median
    pitch (reusing the heuristic above).
    """

    def __init__(
        self,
        hf_token: Optional[str] = None,
        pitch_config: Optional[PitchDiarizerConfig] = None,
    ) -> None:
        try:
            from pyannote.audio import Pipeline
        except ImportError as e:
            raise ImportError(
                "pyannote.audio is required for PyannoteDiarizer.\n"
                "  pip install pyannote.audio"
            ) from e

        token = hf_token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        if not token:
            raise RuntimeError(
                "Missing HuggingFace token.  Set HF_TOKEN env var or pass "
                "hf_token=... .  Also accept the model terms at "
                "https://huggingface.co/pyannote/speaker-diarization-3.1"
            )

        self._pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=token,
        )
        self._pitch = PitchHeuristicDiarizer(pitch_config)

    def assign(
        self,
        audio_path: str | Path,
        utterances: Sequence[UtteranceSegment],
    ) -> List[UtteranceSegment]:
        import librosa

        diarization = self._pipeline(str(audio_path))

        # Collect per-cluster audio snippets to estimate F0 later
        y_full, sr = librosa.load(str(audio_path), sr=None, mono=True)
        cluster_f0: dict[str, list[float]] = {}
        for turn, _, label in diarization.itertracks(yield_label=True):
            s = max(0, int(turn.start * sr))
            e = min(len(y_full), int(turn.end * sr))
            f0 = self._pitch._median_f0(y_full[s:e], sr)
            if f0 is not None:
                cluster_f0.setdefault(label, []).append(f0)

        # Child cluster = highest median F0
        child_cluster: Optional[str] = None
        if cluster_f0:
            child_cluster = max(
                cluster_f0,
                key=lambda k: float(np.median(cluster_f0[k])),
            )

        # Assign a speaker label to each utterance by majority overlap
        out: List[UtteranceSegment] = []
        for u in utterances:
            best_label = None
            best_overlap = 0.0
            for turn, _, label in diarization.itertracks(yield_label=True):
                overlap = max(0.0, min(u.end, turn.end) - max(u.start, turn.start))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_label = label
            if best_label is None:
                u.speaker = ADULT_LABEL
            else:
                u.speaker = CHILD_LABEL if best_label == child_cluster else ADULT_LABEL
            out.append(u)
        return out


# ======================================================================
# Factory
# ======================================================================
def get_diarizer(
    prefer_pyannote: bool = True,
    hf_token: Optional[str] = None,
) -> BaseDiarizer:
    """Return the best diarizer available in the current environment.

    Falls back to the pitch heuristic if pyannote is unavailable OR the
    user has no HuggingFace token configured.
    """
    if prefer_pyannote:
        try:
            return PyannoteDiarizer(hf_token=hf_token)
        except (ImportError, RuntimeError) as e:
            print(f"[diarization] Falling back to pitch heuristic: {e}")
    return PitchHeuristicDiarizer()
