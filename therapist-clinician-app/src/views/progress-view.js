import { store } from "../store/state.js";
import { getChildProgress } from "../services/progress-service.js";
import { buildProgressReportMarkdown } from "../services/report-service.js";
import { renderRadarChart, radarEntries } from "../components/radar-chart.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { addAudit } from "../services/audit-service.js";
import { renderAccessDenied } from "../components/access-denied.js";
import { getVisibleCases } from "../services/case-service.js";

// Standard observation schema definition
const defaultObservations = [
  { key: "pronoun_reversal", name: "Pronoun Reversal", snippet: "CHI: referenced self as 'you' in utterance 3", type: "Linguistic" },
  { key: "repetitive_language", name: "Repetitive Language", snippet: "Repeated 'red car' 4 times in 25 seconds", type: "Linguistic" },
  { key: "response_latency", name: "Response Latency", snippet: "Average response pause of 4.5 seconds", type: "Acoustic/Interaction" },
  { key: "speech_rate", name: "Speech Rate", snippet: "135 words per minute (normal range)", type: "Acoustic" },
  { key: "prosody", name: "Prosody / Acoustic Features", snippet: "Voiced ratio 0.62, monotonic pitch patterns", type: "Acoustic" },
  { key: "word_repetition", name: "Unusual Word Repetition", snippet: "Repeated 'car' 12 times overall", type: "Linguistic" },
  { key: "social_comm", name: "Social Communication Markers", snippet: "Minimal gaze/spontaneous turn-taking", type: "Interaction" }
];

