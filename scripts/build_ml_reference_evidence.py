"""Build a versioned ML reference-evidence artifact package."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.ml.reference_artifacts import write_reference_artifacts  # noqa: E402
from packages.ml.reference_dataset import build_canonical_reference_rows  # noqa: E402
from packages.ml.gate1_validation import evaluate_gate1  # noqa: E402


DEFAULT_KEY_ENV = "ML_REFERENCE_PSEUDONYMIZATION_KEY"


def _pseudonymization_key(environment_name: str) -> bytes:
    raw = os.getenv(environment_name)
    if raw is None:
        raise ValueError(
            f"Set {environment_name} to a secret containing at least 32 bytes."
        )
    if raw.startswith("hex:"):
        try:
            key = bytes.fromhex(raw.removeprefix("hex:"))
        except ValueError as exc:
            raise ValueError(
                f"{environment_name} contains invalid hex key material."
            ) from exc
    else:
        key = raw.encode("utf-8")
    if len(key) < 32:
        raise ValueError(
            f"{environment_name} must contain at least 32 bytes."
        )
    return key


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--combined",
        type=Path,
        default=PROJECT_ROOT / "data" / "combined_features.csv",
    )
    parser.add_argument(
        "--curated",
        type=Path,
        default=PROJECT_ROOT / "data" / "curated_group_features.csv",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--artifact-version", required=True)
    parser.add_argument(
        "--pseudonymization-key-env",
        default=DEFAULT_KEY_ENV,
        help="Environment variable containing raw or hex:<hex> key material.",
    )
    parser.add_argument(
        "--pseudonymization-key-version",
        default="v1",
    )
    parser.add_argument(
        "--skip-gate1",
        action="store_true",
        help="Build descriptive artifacts without running research Gate 1.",
    )
    parser.add_argument(
        "--gate1-bootstrap",
        type=int,
        default=500,
    )
    parser.add_argument(
        "--feature-parity-passed",
        action="store_true",
        help="Record that the reviewed golden-fixture parity gate passed.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    combined = pd.read_csv(args.combined)
    curated = pd.read_csv(args.curated)
    canonical = build_canonical_reference_rows(
        combined,
        curated,
        pseudonymization_key=_pseudonymization_key(
            args.pseudonymization_key_env
        ),
        pseudonymization_key_version=args.pseudonymization_key_version,
    )
    gate1_validation = None
    if not args.skip_gate1:
        gate1_validation = evaluate_gate1(
            canonical.rows,
            n_bootstrap=args.gate1_bootstrap,
            feature_parity_passed=args.feature_parity_passed,
        ).to_dict()
    paths = write_reference_artifacts(
        canonical,
        args.output_dir,
        artifact_version=args.artifact_version,
        gate1_validation=gate1_validation,
    )
    print(f"Reference evidence artifact: {paths.directory}")
    print(f"Canonical rows: {len(canonical.rows)}")
    print(f"Audit rows: {len(canonical.audit)}")
    print(f"Dataset hash: {canonical.dataset_hash}")
    if gate1_validation is not None:
        print(
            "Gate 1 status: "
            + (
                "promoted_candidate"
                if gate1_validation["promotion_gate"]["passed"]
                else "research_only"
            )
        )


if __name__ == "__main__":
    main()
