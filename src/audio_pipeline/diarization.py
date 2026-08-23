"""
Speaker diarization + child-speaker identification.

We provide three backends, all sharing the ``BaseDiarizer.assign(...)``
interface.  The factory ``get_diarizer(...)`` picks the best one
available on the current machine.

1. ``EmbeddingDiarizer``  (default, **no HF token**) — uses
   speechbrain/spkrec-ecapa-voxceleb to compute 192-dim speaker
   embeddings, then sklearn ``AgglomerativeClustering`` to group
   utterances by speaker.  The child cluster is selected by a scoring
   rule combining median F0 (age-aware), mean utterance duration, and
   optionally a user-uploaded reference embedding (speaker enrollment).

2. ``PyannoteDiarizer``  (optional upgrade, **needs HF token**) — uses
   pyannote/speaker-diarization-3.1.  Best quality but gated.

3. ``PitchHeuristicDiarizer``  (final fallback) — librosa-only median
   F0 with an age-aware threshold.  Cheapest but only works for
   well-separated 2-speaker recordings.

The output label used by TalkBank CHAT is:
    "CHI"  -> child
    "MOT"  -> mother (or any adult; we default to this if we only need
              one adult label)
    "INV"  -> investigator / therapist (third speaker)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
import importlib.util
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np

from .whisper_transcribe import UtteranceSegment


CHILD_LABEL = "CHI"
ADULT_LABEL = "MOT"   # generic adult; could be INV/FAT/etc.
ADULT_LABELS = ["MOT", "INV", "FAT"]   # used when >2 clusters are detected


@dataclass(frozen=True)
class DiarizationRuntimeStatus:
    """Dependency and fallback status for diarization runtime planning."""
    selected_backend: str
    fallback_reason: str | None
    available_backends: dict[str, bool]
    config: dict[str, object]
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, object]:
        return {
            "selected_backend": self.selected_backend,
            "fallback_reason": self.fallback_reason,
            "available_backends": dict(self.available_backends),
            "config": dict(self.config),
            "warnings": list(self.warnings),
        }


def age_aware_child_f0_threshold(age_months: Optional[float]) -> float:
    """Return the F0 threshold (Hz) above which a speaker is likely the child.

    F0 drops with age — a 2-year-old child sits around 350 Hz while a
    pre-pubertal 10-year-old is around 240 Hz.  Adult women typically
    sit at 165-220 Hz and adult men at 85-180 Hz.
    """
    if age_months is None:
        return 230.0
    if age_months <= 36:        # 0-3 years
        return 300.0
    if age_months <= 72:        # 4-6 years
        return 260.0
    if age_months <= 144:       # 7-12 years
        return 220.0
    return 180.0                # >12 years


# ======================================================================
# Base class
# ======================================================================
class BaseDiarizer:
    """Fill in `utterance.speaker` on each `UtteranceSegment`."""

    def __init__(self) -> None:
        self.last_f0_cache: Optional[tuple[np.ndarray, np.ndarray, float]] = None
        self.last_audio: Optional[tuple[np.ndarray, int]] = None

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
    # F0 above this => likely a child (default elevated to 260 Hz to prevent adult female motherese false positives)
    child_f0_threshold_hz: float = 260.0
    # Minimum F0 confidence to trust a measurement
    min_voiced_frames: int = 5
    # librosa pyin bounds (Hz)
    fmin: float = 65.0
    fmax: float = 500.0


import re
from typing import Any, List, Optional, Sequence


# Comprehensive clinician / adult caregiver assessment prompts (regex patterns)
_ADULT_PROMPT_REGEXES = [
    # English commands & instructions
    r"\b(?:try again|can you|could you|would you|will you|i'?m gonna ask|i have some questions)\b",
    r"\b(?:touch your|show me|look at|point to|tell me|give me|put it|pick up|fix your chair|come have a seat)\b",
    r"\b(?:splat it|need to do|let's see|let's play|let's do|open the|close the|listen|have something to show)\b",
    r"\b(?:what is|what's|where is|where's|who is|who's|which one|what do you do with|what kind of|where does)\b",
    r"\b(?:do you want|you want|wanna|you wanna|are you ready|ready\?|you ready for|i bet you know)\b",
    r"\b(?:say it|say after me|repeat after|how many|what color|ask you a color|what would you call)\b",
    r"\b(?:good job|nice job|very good|great job|awesome|well done|that's right|super|good answer|nice\.?|good\.?)\b",
    r"\b(?:are they the same|and is this the same|i just want you to do what i do|i need to do this)\b",
    r"\b(?:one, two, three|when you get all|you got all|let's give you|there's the third|last thing|no cards)\b",
    r"\b(?:catch my spider|i'm going to get you|we're not gonna be able|eat them|here's something else)\b",
    # Thai commands & instructions
    r"(?:ลองพูด|ลองทำ|ทำตาม|ดูนี่|ชี้ซิ|บอกหมอ|บอกครู|เอาวาง|เปิดซิ|ปิดซิ|หยิบ|ทำแบบนี้|ลองดู|ตบมือ|จับหัว|จับจมูก)",
    r"(?:อันนี้อะไร|ทำอะไรอยู่|ไปไหนมา|อยู่ไหน|ใครเอ่ย|สีอะไร|กี่อัน|เอาอีกไหม|ตอบได้ไหม|ใช่ไหม|ถูกไหม|อะไรนะ)",
    r"(?:เก่งมาก|เก่งจัง|ถูกแล้ว|ดีมาก|เยี่ยมเลย|สวัสดีครับ|สวัสดีค่ะ|นะลูก|นะคะ|นะครับ|ดูการ์ด|ลองตอบ|ชี้รูป|เก็บของ|นั่งลง)",
]

_ADULT_COMPILED_REGEX = re.compile("|".join(_ADULT_PROMPT_REGEXES), re.IGNORECASE)
_CHILD_SPEECH_REGEX = re.compile(r"^(?:xxx|yyy|uh-oh|uh oh|เอ่อ|อือ|อ๋อ|หืม|งะ|ฮะ|จ๊ะ)$", re.IGNORECASE)


def is_adult_clinical_prompt(text: str) -> bool:
    """Return True if the text contains unmistakable examiner/caregiver prompt, question, or praise cues."""
    if not text:
        return False
    norm = text.strip().lower()
    return bool(_ADULT_COMPILED_REGEX.search(norm))


def is_child_speech_pattern(text: str) -> bool:
    """Return True if text matches typical single-word or unintelligible child response patterns."""
    if not text:
        return False
    norm = text.strip().lower()
    return bool(_CHILD_SPEECH_REGEX.match(norm))


def refine_speakers_by_dialogue_flow(utterances: Sequence[UtteranceSegment]) -> List[UtteranceSegment]:
    """Refine speaker assignments across a session using clinical dialogue turn-taking rules."""
    if not utterances:
        return []

    utts = list(utterances)
    n = len(utts)

    # Pass 1: Apply unmistakable linguistic markers
    for u in utts:
        txt = getattr(u, "text", "") or ""
        if is_adult_clinical_prompt(txt):
            if not u.speaker or u.speaker == CHILD_LABEL:
                u.speaker = ADULT_LABEL
        elif is_child_speech_pattern(txt):
            u.speaker = CHILD_LABEL

    # Pass 2: Turn-taking conversational prior
    for i in range(n - 1):
        curr_u = utts[i]
        next_u = utts[i + 1]

        curr_txt = getattr(curr_u, "text", "") or ""
        next_txt = getattr(next_u, "text", "") or ""
        gap = max(0.0, next_u.start - curr_u.end)
        next_dur = max(0.0, next_u.end - next_u.start)
        next_words = next_txt.strip().split()

        # If curr is an Adult Prompt / Question, and next is a short response within 2.5s
        if curr_u.speaker in (ADULT_LABEL, "INV", "MOT", "FAT") and is_adult_clinical_prompt(curr_txt):
            if gap <= 2.5 and next_dur <= 3.0 and len(next_words) <= 5 and not is_adult_clinical_prompt(next_txt):
                next_u.speaker = CHILD_LABEL

        # If curr is Child and next is adult praise / prompt
        if curr_u.speaker == CHILD_LABEL and is_adult_clinical_prompt(next_txt):
            # If surrounded by child on both sides, do not override unless strong adult prompt
            is_surrounded_by_child = (i + 2 < n and utts[i + 2].speaker == CHILD_LABEL)
            if not is_surrounded_by_child or is_adult_clinical_prompt(next_txt):
                next_u.speaker = ADULT_LABEL

    return utts


def refine_utterance_dicts(utterances: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Refine a list of dictionary utterances in-place using clinical dialogue turn-taking rules."""
    if not utterances:
        return []

    n = len(utterances)
    # Pass 1: Linguistic rules
    for u in utterances:
        txt = u.get("text", "")
        spk = u.get("speaker", "CHI")
        if is_adult_clinical_prompt(txt):
            if spk == "CHI":
                u["speaker"] = "INV"
        elif is_child_speech_pattern(txt):
            u["speaker"] = "CHI"

    # Pass 2: Conversational turn-taking
    for i in range(n - 1):
        curr_u = utterances[i]
        next_u = utterances[i + 1]
        curr_txt = curr_u.get("text", "")
        next_txt = next_u.get("text", "")
        gap = max(0.0, float(next_u.get("start_time", 0.0)) - float(curr_u.get("end_time", 0.0)))
        next_dur = max(0.0, float(next_u.get("end_time", 0.0)) - float(next_u.get("start_time", 0.0)))
        next_words = next_txt.strip().split()

        if curr_u.get("speaker") in ("INV", "MOT", "FAT") and is_adult_clinical_prompt(curr_txt):
            if gap <= 2.5 and next_dur <= 3.0 and len(next_words) <= 5 and not is_adult_clinical_prompt(next_txt):
                next_u["speaker"] = "CHI"

        if curr_u.get("speaker") == "CHI" and is_adult_clinical_prompt(next_txt):
            next_u["speaker"] = "INV"

    return utterances


