"""
Whisper-based ASR wrapper.

Uses `faster-whisper` (4x faster than openai-whisper, same accuracy) to
transcribe child-therapy audio into word-level segments with timestamps
and confidence scores.

The confidence score is later used by the CHAT formatter to mark
low-confidence tokens as `xxx` (unintelligible) which is the CHAT
convention in TalkBank.

Typical usage
-------------
>>> t = WhisperTranscriber(model_size="base")
>>> utts = t.transcribe("session01.wav")
>>> for u in utts:
...     print(u.start, u.end, u.text)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class WordSegment:
    """A single recognised word with timing and confidence."""
    text: str
    start: float           # seconds from start of audio
    end: float
    probability: float     # Whisper's word-level log-prob converted to [0,1]


@dataclass
class UtteranceSegment:
    """A Whisper segment (sentence-ish) containing multiple words.

    Speaker is filled in later by the diarization stage; Whisper itself
    doesn't know who spoke.
    """
    start: float
    end: float
    text: str
    words: List[WordSegment] = field(default_factory=list)
    avg_logprob: float = 0.0
    no_speech_prob: float = 0.0
    speaker: Optional[str] = None   # "CHI", "MOT", "INV", ... set by diarizer


class WhisperTranscriber:
    """Thin wrapper around faster_whisper that returns `UtteranceSegment`s.

    Parameters
    ----------
    model_size : str
        Any faster-whisper model name.  "base" (74M, ~1GB RAM) is the
        sweet-spot for CPU; "small" (244M) gives noticeably better WER
        on child speech; "medium" (769M) is best but slow on CPU.
    device : str
        "cpu" | "cuda" | "auto".
    compute_type : str
        "int8" (fastest on CPU), "float16" (GPU), "float32" (most
        accurate).
    language : str
        ISO-639-1 code.  "en" for TalkBank; pass `None` to auto-detect.
    """

    DEFAULT_MODEL = "base"

    def __init__(
        self,
        model_size: str = DEFAULT_MODEL,
        device: str = "auto",
        compute_type: str = "int8",
        language: Optional[str] = "en",
    ) -> None:
        # Import here so the rest of the project doesn't have to install
        # faster-whisper just to run the classifier/dashboard.
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise ImportError(
                "faster-whisper is required for the audio pipeline.\n"
                "  pip install faster-whisper"
            ) from e

        self._WhisperModel = WhisperModel
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model: Optional[WhisperModel] = None  # lazy-loaded

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------
    def _load(self):
        """Lazy-load the model on first transcription."""
        if self._model is None:
            self._model = self._WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------
    def transcribe(
        self,
        audio_path: str | Path,
        *,
        vad_filter: bool = True,
        beam_size: int = 5,
    ) -> List[UtteranceSegment]:
        """Transcribe audio into a list of utterance segments.

        Parameters
        ----------
        audio_path : Path-like
            Any format supported by ffmpeg (wav, mp3, m4a, ...).
        vad_filter : bool
            Use Whisper's built-in voice-activity-detector to skip
            non-speech chunks.  Greatly reduces hallucinations during
            silences, which is common in therapy recordings.
        beam_size : int
            Beam-search width.  5 is Whisper's default.
        """
        model = self._load()
        audio_path = str(audio_path)

        segments, info = model.transcribe(
            audio_path,
            language=self.language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            word_timestamps=True,
        )

        out: List[UtteranceSegment] = []
        for seg in segments:
            words: List[WordSegment] = []
            if seg.words:
                for w in seg.words:
                    words.append(WordSegment(
                        text=w.word.strip(),
                        start=float(w.start) if w.start is not None else float(seg.start),
                        end=float(w.end) if w.end is not None else float(seg.end),
                        probability=float(w.probability) if w.probability is not None else 0.0,
                    ))
            out.append(UtteranceSegment(
                start=float(seg.start),
                end=float(seg.end),
                text=seg.text.strip(),
                words=words,
                avg_logprob=float(getattr(seg, "avg_logprob", 0.0)),
                no_speech_prob=float(getattr(seg, "no_speech_prob", 0.0)),
            ))
        return out


# ----------------------------------------------------------------------
# CLI quick-test
# ----------------------------------------------------------------------
def _cli() -> None:
    import argparse, json, sys
    ap = argparse.ArgumentParser(description="Quick Whisper transcription test.")
    ap.add_argument("audio", type=Path)
    ap.add_argument("--model", default="base",
                    choices=["tiny", "base", "small", "medium", "large-v3"])
    ap.add_argument("--lang", default="en")
    ap.add_argument("--json", action="store_true",
                    help="Emit JSON instead of human-readable text.")
    args = ap.parse_args()

    t = WhisperTranscriber(model_size=args.model, language=args.lang)
    utts = t.transcribe(args.audio)

    if args.json:
        json.dump(
            [{"start": u.start, "end": u.end, "text": u.text,
              "words": [vars(w) for w in u.words]} for u in utts],
            sys.stdout, indent=2, ensure_ascii=False,
        )
    else:
        for u in utts:
            print(f"[{u.start:6.2f} -> {u.end:6.2f}]  {u.text}")


if __name__ == "__main__":
    _cli()
