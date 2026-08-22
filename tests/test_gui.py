"""Unit tests for LinguaLens Desktop GUI Application."""

from __future__ import annotations

import os
import sys
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


def test_audio_ingest_progress_dialog_and_stage_updates():
    """Verify audio ingestion progress modal creation, live updates, and graceful teardown."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Trigger progress dialog
    app._show_ingest_progress_dialog("test_sample.wav")
    assert app._progress_dialog is not None
    assert app._progress_dialog.winfo_exists()
    assert app._dlg_bar_progress is not None

    # Test real-time progress update
    app._update_ingest_progress(0.45, "Running Whisper ASR: transcribing 00:04.2s - 00:08.5s...")
    assert app._dlg_bar_progress["value"] == 45
    assert "45%" in app._dlg_lbl_pct.cget("text")
    assert "Whisper ASR" in app._dlg_lbl_stage.cget("text")
    assert "45%" in app.lbl_status.cget("text")

    # Test dismiss and cleanup
    app._close_ingest_progress_dialog()
    assert app._progress_dialog is None

    root.destroy()


def test_audio_ingestion_and_findings_determinism(tmp_path, monkeypatch):
    """Verify that ingesting the same audio produces deterministic transcript and feature metrics."""
    import soundfile as sf
    import numpy as np
    from src.audio_pipeline.pipeline import PipelineResult
    from src.audio_pipeline.whisper_transcribe import UtteranceSegment, WordSegment
    from src.audio_pipeline.acoustic_profile import AcousticProfile

    sr = 16000
    t = np.linspace(0, 1.0, int(sr * 1.0))
    wav_data = (0.4 * np.sin(2 * np.pi * 320 * t)).astype(np.float32)
    wav_file = tmp_path / "deterministic_test.wav"
    sf.write(str(wav_file), wav_data, sr)

    def mock_audio_to_cha(audio_path, **kwargs):
        u1 = UtteranceSegment(start=0.0, end=1.0, text="เล่น รถ", speaker="CHI", words=[WordSegment("เล่น", 0.0, 0.4, 0.95), WordSegment("รถ", 0.5, 1.0, 0.95)])
        prof = AcousticProfile(duration_sec=1.0, f0_median_hz=315.0, f0_iqr_hz=18.0, voiced_ratio=0.8, pause_ratio=0.2, child_speech_rate_wps=2.0)
        chat = "@UTF8\n@Begin\n@Languages:\ttha\n@Participants:\tCHI Child\n*CHI:\tเล่น รถ .\n%mor:\tv|เล่น n|รถ .\n@End\n"
        return PipelineResult(
            chat_text=chat,
            chat_path=None,
            utterances=[u1],
            n_child_utterances=1,
            n_adult_utterances=0,
            total_duration_sec=1.0,
            acoustic_profile=prof,
        )

    import src.audio_pipeline.pipeline
    monkeypatch.setattr(src.audio_pipeline.pipeline, "audio_to_cha", mock_audio_to_cha)

    client1 = LinguaLensClient(mock_mode=True)
    c1 = client1.create_case("C-DET-01", "2021-05", "th")
    s1 = client1.create_session(c1["case_id"], "2026-08-23")
    tr1 = client1.ingest_audio_file(s1["session_id"], str(wav_file))
    f1 = client1.get_findings(s1["session_id"])

    client2 = LinguaLensClient(mock_mode=True)
    c2 = client2.create_case("C-DET-02", "2021-05", "th")
    s2 = client2.create_session(c2["case_id"], "2026-08-23")
    tr2 = client2.ingest_audio_file(s2["session_id"], str(wav_file))
    f2 = client2.get_findings(s2["session_id"])

    assert len(tr1["utterances"]) == len(tr2["utterances"]) == 1
    assert tr1.get("raw_cha") == tr2.get("raw_cha")
    assert f1["metrics"].get("f0_median_hz") == f2["metrics"].get("f0_median_hz") == 315.0
    assert f1["metrics"].get("mlu_words") == f2["metrics"].get("mlu_words") == 2.0
    assert f1["metrics"].get("ttr") == f2["metrics"].get("ttr") == 1.0


def test_waveform_and_speed_control(tmp_path):
    """Verify waveform peak calculation, canvas rendering, and speed rate command options."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    import soundfile as sf
    import numpy as np

    sr = 16000
    t = np.linspace(0, 1.5, int(sr * 1.5))
    wav_data = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    wav_file = tmp_path / "waveform_test.wav"
    sf.write(str(wav_file), wav_data, sr)

    peaks = app._compute_waveform_peaks(str(wav_file), num_peaks=50)
    assert len(peaks) > 0
    assert max(peaks) <= 1.0

    app.active_audio_path = str(wav_file)
    app._audio_waveform_peaks = peaks
    app._redraw_waveform()

    # Test Speed change
    app.combo_speed.set("0.75x")
    app._on_speed_changed(None)
    assert app.playback_speed == 0.75

    cmd, _ = app._build_audio_segment_command(str(wav_file), 0.0, 1.0)
    assert cmd is not None
    if sys.platform == "darwin":
        assert "-r" in cmd
        assert "0.75" in cmd

    root.destroy()


