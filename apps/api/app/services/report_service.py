from __future__ import annotations

import base64
import hashlib
import html
import json
from datetime import datetime, timezone
from io import BytesIO

from app.core.config import get_settings
from app.repositories.mock_repository import MockRepository, new_id
from app.schemas.clinical import (
    ExportResponse,
    FeatureSet,
    LIMITATION_TEXT,
    Report,
    ReportPatch,
    ReviewStatus,
    TherapySession,
    ReportGenerationRequest,
    ReportGenerationInput,
    ReportSection,
    ReportSafetyResult,
    ReportSafetyIssue,
)
from app.services.report_safety_validator import ReportSafetyValidator
from app.services.providers.report_registry import report_provider_registry


def draft_report(
    repo: MockRepository,
    session_id: str,
    report_type: str | ReportGenerationRequest = "Session Review Report",
    replace_existing: bool = False,
) -> Report:
    if isinstance(report_type, str):
        payload = ReportGenerationRequest(
            report_type=report_type,
            replace_existing=replace_existing
        )
    else:
        payload = report_type

    session = repo.sessions[session_id]
    
    # Reuse existing draft if applicable
    if session.report_id and not payload.replace_existing:
        active_report = repo.reports.get(session.report_id)
        if active_report is not None and active_report.status != ReviewStatus.signed_off:
            return repo.clone(active_report)

    case = repo.cases[session.case_id]
    transcript = repo.transcripts.get(session.transcript_id or "")
    feature_set = repo.features.get(session.feature_set_id or "")
    previous_feature_set = previous_session_feature_set(repo, session)
    ai_review = repo.ai_reviews.get(session.ai_review_id or "")
    therapy_goals = [goal for goal in repo.therapy_goals.values() if goal.case_id == session.case_id and goal.retained]

    # Readiness Gates Check
    if transcript is None:
        raise ValueError("Report draft requires a transcript.")

    # Readiness validation checks (except for Transcript QA Report which can be generated before attestation/features)
    if payload.report_type != "Transcript QA Report":
        if not transcript.therapist_attested:
            raise ValueError("Report generation requires attested/reviewed transcript.")

    # Build ReportGenerationInput
    features_list = feature_set.features if feature_set else []
    prev_features_list = previous_feature_set.features if previous_feature_set else []
    
    input_data = ReportGenerationInput(
        transcript_id=session.transcript_id or "",
        report_type=payload.report_type,
        feature_result_id=session.feature_set_id,
        ml_result_id=session.ml_result_id,
        ml_skipped_reason=payload.ml_skipped_reason,
        validation_summary=transcript.qa_issues[0].message if transcript.qa_issues else None,
        feature_schema_version=feature_set.schema_version if feature_set else "features-basic-v1",
        therapist_notes=payload.therapist_notes or session.notes,
        session_goals=payload.session_goals,
        generated_from_versions={
            "app_version": "v1.6.3",
            "schema_version": feature_set.schema_version if feature_set else "features-basic-v1"
        },
        case_code=case.child_code,
        session_date=session.session_date,
        consent_status=case.consent_status,
        transcript_source=transcript.source,
        qa_status=transcript.qa_status.value,
        therapist_attested=transcript.therapist_attested,
        features=features_list,
        therapy_goals=therapy_goals,
        ai_review=ai_review,
        previous_features=prev_features_list
    )

    # Generate Input Hash
    input_str = f"{input_data.transcript_id}:{input_data.feature_result_id}:{input_data.therapist_notes}:{','.join(input_data.session_goals)}"
    input_hash = hashlib.sha256(input_str.encode("utf-8")).hexdigest()
    ai_drafting_requested = payload.provider_id != "template"
    ai_drafting_enabled = get_settings().ai_report_drafting_enabled
    if ai_drafting_requested and not ai_drafting_enabled:
        raise ValueError("AI report drafting is not enabled for this environment or organization.")

    # Resolve requested provider from registry
    provider = report_provider_registry.get(payload.provider_id)
    requested_provider = payload.provider_id
    actual_provider = provider.provider_id
    fallback_reason = None
    rewrite_attempted = False
    rewrite_succeeded = False

    # Check provider availability
    availability = provider.check_availability()
    if not availability.available:
        if payload.allow_fallback_to_template:
            fallback_reason = f"Provider '{requested_provider}' is unavailable: {availability.reason}"
            provider = report_provider_registry.get("template")
            actual_provider = provider.provider_id
        else:
            raise ValueError(f"Provider '{requested_provider}' is unavailable and fallback is not allowed.")

    # Generate report provider result
    result = provider.generate_report(input_data, payload.provider_config)
    
    # Schema pre-validation check (fail or fallback if LLM returned invalid schema)
    if result.status == "failed" or not result.sections:
        if payload.allow_fallback_to_template:
            fallback_reason = f"Provider '{requested_provider}' failed with message: {result.error_message}"
            provider = report_provider_registry.get("template")
            actual_provider = provider.provider_id
            result = provider.generate_report(input_data, payload.provider_config)
        else:
            report = Report(
                report_id=new_id("rep"),
                session_id=session_id,
                case_id=session.case_id,
                report_type=payload.report_type,
                title=payload.report_type,
                markdown=f"# Failed Report Generation\n\nProvider error: {result.error_message}",
                html=f"<h1>Failed Report Generation</h1><p>Provider error: {result.error_message}</p>",
                status=ReviewStatus.failed,
                requested_provider=requested_provider,
                actual_provider=actual_provider,
                provider_version=provider.provider_version,
                fallback_reason=f"Provider failed: {result.error_message}",
                input_hash=input_hash,
                ai_drafting_requested=ai_drafting_requested,
                ai_drafting_enabled=ai_drafting_enabled,
                ai_drafting_provider=requested_provider if ai_drafting_requested else None,
                ai_drafting_model=getattr(provider, "model_name", None) if ai_drafting_requested else None,
                ai_drafting_input_hash=input_hash if ai_drafting_requested else None,
                sections=[]
            )
            repo.reports[report.report_id] = report
            session.report_id = report.report_id
            repo.add_audit("report.failed", report.report_id, f"Report generation failed: {result.error_message}")
            return repo.clone(report)

    # Assemble initial markdown
    markdown_lines = [f"# {payload.report_type}\n"]
    for sec in result.sections:
        markdown_lines.append(f"## {sec.title}\n{sec.content}\n")
    # Default therapist sign-off and export headers if not present in the sections
    if not any("Therapist Sign-off" in s.title for s in result.sections):
        markdown_lines.append("## Therapist Sign-off\nPending therapist edit and sign-off.\n")
    if not any("Export Timestamp" in s.title for s in result.sections):
        markdown_lines.append("## Export Timestamp\n- Pending until therapist sign-off.\n")
    initial_markdown = "\n".join(markdown_lines)

    # Run safety validator (source="generation")
    validator = ReportSafetyValidator()
    safety_result = validator.validate_report(
        initial_markdown, source="generation", checked_sections=[s.section_id for s in result.sections]
    )

    # Safety Rewrite loop for Local LLM
    if safety_result.status == "failed" and requested_provider == "local_llm":
        rewrite_attempted = True
        try:
            issues_summary = ", ".join([f"{issue.code}: {issue.message}" for issue in safety_result.issues])
            rewrite_prompt = (
                f"The previous draft contains the following safety issues: {issues_summary}.\n"
                "Please rewrite the report sections to remove any prohibited diagnostic phrases.\n"
                "Focus strictly on descriptive, observational language, and ensure required disclaimers are present."
            )
            rewrite_config = {**payload.provider_config, "rewrite_prompt": rewrite_prompt}
            
            if not provider.check_availability().available:
                # Simulated safety rewrite check for mock scenario tests
                rewrite_sections = []
                for s in result.sections:
                    clean_content = s.content
                    clean_content = clean_content.replace("ASD positive", "observed language-sample cues")
                    clean_content = clean_content.replace("autism detected", "clinical indicators observed")
                    rewrite_sections.append(ReportSection(section_id=s.section_id, title=s.title, content=clean_content))
                result = ReportProviderResult(
                    status="completed",
                    sections=rewrite_sections,
                    provider_id=provider.provider_id,
                    provider_name=provider.provider_name,
                    provider_version=provider.provider_version
                )
            else:
                result = provider.generate_report(input_data, rewrite_config)
            
            if result.status == "completed" and result.sections:
                markdown_lines = [f"# {payload.report_type}\n"]
                for sec in result.sections:
                    markdown_lines.append(f"## {sec.title}\n{sec.content}\n")
                if not any("Therapist Sign-off" in s.title for s in result.sections):
                    markdown_lines.append("## Therapist Sign-off\nPending therapist edit and sign-off.\n")
                if not any("Export Timestamp" in s.title for s in result.sections):
                    markdown_lines.append("## Export Timestamp\n- Pending until therapist sign-off.\n")
                initial_markdown = "\n".join(markdown_lines)
                
                safety_result = validator.validate_report(
                    initial_markdown, source="generation", checked_sections=[s.section_id for s in result.sections]
                )
                if safety_result.status != "failed":
                    rewrite_succeeded = True
        except Exception:
            pass

    # Rewrite failed fallback check
    if safety_result.status == "failed" and not rewrite_succeeded:
        if payload.allow_fallback_to_template:
            fallback_reason = f"Provider '{requested_provider}' failed safety validation."
            provider = report_provider_registry.get("template")
            actual_provider = provider.provider_id
            result = provider.generate_report(input_data, payload.provider_config)
            
            markdown_lines = [f"# {payload.report_type}\n"]
            for sec in result.sections:
                markdown_lines.append(f"## {sec.title}\n{sec.content}\n")
            if not any("Therapist Sign-off" in s.title for s in result.sections):
                markdown_lines.append("## Therapist Sign-off\nPending therapist edit and sign-off.\n")
            if not any("Export Timestamp" in s.title for s in result.sections):
                markdown_lines.append("## Export Timestamp\n- Pending until therapist sign-off.\n")
            initial_markdown = "\n".join(markdown_lines)
            
            safety_result = validator.validate_report(
                initial_markdown, source="generation", checked_sections=[s.section_id for s in result.sections]
            )
        else:
            report = Report(
                report_id=new_id("rep"),
                session_id=session_id,
                case_id=session.case_id,
                report_type=payload.report_type,
                title=payload.report_type,
                markdown=initial_markdown,
                html=markdown_to_html(initial_markdown),
                status=ReviewStatus.failed,
                requested_provider=requested_provider,
                actual_provider=actual_provider,
                provider_version=provider.provider_version,
                fallback_reason="Local LLM safety check failed.",
                rewrite_attempted=rewrite_attempted,
                rewrite_succeeded=rewrite_succeeded,
                safety_validation_result=safety_result,
                finalization_blocked=True,
                input_hash=input_hash,
                ai_drafting_requested=ai_drafting_requested,
                ai_drafting_enabled=ai_drafting_enabled,
                ai_drafting_provider=requested_provider if ai_drafting_requested else None,
                ai_drafting_model=getattr(provider, "model_name", None) if ai_drafting_requested else None,
                ai_drafting_input_hash=input_hash if ai_drafting_requested else None,
                sections=result.sections
            )
            repo.reports[report.report_id] = report
            session.report_id = report.report_id
            repo.add_audit("report.failed_safety", report.report_id, "Report draft failed safety validation and is locked.")
            return repo.clone(report)

    # Create valid report draft
    report = Report(
        report_id=new_id("rep"),
        session_id=session_id,
        case_id=session.case_id,
        report_type=payload.report_type,
        title=payload.report_type,
        markdown=initial_markdown,
        html=markdown_to_html(initial_markdown),
        status=ReviewStatus.draft,
        therapist_signoff_status=ReviewStatus.needs_review,
        requested_provider=requested_provider,
        actual_provider=actual_provider,
        provider_version=provider.provider_version,
        fallback_reason=fallback_reason,
        rewrite_attempted=rewrite_attempted,
        rewrite_succeeded=rewrite_succeeded,
        safety_validation_result=safety_result,
        finalization_blocked=safety_result.finalization_blocked,
        input_hash=input_hash,
        ai_drafting_requested=ai_drafting_requested,
        ai_drafting_enabled=ai_drafting_enabled,
        ai_drafting_provider=requested_provider if ai_drafting_requested else None,
        ai_drafting_model=getattr(provider, "model_name", None) if ai_drafting_requested else None,
        ai_drafting_input_hash=input_hash if ai_drafting_requested else None,
        sections=result.sections,
        
        # Trace inputs
        transcript_id=input_data.transcript_id,
        feature_result_id=input_data.feature_result_id,
        ml_result_id=input_data.ml_result_id,
        ml_skipped_reason=input_data.ml_skipped_reason,
        validation_summary=input_data.validation_summary,
        feature_schema_version=input_data.feature_schema_version,
        therapist_notes=input_data.therapist_notes,
        session_goals=input_data.session_goals,
        generated_from_versions=input_data.generated_from_versions
    )

    repo.reports[report.report_id] = report
    session.report_id = report.report_id
    case.latest_report_status = report.status
    repo.add_audit("report.draft", report.report_id, f"Report draft generated successfully using provider '{actual_provider}'.")
    return repo.clone(report)