export function renderProgressReports() {
  const state = store.getState();
  const progress = getChildProgress(state.selectedCaseId);

  const cases = getVisibleCases();
  const caseOptionsHtml = cases.map(c => `
    <option value="${c.case_id}" ${c.case_id === state.selectedCaseId ? "selected" : ""}>
      ${c.display_label} (${c.anonymized_child_code})
    </option>
  `).join("");

  const caseSelectorHtml = `
    <div class="glass-card print-hide" style="padding: 16px; border: 1px solid var(--line); border-radius: var(--radius-md); display: flex; gap: 12px; align-items: center; margin-bottom: 16px; background: #fff;">
      <label for="progress-case-selector" style="font-weight: 600; color: var(--ink); font-size: 0.9rem;">Select Child Case:</label>
      <select id="progress-case-selector" class="glass-input" style="max-width: 320px; min-height: 38px; padding: 6px 12px; border: 1px solid var(--line); border-radius: var(--radius-sm);">
        ${caseOptionsHtml}
      </select>
    </div>
  `;

  if (!progress) {
    const selectedCaseExists = state.cases.some(c => c.case_id === state.selectedCaseId);
    return `
      ${renderSafetyBanner()}
      ${caseSelectorHtml}
      ${selectedCaseExists ? renderAccessDenied() : '<div style="text-align:center; padding:48px;" class="glass-card"><p class="empty-state">No progress data found for the selected child. Please add sessions and complete transcript reviews first.</p></div>'}
    `;
  }

  const { caseItem, sessions, goals } = progress;
  const reviews = state.observationsReviews || {};
  const currentDate = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });

  // 1. Filter and count reviewed sessions
  const reviewedSessions = sessions.filter(s => s.review_status === "reviewed");
  const totalSessionsCount = sessions.length;

  // 2. Extract and compile only therapist-approved observations (accepted or edited, excluding rejected)
  const compiledObservations = [];
  sessions.forEach(s => {
    const sessReviews = reviews[s.session_id] || {};
    defaultObservations.forEach(obs => {
      const rev = sessReviews[obs.key] || { status: "pending", note: "" };
      if (rev.status === "accepted" || rev.status === "edited") {
        compiledObservations.push({
          session_id: s.session_id,
          session_date: s.date,
          key: obs.key,
          name: obs.name,
          snippet: obs.snippet,
          note: rev.note || "No additional clinician notes added.",
          status: rev.status
        });
      }
    });
  });

  // Safe Thai Summary Text
  let currentThaiSummary = (state.therapistThaiSummaries && state.therapistThaiSummaries[state.selectedCaseId]) || "";
  if (!currentThaiSummary) {
    currentThaiSummary = `**สรุปแนวโน้มพัฒนาการจากข้อมูลเชิงพรรณนาเบื้องต้น:**\n` + generateAutoSummaryText(sessions, state.sessionVocabs || {});
  }

  // Draw longitudinal SVGs
  const svgWidth = 500;
  const svgHeight = 150;
  const paddingLeft = 40;
  const paddingRight = 20;
  const paddingTop = 20;
  const paddingBottom = 30;

  // Generate Score Timeline Chart (SVG Line Chart)
  let scoreChartSvg = "";
  if (sessions.length > 0) {
    const maxScore = 1.0;
    const minScore = 0.0;
    
    // Points calculations
    const points = sessions.map((s, idx) => {
      const x = paddingLeft + (idx / (sessions.length > 1 ? sessions.length - 1 : 1)) * (svgWidth - paddingLeft - paddingRight);
      const y = paddingTop + (1 - (s.score - minScore) / (maxScore - minScore)) * (svgHeight - paddingTop - paddingBottom);
      return { x, y, label: `S${idx+1}`, score: s.score };
    });

    const pathD = points.map((p, idx) => `${idx === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
    
    const dotsHtml = points.map(p => `
      <circle cx="${p.x}" cy="${p.y}" r="4" fill="var(--primary)" stroke="#fff" stroke-width="2" />
      <text x="${p.x}" y="${p.y - 8}" text-anchor="middle" font-size="9" font-weight="bold" fill="var(--ink)">${p.score.toFixed(2)}</text>
      <text x="${p.x}" y="${svgHeight - 10}" text-anchor="middle" font-size="9" fill="var(--muted)">${p.label}</text>
    `).join("");

    scoreChartSvg = `
      <svg width="100%" height="${svgHeight}" viewBox="0 0 ${svgWidth} ${svgHeight}" style="overflow: visible;">
        <!-- Grid lines -->
        <line x1="${paddingLeft}" y1="${paddingTop}" x2="${svgWidth - paddingRight}" y2="${paddingTop}" stroke="var(--slate)" stroke-dasharray="3,3" />
        <line x1="${paddingLeft}" y1="${(paddingTop + svgHeight - paddingBottom) / 2}" x2="${svgWidth - paddingRight}" y2="${(paddingTop + svgHeight - paddingBottom) / 2}" stroke="var(--slate)" stroke-dasharray="3,3" />
        <line x1="${paddingLeft}" y1="${svgHeight - paddingBottom}" x2="${svgWidth - paddingRight}" y2="${svgHeight - paddingBottom}" stroke="var(--slate)" />
        
        <!-- Y Axis Labels -->
        <text x="${paddingLeft - 10}" y="${paddingTop + 3}" text-anchor="end" font-size="9" fill="var(--muted)">1.0</text>
        <text x="${paddingLeft - 10}" y="${(paddingTop + svgHeight - paddingBottom) / 2 + 3}" text-anchor="end" font-size="9" fill="var(--muted)">0.5</text>
        <text x="${paddingLeft - 10}" y="${svgHeight - paddingBottom + 3}" text-anchor="end" font-size="9" fill="var(--muted)">0.0</text>
        
        <!-- Path -->
        ${sessions.length > 1 ? `<path d="${pathD}" fill="none" stroke="var(--primary)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />` : ""}
        
        <!-- Dots and labels -->
        ${dotsHtml}
      </svg>
    `;
  }

  // Generate MLU Chart (SVG Line Chart)
  let mluChartSvg = "";
  if (sessions.length > 0) {
    const maxMlu = 6.0;
    const minMlu = 0.0;
    
    // Points calculations
    const points = sessions.map((s, idx) => {
      const x = paddingLeft + (idx / (sessions.length > 1 ? sessions.length - 1 : 1)) * (svgWidth - paddingLeft - paddingRight);
      const y = paddingTop + (1 - (s.mlu - minMlu) / (maxMlu - minMlu)) * (svgHeight - paddingTop - paddingBottom);
      return { x, y, label: `S${idx+1}`, val: s.mlu };
    });

    const pathD = points.map((p, idx) => `${idx === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
    
    const dotsHtml = points.map(p => `
      <circle cx="${p.x}" cy="${p.y}" r="4" fill="var(--medical-blue)" stroke="#fff" stroke-width="2" />
      <text x="${p.x}" y="${p.y - 8}" text-anchor="middle" font-size="9" font-weight="bold" fill="var(--ink)">${p.val.toFixed(2)}</text>
      <text x="${p.x}" y="${svgHeight - 10}" text-anchor="middle" font-size="9" fill="var(--muted)">${p.label}</text>
    `).join("");

    mluChartSvg = `
      <svg width="100%" height="${svgHeight}" viewBox="0 0 ${svgWidth} ${svgHeight}" style="overflow: visible;">
        <!-- Grid lines -->
        <line x1="${paddingLeft}" y1="${paddingTop}" x2="${svgWidth - paddingRight}" y2="${paddingTop}" stroke="var(--slate)" stroke-dasharray="3,3" />
        <line x1="${paddingLeft}" y1="${(paddingTop + svgHeight - paddingBottom) / 2}" x2="${svgWidth - paddingRight}" y2="${(paddingTop + svgHeight - paddingBottom) / 2}" stroke="var(--slate)" stroke-dasharray="3,3" />
        <line x1="${paddingLeft}" y1="${svgHeight - paddingBottom}" x2="${svgWidth - paddingRight}" y2="${svgHeight - paddingBottom}" stroke="var(--slate)" />
        
        <!-- Y Axis Labels -->
        <text x="${paddingLeft - 10}" y="${paddingTop + 3}" text-anchor="end" font-size="9" fill="var(--muted)">6.0</text>
        <text x="${paddingLeft - 10}" y="${(paddingTop + svgHeight - paddingBottom) / 2 + 3}" text-anchor="end" font-size="9" fill="var(--muted)">3.0</text>
        <text x="${paddingLeft - 10}" y="${svgHeight - paddingBottom + 3}" text-anchor="end" font-size="9" fill="var(--muted)">0.0</text>
        
        <!-- Path -->
        ${sessions.length > 1 ? `<path d="${pathD}" fill="none" stroke="var(--medical-blue)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />` : ""}
        
        <!-- Dots and labels -->
        ${dotsHtml}
      </svg>
    `;
  }

  // Session Completion Timeline Stepper HTML
  const stepperHtml = sessions.map((s, idx) => {
    const isCompleted = s.review_status === "reviewed";
    return `
      <div style="display: flex; flex-direction: column; align-items: center; position: relative; flex: 1;">
        <div style="width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; font-weight: bold; 
          background: ${isCompleted ? "var(--mint-soft)" : "var(--amber-soft)"}; 
          color: ${isCompleted ? "var(--mint)" : "var(--amber-pending)"}; 
          border: 2px solid ${isCompleted ? "var(--mint)" : "var(--amber-pending)"}; z-index: 2;">
          ${idx + 1}
        </div>
        <span style="font-size: 0.75rem; font-weight: 600; margin-top: 6px; color: var(--ink);">Session ${idx + 1}</span>
        <span style="font-size: 0.65rem; color: var(--muted);">${s.date}</span>
        <span class="status-pill" style="font-size: 0.65rem; margin-top: 4px; 
          background: ${isCompleted ? "var(--mint-soft)" : "var(--amber-soft)"}; 
          color: ${isCompleted ? "var(--mint)" : "var(--amber-pending)"};">
          ${isCompleted ? "Reviewed" : "Pending"}
        </span>
      </div>
    `;
  }).join(`
    <div style="flex: 1; height: 2px; background: var(--slate); margin-top: 14px; position: relative; top: 0;"></div>
  `);

  return `
    ${renderSafetyBanner()}
    ${caseSelectorHtml}

    <!-- Header Actions Bar -->
    <section class="dashboard-command print-hide" style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; background: #fff; padding: 16px; border: 1px solid var(--line); border-radius: var(--radius-md);">
      <div>
        <h3 style="margin: 0; font-size: 1.15rem; color: var(--ink);">Research-Friendly Progress Report</h3>
        <p style="color: var(--muted); font-size: 0.8rem; margin: 4px 0 0;">Longitudinal progress tracking and clinical decision support summary.</p>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="secondary-action" id="download-progress-json-btn" data-case-id="${caseItem.case_id}" style="min-height: 36px; padding: 6px 12px; font-size: 0.8rem; font-weight: 600;">
          Download Anonymized Research Summary
        </button>
        <button class="secondary-action" id="download-progress-md-btn" data-case-id="${caseItem.case_id}" style="min-height: 36px; padding: 6px 12px; font-size: 0.8rem; font-weight: 600;">
          Export MD
        </button>
        <button class="primary-action" id="print-progress-pdf-btn" style="min-height: 36px; padding: 6px 12px; font-size: 0.8rem; font-weight: 600;">
          Print / Export PDF
        </button>
      </div>
    </section>

    <!-- Report Paper Workspace -->
    <div class="glass-card" style="padding: 34px; border: 1px solid var(--line); border-radius: var(--radius-lg); background: #ffffff; display: flex; flex-direction: column; gap: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.015);">
      
      <!-- 1. Report Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid var(--primary); padding-bottom: 16px;">
        <div>
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
            <span style="font-size: 0.75rem; background: var(--primary-soft); color: var(--primary); font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em;">Speech Analysis Lab</span>
            <span style="font-size: 0.75rem; background: var(--cyan-pale); color: var(--medical-blue); font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase;">Research Prototype</span>
          </div>
          <h2 style="margin: 0; font-size: 1.5rem; color: var(--ink); font-weight: 800;">CLINICAL PROGRESS SUMMARY REPORT</h2>
          <span style="font-size: 0.8rem; color: var(--muted);">Anonymized Longitudinal speech-language profile analysis</span>
        </div>
        <div style="text-align: right; font-size: 0.85rem; color: var(--muted); display: flex; flex-direction: column; gap: 3px;">
          <span>Reviewed Date: <strong>${currentDate}</strong></span>
          <span>Clinician ID: <strong>${state.currentUser.name}</strong></span>
        </div>
      </div>

      <!-- Child Profile Grid -->
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius-md); padding: 16px;">
        <div>
          <span style="font-size: 0.75rem; color: var(--muted); text-transform: uppercase;">Anonymized Code</span>
          <div style="font-size: 0.95rem; font-weight: bold; color: var(--ink); margin-top: 4px;">${caseItem.anonymized_child_code}</div>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--muted); text-transform: uppercase;">Age</span>
          <div style="font-size: 0.95rem; font-weight: bold; color: var(--ink); margin-top: 4px;">${caseItem.age_months} months</div>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--muted); text-transform: uppercase;">Sex</span>
          <div style="font-size: 0.95rem; font-weight: bold; color: var(--ink); margin-top: 4px; text-transform: capitalize;">${caseItem.sex}</div>
        </div>
        <div>
          <span style="font-size: 0.75rem; color: var(--muted); text-transform: uppercase;">Total Samples</span>
          <div style="font-size: 0.95rem; font-weight: bold; color: var(--ink); margin-top: 4px;">${reviewedSessions.length} Reviewed / ${totalSessionsCount} Total</div>
        </div>
      </div>

      <!-- 2. Summary of Reviewed Sessions, Observations, & Data Limitations -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
        
        <!-- Left: Reviewed Sessions Timeline -->
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <h4 style="font-size: 0.95rem; color: var(--ink); margin: 0; border-bottom: 1.5px solid var(--slate); padding-bottom: 6px;">Reviewed Session Logs</h4>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            ${reviewedSessions.map(s => `
              <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; border: 1px solid var(--slate); border-radius: var(--radius-sm); background: #ffffff;">
                <div style="display: flex; flex-direction: column;">
                  <span style="font-weight: 700; font-size: 0.85rem;">Session: ${s.session_id}</span>
                  <span style="font-size: 0.75rem; color: var(--muted);">Date: ${s.date} · MLU: ${s.mlu.toFixed(2)} · Echolalia: ${(s.echolalia_ratio*100).toFixed(0)}%</span>
                </div>
                <span class="status-pill" style="font-size: 0.65rem; background: var(--mint-soft); color: var(--mint); font-weight: 600;">Therapist Verified</span>
              </div>
            `).join("")}
            ${reviewedSessions.length === 0 ? `<p class="empty-state" style="font-size: 0.8rem; padding: 12px; border: 1px dashed var(--line);">No sessions have been marked as reviewed by the clinician.</p>` : ""}
          </div>
        </div>

        <!-- Right: Data Limitations Warning -->
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <h4 style="font-size: 0.95rem; color: var(--ink); margin: 0; border-bottom: 1.5px solid var(--slate); padding-bottom: 6px;">Data Limitations & Disclaimers</h4>
          <div class="clinical-status-banner status-bad-soft" style="margin: 0; border-radius: var(--radius-md); padding: 14px; display: flex; flex-direction: column; gap: 8px;">
            <div style="display: flex; align-items: center; gap: 6px;">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--destructive)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              <span style="font-weight: bold; font-size: 0.8rem; color: var(--ink);">Assumed Constraints:</span>
            </div>
            <ul style="margin: 0; padding-left: 18px; font-size: 0.78rem; color: var(--muted); display: flex; flex-direction: column; gap: 4px; line-height: 1.4;">
              <li>Acoustic characteristics are subject to microphone positioning and ambient room noise levels.</li>
              <li>Descriptive NLP observations are based on transcript samples and do not reflect complete spontaneous speech contexts.</li>
              <li>This analysis is screening-support only and must never be utilized as an automated diagnosis of Autism Spectrum Disorder (ASD).</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- 3. Therapist-Reviewed Observations ONLY (Excludes Rejected) -->
      <div style="display: flex; flex-direction: column; gap: 12px;">
        <h4 style="font-size: 0.95rem; color: var(--ink); margin: 0; border-bottom: 1.5px solid var(--slate); padding-bottom: 6px;">Clinician-Verified Observations</h4>
        <div style="display: grid; grid-template-columns: 1fr; gap: 10px;">
          ${compiledObservations.map(obs => `
            <div style="border: 1px solid var(--line); border-radius: var(--radius-md); padding: 12px; display: flex; flex-direction: column; gap: 6px; background: #ffffff;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <strong style="font-size: 0.88rem; color: var(--ink);">${obs.name}</strong>
                  <span style="font-size: 0.7rem; background: var(--primary-soft); color: var(--primary); padding: 1px 6px; border-radius: 4px; font-weight: 600;">${obs.session_id}</span>
                </div>
                <span class="status-pill" style="font-size: 0.65rem; background: ${obs.status === "edited" ? "var(--medical-blue-soft)" : "var(--mint-soft)"}; color: ${obs.status === "edited" ? "var(--medical-blue)" : "var(--mint)"}; font-weight: 700; text-transform: uppercase;">
                  ${obs.status === "edited" ? "Clinician Amended" : "Clinician Approved"}
                </span>
              </div>
              <p style="font-size: 0.8rem; color: var(--muted); margin: 0; font-family: monospace; background: var(--bg); padding: 6px; border-radius: 4px; border-left: 3px solid var(--primary);">
                "${obs.snippet}"
              </p>
              <div style="font-size: 0.78rem; color: var(--ink); background: var(--cyan-pale); padding: 6px; border-radius: 4px; display: flex; gap: 4px;">
                <strong style="color: var(--medical-blue);">Note:</strong> <span>${obs.note}</span>
              </div>
            </div>
          `).join("")}
          ${compiledObservations.length === 0 ? `
            <div style="text-align: center; padding: 24px; border: 1.5px dashed var(--line); border-radius: var(--radius-md); background: var(--bg);">
              <span style="font-size: 0.8rem; color: var(--muted); font-style: italic;">No speech-language observations have been verified yet. Complete session reviews in the Transcripts tab to add items here.</span>
            </div>
          ` : ""}
        </div>
      </div>

      <!-- 4. SVG Progress Over Time and Feature Trends Charts -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
        <div style="display: flex; flex-direction: column; gap: 12px; border: 1px solid var(--line); border-radius: var(--radius-md); padding: 16px;">
          <h4 style="font-size: 0.9rem; color: var(--ink); margin: 0;">Screening Support score Trend</h4>
          ${scoreChartSvg}
        </div>
        <div style="display: flex; flex-direction: column; gap: 12px; border: 1px solid var(--line); border-radius: var(--radius-md); padding: 16px;">
          <h4 style="font-size: 0.9rem; color: var(--ink); margin: 0;">Mean Length of Utterance (MLU) Trend</h4>
          ${mluChartSvg}
        </div>
      </div>

      <!-- 5. Session Stepper Timeline -->
      <div style="border: 1px solid var(--line); border-radius: var(--radius-md); padding: 20px; display: flex; flex-direction: column; gap: 12px;">
        <h4 style="font-size: 0.9rem; color: var(--ink); margin: 0;">Session Completion Stepper</h4>
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-top: 10px;">
          ${stepperHtml}
        </div>
      </div>

      <!-- 6. Goals Progress Tracking -->
      <div style="border: 1px solid var(--line); border-radius: var(--radius-md); padding: 20px; display: flex; flex-direction: column; gap: 12px;">
        <h4 style="font-size: 0.9rem; color: var(--ink); margin: 0;">Therapy Goal Metric Checklists</h4>
        <div style="display: grid; gap: 10px;">
          ${goals.map(g => {
            const lastSess = sessions[sessions.length - 1];
            let status = "Active";
            let valStr = "N/A";
            if (lastSess && g.metric && g.metric !== "none") {
              const val = lastSess[g.metric] ?? 0;
              valStr = val.toFixed(2);
              if (val >= g.target_value) {
                status = "Achieved";
              }
            }
            return `
              <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.85rem; padding:8px; border-bottom:1px solid var(--slate);">
                <span>Goal: <strong>${g.text}</strong></span>
                <div style="display:flex; gap:12px; align-items:center;">
                  <span style="font-size:0.8rem; color:var(--muted);">Value: ${valStr} / Target: ${g.target_value.toFixed(2)}</span>
                  <span class="status-pill" style="font-size:0.65rem; background: ${status === "Achieved" ? "var(--mint-soft)" : "var(--amber-soft)"}; color: ${status === "Achieved" ? "var(--mint)" : "var(--amber-pending)"}; font-weight:700;">${status}</span>
                </div>
              </div>
            `;
          }).join("")}
        </div>
      </div>

      <!-- 7. Clinician Safe Thai Summary Section -->
      <div style="border: 1px solid var(--line); border-radius: var(--radius-md); padding: 20px; display: flex; flex-direction: column; gap: 12px;" class="print-hide">
        <h4 style="font-size: 0.95rem; color: var(--ink); margin: 0;">สรุปผลทางคลินิกภาษาไทย (Safe Thai Summary)</h4>
        <p style="font-size: 0.78rem; color: var(--muted); margin: 0;">ป้อนบทสรุปพัฒนาการเป็นภาษาไทยเพื่อเขียนลงในรายงานความก้าวหน้าฉบับพิมพ์</p>
        <textarea id="thai-summary-textarea" 
                  style="width: 100%; min-height: 120px; padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--line); font-family: inherit; line-height: 1.5; background: var(--bg); color: var(--ink); font-size:0.85rem;"
                  placeholder="ป้อนบทสรุปเพิ่มเติมสำหรับการส่งออก..."
        >${currentThaiSummary}</textarea>
      </div>

      <!-- Visible Thai Summary (displayed during print only) -->
      <div class="print-only" style="border: 1px solid var(--line); border-radius: var(--radius-md); padding: 20px; display: flex; flex-direction: column; gap: 8px;">
        <h4 style="font-size: 0.95rem; color: var(--ink); margin: 0;">สรุปพัฒนาการทางคลินิกภาษาไทย (Clinical Summary in Thai)</h4>
        <p style="font-size: 0.85rem; color: var(--ink); white-space: pre-wrap; line-height: 1.6;">${currentThaiSummary}</p>
      </div>

      <!-- 8. Safety & Diagnostic Boundary Banner -->
      <div class="clinical-status-banner status-bad-soft" style="margin: 0; padding: 12px; border-radius: var(--radius-md); display: flex; align-items: center; gap: 8px; page-break-inside: avoid;">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--destructive)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span style="font-size: 0.8rem; color: var(--ink); font-weight: 600; line-height:1.4;">
          <strong>Clinical Decision Support Boundary:</strong> This report is for clinical decision support and research demonstration only. It is not an automated diagnostic report and does not replace qualified clinical judgment.
        </span>
      </div>
    </div>
  `;
}

export function bindProgressReports(navigate) {
  const caseSelector = document.getElementById("progress-case-selector");
  if (caseSelector) {
    caseSelector.addEventListener("change", (e) => {
      store.setState({ selectedCaseId: e.target.value });
      navigate("progress");
    });
  }

  const textarea = document.getElementById("thai-summary-textarea");
  if (textarea) {
    textarea.addEventListener("input", (e) => {
      const state = store.getState();
      const caseId = state.selectedCaseId;
      const updatedSummaries = { ...(state.therapistThaiSummaries || {}), [caseId]: e.target.value };
      store.setState({ therapistThaiSummaries: updatedSummaries });
    });
  }

  // Anonymized JSON research summary download
  const downloadJsonBtn = document.getElementById("download-progress-json-btn");
  if (downloadJsonBtn) {
    downloadJsonBtn.addEventListener("click", () => {
      const caseId = downloadJsonBtn.getAttribute("data-case-id");
      const state = store.getState();
      const progress = getChildProgress(caseId);
      if (!progress) return;

      const reviews = state.observationsReviews || {};
      const childSessions = progress.sessions;
      const caseItem = progress.caseItem;

      // Extract accepted/edited observations
      const approvedObs = [];
      childSessions.forEach(s => {
        const sessReviews = reviews[s.session_id] || {};
        defaultObservations.forEach(obs => {
          const rev = sessReviews[obs.key] || {};
          if (rev.status === "accepted" || rev.status === "edited") {
            approvedObs.push({
              session_id: s.session_id,
              marker_key: obs.key,
              clinical_note: rev.note || "",
              status: rev.status
            });
          }
        });
      });

      // Construct anonymized research schema
      const researchData = {
        anonymized_child_code: caseItem.anonymized_child_code,
        age_months: caseItem.age_months,
        sex: caseItem.sex,
        total_sessions: childSessions.length,
        sessions_trends: childSessions.map(s => ({
          session_id: s.session_id,
          screening_support_score: s.score,
          mlu: s.mlu,
          ttr: s.ttr,
          echolalia_ratio: s.echolalia_ratio,
          total_utterances: s.total_utterances,
          turn_taking_count: s.turn_taking_count
        })),
        approved_speech_markers: approvedObs,
        thai_summary_length: (state.therapistThaiSummaries?.[caseId] || "").length,
        is_clinical_decision_support: true,
        compiled_at: new Date().toISOString()
      };

      const a = document.createElement("a");
      const file = new Blob([JSON.stringify(researchData, null, 2)], { type: "application/json" });
      a.href = URL.createObjectURL(file);
      a.download = `${caseItem.anonymized_child_code}_anonymized_research_summary.json`;
      a.click();

      addAudit("research_summary_downloaded", "ChildCase", caseId, `Downloaded anonymized research JSON summary for case ${caseId}`);
    });
  }

  // Export MD Progress report
  const downloadBtn = document.getElementById("download-progress-md-btn");
  if (downloadBtn) {
    downloadBtn.addEventListener("click", () => {
      const caseId = downloadBtn.getAttribute("data-case-id");
      const state = store.getState();

      const caseItem = state.cases.find(c => c.case_id === caseId);
      const childSessions = state.sessions.filter(s => s.case_id === caseId);
      const currentSummaryText = document.getElementById("thai-summary-textarea")?.value || "";

      const reportMd = buildProgressReportMarkdown(
        caseItem,
        childSessions,
        state.extractedFeatureOutputs,
        state.aiDecisionOutputs,
        state.transcripts,
        currentSummaryText
      );

      const reportId = `REPORT-${String(state.generatedReports.length + 1).padStart(3, "0")}`;
      const newReport = {
        report_id: reportId,
        case_id: caseId,
        owner_user_id: caseItem.owner_user_id,
        title: `Progress Report: ${caseItem.anonymized_child_code}`,
        ai_summary: reportMd,
        export_status: "completed",
        created_at: new Date().toISOString()
      };
      const nextReports = [...(state.generatedReports || []).filter(r => r.case_id !== caseId), newReport];
      store.setState({ generatedReports: nextReports });

      const a = document.createElement("a");
      const file = new Blob([reportMd], { type: "text/markdown" });
      a.href = URL.createObjectURL(file);
      a.download = `${caseItem.anonymized_child_code}_progress_report.md`;
      a.click();

      addAudit("report_exported", "ChildCase", caseId, `Exported progress report markdown for case ${caseId}`);
    });
  }

  // Print PDF Progress report
  const printBtn = document.getElementById("print-progress-pdf-btn");
  if (printBtn) {
    printBtn.addEventListener("click", () => {
      const caseId = store.getState().selectedCaseId;
      const state = store.getState();
      const caseItem = state.cases.find(c => c.case_id === caseId);
      const childSessions = state.sessions.filter(s => s.case_id === caseId);
      const currentSummaryText = document.getElementById("thai-summary-textarea")?.value || "";

      const reportMd = buildProgressReportMarkdown(
        caseItem,
        childSessions,
        state.extractedFeatureOutputs,
        state.aiDecisionOutputs,
        state.transcripts,
        currentSummaryText
      );

      const reportId = `REPORT-${String(state.generatedReports.length + 1).padStart(3, "0")}`;
      const newReport = {
        report_id: reportId,
        case_id: caseId,
        owner_user_id: caseItem.owner_user_id,
        title: `Progress Report: ${caseItem.anonymized_child_code}`,
        ai_summary: reportMd,
        export_status: "completed",
        created_at: new Date().toISOString()
      };
      const nextReports = [...(state.generatedReports || []).filter(r => r.case_id !== caseId), newReport];
      store.setState({ generatedReports: nextReports });

      window.print();
      addAudit("print_report", "ChildCase", store.getState().selectedCaseId, "Printed / Saved PDF progress report.");
    });
  }
}

function generateAutoSummaryText(sessions, sessionVocabs) {
  if (!sessions || sessions.length < 2) {
    return "- ข้อมูลเซสชันไม่เพียงพอสำหรับการวิเคราะห์แนวโน้มพัฒนาการข้ามเซสชัน (ต้องการอย่างน้อย 2 เซสชัน)";
  }

  const sessA = sessions[0];
  const sessB = sessions[sessions.length - 1];

  const mluA = sessA.mlu ?? 0;
  const mluB = sessB.mlu ?? 0;
  const ttrA = sessA.ttr ?? 0;
  const ttrB = sessB.ttr ?? 0;
  const echoA = sessA.echolalia_ratio ?? 0;
  const echoB = sessB.echolalia_ratio ?? 0;

  const mluChange = mluB - mluA;
  const ttrChange = ttrB - ttrA;
  const echoChange = echoB - echoA;

  let mluDesc = "";
  if (mluChange > 0.2) {
    mluDesc = `มีความก้าวหน้าขึ้นในการเพิ่มความยาวประโยคเฉลี่ย (MLU) (เพิ่มขึ้น ${mluChange.toFixed(2)} คำ จากเซสชันแรกที่ ${mluA.toFixed(2)} คำ เป็น ${mluB.toFixed(2)} คำ)`;
  } else if (mluChange < -0.2) {
    mluDesc = `ความยาวประโยคเฉลี่ย (MLU) ลดลงเล็กน้อย (ลดลง ${Math.abs(mluChange).toFixed(2)} คำ จาก ${mluA.toFixed(2)} คำ เป็น ${mluB.toFixed(2)} คำ) ควรติดตามและกระตุ้นการสื่อสารอย่างต่อเนื่อง`;
  } else {
    mluDesc = `ความยาวประโยคเฉลี่ย (MLU) ค่อนข้างคงที่ (อยู่ที่ประมาณ ${mluB.toFixed(2)} คำ)`;
  }

  let ttrDesc = "";
  if (ttrChange > 0.05) {
    ttrDesc = `มีความหลากคำและคลังคำศัพท์ที่กว้างขวางมากขึ้น (TTR เพิ่มขึ้น ${ttrChange.toFixed(2)} จาก ${ttrA.toFixed(2)} เป็น ${ttrB.toFixed(2)})`;
  } else {
    ttrDesc = `ความหลากหลายในการใช้คำศัพท์ค่อนข้างคงที่ (TTR ล่าสุดอยู่ที่ ${ttrB.toFixed(2)})`;
  }

  let echoDesc = "";
  if (echoChange < -0.05) {
    echoDesc = `มีอัตราการพูดซ้ำเลียนแบบ (Echolalia) ลดลงอย่างเห็นได้ชัด (ลดลง ${(Math.abs(echoChange) * 100).toFixed(0)}% จาก ${(echoA * 100).toFixed(0)}% เป็น ${(echoB * 100).toFixed(0)}%) แสดงถึงการตอบสนองที่ตรงวัตถุประสงค์ขึ้น`;
  } else if (echoChange > 0.05) {
    echoDesc = `พบพฤติกรรมการพูดซ้ำเลียนแบบ (Echolalia) เพิ่มขึ้นเล็กน้อย (เพิ่มขึ้น ${(echoChange * 100).toFixed(0)}% จาก ${(echoA * 100).toFixed(0)}% เป็น ${(echoB * 100).toFixed(0)}%) ควรส่งเสริมการพูดตอบโต้ที่เป็นธรรมชาติมากขึ้น`;
  } else {
    echoDesc = `อัตราการพูดซ้ำเลียนแบบค่อนข้างคงที่ (อยู่ที่ประมาณ ${(echoB * 100).toFixed(0)}%)`;
  }

  const vocabA = sessionVocabs[sessA.session_id] || [];
  const vocabB = sessionVocabs[sessB.session_id] || [];
  const wordsA = new Set(vocabA.map(v => v.word));
  const newWordsUsed = vocabB.filter(v => !wordsA.has(v.word)).map(v => v.word);
  let vocabDesc = "ไม่พบคำศัพท์ใหม่ที่แตกต่างอย่างมีนัยสำคัญ";
  if (newWordsUsed.length > 0) {
    vocabDesc = `ตรวจพบคำศัพท์ใหม่ที่เป็นประโยชน์เพิ่มเติมในเซสชันล่าสุด ได้แก่: ${newWordsUsed.slice(0, 5).join(', ')}`;
  }

  return `- **แนวโน้มความยาวประโยคเฉลี่ย (MLU Trend):** ${mluDesc}
- **ความหลากหลายของคำศัพท์ (TTR Trend):** ${ttrDesc}
- **พฤติกรรมการสื่อสารเลียนแบบ (Echolalia Trend):** ${echoDesc}
- **การเพิ่มคลังคำศัพท์ (Vocabulary Expansion):** ${vocabDesc}`;
}
