import { store } from "../store/state.js";
import { getVisibleCases, toggleStarCase } from "../services/case-service.js";
import { getVisibleSessions } from "../services/session-service.js";
import { renderGaugeChart } from "../components/gauge-chart.js";
import { renderTrendChart } from "../components/trend-chart.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { formatFileSize, labelize } from "@shared/utils/format.js";

export function renderDashboard() {
  const state = store.getState();
  const ownedCases = getVisibleCases();
  const ownedSessions = getVisibleSessions();

  const caseItem = ownedCases.find(c => c.case_id === state.selectedCaseId) || ownedCases[0];
  if (!caseItem) {
    return `<p class="empty-state">No visible anonymized cases. Please create a case.</p>`;
  }

  const transcriptQueue = ownedSessions.filter(
    s => s.therapist_review_status === "awaiting_review" || s.therapist_review_status === "needs_correction"
  );
  const reportQueue = ownedSessions.filter(s => s.report_status === "pending");

  // Sub-sections
  const focusCaseCard = `
    <div class="panel case-hero">
      <div class="case-top">
        <div class="avatar child">CH</div>
        <div>
          <p class="eyebrow">${caseItem.case_id}</p>
          <h3>${caseItem.display_label || caseItem.case_id} (${caseItem.anonymized_child_code})</h3>
          <p class="lead" style="font-size: 0.9rem;">${caseItem.primary_concerns}</p>
        </div>
        <button class="star-button icon-button star" data-case-id="${caseItem.case_id}">
          ${caseItem.starred ? "★" : "☆"}
        </button>
      </div>
      <div class="tag-row">
        <span class="mini-tag">Age: ${caseItem.age_months}m</span>
        <span class="mini-tag">Sex: ${caseItem.sex}</span>
        <span class="mini-tag status-pill status-good">${caseItem.anonymization_status}</span>
        <span class="mini-tag status-pill status-warn">${caseItem.external_clinical_status.replaceAll("_", " ")}</span>
      </div>
      <div class="support-box">
        <span>Clinical screening status:</span>
        <strong><i></i>${caseItem.support_level} Support</strong>
      </div>
      <div class="case-stats" style="margin-top: 10px;">
        <div>
          <strong>${ownedSessions.filter(s => s.case_id === caseItem.case_id).length}</strong>
          <span>Sessions</span>
        </div>
        <div>
          <strong>${state.audioFiles.filter(a => a.case_id === caseItem.case_id).length}</strong>
          <span>Audio Uploads</span>
        </div>
        <div>
          <strong>${state.generatedReports.filter(r => r.case_id === caseItem.case_id).length}</strong>
          <span>Reports</span>
        </div>
      </div>
    </div>
  `;

  const featureSummaryCard = `
    <div class="panel feature-panel" style="grid-column: span 2;">
      <div class="panel-title">
        <h3>Feature Summary (Latest Session)</h3>
        <span>extracted linguistic features</span>
      </div>
      <div class="feature-table">
        <div class="feature-head">
          <div>Domain</div>
          <div>Linguistic Feature</div>
          <div>Result Value</div>
          <div>Trend Change</div>
        </div>
        <div class="feature-row">
          <div class="feature-domain"><i class="sc"></i><span>Turn-taking</span></div>
          <div>Spontaneous interaction turn count</div>
          <div>0.62 / 1.00</div>
          <div class="positive">+0.12</div>
        </div>
        <div class="feature-row">
          <div class="feature-domain"><i></i><span>Mean Length of Utterance</span></div>
          <div>MLU in words</div>
          <div>3.25 words</div>
          <div class="positive">+0.45</div>
        </div>
        <div class="feature-row">
          <div class="feature-domain"><i></i><span>Vocabulary Diversity</span></div>
          <div>Type-token ratio (TTR)</div>
          <div>0.38</div>
          <div class="positive">+0.05</div>
        </div>
        <div class="feature-row">
          <div class="feature-domain"><i class="rp"></i><span>Repetitive Phrases</span></div>
          <div>Echolalia / Repetitive words</div>
          <div class="negative">High</div>
          <div class="negative">-0.08</div>
        </div>
        <div class="feature-row">
          <div class="feature-domain"><i class="am"></i><span>Pronoun Reversal</span></div>
          <div>Referring to self as you</div>
          <div>Occasional</div>
          <div class="negative">+0.10</div>
        </div>
      </div>
    </div>
  `;

  const factorsCard = `
    <div class="panel">
      <div class="panel-title">
        <h3>Top Contributing Factors</h3>
        <span>features contributing to concern level</span>
      </div>
      <div class="factor-columns" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
        <div>
          <h4 class="negative" style="font-size: 0.8rem; margin-bottom: 6px;">Increasing Concern</h4>
          <ul style="padding-left: 14px; margin: 0; font-size: 0.8rem; line-height: 1.4;">
            <li>Repetitive phrase frequency (+0.23)</li>
            <li>Limited reciprocal response (+0.18)</li>
            <li>Restricted interests (+0.12)</li>
          </ul>
        </div>
        <div>
          <h4 class="positive" style="font-size: 0.8rem; margin-bottom: 6px;">Reducing Concern</h4>
          <ul style="padding-left: 14px; margin: 0; font-size: 0.8rem; line-height: 1.4;">
            <li>Improved turn-taking (-0.15)</li>
            <li>More varied vocabulary (-0.10)</li>
            <li>Better eye contact (-0.08)</li>
          </ul>
        </div>
      </div>
    </div>
  `;

  const recentCases = ownedCases
    .slice()
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
    .slice(0, 3);
  const recentSessions = ownedSessions
    .slice()
    .sort((a, b) => b.session_date.localeCompare(a.session_date))
    .slice(0, 3);

  const queuesCard = `
    <div class="panel" style="grid-column: span 3; margin-top: 10px;">
      <div class="panel-title">
        <h3>Work Queues & Active Cases</h3>
        <span>manage clinical tasks</span>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;">
        <div>
          <h4>High Review-Priority Cases</h4>
          <div style="display: grid; gap: 6px;">
            ${recentCases
              .map(
                c => `
              <div style="padding: 8px; border: 1px solid var(--line); border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
                <strong>${c.display_label} (${c.anonymized_child_code})</strong>
                <span class="status-pill status-warn">Score: ${c.latest_score.toFixed(2)}</span>
              </div>
            `
              )
              .join("")}
          </div>
        </div>
        <div>
          <h4>Transcript Review Queue</h4>
          <div style="display: grid; gap: 6px;">
            ${transcriptQueue
              .map(
                s => `
              <div style="padding: 8px; border: 1px solid var(--line); border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
                <span>Session ${s.session_id.replace("SESSION-", "")}</span>
                <button class="small-action navigate-transcript" data-session-id="${s.session_id}">Review</button>
              </div>
            `
              )
              .join("")}
            ${transcriptQueue.length === 0 ? '<p class="empty-state" style="font-size: 0.8rem;">Queue is empty.</p>' : ""}
          </div>
        </div>
        <div>
          <h4>Generated Reports Queue</h4>
          <div style="display: grid; gap: 6px;">
            ${reportQueue
              .map(
                s => `
              <div style="padding: 8px; border: 1px solid var(--line); border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
                <span>Session ${s.session_id.replace("SESSION-", "")}</span>
                <button class="small-action navigate-report" data-session-id="${s.session_id}">Report</button>
              </div>
            `
              )
              .join("")}
            ${reportQueue.length === 0 ? '<p class="empty-state" style="font-size: 0.8rem;">Queue is empty.</p>' : ""}
          </div>
        </div>
      </div>
    </div>
  `;

  return `
    ${renderSafetyBanner()}
    <section class="dashboard-command">
      <div>
        <p>Overview of your caseload and recent activities</p>
      </div>
      <div class="action-row">
        <select id="case-filter" aria-label="Select child case" style="padding: 6px; border-radius: var(--radius); border: 1px solid var(--line);">
          ${ownedCases
            .map(
              c =>
                `<option value="${c.case_id}" ${c.case_id === caseItem.case_id ? "selected" : ""}>${c.display_label} (${c.anonymized_child_code})</option>`
            )
            .join("")}
        </select>
        <button class="primary-action" id="dashboard-new-session-btn">+ New Session</button>
      </div>
    </section>
    
    <section class="dashboard-grid" style="display: grid; grid-template-columns: 1.2fr 0.8fr 1fr; gap: 16px;">
      ${focusCaseCard}
      ${renderGaugeChart(caseItem.latest_score)}
      ${renderTrendChart(caseItem.score_trend)}
    </section>

    <section class="dashboard-grid" style="display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-top: 16px;">
      ${featureSummaryCard}
      ${factorsCard}
    </section>

    <section class="metric-strip" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 16px;">
      <div class="panel metric-card" style="padding: 12px; text-align: center;">
        <h3>Active cases</h3>
        <strong style="font-size: 1.6rem; display: block;">${ownedCases.length}</strong>
        <span style="font-size: 0.8rem; color: var(--muted);">visible to this user</span>
      </div>
      <div class="panel metric-card" style="padding: 12px; text-align: center;">
        <h3>Transcript review</h3>
        <strong style="font-size: 1.6rem; display: block; color: var(--amber);">${transcriptQueue.length}</strong>
        <span style="font-size: 0.8rem; color: var(--muted);">awaiting review</span>
      </div>
      <div class="panel metric-card" style="padding: 12px; text-align: center;">
        <h3>Reports pending</h3>
        <strong style="font-size: 1.6rem; display: block; color: var(--violet);">${reportQueue.length}</strong>
        <span style="font-size: 0.8rem; color: var(--muted);">ready after review</span>
      </div>
      <div class="panel metric-card" style="padding: 12px; text-align: center;">
        <h3>Uploaded files</h3>
        <strong style="font-size: 1.6rem; display: block;">${state.audioFiles.length}</strong>
        <span style="font-size: 0.8rem; color: var(--muted);">metadata only</span>
      </div>
    </section>

    <section class="panel quick-actions-panel" style="margin-top: 16px; padding: 16px;">
      <div class="panel-title">
        <h3>Quick Actions</h3>
        <span>mock workflow shortcuts</span>
      </div>
      <div class="quick-action-grid" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
        <button class="secondary-action quick-create-case-btn">Create case</button>
        <button class="secondary-action quick-add-session-btn">Add session</button>
        <button class="secondary-action quick-upload-audio-btn">Upload audio metadata</button>
        <button class="primary-action quick-generate-report-btn">Generate report</button>
      </div>
    </section>

    ${queuesCard}

    <section class="clinical-callout" style="margin-top: 16px; padding: 14px; background: var(--violet-soft); border-radius: var(--radius); border: 1px solid var(--line);">
      <strong>💡 Clinical Reminder:</strong>
      <span style="font-size: 0.9rem; color: var(--violet-strong); display: block; margin-top: 4px;">
        All language analysis, scores, and feature trends are meant to supplement clinician observations. The system is designed for progress tracking and clinical decision support only.
      </span>
    </section>
  `;
}

