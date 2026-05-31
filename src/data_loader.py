"""
Data loader for ASD-project corpora (Eigsti, Nadig, Rollins).

Reads CHAT (.cha) transcripts with pylangacq and extracts child-level
linguistic features for downstream ML / progress tracking.

Outputs:
    data/combined_features.csv  -> Eigsti + Nadig  (for classification)
    data/rollins_features.csv   -> Rollins          (for longitudinal tracking)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

try:
    from src.chat_feature_extractor import (
        age_to_months,
        content_tokens,
        count_echolalia,
        count_pronoun_reversals,
        extract_chat_features,
        extract_child_participant,
        normalize_group,
        safe_first,
    )
except ModuleNotFoundError:  # pragma: no cover - supports `python src/data_loader.py`
    from chat_feature_extractor import (
        age_to_months,
        content_tokens,
        count_echolalia,
        count_pronoun_reversals,
        extract_chat_features,
        extract_child_participant,
        normalize_group,
        safe_first,
    )


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


def _age_to_months(age_str: Optional[str]) -> Optional[float]:
    return age_to_months(age_str)


def _normalize_group(raw: Optional[str]) -> Optional[str]:
    return normalize_group(raw)


def _safe_first(values):
    return safe_first(values)


def _extract_child_participant(reader) -> Optional[object]:
    return extract_child_participant(reader)


def _content_tokens(utt) -> list[str]:
    return content_tokens(utt)


def _count_echolalia(all_utts, window: int = 5, min_tokens: int = 2) -> int:
    return count_echolalia(all_utts, window=window, min_tokens=min_tokens)


def _count_pronoun_reversals(raw_text: str) -> int:
    return count_pronoun_reversals(raw_text)


def _extract_features(cha_path: Path) -> Optional[dict]:
    return extract_chat_features(cha_path)


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
