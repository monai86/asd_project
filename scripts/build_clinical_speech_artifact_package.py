#!/usr/bin/env python3
"""Build an offline Clinical Speech Artifact Package."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.clinical_speech_artifacts import build_reviewed_cha_package


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Clinical Speech Artifact Package from reviewed CHAT."
    )
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--reviewed-cha", required=True, type=Path)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/clinical_speech"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package_dir = build_reviewed_cha_package(
        session_id=args.session_id,
        reviewed_cha_path=args.reviewed_cha,
        output_root=args.output_root,
    )
    print(f"created package: {package_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
