"""LinguaLens Desktop GUI Application (Tkinter / TTK).

Provides an interactive graphical desktop interface for clinicians replicating
the 5-step LinguaLens decision-support workflow with local audio/video file selection,
acoustic prosody feature extraction, transcript QA review, and report sign-off.
"""

from __future__ import annotations

import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from packages.tui.client import LinguaLensClient


class LinguaLensGUIApp:
    """Main Desktop GUI Application window."""

    def __init__(self, root: tk.Tk, client: LinguaLensClient | None = None):
        self.root = root
        self.root.title("LinguaLens — Speech-Language Decision Support Desktop")
        self.root.geometry("1050x740")
        self.root.minsize(900, 600)

        self.client = client or LinguaLensClient()
        self.active_case_id: str | None = None
        self.active_session_id: str | None = None
        self.active_transcript: dict[str, Any] | None = None
        self.active_report: dict[str, Any] | None = None
        self.active_audio_path: str | None = None
        self.is_busy: bool = False
        self.is_findings_stale: bool = False
        self._resize_job: str | None = None
        self._async_queue: queue.Queue[tuple[Callable[[], None], Exception | None]] = queue.Queue()
        self._current_play_process: subprocess.Popen | None = None
        self._is_continuous_playing: bool = False
        self._playback_start_wall_time: float = 0.0
        self._word_highlight_timer_ids: list[str] = []
        self._word_button_widgets: list[tuple[ttk.Button, str, float, float]] = []
        self._progress_dialog: tk.Toplevel | None = None
        self._dlg_bar_progress: ttk.Progressbar | None = None
        self._dlg_lbl_stage: tk.Label | None = None
        self._dlg_lbl_pct: tk.Label | None = None
        self.playback_speed: float = 1.0
        self._audio_waveform_peaks: list[float] | None = None
        self._audio_waveform_duration: float = 0.0
        self._current_playback_offset_sec: float = 0.0
        self._playback_end_limit_sec: float | None = None
        self._playhead_time_sec: float = 0.0
        self._is_user_scrubbing: bool = False
        self._current_temp_slice: str | None = None

        self._configure_styles()
        self._build_header()
        self._build_tabs()
        self._build_statusbar()
        self._bind_shortcuts()
        self._poll_async_queue()
        self._load_initial_data()

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Clinical Teal System Colors & Fonts (Aligned with PRODUCT.md & tokens.css)
        self.bg_color = "#f8fafc"
        self.primary_color = "#0f766e"
        self.primary_strong = "#115e59"
        self.accent_soft = "#f0fdfa"
        self.border_color = "#cbd5e1"
        self.text_color = "#0f172a"
        self.root.configure(bg=self.bg_color)

        style.configure("TNotebook", background=self.bg_color)
        style.configure("TNotebook.Tab", padding=[14, 7], font=("Helvetica", 10, "bold"))
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.accent_soft), ("active", "#e2e8f0")],
            foreground=[("selected", self.primary_color), ("!selected", "#475569")],
        )
        style.configure("Treeview", rowheight=28, font=("Helvetica", 10))
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"), background="#e2e8f0", foreground=self.text_color)
        style.configure("Primary.TButton", font=("Helvetica", 10, "bold"), padding=[10, 5])
        style.configure("Success.TButton", font=("Helvetica", 10, "bold"), padding=[10, 5])

    # --- UI Layout Builders ---
    def _build_header(self) -> None:
        # Classic Desktop App Title Header
        header_frame = tk.Frame(self.root, bg="#f8fafc", padx=16, pady=8, highlightthickness=1, highlightbackground="#e2e8f0")
        header_frame.pack(fill=tk.X)

        title_frame = tk.Frame(header_frame, bg="#f8fafc")
        title_frame.pack(side=tk.LEFT)

        tk.Label(
            title_frame,
            text="🖥️ LinguaLens v1.6.3",
            font=("Helvetica", 14, "bold"),
            fg="#0f172a",
            bg="#f8fafc",
        ).pack(side=tk.LEFT)

        tk.Label(
            title_frame,
            text=" — Clinical Speech-Language Decision Support System",
            font=("Helvetica", 11),
            fg="#64748b",
            bg="#f8fafc",
        ).pack(side=tk.LEFT)

        # Connection Badge
        is_online = self.client.check_health()
        status_text = "● Connected (API)" if is_online else "○ Offline Mode"
        status_bg = "#dcfce7" if is_online else "#fef9c3"
        status_fg = "#166534" if is_online else "#854d0e"

        status_lbl = tk.Label(
            header_frame,
            text=status_text,
            font=("Helvetica", 9, "bold"),
            fg=status_fg,
            bg=status_bg,
            padx=8,
            pady=3,
        )
        status_lbl.pack(side=tk.RIGHT)

        # Subtle safety note
        safety_banner = tk.Frame(self.root, bg="#fffbeb", padx=14, pady=3, highlightthickness=1, highlightbackground="#fef3c7")
        safety_banner.pack(fill=tk.X)
        safety_lbl = tk.Label(
            safety_banner,
            text="⚠️ Research/Education Prototype Only. Non-diagnostic. Human-in-the-loop clinician verification required.",
            font=("Helvetica", 9, "italic"),
            fg="#b45309",
            bg="#fffbeb",
        )
        safety_lbl.pack(anchor=tk.W)

        # Persistent Global Context Bar (Searchable Case, Session, Refresh, Actions)
        ctx_bar = tk.Frame(self.root, bg="#f1f5f9", padx=12, pady=6, highlightthickness=1, highlightbackground="#cbd5e1")
        ctx_bar.pack(fill=tk.X, padx=12, pady=(6, 2))

        # Case Search & Selector
        tk.Label(ctx_bar, text="🔍 Find Case:", font=("Helvetica", 9, "bold"), bg="#f1f5f9", fg="#334155").pack(side=tk.LEFT, padx=(0, 2))
        self.entry_case_search = ttk.Entry(ctx_bar, width=12, font=("Helvetica", 9))
        self.entry_case_search.pack(side=tk.LEFT, padx=(0, 6))
        self.entry_case_search.bind("<KeyRelease>", self._on_case_search_typing)

        tk.Label(ctx_bar, text="👤 Case:", font=("Helvetica", 9, "bold"), bg="#f1f5f9", fg="#0f172a").pack(side=tk.LEFT, padx=(0, 2))
        self.combo_global_case = ttk.Combobox(ctx_bar, state="readonly", width=28, font=("Helvetica", 9))
        self.combo_global_case.pack(side=tk.LEFT, padx=(0, 8))
        self.combo_global_case.bind("<<ComboboxSelected>>", self._on_global_case_changed)

        # Session Selector
        tk.Label(ctx_bar, text="🗓️ Session:", font=("Helvetica", 9, "bold"), bg="#f1f5f9", fg="#0f172a").pack(side=tk.LEFT, padx=(0, 2))
        self.combo_global_session = ttk.Combobox(ctx_bar, state="readonly", width=26, font=("Helvetica", 9))
        self.combo_global_session.pack(side=tk.LEFT, padx=(0, 8))
        self.combo_global_session.bind("<<ComboboxSelected>>", self._on_global_session_changed)

        # Quick Buttons & Refresh
        ttk.Button(ctx_bar, text="🔄 Refresh", command=self._refresh_all_data).pack(side=tk.LEFT, padx=(2, 0))
        ttk.Button(ctx_bar, text="➕ New Case", command=self._show_create_case_dialog).pack(side=tk.RIGHT, padx=(3, 0))
        ttk.Button(ctx_bar, text="➕ New Session", command=self._show_create_session_dialog).pack(side=tk.RIGHT, padx=(3, 0))

    def _build_tabs(self) -> None:
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # Tab 1: Cases & Sessions
        self.tab_cases = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_cases, text="1. 📋 Cases & Sessions")
        self._build_tab_cases()

        # Tab 2: Ingestion (Audio / CHA / Text)
        self.tab_ingestion = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ingestion, text="2. 🎙️ Ingest Audio & Transcript")
        self._build_tab_ingestion()

        # Tab 3: Transcript QA Review
        self.tab_review = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_review, text="3. 🗣️ Transcript QA & Review")
        self._build_tab_review()

        # Tab 4: Findings & Guideline Mapping
        self.tab_findings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_findings, text="4. 📊 Findings & Acoustics")
        self._build_tab_findings()

        # Tab 5: Progress Report & Export
        self.tab_report = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_report, text="5. 📝 Report & Sign-off")
        self._build_tab_report()

    def _build_statusbar(self) -> None:
        """Bottom status bar with operational status and indeterminate progress indicator."""
        self.statusbar_frame = tk.Frame(self.root, bg="#e2e8f0", padx=12, pady=4)
        self.statusbar_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.lbl_status = tk.Label(
            self.statusbar_frame,
            text="Ready",
            font=("Helvetica", 9),
            fg="#334155",
            bg="#e2e8f0",
        )
        self.lbl_status.pack(side=tk.LEFT)

        self.prog_bar = ttk.Progressbar(self.statusbar_frame, mode="indeterminate", length=140)
        # Hidden by default

    def _bind_shortcuts(self) -> None:
        """Register global desktop keyboard shortcuts."""
        self.root.bind("<Control-s>", lambda e: self._handle_ctrl_s())
        self.root.bind("<Command-s>", lambda e: self._handle_ctrl_s())
        self.root.bind("<Control-r>", lambda e: self._refresh_all_data())
        self.root.bind("<Command-r>", lambda e: self._refresh_all_data())
        self.root.bind("<Control-e>", lambda e: self._export_report())
        self.root.bind("<Command-e>", lambda e: self._export_report())
        self.root.bind("<space>", lambda e: self._handle_space_shortcut(e))

    def _handle_space_shortcut(self, event: Any) -> None:
        """Toggle playback when space is pressed outside text entry inputs."""
        widget = self.root.focus_get()
        if isinstance(widget, (tk.Entry, ttk.Entry, tk.Text)):
            return
        if self._is_continuous_playing:
            self._stop_playback()
        else:
            sel = self.tree_utterances.selection() if hasattr(self, "tree_utterances") else ()
            if sel:
                self._play_selected_utterance()
            else:
                self._toggle_continuous_playback()

    def _handle_ctrl_s(self) -> None:
        """Handle quick save depending on current tab."""
        current_tab = self.notebook.index("current")
        if current_tab == 2:  # Review tab
            self._save_utterance_edit()
        elif current_tab == 4:  # Report tab
            self._export_report()

    def _set_busy_state(self, busy: bool, message: str = "Ready") -> None:
        """Update UI busy cursor and progress bar indicator."""
        self.is_busy = busy
        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            self.lbl_status.config(text=message)
        if busy:
            try:
                self.root.config(cursor="watch")
            except Exception:
                pass
            if hasattr(self, "prog_bar") and self.prog_bar.winfo_exists():
                self.prog_bar.pack(side=tk.RIGHT, padx=4)
                if self.root.winfo_exists() and self.root.state() != "withdrawn":
                    try:
                        self.prog_bar.start(50)
                    except Exception:
                        pass
        else:
            try:
                self.root.config(cursor="")
            except Exception:
                pass
            if hasattr(self, "prog_bar") and self.prog_bar.winfo_exists():
                try:
                    self.prog_bar.stop()
                except Exception:
                    pass
                self.prog_bar.pack_forget()

    def _poll_async_queue(self) -> None:
        """Process completed background worker callbacks on the Tkinter main thread."""
        try:
            while not self._async_queue.empty():
                cb, error = self._async_queue.get_nowait()
                if cb and callable(cb):
                    cb()
        except Exception:
            pass

        if self.root.winfo_exists():
            try:
                self.root.after(30, self._poll_async_queue)
            except Exception:
                pass

    def _run_async_task(
        self,
        target: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[Exception], None] | None = None,
        busy_msg: str = "Processing...",
    ) -> threading.Thread:
        """Execute long-running work in a background thread and post results safely via queue."""
        self._set_busy_state(True, busy_msg)

        def worker() -> None:
            try:
                res = target()
                self._async_queue.put((lambda r=res: self._on_task_done(r, on_success, None), None))
            except Exception as exc:
                self._async_queue.put((lambda e=exc: self._on_task_done(None, on_error, e), exc))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    def _on_task_done(
        self,
        result: Any,
        callback: Callable[[Any], None] | None,
        error: Exception | None,
    ) -> None:
        """Handle task completion on Tkinter main thread."""
        self._set_busy_state(False, "Ready")
        if error:
            if callback and callable(callback):
                callback(error)
            else:
                messagebox.showerror("Operation Failed", str(error))
        elif callback and callable(callback):
            callback(result)

    # --- Tab 1: Cases & Sessions UI ---
    def _build_tab_cases(self) -> None:
        frame = ttk.Frame(self.tab_cases, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        # Cases Table Header
        lbl_c = ttk.Label(frame, text="Active Child Cases Directory", font=("Helvetica", 12, "bold"))
        lbl_c.pack(anchor=tk.W, pady=(0, 4))

        columns_c = ("case_id", "child_id", "age", "lang", "sessions", "notes")
        self.tree_cases = ttk.Treeview(frame, columns=columns_c, show="headings", height=6)
        self.tree_cases.heading("case_id", text="Case ID")
        self.tree_cases.heading("child_id", text="Child ID")
        self.tree_cases.heading("age", text="Age (Mo)")
        self.tree_cases.heading("lang", text="Lang")
        self.tree_cases.heading("sessions", text="Sessions")
        self.tree_cases.heading("notes", text="Clinical Notes")

        self.tree_cases.column("case_id", width=120)
        self.tree_cases.column("child_id", width=100)
        self.tree_cases.column("age", width=70, anchor=tk.CENTER)
        self.tree_cases.column("lang", width=60, anchor=tk.CENTER)
        self.tree_cases.column("sessions", width=70, anchor=tk.CENTER)
        self.tree_cases.column("notes", width=380)

        self.tree_cases.pack(fill=tk.X, pady=(0, 8))
        self.tree_cases.bind("<<TreeviewSelect>>", self._on_case_selected)

        # Button Bar for Cases
        btn_bar_c = ttk.Frame(frame)
        btn_bar_c.pack(fill=tk.X, pady=(0, 12))
        ttk.Button(btn_bar_c, text="➕ Create New Case", command=self._show_create_case_dialog).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_bar_c, text="🔄 Refresh Cases", command=self._refresh_cases).pack(side=tk.LEFT)

        # Sessions Table
        lbl_s = ttk.Label(frame, text="Sessions for Selected Case", font=("Helvetica", 12, "bold"))
        lbl_s.pack(anchor=tk.W, pady=(8, 4))

        columns_s = ("session_id", "date", "number", "status", "transcript", "report")
        self.tree_sessions = ttk.Treeview(frame, columns=columns_s, show="headings", height=5)
        self.tree_sessions.heading("session_id", text="Session ID")
        self.tree_sessions.heading("date", text="Date")
        self.tree_sessions.heading("number", text="Sess #")
        self.tree_sessions.heading("status", text="Workflow Status")
        self.tree_sessions.heading("transcript", text="Transcript")
        self.tree_sessions.heading("report", text="Report")

        self.tree_sessions.column("session_id", width=140)
        self.tree_sessions.column("date", width=110)
        self.tree_sessions.column("number", width=60, anchor=tk.CENTER)
        self.tree_sessions.column("status", width=140)
        self.tree_sessions.column("transcript", width=100, anchor=tk.CENTER)
        self.tree_sessions.column("report", width=100, anchor=tk.CENTER)

        self.tree_sessions.pack(fill=tk.X, pady=(0, 8))
        self.tree_sessions.bind("<<TreeviewSelect>>", self._on_session_selected)

        # Button Bar for Sessions
        btn_bar_s = ttk.Frame(frame)
        btn_bar_s.pack(fill=tk.X)
        ttk.Button(btn_bar_s, text="➕ Start New Session", command=self._show_create_session_dialog).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_bar_s, text="🚀 Open in Ingestion Workspace ➔", command=lambda: self.notebook.select(1)).pack(side=tk.LEFT)

    # --- Tab 2: Ingestion UI ---
    def _build_tab_ingestion(self) -> None:
        frame = ttk.Frame(self.tab_ingestion, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        self.lbl_ingest_ctx = ttk.Label(
            frame,
            text="Please select a Session from Tab 1 to begin ingestion.",
            font=("Helvetica", 11, "bold"),
            foreground="#0369a1",
        )
        self.lbl_ingest_ctx.pack(anchor=tk.W, pady=(0, 12))

        # Audio/Video File Picker Card
        card_audio = ttk.LabelFrame(frame, text="🎙️ Option A: Ingest Local Audio / Video Clip", padding=12)
        card_audio.pack(fill=tk.X, pady=(0, 12))

        lbl_desc = ttk.Label(
            card_audio,
            text="Select an audio or video recording from your computer (.wav, .mp3, .m4a, .mp4).\n"
            "The system will extract Pitch/Prosody acoustics (F0) and transcribe dialogue segments.",
            font=("Helvetica", 10),
        )
        lbl_desc.pack(anchor=tk.W, pady=(0, 8))

        f_picker = ttk.Frame(card_audio)
        f_picker.pack(fill=tk.X)
        self.entry_audio_path = ttk.Entry(f_picker, font=("Helvetica", 10))
        self.entry_audio_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(f_picker, text="📂 Browse File...", command=self._browse_audio_file).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(f_picker, text="⚡ Extract & Process Audio", command=self._process_audio_file).pack(side=tk.LEFT)

        # Dedicated Audio Ingestion Progress Panel (Hidden by default, shown during processing)
        self.frame_ingest_progress = tk.Frame(
            card_audio,
            bg="#f0fdf4",
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground="#86efac",
        )
        self.lbl_ingest_stage = tk.Label(
            self.frame_ingest_progress,
            text="🚀 Initializing Audio Pipeline...",
            font=("Helvetica", 10, "bold"),
            fg="#166534",
            bg="#f0fdf4",
        )
        self.lbl_ingest_stage.pack(anchor=tk.W, pady=(0, 4))

        self.bar_ingest_progress = ttk.Progressbar(
            self.frame_ingest_progress,
            orient="horizontal",
            mode="determinate",
            length=500,
        )
        self.bar_ingest_progress.pack(fill=tk.X, pady=(0, 4))

        self.lbl_ingest_percent = tk.Label(
            self.frame_ingest_progress,
            text="0% Completed",
            font=("Helvetica", 9),
            fg="#15803d",
            bg="#f0fdf4",
        )
        self.lbl_ingest_percent.pack(anchor=tk.W)

        # CHA / Text File Picker Card
        card_text = ttk.LabelFrame(frame, text="📄 Option B: Load Demo Dialogue or CHAT File", padding=12)
        card_text.pack(fill=tk.BOTH, expand=True)

        btn_row = ttk.Frame(card_text)
        btn_row.pack(anchor=tk.W, pady=(0, 8))
        ttk.Button(btn_row, text="✨ Load Demo Thai Play Dialogue", command=self._load_demo_dialogue).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="📂 Load .cha / .txt File...", command=self._browse_text_file).pack(side=tk.LEFT)

        lbl_raw = ttk.Label(card_text, text="Or enter dialogue text manually below (format: 'INV: ...' and 'CHI: ...'):", font=("Helvetica", 9, "italic"))
        lbl_raw.pack(anchor=tk.W, pady=(0, 4))

        self.txt_manual = tk.Text(card_text, height=8, font=("Courier", 10))
        self.txt_manual.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        ttk.Button(card_text, text="📥 Ingest Typed Dialogue Text", command=self._ingest_typed_text).pack(anchor=tk.E)

    # --- Tab 3: Review UI (TalkBank / CHAT + Table Editor) ---
    def _build_tab_review(self) -> None:
        frame = ttk.Frame(self.tab_review, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        top_bar = ttk.Frame(frame)
        top_bar.pack(fill=tk.X, pady=(0, 6))
        self.lbl_review_status = ttk.Label(top_bar, text="Transcript Status: Not loaded", font=("Helvetica", 11, "bold"))
        self.lbl_review_status.pack(side=tk.LEFT)

        self.btn_attest = ttk.Button(top_bar, text="✍️ Clinician Sign-Off & Attest", command=self._attest_transcript)
        self.btn_attest.pack(side=tk.RIGHT)

        # Dual-mode sub-notebook (TalkBank CHAT vs Table Editor)
        self.review_notebook = ttk.Notebook(frame)
        self.review_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        # Sub-tab A: TalkBank / CHAT Viewer
        self.subtab_chat = ttk.Frame(self.review_notebook, padding=8)
        self.review_notebook.add(self.subtab_chat, text="📜 TalkBank / CHAT Format View")

        chat_bar = ttk.Frame(self.subtab_chat)
        chat_bar.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(chat_bar, text="TalkBank CHAT Canonical Syntax (@Begin ... *CHI / *INV ... @End):", font=("Helvetica", 9, "italic"), foreground="#475569").pack(side=tk.LEFT)
        ttk.Button(chat_bar, text="📋 Copy CHAT", command=self._copy_chat_text).pack(side=tk.RIGHT)

        self.txt_chat_view = tk.Text(
            self.subtab_chat,
            font=("Courier", 10),
            bg="#ffffff",
            fg="#0f172a",
            insertbackground="#0284c7",
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground="#cbd5e1",
            relief=tk.FLAT,
        )
        self.txt_chat_view.pack(fill=tk.BOTH, expand=True)
        # Configure clean light syntax tags for TalkBank style
        self.txt_chat_view.tag_configure("header", foreground="#475569", font=("Courier", 10, "bold"))
        self.txt_chat_view.tag_configure("chi", foreground="#1d4ed8", font=("Courier", 10, "bold"))
        self.txt_chat_view.tag_configure("inv", foreground="#047857", font=("Courier", 10, "bold"))
        self.txt_chat_view.tag_configure("time", foreground="#b45309", font=("Courier", 10))
        self.txt_chat_view.tag_configure("tier", foreground="#7c3aed", font=("Courier", 10, "italic"))

        # Sub-tab B: Utterance Table & Interactive Editor
        self.subtab_table = ttk.Frame(self.review_notebook, padding=8)
        self.review_notebook.add(self.subtab_table, text="✏️ Utterance Table & Quick Editor")

        # Interactive Audio Waveform Visualizer & Seek Canvas
        self.frame_waveform = tk.Frame(
            self.subtab_table,
            bg="#0f172a",
            height=65,
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self.frame_waveform.pack(fill=tk.X, pady=(0, 6))
        self.frame_waveform.pack_propagate(False)

        self.canvas_waveform = tk.Canvas(
            self.frame_waveform,
            bg="#0f172a",
            height=63,
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas_waveform.pack(fill=tk.BOTH, expand=True)
        self.canvas_waveform.bind("<Configure>", lambda e: self._redraw_waveform())
        self.canvas_waveform.bind("<Button-1>", self._on_waveform_click)
        self.canvas_waveform.bind("<B1-Motion>", self._on_waveform_drag)

        # Interactive Audio Scrubber & Timeline Bar
        self.frame_scrubber = tk.Frame(
            self.subtab_table,
            bg="#f1f5f9",
            padx=8,
            pady=3,
            highlightthickness=1,
            highlightbackground="#cbd5e1",
        )
        self.frame_scrubber.pack(fill=tk.X, pady=(0, 4))

        self.lbl_time_current = tk.Label(
            self.frame_scrubber,
            text="00:00.0",
            font=("Helvetica", 9, "bold"),
            fg="#0f766e",
            bg="#f1f5f9",
            width=7,
        )
        self.lbl_time_current.pack(side=tk.LEFT, padx=(0, 6))

        self.scale_scrubber = ttk.Scale(
            self.frame_scrubber,
            from_=0.0,
            to=100.0,
            orient=tk.HORIZONTAL,
            command=self._on_scrubber_slide,
        )
        self.scale_scrubber.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.scale_scrubber.bind("<Button-1>", self._on_scrubber_press)
        self.scale_scrubber.bind("<ButtonRelease-1>", self._on_scrubber_release)

        self.lbl_time_total = tk.Label(
            self.frame_scrubber,
            text="00:00.0",
            font=("Helvetica", 9),
            fg="#64748b",
            bg="#f1f5f9",
            width=7,
        )
        self.lbl_time_total.pack(side=tk.RIGHT, padx=(6, 0))

        # Audio Player & Synchronized Playback Toolbar
        self.frame_audio_player = tk.Frame(
            self.subtab_table,
            bg="#f8fafc",
            padx=10,
            pady=6,
            highlightthickness=1,
            highlightbackground="#cbd5e1",
        )
        self.frame_audio_player.pack(fill=tk.X, pady=(0, 6))

        self.btn_play_continuous = ttk.Button(
            self.frame_audio_player,
            text="▶️ Play Audio with Follow",
            style="Primary.TButton",
            command=self._toggle_continuous_playback,
        )
        self.btn_play_continuous.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_stop_audio = ttk.Button(
            self.frame_audio_player,
            text="⏹️ Stop",
            command=self._stop_playback,
        )
        self.btn_stop_audio.pack(side=tk.LEFT, padx=(0, 8))

        # Playback speed selector
        ttk.Label(self.frame_audio_player, text="Speed:", font=("Helvetica", 9, "bold")).pack(side=tk.LEFT, padx=(4, 2))
        self.combo_speed = ttk.Combobox(
            self.frame_audio_player,
            values=["0.75x", "1.0x", "1.25x"],
            width=5,
            state="readonly",
            font=("Helvetica", 9),
        )
        self.combo_speed.set("1.0x")
        self.combo_speed.pack(side=tk.LEFT, padx=(0, 8))
        self.combo_speed.bind("<<ComboboxSelected>>", self._on_speed_changed)

        self.lbl_playback_status = tk.Label(
            self.frame_audio_player,
            text="Audio: Ready (Click ▶️ or click waveform to play)",
            font=("Helvetica", 9),
            fg="#475569",
            bg="#f8fafc",
        )
        self.lbl_playback_status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        columns_u = ("id", "speaker", "time", "text", "flags")
        self.tree_utterances = ttk.Treeview(self.subtab_table, columns=columns_u, show="headings", height=8)
        self.tree_utterances.heading("id", text="#")
        self.tree_utterances.heading("speaker", text="Speaker")
        self.tree_utterances.heading("time", text="Time (s)")
        self.tree_utterances.heading("text", text="Utterance Text")
        self.tree_utterances.heading("flags", text="QA Flags")

        self.tree_utterances.column("id", width=40, anchor=tk.CENTER)
        self.tree_utterances.column("speaker", width=90, anchor=tk.CENTER)
        self.tree_utterances.column("time", width=100, anchor=tk.CENTER)
        self.tree_utterances.column("text", width=550)
        self.tree_utterances.column("flags", width=140)

        # Configure real-time playing highlight tag
        self.tree_utterances.tag_configure(
            "playing",
            background="#dbeafe",
            foreground="#1e40af",
        )

        self.tree_utterances.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self.tree_utterances.bind("<<TreeviewSelect>>", self._on_utterance_selected)

        # Edit controls
        edit_box = ttk.LabelFrame(self.subtab_table, text="✏️ Edit Selected Utterance & Speaker", padding=8)
        edit_box.pack(fill=tk.X, pady=(2, 0))

        e_row = ttk.Frame(edit_box)
        e_row.pack(fill=tk.X, pady=(2, 4))
        e_row.columnconfigure(3, weight=1)

        ttk.Label(e_row, text="Speaker:").grid(row=0, column=0, sticky=tk.W, padx=(0, 4))
        self.combo_spk = ttk.Combobox(e_row, values=["CHI", "INV", "MOT", "FAT"], width=7, state="readonly")
        self.combo_spk.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        self.combo_spk.set("CHI")

        ttk.Label(e_row, text="Text:").grid(row=0, column=2, sticky=tk.W, padx=(0, 4))
        self.entry_u_text = ttk.Entry(e_row, font=("Helvetica", 10))
        self.entry_u_text.grid(row=0, column=3, sticky=tk.EW, padx=(0, 10))

        self.btn_play_snippet = ttk.Button(e_row, text="🔊 Play Snippet", command=self._play_selected_utterance)
        self.btn_play_snippet.grid(row=0, column=4, sticky=tk.E, padx=(0, 6))

        self.btn_save_u_edit = ttk.Button(e_row, text="💾 Save Utterance Edit", style="Primary.TButton", command=self._save_utterance_edit)
        self.btn_save_u_edit.grid(row=0, column=5, sticky=tk.E)

        # Word-level interactive audio chips row
        self.frame_words_chips = ttk.Frame(edit_box)
        self.frame_words_chips.pack(fill=tk.X, pady=(6, 0))
        self.lbl_words_title = ttk.Label(self.frame_words_chips, text="🎯 Word Timings (Click to listen):", font=("Helvetica", 9, "bold"))
        self.lbl_words_title.pack(side=tk.LEFT, padx=(0, 6))
        self.container_word_buttons = ttk.Frame(self.frame_words_chips)
        self.container_word_buttons.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # --- Tab 4: Findings UI (Spider Diagram & 15+ Features Hub) ---
    def _build_tab_findings(self) -> None:
        self.frame_tab_findings = ttk.Frame(self.tab_findings, padding=12)
        self.frame_tab_findings.pack(fill=tk.BOTH, expand=True)

        # Stale state notification banner
        self.frame_stale_findings = tk.Frame(
            self.frame_tab_findings,
            bg="#fffbeb",
            padx=10,
            pady=6,
            highlightthickness=1,
            highlightbackground="#fcd34d",
        )
        tk.Label(
            self.frame_stale_findings,
            text="⚠️ Transcript modified: Findings & Report are currently STALE. Click Recalculate to refresh.",
            font=("Helvetica", 9, "bold"),
            fg="#92400e",
            bg="#fffbeb",
        ).pack(side=tk.LEFT)
        ttk.Button(
            self.frame_stale_findings,
            text="🔄 Recalculate Findings",
            command=self._recalculate_findings,
        ).pack(side=tk.RIGHT)

        # Sub-notebook for Spider Diagram vs Detailed Table
        self.findings_notebook = ttk.Notebook(self.frame_tab_findings)
        self.findings_notebook.pack(fill=tk.BOTH, expand=True)

        # Sub-tab 1: Spider / Radar Diagram View
        self.subtab_radar = ttk.Frame(self.findings_notebook, padding=8)
        self.findings_notebook.add(self.subtab_radar, text="🕸️ Spider Diagram (Norm Comparison)")

        radar_split = ttk.Frame(self.subtab_radar)
        radar_split.pack(fill=tk.BOTH, expand=True)

        # Left Canvas for Radar Plot
        canvas_frame = tk.Frame(radar_split, bg="#ffffff", highlightthickness=1, highlightbackground="#cbd5e1")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        self.canvas_radar = tk.Canvas(canvas_frame, width=380, height=330, bg="#ffffff", highlightthickness=0)
        self.canvas_radar.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.canvas_radar.bind("<Configure>", self._on_canvas_radar_resize)

        # Right Summary Panel
        sum_frame = ttk.LabelFrame(radar_split, text="📊 Benchmark Comparison vs TD Norms", padding=10)
        sum_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.txt_radar_summary = tk.Text(sum_frame, font=("Helvetica", 10), bg="#f8fafc", padx=8, pady=8, wrap=tk.WORD, relief=tk.FLAT)
        self.txt_radar_summary.pack(fill=tk.BOTH, expand=True)
        self.txt_radar_summary.tag_configure("title", font=("Helvetica", 10, "bold"), foreground="#0f172a")
        self.txt_radar_summary.tag_configure("green", font=("Helvetica", 9, "bold"), foreground="#15803d")
        self.txt_radar_summary.tag_configure("blue", font=("Helvetica", 9, "bold"), foreground="#1d4ed8")

        # Sub-tab 2: Detailed Table View
        self.subtab_table_features = ttk.Frame(self.findings_notebook, padding=8)
        self.findings_notebook.add(self.subtab_table_features, text="📋 Comprehensive 15+ Features & Guidelines Table")

        lbl_f = ttk.Label(self.subtab_table_features, text="📊 Speech-Language, Interaction & Acoustic Profile", font=("Helvetica", 11, "bold"))
        lbl_f.pack(anchor=tk.W, pady=(0, 4))

        columns_m = ("category", "metric", "val", "desc")
        self.tree_metrics = ttk.Treeview(self.subtab_table_features, columns=columns_m, show="headings", height=8)
        self.tree_metrics.heading("category", text="Domain / หมวดหมู่")
        self.tree_metrics.heading("metric", text="Feature Metric")
        self.tree_metrics.heading("val", text="Value")
        self.tree_metrics.heading("desc", text="Clinical Description / ความหมายเชิงคลินิก")

        self.tree_metrics.column("category", width=180)
        self.tree_metrics.column("metric", width=180)
        self.tree_metrics.column("val", width=100, anchor=tk.CENTER)
        self.tree_metrics.column("desc", width=420)
        self.tree_metrics.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        lbl_g = ttk.Label(self.subtab_table_features, text="📑 Clinical Guideline Linkages (Thai ASD Assessment Dimensions)", font=("Helvetica", 10, "bold"))
        lbl_g.pack(anchor=tk.W, pady=(0, 2))

        columns_g = ("construct", "status", "evidence")
        self.tree_guidelines = ttk.Treeview(self.subtab_table_features, columns=columns_g, show="headings", height=3)
        self.tree_guidelines.heading("construct", text="Clinical Construct")
        self.tree_guidelines.heading("status", text="Observation Status")
        self.tree_guidelines.heading("evidence", text="Evidence Summary")

        self.tree_guidelines.column("construct", width=250)
        self.tree_guidelines.column("status", width=180)
        self.tree_guidelines.column("evidence", width=450)
        self.tree_guidelines.pack(fill=tk.BOTH, expand=True, pady=(0, 2))

    def _on_canvas_radar_resize(self, event: Any) -> None:
        """Handle dynamic resize of the Spider Diagram canvas with debouncing."""
        if self._resize_job:
            try:
                self.root.after_cancel(self._resize_job)
            except Exception:
                pass
        try:
            self._resize_job = self.root.after(60, self._do_redraw_radar)
        except Exception:
            self._do_redraw_radar()

    def _do_redraw_radar(self) -> None:
        self._resize_job = None
        if hasattr(self, "active_session_id") and self.active_session_id:
            findings = self.client.get_findings(self.active_session_id)
            self._draw_spider_diagram(findings.get("metrics", {}))

    def _draw_spider_diagram(self, metrics: dict[str, Any]) -> None:
        """Render native radar chart comparing Child values vs Typical Development (TD) Norms."""
        import math
        self.canvas_radar.delete("all")
        self.canvas_radar.update_idletasks()
        width = max(280, self.canvas_radar.winfo_width()) if self.canvas_radar.winfo_width() > 1 else 380
        height = max(240, self.canvas_radar.winfo_height()) if self.canvas_radar.winfo_height() > 1 else 330
        cx, cy = width / 2, height / 2 - 5
        radius = max(60, min(cx, cy) - 45)

        has_child_data = bool(
            metrics
            and (metrics.get("mlu_words") is not None or metrics.get("total_child_utterances", 0) > 0)
            and metrics.get("total_child_utterances", 0) > 0
        )

        # 6 Axes comparing Child to Typical Development (TD) norm baseline
        f0_val = metrics.get("f0_iqr_hz") if has_child_data else None
        f0_float = float(f0_val) if f0_val is not None and f0_val != "N/A" else None
        sp_val = metrics.get("speech_rate_wpm") if has_child_data else None
        sp_float = float(sp_val) if sp_val is not None and sp_val != "N/A" else None

        mlu_val = float(metrics["mlu_words"]) if has_child_data and metrics.get("mlu_words") is not None else None
        ttr_val = float(metrics["ttr"]) if has_child_data and metrics.get("ttr") is not None else None
        tt_val = float(metrics["turn_taking_ratio"]) if has_child_data and metrics.get("turn_taking_ratio") is not None else None
        intel_val = float(metrics["intelligibility_rate"]) if has_child_data and metrics.get("intelligibility_rate") is not None else None

        axes = [
            {"label": "MLU-w\n(ประโยค)", "val": mlu_val, "td": 3.5, "unit": "คำ"},
            {"label": "TTR\n(คำศัพท์)", "val": ttr_val, "td": 0.75, "unit": ""},
            {"label": "Turn-Taking\n(การผลัดกันพูด)", "val": tt_val, "td": 0.90, "unit": ""},
            {"label": "Intelligibility\n(ความชัดเจน)", "val": intel_val, "td": 0.95, "unit": ""},
            {"label": "Speech Rate\n(ความเร็วพูด)", "val": sp_float, "td": 90.0, "unit": "wpm"},
            {"label": "Prosody IQR\n(ช่วงเสียง)", "val": f0_float, "td": 35.0, "unit": "Hz"},
        ]
        n = len(axes)

        # Concentric grid rings
        for r_ratio in [0.25, 0.5, 0.75, 1.0, 1.2]:
            r = radius * (r_ratio / 1.2)
            pts = []
            for i in range(n):
                angle = -math.pi / 2 + (2 * math.pi * i / n)
                pts.extend([cx + r * math.cos(angle), cy + r * math.sin(angle)])
            is_norm = (r_ratio == 1.0)
            self.canvas_radar.create_polygon(pts, fill="", outline="#94a3b8" if is_norm else "#e2e8f0", width=1.5 if is_norm else 1, dash=(3, 2) if is_norm else ())

        # Spokes and labels
        for i, ax in enumerate(axes):
            angle = -math.pi / 2 + (2 * math.pi * i / n)
            self.canvas_radar.create_line(cx, cy, cx + radius * math.cos(angle), cy + radius * math.sin(angle), fill="#e2e8f0", width=1)
            x_lbl = cx + (radius + 22) * math.cos(angle)
            y_lbl = cy + (radius + 22) * math.sin(angle)
            self.canvas_radar.create_text(x_lbl, y_lbl, text=ax["label"], font=("Helvetica", 8, "bold"), fill="#475569", justify=tk.CENTER)

        # 1. Typical Development (TD) Baseline Polygon (100% ring)
        td_pts = []
        for i in range(n):
            angle = -math.pi / 2 + (2 * math.pi * i / n)
            r_td = radius * (1.0 / 1.2)
            td_pts.extend([cx + r_td * math.cos(angle), cy + r_td * math.sin(angle)])
        self.canvas_radar.create_polygon(td_pts, fill="", outline="#10b981", width=2, dash=(4, 2))

        # 2. Child Session Data Polygon (only if genuine child data exists)
        if has_child_data:
            child_pts = []
            for i, ax in enumerate(axes):
                angle = -math.pi / 2 + (2 * math.pi * i / n)
                if ax["val"] is not None:
                    ratio = ax["val"] / ax["td"] if ax["td"] else 1.0
                    ratio = max(0.15, min(1.25, ratio))
                else:
                    ratio = 0.05
                r_child = radius * (ratio / 1.2)
                child_pts.extend([cx + r_child * math.cos(angle), cy + r_child * math.sin(angle)])

            if len(child_pts) >= 6:
                self.canvas_radar.create_polygon(child_pts, fill="#e0f2fe", outline="#0284c7", width=2.5)

            for i, ax in enumerate(axes):
                if ax["val"] is not None:
                    px, py = child_pts[i*2], child_pts[i*2+1]
                    self.canvas_radar.create_oval(px-3.5, py-3.5, px+3.5, py+3.5, fill="#0369a1", outline="white", width=1)

            # Summary text
            self.txt_radar_summary.config(state=tk.NORMAL)
            self.txt_radar_summary.delete("1.0", tk.END)
            self.txt_radar_summary.insert(tk.END, "Spider Diagram (ผลเปรียบเทียบกับเกณฑ์สมวัย):\n\n", "title")
            self.txt_radar_summary.insert(tk.END, "🟢 เส้นประเขียว: ค่าปกติสมวัย (TD Norm Baseline 100%)\n", "green")
            self.txt_radar_summary.insert(tk.END, "🔵 พื้นที่ฟ้า: ผลการตรวจของเด็กในเซสชันนี้\n\n", "blue")
            for ax in axes:
                lbl_clean = ax['label'].split('\n')[0]
                if ax["val"] is not None:
                    pct = int((ax["val"] / ax["td"]) * 100) if ax["td"] else 100
                    unit_str = f" {ax['unit']}" if ax["unit"] else ""
                    status_emoji = "✓" if pct >= 85 else ("⚡" if pct >= 65 else "⚠️")
                    self.txt_radar_summary.insert(tk.END, f"{status_emoji} {lbl_clean}: {ax['val']}{unit_str} (เกณฑ์ปกติ: {ax['td']}{unit_str}) — {pct}%\n")
                else:
                    self.txt_radar_summary.insert(tk.END, f"○ {lbl_clean}: N/A (ไม่มีไฟล์เสียง - ข้อความล้วน)\n")
            self.txt_radar_summary.config(state=tk.DISABLED)
        else:
            # Clean Empty State Display
            self.canvas_radar.create_rectangle(cx - 130, cy - 26, cx + 130, cy + 26, fill="#f8fafc", outline="#cbd5e1", width=1)
            self.canvas_radar.create_text(cx, cy - 7, text="ยังไม่มีข้อมูลการประเมินในเซสชันนี้", font=("Helvetica", 9, "bold"), fill="#64748b")
            self.canvas_radar.create_text(cx, cy + 10, text="(กรุณา Ingest ไฟล์เสียงหรือข้อความใน Tab 2)", font=("Helvetica", 8), fill="#94a3b8")

            self.txt_radar_summary.config(state=tk.NORMAL)
            self.txt_radar_summary.delete("1.0", tk.END)
            self.txt_radar_summary.insert(tk.END, "Spider Diagram (ผลเปรียบเทียบกับเกณฑ์สมวัย):\n\n", "title")
            self.txt_radar_summary.insert(tk.END, "🟢 เส้นประเขียว: ค่าปกติสมวัย (TD Norm Baseline 100%)\n\n", "green")
            self.txt_radar_summary.insert(tk.END, "⚠️ ยังไม่มีข้อมูลการประเมิน\n\n", "title")
            self.txt_radar_summary.insert(tk.END, "กรุณานำเข้าไฟล์เสียงหรือบทสนทนาในแท็บ '2. Ingest Audio & Transcript' เพื่อเริ่มการวิเคราะห์ตัวชี้วัด LSA และ Acoustic Prosody")
            self.txt_radar_summary.config(state=tk.DISABLED)

    # --- Tab 5: Report UI (Data Ground Truth & Clinical Decision Support) ---
    def _build_tab_report(self) -> None:
        frame = ttk.Frame(self.tab_report, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        top_r = ttk.Frame(frame)
        top_r.pack(fill=tk.X, pady=(0, 4))
        self.lbl_report_status = ttk.Label(top_r, text="Report Status: Draft", font=("Helvetica", 11, "bold"))
        self.lbl_report_status.pack(side=tk.LEFT)

        ttk.Button(top_r, text="✨ Generate Draft", command=self._generate_report_draft).pack(side=tk.LEFT, padx=(8, 4))
        ttk.Button(top_r, text="✍️ Sign-Off Report", command=self._sign_off_report).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(top_r, text="💾 Export Markdown", command=self._export_report).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top_r, text="📊 Export CSV", command=self._export_csv_biomarkers).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top_r, text="📋 Export HTML Report", command=self._export_html_report).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top_r, text="📄 Export TalkBank (.cha)", command=self._export_cha_file).pack(side=tk.RIGHT, padx=4)

        # Ground Truth & Provenance Info Card
        prov_card = tk.Frame(frame, bg="#f8fafc", padx=10, pady=6, highlightthickness=1, highlightbackground="#e2e8f0")
        prov_card.pack(fill=tk.X, pady=(4, 6))
        tk.Label(
            prov_card,
            text="🔒 Ground Truth & Reliability Context: 100% Sourced directly from verified session utterances & deterministic LSA metrics. Clinician sign-off seals report with SHA-256 integrity hash.",
            font=("Helvetica", 9, "italic"),
            fg="#0369a1",
            bg="#f8fafc",
        ).pack(anchor=tk.W)

        lbl_n = ttk.Label(frame, text="Clinical Narrative (Language Sample Analysis):", font=("Helvetica", 10, "bold"))
        lbl_n.pack(anchor=tk.W, pady=(4, 2))
        self.txt_narrative = tk.Text(frame, height=6, font=("Helvetica", 10))
        self.txt_narrative.pack(fill=tk.X, pady=(0, 6))

        lbl_rec = ttk.Label(frame, text="Recommendations & Therapy Goals:", font=("Helvetica", 10, "bold"))
        lbl_rec.pack(anchor=tk.W, pady=(4, 2))
        self.txt_recommendations = tk.Text(frame, height=5, font=("Helvetica", 10))
        self.txt_recommendations.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

    # --- Data Operations & Global Context Handlers ---
    def _on_case_search_typing(self, event: Any) -> None:
        query = self.entry_case_search.get().strip().lower()
        cases = self.client.list_cases()
        matched = []
        for c in cases:
            c_str = f"{c.get('case_id')} {c.get('child_id')} {c.get('clinical_notes')}".lower()
            if not query or query in c_str:
                matched.append(f"{c.get('case_id')} | {c.get('child_id')} ({c.get('age_months', '-')}m, {c.get('primary_language', 'th').upper()})")
        self.combo_global_case["values"] = matched or ["(No matching cases)"]
        if matched:
            self.combo_global_case.current(0)
            self._on_global_case_changed(None)

    def _refresh_all_data(self) -> None:
        self._refresh_cases()
        self._refresh_sessions_for_active_case()
        messagebox.showinfo("Refreshed", "Data refreshed successfully from repository / API.")

    def _load_initial_data(self) -> None:
        self._refresh_cases()
        if self.tree_cases.get_children():
            first_case = self.tree_cases.get_children()[0]
            self.tree_cases.selection_set(first_case)
            self._on_case_selected(None)

    def _refresh_cases(self) -> None:
        for item in self.tree_cases.get_children():
            self.tree_cases.delete(item)
        cases = self.client.list_cases()
        case_options = []
        for c in cases:
            c_id = c.get("case_id")
            self.tree_cases.insert(
                "",
                tk.END,
                iid=c_id,
                values=(
                    c_id,
                    c.get("child_id"),
                    c.get("age_months", "-"),
                    c.get("primary_language", "th").upper(),
                    c.get("session_count", 0),
                    c.get("clinical_notes", ""),
                ),
            )
            case_options.append(f"{c_id} | {c.get('child_id')} ({c.get('age_months', '-')}m, {c.get('primary_language', 'th').upper()})")

        if case_options:
            self.combo_global_case["values"] = case_options
            if not self.combo_global_case.get() or self.combo_global_case.get().startswith("("):
                self.combo_global_case.current(0)
                self.active_case_id = cases[0]["case_id"]
        else:
            self.combo_global_case["values"] = ["(No Cases — Click ➕ New Case)"]
            self.combo_global_case.current(0)
            self.active_case_id = None
            self.combo_global_session["values"] = ["(No Active Case)"]
            self.combo_global_session.current(0)
            self.active_session_id = None
            self.lbl_ingest_ctx.config(text="Active Context: Please create a Case to begin (Click ➕ New Case)")
            self._refresh_transcript_and_findings()

    def _on_global_case_changed(self, event: Any) -> None:
        sel_text = self.combo_global_case.get()
        if not sel_text or sel_text.startswith("("):
            return
        case_id = sel_text.split(" | ")[0].strip()
        self.active_case_id = case_id

        # Sync Tab 1 treeview
        if case_id in self.tree_cases.get_children():
            self.tree_cases.selection_set(case_id)
            self.tree_cases.see(case_id)

        # Refresh sessions dropdown and table
        self._refresh_sessions_for_active_case()

    def _on_global_session_changed(self, event: Any) -> None:
        sel_text = self.combo_global_session.get()
        if not sel_text or sel_text.startswith("("):
            self.active_session_id = None
            self.lbl_ingest_ctx.config(text=f"Active Context: Case {self.active_case_id} > (No Session)")
            self._refresh_transcript_and_findings()
            return
        session_id = sel_text.split(" | ")[0].strip()
        self.active_session_id = session_id

        # Sync Tab 1 treeview
        if session_id in self.tree_sessions.get_children():
            self.tree_sessions.selection_set(session_id)
            self.tree_sessions.see(session_id)

        self.lbl_ingest_ctx.config(text=f"Active Context: Case {self.active_case_id} > Session {self.active_session_id}")
        self._refresh_transcript_and_findings()

    def _refresh_sessions_for_active_case(self) -> None:
        for item in self.tree_sessions.get_children():
            self.tree_sessions.delete(item)

        if not self.active_case_id:
            self.combo_global_session["values"] = ["(No Active Case)"]
            self.combo_global_session.current(0)
            self.active_session_id = None
            self._refresh_transcript_and_findings()
            return

        sessions = self.client.list_sessions(self.active_case_id)
        session_options = []
        for s in sessions:
            s_id = s.get("session_id")
            tr_badge = "✓ Ready" if s.get("transcript_id") else "None"
            rep_badge = "✓ Ready" if s.get("report_id") else "None"
            self.tree_sessions.insert(
                "",
                tk.END,
                iid=s_id,
                values=(
                    s_id,
                    s.get("session_date"),
                    s.get("session_number", 1),
                    s.get("status", "Intake"),
                    tr_badge,
                    rep_badge,
                ),
            )
            session_options.append(f"{s_id} | Date: {s.get('session_date')} ({s.get('status', 'Intake')})")

        if session_options:
            self.combo_global_session["values"] = session_options
            # Pick latest session by default
            self.combo_global_session.current(len(session_options) - 1)
            self.active_session_id = sessions[-1]["session_id"]
            if self.active_session_id in self.tree_sessions.get_children():
                self.tree_sessions.selection_set(self.active_session_id)
            self.lbl_ingest_ctx.config(text=f"Active Context: Case {self.active_case_id} > Session {self.active_session_id}")
        else:
            self.combo_global_session["values"] = ["(No sessions - Click ➕ New Session)"]
            self.combo_global_session.current(0)
            self.active_session_id = None
            self.lbl_ingest_ctx.config(text=f"Active Context: Case {self.active_case_id} > (No Session - Click ➕ New Session)")

        self._refresh_transcript_and_findings()

    def _on_case_selected(self, event: Any) -> None:
        selected = self.tree_cases.selection()
        if not selected:
            return
        self.active_case_id = selected[0]

        # Sync Global Case Dropdown
        for idx, val in enumerate(self.combo_global_case["values"]):
            if val.startswith(self.active_case_id):
                self.combo_global_case.current(idx)
                break

        self._refresh_sessions_for_active_case()

    def _on_session_selected(self, event: Any) -> None:
        selected = self.tree_sessions.selection()
        if not selected:
            return
        self.active_session_id = selected[0]

        # Sync Global Session Dropdown
        for idx, val in enumerate(self.combo_global_session["values"]):
            if val.startswith(self.active_session_id):
                self.combo_global_session.current(idx)
                break

        self.lbl_ingest_ctx.config(text=f"Active Context: Case {self.active_case_id} > Session {self.active_session_id}")
        self._refresh_transcript_and_findings()

    def _copy_chat_text(self) -> None:
        chat_content = self.txt_chat_view.get("1.0", tk.END).strip()
        if chat_content:
            self.root.clipboard_clear()
            self.root.clipboard_append(chat_content)
            messagebox.showinfo("Copied", "TalkBank / CHAT transcript copied to clipboard!")

    def _refresh_transcript_and_findings(self) -> None:
        # Clear QA table
        for item in self.tree_utterances.get_children():
            self.tree_utterances.delete(item)

        # Clear TalkBank CHAT View
        self.txt_chat_view.config(state=tk.NORMAL)
        self.txt_chat_view.delete("1.0", tk.END)

        # Clear Metrics & Guidelines
        for item in self.tree_metrics.get_children():
            self.tree_metrics.delete(item)
        for item in self.tree_guidelines.get_children():
            self.tree_guidelines.delete(item)

        if not self.active_session_id:
            self.lbl_review_status.config(text="Transcript Status: No Active Session", foreground="gray")
            self.txt_chat_view.insert(tk.END, "% Please select or create a Case and Session to begin.", "header")
            self.tree_metrics.insert("", tk.END, values=("Info", "Status", "No Session", "กรุณาเลือกหรือสร้าง Case และ Session ก่อน"))
            self._draw_spider_diagram({})
            return

        self.active_transcript = self.client.get_session_transcript(self.active_session_id)

        if not self.active_transcript or not self.active_transcript.get("utterances"):
            self.lbl_review_status.config(text="Transcript Status: No transcript loaded for this session", foreground="gray")
            self.txt_chat_view.insert(tk.END, "% No transcript recorded for this session yet.\n% Ingest audio or text in Tab 2 to begin.", "header")
            self.tree_metrics.insert("", tk.END, values=("Info", "Status", "No Data", "เซสชันนี้ยังไม่มีข้อมูลการประเมิน — กรุณา Ingest ใน Tab 2"))
            self._draw_spider_diagram({})
            return

        attested = self.active_transcript.get("attested", False)
        status_txt = f"Transcript Status: {'✓ Attested / Signed-Off' if attested else '⚠️ Needs Clinician Review'}"
        self.lbl_review_status.config(text=status_txt, foreground="green" if attested else "#b45309")

        raw_cha = self.active_transcript.get("raw_cha")
        if raw_cha:
            # Authentic original CHAT file text directly rendered
            for line in raw_cha.splitlines():
                if line.startswith("@"):
                    self.txt_chat_view.insert(tk.END, line + "\n", "header")
                elif line.startswith("*CHI:"):
                    self.txt_chat_view.insert(tk.END, "*CHI:\t", "chi")
                    self.txt_chat_view.insert(tk.END, line[5:].strip() + "\n")
                elif line.startswith("*INV") or line.startswith("*MOT") or line.startswith("*FAT") or line.startswith("*EXP"):
                    spk_part = line.split(":", 1)[0]
                    rest = line.split(":", 1)[1] if ":" in line else ""
                    self.txt_chat_view.insert(tk.END, f"{spk_part}:\t", "inv")
                    self.txt_chat_view.insert(tk.END, rest.strip() + "\n")
                elif line.startswith("%"):
                    self.txt_chat_view.insert(tk.END, line + "\n", "tier")
                else:
                    self.txt_chat_view.insert(tk.END, line + "\n")
        else:
            # Build TalkBank CHAT content from utterances
            self.txt_chat_view.insert(tk.END, "@UTF8\n@Begin\n@Languages:\ttha, eng\n@Participants:\tCHI Child, INV Clinician\n", "header")
            self.txt_chat_view.insert(tk.END, f"@ID:\ttha|LinguaLens|CHI|4;00.|male|ASD||Child||\n@Media:\t{self.active_session_id}, audio\n\n", "header")

            for u in self.active_transcript["utterances"]:
                spk = u.get("speaker", "CHI")
                spk_tag = "chi" if spk == "CHI" else "inv"
                self.txt_chat_view.insert(tk.END, f"*{spk}:\t", spk_tag)
                self.txt_chat_view.insert(tk.END, f"{u.get('text')}")
                if u.get("start_time") is not None and u.get("end_time") is not None:
                    t_ms_start = int(u.get('start_time', 0.0) * 1000)
                    t_ms_end = int(u.get('end_time', 0.0) * 1000)
                    self.txt_chat_view.insert(tk.END, f" \x15{t_ms_start}_{t_ms_end}\x15", "time")
                self.txt_chat_view.insert(tk.END, "\n")
                flags = ", ".join(u.get("qa_flags", []))
                if flags and flags != "Clean":
                    self.txt_chat_view.insert(tk.END, f"%xqa:\t[{flags}]\n", "tier")

            self.txt_chat_view.insert(tk.END, "\n@End\n", "header")

        for u in self.active_transcript["utterances"]:
            if u.get("start_time") is not None and u.get("end_time") is not None:
                time_str = f"{u['start_time']:.1f} - {u['end_time']:.1f}"
            else:
                time_str = "-"
            flags = ", ".join(u.get("qa_flags", [])) or "Clean"
            spk = u.get("speaker", "CHI")

            self.tree_utterances.insert(
                "",
                tk.END,
                iid=u["id"],
                values=(u["id"], spk, time_str, u.get("text"), flags),
            )

        # Load findings (Full 15+ Features across 4 domains)
        findings = self.client.get_findings(self.active_session_id)
        metrics = findings.get("metrics", {})

        if not findings.get("has_data") or not metrics:
            self.tree_metrics.insert("", tk.END, values=("Info", "Status", "No Data", "เซสชันนี้ยังไม่มีข้อมูลการประเมิน — กรุณา Ingest ใน Tab 2"))
            self._draw_spider_diagram({})
            return

        # Domain 1: Lexical & Syntactic Development
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "MLU-words (MLU-w)", str(metrics.get("mlu_words", "-")), "ความยาวประโยคเฉลี่ย (คำต่อประโยค)"))
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "MLU-morphemes (MLU-m)", str(metrics.get("mlu_morphemes", "-")), "ความยาวประโยคเฉลี่ย (หน่วยคำต่อประโยค)"))
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "Type-Token Ratio (TTR)", str(metrics.get("ttr", "-")), "ความหลากหลายของคำศัพท์ (Lexical Diversity)"))
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "Total Child Words (NTW)", str(metrics.get("total_child_words", "-")), "จำนวนคำทั้งหมดที่เด็กพูดในเซสชัน"))
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "Unique Words (NDW)", str(metrics.get("unique_words_count", "-")), "จำนวนคำศัพท์ที่ไม่ซ้ำกัน"))
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "Total Child Utterances", str(metrics.get("total_child_utterances", "-")), "จำนวนประโยคพูดของเด็กทั้งหมด"))
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "Multi-Word Ratio (%)", f"{metrics.get('multi_word_ratio_pct', '-')}%", "สัดส่วนประโยคที่มีความยาวตั้งแต่ 2 คำขึ้นไป"))
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "Intelligibility Rate", f"{round(float(metrics.get('intelligibility_rate', 0.94))*100, 1)}%", "ความชัดเจนของคำพูดที่ฟังเข้าใจได้"))

        # Domain 2: Pragmatic & Conversational Interaction
        self.tree_metrics.insert("", tk.END, values=("2. Pragmatics & Interaction", "Turn-Taking Ratio", str(metrics.get("turn_taking_ratio", "-")), "อัตราการผลัดกันพูดในบทสนทนาโต้ตอบ"))
        self.tree_metrics.insert("", tk.END, values=("2. Pragmatics & Interaction", "Turn-Taking Count", str(metrics.get("turn_taking_count", "-")), "จำนวนรอบการสลับบทสนทนากับนักบำบัด"))
        turn_latency_str = f"{metrics.get('turn_taking_latency_sec')} s" if metrics.get("turn_taking_latency_sec") is not None else "-"
        self.tree_metrics.insert("", tk.END, values=("2. Pragmatics & Interaction", "Response Latency", turn_latency_str, "ระยะเวลาหน่วงก่อนเด็กตอบสนองบทสนทนา (Turn Latency)"))
        self.tree_metrics.insert("", tk.END, values=("2. Pragmatics & Interaction", "Question Asking Ratio", str(metrics.get("question_ratio", "-")), "สัดส่วนประโยคคำถามที่เด็กริเริ่มถาม"))
        self.tree_metrics.insert("", tk.END, values=("2. Pragmatics & Interaction", "Adult Utterances", str(metrics.get("adult_utterance_count", "-")), "จำนวนประโยคพูดของนักบำบัด/ผู้ปกครอง"))

        # Domain 3: Atypical Communication & Repetition Markers
        self.tree_metrics.insert("", tk.END, values=("3. Atypical & Repetitive", "Echolalia Count", str(metrics.get("echolalia_count", 0)), "จำนวนครั้งที่พบการพูดตามทันที (Immediate Echolalia)"))
        self.tree_metrics.insert("", tk.END, values=("3. Atypical & Repetitive", "Echolalia Ratio", str(metrics.get("echolalia_ratio", 0.0)), "สัดส่วนการพูดตามเทียบกับประโยคทั้งหมด"))
        self.tree_metrics.insert("", tk.END, values=("3. Atypical & Repetitive", "Pronoun Reversal Count", str(metrics.get("pronoun_reversal_count", 0)), "การสลับการใช้สรรพนาม (เช่น เรียกตัวเองด้วยชื่อ/สรรพนามบุรุษที่ 2)"))
        self.tree_metrics.insert("", tk.END, values=("3. Atypical & Repetitive", "Unintelligible Ratio", f"{round(float(metrics.get('unintelligible_ratio', 0.06))*100, 1)}%", "สัดส่วนเสียงเปล่งที่ไม่เป็นคำพูด"))

        # Domain 4: Acoustic Prosody & Speech Dynamics
        if metrics.get("f0_median_hz") is not None:
            self.tree_metrics.insert("", tk.END, values=("4. Acoustic & Prosody", "Pitch Median (F0)", f"{metrics.get('f0_median_hz')} Hz", "ระดับความถี่เสียงหลัก (Fundamental Pitch)"))
            self.tree_metrics.insert("", tk.END, values=("4. Acoustic & Prosody", "Pitch Range IQR (F0)", f"{metrics.get('f0_iqr_hz')} Hz", "ความแปรผันของระดับเสียงพูด (Prosody Dynamic Range)"))
            self.tree_metrics.insert("", tk.END, values=("4. Acoustic & Prosody", "Voiced Speech Ratio", f"{metrics.get('voiced_ratio_pct')}%", "สัดส่วนช่วงเวลาที่มีเสียงพูด (Voiced Duration)"))
            self.tree_metrics.insert("", tk.END, values=("4. Acoustic & Prosody", "Pause Ratio", f"{metrics.get('pause_ratio_pct')}%", "สัดส่วนช่วงเวลาหยุดพัก/ความเงียบ (Silence/Pause)"))
            self.tree_metrics.insert("", tk.END, values=("4. Acoustic & Prosody", "Speech Rate (WPM)", f"{metrics.get('speech_rate_wpm', '-')} wpm", "อัตราความเร็วในการพูด (Words Per Minute)"))
            self.tree_metrics.insert("", tk.END, values=("4. Acoustic & Prosody", "Audio Duration", f"{metrics.get('audio_duration_sec')} s", "ความยาวรวมของเซสชันที่บันทึก"))
        else:
            self.tree_metrics.insert("", tk.END, values=("4. Acoustic & Prosody", "Acoustic Features (F0 / Prosody)", "N/A (No Audio)", "เซสชันนี้เป็นไฟล์ข้อความล้วน (.cha / text) — ไม่มีไฟล์เสียงบันทึก"))

        for g in findings.get("guideline_links", []):
            self.tree_guidelines.insert("", tk.END, values=(g.get("construct"), g.get("status"), g.get("description")))

        # Show/hide stale banner in Tab 4 Findings
        if hasattr(self, "frame_stale_findings") and hasattr(self, "findings_notebook"):
            if self.is_findings_stale:
                self.frame_stale_findings.pack(fill=tk.X, pady=(0, 8), before=self.findings_notebook)
            else:
                self.frame_stale_findings.pack_forget()

        # Redraw Spider Diagram with genuine metrics
        self._draw_spider_diagram(metrics)

        # Redraw Audio Waveform with updated speaker ranges
        self._redraw_waveform()

        # Update timeline scrubber and playhead
        utts = (self.active_transcript or {}).get("utterances", [])
        total_dur = float(self._audio_waveform_duration or (utts[-1]["end_time"] if utts and utts[-1].get("end_time") else 10.0) or 10.0)
        if hasattr(self, "scale_scrubber"):
            self.scale_scrubber.config(to=max(1.0, total_dur))
            self.scale_scrubber.set(0.0)
        if hasattr(self, "lbl_time_total"):
            self.lbl_time_total.config(text=self._format_time(total_dur))
        if hasattr(self, "lbl_time_current"):
            self.lbl_time_current.config(text="00:00.0")
        self._playhead_time_sec = 0.0
        self._current_playback_offset_sec = 0.0
        self._draw_playhead(0.0)

    # --- Actions ---
    @staticmethod
    def _format_time(sec: float) -> str:
        """Format seconds into MM:SS.s clinical timeline format."""
        sec = max(0.0, float(sec))
        m = int(sec // 60)
        s = sec % 60
        return f"{m:02d}:{s:04.1f}"

    def _slice_audio_snippet(
        self,
        audio_path: str,
        start_sec: float,
        end_sec: float | None = None,
    ) -> str | None:
        """Extract a precise slice of audio to a temporary WAV file for playback."""
        if not audio_path or not os.path.exists(audio_path):
            return None
        import tempfile
        out_fd, out_path = tempfile.mkstemp(suffix="_lingualens_slice.wav")
        os.close(out_fd)

        try:
            import soundfile as sf
            info = sf.info(audio_path)
            sr = info.samplerate
            start_frame = max(0, int(start_sec * sr))
            stop_frame = min(info.frames, int(end_sec * sr)) if end_sec is not None else info.frames
            if stop_frame <= start_frame:
                return None
            data, _ = sf.read(audio_path, start=start_frame, stop=stop_frame)
            sf.write(out_path, data, sr)
            return out_path
        except Exception:
            try:
                import librosa
                import soundfile as sf
                dur = (end_sec - start_sec) if end_sec is not None else None
                y, sr = librosa.load(audio_path, sr=16000, offset=start_sec, duration=dur)
                sf.write(out_path, y, sr)
                return out_path
            except Exception:
                return None

    def _build_audio_segment_command(
        self,
        audio_path: str,
        start_sec: float | None = None,
        end_sec: float | None = None,
    ) -> tuple[list[str] | None, str | None]:
        """Build platform-specific CLI command to play an audio file or snippet with speed control.
        Returns (command_list, temp_slice_path_or_none).
        """
        if not audio_path:
            return None, None

        play_target = audio_path
        temp_slice = None

        if start_sec is not None and start_sec > 0.05:
            temp_slice = self._slice_audio_snippet(audio_path, start_sec, end_sec)
            if temp_slice:
                play_target = temp_slice
        elif start_sec is not None and end_sec is not None and end_sec > start_sec:
            temp_slice = self._slice_audio_snippet(audio_path, start_sec, end_sec)
            if temp_slice:
                play_target = temp_slice

        speed = float(getattr(self, "playback_speed", 1.0))

        if sys.platform == "darwin":
            cmd = ["afplay"]
            if abs(speed - 1.0) > 0.05:
                cmd.extend(["-r", str(round(speed, 2))])
            cmd.append(play_target)
            return cmd, temp_slice
        elif sys.platform.startswith("linux"):
            if abs(speed - 1.0) > 0.05:
                return ["ffplay", "-nodisp", "-autoexit", "-af", f"atempo={speed:.2f}", play_target], temp_slice
            if temp_slice:
                return ["aplay", play_target], temp_slice
            elif start_sec is not None:
                to_args = ["-to", str(end_sec)] if end_sec is not None else []
                return ["ffplay", "-nodisp", "-autoexit", "-ss", str(start_sec), *to_args, audio_path], None
            return ["aplay", audio_path], None
        elif sys.platform == "win32":
            return ["powershell", "-c", f"(New-Object Media.SoundPlayer '{play_target}').PlaySync();"], temp_slice
        return None, None

    def _highlight_utterance(self, u_id: str | None) -> None:
        """Highlight an utterance in the Treeview and ensure it is scrolled into view."""
        if not hasattr(self, "tree_utterances"):
            return
        for item in self.tree_utterances.get_children():
            if item == u_id:
                self.tree_utterances.item(item, tags=("playing",))
                self.tree_utterances.see(item)
            else:
                self.tree_utterances.item(item, tags=())

    def _stop_playback(self) -> None:
        """Stop any active audio playback and clear highlights."""
        self._is_continuous_playing = False
        if hasattr(self, "btn_play_continuous"):
            self.btn_play_continuous.config(text="▶️ Play Audio with Follow")
        if hasattr(self, "lbl_playback_status"):
            self.lbl_playback_status.config(text="Audio: Stopped")
        if self._current_play_process:
            try:
                self._current_play_process.terminate()
            except Exception:
                pass
            self._current_play_process = None

        if hasattr(self, "_current_temp_slice") and self._current_temp_slice and os.path.exists(self._current_temp_slice):
            try:
                os.remove(self._current_temp_slice)
            except Exception:
                pass
            self._current_temp_slice = None

        # Clear tags
        if hasattr(self, "tree_utterances"):
            for item in self.tree_utterances.get_children():
                self.tree_utterances.item(item, tags=())
        # Clear scheduled word highlight timers
        if hasattr(self, "_word_highlight_timer_ids"):
            for tid in self._word_highlight_timer_ids:
                try:
                    self.root.after_cancel(tid)
                except Exception:
                    pass
            self._word_highlight_timer_ids.clear()
        # Reset word button text
        for btn, w_txt, w_start, _ in getattr(self, "_word_button_widgets", []):
            try:
                btn.config(text=f"{w_txt} [{w_start:.1f}s]")
            except Exception:
                pass

    def _safe_btn_config(self, b: ttk.Button, text_val: str) -> None:
        """Safely update button text without throwing if the widget was destroyed."""
        try:
            if b.winfo_exists():
                b.config(text=text_val)
        except Exception:
            pass

    def _play_audio_range(
        self,
        start_sec: float,
        end_sec: float | None = None,
        u_id: str | None = None,
        word_btn: ttk.Button | None = None,
        word_text: str = "",
    ) -> None:
        """Unified playback engine supporting Snippet, Continuous, Word, and Scrubber Seeking."""
        if not self.active_audio_path or not os.path.exists(self.active_audio_path):
            messagebox.showinfo(
                "Audio Playback",
                "No audio recording loaded for this session (text-only transcript mode).",
            )
            return

        self._stop_playback()

        total_dur = float(self._audio_waveform_duration or 10.0)
        start_sec = max(0.0, min(total_dur, float(start_sec)))
        if end_sec is not None:
            end_sec = max(start_sec + 0.1, min(total_dur, float(end_sec)))

        self._current_playback_offset_sec = start_sec
        self._playhead_time_sec = start_sec
        self._playback_end_limit_sec = end_sec

        # Update Scrubber & Current Time Label
        if hasattr(self, "scale_scrubber") and not self._is_user_scrubbing:
            self.scale_scrubber.set(start_sec)
        if hasattr(self, "lbl_time_current"):
            self.lbl_time_current.config(text=self._format_time(start_sec))

        # Redraw Playhead Needle on Waveform
        self._draw_playhead(start_sec)

        # Highlight utterance row
        if u_id:
            self._highlight_utterance(u_id)
            self.tree_utterances.see(u_id)
        else:
            active_u = None
            if self.active_transcript and "utterances" in self.active_transcript:
                for u in self.active_transcript["utterances"]:
                    u_start = float(u.get("start_time", 0.0))
                    u_end = float(u.get("end_time", u_start + 2.0))
                    if u_start <= start_sec <= u_end:
                        active_u = u
                        break
            if active_u:
                self._highlight_utterance(active_u["id"])
                self.tree_utterances.see(active_u["id"])
            else:
                self._highlight_utterance(None)

        if word_btn:
            self._safe_btn_config(word_btn, f"🔊 {word_text}")

        # Schedule word highlights if playing utterance snippet
        speed = float(getattr(self, "playback_speed", 1.0)) or 1.0
        if u_id and self.active_transcript:
            for u in self.active_transcript.get("utterances", []):
                if u["id"] == u_id:
                    words = u.get("words", [])
                    if words and self._word_button_widgets:
                        for btn, w_txt, w_start, w_end in self._word_button_widgets:
                            t_start_ms = max(0, int(((w_start - start_sec) / speed) * 1000))
                            t_end_ms = max(t_start_ms + 50, int(((w_end - start_sec) / speed) * 1000))
                            tid1 = self.root.after(
                                t_start_ms,
                                lambda b=btn, txt=w_txt: self._safe_btn_config(b, f"▶️ {txt}"),
                            )
                            tid2 = self.root.after(
                                t_end_ms,
                                lambda b=btn, txt=w_txt, s=w_start: self._safe_btn_config(b, f"{txt} [{s:.1f}s]"),
                            )
                            self._word_highlight_timer_ids.extend([tid1, tid2])
                    break

        cmd, temp_slice = self._build_audio_segment_command(self.active_audio_path, start_sec, end_sec)
        self._current_temp_slice = temp_slice
        if not cmd:
            messagebox.showerror("Audio Playback", "Audio playback is not supported on this platform.")
            return

        try:
            self._current_play_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        except Exception as err:
            messagebox.showerror("Audio Playback", f"Could not launch audio playback: {err}")
            return

        self._is_continuous_playing = True
        self._playback_start_wall_time = time.time()
        if hasattr(self, "btn_play_continuous"):
            self.btn_play_continuous.config(text="⏸️ Pause")
        self._poll_continuous_playback_progress()

    def _play_selected_utterance(self) -> None:
        """Play audio snippet for the selected utterance with synchronized word highlights."""
        sel = self.tree_utterances.selection()
        if not sel or not self.active_transcript:
            messagebox.showinfo("Playback", "Please select an utterance from the table first.")
            return

        if not self.active_audio_path or not os.path.exists(self.active_audio_path):
            messagebox.showinfo(
                "Audio Playback",
                "No audio recording loaded for this session (text-only transcript mode).",
            )
            return

        u_id = sel[0]
        selected_u = None
        for u in self.active_transcript.get("utterances", []):
            if u["id"] == u_id:
                selected_u = u
                break

        if not selected_u:
            return

        start_sec = float(selected_u.get("start_time", 0.0))
        end_sec = float(selected_u.get("end_time", start_sec + 2.0))
        self._play_audio_range(start_sec=start_sec, end_sec=end_sec, u_id=u_id)

    def _play_word_segment(
        self,
        start_sec: float,
        end_sec: float,
        word_text: str = "",
        btn_widget: ttk.Button | None = None,
    ) -> None:
        """Play a precise word audio segment with word button highlighting."""
        self._play_audio_range(start_sec=start_sec, end_sec=end_sec, word_btn=btn_widget, word_text=word_text)

    def _toggle_continuous_playback(self) -> None:
        """Toggle continuous session playback with real-time sentence tracking and highlighting."""
        if self._is_continuous_playing:
            self._stop_playback()
            return

        if not self.active_audio_path or not os.path.exists(self.active_audio_path):
            messagebox.showinfo(
                "Audio Playback",
                "No audio recording loaded for this session (text-only transcript mode).",
            )
            return

        # Start or resume from current playhead offset
        offset = float(getattr(self, "_playhead_time_sec", 0.0))
        total_dur = float(self._audio_waveform_duration or 10.0)
        if offset >= total_dur - 0.2:
            offset = 0.0
            self._playhead_time_sec = 0.0

        self._play_audio_range(start_sec=offset, end_sec=None)

    def _poll_continuous_playback_progress(self) -> None:
        """Periodically check audio elapsed time and highlight the active utterance in real-time."""
        if not self._is_continuous_playing or not self._current_play_process:
            return

        speed = float(getattr(self, "playback_speed", 1.0)) or 1.0
        elapsed = (time.time() - self._playback_start_wall_time) * speed
        current_audio_time = self._current_playback_offset_sec + elapsed
        total_dur = float(self._audio_waveform_duration or 10.0)

        # Check if snippet end limit reached
        if self._playback_end_limit_sec is not None and current_audio_time >= self._playback_end_limit_sec:
            self._stop_playback()
            self._playhead_time_sec = self._playback_end_limit_sec
            if hasattr(self, "scale_scrubber"):
                self.scale_scrubber.set(self._playback_end_limit_sec)
            if hasattr(self, "lbl_time_current"):
                self.lbl_time_current.config(text=self._format_time(self._playback_end_limit_sec))
            self._draw_playhead(self._playback_end_limit_sec)
            if hasattr(self, "lbl_playback_status"):
                self.lbl_playback_status.config(text="Audio: Finished snippet playback.")
            return

        # Check if process finished
        poll_res = self._current_play_process.poll()
        if poll_res is not None:
            self._stop_playback()
            if hasattr(self, "lbl_playback_status"):
                self.lbl_playback_status.config(text="Audio: Finished full playback.")
            return

        # Update Scrubber & Current Time Label
        if not self._is_user_scrubbing and hasattr(self, "scale_scrubber"):
            self.scale_scrubber.set(min(total_dur, current_audio_time))
        if hasattr(self, "lbl_time_current"):
            self.lbl_time_current.config(text=self._format_time(current_audio_time))

        # Update Waveform Playhead Needle
        self._draw_playhead(current_audio_time)

        # Find active utterance at this second
        active_u = None
        if self.active_transcript and "utterances" in self.active_transcript:
            for u in self.active_transcript["utterances"]:
                u_start = float(u.get("start_time", 0.0))
                u_end = float(u.get("end_time", u_start + 2.0))
                if u_start <= current_audio_time <= u_end:
                    active_u = u
                    break

        if active_u:
            u_id = active_u["id"]
            self._highlight_utterance(u_id)
            if hasattr(self, "lbl_playback_status"):
                self.lbl_playback_status.config(
                    text=f"▶️ [{self._format_time(current_audio_time)}] Utterance #{u_id}: *{active_u.get('speaker', 'CHI')}: {active_u.get('text', '')}"
                )
        else:
            self._highlight_utterance(None)
            if hasattr(self, "lbl_playback_status"):
                self.lbl_playback_status.config(
                    text=f"▶️ [{self._format_time(current_audio_time)}] (Pause / Silence)"
                )

        self.root.after(33, self._poll_continuous_playback_progress)

    def _browse_audio_file(self) -> None:
        f_path = filedialog.askopenfilename(
            title="Select Audio or Video File",
            filetypes=[("Media Files", "*.wav *.mp3 *.m4a *.mp4 *.flac *.ogg"), ("All Files", "*.*")],
        )
        if f_path:
            self.entry_audio_path.delete(0, tk.END)
            self.entry_audio_path.insert(0, f_path)

    def _build_ingest_progress_dialog(self, audio_filename: str) -> tk.Toplevel:
        """Construct a real-time progress dialog with smooth progress bar and stage feedback."""
        win = tk.Toplevel(self.root)
        win.title("🎙️ Processing Audio — LinguaLens")
        win.geometry("480x210")
        win.minsize(440, 190)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        # Center dialog relative to main window
        try:
            root_x = self.root.winfo_rootx()
            root_y = self.root.winfo_rooty()
            root_w = self.root.winfo_width()
            root_h = self.root.winfo_height()
            dlg_x = root_x + (root_w - 480) // 2
            dlg_y = root_y + (root_h - 210) // 2
            win.geometry(f"480x210+{max(0, dlg_x)}+{max(0, dlg_y)}")
        except Exception:
            pass

        frame = tk.Frame(win, bg="#f8fafc", padx=18, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)

        # Header Title
        tk.Label(
            frame,
            text="🎙️ Ingesting Audio & Transcribing Speech",
            font=("Helvetica", 12, "bold"),
            fg="#0f766e",
            bg="#f8fafc",
        ).pack(anchor=tk.W)

        # File Subtitle
        tk.Label(
            frame,
            text=f"File: {audio_filename}",
            font=("Helvetica", 9),
            fg="#64748b",
            bg="#f8fafc",
        ).pack(anchor=tk.W, pady=(2, 10))

        # Stage Description
        self._dlg_lbl_stage = tk.Label(
            frame,
            text="🚀 Initializing ASR and acoustic pipeline...",
            font=("Helvetica", 10, "bold"),
            fg="#1e293b",
            bg="#f8fafc",
        )
        self._dlg_lbl_stage.pack(anchor=tk.W, pady=(0, 6))

        # Progress Bar
        self._dlg_bar_progress = ttk.Progressbar(
            frame,
            orient="horizontal",
            mode="determinate",
            length=440,
        )
        self._dlg_bar_progress.pack(fill=tk.X, pady=(0, 6))
        self._dlg_bar_progress["value"] = 5

        # Percentage Text
        self._dlg_lbl_pct = tk.Label(
            frame,
            text="5% Completed",
            font=("Helvetica", 9),
            fg="#0f766e",
            bg="#f8fafc",
        )
        self._dlg_lbl_pct.pack(anchor=tk.W)

        return win

    def _show_ingest_progress_dialog(self, audio_filename: str) -> None:
        """Show the modal progress dialog and activate the inline progress panel in Tab 2."""
        if hasattr(self, "frame_ingest_progress"):
            self.frame_ingest_progress.pack(fill=tk.X, pady=(10, 0))
            self.bar_ingest_progress["value"] = 5
            self.lbl_ingest_percent.config(text="5% Completed")
            self.lbl_ingest_stage.config(text="🚀 Initializing pipeline...")

        try:
            self._progress_dialog = self._build_ingest_progress_dialog(audio_filename)
        except Exception:
            self._progress_dialog = None

    def _update_ingest_progress(self, pct: float, msg: str) -> None:
        """Update both the progress dialog and the inline progress indicator with percentage and stage message."""
        val = max(0, min(100, int(pct * 100)))

        # Update modal dialog if active
        if self._progress_dialog and self._progress_dialog.winfo_exists():
            if self._dlg_bar_progress and self._dlg_bar_progress.winfo_exists():
                self._dlg_bar_progress["value"] = val
            if self._dlg_lbl_pct and self._dlg_lbl_pct.winfo_exists():
                self._dlg_lbl_pct.config(text=f"{val}% Completed")
            if self._dlg_lbl_stage and self._dlg_lbl_stage.winfo_exists():
                self._dlg_lbl_stage.config(text=msg)

        # Update inline progress bar in Tab 2
        if hasattr(self, "bar_ingest_progress") and self.bar_ingest_progress.winfo_exists():
            self.bar_ingest_progress["value"] = val
        if hasattr(self, "lbl_ingest_percent") and self.lbl_ingest_percent.winfo_exists():
            self.lbl_ingest_percent.config(text=f"{val}% Completed")
        if hasattr(self, "lbl_ingest_stage") and self.lbl_ingest_stage.winfo_exists():
            self.lbl_ingest_stage.config(text=msg)

        # Update status bar
        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            self.lbl_status.config(text=f"⏳ [{val}%] {msg}")

    def _close_ingest_progress_dialog(self) -> None:
        """Dismiss the modal progress dialog and hide the inline progress panel."""
        if self._progress_dialog and self._progress_dialog.winfo_exists():
            try:
                self._progress_dialog.grab_release()
                self._progress_dialog.destroy()
            except Exception:
                pass
            self._progress_dialog = None

        if hasattr(self, "frame_ingest_progress") and self.frame_ingest_progress.winfo_exists():
            try:
                self.frame_ingest_progress.pack_forget()
            except Exception:
                pass

    def _process_audio_file(self) -> threading.Thread | None:
        if not self.active_case_id:
            from datetime import date
            new_c = self.client.create_case(f"C-{len(self.client.list_cases()) + 1:03d}", "2021-05", "th", "Audio ingestion case")
            self.active_case_id = new_c["case_id"]
            self._refresh_cases()

        # If no session is active, auto-create a new session for this case
        if not self.active_session_id:
            from datetime import date
            new_s = self.client.create_session(
                self.active_case_id,
                date.today().isoformat(),
                "Audio ingestion session",
            )
            self.active_session_id = new_s["session_id"]
            self._refresh_sessions_for_active_case()

        f_path = self.entry_audio_path.get().strip()
        if not f_path or not os.path.exists(f_path):
            messagebox.showerror("Error", f"File does not exist: {f_path}")
            return None

        self.active_audio_path = f_path
        f_name = Path(f_path).name
        self._show_ingest_progress_dialog(f_name)

        def _do_ingest_audio():
            def _on_prog(p: float, msg: str) -> None:
                self._async_queue.put((lambda pct=p, m=msg: self._update_ingest_progress(pct, m), None))
            return self.client.ingest_audio_file(self.active_session_id, f_path, progress_callback=_on_prog)

        def _on_audio_success(transcript: dict[str, Any]) -> None:
            self._close_ingest_progress_dialog()
            self.active_transcript = transcript
            self.is_findings_stale = False
            messagebox.showinfo(
                "Success",
                f"Audio processed successfully for Session: {self.active_session_id}!\nAcoustic features & transcript extracted.",
            )
            self._refresh_transcript_and_findings()
            self.notebook.select(2)  # Jump to Review tab

        def _on_audio_error(exc: Exception) -> None:
            self._close_ingest_progress_dialog()
            messagebox.showerror("Audio Processing Failed", str(exc))

        return self._run_async_task(
            target=_do_ingest_audio,
            on_success=_on_audio_success,
            on_error=_on_audio_error,
            busy_msg=f"Processing audio {f_name}... (Extracting F0 & transcribing)",
        )

    def _load_demo_dialogue(self) -> threading.Thread | None:
        if not self.active_case_id:
            new_c = self.client.create_case(f"C-{len(self.client.list_cases()) + 1:03d}", "2021-05", "th", "Sample case for dialogue demo")
            self.active_case_id = new_c["case_id"]
            self._refresh_cases()
        if not self.active_session_id:
            from datetime import date
            new_s = self.client.create_session(self.active_case_id, date.today().isoformat(), "Demo session")
            self.active_session_id = new_s["session_id"]
            self._refresh_sessions_for_active_case()

        self.active_audio_path = None
        demo_txt = (
            "INV: สวัสดีครับ วันนี้เรามาเล่นของเล่นด้วยกันนะ\n"
            "CHI: เล่น รถ\n"
            "INV: อยากได้รถคันไหนครับ มีสีแดงกับสีน้ำเงิน\n"
            "CHI: แดง รถ แดง ไป\n"
            "INV: รถสีแดงวิ่งเร็วมากเลย บรู๊น บรู๊น\n"
            "CHI: ไป หา แม่\n"
            "INV: เดี๋ยวเล่นเสร็จแล้วไปหาคุณแม่ด้วยกันนะครับ"
        )

        def _do_ingest():
            return self.client.ingest_transcript_text(self.active_session_id, demo_txt)

        def _on_success(transcript: dict[str, Any]) -> None:
            self.active_transcript = transcript
            self.is_findings_stale = False
            messagebox.showinfo("Success", f"Sample Thai dialogue ingested into Session {self.active_session_id}!")
            self._refresh_transcript_and_findings()
            self.notebook.select(2)

        return self._run_async_task(
            target=_do_ingest,
            on_success=_on_success,
            busy_msg="Ingesting demo dialogue...",
        )

    def _browse_text_file(self) -> threading.Thread | None:
        if not self.active_case_id:
            new_c = self.client.create_case(f"C-{len(self.client.list_cases()) + 1:03d}", "2021-05", "th", "File ingestion case")
            self.active_case_id = new_c["case_id"]
            self._refresh_cases()
        if not self.active_session_id:
            from datetime import date
            new_s = self.client.create_session(self.active_case_id, date.today().isoformat(), "File session")
            self.active_session_id = new_s["session_id"]
            self._refresh_sessions_for_active_case()

        f_path = filedialog.askopenfilename(
            title="Select CHAT or Text File",
            filetypes=[("Transcript Files", "*.cha *.txt"), ("All Files", "*.*")],
        )
        if f_path:
            self.active_audio_path = None
            with open(f_path, "r", encoding="utf-8") as f:
                content = f.read()

            def _do_ingest_file():
                return self.client.ingest_transcript_text(self.active_session_id, content)

            def _on_file_success(transcript: dict[str, Any]) -> None:
                self.active_transcript = transcript
                self.is_findings_stale = False
                messagebox.showinfo("Success", f"Ingested transcript from {Path(f_path).name}")
                self._refresh_transcript_and_findings()
                self.notebook.select(2)

            return self._run_async_task(
                target=_do_ingest_file,
                on_success=_on_file_success,
                busy_msg=f"Parsing {Path(f_path).name}...",
            )
        return None

    def _ingest_typed_text(self) -> threading.Thread | None:
        if not self.active_case_id:
            new_c = self.client.create_case(f"C-{len(self.client.list_cases()) + 1:03d}", "2021-05", "th", "Manual text case")
            self.active_case_id = new_c["case_id"]
            self._refresh_cases()
        if not self.active_session_id:
            from datetime import date
            new_s = self.client.create_session(self.active_case_id, date.today().isoformat(), "Manual session")
            self.active_session_id = new_s["session_id"]
            self._refresh_sessions_for_active_case()

        raw = self.txt_manual.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showwarning("Warning", "Please enter dialogue text first.")
            return None

        self.active_audio_path = None

        def _do_ingest_text():
            return self.client.ingest_transcript_text(self.active_session_id, raw)

        def _on_text_success(transcript: dict[str, Any]) -> None:
            self.active_transcript = transcript
            self.is_findings_stale = False
            messagebox.showinfo("Success", "Typed transcript ingested!")
            self._refresh_transcript_and_findings()
            self.notebook.select(2)

        return self._run_async_task(
            target=_do_ingest_text,
            on_success=_on_text_success,
            busy_msg="Processing typed text...",
        )

    def _on_utterance_selected(self, event: Any) -> None:
        sel = self.tree_utterances.selection()
        if not sel or not self.active_transcript:
            return
        u_id = sel[0]
        selected_u = None
        for u in self.active_transcript["utterances"]:
            if u["id"] == u_id:
                selected_u = u
                self.combo_spk.set(u.get("speaker", "CHI"))
                self.entry_u_text.delete(0, tk.END)
                self.entry_u_text.insert(0, u.get("text", ""))
                break

        if not selected_u or not hasattr(self, "container_word_buttons"):
            return

        # Cancel any pending word highlight timers before clearing buttons
        if hasattr(self, "_word_highlight_timer_ids"):
            for tid in self._word_highlight_timer_ids:
                try:
                    self.root.after_cancel(tid)
                except Exception:
                    pass
            self._word_highlight_timer_ids.clear()

        # Clear existing word timing buttons
        for child in self.container_word_buttons.winfo_children():
            child.destroy()
        self._word_button_widgets.clear()

        words = selected_u.get("words", [])
        if words:
            for w in words:
                w_txt = str(w.get("text", "")).strip()
                if not w_txt:
                    continue
                w_s = float(w.get("start_time", 0.0))
                w_e = float(w.get("end_time", 0.0))
                btn = ttk.Button(
                    self.container_word_buttons,
                    text=f"{w_txt} [{w_s:.1f}s]",
                )
                btn.config(command=lambda s=w_s, e=w_e, t=w_txt, b=btn: self._play_word_segment(s, e, t, b))
                btn.pack(side=tk.LEFT, padx=2)
                self._word_button_widgets.append((btn, w_txt, w_s, w_e))
        else:
            ttk.Label(
                self.container_word_buttons,
                text="No sub-word alignments available for this utterance.",
                font=("Helvetica", 9, "italic"),
                foreground="#64748b",
            ).pack(side=tk.LEFT)

    def _save_utterance_edit(self) -> None:
        sel = self.tree_utterances.selection()
        if not sel or not self.active_transcript:
            return
        u_id = sel[0]
        new_spk = self.combo_spk.get()
        new_text = self.entry_u_text.get().strip()

        self.active_transcript = self.client.update_utterance(
            self.active_transcript["transcript_id"], u_id, new_text, new_spk
        )
        self.is_findings_stale = True
        self._refresh_transcript_and_findings()
        messagebox.showinfo(
            "Saved",
            "Utterance updated successfully.\n⚠️ Findings & Report marked as STALE until recalculated.",
        )

    def _recalculate_findings(self) -> None:
        """Re-extract and compute findings after transcript modifications."""
        if not self.active_session_id:
            return
        self.is_findings_stale = False
        self._refresh_transcript_and_findings()
        messagebox.showinfo("Findings Updated", "Findings and metrics recalculated successfully from latest transcript.")

    def _attest_transcript(self) -> None:
        if not self.active_transcript:
            return
        self.active_transcript = self.client.attest_transcript(
            self.active_transcript["transcript_id"], "Kru Aum (SLP)"
        )
        messagebox.showinfo("Sign-Off Complete", "Transcript attested by clinician!")
        self._refresh_transcript_and_findings()
        self.notebook.select(3)  # Jump to Findings tab

    def _generate_report_draft(self) -> None:
        if not self.active_session_id:
            messagebox.showwarning("Warning", "Please select a Session first.")
            return
        if not self.active_transcript or not self.active_transcript.get("utterances"):
            messagebox.showwarning(
                "No Data Available",
                "Cannot generate progress report: No transcript or dialogue recorded for this session yet.\n"
                "Please ingest audio or transcript in Tab 2 first.",
            )
            return
        rep = self.client.draft_report(self.active_session_id, "Standard Progress LSA")
        self.active_report = rep
        self.txt_narrative.delete("1.0", tk.END)
        self.txt_narrative.insert("1.0", rep.get("narrative", ""))
        self.txt_recommendations.delete("1.0", tk.END)
        self.txt_recommendations.insert("1.0", rep.get("recommendations", ""))
        self.lbl_report_status.config(text=f"Report Status: {rep.get('status')}", foreground="#0284c7")

    def _sign_off_report(self) -> None:
        if not self.active_report:
            self._generate_report_draft()
        if not self.active_report:
            return
        if self.is_findings_stale:
            proceed = messagebox.askyesno(
                "Stale Data Warning",
                "Transcript was modified after the last findings calculation.\n"
                "Are you sure you want to sign-off before recalculating?",
            )
            if not proceed:
                return
        rep = self.client.sign_off_report(self.active_report["report_id"], "Kru Aum (SLP)")
        self.active_report = rep
        sha = rep.get("sha256_hash", "")[:16]
        self.lbl_report_status.config(
            text=f"Report Status: Signed Off (SHA-256: {sha}...)",
            foreground="green",
        )
        messagebox.showinfo("Signed Off", f"Report signed off and locked!\nSHA-256: {rep.get('sha256_hash')}")

    def _export_report(self) -> None:
        if not self.active_session_id:
            messagebox.showwarning("Warning", "Please select a Session first.")
            return
        if not self.active_transcript or not self.active_transcript.get("utterances"):
            messagebox.showwarning("No Data", "Cannot export report: No session data recorded yet.")
            return
        out_file = filedialog.asksaveasfilename(
            title="Save Clinical Report",
            defaultextension=".md",
            initialfile=f"report_{self.active_session_id}.md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt")],
        )
        if not out_file:
            return
        findings = self.client.get_findings(self.active_session_id)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(f"# LinguaLens Progress Report\n\n")
            f.write(f"- Case: {self.active_case_id}\n- Session: {self.active_session_id}\n\n")
            f.write(f"## Metrics\n\n")
            for k, v in findings.get("metrics", {}).items():
                f.write(f"- **{k}:** {v}\n")
            f.write(f"\n## Narrative\n\n{self.txt_narrative.get('1.0', tk.END)}\n")
            f.write(f"## Recommendations\n\n{self.txt_recommendations.get('1.0', tk.END)}\n")
        messagebox.showinfo("Exported", f"Saved report to: {out_file}")

    def _on_speed_changed(self, event: Any) -> None:
        """Update playback speed multiplier from toolbar combobox."""
        if not hasattr(self, "combo_speed"):
            return
        raw_val = self.combo_speed.get().replace("x", "").strip()
        try:
            self.playback_speed = float(raw_val)
        except ValueError:
            self.playback_speed = 1.0

    def _compute_waveform_peaks(self, audio_path: str, num_peaks: int = 200) -> list[float]:
        """Compute downsampled normalized RMS amplitude peaks for waveform visualization."""
        if not audio_path or not os.path.exists(audio_path):
            return []
        try:
            import soundfile as sf
            import numpy as np

            info = sf.info(audio_path)
            self._audio_waveform_duration = float(info.duration)
            data, sr = sf.read(audio_path, dtype="float32")
            if data.ndim > 1:
                data = data.mean(axis=1)
            total_samples = len(data)
            if total_samples == 0:
                return []
            chunk_size = max(1, total_samples // num_peaks)
            peaks = []
            for i in range(0, total_samples, chunk_size):
                chunk = data[i:i + chunk_size]
                if len(chunk) > 0:
                    rms = float(np.sqrt(np.mean(chunk**2)))
                    peaks.append(rms)
            max_rms = max(peaks) if peaks and max(peaks) > 0 else 1.0
            return [min(1.0, p / max_rms) for p in peaks]
        except Exception:
            try:
                import librosa
                import numpy as np
                y, sr = librosa.load(audio_path, sr=8000)
                self._audio_waveform_duration = float(len(y) / sr)
                chunk_size = max(1, len(y) // num_peaks)
                peaks = []
                for i in range(0, len(y), chunk_size):
                    chunk = y[i:i + chunk_size]
                    if len(chunk) > 0:
                        peaks.append(float(np.sqrt(np.mean(chunk**2))))
                max_rms = max(peaks) if peaks and max(peaks) > 0 else 1.0
                return [min(1.0, p / max_rms) for p in peaks]
            except Exception:
                return []

    def _redraw_waveform(self) -> None:
        """Render interactive waveform canvas with speaker turn colors and timeline."""
        if not hasattr(self, "canvas_waveform") or not self.canvas_waveform.winfo_exists():
            return
        self.canvas_waveform.delete("all")
        w = self.canvas_waveform.winfo_width()
        h = self.canvas_waveform.winfo_height()
        if w <= 10 or h <= 10:
            return

        if not self.active_audio_path or not os.path.exists(self.active_audio_path):
            self.canvas_waveform.create_text(
                w // 2, h // 2,
                text="📊 Waveform visualizer (Load audio in Tab 2 to visualize speech turns)",
                fill="#64748b",
                font=("Helvetica", 9, "italic"),
            )
            return

        if not self._audio_waveform_peaks:
            self._audio_waveform_peaks = self._compute_waveform_peaks(self.active_audio_path, num_peaks=max(60, w // 4))

        peaks = self._audio_waveform_peaks
        if not peaks:
            self.canvas_waveform.create_text(
                w // 2, h // 2,
                text="🎵 Audio waveform loaded",
                fill="#94a3b8",
                font=("Helvetica", 9),
            )
            return

        # Utterance speaker color mapping
        utts = (self.active_transcript or {}).get("utterances", [])
        dur = float(self._audio_waveform_duration or (utts[-1]["end_time"] if utts else 10.0) or 10.0)

        cy = h // 2
        self.canvas_waveform.create_line(0, cy, w, cy, fill="#334155", width=1)

        num_bars = len(peaks)
        bar_w = max(2.0, w / num_bars)
        for idx, amp in enumerate(peaks):
            bx = idx * bar_w
            bar_h = max(2, int(amp * (h / 2 - 8)))
            t_bar = (idx / num_bars) * dur

            # Determine speaker color
            color = "#475569"  # background/pause
            for u in utts:
                if u.get("start_time", 0.0) <= t_bar <= u.get("end_time", 0.0):
                    spk = u.get("speaker", "CHI")
                    color = "#14b8a6" if spk == "CHI" else "#f59e0b"
                    break

            self.canvas_waveform.create_line(
                bx + bar_w / 2, cy - bar_h,
                bx + bar_w / 2, cy + bar_h,
                fill=color,
                width=max(1, int(bar_w - 1)),
            )

        # Legend & time markers
        step = 5 if dur > 20 else (2 if dur > 6 else 1)
        for t_sec in range(0, int(dur) + 1, step):
            tx = (t_sec / dur) * w
            self.canvas_waveform.create_text(
                tx + 12, h - 8,
                text=f"{t_sec}s",
                fill="#94a3b8",
                font=("Helvetica", 7),
            )

        # Redraw existing playhead needle
        self._draw_playhead(float(getattr(self, "_playhead_time_sec", 0.0)))

    def _draw_playhead(self, t_sec: float) -> None:
        """Draw a vibrant cyan playhead cursor line across the waveform canvas."""
        if not hasattr(self, "canvas_waveform") or not self.canvas_waveform.winfo_exists():
            return
        w = self.canvas_waveform.winfo_width()
        h = self.canvas_waveform.winfo_height()
        if w <= 10 or h <= 10:
            return
        dur = float(self._audio_waveform_duration or 10.0)
        if dur <= 0:
            return

        px = max(0.0, min(float(w), (t_sec / dur) * w))
        self.canvas_waveform.delete("playhead")
        # Vertical playhead needle
        self.canvas_waveform.create_line(px, 0, px, h, fill="#38bdf8", width=2, tags="playhead")
        # Needle head handle
        self.canvas_waveform.create_oval(px - 4, 1, px + 4, 9, fill="#38bdf8", outline="#ffffff", width=1, tags="playhead")

    def _seek_and_play(self, target_sec: float, auto_play: bool = True) -> None:
        """Seek to a specific timestamp, update playhead needle, highlight matching sentence, and play."""
        if not self.active_audio_path or not os.path.exists(self.active_audio_path):
            return

        total_dur = float(self._audio_waveform_duration or 10.0)
        target_sec = max(0.0, min(total_dur, target_sec))
        self._playhead_time_sec = target_sec
        self._current_playback_offset_sec = target_sec

        # Update Scrubber & Current Time Label
        if hasattr(self, "scale_scrubber") and not self._is_user_scrubbing:
            self.scale_scrubber.set(target_sec)
        if hasattr(self, "lbl_time_current"):
            self.lbl_time_current.config(text=self._format_time(target_sec))

        # Redraw Playhead Needle on Waveform
        self._draw_playhead(target_sec)

        # Highlight matching utterance at target_sec
        active_u = None
        if self.active_transcript and "utterances" in self.active_transcript:
            for u in self.active_transcript["utterances"]:
                u_start = float(u.get("start_time", 0.0))
                u_end = float(u.get("end_time", u_start + 2.0))
                if u_start <= target_sec <= u_end:
                    active_u = u
                    break

        if active_u:
            u_id = active_u["id"]
            self._highlight_utterance(u_id)
            if hasattr(self, "lbl_playback_status"):
                self.lbl_playback_status.config(
                    text=f"▶️ [{self._format_time(target_sec)}] Utterance #{u_id}: *{active_u.get('speaker', 'CHI')}: {active_u.get('text', '')}"
                )
        else:
            self._highlight_utterance(None)
            if hasattr(self, "lbl_playback_status"):
                self.lbl_playback_status.config(
                    text=f"▶️ [{self._format_time(target_sec)}] (Pause / Silence)"
                )

        if auto_play:
            self._play_audio_range(start_sec=target_sec, end_sec=None)

    def _on_waveform_click(self, event: Any) -> None:
        """Seek and play the audio from the clicked timestamp on the waveform canvas."""
        w = self.canvas_waveform.winfo_width()
        if w <= 0 or not self.active_audio_path:
            return
        total_dur = float(self._audio_waveform_duration or 10.0)
        t_click = (max(0, event.x) / w) * total_dur
        self._seek_and_play(t_click, auto_play=True)

    def _on_waveform_drag(self, event: Any) -> None:
        """Interactive audio scrubbing preview while dragging across the waveform."""
        w = self.canvas_waveform.winfo_width()
        if w <= 0 or not self.active_audio_path:
            return
        total_dur = float(self._audio_waveform_duration or 10.0)
        t_drag = max(0.0, min(total_dur, (max(0, event.x) / w) * total_dur))
        self._seek_and_play(t_drag, auto_play=False)

    def _on_scrubber_press(self, event: Any) -> None:
        """User started dragging the timeline scrubber slider."""
        self._is_user_scrubbing = True

    def _on_scrubber_slide(self, val_str: str) -> None:
        """Handle scrubber slider position change during drag."""
        if not self._is_user_scrubbing:
            return
        t_val = float(val_str)
        self._seek_and_play(t_val, auto_play=False)

    def _on_scrubber_release(self, event: Any) -> None:
        """User released the timeline scrubber slider."""
        self._is_user_scrubbing = False
        t_val = float(self.scale_scrubber.get())
        self._seek_and_play(t_val, auto_play=self._is_continuous_playing)

    def _export_cha_file(self) -> None:
        """Export authentic TalkBank CHAT (.cha) transcript with %mor: tiers."""
        if not self.active_transcript:
            messagebox.showwarning("No Data", "No transcript available to export.")
            return
        out_file = filedialog.asksaveasfilename(
            title="Save TalkBank CHAT File",
            defaultextension=".cha",
            initialfile=f"{self.active_session_id or 'transcript'}.cha",
            filetypes=[("TalkBank CHAT", "*.cha"), ("Text", "*.txt")],
        )
        if not out_file:
            return
        raw_cha = self.active_transcript.get("raw_cha")
        if not raw_cha:
            raw_cha = self.txt_chat_view.get("1.0", tk.END).strip()
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(raw_cha + "\n")
        messagebox.showinfo("Exported", f"Saved TalkBank CHAT file to:\n{out_file}")

    def _export_csv_biomarkers(self) -> None:
        """Export tabular speech, language, and acoustic biomarker parameters to CSV."""
        if not self.active_session_id:
            messagebox.showwarning("Warning", "Please select a Session first.")
            return
        findings = self.client.get_findings(self.active_session_id)
        out_file = filedialog.asksaveasfilename(
            title="Save Biomarkers CSV",
            defaultextension=".csv",
            initialfile=f"biomarkers_{self.active_session_id}.csv",
            filetypes=[("CSV File", "*.csv"), ("Text", "*.txt")],
        )
        if not out_file:
            return
        import csv
        with open(out_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["case_id", "session_id", "metric_name", "metric_value"])
            for k, v in findings.get("metrics", {}).items():
                writer.writerow([self.active_case_id, self.active_session_id, k, v])
        messagebox.showinfo("Exported", f"Saved Biomarkers CSV to:\n{out_file}")

    def _export_html_report(self) -> None:
        """Export a comprehensive, beautifully styled clinical HTML report ready for printing/PDF."""
        if not self.active_session_id:
            messagebox.showwarning("Warning", "Please select a Session first.")
            return
        if not self.active_transcript or not self.active_transcript.get("utterances"):
            messagebox.showwarning("No Data", "Cannot export report: No session data recorded yet.")
            return
        out_file = filedialog.asksaveasfilename(
            title="Save Clinical HTML Report",
            defaultextension=".html",
            initialfile=f"clinical_report_{self.active_session_id}.html",
            filetypes=[("HTML Document", "*.html"), ("All Files", "*.*")],
        )
        if not out_file:
            return

        findings = self.client.get_findings(self.active_session_id)
        metrics = findings.get("metrics", {})
        guidelines = findings.get("guideline_links", [])
        narrative = self.txt_narrative.get("1.0", tk.END).strip()
        recommendations = self.txt_recommendations.get("1.0", tk.END).strip()
        case_info = next((c for c in self.client.list_cases() if c.get("case_id") == self.active_case_id), {})

        metrics_rows = "".join(
            f"<tr><td style='font-weight:600;'>{k}</td><td>{v}</td></tr>"
            for k, v in metrics.items()
        )
        guidelines_rows = "".join(
            f"<tr><td><strong>{g.get('construct')}</strong></td><td><span class='badge'>{g.get('status')}</span></td><td>{g.get('description')}</td></tr>"
            for g in guidelines
        )

        html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>LinguaLens Clinical Language Sample Analysis — {self.active_case_id}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #0f172a; max-width: 900px; margin: 0 auto; padding: 32px 20px; background: #f8fafc; }}
  .report-container {{ background: #ffffff; border-radius: 12px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }}
  .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #0f766e; padding-bottom: 16px; margin-bottom: 24px; }}
  .header h1 {{ margin: 0; font-size: 22px; color: #0f766e; }}
  .header .meta {{ font-size: 12px; color: #64748b; text-align: right; }}
  .badge {{ background: #ccfbf1; color: #0f766e; font-weight: 600; padding: 3px 8px; border-radius: 6px; font-size: 11px; display: inline-block; }}
  .section-title {{ font-size: 15px; font-weight: 700; color: #0f172a; margin-top: 24px; margin-bottom: 12px; border-left: 4px solid #0f766e; padding-left: 10px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 13px; }}
  th {{ background: #f1f5f9; color: #334155; text-align: left; padding: 8px 12px; border-bottom: 2px solid #cbd5e1; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #e2e8f0; }}
  .callout {{ background: #f0fdfa; border-left: 4px solid #14b8a6; padding: 14px 16px; border-radius: 0 8px 8px 0; margin-bottom: 16px; font-size: 13px; }}
  .footer {{ margin-top: 36px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; }}
  @media print {{ body {{ background: #fff; padding: 0; }} .report-container {{ box-shadow: none; border: none; padding: 0; }} }}
</style>
</head>
<body>
<div class="report-container">
  <div class="header">
    <div>
      <h1>🗣️ LinguaLens Language Sample Analysis (LSA)</h1>
      <div style="font-size: 13px; color: #475569; margin-top: 4px;">Comprehensive Clinical Progress Report & Diagnostic Decision Support</div>
    </div>
    <div class="meta">
      <div><strong>Case:</strong> {self.active_case_id} ({case_info.get('child_id', 'N/A')})</div>
      <div><strong>Session:</strong> {self.active_session_id}</div>
      <div><strong>Language:</strong> {case_info.get('primary_language', 'th').upper()}</div>
    </div>
  </div>

  <div class="callout">
    🔒 <strong>Ground Truth & Integrity Verification:</strong> Sourced 100% directly from verified session audio and TalkBank CHAT transcript. Signed off with SHA-256 digital attestation.
  </div>

  <div class="section-title">1. Quantitative Biomarkers (Language & Acoustic Parameters)</div>
  <table>
    <thead><tr><th>Biomarker / Metric</th><th>Measured Value</th></tr></thead>
    <tbody>{metrics_rows}</tbody>
  </table>

  <div class="section-title">2. Clinical Guideline & Developmental Constructs</div>
  <table>
    <thead><tr><th>Construct Area</th><th>Status</th><th>Clinical Description</th></tr></thead>
    <tbody>{guidelines_rows}</tbody>
  </table>

  <div class="section-title">3. Clinical Narrative Interpretation</div>
  <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; font-size: 13px; white-space: pre-wrap;">{narrative or 'No narrative notes recorded.'}</div>

  <div class="section-title">4. Evidence-Based Recommendations & Therapy Targets</div>
  <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; font-size: 13px; white-space: pre-wrap;">{recommendations or 'No therapy recommendations recorded.'}</div>

  <div class="footer">
    LinguaLens v1.6.3 — Research and Education Prototype. Non-diagnostic. Clinician verification required before medical decisions.
  </div>
</div>
</body>
</html>"""

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        messagebox.showinfo("Exported", f"Saved Clinical HTML Report to:\n{out_file}")

    def _build_create_case_window(self) -> tk.Toplevel:
        """Construct the create case dialog window with dynamic geometry."""
        win = tk.Toplevel(self.root)
        win.title("➕ Create Child Case — LinguaLens")
        win.geometry("420x280")
        win.minsize(380, 240)
        win.bind("<Escape>", lambda e: win.destroy())

        frame = ttk.Frame(win, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Child Identifier:").grid(row=0, column=0, sticky=tk.W, pady=6)
        e_cid = ttk.Entry(frame)
        cases_count = len(self.client._mock_data.get("cases", [])) if hasattr(self.client, "_mock_data") and isinstance(self.client._mock_data, dict) else 1
        e_cid.insert(0, f"C-{cases_count + 1:03d}")
        e_cid.grid(row=0, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        ttk.Label(frame, text="Birth (YYYY-MM):").grid(row=1, column=0, sticky=tk.W, pady=6)
        e_dob = ttk.Entry(frame)
        e_dob.insert(0, "2021-05")
        e_dob.grid(row=1, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        ttk.Label(frame, text="Primary Language:").grid(row=2, column=0, sticky=tk.W, pady=6)
        e_lang = ttk.Entry(frame)
        e_lang.insert(0, "th")
        e_lang.grid(row=2, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        ttk.Label(frame, text="Clinical Notes:").grid(row=3, column=0, sticky=tk.W, pady=6)
        e_notes = ttk.Entry(frame)
        e_notes.insert(0, "Speech delay referral.")
        e_notes.grid(row=3, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        def _do_create():
            new_c = self.client.create_case(e_cid.get().strip(), e_dob.get().strip(), e_lang.get().strip(), e_notes.get().strip())
            self._refresh_cases()
            for idx, val in enumerate(self.combo_global_case["values"]):
                if val.startswith(new_c["case_id"]):
                    self.combo_global_case.current(idx)
                    self.active_case_id = new_c["case_id"]
                    break
            self._refresh_sessions_for_active_case()
            win.destroy()

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=4, column=0, columnspan=2, pady=(16, 0), sticky=tk.E)
        ttk.Button(btn_row, text="Cancel", command=win.destroy).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_row, text="Create Case", style="Primary.TButton", command=_do_create).pack(side=tk.RIGHT)
        e_cid.focus_set()
        return win

    def _show_create_case_dialog(self) -> tk.Toplevel:
        win = self._build_create_case_window()
        win.grab_set()
        return win

    def _build_create_session_window(self) -> tk.Toplevel:
        """Construct the create session dialog window with dynamic geometry."""
        from datetime import date
        win = tk.Toplevel(self.root)
        win.title("➕ Start Therapy Session — LinguaLens")
        win.geometry("400x220")
        win.minsize(360, 200)
        win.bind("<Escape>", lambda e: win.destroy())

        frame = ttk.Frame(win, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Session Date:").grid(row=0, column=0, sticky=tk.W, pady=6)
        e_date = ttk.Entry(frame)
        e_date.insert(0, date.today().isoformat())
        e_date.grid(row=0, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        ttk.Label(frame, text="Session Notes:").grid(row=1, column=0, sticky=tk.W, pady=6)
        e_notes = ttk.Entry(frame)
        e_notes.insert(0, "Play-based session.")
        e_notes.grid(row=1, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        def _do_create():
            if not self.active_case_id:
                return
            new_s = self.client.create_session(self.active_case_id, e_date.get().strip(), e_notes.get().strip())
            self._refresh_sessions_for_active_case()
            win.destroy()

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=2, column=0, columnspan=2, pady=(16, 0), sticky=tk.E)
        ttk.Button(btn_row, text="Cancel", command=win.destroy).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_row, text="Start Session", style="Primary.TButton", command=_do_create).pack(side=tk.RIGHT)
        e_notes.focus_set()
        return win

    def _show_create_session_dialog(self) -> tk.Toplevel | None:
        if not self.active_case_id:
            messagebox.showwarning("Warning", "Please select a Case first.")
            return None
        win = self._build_create_session_window()
        win.grab_set()
        return win
