"""
Whisper-based ASR wrapper with TH+EN code-switching support.

Uses ``faster-whisper`` (4x faster than openai-whisper, same accuracy) to
transcribe child-therapy audio into word-level segments with timestamps,
confidence scores, and per-segment language tags.

Hallucination filter and language-aware initial prompts are applied so
the resulting CHAT transcript is closer to what was actually said in
both English and Thai.

Typical usage
-------------
>>> t = WhisperTranscriber(model_size="small", strategy="auto")
>>> utts = t.transcribe("session01.wav")
>>> for u in utts:
...     print(u.start, u.end, u.language, u.text)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal, Optional


# ----------------------------------------------------------------------
# Initial prompts (bias Whisper towards child-therapy / TH+EN domain)
# ----------------------------------------------------------------------
PROMPT_EN = (
    "This is a young child speaking with a parent or therapist during play. "
    "Toys, animals, colours, numbers, mom, dad, yes, no, look, more, please."
)
PROMPT_TH = (
    "เด็กเล็กกำลังพูดกับผู้ปกครองหรือนักบำบัดขณะเล่นของเล่น "
    "มีของเล่น สี ตัวเลข แม่ พ่อ ชอบ ไม่ชอบ เอา ให้."
)
PROMPT_BILINGUAL = PROMPT_EN + " " + PROMPT_TH

# Language strategy options for the dashboard / CLI
LanguageStrategy = Literal[
    "auto", "english", "thai", "dual_pass", "thai_specialized",
]

# Hallucination filter thresholds
_HALLUCINATION_NO_SPEECH_PROB = 0.85
_HALLUCINATION_AVG_LOGPROB = -1.25
_HALLUCINATION_REPEAT_NGRAM = 4   # reject segment if same 4-gram repeats >=3x


def _looks_hallucinated(text: str, avg_logprob: float, no_speech_prob: float) -> bool:
    """Heuristic to drop common Whisper hallucinations on silence / noise."""
    if not text or not text.strip():
        return True
    if no_speech_prob > _HALLUCINATION_NO_SPEECH_PROB:
        return True
    if avg_logprob < _HALLUCINATION_AVG_LOGPROB:
        return True
    # Detect repeated n-grams ("thank you. thank you. thank you. ...")
    tokens = re.findall(r"\w+", text.lower())
    if len(tokens) >= _HALLUCINATION_REPEAT_NGRAM * 3:
        n = _HALLUCINATION_REPEAT_NGRAM
        ngrams = [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]
        if ngrams:
            top = max(ngrams.count(g) for g in set(ngrams))
            if top >= 3:
                return True
    return False


@dataclass
class WordSegment:
    """A single recognised word with timing and confidence."""
    text: str
    start: float           # seconds from start of audio
    end: float
    probability: float     # Whisper's word-level log-prob converted to [0,1]
    language: Optional[str] = None   # "en" / "th" / None


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
    language: Optional[str] = None  # detected language: "en" / "th" / None


class WhisperTranscriber:
    """Thin wrapper around faster_whisper that returns ``UtteranceSegment``s.

    Parameters
    ----------
    model_size : str
        Any faster-whisper model name.  ``"small"`` (244M) is the new
        default — much better than ``"base"`` on child speech and Thai.
        ``"medium"`` (769M) is best but slow on CPU.
    device : str
        ``"cpu"`` | ``"cuda"`` | ``"auto"``.
    compute_type : str
        ``"int8"`` (fastest on CPU), ``"float16"`` (GPU), ``"float32"``
        (most accurate).
    language : Optional[str]
        ISO-639-1 code (``"en"``/``"th"``) or ``None`` to auto-detect.
        Setting this overrides ``strategy``.
    strategy : LanguageStrategy
        Higher-level language strategy:

        * ``"auto"``  — single pass, Whisper detects language (default).
        * ``"english"`` / ``"thai"`` — force a single language.
        * ``"dual_pass"`` — run EN and TH passes, pick per-segment winner.
        * ``"thai_specialized"`` — use a Thai-fine-tuned Whisper model.
    initial_prompt : Optional[str]
        Override the default TH/EN clinical prompt.
    """

    DEFAULT_MODEL = "small"   # was "base" — small is markedly better on child speech and Thai

    def __init__(
        self,
        model_size: str = DEFAULT_MODEL,
        device: str = "auto",
        compute_type: str = "int8",
        language: Optional[str] = None,
        strategy: LanguageStrategy = "auto",
        initial_prompt: Optional[str] = None,
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
        self.strategy = strategy
        # `language` overrides strategy if explicitly set ("en" / "th" / None)
        if language is not None:
            self._explicit_language: Optional[str] = language
        else:
            self._explicit_language = {
                "english": "en", "thai": "th", "auto": None,
                "dual_pass": None, "thai_specialized": None,
            }.get(strategy, None)
        self._initial_prompt = initial_prompt
        self._model: Optional["WhisperModel"] = None      # lazy-loaded primary
        self._model_th: Optional["WhisperModel"] = None   # lazy-loaded Thai-specialized

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------
    def _load(self):
        """Lazy-load the primary multilingual Whisper model."""
        if self._model is None:
            self._model = self._WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def _load_thai_specialized(self):
        """Lazy-load a Thai-specialized Whisper checkpoint (no HF token needed).

        Falls back to the primary model if the Thai checkpoint cannot be
        downloaded (e.g. offline environment).
        """
        if self._model_th is not None:
            return self._model_th
        try:
            self._model_th = self._WhisperModel(
                "biodatlab/whisper-th-medium-combined",
                device=self.device,
                compute_type=self.compute_type,
            )
        except Exception as e:  # noqa: BLE001
            print(f"[whisper] Thai-specialized model unavailable, using primary: {e}")
            self._model_th = self._load()
        return self._model_th

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _run_single(
        self,
        model,
        audio_path: str,
        *,
        language: Optional[str],
        vad_filter: bool,
        beam_size: int,
        prompt: Optional[str],
    ) -> List[UtteranceSegment]:
        """Run one Whisper pass and return parsed UtteranceSegments.

        Applies hallucination filtering and per-segment language tagging.
        """
        segments, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            word_timestamps=True,
            initial_prompt=prompt,
            condition_on_previous_text=False,
            temperature=[0.0, 0.2, 0.4, 0.6],
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
        )
        detected_lang = getattr(info, "language", language)

        out: List[UtteranceSegment] = []
        for seg in segments:
            avg_logprob = float(getattr(seg, "avg_logprob", 0.0))
            no_speech_prob = float(getattr(seg, "no_speech_prob", 0.0))
            text = (seg.text or "").strip()
            if _looks_hallucinated(text, avg_logprob, no_speech_prob):
                continue
            seg_lang = getattr(seg, "language", None) or detected_lang
            words: List[WordSegment] = []
            if seg.words:
                for w in seg.words:
                    words.append(WordSegment(
                        text=(w.word or "").strip(),
                        start=float(w.start) if w.start is not None else float(seg.start),
                        end=float(w.end) if w.end is not None else float(seg.end),
                        probability=float(w.probability) if w.probability is not None else 0.0,
                        language=seg_lang,
                    ))
            out.append(UtteranceSegment(
                start=float(seg.start),
                end=float(seg.end),
                text=text,
                words=words,
                avg_logprob=avg_logprob,
                no_speech_prob=no_speech_prob,
                language=seg_lang,
            ))
        return out

    @staticmethod
    def _merge_dual_pass(
        en_segs: List[UtteranceSegment],
        th_segs: List[UtteranceSegment],
    ) -> List[UtteranceSegment]:
        """Merge English-pass and Thai-pass results, picking per-segment winner.

        Two segments are considered overlapping if their time ranges
        overlap by >=50% of the shorter one.  The one with higher
        ``avg_logprob`` wins.  Non-overlapping segments are kept as-is.
        """
        merged: List[UtteranceSegment] = []
        used_th = [False] * len(th_segs)
        for en in en_segs:
            best_idx = -1
            best_overlap = 0.0
            for j, th in enumerate(th_segs):
                if used_th[j]:
                    continue
                overlap = max(0.0, min(en.end, th.end) - max(en.start, th.start))
                shorter = min(en.end - en.start, th.end - th.start) or 1e-6
                if overlap / shorter >= 0.5 and overlap > best_overlap:
                    best_overlap = overlap
                    best_idx = j
            if best_idx >= 0:
                th = th_segs[best_idx]
                used_th[best_idx] = True
                winner = en if en.avg_logprob >= th.avg_logprob else th
                merged.append(winner)
            else:
                merged.append(en)
        for j, th in enumerate(th_segs):
            if not used_th[j]:
                merged.append(th)
        merged.sort(key=lambda s: s.start)
        return merged

    @staticmethod
    def _recognized_word_count(segments: List[UtteranceSegment]) -> int:
        return sum(len(re.findall(r"\w+", seg.text)) for seg in segments)

    def _fallback_if_sparse(
        self,
        primary: List[UtteranceSegment],
        model,
        audio_path: str,
        *,
        language: Optional[str],
        beam_size: int,
        prompt: Optional[str],
    ) -> List[UtteranceSegment]:
        """Retry without VAD when the first pass looks under-transcribed.

        Therapy recordings often contain short child responses after long
        pauses. VAD can drop those responses, so a second pass is safer when
        the first pass returns only a very small sample.
        """
        if len(primary) >= 4 and self._recognized_word_count(primary) >= 12:
            return primary

        fallback = self._run_single(
            model,
            audio_path,
            language=language,
            vad_filter=False,
            beam_size=beam_size,
            prompt=prompt,
        )
        if len(fallback) > len(primary) or self._recognized_word_count(fallback) > self._recognized_word_count(primary):
            return fallback
        return primary

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

        The ``strategy`` set on the constructor controls how language is
        handled (see class docstring).

        Parameters
        ----------
        audio_path : Path-like
            Any format supported by ffmpeg (wav, mp3, m4a, ...).
        vad_filter : bool
            Use Whisper's built-in voice-activity-detector to skip
            non-speech chunks.  Greatly reduces hallucinations during
            silences common in therapy recordings.
        beam_size : int
            Beam-search width.  5 is Whisper's default.
        """
        audio_path = str(audio_path)

        # Choose initial prompt based on the language we're targeting
        if self._initial_prompt is not None:
            prompt: Optional[str] = self._initial_prompt
        elif self.strategy == "english" or self._explicit_language == "en":
            prompt = PROMPT_EN
        elif self.strategy == "thai" or self._explicit_language == "th":
            prompt = PROMPT_TH
        else:
            prompt = PROMPT_BILINGUAL

        if self.strategy == "dual_pass":
            model = self._load()
            en = self._run_single(
                model, audio_path, language="en",
                vad_filter=vad_filter, beam_size=beam_size, prompt=PROMPT_EN,
            )
            if vad_filter:
                en = self._fallback_if_sparse(
                    en, model, audio_path,
                    language="en", beam_size=beam_size, prompt=PROMPT_EN,
                )
            th = self._run_single(
                model, audio_path, language="th",
                vad_filter=vad_filter, beam_size=beam_size, prompt=PROMPT_TH,
            )
            if vad_filter:
                th = self._fallback_if_sparse(
                    th, model, audio_path,
                    language="th", beam_size=beam_size, prompt=PROMPT_TH,
                )
            return self._merge_dual_pass(en, th)

        if self.strategy == "thai_specialized":
            model = self._load_thai_specialized()
            primary = self._run_single(
                model, audio_path, language="th",
                vad_filter=vad_filter, beam_size=beam_size, prompt=PROMPT_TH,
            )
            if vad_filter:
                return self._fallback_if_sparse(
                    primary, model, audio_path,
                    language="th", beam_size=beam_size, prompt=PROMPT_TH,
                )
            return primary

        # auto / english / thai => single pass
        model = self._load()
        primary = self._run_single(
            model, audio_path, language=self._explicit_language,
            vad_filter=vad_filter, beam_size=beam_size, prompt=prompt,
        )
        if vad_filter:
            return self._fallback_if_sparse(
                primary, model, audio_path,
                language=self._explicit_language, beam_size=beam_size, prompt=prompt,
            )
        return primary


