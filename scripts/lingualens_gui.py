#!/usr/bin/env python3
"""LinguaLens Desktop GUI Launcher.

Launches the native graphical desktop interface for clinicians.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tkinter as tk

# Ensure root directory is in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.tui.client import LinguaLensClient, DEFAULT_API_URL
from packages.gui.app import LinguaLensGUIApp


def main() -> int:
    parser = argparse.ArgumentParser(description="LinguaLens Desktop GUI Application")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Base URL of LinguaLens Backend API")
    parser.add_argument("--mock", action="store_true", help="Force offline mock mode")
    args = parser.parse_args()

    client = LinguaLensClient(base_url=args.api_url, mock_mode=args.mock)

    root = tk.Tk()
    app = LinguaLensGUIApp(root, client=client)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