def test_multiformat_export_center(tmp_path, monkeypatch):
    """Verify TalkBank .cha, CSV, and HTML report export flows."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Ingest mock transcript
    c = client.create_case("C-EXP-01", "2021-05", "th")
    s = client.create_session(c["case_id"], "2026-08-23")
    app.active_case_id = c["case_id"]
    app.active_session_id = s["session_id"]
    client.ingest_transcript_text(s["session_id"], "CHI: เล่น รถ สนุก\nINV: เก่ง มาก ครับ")
    app._refresh_transcript_and_findings()

    # 1. Test CHA Export
    cha_out = tmp_path / "test_export.cha"
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda **kwargs: str(cha_out))
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *a, **k: None)
    app._export_cha_file()
    assert cha_out.exists()
    assert "@Begin" in cha_out.read_text(encoding="utf-8")

    # 2. Test CSV Export
    csv_out = tmp_path / "test_export.csv"
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda **kwargs: str(csv_out))
    app._export_csv_biomarkers()
    assert csv_out.exists()
    csv_content = csv_out.read_text(encoding="utf-8")
    assert "mlu_words" in csv_content or "metric_name" in csv_content

    # 3. Test HTML Report Export
    html_out = tmp_path / "test_export.html"
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda **kwargs: str(html_out))
    app._export_html_report()
    assert html_out.exists()
    html_content = html_out.read_text(encoding="utf-8")
    assert "LinguaLens" in html_content
    assert "<!DOCTYPE html>" in html_content

    # 4. Test Edit Box Buttons & Speaker Update
    assert app.btn_play_snippet.cget("text") == "🔊 Play Snippet"
    assert app.btn_save_u_edit.cget("text") == "💾 Save Utterance Edit"

    # Select u-1, change speaker to MOT and save
    app.tree_utterances.selection_set("u-1")
    app._on_utterance_selected(None)
    assert app.combo_spk.get() == "CHI"
    app.combo_spk.set("MOT")
    app._save_utterance_edit()
    assert app.is_findings_stale is True

    updated_tr = client.get_session_transcript(s["session_id"])
    assert updated_tr["utterances"][0]["speaker"] == "MOT"

    root.destroy()


def test_audio_scrubber_and_seeking(tmp_path):
    """Verify audio scrubber slider, waveform seeking, playhead needle, and utterance auto-highlighting."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    import soundfile as sf
    import numpy as np

    sr = 16000
    t = np.linspace(0, 3.0, int(sr * 3.0))
    wav_data = (0.3 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    wav_file = tmp_path / "scrubber_test.wav"
    sf.write(str(wav_file), wav_data, sr)

    app.active_audio_path = str(wav_file)
    app._audio_waveform_duration = 3.0
    app.active_transcript = {
        "transcript_id": "tr-scrub-01",
        "utterances": [
            {"id": "u-1", "speaker": "INV", "text": "สวัสดีครับ", "start_time": 0.0, "end_time": 1.0},
            {"id": "u-2", "speaker": "CHI", "text": "เล่น รถ", "start_time": 1.2, "end_time": 2.5},
        ]
    }
    app.tree_utterances.insert("", tk.END, iid="u-1", values=("1", "INV", "0.0 - 1.0", "สวัสดีครับ", "Clean"))
    app.tree_utterances.insert("", tk.END, iid="u-2", values=("2", "CHI", "1.2 - 2.5", "เล่น รถ", "Clean"))

    # Test time formatting
    assert app._format_time(65.4) == "01:05.4"
    assert app._format_time(0.0) == "00:00.0"

    # Test seek to 1.5s (should highlight u-2)
    app._seek_and_play(1.5, auto_play=False)
    assert app._playhead_time_sec == 1.5
    assert app.lbl_time_current.cget("text") == "00:01.5"
    assert "playing" in app.tree_utterances.item("u-2", "tags")
    assert "playing" not in app.tree_utterances.item("u-1", "tags")

    # Test scrubber drag
    app._on_scrubber_press(None)
    assert app._is_user_scrubbing is True
    app._on_scrubber_slide("0.5")
    assert "playing" in app.tree_utterances.item("u-1", "tags")
    app._on_scrubber_release(None)
    assert app._is_user_scrubbing is False

    # Test stop playback
    app._stop_playback()
    assert app._is_continuous_playing is False

    # Test snippet playback via _play_selected_utterance
    app.tree_utterances.selection_set("u-2")
    app._play_selected_utterance()
    assert app._is_continuous_playing is True
    assert app._playback_end_limit_sec == 2.5
    assert app._current_playback_offset_sec == 1.2

    # Verify widget destruction safety (no TclError)
    app._on_utterance_selected(None)
    app._stop_playback()
    root.destroy()


def test_speaker_refinement_and_hotkeys(tmp_path, monkeypatch):
    """Verify Auto-Refine Speakers, Swap Speakers, and C/I/M keyboard tagging."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Ingest session with inverted speakers
    c = client.create_case("C-SPK-01", "2021-05", "th")
    s = client.create_session(c["case_id"], "2026-08-23")
    app.active_case_id = c["case_id"]
    app.active_session_id = s["session_id"]

    tr_data = {
        "transcript_id": "tr-spk-01",
        "session_id": s["session_id"],
        "utterances": [
            {"id": "u-1", "speaker": "CHI", "text": "Can you do this? Try again.", "start_time": 0.0, "end_time": 2.0},
            {"id": "u-2", "speaker": "INV", "text": "car", "start_time": 2.2, "end_time": 3.0},
            {"id": "u-3", "speaker": "CHI", "text": "Good job. Now touch your nose.", "start_time": 3.2, "end_time": 5.0},
        ],
        "qa_summary": {"total_utterances": 3, "unresolved_flags": 0, "child_utterance_count": 2},
    }
    client._mock_data["transcripts"]["tr-spk-01"] = tr_data
    app.active_transcript = tr_data
    app._refresh_transcript_and_findings()

    # 1. Test Auto-Refine Speakers
    app._auto_refine_speakers()
    utts = app.active_transcript["utterances"]
    assert utts[0]["speaker"] == "INV"  # Adult prompt corrected
    assert utts[1]["speaker"] == "CHI"  # Child response
    assert utts[2]["speaker"] == "INV"  # Adult prompt corrected

    # 2. Test Swap CHI <-> Adult
    app._swap_speakers()
    assert utts[0]["speaker"] == "CHI"
    assert utts[1]["speaker"] == "INV"
    assert utts[2]["speaker"] == "CHI"

    # 3. Test Keyboard Quick Tagging (Press C/I/M)
    app.tree_utterances.selection_set("u-1")

    class FakeEvent:
        def __init__(self, char, keysym=""):
            self.char = char
            self.keysym = keysym

    # Press 'I' on u-1
    res = app._on_tree_key_press(FakeEvent("i", "i"))
    assert res == "break"
    assert app.active_transcript["utterances"][0]["speaker"] == "INV"

    # Press 'C' on next row (u-2)
    res = app._on_tree_key_press(FakeEvent("c", "c"))
    assert res == "break"
    assert app.active_transcript["utterances"][1]["speaker"] == "CHI"

    root.destroy()