class PitchHeuristicDiarizer(BaseDiarizer):
    """Assign CHI/MOT based on median F0 of each utterance and linguistic prompt cues.

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
        super().__init__()
        self.config = config or PitchDiarizerConfig()

    def _median_f0(self, y: np.ndarray, sr: int) -> Optional[float]:
        """Return median F0 of voiced frames, or None if too few voiced frames."""
        import librosa
        if len(y) == 0:
            return None
        try:
            fmin = float(self.config.fmin)
            fmax = float(self.config.fmax)
            hop_length = 512
            f0 = librosa.yin(y, fmin=fmin, fmax=fmax, sr=sr, hop_length=hop_length)
            rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=hop_length)[0]
            min_len = min(len(f0), len(rms))
            f0 = f0[:min_len]
            rms = rms[:min_len]

            max_rms = float(np.max(rms)) if rms.size else 0.0
            energy_threshold = max(0.001, max_rms * 0.05) if max_rms > 0 else 0.001
            voiced = f0[(rms > energy_threshold) & np.isfinite(f0) & (f0 > fmin + 1.0) & (f0 < fmax - 1.0)]
            if len(voiced) < self.config.min_voiced_frames:
                return None
            return float(np.median(voiced))
        except Exception:
            return None

    @staticmethod
    def _compute_global_f0_contour(
        y: np.ndarray,
        sr: int = 16000,
        fmin: float = 65.0,
        fmax: float = 500.0,
        hop_length: int = 512,
    ) -> tuple[np.ndarray, np.ndarray, float]:
        """Compute frame-level F0 and voiced mask across the entire audio at once."""
        import librosa
        if len(y) == 0:
            return np.array([], dtype=float), np.array([], dtype=bool), hop_length / sr
        try:
            f0 = librosa.yin(y, fmin=float(fmin), fmax=float(fmax), sr=sr, hop_length=hop_length)
            rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=hop_length)[0]
            min_len = min(len(f0), len(rms))
            f0 = f0[:min_len]
            rms = rms[:min_len]

            max_rms = float(np.max(rms)) if rms.size else 0.0
            energy_threshold = max(0.001, max_rms * 0.05) if max_rms > 0 else 0.001
            voiced_mask = (rms > energy_threshold) & np.isfinite(f0) & (f0 > fmin + 1.0) & (f0 < fmax - 1.0)
            return f0, voiced_mask, hop_length / sr
        except Exception:
            return np.array([], dtype=float), np.array([], dtype=bool), hop_length / sr

    def assign(
        self,
        audio_path: str | Path,
        utterances: Sequence[UtteranceSegment],
    ) -> List[UtteranceSegment]:
        import librosa
        if not utterances:
            return []

        try:
            import soundfile as sf
            y_full, sr = sf.read(str(audio_path), dtype="float32")
            if y_full.ndim > 1:
                y_full = np.mean(y_full, axis=1)
            if sr != 16000:
                y_full = librosa.resample(y_full, orig_sr=sr, target_sr=16000)
                sr = 16000
        except Exception:
            y_full, sr = librosa.load(str(audio_path), sr=16000, mono=True)

        f0_contour, voiced_mask, hop_sec = self._compute_global_f0_contour(
            y_full, sr=sr, fmin=self.config.fmin, fmax=self.config.fmax
        )
        self.last_audio = (y_full, sr)
        self.last_f0_cache = (f0_contour, voiced_mask, hop_sec)

        # 1. First pass: extract median F0 for each utterance
        utterance_medians: list[float | None] = []
        for u in utterances:
            med_f0: float | None = None
            if f0_contour.size and hop_sec > 0:
                start_frame = max(0, int(u.start / hop_sec))
                end_frame = min(len(f0_contour), int(u.end / hop_sec) + 1)
                if end_frame > start_frame:
                    u_f0 = f0_contour[start_frame:end_frame]
                    u_mask = voiced_mask[start_frame:end_frame]
                    voiced_f0 = u_f0[u_mask]
                    if len(voiced_f0) >= self.config.min_voiced_frames:
                        med_f0 = float(np.median(voiced_f0))
            utterance_medians.append(med_f0)

        # 2. Dynamic threshold calculation across the session
        valid_f0s = [f for f in utterance_medians if f is not None]
        eff_threshold = float(self.config.child_f0_threshold_hz)
        if len(valid_f0s) >= 4:
            f0_p25 = float(np.percentile(valid_f0s, 25))
            f0_p75 = float(np.percentile(valid_f0s, 75))
            if (f0_p75 - f0_p25) >= 35.0:
                midpoint = (f0_p25 + f0_p75) / 2.0
                eff_threshold = max(230.0, min(300.0, midpoint))

        # 3. Second pass: classify speaker with acoustic pitch + linguistic prompt heuristic
        out: List[UtteranceSegment] = []
        for u, med_f0 in zip(utterances, utterance_medians):
            speaker = ADULT_LABEL  # Default

            # Linguistic prompt pattern check
            is_prompt_pattern = is_adult_clinical_prompt(u.text)
            is_child_pattern = is_child_speech_pattern(u.text)

            if is_prompt_pattern:
                speaker = ADULT_LABEL
            elif is_child_pattern:
                speaker = CHILD_LABEL
            elif med_f0 is not None:
                if med_f0 >= eff_threshold:
                    speaker = CHILD_LABEL
                else:
                    speaker = ADULT_LABEL
            else:
                speaker = CHILD_LABEL

            u.speaker = speaker
            out.append(u)

        # 4. Apply dialogue turn-taking refinement
        return refine_speakers_by_dialogue_flow(out)


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
# Default: speaker-embedding diarizer (no HF token)
# ======================================================================
@dataclass
class EmbeddingDiarizerConfig:
    """Tunables for the speechbrain-ECAPA + AgglomerativeClustering backend."""
    # Distance threshold for AgglomerativeClustering (cosine).  Lower =>
    # more clusters.  0.5 works well for 2-3 speakers in child therapy.
    distance_threshold: float = 0.5
    # Cap clusters even if more are found (avoids over-splitting)
    max_speakers: int = 4
    # Minimum utterance duration to embed (seconds) — too short and
    # ECAPA embeddings are unstable.  Short utterances fall back to F0.
    min_embed_duration: float = 0.4
    # Weights for the child-cluster scoring rule
    weight_f0: float = 1.0
    weight_duration: float = 0.3
    weight_enrollment: float = 2.0
    # Age (months) drives the F0 threshold for scoring; None => 230 Hz
    child_age_months: Optional[float] = None


class EmbeddingDiarizer(BaseDiarizer):
    """Speaker-embedding-based diarization — no HF token required.

    Pipeline:
      1. For each utterance long enough, compute an ECAPA-TDNN embedding
         using ``speechbrain/spkrec-ecapa-voxceleb`` (open-weight,
         downloads on first use).
      2. Cluster embeddings with ``AgglomerativeClustering`` using cosine
         distance.
      3. Pick the child cluster with a weighted scoring rule combining:
         * median F0 of the cluster (higher = more child-like, age-aware)
         * mean utterance duration (lower = more child-like)
         * cosine similarity to an optional enrollment embedding
      4. Label the child cluster CHI; remaining clusters get MOT, INV,
         FAT in order of total speech time.

    Short utterances that cannot be reliably embedded fall back to the
    age-aware pitch heuristic.
    """

    def __init__(
        self,
        config: Optional[EmbeddingDiarizerConfig] = None,
        enrollment_audio_path: Optional[str | Path] = None,
    ) -> None:
        self.config = config or EmbeddingDiarizerConfig()
        self._classifier = None
        self._pitch = PitchHeuristicDiarizer(
            PitchDiarizerConfig(
                child_f0_threshold_hz=age_aware_child_f0_threshold(
                    self.config.child_age_months,
                ),
            ),
        )
        self._enrollment_embedding: Optional[np.ndarray] = None
        if enrollment_audio_path is not None:
            self._enrollment_embedding = self._embed_file(
                Path(enrollment_audio_path),
            )

    # ------------------------------------------------------------------
    def _load_classifier(self):
        if self._classifier is not None:
            return self._classifier
        try:
            from speechbrain.inference.speaker import EncoderClassifier
        except ImportError as e:
            raise ImportError(
                "speechbrain is required for EmbeddingDiarizer.\n"
                "  pip install speechbrain"
            ) from e
        self._classifier = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=os.path.expanduser("~/.cache/speechbrain/ecapa"),
            run_opts={"device": "cpu"},
        )
        return self._classifier

    def _embed_clip(self, clip: np.ndarray, sr: int) -> Optional[np.ndarray]:
        """Return a 192-dim ECAPA embedding for an audio clip."""
        import librosa
        import torch

        if len(clip) < int(self.config.min_embed_duration * sr):
            return None
        # speechbrain expects 16 kHz
        if sr != 16000:
            clip = librosa.resample(clip, orig_sr=sr, target_sr=16000)
        clf = self._load_classifier()
        with torch.inference_mode():
            emb = clf.encode_batch(torch.from_numpy(clip).float().unsqueeze(0))
        return emb.squeeze().cpu().numpy()

    def _embed_file(self, audio_path: Path) -> Optional[np.ndarray]:
        import librosa
        y, sr = librosa.load(str(audio_path), sr=16000, mono=True)
        return self._embed_clip(y, sr)

    # ------------------------------------------------------------------
    def assign(
        self,
        audio_path: str | Path,
        utterances: Sequence[UtteranceSegment],
    ) -> List[UtteranceSegment]:
        import librosa

        if not utterances:
            return list(utterances)

        y_full, sr = librosa.load(str(audio_path), sr=None, mono=True)

        # ---- 1. Compute embeddings + per-utt F0 -------------------------
        embeddings: List[Optional[np.ndarray]] = []
        f0s: List[Optional[float]] = []
        durations: List[float] = []
        for u in utterances:
            s = max(0, int(u.start * sr))
            e = min(len(y_full), int(u.end * sr))
            clip = y_full[s:e]
            durations.append(max(0.0, u.end - u.start))
            f0s.append(self._pitch._median_f0(clip, sr) if len(clip) else None)
            try:
                emb = self._embed_clip(clip, sr)
            except Exception as exc:  # noqa: BLE001
                print(f"[diarization] embedding failed for {u.start:.2f}s: {exc}")
                emb = None
            embeddings.append(emb)

        # ---- 2. Cluster the utterances we could embed -------------------
        try:
            from sklearn.cluster import AgglomerativeClustering
        except ImportError as exc:
            raise ImportError(
                "scikit-learn is required for EmbeddingDiarizer.\n"
                "  pip install scikit-learn"
            ) from exc

        usable = [i for i, e in enumerate(embeddings) if e is not None]
        labels: List[Optional[int]] = [None] * len(utterances)
        if len(usable) >= 2:
            X = np.stack([embeddings[i] for i in usable])
            # Normalize for cosine clustering
            X_norm = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-8)
            clust = AgglomerativeClustering(
                n_clusters=None,
                metric="cosine",
                linkage="average",
                distance_threshold=self.config.distance_threshold,
            )
            cluster_ids = clust.fit_predict(X_norm)
            # Cap number of clusters
            unique = list(np.unique(cluster_ids))
            if len(unique) > self.config.max_speakers:
                # Keep the largest N clusters; reassign rest to nearest centroid
                sizes = sorted(
                    unique, key=lambda c: -np.sum(cluster_ids == c),
                )[: self.config.max_speakers]
                centroids = {c: X_norm[cluster_ids == c].mean(axis=0) for c in sizes}
                for j, cid in enumerate(cluster_ids):
                    if cid not in sizes:
                        # nearest kept centroid
                        cluster_ids[j] = max(
                            sizes,
                            key=lambda c: float(centroids[c] @ X_norm[j]),
                        )
            for i, c in zip(usable, cluster_ids):
                labels[i] = int(c)
        else:
            # Fall back entirely to pitch heuristic
            return self._pitch.assign(audio_path, utterances)

        # ---- 3. Score each cluster, pick child --------------------------
        unique = sorted({l for l in labels if l is not None})
        cluster_score: dict[int, float] = {}
        f0_thresh = age_aware_child_f0_threshold(self.config.child_age_months)
        for c in unique:
            members = [i for i, l in enumerate(labels) if l == c]
            f0_vals = [f0s[i] for i in members if f0s[i] is not None]
            dur_vals = [durations[i] for i in members]
            score = 0.0
            if f0_vals:
                score += self.config.weight_f0 * (np.median(f0_vals) - f0_thresh)
            # Children speak in shorter bursts
            mean_dur = float(np.mean(dur_vals)) if dur_vals else 5.0
            score += -self.config.weight_duration * mean_dur
            if self._enrollment_embedding is not None:
                centroid = np.mean(
                    [embeddings[i] for i in members if embeddings[i] is not None],
                    axis=0,
                )
                centroid = centroid / (np.linalg.norm(centroid) + 1e-8)
                ref = self._enrollment_embedding / (
                    np.linalg.norm(self._enrollment_embedding) + 1e-8
                )
                score += self.config.weight_enrollment * float(centroid @ ref)
            cluster_score[c] = score

        child_cluster = max(cluster_score, key=cluster_score.get)

        # Order remaining clusters by total speech time
        adult_clusters = [c for c in unique if c != child_cluster]
        adult_clusters.sort(
            key=lambda c: -sum(
                durations[i] for i, l in enumerate(labels) if l == c
            )
        )
        cluster_to_label: dict[int, str] = {child_cluster: CHILD_LABEL}
        for idx, c in enumerate(adult_clusters):
            cluster_to_label[c] = (
                ADULT_LABELS[idx] if idx < len(ADULT_LABELS) else f"AD{idx}"
            )

        # ---- 4. Assign labels (fall back to pitch first if available, then context-aware continuity) -
        # Pass 1: Assign clustered and pitch-based speaker labels first
        for u, l, f0 in zip(utterances, labels, f0s):
            if l is not None:
                u.speaker = cluster_to_label[l]
            elif f0 is not None:
                u.speaker = (
                    CHILD_LABEL
                    if f0 >= f0_thresh
                    else ADULT_LABEL
                )
            else:
                u.speaker = None

        # Pass 2: Fill in any None speaker segments using context
        for idx, u in enumerate(utterances):
            if u.speaker is None:
                left_speakers = [utterances[i].speaker for i in range(max(0, idx-3), idx) if utterances[i].speaker]
                right_speakers = [utterances[i].speaker for i in range(idx+1, min(len(utterances), idx+4)) if utterances[i].speaker]
                
                # If surrounded by the same speaker, inherit it
                if left_speakers and right_speakers and left_speakers[-1] == right_speakers[0]:
                    u.speaker = left_speakers[-1]
                elif left_speakers:
                    u.speaker = left_speakers[-1]
                elif right_speakers:
                    u.speaker = right_speakers[0]
                else:
                    u.speaker = ADULT_LABEL

        # Pass 3: Apply dialogue turn-taking and clinical prompt refinement
        return refine_speakers_by_dialogue_flow(utterances)


# ======================================================================
# Factory
# ======================================================================
def get_diarization_runtime_status(
    *,
    prefer_pyannote: bool = False,
    hf_token: Optional[str] = None,
    child_age_months: Optional[float] = None,
    enrollment_audio_path: Optional[str | Path] = None,
    distance_threshold: float | None = None,
    max_speakers: int | None = None,
    min_embed_duration: float | None = None,
) -> DiarizationRuntimeStatus:
    """Inspect diarization dependency readiness without loading audio/models."""
    speechbrain_available = _module_available("speechbrain")
    sklearn_available = _module_available("sklearn")
    librosa_available = _module_available("librosa")
    pyannote_available = _module_available("pyannote.audio")
    token_available = bool(hf_token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN"))
    pyannote_ready = pyannote_available and token_available
    embedding_ready = speechbrain_available and sklearn_available and librosa_available
    pitch_ready = librosa_available
    config = EmbeddingDiarizerConfig(child_age_months=child_age_months)
    if distance_threshold is not None:
        config.distance_threshold = distance_threshold
    if max_speakers is not None:
        config.max_speakers = max_speakers
    if min_embed_duration is not None:
        config.min_embed_duration = min_embed_duration

    warnings: list[str] = []
    fallback_reason: str | None = None
    if prefer_pyannote and pyannote_ready:
        selected = "pyannote"
    elif embedding_ready:
        selected = "speechbrain_embedding"
        if prefer_pyannote:
            fallback_reason = "pyannote unavailable or missing HF token"
    elif pitch_ready:
        selected = "pitch_heuristic"
        missing = _missing_dependencies(
            {
                "speechbrain": speechbrain_available,
                "sklearn": sklearn_available,
            }
        )
        fallback_reason = f"embedding diarizer unavailable: missing {', '.join(missing)}"
        warnings.append("Pitch heuristic is a fallback and needs human speaker review.")
    else:
        selected = "unavailable"
        fallback_reason = "librosa unavailable; no diarization backend can run"
        warnings.append("Install audio dependencies before running diarization.")

    if prefer_pyannote and not token_available:
        warnings.append("pyannote requested but HF_TOKEN/HUGGINGFACE_TOKEN is not set.")
    if enrollment_audio_path is not None and not Path(enrollment_audio_path).exists():
        warnings.append("enrollment_audio_path does not exist; enrollment scoring will be unavailable.")

    return DiarizationRuntimeStatus(
        selected_backend=selected,
        fallback_reason=fallback_reason,
        available_backends={
            "pyannote": pyannote_ready,
            "speechbrain_embedding": embedding_ready,
            "pitch_heuristic": pitch_ready,
        },
        config={
            "child_age_months": child_age_months,
            "child_f0_threshold_hz": age_aware_child_f0_threshold(child_age_months),
            "distance_threshold": config.distance_threshold,
            "max_speakers": config.max_speakers,
            "min_embed_duration": config.min_embed_duration,
            "enrollment_audio_path_provided": enrollment_audio_path is not None,
        },
        warnings=warnings,
    )


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False


def _missing_dependencies(availability: dict[str, bool]) -> list[str]:
    return [name for name, available in availability.items() if not available]


def get_diarizer(
    prefer_pyannote: bool = False,
    hf_token: Optional[str] = None,
    *,
    child_age_months: Optional[float] = None,
    enrollment_audio_path: Optional[str | Path] = None,
) -> BaseDiarizer:
    """Return the best diarizer available in the current environment.

    Default priority (no HF token required):
        EmbeddingDiarizer (speechbrain) -> PitchHeuristicDiarizer

    Set ``prefer_pyannote=True`` if you have an HF_TOKEN configured and
    want to use pyannote 3.1 (better quality, gated).
    """
    if prefer_pyannote:
        try:
            return PyannoteDiarizer(hf_token=hf_token)
        except (ImportError, RuntimeError) as e:
            print(f"[diarization] Pyannote unavailable: {e}")
            # Fall through to embedding diarizer
    if _module_available("speechbrain") and _module_available("sklearn") and _module_available("librosa"):
        try:
            return EmbeddingDiarizer(
                EmbeddingDiarizerConfig(child_age_months=child_age_months),
                enrollment_audio_path=enrollment_audio_path,
            )
        except Exception as e:
            print(f"[diarization] Embedding diarizer initialization failed: {e}")

    return PitchHeuristicDiarizer(
        PitchDiarizerConfig(
            child_f0_threshold_hz=age_aware_child_f0_threshold(child_age_months),
        ),
    )
