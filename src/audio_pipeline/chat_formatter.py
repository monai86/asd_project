"""
Format Whisper + diarization output as a valid CHAT (.cha) transcript.

Implements the subset of CHAT conventions consumed by ``pylangacq`` and
expected by TalkBank's CHATTER validator:

    * ``@UTF8`` / ``@Begin`` / ``@End`` sentinels
    * ``@Languages`` (single or comma-separated for code-switching)
    * ``@Participants``, ``@ID`` (10 pipe-separated fields)
    * ``@Date``, ``@Coder``, ``@Comment``, ``@Activities``, ``@Media``
    * ``*CHI:`` / ``*MOT:`` / ``*INV:`` / ``*FAT:`` main speaker tiers
    * ``%tim:`` dependent tier with HH:MM:SS.sss start timestamps
    * Word-level CHAT codes:
        - ``xxx`` (unintelligible) when Whisper confidence < threshold
        - ``&-um``/``&-uh`` (fillers) for known filler words
        - ``[/]`` immediate repetition (stutter), ``[//]`` reformulation
        - ``(.)`` short pause, ``(..)`` medium pause, ``(...)`` long pause
        - ``[- eng]`` / ``[- tha]`` inline language switch (CHAT spec)
    * Sentence terminators: ``.`` ``?`` ``!`` ``+/.`` (interrupted)
      ``+...`` (trailing off)
    * Long child silences become ``*CHI: 0 .`` (zero-vocalization marker)
    * Non-verbal long segments become ``&=vocalization``

The resulting file passes ``pylangacq.read_chat`` and \u2014 with Java
installed \u2014 the TalkBank CHATTER validator (see ``chatter_validator.py``).
"""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from .whisper_transcribe import UtteranceSegment, WordSegment


# ----------------------------------------------------------------------
# Tunables
# ----------------------------------------------------------------------
DEFAULT_UNINTELLIGIBLE_THRESHOLD = 0.30
DEFAULT_ZERO_VOCALIZATION_GAP = 5.0
MAX_ZERO_VOCALIZATION_GAPS = 3

# Pauses *within* an utterance, in seconds
PAUSE_SHORT = 0.6     # (.)
PAUSE_MEDIUM = 1.2    # (..)
PAUSE_LONG = 2.0      # (...)

# Word-level filler dictionaries (lowercased, tokenised)
FILLER_WORDS = {
    "en": {
        "um": "&-um", "uh": "&-uh", "uhh": "&-uh", "umm": "&-um",
        "ah": "&-ah", "er": "&-er", "hmm": "&-hmm", "mhm": "&-mhm",
        "huh": "&-huh", "oh": "&-oh", "eh": "&-eh",
    },
    "th": {
        "เอ่อ": "&-เอ่อ", "อืม": "&-อืม", "อ่อ": "&-อ่อ",
        "เออ": "&-เออ", "หา": "&-หา", "อะ": "&-อะ",
    },
}


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _format_time(seconds: float) -> str:
    """CHAT ``%tim`` format: ``HH:MM:SS.sss``."""
    if seconds < 0:
        seconds = 0
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


_END_PUNCT = {".", "?", "!"}
_STRIP_PUNCT_RE = re.compile(r"[.?!,;:\"]+$")
_WHITESPACE_RE = re.compile(r"\s+")
_THAI_FALLBACK_WORDS = sorted(
    {
        "สวัสดี",
        "ครับ",
        "ค่ะ",
        "คุณแม่",
        "แม่",
        "พ่อ",
        "ลูก",
        "เธอ",
        "คุณ",
        "กิน",
        "ข้าว",
        "ไป",
        "เที่ยว",
        "กัน",
        "ไหม",
        "อยาก",
        "เอา",
        "จะ",
    },
    key=len,
    reverse=True,
)


def _split_terminator(text: str) -> Tuple[str, str]:
    """Return ``(body_without_terminator, terminator)``.

    Default terminator is ``"."``.
    """
    t = text.strip()
    if not t:
        return "", "."
    last = t[-1]
    if last in _END_PUNCT:
        return t[:-1].rstrip(), last
    return t, "."


