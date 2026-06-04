import { store } from "../store/state.js";
import { getVisibleCases } from "../services/case-service.js";
import { getVisibleSessions } from "../services/session-service.js";
import { renderTrendChart } from "../components/trend-chart.js";
import { iconSvg } from "../components/icons.js";

export function renderCaseDetail() {
  const state = store.getState();
  const cases = getVisibleCases();
  const caseItem = cases.find(c => c.case_id === state.selectedCaseId) || cases[0];

  if (!caseItem) {
    return `<p class="empty-state">No case selected.</p>`;
  }

  const sessions = getVisibleSessions().filter(s => s.case_id === caseItem.case_id);
  const activeTab = state.caseDetailTab || "overview";

  // Tab Header HTML
  const tabs = [
    ["overview", "Overview"],
    ["sessions", "Sessions"],
    ["transcript", "Transcripts"],
    ["ai_review", "AI Review"],
    ["progress", "Progress"],
    ["notes", "Notes"],
    ["reports", "Reports"]
  ];

  const tabsHtml = tabs.map(([key, label]) => `
    <button class="case-tab-btn ${activeTab === key ? "active" : ""}" data-tab="${key}" style="
      background: ${activeTab === key ? "var(--primary-soft)" : "transparent"};
      color: ${activeTab === key ? "var(--primary)" : "var(--muted)"};
      border: none;
      border-bottom: 2px solid ${activeTab === key ? "var(--primary)" : "transparent"};
      padding: 10px 16px;
      font-weight: 600;
      font-size: 0.9rem;
      cursor: pointer;
      transition: all 0.2s ease;
    ">${label}</button>
  `).join("");

  // Determine Tab Content
  let tabContentHtml = "";
  if (activeTab === "overview") {
    // Overview tab: timeline, charts, features summary, quality indicators
    const timelineHtml = sessions.length > 0 
      ? `<div style="display: flex; flex-direction: column; gap: 12px; position: relative; padding-left: 20px; border-left: 2px solid var(--slate); margin-top: 10px;">
          ${sessions.map((s, idx) => `
            <div style="position: relative; margin-bottom: 8px;">
              <div style="position: absolute; left: -27px; top: 2px; width: 12px; height: 12px; border-radius: 50%; background: var(--primary); border: 2px solid #fff;"></div>
              <strong style="font-size: 0.9rem; color: var(--ink);">Session ${idx + 1}: ${s.session_date}</strong>
              <div style="font-size: 0.75rem; color: var(--muted); margin-top: 2px;">
                Review: <span class="status-pill" style="font-size: 0.65rem; background: ${s.therapist_review_status === "reviewed" ? "var(--mint-soft)" : "var(--amber-soft)"}; color: ${s.therapist_review_status === "reviewed" ? "var(--mint)" : "var(--amber-pending)"};">${s.therapist_review_status}</span>
                · QA: ${s.qa_status || "Pass"}
              </div>
            </div>
          `).join("")}
         </div>`
      : `<p class="empty-state" style="font-size: 0.85rem;">No sessions recorded for this case.</p>`;

    tabContentHtml = `
      <div style="display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 24px; align-items: start;">
        <!-- Left: Clinical Timeline & Notes -->
        <div style="display: flex; flex-direction: column; gap: 20px;">
          <div class="glass-card" style="padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-md);">
            <h4 style="margin-bottom: 12px; font-size: 1rem; color: var(--ink);">Clinical Session Timeline</h4>
            ${timelineHtml}
          </div>
          
          <div class="glass-card" style="padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-md);">
            <h4 style="margin-bottom: 8px; font-size: 1rem; color: var(--ink);">Therapist Notes & Insights</h4>
            <p style="font-size: 0.85rem; color: var(--muted); line-height: 1.5;">
              ${caseItem.notes || "No therapist notes recorded. Select the Notes tab to add internal case commentary."}
            </p>
          </div>
        </div>

        <!-- Right: SVG Trend & Feature summaries -->
        <div style="display: flex; flex-direction: column; gap: 20px;">
          <div class="glass-card" style="padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-md);">
            <h4 style="margin-bottom: 12px; font-size: 1rem; color: var(--ink);">Speech Metrics Trend</h4>
            ${renderTrendChart(caseItem.score_trend || [0.4, 0.45, 0.52])}
          </div>

          <div class="glass-card" style="padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-md); display: flex; flex-direction: column; gap: 12px;">
            <h4 style="margin-bottom: 4px; font-size: 1rem; color: var(--ink);">Observations Summary</h4>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; padding-bottom: 8px; border-bottom: 1px solid var(--slate);">
              <span>Mean Length of Utterance (MLU)</span>
              <strong style="color: var(--primary);">3.25 words</strong>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; padding-bottom: 8px; border-bottom: 1px solid var(--slate);">
              <span>Vocabulary Diversity (TTR)</span>
              <strong style="color: var(--primary);">0.38</strong>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; padding-bottom: 8px; border-bottom: 1px solid var(--slate);">
              <span>Turn-taking interaction</span>
              <strong style="color: var(--primary);">0.62 ratio</strong>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem;">
              <span>Data Quality Status</span>
              <span class="status-pill" style="background: var(--mint-soft); color: var(--mint); font-size: 0.7rem; font-weight: 600;">Good Quality</span>
            </div>
          </div>
        </div>
      </div>
    `;
  } else if (activeTab === "sessions") {
    tabContentHtml = `
      <div class="glass-card" style="padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-md);">
        <h4 style="margin-bottom: 12px; font-size: 1rem; color: var(--ink);">Child Case Sessions</h4>
        <div style="display: flex; flex-direction: column; gap: 10px;">
          ${sessions.map((s, idx) => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid var(--lavender);">
              <div>
                <strong style="font-size: 0.9rem;">Session ${idx + 1} (${s.session_date})</strong>
                <div style="font-size: 0.75rem; color: var(--muted); margin-top: 2px;">Review: ${s.therapist_review_status} · Type: Picture Description</div>
              </div>
              <button class="small-action open-session-btn" data-session-id="${s.session_id}" style="min-height: 32px; padding: 4px 12px; font-size: 0.8rem;">Open</button>
            </div>
          `).join("")}
          ${sessions.length === 0 ? `<p class="empty-state">No sessions added yet.</p>` : ""}
        </div>
      </div>
    `;
  } else {
    // Other tabs redirect to their corresponding main app views
    tabContentHtml = `
      <div style="text-align: center; padding: 36px;" class="glass-card">
        <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 10px;"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
        <p style="font-size: 0.9rem; color: var(--ink);">Detailed assessment review lives in the central workspaces. Click below to open.</p>
        <button class="primary-action redirect-tab-btn" data-target-tab="${activeTab}" style="margin-top: 10px; min-height: 38px; font-size: 0.85rem; font-weight: 600;">
          Go to ${activeTab.toUpperCase()} Workspace
        </button>
      </div>
    `;
  }

  return `
    <div style="display: flex; flex-direction: column; gap: 20px;">
      <!-- Profile Header -->
      <div class="glass-card" style="padding: 24px; border: 1px solid var(--line); border-radius: var(--radius-lg); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
        <div style="display: flex; align-items: center; gap: 16px;">
          <div class="avatar child" style="width: 54px; height: 54px; font-size: 1.2rem;">CH</div>
          <div>
            <h3 style="font-size: 1.35rem; color: var(--ink); margin-bottom: 4px;">${caseItem.display_label} (${caseItem.anonymized_child_code})</h3>
            <div style="display: flex; align-items: center; gap: 12px; font-size: 0.85rem; color: var(--muted);">
              <span>Age: <strong>${caseItem.age_months} mo</strong></span>
              <span>Sex: <strong style="text-transform: capitalize;">${caseItem.sex}</strong></span>
              <span>Therapist: <strong>${caseItem.owner_user_id === "user_therapist_001" ? "Therapist" : "Clinician"}</strong></span>
            </div>
          </div>
        </div>
        <div style="text-align: right; display: flex; flex-direction: column; gap: 6px;">
          <span style="font-size: 0.75rem; color: var(--muted);">Total Language Samples: <strong>${sessions.length}</strong></span>
          <span style="font-size: 0.75rem; color: var(--muted);">Latest Session: <strong>${sessions[0]?.session_date || "N/A"}</strong></span>
        </div>
      </div>

      <!-- Disclaimer banner -->
      <div class="clinical-status-banner status-bad-soft" style="margin-bottom: 0; padding: 12px; border-radius: var(--radius-md); display: flex; align-items: center; gap: 8px;">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--destructive)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span style="font-size: 0.8rem; color: var(--ink); font-weight: 500;">
          <strong>Clinical Decision Support Boundary:</strong> AI-assisted observations only. Final interpretation must be reviewed by a clinician. This system does not diagnose ASD.
        </span>
      </div>

      <!-- Tabs Bar -->
      <div style="display: flex; border-bottom: 1.5px solid var(--slate); margin-top: 4px; overflow-x: auto; white-space: nowrap;">
        ${tabsHtml}
      </div>

      <!-- Tab Content Area -->
      <div style="margin-top: 8px;">
        ${tabContentHtml}
      </div>
    </div>
  `;
}

export function bindCaseDetail(navigate) {
  // Tab buttons click
  const tabBtns = document.querySelectorAll(".case-tab-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const tab = btn.getAttribute("data-tab");
      store.setState({ caseDetailTab: tab });
      navigate("case_detail");
    });
  });

  // Redirect buttons click
  const redirectBtns = document.querySelectorAll(".redirect-tab-btn");
  redirectBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-target-tab");
      // Map to correct workspace
      let view = target;
      if (target === "transcript") view = "transcript";
      if (target === "ai_review") view = "ai_review";
      if (target === "progress") view = "progress";
      if (target === "reports") view = "reports";
      if (target === "notes") view = "transcript";
      navigate(view);
    });
  });

  // Open session buttons
  const openSessBtns = document.querySelectorAll(".open-session-btn");
  openSessBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const sessId = btn.getAttribute("data-session-id");
      store.setState({ selectedSessionId: sessId });
      navigate("transcript");
    });
  });
}
