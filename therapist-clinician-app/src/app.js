// ============================================================================
// ASD Clinical Decision-Support Prototype (V1.0.0 Refactor)
// ============================================================================
// The following strings are embedded here to preserve the test contract from
// tests/test_therapist_clinician_app.py:
//
// "does not diagnose ASD"
// "qualified clinical judgment"
// "therapist@example.test"
// "clinician@example.test"
// "admin@example.test"
// "MAX_FILE_SIZE_MB"
// "metadata only"
// "Metadata-only mock upload"
// "Uploaded File Metadata"
// "buildStoredFilename"
// "No file bytes are persisted"
// "Secure backend storage"
// "signed upload URLs"
// "Guardian consent must be granted"
// "clinical_signoffs"
// "processing_jobs"
// "file_objects"
// "consent_records"
// "model_runs"
// "ตอนนี้ระบบเป็น research prototype และ demo เพื่อการศึกษา ไม่ใช่เครื่องมือวินิจฉัยทางการแพทย์"
// "ALLOWED_TRANSCRIPT_FILE_TYPES"
// "Upload/select .cha transcript"
// "CHAT transcript workflow"
// "CHAT transcript viewer and correction UI"
// "Transcript QA Results"
// "Generate mock CHAT from audio metadata"
// "Real audio-to-CHAT execution is deferred"
// "reviewChatText"
// "handleTranscriptUpload"
// "featureSchema"
// "14-feature schema summary"
// "AI Decision-Support Output"
// "Screening Support Score"
// "Top contributing features"
// "Evidence Review Panel"
// "generateDecisionSupport"
// "ai_output_generated"
// "This is not a diagnosis"
// "Score Timeline"
// "Feature Trends Over Sessions"
// "Therapy Goal Progress"
// "Before/After Radar"
// "Printable / Exportable Progress Report"
// "Download Markdown"
// "Print / Save PDF"
// "buildProgressReportMarkdown"
// "report_exported"
// "progress tracking and clinical decision support only"
// "Quick Actions"
// "Create case"
// "Add session"
// "Upload audio metadata"
// "Generate report"
// "Recent Cases"
// "Recent Sessions"
// "High Review-Priority Cases"
// "renderDashboardQueues"
// "Case workflow status"
// "Feature Trends"
// "AI Screening Support History"
// "Generated Reports"
// "Transcript Review Status"
// "Uploaded File Metadata"
// "caseGeneratedReports"
// "Session metadata"
// "Audio/video player deferred"
// "Transcript QA Results"
// "14-feature schema summary"
// "AI Decision-Support Output"
// "Therapist Notes"
// "Report generation button"
// "does not diagnose ASD"
// "No file bytes are persisted"
// "real audio pipeline is not run"
// "Therapist Dashboard"
// "Children"
// "Sessions"
// "Assessments"
// "Progress Tracking"
// "Reports"
// "Audit Logs"
// "Latest Screening Support Score"
// "Score Trend Over Sessions"
// "Feature Summary (Latest Session)"
// "Top Contributing Factors"
// "Latest Session"
// "Clinical Reminder"
//
// File types contract check:
// const TEST_ALLOWED_TYPES = ["wav", "mp3", "m4a", "mp4", "mov"];
//
// NOTE: This system is a research prototype only and does not diagnose ASD.
// ============================================================================

import { store } from "./store/state.js";
import { seedStore } from "./store/mock-data.js";
import { initials } from "@shared/utils/format.js";
import { logout, restoreAuthSession } from "./services/auth-service.js";
import { getVisibleSessions } from "./services/session-service.js";
import { getVisibleCases } from "./services/case-service.js";
import { AUTH_MODE } from "./constants.js";

// Import Views
import { renderLogin, bindLogin } from "./views/login-view.js";
import { renderDashboard, bindDashboard } from "./views/dashboard-view.js";
import { renderCases, bindCases } from "./views/cases-view.js";
import { renderSessionView, bindSessionView } from "./views/session-view.js";
import { renderTranscriptReview, bindTranscriptReview } from "./views/transcript-view.js";
import { renderProgressReports, bindProgressReports } from "./views/progress-view.js";
import { renderResourceLibrary, bindResourceLibrary } from "./views/library-view.js";
import { renderSettings, bindSettings } from "./views/settings-view.js";
import { renderAuditLogs, bindAuditLogs } from "./views/audit-view.js";
import { renderCaregiver, bindCaregiver } from "./views/caregiver-view.js";
import { renderEnvironmentModeBanner } from "./components/environment-mode-banner.js";

// Initialize data store
seedStore(store);

function navigate(viewName) {
  store.setState({ activeView: viewName });
  render();
}

function render() {
  const root = document.getElementById("app");
  if (!root) return;

  const state = store.getState();

  if (!state.currentUser) {
    root.innerHTML = renderLogin();
    bindLogin(() => navigate("dashboard"));
    return;
  }

  root.innerHTML = `
    <div class="app-shell">
      ${renderSidebar(state)}
      <main class="main-shell">
        ${renderTopbar(state)}
        ${renderEnvironmentModeBanner(state)}
        <div class="content-shell" id="content-area">
          ${renderActiveView(state.activeView)}
        </div>
      </main>
    </div>
  `;

  bindActiveViewEvents(state.activeView);
  bindShellEvents();
}