def _fallback_thai_word_tokenize(raw: str) -> List[str]:
    tokens: List[str] = []
    for part in re.findall(r"[ก-๙]+|[A-Za-z0-9'-]+", raw):
        if not any("\u0e00" <= char <= "\u0e7f" for char in part):
            tokens.append(part)
            continue

        pos = 0
        while pos < len(part):
            match = next(
                (word for word in _THAI_FALLBACK_WORDS if part.startswith(word, pos)),
                None,
            )
            if match:
                tokens.append(match)
                pos += len(match)
                continue

            next_pos = pos + 1
            while next_pos < len(part) and not any(
                part.startswith(word, next_pos) for word in _THAI_FALLBACK_WORDS
            ):
                next_pos += 1
            tokens.append(part[pos:next_pos])
            pos = next_pos
    return tokens


def _tokenize_thai_words(raw: str) -> List[str]:
    try:
        from pythainlp.tokenize import word_tokenize
    except ImportError:
        return _fallback_thai_word_tokenize(raw)

    return [token.strip() for token in word_tokenize(raw, engine="newmm") if token.strip()]


def _detect_filler(token: str, lang: Optional[str]) -> Optional[str]:
    """Return the CHAT-encoded filler for a token, or None if not a filler."""
    if not token:
        return None
    low = token.strip().lower()
    if lang and lang in FILLER_WORDS and low in FILLER_WORDS[lang]:
        return FILLER_WORDS[lang][low]
    # Fallback: try both languages
    for code, mapping in FILLER_WORDS.items():
        if low in mapping:
            return mapping[low]
    return None


def _pause_marker(gap_seconds: float) -> Optional[str]:
    """Return the appropriate ``(.)``/``(..)``/``(...)`` marker for an internal gap."""
    if gap_seconds >= PAUSE_LONG:
        return "(...)"
    if gap_seconds >= PAUSE_MEDIUM:
        return "(..)"
    if gap_seconds >= PAUSE_SHORT:
        return "(.)"
    return None


def _detect_repetition(tokens: List[str]) -> List[str]:
    """Mark immediate adjacent duplicates with ``[/]``.

    Example: ``['cat', 'cat', 'sat']`` -> ``['cat [/]', 'cat', 'sat']``.
    """
    if len(tokens) < 2:
        return tokens
    out: List[str] = []
    i = 0
    while i < len(tokens):
        # Find run of identical tokens
        j = i + 1
        while j < len(tokens) and tokens[j] == tokens[i]:
            j += 1
        run_len = j - i
        if run_len >= 2:
            # Each but the last gets [/]
            for _ in range(run_len - 1):
                out.append(f"{tokens[i]} [/]")
            out.append(tokens[i])
        else:
            out.append(tokens[i])
        i = j
    return out


def _render_utterance_body(
    u: UtteranceSegment,
    unintelligible_threshold: float,
) -> str:
    """Render the body of a CHAT utterance line with codes for fillers,
    pauses, repetitions and unintelligible words.

    If Whisper didn't return word-level timings, fall back to the raw
    segment text (terminator stripped).
    """
    has_thai = any('\u0e00' <= char <= '\u0e7f' for char in (u.text or ""))

    if not u.words:
        body, _term = _split_terminator(u.text)
        if has_thai:
            return " ".join(_tokenize_thai_words(body))
        return body

    raw_tokens: List[str] = []
    timings: List[Tuple[float, float]] = []
    for w in u.words:
        word = _WHITESPACE_RE.sub(" ", w.text.strip())
        word = _STRIP_PUNCT_RE.sub("", word)
        if not word:
            continue
        timings.append((w.start, w.end))

        if w.probability < unintelligible_threshold:
            raw_tokens.append("xxx")
            continue

        filler = _detect_filler(word, w.language)
        if filler:
            raw_tokens.append(filler)
            continue

        # Lowercase ASCII words; preserve unicode case for Thai
        if word.isascii():
            word = word.lower()

        # Segment sub-words if the token contains Thai characters and was combined
        word_has_thai = any('\u0e00' <= char <= '\u0e7f' for char in word)
        if word_has_thai:
            sub_tokens = _tokenize_thai_words(word)
            if not sub_tokens:
                raw_tokens.append(word)
            else:
                raw_tokens.extend(sub_tokens)
                # Duplicate the timestamp mapping for segmented tokens
                for _ in range(len(sub_tokens) - 1):
                    timings.append((w.start, w.end))
        else:
            raw_tokens.append(word)

    # Insert pause markers between tokens with long internal gaps
    spaced: List[str] = []
    for idx, tok in enumerate(raw_tokens):
        if idx > 0 and idx < len(timings):
            gap = timings[idx][0] - timings[idx - 1][1]
            mark = _pause_marker(gap)
            if mark:
                spaced.append(mark)
        spaced.append(tok)

    # Mark immediate repetitions with [/]
    spaced = _detect_repetition(spaced)
    return " ".join(spaced)


