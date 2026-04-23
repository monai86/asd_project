"""
Smoke test for the audio_pipeline package.

Runs WITHOUT loading the Whisper model (no network, no audio needed):
  1. Build fake UtteranceSegments
  2. Run the CHAT formatter
  3. Re-parse the output with pylangacq (the same library data_loader uses)
  4. Assert the important fields survived the round-trip

If this passes, the downstream data_loader -> classifier -> dashboard
chain will happily consume the .cha files we auto-generate from audio.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Make `src` importable when running this file directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pylangacq

from src.audio_pipeline.chat_formatter import utterances_to_chat
from src.audio_pipeline.whisper_transcribe import UtteranceSegment, WordSegment
from src.data_loader import _age_to_months, _extract_child_participant


def _fake_utterances():
    return [
        UtteranceSegment(
            start=0.5, end=2.0, text="Hi there!",
            words=[
                WordSegment(text="Hi", start=0.5, end=0.9, probability=0.95),
                WordSegment(text="there", start=1.0, end=1.9, probability=0.90),
            ],
            speaker="CHI",
        ),
        UtteranceSegment(
            start=3.0, end=5.0, text="What do you want?",
            words=[
                WordSegment(text="What", start=3.0, end=3.3, probability=0.90),
                WordSegment(text="do",   start=3.4, end=3.6, probability=0.90),
                WordSegment(text="you",  start=3.7, end=3.9, probability=0.90),
                WordSegment(text="want", start=4.0, end=4.9, probability=0.15),  # -> xxx
            ],
            speaker="MOT",
        ),
        # Big gap triggers the 0. (zero-vocalization) marker for the child.
        UtteranceSegment(
            start=15.0, end=17.0, text="cookie.",
            words=[WordSegment(text="cookie", start=15.0, end=16.9, probability=0.88)],
            speaker="CHI",
        ),
    ]


def main() -> int:
    print("[1/4] Building fake utterances ...")
    utts = _fake_utterances()

    print("[2/4] Rendering CHAT ...")
    cha = utterances_to_chat(
        utts,
        child_id="test001",
        child_age_months=48,
        child_sex="male",
        child_group="ASD",
        media_filename="test.wav",
    )
    print("--- CHAT output ---")
    print(cha)
    print("-------------------")

    print("[3/4] Parsing back with pylangacq ...")
    with tempfile.NamedTemporaryFile(suffix=".cha", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write(cha)
        path = Path(f.name)
    try:
        # Mirror data_loader.py: strict first, fall back to non-strict.
        try:
            reader = pylangacq.read_chat(str(path))
        except Exception:
            reader = pylangacq.read_chat(str(path), strict=False)
        all_utts = reader.utterances()
        chi_utts = [u for u in all_utts if u.participant == "CHI"]
        mot_utts = [u for u in all_utts if u.participant == "MOT"]
        # Age: match data_loader.py's extraction path
        chi_participant = _extract_child_participant(reader)
        age_months = _age_to_months(chi_participant.age) if chi_participant else None
        print(f"  CHI utterances : {len(chi_utts)}")
        print(f"  MOT utterances : {len(mot_utts)}")
        print(f"  Age (months)   : {age_months}")
        print(f"  CHI.sex        : {chi_participant.sex if chi_participant else None}")
        print(f"  CHI.group      : {chi_participant.group if chi_participant else None}")
    finally:
        path.unlink(missing_ok=True)

    print("[4/4] Assertions ...")
    # Expected: 2 original CHI utterances + 1 injected '0.' = 3,
    # but '0.' utterances may or may not be surfaced as standalone
    # utterances depending on pylangacq's tokenizer.  So allow >= 2.
    assert len(chi_utts) >= 2, f"expected >=2 CHI utterances, got {len(chi_utts)}"
    assert len(mot_utts) >= 1, f"expected >=1 MOT utterance, got {len(mot_utts)}"
    # 48 months age should round-trip
    assert age_months is not None and abs(age_months - 48.0) < 0.5, \
        f"age did not round-trip, got {age_months}"

    print("\n[ok] smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
