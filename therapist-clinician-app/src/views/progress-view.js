import { store } from "../store/state.js";
import { getChildProgress } from "../services/progress-service.js";
import { buildProgressReportMarkdown } from "../services/report-service.js";
import { renderRadarChart, radarEntries } from "../components/radar-chart.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { addAudit } from "../services/audit-service.js";

export function renderProgressReports() {
  const state = store.getState();
  const progress = getChildProgress(state.selectedCaseId);

  if (!progress) {
    return `
      ${renderSafetyBanner()}
      <p class="empty-state">No progress data found for the selected child. Please add sessions and complete transcript reviews first.</p>
    `;
  }

  const { caseItem, sessions, goals } = progress;

  // Render score timeline list
  const timelineHtml = sessions
    .map(
      s => `
    <div style="padding: 10px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--shell); display: flex; justify-content: space-between; align-items: center;">
      <div>
        <strong>Session ${s.session_id.replace("SESSION-", "")}</strong>
        <span style="font-size: 0.8rem; color: var(--muted); margin-left: 10px;">${s.date}</span>
      </div>
      <div style="display: flex; align-items: center; gap: 12px;">
        <span class="status-pill status-good" style="font-weight: 800;">Score: ${s.score.toFixed(2)}</span>
        <span class="status-pill status-warn">${s.review_status}</span>
      </div>
    </div>
  `
    )
    .join("");

  // Feature trends list
  const trendsHtml = `
    <div style="display: grid; gap: 8px;">
      <div style="padding: 10px; border: 1px solid var(--line); border-radius: 4px; display: flex; justify-content: space-between;">
        <span>Mean Length of Utterance (MLU):</span>
        <strong>${sessions.length ? sessions[sessions.length - 1].mlu.toFixed(2) : "0.00"} words</strong>
      </div>
      <div style="padding: 10px; border: 1px solid var(--line); border-radius: 4px; display: flex; justify-content: space-between;">
        <span>Vocabulary Diversity (TTR):</span>
        <strong>${sessions.length ? sessions[sessions.length - 1].ttr.toFixed(2) : "0.00"}</strong>
      </div>
      <div style="padding: 10px; border: 1px solid var(--line); border-radius: 4px; display: flex; justify-content: space-between;">
        <span>Echolalia Ratio:</span>
        <strong>${sessions.length ? sessions[sessions.length - 1].echolalia_ratio.toFixed(2) : "0.00"}</strong>
      </div>
    </div>
  `;

  // Goals progress
  const goalsHtml = goals
    .map(
      g => `
    <div style="padding: 8px; border: 1px solid var(--line); border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
      <span style="font-size: 0.9rem;">${g.text}</span>
      <span class="status-pill status-good">${g.status}</span>
    </div>
  `
    )
    .join("");

  const radarChartHtml = renderRadarChart(radarEntries(caseItem));

  return `
    ${renderSafetyBanner()}
    <section class="dashboard-command" style="margin-bottom: 16px;">
      <div>
        <h2>Printable / Exportable Progress Report</h2>
        <p style="color: var(--muted); font-size: 0.85rem;">This tool is for progress tracking and clinical decision support only.</p>
      </div>
      <div style="display: flex; gap: 10px;">
        <button class="secondary-action" id="download-progress-md-btn" data-case-id="${caseItem.case_id}">
          Download Markdown
        </button>
        <button class="primary-action" id="print-progress-pdf-btn">
          Print / Save PDF
        </button>
      </div>
    </section>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
      <section class="panel" style="padding: 16px;">
        <div class="panel-title">
          <h3>Score Timeline</h3>
          <span>longitudinal concern metrics</span>
        </div>
        <div style="display: grid; gap: 8px;">
          ${timelineHtml || '<p class="empty-state">No session timeline scores found.</p>'}
        </div>
      </section>

      ${radarChartHtml}
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
      <section class="panel" style="padding: 16px;">
        <div class="panel-title">
          <h3>Feature Trends Over Sessions</h3>
          <span>longitudinal language feature values</span>
        </div>
        ${trendsHtml}
      </section>

      <section class="panel" style="padding: 16px;">
        <div class="panel-title">
          <h3>Therapy Goal Progress</h3>
          <span>caseload active goals</span>
        </div>
        <div style="display: grid; gap: 8px;">
          ${goalsHtml || '<p class="empty-state">No active goal records for this case.</p>'}
        </div>
      </section>
    </div>
  `;
}

export function bindProgressReports(navigate) {
  const downloadBtn = document.getElementById("download-progress-md-btn");
  if (downloadBtn) {
    downloadBtn.addEventListener("click", () => {
      const caseId = downloadBtn.getAttribute("data-case-id");
      const state = store.getState();

      const caseItem = state.cases.find(c => c.case_id === caseId);
      const childSessions = state.sessions.filter(s => s.case_id === caseId);

      // Generate report using buildProgressReportMarkdown
      const reportMd = buildProgressReportMarkdown(
        caseItem,
        childSessions,
        state.extractedFeatureOutputs,
        state.aiDecisionOutputs
      );

      const a = document.createElement("a");
      const file = new Blob([reportMd], { type: "text/markdown" });
      a.href = URL.createObjectURL(file);
      a.download = `${caseItem.anonymized_child_code}_progress_report.md`;
      a.click();

      addAudit("report_exported", "ChildCase", caseId, `Exported progress report markdown for case ${caseId}`);
    });
  }

  const printBtn = document.getElementById("print-progress-pdf-btn");
  if (printBtn) {
    printBtn.addEventListener("click", () => {
      window.print();
      addAudit("print_report", "ChildCase", store.getState().selectedCaseId, "Printed / Saved PDF progress report.");
    });
  }
}
