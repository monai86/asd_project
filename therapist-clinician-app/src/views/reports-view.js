import { store } from "../store/state.js";
import { getVisibleCases } from "../services/case-service.js";
import { getVisibleSessions } from "../services/session-service.js";
import { featureSchema } from "../store/mock-data.js";
import { SAFETY_DISCLAIMER } from "../constants.js";
import { renderSafetyBanner } from "../components/safety-banner.js";
import { addAudit } from "../services/audit-service.js";
import { buildProgressReportMarkdown } from "../services/report-service.js";
import { escapeHtml } from "@shared/utils/html.js";

// ── Module-level report state ──────────────────────────────────────
let reportMode = "list"; // "list" | "detail"
let reportCaseId = null;
let reportSessionId = null;

// ── Helper functions ───────────────────────────────────────────────

function getAgeBand(ageMonths) {
  if (ageMonths < 48) return "36-47";
  if (ageMonths < 60) return "48-59";
  return "60-72";
}

function formatAge(months) {
  const years = Math.floor(months / 12);
  const remaining = months % 12;
  return `${years} ปี ${remaining} เดือน (${years}y ${remaining}m)`;
}

function formatSessionType(type) {
  const map = {
    free_play: "Free Play (เล่นอิสระ)",
    therapy_session: "Therapy Session (เซสชันบำบัด)",
    structured_assessment: "Structured Assessment (การประเมินแบบมีโครงสร้าง)"
  };
  return map[type] || type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function h(value) {
  return escapeHtml(value);
}

function formatEvidenceItem(item) {
  if (!item) return "";
  if (typeof item === "string") return item;
  const feature = item.feature_key || item.feature || item.type || "evidence";
  const value = item.value === null || item.value === undefined ? "" : ` = ${item.value}`;
  const explanation = item.explanation || item.message || item.note || "";
  return `${feature}${value}${explanation ? ` — ${explanation}` : ""}`;
}

function formatConcernLevel(level) {
  const map = {
    no_concern: { label: "ไม่พบข้อกังวล (No Concern)", color: "var(--success)", bg: "rgba(34,197,94,0.12)" },
    watchful_review: { label: "ควรติดตาม (Watchful Review)", color: "var(--warning)", bg: "rgba(245,158,11,0.12)" },
    moderate_concern: { label: "มีข้อกังวลปานกลาง (Moderate Concern)", color: "var(--destructive)", bg: "rgba(244,63,94,0.12)" }
  };
  return map[level] || { label: level, color: "var(--muted)", bg: "var(--neutral-glass)" };
}

function getNormRange(key, norms, ageBand) {
  const bandNorms = norms[ageBand];
  if (!bandNorms || !bandNorms[key]) return "—";
  const n = bandNorms[key];
  return `${(n.mean - n.sd).toFixed(2)} – ${(n.mean + n.sd).toFixed(2)} (M=${n.mean.toFixed(2)})`;
}

function getFeatureStatus(key, value, norms, ageBand) {
  if (value === null || value === undefined) return "na";
  const bandNorms = norms[ageBand];

  // MLU flag: below mean - sd
  if (key === "mlu" && bandNorms?.mlu) {
    return value < (bandNorms.mlu.mean - bandNorms.mlu.sd) ? "flagged" : "normal";
  }
  // TTR flag: below mean - sd
  if (key === "ttr" && bandNorms?.ttr) {
    return value < (bandNorms.ttr.mean - bandNorms.ttr.sd) ? "flagged" : "normal";
  }
  // Echolalia ratio
  if (key === "echolalia_ratio") {
    return value > 0.10 ? "flagged" : "normal";
  }
  // Pronoun reversal
  if (key === "pronoun_reversal_count") {
    return value > 0 ? "flagged" : "normal";
  }
  // Unintelligible ratio
  if (key === "unintelligible_ratio") {
    return value > 0.30 ? "flagged" : "normal";
  }
  // Zero vocalizations
  if (key === "zero_vocalization_count") {
    return value > 1 ? "flagged" : "normal";
  }
  return "normal";
}

function formatFeatureValue(key, value) {
  if (value === null || value === undefined) return "—";
  const ratioKeys = ["mlu", "mluw", "ttr", "unintelligible_ratio", "question_ratio", "echolalia_ratio"];
  if (ratioKeys.includes(key)) return Number(value).toFixed(2);
  return String(value);
}

function generateRecommendations(features, aiOutput, norms, ageBand) {
  const recs = [];

  if (!features) return ["Review transcript quality and session context before finalizing clinical interpretations."];

  const bandNorms = norms[ageBand];

  // MLU below reference
  if (bandNorms?.mlu && features.mlu < (bandNorms.mlu.mean - bandNorms.mlu.sd)) {
    recs.push("Continue targeting Mean Length of Utterance through structured play and modeling longer phrases.");
  }

  // Echolalia elevated
  if (features.echolalia_ratio > 0.10) {
    recs.push("Monitor echolalia patterns across sessions. Differentiate between functional and non-functional echolalia.");
  }

  // Pronoun reversal
  if (features.pronoun_reversal_count > 0) {
    recs.push("Address pronoun reversal through naturalistic modeling (e.g., \"I want\" vs \"you want\").");
  }

  // Unintelligible high
  if (features.unintelligible_ratio > 0.30) {
    recs.push("Consider articulation assessment. Increase opportunities for speech clarity practice.");
  }

  // Zero vocalizations high
  if (features.zero_vocalization_count > 1) {
    recs.push("Investigate non-responsiveness patterns. Consider environmental factors and engagement strategies.");
  }

  // TTR below reference
  if (bandNorms?.ttr && features.ttr < (bandNorms.ttr.mean - bandNorms.ttr.sd)) {
    recs.push("Expand vocabulary diversity through thematic play, book reading, and new word exposure activities.");
  }

  // AI-driven recommendation
  if (aiOutput?.concern_level === "moderate_concern") {
    recs.push("Schedule a follow-up assessment session within 4–6 weeks to re-evaluate concern markers.");
  }

  // Always include
  recs.push("Review transcript quality and session context before finalizing clinical interpretations.");

  return recs;
}

function generateReportId() {
  return `RPT-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;
}

function getPreviewReportId(state, caseId, sessionId) {
  const existing = (state.generatedReports || []).find(
    r => r.case_id === caseId && r.session_id === sessionId
  );
  return existing?.report_id || `REPORT-PREVIEW-${sessionId}`;
}

function persistPrintableProgressReport(caseId, sessionId) {
  const state = store.getState();
  const caseItem = state.cases.find(c => c.case_id === caseId);
  if (!caseItem) return null;

  const caseSessions = state.sessions.filter(s => s.case_id === caseId);
  const existing = (state.generatedReports || []).find(
    r => r.case_id === caseId && r.session_id === sessionId
  );

  const reportMd = buildProgressReportMarkdown(
    caseItem,
    caseSessions,
    state.extractedFeatureOutputs,
    state.aiDecisionOutputs,
    state.transcripts,
    (state.therapistThaiSummaries && state.therapistThaiSummaries[caseId]) || ""
  );

  const newReport = {
    ...(existing || {}),
    report_id: existing?.report_id || `REPORT-${String((state.generatedReports || []).length + 1).padStart(3, "0")}`,
    case_id: caseId,
    session_id: sessionId,
    owner_user_id: caseItem.owner_user_id,
    title: `Progress Report: ${caseItem.anonymized_child_code}`,
    ai_summary: reportMd,
    export_status: "completed",
    created_at: existing?.created_at || new Date().toISOString(),
    updated_at: new Date().toISOString()
  };

  const nextReports = [
    ...(state.generatedReports || []).filter(r => r.report_id !== newReport.report_id),
    newReport
  ];
  store.setState({ generatedReports: nextReports });
  addAudit("print_report", "ChildCase", caseId, `Printed / saved PDF progress report ${newReport.report_id} for session ${sessionId}.`);
  return newReport;
}

export function __setReportsViewStateForTest(mode = "list", caseId = null, sessionId = null) {
  reportMode = mode;
  reportCaseId = caseId;
  reportSessionId = sessionId;
}

// ── Report List Mode ───────────────────────────────────────────────

function renderReportList() {
  const state = store.getState();
  const cases = getVisibleCases();
  const sessions = getVisibleSessions();

  // Cases that have at least one completed session
  const reportableCases = cases.filter(c => {
    const caseSessions = sessions.filter(
      s => s.case_id === c.case_id && s.feature_extraction_status === "completed"
    );
    return caseSessions.length > 0;
  });

  if (reportableCases.length === 0) {
    return `
      ${renderSafetyBanner()}
      <section class="dashboard-command">
        <div>
          <h2>รายงานติดตามพัฒนาการ <span style="font-weight:400; font-size:0.85em; color:var(--muted);">Progress Reports</span></h2>
          <p style="color:var(--muted); font-size:0.85rem;">No cases with completed feature extraction found. Complete a session pipeline first.</p>
        </div>
      </section>
      <p class="empty-state">ยังไม่มีข้อมูลเพียงพอสำหรับสร้างรายงาน กรุณาบันทึกและประมวลผลเซสชันก่อน</p>
    `;
  }

  const cardsHtml = reportableCases.map(c => {
    const caseSessions = sessions.filter(
      s => s.case_id === c.case_id && s.feature_extraction_status === "completed"
    );
    const latestSession = caseSessions.sort((a, b) => b.session_date.localeCompare(a.session_date))[0];
    const aiOut = state.aiDecisionOutputs[latestSession?.session_id];
    const score = aiOut?.screening_support_score ?? c.latest_score;

    const supportClass = c.support_level === "High" ? "status-bad"
      : c.support_level === "Medium" ? "status-warn"
      : "status-good";

    return `
      <div class="glass-card" style="padding: 20px; display: flex; flex-direction: column; gap: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <h3 style="margin: 0 0 4px; font-size: 1.05rem;">${h(c.display_label)}</h3>
            <p style="margin: 0; font-size: 0.8rem; color: var(--muted);">${h(c.anonymized_child_code)} · ${h(formatAge(c.age_months))}</p>
          </div>
          <span class="badge status-pill ${supportClass}" style="font-size: 0.75rem;">
            ${h(c.support_level)} Support
          </span>
        </div>
        <div style="display: flex; gap: 16px; font-size: 0.85rem; color: var(--muted);">
          <div>
            <strong style="color: var(--ink); font-size: 1.3rem;">${h(Number(score || 0).toFixed(2))}</strong>
            <span style="display: block; font-size: 0.72rem;">Screening Support Score</span>
          </div>
          <div>
            <strong style="color: var(--ink); font-size: 1.3rem;">${caseSessions.length}</strong>
            <span style="display: block; font-size: 0.72rem;">Completed Sessions</span>
          </div>
        </div>
        <button class="btn btn-primary generate-report-btn"
                data-case-id="${h(c.case_id)}"
                data-session-id="${h(latestSession.session_id)}"
                style="margin-top: auto;">
          Generate Progress Report
        </button>
      </div>
    `;
  }).join("");

  return `
    ${renderSafetyBanner()}
    <section class="dashboard-command">
      <div>
        <h2>รายงานติดตามพัฒนาการ <span style="font-weight:400; font-size:0.85em; color:var(--muted);">Progress Reports</span></h2>
        <p style="color:var(--muted); font-size:0.85rem;">Select a case to prepare a therapist-reviewed progress report. This tool is for progress tracking and clinical decision support only.</p>
      </div>
    </section>
    <section style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; margin-top: 8px;">
      ${cardsHtml}
    </section>
  `;
}

// ── Report Detail Mode ─────────────────────────────────────────────

function renderReportDetail() {
  const state = store.getState();
  const cases = getVisibleCases();
  const sessions = getVisibleSessions();

  const caseItem = cases.find(c => c.case_id === reportCaseId);
  if (!caseItem) {
    reportMode = "list";
    return renderReportList();
  }

  const caseSessions = sessions
    .filter(s => s.case_id === reportCaseId && s.feature_extraction_status === "completed")
    .sort((a, b) => a.session_date.localeCompare(b.session_date));

  const session = caseSessions.find(s => s.session_id === reportSessionId) || caseSessions[caseSessions.length - 1];
  if (!session) {
    reportMode = "list";
    return renderReportList();
  }

  // Ensure reportSessionId is set
  reportSessionId = session.session_id;

  const features = state.extractedFeatureOutputs[session.session_id]?.features;
  const featureOutput = state.extractedFeatureOutputs[session.session_id];
  const aiOutput = state.aiDecisionOutputs[session.session_id];
  const transcript = state.transcripts[session.session_id];
  const caseGoals = (state.goals || []).filter(g => g.case_id === caseItem.case_id);
  const norms = state.developmentalNorms || {};
  const ageBand = getAgeBand(caseItem.age_months);
  const currentUser = state.currentUser || {};
  const evaluator = state.users?.find(u => u.user_id === caseItem.owner_user_id) || currentUser;

  const reportId = getPreviewReportId(state, caseItem.case_id, session.session_id);
  const generationDate = new Date().toLocaleDateString("th-TH", {
    year: "numeric", month: "long", day: "numeric"
  });
  const generationTimestamp = new Date().toISOString();

  // ── Concern level badge ──
  const concern = formatConcernLevel(aiOutput?.concern_level);

  // ── Consent badge ──
  const consentColor = caseItem.consent_status === "granted" ? "var(--success)"
    : caseItem.consent_status === "pending" ? "var(--warning)"
    : "var(--destructive)";

  // ── Section 5: Feature table rows ──
  const featureRows = featureSchema.map(([key, label, category]) => {
    const val = features?.[key];
    const status = getFeatureStatus(key, val, norms, ageBand);
    const normRange = (key === "mlu" || key === "ttr") ? getNormRange(key, norms, ageBand) : "—";
    const statusLabel = status === "flagged" ? "Flagged" : status === "na" ? "—" : "Normal";
    const rowClass = status === "flagged" ? "feature-flag" : "feature-normal";

    return `
      <tr class="${rowClass}">
        <td>${h(label)}</td>
        <td style="font-variant-numeric: tabular-nums; font-weight: 600;">${h(formatFeatureValue(key, val))}</td>
        <td>${h(category)}</td>
        <td>${h(normRange)}</td>
        <td style="font-weight: 600;">${h(statusLabel)}</td>
      </tr>
    `;
  }).join("");

  // ── Section 6: Score bar ──
  const screeningScore = aiOutput?.screening_support_score ?? 0;
  const scorePercent = Math.min(100, Math.round(screeningScore * 100));
  const scoreColor = screeningScore >= 0.7 ? "var(--destructive)"
    : screeningScore >= 0.4 ? "var(--warning)"
    : "var(--success)";

  // ── Section 7: Longitudinal progress ──
  let longitudinalHtml = "";
  if (caseSessions.length > 1) {
    const longitudinalRows = caseSessions.map(s => {
      const f = state.extractedFeatureOutputs[s.session_id]?.features;
      const ai = state.aiDecisionOutputs[s.session_id];
      return `
        <tr${s.session_id === session.session_id ? ' style="background: rgba(99,102,241,0.08);"' : ""}>
          <td>${h(s.session_date)}</td>
          <td>${h(f?.mlu?.toFixed(2) ?? "—")}</td>
          <td>${h(f?.ttr?.toFixed(2) ?? "—")}</td>
          <td>${h(f?.echolalia_ratio?.toFixed(2) ?? "—")}</td>
          <td>${h(ai?.screening_support_score?.toFixed(2) ?? "—")}</td>
        </tr>
      `;
    }).join("");

    longitudinalHtml = `
      <section class="report-section">
        <h2>7. แนวโน้มพัฒนาการข้ามเซสชัน <span style="font-weight: 400; font-size: 0.85em;">Longitudinal Progress</span></h2>
        <table class="report-table">
          <thead>
            <tr>
              <th>Session Date</th>
              <th>MLU</th>
              <th>TTR</th>
              <th>Echolalia Ratio</th>
              <th>Screening Score</th>
            </tr>
          </thead>
          <tbody>
            ${longitudinalRows}
          </tbody>
        </table>
      </section>
    `;
  }

  // ── Section 8: Therapy goals ──
  let goalsHtml = "";
  if (caseGoals.length > 0) {
    const goalRows = caseGoals.map(g => {
      const met = g.metric !== "none" && g.target_value > 0
        ? (g.metric === "echolalia_ratio"
            ? g.current_value <= g.target_value
            : g.current_value >= g.target_value)
        : false;
      const statusPrefix = met ? "Met" : "Review";
      return `
        <tr>
          <td>${h(g.text || g.goal_text)}</td>
          <td style="text-align: center;">${h(g.target_value > 0 ? g.target_value.toFixed(2) : "—")}</td>
          <td style="text-align: center;">${h(g.current_value > 0 ? g.current_value.toFixed(2) : "—")}</td>
          <td style="text-align: center;">${g.metric !== "none" && g.target_value > 0 ? statusPrefix : "—"} ${h(g.status)}</td>
        </tr>
      `;
    }).join("");

    goalsHtml = `
      <section class="report-section">
        <h2>8. เป้าหมายการบำบัด <span style="font-weight: 400; font-size: 0.85em;">Therapy Goals</span></h2>
        <table class="report-table">
          <thead>
            <tr>
              <th>Goal</th>
              <th style="text-align:center;">Target</th>
              <th style="text-align:center;">Current</th>
              <th style="text-align:center;">Status</th>
            </tr>
          </thead>
          <tbody>
            ${goalRows}
          </tbody>
        </table>
      </section>
    `;
  }

  // ── Section 9: Recommendations ──
  const recommendations = generateRecommendations(features, aiOutput, norms, ageBand);
  const recommendationsHtml = recommendations.map((r, i) =>
    `<li style="margin-bottom: 6px;">${i + 1}. ${h(r)}</li>`
  ).join("");

  // ── Action bar (case/session selectors) ──
  const caseOptions = cases
    .filter(c => sessions.some(s => s.case_id === c.case_id && s.feature_extraction_status === "completed"))
    .map(c =>
      `<option value="${h(c.case_id)}" ${c.case_id === reportCaseId ? "selected" : ""}>${h(c.display_label)} (${h(c.anonymized_child_code)})</option>`
    ).join("");

  const sessionOptions = caseSessions.map(s =>
    `<option value="${h(s.session_id)}" ${s.session_id === reportSessionId ? "selected" : ""}>Session ${h(s.session_id.replace("SESSION-", ""))} — ${h(s.session_date)}</option>`
  ).join("");

  // ── Combine ──
  return `
    ${renderSafetyBanner()}

    <section class="dashboard-command" style="margin-bottom: 16px;">
      <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
        <button class="btn btn-ghost" id="report-back-btn">← Back to Reports</button>
        <select id="report-case-select" class="case-select-filter" aria-label="Select case for report">
          ${caseOptions}
        </select>
        <select id="report-session-select" class="case-select-filter" aria-label="Select session for report">
          ${sessionOptions}
        </select>
      </div>
      <div style="display: flex; gap: 10px;">
        <button class="btn btn-primary" id="report-print-btn">🖨 Print / Save PDF</button>
      </div>
    </section>

    <article class="report-document" style="
      background: #ffffff;
      color: #1a1a1a;
      max-width: 210mm;
      margin: 0 auto;
      padding: 40px 48px;
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-glass);
      font-family: 'Sarabun', 'Noto Sans Thai', 'Inter', sans-serif;
      font-size: 10.5pt;
      line-height: 1.65;
    ">

      <!-- ══ SECTION 1: Report Header ══ -->
      <header style="text-align: center; border-bottom: 3px double #334155; padding-bottom: 20px; margin-bottom: 24px;">
        <p style="margin: 0; font-size: 0.85em; color: #64748b; letter-spacing: 0.05em;">
          ${h(evaluator.organization || "Speech-Language Clinic")}
        </p>
        <h1 style="margin: 12px 0 4px; font-size: 1.6em; color: #0f172a; letter-spacing: 0.02em;">
          รายงานติดตามพัฒนาการภาษาและการพูด
        </h1>
        <p style="margin: 0 0 2px; font-size: 1em; color: #475569;">
          Speech-Language Progress Report
        </p>
        <p style="margin: 0; font-size: 0.82em; color: #94a3b8; font-style: italic;">
          Progress Tracking and Clinical Decision-Support Document — Not a Diagnostic Report
        </p>
        <p style="margin: 12px 0 0; font-size: 0.78em; color: #94a3b8;">
          Report ID: ${h(reportId)} &nbsp;|&nbsp; Generated: ${h(generationDate)}
        </p>
      </header>

      <!-- ══ SECTION 2: Patient Demographics ══ -->
      <section class="report-demographics" style="margin-bottom: 24px;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          2. ข้อมูลเด็กแบบไม่ระบุตัวตน <span style="font-weight: 400; font-size: 0.85em;">Anonymized Case Context</span>
        </h2>
        <table style="width: 100%; border-collapse: collapse; font-size: 0.92em;">
          <tbody>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; width: 28%; border-bottom: 1px solid #f1f5f9;">Case Code</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(caseItem.anonymized_child_code)}</td>
              <td style="padding: 6px 12px; color: #64748b; width: 28%; border-bottom: 1px solid #f1f5f9;">Display Label</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(caseItem.display_label)}</td>
            </tr>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">Age (อายุ)</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(formatAge(caseItem.age_months))}</td>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">Sex (เพศ)</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(caseItem.sex === "male" ? "ชาย (Male)" : caseItem.sex === "female" ? "หญิง (Female)" : caseItem.sex)}</td>
            </tr>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">Date of Report</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(generationDate)}</td>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">Evaluator</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(evaluator.name || "—")}, ${h(evaluator.credentials || "—")}</td>
            </tr>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">Organization</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(evaluator.organization || "—")}</td>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">Consent Status</td>
              <td style="padding: 6px 12px; border-bottom: 1px solid #f1f5f9;">
                <span style="display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.85em; font-weight: 600; color: ${consentColor}; background: ${caseItem.consent_status === 'granted' ? 'rgba(34,197,94,0.1)' : caseItem.consent_status === 'pending' ? 'rgba(245,158,11,0.1)' : 'rgba(244,63,94,0.1)'};">
                  ${h(caseItem.consent_status)}
                </span>
              </td>
            </tr>
            <tr>
              <td style="padding: 6px 12px; color: #64748b;">External Clinical Status</td>
              <td colspan="3" style="padding: 6px 12px; font-weight: 600;">${h(caseItem.external_clinical_status.replace(/_/g, " "))}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ══ SECTION 3: Referral & Background ══ -->
      <section class="report-section" style="margin-bottom: 24px;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          3. ข้อมูลส่งต่อและภูมิหลัง <span style="font-weight: 400; font-size: 0.85em;">Referral &amp; Background</span>
        </h2>
        <div style="margin-bottom: 10px;">
          <strong style="color: #475569;">Primary Concerns (ปัญหาหลัก):</strong>
          <p style="margin: 4px 0 0; padding-left: 8px; border-left: 3px solid #e2e8f0;">${h(caseItem.primary_concerns)}</p>
        </div>
        <div style="margin-bottom: 10px;">
          <strong style="color: #475569;">Clinical Notes (บันทึกทางคลินิก):</strong>
          <p style="margin: 4px 0 0; padding-left: 8px; border-left: 3px solid #e2e8f0;">${h(caseItem.notes || "ไม่มีบันทึกเพิ่มเติม (No additional notes)")}</p>
        </div>
        <div>
          <strong style="color: #475569;">External Clinical Status:</strong>
          <span style="margin-left: 8px;">${h(caseItem.external_clinical_status.replace(/_/g, " "))}</span>
        </div>
      </section>

      <!-- ══ SECTION 4: Assessment Procedures ══ -->
      <section class="report-section" style="margin-bottom: 24px;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          4. กระบวนการประเมิน <span style="font-weight: 400; font-size: 0.85em;">Assessment Procedures</span>
        </h2>
        <table style="width: 100%; border-collapse: collapse; font-size: 0.92em;">
          <tbody>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; width: 35%; border-bottom: 1px solid #f1f5f9;">Session Type (รูปแบบเซสชัน)</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(formatSessionType(session.session_type))}</td>
            </tr>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">Session Date (วันที่)</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(session.session_date)}</td>
            </tr>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">Transcript QA Status</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(transcript?.qa_status || "—")} ${transcript?.qa_score != null ? `(Score: ${h(transcript.qa_score)})` : ""}</td>
            </tr>
            <tr>
              <td style="padding: 6px 12px; color: #64748b; border-bottom: 1px solid #f1f5f9;">Feature Schema Version</td>
              <td style="padding: 6px 12px; font-weight: 600; border-bottom: 1px solid #f1f5f9;">${h(featureOutput?.feature_schema_version || "14-feature-schema")}</td>
            </tr>
          </tbody>
        </table>
        <p style="margin-top: 10px; font-size: 0.82em; color: #94a3b8; font-style: italic;">
          Tool: Automated feature extraction prototype. All values require clinician review before interpretation.
        </p>
      </section>

      <!-- ══ SECTION 5: Feature Summary ══ -->
      <section class="report-feature-table" style="margin-bottom: 24px;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          5. สรุปคุณลักษณะทางภาษาและการพูด <span style="font-weight: 400; font-size: 0.85em;">Speech-Language Feature Summary</span>
        </h2>
        <table class="report-table" style="width: 100%; border-collapse: collapse; font-size: 0.88em;">
          <thead>
            <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1;">
              <th style="padding: 8px 10px; text-align: left; color: #475569; font-weight: 700;">Feature</th>
              <th style="padding: 8px 10px; text-align: left; color: #475569; font-weight: 700;">Value</th>
              <th style="padding: 8px 10px; text-align: left; color: #475569; font-weight: 700;">Category</th>
              <th style="padding: 8px 10px; text-align: left; color: #475569; font-weight: 700;">Reference Range</th>
              <th style="padding: 8px 10px; text-align: left; color: #475569; font-weight: 700;">Status</th>
            </tr>
          </thead>
          <tbody>
            ${featureRows}
          </tbody>
        </table>
        <p style="margin-top: 8px; font-size: 0.78em; color: #94a3b8;">
          Reference ranges based on developmental norms for age band ${h(ageBand)} months.
          Flagged items warrant further clinical review and are not diagnostic indicators.
        </p>
      </section>

      <!-- ══ SECTION 6: AI Decision-Support Output ══ -->
      <section class="report-ai-section" style="margin-bottom: 24px; page-break-inside: avoid;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          6. ผลลัพธ์ระบบสนับสนุนการตัดสินใจ <span style="font-weight: 400; font-size: 0.85em;">AI Decision-Support Output</span>
        </h2>

        <div style="display: flex; gap: 24px; align-items: center; margin-bottom: 16px;">
          <!-- Score -->
          <div style="text-align: center;">
            <div style="font-size: 2.4em; font-weight: 800; color: ${scoreColor}; line-height: 1.1;">
              ${h(screeningScore.toFixed(2))}
            </div>
            <div style="font-size: 0.78em; color: #94a3b8; margin-top: 2px;">Screening Support Score</div>
          </div>
          <!-- Progress bar -->
          <div style="flex: 1;">
            <div style="height: 14px; background: #e2e8f0; border-radius: 7px; overflow: hidden;">
              <div style="height: 100%; width: ${scorePercent}%; background: ${scoreColor}; border-radius: 7px; transition: width 0.3s ease;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px; font-size: 0.72em; color: #94a3b8;">
              <span>0.00</span>
              <span>0.50</span>
              <span>1.00</span>
            </div>
          </div>
        </div>

        <!-- Concern level -->
        <div style="margin-bottom: 14px;">
          <strong style="color: #475569;">Concern Level (ระดับความกังวล):</strong>
          <span style="display: inline-block; margin-left: 8px; padding: 3px 14px; border-radius: 14px; font-weight: 700; font-size: 0.88em; color: ${concern.color}; background: ${concern.bg};">
            ${h(concern.label)}
          </span>
        </div>

        <!-- Top contributing features -->
        <div style="margin-bottom: 14px;">
          <strong style="color: #475569;">Top Contributing Features:</strong>
          <ul style="margin: 6px 0 0; padding-left: 20px;">
            ${(aiOutput?.top_contributing_features || []).map(f => {
              const schema = featureSchema.find(([k]) => k === f);
              return `<li>${h(schema ? schema[1] : f)} <span style="color: #94a3b8;">(${h(f)})</span></li>`;
            }).join("")}
          </ul>
        </div>

        <!-- Evidence items -->
        <div style="margin-bottom: 14px;">
          <strong style="color: #475569;">Evidence Items:</strong>
          <ul style="margin: 6px 0 0; padding-left: 20px;">
            ${(aiOutput?.evidence_items || []).map(e => `<li>${h(formatEvidenceItem(e))}</li>`).join("")}
          </ul>
        </div>

        <!-- Explanation -->
        <div style="margin-bottom: 16px;">
          <strong style="color: #475569;">Explanation:</strong>
          <p style="margin: 4px 0 0; padding-left: 8px; border-left: 3px solid #e2e8f0;">
            ${h(aiOutput?.explanation || aiOutput?.plain_language_explanation || "No explanation available.")}
          </p>
        </div>

        <!-- Prominent disclaimer box -->
        <div style="
          padding: 14px 18px;
          border: 2px solid #f59e0b;
          border-radius: 8px;
          background: #fffbeb;
          color: #92400e;
          font-size: 0.88em;
          line-height: 1.5;
        ">
          <strong>ข้อความเตือนสำคัญ (Important Disclaimer):</strong><br>
          ผลลัพธ์ข้างต้นเป็นข้อมูลสนับสนุนการตัดสินใจทางคลินิกเท่านั้น ไม่ใช่ผลการวินิจฉัยโรค
          ค่าคะแนนและระดับความกังวลต้องได้รับการตีความร่วมกับบริบทเซสชัน คุณภาพถอดเสียง
          และวิจารณญาณของนักบำบัดที่มีความเชี่ยวชาญเสมอ<br>
          <em>The above outputs are clinical decision-support only and do not constitute a diagnosis.
          Scores and concern levels must always be interpreted alongside session context,
          transcript quality, and expert clinical judgment.</em>
        </div>
      </section>

      <!-- ══ SECTION 7: Longitudinal Progress ══ -->
      ${longitudinalHtml}

      <!-- ══ SECTION 8: Therapy Goals ══ -->
      ${goalsHtml}

      <!-- ══ SECTION 9: Clinical Recommendations ══ -->
      <section class="report-section" style="margin-bottom: 24px;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          ${longitudinalHtml && goalsHtml ? "9" : longitudinalHtml || goalsHtml ? "8" : "7"}. ข้อเสนอแนะทางคลินิก <span style="font-weight: 400; font-size: 0.85em;">Clinical Recommendations</span>
        </h2>
        <ol style="padding-left: 20px; margin: 0;">
          ${recommendationsHtml}
        </ol>
        <p style="margin-top: 10px; font-size: 0.82em; color: #94a3b8; font-style: italic;">
          Recommendations are auto-generated based on feature flags and AI output.
          They must be reviewed and adapted by the responsible clinician.
        </p>
      </section>

      <!-- ══ SECTION 10: Disclaimer & Signature ══ -->
      <section class="report-section" style="margin-bottom: 24px; page-break-inside: avoid;">
        <h2 style="font-size: 1.05em; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px;">
          ${longitudinalHtml && goalsHtml ? "10" : longitudinalHtml || goalsHtml ? "9" : "8"}. ข้อจำกัดความรับผิดชอบและลงนาม <span style="font-weight: 400; font-size: 0.85em;">Disclaimer &amp; Signature</span>
        </h2>

        <!-- Safety disclaimer box -->
        <div style="
          padding: 14px 18px;
          border: 2px solid #ef4444;
          border-radius: 8px;
          background: #fef2f2;
          color: #991b1b;
          font-size: 0.88em;
          line-height: 1.5;
          margin-bottom: 20px;
        ">
          <strong>⛔ Clinical Safety Disclaimer:</strong><br>
          ${h(SAFETY_DISCLAIMER)}
        </div>

        <!-- Clinician signature block -->
        <div style="
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          padding: 20px;
          background: #fafafa;
        ">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 20px; font-size: 0.92em;">
            <div>
              <span style="color: #64748b;">Clinician Name:</span>
              <strong style="display: block; margin-top: 2px;">${h(evaluator.name || "—")}</strong>
            </div>
            <div>
              <span style="color: #64748b;">Credentials:</span>
              <strong style="display: block; margin-top: 2px;">${h(evaluator.credentials || "—")}</strong>
            </div>
            <div>
              <span style="color: #64748b;">Organization:</span>
              <strong style="display: block; margin-top: 2px;">${h(evaluator.organization || "—")}</strong>
            </div>
            <div>
              <span style="color: #64748b;">Date:</span>
              <strong style="display: block; margin-top: 2px;">${h(generationDate)}</strong>
            </div>
          </div>

          <div style="margin-top: 16px;">
            <span style="color: #64748b; font-size: 0.85em;">Signature (ลงนาม):</span>
            <div style="
              margin-top: 8px;
              height: 48px;
              border-bottom: 2px dashed #cbd5e1;
            "></div>
          </div>

          <div style="margin-top: 14px; display: flex; gap: 16px; font-size: 0.85em; color: #64748b;">
            <label style="display: flex; align-items: center; gap: 6px;">
              <span style="display: inline-block; width: 16px; height: 16px; border: 2px solid #cbd5e1; border-radius: 3px;"></span>
              Reviewed and approved
            </label>
            <label style="display: flex; align-items: center; gap: 6px;">
              <span style="display: inline-block; width: 16px; height: 16px; border: 2px solid #cbd5e1; border-radius: 3px;"></span>
              Pending additional review
            </label>
          </div>
        </div>
      </section>

      <!-- ══ FOOTER ══ -->
      <footer style="
        border-top: 2px solid #e2e8f0;
        padding-top: 12px;
        margin-top: 20px;
        text-align: center;
        font-size: 0.75em;
        color: #94a3b8;
        line-height: 1.6;
      ">
        <p style="margin: 0;">Report ID: ${h(reportId)} &nbsp;|&nbsp; Generated: ${h(generationTimestamp)}</p>
        <p style="margin: 4px 0 0; font-weight: 600;">
          This document is clinical decision support only. It does not diagnose ASD.
        </p>
        <p style="margin: 2px 0 0;">
          เอกสารนี้ใช้เพื่อสนับสนุนการตัดสินใจทางคลินิกเท่านั้น ไม่ใช่การวินิจฉัยโรค ASD
        </p>
      </footer>

    </article>

    <style>
      .report-document .report-table tr.feature-flag {
        background: #fef2f2;
      }
      .report-document .report-table tr.feature-flag td:last-child {
        color: #dc2626;
      }
      .report-document .report-table tr.feature-normal td:last-child {
        color: #16a34a;
      }
      .report-document .report-table {
        width: 100%;
        border-collapse: collapse;
      }
      .report-document .report-table th,
      .report-document .report-table td {
        padding: 8px 10px;
        text-align: left;
        border-bottom: 1px solid #f1f5f9;
      }
      .report-document .report-table thead tr {
        background: #f8fafc;
        border-bottom: 2px solid #cbd5e1;
      }
      .report-document .report-table thead th {
        color: #475569;
        font-weight: 700;
      }
      .report-document .report-table tbody tr:hover {
        background: #f8fafc;
      }
      .report-document .report-section h2 {
        font-size: 1.05em;
        color: #1e293b;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 6px;
        margin-bottom: 12px;
      }

      @media print {
        .report-document {
          box-shadow: none !important;
          border-radius: 0 !important;
          max-width: 100% !important;
          padding: 20px !important;
        }
        .dashboard-command,
        .safety-banner,
        #report-back-btn,
        #report-print-btn,
        #report-case-select,
        #report-session-select {
          display: none !important;
        }
        .report-document .report-table tr.feature-flag {
          background: #fef2f2 !important;
          -webkit-print-color-adjust: exact;
          print-color-adjust: exact;
        }
      }
    </style>
  `;
}

// ── Main render function ───────────────────────────────────────────

export function renderReportsView() {
  if (reportMode === "detail" && reportCaseId) {
    return renderReportDetail();
  }
  return renderReportList();
}

// ── Bind event listeners ───────────────────────────────────────────

export function bindReportsView(navigate) {
  // Generate Report buttons (list mode)
  const generateBtns = document.querySelectorAll(".generate-report-btn");
  generateBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      reportMode = "detail";
      reportCaseId = btn.getAttribute("data-case-id");
      reportSessionId = btn.getAttribute("data-session-id");
      navigate("reports");
    });
  });

  // Back to reports list
  const backBtn = document.getElementById("report-back-btn");
  if (backBtn) {
    backBtn.addEventListener("click", () => {
      reportMode = "list";
      reportCaseId = null;
      reportSessionId = null;
      navigate("reports");
    });
  }

  // Print button
  const printBtn = document.getElementById("report-print-btn");
  if (printBtn) {
    printBtn.addEventListener("click", () => {
      if (reportCaseId && reportSessionId) {
        persistPrintableProgressReport(reportCaseId, reportSessionId);
      }
      window.print();
    });
  }

  // Case selector
  const caseSelect = document.getElementById("report-case-select");
  if (caseSelect) {
    caseSelect.addEventListener("change", (e) => {
      reportCaseId = e.target.value;
      reportSessionId = null; // reset to latest
      navigate("reports");
    });
  }

  // Session selector
  const sessionSelect = document.getElementById("report-session-select");
  if (sessionSelect) {
    sessionSelect.addEventListener("change", (e) => {
      reportSessionId = e.target.value;
      navigate("reports");
    });
  }
}