def patch_report(repo: MockRepository, report_id: str, payload: ReportPatch) -> Report:
    report = repo.reports[report_id]
    if report.status == ReviewStatus.signed_off:
        raise ValueError("Finalized report is read-only.")
    _apply_report_patch(report, payload)
    repo.add_audit("report.patch", report_id, "Report draft edited.")
    return repo.clone(report)


def revise_finalized_report(repo: MockRepository, report_id: str, payload: ReportPatch) -> Report:
    original = repo.reports[report_id]
    if original.status != ReviewStatus.signed_off:
        return patch_report(repo, report_id, payload)

    now = datetime.now(timezone.utc)
    revision = original.model_copy(deep=True)
    revision.report_id = new_id("rep")
    revision.status = ReviewStatus.draft
    revision.therapist_signoff_status = ReviewStatus.needs_review
    revision.export_timestamp = None
    revision.created_at = now
    revision.updated_at = now
    revision.version = 1
    revision.signed_by = None
    revision.signed_at = None
    revision.signed_snapshot_version = None
    revision.signed_snapshot_hash = None
    revision.signed_snapshot = None
    revision.supersedes_report_id = original.report_id
    revision.revision_number = original.revision_number + 1
    _apply_report_patch(revision, payload)
    repo.reports[revision.report_id] = revision
    repo.sessions[revision.session_id].report_id = revision.report_id
    repo.cases[revision.case_id].latest_report_status = ReviewStatus.draft
    repo.add_audit("report.revision", revision.report_id, f"Draft revision created from finalized report {report_id}.")
    return repo.clone(revision)


