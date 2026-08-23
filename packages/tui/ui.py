"""Rich-based UI rendering components and helpers for LinguaLens TUI."""

from __future__ import annotations

from typing import Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, Confirm

console = Console()


def print_banner(api_online: bool = False, current_step: str = "Dashboard") -> None:
    """Render top application banner with clinical safety boundaries."""
    status_badge = "[bold green]● API Connected[/bold green]" if api_online else "[bold yellow]○ Offline / Local Mock[/bold yellow]"
    
    header_text = Text()
    header_text.append("LINGUALENS ", style="bold cyan")
    header_text.append("v1.6.3 ", style="bold white")
    header_text.append("— Speech-Language Decision Support TUI\n", style="dim white")
    header_text.append("Status: ", style="bold")
    header_text.append_text(Text.from_markup(status_badge))
    header_text.append(f"  |  Workspace: [bold magenta]{current_step}[/bold magenta]\n", style="white")
    header_text.append("⚠️  Research/Education Prototype Only. Non-diagnostic. Human-in-the-loop sign-off required.", style="dim italic yellow")

    console.print(Panel(header_text, border_style="cyan", padding=(0, 2)))


def print_status_badge(status_str: str) -> str:
    """Format status with color styling."""
    status_lower = status_str.lower()
    if "signed off" in status_lower or "reported" in status_lower or "attested" in status_lower:
        return f"[bold green]{status_str}[/bold green]"
    if "needs review" in status_lower or "pending" in status_lower:
        return f"[bold yellow]{status_str}[/bold yellow]"
    if "draft" in status_lower or "intake" in status_lower:
        return f"[bold blue]{status_str}[/bold blue]"
    return f"[white]{status_str}[/white]"


def render_cases_table(cases: list[dict[str, Any]]) -> None:
    """Render cases list table."""
    table = Table(title="📋 Case Directory", border_style="cyan", show_lines=True)
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Case ID", style="bold white")
    table.add_column("Child ID", style="green")
    table.add_column("Age (Mo)", justify="center")
    table.add_column("Lang", justify="center")
    table.add_column("Sessions", justify="center")
    table.add_column("Clinical Notes", style="dim")

    for i, c in enumerate(cases, 1):
        table.add_row(
            str(i),
            c.get("case_id", "-"),
            c.get("child_id", "-"),
            str(c.get("age_months", "-")),
            c.get("primary_language", "th").upper(),
            str(c.get("session_count", 0)),
            c.get("clinical_notes", "")[:40] + ("..." if len(c.get("clinical_notes", "")) > 40 else ""),
        )
    console.print(table)


def render_sessions_table(case_id: str, sessions: list[dict[str, Any]]) -> None:
    """Render sessions table for a case."""
    table = Table(title=f"🗓️ Sessions for Case: [bold cyan]{case_id}[/bold cyan]", border_style="cyan", show_lines=True)
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Session ID", style="bold white")
    table.add_column("Date", style="white")
    table.add_column("Sess #", justify="center")
    table.add_column("Workflow Status", style="bold")
    table.add_column("Transcript", justify="center")
    table.add_column("Report", justify="center")

    for i, s in enumerate(sessions, 1):
        tr_badge = "[green]✓ Ready[/green]" if s.get("transcript_id") else "[dim]None[/dim]"
        rep_badge = "[green]✓ Ready[/green]" if s.get("report_id") else "[dim]None[/dim]"
        table.add_row(
            str(i),
            s.get("session_id", "-"),
            s.get("session_date", "-"),
            str(s.get("session_number", 1)),
            print_status_badge(s.get("status", "Intake")),
            tr_badge,
            rep_badge,
        )
    console.print(table)


def render_transcript_review_table(utterances: list[dict[str, Any]], attested: bool = False) -> None:
    """Render transcript review utterance list."""
    status_note = "[bold green]Signed Off / Attested[/bold green]" if attested else "[bold yellow]Pending Clinician Review[/bold yellow]"
    table = Table(title=f"🗣️ Transcript Human-in-the-Loop Review ({status_note})", border_style="cyan", show_lines=True)
    table.add_column("#", justify="right", style="cyan", width=4)
    table.add_column("Speaker", justify="center", width=10)
    table.add_column("Time (s)", justify="center", width=12, style="dim")
    table.add_column("Utterance Text", style="white")
    table.add_column("QA Flags", style="bold yellow", width=18)

    for i, u in enumerate(utterances, 1):
        spk = u.get("speaker", "CHI")
        spk_style = "[bold green]CHI (Child)[/bold green]" if spk == "CHI" else f"[bold blue]{spk}[/bold blue]"
        time_str = f"{u.get('start_time', 0.0):.1f} - {u.get('end_time', 0.0):.1f}"
        flags = ", ".join(u.get("qa_flags", [])) or "[dim green]✓ Clean[/dim green]"
        table.add_row(
            str(i),
            spk_style,
            time_str,
            u.get("text", ""),
            flags,
        )
    console.print(table)


