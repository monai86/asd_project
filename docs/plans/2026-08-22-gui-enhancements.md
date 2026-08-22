# LinguaLens GUI Comprehensive Multi-Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the LinguaLens Desktop GUI (`packages/gui/app.py`) and UI workflow into a highly responsive, non-blocking, clinically-safe, and visually refined application aligned with `PRODUCT.md` and `PROJECT_SOURCE_OF_TRUTH.md`.

**Architecture:** 
1. Asynchronous background execution layer using Python's `threading.Thread` with thread-safe UI scheduling via `root.after()` to eliminate UI freeze during audio/transcript ingestion.
2. Cross-platform native audio snippet player (`afplay`/`aplay`/`ffplay`/subprocess) attached to transcript utterances.
3. Strict Rule 9 compliance with `stale` state tracking and recalculation gates across findings and reports.
4. Dynamic canvas geometry computation with `<Configure>` debounce for the Spider / Radar Diagram.
5. Clinical Teal design system (`#0f766e`, `#f0fdfa`, `#0f172a`) with flexible HiDPI grid layouts.

**Tech Stack:** Python 3.10+ / Tkinter & TTK / Pytest / Next.js 16 (for UI parity)

---

## Task Decomposition

### Task 1: Non-Blocking Background Worker for Ingestion & Progress Indicator

**Files:**
- Modify: `packages/gui/app.py`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Write the failing tests in `tests/test_gui.py` for async worker and progress states**

```python
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

    app._run_async_task(
        target=background_work,
        on_success=on_complete,
        on_error=lambda err: None,
        busy_msg="Processing...",
    )

    # Process pending Tkinter events
    root.update()
    import time
    time.sleep(0.1)
    root.update()

    assert len(result_holder) == 1
    assert result_holder[0]["value"] == 42
    root.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest tests/test_gui.py::test_async_task_execution -v`
Expected: FAIL with `AttributeError: 'LinguaLensGUIApp' object has no attribute '_run_async_task'`

- [ ] **Step 3: Implement `_run_async_task`, status banner, and progress bar in `packages/gui/app.py`**

Add thread-safe background runner and integrate it into `_process_audio_file()`, `_load_demo_dialogue()`, `_browse_text_file()`, and `_ingest_typed_text()`:

```python
import threading

def _run_async_task(
    self,
    target: Any,
    on_success: Any,
    on_error: Any = None,
    busy_msg: str = "Processing...",
) -> None:
    """Execute long-running work in a background thread and post results back to Tkinter event loop."""
    self._set_busy_state(True, busy_msg)

    def worker():
        try:
            res = target()
            self.root.after(0, lambda: self._on_task_done(res, on_success, None))
        except Exception as exc:
            self.root.after(0, lambda: self._on_task_done(None, on_error, exc))

    t = threading.Thread(target=worker, daemon=True)
    t.start()

def _on_task_done(self, result: Any, callback: Any, error: Exception | None) -> None:
    self._set_busy_state(False)
    if error:
        if callback:
            callback(error)
        else:
            messagebox.showerror("Operation Failed", str(error))
    elif callback:
        callback(result)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest tests/test_gui.py::test_async_task_execution -v`
Expected: PASS

---

### Task 2: Utterance Audio Snippet Playback System

**Files:**
- Modify: `packages/gui/app.py`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Write failing tests for audio snippet range extraction and player dispatch**

```python
def test_audio_segment_playback_command():
    """Verify audio snippet command generation for given start and end seconds."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    cmd = app._build_audio_segment_command("sample.wav", 1.5, 4.2)
    assert cmd is not None
    assert "sample.wav" in cmd[len(cmd)-1] or "sample.wav" in " ".join(cmd)
    root.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest tests/test_gui.py::test_audio_segment_playback_command -v`
Expected: FAIL with `AttributeError: 'LinguaLensGUIApp' object has no attribute '_build_audio_segment_command'`

- [ ] **Step 3: Implement audio playback logic and `[🔊 Play Snippet]` button in Tab 3 Review UI**

