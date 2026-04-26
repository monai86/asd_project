"""
End-to-end audio-to-CHAT pipeline.

    audio file                                produces:
        │
        ├─ WhisperTranscriber ────────────────▶  list[UtteranceSegment]
        │                                        (words, timings, conf)
        │
        ├─ Diarizer (pyannote OR pitch) ──────▶  .speaker filled in
        │                                        for each utterance
        │
        └─ chat_formatter ────────────────────▶  .cha text

This file wires those three together into a single function the
dashboard + CLI can call.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .chat_formatter import utterances_to_chat, write_chat
from .chatter_validator import ValidationReport, validate_chat_file
from .diarization import BaseDiarizer, get_diarizer
from .segmentation import clean_segments
from .whisper_transcribe import LanguageStrategy, WhisperTranscriber


@dataclass
class PipelineResult:
    """What the pipeline returns so callers can inspect intermediate state."""
    chat_text: str
    chat_path: Optional[Path]
    utterances: list      # list[UtteranceSegment] — kept generic to avoid re-import
    n_child_utterances: int
    n_adult_utterances: int
    total_duration_sec: float
    validation: Optional[ValidationReport] = None


def audio_to_cha(
    audio_path: str | Path,
    *,
    output_path: Optional[str | Path] = None,
    # Whisper options
    model_size: str = "small",
    device: str = "auto",
    language: Optional[str] = None,
    strategy: LanguageStrategy = "auto",
    # Diarization
    diarizer: Optional[BaseDiarizer] = None,
    prefer_pyannote: bool = False,
    hf_token: Optional[str] = None,
    enrollment_audio_path: Optional[str | Path] = None,
    # Metadata baked into the CHAT header
    child_id: str = "CHI001",
    child_age_months: Optional[float] = None,
    child_sex: Optional[str] = None,
    child_group: str = "ASD",
    activities: Optional[str] = None,
    # Formatter options
    unintelligible_threshold: float = 0.30,
    # Validation
    validate: bool = True,
) -> PipelineResult:
    """Transcribe + diarize + format an audio file into a CHAT transcript.

    Parameters
    ----------
    audio_path : Path-like
        Input audio (wav / mp3 / m4a / etc — anything ffmpeg reads).
    output_path : Path-like or None
        If given, the resulting `.cha` is written here.  If None, the
        CHAT text is only returned in-memory.
    model_size : str
        Whisper model size ("tiny" | "base" | "small" | "medium" | "large-v3").
        "small" is the new default — markedly better than "base" on child
        speech and Thai.
    language : Optional[str]
        Force a single language ("en" / "th") or ``None`` to auto-detect.
    strategy : LanguageStrategy
        Higher-level language strategy.  ``"auto"`` (default), ``"english"``,
        ``"thai"``, ``"dual_pass"`` (run EN+TH, pick per-segment winner) or
        ``"thai_specialized"`` (use a Thai-fine-tuned Whisper model).
    diarizer : BaseDiarizer or None
        Override the diarizer.  If None, auto-selects pyannote (if
        available + HF_TOKEN is set) or falls back to pitch heuristic.
    child_age_months, child_sex, child_group, child_id
        Clinical metadata — stored in the CHAT header so the existing
        `data_loader.py` can pick it up automatically.

    Returns
    -------
    PipelineResult
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(audio_path)

    # ---- 1. ASR ------------------------------------------------------------
    transcriber = WhisperTranscriber(
        model_size=model_size, device=device,
        language=language, strategy=strategy,
    )
    utterances = transcriber.transcribe(audio_path)

    # ---- 2. Diarization ---------------------------------------------------
    if diarizer is None:
        diarizer = get_diarizer(
            prefer_pyannote=prefer_pyannote,
            hf_token=hf_token,
            child_age_months=child_age_months,
            enrollment_audio_path=enrollment_audio_path,
        )
    utterances = diarizer.assign(audio_path, utterances)

    # ---- 3. Clean / re-segment -------------------------------------------
    utterances = clean_segments(utterances)

    # ---- 4. CHAT formatting ----------------------------------------------
    chat_text = utterances_to_chat(
        utterances,
        child_id=child_id,
        child_age_months=child_age_months,
        child_sex=child_sex,
        child_group=child_group,
        media_filename=audio_path.name,
        activities=activities,
        unintelligible_threshold=unintelligible_threshold,
    )

    chat_path: Optional[Path] = None
    if output_path is not None:
        chat_path = Path(output_path)
        chat_path.parent.mkdir(parents=True, exist_ok=True)
        chat_path.write_text(chat_text, encoding="utf-8")

    # ---- 5. CHATTER validation (best-effort) -----------------------------
    validation: Optional[ValidationReport] = None
    if validate and chat_path is not None:
        validation = validate_chat_file(chat_path, auto_fix_first=True, save_fixed=True)
        # Refresh chat_text from disk in case auto-fix changed it
        if validation.fixed_count > 0:
            chat_text = chat_path.read_text(encoding="utf-8")

    # ---- 4. Stats for the caller / dashboard -----------------------------
    n_child = sum(1 for u in utterances if (u.speaker or "").upper() == "CHI")
    n_adult = len(utterances) - n_child
    total_duration = max((u.end for u in utterances), default=0.0)

    return PipelineResult(
        chat_text=chat_text,
        chat_path=chat_path,
        utterances=list(utterances),
        n_child_utterances=n_child,
        n_adult_utterances=n_adult,
        total_duration_sec=total_duration,
        validation=validation,
    )


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def _cli() -> None:
    import argparse
    ap = argparse.ArgumentParser(
        description="Audio (.wav/.mp3/...) -> CHAT (.cha) pipeline."
    )
    ap.add_argument("audio", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=None,
                    help="Where to write the .cha file.  "
                         "Default: <audio_stem>.cha next to the audio.")
    ap.add_argument("--model", default="small",
                    choices=["tiny", "base", "small", "medium", "large-v3"])
    ap.add_argument("--lang", default=None,
                    help="Force language: 'en' / 'th' / None (auto)")
    ap.add_argument("--strategy", default="auto",
                    choices=["auto", "english", "thai", "dual_pass", "thai_specialized"])
    ap.add_argument("--age-months", type=float, default=None)
    ap.add_argument("--sex", choices=["male", "female"], default=None)
    ap.add_argument("--group", default="ASD", help="ASD / TD / DD / ...")
    ap.add_argument("--child-id", default="CHI001")
    ap.add_argument("--no-pyannote", action="store_true",
                    help="Skip pyannote and use the pitch-heuristic "
                         "diarizer directly (no HF token required).")
    args = ap.parse_args()

    output = args.output or args.audio.with_suffix(".cha")
    result = audio_to_cha(
        args.audio,
        output_path=output,
        model_size=args.model,
        language=args.lang,
        strategy=args.strategy,
        prefer_pyannote=not args.no_pyannote,
        child_id=args.child_id,
        child_age_months=args.age_months,
        child_sex=args.sex,
        child_group=args.group,
    )

    print(f"[ok] wrote {result.chat_path}")
    print(f"     child utterances : {result.n_child_utterances}")
    print(f"     adult utterances : {result.n_adult_utterances}")
    print(f"     duration         : {result.total_duration_sec:.1f} s")


if __name__ == "__main__":
    _cli()
