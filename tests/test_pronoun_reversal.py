from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import _count_pronoun_reversals  # noqa: E402


def test_pronoun_reversal_counts_obvious_i_you_patterns():
    assert _count_pronoun_reversals("you am hungry .") == 1
    assert _count_pronoun_reversals("I are going .") == 1


def test_pronoun_reversal_counts_me_and_my_substitutions():
    assert _count_pronoun_reversals("me want cookie .") == 1
    assert _count_pronoun_reversals("my need help .") == 1


def test_pronoun_reversal_ignores_typical_pronoun_use():
    assert _count_pronoun_reversals("I want cookie .") == 0
    assert _count_pronoun_reversals("you are funny .") == 0