Implement platform-aware audio segment player:
- On macOS: `afplay` with `-t` duration or ffmpeg / subprocess.
- Add `_play_selected_utterance()` method and attach to a prominent `[🔊 Play Segment]` button in the Utterance Editor toolbar.
- Provide feedback label when audio is playing or if session has no audio file.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest tests/test_gui.py::test_audio_segment_playback_command -v`
Expected: PASS

---

### Task 3: Stale State Invalidation & Clinical Guard in GUI

**Files:**
- Modify: `packages/gui/app.py`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Write failing test for stale state tracking on utterance edit**

```python
def test_utterance_edit_marks_stale():
    """Editing an utterance must mark findings and reports as stale until recalculated."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Ingest demo dialogue
    app._load_demo_dialogue()
    assert not app.is_findings_stale

    # Select first utterance and edit
    app.tree_utterances.selection_set(app.tree_utterances.get_children()[0])
    app.entry_u_text.delete(0, tk.END)
    app.entry_u_text.insert(0, "เล่น รถ สี แดง เร็ว")
    app._save_utterance_edit()

    assert app.is_findings_stale is True
    root.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest tests/test_gui.py::test_utterance_edit_marks_stale -v`
Expected: FAIL with `AttributeError: 'LinguaLensGUIApp' object has no attribute 'is_findings_stale'`

- [ ] **Step 3: Implement stale state tracking, UI warning banner, and `_recalculate_findings()` action**

- Add `self.is_findings_stale: bool = False` to `LinguaLensGUIApp`.
- When `_save_utterance_edit()` executes, set `self.is_findings_stale = True`.
- In Tab 4 (Findings) & Tab 5 (Report), show amber banner `⚠️ Transcript modified: Findings & Report are stale. Please click [🔄 Recalculate]`.
- Guard `_sign_off_report()` with a confirmation warning if findings are currently stale.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest tests/test_gui.py::test_utterance_edit_marks_stale -v`
Expected: PASS

---

### Task 4: Dynamic Canvas Resize & Responsive Radar Diagram Scaling

**Files:**
- Modify: `packages/gui/app.py`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Write failing test for dynamic canvas resize binding**

```python
def test_spider_diagram_drawing_and_resize():
    """Verify radar chart draws correctly and recalculates on resize."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    app._load_demo_dialogue()
    assert len(app.canvas_radar.find_all()) > 0

    # Trigger resize event handler
    app._on_canvas_radar_resize(None)
    assert len(app.canvas_radar.find_all()) > 0
    root.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest tests/test_gui.py::test_spider_diagram_drawing_and_resize -v`
Expected: FAIL with `AttributeError: 'LinguaLensGUIApp' object has no attribute '_on_canvas_radar_resize'`

- [ ] **Step 3: Implement `<Configure>` event binding and dynamic geometry math for `canvas_radar`**

- Bind `self.canvas_radar.bind("<Configure>", self._on_canvas_radar_resize)`
- Add debounce timer (`after_cancel` / `after`) to redraw smoothly only when geometry settles.
- Compute radius dynamically: `radius = min(width, height) / 2 - 40` with bounds check `min_radius = 80`.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest tests/test_gui.py::test_spider_diagram_drawing_and_resize -v`
Expected: PASS

---

### Task 5: Modern Clinical Teal Design System & HiDPI Dialog Scaling

**Files:**
- Modify: `packages/gui/app.py`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Write failing test for dialog geometry responsiveness**

```python
def test_dialog_creation():
    """Verify create case and session dialogs instantiate with dynamic column weights."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    dialog = app._build_create_case_window()
    assert dialog.winfo_exists()
    dialog.destroy()
    root.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest tests/test_gui.py::test_dialog_creation -v`
Expected: FAIL with `AttributeError: 'LinguaLensGUIApp' object has no attribute '_build_create_case_window'`

- [ ] **Step 3: Implement Clinical Teal Design System and flexible dialog layouts**

- Update `_configure_styles()`:
  - Background: `#f8fafc` (slate-50)
  - Primary Teal Accent: `#0f766e` / Active Tab `#f0fdfa` / Focus `#115e59`
  - Text Strong: `#0f172a` / Muted: `#475569`
  - Enhanced Treeview styling: row height 28px, alternating subtle row striping.
- Add Keyboard Shortcuts:
  - `root.bind("<Control-s>", lambda e: self._handle_ctrl_s())`
  - `root.bind("<Command-s>", lambda e: self._handle_ctrl_s())`
- Refactor dialogs to use `columnconfigure(1, weight=1)` and dynamic padding.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest tests/test_gui.py::test_dialog_creation -v`
Expected: PASS

---

### Task 6: Full Verification & Automated Regression Testing

**Files:**
- Modify: `tests/test_gui.py`
- Run: `bash scripts/check_project.sh`

- [ ] **Step 1: Run complete GUI test suite**

Run: `PYTHONPATH=. pytest tests/test_gui.py -v`
Expected: All tests pass (100%)

- [ ] **Step 2: Run full project verification check**

Run: `bash scripts/check_project.sh`
Expected: All project linters, core tests, and audits pass cleanly.

---

## Verification Plan

### Automated Tests
1. `PYTHONPATH=. pytest tests/test_gui.py -v` (Unit & Component tests for GUI)
2. `pytest -m "not audio"` (Core Python tests)
3. `cd apps/lingualens-app && npm test` (Frontend Next.js tests)
4. `bash scripts/check_project.sh` (Repository health & consistency verification)

### Manual Verification
1. Launch Desktop GUI via `./run_gui.sh --mock`
2. Test Case & Session switching in top context bar.
3. Test Ingestion with Demo dialogue & local file selection.
4. Verify non-blocking async execution indicator.
5. In Tab 3, edit an utterance and verify the `⚠️ Stale` badge appears in Tab 4 & Tab 5.
6. Verify Spider Diagram scales smoothly when resizing window.
7. Test Report generation, sign-off gate, and Markdown export.
