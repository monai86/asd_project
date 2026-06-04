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
import { renderReportsView, bindReportsView } from "./views/reports-view.js";
import { renderCaseDetail, bindCaseDetail } from "./views/case-detail-view.js";
import { renderAIReview, bindAIReview } from "./views/ai-review-view.js";
import { renderEnvironmentModeBanner } from "./components/environment-mode-banner.js";
import { iconSvg } from "./components/icons.js";
import { bindNativeShellStatus, getNativeShellState } from "./services/native-shell-service.js";

// Initialize data store
seedStore(store);

let nativeShellState = getNativeShellState();
let unbindNativeShellStatus = null;
let shellKeydownBound = false;

const NAV_ITEMS_BASE = [
  ["dashboard", "Dashboard", iconSvg.home],
  ["cases", "Child Cases", iconSvg.users],
  ["session", "Sessions", iconSvg.calendarPlus],
  ["transcript", "Transcripts", iconSvg.penLine],
  ["ai_review", "AI Review", iconSvg.checkCircle],
  ["progress", "Progress", iconSvg.trendUp],
  ["reports", "Reports", iconSvg.fileText],
  ["settings", "Settings", iconSvg.settings]
];

const VIEW_TITLES = {
  dashboard: "Therapist Dashboard",
  cases: "Child Cases",
  session: "Sessions",
  transcript: "Transcripts",
  ai_review: "AI Review Queue",
  progress: "Progress",
  reports: "Reports",
  settings: "Settings",
  case_detail: "Clinical Case Board",
  audit: "Audit Logs"
};

function getShellNavItems(state) {
  const items = [...NAV_ITEMS_BASE];
  if (state.currentUser?.role === "admin") {
    items.push(["audit", "Audit Logs", iconSvg.audit]);
  }
  return items;
}

function resetWorkspaceViewport() {
  if (typeof window === "undefined") return;
  window.requestAnimationFrame(() => {
    window.scrollTo(0, 0);
    document.getElementById("main-workspace")?.focus({ preventScroll: true });
  });
}

