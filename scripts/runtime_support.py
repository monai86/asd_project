"""Pure-Python runtime policy; safe to import before native dependencies."""

from __future__ import annotations


MIN_VERSION = (3, 11)
MAX_VERSION = (3, 14)
RECOMMENDED_VERSION = "3.12"


def validation_error(version: tuple[int, int]) -> str | None:
    if version < MIN_VERSION or version >= MAX_VERSION:
        return (
            "LinguaLens supports Python >=3.11,<3.14. "
            "Use Python 3.12 for the verified environment."
        )
    return None
