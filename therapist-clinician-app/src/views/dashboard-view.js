import { store } from "../store/state.js";
import { getVisibleCases } from "../services/case-service.js";
import { getVisibleSessions } from "../services/session-service.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { renderConsentWarning } from "../components/privacy-status.js";
import { renderAccessDenied } from "../components/access-denied.js";

export function renderDashboard() {
  const state = store.getState();
  const cases = getVisibleCases();
  const sessions = getVisibleSessions();

  // Access check for selected case
  const allCases = state.cases || [];
  const selectedCaseFromStore = allCases.find(c => c.case_id === state.selectedCaseId);
  if (cases.length > 0 && selectedCaseFromStore && !cases.some(c => c.case_id === selectedCaseFromStore.case_id)) {
    return renderAccessDenied("Access denied: this case is not assigned to your account.");
  }

  const pendingReviewsCount = sessions.filter(s => s.therapist_review_status === "awaiting_review").length;
  const newUploadsCount = state.audioFiles.length;
  const transcriptsReadyCount = sessions.filter(s => s.processing_stage === "qa" || s.processing_stage === "awaiting_review").length;
  const reportsReadyCount = state.generatedReports.length;
  const caseloadItems = cases.slice(0, 3);
  const recentLogs = (state.auditLogs || [])
    .slice()
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, 4);

  const selectedCase = cases.find(c => c.case_id === state.selectedCaseId) || cases[0];
  const consentWarningHtml = selectedCase ? renderConsentWarning(selectedCase) : "";
  const activeSessions = sessions.filter(s => s.therapist_review_status !== "reviewed");
  const scheduleTimes = ["10:00 AM", "11:30 AM", "01:30 PM", "03:00 PM"];
  const metricCards = [
    {
      label: "Pending reviews",
      value: pendingReviewsCount,
      note: "clinician sign-off needed",
      tone: "warn",
      icon: "M9 11l3 3 8-8"
    },
    {
      label: "New uploads",
      value: newUploadsCount,
      note: "audio files registered",
      tone: "sky",
      icon: "M12 4v12"
    },
    {
      label: "Transcripts ready",
      value: transcriptsReadyCount,
      note: "CHAT review queue",
      tone: "teal",
      icon: "M5 3h14v18H5z"
    },
    {
      label: "Reports ready",
      value: reportsReadyCount,
      note: "safe progress exports",
      tone: "mint",
      icon: "M14 2H6a2 2 0 0 0-2 2v16h14a2 2 0 0 0 2-2V8z"
    }
  ];
  const workflowSteps = [
    ["Audio", "Uploaded", "sky"],
    ["CHAT", "Transcript ready", "neutral"],
    ["Observations", "AI-assisted", "warn"],
    ["Clinician", "Review gate", "teal"],
    ["Report", "Ready", "mint"]
  ];
  const calendarDays = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];
  const calendarDates = [8, 9, 10, 11, 12, 13, 14];

  return `
    ${renderSafetyBanner()}
    ${consentWarningHtml}
    <div class="clinical-dashboard">
      <section class="dashboard-hero-panel">
        <div>
          <span class="dashboard-kicker">Speech therapy workspace</span>
          <h2>Good morning, Therapist</h2>
          <p>Review session evidence, keep child cases organized, and prepare safe progress outputs.</p>
        </div>
        <div class="dashboard-hero-actions">
          <button class="secondary-action" type="button" id="dashboard-session-shortcut">Review queue</button>
          <button class="primary-action" id="dashboard-new-case-btn">New case</button>
        </div>
      </section>

      <section class="clinical-metric-grid" aria-label="Clinical workspace metrics">
        ${metricCards.map(card => `
          <article class="clinical-metric-card metric-${card.tone}">
            <span class="metric-icon" aria-hidden="true">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="${card.icon}"/>
              </svg>
            </span>
            <div>
              <span>${card.label}</span>
              <strong>${card.value}</strong>
              <small>${card.note}</small>
            </div>
          </article>
        `).join("")}
      </section>

      <div class="clinical-ops-grid">
        <div class="clinical-primary-column">
          <section class="workflow-panel">
            <div class="panel-title">
              <div>
                <h3>Review queue workflow</h3>
                <span>Human-in-the-loop clinical decision-support path</span>
              </div>
              <button class="secondary-action" type="button" id="view-all-cases">View cases</button>
            </div>
            <div class="workflow-track">
              ${workflowSteps.map(([label, detail, tone], index) => `
                <div class="workflow-step workflow-${tone}">
                  <span>${index + 1}</span>
                  <strong>${label}</strong>
                  <small>${detail}</small>
                </div>
              `).join("")}
            </div>
            <div class="review-queue-list">
              ${activeSessions.length === 0 ? `
                <p class="empty-state">No session reviews are assigned yet.</p>
              ` : activeSessions.slice(0, 4).map((s, index) => {
                const c = cases.find(item => item.case_id === s.case_id);
                const status = s.therapist_review_status?.replaceAll("_", " ") || "queued";
                return `
                  <button class="review-queue-row navigate-transcript-btn" type="button" data-session-id="${s.session_id}">
                    <span class="review-time">${scheduleTimes[index] || "04:30 PM"}</span>
                    <span>
                      <strong>${c?.display_label || s.case_id}</strong>
                      <small>${s.session_date} · ${status}</small>
                    </span>
                    <b>Review</b>
                  </button>
                `;
              }).join("")}
            </div>
          </section>

          <section class="case-management-panel">
            <div class="panel-title">
              <div>
                <h3>Child case management</h3>
                <span>Case cards and table-style details for assigned caseload</span>
              </div>
            </div>
            <div class="dashboard-case-grid">
              ${caseloadItems.length === 0 ? `
                <p class="empty-state">No child cases are assigned yet. Create an anonymized case file to start a workspace.</p>
              ` : caseloadItems.map(c => {
                const caseSessions = sessions.filter(s => s.case_id === c.case_id);
                const latestSession = caseSessions[0]?.session_date || "No sessions";
                const reviewState = caseSessions.some(s => s.therapist_review_status === "awaiting_review") ? "Needs review" : "Monitoring";
                return `
                  <article class="dashboard-case-card">
                    <div>
                      <strong>${c.display_label}</strong>
                      <span>${c.anonymized_child_code} · ${c.age_months} mo</span>
                    </div>
                    <div class="case-card-meta">
                      <span>${caseSessions.length} sessions</span>
                      <span>${latestSession}</span>
                      <span>${reviewState}</span>
                    </div>
                    <button class="secondary-action open-case-btn" type="button" data-case-id="${c.case_id}">Open case</button>
                  </article>
                `;
              }).join("")}
            </div>

            <div class="case-table-panel">
              <div class="case-table-row case-table-head">
                <span>Case</span>
                <span>Sessions</span>
                <span>Transcript</span>
                <span>Status</span>
              </div>
              ${caseloadItems.length === 0 ? `
                <p class="empty-state">Case table will appear after the first anonymized child case is created.</p>
              ` : caseloadItems.map(c => {
                const caseSessions = sessions.filter(s => s.case_id === c.case_id);
                const latest = caseSessions[0];
                const transcriptState = latest?.transcript_status?.replaceAll("_", " ") || "not started";
                const status = c.external_clinical_status?.replaceAll("_", " ") || "not provided";
                return `
                  <div class="case-table-row">
                    <span><strong>${c.display_label}</strong><small>${c.anonymized_child_code}</small></span>
                    <span>${caseSessions.length}</span>
                    <span>${transcriptState}</span>
                    <span><b>${status}</b></span>
                  </div>
                `;
              }).join("")}
            </div>
          </section>
        </div>

        <aside class="clinical-side-column">
          <section class="appointment-panel">
            <div class="appointment-month">
              <button class="icon-button" type="button" aria-label="Previous week">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m15 18-6-6 6-6"/></svg>
              </button>
              <strong>June 2026</strong>
              <button class="icon-button" type="button" aria-label="Next week">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg>
              </button>
            </div>
            <div class="mini-calendar">
              ${calendarDays.map((day, index) => `
                <div class="${calendarDates[index] === 9 ? "active" : ""}">
                  <span>${day}</span>
                  <strong>${calendarDates[index]}</strong>
                </div>
              `).join("")}
            </div>
            <div class="appointment-list">
              ${sessions.length === 0 ? `
                <p class="empty-state">No scheduled sessions today.</p>
              ` : sessions.slice(0, 5).map((session, index) => {
                const caseItem = cases.find(item => item.case_id === session.case_id);
                return `
                  <button class="appointment-row navigate-transcript-btn" type="button" data-session-id="${session.session_id}">
                    <span>${scheduleTimes[index] || "04:30 PM"}</span>
                    <strong>${caseItem?.display_label || session.case_id}</strong>
                    <small>45 min speech-language review</small>
                  </button>
                `;
              }).join("")}
            </div>
          </section>

          <section class="alert-panel">
            <div class="panel-title">
              <div>
                <h3>Clinical alerts</h3>
                <span>Safety and workflow checks</span>
              </div>
            </div>
            <div class="alert-stack">
              <div class="alert-card alert-warn">
                <strong>Review before export</strong>
                <span>Reports remain locked behind therapist sign-off.</span>
              </div>
              <div class="alert-card alert-info">
                <strong>Consent-aware uploads</strong>
                <span>Use anonymized case codes and verify guardian consent before adding media.</span>
              </div>
              <div class="alert-card alert-good">
                <strong>Decision-support only</strong>
                <span>No automated ASD diagnosis wording is shown in workflow outputs.</span>
              </div>
            </div>
          </section>

          <section class="activity-panel">
            <div class="panel-title">
              <div>
                <h3>Recent activity</h3>
                <span>Latest workspace events</span>
              </div>
            </div>
            <div class="activity-list">
              ${recentLogs.length === 0 ? `
                <p class="empty-state">No activity has been recorded yet.</p>
              ` : recentLogs.map(log => `
                <div class="activity-row">
                  <span>${new Date(log.created_at).toLocaleTimeString([], {hour: "2-digit", minute:"2-digit"})}</span>
                  <strong>${log.message}</strong>
                </div>
              `).join("")}
            </div>
          </section>
        </aside>
      </div>
    </div>
  `;
}

export function bindDashboard(navigate) {
  const newCaseBtn = document.getElementById("dashboard-new-case-btn");
  if (newCaseBtn) {
    newCaseBtn.addEventListener("click", () => navigate("cases"));
  }

  const reviewShortcut = document.getElementById("dashboard-session-shortcut");
  if (reviewShortcut) {
    reviewShortcut.addEventListener("click", () => navigate("transcript"));
  }

  const viewAllCases = document.getElementById("view-all-cases");
  if (viewAllCases) {
    viewAllCases.addEventListener("click", (e) => {
      e.preventDefault();
      navigate("cases");
    });
  }

  const reviewBtns = document.querySelectorAll(".navigate-transcript-btn");
  reviewBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const sessId = btn.getAttribute("data-session-id");
      store.setState({ selectedSessionId: sessId });
      navigate("transcript");
    });
  });

  const openBtns = document.querySelectorAll(".open-case-btn");
  openBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const caseId = btn.getAttribute("data-case-id");
      store.setState({ selectedCaseId: caseId, caseDetailTab: "overview" });
      navigate("case_detail");
    });
  });
}
