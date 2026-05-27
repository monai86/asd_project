from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "therapist-clinician-app"
PHASE7_DOC = PROJECT_ROOT / "docs" / "SPEECH_THERAPIST_PROTOTYPE_PHASE7.md"


def test_standalone_therapist_app_files_exist():
    assert (APP_DIR / "index.html").exists()
    assert (APP_DIR / "package.json").exists()
    assert (APP_DIR / "src" / "app.js").exists()
    assert (APP_DIR / "src" / "styles.css").exists()


def test_app_is_not_pastel_dashboard_surface():
    html = (APP_DIR / "index.html").read_text(encoding="utf-8")
    js = (APP_DIR / "src" / "app.js").read_text(encoding="utf-8")

    assert "Speech Therapist Prototype" in html
    assert "Pastel" not in html
    assert "dashboard_unified" not in js


def test_safety_boundary_and_mock_accounts_are_visible():
    js = (APP_DIR / "src" / "app.js").read_text(encoding="utf-8")

    assert "does not diagnose ASD" in js
    assert "qualified clinical judgment" in js
    assert "therapist@example.test" in js
    assert "clinician@example.test" in js
    assert "admin@example.test" in js


def test_upload_validation_contract_is_present():
    js = (APP_DIR / "src" / "app.js").read_text(encoding="utf-8")

    for file_type in ["wav", "mp3", "m4a", "mp4", "mov"]:
        assert f'"{file_type}"' in js
    assert "MAX_FILE_SIZE_MB" in js
    assert "metadata only" in js
    assert "Metadata-only mock upload" in js
    assert "Uploaded File Metadata" in js
    assert "buildStoredFilename" in js
    assert "No file bytes are persisted" in js


def test_transcript_workflow_contract_is_present():
    js = (APP_DIR / "src" / "app.js").read_text(encoding="utf-8")

    for text in [
        "ALLOWED_TRANSCRIPT_FILE_TYPES",
        "Upload/select .cha transcript",
        "CHAT transcript workflow",
        "CHAT transcript viewer and correction UI",
        "Transcript QA Results",
        "Generate mock CHAT from audio metadata",
        "Real audio-to-CHAT execution is deferred",
        "reviewChatText",
        "handleTranscriptUpload",
    ]:
        assert text in js


def test_phase_5_decision_support_contract_is_present():
    js = (APP_DIR / "src" / "app.js").read_text(encoding="utf-8")

    for text in [
        "featureSchema",
        "14-feature schema summary",
        "AI Decision-Support Output",
        "Screening Support Score",
        "Top contributing features",
        "Evidence Review Panel",
        "generateDecisionSupport",
        "ai_output_generated",
        "This is not a diagnosis",
    ]:
        assert text in js


def test_phase_6_progress_report_contract_is_present():
    js = (APP_DIR / "src" / "app.js").read_text(encoding="utf-8")

    for text in [
        "Score Timeline",
        "Feature Trends Over Sessions",
        "Therapy Goal Progress",
        "Before/After Radar",
        "Printable / Exportable Progress Report",
        "Download Markdown",
        "Print / Save PDF",
        "buildProgressReportMarkdown",
        "report_exported",
        "progress tracking and clinical decision support only",
    ]:
        assert text in js


def test_phase_7_checklist_doc_maps_all_phases_and_md_areas():
    assert PHASE7_DOC.exists()
    text = PHASE7_DOC.read_text(encoding="utf-8")

    assert "Phase Completion / MD Checklist" in text
    for phase in ["Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5", "Phase 6", "Phase 7"]:
        assert phase in text
    for area in [
        "Authentication and user accounts",
        "Case ownership and data separation",
        "Database-ready data model",
        "Audio upload and processing workflow",
        "Session detail page",
        "Tests and documentation",
    ]:
        assert area in text


def test_phase_7_dashboard_hardening_contract_is_present():
    js = (APP_DIR / "src" / "app.js").read_text(encoding="utf-8")

    for text in [
        "Quick Actions",
        "Create case",
        "Add session",
        "Upload audio metadata",
        "Generate report",
        "Recent Cases",
        "Recent Sessions",
        "High Review-Priority Cases",
        "renderDashboardQueues",
    ]:
        assert text in js


def test_phase_7_case_detail_contract_is_present():
    js = (APP_DIR / "src" / "app.js").read_text(encoding="utf-8")

    for text in [
        "Case workflow status",
        "Feature Trends",
        "AI Screening Support History",
        "Generated Reports",
        "Transcript Review Status",
        "Uploaded File Metadata",
        "caseGeneratedReports",
    ]:
        assert text in js


def test_phase_7_session_detail_contract_is_present():
    js = (APP_DIR / "src" / "app.js").read_text(encoding="utf-8")

    for text in [
        "Session metadata",
        "Audio/video player deferred",
        "Transcript QA Results",
        "14-feature schema summary",
        "AI Decision-Support Output",
        "Therapist Notes",
        "Report generation button",
    ]:
        assert text in js


def test_phase_7_safety_acceptance_contract_is_present():
    js = (APP_DIR / "src" / "app.js").read_text(encoding="utf-8")
    doc = PHASE7_DOC.read_text(encoding="utf-8")

    assert "does not diagnose ASD" in js
    assert "diagnosed with" not in js.lower()
    assert "localStorage" not in js
    assert "No file bytes are persisted" in js
    assert "real audio pipeline is not run" in js
    assert "Reports and AI outputs must avoid diagnostic language" in doc


def test_clinician_workflow_views_are_present():
    js = (APP_DIR / "src" / "app.js").read_text(encoding="utf-8")

    for text in [
        "Therapist Dashboard",
        "Children",
        "Sessions",
        "Assessments",
        "Progress Tracking",
        "Reports",
        "Audit Logs",
    ]:
        assert text in js


def test_visual_dashboard_sections_are_present():
    js = (APP_DIR / "src" / "app.js").read_text(encoding="utf-8")

    for text in [
        "Latest Screening Support Score",
        "Score Trend Over Sessions",
        "Feature Summary (Latest Session)",
        "Top Contributing Factors",
        "Latest Session",
        "Clinical Reminder",
    ]:
        assert text in js


def test_stabilization_wording_consistency():
    # 1. Safety disclaimer presence
    constants_js = (APP_DIR / "src" / "constants.js").read_text(encoding="utf-8")
    assert "clinical decision-support prototype" in constants_js
    assert "does not diagnose ASD" in constants_js
    assert "does not replace qualified clinical judgment" in constants_js

    # 2. 14-feature schema label consistency (no "18+ speech-language features")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "18+ linguistic features" not in readme
    assert "Core 14-feature schema" in readme

    app_readme = (APP_DIR / "README.md").read_text(encoding="utf-8")
    assert "18+ automated linguistic features" not in app_readme
    assert "Core 14-feature schema" in app_readme

    # 3. Case ownership filtering
    case_service_js = (APP_DIR / "src" / "services" / "case-service.js").read_text(encoding="utf-8")
    auth_adapter_js = (APP_DIR / "src" / "services" / "auth-adapter.js").read_text(encoding="utf-8")
    assert "canAccessCase" in case_service_js
    assert "childCase.owner_user_id === user.user_id" in auth_adapter_js

    # 4. Mock mode label is visible in login-view
    login_view_js = (APP_DIR / "src" / "views" / "login-view.js").read_text(encoding="utf-8")
    assert "MOCK_MODE=true" in login_view_js