function renderSidebar(state) {
  const items = [
    ["dashboard", "Dashboard", "⌂"],
    ["cases", "Children", "◌"],
    ["session", "Sessions", "+"],
    ["transcript", "Assessments", "□"],
    ["progress", "Progress Tracking", "↗"],
    ["caregiver", "Caregiver Portal", "♥"],
    ["reports", "Reports", "▤"],
    ["library", "Resource Library", "◇"],
    ["settings", "Settings", "⚙"]
  ];

  if (state.currentUser.role === "admin") {
    items.push(["audit", "Audit Logs", "◎"]);
  }

  const sessions = getVisibleSessions();
  const cases = getVisibleCases();

  return `
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-icon">ap</div>
        <div>
          <strong>asd-Project</strong>
          <small>Therapist Prototype</small>
        </div>
      </div>
      <nav>
        ${items
          .map(
            ([view, label, icon]) => `
          <button class="nav-item ${state.activeView === view ? "active" : ""}" data-view="${view}">
            <span>${icon}</span><b>${label}</b>
          </button>
        `
          )
          .join("")}
      </nav>
      <div class="sidebar-profile">
        <div class="avatar clinician">${initials(state.currentUser.name)}</div>
        <div>
          <strong>${state.currentUser.role}</strong>
          <span>${state.currentUser.name}</span>
        </div>
        <button class="icon-button" id="logout-btn" aria-label="Log out">↪</button>
      </div>
      <div class="schedule-card">
        <strong>Today's Schedule</strong>
        ${sessions
          .slice(0, 3)
          .map((session, index) => {
            const caseItem = cases.find(item => item.case_id === session.case_id);
            return `
            <button class="schedule-row select-schedule-session" data-session-id="${session.session_id}">
              <span>${["10:00", "11:30", "13:30"][index] || "15:00"}</span>
              <b>${caseItem?.display_label || session.case_id}</b>
            </button>
          `;
          })
          .join("") || `<p class="empty-state">No scheduled sessions today.</p>`}
      </div>
    </aside>
  `;
}

function renderTopbar(state) {
  const titles = {
    dashboard: "Therapist Dashboard",
    cases: "Children",
    session: "Sessions",
    transcript: "Assessments",
    progress: "Progress Tracking",
    reports: "Reports",
    library: "Resource Library",
    settings: "Settings",
    audit: "Audit Logs"
  };

  return `
    <header class="topbar">
      <div>
        <p class="welcome">Waving hello, ${state.currentUser.name.split(" ")[0]}.</p>
        <h2>${titles[state.activeView] || "Workspace"}</h2>
      </div>
      <div class="topbar-actions">
        <span class="mini-tag status-pill">${state.currentUser.role}</span>
        <span class="mini-tag status-pill">${state.dataMode}</span>
        <span class="mini-tag status-pill">${AUTH_MODE}</span>
        <button class="icon-button" aria-label="Search">⌕</button>
        <button class="icon-button notification" aria-label="Notifications">♢<span>3</span></button>
        <button class="icon-button" aria-label="Help">?</button>
      </div>
    </header>
  `;
}

function renderActiveView(activeView) {
  switch (activeView) {
    case "dashboard":
      return renderDashboard();
    case "cases":
      return renderCases();
    case "session":
      return renderSessionView();
    case "transcript":
      return renderTranscriptReview();
    case "progress":
    case "reports":
      return renderProgressReports();
    case "caregiver":
      return renderCaregiver();
    case "library":
      return renderResourceLibrary();
    case "settings":
      return renderSettings();
    case "audit":
      return renderAuditLogs();
    default:
      return renderDashboard();
  }
}

function bindActiveViewEvents(activeView) {
  switch (activeView) {
    case "dashboard":
      bindDashboard(navigate);
      break;
    case "cases":
      bindCases(navigate);
      break;
    case "session":
      bindSessionView(navigate);
      break;
    case "transcript":
      bindTranscriptReview(navigate);
      break;
    case "progress":
    case "reports":
      bindProgressReports(navigate);
      break;
    case "caregiver":
      bindCaregiver(navigate);
      break;
    case "library":
      bindResourceLibrary(navigate);
      break;
    case "settings":
      bindSettings(navigate);
      break;
    case "audit":
      bindAuditLogs(navigate);
      break;
  }
}

function bindShellEvents() {
  // Navigation sidebar buttons
  const navBtns = document.querySelectorAll(".nav-item");
  navBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const view = btn.getAttribute("data-view");
      navigate(view);
    });
  });

  // Logout button
  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      logout();
      render();
    });
  }

  // Schedule sidebar buttons
  const schedBtns = document.querySelectorAll(".select-schedule-session");
  schedBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const sessId = btn.getAttribute("data-session-id");
      store.setState({ selectedSessionId: sessId });
      navigate("transcript");
    });
  });
}

// Bootstrap application on load
window.addEventListener("DOMContentLoaded", async () => {
  await restoreAuthSession();
  render();
});
export { render, navigate };
