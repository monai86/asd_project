"""
Format Whisper + diarization output as a valid CHAT (.cha) transcript.

The output follows the subset of CHAT conventions actually consumed by
the existing `data_loader.py` + `pylangacq`, namely:

    - `@Begin` / `@End` sentinels
    - `@Languages`, `@Participants`, `@ID`, `@Media` headers
    - `*CHI:` / `*MOT:` main speaker tiers
    - `%tim:` dependent tier with start timestamps (so `age_months`
      and progress order can be reconstructed)
    - Low-confidence words replaced with `xxx` (unintelligible)
    - Long silences inserted as `0.` utterances by the child
    - Non-verbal adult-ish filler turns flagged with `&=vocalization`
    - Sentence-final `?` / `!` / `.` kept from Whisper

The resulting file is fully consumable by `pylangacq.read_chat`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from .whisper_transcribe import UtteranceSegment, WordSegment


# ----------------------------------------------------------------------
# Tunables
# ----------------------------------------------------------------------
# Words with probability below this are marked "xxx" (unintelligible).
DEFAULT_UNINTELLIGIBLE_THRESHOLD = 0.30

# Gaps between consecutive child utterances longer than this (seconds)
# become `*CHI: 0 .` (zero-vocalization) markers — this feeds directly
# into the `zero_vocalization_count` feature used by the classifier.
DEFAULT_ZERO_VOCALIZATION_GAP = 5.0

# Maximum gap before we stop marking as "the same silence" (avoid
# spamming zero-vocalization markers during a long pause at the start
# of a recording).
MAX_ZERO_VOCALIZATION_GAPS = 3


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _format_time(seconds: float) -> str:
    """CHAT `%tim` format: HH:MM:SS.sss."""
    if seconds < 0:
        seconds = 0
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def _clean_word(text: str) -> str:
    """Strip Whisper decorations + normalise punctuation."""
    t = text.strip()
    # Whisper sometimes leaves leading space + capitalisation mid-sentence
    t = re.sub(r"\s+", " ", t)
    return t


_END_PUNCT = {".", "?", "!"}
_STRIP_PUNCT_RE = re.compile(r"[.?!,;:\"]+$")


def _split_terminator(text: str) -> tuple[str, str]:
    """Return (body_without_terminator, terminator) where terminator is
    one of '.', '?', '!' (default '.')."""
    t = text.strip()
    if not t:
        return "", "."
    last = t[-1]
    if last in _END_PUNCT:
        return t[:-1].rstrip(), last
    return t, "."


def _render_utterance_body(
    u: UtteranceSegment,
    unintelligible_threshold: float,
) -> str:
    """Word-level render with low-confidence -> 'xxx'.

    If Whisper didn't give word-level timings/probabilities (rare),
    fall back to the raw segment text.
    """
    if not u.words:
        body, _term = _split_terminator(u.text)
        return body

    tokens: List[str] = []
    for w in u.words:
        word = _clean_word(w.text)
        # Strip sentence-final punctuation per-word; we add one at the end.
        word_no_punct = _STRIP_PUNCT_RE.sub("", word)
        if not word_no_punct:
            continue
        if w.probability < unintelligible_threshold:
            tokens.append("xxx")
        else:
            tokens.append(word_no_punct.lower())
    return " ".join(tokens)


# ----------------------------------------------------------------------
# Core formatter
# ----------------------------------------------------------------------
def utterances_to_chat(
    utterances: Sequence[UtteranceSegment],
    *,
    child_id: str = "CHI001",
    child_age_months: Optional[float] = None,
    child_sex: Optional[str] = None,
    child_group: str = "ASD",         # ASD / TD / DD — free-form
    media_filename: Optional[str] = None,
    language: str = "eng",
    unintelligible_threshold: float = DEFAULT_UNINTELLIGIBLE_THRESHOLD,
    zero_vocalization_gap: float = DEFAULT_ZERO_VOCALIZATION_GAP,
    max_zero_vocalization_gaps: int = MAX_ZERO_VOCALIZATION_GAPS,
) -> str:
    """Convert an ordered list of utterances into a CHAT transcript.

    All utterances are expected to already have `u.speaker` filled
    (either "CHI" or any adult label — we keep the adult label as-is so
    downstream tools can distinguish MOT/INV/FAT if available).

    Returns
    -------
    str
        The full CHAT document, ready to be written to `.cha`.
    """
    utts = sorted(utterances, key=lambda u: u.start)

    # --- Participants header ---------------------------------------------------
    adult_labels: List[str] = []
    seen: set[str] = set()
    for u in utts:
        sp = (u.speaker or "").upper()
        if sp and sp != "CHI" and sp not in seen:
            adult_labels.append(sp)
            seen.add(sp)
    if not adult_labels:
        adult_labels = ["MOT"]

    # (code, role) pairs — role strings here MUST match the role slot
    # of the corresponding @ID line below (pylangacq validates this).
    child_role = "Target_Child"
    adult_roles: dict[str, str] = {
        "MOT": "Mother", "FAT": "Father", "INV": "Investigator",
        "SIS": "Sibling", "BRO": "Sibling", "GRA": "Grandmother",
    }
    participants_line = f"CHI {child_role}"
    for lab in adult_labels:
        participants_line += f", {lab} {adult_roles.get(lab, lab.title())}"

    # --- Age in CHAT format "Y;MM.DD" ------------------------------------------
    age_field = ""
    if child_age_months is not None and child_age_months > 0:
        years = int(child_age_months // 12)
        months = int(child_age_months - years * 12)
        age_field = f"{years};{months:02d}.00"

    sex_field = (child_sex or "").lower()
    if sex_field not in ("male", "female"):
        sex_field = ""

    # --- Build output ----------------------------------------------------------
    lines: List[str] = []
    lines.append("@UTF8")
    lines.append("@Begin")
    lines.append(f"@Languages:\t{language}")
    lines.append(f"@Participants:\t{participants_line}")
    # CHAT @ID format (10 pipe-separated fields):
    #   language | corpus | code | age | sex | group | SES | role | education | custom
    lines.append(
        f"@ID:\t{language}|asd-project|CHI|{age_field}|{sex_field}|{child_group}||{child_role}|{child_id}|"
    )
    for lab in adult_labels:
        role = adult_roles.get(lab, lab.title())
        lines.append(
            f"@ID:\t{language}|asd-project|{lab}||||||{role}||"
        )
    if media_filename:
        lines.append(f"@Media:\t{media_filename}, audio")

    # Stream through utterances, inserting 0-vocalization markers when
    # the child goes silent for too long.
    prev_end: Optional[float] = None
    prev_was_child: bool = False
    zero_inserted = 0

    for u in utts:
        speaker = (u.speaker or "MOT").upper()
        is_child = speaker == "CHI"

        # Zero-vocalization: long gap AND we had (or will have) a child turn
        if (
            prev_end is not None
            and prev_was_child
            and (u.start - prev_end) > zero_vocalization_gap
            and zero_inserted < max_zero_vocalization_gaps
        ):
            gap_mid = prev_end + (u.start - prev_end) / 2
            lines.append("*CHI:\t0 .")
            lines.append(f"%tim:\t{_format_time(gap_mid)}")
            zero_inserted += 1

        body = _render_utterance_body(u, unintelligible_threshold)
        _raw_body, terminator = _split_terminator(u.text)

        # If Whisper produced nothing intelligible but the segment was
        # non-trivially long, treat it as a non-verbal vocalization.
        if not body.strip():
            if (u.end - u.start) >= 0.3:
                lines.append(f"*{speaker}:\t&=vocalization .")
                lines.append(f"%tim:\t{_format_time(u.start)}")
            prev_end = u.end
            prev_was_child = is_child
            continue

        lines.append(f"*{speaker}:\t{body} {terminator}")
        lines.append(f"%tim:\t{_format_time(u.start)}")

        prev_end = u.end
        prev_was_child = is_child

    lines.append("@End")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------
# Convenience: write straight to disk
# ----------------------------------------------------------------------
def write_chat(
    utterances: Sequence[UtteranceSegment],
    output_path: str | Path,
    **kwargs,
) -> Path:
    """Render `utterances_to_chat(...)` and write to disk.  Returns the path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = utterances_to_chat(utterances, **kwargs)
    output_path.write_text(text, encoding="utf-8")
    return output_path
