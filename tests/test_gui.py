"""Unit tests for LinguaLens Desktop GUI Application."""

from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk
import pytest

from packages.tui.client import LinguaLensClient
from packages.gui.app import LinguaLensGUIApp


def test_gui_app_initialization():
    """Verify GUI widgets initialize properly without errors."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()  # Don't show actual window during test
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    assert app.active_case_id is not None
    assert app.tree_cases.get_children()
    assert len(app.notebook.tabs()) == 5

    # Test tab switching
    app.notebook.select(1)
    assert app.notebook.index("current") == 1

    root.destroy()
