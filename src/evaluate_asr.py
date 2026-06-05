"""
Evaluate the Whisper ASR step against TalkBank ground-truth transcripts.

For every (audio, .cha) pair under `data/`, we:
  1. Extract the gold child utterances from the .cha (pylangacq).
  2. Run the audio through our Whisper + diarization pipeline.
  3. Pull out the hypothesized child utterances from the resulting .cha.
  4. Compute WER (+ accuracy) using `jiwer`.

We evaluate per-file AND pooled, so the report captures both
variability and overall quality.

Outputs:
    reports/metrics/asr_evaluation.csv   per-file WER/CER/n_words
    reports/metrics/asr_evaluation.md    human-readable summary
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd

try:
    import pylangacq
except ImportError as e:
    raise ImportError("pylangacq required: pip install pylangacq") from e

try:
    import jiwer
except ImportError as e:
    raise ImportError("jiwer required for WER: pip install jiwer") from e


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
METRIC_DIR = PROJECT_ROOT / "reports" / "metrics"
METRIC_DIR.mkdir(parents=True, exist_ok=True)


# -------- text normalisation for fair comparison --------
_CHAT_CLEAN = re.compile(r"[^a-z0-9\s'\u0e00-\u0e7f]")
_WS = re.compile(r"\s+")


def _normalize(text: str) -> str:
    t = text.lower()
    t = t.replace("xxx", " ")
    t = _CHAT_CLEAN.sub(" ", t)
    
    # Check if text contains Thai characters
    has_thai = any('\u0e00' <= char <= '\u0e7f' for char in t)
    if has_thai:
        try:
            from pythainlp.tokenize import word_tokenize
            tokens = word_tokenize(t)
            t = " ".join(tokens)
        except ImportError:
            pass

    t = _WS.sub(" ", t).strip()
    return t


def _child_text_from_cha(cha_path: Path) -> str:
    """Concatenate all child (`*CHI:`) utterances from a .cha into one string."""
    try:
        try:
            reader = pylangacq.read_chat(str(cha_path))
        except Exception:
            reader = pylangacq.read_chat(str(cha_path), strict=False)
    except Exception as e:
        print(f"  [warn] could not read {cha_path.name}: {e}")
        return ""
    utts = [u for u in reader.utterances() if u.participant == "CHI"]
    parts: List[str] = []
    for u in utts:
        for tok in u.tokens:
            word = getattr(tok, "word", "") or ""
            if word:
                parts.append(word)
    return " ".join(parts)


# -----------------------------------------------------------------------
@dataclass
class ASRResult:
    file: str
    n_gold_words: int
    n_hyp_words: int
    wer: float
    cer: float


def evaluate_pair(
    audio_path: Path,
    gold_cha: Path,
    *,
    model_size: str = "base",
    prefer_pyannote: bool = False,
) -> Optional[ASRResult]:
    """Run pipeline + score against gold.  Returns None if anything fails."""
    from src.audio_pipeline import audio_to_cha  # lazy import

    gold_text = _normalize(_child_text_from_cha(gold_cha))
    if not gold_text:
        print(f"  [skip] {gold_cha.name}: gold has no child tokens")
        return None

    out_cha = METRIC_DIR / f"_asr_hyp_{audio_path.stem}.cha"
    try:
        audio_to_cha(
            audio_path,
            output_path=out_cha,
            model_size=model_size,
            prefer_pyannote=prefer_pyannote,
        )
    except Exception as e:
        print(f"  [fail] {audio_path.name}: {e}")
        return None

    hyp_text = _normalize(_child_text_from_cha(out_cha))
    if not hyp_text:
        hyp_text = "[empty]"  # jiwer requires non-empty

    wer = float(jiwer.wer(gold_text, hyp_text))
    cer = float(jiwer.cer(gold_text, hyp_text))

    return ASRResult(
        file=audio_path.name,
        n_gold_words=len(gold_text.split()),
        n_hyp_words=len(hyp_text.split()),
        wer=wer,
        cer=cer,
    )


# -----------------------------------------------------------------------
def find_pairs(data_dir: Path) -> List[tuple[Path, Path]]:
    """Find all (audio, .cha) pairs under `data_dir`.

    A pair is any audio file (.wav / .mp3 / .m4a) that has a .cha with
    the same stem in the same folder.
    """
    audio_exts = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
    pairs: List[tuple[Path, Path]] = []
    for audio in data_dir.rglob("*"):
        if audio.suffix.lower() not in audio_exts:
            continue
        cha = audio.with_suffix(".cha")
        if cha.exists():
            pairs.append((audio, cha))
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="base",
                    choices=["tiny", "base", "small", "medium", "large-v3"])
    ap.add_argument("--limit", type=int, default=None,
                    help="Evaluate only the first N pairs (for quick smoke tests).")
    ap.add_argument("--use-pyannote", action="store_true",
                    help="Use pyannote diarization (requires HF_TOKEN).")
    ap.add_argument("--data-dir", type=Path, default=DATA_DIR)
    args = ap.parse_args()

    pairs = find_pairs(args.data_dir)
    print(f"Found {len(pairs)} (audio, .cha) pairs under {args.data_dir}")
    if args.limit:
        pairs = pairs[: args.limit]
        print(f"Limiting to first {len(pairs)}.")

    if not pairs:
        print(
            "\nNo audio files found next to .cha files.  "
            "TalkBank distributes audio separately from the zipped "
            "CHAT corpora — you need to download the companion .wav/.mp3 "
            "files from https://asd.talkbank.org and drop them next to "
            "the matching .cha before re-running this script."
        )
        return

    rows: List[ASRResult] = []
    for i, (audio, cha) in enumerate(pairs, 1):
        print(f"[{i}/{len(pairs)}] {audio.relative_to(args.data_dir)}")
        r = evaluate_pair(
            audio, cha,
            model_size=args.model,
            prefer_pyannote=args.use_pyannote,
        )
        if r is not None:
            rows.append(r)
            print(f"    WER={r.wer:.3f}  CER={r.cer:.3f}  "
                  f"(gold={r.n_gold_words}w, hyp={r.n_hyp_words}w)")

    if not rows:
        print("\nNo successful evaluations — nothing written.")
        return

    df = pd.DataFrame([vars(r) for r in rows])
    out_csv = METRIC_DIR / "asr_evaluation.csv"
    df.to_csv(out_csv, index=False)
    print(f"\n[saved] {out_csv.relative_to(PROJECT_ROOT)}")

    summary = {
        "n_files": len(df),
        "mean_wer": float(df["wer"].mean()),
        "median_wer": float(df["wer"].median()),
        "mean_cer": float(df["cer"].mean()),
        "total_gold_words": int(df["n_gold_words"].sum()),
    }
    md = [
        "# ASR Evaluation",
        "",
        f"- Model: **Whisper {args.model}**",
        f"- Files evaluated: **{summary['n_files']}**",
        f"- Mean WER: **{summary['mean_wer']:.3f}**",
        f"- Median WER: **{summary['median_wer']:.3f}**",
        f"- Mean CER: **{summary['mean_cer']:.3f}**",
        f"- Total gold words: **{summary['total_gold_words']}**",
        "",
        "## Per-file results",
        "",
        df.to_markdown(index=False),
    ]
    out_md = METRIC_DIR / "asr_evaluation.md"
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(f"[saved] {out_md.relative_to(PROJECT_ROOT)}")

    print(
        f"\nSummary: mean WER = {summary['mean_wer']:.3f} over "
        f"{summary['n_files']} files (~{summary['total_gold_words']} gold words)."
    )


if __name__ == "__main__":
    main()