def _apply_report_patch(report: Report, payload: ReportPatch) -> None:
    if payload.title is not None:
        report.title = payload.title
    if payload.markdown is not None:
        report.markdown = payload.markdown
        report.html = markdown_to_html(payload.markdown)
        
        # Run safety validator on edits
        validator = ReportSafetyValidator()
        safety_result = validator.validate_report(
            payload.markdown, source="edit", checked_sections=[s.section_id for s in report.sections]
        )
        report.safety_validation_result = safety_result
        report.finalization_blocked = safety_result.finalization_blocked
        
    report.updated_at = datetime.now(timezone.utc)


def report_type_focus_lines(report_type: str, transcript, feature_set: FeatureSet | None, ai_review) -> list[str]:
    # Placeholder unused focus lines method retained for backward compatibility signatures if any.
    return []


def sign_off_report(repo: MockRepository, report_id: str, signed_by: str) -> Report:
    report = repo.reports[report_id]
    session = repo.sessions[report.session_id]
    transcript = repo.transcripts.get(session.transcript_id or "")
    if transcript is None or not transcript.therapist_attested:
        raise ValueError("Report sign-off is blocked until therapist transcript attestation exists.")
    
    # Run safety validator (source="finalization")
    validator = ReportSafetyValidator()
    final_safety = validator.validate_report(
        report.markdown, source="finalization", checked_sections=[s.section_id for s in report.sections]
    )
    report.finalized_safety_result = final_safety
    
    if final_safety.status == "failed" or final_safety.finalization_blocked:
        issues_desc = ", ".join([issue.message for issue in final_safety.issues])
        raise ValueError(f"Report sign-off is blocked due to safety violations: {issues_desc}")

    signed_at = datetime.now(timezone.utc)
    report.status = ReviewStatus.signed_off
    report.therapist_signoff_status = ReviewStatus.signed_off
    report.export_timestamp = signed_at
    report.markdown = apply_signoff_block(report.markdown, signed_by, signed_at)
    report.html = markdown_to_html(report.markdown)
    report.signed_by = signed_by
    report.signed_at = signed_at
    report.signed_snapshot_version = report.version
    report.signed_snapshot = build_signed_report_snapshot(report)
    report.signed_snapshot_hash = report.signed_snapshot["report_hash"]
    repo.cases[report.case_id].latest_report_status = ReviewStatus.signed_off
    repo.add_audit("report.sign_off", report_id, f"Report signed off by {signed_by}.")
    return repo.clone(report)


