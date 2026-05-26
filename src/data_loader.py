"""
Data loader for ASD-project corpora (Eigsti, Nadig, Rollins).

Reads CHAT (.cha) transcripts with pylangacq and extracts child-level
linguistic features for downstream ML / progress tracking.

Outputs:
    data/combined_features.csv  -> Eigsti + Nadig  (for classification)
    data/rollins_features.csv   -> Rollins          (for longitudinal tracking)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pandas as pd
import pylangacq as pla


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
EIGSTI_DIR = DATA_DIR / "Eigsti"
NADIG_DIR = DATA_DIR / "Nadig"
ROLLINS_DIR = DATA_DIR / "Rollins"
NYU_EMR_DIR = DATA_DIR / "NYU-Emerson"
QUIGLEY_DIR = DATA_DIR / "QuigleyMcNally"
FLUSBERG_DIR = DATA_DIR / "Flusberg"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_AGE_RE = re.compile(r"^(\d+);(\d*)\.?(\d*)$")


def _age_to_months(age_str: Optional[str]) -> Optional[float]:
    """Convert CHAT age string (e.g. '5;03.10' or '2;08.') to months (float)."""
    if not age_str:
        return None
    age_str = str(age_str).strip()
    m = _AGE_RE.match(age_str)
    if not m:
        return None
    years = int(m.group(1) or 0)
    months = int(m.group(2) or 0)
    days = int(m.group(3) or 0)
    return years * 12 + months + days / 30.0


def _normalize_group(raw: Optional[str]) -> Optional[str]:
    """Normalize CHAT group codes to {ASD, DD, TD}."""
    if not raw:
        return None
    g = str(raw).strip().upper()
    if g in ("TYP", "TD", "NT", "CONTROL"):
        return "TD"
    if g in ("ASD", "AUTISM"):
        return "ASD"
    if g in ("DD", "DELAY"):
        return "DD"
    return g  # leave as-is for anything else


def _safe_first(values):
    """Return first element of a list-like, or None."""
    if values is None:
        return None
    try:
        return values[0]
    except (IndexError, TypeError):
        return None


def _extract_child_participant(reader) -> Optional[object]:
    """Return the CHI Participant object from the first header, or None."""
    headers = reader.headers()
    if not headers:
        return None
    for p in headers[0].participants:
        if p.code == "CHI":
            return p
    return None


def _content_tokens(utt) -> list[str]:
    """Lower-cased word tokens with punctuation removed."""
    PUNCT = {".", "?", "!", ",", ";", ":", "+...", "+..", "+/.", "+//.", "+/?"}
    out = []
    for t in utt.tokens or []:
        w = (t.word or "").lower().strip()
        if not w or w in PUNCT:
            continue
        out.append(w)
    return out


def _count_echolalia(all_utts, window: int = 5, min_tokens: int = 2) -> int:
    """
    Count CHI utterances that *repeat* a recent utterance verbatim.

    A CHI utterance counts as echolalia when its sequence of content tokens
    matches the sequence of any utterance (by any speaker, including CHI
    itself for self-repetition) in the previous `window` utterances.

    Single-word utterances are excluded because routine "yes"/"no"/"mama"
    repeats are not clinically meaningful echolalia.

    References
    ----------
    Prizant, B. M. (1983). Echolalia in autism: Assessment, intervention, and
    theoretical considerations. *Journal of Child Psychology and Psychiatry,
    24*(3), 399-418.
    """
    seqs: list[tuple[str, ...]] = []   # parallel history of token sequences
    count = 0
    for u in all_utts:
        toks = tuple(_content_tokens(u))
        if u.participant == "CHI" and len(toks) >= min_tokens:
            recent = seqs[-window:]
            if toks in recent:
                count += 1
        seqs.append(toks)
    return count


_PRONOUN_REVERSAL_PATTERNS = [
    re.compile(r"\byou\s+(?:am|was)\b", re.IGNORECASE),
    re.compile(r"\bme\s+(?:am|want|need|have|like|go|do|see|get)\b", re.IGNORECASE),
    re.compile(r"\bmy\s+(?:want|need|have|like|go|do|see|get)\b", re.IGNORECASE),
    re.compile(r"\bi\s+(?:are|is)\b", re.IGNORECASE),
    re.compile(r"\byour\s+(?:want|need|have|like|go|do|see|get)\b", re.IGNORECASE),
]


def _count_pronoun_reversals(raw_text: str) -> int:
    """Count only obvious pronoun-reversal patterns in one utterance.

    This intentionally avoids broad grammar correction. The feature is a
    conservative screening-support marker and should be reviewed by a human.
    """
    return sum(len(pattern.findall(raw_text or "")) for pattern in _PRONOUN_REVERSAL_PATTERNS)


def _extract_features(cha_path: Path) -> Optional[dict]:
    """Extract features from one .cha file. Returns a dict or None if unreadable."""
    try:
        reader = pla.read_chat(str(cha_path))
    except Exception:  # noqa: BLE001
        # Some files use non-standard terminators (e.g. "+!?", "+...").
        # Fall back to non-strict parsing before giving up.
        try:
            reader = pla.read_chat(str(cha_path), strict=False)
        except Exception as e:  # noqa: BLE001
            print(f"  [skip] cannot read {cha_path.name}: {e}")
            return None

    chi = _extract_child_participant(reader)
    if chi is None:
        print(f"  [skip] no CHI participant in {cha_path.name}")
        return None

    # All utterances (across participants) -> filter CHI
    all_utts = reader.utterances()
    chi_utts = [u for u in all_utts if u.participant == "CHI"]
    total_utt = len(chi_utts)
    if total_utt == 0:
        print(f"  [skip] no CHI utterances in {cha_path.name}")
        return None

    # MLU / TTR via pylangacq (one value per file)
    mlu_morph = _safe_first(reader.mlu(participant="CHI"))
    mlu_words = _safe_first(reader.mluw(participant="CHI"))
    ttr = _safe_first(reader.ttr(participant="CHI"))

    # Counts from tokens (exclude punctuation tokens)
    PUNCT = {".", "?", "!", ",", ";", ":", "+...", "+..", "+/.", "+//.", "+/?"}
    total_words = 0
    question_utts = 0
    for u in chi_utts:
        # raw CHI tier text
        raw = u.tiers.get("CHI", "")
        if raw.rstrip().endswith("?"):
            question_utts += 1
        for t in u.tokens:
            w = t.word
            if not w:
                continue
            if w in PUNCT:
                continue
            total_words += 1

    # Unintelligible + zero vocalizations from raw tier text
    unintelligible = 0
    zero_vocal = 0
    vocalization = 0  # &=laugh, &=gasp, &=cough...
    pronoun_reversal_count = 0
    for u in chi_utts:
        raw = u.tiers.get("CHI", "").strip()
        # zero vocalization: line is just "0 ." or "0."
        stripped = raw.rstrip(" .?!").strip()
        if stripped == "0":
            zero_vocal += 1
        # xxx / yyy markers (unintelligible / phonological coding)
        if re.search(r"\bxxx\b|\byyy\b", raw):
            unintelligible += 1
        # non-verbal vocalizations &=gasp etc.
        if re.search(r"&=[A-Za-z]+", raw):
            vocalization += 1
        pronoun_reversal_count += _count_pronoun_reversals(raw)

    age_months = _age_to_months(chi.age)

    # Echolalia: CHI utterance verbatim-matches a recent utterance
    echolalia_count = _count_echolalia(all_utts)

    return {
        "participant_id": cha_path.stem,
        "group_header": _normalize_group(chi.group),
        "sex": chi.sex or None,
        "age_months": round(age_months, 2) if age_months is not None else None,
        "total_utterances": total_utt,
        "mlu": round(mlu_morph, 3) if mlu_morph is not None else None,
        "mluw": round(mlu_words, 3) if mlu_words is not None else None,
        "ttr": round(ttr, 4) if ttr is not None else None,
        "total_words": total_words,
        "unintelligible_count": unintelligible,
        "unintelligible_ratio": round(unintelligible / total_utt, 4),
        "zero_vocalization_count": zero_vocal,
        "nonverbal_vocalization_count": vocalization,
        "question_ratio": round(question_utts / total_utt, 4),
        "echolalia_count": echolalia_count,
        "echolalia_ratio": round(echolalia_count / total_utt, 4),
        "pronoun_reversal_count": pronoun_reversal_count,
        "pronoun_reversal_ratio": round(pronoun_reversal_count / total_utt, 4),
    }


# ---------------------------------------------------------------------------
# Corpus loaders
# ---------------------------------------------------------------------------
def load_eigsti() -> pd.DataFrame:
    """Eigsti: labels come from subfolder (ASD / DD / TD), verified with @ID header."""
    print("\n[Eigsti] loading...")
    rows = []
    for subgroup_dir in sorted(p for p in EIGSTI_DIR.iterdir() if p.is_dir()):
        folder_label = subgroup_dir.name  # ASD / DD / TD
        for cha in sorted(subgroup_dir.glob("*.cha")):
            feats = _extract_features(cha)
            if feats is None:
                continue
            # folder label is authoritative for Eigsti
            feats["group"] = _normalize_group(folder_label) or folder_label
            feats["corpus"] = "eigsti"
            rows.append(feats)
    df = pd.DataFrame(rows)
    print(f"[Eigsti] {len(df)} files loaded.")
    return df


def load_nadig() -> pd.DataFrame:
    """Nadig: labels from @ID header (mixed ASD + TYP despite 0types.txt)."""
    print("\n[Nadig] loading...")
    rows = []
    for cha in sorted(NADIG_DIR.glob("*.cha")):
        feats = _extract_features(cha)
        if feats is None:
            continue
        # header group is authoritative for Nadig
        feats["group"] = feats["group_header"] or "ASD"
        feats["corpus"] = "nadig"
        rows.append(feats)
    df = pd.DataFrame(rows)
    print(f"[Nadig] {len(df)} files loaded.")
    return df


def load_rollins() -> pd.DataFrame:
    """Rollins: longitudinal ASD, one subfolder per child. session_order from filename."""
    print("\n[Rollins] loading...")
    rows = []
    for child_dir in sorted(p for p in ROLLINS_DIR.iterdir() if p.is_dir()):
        child_name = child_dir.name
        cha_files = sorted(child_dir.glob("*.cha"), key=lambda p: p.stem)
        for order, cha in enumerate(cha_files, start=1):
            feats = _extract_features(cha)
            if feats is None:
                continue
            feats["child"] = child_name
            feats["session_id"] = cha.stem           # e.g. "020800"
            feats["session_order"] = order           # 1, 2, 3, ...
            # Corpus ships as all ASD
            feats["group"] = feats["group_header"] or "ASD"
            feats["corpus"] = "rollins"
            rows.append(feats)
    df = pd.DataFrame(rows)
    print(f"[Rollins] {len(df)} sessions loaded.")
    return df


def load_nyu_emerson() -> pd.DataFrame:
    """NYU-Emerson: 30 ASD children with audio/video. Flat structure."""
    print("\n[NYU-Emerson] loading...")
    rows = []
    for cha in sorted(NYU_EMR_DIR.glob("*.cha")):
        feats = _extract_features(cha)
        if feats is None:
            continue
        # All NYU-Emerson are ASD
        feats["group"] = "ASD"
        feats["corpus"] = "nyu_emerson"
        rows.append(feats)
    df = pd.DataFrame(rows)
    print(f"[NYU-Emerson] {len(df)} files loaded.")
    return df


def load_quigley_classification() -> pd.DataFrame:
    """QuigleyMcNally: HR=ASD (10 children), LR=TD (9 children). Use session 1 only."""
    print("\n[QuigleyMcNally - Classification] loading...")
    rows = []

    # HR folder = High Risk = ASD
    hr_dir = QUIGLEY_DIR / "HR"
    for child_dir in sorted(p for p in hr_dir.iterdir() if p.is_dir()):
        child_name = child_dir.name
        cha_files = sorted(child_dir.glob("*.cha"), key=lambda p: p.stem)
        if not cha_files:
            continue
        # Use first session only to avoid repeated measures
        cha = cha_files[0]
        feats = _extract_features(cha)
        if feats is None:
            continue
        feats["child"] = child_name
        feats["group"] = "ASD"
        feats["corpus"] = "quigley"
        rows.append(feats)

    # LR folder = Low Risk = TD
    lr_dir = QUIGLEY_DIR / "LR"
    for child_dir in sorted(p for p in lr_dir.iterdir() if p.is_dir()):
        child_name = child_dir.name
        cha_files = sorted(child_dir.glob("*.cha"), key=lambda p: p.stem)
        if not cha_files:
            continue
        cha = cha_files[0]
        feats = _extract_features(cha)
        if feats is None:
            continue
        feats["child"] = child_name
        feats["group"] = "TD"
        feats["corpus"] = "quigley"
        rows.append(feats)

    df = pd.DataFrame(rows)
    print(f"[QuigleyMcNally] {len(df)} children loaded (session 1 only).")
    return df


def load_quigley_progress() -> pd.DataFrame:
    """QuigleyMcNally: All sessions for longitudinal analysis."""
    print("\n[QuigleyMcNally - Progress] loading...")
    rows = []

    # HR folder = ASD
    hr_dir = QUIGLEY_DIR / "HR"
    for child_dir in sorted(p for p in hr_dir.iterdir() if p.is_dir()):
        child_name = child_dir.name
        cha_files = sorted(child_dir.glob("*.cha"), key=lambda p: p.stem)
        for order, cha in enumerate(cha_files, start=1):
            feats = _extract_features(cha)
            if feats is None:
                continue
            feats["child"] = child_name
            feats["session_id"] = cha.stem
            feats["session_order"] = order
            feats["group"] = "ASD"
            feats["corpus"] = "quigley"
            rows.append(feats)

    # LR folder = TD
    lr_dir = QUIGLEY_DIR / "LR"
    for child_dir in sorted(p for p in lr_dir.iterdir() if p.is_dir()):
        child_name = child_dir.name
        cha_files = sorted(child_dir.glob("*.cha"), key=lambda p: p.stem)
        for order, cha in enumerate(cha_files, start=1):
            feats = _extract_features(cha)
            if feats is None:
                continue
            feats["child"] = child_name
            feats["session_id"] = cha.stem
            feats["session_order"] = order
            feats["group"] = "TD"
            feats["corpus"] = "quigley"
            rows.append(feats)

    df = pd.DataFrame(rows)
    print(f"[QuigleyMcNally] {len(df)} sessions loaded (longitudinal).")
    return df


def load_flusberg_classification() -> pd.DataFrame:
    """Flusberg: 6 ASD children, use session 1 only for classification."""
    print("\n[Flusberg - Classification] loading...")
    rows = []
    for child_dir in sorted(p for p in FLUSBERG_DIR.iterdir() if p.is_dir()):
        child_name = child_dir.name
        cha_files = sorted(child_dir.glob("*.cha"), key=lambda p: p.stem)
        if not cha_files:
            continue
        cha = cha_files[0]
        feats = _extract_features(cha)
        if feats is None:
            continue
        feats["child"] = child_name
        feats["group"] = "ASD"
        feats["corpus"] = "flusberg"
        rows.append(feats)
    df = pd.DataFrame(rows)
    print(f"[Flusberg] {len(df)} children loaded (session 1 only).")
    return df


def load_flusberg_progress() -> pd.DataFrame:
    """Flusberg: All sessions for longitudinal analysis."""
    print("\n[Flusberg - Progress] loading...")
    rows = []
    for child_dir in sorted(p for p in FLUSBERG_DIR.iterdir() if p.is_dir()):
        child_name = child_dir.name
        cha_files = sorted(child_dir.glob("*.cha"), key=lambda p: p.stem)
        for order, cha in enumerate(cha_files, start=1):
            feats = _extract_features(cha)
            if feats is None:
                continue
            feats["child"] = child_name
            feats["session_id"] = cha.stem
            feats["session_order"] = order
            feats["group"] = "ASD"
            feats["corpus"] = "flusberg"
            rows.append(feats)
    df = pd.DataFrame(rows)
    print(f"[Flusberg] {len(df)} sessions loaded (longitudinal).")
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    # Load all corpora
    eigsti_df = load_eigsti()
    nadig_df = load_nadig()
    rollins_df = load_rollins()
    nyu_df = load_nyu_emerson()
    quigley_cls_df = load_quigley_classification()
    quigley_prog_df = load_quigley_progress()
    flusberg_cls_df = load_flusberg_classification()
    flusberg_prog_df = load_flusberg_progress()

    # Combine classification datasets
    combined_df = pd.concat([
        eigsti_df, nadig_df, nyu_df,
        quigley_cls_df, flusberg_cls_df
    ], ignore_index=True)

    # Combine longitudinal datasets
    longitudinal_df = pd.concat([
        rollins_df, quigley_prog_df, flusberg_prog_df
    ], ignore_index=True)

    # Column ordering for the classification CSV
    combined_cols = [
        "participant_id", "corpus", "group", "group_header",
        "sex", "age_months",
        "total_utterances", "mlu", "mluw", "ttr", "total_words",
        "unintelligible_count", "unintelligible_ratio",
        "zero_vocalization_count", "nonverbal_vocalization_count",
        "question_ratio",
        "echolalia_count", "echolalia_ratio",
        "pronoun_reversal_count", "pronoun_reversal_ratio",
    ]
    combined_df = combined_df[combined_cols]

    # Column ordering for longitudinal CSV
    longitudinal_cols = [
        "child", "session_id", "session_order",
        "participant_id", "corpus", "group", "group_header",
        "sex", "age_months",
        "total_utterances", "mlu", "mluw", "ttr", "total_words",
        "unintelligible_count", "unintelligible_ratio",
        "zero_vocalization_count", "nonverbal_vocalization_count",
        "question_ratio",
        "echolalia_count", "echolalia_ratio",
        "pronoun_reversal_count", "pronoun_reversal_ratio",
    ]
    longitudinal_df = longitudinal_df[longitudinal_cols]

    # Save outputs
    combined_path = DATA_DIR / "combined_features.csv"
    longitudinal_path = DATA_DIR / "longitudinal_features.csv"
    combined_df.to_csv(combined_path, index=False)
    longitudinal_df.to_csv(longitudinal_path, index=False)

    print("\n" + "=" * 72)
    print(f"Saved: {combined_path.relative_to(PROJECT_ROOT)}  ({len(combined_df)} rows)")
    print(f"Saved: {longitudinal_path.relative_to(PROJECT_ROOT)}  ({len(longitudinal_df)} rows)")
    print("=" * 72)

    print("\n--- combined_features.csv (head) ---")
    print(combined_df.head(10).to_string(index=False))
    print("\nGroup distribution in combined:")
    print(combined_df.groupby(["corpus", "group"]).size())

    print("\n--- longitudinal_features.csv (head) ---")
    print(longitudinal_df.head(10).to_string(index=False))
    print("\nSessions per child (longitudinal):")
    print(longitudinal_df.groupby(["corpus", "child"]).size().sort_index())


if __name__ == "__main__":
    main()