# ----------------------------------------------------------------------
# CLI quick-test
# ----------------------------------------------------------------------
def _cli() -> None:
    import argparse, json, sys
    ap = argparse.ArgumentParser(description="Quick Whisper transcription test.")
    ap.add_argument("audio", type=Path)
    ap.add_argument("--model", default="small",
                    choices=["tiny", "base", "small", "medium", "large-v3"])
    ap.add_argument("--strategy", default="auto",
                    choices=["auto", "english", "thai", "dual_pass", "thai_specialized"])
    ap.add_argument("--lang", default=None,
                    help="Override language: 'en'/'th'/None (auto)")
    ap.add_argument("--json", action="store_true",
                    help="Emit JSON instead of human-readable text.")
    args = ap.parse_args()

    t = WhisperTranscriber(
        model_size=args.model, language=args.lang, strategy=args.strategy,
    )
    utts = t.transcribe(args.audio)

    if args.json:
        json.dump(
            [{"start": u.start, "end": u.end, "lang": u.language,
              "text": u.text, "words": [vars(w) for w in u.words]} for u in utts],
            sys.stdout, indent=2, ensure_ascii=False,
        )
    else:
        for u in utts:
            lang = u.language or "??"
            print(f"[{u.start:6.2f} -> {u.end:6.2f}]  ({lang})  {u.text}")


if __name__ == "__main__":
    _cli()