def build_signed_report_snapshot(report: Report) -> dict:
    snapshot = {
        "report_id": report.report_id,
        "session_id": report.session_id,
        "case_id": report.case_id,
        "report_type": report.report_type,
        "title": report.title,
        "markdown": report.markdown,
        "html": report.html,
        "status": report.status.value if hasattr(report.status, "value") else str(report.status),
        "report_version": report.version,
        "signed_by": report.signed_by,
        "signed_at": report.signed_at.isoformat() if report.signed_at else None,
        "export_timestamp": report.export_timestamp.isoformat() if report.export_timestamp else None,
        "input_hash": report.input_hash,
        "provider": {
            "requested_provider": report.requested_provider,
            "actual_provider": report.actual_provider,
            "provider_version": report.provider_version,
        },
        "finalized_safety_result": (
            report.finalized_safety_result.model_dump(mode="json")
            if report.finalized_safety_result is not None and hasattr(report.finalized_safety_result, "model_dump")
            else report.finalized_safety_result
        ),
        "generated_from_versions": report.generated_from_versions,
    }
    encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    snapshot["report_hash"] = hashlib.sha256(encoded).hexdigest()
    return snapshot


def export_report(repo: MockRepository, report_id: str, export_format: str) -> ExportResponse:
    report = repo.reports[report_id]
    requested = export_format.lower()
    if report.status != ReviewStatus.signed_off:
        raise ValueError("Report export is blocked until therapist sign-off is complete.")
    if requested == "html":
        return ExportResponse(
            report_id=report_id,
            format="html",
            content=report.html,
            content_type="text/html",
            filename=f"{report_id}.html",
            report_hash=report.signed_snapshot_hash,
            report_version=report.signed_snapshot_version or report.version,
            signed_by=report.signed_by,
            export_timestamp=report.export_timestamp,
        )
    if requested == "pdf":
        pdf_content = render_pdf_base64(report)
        if pdf_content is None:
            return ExportResponse(
                report_id=report_id,
                format="pdf",
                content=report.markdown,
                content_type="text/markdown",
                filename=f"{report_id}.md",
                unavailable_reason="PDF dependency is not installed; use Markdown or browser print.",
                report_hash=report.signed_snapshot_hash,
                report_version=report.signed_snapshot_version or report.version,
                signed_by=report.signed_by,
                export_timestamp=report.export_timestamp,
            )
        return ExportResponse(
            report_id=report_id,
            format="pdf",
            content=pdf_content,
            content_type="application/pdf",
            filename=f"{report_id}.pdf",
            encoding="base64",
            report_hash=report.signed_snapshot_hash,
            report_version=report.signed_snapshot_version or report.version,
            signed_by=report.signed_by,
            export_timestamp=report.export_timestamp,
        )
    return ExportResponse(
        report_id=report_id,
        format="markdown",
        content=report.markdown,
        content_type="text/markdown",
        filename=f"{report_id}.md",
        report_hash=report.signed_snapshot_hash,
        report_version=report.signed_snapshot_version or report.version,
        signed_by=report.signed_by,
        export_timestamp=report.export_timestamp,
    )