export function bindDashboard(navigate) {
  const caseFilter = document.getElementById("case-filter");
  if (caseFilter) {
    caseFilter.addEventListener("change", e => {
      store.setState({ selectedCaseId: e.target.value });
      navigate("dashboard");
    });
  }

  const starBtn = document.querySelector(".star-button");
  if (starBtn) {
    starBtn.addEventListener("click", () => {
      const caseId = starBtn.getAttribute("data-case-id");
      toggleStarCase(caseId);
      navigate("dashboard");
    });
  }

  const newSessionBtn = document.getElementById("dashboard-new-session-btn");
  if (newSessionBtn) {
    newSessionBtn.addEventListener("click", () => navigate("session"));
  }

  // Quick Action Buttons
  const createBtn = document.querySelector(".quick-create-case-btn");
  if (createBtn) {
    createBtn.addEventListener("click", () => navigate("cases"));
  }
  const addSessBtn = document.querySelector(".quick-add-session-btn");
  if (addSessBtn) {
    addSessBtn.addEventListener("click", () => navigate("session"));
  }
  const uploadAudBtn = document.querySelector(".quick-upload-audio-btn");
  if (uploadAudBtn) {
    uploadAudBtn.addEventListener("click", () => navigate("session"));
  }
  const genRepBtn = document.querySelector(".quick-generate-report-btn");
  if (genRepBtn) {
    genRepBtn.addEventListener("click", () => navigate("reports"));
  }

  // Work queues navigation
  const transcriptNavBtns = document.querySelectorAll(".navigate-transcript");
  transcriptNavBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const sessId = btn.getAttribute("data-session-id");
      store.setState({ selectedSessionId: sessId });
      navigate("transcript");
    });
  });

  const reportNavBtns = document.querySelectorAll(".navigate-report");
  reportNavBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const sessId = btn.getAttribute("data-session-id");
      store.setState({ selectedSessionId: sessId });
      navigate("reports");
    });
  });
}
