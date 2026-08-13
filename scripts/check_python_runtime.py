#!/usr/bin/env python3
"""Fail before scientific/audio imports when Python is unsupported."""

from __future__ import annotations

import sys

from runtime_support import validation_error


def main() -> int:
    error = validation_error(sys.version_info[:2])
    if error:
        print(error, file=sys.stderr)
        return 2
    print(f"Supported Python runtime: {sys.version.split()[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