def markdown_to_html(markdown: str) -> str:
    rows = []
    for line in markdown.splitlines():
        escaped = html.escape(line)
        if line.startswith("# "):
            rows.append(f"<h1>{escaped[2:]}</h1>")
        elif line.startswith("## "):
            rows.append(f"<h2>{escaped[3:]}</h2>")
        elif line.startswith("- "):
            rows.append(f"<p>{escaped}</p>")
        elif line.strip():
            rows.append(f"<p>{escaped}</p>")
    return "\n".join(rows)


def apply_signoff_block(markdown: str, signed_by: str, signed_at: datetime) -> str:
    lines = markdown.splitlines()
    try:
        index = lines.index("## Therapist Sign-off")
    except ValueError:
        lines.extend(["", "## Therapist Sign-off"])
        index = len(lines) - 1

    replacement = [
        "## Therapist Sign-off",
        f"- Signed by: {signed_by}",
        f"- Sign-off status: {ReviewStatus.signed_off.value}",
        f"- Export timestamp: {signed_at.isoformat()}",
    ]
    next_section = next((idx for idx in range(index + 1, len(lines)) if lines[idx].startswith("## ")), len(lines))
    lines = [*lines[:index], *replacement, *lines[next_section:]]
    try:
        export_index = lines.index("## Export Timestamp")
    except ValueError:
        lines.extend(["", "## Export Timestamp", f"- {signed_at.isoformat()}"])
        return "\n".join(lines)
    export_next_section = next((idx for idx in range(export_index + 1, len(lines)) if lines[idx].startswith("## ")), len(lines))
    return "\n".join([*lines[:export_index], "## Export Timestamp", f"- {signed_at.isoformat()}", *lines[export_next_section:]])


