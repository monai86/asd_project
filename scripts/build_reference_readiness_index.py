"""Build the Reference Readiness Index JSON artifact."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifests"

COVERAGE_PATH = REFERENCE_DIR / "english_child_reference_coverage.csv"
COHORTS_PATH = REFERENCE_DIR / "english_child_reference_cohorts.csv"
CLAN_QC_PATH = MANIFEST_DIR / "english_child_clan_qc_summary.csv"
OUTPUT_JSON_PATH = REFERENCE_DIR / "reference_readiness_index.json"


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"Required CSV file not found: {path}")
    return pd.read_csv(path, keep_default_na=False)


def build_readiness_index(
    coverage_path: Path = COVERAGE_PATH,
    cohorts_path: Path = COHORTS_PATH,
    clan_qc_path: Path = CLAN_QC_PATH,
) -> dict:
    coverage_df = _read_csv(coverage_path)
    cohorts_df = _read_csv(cohorts_path)
    
    # Verify CLAN QC file exists
    if not clan_qc_path.exists():
        raise FileNotFoundError(f"Required CLAN QC summary file not found: {clan_qc_path}")

    # Calculate summary counts based on coverage_status
    status_counts = coverage_df["coverage_status"].value_counts().to_dict()
    summary = {
        "ok": int(status_counts.get("ok", 0)),
        "low_n": int(status_counts.get("low_n", 0)),
        "not_cohort_ready": int(status_counts.get("not_cohort_ready", 0)),
    }

    # Map each row to a cell metadata dictionary
    cells = []
    for _, row in coverage_df.iterrows():
        # Match with cohorts_df if needed, but english_child_reference_coverage.csv already has confidence_flag and cohort_n
        lang = str(row.get("language") or "eng").strip()
        age_band = str(row.get("age_band_12mo") or "").strip()
        task = str(row.get("task_type") or "").strip()
        grp = str(row.get("group") or "").strip()
        
        cohort_n = 0
        try:
            cohort_n = int(row.get("cohort_n") or 0)
        except ValueError:
            pass

        coverage_status = str(row.get("coverage_status") or "").strip()
        confidence_flag = str(row.get("confidence_flag") or "").strip()
        clan_status = str(row.get("clan_coverage_status") or "").strip()
        clan_metric_ready = (clan_status == "matched")

        cells.append({
            "language": lang,
            "age_band_12mo": age_band,
            "task_type": task,
            "group": grp,
            "cohort_n": cohort_n,
            "coverage_status": coverage_status,
            "confidence_flag": confidence_flag,
            "clan_metric_ready": clan_metric_ready
        })

    # Get relative source files
    source_files = [
        str(coverage_path.relative_to(PROJECT_ROOT)),
        str(cohorts_path.relative_to(PROJECT_ROOT)),
        str(clan_qc_path.relative_to(PROJECT_ROOT)),
    ]

    return {
        "summary": summary,
        "cells": cells,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_files": source_files
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, default=COVERAGE_PATH)
    parser.add_argument("--cohorts", type=Path, default=COHORTS_PATH)
    parser.add_argument("--clan-qc", type=Path, default=CLAN_QC_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_JSON_PATH)
    args = parser.parse_args()

    try:
        data = build_readiness_index(
            coverage_path=args.coverage,
            cohorts_path=args.cohorts,
            clan_qc_path=args.clan_qc
        )
        
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        print(f"Saved Reference Readiness Index to {args.output}")
        print(f"Summary: ok={data['summary']['ok']}, low_n={data['summary']['low_n']}, not_cohort_ready={data['summary']['not_cohort_ready']}")
    except Exception as exc:
        print(f"Error building readiness index: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