def _languages_field(detected_languages: Iterable[Optional[str]],
                     fallback: str = "eng") -> Tuple[str, bool]:
    """Build the ``@Languages`` value and a flag for code-switching.

    Returns ``(field_value, is_code_switching)``.
    """
    iso_map = {"en": "eng", "th": "tha"}
    seen: List[str] = []
    for lang in detected_languages:
        if not lang:
            continue
        iso = iso_map.get(lang.lower(), lang.lower())
        if iso not in seen:
            seen.append(iso)
    if not seen:
        return fallback, False
    return ", ".join(seen), len(seen) > 1


# ----------------------------------------------------------------------
# Core formatter
# ----------------------------------------------------------------------
def utterances_to_chat(
    utterances: Sequence[UtteranceSegment],
    *,
    child_id: str = "CHI001",
    child_age_months: Optional[float] = None,
    child_sex: Optional[str] = None,
    child_group: str = "ASD",
    media_filename: Optional[str] = None,
    language: str = "eng",
    activities: Optional[str] = None,
    coder: str = "AI",
    unintelligible_threshold: float = DEFAULT_UNINTELLIGIBLE_THRESHOLD,
    zero_vocalization_gap: float = DEFAULT_ZERO_VOCALIZATION_GAP,
    max_zero_vocalization_gaps: int = MAX_ZERO_VOCALIZATION_GAPS,
) -> str:
    """Convert an ordered list of utterances into a CHAT transcript.

    All utterances are expected to already have ``u.speaker`` filled in
    (run diarization first).
    """
    utts = sorted(utterances, key=lambda u: u.start)

    # --- Languages (auto-detect single vs code-switching) -----------------
    languages_field, is_code_switching = _languages_field(
        (u.language for u in utts), fallback=language,
    )

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
    lines.append(f"@Languages:\t{languages_field}")
    lines.append(f"@Participants:\t{participants_line}")
    # CHAT @ID format (10 pipe-separated fields):
    #   language | corpus | code | age | sex | group | SES | role | education | custom
    primary_lang_iso = languages_field.split(",")[0].strip()
    lines.append(
        f"@ID:\t{primary_lang_iso}|asd-project|CHI|{age_field}|{sex_field}|"
        f"{child_group}||{child_role}|{child_id}|"
    )
    for lab in adult_labels:
        role = adult_roles.get(lab, lab.title())
        lines.append(f"@ID:\t{primary_lang_iso}|asd-project|{lab}||||||{role}||")

    today = _dt.date.today().strftime("%d-%b-%Y").upper()
    lines.append(f"@Date:\t{today}")
    if activities:
        lines.append(f"@Activities:\t{activities}")
    lines.append(f"@Coder:\t{coder}")
    duration_sec = max((u.end for u in utts), default=0.0)
    duration_str = _format_time(duration_sec)
    lines.append(f"@Time Duration:\t00:00:00.000-{duration_str}")

    auto_comment = (
        "Auto-generated by ASD Assessment Dashboard (Whisper + ECAPA "
        + "diarization)"
    )
    if is_code_switching:
        auto_comment += " · TH+EN code-switching detected"
    lines.append(f"@Comment:\t{auto_comment}")
    if media_filename:
        media_stem = Path(media_filename).stem
        lines.append(f"@Media:\t{media_stem}, audio")

    # Stream through utterances, inserting 0-vocalization markers when
    # the child goes silent for too long.
    prev_end: Optional[float] = None
    prev_was_child: bool = False
    zero_inserted = 0

    for u in utts:
        speaker = (u.speaker or "MOT").upper()
        is_child = speaker == "CHI"

        # Zero-vocalization: long gap AND we had a prior child turn
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

        # Inline language tag for code-switching (CHAT spec)
        if is_code_switching and u.language:
            iso = {"en": "eng", "th": "tha"}.get(u.language.lower(), u.language.lower())
            body = f"[- {iso}] {body}"

        lines.append(f"*{speaker}:\t{body} {terminator}")
        lines.append(f"%tim:\t{_format_time(u.start)}-{_format_time(u.end)}")

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
    """Render ``utterances_to_chat(...)`` and write to disk.  Returns the path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = utterances_to_chat(utterances, **kwargs)
    output_path.write_text(text, encoding="utf-8")
    return output_path