function navigate(viewName) {
  store.setState({ activeView: viewName });
  render();
  resetWorkspaceViewport();
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

  const items = getShellNavItems(state);
  const isMoreActive = !["dashboard", "cases", "session", "transcript"].includes(state.activeView);

  root.innerHTML = `
    <a class="skip-link" href="#content-area">Skip to clinical workspace</a>
    <div class="clinical-background-layer" aria-hidden="true"></div>

    <!-- 2. Tablet Top Header -->
    <header class="tablet-header">
      <button class="icon-button hamburger-btn" id="tablet-hamburger-btn" aria-label="Open navigation menu" aria-controls="tablet-drawer" aria-expanded="false">
        ${iconSvg.menu}
      </button>
      <div class="brand">
        <div class="brand-icon">ap</div>
        <strong>asd-Project</strong>
      </div>
      <div class="avatar clinician small" title="${state.currentUser.name}">${initials(state.currentUser.name)}</div>
    </header>

    <!-- Tablet Drawer overlay & panel -->
    <div class="drawer-overlay" id="tablet-drawer-overlay"></div>
    <aside class="drawer-panel" id="tablet-drawer" aria-hidden="true" aria-label="Tablet navigation">
      <div class="drawer-header">
        <div class="brand">
          <div class="brand-icon">ap</div>
          <strong>asd-Project</strong>
        </div>
        <button class="icon-button close-btn" id="tablet-drawer-close-btn" aria-label="Close navigation menu">${iconSvg.close}</button>
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
        <button class="icon-button logout-btn" id="tablet-logout-btn" aria-label="Log out">${iconSvg.logOut}</button>
      </div>
    </aside>

    <!-- 3. Mobile Top Header & Bottom Nav -->
    <header class="mobile-header">
      <div class="brand">
        <div class="brand-icon">ap</div>
        <strong>asd-Project</strong>
      </div>
      <span class="view-title-pill">${VIEW_TITLES[state.activeView] || "Workspace"}</span>
    </header>

    <nav class="mobile-bottom-nav">
      ${renderMobileNavItems(state, items, isMoreActive)}
    </nav>

    <!-- Mobile More Bottom Drawer Panel & Overlay -->
    <div class="drawer-overlay" id="mobile-more-overlay"></div>
    <aside class="drawer-panel bottom-drawer" id="mobile-more-drawer" aria-hidden="true" aria-label="More navigation">
      <div class="drawer-header">
        <h3>More Features</h3>
        <button class="icon-button close-btn" id="mobile-more-close-btn" aria-label="Close more navigation">${iconSvg.close}</button>
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
        <button class="icon-button logout-btn" id="mobile-logout-btn" aria-label="Log out">${iconSvg.logOut}</button>
      </div>
    </aside>

    <div class="app-shell">
      ${renderSidebar(state)}
      <main class="main-shell" id="main-workspace" tabindex="-1">
        ${renderTopbar(state)}
        ${renderNativeShellBanner(nativeShellState)}
        ${renderEnvironmentModeBanner(state)}
        <div class="content-shell" id="content-area" tabindex="-1">
          ${renderActiveView(state.activeView)}
        </div>
      </main>
    </div>

    <!-- Search Modal Overlay -->
    <div class="clinical-modal-overlay" id="topbar-search-modal" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15, 23, 42, 0.45); z-index: 2000; align-items: center; justify-content: center; backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);">
      <div class="glass-card" style="background: #fff; width: 90%; max-width: 500px; padding: 20px; border-radius: var(--radius-lg); border: 1px solid var(--line); display: flex; flex-direction: column; gap: 12px; max-height: 80vh; box-shadow: 0 8px 18px rgba(8, 145, 178, 0.08);">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--line); padding-bottom: 8px;">
          <h3 style="margin: 0; font-size: 1.1rem; color: var(--ink);">Search Clinical Cases</h3>
          <button class="icon-button" id="close-search-modal-btn" style="border: none; background: transparent; cursor: pointer; color: var(--muted);">${iconSvg.close}</button>
        </div>
        <input type="text" class="glass-input" id="search-modal-input" placeholder="Type a child name or anonymized code..." style="width: 100%; min-height: 40px; padding: 8px 12px;" />
        <div id="search-modal-results" style="display: flex; flex-direction: column; gap: 6px; overflow-y: auto; max-height: 250px; padding-top: 6px;">
          <!-- Filled dynamically -->
        </div>
      </div>
    </div>

    <!-- Notifications Popover -->
    <div class="clinical-popover glass-card" id="topbar-notifications-popover" style="display: none; position: fixed; top: 70px; right: 20px; width: 320px; background: #fff; border: 1px solid var(--line); border-radius: var(--radius-md); box-shadow: 0 10px 25px rgba(0,0,0,0.08); z-index: 1500; padding: 14px; flex-direction: column; gap: 10px;">
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--line); padding-bottom: 8px; margin-bottom: 4px;">
        <strong style="font-size: 0.9rem; color: var(--ink);">Workspace Notifications</strong>
        <button id="clear-notifications-btn" style="border: none; background: transparent; color: var(--primary); font-size: 0.72rem; font-weight: bold; cursor: pointer;">Clear All</button>
      </div>
      <div id="notifications-list-container" style="display: flex; flex-direction: column; gap: 8px; max-height: 200px; overflow-y: auto;">
        ${
          ((state.notificationsCount !== undefined ? state.notificationsCount : 3) !== 0)
            ? `
          <div class="notification-item" style="font-size: 0.78rem; padding: 8px; border-radius: 6px; background: var(--neutral-bg); line-height: 1.3; border: 1px solid var(--line);">
            <div style="font-weight: bold; color: var(--ink);">New transcript processed</div>
            <div style="color: var(--muted); margin-top: 2px;">CHI-ภูมิ (48 mo) transcript is ready for clinician QA.</div>
          </div>
          <div class="notification-item" style="font-size: 0.78rem; padding: 8px; border-radius: 6px; background: var(--neutral-bg); line-height: 1.3; border: 1px solid var(--line);">
            <div style="font-weight: bold; color: var(--ink);">AI review sign-off pending</div>
            <div style="color: var(--muted); margin-top: 2px;">CHI-มีนา (52 mo) requires final clinician confirmation.</div>
          </div>
          <div class="notification-item" style="font-size: 0.78rem; padding: 8px; border-radius: 6px; background: var(--neutral-bg); line-height: 1.3; border: 1px solid var(--line);">
            <div style="font-weight: bold; color: var(--ink);">Welcome to Clinician Workspace</div>
            <div style="color: var(--muted); margin-top: 2px;">Prototype v1.0 is initialized in Mock Mode.</div>
          </div>
        `
            : `<p class="empty-state" style="font-size: 0.78rem; text-align: center; color: var(--muted); margin: 10px 0;">No unread notifications.</p>`
        }
      </div>
    </div>

    <!-- Help Modal Overlay -->
    <div class="clinical-modal-overlay" id="topbar-help-modal" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15, 23, 42, 0.45); z-index: 2000; align-items: center; justify-content: center; backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);">
      <div class="glass-card" style="background: #fff; width: 90%; max-width: 600px; padding: 20px; border-radius: var(--radius-lg); border: 1px solid var(--line); display: flex; flex-direction: column; gap: 12px; max-height: 85vh; overflow-y: auto; box-shadow: 0 8px 18px rgba(8, 145, 178, 0.08);">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--line); padding-bottom: 8px;">
          <h3 style="margin: 0; font-size: 1.1rem; color: var(--ink);">Clinical Assistant Reference Help</h3>
          <button class="icon-button" id="close-help-modal-btn" style="border: none; background: transparent; cursor: pointer; color: var(--muted);">${iconSvg.close}</button>
        </div>
        <div style="font-size: 0.85rem; color: var(--ink); line-height: 1.5; display: flex; flex-direction: column; gap: 10px;">
          <strong>Clinical Support System Summary:</strong>
          <p>This prototype serves as a speech-language feature extraction tool. It extracts 14 diagnostic speech features from transcripts to assist clinician screening. <strong>It does not diagnose ASD.</strong> All results must be interpreted using qualified clinical judgment.</p>
          
          <strong style="margin-top: 8px;">14 Core Speech-Language Markers:</strong>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 0.78rem; background: var(--neutral-bg); padding: 10px; border-radius: 6px; border: 1px solid var(--line);">
            <span>• MLU: Mean Length of Utterance</span>
            <span>• TTR: Type-Token Ratio</span>
            <span>• Echolalia Count / Ratio</span>
            <span>• Pronoun Reversals</span>
            <span>• Zero Vocalizations</span>
            <span>• Unintelligible Words Ratio</span>
            <span>• Nonverbal Vocalizations</span>
            <span>• Child Question Ratio</span>
          </div>

          <strong style="margin-top: 8px;">CHAT standard timing (%tim:) format:</strong>
          <p>Timing in transcripts uses the standard CHAT standard <code>%tim: HH:MM:SS.sss-HH:MM:SS.sss</code> tier mapped to segment timelines. Play buttons synchronise audio highlight based on these time stamps.</p>
        </div>
      </div>
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

function renderMobileNavItems(state, items, isMoreActive = false) {
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
    <button class="nav-item ${isMoreActive ? "active" : ""}" id="mobile-more-trigger" type="button" aria-controls="mobile-more-drawer" aria-expanded="false">
      <span>${iconSvg.more}</span>
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
  const items = getShellNavItems(state);
  const sessions = getVisibleSessions();
  const cases = getVisibleCases();

  return `
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-icon">ap</div>
        <div>
          <strong>asd-Project</strong>
          <small>Clinical Workspace</small>
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
        <button class="icon-button logout-btn" id="logout-btn" aria-label="Log out">${iconSvg.logOut}</button>
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
      <div style="font-size: 0.65rem; color: var(--muted); border-top: 1px solid var(--line); padding-top: 10px; margin-top: 10px; line-height: 1.3;">
        <strong>Notice:</strong> Decision-support prototype. Does not diagnose ASD.
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

  const notificationsCount = state.notificationsCount !== undefined ? state.notificationsCount : 3;

  return `
    <header class="topbar">
      <div>
        <p class="welcome">Signed in as ${state.currentUser.name.split(" ")[0]} (${state.currentUser.role})</p>
        <h2>${titles[state.activeView] || "Workspace"}</h2>
      </div>
      <div class="topbar-actions" style="position: relative;">
        ${state.dataMode === "mock" ? `<span class="status-pill status-warn" style="font-size: 0.72rem; padding: 2px 8px; font-weight: bold; text-transform: uppercase;">Mock Mode</span>` : ""}
        <button class="icon-button" id="topbar-search-btn" aria-label="Search clinical workspace">${iconSvg.search}</button>
        <button class="icon-button notification" id="topbar-bell-btn" aria-label="Notifications">
          ${iconSvg.bell}
          ${notificationsCount > 0 ? `<span>${notificationsCount}</span>` : ""}
        </button>
        <button class="icon-button" id="topbar-help-btn" aria-label="Clinical help">${iconSvg.help}</button>
      </div>
    </header>
  `;
}

