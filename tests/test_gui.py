"""Unit tests for LinguaLens Desktop GUI Application."""

from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk
import pytest

from packages.tui.client import LinguaLensClient
from packages.gui.app import LinguaLensGUIApp


@pytest.fixture(autouse=True)
def mock_msgbox(monkeypatch):
    """Prevent blocking modal dialogs during automated tests."""
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *a, **k: None)
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda *a, **k: None)
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *a, **k: None)
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *a, **k: True)
    monkeypatch.setattr("tkinter.filedialog.askopenfilename", lambda *a, **k: "")
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda *a, **k: "")


def test_gui_app_initialization():
    """Verify GUI widgets initialize cleanly without pre-populated mock cases."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()  # Don't show actual window during test
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Starts clean and empty
    assert app.active_case_id is None
    assert len(app.tree_cases.get_children()) == 0
    assert len(app.notebook.tabs()) == 5

    # Test tab switching
    app.notebook.select(1)
    assert app.notebook.index("current") == 1

    # Create new case
    new_c = client.create_case("C-001", "2021-06", "th", "Referral")
    app._refresh_cases()
    assert app.active_case_id == new_c["case_id"]
    assert len(app.tree_cases.get_children()) == 1

    root.destroy()


def test_empty_state_without_fake_metrics():
    """Verify that sessions without transcripts do NOT show synthetic metrics or fake radar polygons."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Create case and empty session
    new_c = client.create_case("C-EMPTY", "2021-06", "th")
    new_s = client.create_session(new_c["case_id"], "2026-08-22")
    app.active_case_id = new_c["case_id"]
    app.active_session_id = new_s["session_id"]
    app._refresh_transcript_and_findings()

    # Findings should be clean empty state
    findings = client.get_findings(new_s["session_id"])
    assert findings["has_data"] is False
    assert findings["metrics"] == {}

    # Tab 4 feature table should show "No Data" notice, not fake numbers
    rows = [app.tree_metrics.item(i)["values"] for i in app.tree_metrics.get_children()]
    assert any("No Data" in str(r) for r in rows)

    # Report draft on empty session should not generate fake text
    app._generate_report_draft()
    assert app.txt_narrative.get("1.0", tk.END).strip() == ""

    root.destroy()


def _pump_events(root: tk.Tk) -> None:
    """Pump Tkinter event queue safely without blocking on withdrawn windows."""
    try:
        import _tkinter
        for _ in range(20):
            if not root.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
                break
    except Exception:
        root.update_idletasks()


def test_async_task_execution():
    """Verify background task execution updates UI asynchronously via root.after."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    result_holder = []

    def background_work():
        return {"status": "ok", "value": 42}

    def on_complete(result):
        result_holder.append(result)

    thread = app._run_async_task(
        target=background_work,
        on_success=on_complete,
        on_error=lambda err: None,
        busy_msg="Processing test...",
    )

    if thread:
        thread.join(timeout=2.0)

    # Drain async queue on main thread
    app._poll_async_queue()

    assert len(result_holder) == 1
    assert result_holder[0]["value"] == 42
    root.destroy()


def test_audio_segment_playback_command():
    """Verify audio snippet command generation for given start and end seconds."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    cmd, _ = app._build_audio_segment_command("sample.wav", 1.5, 4.2)
    assert cmd is not None
    assert any("afplay" in str(arg) or "play" in str(arg) or "sound" in str(arg).lower() for arg in cmd)
    root.destroy()


def test_utterance_edit_marks_stale():
    """Editing an utterance must mark findings and reports as stale until recalculated."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Ingest demo dialogue synchronously via worker
    thread = app._load_demo_dialogue()
    if thread:
        thread.join(timeout=2.0)
    app._poll_async_queue()

    assert not app.is_findings_stale
    assert app.tree_utterances.get_children()

    # Select first utterance and edit
    first_u = app.tree_utterances.get_children()[0]
    app.tree_utterances.selection_set(first_u)
    app._on_utterance_selected(None)
    app.entry_u_text.delete(0, tk.END)
    app.entry_u_text.insert(0, "เล่น รถ สี แดง เร็ว")
    app._save_utterance_edit()

    assert app.is_findings_stale is True

    # Recalculate findings
    app._recalculate_findings()
    assert app.is_findings_stale is False
    root.destroy()


def test_spider_diagram_drawing_and_resize():
    """Verify radar chart draws correctly and recalculates on resize."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    thread = app._load_demo_dialogue()
    if thread:
        thread.join(timeout=2.0)
    app._poll_async_queue()

    assert len(app.canvas_radar.find_all()) > 0

    # Trigger resize event handler
    app._on_canvas_radar_resize(None)
    app._do_redraw_radar()
    assert len(app.canvas_radar.find_all()) > 0
    root.destroy()


def test_dialog_creation():
    """Verify create case and session dialogs instantiate with dynamic column weights."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    dialog_case = app._build_create_case_window()
    assert dialog_case.winfo_exists()
    dialog_case.destroy()

    dialog_session = app._build_create_session_window()
    assert dialog_session.winfo_exists()
    dialog_session.destroy()

    root.destroy()


def test_word_segment_ui_and_playback():
    """Verify word timing chips render and invoke segment audio playback."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Mock an active transcript with sub-word alignments
    app.active_transcript = {
        "transcript_id": "tr-test-words",
        "session_id": "S-001",
        "status": "pending_review",
        "utterances": [
            {
                "id": "u-1",
                "speaker": "CHI",
                "text": "เล่น รถ แดง",
                "start_time": 1.0,
                "end_time": 3.5,
                "words": [
                    {"text": "เล่น", "start_time": 1.0, "end_time": 1.5},
                    {"text": "รถ", "start_time": 1.6, "end_time": 2.2},
                    {"text": "แดง", "start_time": 2.3, "end_time": 3.5},
                ],
            }
        ],
    }
    app.active_audio_path = "mock_session.wav"
    app.tree_utterances.insert("", tk.END, iid="u-1", values=("1", "CHI", "1.00 - 3.50", "เล่น รถ แดง", ""))
    app.tree_utterances.selection_set("u-1")
    app._on_utterance_selected(None)

    # Verify that word chips were rendered
    chips = app.container_word_buttons.winfo_children()
    assert len(chips) == 3
    assert "เล่น" in chips[0].cget("text")
    assert "รถ" in chips[1].cget("text")
    assert "แดง" in chips[2].cget("text")

    # Verify build audio segment command for word
    cmd, _ = app._build_audio_segment_command("mock_session.wav", 1.6, 2.2)
    assert cmd is not None
    assert any("afplay" in str(arg) or "play" in str(arg) or "sound" in str(arg).lower() for arg in cmd)

    # Test utterance highlighting method
    app._highlight_utterance("u-1")
    assert "playing" in app.tree_utterances.item("u-1", "tags")

    # Test stop playback clears highlighting tags
    app._stop_playback()
    assert "playing" not in app.tree_utterances.item("u-1", "tags")

    root.destroy()


def test_continuous_playback_toolbar_and_follow():
    """Verify audio player toolbar and live follow state controls."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    assert hasattr(app, "btn_play_continuous")
    assert hasattr(app, "btn_stop_audio")
    assert hasattr(app, "lbl_playback_status")

    # Test stop when idle is safe
    app._stop_playback()
    assert not app._is_continuous_playing
    assert "Stopped" in app.lbl_playback_status.cget("text")

    root.destroy()
