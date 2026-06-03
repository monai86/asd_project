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

  const svgIcons = {
    dashboard: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
    cases: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    session: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 13V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h8"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="19" y1="16" x2="19" y2="22"/><line x1="16" y1="19" x2="22" y2="19"/></svg>`,
    transcript: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/><path d="m15 5 3 3"/></svg>`,
    progress: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>`,
    caregiver: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>`,
    reports: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>`,
    library: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>`,
    settings: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.1a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>`,
    audit: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`
  };

  const items = [
    ["dashboard", "Dashboard", svgIcons.dashboard],
    ["cases", "Children", svgIcons.cases],
    ["session", "Sessions", svgIcons.session],
    ["transcript", "Assessments", svgIcons.transcript],
    ["progress", "Progress Tracking", svgIcons.progress],
    ["caregiver", "Caregiver Portal", svgIcons.caregiver],
    ["reports", "Reports", svgIcons.reports],
    ["library", "Resource Library", svgIcons.library],
    ["settings", "Settings", svgIcons.settings]
  ];

  if (state.currentUser.role === "admin") {
    items.push(["audit", "Audit Logs", svgIcons.audit]);
  }

  root.innerHTML = `
    <div class="liquid-background-container">
      <div class="liquid-blob blob-rose"></div>
      <div class="liquid-blob blob-peach"></div>
      <div class="liquid-blob blob-coral"></div>
      <div class="liquid-blob blob-yellow"></div>
      <div class="liquid-blob blob-lavender"></div>
      <div class="liquid-blob blob-teal"></div>
    </div>
    
    <!-- 1. Desktop Top Bar Navigation -->
    <header class="desktop-header">
      <div class="brand">
        <div class="brand-icon">ap</div>
        <div>
          <strong>asd-Project</strong>
          <small>Therapist Prototype</small>
        </div>
      </div>
      <nav>
        ${renderNavItems(state, items)}
      </nav>
      <div class="header-profile">
        <div class="avatar clinician" title="${state.currentUser.name}">${initials(state.currentUser.name)}</div>
        <button class="icon-button logout-btn" id="desktop-logout-btn" title="Log out">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>
        </button>
      </div>
    </header>

    <!-- 2. Tablet Top Header -->
    <header class="tablet-header">
      <button class="icon-button hamburger-btn" id="tablet-hamburger-btn" aria-label="Menu">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/></svg>
      </button>
      <div class="brand">
        <div class="brand-icon">ap</div>
        <strong>asd-Project</strong>
      </div>
      <div class="avatar clinician small" title="${state.currentUser.name}">${initials(state.currentUser.name)}</div>
    </header>

    <!-- Tablet Drawer overlay & panel -->
    <div class="drawer-overlay" id="tablet-drawer-overlay"></div>
    <aside class="drawer-panel" id="tablet-drawer">
      <div class="drawer-header">
        <div class="brand">
          <div class="brand-icon">ap</div>
          <strong>asd-Project</strong>
        </div>
        <button class="icon-button close-btn" id="tablet-drawer-close-btn">&times;</button>
      </div>
      <nav>
        ${renderNavItems(state, items)}
      </nav>
      <div class="drawer-profile">
        <div class="avatar clinician">${initials(state.currentUser.name)}</div>
        <div class="profile-info">
          <strong>${state.currentUser.role}</strong>
          <span>${state.currentUser.name}</span>
        </div>
        <button class="icon-button logout-btn" id="tablet-logout-btn" title="Log out"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg></button>
      </div>
    </aside>

    <!-- 3. Mobile Top Header & Bottom Nav -->
    <header class="mobile-header">
      <div class="brand">
        <div class="brand-icon">ap</div>
        <strong>asd-Project</strong>
      </div>
      <span class="view-title-pill">${titles[state.activeView] || "Workspace"}</span>
    </header>

    <nav class="mobile-bottom-nav">
      ${renderMobileNavItems(state, items)}
    </nav>

    <!-- Mobile More Bottom Drawer Panel & Overlay -->
    <div class="drawer-overlay" id="mobile-more-overlay"></div>
    <aside class="drawer-panel bottom-drawer" id="mobile-more-drawer">
      <div class="drawer-header">
        <h3>More Features</h3>
        <button class="icon-button close-btn" id="mobile-more-close-btn">&times;</button>
      </div>
      <nav>
        ${renderMobileMoreNavItems(state, items)}
      </nav>
      <div class="drawer-profile">
        <div class="avatar clinician">${initials(state.currentUser.name)}</div>
        <div class="profile-info">
          <strong>${state.currentUser.role}</strong>
          <span>${state.currentUser.name}</span>
        </div>
        <button class="icon-button logout-btn" id="mobile-logout-btn" title="Log out"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg></button>
      </div>
    </aside>

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

function renderNavItems(state, items) {
  return items
    .map(
      ([view, label, icon]) => `
      <button class="nav-item ${state.activeView === view ? "active" : ""}" data-view="${view}">
        <span>${icon}</span><b>${label}</b>
      </button>
    `
    )
    .join("");
}

function renderMobileNavItems(state, items) {
  const primaryKeys = ["dashboard", "cases", "session", "transcript"];
  const primaryItems = items.filter(([view]) => primaryKeys.includes(view));
  
  const bottomButtons = primaryItems.map(([view, label, icon]) => {
    const isAct = state.activeView === view;
    return `
      <button class="nav-item ${isAct ? "active" : ""}" data-view="${view}">
        <span>${icon}</span><b>${label}</b>
      </button>
    `;
  });
  
  bottomButtons.push(`
    <button class="nav-item" id="mobile-more-trigger" type="button">
      <span><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg></span>
      <b>More</b>
    </button>
  `);
  
  return bottomButtons.join("");
}

function renderMobileMoreNavItems(state, items) {
  const primaryKeys = ["dashboard", "cases", "session", "transcript"];
  const moreItems = items.filter(([view]) => !primaryKeys.includes(view));
  
  return moreItems
    .map(([view, label, icon]) => {
      const isAct = state.activeView === view;
      return `
        <button class="nav-item ${isAct ? "active" : ""}" data-view="${view}">
          <span>${icon}</span><b>${label}</b>
        </button>
      `;
    })
    .join("");
}

function renderSidebar(state) {
  const svgIcons = {
    dashboard: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
    cases: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    session: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 13V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h8"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="19" y1="16" x2="19" y2="22"/><line x1="16" y1="19" x2="22" y2="19"/></svg>`,
    transcript: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/><path d="m15 5 3 3"/></svg>`,
    progress: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>`,
    caregiver: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>`,
    reports: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>`,
    library: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>`,
    settings: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.1a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>`,
    audit: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`
  };

  const items = [
    ["dashboard", "Dashboard", svgIcons.dashboard],
    ["cases", "Children", svgIcons.cases],
    ["session", "Sessions", svgIcons.session],
    ["transcript", "Assessments", svgIcons.transcript],
    ["progress", "Progress Tracking", svgIcons.progress],
    ["caregiver", "Caregiver Portal", svgIcons.caregiver],
    ["reports", "Reports", svgIcons.reports],
    ["library", "Resource Library", svgIcons.library],
    ["settings", "Settings", svgIcons.settings]
  ];

  if (state.currentUser.role === "admin") {
    items.push(["audit", "Audit Logs", svgIcons.audit]);
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
      <div class="sidebar-profile glass-card">
        <div class="avatar clinician">${initials(state.currentUser.name)}</div>
        <div>
          <strong>${state.currentUser.role}</strong>
          <span>${state.currentUser.name}</span>
        </div>
        <button class="icon-button logout-btn" id="logout-btn" aria-label="Log out"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg></button>
      </div>
      <div class="schedule-card glass-card">
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
        <button class="icon-button" aria-label="Search"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></button>
        <button class="icon-button notification" aria-label="Notifications"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg><span>3</span></button>
        <button class="icon-button" aria-label="Help"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></button>
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

function toggleDrawer(drawerId, overlayId, show) {
  const drawer = document.getElementById(drawerId);
  const overlay = document.getElementById(overlayId);
  if (drawer && overlay) {
    if (show) {
      drawer.classList.add("open");
      overlay.classList.add("open");
    } else {
      drawer.classList.remove("open");
      overlay.classList.remove("open");
    }
  }
}

function closeAllDrawers() {
  toggleDrawer("tablet-drawer", "tablet-drawer-overlay", false);
  toggleDrawer("mobile-more-drawer", "mobile-more-overlay", false);
}

function bindShellEvents() {
  // Navigation buttons
  const navBtns = document.querySelectorAll(".nav-item");
  navBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const view = btn.getAttribute("data-view");
      if (view) {
        navigate(view);
        closeAllDrawers();
      }
    });
  });

  // Logout buttons
  const logoutBtns = document.querySelectorAll(".logout-btn");
  logoutBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      logout();
      render();
    });
  });

  // Hamburger button for tablet
  const hamburgerBtn = document.getElementById("tablet-hamburger-btn");
  if (hamburgerBtn) {
    hamburgerBtn.addEventListener("click", () => {
      toggleDrawer("tablet-drawer", "tablet-drawer-overlay", true);
    });
  }

  // Tablet close buttons
  const tabletCloseBtn = document.getElementById("tablet-drawer-close-btn");
  if (tabletCloseBtn) {
    tabletCloseBtn.addEventListener("click", () => {
      toggleDrawer("tablet-drawer", "tablet-drawer-overlay", false);
    });
  }
  const tabletOverlay = document.getElementById("tablet-drawer-overlay");
  if (tabletOverlay) {
    tabletOverlay.addEventListener("click", () => {
      toggleDrawer("tablet-drawer", "tablet-drawer-overlay", false);
    });
  }

  // Mobile More button trigger
  const mobileMoreBtn = document.getElementById("mobile-more-trigger");
  if (mobileMoreBtn) {
    mobileMoreBtn.addEventListener("click", () => {
      toggleDrawer("mobile-more-drawer", "mobile-more-overlay", true);
    });
  }

  // Mobile More close buttons
  const mobileCloseBtn = document.getElementById("mobile-more-close-btn");
  if (mobileCloseBtn) {
    mobileCloseBtn.addEventListener("click", () => {
      toggleDrawer("mobile-more-drawer", "mobile-more-overlay", false);
    });
  }
  const mobileOverlay = document.getElementById("mobile-more-overlay");
  if (mobileOverlay) {
    mobileOverlay.addEventListener("click", () => {
      toggleDrawer("mobile-more-drawer", "mobile-more-overlay", false);
    });
  }

  // Schedule sidebar buttons (if present)
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
  try {
    await restoreAuthSession();
  } catch (err) {
    console.error("Session restoration failed:", err);
  }
  render();
});
export { render, navigate };
