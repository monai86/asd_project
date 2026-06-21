"""Reusable CHAT transcript feature extraction.

This module is the single extraction path for TalkBank/CHAT-derived feature
tables. Keeping the legacy data loader and the reference cohort builder on the
same helper prevents feature drift across generated CSVs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pylangacq as pla


_AGE_RE = re.compile(r"^(\d+);(\d*)\.?(\d*)$")
_PUNCT = {".", "?", "!", ",", ";", ":", "+...", "+..", "+/.", "+//.", "+/?"}
_THAI_FALLBACK_WORDS = sorted(
    {
        "สวัสดี",
        "ครับ",
        "ค่ะ",
        "คุณแม่",
        "แม่",
        "พ่อ",
        "เธอ",
        "คุณ",
        "กิน",
        "ข้าว",
        "อยาก",
        "เอา",
        "ไป",
        "จะ",
    },
    key=len,
    reverse=True,
)


def age_to_months(age_str: Optional[str]) -> Optional[float]:
    """Convert CHAT age string such as ``5;03.10`` or ``2;08.`` to months."""
    if not age_str:
        return None
    age_str = str(age_str).strip()
    match = _AGE_RE.match(age_str)
    if not match:
        return None
    years = int(match.group(1) or 0)
    months = int(match.group(2) or 0)
    days = int(match.group(3) or 0)
    return years * 12 + months + days / 30.0


def normalize_group(raw: Optional[str]) -> Optional[str]:
    """Normalize common CHAT group codes while preserving corpus-specific labels."""
    if not raw:
        return None
    group = str(raw).strip().upper()
    if group in ("TYP", "TD", "NT", "CONTROL"):
        return "TD"
    if group in ("ASD", "AUTISM"):
        return "ASD"
    if group in ("DD", "DELAY"):
        return "DD"
    return group


def safe_first(values):
    """Return the first element of a list-like value, or ``None``."""
    if values is None:
        return None
    try:
        return values[0]
    except (IndexError, TypeError):
        return None


def read_chat(path: Path):
    """Read a CHAT file with strict parsing first, then non-strict fallback."""
    try:
        return pla.read_chat(str(path))
    except Exception:  # noqa: BLE001
        return pla.read_chat(str(path), strict=False)


def extract_child_participant(reader) -> Optional[object]:
    """Return the CHI Participant object from the first header, or ``None``."""
    headers = reader.headers()
    if not headers:
        return None
    for participant in headers[0].participants:
        if participant.code == "CHI":
            return participant
    return None


def content_tokens(utt) -> list[str]:
    """Lower-cased word tokens with punctuation removed."""
    out = []
    for token in utt.tokens or []:
        word = (token.word or "").lower().strip()
        if not word or word in _PUNCT:
            continue
        
        # If contains Thai, tokenize it further
        has_thai = any('\u0e00' <= char <= '\u0e7f' for char in word)
        if has_thai:
            out.extend(_tokenize_thai_words(word))
        else:
            out.append(word)
    return out


def _fallback_thai_word_tokenize(raw: str) -> list[str]:
    tokens: list[str] = []
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


def _tokenize_thai_words(raw: str) -> list[str]:
    try:
        from pythainlp.tokenize import word_tokenize
    except ImportError:
        return _fallback_thai_word_tokenize(raw)

    return [token.strip() for token in word_tokenize(raw, engine="newmm") if token.strip()]


def count_echolalia(all_utts, window: int = 5, min_tokens: int = 2) -> int:
    """Count CHI utterances that repeat a recent utterance verbatim."""
    seqs: list[tuple[str, ...]] = []
    count = 0
    for utterance in all_utts:
        tokens = tuple(content_tokens(utterance))
        if utterance.participant == "CHI" and len(tokens) >= min_tokens:
            if tokens in seqs[-window:]:
                count += 1
        seqs.append(tokens)
    return count


_PRONOUN_REVERSAL_PATTERNS = [
    re.compile(r"\byou\s+(?:am|was)\b", re.IGNORECASE),
    re.compile(r"\bme\s+(?:am|want|need|have|like|go|do|see|get)\b", re.IGNORECASE),
    re.compile(r"\bmy\s+(?:want|need|have|like|go|do|see|get)\b", re.IGNORECASE),
    re.compile(r"\bi\s+(?:are|is)\b", re.IGNORECASE),
    re.compile(r"\byour\s+(?:want|need|have|like|go|do|see|get)\b", re.IGNORECASE),
]

_TH_PRONOUN_REVERSAL_PATTERNS = [
    # Child incorrectly refers to self (1st person) as "เธอ" or "คุณ"
    re.compile(r"\bเธอ\s*(?:จะ|อยาก|เอา|ไป)\b"),
    re.compile(r"\bคุณ\s*(?:จะ|อยาก|เอา|ไป)\b"),
]

_RESTRICTED_INTEREST_TERMS = {
    # English
    "train", "trains", "wheel", "wheels", "number", "numbers", "letter",
    "letters", "map", "maps", "dinosaur", "dinosaurs", "schedule", "schedules",
    # Thai equivalents
    "รถไฟ", "ล้อ", "ตัวเลข", "ตัวอักษร", "แผนที่", "ไดโนเสาร์", "ตาราง"
}


def count_pronoun_reversals(raw_text: str) -> int:
    """Count only obvious pronoun-reversal patterns in one utterance."""
    has_thai = any('\u0e00' <= char <= '\u0e7f' for char in (raw_text or ""))
    if has_thai:
        # Tokenize and join with spaces so word boundary regex assertions (\b) work properly
        tokens = _tokenize_thai_words(raw_text)
        raw_text = " ".join(tokens)

    count = sum(len(pattern.findall(raw_text or "")) for pattern in _PRONOUN_REVERSAL_PATTERNS)
    count += sum(len(pattern.findall(raw_text or "")) for pattern in _TH_PRONOUN_REVERSAL_PATTERNS)
    return count


def extract_chat_features(cha_path: Path) -> Optional[dict]:
    """Extract child-level feature values from one CHAT file.

    Returns ``None`` when the file cannot be read or has no CHI participant or
    no child utterances.
    """
    try:
        reader = read_chat(cha_path)
    except Exception as exc:  # noqa: BLE001
        print(f"  [skip] cannot read {cha_path.name}: {exc}")
        return None

    chi = extract_child_participant(reader)
    if chi is None:
        print(f"  [skip] no CHI participant in {cha_path.name}")
        return None

    all_utts = reader.utterances()
    chi_utts = [utterance for utterance in all_utts if utterance.participant == "CHI"]
    total_utterances = len(chi_utts)
    if total_utterances == 0:
        print(f"  [skip] no CHI utterances in {cha_path.name}")
        return None

    mlu_morph = safe_first(reader.mlu(participant="CHI"))
    mlu_words = safe_first(reader.mluw(participant="CHI"))
    ttr = safe_first(reader.ttr(participant="CHI"))

    total_words = 0
    question_utterances = 0
    for utterance in chi_utts:
        raw = utterance.tiers.get("CHI", "")
        if raw.rstrip().endswith("?"):
            question_utterances += 1
        for token in utterance.tokens:
            word = token.word
            if not word or word in _PUNCT:
                continue
            total_words += 1

    unintelligible = 0
    zero_vocalization = 0
    vocalization = 0
    pronoun_reversal_count = 0
    restricted_interest_words = 0
    for utterance in chi_utts:
        raw = utterance.tiers.get("CHI", "").strip()
        stripped = raw.rstrip(" .?!").strip()
        if stripped == "0":
            zero_vocalization += 1
        if re.search(r"\bxxx\b|\byyy\b", raw):
            unintelligible += 1
        if re.search(r"&=[A-Za-z]+", raw):
            vocalization += 1
        pronoun_reversal_count += count_pronoun_reversals(raw)
        restricted_interest_words += sum(
            1 for token in content_tokens(utterance) if token in _RESTRICTED_INTEREST_TERMS
        )

    age_months = age_to_months(chi.age)
    echolalia_count = count_echolalia(all_utts)

    return {
        "participant_id": cha_path.stem,
        "group_header": normalize_group(chi.group),
        "sex": chi.sex or None,
        "age_months": round(age_months, 2) if age_months is not None else None,
        "total_utterances": total_utterances,
        "mlu": round(mlu_morph, 3) if mlu_morph is not None else None,
        "mluw": round(mlu_words, 3) if mlu_words is not None else None,
        "ttr": round(ttr, 4) if ttr is not None else None,
        "total_words": total_words,
        "unintelligible_count": unintelligible,
        "unintelligible_ratio": round(unintelligible / total_utterances, 4),
        "zero_vocalization_count": zero_vocalization,
        "nonverbal_vocalization_count": vocalization,
        "question_ratio": round(question_utterances / total_utterances, 4),
        "echolalia_count": echolalia_count,
        "echolalia_ratio": round(echolalia_count / total_utterances, 4),
        "pronoun_reversal_count": pronoun_reversal_count,
        "pronoun_reversal_ratio": round(pronoun_reversal_count / total_utterances, 4),
        "restricted_interest_words": restricted_interest_words,
    }