def render_findings_view(findings: dict[str, Any]) -> None:
    """Render speech-language features and guideline constructs."""
    metrics = findings.get("metrics", {})
    links = findings.get("guideline_links", [])

    m_table = Table(title="📊 Speech-Language & ML Feature Summary", border_style="green", show_lines=True)
    m_table.add_column("Metric", style="bold cyan")
    m_table.add_column("Value", style="bold white", justify="center")
    m_table.add_column("Description", style="dim")

    m_table.add_row("MLU-words (Mean Length of Utterance)", str(metrics.get("mlu_words", "-")), "ความยาวประโยคเฉลี่ย (จำนวนคำต่อประโยค)")
    m_table.add_row("Type-Token Ratio (TTR)", str(metrics.get("ttr", "-")), "ความหลากหลายของคลังคำศัพท์ (Lexical Diversity)")
    m_table.add_row("Total Child Utterances", str(metrics.get("total_child_utterances", "-")), "จำนวนประโยคพูดของเด็กทั้งหมด")
    m_table.add_row("Intelligibility Rate", f"{float(metrics.get('intelligibility_rate', 1.0))*100:.0f}%" if "intelligibility_rate" in metrics else "-", "อัตราความชัดเจนของคำพูด")
    m_table.add_row("Turn-Taking Ratio", str(metrics.get("turn_taking_ratio", "-")), "อัตราการผลัดกันพูดในบทสนทนา")

    if "f0_median_hz" in metrics:
        m_table.add_row("Pitch Median (F0 in Hz)", f"{metrics.get('f0_median_hz')} Hz", "ระดับความถี่เสียงหลัก (Fundamental Frequency)")
        m_table.add_row("Pitch Variability (F0 IQR in Hz)", f"{metrics.get('f0_iqr_hz')} Hz", "ความแปรผันของระดับเสียง (Prosody Modulation)")
        m_table.add_row("Voiced Speech Ratio", f"{metrics.get('voiced_ratio_pct')}%", "สัดส่วนของช่วงเวลาที่มีเสียงพูด (Voiced)")
        m_table.add_row("Pause Ratio", f"{metrics.get('pause_ratio_pct')}%", "สัดส่วนของช่วงเวลาหยุดพัก/เงียบ (Pauses)")
        m_table.add_row("Audio Duration", f"{metrics.get('audio_duration_sec')} s", "ความยาวของคลิปเสียง/วิดีโอ")

    console.print(m_table)

    if links:
        g_table = Table(title="📑 Clinical Guideline Mappings", border_style="magenta", show_lines=True)
        g_table.add_column("Clinical Construct", style="bold magenta")
        g_table.add_column("Observation Status", style="bold white")
        g_table.add_column("Evidence Summary", style="white")

        for g in links:
            g_table.add_row(g.get("construct", "-"), g.get("status", "-"), g.get("description", "-"))
        console.print(g_table)


def render_report_view(report: dict[str, Any]) -> None:
    """Render clinical report draft or signed-off progress report."""
    status = report.get("status", "Draft")
    signed_by = report.get("signed_by") or report.get("therapist_name") or "Not Signed"
    signed_at = report.get("signed_at") or "-"
    sha = report.get("sha256_hash", "Pending sign-off")

    panel_content = Text()
    panel_content.append(f"Report ID: {report.get('report_id', '-')}  |  Status: {print_status_badge(status)}\n", style="bold")
    panel_content.append(f"Signer: {signed_by}  |  Signed At: {signed_at}\n", style="dim")
    if sha != "Pending sign-off":
        panel_content.append(f"Integrity SHA-256: {sha[:16]}...{sha[-16:]}\n\n", style="bold green")
    else:
        panel_content.append("\n")

    panel_content.append("📝 Clinical Narrative (LSA Summary):\n", style="bold cyan")
    panel_content.append(f"{report.get('narrative', '-')}\n\n", style="white")
    panel_content.append("🎯 Recommendations & Therapy Goals:\n", style="bold cyan")
    panel_content.append(f"{report.get('recommendations', '-')}\n", style="white")

    console.print(Panel(panel_content, title="📄 Progress Report Summary", border_style="blue", padding=(1, 2)))
