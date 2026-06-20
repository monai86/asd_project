"""Extract features from labeled CHAT folders and train baseline classifiers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from packages.ml.train_model import (
    DEFAULT_CURATED_TRANSCRIPT_DIR,
    build_dataset_from_labeled_folders,
    train_reference_cohort_models,
)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Scan a .cha directory where parent folders encode labels "
            "(ASD, TD, DD, SLI/STI, LT, HL), extract features, and train models."
        )
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_CURATED_TRANSCRIPT_DIR)
    parser.add_argument(
        "--features-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "curated_group_features.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "curated_group_training",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = get_parser().parse_args()
    df = build_dataset_from_labeled_folders(args.root, output_path=args.features_csv)
    labeled = df[df.get("error", "").fillna("") == ""] if "error" in df.columns else df
    print(f"Extracted {len(labeled)} usable feature rows from {args.root}")
    if "label" in labeled.columns:
        print(labeled["label"].value_counts().to_string())

    result = train_reference_cohort_models(
        labeled,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Features CSV: {args.features_csv}")
    if not args.dry_run:
        print(f"Training outputs: {args.output_dir}")


if __name__ == "__main__":
    main()
