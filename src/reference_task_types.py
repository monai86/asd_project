"""Shared TalkBank task type normalization helpers."""

from __future__ import annotations

import re
from typing import Any


def normalize_task_type(value: Any) -> str:
    """Return the canonical task type label used by reference cohorts."""
    raw = str(value or "").strip()
    if not raw:
        return ""

    canonical = re.sub(r"[\s-]+", "_", raw.lower())
    compact = canonical.replace("_", "")
    aliases = {
        "toyplay": "toyplay",
        "narrative": "narrative",
        "pictures": "picture_description",
        "picturedescription": "picture_description",
    }
    return aliases.get(compact, canonical)
