#!/usr/bin/env python3
"""LinguaLens Interactive Terminal UI (TUI) Launcher.

Runs an interactive, text-based clinician workflow replicating all 5 steps
from the web application with live API support or offline mock fallback.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure root is in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.tui.client import LinguaLensClient, DEFAULT_API_URL
from packages.tui.workflow import WorkflowRunner


def main() -> int:
    parser = argparse.ArgumentParser(description="LinguaLens Interactive Terminal UI")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Base URL of LinguaLens Backend API")
    parser.add_argument("--mock", action="store_true", help="Force offline mock mode")
    parser.add_argument("--case", default=None, help="Initial case ID to load")
    args = parser.parse_args()

    client = LinguaLensClient(base_url=args.api_url, mock_mode=args.mock)
    runner = WorkflowRunner(client)

    try:
        runner.start(initial_case_id=args.case)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled. Exiting LinguaLens TUI.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