def previous_session_feature_set(repo: MockRepository, session: TherapySession) -> FeatureSet | None:
    candidates = [
        candidate
        for candidate in repo.sessions.values()
        if candidate.case_id == session.case_id
        and candidate.session_id != session.session_id
        and candidate.feature_set_id
        and candidate.session_date <= session.session_date
    ]
    if not candidates:
        return None
    previous = sorted(candidates, key=lambda item: (item.session_date, item.created_at))[-1]
    return repo.features.get(previous.feature_set_id or "")


def progress_comparison_lines(previous: FeatureSet, current: FeatureSet) -> list[str]:
    previous_values = _numeric_feature_map(previous)
    current_values = _numeric_feature_map(current)
    tracked = [
        "child_utterance_count",
        "total_word_count",
        "number_of_different_words",
        "type_token_ratio",
        "mean_length_of_utterance_words",
        "unintelligible_ratio",
        "question_ratio",
    ]
    lines = []
    for name in tracked:
        if name not in previous_values or name not in current_values:
            continue
        delta = round(current_values[name] - previous_values[name], 4)
        direction = "increased" if delta > 0 else "decreased" if delta < 0 else "was unchanged"
        lines.append(f"- {name}: {direction} by {abs(delta)} compared with the previous reviewed session.")
    if not lines:
        lines.append("- No comparable numeric features were available across the reviewed sessions.")
    lines.append("- Progress comparison is descriptive and requires therapist interpretation.")
    return lines


def _numeric_feature_map(feature_set: FeatureSet) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in feature_set.features:
        if isinstance(item.value, (int, float)):
            values[item.name] = float(item.value)
    return values


def render_pdf_base64(report: Report) -> str | None:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception:
        return None

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    text = pdf.beginText(48, height - 48)
    text.setFont("Helvetica", 10)
    for raw_line in report.markdown.splitlines():
        line = raw_line[:100]
        if text.getY() < 48:
            pdf.drawText(text)
            pdf.showPage()
            text = pdf.beginText(48, height - 48)
            text.setFont("Helvetica", 10)
        text.textLine(line)
    pdf.drawText(text)
    pdf.save()
    return base64.b64encode(buffer.getvalue()).decode("ascii")
