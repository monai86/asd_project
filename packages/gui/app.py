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

        self.tree_utterances.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self.tree_utterances.bind("<<TreeviewSelect>>", self._on_utterance_selected)

        # Edit controls
        edit_box = ttk.LabelFrame(self.subtab_table, text="✏️ Edit Selected Utterance", padding=8)
        edit_box.pack(fill=tk.X)

        e_row = ttk.Frame(edit_box)
        e_row.pack(fill=tk.X)
        ttk.Label(e_row, text="Speaker:").pack(side=tk.LEFT, padx=(0, 4))
        self.combo_spk = ttk.Combobox(e_row, values=["CHI", "INV", "MOT", "FAT"], width=6, state="readonly")
        self.combo_spk.pack(side=tk.LEFT, padx=(0, 12))
        self.combo_spk.set("CHI")

        ttk.Label(e_row, text="Text:").pack(side=tk.LEFT, padx=(0, 4))
        self.entry_u_text = ttk.Entry(e_row, font=("Helvetica", 10))
        self.entry_u_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        ttk.Button(e_row, text="🔊 Play Snippet", command=self._play_selected_utterance).pack(side=tk.RIGHT, padx=(0, 6))
        ttk.Button(e_row, text="💾 Save Utterance Edit", command=self._save_utterance_edit).pack(side=tk.RIGHT)

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

        ttk.Button(top_r, text="✨ Generate Draft", command=self._generate_report_draft).pack(side=tk.LEFT, padx=12)
        ttk.Button(top_r, text="✍️ Sign-Off Report", command=self._sign_off_report).pack(side=tk.RIGHT)
        ttk.Button(top_r, text="💾 Export Markdown File", command=self._export_report).pack(side=tk.RIGHT, padx=8)

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

    # --- Actions ---
    def _build_audio_segment_command(
        self,
        audio_path: str,
        start_sec: float | None = None,
        end_sec: float | None = None,
    ) -> list[str] | None:
        """Build platform-specific CLI command to play an audio file or snippet."""
        if not audio_path:
            return None

        if sys.platform == "darwin":
            if start_sec is not None and end_sec is not None and end_sec > start_sec:
                duration = end_sec - start_sec
                return ["afplay", "-t", str(round(duration, 2)), audio_path]
            return ["afplay", audio_path]
        elif sys.platform.startswith("linux"):
            if start_sec is not None and end_sec is not None:
                return ["ffplay", "-nodisp", "-autoexit", "-ss", str(start_sec), "-to", str(end_sec), audio_path]
            return ["aplay", audio_path]
        elif sys.platform == "win32":
            return ["powershell", "-c", f"(New-Object Media.SoundPlayer '{audio_path}').PlaySync();"]
        return None

    def _play_selected_utterance(self) -> None:
        """Play audio snippet for the selected utterance."""
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

        start_sec = selected_u.get("start_time")
        end_sec = selected_u.get("end_time")

        cmd = self._build_audio_segment_command(self.active_audio_path, start_sec, end_sec)
        if not cmd:
            messagebox.showerror("Audio Playback", "Audio playback is not supported on this platform.")
            return

        def _do_play():
            try:
                subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        return self._run_async_task(
            target=_do_play,
            on_success=lambda _: None,
            busy_msg=f"Playing audio snippet #{u_id}...",
        )

    def _play_word_segment(self, start_sec: float, end_sec: float, word_text: str = "") -> threading.Thread | None:
        """Play a precise word audio segment."""
        if not self.active_audio_path or not os.path.exists(self.active_audio_path):
            messagebox.showinfo("Audio Playback", "No audio recording loaded for this session.")
            return None

        cmd = self._build_audio_segment_command(self.active_audio_path, start_sec, end_sec)
        if not cmd:
            messagebox.showerror("Audio Playback", "Audio playback is not supported on this platform.")
            return None

        def _do_play():
            try:
                subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        return self._run_async_task(
            target=_do_play,
            on_success=lambda _: None,
            busy_msg=f"Playing word '{word_text}' ({start_sec:.2f}s - {end_sec:.2f}s)...",
        )

    def _browse_audio_file(self) -> None:
        f_path = filedialog.askopenfilename(
            title="Select Audio or Video File",
            filetypes=[("Media Files", "*.wav *.mp3 *.m4a *.mp4 *.flac *.ogg"), ("All Files", "*.*")],
        )
        if f_path:
            self.entry_audio_path.delete(0, tk.END)
            self.entry_audio_path.insert(0, f_path)

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

        def _do_ingest_audio():
            return self.client.ingest_audio_file(self.active_session_id, f_path)

        def _on_audio_success(transcript: dict[str, Any]) -> None:
            self.active_transcript = transcript
            self.is_findings_stale = False
            messagebox.showinfo(
                "Success",
                f"Audio processed successfully for Session: {self.active_session_id}!\nAcoustic features & transcript extracted.",
            )
            self._refresh_transcript_and_findings()
            self.notebook.select(2)  # Jump to Review tab

        return self._run_async_task(
            target=_do_ingest_audio,
            on_success=_on_audio_success,
            busy_msg=f"Processing audio {Path(f_path).name}... (Extracting F0 & transcribing)",
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

        # Clear existing word timing buttons
        for child in self.container_word_buttons.winfo_children():
            child.destroy()

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
                    command=lambda s=w_s, e=w_e, t=w_txt: self._play_word_segment(s, e, t),
                )
                btn.pack(side=tk.LEFT, padx=2)
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