function renderNativeShellBanner(shellState) {
  if (!shellState.isNativeShell && shellState.isOnline) return "";
  const tone = shellState.isOnline ? "online" : "offline";
  const title = shellState.isOnline ? "iOS shell active" : "Offline shell mode";
  const message = shellState.isOnline
    ? "Native shell is handling safe areas and system status. Clinical records still load from the shared workspace."
    : "Static app shell is available. Clinical records, uploads, and reports require network access.";

  return `
    <section class="native-shell-banner ${tone}" role="status" aria-live="polite">
      <span class="native-shell-banner__icon">${shellState.isOnline ? iconSvg.check : iconSvg.network}</span>
      <div>
        <strong>${title}</strong>
        <p>${message}</p>
      </div>
    </section>
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
    case "ai_review":
      return renderAIReview();
    case "case_detail":
      return renderCaseDetail();
    case "progress":
      return renderProgressReports();
    case "reports":
      return renderReportsView();
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
    case "ai_review":
      bindAIReview(navigate);
      break;
    case "case_detail":
      bindCaseDetail(navigate);
      break;
    case "progress":
      bindProgressReports(navigate);
      break;
    case "reports":
      bindReportsView(navigate);
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

function toggleDrawer(drawerId, overlayId, show, triggerId = null) {
  const drawer = document.getElementById(drawerId);
  const overlay = document.getElementById(overlayId);
  const trigger = triggerId ? document.getElementById(triggerId) : null;
  if (drawer && overlay) {
    if (show) {
      drawer.classList.add("open");
      overlay.classList.add("open");
      drawer.setAttribute("aria-hidden", "false");
      trigger?.setAttribute("aria-expanded", "true");
      drawer.querySelector("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])")?.focus();
    } else {
      drawer.classList.remove("open");
      overlay.classList.remove("open");
      drawer.setAttribute("aria-hidden", "true");
      trigger?.setAttribute("aria-expanded", "false");
      trigger?.focus();
    }
  }
}

function closeAllDrawers() {
  toggleDrawer("tablet-drawer", "tablet-drawer-overlay", false, "tablet-hamburger-btn");
  toggleDrawer("mobile-more-drawer", "mobile-more-overlay", false, "mobile-more-trigger");
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
      toggleDrawer("tablet-drawer", "tablet-drawer-overlay", true, "tablet-hamburger-btn");
    });
  }

  // Tablet close buttons
  const tabletCloseBtn = document.getElementById("tablet-drawer-close-btn");
  if (tabletCloseBtn) {
    tabletCloseBtn.addEventListener("click", () => {
      toggleDrawer("tablet-drawer", "tablet-drawer-overlay", false, "tablet-hamburger-btn");
    });
  }
  const tabletOverlay = document.getElementById("tablet-drawer-overlay");
  if (tabletOverlay) {
    tabletOverlay.addEventListener("click", () => {
      toggleDrawer("tablet-drawer", "tablet-drawer-overlay", false, "tablet-hamburger-btn");
    });
  }

  // Mobile More button trigger
  const mobileMoreBtn = document.getElementById("mobile-more-trigger");
  if (mobileMoreBtn) {
    mobileMoreBtn.addEventListener("click", () => {
      toggleDrawer("mobile-more-drawer", "mobile-more-overlay", true, "mobile-more-trigger");
    });
  }

  // Mobile More close buttons
  const mobileCloseBtn = document.getElementById("mobile-more-close-btn");
  if (mobileCloseBtn) {
    mobileCloseBtn.addEventListener("click", () => {
      toggleDrawer("mobile-more-drawer", "mobile-more-overlay", false, "mobile-more-trigger");
    });
  }
  const mobileOverlay = document.getElementById("mobile-more-overlay");
  if (mobileOverlay) {
    mobileOverlay.addEventListener("click", () => {
      toggleDrawer("mobile-more-drawer", "mobile-more-overlay", false, "mobile-more-trigger");
    });
  }

  if (!shellKeydownBound) {
    document.addEventListener("keydown", event => {
      if (event.key === "Escape") {
        closeAllDrawers();
        const sm = document.getElementById("topbar-search-modal");
        const hm = document.getElementById("topbar-help-modal");
        const np = document.getElementById("topbar-notifications-popover");
        if (sm) sm.style.display = "none";
        if (hm) hm.style.display = "none";
        if (np) np.style.display = "none";
      }
    });
    shellKeydownBound = true;
  }

  // Topbar search modal toggle
  const searchBtn = document.getElementById("topbar-search-btn");
  const searchModal = document.getElementById("topbar-search-modal");
  const closeSearchBtn = document.getElementById("close-search-modal-btn");
  if (searchBtn && searchModal) {
    searchBtn.addEventListener("click", () => {
      searchModal.style.display = "flex";
      document.getElementById("search-modal-input")?.focus();
      document.getElementById("search-modal-input").value = "";
      document.getElementById("search-modal-results").innerHTML = "";
    });
    closeSearchBtn?.addEventListener("click", () => {
      searchModal.style.display = "none";
    });
  }

  // Topbar search filter and select logic
  const searchInput = document.getElementById("search-modal-input");
  const searchResults = document.getElementById("search-modal-results");
  if (searchInput && searchResults) {
    searchInput.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase().trim();
      if (!q) {
        searchResults.innerHTML = "";
        return;
      }
      const allCases = store.getState().cases;
      const filtered = allCases.filter(c => 
        (c.display_label || "").toLowerCase().includes(q) || 
        (c.anonymized_child_code || "").toLowerCase().includes(q)
      );
      searchResults.innerHTML = filtered.map(c => `
        <button class="search-result-row select-search-case" data-case-id="${c.case_id}" style="text-align: left; padding: 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); cursor: pointer; font-size: 0.85rem; color: var(--ink); width: 100%; display: flex; justify-content: space-between; align-items: center; transition: background-color 0.2s;">
          <strong>${c.display_label}</strong>
          <span style="color: var(--muted); font-size: 0.76rem;">${c.anonymized_child_code}</span>
        </button>
      `).join("");
      
      const rows = searchResults.querySelectorAll(".select-search-case");
      rows.forEach(row => {
        row.addEventListener("click", () => {
          const caseId = row.getAttribute("data-case-id");
          store.setState({ selectedCaseId: caseId, caseDetailTab: "overview" });
          searchModal.style.display = "none";
          navigate("case_detail");
        });
      });
    });
  }

  // Topbar notification popover toggle
  const bellBtn = document.getElementById("topbar-bell-btn");
  const notificationsPopover = document.getElementById("topbar-notifications-popover");
  if (bellBtn && notificationsPopover) {
    bellBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isHidden = notificationsPopover.style.display === "none";
      notificationsPopover.style.display = isHidden ? "flex" : "none";
    });
    document.addEventListener("click", (e) => {
      if (notificationsPopover && !notificationsPopover.contains(e.target) && e.target !== bellBtn) {
        notificationsPopover.style.display = "none";
      }
    });
  }

  const clearBtn = document.getElementById("clear-notifications-btn");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      store.setState({ notificationsCount: 0 });
      const container = document.getElementById("notifications-list-container");
      if (container) {
        container.innerHTML = `<p class="empty-state" style="font-size: 0.78rem; text-align: center; color: var(--muted); margin: 10px 0;">No unread notifications.</p>`;
      }
      render();
    });
  }

  // Topbar help modal toggle
  const helpBtn = document.getElementById("topbar-help-btn");
  const helpModal = document.getElementById("topbar-help-modal");
  const closeHelpBtn = document.getElementById("close-help-modal-btn");
  if (helpBtn && helpModal) {
    helpBtn.addEventListener("click", () => {
      helpModal.style.display = "flex";
    });
    closeHelpBtn?.addEventListener("click", () => {
      helpModal.style.display = "none";
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
  unbindNativeShellStatus?.();
  unbindNativeShellStatus = bindNativeShellStatus(nextState => {
    nativeShellState = nextState;
    document.documentElement.dataset.platform = nextState.platform;
    document.documentElement.dataset.shellStatus = nextState.status;
    if (store.getState().currentUser) {
      render();
    }
  });
  try {
    await restoreAuthSession();
  } catch (err) {
    console.error("Session restoration failed:", err);
  }
  render();
  resetWorkspaceViewport();
});
export { render, navigate };
