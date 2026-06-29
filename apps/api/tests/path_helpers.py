from __future__ import annotations

from pathlib import Path


def api_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    return api_root().parents[1]
