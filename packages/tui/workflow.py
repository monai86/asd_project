"""Interactive 5-step clinical workflow controller for LinguaLens TUI."""

from __future__ import annotations

import os
from typing import Any
from rich.console import Console
from rich.prompt import Prompt, Confirm

from packages.tui.client import LinguaLensClient
from packages.tui.ui import (
    console,
    print_banner,
    render_cases_table,
    render_sessions_table,
    render_transcript_review_table,
    render_findings_view,
    render_report_view,
)


class WorkflowRunner:
    """Controls the interactive text-based session navigation."""

    def __init__(self, client: LinguaLensClient):
        self.client = client
        self.active_case_id: str | None = None
        self.active_session_id: str | None = None
        self.active_transcript: dict[str, Any] | None = None

    def start(self, initial_case_id: str | None = None) -> None:
        """Main interaction loop."""
        if initial_case_id:
            self.active_case_id = initial_case_id

        while True:
            console.clear()
            is_online = self.client.check_health()
            print_banner(api_online=is_online, current_step=self._get_current_step_name())

            if not self.active_case_id:
                action = self._cases_menu()
                if action == "exit":
                    console.print("[yellow]Exiting LinguaLens TUI. Goodbye![/yellow]")
                    break
            elif not self.active_session_id:
                action = self._sessions_menu()
                if action == "back":
                    self.active_case_id = None
                elif action == "exit":
                    break
            else:
                action = self._session_workspace_menu()
                if action == "back":
                    self.active_session_id = None
                    self.active_transcript = None
                elif action == "exit":
                    break

    def _get_current_step_name(self) -> str:
        if not self.active_case_id:
            return "Cases Directory"
        if not self.active_session_id:
            return f"Case: {self.active_case_id} > Sessions"
        return f"Session Workspace ({self.active_session_id})"

    # --- Step 1: Cases Menu ---
    def _cases_menu(self) -> str:
        cases = self.client.list_cases()
        render_cases_table(cases)

        console.print("\n[bold cyan]Actions:[/bold cyan]")
        console.print("  [1-N] Select Case Number to open")
        console.print("  [N]   Create [bold green]N[/bold green]ew Case")
        console.print("  [Q]   [bold red]Q[/bold red]uit")

        choice = Prompt.ask("\nChoose an option", default="1")
        if choice.lower() in ("q", "quit", "exit"):
            return "exit"
        if choice.lower() == "n":
            self._create_case_wizard()
            return "continue"

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(cases):
                self.active_case_id = cases[idx]["case_id"]
                return "continue"
        except ValueError:
            pass

        console.print("[red]Invalid selection.[/red]")
        Prompt.ask("Press Enter to continue")
        return "continue"

    def _create_case_wizard(self) -> None:
        console.print("\n[bold green]➕ Create New Child Case[/bold green]")
        child_id = Prompt.ask("Child Identifier / Code", default="C-0301")
        birth_ym = Prompt.ask("Birth Year-Month (YYYY-MM)", default="2021-06")
        lang = Prompt.ask("Primary Language (th/en)", default="th")
        notes = Prompt.ask("Clinical Notes / Referral Reason", default="Speech sound and vocabulary delay.")

        new_case = self.client.create_case(child_id, birth_ym, lang, notes)
        console.print(f"[bold green]✓ Case created successfully: {new_case['case_id']}[/bold green]")
        self.active_case_id = new_case["case_id"]
        Prompt.ask("Press Enter to proceed to Sessions")

    # --- Step 2: Sessions Menu ---
    def _sessions_menu(self) -> str:
        sessions = self.client.list_sessions(self.active_case_id)
        render_sessions_table(self.active_case_id, sessions)

        console.print("\n[bold cyan]Actions:[/bold cyan]")
        if sessions:
            console.print("  [1-N] Select Session Number to open")
        console.print("  [N]   Start [bold green]N[/bold green]ew Therapy Session")
        console.print("  [B]   [bold blue]B[/bold blue]ack to Cases Directory")
        console.print("  [Q]   [bold red]Q[/bold red]uit")

        choice = Prompt.ask("\nChoose an option", default="1" if sessions else "n")
        if choice.lower() in ("q", "quit", "exit"):
            return "exit"
        if choice.lower() in ("b", "back"):
            return "back"
        if choice.lower() == "n":
            self._create_session_wizard()
            return "continue"

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(sessions):
                self.active_session_id = sessions[idx]["session_id"]
                return "continue"
        except ValueError:
            pass

        console.print("[red]Invalid selection.[/red]")
        Prompt.ask("Press Enter to continue")
        return "continue"

    def _create_session_wizard(self) -> None:
        from datetime import date
        today = date.today().isoformat()
        console.print("\n[bold green]➕ Start New Therapy Session[/bold green]")
        s_date = Prompt.ask("Session Date (YYYY-MM-DD)", default=today)
        notes = Prompt.ask("Session Goals / Notes", default="Naturalistic play and language sampling.")

        new_s = self.client.create_session(self.active_case_id, s_date, notes)
        console.print(f"[bold green]✓ Session started: {new_s['session_id']}[/bold green]")
        self.active_session_id = new_s["session_id"]
        Prompt.ask("Press Enter to open Session Workspace")

    # --- Step 3, 4, 5: Session Workspace Hub ---
    def _session_workspace_menu(self) -> str:
        self.active_transcript = self.client.get_session_transcript(self.active_session_id)
        has_transcript = bool(self.active_transcript and self.active_transcript.get("utterances"))
        is_attested = bool(self.active_transcript and self.active_transcript.get("attested"))

        console.print(f"\n[bold]Current Case:[/bold] [cyan]{self.active_case_id}[/cyan] | [bold]Session:[/bold] [cyan]{self.active_session_id}[/cyan]")
        tr_status = "[green]Ingested & Attested[/green]" if is_attested else ("[yellow]Ingested (Needs Review)[/yellow]" if has_transcript else "[red]Not Uploaded[/red]")
        console.print(f"[bold]Transcript Status:[/bold] {tr_status}")

        console.print("\n[bold cyan]Session Workspace Options (5-Step Workflow):[/bold cyan]")
        console.print("  [1] 📥 Ingest / Upload Transcript (.cha, txt, or manual text)")
        console.print("  [2] 🗣️  Human-in-the-Loop Transcript Review & Attestation")
        console.print("  [3] 📊 View Speech-Language Findings & Guideline Linkages")
        console.print("  [4] 📝 Generate / View Progress Report (Draft & Sign-Off)")
        console.print("  [5] 💾 Export Report & Findings to File (.md / .txt)")
        console.print("  [B] 🔙 Back to Sessions List")
        console.print("  [Q] ❌ Quit")

        choice = Prompt.ask("\nSelect Workflow Step", default="2" if has_transcript else "1")
        if choice.lower() in ("q", "quit", "exit"):
            return "exit"
        if choice.lower() in ("b", "back"):
            return "back"
        if choice == "1":
            self._ingest_transcript_flow()
        elif choice == "2":
            self._review_transcript_flow()
        elif choice == "3":
            self._view_findings_flow()
        elif choice == "4":
            self._report_flow()
        elif choice == "5":
            self._export_flow()

        return "continue"

    # --- Step 3 Subflow: Transcript Ingestion ---
    def _ingest_transcript_flow(self) -> None:
        console.print("\n[bold cyan]📥 Transcript Ingestion Mode[/bold cyan]")
        console.print("  [1] Load Sample Thai Play Dialogue (Demo)")
        console.print("  [2] Ingest from local .cha or .txt file")
        console.print("  [3] Paste Raw Dialogue Text")
        console.print("  [4] 🎙️ Ingest from Audio/Video File (.wav, .mp3, .m4a, .mp4) & Extract Acoustic Profile")

        sub = Prompt.ask("Choose Ingestion Source", default="1")
        if sub == "1":
            sample_text = (
                "INV: สวัสดีครับ วันนี้เรามาเล่นของเล่นด้วยกันนะ\n"
                "CHI: เล่น รถ\n"
                "INV: อยากได้รถคันไหนครับ มีสีแดงกับสีน้ำเงิน\n"
                "CHI: แดง รถ แดง ไป\n"
                "INV: รถสีแดงวิ่งเร็วมากเลย บรู๊น บรู๊น\n"
                "CHI: ไป หา แม่\n"
                "INV: เดี๋ยวเล่นเสร็จแล้วไปหาคุณแม่ด้วยกันนะครับ"
            )
            self.active_transcript = self.client.ingest_transcript_text(self.active_session_id, sample_text)
            console.print("[bold green]✓ Sample transcript ingested successfully with 7 utterances![/bold green]")
        elif sub == "2":
            file_path = Prompt.ask("Enter path to .cha or .txt file")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.active_transcript = self.client.ingest_transcript_text(self.active_session_id, content)
                console.print(f"[bold green]✓ Ingested from file: {file_path}[/bold green]")
            else:
                console.print(f"[bold red]File not found: {file_path}[/bold red]")
        elif sub == "3":
            console.print("[dim]Enter dialogue lines (Type 'EOF' on a new line when done):[/dim]")
            lines = []
            while True:
                line = input()
                if line.strip() == "EOF":
                    break
                lines.append(line)
            raw = "\n".join(lines)
            if raw.strip():
                self.active_transcript = self.client.ingest_transcript_text(self.active_session_id, raw)
                console.print("[bold green]✓ Transcript ingested successfully![/bold green]")
        elif sub == "4":
            audio_path = Prompt.ask("Enter path to audio/video file (.wav, .mp3, .m4a, .mp4)")
            if os.path.exists(audio_path):
                try:
                    console.print(f"[cyan]🔄 Processing audio file and extracting acoustic & speech features...[/cyan]")
                    self.active_transcript = self.client.ingest_audio_file(self.active_session_id, audio_path)
                    console.print(f"[bold green]✓ Audio processed successfully! Transcripts & Acoustic Profile extracted.[/bold green]")
                except Exception as exc:
                    console.print(f"[bold red]Failed to process audio: {exc}[/bold red]")
            else:
                console.print(f"[bold red]File not found: {audio_path}[/bold red]")

        Prompt.ask("Press Enter to continue")

    # --- Step 4 Subflow: Human-in-the-loop Review ---
    def _review_transcript_flow(self) -> None:
        if not self.active_transcript or not self.active_transcript.get("utterances"):
            console.print("[yellow]⚠️ No transcript available. Please ingest a transcript first (Step 1).[/yellow]")
            Prompt.ask("Press Enter to continue")
            return

        while True:
            console.clear()
            print_banner(api_online=self.client.check_health(), current_step="Transcript Review")
            utterances = self.active_transcript["utterances"]
            is_attested = self.active_transcript.get("attested", False)
            render_transcript_review_table(utterances, attested=is_attested)

            console.print("\n[bold cyan]Review Actions:[/bold cyan]")
            console.print("  [1-N] Select Utterance Number to Edit Text/Speaker")
            if not is_attested:
                console.print("  [S]   [bold green]S[/bold green]ign-off & Attest Transcript (Clinician Verification)")
            console.print("  [B]   [bold blue]B[/bold blue]ack to Workspace Hub")

            choice = Prompt.ask("\nSelect action", default="s" if not is_attested else "b")
            if choice.lower() in ("b", "back"):
                break
            if choice.lower() in ("s", "signoff", "attest") and not is_attested:
                therapist_name = Prompt.ask("Clinician / Therapist Name", default="Kru Aum (SLP)")
                self.active_transcript = self.client.attest_transcript(self.active_transcript["transcript_id"], therapist_name)
                console.print(f"[bold green]✓ Transcript successfully attested by {therapist_name}![/bold green]")
                Prompt.ask("Press Enter to continue")
                break

            try:
                u_idx = int(choice) - 1
                if 0 <= u_idx < len(utterances):
                    u = utterances[u_idx]
                    console.print(f"\n[bold]Editing Utterance #{u_idx + 1}[/bold]")
                    new_spk = Prompt.ask("Speaker (CHI/INV/MOT/FAT)", default=u.get("speaker", "CHI"))
                    new_text = Prompt.ask("Utterance Text", default=u.get("text", ""))
                    self.active_transcript = self.client.update_utterance(
                        self.active_transcript["transcript_id"],
                        u["id"],
                        new_text,
                        new_spk,
                    )
                    console.print("[green]✓ Utterance updated.[/green]")
                    Prompt.ask("Press Enter to refresh")
            except ValueError:
                pass

    # --- Step 5 Subflow: Findings ---
    def _view_findings_flow(self) -> None:
        findings = self.client.get_findings(self.active_session_id)
        console.clear()
        print_banner(api_online=self.client.check_health(), current_step="Clinical Findings")
        render_findings_view(findings)
        Prompt.ask("\nPress Enter to return to Session Workspace")

    # --- Step 5 Subflow: Reports ---
    def _report_flow(self) -> None:
        console.clear()
        print_banner(api_online=self.client.check_health(), current_step="Progress Report")

        # Check existing reports
        report_data = None
        for r in self.client._mock_data["reports"].values():
            if r.get("session_id") == self.active_session_id:
                report_data = r
                break

        if not report_data:
            console.print("[yellow]No report exists yet for this session.[/yellow]")
            if Confirm.ask("Would you like to generate a Clinical Progress Report Draft now?", default=True):
                notes = Prompt.ask("Therapist focus / clinical observations", default="Focus on phrase expansion.")
                report_data = self.client.draft_report(self.active_session_id, notes)
                console.print("[bold green]✓ Progress report draft created![/bold green]")
            else:
                return

        render_report_view(report_data)

        if report_data.get("status") != "Signed Off":
            if Confirm.ask("\nWould you like to complete Digital Clinician Sign-off?", default=True):
                signer = Prompt.ask("Therapist Name & Title", default="Kru Aum (SLP)")
                report_data = self.client.sign_off_report(report_data["report_id"], signer)
                console.print(f"[bold green]✓ Report signed off! SHA-256 Hash: {report_data.get('sha256_hash')}[/bold green]")
                render_report_view(report_data)

        Prompt.ask("\nPress Enter to return to Session Workspace")

    # --- Step 5 Export Subflow ---
    def _export_flow(self) -> None:
        findings = self.client.get_findings(self.active_session_id)
        report_data = None
        for r in self.client._mock_data["reports"].values():
            if r.get("session_id") == self.active_session_id:
                report_data = r
                break

        out_path = f"reports/export_{self.active_session_id}.md"
        os.makedirs("reports", exist_ok=True)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# LinguaLens Clinical Progress Report\n\n")
            f.write(f"- **Case ID:** {self.active_case_id}\n")
            f.write(f"- **Session ID:** {self.active_session_id}\n")
            f.write(f"- **Exported At:** 2026-08-16\n")
            f.write(f"- **Clinical Safety Note:** Research/educational decision support prototype; non-diagnostic.\n\n")

            f.write(f"## 1. Speech-Language Metrics\n\n")
            metrics = findings.get("metrics", {})
            for k, v in metrics.items():
                f.write(f"- **{k}:** {v}\n")

            f.write(f"\n## 2. Clinical Guideline Mappings\n\n")
            for g in findings.get("guideline_links", []):
                f.write(f"- **{g.get('construct')}:** {g.get('status')} ({g.get('description')})\n")

            if report_data:
                f.write(f"\n## 3. Therapist Clinical Narrative\n\n")
                f.write(f"{report_data.get('narrative', '')}\n\n")
                f.write(f"### Recommendations & Goals\n\n")
                f.write(f"{report_data.get('recommendations', '')}\n\n")
                f.write(f"- **Sign-Off Status:** {report_data.get('status')}\n")
                f.write(f"- **Signed By:** {report_data.get('signed_by')}\n")
                f.write(f"- **Integrity Hash:** `{report_data.get('sha256_hash', '-')}`\n")

        console.print(f"[bold green]✓ Full Session & Report exported to file: [cyan]{out_path}[/cyan][/bold green]")
        Prompt.ask("Press Enter to return")
